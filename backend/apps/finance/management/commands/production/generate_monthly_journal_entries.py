"""Management command to generate monthly journal entries for G/L integration.

This command can be scheduled to run monthly (e.g., via cron) to automatically
create journal entries for the previous month's financial transactions.

Usage:
    # Generate for specific month
    python manage.py generate_monthly_journal_entries --year 2025 --month 1

    # Generate for previous month (default)
    python manage.py generate_monthly_journal_entries

    # Export to file
    python manage.py generate_monthly_journal_entries --export --format csv

    # Dry run (preview without creating)
    python manage.py generate_monthly_journal_entries --dry-run
"""

import logging
from datetime import UTC, datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import models, transaction
from django.utils import timezone

from apps.finance.gl_integration_service import GLIntegrationService
from apps.finance.models import GLBatch, Payment

# Constants
MIN_MONTH = 1
MAX_MONTH = 12
DECEMBER = 12

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Generate monthly journal entries for General Ledger integration"

    def add_arguments(self, parser):
        """Add command arguments."""
        # Date parameters
        parser.add_argument(
            "--year",
            type=int,
            help="Year to process (default: previous month)",
        )
        parser.add_argument(
            "--month",
            type=int,
            help="Month to process 1-12 (default: previous month)",
        )

        # Processing options
        parser.add_argument(
            "--batch-number",
            type=str,
            help="Custom batch number (auto-generated if not provided)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview without creating entries",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force regeneration even if entries exist",
        )

        # Export options
        parser.add_argument(
            "--export",
            action="store_true",
            help="Export entries to file after generation",
        )
        parser.add_argument(
            "--format",
            type=str,
            choices=["csv", "xml", "json"],
            default="csv",
            help="Export format (default: csv)",
        )
        parser.add_argument(
            "--email",
            type=str,
            help="Email address to send export file",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        try:
            # Determine period to process
            year, month = self._get_processing_period(options)

            self.stdout.write(self.style.SUCCESS(f"Processing journal entries for {year}-{month:02d}"))

            # Check if entries already exist
            if self._check_existing_entries(year, month) and not options["force"]:
                self.stdout.write(
                    self.style.WARNING("Journal entries already exist for this period. Use --force to regenerate."),
                )
                return

            # Preview mode
            if options["dry_run"]:
                self._preview_entries(year, month)
                return

            # Generate entries
            service = GLIntegrationService()

            # Get system user for automated processing
            from apps.enrollment.services import get_system_user

            user = get_system_user()

            with transaction.atomic():
                batch = service.generate_monthly_journal_entries(
                    year=year,
                    month=month,
                    user=user,
                    batch_number=options.get("batch_number"),
                )

                self.stdout.write(
                    self.style.SUCCESS(
                        f"Generated {batch.total_entries} journal entries in batch {batch.batch_number}",
                    ),
                )

                # Export if requested
                if options["export"]:
                    export_path = service.export_batch_to_file(
                        batch=batch,
                        format=options["format"],
                        user=user,
                    )

                    self.stdout.write(self.style.SUCCESS(f"Exported to: {export_path}"))

                    # Email if requested
                    if options.get("email"):
                        self._send_export_email(batch, export_path, options["email"])

        except Exception as e:
            logger.exception("Error generating journal entries")
            msg = f"Failed to generate journal entries: {e}"
            raise CommandError(msg) from e

    def _get_processing_period(self, options):
        """Determine which period to process."""
        if options.get("year") and options.get("month"):
            # Explicit period specified
            year = options["year"]
            month = options["month"]

            if month < MIN_MONTH or month > MAX_MONTH:
                msg = f"Month must be between {MIN_MONTH} and {MAX_MONTH}"
                raise CommandError(msg)

            # Don't process future periods
            today = timezone.now().date()
            if year > today.year or (year == today.year and month > today.month):
                msg = "Cannot process future periods"
                raise CommandError(msg)

        else:
            # Default to previous month
            today = timezone.now().date()
            first_of_month = today.replace(day=1)
            last_month = first_of_month - timedelta(days=1)
            year = last_month.year
            month = last_month.month

        return year, month

    def _check_existing_entries(self, year: int, month: int) -> bool:
        """Check if entries already exist for the period."""
        accounting_period = f"{year:04d}-{month:02d}"

        return GLBatch.objects.filter(accounting_period=accounting_period).exists()

    def _preview_entries(self, year: int, month: int):
        """Preview what would be generated without creating entries."""
        # Get payment summary
        start_date = datetime(year, month, 1, tzinfo=UTC).date()
        end_date = (
            datetime(year + 1, 1, 1, tzinfo=UTC).date()
            if month == DECEMBER
            else datetime(year, month + 1, 1, tzinfo=UTC).date()
        )

        payments = Payment.objects.filter(
            payment_date__gte=start_date,
            payment_date__lt=end_date,
            status=Payment.PaymentStatus.COMPLETED,
        )

        # Summarize by payment method
        summary = (
            payments.values("payment_method")
            .annotate(
                count=models.Count("id"),
                total=models.Sum("amount"),
            )
            .order_by("payment_method")
        )

        self.stdout.write("\nPayment Summary:")
        self.stdout.write("-" * 50)

        total_amount = 0
        total_count = 0

        for item in summary:
            self.stdout.write(f"{item['payment_method']:20} {item['count']:6,d} payments  ${item['total']:12,.2f}")
            total_amount += item["total"] or 0
            total_count += item["count"] or 0

        self.stdout.write("-" * 50)
        self.stdout.write(f"{'TOTAL':20} {total_count:6,d} payments  ${total_amount:12,.2f}")

        # Show sample journal entry structure
        self.stdout.write("\n\nSample Journal Entry Structure:")
        self.stdout.write("-" * 50)
        self.stdout.write("Dr  1010 Cash on Hand           $X,XXX.XX")
        self.stdout.write("    Cr  4000 Tuition Revenue            $X,XXX.XX")
        self.stdout.write("    Cr  4100 Fee Revenue                $XXX.XX")
        self.stdout.write("\n(Following service accounting - revenue recognized on receipt)")

    def _send_export_email(self, batch: GLBatch, export_path: str, email: str):
        """Send export file via email."""
        import os

        from django.conf import settings
        from django.core.mail import EmailMessage

        subject = f"G/L Journal Entries - Batch {batch.batch_number}"
        body = f"""
        G/L journal entries have been generated and exported.

        Batch Number: {batch.batch_number}
        Accounting Period: {batch.accounting_period}
        Total Entries: {batch.total_entries}
        Total Amount: ${batch.total_amount:,.2f}

        The export file is attached to this email.
        """

        email_message = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[email],
        )

        # Attach the export file
        with open(export_path, "rb") as f:
            email_message.attach(
                os.path.basename(export_path),
                f.read(),
                ("text/csv" if export_path.endswith(".csv") else "application/octet-stream"),
            )

        email_message.send()

        self.stdout.write(self.style.SUCCESS(f"Export file sent to {email}"))
