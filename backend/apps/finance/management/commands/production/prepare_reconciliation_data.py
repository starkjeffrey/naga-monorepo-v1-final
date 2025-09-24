"""Management command to prepare reconciliation data from legacy CSV files.

This command loads the legacy data files with timestamp 250728 and prepares
them for reconciliation processing.
"""

import csv
import logging
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Load and prepare legacy data for reconciliation."""

    help = "Load legacy CSV data (250728) and prepare for reconciliation"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {
            "students_loaded": 0,
            "payments_loaded": 0,
            "enrollments_loaded": 0,
            "classes_loaded": 0,
            "errors": 0,
        }

        # Base data directory
        self.data_dir = Path("data/legacy")

        # File mappings with 250728 timestamp
        self.file_mappings = {
            "students": "all_students_250728.csv",
            "payments": "all_receipt_headers_250728.csv",
            "enrollments": "all_academiccoursetakers_250728.csv",
            "classes": "all_academicclasses_250728.csv",
        }

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--data-dir",
            type=str,
            default="data/legacy",
            help="Directory containing legacy CSV files",
        )
        parser.add_argument(
            "--load-tables",
            action="store_true",
            help="Load data into legacy_* tables in database",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run in dry-run mode without saving data",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Skip records that already exist",
        )
        parser.add_argument(
            "--students-only",
            action="store_true",
            help="Load only students data for testing",
        )
        parser.add_argument("--limit", type=int, help="Limit number of records to process (for testing)")

    def handle(self, *args, **options):
        """Main command handler."""

        self.data_dir = Path(options["data_dir"])
        self.load_tables = options["load_tables"]
        self.dry_run = options["dry_run"]
        self.skip_existing = options["skip_existing"]
        self.students_only = options["students_only"]
        self.limit = options.get("limit")

        if self.dry_run:
            self.stdout.write(self.style.WARNING("Running in DRY-RUN mode"))

        try:
            # Verify all files exist
            self._verify_files()

            if self.load_tables:
                # Load data into database tables
                with transaction.atomic():
                    self._create_legacy_tables()
                    self._load_students()

                    # Only load other data if not students-only mode
                    if not self.students_only:
                        self._load_payments()
                        self._load_classes()
                        self._load_enrollments()

                    if self.dry_run:
                        transaction.set_rollback(True)
            else:
                # Just verify data integrity
                self._verify_data_integrity()

            # Print summary
            self._print_summary()

        except Exception as e:
            logger.error(f"Error in reconciliation data preparation: {e}")
            raise CommandError(f"Failed to prepare reconciliation data: {e}") from e

    def _verify_files(self):
        """Verify all required files exist."""
        self.stdout.write("Verifying data files...")

        for file_type, filename in self.file_mappings.items():
            filepath = self.data_dir / filename
            if not filepath.exists():
                raise CommandError(f"Missing {file_type} file: {filepath}")

            # Check file is readable and has content
            with open(filepath, encoding="utf-8") as f:
                reader = csv.reader(f)
                try:
                    headers = next(reader)
                    self.stdout.write(f"  ✓ {filename} - {len(headers)} columns")
                except StopIteration as e:
                    raise CommandError(f"Empty file: {filepath}") from e

    def _create_legacy_tables(self):
        """Create legacy_* tables if loading to database."""
        from django.db import connection

        self.stdout.write("Creating legacy tables...")

        with connection.cursor() as cursor:
            # Drop existing tables to recreate with correct schema
            cursor.execute("DROP TABLE IF EXISTS legacy_students CASCADE")
            cursor.execute("DROP TABLE IF EXISTS legacy_payments CASCADE")
            cursor.execute("DROP TABLE IF EXISTS legacy_enrollments CASCADE")
            cursor.execute("DROP TABLE IF EXISTS legacy_classes CASCADE")

            # Create legacy_students table
            cursor.execute(
                """
                CREATE TABLE legacy_students (
                    student_id VARCHAR(10) PRIMARY KEY,
                    first_name VARCHAR(100),
                    last_name VARCHAR(100),
                    citizenship VARCHAR(50),
                    email VARCHAR(100),
                    phone VARCHAR(50),
                    created_date DATE,
                    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create legacy_payments table
            cursor.execute(
                """
                CREATE TABLE legacy_payments (
                    receipt_id VARCHAR(200) PRIMARY KEY,
                    student_id VARCHAR(10),
                    term_id VARCHAR(50),
                    amount DECIMAL(10,2),
                    payment_date TIMESTAMP,
                    deleted BOOLEAN DEFAULT FALSE,
                    notes TEXT,
                    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create legacy_enrollments table
            cursor.execute(
                """
                CREATE TABLE legacy_enrollments (
                    id SERIAL PRIMARY KEY,
                    student_id VARCHAR(10),
                    class_id VARCHAR(300),
                    term_id VARCHAR(50),
                    course_code VARCHAR(50),
                    normalized_course VARCHAR(50),
                    attendance VARCHAR(50),
                    grade VARCHAR(10),
                    credits DECIMAL(3,1),
                    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(student_id, class_id)
                )
            """
            )

            # Create legacy_classes table
            cursor.execute(
                """
                CREATE TABLE legacy_classes (
                    class_id VARCHAR(300) PRIMARY KEY,
                    term_id VARCHAR(50),
                    course_code VARCHAR(50),
                    normalized_course VARCHAR(50),
                    time_of_day VARCHAR(20),
                    section VARCHAR(20),
                    instructor VARCHAR(100),
                    max_enrollment INTEGER,
                    imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_legacy_payments_student ON legacy_payments(student_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_legacy_payments_term ON legacy_payments(term_id)")
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_legacy_enrollments_student ON legacy_enrollments(student_id)"
            )
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_legacy_enrollments_term ON legacy_enrollments(term_id)")

    def _load_students(self):
        """Load student data."""
        self.stdout.write("Loading students...")

        filepath = self.data_dir / self.file_mappings["students"]

        with open(filepath, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            count = 0
            for row in reader:
                # Apply limit if specified
                if self.limit and count >= self.limit:
                    break
                count += 1
                try:
                    # Use actual CSV column 'ID' for student number (handle both numeric and text IDs)
                    raw_id = row.get("ID", "").strip()
                    # Only zero-pad if it's a numeric ID, otherwise use as-is
                    if raw_id.isdigit():
                        student_id = raw_id.zfill(5)  # Ensure 5 digits for numeric IDs
                    else:
                        student_id = raw_id  # Keep non-numeric IDs as-is (e.g., 'GEI001')

                    if self.load_tables:
                        from django.db import connection

                        with connection.cursor() as cursor:
                            cursor.execute(
                                """
                                INSERT INTO legacy_students
                                (student_id, first_name, last_name, citizenship, email, phone)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (student_id) DO NOTHING
                            """,
                                [
                                    student_id,
                                    row.get("Name", ""),  # CSV has 'Name' not 'FirstName'/'LastName'
                                    "",  # No separate LastName in CSV
                                    row.get("Nationality", ""),  # CSV has 'Nationality' not 'Citizenship'
                                    row.get("Email", ""),
                                    row.get("MobilePhone", ""),  # CSV has 'MobilePhone' not 'Phone'
                                ],
                            )

                    self.stats["students_loaded"] += 1

                except Exception as e:
                    logger.error(f"Error loading student {row}: {e}")
                    self.stats["errors"] += 1

    def _load_payments(self):
        """Load payment data."""
        self.stdout.write("Loading payments...")

        filepath = self.data_dir / self.file_mappings["payments"]

        with open(filepath, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    # Skip deleted payments
                    if row.get("Deleted") == "1":
                        continue

                    # Use actual CSV column 'ID' for student number (handle both numeric and text IDs)
                    raw_id = row.get("ID", "").strip()
                    # Only zero-pad if it's a numeric ID, otherwise use as-is
                    if raw_id.isdigit():
                        student_id = raw_id.zfill(5)  # Ensure 5 digits for numeric IDs
                    else:
                        student_id = raw_id  # Keep non-numeric IDs as-is (e.g., 'GEI001')

                    # Handle NULL amounts properly
                    amount_str = row.get("Amount", "0")
                    if amount_str == "NULL" or not amount_str:
                        amount = Decimal("0")
                    else:
                        try:
                            amount = Decimal(amount_str)
                        except (ValueError, TypeError, InvalidOperation):
                            amount = Decimal("0")

                    if self.load_tables:
                        from django.db import connection

                        with connection.cursor() as cursor:
                            # Handle NULL payment date
                            pmt_date = row.get("PmtDate")
                            if pmt_date == "NULL" or not pmt_date:
                                pmt_date = None

                            cursor.execute(
                                """
                                INSERT INTO legacy_payments
                                (receipt_id, student_id, term_id, amount, payment_date, deleted)
                                VALUES (%s, %s, %s, %s, %s, %s)
                                ON CONFLICT (receipt_id) DO NOTHING
                            """,
                                [
                                    row.get("ReceiptID"),
                                    student_id,
                                    row.get("TermID"),
                                    amount,
                                    pmt_date,  # Handle NULL dates
                                    row.get("Deleted") == "1",
                                ],
                            )

                    self.stats["payments_loaded"] += 1

                except Exception as e:
                    logger.error(f"Error loading payment {row}: {e}")
                    self.stats["errors"] += 1

    def _load_classes(self):
        """Load class data."""
        self.stdout.write("Loading classes...")

        filepath = self.data_dir / self.file_mappings["classes"]

        with open(filepath, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    if self.load_tables:
                        from django.db import connection

                        with connection.cursor() as cursor:
                            cursor.execute(
                                """
                                INSERT INTO legacy_classes
                                (class_id, term_id, course_code, normalized_course,
                                 time_of_day, section, instructor, max_enrollment)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (class_id) DO NOTHING
                            """,
                                [
                                    row.get("ClassID"),
                                    row.get("TermID"),
                                    row.get("CourseCode"),
                                    row.get("NormalizedCourse"),
                                    row.get("NormalizedTOD"),  # CSV has 'NormalizedTOD' not 'TimeOfDay'
                                    row.get("NormalizedSection"),  # CSV has 'NormalizedSection' not 'Section'
                                    "",  # No instructor field in CSV
                                    30,  # Default max enrollment
                                ],
                            )

                    self.stats["classes_loaded"] += 1

                except Exception as e:
                    logger.error(f"Error loading class {row}: {e}")
                    self.stats["errors"] += 1

    def _load_enrollments(self):
        """Load enrollment data."""
        self.stdout.write("Loading enrollments...")

        filepath = self.data_dir / self.file_mappings["enrollments"]

        with open(filepath, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                try:
                    # Use actual CSV column 'ID' for student number (handle both numeric and text IDs)
                    raw_id = row.get("ID", "").strip()
                    # Only zero-pad if it's a numeric ID, otherwise use as-is
                    if raw_id.isdigit():
                        student_id = raw_id.zfill(5)  # Ensure 5 digits for numeric IDs
                    else:
                        student_id = raw_id  # Keep non-numeric IDs as-is (e.g., 'GEI001')

                    if self.load_tables:
                        from django.db import connection

                        with connection.cursor() as cursor:
                            cursor.execute(
                                """
                                INSERT INTO legacy_enrollments
                                (student_id, class_id, term_id, course_code,
                                 normalized_course, attendance, grade, credits)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (student_id, class_id) DO NOTHING
                            """,
                                [
                                    student_id,
                                    row.get("ClassID"),
                                    row.get("parsed_termid"),  # CSV has 'parsed_termid' not 'TermID'
                                    row.get("parsed_coursecode"),  # CSV has 'parsed_coursecode' not 'CourseCode'
                                    row.get("NormalizedCourse"),
                                    row.get("Attendance", "Normal"),
                                    row.get("Grade"),
                                    row.get("Credit", 3),  # CSV has 'Credit' not 'Credits'
                                ],
                            )

                    self.stats["enrollments_loaded"] += 1

                except Exception as e:
                    logger.error(f"Error loading enrollment {row}: {e}")
                    self.stats["errors"] += 1

    def _verify_data_integrity(self):
        """Verify data integrity without loading."""
        self.stdout.write("Verifying data integrity...")

        # Count records in each file
        for _file_type, filename in self.file_mappings.items():
            filepath = self.data_dir / filename
            with open(filepath, encoding="utf-8") as f:
                reader = csv.reader(f)
                count = sum(1 for row in reader) - 1  # Subtract header
                self.stdout.write(f"  {filename}: {count:,} records")

    def _print_summary(self):
        """Print summary of operations."""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("RECONCILIATION DATA PREPARATION SUMMARY")
        self.stdout.write("=" * 50)

        if self.load_tables:
            self.stdout.write(f"Students loaded: {self.stats['students_loaded']:,}")
            self.stdout.write(f"Payments loaded: {self.stats['payments_loaded']:,}")
            self.stdout.write(f"Classes loaded: {self.stats['classes_loaded']:,}")
            self.stdout.write(f"Enrollments loaded: {self.stats['enrollments_loaded']:,}")
            self.stdout.write(f"Errors: {self.stats['errors']:,}")

            if self.dry_run:
                self.stdout.write(self.style.WARNING("\nDRY RUN - No data was actually saved"))
        else:
            self.stdout.write("Data verification completed")

        self.stdout.write("=" * 50)
