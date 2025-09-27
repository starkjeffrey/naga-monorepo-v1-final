"""Import script for deduced major declarations from legacy data.

This script imports major declarations from backend/data/migrate/deduced_major.csv
into the MajorDeclaration model, following clean architecture principles.

Input CSV format:
- StudentID: Legacy student identifier (5-digit format)
- DeducedMajor: Major code (BUSADMIN, IR, TESOL, FIN, TOU)
- LastTermDate: Date of last enrollment in that major (YYYY-MM-DD)

Business Logic:
- Creates MajorDeclaration records with effective_date = LastTermDate
- Maps legacy student IDs to StudentProfile instances
- Maps legacy major codes to Major instances
- Handles rejection categorization for failed imports
- Generates comprehensive audit reports
"""

import csv
import time
from datetime import datetime
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Major
from apps.enrollment.models import MajorDeclaration
from apps.people.models import StudentProfile


class Command(BaseMigrationCommand):
    """Import deduced major declarations from CSV file."""

    help = "Import major declarations from deduced_major.csv"

    # Major code mapping from legacy codes to official Major model codes
    MAJOR_CODE_MAPPING = {
        "BUSADMIN": "BUSADMIN",
        "IR": "IR",
        "TESOL": "TESOL",
        "FIN": "FIN-BANK",  # Finance maps to official FIN-BANK code
        "TOU": "TOUR-HOSP",  # Tourism maps to official TOUR-HOSP code
    }

    def get_rejection_categories(self) -> list[str]:
        """Return list of possible rejection categories for this migration."""
        return [
            "student_not_found",
            "major_not_found",
            "invalid_date_format",
            "duplicate_declaration",
            "validation_error",
            "database_error",
        ]

    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            "--file",
            type=str,
            default="data/migrate/deduced_major.csv",
            help="Path to the CSV file (default: data/migrate/deduced_major.csv)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Perform a dry run without saving data",
        )

    def execute_migration(self, *args, **options):
        """Execute the migration with comprehensive tracking."""
        csv_file = Path(options["file"])
        dry_run = options.get("dry_run", False)

        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")

        # Update audit tracking with migration-specific info
        self.audit_data["migration_info"].update(
            {
                "source_file": str(csv_file),
                "dry_run": dry_run,
            },
        )

        total_processed = 0
        successful_imports = 0

        with open(csv_file, encoding="utf-8") as file:
            reader = csv.DictReader(file)

            # Validate CSV headers
            required_headers = {"StudentID", "DeducedMajor", "LastTermDate"}
            if not required_headers.issubset(reader.fieldnames):
                missing = required_headers - set(reader.fieldnames)
                raise ValueError(f"Missing required CSV headers: {missing}")

            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):  # start=2 for CSV line numbers
                    total_processed += 1

                    success = self._process_row(row, row_num, dry_run)
                    if success:
                        successful_imports += 1

                    # Progress reporting
                    if total_processed % 100 == 0:
                        self.stdout.write(f"Processed {total_processed} rows, {successful_imports} successful imports")

                if dry_run:
                    # Rollback transaction for dry run
                    transaction.set_rollback(True)

        # Update audit summary
        self.audit_data["summary"]["input"]["total_rows"] = total_processed
        self.audit_data["summary"]["output"]["successful_imports"] = successful_imports
        self.audit_data["summary"]["rejected"]["total_rejected"] = total_processed - successful_imports

        # Calculate performance metrics
        self._calculate_performance_metrics(total_processed, successful_imports)

        # Generate samples
        self._generate_samples()

        # Output summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\nMigration completed!\n"
                f"Total processed: {total_processed}\n"
                f"Successful imports: {successful_imports}\n"
                f"Rejected: {total_processed - successful_imports}\n"
                f"Dry run: {dry_run}",
            ),
        )

    def _process_row(self, row: dict, row_num: int, dry_run: bool) -> bool:
        """Process a single CSV row."""
        try:
            # Extract and validate data
            student_id = row["StudentID"].strip()
            major_code = row["DeducedMajor"].strip()
            last_term_date_str = row["LastTermDate"].strip()

            # Validate student ID format (5 digits)
            if not student_id.isdigit() or len(student_id) != 5:
                self._record_rejection(
                    "validation_error",
                    row_num,
                    f"Invalid student ID format: {student_id}",
                    row,
                )
                return False

            # Parse date
            try:
                last_term_date = datetime.strptime(last_term_date_str, "%Y-%m-%d").date()
            except ValueError:
                self._record_rejection(
                    "invalid_date_format",
                    row_num,
                    f"Invalid date format: {last_term_date_str}",
                    row,
                )
                return False

            # Look up student
            try:
                student = StudentProfile.objects.get(student_id=student_id)
            except StudentProfile.DoesNotExist:
                self._record_rejection(
                    "student_not_found",
                    row_num,
                    f"Student not found: {student_id}",
                    row,
                )
                return False

            # Look up major
            mapped_major_code = self.MAJOR_CODE_MAPPING.get(major_code)
            if not mapped_major_code:
                self._record_rejection(
                    "major_not_found",
                    row_num,
                    f"Unknown major code: {major_code}",
                    row,
                )
                return False

            try:
                major = Major.objects.get(code=mapped_major_code)
            except Major.DoesNotExist:
                self._record_rejection(
                    "major_not_found",
                    row_num,
                    f"Major not found in database: {mapped_major_code}",
                    row,
                )
                return False

            # Check for existing declaration on same date
            existing = MajorDeclaration.objects.filter(
                student=student,
                effective_date=last_term_date,
                is_active=True,
            ).exists()

            if existing:
                self._record_rejection(
                    "duplicate_declaration",
                    row_num,
                    f"Declaration already exists for {student_id} on {last_term_date}",
                    row,
                )
                return False

            # Create MajorDeclaration
            if not dry_run:
                # Set declared_date to the same as effective_date to pass validation
                # This represents historical data where exact declaration date is unknown
                declared_datetime = timezone.make_aware(datetime.combine(last_term_date, datetime.min.time()))

                declaration = MajorDeclaration.objects.create(
                    student=student,
                    major=major,
                    effective_date=last_term_date,
                    declared_date=declared_datetime,
                    is_active=True,
                    is_self_declared=False,  # This is migrated data, not self-declared
                    notes=(
                        f"Imported from legacy data migration. Original major code: {major_code}. "
                        "Declaration date set to effective date as historical data."
                    ),
                )

                # Validate the created object
                try:
                    declaration.full_clean()
                except Exception as e:
                    self._record_rejection(
                        "validation_error",
                        row_num,
                        f"Model validation failed: {e!s}",
                        row,
                    )
                    return False

            return True

        except Exception as e:
            self._record_rejection(
                "database_error",
                row_num,
                f"Unexpected error: {e!s}",
                row,
            )
            return False

    def _record_rejection(self, category: str, row_num: int, reason: str, row_data: dict):
        """Record a rejected row with categorization."""
        if category not in self.detailed_rejections:
            self.detailed_rejections[category] = []

        self.detailed_rejections[category].append(
            {
                "row_number": row_num,
                "reason": reason,
                "data": row_data,
            },
        )

        # Update summary counts
        if category not in self.audit_data["summary"]["rejected"]["rejection_breakdown"]:
            self.audit_data["summary"]["rejected"]["rejection_breakdown"][category] = 0
        self.audit_data["summary"]["rejected"]["rejection_breakdown"][category] += 1

    def _calculate_performance_metrics(self, total_processed: int, successful_imports: int):
        """Calculate performance metrics for audit report."""
        duration = time.time() - self.migration_start_time

        self.audit_data["performance_metrics"] = {
            "total_duration_seconds": round(duration, 2),
            "rows_per_second": (round(total_processed / duration, 2) if duration > 0 else 0),
            "success_rate_percentage": (
                round((successful_imports / total_processed * 100), 2) if total_processed > 0 else 0
            ),
            "memory_usage_estimate": "N/A",  # Could be implemented if needed
        }

    def _generate_samples(self):
        """Generate sample data for audit report."""
        # Sample successful imports
        sample_declarations = MajorDeclaration.objects.filter(
            notes__contains="Imported from legacy data migration",
        ).order_by("-created_at")[:5]

        self.audit_data["samples"]["successful_imports"] = [
            {
                "student_id": decl.student.student_id,
                "major_code": decl.major.code,
                "effective_date": decl.effective_date.isoformat(),
                "notes": decl.notes,
            }
            for decl in sample_declarations
        ]

        # Sample rejections (first few from each category)
        sample_rejections = {}
        for category, rejections in self.detailed_rejections.items():
            sample_rejections[category] = rejections[:3]  # First 3 rejections per category

        self.audit_data["samples"]["rejected_samples"] = sample_rejections

        # Store detailed rejections for full audit
        self.audit_data["detailed_rejections"] = self.detailed_rejections

    def get_migration_description(self) -> str:
        """Return description of this migration."""
        return (
            "Import major declarations from deduced_major.csv into MajorDeclaration model. "
            "Maps legacy student IDs to StudentProfile and major codes to Major instances."
        )
