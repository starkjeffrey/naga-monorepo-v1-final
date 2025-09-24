"""Management command for Moodle cleanup operations."""

from datetime import datetime, timedelta

from django.core.management.base import BaseCommand

from apps.moodle.models import MoodleAPILog, MoodleSyncStatus


class Command(BaseCommand):
    """Management command for Moodle cleanup operations."""

    help = "Clean up old Moodle integration data"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--api-logs-days",
            type=int,
            default=30,
            help="Delete API logs older than this many days (default: 30)",
        )
        parser.add_argument(
            "--failed-syncs-days",
            type=int,
            default=90,
            help="Delete failed sync records older than this many days (default: 90)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting",
        )

    def handle(self, *args, **options):
        """Handle the command execution."""
        api_logs_days = options["api_logs_days"]
        failed_syncs_days = options["failed_syncs_days"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No data will be deleted"))

        # Clean up old API logs
        self.cleanup_api_logs(api_logs_days, dry_run)

        # Clean up old failed sync records
        self.cleanup_failed_syncs(failed_syncs_days, dry_run)

    def cleanup_api_logs(self, days: int, dry_run: bool):
        """Clean up old API logs."""
        cutoff_date = datetime.now() - timedelta(days=days)

        old_logs = MoodleAPILog.objects.filter(created_at__lt=cutoff_date)
        count = old_logs.count()

        if count == 0:
            self.stdout.write("No old API logs to clean up")
            return

        if dry_run:
            self.stdout.write(f"Would delete {count} API logs older than {days} days")
            return

        deleted_count, _ = old_logs.delete()
        self.stdout.write(self.style.SUCCESS(f"✓ Deleted {deleted_count} old API logs"))

    def cleanup_failed_syncs(self, days: int, dry_run: bool):
        """Clean up old failed sync records."""
        cutoff_date = datetime.now() - timedelta(days=days)

        failed_syncs = MoodleSyncStatus.objects.filter(sync_status="failed", updated_at__lt=cutoff_date)
        count = failed_syncs.count()

        if count == 0:
            self.stdout.write("No old failed sync records to clean up")
            return

        if dry_run:
            self.stdout.write(f"Would delete {count} failed sync records older than {days} days")
            return

        deleted_count, _ = failed_syncs.delete()
        self.stdout.write(self.style.SUCCESS(f"✓ Deleted {deleted_count} old failed sync records"))
