#!/usr/bin/env python3
"""
Import legacy students data with proper validation rules:
- REJECT: Missing ID or Name
- DEFAULT: Missing birthdate -> 1900-01-01
- IGNORE: Missing emails (optional field)

This implements the actual business rules for data quality.
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


class LegacyStudentValidated(BaseModel):
    """Pydantic model with proper validation rules for legacy students."""

    # REQUIRED FIELDS - will reject if missing
    id: str = Field(..., min_length=1, description="Student ID (REQUIRED)")
    name: str = Field(..., min_length=1, description="Student name (REQUIRED)")

    # Optional fields with defaults
    ui: str | None = Field(None, max_length=100)
    pw: str | None = Field(None, max_length=10)
    kname: str | None = Field(None, max_length=100)

    # Birth date with default if missing
    birth_date: datetime = Field(default=datetime(1900, 1, 1), description="Birth date (defaults to 1900-01-01)")
    birth_place: str | None = Field(None, max_length=50)
    gender: str | None = Field(None, max_length=30)
    marital_status: str | None = Field(None, max_length=30)
    nationality: str | None = Field(None, max_length=50)

    # Contact - email is optional
    home_address: str | None = Field(None, max_length=250)
    home_phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=50)  # Optional, no validation
    mobile_phone: str | None = Field(None, max_length=50)

    # Employment
    employment_place: str | None = Field(None, max_length=200)
    position: str | None = Field(None, max_length=150)

    # Family
    father_name: str | None = Field(None, max_length=50)
    spouse_name: str | None = Field(None, max_length=50)

    # Emergency contact
    emg_contact_person: str | None = Field(None, max_length=50)
    relationship: str | None = Field(None, max_length=50)
    contact_person_address: str | None = Field(None, max_length=250)
    contact_person_phone: str | None = Field(None, max_length=30)

    # Education fields - all optional
    high_school_program_school: str | None = Field(None, max_length=150)
    high_school_program_province: str | None = Field(None, max_length=100)
    high_school_program_year: int | None = Field(None)
    high_school_program_diploma: str | None = Field(None, max_length=10)

    english_program_school: str | None = Field(None, max_length=150)
    english_program_level: str | None = Field(None, max_length=50)
    english_program_year: int | None = Field(None)

    # Program fields
    current_program: str | None = Field(None, max_length=50)
    selected_program: str | None = Field(None, max_length=100)
    selected_major: str | None = Field(None, max_length=100)
    selected_faculty: str | None = Field(None, max_length=150)

    # Dates with defaults
    admission_date: datetime | None = Field(None)
    graduation_date: datetime | None = Field(None)
    ba_grad_date: datetime | None = Field(None)
    ma_grad_date: datetime | None = Field(None)

    # System fields
    status: str | None = Field(None, max_length=15)
    batch_id: str | None = Field(None, max_length=20)
    first_term: str | None = Field(None, max_length=50)
    ipk: int | None = Field(None)

    # Audit fields
    csv_row_number: int | None = Field(None)
    imported_at: datetime = Field(default_factory=datetime.now)

    @field_validator("id", "name")
    @classmethod
    def validate_required_fields(cls, v, info):
        """Validate required fields - reject if missing."""
        field_name = info.field_name
        if not v or v.strip() in ("", "NULL", "null"):
            raise ValueError(f"{field_name} is required and cannot be empty")
        return v.strip()

    @field_validator("birth_date", "admission_date", "graduation_date", "ba_grad_date", "ma_grad_date", mode="before")
    @classmethod
    def parse_datetime_with_default(cls, v, info):
        """Parse datetime fields with proper defaults."""
        field_name = info.field_name

        # For birth_date, use default if missing
        if field_name == "birth_date":
            if not v or v in ("", "NULL", "null"):
                return datetime(1900, 1, 1)
        else:
            # For other dates, allow None
            if not v or v in ("", "NULL", "null"):
                return None

        if isinstance(v, str):
            for fmt in [
                "%Y-%m-%d %H:%M:%S.%f",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
                "%m/%d/%Y",
                "%d/%m/%Y",
            ]:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue

        if isinstance(v, datetime):
            return v

        # If we can't parse it, use default for birth_date, None for others
        if field_name == "birth_date":
            return datetime(1900, 1, 1)
        return None

    @field_validator("high_school_program_year", "english_program_year", "ipk", mode="before")
    @classmethod
    def parse_int_optional(cls, v):
        """Parse integer fields, allowing None."""
        if not v or v in ("", "NULL", "null"):
            return None
        if isinstance(v, str):
            try:
                return int(float(v))
            except (ValueError, TypeError):
                return None
        return v

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, v):
        """Clean email field - drop if malformed, optional field."""
        if not v or v in ("", "NULL", "null", "NA"):
            return None

        v = v.strip()
        if not v:
            return None

        # Basic email validation - must contain @ and have reasonable format
        if "@" not in v or "." not in v.split("@")[-1]:
            return None  # Drop malformed email, keep the record

        # Additional checks for common malformed patterns
        if v.count("@") != 1:  # Must have exactly one @
            return None

        local, domain = v.split("@")
        if not local or not domain or len(domain) < 3:  # Basic structure check
            return None

        return v

    # Clean all other string fields
    @field_validator(
        "ui",
        "pw",
        "kname",
        "birth_place",
        "gender",
        "marital_status",
        "nationality",
        "home_address",
        "home_phone",
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
        "current_program",
        "selected_program",
        "selected_major",
        "selected_faculty",
        "status",
        "batch_id",
        "first_term",
        mode="before",
    )
    @classmethod
    def clean_string_fields(cls, v):
        """Clean string fields, converting NULL to None."""
        if not v or v in ("NULL", "null", "NA"):
            return None
        if isinstance(v, str):
            v = v.strip()
            return v if v else None
        return str(v) if v is not None else None


def create_validated_students_table(drop_existing: bool = False):
    """Create the legacy_students_validated table."""

    if drop_existing:
        drop_sql = "DROP TABLE IF EXISTS legacy_students_validated;"
        with connection.cursor() as cursor:
            cursor.execute(drop_sql)
            print("✅ Dropped existing legacy_students_validated table")

    create_sql = """
    CREATE TABLE legacy_students_validated (
        id VARCHAR(10) NOT NULL PRIMARY KEY,
        name VARCHAR(100) NOT NULL,
        ui VARCHAR(100),
        pw VARCHAR(10),
        kname VARCHAR(100),
        birth_date TIMESTAMP NOT NULL DEFAULT '1900-01-01'::timestamp,
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
        current_program VARCHAR(50),
        selected_program VARCHAR(100),
        selected_major VARCHAR(100),
        selected_faculty VARCHAR(150),
        admission_date TIMESTAMP,
        graduation_date TIMESTAMP,
        ba_grad_date TIMESTAMP,
        ma_grad_date TIMESTAMP,
        status VARCHAR(15),
        batch_id VARCHAR(20),
        first_term VARCHAR(50),
        ipk INTEGER,
        csv_row_number INTEGER,
        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX idx_validated_students_name ON legacy_students_validated(name);
    CREATE INDEX idx_validated_students_status ON legacy_students_validated(status);
    CREATE INDEX idx_validated_students_program ON legacy_students_validated(current_program);
    CREATE INDEX idx_validated_students_batch ON legacy_students_validated(batch_id);
    """

    with connection.cursor() as cursor:
        cursor.execute(create_sql)
        print("✅ Created legacy_students_validated table with proper validation schema")


def import_and_validate_students(csv_file_path: str, dry_run: bool = False) -> dict:
    """Import students with validation, rejection, and defaults."""

    csv_file = Path(csv_file_path)
    if not csv_file.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_file_path}")

    print(f"📄 Processing: {csv_file_path}")
    if dry_run:
        print("🔍 DRY RUN MODE - No data will be modified")

    stats = {
        "total_rows": 0,
        "valid_rows": 0,
        "rejected_rows": 0,
        "inserted_rows": 0,
        "rejections": [],
        "validation_errors": [],
    }

    # Field mapping from CSV to model
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
        "CurrentProgram": "current_program",
        "SelectedProgram": "selected_program",
        "SelectedMajor": "selected_major",
        "SelectedFaculty": "selected_faculty",
        "AdmissionDate": "admission_date",
        "GraduationDate": "graduation_date",
        "BAGradDate": "ba_grad_date",
        "MAGradDate": "ma_grad_date",
        "Status": "status",
        "BatchID": "batch_id",
        "FirstTerm": "first_term",
        "IPK": "ipk",
    }

    with open(csv_file, encoding="utf-8") as file:
        reader = csv.DictReader(file)

        if not dry_run:
            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):
                    stats["total_rows"] += 1

                    try:
                        # Map CSV fields to model fields
                        mapped_data = {}
                        for csv_field, model_field in field_mapping.items():
                            if csv_field in row:
                                mapped_data[model_field] = row[csv_field]

                        # Add row number
                        mapped_data["csv_row_number"] = row_num - 1

                        # Validate with Pydantic
                        validated_student = LegacyStudentValidated(**mapped_data)
                        stats["valid_rows"] += 1

                        # Insert into database
                        insert_validated_student(validated_student)
                        stats["inserted_rows"] += 1

                        if row_num % 1000 == 0:
                            print(f"⏳ Processed {row_num} rows...")

                    except ValidationError as e:
                        stats["rejected_rows"] += 1
                        rejection_info = {
                            "row": row_num,
                            "csv_row": row_num - 1,
                            "id": row.get("ID", "N/A"),
                            "name": row.get("Name", "N/A"),
                            "errors": str(e),
                        }
                        stats["rejections"].append(rejection_info)

                        print(
                            f"❌ REJECTED Row {row_num} (ID: {row.get('ID', 'N/A')}, Name: {row.get('Name', 'N/A')}): {e}"
                        )

                    except Exception as e:
                        stats["rejected_rows"] += 1
                        error_msg = f"Row {row_num} (ID: {row.get('ID', 'N/A')}): {e!s}"
                        stats["validation_errors"].append(error_msg)
                        print(f"❌ ERROR: {error_msg}")
        else:
            # Dry run - just validate
            for row_num, row in enumerate(reader, start=2):
                stats["total_rows"] += 1

                try:
                    mapped_data = {}
                    for csv_field, model_field in field_mapping.items():
                        if csv_field in row:
                            mapped_data[model_field] = row[csv_field]

                    LegacyStudentValidated(**mapped_data)
                    stats["valid_rows"] += 1

                except ValidationError as e:
                    stats["rejected_rows"] += 1
                    print(
                        f"❌ WOULD REJECT Row {row_num} (ID: {row.get('ID', 'N/A')}, Name: {row.get('Name', 'N/A')}): {e}"
                    )

    return stats


def insert_validated_student(student: LegacyStudentValidated):
    """Insert a validated student record."""

    insert_sql = """
    INSERT INTO legacy_students_validated (
        id, name, ui, pw, kname, birth_date, birth_place, gender, marital_status,
        nationality, home_address, home_phone, email, mobile_phone, employment_place,
        position, father_name, spouse_name, emg_contact_person, relationship,
        contact_person_address, contact_person_phone, high_school_program_school,
        high_school_program_province, high_school_program_year, high_school_program_diploma,
        english_program_school, english_program_level, english_program_year,
        current_program, selected_program, selected_major, selected_faculty,
        admission_date, graduation_date, ba_grad_date, ma_grad_date, status,
        batch_id, first_term, ipk, csv_row_number, imported_at
    ) VALUES (
        %(id)s, %(name)s, %(ui)s, %(pw)s, %(kname)s, %(birth_date)s, %(birth_place)s,
        %(gender)s, %(marital_status)s, %(nationality)s, %(home_address)s, %(home_phone)s,
        %(email)s, %(mobile_phone)s, %(employment_place)s, %(position)s, %(father_name)s,
        %(spouse_name)s, %(emg_contact_person)s, %(relationship)s, %(contact_person_address)s,
        %(contact_person_phone)s, %(high_school_program_school)s, %(high_school_program_province)s,
        %(high_school_program_year)s, %(high_school_program_diploma)s, %(english_program_school)s,
        %(english_program_level)s, %(english_program_year)s, %(current_program)s,
        %(selected_program)s, %(selected_major)s, %(selected_faculty)s, %(admission_date)s,
        %(graduation_date)s, %(ba_grad_date)s, %(ma_grad_date)s, %(status)s, %(batch_id)s,
        %(first_term)s, %(ipk)s, %(csv_row_number)s, %(imported_at)s
    )
    """

    data = student.model_dump()
    with connection.cursor() as cursor:
        cursor.execute(insert_sql, data)


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description="Import legacy students with proper validation")
    parser.add_argument("--file", default="data/legacy/all_students_250811.csv")
    parser.add_argument("--drop-table", action="store_true")
    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    print("🎓 Legacy Students Import with Proper Validation")
    print("=" * 60)
    print("✅ ACCEPT: Valid ID and Name")
    print("🔄 DEFAULT: Missing birth date -> 1900-01-01")
    print("❌ REJECT: Missing ID or Name")
    print("=" * 60)

    try:
        # Create table
        if not args.dry_run:
            create_validated_students_table(drop_existing=args.drop_table)

        # Import data
        stats = import_and_validate_students(args.file, dry_run=args.dry_run)

        # Print results
        print("\n📊 VALIDATION SUMMARY")
        print("=" * 60)
        print(f"📄 Total rows: {stats['total_rows']:,}")
        print(f"✅ Valid rows: {stats['valid_rows']:,}")
        print(f"❌ Rejected rows: {stats['rejected_rows']:,}")

        if not args.dry_run:
            print(f"💾 Successfully inserted: {stats['inserted_rows']:,}")
        else:
            print("🔍 DRY RUN - No data was inserted")

        if stats["rejections"]:
            print(f"\n❌ REJECTED RECORDS ({len(stats['rejections'])}):")
            for rejection in stats["rejections"][:10]:  # Show first 10
                print(f"   Row {rejection['row']}: ID='{rejection['id']}', Name='{rejection['name']}'")

        print("=" * 60)

    except Exception as e:
        print(f"❌ Fatal error: {e!s}")
        sys.exit(1)


if __name__ == "__main__":
    main()
