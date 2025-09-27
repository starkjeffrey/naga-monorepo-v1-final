"""Management command to run the reconciliation process.

This is the main entry point for running payment reconciliation using
the price determination engine.
"""

import csv
import logging
from datetime import date, datetime
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.finance.models import (
    Payment,
    ReconciliationBatch,
    ReconciliationStatus,
)
from apps.finance.services.enhanced_reconciliation_service import (
    EnhancedReconciliationService,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Run reconciliation process for payments."""

    help = "Run reconciliation process to match payments with enrollments"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = EnhancedReconciliationService()
        self.stats = {
            "total_payments": 0,
            "fully_reconciled": 0,
            "auto_allocated": 0,
            "pending_review": 0,
            "unmatched": 0,
            "errors": 0,
            "total_variance": Decimal("0"),
        }

    def add_arguments(self, parser):
        """Add command arguments."""

        # Date range options
        parser.add_argument(
            "--start-date",
            type=str,
            help="Start date (YYYY-MM-DD) for payments to reconcile",
        )
        parser.add_argument(
            "--end-date",
            type=str,
            help="End date (YYYY-MM-DD) for payments to reconcile",
        )
        parser.add_argument("--term", type=str, help="Term code to reconcile (e.g., FALL2023)")
        parser.add_argument("--year", type=int, help="Year to reconcile payments for")

        # Processing options
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of payments to process in each batch (default: 100)",
        )
        parser.add_argument(
            "--payment-ids",
            nargs="+",
            type=int,
            help="Specific payment IDs to reconcile",
        )
        parser.add_argument("--student-id", type=str, help="Reconcile payments for a specific student")

        # Mode options
        parser.add_argument("--dry-run", action="store_true", help="Run without saving results")
        parser.add_argument(
            "--reprocess",
            action="store_true",
            help="Reprocess already reconciled payments",
        )
        parser.add_argument(
            "--only-unmatched",
            action="store_true",
            help="Only process unmatched payments",
        )

        # Output options
        parser.add_argument("--export-csv", type=str, help="Export results to CSV file")
        parser.add_argument("--verbose", action="store_true", help="Show detailed progress")

    def handle(self, *args, **options):
        """Main command handler."""

        try:
            # Parse options
            self.dry_run = options["dry_run"]
            self.verbose = options["verbose"]
            self.reprocess = options["reprocess"]

            if self.dry_run:
                self.stdout.write(self.style.WARNING("Running in DRY-RUN mode - no changes will be saved"))

            # Create reconciliation batch
            batch = self._create_batch(options)

            # Get payments to process
            payments = self._get_payments_queryset(options)

            if not payments.exists():
                self.stdout.write(self.style.WARNING("No payments found matching criteria"))
                return

            total_count = payments.count()
            self.stdout.write(f"Found {total_count:,} payments to process")

            # Process payments in batches
            batch_size = options["batch_size"]

            with transaction.atomic():
                for i in range(0, total_count, batch_size):
                    batch_payments = payments[i : i + batch_size]
                    self._process_batch(batch_payments, batch)

                    # Show progress
                    processed = min(i + batch_size, total_count)
                    self.stdout.write(f"Processed {processed:,}/{total_count:,} payments...")

                # Update batch statistics
                self._update_batch_stats(batch)

                if self.dry_run:
                    transaction.set_rollback(True)
                    self.stdout.write(self.style.WARNING("DRY RUN - Rolling back all changes"))

            # Export results if requested
            if options["export_csv"]:
                self._export_results(options["export_csv"], batch)

            # Print summary
            self._print_summary()

        except Exception as e:
            logger.error(f"Error in reconciliation process: {e}")
            raise CommandError(f"Reconciliation failed: {e}") from e

    def _create_batch(self, options) -> ReconciliationBatch:
        """Create a reconciliation batch."""

        # Determine date range
        if options["start_date"]:
            start_date = datetime.strptime(options["start_date"], "%Y-%m-%d").date()
        else:
            start_date = date(2000, 1, 1)  # Default to early date

        if options["end_date"]:
            end_date = datetime.strptime(options["end_date"], "%Y-%m-%d").date()
        else:
            end_date = date.today()

        # Create batch ID
        batch_id = f"RECON-{timezone.now().strftime('%Y%m%d-%H%M%S')}"

        if self.dry_run:
            batch_id += "-DRYRUN"

        batch = ReconciliationBatch.objects.create(
            batch_id=batch_id,
            batch_type=ReconciliationBatch.BatchType.MANUAL,
            start_date=start_date,
            end_date=end_date,
            status=ReconciliationBatch.BatchStatus.PROCESSING,
            started_at=timezone.now(),
            parameters={"options": options, "command": "run_reconciliation"},
        )

        return batch

    def _get_payments_queryset(self, options):
        """Build queryset for payments to process."""

        queryset = Payment.objects.all()

        # Filter by date range
        if options["start_date"]:
            start_date = datetime.strptime(options["start_date"], "%Y-%m-%d").date()
            queryset = queryset.filter(payment_date__gte=start_date)

        if options["end_date"]:
            end_date = datetime.strptime(options["end_date"], "%Y-%m-%d").date()
            queryset = queryset.filter(payment_date__lte=end_date)

        # Filter by year
        if options["year"]:
            queryset = queryset.filter(payment_date__year=options["year"])

        # Filter by term
        if options["term"]:
            queryset = queryset.filter(invoice__term__code=options["term"])

        # Filter by student
        if options["student_id"]:
            queryset = queryset.filter(invoice__student__student_id=options["student_id"])

        # Filter by specific payment IDs
        if options["payment_ids"]:
            queryset = queryset.filter(id__in=options["payment_ids"])

        # Filter by reconciliation status
        if options["only_unmatched"]:
            queryset = queryset.filter(
                Q(reconciliation_status__isnull=True)
                | Q(reconciliation_status__status=ReconciliationStatus.Status.UNMATCHED)
            )
        elif not self.reprocess:
            # Exclude already reconciled unless reprocessing
            queryset = queryset.exclude(reconciliation_status__status=ReconciliationStatus.Status.FULLY_RECONCILED)

        # Order by date for consistent processing
        return queryset.order_by("payment_date", "id")

    def _process_batch(self, payments, batch: ReconciliationBatch):
        """Process a batch of payments."""

        for payment in payments:
            try:
                if self.verbose:
                    self.stdout.write(
                        f"Processing payment {payment.payment_reference} "
                        f"for {payment.invoice.student} - ${payment.amount}"
                    )

                # Run reconciliation
                status = self.service.reconcile_payment(payment, batch)

                # Update statistics
                self.stats["total_payments"] += 1

                if status.status == ReconciliationStatus.Status.FULLY_RECONCILED:
                    self.stats["fully_reconciled"] += 1
                elif status.status == ReconciliationStatus.Status.AUTO_ALLOCATED:
                    self.stats["auto_allocated"] += 1
                elif status.status == ReconciliationStatus.Status.PENDING_REVIEW:
                    self.stats["pending_review"] += 1
                elif status.status == ReconciliationStatus.Status.UNMATCHED:
                    self.stats["unmatched"] += 1
                elif status.status == ReconciliationStatus.Status.EXCEPTION_ERROR:
                    self.stats["errors"] += 1

                self.stats["total_variance"] += abs(status.variance_amount)

                if self.verbose and status.variance_amount > 0:
                    self.stdout.write(
                        f"  → {status.get_status_display()} "
                        f"(Confidence: {status.confidence_score}%, "
                        f"Variance: ${status.variance_amount})"
                    )

            except Exception as e:
                logger.error(f"Error processing payment {payment.id}: {e}")
                self.stats["errors"] += 1

                if self.verbose:
                    self.stdout.write(self.style.ERROR(f"  → ERROR: {e!s}"))

    def _update_batch_stats(self, batch: ReconciliationBatch):
        """Update batch with final statistics."""

        batch.total_payments = self.stats["total_payments"]
        batch.processed_payments = self.stats["total_payments"]
        batch.successful_matches = self.stats["fully_reconciled"] + self.stats["auto_allocated"]
        batch.failed_matches = self.stats["unmatched"] + self.stats["errors"]
        batch.completed_at = timezone.now()
        batch.status = ReconciliationBatch.BatchStatus.COMPLETED

        batch.results_summary = {
            "fully_reconciled": self.stats["fully_reconciled"],
            "auto_allocated": self.stats["auto_allocated"],
            "pending_review": self.stats["pending_review"],
            "unmatched": self.stats["unmatched"],
            "errors": self.stats["errors"],
            "total_variance": str(self.stats["total_variance"]),
            "average_variance": str(
                self.stats["total_variance"] / self.stats["total_payments"] if self.stats["total_payments"] > 0 else 0
            ),
        }

        batch.save()

    def _export_results(self, filename: str, batch: ReconciliationBatch):
        """Export reconciliation results to CSV."""

        self.stdout.write(f"Exporting results to {filename}...")

        with open(filename, "w", newline="") as csvfile:
            fieldnames = [
                "payment_id",
                "payment_reference",
                "payment_date",
                "amount",
                "student_id",
                "student_name",
                "term",
                "status",
                "confidence",
                "variance_amount",
                "variance_percentage",
                "pricing_method",
                "matched_courses",
                "notes",
            ]

            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            # Get all reconciliation statuses for this batch
            statuses = (
                ReconciliationStatus.objects.filter(reconciliation_batch=batch)
                .select_related("payment__invoice__student", "payment__invoice__term")
                .prefetch_related("matched_enrollments")
            )

            for status in statuses:
                payment = status.payment
                student = payment.invoice.student

                # Get matched course list
                matched_courses = ", ".join(
                    [enrollment.class_header.course.code for enrollment in status.matched_enrollments.all()]
                )

                writer.writerow(
                    {
                        "payment_id": payment.id,
                        "payment_reference": payment.payment_reference,
                        "payment_date": payment.payment_date,
                        "amount": payment.amount,
                        "student_id": student.student_id,
                        "student_name": str(student),
                        "term": payment.invoice.term.code,
                        "status": status.get_status_display(),
                        "confidence": status.confidence_score,
                        "variance_amount": status.variance_amount,
                        "variance_percentage": status.variance_percentage,
                        "pricing_method": (
                            status.get_pricing_method_applied_display() if status.pricing_method_applied else ""
                        ),
                        "matched_courses": matched_courses,
                        "notes": status.notes,
                    }
                )

        self.stdout.write(self.style.SUCCESS(f"Results exported to {filename}"))

    def _print_summary(self):
        """Print reconciliation summary."""

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("RECONCILIATION SUMMARY")
        self.stdout.write("=" * 60)

        total = self.stats["total_payments"]

        if total > 0:
            self.stdout.write(f"Total Payments Processed: {total:,}")
            self.stdout.write("")

            # Status breakdown
            self.stdout.write("Status Breakdown:")
            self.stdout.write(
                f"  - Fully Reconciled: {self.stats['fully_reconciled']:,} "
                f"({self.stats['fully_reconciled'] / total * 100:.1f}%)"
            )
            self.stdout.write(
                f"  - Auto-Allocated: {self.stats['auto_allocated']:,} "
                f"({self.stats['auto_allocated'] / total * 100:.1f}%)"
            )
            self.stdout.write(
                f"  - Pending Review: {self.stats['pending_review']:,} "
                f"({self.stats['pending_review'] / total * 100:.1f}%)"
            )
            self.stdout.write(
                f"  - Unmatched: {self.stats['unmatched']:,} ({self.stats['unmatched'] / total * 100:.1f}%)"
            )
            self.stdout.write(f"  - Errors: {self.stats['errors']:,} ({self.stats['errors'] / total * 100:.1f}%)")

            self.stdout.write("")
            self.stdout.write(f"Total Variance: ${self.stats['total_variance']:,.2f}")
            self.stdout.write(f"Average Variance: ${self.stats['total_variance'] / total:,.2f}")

            # Success rate
            successful = self.stats["fully_reconciled"] + self.stats["auto_allocated"]
            success_rate = successful / total * 100
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(f"Overall Success Rate: {success_rate:.1f}%"))
        else:
            self.stdout.write("No payments were processed")

        self.stdout.write("=" * 60)

        if self.dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN MODE - No data was saved"))
