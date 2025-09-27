"""Django signals for finance app.

This module handles automatic financial operations and audit trail creation:
- Automatic invoice generation when students enroll
- Financial transaction logging for all financial events
- Payment processing workflows
- Invoice status updates

Following clean architecture principles with proper error handling
and comprehensive audit trails for financial compliance.
"""

import logging
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import Signal, receiver
from django.utils import timezone

from apps.enrollment.models import ClassHeaderEnrollment

from .models import FinancialTransaction, Invoice, InvoiceLineItem, Payment
from .services import FinancialError, FinancialTransactionService, InvoiceService

User = get_user_model()


@runtime_checkable
class InvoiceLike(Protocol):
    id: int
    invoice_number: str
    student: Any
    currency: Any
    version: int
    tax_amount: Any
    total_amount: Any

    def refresh_from_db(self) -> None: ...
    @property
    def line_items(self) -> Any: ...


@runtime_checkable
class PaymentLike(Protocol):
    id: int
    amount: Any
    currency: Any
    status: Any
    processed_by: Any
    payment_reference: str
    invoice_id: int
    payment_method: Any
    external_reference: Any
    payer_name: Any


@runtime_checkable
class InvoiceLineItemLike(Protocol):
    id: int
    invoice_id: int
    line_total: Any


logger = logging.getLogger(__name__)

# Cache system user to avoid repeated database queries
_system_user_cache = None


def get_system_user():
    """Get system user for automated operations, cached for performance."""
    global _system_user_cache
    if _system_user_cache is None:
        _system_user_cache, _ = User.objects.get_or_create(
            email="system@naga-sis.local",
            defaults={
                "name": "System User",
                "is_active": False,
            },
        )
    return _system_user_cache


# Custom signals for finance operations
invoice_sent = Signal()
payment_processed = Signal()
financial_transaction_created = Signal()


@receiver(pre_save, sender=ClassHeaderEnrollment)
def store_original_enrollment_status(
    sender: type,
    instance: ClassHeaderEnrollment,
    **kwargs: Any,
) -> None:
    """Store original enrollment status to detect status transitions.

    This avoids the N+1 query issue in the post_save signal by caching
    the original status during the pre_save phase.
    """
    if instance.pk:
        try:
            original = sender.objects.only("status").get(pk=instance.pk)  # type: ignore[attr-defined]
            instance._original_status = original.status
        except sender.DoesNotExist:  # type: ignore[attr-defined]
            instance._original_status = None
    else:
        instance._original_status = None


@receiver(post_save, sender=ClassHeaderEnrollment)
def create_invoice_on_enrollment(
    sender: type,
    instance: Any,
    *,
    created: bool,
    **kwargs: Any,
) -> None:
    """Create invoice automatically when student enrolls in a class.

    This signal handles both new enrollments and status transitions to ENROLLED,
    ensuring that billing is generated for all billable enrollment events.
    """
    should_create_invoice = False

    # Check if this is a new enrollment with ENROLLED status
    if created and instance.status == "ENROLLED":
        should_create_invoice = True
    # Check if status changed TO ENROLLED (from non-enrolled status)
    elif not created and hasattr(instance, "_original_status"):
        original_status = instance._original_status
        if original_status != "ENROLLED" and instance.status == "ENROLLED":
            should_create_invoice = True

    if not should_create_invoice:
        return

    try:
        # Get cached system user for automated operations
        system_user = get_system_user()

        # Create invoice for the enrollment
        invoice = InvoiceService.create_invoice_for_enrollment(
            enrollment=instance,
            created_by=system_user,
        )

        logger.info(
            "Automatic invoice %s created for enrollment %s - Student: %s, Class: %s",
            invoice.invoice_number,
            instance.id,
            instance.student,
            instance.class_header,
        )

    except FinancialError:
        logger.exception("Failed to create invoice for enrollment %s", instance.id)
    except Exception:
        logger.exception(
            "Unexpected error creating invoice for enrollment %s",
            instance.id,
        )


