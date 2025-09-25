"""Invoice service for invoice generation and management.

Handles invoice creation, modification, and status management
with proper audit trails and business rule enforcement.
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
    FeePricing,
    FinancialTransaction,
    Invoice,
    InvoiceLineItem,
    Payment,
)

from .separated_pricing_service import (
    FinancialError,
    PricingReportService,
    SeparatedPricingService,
    normalize_decimal,
)


def safe_decimal_multiply(a: Decimal, b: Decimal) -> Decimal:
    """Safely multiply two decimal values."""
    result = normalize_decimal(a) * normalize_decimal(b)
    return normalize_decimal(result)


class InvoiceService:
    """Service for invoice generation and management.

    Handles invoice creation, modification, and status management
    with proper audit trails and business rule enforcement.
    """

    @staticmethod
    def generate_invoice_number(term, student) -> str:
        """Generate a unique invoice number.

        Args:
            term: Term instance
            student: StudentProfile instance

        Returns:
            Unique invoice number
        """
        # Format: YYYY-TERM-STUDENTID-XXXX
        year = term.start_date.year
        term_code = term.code if hasattr(term, "code") else str(term.id)
        student_id = student.student_id if hasattr(student, "student_id") else str(student.id)

        # Get next sequence number for this term/student
        existing_count = Invoice.objects.filter(
            student=student,
            term=term,
        ).count()

        sequence = existing_count + 1

        return f"{year}-{term_code}-{student_id}-{sequence:04d}"

    @staticmethod
    @transaction.atomic
    def create_invoice(
        student,
        term,
        enrollments: list,
        due_days: int = 30,
        notes: str = "",
        created_by=None,
    ) -> Invoice:
        """Create a new invoice for a student's enrollments.

        Args:
            student: StudentProfile instance
            term: Term instance
            enrollments: List of ClassHeaderEnrollment instances
            due_days: Number of days until payment is due
            notes: Additional notes for the invoice
            created_by: User creating the invoice

        Returns:
            Created Invoice instance

        Raises:
            FinancialError: If invoice creation fails
        """
        # Import here to avoid circular dependency
        from .transaction_service import FinancialTransactionService

        # Calculate costs
        cost_breakdown = PricingReportService.calculate_total_cost(
            student=student,
            term=term,
            enrollments=enrollments,
        )

        if not cost_breakdown["course_costs"]:
            msg = "No valid course costs found for invoice"
            raise FinancialError(msg)

        # Generate invoice number
        invoice_number = InvoiceService.generate_invoice_number(term, student)

        # Create invoice
        issue_date = get_current_date()
        due_date = issue_date + timedelta(days=due_days)

        try:
            invoice = Invoice.objects.create(
                invoice_number=invoice_number,
                student=student,
                term=term,
                issue_date=issue_date,
                due_date=due_date,
                subtotal=normalize_decimal(cost_breakdown["subtotal"]),
                tax_amount=normalize_decimal(cost_breakdown["tax_amount"]),
                total_amount=normalize_decimal(cost_breakdown["total_amount"]),
                currency=cost_breakdown["currency"],
                notes=notes,
            )
        except IntegrityError as e:
            msg = f"Failed to create invoice: {e}"
            raise FinancialError(msg) from e
        except ValidationError as e:
            msg = f"Invalid invoice data: {e}"
            raise FinancialError(msg) from e

        # Create line items for courses
        for course_cost in cost_breakdown["course_costs"]:
            if "error" not in course_cost:
                enrollment = next(e for e in enrollments if e.id == course_cost["enrollment_id"])

                unit_price = normalize_decimal(course_cost["price"])
                quantity = normalize_decimal("1.00")
                line_total = safe_decimal_multiply(unit_price, quantity)

                try:
                    InvoiceLineItem.objects.create(
                        invoice=invoice,
                        line_item_type=InvoiceLineItem.LineItemType.COURSE,
                        description=f"Tuition: {course_cost['course']}",
                        enrollment=enrollment,
                        unit_price=unit_price,
                        quantity=quantity,
                        line_total=line_total,
                    )
                except IntegrityError as e:
                    msg = f"Failed to create course line item: {e}"
                    raise FinancialError(msg) from e
                except ValidationError as e:
                    msg = f"Invalid course line item data: {e}"
                    raise FinancialError(msg) from e

        # Create line items for fees
        for fee in cost_breakdown["applicable_fees"]:
            try:
                fee_pricing = FeePricing.objects.get(id=fee["fee_pricing_id"])
            except FeePricing.DoesNotExist as e:
                msg = f"Fee pricing not found: {fee['fee_pricing_id']}"
                raise FinancialError(msg) from e

            unit_price = normalize_decimal(fee["amount"])
            quantity = normalize_decimal(fee["quantity"])
            line_total = safe_decimal_multiply(unit_price, quantity)

            try:
                InvoiceLineItem.objects.create(
                    invoice=invoice,
                    line_item_type=InvoiceLineItem.LineItemType.FEE,
                    description=fee["name"],
                    fee_pricing=fee_pricing,
                    unit_price=unit_price,
                    quantity=quantity,
                    line_total=line_total,
                )
            except IntegrityError as e:
                msg = f"Failed to create fee line item: {e}"
                raise FinancialError(msg) from e
            except ValidationError as e:
                msg = f"Invalid fee line item data: {e}"
                raise FinancialError(msg) from e

        # Create financial transaction record
        FinancialTransactionService.record_transaction(
            transaction_type=FinancialTransaction.TransactionType.INVOICE_CREATED,
            student=student,
            amount=invoice.total_amount,
            currency=invoice.currency,
            description=f"Invoice {invoice.invoice_number} created",
            invoice=invoice,
            processed_by=created_by,
            reference_data={
                "enrollments": [e.id for e in enrollments],
                "cost_breakdown": cost_breakdown,
            },
        )

        return invoice

    @staticmethod
    @transaction.atomic
    def send_invoice(invoice: Invoice, sent_by=None) -> Invoice:
        """Mark an invoice as sent and update status.

        Args:
            invoice: Invoice instance to send
            sent_by: User sending the invoice

        Returns:
            Updated Invoice instance
        """
        # Import here to avoid circular dependency
        from .transaction_service import FinancialTransactionService

        if invoice.status != Invoice.InvoiceStatus.DRAFT:
            msg = "Only draft invoices can be sent"
            raise FinancialError(msg)

        invoice.status = Invoice.InvoiceStatus.SENT
        invoice.sent_date = timezone.now()
        invoice.save()

        # Record transaction
        from typing import Any as _Any
        from typing import cast

        FinancialTransactionService.record_transaction(
            transaction_type=cast("_Any", FinancialTransaction.TransactionType).INVOICE_SENT,
            student=invoice.student,
            amount=invoice.total_amount,
            currency=invoice.currency,
            description=f"Invoice {invoice.invoice_number} sent to student",
            invoice=invoice,
            processed_by=sent_by,
        )

        return invoice

    @staticmethod
    @transaction.atomic
    def create_invoice_for_enrollment(
        enrollment,
        created_by,
    ) -> Invoice:
        """Create an invoice for a single enrollment.

        Args:
            enrollment: ClassHeaderEnrollment instance
            created_by: User creating the invoice

        Returns:
            Created Invoice instance

        Raises:
            FinancialError: If invoice creation fails
        """
        student = enrollment.student
        term = enrollment.class_header.term

        # Check if invoice already exists for this term
        existing_invoice = Invoice.objects.filter(
            student=student,
            term=term,
            status__in=[
                Invoice.InvoiceStatus.DRAFT,
                Invoice.InvoiceStatus.SENT,
                Invoice.InvoiceStatus.PARTIALLY_PAID,
            ],
        ).first()

        if existing_invoice:
            # Add enrollment to existing invoice
            return InvoiceService.add_enrollment_to_invoice(
                invoice=existing_invoice,
                enrollment=enrollment,
                updated_by=created_by,
            )

        # Create new invoice for this enrollment
        return InvoiceService.create_invoice(
            student=student,
            term=term,
            enrollments=[enrollment],
            notes=f"Auto-generated invoice for enrollment in {enrollment.class_header.course}",
            created_by=created_by,
        )

    @staticmethod
    @transaction.atomic
    def add_enrollment_to_invoice(
        invoice: Invoice,
        enrollment,
        updated_by,
    ) -> Invoice:
        """Add an enrollment to an existing invoice.

        Args:
            invoice: Existing Invoice instance
            enrollment: ClassHeaderEnrollment to add
            updated_by: User making the update

        Returns:
            Updated Invoice instance
        """
        # Import here to avoid circular dependency
        from .transaction_service import FinancialTransactionService

        course = enrollment.class_header.course

        # Get course pricing
        try:
            pricing_service = SeparatedPricingService()
            price, currency, _pricing_details = cast("Any", pricing_service).get_course_price(
                course=course,
                student=invoice.student,
                term=invoice.term,
            )
        except FinancialError as e:
            msg = f"Failed to get pricing for {course}: {e}"
            raise FinancialError(msg) from e

        # Create line item for course
        try:
            line_item = InvoiceLineItem.objects.create(
                invoice=invoice,
                line_item_type=InvoiceLineItem.LineItemType.COURSE,
                description=f"Course: {course.code} - {course.title}",
                unit_price=price,
                quantity=Decimal("1.00"),
                line_total=price,
                enrollment=enrollment,
            )
        except IntegrityError as e:
            msg = f"Course line item creation failed due to integrity constraint: {e}"
            raise FinancialError(msg) from e
        except ValidationError as e:
            msg = f"Course line item creation failed due to validation error: {e}"
            raise FinancialError(msg) from e

        # Update invoice totals (will be handled by signals)

        # Record transaction
        FinancialTransactionService.record_transaction(
            transaction_type=cast("Any", FinancialTransaction.TransactionType).INVOICE_MODIFIED,
            student=invoice.student,
            amount=price,
            currency=currency,
            description=f"Added {course} to invoice {invoice.invoice_number}",
            invoice=invoice,
            processed_by=updated_by,
            reference_data={
                "enrollment_id": enrollment.id,
                "course_code": course.code,
                "line_item_id": line_item.id,
            },
        )

        return invoice

    @staticmethod
    @transaction.atomic
    def apply_payment_to_invoice(payment, processed_by) -> Invoice:
        """Apply a payment to its associated invoice.

        Args:
            payment: Payment instance
            processed_by: User processing the payment

        Returns:
            Updated Invoice instance
        """
        invoice = payment.invoice

        # Update invoice paid amount (if not already done)
        if payment.status == Payment.PaymentStatus.COMPLETED:
            invoice.paid_amount += payment.amount
            invoice.save()

            # Update invoice status based on payment
            InvoiceService.update_invoice_payment_status(invoice)

        return invoice

    @staticmethod
    @transaction.atomic
    def update_invoice_payment_status(invoice):
        """Update invoice status based on payment status with atomic operations.

        Args:
            invoice: Invoice instance to update

        Returns:
            Updated Invoice instance
        """
        # Determine new status based on payment amount
        new_status = None
        if invoice.paid_amount >= invoice.total_amount:
            new_status = Invoice.InvoiceStatus.PAID
        elif invoice.paid_amount > 0:
            new_status = Invoice.InvoiceStatus.PARTIALLY_PAID
        elif invoice.is_overdue:
            new_status = Invoice.InvoiceStatus.OVERDUE

        # Use atomic update with version check for race condition protection
        if new_status and new_status != invoice.status:
            updated_rows = Invoice.objects.filter(id=invoice.id, version=invoice.version).update(
                status=new_status,
                version=F("version") + 1,
            )

            if updated_rows == 0:
                # Another transaction modified the invoice, refresh and retry once
                invoice.refresh_from_db()
                if invoice.paid_amount >= invoice.total_amount:
                    new_status = Invoice.InvoiceStatus.PAID
                elif invoice.paid_amount > 0:
                    new_status = Invoice.InvoiceStatus.PARTIALLY_PAID
                elif invoice.is_overdue:
                    new_status = Invoice.InvoiceStatus.OVERDUE

                if new_status and new_status != invoice.status:
                    Invoice.objects.filter(id=invoice.id).update(status=new_status, version=F("version") + 1)

            # Update local instance status to reflect change
            invoice.status = new_status
            invoice.refresh_from_db(fields=["version"])

        return invoice
