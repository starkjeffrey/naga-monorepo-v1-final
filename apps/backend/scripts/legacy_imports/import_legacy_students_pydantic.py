#!/usr/bin/env python3
"""
Import legacy students data using Pydantic validation.

Converts all_students_250811.csv to PostgreSQL legacy_students table
with comprehensive validation and error reporting.

Usage:
    # Drop existing table and import
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/legacy_imports/import_legacy_students_pydantic.py --drop-table

    # Import with validation only (dry run)
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/legacy_imports/import_legacy_students_pydantic.py --dry-run

    # Import specific file
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/legacy_imports/import_legacy_students_pydantic.py \
        --file data/legacy/all_students_250811.csv
"""

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

import django
from pydantic import BaseModel, Field, ValidationError, field_validator

# Setup Django
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.db import connection, transaction


class LegacyStudent(BaseModel):
    """Pydantic model for legacy students data based on original DDL.

    Handles all the complex field mappings and validation from the CSV.
    """

    # Basic fields
    ui: str | None = Field(None, max_length=100, description="User Interface field")
    pw: str | None = Field(None, max_length=10, description="Password field")
    id: str = Field(..., max_length=10, description="Student ID (Primary Key)")
    name: str | None = Field(None, max_length=100, description="Student name")
    kname: str | None = Field(None, max_length=100, description="Khmer name")

    # Personal information
    birth_date: datetime | None = Field(None, description="Birth date")
    birth_place: str | None = Field(None, max_length=50, description="Birth place")
    gender: str | None = Field(None, max_length=30, description="Gender")
    marital_status: str | None = Field(None, max_length=30, description="Marital status")
    nationality: str | None = Field(None, max_length=50, description="Nationality")

    # Contact information
    home_address: str | None = Field(None, max_length=250, description="Home address")
    home_phone: str | None = Field(None, max_length=50, description="Home phone")
    email: str | None = Field(None, max_length=50, description="Email address")
    mobile_phone: str | None = Field(None, max_length=50, description="Mobile phone")

    # Employment
    employment_place: str | None = Field(None, max_length=200, description="Employment place")
    position: str | None = Field(None, max_length=150, description="Position")

    # Family information
    father_name: str | None = Field(None, max_length=50, description="Father's name")
    spouse_name: str | None = Field(None, max_length=50, description="Spouse's name")

    # Emergency contact
    emg_contact_person: str | None = Field(None, max_length=50, description="Emergency contact person")
    relationship: str | None = Field(None, max_length=50, description="Relationship to emergency contact")
    contact_person_address: str | None = Field(None, max_length=250, description="Emergency contact address")
    contact_person_phone: str | None = Field(None, max_length=30, description="Emergency contact phone")

    # Educational background - High School
    high_school_program_school: str | None = Field(None, max_length=150, description="High school name")
    high_school_program_province: str | None = Field(None, max_length=100, description="High school province")
    high_school_program_year: int | None = Field(None, description="High school graduation year")
    high_school_program_diploma: str | None = Field(None, max_length=10, description="High school diploma")

    # Educational background - English
    english_program_school: str | None = Field(None, max_length=150, description="English program school")
    english_program_level: str | None = Field(None, max_length=50, description="English program level")
    english_program_year: int | None = Field(None, description="English program year")

    # Educational background - Less than 4-year
    less_than_four_year_program_school: str | None = Field(
        None, max_length=150, description="Less than 4-year program school"
    )
    less_than_four_year_program_year: str | None = Field(
        None, max_length=50, description="Less than 4-year program year"
    )

    # Educational background - 4-year
    four_year_program_school: str | None = Field(None, max_length=150, description="4-year program school")
    four_year_program_degree: str | None = Field(None, max_length=50, description="4-year program degree")
    four_year_program_major: str | None = Field(None, max_length=100, description="4-year program major")
    four_year_program_year: int | None = Field(None, description="4-year program year")

    # Educational background - Graduate
    graduate_program_school: str | None = Field(None, max_length=100, description="Graduate program school")
    graduate_program_degree: str | None = Field(None, max_length=50, description="Graduate program degree")
    graduate_program_major: str | None = Field(None, max_length=100, description="Graduate program major")
    graduate_program_year: int | None = Field(None, description="Graduate program year")

    # Educational background - Post Graduate
    post_graduate_program_school: str | None = Field(None, max_length=150, description="Post graduate program school")
    post_graduate_program_degree: str | None = Field(None, max_length=100, description="Post graduate program degree")
    post_graduate_program_major: str | None = Field(None, max_length=100, description="Post graduate program major")
    post_graduate_program_year: int | None = Field(None, description="Post graduate program year")

    # Current program information
    current_program: str | None = Field(None, max_length=50, description="Current program")
    sel_program: float | None = Field(None, description="Selected program ID")
    selected_program: str | None = Field(None, max_length=100, description="Selected program name")
    sel_major: float | None = Field(None, description="Selected major ID")
    selected_major: str | None = Field(None, max_length=100, description="Selected major name")
    sel_faculty: float | None = Field(None, description="Selected faculty ID")
    selected_faculty: str | None = Field(None, max_length=150, description="Selected faculty name")
    selected_degree_type: str | None = Field(None, max_length=100, description="Selected degree type")

    # Admission dates
    admission_date: datetime | None = Field(None, description="General admission date")
    admission_date_for_under: datetime | None = Field(None, description="Undergraduate admission date")
    admission_date_for_master: datetime | None = Field(None, description="Master admission date")
    admission_date_for_doctor: datetime | None = Field(None, description="Doctorate admission date")

    # Previous education details
    previous_degree: str | None = Field(None, max_length=200, description="Previous degree")
    previous_institution: str | None = Field(None, max_length=200, description="Previous institution")
    year_awarded: str | None = Field(None, max_length=10, description="Year degree awarded")
    other_credit_transfer_institution: str | None = Field(
        None, max_length=200, description="Other credit transfer institution"
    )
    degree_awarded: str | None = Field(None, max_length=150, description="Degree awarded")

    # Graduation information
    graduation_date: datetime | None = Field(None, description="General graduation date")
    ba_grad_date: datetime | None = Field(None, description="BA graduation date")
    ma_grad_date: datetime | None = Field(None, description="MA graduation date")

    # Terms and enrollment
    first_term: str | None = Field(None, max_length=50, description="First term")
    paid_term: str | None = Field(None, max_length=50, description="Paid term")

    # Batch information
    batch_id: str | None = Field(None, max_length=20, description="Batch ID")
    batch_id_for_under: str | None = Field(None, max_length=20, description="Undergraduate batch ID")
    batch_id_for_master: str | None = Field(None, max_length=20, description="Master batch ID")
    batch_id_for_doctor: str | None = Field(None, max_length=20, description="Doctorate batch ID")

    # Group information
    group_id: str | None = Field(None, max_length=20, description="Group ID")
    int_group_id: float | None = Field(None, description="Integer group ID")
    color: str | None = Field(None, max_length=20, description="Color coding")

    # Status fields
    admitted: int | None = Field(None, description="Admitted status")
    deleted: int | None = Field(None, description="Deleted status")
    status: str | None = Field(None, max_length=15, description="Current status")
    school_email: str | None = Field(None, max_length=100, description="School email")

    # Additional dates
    notes: str | None = Field(None, max_length=255, description="Notes")
    lastenroll: datetime | None = Field(None, description="Last enrollment date")
    firstenroll: datetime | None = Field(None, description="First enrollment date")
    firstenroll_lang: datetime | None = Field(None, description="First language enrollment date")
    firstenroll_ba: datetime | None = Field(None, description="First BA enrollment date")
    firstenroll_ma: datetime | None = Field(None, description="First MA enrollment date")

    # Transfer and additional info
    transfer: str | None = Field(None, max_length=25, description="Transfer status")
    kname2: str | None = Field(None, max_length=100, description="Alternative Khmer name")

    # System dates
    created_date: datetime | None = Field(None, description="Created date")
    modified_date: datetime | None = Field(None, description="Modified date")
    ipk: int | None = Field(None, description="Identity primary key")

    @field_validator(
        "birth_date",
        "admission_date",
        "admission_date_for_under",
        "admission_date_for_master",
        "admission_date_for_doctor",
        "graduation_date",
        "ba_grad_date",
        "ma_grad_date",
        "lastenroll",
        "firstenroll",
        "firstenroll_lang",
        "firstenroll_ba",
        "firstenroll_ma",
        "created_date",
        "modified_date",
        mode="before",
    )
    @classmethod
    def parse_datetime(cls, v):
        """Parse datetime fields, handling various formats and NULL values."""
        if v is None or v == "" or v == "NULL" or v == "null":
            return None

        if isinstance(v, str):
            # Handle common datetime formats
            for fmt in [
                "%Y-%m-%d %H:%M:%S.%f",  # 2009-04-07 00:00:00.000
                "%Y-%m-%d %H:%M:%S",  # 2009-04-07 00:00:00
                "%Y-%m-%d",  # 2009-04-07
                "%m/%d/%Y",  # 04/07/2009
                "%d/%m/%Y",  # 07/04/2009
            ]:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue

        # If it's already a datetime, return it
        if isinstance(v, datetime):
            return v

        # If we can't parse it, return None rather than failing
        return None

    @field_validator(
        "high_school_program_year",
        "english_program_year",
        "four_year_program_year",
        "graduate_program_year",
        "post_graduate_program_year",
        "admitted",
        "deleted",
        "ipk",
        mode="before",
    )
    @classmethod
    def parse_int(cls, v):
        """Parse integer fields, handling NULL and empty values."""
        if v is None or v == "" or v == "NULL" or v == "null":
            return None

        if isinstance(v, str):
            try:
                # Handle float strings (convert to int)
                return int(float(v))
            except (ValueError, TypeError):
                return None

        return v

    @field_validator("sel_program", "sel_major", "sel_faculty", "int_group_id", mode="before")
    @classmethod
    def parse_float(cls, v):
        """Parse float fields, handling NULL and empty values."""
        if v is None or v == "" or v == "NULL" or v == "null":
            return None

        if isinstance(v, str):
            try:
                return float(v)
            except (ValueError, TypeError):
                return None

        return v

    @field_validator(
        "ui",
        "pw",
        "id",
        "name",
        "kname",
        "birth_place",
        "gender",
        "marital_status",
        "nationality",
        "home_address",
        "home_phone",
        "email",
        "mobile_phone",
        "employment_place",
        "position",
        "father_name",
        "spouse_name",
        "emg_contact_person",
        "relationship",
        "contact_person_address",
        "contact_person_phone",
        "high_school_program_school",
        "high_school_program_province",
        "high_school_program_diploma",
        "english_program_school",
        "english_program_level",
        "less_than_four_year_program_school",
        "less_than_four_year_program_year",
        "four_year_program_school",
        "four_year_program_degree",
        "four_year_program_major",
        "graduate_program_school",
        "graduate_program_degree",
        "graduate_program_major",
        "post_graduate_program_school",
        "post_graduate_program_degree",
        "post_graduate_program_major",
        "current_program",
        "selected_program",
        "selected_major",
        "selected_faculty",
        "selected_degree_type",
        "previous_degree",
        "previous_institution",
        "year_awarded",
        "other_credit_transfer_institution",
        "degree_awarded",
        "first_term",
        "paid_term",
        "batch_id",
        "batch_id_for_under",
        "batch_id_for_master",
        "batch_id_for_doctor",
        "group_id",
        "color",
        "status",
        "school_email",
        "notes",
        "transfer",
        "kname2",
        mode="before",
    )
    @classmethod
    def parse_string(cls, v):
        """Parse string fields, handling NULL values and trimming whitespace."""
        if v is None or v == "NULL" or v == "null":
            return None

        if isinstance(v, str):
            v = v.strip()
            if v == "" or v == "NA" or v == "NULL":
                return None
            return v

        return str(v) if v is not None else None


