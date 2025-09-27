"""Cashier service for cashier operations and cash management.

Handles cashier sessions, cash drawer management, and
daily reconciliation with proper controls and audit trails.
"""

from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Sum
from django.utils import timezone

from apps.finance.models import (
    CashierSession,
    Currency,
    FinancialTransaction,
    Payment,
)

from .separated_pricing_service import FinancialError, normalize_decimal
from .transaction_service import FinancialTransactionService


class CashierService:
    """Service for cashier operations and cash management.

    Handles cashier sessions, cash drawer management, and
    daily reconciliation with proper controls and audit trails.
    """

    @staticmethod
    def get_or_create_session(user):
        """Get or create a cashier session for the user.

        Args:
            user: User object

        Returns:
            CashierSession instance
        """
        today = timezone.now().date()

        # Check for existing open session
        session = CashierSession.objects.filter(cashier=user, opened_at__date=today, closed_at__isnull=True).first()

        if not session:
            # Create new session
            session = CashierSession.objects.create(
                cashier=user, opened_at=timezone.now(), opening_balance=Decimal("0.00")
            )

        return session

    @staticmethod
    @transaction.atomic
    def open_cash_drawer(user, opening_cash: Decimal) -> None:
        """Open cash drawer with opening count.

        Args:
            user: Cashier user
            opening_cash: Opening cash amount
        """
        session = CashierService.get_or_create_session(user)

        if session.opening_balance > Decimal("0.00"):
            msg = "Cash drawer already opened for this session"
            raise FinancialError(msg)

        session.opening_balance = normalize_decimal(opening_cash)
        session.save()

        # Log transaction
        from typing import Any as _Any
        from typing import cast

        FinancialTransactionService.record_transaction(
            transaction_type=cast("_Any", FinancialTransaction.TransactionType).CASH_DRAWER_OPEN,
            student=None,  # No student for drawer operations
            amount=opening_cash,
            currency=Currency.USD,
            description=f"Cash drawer opened with ${opening_cash}",
            processed_by=user,
            reference_data={
                "session_id": session.id,
                "opening_cash": float(opening_cash),
            },
        )

    @staticmethod
    @transaction.atomic
    def close_cash_drawer(user, closing_cash: Decimal) -> Decimal:
        """Close cash drawer with closing count and calculate variance.

        Args:
            user: Cashier user
            closing_cash: Counted closing cash amount

        Returns:
            Variance amount (positive = over, negative = short)
        """
        session = CashierService.get_or_create_session(user)

        if session.closed_at is not None:
            msg = "No open cash drawer session found"
            raise FinancialError(msg)

        # Calculate expected cash
        cash_payments = Payment.objects.filter(
            processed_by=user,
            payment_date__date=session.opened_at.date(),
            payment_method=Payment.PaymentMethod.CASH,
            status=Payment.PaymentStatus.COMPLETED,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        expected_cash = (session.opening_balance or Decimal("0.00")) + cash_payments
        variance = normalize_decimal(closing_cash) - expected_cash

        # Update session
        # variance will be calculated automatically by the model property
        session.closed_at = timezone.now()
        session.closing_balance = normalize_decimal(closing_cash)
        session.expected_balance = expected_cash
        session.save()

        # Log transaction
        from typing import Any as _Any
        from typing import cast

        FinancialTransactionService.record_transaction(
            transaction_type=cast("_Any", FinancialTransaction.TransactionType).CASH_DRAWER_CLOSE,
            student=None,
            amount=closing_cash,
            currency=Currency.USD,
            description=f"Cash drawer closed. Variance: ${variance}",
            processed_by=user,
            reference_data={
                "session_id": session.id,
                "opening_cash": float(session.opening_balance),
                "expected_cash": float(expected_cash),
                "closing_cash": float(closing_cash),
                "variance": float(variance),
            },
        )

        return variance

    @staticmethod
    def get_current_cash_balance(user) -> Decimal:
        """Get current expected cash balance for cashier.

        Args:
            user: Cashier user

        Returns:
            Current expected cash balance
        """
        session = CashierService.get_or_create_session(user)

        if session.closed_at is not None:
            return Decimal("0.00")

        # Calculate cash payments for today
        cash_payments = Payment.objects.filter(
            processed_by=user,
            payment_date__date=session.opened_at.date(),
            payment_method=Payment.PaymentMethod.CASH,
            status=Payment.PaymentStatus.COMPLETED,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        opening_cash = session.opening_balance or Decimal("0.00")
        return opening_cash + cash_payments

    @staticmethod
    def get_session_summary(user, date=None):
        """Get session summary for reporting.

        Args:
            user: Cashier user
            date: Date to get summary for (defaults to today)

        Returns:
            Dictionary with session summary
        """
        if date is None:
            date = timezone.now().date()

        # Get all payments for the date
        payments = Payment.objects.filter(processed_by=user, payment_date=date, status=Payment.PaymentStatus.COMPLETED)

        # Summarize by payment method
        summary_by_method = payments.values("payment_method").annotate(total=Sum("amount"), count=Count("id"))

        # Get session info
        session = CashierSession.objects.filter(cashier=user, date=date).first()

        return {
            "date": date,
            "cashier": str(user),
            "session": {
                "status": "OPEN" if session and not session.closed_at else "CLOSED" if session else "NO_SESSION",
                "opening_cash": (float(session.opening_balance) if session and session.opening_balance else 0),
                "closing_cash": (float(session.closing_balance) if session and session.closing_balance else 0),
                "variance": (float(session.variance) if session and session.closing_balance else 0),
            },
            "payments_by_method": {
                item["payment_method"]: {
                    "total": float(item["total"]),
                    "count": item["count"],
                }
                for item in summary_by_method
            },
            "total_collected": float(payments.aggregate(Sum("amount"))["amount__sum"] or 0),
            "transaction_count": payments.count(),
        }
