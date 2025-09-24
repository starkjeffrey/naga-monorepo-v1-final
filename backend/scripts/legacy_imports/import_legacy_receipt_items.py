"""Django management command to import legacy receipt items data from
leg_receipt_items.csv.

Contains late fee data
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils.dateparse import parse_datetime


class Command(BaseCommand):
    help = "Import legacy receipt items data from leg_receipt_items.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/legacy/leg_receipt_items.csv",
            help="Path to the CSV file with legacy receipt items data",
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

        self.stdout.write(f"Processing legacy receipt items file: {file_path}")

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
                            error_msg = f"Row {row_num}: {e!s} - ID: {row.get('IPK', 'N/A')}"

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
            self.stdout.write(self.style.SUCCESS(f"DRY RUN: Would import {imported_count} receipt item records"))

        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully imported {imported_count} receipt item records"))

    def _create_table(self, drop_table):
        """Create the legacy receipt items table in PostgreSQL."""
        drop_sql = """

        DROP TABLE IF EXISTS legacy_receipt_items;

        """

        create_sql = """

        CREATE TABLE legacy_receipt_items (

            ipk INTEGER PRIMARY KEY,

            term_id VARCHAR(100),

            program DECIMAL(10,2),

            student_id VARCHAR(50),

            receipt_no VARCHAR(150),

            receipt_id VARCHAR(250),

            item VARCHAR(255),

            unit_cost DECIMAL(10,2),

            quantity VARCHAR(50),

            discount DECIMAL(10,2),

            amount DECIMAL(10,2),

            notes VARCHAR(500),

            deleted INTEGER,

            rec_id VARCHAR(150),

            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        );



        CREATE INDEX idx_legacy_ri_student_id ON legacy_receipt_items(student_id);

        CREATE INDEX idx_legacy_ri_receipt_no ON legacy_receipt_items(receipt_no);

        CREATE INDEX idx_legacy_ri_term_id ON legacy_receipt_items(term_id);

        CREATE INDEX idx_legacy_ri_item ON legacy_receipt_items(item);

        """

        with connection.cursor() as cursor:
            if drop_table:
                cursor.execute(drop_sql)

                self.stdout.write(self.style.SUCCESS("Dropped existing legacy_receipt_items table"))

            cursor.execute(create_sql)

            self.stdout.write(self.style.SUCCESS("Created legacy_receipt_items table"))

    def _validate_record(self, row):
        """Validate a CSV row without inserting."""
        required_fields = ["IPK"]

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
            "term_id": clean_value(row["TermID"]),
            "program": clean_value(row["Program"], "decimal"),
            "student_id": clean_value(row["ID"]),
            "receipt_no": clean_value(row["ReceiptNo"]),
            "receipt_id": clean_value(row["ReceiptID"]),
            "item": clean_value(row["Item"]),
            "unit_cost": clean_value(row["UnitCost"], "decimal"),
            "quantity": clean_value(row["Quantity"]),
            "discount": clean_value(row["Discount"], "decimal"),
            "amount": clean_value(row["Amount"], "decimal"),
            "notes": clean_value(row["Notes"]),
            "deleted": clean_value(row["Deleted"], "integer"),
            "rec_id": clean_value(row["recID"]),
        }

        # Insert the record

        insert_sql = """

        INSERT INTO legacy_receipt_items (

            ipk, term_id, program, student_id, receipt_no, receipt_id,

            item, unit_cost, quantity, discount, amount, notes, deleted, rec_id

        ) VALUES (

            %(ipk)s, %(term_id)s, %(program)s, %(student_id)s, %(receipt_no)s,

            %(receipt_id)s, %(item)s, %(unit_cost)s, %(quantity)s, %(discount)s,

            %(amount)s, %(notes)s, %(deleted)s, %(rec_id)s

        )

        """

        with connection.cursor() as cursor:
            cursor.execute(insert_sql, record_data)