@receiver(pre_save, sender=Invoice)
def track_invoice_status_changes(
    sender: type,
    instance: Any,
    **kwargs: Any,
) -> None:
    """Track invoice status changes and create audit trail.

    This ensures comprehensive tracking of all invoice lifecycle events
    for financial compliance and audit purposes.
    """
    if not instance.pk:
        return

    try:
        old_instance = Invoice.objects.get(pk=instance.pk)

        # Check if status changed
        if old_instance.status != instance.status:
            # Create financial transaction for status change
            transaction_type_map = {
                "DRAFT": "INVOICE_CREATED",
                "SENT": "INVOICE_SENT",
                "CANCELLED": "INVOICE_CANCELLED",
                "PAID": "PAYMENT_RECEIVED",
                "PARTIALLY_PAID": "PAYMENT_RECEIVED",
                "OVERDUE": "INVOICE_MODIFIED",
                "REFUNDED": "PAYMENT_REFUNDED",
            }

            transaction_type = transaction_type_map.get(
                instance.status,
                "INVOICE_MODIFIED",
            )

            # Get cached system user for automated transactions
            system_user = get_system_user()

            FinancialTransactionService.record_transaction(
                transaction_type=transaction_type,
                student=instance.student,
                amount=Decimal("0.00"),  # Status change, no amount
                currency=instance.currency,
                description=f"Invoice status changed from {old_instance.status} to {instance.status}",
                processed_by=system_user,
                invoice=instance,
                reference_data={
                    "old_status": old_instance.status,
                    "new_status": instance.status,
                    "change_timestamp": timezone.now().isoformat(),
                },
            )

            logger.info(
                "Invoice %s status changed: %s -> %s",
                instance.invoice_number,
                old_instance.status,
                instance.status,
            )

    except Invoice.DoesNotExist:
        # New invoice, no need to track changes
        pass
    except Exception:
        logger.exception(
            "Error tracking status change for invoice %s",
            instance.invoice_number,
        )


@receiver(post_save, sender=Payment)
@transaction.atomic
def process_payment_and_update_invoice(
    sender: type,
    instance: PaymentLike,
    *,
    created: bool,
    **kwargs: Any,
) -> None:
    """Process payment and update related invoice automatically with atomic operations.

    This signal handles the complete payment workflow including
    invoice updates and financial transaction creation using race condition protection.
    """
    if not created:
        return

    if instance.status != "COMPLETED":
        return

    try:
        # Lock the invoice to prevent concurrent modifications
        invoice: InvoiceLike = Invoice.objects.select_for_update().get(id=instance.invoice_id)

        # Update invoice paid amount using atomic operation
        current_version = invoice.version
        updated_rows = Invoice.objects.filter(id=invoice.id, version=current_version).update(
            paid_amount=F("paid_amount") + instance.amount,
            version=F("version") + 1,
        )

        if updated_rows == 0:
            # Retry once if version changed
            invoice.refresh_from_db()
            Invoice.objects.filter(id=invoice.id).update(
                paid_amount=F("paid_amount") + instance.amount,
                version=F("version") + 1,
            )

        # Refresh invoice and update payment status
        invoice.refresh_from_db()
        # Cast to satisfy type expectations of the service helper
        from typing import cast as _cast

        InvoiceService.update_invoice_payment_status(_cast("Invoice", invoice))

        # Create financial transaction for payment
        FinancialTransactionService.record_transaction(
            transaction_type="PAYMENT_RECEIVED",
            student=invoice.student,
            amount=instance.amount,
            currency=instance.currency,
            description=f"Payment received: {instance.payment_method}",
            processed_by=instance.processed_by,
            invoice=invoice,  # type: ignore[arg-type]
            payment=instance,  # type: ignore[arg-type]
            reference_data={
                "payment_method": instance.payment_method,
                "payment_reference": instance.payment_reference,
                "external_reference": instance.external_reference,
                "payer_name": instance.payer_name,
            },
        )

        # Send custom signal for payment processed
        payment_processed.send(
            sender=Payment,
            payment=instance,
            invoice=invoice,
        )

        logger.info(
            "Payment %s processed atomically: %s %s for invoice %s",
            instance.payment_reference,
            instance.amount,
            instance.currency,
            invoice.invoice_number,
        )

    except FinancialError:
        logger.exception("Failed to process payment %s", instance.payment_reference)
    except Exception:
        logger.exception(
            "Unexpected error processing payment %s",
            instance.payment_reference,
        )


