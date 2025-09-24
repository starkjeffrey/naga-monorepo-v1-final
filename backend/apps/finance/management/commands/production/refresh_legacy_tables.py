"""Refresh legacy tables with incremental data based on IPK comparison.

This script compares the highest IPK (primary key) in existing PostgreSQL tables
with new CSV data and imports only records with higher IPK values.
"""

import csv
from datetime import datetime
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand
from django.db import connection
from pydantic import BaseModel, Field, field_validator


class LegacyStudent(BaseModel):
    """Pydantic model for legacy student data validation."""

    # Primary fields
    id: str = Field(..., max_length=10)
    ipk: int = Field(..., description="Internal primary key")

    # User credentials
    ui: str | None = Field(None, max_length=200)
    pw: str | None = Field(None, max_length=20)

    # Basic info
    name: str | None = Field(None, max_length=150)
    kname: str | None = Field(None, max_length=150)
    birthdate: datetime | None = None
    birthplace: str | None = Field(None, max_length=100)
    gender: str | None = Field(None, max_length=10)
    marital_status: str | None = Field(None, max_length=50)
    nationality: str | None = Field(None, max_length=50)

    # Contact info
    home_address: str | None = Field(None, max_length=500)
    home_phone: str | None = Field(None, max_length=50)
    email: str | None = Field(None, max_length=100)
    mobile_phone: str | None = Field(None, max_length=50)

    # Employment
    employment_place: str | None = Field(None, max_length=200)
    position: str | None = Field(None, max_length=150)

    # Family/Emergency contact
    father_name: str | None = Field(None, max_length=100)
    spouse_name: str | None = Field(None, max_length=100)
    emg_contact_person: str | None = Field(None, max_length=100)
    relationship: str | None = Field(None, max_length=50)
    contact_person_address: str | None = Field(None, max_length=500)
    contact_person_phone: str | None = Field(None, max_length=50)

    # Education history fields
    high_school_program_school: str | None = Field(None, max_length=150)
    high_school_program_province: str | None = Field(None, max_length=150)
    high_school_program_year: int | None = None
    high_school_program_diploma: str | None = Field(None, max_length=100)

    # Status fields
    deleted: int | None = None
    status: str | None = Field(None, max_length=15)

    # Dates
    created_date: datetime | None = None
    modified_date: datetime | None = None

    @field_validator("id")
    @classmethod
    def validate_student_id(cls, v: str) -> str:
        """Ensure student ID is properly formatted (5 digits, left padded)."""
        if v and v not in ["NULL", "null", ""]:
            numeric_part = "".join(c for c in v if c.isdigit())
            if numeric_part:
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


