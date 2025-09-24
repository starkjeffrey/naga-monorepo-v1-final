"""Management command to run payment reconciliation in batches.

This command processes payments through the reconciliation engine,
matching them with enrollments and generating audit trails for
legacy data migration.
"""

import logging
from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.finance.models import (
    MaterialityThreshold,
    Payment,
    ReconciliationBatch,
    ReconciliationStatus,
)
from apps.finance.services.reconciliation_service import (
    ReconciliationMonitor,
    ReconciliationService,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Run payment reconciliation in batches."""

    help = "Process payments through reconciliation engine in configurable batches"

    def add_arguments(self, parser):
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of payments to process in each batch (default: 100)",
        )

        parser.add_argument(
            "--start-date",
            type=str,
            help="Start date for payment processing (YYYY-MM-DD format)",
        )

        parser.add_argument(
            "--end-date",
            type=str,
            help="End date for payment processing (YYYY-MM-DD format)",
        )

        parser.add_argument(
            "--batch-type",
            choices=["INITIAL", "REFINEMENT", "MANUAL", "SCHEDULED"],
            default="SCHEDULED",
            help="Type of reconciliation batch to run",
        )

        parser.add_argument(
            "--status-filter",
            choices=["UNMATCHED", "PENDING_REVIEW", "EXCEPTION_ERROR"],
            help="Only process payments with specific reconciliation status",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be processed without making changes",
        )

        parser.add_argument(
            "--force",
            action="store_true",
            help="Process already reconciled payments (for refinement)",
        )

        parser.add_argument(
            "--create-thresholds",
            action="store_true",
            help="Create default materiality thresholds if they don't exist",
        )

        parser.add_argument(
            "--monitor",
            action="store_true",
            help="Show reconciliation dashboard metrics after processing",
        )

    def handle(self, *args, **options):
        """Execute the reconciliation batch processing."""

        # Parse options
        batch_size = options["batch_size"]
        start_date = self._parse_date(options.get("start_date"))
        end_date = self._parse_date(options.get("end_date"))
        batch_type = options["batch_type"]
        status_filter = options.get("status_filter")
        dry_run = options["dry_run"]
        force = options["force"]
        create_thresholds = options["create_thresholds"]
        monitor = options["monitor"]

        self.stdout.write(self.style.SUCCESS("🚀 Starting Reconciliation Batch Processing"))

        # Create materiality thresholds if requested
        if create_thresholds:
            self._create_default_thresholds()

        # Build payment queryset
        payments_qs = self._build_payment_queryset(start_date, end_date, status_filter, force)

        total_payments = payments_qs.count()

        if total_payments == 0:
            self.stdout.write(self.style.WARNING("❌ No payments found matching criteria"))
            return

        self.stdout.write(f"📊 Found {total_payments} payments to process")

        if dry_run:
            self._show_dry_run_summary(payments_qs, batch_size)
            return

        # Create batch record
        batch = self._create_batch_record(start_date, end_date, batch_type, total_payments)

        # Process payments
        try:
            self._process_payments_in_batches(payments_qs, batch, batch_size)
        except Exception as e:
            batch.status = ReconciliationBatch.BatchStatus.FAILED
            batch.error_log = str(e)
            batch.save()
            raise CommandError(f"Batch processing failed: {e}") from e

        # Finalize batch
        self._finalize_batch(batch)

        # Show results
        self._show_results(batch)

        # Show monitoring dashboard if requested
        if monitor:
            self._show_dashboard_metrics()

    def _parse_date(self, date_str: str | None) -> date | None:
        """Parse date string into date object."""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError as err:
            raise CommandError(f"Invalid date format: {date_str}. Use YYYY-MM-DD") from err

    def _create_default_thresholds(self):
        """Create default materiality thresholds."""
        defaults = [
            {
                "context": MaterialityThreshold.ThresholdContext.INDIVIDUAL_PAYMENT,
                "absolute_threshold": 50.00,
                "notes": "Individual payment variance threshold",
            },
            {
                "context": MaterialityThreshold.ThresholdContext.STUDENT_ACCOUNT,
                "absolute_threshold": 500.00,
                "notes": "Student account total variance threshold",
            },
            {
                "context": MaterialityThreshold.ThresholdContext.BATCH_TOTAL,
                "absolute_threshold": 5000.00,
                "notes": "Batch total variance threshold",
            },
            {
                "context": MaterialityThreshold.ThresholdContext.ERROR_CATEGORY,
                "absolute_threshold": 10000.00,
                "notes": "Error category aggregate threshold",
            },
        ]

        created_count = 0
        for threshold_data in defaults:
            threshold, created = MaterialityThreshold.objects.get_or_create(
                context=threshold_data["context"],
                defaults={
                    "absolute_threshold": threshold_data["absolute_threshold"],
                    "notes": threshold_data["notes"],
                    "effective_date": timezone.now().date(),
                },
            )
            if created:
                created_count += 1
                self.stdout.write(f"✅ Created threshold: {threshold}")

        if created_count:
            self.stdout.write(self.style.SUCCESS(f"📋 Created {created_count} materiality thresholds"))

    def _build_payment_queryset(
        self,
        start_date: date | None,
        end_date: date | None,
        status_filter: str | None,
        force: bool,
    ):
        """Build queryset for payments to process."""
        qs = Payment.objects.select_related("invoice__student__person", "invoice__term").prefetch_related(
            "reconciliation_status"
        )

        # Date filtering
        if start_date:
            qs = qs.filter(payment_date__date__gte=start_date)
        if end_date:
            qs = qs.filter(payment_date__date__lte=end_date)

        # Status filtering
        if status_filter:
            qs = qs.filter(reconciliation_status__status=status_filter)
        elif not force:
            # Exclude already fully reconciled payments unless forced
            qs = qs.exclude(reconciliation_status__status=ReconciliationStatus.Status.FULLY_RECONCILED)

        return qs.order_by("payment_date", "id")

    def _show_dry_run_summary(self, payments_qs, batch_size):
        """Show what would be processed in dry run mode."""
        total = payments_qs.count()
        batches = (total + batch_size - 1) // batch_size

        self.stdout.write(self.style.SUCCESS("🧪 DRY RUN MODE - No changes will be made"))
        self.stdout.write(f"📊 Would process {total} payments in {batches} batches")

        # Show sample payments
        sample_payments = payments_qs[:5]
        self.stdout.write("\n📋 Sample payments to process:")
        for payment in sample_payments:
            status = getattr(payment, "reconciliation_status", None)
            status_display = status.get_status_display() if status else "No Status"
            self.stdout.write(
                f"  • {payment.payment_reference} - {payment.invoice.student} - ${payment.amount} - {status_display}"
            )

        if total > 5:
            self.stdout.write(f"  ... and {total - 5} more")

    def _create_batch_record(
        self,
        start_date: date | None,
        end_date: date | None,
        batch_type: str,
        total_payments: int,
    ) -> ReconciliationBatch:
        """Create batch tracking record."""

        # Generate batch ID
        today = timezone.now().date()
        batch_id = f"RECON-{today.strftime('%Y%m%d')}-{timezone.now().strftime('%H%M%S')}"

        batch = ReconciliationBatch.objects.create(
            batch_id=batch_id,
            batch_type=batch_type,
            start_date=start_date or date(2018, 1, 1),  # Default to early date
            end_date=end_date or today,
            status=ReconciliationBatch.BatchStatus.PROCESSING,
            total_payments=total_payments,
            started_at=timezone.now(),
            parameters={
                "command_args": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "batch_type": batch_type,
                }
            },
        )

        self.stdout.write(f"📝 Created batch: {batch.batch_id}")
        return batch

    def _process_payments_in_batches(self, payments_qs, batch: ReconciliationBatch, batch_size: int):
        """Process payments in configurable batches."""

        service = ReconciliationService()
        processed_count = 0
        successful_count = 0
        failed_count = 0

        # Process in batches
        for offset in range(0, batch.total_payments, batch_size):
            batch_payments = payments_qs[offset : offset + batch_size]

            self.stdout.write(f"🔄 Processing batch {offset // batch_size + 1} ({len(batch_payments)} payments)...")

            with transaction.atomic():
                for payment in batch_payments:
                    try:
                        status = service.reconcile_payment(payment, batch)
                        processed_count += 1

                        if status.status in [
                            ReconciliationStatus.Status.FULLY_RECONCILED,
                            ReconciliationStatus.Status.AUTO_ALLOCATED,
                        ]:
                            successful_count += 1
                        else:
                            failed_count += 1

                        # Log progress every 10 payments
                        if processed_count % 10 == 0:
                            self.stdout.write(f"  📊 Processed {processed_count} payments...")

                    except Exception as e:
                        failed_count += 1
                        logger.error(f"Error processing payment {payment.payment_reference}: {e}")

            # Update batch statistics
            batch.processed_payments = processed_count
            batch.successful_matches = successful_count
            batch.failed_matches = failed_count
            batch.save()

    def _finalize_batch(self, batch: ReconciliationBatch):
        """Finalize batch processing."""
        batch.status = ReconciliationBatch.BatchStatus.COMPLETED
        batch.completed_at = timezone.now()

        # Generate results summary
        batch.results_summary = {
            "total_processed": batch.processed_payments,
            "successful_matches": batch.successful_matches,
            "failed_matches": batch.failed_matches,
            "success_rate": float(batch.success_rate),
            "processing_time_minutes": ((batch.completed_at - batch.started_at).total_seconds() / 60),
        }

        batch.save()

    def _show_results(self, batch: ReconciliationBatch):
        """Display batch processing results."""
        self.stdout.write(self.style.SUCCESS("\n🎉 Batch Processing Complete!"))
        self.stdout.write(f"📝 Batch ID: {batch.batch_id}")
        self.stdout.write(f"⏱️  Processing Time: {batch.results_summary['processing_time_minutes']:.1f} minutes")
        self.stdout.write(f"📊 Total Processed: {batch.processed_payments}")
        self.stdout.write(f"✅ Successful Matches: {batch.successful_matches}")
        self.stdout.write(f"❌ Failed Matches: {batch.failed_matches}")
        self.stdout.write(f"📈 Success Rate: {batch.success_rate:.1f}%")

        # Color code success rate
        if batch.success_rate >= 95:
            rate_style = self.style.SUCCESS
        elif batch.success_rate >= 80:
            rate_style = self.style.WARNING
        else:
            rate_style = self.style.ERROR

        self.stdout.write(rate_style(f"🎯 Final Success Rate: {batch.success_rate:.1f}%"))

    def _show_dashboard_metrics(self):
        """Show reconciliation dashboard metrics."""
        monitor = ReconciliationMonitor()
        metrics = monitor.get_dashboard_metrics()

        self.stdout.write(self.style.SUCCESS("\n📊 Reconciliation Dashboard"))
        self.stdout.write("─" * 50)

        daily_stats = metrics["daily_stats"]
        self.stdout.write(f"📅 Payments Received Today: {daily_stats['payments_received']}")
        self.stdout.write(f"🤖 Auto-Reconciled Rate: {daily_stats['auto_reconciled']:.1f}%")
        self.stdout.write(f"👥 Pending Review: {daily_stats['pending_review']}")
        self.stdout.write(f"⚠️  Error Rate: {daily_stats['error_rate']:.1f}%")

        if metrics["alerts"]:
            self.stdout.write("\n🚨 Active Alerts:")
            for alert in metrics["alerts"]:
                self.stdout.write(f"  • {alert['type']}: {alert['message']}")
