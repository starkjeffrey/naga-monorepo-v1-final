"""Load major declarations from CSV file replacing existing data.

This script replaces all major declaration records with data from the CSV file.
The CSV contains legacy student IDs (zero-padded) and major codes that need
to be mapped to current database records.

Usage:
    python manage.py load_major_declarations data/migrate/major_declaration.csv
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Major
from apps.enrollment.models import MajorDeclaration
from apps.people.models import StudentProfile


class Command(BaseMigrationCommand):
    """Load major declarations from CSV, replacing existing data."""

    help = "Load major declarations from CSV file, replacing all existing records"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            help="Path to CSV file containing major declarations",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be processed without making changes",
        )

    def get_rejection_categories(self) -> list[str]:
        """Return possible rejection categories for this migration."""
        return [
            "student_not_found",
            "major_not_found",
            "invalid_date_format",
            "missing_required_data",
            "database_error",
        ]

    def execute_migration(self, *args, **options) -> Any:
        """Execute the major declarations migration."""
        csv_file = options["csv_file"]
        dry_run = options["dry_run"]

        if not Path(csv_file).exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")

        # Map major codes to database IDs
        major_mapping = self._build_major_mapping()
        self.stdout.write(f"✅ Built major mapping: {major_mapping}")

        # Process CSV file
        major_declarations = self._process_csv(csv_file, major_mapping)

        if dry_run:
            self.stdout.write(
                self.style.WARNING(f"🔍 DRY RUN: Would process {len(major_declarations)} major declarations")
            )
            return

        # Replace existing data
        with transaction.atomic():
            # Clear existing major declarations
            existing_count = MajorDeclaration.objects.count()
            MajorDeclaration.objects.all().delete()
            self.stdout.write(f"🗑️  Cleared {existing_count} existing major declarations")

            # Insert new declarations
            created_declarations = MajorDeclaration.objects.bulk_create(major_declarations, batch_size=1000)

            self.record_success("major_declarations_created", len(created_declarations))
            self.stdout.write(self.style.SUCCESS(f"✅ Created {len(created_declarations)} major declarations"))

        # Record performance metrics
        self.record_performance_metric("batch_size", 1000)
        self.record_data_integrity("post_migration_count", MajorDeclaration.objects.count())

        return (
            f"Successfully migrated {len(created_declarations)} major declarations "
            f"(deleted {existing_count} existing records)"
        )

    def _build_major_mapping(self) -> dict[str, int]:
        """Build mapping from CSV major codes to database major IDs."""
        major_mapping = {
            "BUS": "BUSADMIN",
            "FIN": "FIN-BANK",
            "IR": "IR",
            "TESOL": "TESOL",
            "TOU": "TOUR-HOSP",
        }

        # Get actual major IDs from database
        majors = Major.objects.filter(code__in=major_mapping.values())
        major_id_map = {major.code: major.id for major in majors}

        # Map CSV codes to database IDs
        final_mapping = {}
        for csv_code, db_code in major_mapping.items():
            if db_code in major_id_map:
                final_mapping[csv_code] = major_id_map[db_code]
            else:
                self.stdout.write(self.style.ERROR(f"❌ Major code not found in database: {db_code}"))

        return final_mapping

    def _process_csv(self, csv_file: str, major_mapping: dict[str, int]) -> list[MajorDeclaration]:
        """Process CSV file and return list of MajorDeclaration objects."""
        major_declarations = []

        with open(csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            total_rows = sum(1 for _ in reader)
            f.seek(0)
            reader = csv.DictReader(f)

            self.record_input_stats(csv_rows=total_rows)

            for row_num, row in enumerate(reader, 1):
                try:
                    declaration = self._process_row(row, major_mapping, row_num)
                    if declaration:
                        major_declarations.append(declaration)

                except Exception as e:
                    self.record_rejection(
                        "database_error",
                        f"row_{row_num}",
                        f"Error processing row: {e}",
                        error_details=str(e),
                        raw_data=row,
                    )

        return major_declarations

    def _process_row(self, row: dict, major_mapping: dict[str, int], row_num: int) -> MajorDeclaration | None:
        """Process a single CSV row and return MajorDeclaration object or None."""
        student_id_str = row["reStudentID"].strip()
        major_code = row["major"].strip()
        start_date_str = row["StartOfBA"].strip()

        # Validate required data
        if not all([student_id_str, major_code, start_date_str]):
            self.record_rejection(
                "missing_required_data",
                f"row_{row_num}",
                f"Missing required fields in row {row_num}",
                raw_data=row,
            )
            return None

        # Convert student ID to integer (remove leading zeros)
        try:
            student_id = int(student_id_str)
        except ValueError:
            self.record_rejection(
                "missing_required_data",
                f"row_{row_num}",
                f"Invalid student ID format: {student_id_str}",
                raw_data=row,
            )
            return None

        # Find student profile
        try:
            student_profile = StudentProfile.objects.select_related("person").get(student_id=student_id)
        except StudentProfile.DoesNotExist:
            self.record_rejection(
                "student_not_found",
                f"row_{row_num}",
                f"Student not found: {student_id}",
                raw_data=row,
            )
            return None

        # Get major ID
        if major_code not in major_mapping:
            self.record_rejection(
                "major_not_found",
                f"row_{row_num}",
                f"Major code not found: {major_code}",
                raw_data=row,
            )
            return None

        major_id = major_mapping[major_code]

        # Parse date
        try:
            # Parse datetime string: "2012-01-03 00:00:00.000"
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S.%f").date()
        except ValueError:
            try:
                # Try without microseconds: "2012-01-03 00:00:00"
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S").date()
            except ValueError:
                self.record_rejection(
                    "invalid_date_format",
                    f"row_{row_num}",
                    f"Invalid date format: {start_date_str}",
                    raw_data=row,
                )
                return None

        # Create MajorDeclaration object
        now = timezone.now()
        return MajorDeclaration(
            student_id=student_profile.id,
            major_id=major_id,
            effective_date=start_date,
            declared_date=now,
            is_active=True,
            is_self_declared=False,
            change_reason="Migrated from legacy system",
            supporting_documents="",
            requires_approval=False,
            approved_date=now,
            notes=f"Migrated from legacy student ID {student_id_str}",
            created_at=now,
            updated_at=now,
        )
