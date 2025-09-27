"""Management command to import language course fixed pricing from CSV.

This command loads language course pricing data into the CourseFixedPricing model,
mapping course codes from the CSV to Course records in the LANG division.

Usage:
    python manage.py import_language_pricing [--dry-run] [--csv-file PATH]

Key Features:
- Maps CSV course codes to Course.code field for LANG division courses
- Handles multiple price versions with effective dates from the CSV
- Creates CourseFixedPricing records with proper date ranges
- Comprehensive audit reporting with rejection categorization
- Safe dry-run mode for validation before actual import
- Foreign student pricing assumed same as domestic (data limitation)

CSV Format Expected:
    Language_Course,Price_USD,Effective_Term,Effective_Date,End_date,
    EHSS-01,60,2009T1E,2009-04-27,2018-12-10,
    EHSS-01,70,2018T3E,2018-12-11,2024-01-08,
    EHSS-01,80,240109E-T1AE,2024-01-09,,
"""

import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import CommandError

from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Course, Division
from apps.finance.models import CourseFixedPricing


class Command(BaseMigrationCommand):
    """Import language course fixed pricing from CSV file."""

    help = "Import language course fixed pricing from CSV file"

    def add_arguments(self, parser):
        """Add command arguments."""
        super().add_arguments(parser)
        parser.add_argument(
            "--csv-file",
            type=str,
            default="data/migrate/language_price_list.csv",
            help="Path to CSV file (relative to backend directory)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without applying them",
        )

    def get_rejection_categories(self) -> dict[str, str]:
        """Return rejection categories for this import."""
        return {
            "missing_course": "Course code not found in LANG division",
            "invalid_price": "Invalid or negative price value",
            "invalid_date": "Invalid date format in CSV",
            "duplicate_record": "CourseFixedPricing already exists for course/date",
            "validation_error": "Database or validation error",
        }

    def execute_migration(self, **options):
        """Execute the migration logic."""
        csv_file_path = self._get_csv_file_path()

        # Validate file exists
        if not csv_file_path.exists():
            raise CommandError(f"CSV file not found: {csv_file_path}")

        # Start the import process
        self.stdout.write(self.style.SUCCESS(f"Starting language pricing import from: {csv_file_path}"))

        # Initialize tracking
        self._init_tracking()

        # Load and validate data
        pricing_data = self._load_csv_data(csv_file_path)
        self._validate_prerequisites()

        # Process the data
        for row_num, row_data in enumerate(pricing_data, start=2):  # Skip header
            self._process_pricing_row(row_num, row_data)

        return {
            "csv_file": str(csv_file_path),
            "lang_division_courses": len(self.course_cache),
            "missing_weekend_english": "Note: Weekend English classes mentioned as missing from source data",
        }

    def handle(self, *args, **options):
        """Main command handler."""
        self.options = options
        csv_file_path = self._get_csv_file_path()

        # Validate file exists
        if not csv_file_path.exists():
            raise CommandError(f"CSV file not found: {csv_file_path}")

        # Start the import process
        self.stdout.write(self.style.SUCCESS(f"Starting language pricing import from: {csv_file_path}"))
        self.stdout.write(f"Dry run mode: {options['dry_run']}")

        # Initialize tracking
        self._init_tracking()

        # Load and validate data
        pricing_data = self._load_csv_data(csv_file_path)
        self._validate_prerequisites()

        # Process the data
        for row_num, row_data in enumerate(pricing_data, start=2):  # Skip header
            self._process_pricing_row(row_num, row_data)

        # Generate report
        self._generate_report()

    def _get_csv_file_path(self) -> Path:
        """Get the CSV file path."""
        csv_file = self.options["csv_file"]
        if not Path(csv_file).is_absolute():
            csv_file = Path(__file__).parent.parent.parent.parent.parent / csv_file
        return Path(csv_file)

    def _init_tracking(self):
        """Initialize tracking variables."""
        self.processed_count = 0
        self.success_count = 0
        self.rejection_counts = {
            "missing_course": 0,
            "invalid_price": 0,
            "invalid_date": 0,
            "duplicate_record": 0,
            "validation_error": 0,
        }
        self.rejection_details = {key: [] for key in self.rejection_counts.keys()}
        self.lang_division = None
        self.course_cache = {}

    def _load_csv_data(self, csv_file_path: Path) -> list[dict]:
        """Load and parse CSV data."""
        pricing_data = []

        try:
            with open(csv_file_path, encoding="utf-8-sig") as file:
                reader = csv.DictReader(file)
                expected_headers = [
                    "Language_Course",
                    "Price_USD",
                    "Effective_Term",
                    "Effective_Date",
                    "End_date",
                ]

                # Validate headers
                if not all(header in reader.fieldnames for header in expected_headers):
                    raise CommandError(f"CSV missing required headers. Expected: {expected_headers}")

                for row in reader:
                    pricing_data.append(row)

        except Exception as e:
            raise CommandError(f"Error reading CSV file: {e}") from e

        self.stdout.write(f"Loaded {len(pricing_data)} pricing records from CSV")
        return pricing_data

    def _validate_prerequisites(self):
        """Validate system prerequisites for import."""
        # Get LANG division
        try:
            self.lang_division = Division.objects.get(short_name="LANG")
        except Division.DoesNotExist as e:
            raise CommandError("LANG division not found. Please ensure divisions are set up correctly.") from e

        # Cache language courses
        lang_courses = Course.objects.filter(cycle__division=self.lang_division)
        for course in lang_courses:
            self.course_cache[course.code] = course

        self.stdout.write(f"Found {len(self.course_cache)} language courses in LANG division")

    def _process_pricing_row(self, row_num: int, row_data: dict):
        """Process a single pricing row."""
        self.processed_count += 1

        try:
            # Extract and validate data
            course_code = row_data["Language_Course"].strip()
            price_usd = row_data["Price_USD"].strip()
            effective_date_str = row_data["Effective_Date"].strip()
            end_date_str = row_data["End_date"].strip() if row_data["End_date"] else ""

            # Validate course exists
            if course_code not in self.course_cache:
                self._record_rejection(
                    "missing_course",
                    row_num,
                    course_code,
                    f"Course {course_code} not found in LANG division",
                )
                return

            course = self.course_cache[course_code]

            # Validate and parse price
            try:
                price = Decimal(price_usd)
                if price < 0:
                    raise ValueError("Negative price")
            except (InvalidOperation, ValueError) as e:
                self._record_rejection(
                    "invalid_price",
                    row_num,
                    course_code,
                    f"Invalid price '{price_usd}': {e}",
                )
                return

            # Validate and parse effective date
            try:
                effective_date = datetime.strptime(effective_date_str, "%Y-%m-%d").date()
            except ValueError as e:
                self._record_rejection(
                    "invalid_date",
                    row_num,
                    course_code,
                    f"Invalid effective date '{effective_date_str}': {e}",
                )
                return

            # Validate and parse end date (optional)
            end_date = None
            if end_date_str:
                try:
                    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
                except ValueError as e:
                    self._record_rejection(
                        "invalid_date",
                        row_num,
                        course_code,
                        f"Invalid end date '{end_date_str}': {e}",
                    )
                    return

            # Check for existing record with same course and effective date
            if CourseFixedPricing.objects.filter(course=course, effective_date=effective_date).exists():
                self._record_rejection(
                    "duplicate_record",
                    row_num,
                    course_code,
                    f"CourseFixedPricing already exists for {course_code} on {effective_date}",
                )
                return

            # Create the pricing record
            self._create_pricing_record(course, price, effective_date, end_date, row_num, course_code)

        except Exception as e:
            self._record_rejection(
                "validation_error",
                row_num,
                row_data.get("Language_Course", "Unknown"),
                f"Unexpected error: {e}",
            )

    def _create_pricing_record(
        self,
        course: Course,
        price: Decimal,
        effective_date: date,
        end_date: date | None,
        row_num: int,
        course_code: str,
    ):
        """Create a CourseFixedPricing record."""
        try:
            if not self.options["dry_run"]:
                CourseFixedPricing.objects.create(
                    course=course,
                    domestic_price=price,
                    foreign_price=price,  # Use same price for both domestic and foreign students
                    effective_date=effective_date,
                    end_date=end_date,  # None means current/active pricing
                )
                end_date_display = end_date if end_date else "current/active"
                self.stdout.write(f"Created pricing: {course_code} ${price} ({effective_date} to {end_date_display})")
            else:
                end_date_display = end_date if end_date else "current/active"
                self.stdout.write(
                    f"[DRY RUN] Would create pricing for {course_code}: ${price} "
                    f"({effective_date} to {end_date_display})"
                )

            self.success_count += 1

        except Exception as e:
            self._record_rejection(
                "validation_error",
                row_num,
                course_code,
                f"Database error creating pricing: {e}",
            )

    def _record_rejection(self, rejection_type: str, row_num: int, course_code: str, reason: str):
        """Record a rejection with details."""
        self.rejection_counts[rejection_type] += 1
        self.rejection_details[rejection_type].append({"row": row_num, "course_code": course_code, "reason": reason})
        self.stdout.write(self.style.WARNING(f"Row {row_num} ({course_code}): {reason}"))

    def _generate_report(self):
        """Generate comprehensive import report."""
        {
            "command": "import_language_pricing",
            "csv_file": str(self.options["csv_file"]),
            "dry_run": self.options["dry_run"],
            "processed_count": self.processed_count,
            "success_count": self.success_count,
            "total_rejections": sum(self.rejection_counts.values()),
            "rejection_summary": self.rejection_counts,
            "rejection_details": self.rejection_details,
            "lang_division_courses": len(self.course_cache),
            "missing_weekend_english": "Note: Weekend English classes mentioned as missing from source data",
        }

        # Generate the audit report
        self._generate_audit_report()

        # Display summary
        self._display_summary()

    def _display_summary(self):
        """Display import summary."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("LANGUAGE PRICING IMPORT SUMMARY"))
        self.stdout.write("=" * 60)

        self.stdout.write(f"Total records processed: {self.processed_count}")
        self.stdout.write(self.style.SUCCESS(f"Successfully imported: {self.success_count}"))

        total_rejections = sum(self.rejection_counts.values())
        if total_rejections > 0:
            self.stdout.write(self.style.WARNING(f"Total rejections: {total_rejections}"))
            for rejection_type, count in self.rejection_counts.items():
                if count > 0:
                    self.stdout.write(f"  - {rejection_type.replace('_', ' ').title()}: {count}")

        if self.options["dry_run"]:
            self.stdout.write(self.style.WARNING("\nDRY RUN MODE - No actual changes made"))
        else:
            self.stdout.write(self.style.SUCCESS("\nImport completed successfully"))

        self.stdout.write(f"\nLANG division courses available: {len(self.course_cache)}")

        # Note about limitations
        self.stdout.write("\nIMPORTANT NOTES:")
        self.stdout.write("- Foreign student pricing set equal to domestic (CSV limitation)")
        self.stdout.write("- Weekend English Express classes included in current data")
        self.stdout.write("- Empty end_date means current/active pricing")