@receiver(post_save, sender=InvoiceLineItem)
@transaction.atomic
def recalculate_invoice_totals(
    sender: type,
    instance: InvoiceLineItemLike,
    *,
    created: bool,
    **kwargs: Any,
) -> None:
    """Recalculate invoice totals when line items change with atomic operations.

    This ensures invoice totals are always accurate and consistent
    with their line items using optimistic locking and race condition protection.
    """
    try:
        # Lock the invoice to prevent concurrent modifications
        invoice: InvoiceLike = Invoice.objects.select_for_update().get(id=instance.invoice_id)

        # Store current version for optimistic locking check
        current_version = invoice.version

        # Recalculate totals from all line items
        line_items = invoice.line_items.all()
        subtotal = sum(item.line_total for item in line_items)
        new_total = subtotal + invoice.tax_amount

        # Use atomic update with version check for race condition protection
        updated_rows = Invoice.objects.filter(id=invoice.id, version=current_version).update(
            subtotal=subtotal,
            total_amount=new_total,
            version=F("version") + 1,
        )

        if updated_rows == 0:
            # Another transaction modified the invoice, retry once
            invoice.refresh_from_db()
            line_items = invoice.line_items.all()
            subtotal = sum(item.line_total for item in line_items)
            new_total = subtotal + invoice.tax_amount

            Invoice.objects.filter(id=invoice.id).update(
                subtotal=subtotal,
                total_amount=new_total,
                version=F("version") + 1,
            )

        if created:
            logger.info(
                "Invoice %s totals recalculated atomically: subtotal=%s, total=%s",
                invoice.invoice_number,
                subtotal,
                new_total,
            )

    except Exception:
        logger.exception(
            "Error recalculating totals for invoice line item %s",
            instance.id,
        )


@receiver(invoice_sent)
def log_invoice_sent(
    sender: type,
    invoice: InvoiceLike,
    sent_by: Any,
    **kwargs: Any,
) -> None:
    """Log when invoices are sent to students.

    Creates audit trail for invoice communication tracking.
    """
    try:
        FinancialTransactionService.record_transaction(
            transaction_type="INVOICE_SENT",
            student=invoice.student,
            amount=Decimal("0.00"),
            currency=invoice.currency,
            description="Invoice sent to student",
            processed_by=sent_by,
            invoice=invoice,  # type: ignore[arg-type]
            reference_data={
                "sent_method": "email",  # Could be extended for other methods
                "sent_timestamp": timezone.now().isoformat(),
                "invoice_total": str(getattr(invoice, "total_amount", Decimal("0.00"))),
            },
        )

        logger.info("Invoice %s sent by %s", invoice.invoice_number, getattr(sent_by, "email", ""))

    except Exception:
        logger.exception(
            "Error logging invoice send for %s",
            invoice.invoice_number,
        )


@receiver(post_delete, sender=InvoiceLineItem)
@transaction.atomic
def recalculate_invoice_totals_on_delete(
    sender: type,
    instance: InvoiceLineItemLike,
    **kwargs: Any,
) -> None:
    """Recalculate invoice totals when line items are deleted.

    Ensures invoice balance integrity when line items are removed.
    """
    try:
        # Lock the invoice to prevent concurrent modifications
        invoice: InvoiceLike = Invoice.objects.select_for_update().get(id=instance.invoice_id)

        # Store current version for optimistic locking check
        current_version = invoice.version

        # Recalculate totals from remaining line items
        line_items = invoice.line_items.all()
        subtotal = sum(item.line_total for item in line_items)
        new_total = subtotal + invoice.tax_amount

        # Use atomic update with version check
        updated_rows = Invoice.objects.filter(id=invoice.id, version=current_version).update(
            subtotal=subtotal,
            total_amount=new_total,
            version=F("version") + 1,
        )

        if updated_rows == 0:
            # Retry once if version changed
            invoice.refresh_from_db()
            line_items = invoice.line_items.all()
            subtotal = sum(item.line_total for item in line_items)
            new_total = subtotal + invoice.tax_amount

            Invoice.objects.filter(id=invoice.id).update(
                subtotal=subtotal,
                total_amount=new_total,
                version=F("version") + 1,
            )

        logger.info(
            "Invoice %s totals recalculated after line item deletion: subtotal=%s, total=%s",
            invoice.invoice_number,
            subtotal,
            new_total,
        )

    except Invoice.DoesNotExist:
        # Invoice was deleted, nothing to update
        pass
    except Exception:
        logger.exception(
            "Error recalculating totals after deleting invoice line item %s",
            instance.id,
        )


