"""Load ET (English Testing) results from legacy CSV file with comprehensive validation.

This script imports historical English test results data with proper validation,
error handling, and audit reporting following project standards.

Usage:
    docker compose -f docker-compose.local.yml run --rm django \\
        python manage.py load_et_results data/legacy/all_et_results_250802.csv
"""

# ruff: noqa: E501

from datetime import datetime

import pandas as pd
from django.core.management.base import CommandError
from django.db import connection
from pydantic import BaseModel, Field, ValidationError, field_validator

from apps.common.management.base_migration import BaseMigrationCommand


class ETResultRecord(BaseModel):
    """Pydantic model for ET_Results data validation with proper type coercion."""

    # Core identification fields
    term_id: str | None = Field(None, alias="TermID", max_length=50, description="Term identifier")
    serial_id: str | None = Field(None, alias="SerialID", max_length=50, description="Serial number")
    id: str | None = Field(None, alias="ID", max_length=100, description="Student ID")
    name: str | None = Field(None, alias="Name", max_length=50, description="Student name")

    # Personal information
    birth_date: datetime | None = Field(None, alias="BirthDate", description="Date of birth")
    birth_place: str | None = Field(None, alias="BirthPlace", max_length=50, description="Place of birth")
    gender: str | None = Field(None, alias="Gender", max_length=50, description="Gender")
    mobile_phone: str | None = Field(None, alias="MobilePhone", max_length=50, description="Mobile phone number")

    # Admission and test data
    admission_date: datetime | None = Field(None, alias="AdmissionDate", description="Admission date")
    test_type: str | None = Field(None, alias="TestType", max_length=50, description="Type of test (IEAP, GESL, EHSS)")
    result: str | None = Field(None, alias="Result", max_length=100, description="Test result score")
    result1: str | None = Field(None, alias="Result1", max_length=100, description="Alternative result")
    admitted_to_puc: str | None = Field(None, alias="AdmittedToPUC", max_length=50, description="Admitted to PUC flag")

    # Additional information
    notes: str | None = Field(None, alias="Notes", max_length=200, description="Additional notes")
    back_color: str | None = Field(None, alias="BackColor", max_length=50, description="Background color code")
    fore_color: str | None = Field(None, alias="ForeColor", max_length=100, description="Foreground color code")
    class_time: str | None = Field(None, alias="ClassTime", max_length=50, description="Scheduled class time")

    # Program and administrative data
    program: float | None = Field(None, alias="Program", description="Program ID")
    overall_time: str | None = Field(None, alias="OverallTime", max_length=10, description="Overall time")
    admitted: str | None = Field(None, alias="Admitted", max_length=3, description="Admission status")
    first_pay_date: str | None = Field(None, alias="FirstPayDate", max_length=100, description="First payment date")

    # System fields
    rec_id: float | None = Field(None, alias="RecID", description="Record ID")
    receipt_id: str | None = Field(None, alias="ReceiptID", max_length=250, description="Receipt identifier")
    owner: float | None = Field(None, alias="Owner", description="Owner ID")

    # Audit fields
    add_time: datetime | None = Field(None, alias="AddTime", description="Record creation time")
    last_access_user: float | None = Field(None, alias="LastAccessUser", description="Last access user ID")
    last_modify_user: float | None = Field(None, alias="LastModifyUser", description="Last modify user ID")
    last_modify_time: datetime | None = Field(None, alias="LastModifyTime", description="Last modification time")
    last_access_time: datetime | None = Field(None, alias="LastAccessTime", description="Last access time")

    # Financial fields
    refunded: int | None = Field(None, alias="Refunded", description="Refunded flag")
    ipk: int | None = Field(None, alias="IPK", description="Primary key from legacy system")

    # Metadata
    csv_row_number: int = Field(..., description="Original CSV row number for tracking")

    @field_validator("birth_date", "admission_date", "add_time", "last_modify_time", "last_access_time", mode="before")
    @classmethod
    def parse_datetime(cls, v):
        """Parse various datetime formats from legacy system."""
        if not v or v == "NULL" or pd.isna(v):
            return None

        if isinstance(v, str):
            v = v.strip()
            if not v or v.lower() == "null":
                return None

            # Try multiple datetime formats from legacy system
            for fmt in [
                "%Y-%m-%d %H:%M:%S.%f",  # 2013-12-04 17:33:55.000
                "%Y-%m-%d %H:%M:%S",  # 2013-12-04 17:33:55
                "%Y-%m-%d",  # 2013-12-04
                "%m/%d/%Y %H:%M:%S",  # US format
                "%m/%d/%Y",  # US format date only
            ]:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue

            # If no format matched, return None rather than failing
            return None

        return v

    @field_validator("program", "rec_id", "owner", "last_access_user", "last_modify_user", mode="before")
    @classmethod
    def parse_float(cls, v):
        """Parse float values with null handling."""
        if not v or v == "NULL" or (isinstance(v, str) and v.strip().lower() in ["null", ""]):
            return None
        try:
            return float(v)
        except (ValueError, TypeError):
            return None

    @field_validator("refunded", "ipk", mode="before")
    @classmethod
    def parse_int(cls, v):
        """Parse integer values with null handling."""
        if not v or v == "NULL" or (isinstance(v, str) and v.strip().lower() in ["null", ""]):
            return None
        try:
            return int(float(v))  # Handle "123.0" format
        except (ValueError, TypeError):
            return None

    @field_validator(
        "term_id",
        "serial_id",
        "id",
        "name",
        "birth_place",
        "gender",
        "mobile_phone",
        "test_type",
        "result",
        "result1",
        "admitted_to_puc",
        "notes",
        "back_color",
        "fore_color",
        "class_time",
        "overall_time",
        "admitted",
        "first_pay_date",
        "receipt_id",
        mode="before",
    )
    @classmethod
    def parse_string(cls, v):
        """Parse string values with null handling and cleanup."""
        if not v or (isinstance(v, str) and v.strip().lower() in ["null", ""]):
            return None
        if isinstance(v, str):
            return v.strip()
        return str(v) if v is not None else None

    class Config:
        """Pydantic configuration."""

        str_strip_whitespace = True
        validate_assignment = True
        use_enum_values = True
        populate_by_name = True
        allow_population_by_field_name = True


