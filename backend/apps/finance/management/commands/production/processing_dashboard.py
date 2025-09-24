"""Real-time processing dashboard for enterprise-scale A/R reconstruction monitoring."""

import time
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db.models import Avg, Count, Sum
from django.utils import timezone

from apps.finance.models.ar_reconstruction import (
    ARReconstructionBatch,
    LegacyReceiptMapping,
)


class Command(BaseCommand):
    """Real-time dashboard for monitoring enterprise-scale processing."""

    help = "Live monitoring dashboard for A/R reconstruction processing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh-interval",
            type=int,
            default=30,
            help="Dashboard refresh interval in seconds (default: 30)",
        )

        parser.add_argument("--batch-id", type=str, help="Monitor specific batch ID")

        parser.add_argument(
            "--one-shot",
            action="store_true",
            help="Show current status and exit (no live monitoring)",
        )

    def handle(self, *args, **options):
        """Execute real-time processing dashboard."""
        self.refresh_interval = options["refresh_interval"]
        self.batch_id = options.get("batch_id")
        self.one_shot = options["one_shot"]

        if self.one_shot:
            self.display_current_status()
        else:
            self.run_live_dashboard()

    def run_live_dashboard(self):
        """Run live monitoring dashboard with real-time updates."""
        self.stdout.write("🖥️  Enterprise Processing Dashboard")
        self.stdout.write("   Press Ctrl+C to exit")
        self.stdout.write(f"   Refresh interval: {self.refresh_interval} seconds")
        self.stdout.write("=" * 80)

        try:
            while True:
                # Clear screen (works on most terminals)
                self.stdout.write("\033[2J\033[H")

                self.display_header()
                self.display_current_status()
                self.display_batch_details()
                self.display_error_analysis()
                self.display_financial_summary()

                time.sleep(self.refresh_interval)

        except KeyboardInterrupt:
            self.stdout.write("\n👋 Dashboard monitoring stopped")

    def display_header(self):
        """Display dashboard header with timestamp."""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.stdout.write("🖥️  ENTERPRISE A/R RECONSTRUCTION DASHBOARD")
        self.stdout.write(f"   Last Updated: {current_time}")
        self.stdout.write("=" * 80)

    def display_current_status(self):
        """Display current processing status overview."""
        # Get active batches
        active_batches = ARReconstructionBatch.objects.filter(
            status__in=[
                ARReconstructionBatch.BatchStatus.PROCESSING,
                ARReconstructionBatch.BatchStatus.PENDING,
            ]
        )

        # Get recent batches (last 24 hours)
        recent_batches = ARReconstructionBatch.objects.filter(created_at__gte=timezone.now() - timedelta(hours=24))

        # Overall statistics
        total_mappings = LegacyReceiptMapping.objects.count()
        validated_mappings = LegacyReceiptMapping.objects.filter(validation_status="VALIDATED").count()

        self.stdout.write("\n📊 SYSTEM STATUS")
        self.stdout.write(f"   Active Batches: {active_batches.count()}")
        self.stdout.write(f"   Recent Batches (24h): {recent_batches.count()}")
        self.stdout.write(f"   Total Reconstructions: {total_mappings:,}")
        self.stdout.write(f"   Validated Records: {validated_mappings:,}")

        if total_mappings > 0:
            validation_rate = (validated_mappings / total_mappings) * 100
            self.stdout.write(f"   Validation Rate: {validation_rate:.1f}%")

    def display_batch_details(self):
        """Display detailed batch processing information."""
        if self.batch_id:
            batches = ARReconstructionBatch.objects.filter(batch_id=self.batch_id)
        else:
            # Show recent batches
            batches = ARReconstructionBatch.objects.order_by("-created_at")[:5]

        if not batches.exists():
            self.stdout.write("\n📦 BATCH STATUS: No active batches found")
            return

        self.stdout.write("\n📦 BATCH PROCESSING STATUS")
        self.stdout.write("   " + "-" * 76)
        self.stdout.write(f"   {'Batch ID':<20} {'Status':<12} {'Progress':<15} {'Success Rate':<12} {'Speed':<10}")
        self.stdout.write("   " + "-" * 76)

        for batch in batches:
            # Calculate progress
            if batch.total_receipts > 0:
                progress = (batch.processed_receipts / batch.total_receipts) * 100
                progress_str = f"{batch.processed_receipts:,}/{batch.total_receipts:,} ({progress:.1f}%)"
            else:
                progress_str = "0/0 (0%)"

            # Calculate success rate
            if batch.processed_receipts > 0:
                success_rate = (batch.successful_reconstructions / batch.processed_receipts) * 100
                success_str = f"{success_rate:.1f}%"
            else:
                success_str = "N/A"

            # Calculate processing speed
            if batch.started_at and batch.processed_receipts > 0:
                elapsed = (timezone.now() - batch.started_at).total_seconds()
                speed = (batch.processed_receipts / elapsed) * 60  # records per minute
                speed_str = f"{speed:.0f}/min"
            else:
                speed_str = "N/A"

            # Status emoji
            status_emoji = {
                "PENDING": "⏳",
                "PROCESSING": "🔄",
                "COMPLETED": "✅",
                "FAILED": "❌",
                "PAUSED": "⏸️",
                "CANCELLED": "🚫",
            }.get(batch.status, "❓")

            status_display = f"{status_emoji} {batch.get_status_display()}"

            self.stdout.write(
                f"   {batch.batch_id:<20} {status_display:<18} {progress_str:<15} {success_str:<12} {speed_str:<10}"
            )

        # Show ETA for active batches
        active_batch = batches.filter(status=ARReconstructionBatch.BatchStatus.PROCESSING).first()

        if active_batch:
            eta = self.calculate_eta(active_batch)
            if eta:
                self.stdout.write(f"\n   🕐 Estimated Completion: {eta.strftime('%H:%M:%S')}")

    def display_error_analysis(self):
        """Display error analysis and common issues."""
        # Get recent mappings with issues
        problem_mappings = LegacyReceiptMapping.objects.filter(
            validation_status__in=["PENDING", "REJECTED"],
            processing_date__gte=timezone.now() - timedelta(hours=24),
        )

        if not problem_mappings.exists():
            return

        # Analyze variance patterns
        high_variance = problem_mappings.filter(variance_amount__gt=Decimal("10.00")).count()

        self.stdout.write("\n⚠️  ERROR ANALYSIS (Last 24 Hours)")
        self.stdout.write(f"   Pending Review: {problem_mappings.count():,}")
        self.stdout.write(f"   High Variance (>$10): {high_variance:,}")

        # Show sample problematic records
        sample_problems = problem_mappings.order_by("-variance_amount")[:3]
        if sample_problems:
            self.stdout.write("   Top Variance Issues:")
            for mapping in sample_problems:
                self.stdout.write(
                    f"     Receipt {mapping.legacy_receipt_number}: "
                    f"${mapping.variance_amount} variance "
                    f"(Student {mapping.legacy_student_id})"
                )

    def display_financial_summary(self):
        """Display financial reconciliation summary."""
        # Get financial totals
        mappings = LegacyReceiptMapping.objects.all()

        if not mappings.exists():
            return

        financial_stats = mappings.aggregate(
            total_legacy=Sum("legacy_net_amount"),
            total_reconstructed=Sum("reconstructed_total"),
            total_variance=Sum("variance_amount"),
            avg_variance=Avg("variance_amount"),
            count=Count("id"),
        )

        legacy_total = financial_stats["total_legacy"] or Decimal("0")
        reconstructed_total = financial_stats["total_reconstructed"] or Decimal("0")
        total_variance = financial_stats["total_variance"] or Decimal("0")
        avg_variance = financial_stats["avg_variance"] or Decimal("0")
        count = financial_stats["count"]

        # Calculate variance percentage
        if legacy_total > 0:
            variance_pct = (total_variance / legacy_total) * 100
        else:
            variance_pct = 0

        self.stdout.write("\n💰 FINANCIAL RECONCILIATION")
        self.stdout.write(f"   Records Processed: {count:,}")
        self.stdout.write(f"   Legacy Amount: ${legacy_total:,.2f}")
        self.stdout.write(f"   Reconstructed Amount: ${reconstructed_total:,.2f}")
        self.stdout.write(f"   Total Variance: ${total_variance:,.2f} ({variance_pct:.2f}%)")
        self.stdout.write(f"   Average Variance: ${avg_variance:.2f}")

        # Variance quality assessment
        if variance_pct < 0.1:
            quality_status = "🟢 EXCELLENT"
        elif variance_pct < 0.5:
            quality_status = "🟡 GOOD"
        elif variance_pct < 2.0:
            quality_status = "🟠 ACCEPTABLE"
        else:
            quality_status = "🔴 NEEDS REVIEW"

        self.stdout.write(f"   Reconciliation Quality: {quality_status}")

    def calculate_eta(self, batch: ARReconstructionBatch) -> datetime:
        """Calculate estimated time of arrival for batch completion."""
        if not batch.started_at or batch.processed_receipts == 0:
            return None

        elapsed = (timezone.now() - batch.started_at).total_seconds()
        records_per_second = batch.processed_receipts / elapsed

        remaining_records = batch.total_receipts - batch.processed_receipts
        if remaining_records <= 0:
            return None

        eta_seconds = remaining_records / records_per_second
        return datetime.now() + timedelta(seconds=eta_seconds)