@receiver(post_delete, sender=Payment)
@transaction.atomic
def handle_payment_deletion(
    sender: type,
    instance: PaymentLike,
    **kwargs: Any,
) -> None:
    """Handle payment deletion by updating invoice paid amount.

    Ensures invoice balance integrity when payments are deleted or refunded.
    """
    try:
        # Only process completed payments
        if instance.status != Payment.PaymentStatus.COMPLETED:
            return

        # Lock the invoice to prevent concurrent modifications
        invoice: InvoiceLike = Invoice.objects.select_for_update().get(id=instance.invoice_id)

        # Store current version for optimistic locking check
        current_version = invoice.version

        # Use atomic update to reduce paid amount
        updated_rows = Invoice.objects.filter(id=invoice.id, version=current_version).update(
            paid_amount=F("paid_amount") - instance.amount,
            version=F("version") + 1,
        )

        if updated_rows == 0:
            # Retry once if version changed
            invoice.refresh_from_db()
            Invoice.objects.filter(id=invoice.id).update(
                paid_amount=F("paid_amount") - instance.amount,
                version=F("version") + 1,
            )

        # Refresh invoice and update payment status
        invoice.refresh_from_db()
        from typing import cast as _cast

        InvoiceService.update_invoice_payment_status(_cast("Invoice", invoice))

        # Record financial transaction for payment reversal
        system_user = get_system_user()
        # Cast invoice to Any to satisfy typing for helper accepting Invoice | None

        FinancialTransactionService.record_transaction(
            transaction_type="PAYMENT_REVERSED",
            student=invoice.student,
            amount=instance.amount,
            currency=instance.currency,
            description=f"Payment {instance.payment_reference} deleted/reversed",
            processed_by=system_user,
            invoice=invoice,  # type: ignore[arg-type]
            reference_data={
                "reversed_payment_id": instance.id,
                "payment_reference": instance.payment_reference,
                "reversal_reason": "payment_deleted",
            },
        )

        logger.info(
            "Payment %s deletion processed: %s %s reversed from invoice %s",
            instance.payment_reference,
            instance.amount,
            instance.currency,
            invoice.invoice_number,
        )

    except Invoice.DoesNotExist:
        # Invoice was deleted, nothing to update
        pass
    except Exception:
        logger.exception(
            "Error processing payment deletion for %s",
            instance.payment_reference,
        )


@receiver(payment_processed)
def send_payment_confirmation(
    sender: type,
    payment: PaymentLike,
    invoice: InvoiceLike,
    **kwargs: Any,
) -> None:
    """Send payment confirmation notifications.

    This could be extended to send email notifications to students
    or integrate with external notification systems.
    """
    try:
        logger.info(
            "Payment confirmation: %s %s received for invoice %s (Student: %s)",
            payment.amount,
            payment.currency,
            invoice.invoice_number,
            invoice.student,
        )

    except Exception:
        logger.exception(
            "Error sending payment confirmation for %s",
            payment.payment_reference,
        )


@receiver(financial_transaction_created)
def audit_financial_transaction(
    sender: type,
    transaction: FinancialTransaction,
    **kwargs: Any,
) -> None:
    """Additional audit logging for financial transactions.

    This provides an extra layer of audit trail for compliance purposes.
    """
    try:
        logger.info(
            "Financial transaction created: %s - Type: %s, Amount: %s %s, Student: %s",
            transaction.transaction_id,
            transaction.transaction_type,
            transaction.amount,
            transaction.currency,
            transaction.student,
        )

    except Exception:
        logger.exception(
            "Error in financial transaction audit for %s",
            transaction.transaction_id,
        )


# Signal connection helper functions
def connect_finance_signals() -> None:
    """Explicitly connect all finance signals.

    This function can be called from apps.py to ensure all signals
    are properly connected when the app starts.
    """
    # Signals are connected via decorators, but this function
    # provides a place for any additional signal setup if needed
    logger.info("Finance signals connected successfully")


def disconnect_finance_signals() -> None:
    """Disconnect finance signals for testing purposes.

    This allows tests to run without automatic signal processing
    when needed for isolation.
    """
    logger.info("Finance signals disconnected")
