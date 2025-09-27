"""Payment service for processing payments and managing student balances.

Handles payment recording, validation, invoice updates, refunds,
and student balance tracking with comprehensive audit trails.
"""

from datetime import timedelta
from decimal import Decimal
from typing import Any, cast

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

from apps.common.utils import get_current_date
from apps.finance.models import (
    FinancialTransaction,
    Invoice,
    Payment,
)

from .separated_pricing_service import FinancialError


class PaymentService:
    """Service for payment processing and management.

    Handles payment recording, validation, invoice updates,
    student balance tracking, and refunds with comprehensive audit trails.
    """

    @staticmethod
    def generate_payment_reference() -> str:
        """Generate a unique payment reference number.

        Returns:
            Unique payment reference
        """
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        sequence = (
            Payment.objects.filter(
                payment_reference__startswith=f"PAY-{timestamp}",
            ).count()
            + 1
        )

        return f"PAY-{timestamp}-{sequence:04d}"

    @staticmethod
    @transaction.atomic
    def record_payment(
        invoice: Invoice,
        amount: Decimal,
        payment_method: str,
        payment_date,
        processed_by,
        payer_name: str = "",
        external_reference: str = "",
        notes: str = "",
        idempotency_key: str = "",
    ) -> Payment:
        """Record a payment against an invoice with race condition protection.

        Args:
            invoice: Invoice being paid
            amount: Payment amount
            payment_method: Payment method used
            payment_date: Date payment was made
            processed_by: User processing the payment
            payer_name: Name of person making payment
            external_reference: External payment reference
            notes: Additional notes
            idempotency_key: Unique key to prevent duplicate payments

        Returns:
            Created Payment instance

        Raises:
            FinancialError: If payment is invalid
        """
        # Import here to avoid circular dependency
        from .invoice_service import InvoiceService
        from .transaction_service import FinancialTransactionService

        # Validate payment amount
        if amount <= 0:
            msg = "Payment amount must be positive"
            raise FinancialError(msg)

        # Lock the invoice to prevent concurrent modifications
        inv = cast("Any", invoice)
        locked_invoice = Invoice.objects.select_for_update().get(id=inv.id)

        # Check for duplicate payment if idempotency key provided
        if idempotency_key:
            existing_payment = Payment.objects.filter(legacy_receipt_reference=idempotency_key).first()
            if existing_payment:
                return existing_payment

        # Re-calculate remaining amount with lock held
        remaining_amount = locked_invoice.amount_due
        if amount > remaining_amount:
            msg = f"Payment amount {amount} exceeds remaining balance {remaining_amount}"
            raise FinancialError(msg)

        # Check for potential duplicate based on amount and timing (last 5 minutes)
        cutoff_time = timezone.now() - timedelta(minutes=5)
        similar_payment = Payment.objects.filter(
            invoice=locked_invoice,
            amount=amount,
            payment_method=payment_method,
            processed_date__gte=cutoff_time,
            status=Payment.PaymentStatus.COMPLETED,
        ).first()

        if similar_payment and not idempotency_key:
            msg = "Similar payment detected within 5 minutes. Use idempotency key to confirm."
            raise FinancialError(msg)

        # Generate payment reference
        payment_reference = PaymentService.generate_payment_reference()

        # Create payment record
        try:
            payment = Payment.objects.create(
                payment_reference=payment_reference,
                invoice=locked_invoice,
                amount=amount,
                currency=locked_invoice.currency,
                payment_method=payment_method,
                payment_date=payment_date,
                processed_date=payment_date,
                status=Payment.PaymentStatus.COMPLETED,
                payer_name=payer_name or str(locked_invoice.student),
                external_reference=external_reference,
                notes=notes,
                processed_by=processed_by,
                legacy_receipt_reference=idempotency_key or None,
            )
        except IntegrityError as e:
            msg = f"Payment creation failed due to integrity constraint: {e}"
            raise FinancialError(msg) from e
        except ValidationError as e:
            msg = f"Payment creation failed due to validation error: {e}"
            raise FinancialError(msg) from e

        # Update invoice paid amount using F() expression for atomicity
        Invoice.objects.filter(id=locked_invoice.id).update(paid_amount=F("paid_amount") + amount)

        # Refresh the invoice to get updated values
        locked_invoice.refresh_from_db()

        # Update invoice status
        InvoiceService.update_invoice_payment_status(locked_invoice)

        # Record financial transaction
        FinancialTransactionService.record_transaction(
            transaction_type=FinancialTransaction.TransactionType.PAYMENT_RECEIVED,
            student=inv.student,
            amount=amount,
            currency=inv.currency,
            description=f"Payment {payment_reference} for invoice {inv.invoice_number}",
            invoice=inv,
            payment=payment,
            processed_by=processed_by,
            reference_data={
                "payment_method": payment_method,
                "external_reference": external_reference,
            },
        )

        return payment

    @staticmethod
    @transaction.atomic
    def refund_payment(
        payment: Payment,
        refund_amount: Decimal,
        reason: str,
        processed_by,
    ) -> Payment:
        """Process a payment refund with race condition protection.

        Args:
            payment: Original payment to refund
            refund_amount: Amount to refund
            reason: Reason for refund
            processed_by: User processing the refund

        Returns:
            Created refund Payment instance

        Raises:
            FinancialError: If refund is invalid
        """
        # Import here to avoid circular dependency
        from .invoice_service import InvoiceService
        from .transaction_service import FinancialTransactionService

        if refund_amount <= 0:
            msg = "Refund amount must be positive"
            raise FinancialError(msg)

        if refund_amount > payment.amount:
            msg = "Refund amount cannot exceed original payment"
            raise FinancialError(msg)

        if payment.status != Payment.PaymentStatus.COMPLETED:
            msg = "Can only refund completed payments"
            raise FinancialError(msg)

        # Lock the invoice to prevent concurrent modifications
        locked_invoice = Invoice.objects.select_for_update().get(id=cast("Any", payment.invoice).id)

        # Verify refund doesn't exceed paid amount
        if refund_amount > locked_invoice.paid_amount:
            msg = f"Refund amount {refund_amount} exceeds paid amount {locked_invoice.paid_amount}"
            raise FinancialError(msg)

        # Create refund payment record
        refund_reference = PaymentService.generate_payment_reference()

        try:
            refund = Payment.objects.create(
                payment_reference=refund_reference,
                invoice=locked_invoice,
                amount=-refund_amount,  # Negative amount for refund
                currency=payment.currency,
                payment_method=payment.payment_method,
                payment_date=get_current_date(),
                status=Payment.PaymentStatus.REFUNDED,
                payer_name=payment.payer_name,
                external_reference=f"REFUND-{payment.payment_reference}",
                notes=f"Refund: {reason}",
                processed_by=processed_by,
            )
        except IntegrityError as e:
            msg = f"Refund payment creation failed due to integrity constraint: {e}"
            raise FinancialError(msg) from e
        except ValidationError as e:
            msg = f"Refund payment creation failed due to validation error: {e}"
            raise FinancialError(msg) from e

        # Update invoice paid amount using F() expression for atomicity
        Invoice.objects.filter(id=locked_invoice.id).update(paid_amount=F("paid_amount") - refund_amount)

        # Refresh the invoice to get updated values
        locked_invoice.refresh_from_db()

        # Update invoice status
        InvoiceService.update_invoice_payment_status(locked_invoice)

        # Record financial transaction
        FinancialTransactionService.record_transaction(
            transaction_type=FinancialTransaction.TransactionType.PAYMENT_REFUNDED,
            student=cast("Any", payment.invoice).student,
            amount=-refund_amount,
            currency=payment.currency,
            description=f"Refund {refund_reference} for payment {payment.payment_reference}",
            invoice=cast("Any", payment.invoice),
            payment=refund,
            processed_by=processed_by,
            reference_data={
                "original_payment": payment.payment_reference,
                "refund_reason": reason,
            },
        )

        return refund

    @staticmethod
    def get_student_balance(student) -> Decimal:
        """Get current outstanding balance for a student.

        Args:
            student: StudentProfile instance

        Returns:
            Outstanding balance amount
        """
        # Get all outstanding invoices
        outstanding_invoices = Invoice.objects.filter(
            student=student,
            status__in=[
                Invoice.InvoiceStatus.SENT,
                Invoice.InvoiceStatus.PARTIALLY_PAID,
                Invoice.InvoiceStatus.OVERDUE,
            ],
        )

        total_balance = Decimal("0.00")
        for invoice in outstanding_invoices:
            total_balance += invoice.amount_due

        return total_balance

    @staticmethod
    @transaction.atomic
    def process_payment(
        student,
        amount: Decimal,
        payment_method: str,
        invoices: list[Invoice] | None = None,
        reference: str = "",
        notes: str = "",
        processed_by=None,
    ) -> Payment | None:
        """Process a payment and apply to invoices with race condition protection.

        Args:
            student: StudentProfile instance
            amount: Payment amount
            payment_method: Payment method
            invoices: List of invoices to apply payment to
            reference: External reference
            notes: Payment notes
            processed_by: User processing payment

        Returns:
            Created Payment instance (first one if multiple)
        """
        # Validate amount
        if amount <= 0:
            msg = "Payment amount must be positive"
            raise FinancialError(msg)

        # If no invoices specified, get oldest outstanding with lock
        if not invoices:
            invoices_list = list(
                Invoice.objects.select_for_update()
                .filter(
                    student=student,
                    status__in=[
                        Invoice.InvoiceStatus.SENT,
                        Invoice.InvoiceStatus.PARTIALLY_PAID,
                        Invoice.InvoiceStatus.OVERDUE,
                    ],
                )
                .order_by("due_date")
            )
            invoices = invoices_list
        else:
            # Lock all provided invoices to prevent concurrent modification
            invoice_ids = [cast("Any", inv).id for inv in invoices]
            invoices = list(Invoice.objects.select_for_update().filter(id__in=invoice_ids).order_by("due_date"))

        # Apply payment to invoices in order
        remaining_amount = amount
        payments_created = []

        # invoices should not be None at this point due to the logic above
        assert invoices is not None, "invoices should be set by the logic above"

        for invoice in invoices:
            if remaining_amount <= 0:
                break

            # Calculate amount to apply to this invoice (using locked invoice data)
            amount_due = invoice.amount_due
            amount_to_apply = min(remaining_amount, amount_due)

            # Create payment record (record_payment handles its own locking)
            payment = PaymentService.record_payment(
                invoice=invoice,
                amount=amount_to_apply,
                payment_method=payment_method,
                payment_date=timezone.now().date(),
                processed_by=processed_by,
                external_reference=reference,
                notes=notes,
            )

            payments_created.append(payment)
            remaining_amount -= amount_to_apply

        # If there's remaining amount, create as advance payment
        if remaining_amount > 0 and invoices:
            # Apply to last invoice as overpayment
            payment = PaymentService.record_payment(
                invoice=invoices[-1],
                amount=remaining_amount,
                payment_method=payment_method,
                payment_date=timezone.now().date(),
                processed_by=processed_by,
                external_reference=reference,
                notes=f"Advance payment: {notes}",
            )
            payments_created.append(payment)

        return payments_created[0] if payments_created else None

    @staticmethod
    @transaction.atomic
    def process_refund(payment: Payment, amount: Decimal, reason: str, processed_by) -> Payment:
        """Process a refund for a payment.

        Args:
            payment: Original payment
            amount: Refund amount
            reason: Refund reason
            processed_by: User processing refund

        Returns:
            Refund Payment instance
        """
        return PaymentService.refund_payment(
            payment=payment,
            refund_amount=amount,
            reason=reason,
            processed_by=processed_by,
        )