def create_legacy_students_table(drop_existing: bool = False) -> None:
    """Create the legacy_students table with proper PostgreSQL DDL."""

    drop_sql = "DROP TABLE IF EXISTS legacy_students;" if drop_existing else ""

    create_sql = """
    CREATE TABLE legacy_students (
        ui VARCHAR(100),
        pw VARCHAR(10),
        id VARCHAR(10) NOT NULL PRIMARY KEY,
        name VARCHAR(100),
        kname VARCHAR(100),
        birth_date TIMESTAMP,
        birth_place VARCHAR(50),
        gender VARCHAR(30),
        marital_status VARCHAR(30),
        nationality VARCHAR(50),
        home_address VARCHAR(250),
        home_phone VARCHAR(50),
        email VARCHAR(50),
        mobile_phone VARCHAR(50),
        employment_place VARCHAR(200),
        position VARCHAR(150),
        father_name VARCHAR(50),
        spouse_name VARCHAR(50),
        emg_contact_person VARCHAR(50),
        relationship VARCHAR(50),
        contact_person_address VARCHAR(250),
        contact_person_phone VARCHAR(30),
        high_school_program_school VARCHAR(150),
        high_school_program_province VARCHAR(100),
        high_school_program_year INTEGER,
        high_school_program_diploma VARCHAR(10),
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
        post_graduate_program_degree VARCHAR(100),
        post_graduate_program_major VARCHAR(100),
        post_graduate_program_year INTEGER,
        current_program VARCHAR(50),
        sel_program FLOAT,
        selected_program VARCHAR(100),
        sel_major FLOAT,
        selected_major VARCHAR(100),
        sel_faculty FLOAT,
        selected_faculty VARCHAR(150),
        selected_degree_type VARCHAR(100),
        admission_date TIMESTAMP,
        admission_date_for_under TIMESTAMP,
        admission_date_for_master TIMESTAMP,
        admission_date_for_doctor TIMESTAMP,
        previous_degree VARCHAR(200),
        previous_institution VARCHAR(200),
        year_awarded VARCHAR(10),
        other_credit_transfer_institution VARCHAR(200),
        degree_awarded VARCHAR(150),
        graduation_date TIMESTAMP,
        first_term VARCHAR(50),
        paid_term VARCHAR(50),
        batch_id VARCHAR(20),
        batch_id_for_under VARCHAR(20),
        batch_id_for_master VARCHAR(20),
        batch_id_for_doctor VARCHAR(20),
        group_id VARCHAR(20),
        int_group_id FLOAT,
        color VARCHAR(20),
        admitted INTEGER,
        deleted INTEGER,
        status VARCHAR(15),
        school_email VARCHAR(100),
        ba_grad_date TIMESTAMP,
        ma_grad_date TIMESTAMP,
        notes VARCHAR(255),
        lastenroll TIMESTAMP,
        firstenroll TIMESTAMP,
        firstenroll_lang TIMESTAMP,
        firstenroll_ba TIMESTAMP,
        firstenroll_ma TIMESTAMP,
        transfer VARCHAR(25),
        kname2 VARCHAR(100),
        created_date TIMESTAMP,
        modified_date TIMESTAMP,
        ipk INTEGER,

        -- Audit fields
        csv_row_number INTEGER,
        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Create indexes for common queries
    CREATE INDEX idx_legacy_students_name ON legacy_students(name);
    CREATE INDEX idx_legacy_students_status ON legacy_students(status);
    CREATE INDEX idx_legacy_students_program ON legacy_students(current_program);
    CREATE INDEX idx_legacy_students_batch ON legacy_students(batch_id);
    CREATE INDEX idx_legacy_students_admission ON legacy_students(admission_date);
    """

    with connection.cursor() as cursor:
        if drop_sql:
            cursor.execute(drop_sql)
            print("✅ Dropped existing legacy_students table")

        cursor.execute(create_sql)
        print("✅ Created legacy_students table with proper schema")


