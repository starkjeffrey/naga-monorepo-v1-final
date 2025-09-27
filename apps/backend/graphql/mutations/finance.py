"""Finance-related GraphQL mutations."""

import strawberry
from datetime import datetime

from ..types.finance import (
    POSTransactionInput,
    POSTransactionResult,
    PaymentReminderInput,
    PaymentReminderResult
)


@strawberry.type
class FinanceMutations:
    """Finance-related GraphQL mutations."""

    @strawberry.mutation
    def process_pos_transaction(
        self,
        info,
        transaction_input: POSTransactionInput
    ) -> POSTransactionResult:
        """Process a point-of-sale transaction."""

        try:
            # Mock transaction processing
            import uuid
            transaction_id = str(uuid.uuid4())

            return POSTransactionResult(
                transaction_id=transaction_id,
                amount=transaction_input.amount,
                status="completed",
                receipt_number=f"POS-{transaction_id[:8].upper()}",
                processed_at=datetime.now()
            )

        except Exception as e:
            return POSTransactionResult(
                transaction_id="",
                amount="0.00",
                status="failed",
                receipt_number="",
                processed_at=datetime.now()
            )

    @strawberry.mutation
    def setup_payment_reminders(
        self,
        info,
        reminder_input: PaymentReminderInput
    ) -> PaymentReminderResult:
        """Setup automated payment reminders."""

        try:
            # Mock reminder setup
            students_processed = len(reminder_input.student_ids) if reminder_input.student_ids else 50
            reminders_created = students_processed * len(reminder_input.reminder_days)

            return PaymentReminderResult(
                success=True,
                reminders_created=reminders_created,
                students_processed=students_processed,
                message=f"Created {reminders_created} reminders for {students_processed} students"
            )

        except Exception as e:
            return PaymentReminderResult(
                success=False,
                reminders_created=0,
                students_processed=0,
                message=f"Failed to setup reminders: {str(e)}"
            )