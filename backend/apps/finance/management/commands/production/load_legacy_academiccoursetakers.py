"""Load legacy academiccoursetakers data with Pydantic validation based on SQL Server DDL."""

import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection
from pydantic import BaseModel, Field, field_validator


class LegacyAcademicCourseTaker(BaseModel):
    """Pydantic model for legacy academiccoursetakers data validation based on SQL Server DDL."""

    # Primary key
    ipk: int = Field(..., description="Internal primary key")

    # Student and class info
    id: str = Field(..., max_length=50, description="Student ID (5 digits, left padded)")
    classid: str = Field(..., max_length=100, description="Class ID (unique to class/time-of-day/section)")

    # Academic performance
    repeatnum: int | None = Field(None, description="Number of times repeated")
    lscore: Decimal | None = Field(None, max_digits=10, decimal_places=2, description="Lower score")
    uscore: Decimal | None = Field(None, max_digits=10, decimal_places=2, description="Upper score")
    credit: int | None = Field(None, description="Credit hours")
    gradepoint: Decimal | None = Field(None, max_digits=10, decimal_places=2)
    totalpoint: Decimal | None = Field(None, max_digits=10, decimal_places=2)
    grade: str | None = Field(None, max_length=10)
    previousgrade: str | None = Field(None, max_length=10)

    # Status and notes
    comment: str | None = Field(None, max_length=100)
    passed: int | None = Field(None, description="1 if passed, 0 if failed")
    remarks: str | None = Field(None, max_length=50)

    # Registration info
    registermode: str | None = Field(None, max_length=20)
    attendance: str | None = Field(None, max_length=20, description="Normal/Audit - critical for pricing")

    # UI/Display fields
    color: Decimal | None = Field(None, max_digits=10, decimal_places=2)
    forecolor: int | None = Field(None)
    backcolor: int | None = Field(None)

    # Quick note and positioning
    quicknote: str | None = Field(None, max_length=50)
    pos: Decimal | None = Field(None, max_digits=10, decimal_places=2)
    gpos: Decimal | None = Field(None, max_digits=10, decimal_places=2)

    # Audit fields
    adder: Decimal | None = Field(None, max_digits=10, decimal_places=2)
    addtime: datetime | None = None
    lastupdate: datetime | None = None
    createddate: datetime | None = None
    modifieddate: datetime | None = None

    # Parsed fields from ClassID
    section: str | None = Field(None, max_length=10)
    timeslot: str | None = Field(None, max_length=10)
    parsedtermid: str | None = Field(None, max_length=50)
    parsedcoursecode: str | None = Field(None, max_length=100)
    parsedlangcourse: str | None = Field(None, max_length=255)

    # CRITICAL: Normalized fields for pricing and analysis
    normalizedcourse: str | None = Field(None, max_length=50, description="Normalized course code")
    normalizedsection: str | None = Field(None, max_length=50, description="CRITICAL for Reading Class pricing")
    normalizedtod: str | None = Field(None, max_length=50, description="Normalized time of day")

    @field_validator("id")
    @classmethod
    def validate_student_id(cls, v: str) -> str:
        """Ensure student ID is properly formatted (5 digits, left padded)."""
        if v and v not in ["NULL", "null", ""]:
            # Remove any non-numeric characters first
            numeric_part = "".join(c for c in v if c.isdigit())
            if numeric_part:
                # Pad to 5 digits
                return numeric_part.zfill(5)
        return v

    @field_validator("classid")
    @classmethod
    def validate_classid(cls, v: str) -> str:
        """Validate ClassID format."""
        if v and v not in ["NULL", "null", ""]:
            # ClassID contains composite information about term/course/section
            # Just ensure it's cleaned
            return v.strip()
        return v

    @field_validator("attendance")
    @classmethod
    def validate_attendance(cls, v: str | None) -> str | None:
        """Validate attendance field - critical for pricing."""
        if v and v not in ["NULL", "null", ""]:
            # Normalize to title case for consistency
            return v.strip().title()
        return v

    @field_validator("*", mode="before")
    @classmethod
    def empty_str_to_none(cls, v):
        """Convert empty strings and 'NULL' to None."""
        if v in ["", "NULL", "null"]:
            return None
        return v

    class Config:
        str_strip_whitespace = True


