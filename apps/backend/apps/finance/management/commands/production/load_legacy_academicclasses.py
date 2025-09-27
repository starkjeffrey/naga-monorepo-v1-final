"""Load legacy academicclasses data with Pydantic validation based on SQL Server DDL.

PRODUCTION LOADER - Validated data import with EXACT DDL field specifications
"""

import csv
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection
from pydantic import BaseModel, Field, field_validator


class LegacyAcademicClass(BaseModel):
    """Pydantic model for legacy academicclasses data validation based on SQL Server DDL.

    This represents class/course offerings from the legacy system with EXACT field lengths.
    """

    # Term and program info
    termid: str | None = Field(None, max_length=100, description="Term ID")
    program: float | None = Field(None, description="Program code")
    major: float | None = Field(None, description="Major code")

    # Group identifiers
    groupid: str | None = Field(None, max_length=100, description="Group ID")
    desgroupid: str | None = Field(None, max_length=100, description="Designated group ID - CHAR field")

    # Course info
    coursecode: str | None = Field(None, max_length=100, description="Course code")
    classid: str | None = Field(None, max_length=255, description="Class ID (unique to class/time-of-day/section)")
    coursetitle: str | None = Field(None, max_length=255, description="Course title/name")

    # Class details
    stnumber: float | None = Field(None, description="Student number/enrollment")
    coursetype: str | None = Field(None, max_length=100, description="Type of course")
    schooltime: str | None = Field(None, max_length=50, description="Class time/schedule")

    # Display and positioning
    color: str | None = Field(None, max_length=50, description="Display color")
    pos: float | None = Field(None, description="Position")
    gidpos: float | None = Field(None, description="Group ID position")
    cidpos: float | None = Field(None, description="Class ID position")
    propos: float | None = Field(None, description="Program position")

    # Subject fields
    subject: str | None = Field(None, max_length=150, description="Subject")
    exsubject: str | None = Field(None, max_length=100, description="Extended subject")

    # Shadow flag
    isshadow: float | None = Field(None, description="Is shadow class flag")

    # Primary key
    ipk: int = Field(..., description="Internal primary key")

    # Audit fields
    createddate: datetime | None = None
    modifieddate: datetime | None = None

    # CRITICAL: Normalized fields for pricing and analysis
    normalizedcourse: str | None = Field(None, max_length=20, description="Normalized course code")
    normalizedpart: str | None = Field(None, max_length=20, description="Normalized part")
    normalizedsection: str | None = Field(None, max_length=20, description="CRITICAL for Reading Class pricing")
    normalizedtod: str | None = Field(None, max_length=10, description="Normalized time of day")

    # Legacy course code
    oldcoursecode: str | None = Field(None, max_length=20, description="Old/legacy course code")

    @field_validator("classid")
    @classmethod
    def validate_classid(cls, v: str) -> str:
        """Validate ClassID format."""
        if v and v not in ["NULL", "null", ""]:
            # ClassID contains composite information about term/course/section
            # Just ensure it's cleaned
            return v.strip()
        return v

    @field_validator("desgroupid")
    @classmethod
    def validate_desgroupid(cls, v: str | None) -> str | None:
        """Validate designated group ID - this is a CHAR field so preserve spacing."""
        if v and v not in ["NULL", "null"]:
            # CHAR fields maintain their full length with padding
            return v
        return None

    @field_validator("normalizedsection")
    @classmethod
    def validate_normalized_section(cls, v: str | None) -> str | None:
        """Validate normalized section - critical for pricing."""
        if v and v not in ["NULL", "null", ""]:
            return v.strip()
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
    """PRODUCTION LOADER - Load legacy academicclasses data with EXACT DDL validation."""

    help = "PRODUCTION: Load legacy academicclasses data from CSV with exact DDL field validation"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/legacy/all_academicclasses_250802.csv",
            help="Path to academicclasses CSV file",
        )
        parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for inserts")
        parser.add_argument("--drop-existing", action="store_true", help="Drop existing table before loading")

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        batch_size = options["batch_size"]

        if not file_path.exists():
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        self.stdout.write(self.style.WARNING("=== PRODUCTION DATA LOADER - ACADEMIC CLASSES ==="))
        self.stdout.write("Loading academic classes with exact SQL Server DDL specifications")

        # Create table
        if options["drop_existing"]:
            self._drop_table()
        self._create_table()

        # Load data
        success_count = 0
        error_count = 0
        batch_data = []

        # Track statistics for analysis
        term_stats = {}
        program_stats = {}
        section_stats = {}
        course_type_stats = {}
        error_details = []

        self.stdout.write(f"Loading academic classes from {file_path}")

        with open(file_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):
                try:
                    # Parse dates
                    for date_field in ["CreatedDate", "ModifiedDate"]:
                        if row.get(date_field) and row[date_field] not in ["NULL", ""]:
                            try:
                                # Handle datetime format
                                row[date_field] = datetime.strptime(row[date_field].split(".")[0], "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                row[date_field] = None
                        else:
                            row[date_field] = None

                    # Create Pydantic model for validation
                    class_data = {key.lower(): value for key, value in row.items()}

                    # Validate with Pydantic
                    academic_class = LegacyAcademicClass(**class_data)

                    # Collect statistics
                    if academic_class.termid:
                        term_stats[academic_class.termid] = term_stats.get(academic_class.termid, 0) + 1

                    if academic_class.program:
                        program_key = f"P{int(academic_class.program)}"
                        program_stats[program_key] = program_stats.get(program_key, 0) + 1

                    if academic_class.normalizedsection:
                        section_stats[academic_class.normalizedsection] = (
                            section_stats.get(academic_class.normalizedsection, 0) + 1
                        )

                    if academic_class.coursetype:
                        course_type_stats[academic_class.coursetype] = (
                            course_type_stats.get(academic_class.coursetype, 0) + 1
                        )

                    # Add to batch
                    batch_data.append(academic_class.model_dump())

                    # Insert batch
                    if len(batch_data) >= batch_size:
                        self._insert_batch(batch_data)
                        success_count += len(batch_data)
                        self.stdout.write(f"  Inserted {success_count:,} records...")
                        batch_data = []

                except Exception as e:
                    error_count += 1
                    error_detail = {
                        "row": row_num,
                        "error": str(e),
                        "classid": row.get("ClassID", "N/A"),
                        "coursecode": row.get("CourseCode", "N/A"),
                        "ipk": row.get("IPK", "N/A"),
                    }
                    error_details.append(error_detail)

                    if error_count <= 10:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_num}: {e!s} - ClassID: {row.get('ClassID', 'N/A')}, "
                                f"Course: {row.get('CourseCode', 'N/A')}"
                            )
                        )
                    continue

            # Insert remaining batch
            if batch_data:
                self._insert_batch(batch_data)
                success_count += len(batch_data)

        self.stdout.write(self.style.SUCCESS(f"Completed: {success_count:,} records loaded, {error_count:,} errors"))

        # Write error log if needed
        if error_count > 0:
            error_log_path = Path("academicclasses_errors.log")
            with open(error_log_path, "w") as f:
                f.write(f"Total errors: {error_count}\n\n")
                for error in error_details[:1000]:  # First 1000 errors
                    f.write(f"Row {error['row']}: {error['error']}\n")
                    f.write(f"  ClassID: {error['classid']}, Course: {error['coursecode']}, IPK: {error['ipk']}\n\n")
            self.stdout.write(f"Error details written to {error_log_path}")

        # Report statistics
        self.stdout.write("\n=== TERM DISTRIBUTION ===")
        sorted_terms = sorted(term_stats.items(), key=lambda x: x[1], reverse=True)[:10]
        for term, count in sorted_terms:
            self.stdout.write(f"Term {term}: {count:,} classes")

        self.stdout.write("\n=== PROGRAM DISTRIBUTION ===")
        sorted_programs = sorted(program_stats.items(), key=lambda x: x[1], reverse=True)[:10]
        for program, count in sorted_programs:
            self.stdout.write(f"Program {program}: {count:,} classes")

        self.stdout.write("\n=== SECTION DISTRIBUTION (Critical for Pricing) ===")
        sorted_sections = sorted(section_stats.items(), key=lambda x: x[1], reverse=True)[:20]
        for section, count in sorted_sections:
            self.stdout.write(f"Section {section}: {count:,} classes")

        self.stdout.write("\n=== COURSE TYPE DISTRIBUTION ===")
        sorted_types = sorted(course_type_stats.items(), key=lambda x: x[1], reverse=True)[:10]
        for course_type, count in sorted_types:
            self.stdout.write(f"{course_type}: {count:,} classes")

    def _drop_table(self):
        """Drop existing table."""
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS legacy_academic_classes CASCADE")
            self.stdout.write("Dropped existing legacy_academic_classes table")

    def _create_table(self):
        """Create legacy_academic_classes table based on EXACT SQL Server DDL."""
        create_sql = """
        CREATE TABLE IF NOT EXISTS legacy_academic_classes (
            termid VARCHAR(100),
            program FLOAT,
            major FLOAT,
            groupid VARCHAR(100),
            desgroupid CHAR(100),              -- CHAR field, preserves padding
            coursecode VARCHAR(100),
            classid VARCHAR(255),              -- Critical field for matching enrollments
            coursetitle VARCHAR(255),
            stnumber FLOAT,
            coursetype VARCHAR(100),
            schooltime VARCHAR(50),
            color VARCHAR(50),
            pos FLOAT,
            subject VARCHAR(150),
            exsubject VARCHAR(100),
            isshadow FLOAT,
            gidpos FLOAT,
            cidpos FLOAT,
            propos FLOAT,
            ipk INTEGER PRIMARY KEY,
            createddate TIMESTAMP,
            modifieddate TIMESTAMP,
            -- Normalized fields for pricing and analysis
            normalizedcourse VARCHAR(20),
            normalizedpart VARCHAR(20),
            normalizedsection VARCHAR(20),     -- CRITICAL for Reading Class pricing
            normalizedtod VARCHAR(10),
            oldcoursecode VARCHAR(20),
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Critical indexes for performance and analysis
        CREATE INDEX idx_legacy_ac_termid ON legacy_academic_classes(termid);
        CREATE INDEX idx_legacy_ac_classid ON legacy_academic_classes(classid);
        CREATE INDEX idx_legacy_ac_coursecode ON legacy_academic_classes(coursecode);
        CREATE INDEX idx_legacy_ac_program ON legacy_academic_classes(program);
        CREATE INDEX idx_legacy_ac_groupid ON legacy_academic_classes(groupid);
        CREATE INDEX idx_legacy_ac_normalized_section ON legacy_academic_classes(normalizedsection);
        CREATE INDEX idx_legacy_ac_normalized_course ON legacy_academic_classes(normalizedcourse);
        CREATE INDEX idx_legacy_ac_coursetype ON legacy_academic_classes(coursetype);

        -- Composite indexes for common queries
        CREATE INDEX idx_legacy_ac_term_program ON legacy_academic_classes(termid, program);
        CREATE INDEX idx_legacy_ac_pricing_analysis
            ON legacy_academic_classes(classid, normalizedsection, normalizedcourse)
            WHERE normalizedsection IS NOT NULL;
        """

        with connection.cursor() as cursor:
            cursor.execute(create_sql)
            self.stdout.write("Created legacy_academic_classes table with EXACT DDL specifications")

    def _insert_batch(self, batch_data):
        """Insert a batch of academic class records."""
        if not batch_data:
            return

        # Get column names from first record
        columns = list(batch_data[0].keys())
        placeholders = ", ".join(["%s"] * len(columns))
        columns_str = ", ".join(columns)

        insert_sql = f"""
        INSERT INTO legacy_academic_classes ({columns_str})
        VALUES ({placeholders})
        ON CONFLICT (ipk) DO NOTHING
        """

        with connection.cursor() as cursor:
            for record in batch_data:
                values = [record.get(col) for col in columns]
                cursor.execute(insert_sql, values)
