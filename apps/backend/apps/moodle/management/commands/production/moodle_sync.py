"""Management command for Moodle synchronization operations."""

from django.core.management.base import BaseCommand, CommandError

from apps.moodle.services import MoodleAPIClient, MoodleCourseService
from apps.moodle.tasks import bulk_sync_users_to_moodle


class Command(BaseCommand):
    """Management command for Moodle synchronization."""

    help = "Perform various Moodle synchronization operations"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "operation",
            choices=["test", "sync-users", "sync-courses", "health-check"],
            help="Synchronization operation to perform",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=50,
            help="Batch size for bulk operations",
        )

    def handle(self, *args, **options):
        """Handle the command execution."""
        operation = options["operation"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        try:
            if operation == "test":
                self.test_connection()
            elif operation == "sync-users":
                self.sync_users(dry_run, options["batch_size"])
            elif operation == "sync-courses":
                self.sync_courses(dry_run)
            elif operation == "health-check":
                self.health_check()
        except Exception as e:
            raise CommandError(f"Operation failed: {e}") from e

    def test_connection(self):
        """Test connection to Moodle API."""
        self.stdout.write("Testing Moodle API connection...")

        try:
            client = MoodleAPIClient()
            if client.test_connection():
                self.stdout.write(self.style.SUCCESS("✓ Moodle API connection successful"))
            else:
                self.stdout.write(self.style.ERROR("✗ Moodle API connection failed"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Connection test error: {e}"))

    def sync_users(self, dry_run: bool, batch_size: int):
        """Sync users to Moodle."""
        from apps.people.models import Person

        self.stdout.write("Starting user synchronization...")

        # Get users that need syncing
        users_to_sync = Person.objects.filter(
            # Add filters for users that need syncing
            # moodle_mapping__isnull=True
        )

        total_users = users_to_sync.count()
        self.stdout.write(f"Found {total_users} users to sync")

        if dry_run:
            self.stdout.write("Would sync the following users:")
            for user in users_to_sync[:10]:  # Show first 10
                self.stdout.write(f"  - {user.first_name} {user.last_name} (ID: {user.id})")
            if total_users > 10:
                self.stdout.write(f"  ... and {total_users - 10} more")
            return

        if total_users == 0:
            self.stdout.write("No users need syncing")
            return

        # Trigger bulk sync
        bulk_sync_users_to_moodle.send()
        self.stdout.write(self.style.SUCCESS(f"✓ Bulk user sync triggered for {total_users} users"))

    def sync_courses(self, dry_run: bool):
        """Sync courses to Moodle."""
        from apps.curriculum.models import Course

        self.stdout.write("Starting course synchronization...")

        # Get courses that need syncing
        courses_to_sync = Course.objects.filter(
            # Add filters for courses that need syncing
            # moodle_mapping__isnull=True
        )

        total_courses = courses_to_sync.count()
        self.stdout.write(f"Found {total_courses} courses to sync")

        if dry_run:
            self.stdout.write("Would sync the following courses:")
            for course in courses_to_sync[:10]:  # Show first 10
                self.stdout.write(f"  - {course.code}: {course.title} (ID: {course.id})")
            if total_courses > 10:
                self.stdout.write(f"  ... and {total_courses - 10} more")
            return

        if total_courses == 0:
            self.stdout.write("No courses need syncing")
            return

        # Sync courses individually for now
        service = MoodleCourseService()
        success_count = 0
        error_count = 0

        for course in courses_to_sync:
            try:
                if service.sync_course_to_moodle(course):
                    success_count += 1
                    self.stdout.write(f"✓ Synced course: {course.code}")
                else:
                    error_count += 1
                    self.stdout.write(f"✗ Failed to sync course: {course.code}")
            except Exception as e:
                error_count += 1
                self.stdout.write(f"✗ Error syncing course {course.code}: {e}")

        self.stdout.write(
            self.style.SUCCESS(f"Course sync complete: {success_count} successful, {error_count} errors"),
        )

    def health_check(self):
        """Perform comprehensive health check."""
        self.stdout.write("Performing Moodle integration health check...")

        # Test API connection
        self.test_connection()

        # Check sync status summary
        from django.db.models import Count

        from apps.moodle.models import MoodleSyncStatus

        status_counts = MoodleSyncStatus.objects.values("sync_status").annotate(count=Count("id"))

        self.stdout.write("\nSync Status Summary:")
        for status in status_counts:
            self.stdout.write(f"  {status['sync_status']}: {status['count']}")

        # Check recent API errors
        from datetime import datetime, timedelta

        from apps.moodle.models import MoodleAPILog

        recent_errors = MoodleAPILog.objects.filter(
            created_at__gte=datetime.now() - timedelta(hours=24),
            status_code__gte=400,
        ).count()

        if recent_errors > 0:
            self.stdout.write(self.style.WARNING(f"⚠ {recent_errors} API errors in last 24 hours"))
        else:
            self.stdout.write(self.style.SUCCESS("✓ No API errors in last 24 hours"))

        self.stdout.write("\nHealth check complete.")
