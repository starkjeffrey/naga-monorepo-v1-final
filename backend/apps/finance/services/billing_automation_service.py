"""Billing automation service for automated billing based on enrollment events.

Handles automatic invoice generation when students enroll
in courses, with configurable timing and rules.
"""

from datetime import timedelta

from django.db import transaction

from apps.common.utils import get_current_date
from apps.finance.models import Invoice

from .invoice_service import InvoiceService
from .separated_pricing_service import FinancialError


class BillingAutomationService:
    """Service for automated billing based on enrollment events.

    Handles automatic invoice generation when students enroll
    in courses, with configurable timing and rules.
    """

    @staticmethod
    @transaction.atomic
    def create_enrollment_invoice(
        student,
        term,
        enrollments: list,
        created_by=None,
    ) -> Invoice | None:
        """Create an invoice for new enrollments.

        Args:
            student: StudentProfile instance
            term: Term instance
            enrollments: List of new enrollments
            created_by: User triggering the billing

        Returns:
            Created Invoice instance or None if no billing needed
        """
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
            # Add enrollments to existing invoice
            for enrollment in enrollments:
                try:
                    InvoiceService.add_enrollment_to_invoice(
                        invoice=existing_invoice,
                        enrollment=enrollment,
                        updated_by=created_by,
                    )
                except FinancialError:
                    # Log error but continue with other enrollments
                    pass
            return existing_invoice

        # Create new invoice
        try:
            return InvoiceService.create_invoice(
                student=student,
                term=term,
                enrollments=enrollments,
                notes="Auto-generated invoice for course enrollments",
                created_by=created_by,
            )
        except FinancialError:
            # Log error but don't fail enrollment
            return None

    @staticmethod
    def process_overdue_invoices(days_overdue: int = 7) -> list[Invoice]:
        """Process overdue invoices and update their status.

        Args:
            days_overdue: Minimum days overdue to process

        Returns:
            List of processed overdue invoices
        """
        cutoff_date = get_current_date() - timedelta(days=days_overdue)

        overdue_invoices = Invoice.objects.filter(
            status=Invoice.InvoiceStatus.SENT,
            due_date__lt=cutoff_date,
        )

        processed = []
        for invoice in overdue_invoices:
            invoice.status = Invoice.InvoiceStatus.OVERDUE
            invoice.save()
            processed.append(invoice)

        return processed
