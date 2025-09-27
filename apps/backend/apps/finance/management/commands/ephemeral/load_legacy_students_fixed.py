"""Load legacy students data with Pydantic validation based on SQL Server DDL.

PRODUCTION LOADER - Validated data import with EXACT DDL field specifications
"""

import csv
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection
from pydantic import BaseModel, Field, field_validator


class LegacyStudent(BaseModel):
    """Pydantic model for legacy student data validation based on SQL Server DDL with EXACT field lengths."""

    # User credentials - FIXED LENGTHS
    ui: str | None = Field(None, max_length=200)  # FIXED: was 100, now 200
    pw: str | None = Field(None, max_length=20)  # FIXED: was 10, now 20

    # Primary key - student ID (5 digits, left padded with zeros)
    id: str = Field(..., max_length=10)

    # Basic info - FIXED LENGTHS
    name: str | None = Field(None, max_length=150)  # FIXED: was 100, now 150
    kname: str | None = Field(None, max_length=150)  # FIXED: was 100, now 150
    birthdate: datetime | None = None
    birthplace: str | None = Field(None, max_length=100)  # FIXED: was 50, now 100
    gender: str | None = Field(None, max_length=10)  # FIXED: was 30, now 10
    marital_status: str | None = Field(None, max_length=50)  # FIXED: was 30, now 50
    nationality: str | None = Field(None, max_length=50)

    # Contact info - FIXED LENGTHS
    home_address: str | None = Field(None, max_length=500)  # FIXED: was 250, now 500
    home_phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=100)  # FIXED: was 50, now 100
    mobile_phone: str | None = Field(None, max_length=50)

    # Employment
    employment_place: str | None = Field(None, max_length=200)
    position: str | None = Field(None, max_length=150)

    # Family/Emergency contact - FIXED LENGTHS
    father_name: str | None = Field(None, max_length=100)  # FIXED: was 50, now 100
    spouse_name: str | None = Field(None, max_length=100)  # FIXED: was 50, now 100
    emg_contact_person: str | None = Field(None, max_length=100)  # FIXED: was 50, now 100
    relationship: str | None = Field(None, max_length=50)
    contact_person_address: str | None = Field(None, max_length=500)  # FIXED: was 250, now 500
    contact_person_phone: str | None = Field(None, max_length=50)  # FIXED: was 30, now 50

    # Education history - FIXED LENGTHS
    high_school_program_school: str | None = Field(None, max_length=150)
    high_school_program_province: str | None = Field(None, max_length=150)  # FIXED: was 100, now 150
    high_school_program_year: int | None = None
    high_school_program_diploma: str | None = Field(None, max_length=100)  # FIXED: was 10, now 100

    english_program_school: str | None = Field(None, max_length=150)
    english_program_level: str | None = Field(None, max_length=50)
    english_program_year: int | None = None

    less_than_four_year_program_school: str | None = Field(None, max_length=150)
    less_than_four_year_program_year: str | None = Field(None, max_length=50)

    four_year_program_school: str | None = Field(None, max_length=150)
    four_year_program_degree: str | None = Field(None, max_length=50)
    four_year_program_major: str | None = Field(None, max_length=100)
    four_year_program_year: int | None = None

    graduate_program_school: str | None = Field(None, max_length=100)
    graduate_program_degree: str | None = Field(None, max_length=50)
    graduate_program_major: str | None = Field(None, max_length=100)
    graduate_program_year: int | None = None

    # FIXED LENGTHS
    post_graduate_program_school: str | None = Field(None, max_length=150)
    post_graduate_program_degree: str | None = Field(None, max_length=50)  # FIXED: was 100, now 50
    post_graduate_program_major: str | None = Field(None, max_length=100)
    post_graduate_program_year: int | None = None

    # Current program info - FIXED DATA TYPES
    current_program: str | None = Field(None, max_length=50)
    sel_program: float | None = None  # FIXED: was Decimal, now float
    selected_program: str | None = Field(None, max_length=100)
    sel_major: float | None = None  # FIXED: was Decimal, now float
    selected_major: str | None = Field(None, max_length=100)
    sel_faculty: float | None = None  # FIXED: was Decimal, now float
    selected_faculty: str | None = Field(None, max_length=150)
    selected_degree_type: str | None = Field(None, max_length=100)

    # Admission dates
    admission_date: datetime | None = None
    admission_date_for_under: datetime | None = None
    admission_date_for_master: datetime | None = None
    admission_date_for_doctor: datetime | None = None

    # Previous education - FIXED LENGTHS
    previous_degree: str | None = Field(None, max_length=200)
    previous_institution: str | None = Field(None, max_length=200)
    year_awarded: str | None = Field(None, max_length=20)  # FIXED: was 10, now 20
    other_credit_transfer_institution: str | None = Field(None, max_length=200)

    # Graduation info - FIXED LENGTHS
    degree_awarded: str | None = Field(None, max_length=200)  # FIXED: was 150, now 200
    graduation_date: datetime | None = None

    # Term info
    first_term: str | None = Field(None, max_length=50)
    paid_term: str | None = Field(None, max_length=50)

    # Batch/Group info
    batch_id: str | None = Field(None, max_length=20)
    batch_id_for_under: str | None = Field(None, max_length=20)
    batch_id_for_master: str | None = Field(None, max_length=20)
    batch_id_for_doctor: str | None = Field(None, max_length=20)
    group_id: str | None = Field(None, max_length=20)
    int_group_id: float | None = None  # FIXED: was Decimal, now float

    # Status fields
    color: str | None = Field(None, max_length=20)
    admitted: int | None = None
    deleted: int | None = None
    status: str | None = Field(None, max_length=15)

    # Additional fields
    school_email: str | None = Field(None, max_length=100)
    ba_grad_date: datetime | None = None
    ma_grad_date: datetime | None = None
    notes: str | None = Field(None, max_length=255)

    # Enrollment dates
    last_enroll: datetime | None = None
    first_enroll: datetime | None = None
    first_enroll_lang: datetime | None = None
    first_enroll_ba: datetime | None = None
    first_enroll_ma: datetime | None = None

    # Other - FIXED LENGTH
    transfer: str | None = Field(None, max_length=100)  # FIXED: was 25, now 100
    kname2: str | None = Field(None, max_length=100)

    # Audit fields
    created_date: datetime | None = None
    modified_date: datetime | None = None
    ipk: int | None = None

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
    """PRODUCTION LOADER - Load legacy students data with EXACT DDL validation."""

    help = "PRODUCTION: Load legacy students data from CSV with exact DDL field validation"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file", type=str, default="data/legacy/all_students_250802.csv", help="Path to students CSV file"
        )
        parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for inserts")
        parser.add_argument("--drop-existing", action="store_true", help="Drop existing table before loading")

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        batch_size = options["batch_size"]

        if not file_path.exists():
            self.stdout.write(self.style.ERROR(f"File not found: {file_path}"))
            return

        self.stdout.write(self.style.WARNING("=== PRODUCTION DATA LOADER (FIXED DDL) ==="))
        self.stdout.write("Loading students with exact SQL Server DDL specifications")

        # Create table
        if options["drop_existing"]:
            self._drop_table()
        self._create_table()

        # Load data
        success_count = 0
        error_count = 0
        batch_data = []
        error_details = []

        self.stdout.write(f"Loading students from {file_path}")

        with open(file_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):
                try:
                    # Parse dates
                    for date_field in [
                        "BirthDate",
                        "AdmissionDate",
                        "AdmissionDateForUnder",
                        "AdmissionDateForMaster",
                        "AdmissionDateForDoctor",
                        "GraduationDate",
                        "BAGradDate",
                        "MAGradDate",
                        "Lastenroll",
                        "Firstenroll",
                        "Firstenroll_Lang",
                        "Firstenroll_BA",
                        "Firstenroll_MA",
                        "CreatedDate",
                        "ModifiedDate",
                    ]:
                        if row.get(date_field) and row[date_field] not in ["NULL", ""]:
                            try:
                                # Handle datetime format
                                row[date_field] = datetime.strptime(row[date_field].split(".")[0], "%Y-%m-%d %H:%M:%S")
                            except ValueError:
                                row[date_field] = None
                        else:
                            row[date_field] = None

                    # Create Pydantic model for validation
                    student_data = {key.lower().replace(" ", "_"): value for key, value in row.items()}

                    # Handle special field mappings
                    student_data["marital_status"] = student_data.get("maritalstatus")
                    student_data["emg_contact_person"] = student_data.get("emg_contactperson")
                    student_data["contact_person_address"] = student_data.get("contactpersonaddress")
                    student_data["contact_person_phone"] = student_data.get("contactpersonphone")

                    # Validate with Pydantic
                    student = LegacyStudent(**student_data)

                    # Add to batch
                    batch_data.append(student.model_dump())

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
                        "id": row.get("ID", "N/A"),
                        "name": row.get("name", "N/A"),
                    }
                    error_details.append(error_detail)

                    if error_count <= 10:
                        self.stdout.write(self.style.ERROR(f"Row {row_num}: {e!s} - ID: {row.get('ID', 'N/A')}"))
                    continue

            # Insert remaining batch
            if batch_data:
                self._insert_batch(batch_data)
                success_count += len(batch_data)

        self.stdout.write(self.style.SUCCESS(f"Completed: {success_count:,} records loaded, {error_count:,} errors"))

        # Write error log if needed
        if error_count > 0:
            error_log_path = Path("students_errors.log")
            with open(error_log_path, "w") as f:
                f.write(f"Total errors: {error_count}\n\n")
                for error in error_details[:1000]:  # First 1000 errors
                    f.write(f"Row {error['row']}: {error['error']}\n")
                    f.write(f"  ID: {error['id']}, Name: {error['name']}\n\n")
            self.stdout.write(f"Error details written to {error_log_path}")

    def _drop_table(self):
        """Drop existing table."""
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS legacy_students CASCADE")
            self.stdout.write("Dropped existing legacy_students table")

    def _create_table(self):
        """Create legacy_students table based on EXACT SQL Server DDL."""
        create_sql = """
        CREATE TABLE IF NOT EXISTS legacy_students (
            ui VARCHAR(200),                   -- FIXED: was 100, now 200
            pw VARCHAR(20),                    -- FIXED: was 10, now 20
            id VARCHAR(10) PRIMARY KEY,
            name VARCHAR(150),                 -- FIXED: was 100, now 150
            kname VARCHAR(150),                -- FIXED: was 100, now 150
            birthdate TIMESTAMP,
            birthplace VARCHAR(100),           -- FIXED: was 50, now 100
            gender VARCHAR(10),                -- FIXED: was 30, now 10
            marital_status VARCHAR(50),        -- FIXED: was 30, now 50
            nationality VARCHAR(50),
            home_address VARCHAR(500),         -- FIXED: was 250, now 500
            home_phone VARCHAR(50),
            email VARCHAR(100),                -- FIXED: was 50, now 100
            mobile_phone VARCHAR(50),
            employment_place VARCHAR(200),
            position VARCHAR(150),
            father_name VARCHAR(100),          -- FIXED: was 50, now 100
            spouse_name VARCHAR(100),          -- FIXED: was 50, now 100
            emg_contact_person VARCHAR(100),   -- FIXED: was 50, now 100
            relationship VARCHAR(50),
            contact_person_address VARCHAR(500), -- FIXED: was 250, now 500
            contact_person_phone VARCHAR(50),  -- FIXED: was 30, now 50
            high_school_program_school VARCHAR(150),
            high_school_program_province VARCHAR(150), -- FIXED: was 100, now 150
            high_school_program_year INTEGER,
            high_school_program_diploma VARCHAR(100), -- FIXED: was 10, now 100
            english_program_school VARCHAR(150),
            english_program_level VARCHAR(50),
            english_program_year INTEGER,
            less_than_four_year_program_school VARCHAR(150),
            less_than_four_year_program_year VARCHAR(50),
            four_year_program_school VARCHAR(150),
            four_year_program_degree VARCHAR(50),
            four_year_program_major VARCHAR(100),
            four_year_program_year INTEGER,
            graduate_program_school VARCHAR(100),
            graduate_program_degree VARCHAR(50),
            graduate_program_major VARCHAR(100),
            graduate_program_year INTEGER,
            post_graduate_program_school VARCHAR(150),
            post_graduate_program_degree VARCHAR(50), -- FIXED: was 100, now 50
            post_graduate_program_major VARCHAR(100),
            post_graduate_program_year INTEGER,
            current_program VARCHAR(50),
            sel_program FLOAT,                 -- FIXED: was DECIMAL, now FLOAT
            selected_program VARCHAR(100),
            sel_major FLOAT,                   -- FIXED: was DECIMAL, now FLOAT
            selected_major VARCHAR(100),
            sel_faculty FLOAT,                 -- FIXED: was DECIMAL, now FLOAT
            selected_faculty VARCHAR(150),
            selected_degree_type VARCHAR(100),
            admission_date TIMESTAMP,
            admission_date_for_under TIMESTAMP,
            admission_date_for_master TIMESTAMP,
            admission_date_for_doctor TIMESTAMP,
            previous_degree VARCHAR(200),
            previous_institution VARCHAR(200),
            year_awarded VARCHAR(20),          -- FIXED: was 10, now 20
            other_credit_transfer_institution VARCHAR(200),
            degree_awarded VARCHAR(200),       -- FIXED: was 150, now 200
            graduation_date TIMESTAMP,
            first_term VARCHAR(50),
            paid_term VARCHAR(50),
            batch_id VARCHAR(20),
            batch_id_for_under VARCHAR(20),
            batch_id_for_master VARCHAR(20),
            batch_id_for_doctor VARCHAR(20),
            group_id VARCHAR(20),
            int_group_id FLOAT,                -- FIXED: was DECIMAL, now FLOAT
            color VARCHAR(20),
            admitted INTEGER,
            deleted INTEGER,
            status VARCHAR(15),
            school_email VARCHAR(100),
            ba_grad_date TIMESTAMP,
            ma_grad_date TIMESTAMP,
            notes VARCHAR(255),
            last_enroll TIMESTAMP,
            first_enroll TIMESTAMP,
            first_enroll_lang TIMESTAMP,
            first_enroll_ba TIMESTAMP,
            first_enroll_ma TIMESTAMP,
            transfer VARCHAR(100),             -- FIXED: was 25, now 100
            kname2 VARCHAR(100),
            created_date TIMESTAMP,
            modified_date TIMESTAMP,
            ipk INTEGER,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX idx_legacy_students_name ON legacy_students(name);
        CREATE INDEX idx_legacy_students_email ON legacy_students(email);
        CREATE INDEX idx_legacy_students_status ON legacy_students(status);
        CREATE INDEX idx_legacy_students_deleted ON legacy_students(deleted);
        CREATE INDEX idx_legacy_students_ipk ON legacy_students(ipk);
        """

        with connection.cursor() as cursor:
            cursor.execute(create_sql)
            self.stdout.write("Created legacy_students table with EXACT DDL specifications")

    def _insert_batch(self, batch_data):
        """Insert a batch of student records."""
        if not batch_data:
            return

        # Get column names from first record
        columns = list(batch_data[0].keys())
        placeholders = ", ".join(["%s"] * len(columns))
        columns_str = ", ".join(columns)

        insert_sql = f"""
        INSERT INTO legacy_students ({columns_str})
        VALUES ({placeholders})
        ON CONFLICT (id) DO NOTHING
        """

        with connection.cursor() as cursor:
            for record in batch_data:
                values = [record.get(col) for col in columns]
                cursor.execute(insert_sql, values)