class LegacyReceiptHeader(BaseModel):
    """Pydantic model for legacy receipt headers data validation."""

    # Primary fields
    ipk: int = Field(..., description="Internal primary key")

    # Student and term info
    id: str | None = Field(None, max_length=10, description="Student ID")
    termid: str | None = Field(None, max_length=50)
    program: float | None = None

    # Receipt identifiers
    receiptno: str | None = Field(None, max_length=150)

    # Payment info
    pmtdate: datetime | None = None
    amount: float | None = None
    netamount: float | None = None

    # Receipt metadata
    notes: str | None = Field(None, max_length=4000)

    # System fields
    deleted: int | None = None
    name: str | None = Field(None, max_length=100)

    @field_validator("id")
    @classmethod
    def validate_student_id(cls, v: str) -> str:
        """Ensure student ID is properly formatted (5 digits, left padded)."""
        if v and v not in ["NULL", "null", ""]:
            numeric_part = "".join(c for c in v if c.isdigit())
            if numeric_part:
                return numeric_part.zfill(5)
        return v

    @field_validator("pmtdate", mode="before")
    @classmethod
    def parse_payment_date(cls, v):
        """Parse payment date from various formats."""
        if isinstance(v, datetime):
            return v
        if v and v not in ["NULL", "null", ""]:
            try:
                return datetime.strptime(v.split(".")[0], "%Y-%m-%d %H:%M:%S")
            except (ValueError, AttributeError):
                try:
                    return datetime.strptime(v, "%Y-%m-%d")
                except (ValueError, AttributeError):
                    return None
        return None

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
    """Refresh legacy tables with incremental data based on IPK comparison."""

    help = "Refresh legacy tables by importing only new records (IPK > last IPK in DB)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--students-file",
            type=str,
            default="data/legacy/all_students_250802.csv",
            help="Path to new students CSV file",
        )
        parser.add_argument(
            "--receipts-file",
            type=str,
            default="data/legacy/all_receipt_headers_250802.csv",
            help="Path to new receipt headers CSV file",
        )
        parser.add_argument("--batch-size", type=int, default=1000, help="Batch size for inserts")
        parser.add_argument(
            "--table",
            type=str,
            choices=["students", "receipts", "both"],
            default="both",
            help="Which table(s) to refresh",
        )

    def handle(self, *args, **options):
        batch_size = options["batch_size"]
        table_choice = options["table"]

        self.stdout.write(self.style.WARNING("=== LEGACY TABLE REFRESH TOOL ==="))
        self.stdout.write("Refreshing tables with incremental data based on IPK comparison")

        if table_choice in ["students", "both"]:
            self._refresh_students(options["students_file"], batch_size)

        if table_choice in ["receipts", "both"]:
            self._refresh_receipts(options["receipts_file"], batch_size)

    def _get_last_ipk(self, table_name: str) -> int:
        """Get the highest IPK value from the specified table."""
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT COALESCE(MAX(ipk), 0) FROM {table_name}")
            result = cursor.fetchone()
            return result[0] if result else 0

    def _refresh_students(self, file_path: str, batch_size: int):
        """Refresh legacy_students table with new records."""
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            self.stdout.write(self.style.ERROR(f"Students file not found: {file_path}"))
            return

        # Get last IPK from database
        last_ipk = self._get_last_ipk("legacy_students")
        self.stdout.write("\nRefreshing legacy_students table...")
        self.stdout.write(f"Last IPK in database: {last_ipk}")

        # Load and process new records
        new_records = 0
        batch_data = []
        error_count = 0

        with open(file_path_obj, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):
                try:
                    # Get IPK value
                    ipk_str = row.get("IPK", "")
                    if not ipk_str or ipk_str in ["NULL", "null", ""]:
                        continue

                    ipk = int(ipk_str)

                    # Skip if IPK is not greater than last IPK
                    if ipk <= last_ipk:
                        continue

                    # Process new record
                    student_data = {key.lower().replace("_", ""): value for key, value in row.items()}

                    # Validate with limited model (only essential fields)
                    LegacyStudent(**student_data)

                    # Add to batch - use all fields from CSV
                    batch_data.append(self._prepare_student_record(row))
                    new_records += 1

                    # Insert batch
                    if len(batch_data) >= batch_size:
                        self._insert_students_batch(batch_data)
                        self.stdout.write(f"  Inserted {new_records:,} new student records...")
                        batch_data = []

                except Exception as e:
                    error_count += 1
                    if error_count <= 5:
                        self.stdout.write(self.style.ERROR(f"Row {row_num}: {e!s} - ID: {row.get('ID', 'N/A')}"))

        # Insert remaining batch
        if batch_data:
            self._insert_students_batch(batch_data)

        self.stdout.write(
            self.style.SUCCESS(f"Students refresh complete: {new_records:,} new records added, {error_count:,} errors")
        )

    def _refresh_receipts(self, file_path: str, batch_size: int):
        """Refresh legacy_receipt_headers table with new records."""
        file_path_obj = Path(file_path)

        if not file_path_obj.exists():
            self.stdout.write(self.style.ERROR(f"Receipts file not found: {file_path}"))
            return

        # Get last IPK from database
        last_ipk = self._get_last_ipk("legacy_receipt_headers")
        self.stdout.write("\nRefreshing legacy_receipt_headers table...")
        self.stdout.write(f"Last IPK in database: {last_ipk}")

        # Load and process new records
        new_records = 0
        batch_data = []
        error_count = 0

        with open(file_path_obj, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):
                try:
                    # Get IPK value
                    ipk_str = row.get("IPK", "")
                    if not ipk_str or ipk_str in ["NULL", "null", ""]:
                        continue

                    ipk = int(ipk_str)

                    # Skip if IPK is not greater than last IPK
                    if ipk <= last_ipk:
                        continue

                    # Process new record
                    receipt_data = {key.lower().replace("_", ""): value for key, value in row.items()}

                    # Validate with limited model
                    LegacyReceiptHeader(**receipt_data)

                    # Add to batch - use all fields from CSV
                    batch_data.append(self._prepare_receipt_record(row))
                    new_records += 1

                    # Insert batch
                    if len(batch_data) >= batch_size:
                        self._insert_receipts_batch(batch_data)
                        self.stdout.write(f"  Inserted {new_records:,} new receipt records...")
                        batch_data = []

                except Exception as e:
                    error_count += 1
                    if error_count <= 5:
                        self.stdout.write(
                            self.style.ERROR(f"Row {row_num}: {e!s} - Receipt: {row.get('ReceiptNo', 'N/A')}")
                        )

        # Insert remaining batch
        if batch_data:
            self._insert_receipts_batch(batch_data)

        self.stdout.write(
            self.style.SUCCESS(f"Receipts refresh complete: {new_records:,} new records added, {error_count:,} errors")
        )

    def _prepare_student_record(self, row: dict[str, Any]) -> dict[str, Any]:
        """Prepare student record for database insertion."""
        # Map CSV columns to database columns
        record: dict[str, Any] = {}

        # Handle all fields from original CSV
        for key, value in row.items():
            db_column = key.lower().replace("_", "")

            # Clean empty values
            if value in ["", "NULL", "null"]:
                record[db_column] = None
            else:
                record[db_column] = value

        # Special handling for student ID
        if record.get("id"):
            numeric_id = "".join(c for c in str(record["id"]) if c.isdigit())
            if numeric_id:
                record["id"] = numeric_id.zfill(5)

        # Ensure IPK is an integer
        if record.get("ipk"):
            record["ipk"] = int(record["ipk"])

        return record

    def _prepare_receipt_record(self, row: dict[str, Any]) -> dict[str, Any]:
        """Prepare receipt record for database insertion."""
        # Map CSV columns to database columns
        record: dict[str, Any] = {}

        # Handle all fields from original CSV
        for key, value in row.items():
            db_column = key.lower().replace("_", "")

            # Clean empty values
            if value in ["", "NULL", "null"]:
                record[db_column] = None
            else:
                record[db_column] = value

        # Special handling for student ID
        if record.get("id"):
            numeric_id = "".join(c for c in str(record["id"]) if c.isdigit())
            if numeric_id:
                record["id"] = numeric_id.zfill(5)

        # Ensure IPK is an integer
        if record.get("ipk"):
            record["ipk"] = int(record["ipk"])

        # Handle date fields
        if record.get("pmtdate"):
            try:
                record["pmtdate"] = datetime.strptime(record["pmtdate"].split(".")[0], "%Y-%m-%d %H:%M:%S")
            except (ValueError, AttributeError):
                record["pmtdate"] = None

        return record

    def _insert_students_batch(self, batch_data):
        """Insert a batch of student records."""
        if not batch_data:
            return

        # Get all possible columns from the first record
        columns = list(batch_data[0].keys())

        # Build dynamic insert query
        placeholders = ", ".join(["%s"] * len(columns))
        columns_str = ", ".join(columns)

        insert_sql = f"""
        INSERT INTO legacy_students ({columns_str})
        VALUES ({placeholders})
        ON CONFLICT (ipk) DO NOTHING
        """

        with connection.cursor() as cursor:
            for record in batch_data:
                values = [record.get(col) for col in columns]
                cursor.execute(insert_sql, values)

    def _insert_receipts_batch(self, batch_data):
        """Insert a batch of receipt records."""
        if not batch_data:
            return

        # Get all possible columns from the first record
        columns = list(batch_data[0].keys())

        # Build dynamic insert query
        placeholders = ", ".join(["%s"] * len(columns))
        columns_str = ", ".join(columns)

        insert_sql = f"""
        INSERT INTO legacy_receipt_headers ({columns_str})
        VALUES ({placeholders})
        ON CONFLICT (ipk) DO NOTHING
        """

        with connection.cursor() as cursor:
            for record in batch_data:
                values = [record.get(col) for col in columns]
                cursor.execute(insert_sql, values)