def import_students_csv(csv_file_path: str, dry_run: bool = False, limit: int | None = None) -> dict:
    """Import students from CSV using Pydantic validation."""

    csv_file = Path(csv_file_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

    print(f"📄 Processing: {csv_file_path}")
    if dry_run:
        print("🔍 DRY RUN MODE - No data will be modified")
    if limit:
        print(f"🔢 Limiting to {limit} records")

    # Statistics tracking
    stats = {
        "total_rows": 0,
        "valid_rows": 0,
        "invalid_rows": 0,
        "inserted_rows": 0,
        "errors": [],
        "validation_errors": [],
    }

    # CSV field to model field mapping
    field_mapping = {
        "UI": "ui",
        "PW": "pw",
        "ID": "id",
        "Name": "name",
        "KName": "kname",
        "BirthDate": "birth_date",
        "BirthPlace": "birth_place",
        "Gender": "gender",
        "MaritalStatus": "marital_status",
        "Nationality": "nationality",
        "HomeAddress": "home_address",
        "HomePhone": "home_phone",
        "Email": "email",
        "MobilePhone": "mobile_phone",
        "EmploymentPlace": "employment_place",
        "Position": "position",
        "FatherName": "father_name",
        "SpouseName": "spouse_name",
        "Emg_ContactPerson": "emg_contact_person",
        "Relationship": "relationship",
        "ContactPersonAddress": "contact_person_address",
        "ContactPersonPhone": "contact_person_phone",
        "HighSchoolProgram_School": "high_school_program_school",
        "HighSchoolProgram_Province": "high_school_program_province",
        "HighSchoolProgram_Year": "high_school_program_year",
        "HighSchoolProgram_Diploma": "high_school_program_diploma",
        "EnglishProgram_School": "english_program_school",
        "EnglishProgram_Level": "english_program_level",
        "EnglishProgram_Year": "english_program_year",
        "LessThanFourYearProgram_School": "less_than_four_year_program_school",
        "LessThanFourYearProgram_Year": "less_than_four_year_program_year",
        "FourYearProgram_School": "four_year_program_school",
        "FourYearProgram_Degree": "four_year_program_degree",
        "FourYearProgram_Major": "four_year_program_major",
        "FourYearProgram_Year": "four_year_program_year",
        "GraduateProgram_School": "graduate_program_school",
        "GraduateProgram_Degree": "graduate_program_degree",
        "GraduateProgram_Major": "graduate_program_major",
        "GraduateProgram_Year": "graduate_program_year",
        "PostGraduateProgram_School": "post_graduate_program_school",
        "PostGraduateProgram_Degree": "post_graduate_program_degree",
        "PostGraduateProgram_Major": "post_graduate_program_major",
        "PostGraduateProgram_Year": "post_graduate_program_year",
        "CurrentProgram": "current_program",
        "SelProgram": "sel_program",
        "SelectedProgram": "selected_program",
        "SelMajor": "sel_major",
        "SelectedMajor": "selected_major",
        "SelFaculty": "sel_faculty",
        "SelectedFaculty": "selected_faculty",
        "SelectedDegreeType": "selected_degree_type",
        "AdmissionDate": "admission_date",
        "AdmissionDateForUnder": "admission_date_for_under",
        "AdmissionDateForMaster": "admission_date_for_master",
        "AdmissionDateForDoctor": "admission_date_for_doctor",
        "PreviousDegree": "previous_degree",
        "PreviousInstitution": "previous_institution",
        "YearAwarded": "year_awarded",
        "OtherCreditTransferInstitution": "other_credit_transfer_institution",
        "DegreeAwarded": "degree_awarded",
        "GraduationDate": "graduation_date",
        "FirstTerm": "first_term",
        "PaidTerm": "paid_term",
        "BatchID": "batch_id",
        "BatchIDForUnder": "batch_id_for_under",
        "BatchIDForMaster": "batch_id_for_master",
        "BatchIDForDoctor": "batch_id_for_doctor",
        "GroupID": "group_id",
        "intGroupID": "int_group_id",
        "Color": "color",
        "Admitted": "admitted",
        "Deleted": "deleted",
        "Status": "status",
        "SchoolEmail": "school_email",
        "BAGradDate": "ba_grad_date",
        "MAGradDate": "ma_grad_date",
        "Notes": "notes",
        "Lastenroll": "lastenroll",
        "Firstenroll": "firstenroll",
        "Firstenroll_Lang": "firstenroll_lang",
        "Firstenroll_BA": "firstenroll_ba",
        "Firstenroll_MA": "firstenroll_ma",
        "Transfer": "transfer",
        "KName2": "kname2",
        "CreatedDate": "created_date",
        "ModifiedDate": "modified_date",
        "IPK": "ipk",
    }

    # Process CSV file
    with open(csv_file, encoding="utf-8") as file:
        reader = csv.DictReader(file)

        if not dry_run:
            # Use transaction for data consistency
            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):
                    stats["total_rows"] += 1

                    if limit and stats["total_rows"] > limit:
                        break

                    try:
                        # Map CSV fields to model fields
                        mapped_data = {}
                        for csv_field, model_field in field_mapping.items():
                            if csv_field in row:
                                mapped_data[model_field] = row[csv_field]

                        # Add row number for audit
                        mapped_data["csv_row_number"] = row_num - 1

                        # Validate with Pydantic
                        validated_student = LegacyStudent(**mapped_data)
                        stats["valid_rows"] += 1

                        # Insert into database
                        insert_student_record(validated_student)
                        stats["inserted_rows"] += 1

                        if row_num % 1000 == 0:
                            print(f"⏳ Processed {row_num} rows...")

                    except ValidationError as e:
                        stats["invalid_rows"] += 1
                        error_msg = f"Row {row_num} (ID: {row.get('ID', 'N/A')}): Validation error"
                        stats["validation_errors"].append(
                            {"row": row_num, "id": row.get("ID", "N/A"), "error": str(e)}
                        )

                        # Log first 10 validation errors
                        if len(stats["validation_errors"]) <= 10:
                            print(f"❌ {error_msg}: {e}")

                    except Exception as e:
                        stats["invalid_rows"] += 1
                        error_msg = f"Row {row_num} (ID: {row.get('ID', 'N/A')}): {e!s}"
                        stats["errors"].append(error_msg)

                        # Log first 10 general errors
                        if len(stats["errors"]) <= 10:
                            print(f"❌ {error_msg}")

                        # Stop if too many errors
                        if len(stats["errors"]) > 50:
                            print(f"❌ Too many errors ({len(stats['errors'])}), stopping import")
                            break

        else:
            # Dry run - just validate
            for row_num, row in enumerate(reader, start=2):
                stats["total_rows"] += 1

                if limit and stats["total_rows"] > limit:
                    break

                try:
                    # Map and validate
                    mapped_data = {}
                    for csv_field, model_field in field_mapping.items():
                        if csv_field in row:
                            mapped_data[model_field] = row[csv_field]

                    LegacyStudent(**mapped_data)
                    stats["valid_rows"] += 1

                except ValidationError as e:
                    stats["invalid_rows"] += 1
                    if len(stats["validation_errors"]) < 10:
                        print(f"❌ Row {row_num} validation error: {e}")
                    stats["validation_errors"].append({"row": row_num, "id": row.get("ID", "N/A"), "error": str(e)})

                except Exception as e:
                    stats["invalid_rows"] += 1
                    if len(stats["errors"]) < 10:
                        print(f"❌ Row {row_num} error: {e!s}")
                    stats["errors"].append(f"Row {row_num}: {e!s}")

                if row_num % 1000 == 0:
                    print(f"⏳ Validated {row_num} rows...")

    return stats


