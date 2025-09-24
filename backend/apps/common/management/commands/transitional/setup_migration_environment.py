"""Management command to set up the migration environment."""

import logging

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand

logger = logging.getLogger("migration")


class Command(BaseCommand):
    """Set up the migration environment with both test and migration databases.

    This command:
    1. Migrates both databases
    2. Sets up test data in the default database
    3. Prepares migration database for legacy data
    """

    help = "Set up migration environment with both test and migration databases"

    def add_arguments(self, parser):
        parser.add_argument(
            "--skip-test-data",
            action="store_true",
            help="Skip generating test data in default database",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force setup even if databases exist",
        )

    def handle(self, *args, **options):
        """Execute the migration environment setup."""
        self.stdout.write(self.style.SUCCESS("🚀 Setting up migration environment..."))

        # Verify we're in migration settings
        if not hasattr(settings, "DATABASES") or "migration_data" not in settings.DATABASES:
            self.stdout.write(
                self.style.ERROR(
                    "❌ Migration environment not configured. Ensure DJANGO_SETTINGS_MODULE=config.settings.migration",
                ),
            )
            return

        try:
            # 1. Migrate default database (for test data)
            self.stdout.write("📊 Migrating default database...")
            call_command("migrate", database="default", verbosity=1)

            # 2. Migrate migration database (for legacy data)
            self.stdout.write("📊 Migrating migration database...")
            call_command("migrate", database="migration_data", verbosity=1)

            # 3. Set up test data in default database
            if not options["skip_test_data"]:
                self.stdout.write("🧪 Setting up test data in default database...")
                call_command("setup_test_data")

            # 4. Prepare migration database
            self.stdout.write("🔄 Preparing migration database...")
            self._prepare_migration_database()

            self.stdout.write(
                self.style.SUCCESS(
                    "✅ Migration environment ready!\n"
                    "   - Default DB: Test data with Faker\n"
                    "   - Migration DB: Ready for legacy data\n"
                    "   - Use manage.py migrate_legacy_data to import legacy data",
                ),
            )

        except Exception as e:
            logger.exception("Migration environment setup failed")
            self.stdout.write(self.style.ERROR(f"❌ Setup failed: {e}"))
            raise

    def _prepare_migration_database(self):
        """Prepare the migration database for legacy data import."""
        # This is where we could add any migration-specific setup
        # For now, just log that it's ready
        logger.info("Migration database prepared for legacy data import")
        self.stdout.write("   Migration database is ready for legacy data import")
