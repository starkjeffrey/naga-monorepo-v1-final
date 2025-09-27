"""Financial transaction service for audit trails.

Provides comprehensive logging of all financial operations
for compliance, reporting, and audit purposes.
"""

from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.finance.models import (
    FinancialTransaction,
    Invoice,
    Payment,
)

from .separated_pricing_service import FinancialError


class FinancialTransactionService:
    """Service for financial transaction audit trails.

    Provides comprehensive logging of all financial operations
    for compliance, reporting, and audit purposes.
    """

    @staticmethod
    def generate_transaction_id() -> str:
        """Generate a unique transaction ID.

        Returns:
            Unique transaction identifier
        """
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        sequence = (
            FinancialTransaction.objects.filter(
                transaction_id__startswith=f"TXN-{timestamp}",
            ).count()
            + 1
        )

        return f"TXN-{timestamp}-{sequence:06d}"

    @staticmethod
    @transaction.atomic
    def record_transaction(
        transaction_type: str,
        student,
        amount: Decimal,
        currency: str,
        description: str,
        processed_by,
        invoice: Invoice | None = None,
        payment: Payment | None = None,
        reference_data: dict[str, Any] | None = None,
    ) -> FinancialTransaction:
        """Record a financial transaction for audit purposes.

        Args:
            transaction_type: Type of transaction
            student: StudentProfile instance
            amount: Transaction amount
            currency: Currency code
            description: Transaction description
            processed_by: User who processed the transaction
            invoice: Related invoice (optional)
            payment: Related payment (optional)
            reference_data: Additional reference data (optional)

        Returns:
            Created FinancialTransaction instance
        """
        transaction_id = FinancialTransactionService.generate_transaction_id()

        try:
            return FinancialTransaction.objects.create(
                transaction_id=transaction_id,
                transaction_type=transaction_type,
                student=student,
                invoice=invoice,
                payment=payment,
                amount=amount,
                currency=currency,
                description=description,
                reference_data=reference_data or {},
                processed_by=processed_by,
            )
        except IntegrityError as e:
            msg = f"Financial transaction creation failed due to integrity constraint: {e}"
            raise FinancialError(msg) from e
        except ValidationError as e:
            msg = f"Financial transaction creation failed due to validation error: {e}"
            raise FinancialError(msg) from e

    @staticmethod
    def get_student_financial_history(
        student,
        term=None,
        limit: int = 50,
    ) -> list[FinancialTransaction]:
        """Get financial transaction history for a student.

        Args:
            student: StudentProfile instance
            term: Term to filter by (optional)
            limit: Maximum number of transactions to return

        Returns:
            List of FinancialTransaction instances
        """
        queryset = (
            FinancialTransaction.objects.filter(student=student)
            .select_related("invoice", "payment", "processed_by")
            .order_by("-transaction_date")
        )

        if term:
            queryset = queryset.filter(invoice__term=term)

        return list(queryset[:limit])
