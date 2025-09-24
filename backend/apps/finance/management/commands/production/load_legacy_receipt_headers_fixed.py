"""Load legacy receipt headers data with Pydantic validation based on SQL Server DDL.

PRODUCTION LOADER - Validated data import for financial records with EXACT DDL specifications
"""

import csv
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection
from pydantic import BaseModel, Field, field_validator


class LegacyReceiptHeader(BaseModel):
    """Pydantic model for legacy receipt headers data validation based on SQL Server DDL.

    This represents payment/receipt records from the legacy system with EXACT field lengths.
    """

    # Student and term info - FIXED LENGTHS
    id: str | None = Field(None, max_length=10, description="Student ID (5 digits, left padded)")
    termid: str | None = Field(None, max_length=50, description="Term ID")
    program: float | None = Field(None, description="Program code")

    # Receipt identifiers
    intreceiptno: float | None = Field(None, description="Internal receipt number")
    receiptno: str | None = Field(None, max_length=150, description="Receipt number")
    receiptid: str | None = Field(None, max_length=250, description="Receipt ID")

    # Payment info
    pmtdate: datetime | None = Field(None, description="Payment date")
    amount: float | None = Field(None, description="Payment amount")
    netamount: float | None = Field(None, description="Net amount after discounts")
    netdiscount: float | None = Field(None, description="Net discount amount")
    scholargrant: float | None = Field(None, description="Scholarship/grant amount")
    balance: float | None = Field(None, description="Remaining balance")

    # Receipt metadata - FIXED LENGTHS
    termname: str | None = Field(None, max_length=80, description="Term name/description")
    receipttype: str | None = Field(None, max_length=50, description="Type of receipt")
    notes: str | None = Field(None, max_length=4000, description="Receipt notes - contains discount reasons")

    # System fields
    receiver: float | None = Field(None, description="Receiver/cashier ID")
    deleted: int | None = Field(None, description="Soft delete flag")
    name: str | None = Field(None, max_length=100, description="Student name")
    recid: str | None = Field(None, max_length=150, description="Record ID")

    # Additional fees/deductions
    otherdeduct: float | None = Field(None, description="Other deductions")
    latefee: float | None = Field(None, description="Late fee amount")
    prepaidfee: float | None = Field(None, description="Prepaid fee amount")

    # Payment details
    pmttype: str | None = Field(None, max_length=50, description="Payment type (cash/check/etc)")
    checkno: str | None = Field(None, max_length=50, description="Check number if applicable")

    # Student info - FIXED LENGTHS
    gender: str | None = Field(None, max_length=10, description="Student gender - includes 'Monk'")
    curlevel: float | None = Field(None, description="Current level")

    # Transaction info - FIXED LENGTHS
    cash_received: int | None = Field(None, description="Cash received flag")
    transtype: str | None = Field(None, max_length=50, description="Transaction type")

    # Primary key
    ipk: int = Field(..., description="Internal primary key")

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

    @field_validator("pmtdate", mode="before")
    @classmethod
    def parse_payment_date(cls, v):
        """Parse payment date from various formats."""
        if isinstance(v, datetime):
            return v
        if v and v not in ["NULL", "null", ""]:
            try:
                # Try common datetime formats
                return datetime.strptime(v.split(".")[0], "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    return datetime.strptime(v, "%Y-%m-%d")
                except ValueError:
                    return None
        return None

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, v: str | None) -> str | None:
        """Validate notes field - critical for discount analysis."""
        if v and v not in ["NULL", "null", ""]:
            # Notes often contain discount reasons - preserve them carefully
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
    """PRODUCTION LOADER - Load legacy receipt headers data with EXACT DDL validation."""

    help = "PRODUCTION: Load legacy receipt headers (payment records) from CSV with exact DDL field validation"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/legacy/all_receipt_headers_250802.csv",
            help="Path to receipt headers CSV file",
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
        self.stdout.write("Loading financial receipt records with exact SQL Server DDL specifications")

        # Create table
        if options["drop_existing"]:
            self._drop_table()
        self._create_table()

        # Load data
        success_count = 0
        error_count = 0
        batch_data = []

        # Track financial statistics
        total_amount = Decimal("0.00")
        total_discount = Decimal("0.00")
        total_scholarship = Decimal("0.00")
        payment_types = {}
        discount_notes_sample = []
        error_details = []

        self.stdout.write(f"Loading receipt headers from {file_path}")

        with open(file_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2):
                try:
                    # Create Pydantic model for validation
                    receipt_data = {key.lower().replace("_", ""): value for key, value in row.items()}

                    # Validate with Pydantic
                    receipt = LegacyReceiptHeader(**receipt_data)

                    # Collect financial statistics
                    if receipt.amount:
                        total_amount += Decimal(str(receipt.amount))
                    if receipt.netdiscount:
                        total_discount += Decimal(str(receipt.netdiscount))
                    if receipt.scholargrant:
                        total_scholarship += Decimal(str(receipt.scholargrant))

                    if receipt.pmttype:
                        payment_types[receipt.pmttype] = payment_types.get(receipt.pmttype, 0) + 1

                    # Collect discount note samples
                    if receipt.notes and receipt.netdiscount and len(discount_notes_sample) < 20:
                        discount_notes_sample.append(
                            {
                                "receipt_no": receipt.receiptno,
                                "discount": receipt.netdiscount,
                                "notes": receipt.notes[:100],  # First 100 chars
                            }
                        )

                    # Add to batch
                    batch_data.append(receipt.model_dump())

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
                        "receipt": row.get("ReceiptNo", "N/A"),
                        "ipk": row.get("IPK", "N/A"),
                    }
                    error_details.append(error_detail)

                    if error_count <= 10:
                        self.stdout.write(
                            self.style.ERROR(
                                f"Row {row_num}: {e!s} - ID: {row.get('ID', 'N/A')}, "
                                f"Receipt: {row.get('ReceiptNo', 'N/A')}"
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
            error_log_path = Path("receipt_headers_errors.log")
            with open(error_log_path, "w") as f:
                f.write(f"Total errors: {error_count}\n\n")
                for error in error_details[:1000]:  # First 1000 errors
                    f.write(f"Row {error['row']}: {error['error']}\n")
                    f.write(f"  ID: {error['id']}, Receipt: {error['receipt']}, IPK: {error['ipk']}\n\n")
            self.stdout.write(f"Error details written to {error_log_path}")

        # Report financial statistics
        self.stdout.write("\n=== FINANCIAL SUMMARY ===")
        self.stdout.write(f"Total Amount: ${total_amount:,.2f}")
        self.stdout.write(f"Total Discounts: ${total_discount:,.2f}")
        self.stdout.write(f"Total Scholarships: ${total_scholarship:,.2f}")

        self.stdout.write("\n=== PAYMENT TYPES ===")
        for pmt_type, count in sorted(payment_types.items(), key=lambda x: x[1], reverse=True)[:10]:
            self.stdout.write(f"{pmt_type}: {count:,} receipts")

        self.stdout.write("\n=== SAMPLE DISCOUNT NOTES (for pricing analysis) ===")
        for sample in discount_notes_sample[:10]:
            self.stdout.write(f"Receipt {sample['receipt_no']}: ${sample['discount']:.2f} - {sample['notes']}")

    def _drop_table(self):
        """Drop existing table."""
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS legacy_receipt_headers CASCADE")
            self.stdout.write("Dropped existing legacy_receipt_headers table")

    def _create_table(self):
        """Create legacy_receipt_headers table based on EXACT SQL Server DDL."""
        create_sql = """
        CREATE TABLE IF NOT EXISTS legacy_receipt_headers (
            id VARCHAR(10),                    -- FIXED: was 50, now 10
            termid VARCHAR(50),                -- FIXED: was 100, now 50
            program FLOAT,
            intreceiptno FLOAT,
            receiptno VARCHAR(150),
            receiptid VARCHAR(250),
            pmtdate TIMESTAMP,
            amount FLOAT,
            netamount FLOAT,
            netdiscount FLOAT,
            scholargrant FLOAT,
            balance FLOAT,
            termname VARCHAR(80),
            receipttype VARCHAR(50),           -- FIXED: was 100, now 50
            notes VARCHAR(4000),               -- FIXED: was 500, now 4000
            receiver FLOAT,
            deleted INTEGER,
            name VARCHAR(100),                 -- FIXED: was 120, now 100
            recid VARCHAR(150),
            otherdeduct FLOAT,
            latefee FLOAT,
            prepaidfee FLOAT,
            pmttype VARCHAR(50),
            checkno VARCHAR(50),
            gender VARCHAR(10),                -- Needs to accommodate 'Monk' value
            curlevel FLOAT,
            cash_received INTEGER,
            transtype VARCHAR(50),             -- FIXED: was 100, now 50
            ipk INTEGER PRIMARY KEY,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        -- Critical indexes for financial analysis
        CREATE INDEX idx_legacy_rh_student_id ON legacy_receipt_headers(id);
        CREATE INDEX idx_legacy_rh_termid ON legacy_receipt_headers(termid);
        CREATE INDEX idx_legacy_rh_receiptno ON legacy_receipt_headers(receiptno);
        CREATE INDEX idx_legacy_rh_pmtdate ON legacy_receipt_headers(pmtdate);
        CREATE INDEX idx_legacy_rh_deleted ON legacy_receipt_headers(deleted);
        CREATE INDEX idx_legacy_rh_pmttype ON legacy_receipt_headers(pmttype);

        -- Financial analysis indexes
        CREATE INDEX idx_legacy_rh_financial ON legacy_receipt_headers(amount, netdiscount, scholargrant);
        CREATE INDEX idx_legacy_rh_discount_analysis ON legacy_receipt_headers(netdiscount)
            WHERE netdiscount > 0 AND notes IS NOT NULL;
        """

        with connection.cursor() as cursor:
            cursor.execute(create_sql)
            self.stdout.write("Created legacy_receipt_headers table with EXACT DDL specifications")

    def _insert_batch(self, batch_data):
        """Insert a batch of receipt records."""
        if not batch_data:
            return

        # Get column names from first record
        columns = list(batch_data[0].keys())
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
