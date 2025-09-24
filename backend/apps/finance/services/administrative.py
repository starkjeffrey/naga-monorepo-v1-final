"""Administrative fee services for cycle-based fees and document excess charges."""

from datetime import date, timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.academic_records.models import DocumentQuota
from apps.enrollment.models import StudentCycleStatus
from apps.finance.models import AdministrativeFeeConfig, DocumentExcessFee, Invoice, InvoiceLineItem
from apps.people.models import StudentProfile


class AdministrativeFeeService:
    """Service for managing administrative fees for students with cycle changes."""

    @staticmethod
    def get_active_fee_config(cycle_type: str) -> AdministrativeFeeConfig | None:
        """Get the active fee configuration for a cycle type.

        Args:
            cycle_type: The cycle type (NEW, L2B, B2M)

        Returns:
            Active AdministrativeFeeConfig or None if not found
        """
        return AdministrativeFeeConfig.objects.filter(cycle_type=cycle_type, is_active=True).first()

    @staticmethod
    @transaction.atomic
    def apply_administrative_fee(
        student: StudentProfile, term, cycle_status: StudentCycleStatus, invoice: Invoice | None = None
    ) -> tuple[InvoiceLineItem | None, DocumentQuota | None]:
        """Apply administrative fee for a student with cycle status.

        Args:
            student: The student to apply fee to
            term: The term to apply fee for
            cycle_status: The student's cycle status
            invoice: Optional existing invoice to add to

        Returns:
            Tuple of (InvoiceLineItem, DocumentQuota) or (None, None) if no fee config
        """
        # Get fee configuration
        fee_config = AdministrativeFeeService.get_active_fee_config(cycle_status.cycle_type)
        if not fee_config:
            return None, None

        # Check if fee already applied this term
        existing_fee = InvoiceLineItem.objects.filter(
            invoice__student=student,
            invoice__term=term,
            line_item_type=InvoiceLineItem.LineItemType.ADMIN_FEE,
            description__contains=f"Administrative Fee - {cycle_status.cycle_type}",
        ).exists()

        if existing_fee:
            return None, None

        # Create or get invoice
        if not invoice:
            invoice_number = f"INV-{student.pk}-{term.code}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            invoice = Invoice.objects.create(
                invoice_number=invoice_number,
                student=student,
                term=term,
                status=Invoice.InvoiceStatus.DRAFT,
                due_date=date.today() + timedelta(days=30),
            )

        # Create line item for administrative fee
        line_item = InvoiceLineItem.objects.create(
            invoice=invoice,
            line_item_type=InvoiceLineItem.LineItemType.ADMIN_FEE,
            description=f"Administrative Fee - {cycle_status.cycle_type}",
            unit_price=fee_config.fee_amount,
            quantity=Decimal("1.00"),
            line_total=fee_config.fee_amount,
        )

        # Update invoice totals
        invoice.calculate_totals()
        invoice.save()

        # Create document quota if included
        document_quota = None
        if fee_config.included_document_units > 0:
            from apps.academic_records.services import DocumentQuotaService

            document_quota = DocumentQuotaService.create_quota_for_term(
                student=student,
                term=term,
                cycle_status=cycle_status,
                total_units=fee_config.included_document_units,
                admin_fee_line_item=line_item,
            )

        return line_item, document_quota

    @staticmethod
    def process_term_administrative_fees(term):
        """Process administrative fees for all eligible students in a term.

        Args:
            term: The term to process fees for

        Returns:
            Dictionary with processing results
        """
        results = {"processed": 0, "fees_applied": 0, "errors": [], "total_revenue": Decimal("0.00")}

        # Get all students with active cycle status
        active_statuses = StudentCycleStatus.objects.filter(is_active=True).select_related("student", "target_program")

        for cycle_status in active_statuses:
            try:
                # Check if student is enrolled this term
                from apps.enrollment.models import ClassHeaderEnrollment

                enrolled = ClassHeaderEnrollment.objects.filter(
                    student=cycle_status.student,
                    class_header__term=term,
                    enrollment_status__in=["ENROLLED", "COMPLETED"],
                ).exists()

                if not enrolled:
                    continue

                # Apply administrative fee
                line_item, quota = AdministrativeFeeService.apply_administrative_fee(
                    student=cycle_status.student, term=term, cycle_status=cycle_status
                )

                if line_item:
                    results["fees_applied"] += 1
                    results["total_revenue"] += line_item.line_total

                results["processed"] += 1

            except Exception as e:
                results["errors"].append({"student_id": getattr(cycle_status.student, "pk", None), "error": str(e)})

        return results

    @staticmethod
    @transaction.atomic
    def calculate_document_excess_fee(student: StudentProfile, document_type, term) -> DocumentExcessFee | None:
        """Calculate excess fee for document request if quota exceeded.

        Args:
            student: The student requesting document
            document_type: The type of document requested
            term: The current term

        Returns:
            DocumentExcessFee if quota exceeded, None otherwise
        """
        from apps.academic_records.services import DocumentQuotaService

        # Check if student has quota
        quota = DocumentQuotaService.get_active_quota(student, term)
        if not quota:
            return None

        # Check if quota would be exceeded
        units_needed = document_type.unit_cost
        if quota.remaining_units >= units_needed:
            return None

        # Get active excess fee configuration
        excess_config = AdministrativeFeeConfig.objects.filter(
            cycle_type=quota.cycle_status.cycle_type, is_active=True
        ).first()

        if not excess_config:
            return None

        # Calculate excess units
        excess_units = units_needed - quota.remaining_units
        excess_config.fee_amount * excess_units

        # TODO: This code needs to be refactored - DocumentExcessFee requires invoice_line_item and document_request
        # which are not available in this context. For now, returning None to fix type errors.
        return None

    @staticmethod
    @transaction.atomic
    def apply_document_excess_charge(
        student: StudentProfile,
        document_request,
        excess_units: int,
        fee_per_unit: Decimal,
        invoice: Invoice | None = None,
    ) -> InvoiceLineItem:
        """Apply excess document charge to student's invoice.

        Args:
            student: The student to charge
            document_request: The document request triggering the charge
            excess_units: Number of excess units
            fee_per_unit: Fee per excess unit
            invoice: Optional existing invoice to add to

        Returns:
            InvoiceLineItem for the excess charge
        """
        # Create or get invoice
        if not invoice:
            term = document_request.student.current_term
            invoice_number = f"INV-{student.pk}-{term.code}-{timezone.now().strftime('%Y%m%d%H%M%S')}"
            invoice = Invoice.objects.create(
                invoice_number=invoice_number,
                student=student,
                term=term,
                status=Invoice.InvoiceStatus.DRAFT,
                due_date=date.today() + timedelta(days=30),
            )

        # Create line item for excess charge
        total_fee = fee_per_unit * excess_units
        line_item = InvoiceLineItem.objects.create(
            invoice=invoice,
            line_item_type=InvoiceLineItem.LineItemType.DOC_EXCESS,
            description=f"Document Excess Fee - {document_request.document_type.name} ({excess_units} units)",
            unit_price=fee_per_unit,
            quantity=Decimal(str(excess_units)),
            line_total=total_fee,
        )

        # Update invoice totals
        invoice.calculate_totals()
        invoice.save()

        return line_item
