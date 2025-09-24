"""Load only payment data from legacy CSV for A/R reconstruction."""

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    """Load only legacy payment data for A/R reconstruction."""

    help = "Load legacy payment data (receipts) from CSV"

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, help="Limit number of records to process (for testing)")

    def handle(self, *args, **options):
        """Main command handler."""

        data_dir = Path("data/legacy")
        payments_file = data_dir / "all_receipt_headers_250728.csv"

        if not payments_file.exists():
            self.stdout.write(self.style.ERROR(f"Payment file not found: {payments_file}"))
            return

        # Recreate payments table with correct schema
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE IF EXISTS legacy_payments")
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
            self.stdout.write("Recreated legacy_payments table with correct schema")

        # Load payments
        self._load_payments(payments_file, options.get("limit"))

        # Show summary
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM legacy_payments")
            count = cursor.fetchone()[0]
            self.stdout.write(self.style.SUCCESS(f"Loaded {count:,} payment records"))

    def _load_payments(self, filepath, limit=None):
        """Load payment data from CSV."""
        self.stdout.write(f"Loading payments from {filepath.name}...")

        with open(filepath, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            batch_data = []
            batch_size = 1000
            count = 0
            errors = 0

            for row in reader:
                # Apply limit if specified
                if limit and count >= limit:
                    break

                try:
                    # Skip deleted payments
                    if row.get("Deleted") == "1":
                        continue

                    # Handle student ID (numeric and non-numeric)
                    raw_id = row.get("ID", "").strip()
                    if raw_id.isdigit():
                        student_id = raw_id.zfill(5)  # Zero-pad numeric IDs
                    else:
                        student_id = raw_id  # Keep non-numeric IDs as-is

                    # Handle NULL/empty amounts
                    amount_str = row.get("Amount", "0")
                    if amount_str == "NULL" or not amount_str:
                        amount = Decimal("0")
                    else:
                        try:
                            amount = Decimal(amount_str)
                        except (ValueError, TypeError, InvalidOperation):
                            amount = Decimal("0")

                    # Handle NULL payment date
                    pmt_date = row.get("PmtDate")
                    if pmt_date == "NULL" or not pmt_date:
                        pmt_date = None

                    # Prepare data for batch insert
                    batch_data.append(
                        [
                            row.get("ReceiptID", ""),
                            student_id,
                            row.get("TermID", ""),
                            amount,
                            pmt_date,
                            row.get("Deleted") == "1",
                        ]
                    )

                    count += 1

                    # Insert in batches
                    if len(batch_data) >= batch_size:
                        self._insert_batch(batch_data)
                        self.stdout.write(f"  Inserted {count:,} payments...")
                        batch_data = []

                except Exception as e:
                    errors += 1
                    if errors <= 5:  # Only show first 5 errors
                        self.stdout.write(self.style.WARNING(f"Payment error: {e!s}"))
                    continue

            # Insert remaining data
            if batch_data:
                self._insert_batch(batch_data)

            self.stdout.write(f"Processed {count:,} payments with {errors} errors")

    def _insert_batch(self, batch_data):
        """Insert batch of payment data."""
        with connection.cursor() as cursor:
            cursor.executemany(
                """
                INSERT INTO legacy_payments
                (receipt_id, student_id, term_id, amount, payment_date, deleted)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (receipt_id) DO NOTHING
            """,
                batch_data,
            )
