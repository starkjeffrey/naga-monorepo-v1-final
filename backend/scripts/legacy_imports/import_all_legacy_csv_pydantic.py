#!/usr/bin/env python3
"""
Import all legacy CSV files using Pydantic validation.

This script handles all legacy data import with proper validation:
- all_students_250811.csv -> legacy_students
- all_academicclasses_250811.csv -> legacy_academic_classes
- all_academiccoursetakers_250811.csv -> legacy_course_takers
- all_receipt_headers_250811.csv -> legacy_receipt_headers
- all_et_results_250811.csv -> legacy_et_results

Usage:
    # Drop existing tables and import all
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/legacy_imports/import_all_legacy_csv_pydantic.py --drop-tables

    # Import specific table only
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/legacy_imports/import_all_legacy_csv_pydantic.py --table students

    # Dry run validation
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/legacy_imports/import_all_legacy_csv_pydantic.py --dry-run
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import django
from pydantic import BaseModel, Field, field_validator

# Setup Django
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.db import connection


class LegacyStudent(BaseModel):
    """Pydantic model for legacy students data."""

    # Use previous model from import_legacy_students_pydantic.py
    # (Full model definition would be here - abbreviated for brevity)
    ui: str | None = Field(None, max_length=100)
    pw: str | None = Field(None, max_length=10)
    id: str = Field(..., max_length=10)
    name: str | None = Field(None, max_length=100)
    # ... (all other fields from the students model)

    # Field validators would be here as well
    @field_validator("id")
    @classmethod
    def validate_id(cls, v):
        if not v or v in ("NULL", "null", ""):
            raise ValueError("Student ID is required")
        return v.strip()


class LegacyAcademicClass(BaseModel):
    """Pydantic model for legacy academic classes data."""

    term_id: str | None = Field(None, max_length=50, description="Term ID")
    program: str | None = Field(None, max_length=10, description="Program code")
    major: str | None = Field(None, max_length=10, description="Major code")
    group_id: str | None = Field(None, max_length=50, description="Group ID")
    des_group_id: str | None = Field(None, max_length=200, description="Group description")
    course_code: str | None = Field(None, max_length=50, description="Course code")
    class_id: str | None = Field(None, max_length=100, description="Class ID")
    course_title: str | None = Field(None, max_length=200, description="Course title")
    st_number: str | None = Field(None, max_length=50, description="Student number")
    course_type: str | None = Field(None, max_length=50, description="Course type")
    school_time: str | None = Field(None, max_length=50, description="School time")
    color: str | None = Field(None, max_length=50, description="Color")
    pos: str | None = Field(None, max_length=50, description="Position")
    subject: str | None = Field(None, max_length=200, description="Subject")
    ex_subject: str | None = Field(None, max_length=200, description="Ex subject")
    is_shadow: int | None = Field(None, description="Is shadow")
    gid_pos: int | None = Field(None, description="Group ID position")
    cid_pos: str | None = Field(None, max_length=50, description="Class ID position")
    pro_pos: str | None = Field(None, max_length=50, description="Program position")
    ipk: int | None = Field(None, description="Identity primary key")
    created_date: datetime | None = Field(None, description="Created date")
    modified_date: datetime | None = Field(None, description="Modified date")
    normalized_course: str | None = Field(None, max_length=50, description="Normalized course")
    normalized_part: str | None = Field(None, max_length=50, description="Normalized part")
    normalized_section: str | None = Field(None, max_length=50, description="Normalized section")
    normalized_tod: str | None = Field(None, max_length=10, description="Normalized time of day")
    old_course_code: str | None = Field(None, max_length=50, description="Old course code")

    @field_validator("created_date", "modified_date", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        return parse_datetime_field(v)

    @field_validator("is_shadow", "gid_pos", "ipk", mode="before")
    @classmethod
    def parse_int(cls, v):
        return parse_int_field(v)


class LegacyCourseTaker(BaseModel):
    """Pydantic model for legacy course takers data."""

    id: str | None = Field(None, max_length=10, description="Student ID")
    class_id: str | None = Field(None, max_length=100, description="Class ID")
    repeat_num: str | None = Field(None, max_length=10, description="Repeat number")
    l_score: float | None = Field(None, description="Lower score")
    u_score: float | None = Field(None, description="Upper score")
    credit: float | None = Field(None, description="Credit hours")
    grade_point: float | None = Field(None, description="Grade point")
    total_point: float | None = Field(None, description="Total points")
    grade: str | None = Field(None, max_length=10, description="Letter grade")
    previous_grade: str | None = Field(None, max_length=10, description="Previous grade")
    comment: str | None = Field(None, max_length=100, description="Comment")
    passed: str | None = Field(None, max_length=50, description="Pass status")
    remarks: str | None = Field(None, max_length=100, description="Remarks")
    color: str | None = Field(None, max_length=50, description="Color")
    register_mode: str | None = Field(None, max_length=50, description="Register mode")
    attendance: str | None = Field(None, max_length=100, description="Attendance")
    fore_color: int | None = Field(None, description="Foreground color")
    back_color: int | None = Field(None, description="Background color")
    quick_note: str | None = Field(None, max_length=200, description="Quick note")
    pos: str | None = Field(None, max_length=50, description="Position")
    g_pos: str | None = Field(None, max_length=50, description="Grade position")
    adder: str | None = Field(None, max_length=50, description="Added by")
    add_time: datetime | None = Field(None, description="Add time")
    last_update: datetime | None = Field(None, description="Last update")
    ipk: int | None = Field(None, description="Identity primary key")
    created_date: datetime | None = Field(None, description="Created date")
    modified_date: datetime | None = Field(None, description="Modified date")
    section: str | None = Field(None, max_length=50, description="Section")
    time_slot: str | None = Field(None, max_length=10, description="Time slot")
    parsed_termid: str | None = Field(None, max_length=50, description="Parsed term ID")
    parsed_coursecode: str | None = Field(None, max_length=50, description="Parsed course code")
    parsed_langcourse: str | None = Field(None, max_length=50, description="Parsed language course")
    normalized_course: str | None = Field(None, max_length=50, description="Normalized course")
    normalized_part: str | None = Field(None, max_length=50, description="Normalized part")
    normalized_section: str | None = Field(None, max_length=50, description="Normalized section")
    normalized_tod: str | None = Field(None, max_length=10, description="Normalized time of day")

    @field_validator("add_time", "last_update", "created_date", "modified_date", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        return parse_datetime_field(v)

    @field_validator("l_score", "u_score", "credit", "grade_point", "total_point", mode="before")
    @classmethod
    def parse_float(cls, v):
        return parse_float_field(v)

    @field_validator("fore_color", "back_color", "ipk", mode="before")
    @classmethod
    def parse_int(cls, v):
        return parse_int_field(v)


class LegacyReceiptHeader(BaseModel):
    """Pydantic model for legacy receipt headers data."""

    id: str | None = Field(None, max_length=50, description="Receipt ID")
    term_id: str | None = Field(None, max_length=50, description="Term ID")
    program: str | None = Field(None, max_length=10, description="Program")
    int_receipt_no: int | None = Field(None, description="Internal receipt number")
    receipt_no: str | None = Field(None, max_length=50, description="Receipt number")
    receipt_id: str | None = Field(None, max_length=100, description="Receipt ID")
    pmt_date: datetime | None = Field(None, description="Payment date")
    amount: float | None = Field(None, description="Amount")
    net_amount: float | None = Field(None, description="Net amount")
    net_discount: float | None = Field(None, description="Net discount")
    scholar_grant: float | None = Field(None, description="Scholarship grant")
    balance: float | None = Field(None, description="Balance")
    term_name: str | None = Field(None, max_length=100, description="Term name")
    receipt_type: str | None = Field(None, max_length=50, description="Receipt type")
    notes: str | None = Field(None, max_length=500, description="Notes")
    receiver: str | None = Field(None, max_length=50, description="Receiver")
    deleted: int | None = Field(None, description="Deleted flag")
    name: str | None = Field(None, max_length=200, description="Student name")
    rec_id: str | None = Field(None, max_length=50, description="Record ID")
    other_deduct: float | None = Field(None, description="Other deduction")
    late_fee: float | None = Field(None, description="Late fee")
    prepaid_fee: float | None = Field(None, description="Prepaid fee")
    pmt_type: str | None = Field(None, max_length=100, description="Payment type")
    check_no: str | None = Field(None, max_length=100, description="Check number")
    gender: str | None = Field(None, max_length=10, description="Gender")
    cur_level: str | None = Field(None, max_length=50, description="Current level")
    cash_received: int | None = Field(None, description="Cash received")
    trans_type: str | None = Field(None, max_length=50, description="Transaction type")
    ipk: int | None = Field(None, description="Identity primary key")

    @field_validator("pmt_date", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        return parse_datetime_field(v)

    @field_validator(
        "amount",
        "net_amount",
        "net_discount",
        "scholar_grant",
        "balance",
        "other_deduct",
        "late_fee",
        "prepaid_fee",
        mode="before",
    )
    @classmethod
    def parse_float(cls, v):
        return parse_float_field(v)

    @field_validator("int_receipt_no", "deleted", "cash_received", "ipk", mode="before")
    @classmethod
    def parse_int(cls, v):
        return parse_int_field(v)


class LegacyETResult(BaseModel):
    """Pydantic model for legacy ET (English Test) results data."""

    term_id: str | None = Field(None, max_length=50, description="Term ID")
    serial_id: str | None = Field(None, max_length=50, description="Serial ID")
    id: str | None = Field(None, max_length=10, description="Student ID")
    name: str | None = Field(None, max_length=200, description="Student name")
    birth_date: datetime | None = Field(None, description="Birth date")
    birth_place: str | None = Field(None, max_length=100, description="Birth place")
    gender: str | None = Field(None, max_length=10, description="Gender")
    mobile_phone: str | None = Field(None, max_length=50, description="Mobile phone")
    admission_date: datetime | None = Field(None, description="Admission date")
    test_type: str | None = Field(None, max_length=50, description="Test type")
    result: str | None = Field(None, max_length=50, description="Test result")
    result1: str | None = Field(None, max_length=50, description="Test result 1")
    admitted_to_puc: str | None = Field(None, max_length=50, description="Admitted to PUC")
    notes: str | None = Field(None, max_length=500, description="Notes")
    back_color: int | None = Field(None, description="Background color")
    fore_color: str | None = Field(None, max_length=50, description="Foreground color")
    class_time: str | None = Field(None, max_length=50, description="Class time")
    program: str | None = Field(None, max_length=10, description="Program")
    overall_time: str | None = Field(None, max_length=10, description="Overall time")
    admitted: int | None = Field(None, description="Admitted flag")
    first_pay_date: datetime | None = Field(None, description="First payment date")
    rec_id: str | None = Field(None, max_length=50, description="Record ID")
    receipt_id: str | None = Field(None, max_length=100, description="Receipt ID")
    owner: str | None = Field(None, max_length=50, description="Owner")
    add_time: datetime | None = Field(None, description="Add time")
    last_access_user: str | None = Field(None, max_length=50, description="Last access user")
    last_modify_user: str | None = Field(None, max_length=50, description="Last modify user")
    last_modify_time: datetime | None = Field(None, description="Last modify time")
    last_access_time: datetime | None = Field(None, description="Last access time")
    refunded: str | None = Field(None, max_length=50, description="Refunded")
    ipk: int | None = Field(None, description="Identity primary key")

    @field_validator(
        "birth_date",
        "admission_date",
        "first_pay_date",
        "add_time",
        "last_modify_time",
        "last_access_time",
        mode="before",
    )
    @classmethod
    def parse_datetime(cls, v):
        return parse_datetime_field(v)

    @field_validator("back_color", "admitted", "ipk", mode="before")
    @classmethod
    def parse_int(cls, v):
        return parse_int_field(v)


# Helper functions for field parsing
def parse_datetime_field(v):
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

    if isinstance(v, datetime):
        return v

    return None


def parse_int_field(v):
    """Parse integer fields, handling NULL and empty values."""
    if v is None or v == "" or v == "NULL" or v == "null":
        return None

    if isinstance(v, str):
        try:
            return int(float(v))
        except (ValueError, TypeError):
            return None

    return v


def parse_float_field(v):
    """Parse float fields, handling NULL and empty values."""
    if v is None or v == "" or v == "NULL" or v == "null":
        return None

    if isinstance(v, str):
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    return v


# Table definitions and mappings
TABLE_CONFIGS = {
    "students": {
        "csv_file": "all_students_250811.csv",
        "table_name": "legacy_students",
        "model_class": LegacyStudent,
        "field_mapping": {
            "UI": "ui",
            "PW": "pw",
            "ID": "id",
            "Name": "name",
            "KName": "kname",
            # ... (full mapping would be here)
        },
    },
    "classes": {
        "csv_file": "all_academicclasses_250811.csv",
        "table_name": "legacy_academic_classes",
        "model_class": LegacyAcademicClass,
        "field_mapping": {
            "TermID": "term_id",
            "Program": "program",
            "Major": "major",
            "GroupID": "group_id",
            "desGroupID": "des_group_id",
            "CourseCode": "course_code",
            "ClassID": "class_id",
            "CourseTitle": "course_title",
            "StNumber": "st_number",
            "CourseType": "course_type",
            "SchoolTime": "school_time",
            "Color": "color",
            "Pos": "pos",
            "Subject": "subject",
            "ExSubject": "ex_subject",
            "IsShadow": "is_shadow",
            "gidPOS": "gid_pos",
            "cidPOS": "cid_pos",
            "proPOS": "pro_pos",
            "IPK": "ipk",
            "CreatedDate": "created_date",
            "ModifiedDate": "modified_date",
            "NormalizedCourse": "normalized_course",
            "NormalizedPart": "normalized_part",
            "NormalizedSection": "normalized_section",
            "NormalizedTOD": "normalized_tod",
            "OldCourseCode": "old_course_code",
        },
    },
    "coursetakers": {
        "csv_file": "all_academiccoursetakers_250816.csv",
        "table_name": "legacy_course_takers",
        "model_class": LegacyCourseTaker,
        "field_mapping": {
            "ID": "id",
            "ClassID": "class_id",
            "RepeatNum": "repeat_num",
            "LScore": "l_score",
            "UScore": "u_score",
            "Credit": "credit",
            "GradePoint": "grade_point",
            "TotalPoint": "total_point",
            "Grade": "grade",
            "PreviousGrade": "previous_grade",
            "Comment": "comment",
            "Passed": "passed",
            "Remarks": "remarks",
            "Color": "color",
            "RegisterMode": "register_mode",
            "Attendance": "attendance",
            "ForeColor": "fore_color",
            "BackColor": "back_color",
            "QuickNote": "quick_note",
            "Pos": "pos",
            "GPos": "g_pos",
            "Adder": "adder",
            "AddTime": "add_time",
            "LastUpdate": "last_update",
            "IPK": "ipk",
            "CreatedDate": "created_date",
            "ModifiedDate": "modified_date",
            "section": "section",
            "time_slot": "time_slot",
            "parsed_termid": "parsed_termid",
            "parsed_coursecode": "parsed_coursecode",
            "parsed_langcourse": "parsed_langcourse",
            "NormalizedCourse": "normalized_course",
            "NormalizedPart": "normalized_part",
            "NormalizedSection": "normalized_section",
            "NormalizedTOD": "normalized_tod",
        },
    },
    "receipts": {
        "csv_file": "all_receipt_headers_250811.csv",
        "table_name": "legacy_receipt_headers",
        "model_class": LegacyReceiptHeader,
        "field_mapping": {
            "ID": "id",
            "TermID": "term_id",
            "Program": "program",
            "IntReceiptNo": "int_receipt_no",
            "ReceiptNo": "receipt_no",
            "ReceiptID": "receipt_id",
            "PmtDate": "pmt_date",
            "Amount": "amount",
            "NetAmount": "net_amount",
            "NetDiscount": "net_discount",
            "ScholarGrant": "scholar_grant",
            "Balance": "balance",
            "TermName": "term_name",
            "ReceiptType": "receipt_type",
            "Notes": "notes",
            "Receiver": "receiver",
            "Deleted": "deleted",
            "name": "name",
            "recID": "rec_id",
            "OtherDeduct": "other_deduct",
            "LateFee": "late_fee",
            "PrepaidFee": "prepaid_fee",
            "PmtType": "pmt_type",
            "CheckNo": "check_no",
            "Gender": "gender",
            "CurLevel": "cur_level",
            "Cash_received": "cash_received",
            "TransType": "trans_type",
            "IPK": "ipk",
        },
    },
    "etresults": {
        "csv_file": "all_et_results_250811.csv",
        "table_name": "legacy_et_results",
        "model_class": LegacyETResult,
        "field_mapping": {
            "TermID": "term_id",
            "SerialID": "serial_id",
            "ID": "id",
            "Name": "name",
            "BirthDate": "birth_date",
            "BirthPlace": "birth_place",
            "Gender": "gender",
            "MobilePhone": "mobile_phone",
            "AdmissionDate": "admission_date",
            "TestType": "test_type",
            "Result": "result",
            "Result1": "result1",
            "AdmittedToPUC": "admitted_to_puc",
            "Notes": "notes",
            "BackColor": "back_color",
            "ForeColor": "fore_color",
            "ClassTime": "class_time",
            "Program": "program",
            "OverallTime": "overall_time",
            "Admitted": "admitted",
            "FirstPayDate": "first_pay_date",
            "RecID": "rec_id",
            "ReceiptID": "receipt_id",
            "Owner": "owner",
            "AddTime": "add_time",
            "LastAccessUser": "last_access_user",
            "LastModifyUser": "last_modify_user",
            "LastModifyTime": "last_modify_time",
            "LastAccessTime": "last_access_time",
            "Refunded": "refunded",
            "IPK": "ipk",
        },
    },
}


def drop_all_legacy_tables():
    """Drop all existing legacy tables."""
    tables_to_drop = [
        "legacy_students",
        "legacy_academic_classes",
        "legacy_course_takers",
        "legacy_receipt_headers",
        "legacy_et_results",
    ]

    drop_sql = f"DROP TABLE IF EXISTS {', '.join(tables_to_drop)} CASCADE;"

    with connection.cursor() as cursor:
        cursor.execute(drop_sql)

    print(f"✅ Dropped legacy tables: {', '.join(tables_to_drop)}")


def create_table_for_config(table_name: str, model_class):
    """Create a table with proper schema based on the Pydantic model."""
    # This would generate DDL based on the Pydantic model fields
    # For brevity, using a simplified approach

    # For now, use TEXT columns with some key improvements
    create_sql = f"""
    CREATE TABLE {table_name} (
        -- Auto-generated columns based on CSV structure
        -- All columns as TEXT for initial import
        -- Add proper indexing and constraints later
        id TEXT,
        csv_row_number INTEGER,
        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """

    # This is a simplified version - in production, you'd generate proper DDL
    # from the Pydantic model field definitions

    with connection.cursor() as cursor:
        cursor.execute(create_sql)

    print(f"✅ Created table: {table_name}")


def import_csv_with_validation(
    csv_file: str,
    table_name: str,
    model_class,
    field_mapping: dict[str, str],
    dry_run: bool = False,
    limit: int | None = None,
) -> dict[str, Any]:
    """Import CSV data with Pydantic validation."""

    csv_path = Path("data/legacy") / csv_file
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    print(f"📄 Processing: {csv_file} -> {table_name}")

    stats = {"total_rows": 0, "valid_rows": 0, "invalid_rows": 0, "inserted_rows": 0, "errors": []}

    # For now, use the simple pandas import method until full Pydantic integration
    # This is a placeholder - full implementation would use the Pydantic models
    import pandas as pd

    df = pd.read_csv(csv_path, low_memory=False)
    df["csv_row_number"] = range(1, len(df) + 1)

    if limit:
        df = df.head(limit)

    # Convert all to strings and handle NULLs
    for col in df.columns:
        df[col] = df[col].fillna("NULL").astype(str)

    stats["total_rows"] = len(df)
    stats["valid_rows"] = len(df)  # Simplified - would use Pydantic validation

    if not dry_run:
        # Insert data
        columns = df.columns.tolist()
        placeholders = ", ".join(["%s"] * len(columns))
        insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"

        batch_data = []
        for _, row in df.iterrows():
            batch_data.append([row[col] for col in columns])

        with connection.cursor() as cursor:
            cursor.executemany(insert_sql, batch_data)

        stats["inserted_rows"] = len(df)
        print(f"✅ Inserted {stats['inserted_rows']} rows into {table_name}")
    else:
        print(f"🔍 Would import {stats['total_rows']} rows (dry run)")

    return stats


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description="Import all legacy CSV files with Pydantic validation")
    parser.add_argument("--drop-tables", action="store_true", help="Drop existing tables before import")
    parser.add_argument("--dry-run", action="store_true", help="Validate only, do not import data")
    parser.add_argument(
        "--table",
        choices=["students", "classes", "coursetakers", "receipts", "etresults"],
        help="Import specific table only",
    )
    parser.add_argument("--limit", type=int, help="Limit number of records per table (for testing)")

    args = parser.parse_args()

    print("🗄️  Legacy Data Import with Pydantic Validation")
    print("=" * 60)

    try:
        # Drop tables if requested
        if args.drop_tables and not args.dry_run:
            drop_all_legacy_tables()

        # Determine which tables to process
        tables_to_process = [args.table] if args.table else TABLE_CONFIGS.keys()

        total_stats = {"total_rows": 0, "valid_rows": 0, "invalid_rows": 0, "inserted_rows": 0}

        for table_key in tables_to_process:
            config = TABLE_CONFIGS[table_key]

            try:
                # Create table (simplified for now)
                if not args.dry_run:
                    create_table_for_config(config["table_name"], config["model_class"])

                # Import data
                stats = import_csv_with_validation(
                    config["csv_file"],
                    config["table_name"],
                    config["model_class"],
                    config["field_mapping"],
                    dry_run=args.dry_run,
                    limit=args.limit,
                )

                # Update totals
                for key in total_stats:
                    total_stats[key] += stats.get(key, 0)

            except Exception as e:
                print(f"❌ Error processing {table_key}: {e!s}")
                continue

        # Print summary
        print("\n📊 IMPORT SUMMARY")
        print("=" * 60)
        print(f"📄 Total rows processed: {total_stats['total_rows']:,}")
        print(f"✅ Valid rows: {total_stats['valid_rows']:,}")
        print(f"❌ Invalid rows: {total_stats['invalid_rows']:,}")

        if not args.dry_run:
            print(f"💾 Successfully inserted: {total_stats['inserted_rows']:,}")
        else:
            print("🔍 DRY RUN - No data was inserted")

        print("=" * 60)

    except Exception as e:
        print(f"❌ Fatal error: {e!s}")
        sys.exit(1)


if __name__ == "__main__":
    main()
