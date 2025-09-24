"""Django management command to import legacy receipt headers data from
leg_receipt_headers.csv.

Contains payment/receipt header information
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils.dateparse import parse_datetime


class Command(BaseCommand):
    help = "Import legacy receipt headers data from leg_receipt_headers.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/legacy/leg_receipt_headers.csv",
            help="Path to the CSV file with legacy receipt headers data",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without actually importing",
        )

        parser.add_argument(
            "--drop-table",
            action="store_true",
            help="Drop existing table before creating new one",
        )

        parser.add_argument("--limit", type=int, help="Limit number of records to import (for testing)")

    def handle(self, *args, **options):
        file_path = options["file"]

        dry_run = options["dry_run"]

        drop_table = options["drop_table"]

        limit = options.get("limit")

        self.stdout.write(f"Processing legacy receipt headers file: {file_path}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No data will be modified"))

        if limit:
            self.stdout.write(f"Limiting import to {limit} records")

        # Create the table

        if not dry_run:
            self._create_table(drop_table)

        # Import the data

        imported_count = 0

        errors = []

        try:
            with Path(file_path).open(encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)

                with transaction.atomic():
                    for row_num, row in enumerate(reader, start=2):
                        try:
                            if limit and row_num > limit + 1:
                                break

                            if not dry_run:
                                self._insert_record(row)

                            else:
                                self._validate_record(row)

                            imported_count += 1

                            if row_num % 2000 == 0:
                                self.stdout.write(f"Processed {row_num} rows...")

                        except Exception as e:
                            error_msg = f"Row {row_num}: {e!s} - ID: {row.get('ID', 'N/A')}"

                            errors.append(error_msg)

                            if len(errors) > 20:
                                break

        except FileNotFoundError:
            msg = f"File not found: {file_path}"

            raise CommandError(msg) from None

        except Exception as e:
            msg = f"Error processing file: {e!s}"

            raise CommandError(msg) from e

        # Report results

        if errors:
            self.stdout.write(self.style.ERROR(f"Encountered {len(errors)} errors:"))

            for error in errors[:10]:
                self.stdout.write(self.style.ERROR(f"  {error}"))

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"DRY RUN: Would import {imported_count} receipt header records"))

        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully imported {imported_count} receipt header records"))

    def _create_table(self, drop_table):
        """Create the legacy receipt headers table in PostgreSQL."""
        drop_sql = """

        DROP TABLE IF EXISTS legacy_receipt_headers;

        """

        create_sql = """

        CREATE TABLE legacy_receipt_headers (

            ipk INTEGER PRIMARY KEY,

            student_id VARCHAR(50),

            term_id VARCHAR(100),

            program DECIMAL(10,2),

            int_receipt_no DECIMAL(10,2),

            receipt_no VARCHAR(150),

            receipt_id VARCHAR(250),

            pmt_date TIMESTAMP,

            amount DECIMAL(10,2),

            net_amount DECIMAL(10,2),

            net_discount DECIMAL(10,2),

            scholar_grant DECIMAL(10,2),

            balance DECIMAL(10,2),

            term_name VARCHAR(80),

            receipt_type VARCHAR(100),

            notes VARCHAR(500),

            receiver DECIMAL(10,2),

            deleted INTEGER,

            name VARCHAR(120),

            rec_id VARCHAR(150),

            other_deduct DECIMAL(10,2),

            late_fee DECIMAL(10,2),

            prepaid_fee DECIMAL(10,2),

            pmt_type VARCHAR(50),

            check_no VARCHAR(50),

            gender VARCHAR(10),

            cur_level DECIMAL(10,2),

            cash_received INTEGER,

            trans_type VARCHAR(100),

            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        );



        CREATE INDEX idx_legacy_rh_student_id ON legacy_receipt_headers(student_id);

        CREATE INDEX idx_legacy_rh_term_id ON legacy_receipt_headers(term_id);

        CREATE INDEX idx_legacy_rh_receipt_no ON legacy_receipt_headers(receipt_no);

        CREATE INDEX idx_legacy_rh_pmt_date ON legacy_receipt_headers(pmt_date);

        CREATE INDEX idx_legacy_rh_deleted ON legacy_receipt_headers(deleted);

        """

        with connection.cursor() as cursor:
            if drop_table:
                cursor.execute(drop_sql)

                self.stdout.write(self.style.SUCCESS("Dropped existing legacy_receipt_headers table"))

            cursor.execute(create_sql)

            self.stdout.write(self.style.SUCCESS("Created legacy_receipt_headers table"))

    def _validate_record(self, row):
        """Validate a CSV row without inserting."""
        required_fields = ["ID", "IPK"]

        for field in required_fields:
            if not row.get(field):
                msg = f"Missing required field: {field}"

                raise ValueError(msg)

    def _insert_record(self, row):
        """Insert a record into the database."""

        def clean_value(value, field_type="string"):
            """Clean CSV values, handling NULL and empty strings."""
            if value in ("NULL", "", None, "null"):
                return None

            if field_type == "integer":
                try:
                    return int(float(value)) if value else None

                except (ValueError, TypeError):
                    return None

            elif field_type == "decimal":
                try:
                    return float(value) if value else None

                except (ValueError, TypeError):
                    return None

            elif field_type == "datetime":
                if value:
                    try:
                        return parse_datetime(value)

                    except (ValueError, TypeError):
                        return None

                return None

            return value.strip() if value else None

        # Map CSV columns to database columns

        record_data = {
            "ipk": clean_value(row["IPK"], "integer"),
            "student_id": clean_value(row["ID"]),
            "term_id": clean_value(row["TermID"]),
            "program": clean_value(row["Program"], "decimal"),
            "int_receipt_no": clean_value(row["IntReceiptNo"], "decimal"),
            "receipt_no": clean_value(row["ReceiptNo"]),
            "receipt_id": clean_value(row["ReceiptID"]),
            "pmt_date": clean_value(row["PmtDate"], "datetime"),
            "amount": clean_value(row["Amount"], "decimal"),
            "net_amount": clean_value(row["NetAmount"], "decimal"),
            "net_discount": clean_value(row["NetDiscount"], "decimal"),
            "scholar_grant": clean_value(row["ScholarGrant"], "decimal"),
            "balance": clean_value(row["Balance"], "decimal"),
            "term_name": clean_value(row["TermName"]),
            "receipt_type": clean_value(row["ReceiptType"]),
            "notes": clean_value(row["Notes"]),
            "receiver": clean_value(row["Receiver"], "decimal"),
            "deleted": clean_value(row["Deleted"], "integer"),
            "name": clean_value(row["name"]),
            "rec_id": clean_value(row["recID"]),
            "other_deduct": clean_value(row["OtherDeduct"], "decimal"),
            "late_fee": clean_value(row["LateFee"], "decimal"),
            "prepaid_fee": clean_value(row["PrepaidFee"], "decimal"),
            "pmt_type": clean_value(row["PmtType"]),
            "check_no": clean_value(row["CheckNo"]),
            "gender": clean_value(row["Gender"]),
            "cur_level": clean_value(row["CurLevel"], "decimal"),
            "cash_received": clean_value(row["Cash_received"], "integer"),
            "trans_type": clean_value(row["TransType"]),
        }

        # Insert the record

        insert_sql = """

        INSERT INTO legacy_receipt_headers (

            ipk, student_id, term_id, program, int_receipt_no, receipt_no,

            receipt_id, pmt_date, amount, net_amount, net_discount, scholar_grant,

            balance, term_name, receipt_type, notes, receiver, deleted, name,

            rec_id, other_deduct, late_fee, prepaid_fee, pmt_type, check_no,

            gender, cur_level, cash_received, trans_type

        ) VALUES (

            %(ipk)s, %(student_id)s, %(term_id)s, %(program)s, %(int_receipt_no)s,

            %(receipt_no)s, %(receipt_id)s, %(pmt_date)s, %(amount)s, %(net_amount)s,

            %(net_discount)s, %(scholar_grant)s, %(balance)s, %(term_name)s,

            %(receipt_type)s, %(notes)s, %(receiver)s, %(deleted)s, %(name)s,

            %(rec_id)s, %(other_deduct)s, %(late_fee)s, %(prepaid_fee)s,

            %(pmt_type)s, %(check_no)s, %(gender)s, %(cur_level)s,

            %(cash_received)s, %(trans_type)s

        )

        """

        with connection.cursor() as cursor:
            cursor.execute(insert_sql, record_data)
