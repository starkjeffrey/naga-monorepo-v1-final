"""Django management command to import scholarship records from receipt data.

This command processes legacy receipt CSV data and creates Scholarship model records
with proper validation, duplicate prevention, and comprehensive reporting.
Designed to support financial reconciliation and receipt balancing.
"""

import csv
from pathlib import Path

from apps.common.management.base_migration import BaseMigrationCommand
from apps.scholarships.services.import_service import ScholarshipImportService


class Command(BaseMigrationCommand):
    """Import scholarship records from receipt CSV data."""

    help = "Import scholarship records from receipt CSV data with validation and reporting"

    def get_rejection_categories(self):
        """Return rejection categories for failed imports."""
        return {
            "STUDENT_NOT_FOUND": "Student record not found in current system",
            "CYCLE_UNDETERMINED": "Cannot determine appropriate academic cycle",
            "INVALID_AMOUNT": "Scholarship amount calculation failed",
            "DUPLICATE_SCHOLARSHIP": "Scholarship record already exists",
            "VALIDATION_ERROR": "Data validation failed",
            "PROCESSING_ERROR": "Unexpected error during processing",
            "CRITICAL": "Critical system error during import",
        }

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument("csv_file", type=str, help="Path to receipt CSV file containing scholarship data")

        parser.add_argument(
            "--batch-id", type=str, help="Custom batch identifier for tracking (auto-generated if not provided)"
        )

        parser.add_argument(
            "--dry-run", action="store_true", help="Validate data without creating scholarship records"
        )

        parser.add_argument("--report-file", type=str, help="Path to save detailed import report (optional)")

    def execute_migration(self, *args, **options):
        """Execute the scholarship import migration."""
        csv_file = options["csv_file"]
        batch_id = options.get("batch_id")
        dry_run = options["dry_run"]
        report_file = options.get("report_file")

        # Validate input file
        csv_path = Path(csv_file)
        if not csv_path.is_absolute():
            csv_path = Path(__file__).parent.parent.parent.parent.parent / csv_file

        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        self.stdout.write(f"Importing scholarships from: {csv_path}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No records will be created"))

        # Initialize import service
        import_service = ScholarshipImportService()

        try:
            # Execute import
            result = import_service.import_scholarships_from_receipts(
                str(csv_path), batch_id=batch_id, dry_run=dry_run
            )

            # Display summary
            self._display_import_summary(result, dry_run)

            # Generate detailed report if requested
            if report_file:
                self._generate_detailed_report(result, report_file, dry_run)

            # Return result for audit trail as string
            return (
                f"Import completed: {result.successful_imports} successful, "
                f"{result.failed_imports} failed, {result.skipped_records} skipped"
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Import failed: {e!s}"))
            raise

    def _display_import_summary(self, result, dry_run: bool):
        """Display import summary to stdout."""

        mode_text = "VALIDATION" if dry_run else "IMPORT"

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(f"SCHOLARSHIP {mode_text} SUMMARY")
        self.stdout.write("=" * 60)

        # Success metrics
        if dry_run:
            self.stdout.write(f"Records validated: {result.successful_imports}")
        else:
            self.stdout.write(f"Scholarships created: {result.successful_imports}")

        self.stdout.write(f"Failed records: {result.failed_imports}")
        self.stdout.write(f"Skipped records: {result.skipped_records}")

        # Error breakdown
        if result.errors:
            self.stdout.write("\nError breakdown:")
            error_categories = self._categorize_errors(result.errors)
            for category, count in error_categories.items():
                self.stdout.write(f"  {category}: {count}")

        # Warnings
        if result.warnings:
            self.stdout.write(f"\nWarnings: {len(result.warnings)}")

        # Success rate
        total_processed = result.successful_imports + result.failed_imports
        if total_processed > 0:
            success_rate = (result.successful_imports / total_processed) * 100
            self.stdout.write(f"\nSuccess rate: {success_rate:.1f}%")

        # Sample errors (first 5)
        if result.errors:
            self.stdout.write("\nSample errors:")
            for error in result.errors[:5]:
                self.stdout.write(f"  Receipt {error['receipt_number']}: {error['error_message'][:80]}...")
            if len(result.errors) > 5:
                self.stdout.write(f"  ... and {len(result.errors) - 5} more errors")

        # Success message
        if result.successful_imports > 0:
            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✅ Validation completed: {result.successful_imports} records would be imported"
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✅ Import completed: {result.successful_imports} scholarship records created"
                    )
                )
        elif result.failed_imports > 0:
            self.stdout.write(
                self.style.ERROR(f"\n❌ {mode_text.lower()} failed: {result.failed_imports} errors occurred")
            )
        else:
            self.stdout.write(self.style.WARNING("\n⚠️ No scholarship records found in input data"))

    def _categorize_errors(self, errors: list) -> dict:
        """Categorize errors by type for summary reporting."""
        categories = {}
        for error in errors:
            category = error.get("error_category", "UNKNOWN")
            categories[category] = categories.get(category, 0) + 1
        return categories

    def _generate_detailed_report(self, result, report_file: str, dry_run: bool):
        """Generate detailed CSV report of import results."""

        report_path = Path(report_file)
        if not report_path.is_absolute():
            report_path = Path(__file__).parent.parent.parent.parent.parent / report_file

        # Ensure directory exists
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)

            # Write header
            writer.writerow(
                [
                    "Status",
                    "Receipt_Number",
                    "Student_ID",
                    "Scholarship_Name",
                    "Award_Amount",
                    "Award_Percentage",
                    "Error_Category",
                    "Error_Message",
                ]
            )

            # Write successful imports
            for scholarship in result.created_scholarships:
                if scholarship:  # Skip None entries from dry run
                    writer.writerow(
                        [
                            "SUCCESS",
                            "N/A",  # Receipt number not stored in scholarship
                            scholarship.student.id,
                            scholarship.name,
                            scholarship.award_amount or "",
                            scholarship.award_percentage or "",
                            "",
                            "",
                        ]
                    )

            # Write errors
            for error in result.errors:
                writer.writerow(
                    [
                        "ERROR",
                        error["receipt_number"],
                        error["student_id"],
                        "",
                        "",
                        "",
                        error["error_category"],
                        error["error_message"],
                    ]
                )

            # Write warnings
            for warning in result.warnings:
                writer.writerow(
                    [
                        "WARNING",
                        warning["receipt_number"],
                        warning["student_id"],
                        "",
                        "",
                        "",
                        "WARNING",
                        warning["warning_message"],
                    ]
                )

        self.stdout.write(f"📄 Detailed report saved to: {report_path}")