class Command(BaseCommand):
    """Load legacy academiccoursetakers data with validation."""

    help = "Load legacy academiccoursetakers data from CSV with Pydantic validation"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/legacy/all_academiccoursetakers_250802.csv",
            help="Path to academiccoursetakers CSV file",
        )
        parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for inserts")
        parser.add_argument("--drop-existing", action="store_true", help="Drop existing table before loading")

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        batch_size = options["batch_size"]

        if not file_path.exists():
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        # Create table
        if options["drop_existing"]:
            self._drop_table()
        self._create_table()

        # Load data
        success_count = 0
        error_count = 0
        batch_data = []

        # Track statistics for pricing analysis
        attendance_stats = {"Normal": 0, "Audit": 0, "Other": 0}
        section_stats = {}

        self.stdout.write(f"Loading academiccoursetakers from {file_path}")

        with open(file_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):
                try:
                    # Parse dates
                    for date_field in ["AddTime", "LastUpdate", "CreatedDate", "ModifiedDate"]:
                        if row.get(date_field) and row[date_field] not in ["NULL", ""]:
                            try:
                                # Handle datetime format
                                row[date_field] = datetime.strptime(row[date_field].split(".")[0], "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                row[date_field] = None
                        else:
                            row[date_field] = None

                    # Create Pydantic model for validation
                    course_taker_data = {key.lower(): value for key, value in row.items()}

                    # Validate with Pydantic
                    course_taker = LegacyAcademicCourseTaker(**course_taker_data)

                    # Collect statistics
                    if course_taker.attendance:
                        if course_taker.attendance == "Normal":
                            attendance_stats["Normal"] += 1
                        elif course_taker.attendance == "Audit":
                            attendance_stats["Audit"] += 1
                        else:
                            attendance_stats["Other"] += 1

                    if course_taker.normalizedsection:
                        section = course_taker.normalizedsection
                        section_stats[section] = section_stats.get(section, 0) + 1

                    # Add to batch
                    batch_data.append(course_taker.model_dump())

                    # Insert batch
                    if len(batch_data) >= batch_size:
                        self._insert_batch(batch_data)
                        success_count += len(batch_data)
                        self.stdout.write(f"  Inserted {success_count:,} records...")
                        batch_data = []

                except Exception as e:
                    error_count += 1
                    if error_count <= 10:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_num}: {e!s} - ID: {row.get('ID', 'N/A')}, "
                                f"ClassID: {row.get('ClassID', 'N/A')}"
                            )
                        )
                    continue

            # Insert remaining batch
            if batch_data:
                self._insert_batch(batch_data)
                success_count += len(batch_data)

        self.stdout.write(self.style.SUCCESS(f"Completed: {success_count:,} records loaded, {error_count:,} errors"))

        # Report statistics
        self.stdout.write("\n=== ATTENDANCE STATISTICS (Critical for Pricing) ===")
        for attendance_type, count in attendance_stats.items():
            self.stdout.write(f"{attendance_type}: {count:,} records")

        self.stdout.write("\n=== TOP 10 SECTIONS BY ENROLLMENT ===")
        sorted_sections = sorted(section_stats.items(), key=lambda x: x[1], reverse=True)[:10]
        for section, count in sorted_sections:
            self.stdout.write(f"Section {section}: {count:,} enrollments")

    def _drop_table(self):
        """Drop existing table."""
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS legacy_course_takers")
            self.stdout.write("Dropped existing legacy_course_takers table")

    def _create_table(self):
        """Create legacy_course_takers table based on SQL Server DDL."""
        create_sql = """
        CREATE TABLE IF NOT EXISTS legacy_course_takers (
            ipk INTEGER PRIMARY KEY,
            id VARCHAR(50),
            classid VARCHAR(100),
            repeatnum INTEGER,
            lscore DECIMAL(10,2),
            uscore DECIMAL(10,2),
            credit INTEGER,
            gradepoint DECIMAL(10,2),
            totalpoint DECIMAL(10,2),
            grade VARCHAR(10),
            previousgrade VARCHAR(10),
            comment VARCHAR(100),
            passed INTEGER,
            remarks VARCHAR(50),
            color DECIMAL(10,2),
            registermode VARCHAR(20),
            attendance VARCHAR(20),
            forecolor INTEGER,
            backcolor INTEGER,
            quicknote VARCHAR(50),
            pos DECIMAL(10,2),
            gpos DECIMAL(10,2),
            adder DECIMAL(10,2),
            addtime TIMESTAMP,
            lastupdate TIMESTAMP,
            createddate TIMESTAMP,
            modifieddate TIMESTAMP,
            section VARCHAR(10),
            timeslot VARCHAR(10),
            parsedtermid VARCHAR(50),
            parsedcoursecode VARCHAR(100),
            parsedlangcourse VARCHAR(255),
            normalizedcourse VARCHAR(50),
            normalizedsection VARCHAR(50),
            normalizedtod VARCHAR(50),
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Critical indexes for performance and analysis
        CREATE INDEX idx_legacy_ct_student_id ON legacy_course_takers(id);
        CREATE INDEX idx_legacy_ct_classid ON legacy_course_takers(classid);
        CREATE INDEX idx_legacy_ct_attendance ON legacy_course_takers(attendance);
        CREATE INDEX idx_legacy_ct_normalized_section ON legacy_course_takers(normalizedsection);
        CREATE INDEX idx_legacy_ct_normalized_course ON legacy_course_takers(normalizedcourse);
        CREATE INDEX idx_legacy_ct_parsed_term ON legacy_course_takers(parsedtermid);
        CREATE INDEX idx_legacy_ct_grade ON legacy_course_takers(grade);
        CREATE INDEX idx_legacy_ct_passed ON legacy_course_takers(passed);

        -- Composite index for Reading Class pricing queries
        CREATE INDEX idx_legacy_ct_reading_class_pricing
            ON legacy_course_takers(classid, attendance, normalizedsection)
            WHERE attendance = 'Normal';
        """

        with connection.cursor() as cursor:
            cursor.execute(create_sql)
            self.stdout.write("Created legacy_course_takers table with indexes")

    def _insert_batch(self, batch_data):
        """Insert a batch of course taker records."""
        if not batch_data:
            return

        # Get column names from first record
        columns = list(batch_data[0].keys())
        placeholders = ", ".join(["%s"] * len(columns))
        columns_str = ", ".join(columns)

        insert_sql = f"""
        INSERT INTO legacy_course_takers ({columns_str})
        VALUES ({placeholders})
        ON CONFLICT (ipk) DO NOTHING
        """

        with connection.cursor() as cursor:
            for record in batch_data:
                values = [record.get(col) for col in columns]
                cursor.execute(insert_sql, values)
