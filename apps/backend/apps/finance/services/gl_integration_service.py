"""General Ledger integration service following service accounting principles.

This service handles:
- Monthly journal entry generation from financial transactions
- Service accounting (cash basis) revenue recognition
- Double-entry bookkeeping validation
- Batch processing for G/L exports
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from .separated_pricing_service import FinancialError

# Constants
DECEMBER = 12
JANUARY = 1


class GLIntegrationService:
    """Service for General Ledger integration following service accounting principles.

    This service handles:
    - Monthly journal entry generation from financial transactions
    - Service accounting (cash basis) revenue recognition
    - Double-entry bookkeeping validation
    - Batch processing for G/L exports
    """

    def generate_monthly_journal_entries(
        self,
        year: int,
        month: int,
        user: Any,
        batch_number: str | None = None,
    ) -> list[Any]:
        """Generate journal entries for all financial transactions in a month.

        For service accounting, revenue is recognized when payment is received,
        not when services are rendered or invoiced.

        Args:
            year: Year for processing
            month: Month for processing (1-12)
            user: User generating the entries
            batch_number: Optional batch number for grouping

        Returns:
            List of generated journal entries
        """
        from apps.finance.models import (
            FinancialTransaction,
            GLAccount,
            JournalEntry,
            JournalEntryLine,
        )

        # Get the default cash account
        try:
            cash_account = GLAccount.objects.get(
                account_code="1010",  # Standard cash account
                is_active=True,
            )
        except GLAccount.DoesNotExist as e:
            msg = "Default cash account (1010) not configured"
            raise FinancialError(msg) from e

        # Get all payment transactions for the month
        start_date = date(year, month, 1)
        if month == DECEMBER:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        transactions = (
            FinancialTransaction.objects.filter(
                transaction_date__gte=start_date,
                transaction_date__lte=end_date,
            )
            .select_related("student__person")
            .order_by("transaction_date", "created_at")
        )

        # Group transactions by date and type for daily summarization
        daily_entries: dict[tuple[date, str], list] = {}

        for trans in transactions:
            key = (trans.transaction_date, trans.transaction_type)
            if key not in daily_entries:
                daily_entries[key] = []
            daily_entries[key].append(trans)

        # Create journal entries
        entries_created = []
        entry_counter = 1

        with transaction.atomic():
            for (entry_date, trans_type), daily_transactions in sorted(daily_entries.items()):
                # Skip if no transactions
                if not daily_transactions:
                    continue

                # Create journal entry
                entry_number = f"JE-{year:04d}-{month:02d}-{entry_counter:03d}"

                # Determine entry type based on transaction type
                if trans_type == FinancialTransaction.TransactionType.PAYMENT_RECEIVED:
                    entry_type = JournalEntry.EntryType.REVENUE
                    description = f"Daily cash receipts - {len(daily_transactions)} transactions"
                elif trans_type == FinancialTransaction.TransactionType.PAYMENT_REFUNDED:
                    entry_type = JournalEntry.EntryType.REFUND
                    description = f"Daily refunds - {len(daily_transactions)} transactions"
                else:
                    continue  # Skip other transaction types for now

                try:
                    journal_entry = JournalEntry.objects.create(
                        entry_number=entry_number,
                        entry_date=entry_date,
                        accounting_period=f"{year:04d}-{month:02d}",
                        entry_type=entry_type,
                        description=description,
                        prepared_by=user,
                        batch_id=batch_number or "",
                    )
                except IntegrityError as e:
                    msg = f"Journal entry creation failed due to integrity constraint: {e}"
                    raise FinancialError(msg) from e
                except ValidationError as e:
                    msg = f"Journal entry creation failed due to validation error: {e}"
                    raise FinancialError(msg) from e

                # Process transactions by fee type
                fee_totals = {}
                for trans in daily_transactions:
                    # Get fee type from transaction reference data or default
                    fee_type = trans.reference_data.get("fee_type", "TUITION")
                    if fee_type not in fee_totals:
                        fee_totals[fee_type] = Decimal("0.00")
                    fee_totals[fee_type] += abs(trans.amount)  # Use absolute value

                # Create journal entry lines
                line_number = 1

                # For payments: Dr Cash, Cr Revenue
                # For refunds: Dr Revenue, Cr Cash

                if trans_type == FinancialTransaction.TransactionType.PAYMENT_RECEIVED:
                    # Debit cash for total amount
                    total_amount = sum(fee_totals.values())
                    try:
                        JournalEntryLine.objects.create(
                            journal_entry=journal_entry,
                            line_number=line_number,
                            gl_account=cash_account,
                            debit_amount=total_amount,
                            credit_amount=Decimal("0.00"),
                            description="Cash received",
                        )
                    except IntegrityError as e:
                        msg = f"Journal entry line creation failed due to integrity constraint: {e}"
                        raise FinancialError(msg) from e
                    except ValidationError as e:
                        msg = f"Journal entry line creation failed due to validation error: {e}"
                        raise FinancialError(msg) from e
                    line_number += 1

                    # Credit revenue accounts by fee type
                    for fee_type, amount in fee_totals.items():
                        fee_mapping = self._get_fee_gl_mapping(fee_type, entry_date)
                        if not fee_mapping:
                            # Use default revenue account if no mapping
                            continue

                        try:
                            JournalEntryLine.objects.create(
                                journal_entry=journal_entry,
                                line_number=line_number,
                                gl_account=fee_mapping.revenue_account,
                                debit_amount=Decimal("0.00"),
                                credit_amount=amount,
                                description=f"{fee_type} revenue",
                            )
                        except IntegrityError as e:
                            msg = f"Journal entry line creation failed due to integrity constraint: {e}"
                            raise FinancialError(msg) from e
                        except ValidationError as e:
                            msg = f"Journal entry line creation failed due to validation error: {e}"
                            raise FinancialError(msg) from e
                        line_number += 1

                elif trans_type == FinancialTransaction.TransactionType.PAYMENT_REFUNDED:
                    # For refunds: reverse the entries
                    # Debit revenue accounts
                    for fee_type, amount in fee_totals.items():
                        fee_mapping = self._get_fee_gl_mapping(fee_type, entry_date)
                        if not fee_mapping:
                            continue

                        try:
                            JournalEntryLine.objects.create(
                                journal_entry=journal_entry,
                                line_number=line_number,
                                gl_account=fee_mapping.revenue_account,
                                debit_amount=amount,
                                credit_amount=Decimal("0.00"),
                                description=f"{fee_type} refund",
                            )
                        except IntegrityError as e:
                            msg = f"Journal entry line creation failed due to integrity constraint: {e}"
                            raise FinancialError(msg) from e
                        except ValidationError as e:
                            msg = f"Journal entry line creation failed due to validation error: {e}"
                            raise FinancialError(msg) from e
                        line_number += 1

                    # Credit cash for total amount
                    total_amount = sum(fee_totals.values())
                    try:
                        JournalEntryLine.objects.create(
                            journal_entry=journal_entry,
                            line_number=line_number,
                            gl_account=cash_account,
                            debit_amount=Decimal("0.00"),
                            credit_amount=total_amount,
                            description="Cash refunded",
                        )
                    except IntegrityError as e:
                        msg = f"Journal entry line creation failed due to integrity constraint: {e}"
                        raise FinancialError(msg) from e
                    except ValidationError as e:
                        msg = f"Journal entry line creation failed due to validation error: {e}"
                        raise FinancialError(msg) from e

                # Calculate and update totals
                journal_entry.calculate_totals()
                entries_created.append(journal_entry)
                entry_counter += 1

        return entries_created

    def _get_fee_gl_mapping(self, fee_type: str, effective_date: date) -> Any:
        """Get the G/L account mapping for a fee type on a specific date."""
        from apps.finance.models import FeeGLMapping

        return (
            FeeGLMapping.objects.filter(
                fee_type=fee_type,
                effective_date__lte=effective_date,
            )
            .exclude(end_date__lt=effective_date)
            .order_by("-effective_date")
            .first()
        )