def insert_student_record(student: LegacyStudent) -> None:
    """Insert a validated student record into the database."""

    insert_sql = """
    INSERT INTO legacy_students (
        ui, pw, id, name, kname, birth_date, birth_place, gender, marital_status,
        nationality, home_address, home_phone, email, mobile_phone, employment_place,
        position, father_name, spouse_name, emg_contact_person, relationship,
        contact_person_address, contact_person_phone, high_school_program_school,
        high_school_program_province, high_school_program_year, high_school_program_diploma,
        english_program_school, english_program_level, english_program_year,
        less_than_four_year_program_school, less_than_four_year_program_year,
        four_year_program_school, four_year_program_degree, four_year_program_major,
        four_year_program_year, graduate_program_school, graduate_program_degree,
        graduate_program_major, graduate_program_year, post_graduate_program_school,
        post_graduate_program_degree, post_graduate_program_major, post_graduate_program_year,
        current_program, sel_program, selected_program, sel_major, selected_major,
        sel_faculty, selected_faculty, selected_degree_type, admission_date,
        admission_date_for_under, admission_date_for_master, admission_date_for_doctor,
        previous_degree, previous_institution, year_awarded, other_credit_transfer_institution,
        degree_awarded, graduation_date, first_term, paid_term, batch_id,
        batch_id_for_under, batch_id_for_master, batch_id_for_doctor, group_id,
        int_group_id, color, admitted, deleted, status, school_email, ba_grad_date,
        ma_grad_date, notes, lastenroll, firstenroll, firstenroll_lang, firstenroll_ba,
        firstenroll_ma, transfer, kname2, created_date, modified_date, ipk, csv_row_number
    ) VALUES (
        %(ui)s, %(pw)s, %(id)s, %(name)s, %(kname)s, %(birth_date)s, %(birth_place)s,
        %(gender)s, %(marital_status)s, %(nationality)s, %(home_address)s, %(home_phone)s,
        %(email)s, %(mobile_phone)s, %(employment_place)s, %(position)s, %(father_name)s,
        %(spouse_name)s, %(emg_contact_person)s, %(relationship)s, %(contact_person_address)s,
        %(contact_person_phone)s, %(high_school_program_school)s, %(high_school_program_province)s,
        %(high_school_program_year)s, %(high_school_program_diploma)s, %(english_program_school)s,
        %(english_program_level)s, %(english_program_year)s, %(less_than_four_year_program_school)s,
        %(less_than_four_year_program_year)s, %(four_year_program_school)s, %(four_year_program_degree)s,
        %(four_year_program_major)s, %(four_year_program_year)s, %(graduate_program_school)s,
        %(graduate_program_degree)s, %(graduate_program_major)s, %(graduate_program_year)s,
        %(post_graduate_program_school)s, %(post_graduate_program_degree)s, %(post_graduate_program_major)s,
        %(post_graduate_program_year)s, %(current_program)s, %(sel_program)s, %(selected_program)s,
        %(sel_major)s, %(selected_major)s, %(sel_faculty)s, %(selected_faculty)s,
        %(selected_degree_type)s, %(admission_date)s, %(admission_date_for_under)s,
        %(admission_date_for_master)s, %(admission_date_for_doctor)s, %(previous_degree)s,
        %(previous_institution)s, %(year_awarded)s, %(other_credit_transfer_institution)s,
        %(degree_awarded)s, %(graduation_date)s, %(first_term)s, %(paid_term)s, %(batch_id)s,
        %(batch_id_for_under)s, %(batch_id_for_master)s, %(batch_id_for_doctor)s, %(group_id)s,
        %(int_group_id)s, %(color)s, %(admitted)s, %(deleted)s, %(status)s, %(school_email)s,
        %(ba_grad_date)s, %(ma_grad_date)s, %(notes)s, %(lastenroll)s, %(firstenroll)s,
        %(firstenroll_lang)s, %(firstenroll_ba)s, %(firstenroll_ma)s, %(transfer)s,
        %(kname2)s, %(created_date)s, %(modified_date)s, %(ipk)s, %(csv_row_number)s
    )
    """

    # Convert Pydantic model to dict for database insertion
    data = student.model_dump()

    with connection.cursor() as cursor:
        cursor.execute(insert_sql, data)


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description="Import legacy students with Pydantic validation")
    parser.add_argument(
        "--file",
        default="data/legacy/all_students_250811.csv",
        help="Path to CSV file (default: data/legacy/all_students_250811.csv)",
    )
    parser.add_argument("--drop-table", action="store_true", help="Drop existing table before import")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, do not import data")
    parser.add_argument("--limit", type=int, help="Limit number of records to process (for testing)")

    args = parser.parse_args()

    print("🎓 Legacy Students Import with Pydantic Validation")
    print("=" * 60)

    try:
        # Create table
        if not args.dry_run:
            create_legacy_students_table(drop_existing=args.drop_table)

        # Import data
        stats = import_students_csv(args.file, dry_run=args.dry_run, limit=args.limit)

        # Print results
        print("\n📊 IMPORT SUMMARY")
        print("=" * 60)
        print(f"📄 Total rows processed: {stats['total_rows']:,}")
        print(f"✅ Valid rows: {stats['valid_rows']:,}")
        print(f"❌ Invalid rows: {stats['invalid_rows']:,}")

        if not args.dry_run:
            print(f"💾 Successfully inserted: {stats['inserted_rows']:,}")
        else:
            print("🔍 DRY RUN - No data was inserted")

        if stats["validation_errors"]:
            print(f"⚠️  Validation errors: {len(stats['validation_errors'])}")

        if stats["errors"]:
            print(f"🚨 General errors: {len(stats['errors'])}")

        if stats["invalid_rows"] == 0:
            print("🎉 All records processed successfully!")

        print("=" * 60)

    except Exception as e:
        print(f"❌ Fatal error: {e!s}")
        sys.exit(1)


if __name__ == "__main__":
    main()