class Command(BaseMigrationCommand):
    """Load ET results with comprehensive validation and error handling."""

    help = "Load ET (English Testing) results from legacy CSV file"

    def add_arguments(self, parser):
        """Add command arguments."""
        super().add_arguments(parser)
        parser.add_argument("csv_file", type=str, help="Path to the ET results CSV file")
        parser.add_argument(
            "--batch-size", type=int, default=1000, help="Number of records to process in each batch (default: 1000)"
        )
        parser.add_argument(
            "--validate-only", action="store_true", help="Only validate data without importing to database"
        )

    def get_rejection_categories(self) -> list[str]:
        """Return list of possible rejection categories."""
        return [
            "VALIDATION_ERROR",
            "DUPLICATE_IPK",
            "DATABASE_ERROR",
            "MISSING_REQUIRED_FIELD",
            "INVALID_DATE_FORMAT",
            "INVALID_NUMERIC_VALUE",
            "STRING_TOO_LONG",
        ]

    def execute_migration(self, *args, **options):
        """Execute the ET results import."""
        csv_file = options["csv_file"]
        batch_size = options["batch_size"]
        validate_only = options["validate_only"]

        self.stdout.write(f"Loading ET results from {csv_file}")
        self.stdout.write(f"Validation only: {validate_only}")

        # Record input parameters
        self.audit_data["summary"]["input"].update(
            {"csv_file": csv_file, "batch_size": batch_size, "validate_only": validate_only}
        )

        # Process the CSV file
        total_processed, total_imported, validation_errors = self.process_csv_file(csv_file, batch_size, validate_only)

        # Update audit summary
        self.audit_data["summary"]["output"].update(
            {
                "total_processed": total_processed,
                "total_imported": total_imported,
                "validation_errors": validation_errors,
                "success_rate": (
                    f"{((total_processed - validation_errors) / total_processed * 100):.1f}%"
                    if total_processed > 0
                    else "0%"
                ),
            }
        )

        return {
            "success": True,
            "total_processed": total_processed,
            "total_imported": total_imported,
            "validation_errors": validation_errors,
        }

    def process_csv_file(self, csv_file: str, batch_size: int, validate_only: bool) -> tuple[int, int, int]:
        """Process the CSV file and import data."""
        import pandas as pd

        try:
            # Read CSV file
            df = pd.read_csv(csv_file, low_memory=False)
            total_rows = len(df)

            self.stdout.write(f"Found {total_rows} records in CSV file")

            # Add row numbers for tracking
            df["csv_row_number"] = range(1, len(df) + 1)

            # Process in batches
            total_processed = 0
            total_imported = 0
            validation_errors = 0

            # Create table if not in validation-only mode
            if not validate_only:
                self.create_legacy_table()

            for batch_start in range(0, total_rows, batch_size):
                batch_end = min(batch_start + batch_size, total_rows)
                batch_df = df.iloc[batch_start:batch_end]

                self.stdout.write(f"Processing batch {batch_start + 1}-{batch_end} of {total_rows}")

                # Process batch
                batch_processed, batch_imported, batch_errors = self.process_batch(batch_df, validate_only)

                total_processed += batch_processed
                total_imported += batch_imported
                validation_errors += batch_errors

                # Progress update
                if total_processed % (batch_size * 5) == 0:
                    self.stdout.write(
                        f"Progress: {total_processed}/{total_rows} "
                        f"({total_processed / total_rows * 100:.1f}%) - "
                        f"Imported: {total_imported}, Errors: {validation_errors}"
                    )

            return total_processed, total_imported, validation_errors

        except Exception as e:
            self.record_rejection("DATABASE_ERROR", "csv_processing", f"error: {e}, csv_file: {csv_file}")
            raise CommandError(f"Failed to process CSV file: {e}") from e

    def process_batch(self, batch_df, validate_only: bool) -> tuple[int, int, int]:
        """Process a batch of records."""
        batch_processed = 0
        batch_imported = 0
        batch_errors = 0

        validated_records = []

        # Validate each record in the batch
        for idx, row in batch_df.iterrows():
            batch_processed += 1

            try:
                # Convert row to dict and validate with Pydantic
                row_dict = row.to_dict()
                validated_record = ETResultRecord(**row_dict)
                validated_records.append(validated_record)

            except ValidationError as e:
                batch_errors += 1
                error_msg = f"row_number: {row.get('csv_row_number', idx)}, validation_errors: {[f'{err["loc"]}: {err["msg"]}' for err in e.errors()]}, raw_data: {row_dict}"
                self.record_rejection(
                    "VALIDATION_ERROR",
                    f"row_{row.get('csv_row_number', idx)}",
                    error_msg,
                )
                continue

            except Exception as e:
                batch_errors += 1
                error_msg = f"row_number: {row.get('csv_row_number', idx)}, error: {e}, raw_data: {row.to_dict()}"
                self.record_rejection(
                    "DATABASE_ERROR",
                    f"row_{row.get('csv_row_number', idx)}",
                    error_msg,
                )
                continue

        # Import validated records if not validation-only mode
        if not validate_only and validated_records:
            try:
                imported_count = self.import_validated_records(validated_records)
                batch_imported += imported_count
            except Exception as e:
                self.record_rejection(
                    "DATABASE_ERROR",
                    f"batch_import_{len(validated_records)}_records",
                    f"error: {e}, record_count: {len(validated_records)}",
                )

        return batch_processed, batch_imported, batch_errors

    def create_legacy_table(self):
        """Create the legacy_et_results table."""
        create_table_sql = """
        DROP TABLE IF EXISTS legacy_et_results;
        CREATE TABLE legacy_et_results (
            term_id VARCHAR(50),
            serial_id VARCHAR(50),
            id VARCHAR(100),
            name VARCHAR(50),
            birth_date TIMESTAMP,
            birth_place VARCHAR(50),
            gender VARCHAR(50),
            mobile_phone VARCHAR(50),
            admission_date TIMESTAMP,
            test_type VARCHAR(50),
            result VARCHAR(100),
            result1 VARCHAR(100),
            admitted_to_puc VARCHAR(50),
            notes VARCHAR(200),
            back_color VARCHAR(50),
            fore_color VARCHAR(100),
            class_time VARCHAR(50),
            program DOUBLE PRECISION,
            overall_time VARCHAR(10),
            admitted VARCHAR(3),
            first_pay_date VARCHAR(100),
            rec_id DOUBLE PRECISION,
            receipt_id VARCHAR(250),
            owner DOUBLE PRECISION,
            add_time TIMESTAMP,
            last_access_user DOUBLE PRECISION,
            last_modify_user DOUBLE PRECISION,
            last_modify_time TIMESTAMP,
            last_access_time TIMESTAMP,
            refunded INTEGER,
            ipk INTEGER,
            csv_row_number INTEGER,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """

        with connection.cursor() as cursor:
            cursor.execute(create_table_sql)

        self.stdout.write("Created legacy_et_results table")

    def import_validated_records(self, records: list[ETResultRecord]) -> int:
        """Import validated records to the database."""
        if not records:
            return 0

        insert_sql = """
        INSERT INTO legacy_et_results (
            term_id, serial_id, id, name, birth_date, birth_place, gender, mobile_phone,
            admission_date, test_type, result, result1, admitted_to_puc, notes,
            back_color, fore_color, class_time, program, overall_time, admitted,
            first_pay_date, rec_id, receipt_id, owner, add_time, last_access_user,
            last_modify_user, last_modify_time, last_access_time, refunded, ipk,
            csv_row_number
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """

        # Prepare batch data
        batch_data = []
        for record in records:
            row_data = (
                record.term_id,
                record.serial_id,
                record.id,
                record.name,
                record.birth_date,
                record.birth_place,
                record.gender,
                record.mobile_phone,
                record.admission_date,
                record.test_type,
                record.result,
                record.result1,
                record.admitted_to_puc,
                record.notes,
                record.back_color,
                record.fore_color,
                record.class_time,
                record.program,
                record.overall_time,
                record.admitted,
                record.first_pay_date,
                record.rec_id,
                record.receipt_id,
                record.owner,
                record.add_time,
                record.last_access_user,
                record.last_modify_user,
                record.last_modify_time,
                record.last_access_time,
                record.refunded,
                record.ipk,
                record.csv_row_number,
            )
            batch_data.append(row_data)

        # Execute batch insert
        with connection.cursor() as cursor:
            cursor.executemany(insert_sql, batch_data)

        return len(records)
