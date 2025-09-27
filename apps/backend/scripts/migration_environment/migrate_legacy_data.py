"""Management command to migrate legacy data to the migration database."""

import csv
import logging
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger("legacy_import")


class Command(BaseCommand):
    """Migrate legacy data from CSV files to the migration database.

    This command imports and transforms legacy data into the clean
    architecture while maintaining data integrity.
    """

    help = "Migrate legacy data from CSV files to migration database"

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-type",
            choices=["all", "students", "courses", "terms", "enrollments", "receipts"],
            default="all",
            help="Type of data to migrate (default: all)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be migrated without actually doing it",
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Clear existing migration data before importing",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Batch size for bulk operations (default: 1000)",
        )

    def handle(self, *args, **options):
        """Execute legacy data migration."""
        # Verify we're in migration settings
        if "migration_data" not in settings.DATABASES:
            self.stdout.write(
                self.style.ERROR(
                    "❌ Migration database not configured. Ensure DJANGO_SETTINGS_MODULE=config.settings.migration",
                ),
            )
            return

        self.stdout.write(self.style.SUCCESS("🔄 Starting legacy data migration..."))

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("📋 DRY RUN MODE - No data will be modified"))

        try:
            self._migrate_data(options)

            if not options["dry_run"]:
                self.stdout.write(self.style.SUCCESS("✅ Legacy data migration completed!"))
            else:
                self.stdout.write(self.style.SUCCESS("✅ Dry run completed - ready for actual migration"))

        except Exception as e:
            logger.exception("Legacy migration failed: %s", e)
            self.stdout.write(self.style.ERROR(f"❌ Migration failed: {e}"))
            raise

    def _migrate_data(self, options: dict[str, Any]):
        """Orchestrate the data migration process."""
        data_type = options["data_type"]

        if options["clear_existing"] and not options["dry_run"]:
            self._clear_migration_data()

        migration_order = ["students", "courses", "terms", "enrollments", "receipts"]

        if data_type == "all":
            for data_type_item in migration_order:
                self._migrate_specific_data(data_type_item, options)
        else:
            self._migrate_specific_data(data_type, options)

    def _clear_migration_data(self):
        """Clear existing migration data safely."""
        self.stdout.write("🧹 Clearing existing migration data...")

        # Import models (avoiding circular imports)
        from apps.curriculum.models import Course
        from apps.enrollment.models import ClassHeaderEnrollment
        from apps.finance.models import ReceiptHeader, ReceiptItem
        from apps.people.models import Person

        # Clear in dependency order using migration database
        ClassHeaderEnrollment.objects.using("migration_data").all().delete()
        ReceiptItem.objects.using("migration_data").all().delete()
        ReceiptHeader.objects.using("migration_data").all().delete()
        Course.objects.using("migration_data").all().delete()
        Person.objects.using("migration_data").filter(person_type="student").delete()

        self.stdout.write("   Migration data cleared")

    def _migrate_specific_data(self, data_type: str, options: dict[str, Any]):
        """Migrate specific type of legacy data."""
        migration_methods = {
            "students": self._migrate_students,
            "courses": self._migrate_courses,
            "terms": self._migrate_terms,
            "enrollments": self._migrate_enrollments,
            "receipts": self._migrate_receipts,
        }

        if data_type in migration_methods:
            self.stdout.write(f"📊 Migrating {data_type}...")
            migration_methods[data_type](options)
        else:
            self.stdout.write(self.style.WARNING(f"⚠️  Unknown data type: {data_type}"))

    def _migrate_students(self, options: dict[str, Any]):
        """Migrate student data from CSV."""
        csv_path = Path(settings.MIGRATION_DATA_PATH) / "all_students_20250612.csv"

        if not csv_path.exists():
            self.stdout.write(self.style.WARNING(f"⚠️  Student CSV not found: {csv_path}"))
            return

        students_created = 0
        batch_data = []

        with csv_path.open(encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                student_data = self._transform_student_data(row)
                if options["dry_run"]:
                    self.stdout.write(f"   Would create student: {student_data.get('name', 'Unknown')}")
                else:
                    batch_data.append(student_data)

                students_created += 1

                # Process in batches
                if len(batch_data) >= options["batch_size"]:
                    self._create_students_batch(batch_data)
                    batch_data = []

        # Process remaining batch
        if batch_data and not options["dry_run"]:
            self._create_students_batch(batch_data)

        self.stdout.write(f"   Processed {students_created} students")

    def _migrate_courses(self, options: dict[str, Any]):
        """Migrate course data - placeholder for now."""
        self.stdout.write("   Course migration not yet implemented")

    def _migrate_terms(self, options: dict[str, Any]):
        """Migrate term data - placeholder for now."""
        self.stdout.write("   Term migration not yet implemented")

    def _migrate_enrollments(self, options: dict[str, Any]):
        """Migrate enrollment data - placeholder for now."""
        self.stdout.write("   Enrollment migration not yet implemented")

    def _migrate_receipts(self, options: dict[str, Any]):
        """Migrate receipt data - placeholder for now."""
        self.stdout.write("   Receipt migration not yet implemented")

    def _transform_student_data(self, row: dict[str, str]) -> dict[str, Any]:
        """Transform legacy student data to new format."""
        # This is a placeholder - actual transformation depends on CSV structure
        return {
            "name": row.get("name", "").strip(),
            "email": row.get("email", "").strip(),
            "phone": row.get("phone", "").strip(),
            "person_type": "student",
            # Add more fields based on actual CSV structure
        }

    def _create_students_batch(self, student_data_list: list[dict[str, Any]]):
        """Create students in batch using migration database."""
        from apps.people.models import Person

        with transaction.atomic(using="migration_data"):
            students = []
            for data in student_data_list:
                students.append(Person(**data))

            Person.objects.using("migration_data").bulk_create(students, ignore_conflicts=True)
