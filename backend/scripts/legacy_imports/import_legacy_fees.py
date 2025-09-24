"""Django management command to import legacy fees data from leg_fees.csv.

Contains historical pricing structure for BA courses and fees
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils.dateparse import parse_datetime


class Command(BaseCommand):
    help = "Import legacy fees data from leg_fees.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/legacy/leg_fees.csv",
            help="Path to the CSV file with legacy fees data",
        )

        parser.add_argument(
            "--drop-table",
            action="store_true",
            help="Drop existing table before creating new one",
        )

    def handle(self, *args, **options):
        file_path = options["file"]

        drop_table = options["drop_table"]

        self.stdout.write(f"Processing legacy fees file: {file_path}")

        # Create the table

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
                            self._insert_record(row)

                            imported_count += 1

                        except Exception as e:
                            error_msg = f"Row {row_num}: {e!s}"

                            errors.append(error_msg)

                            if len(errors) > 10:
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

            for error in errors[:5]:
                self.stdout.write(self.style.ERROR(f"  {error}"))

        self.stdout.write(self.style.SUCCESS(f"Successfully imported {imported_count} fee records"))

    def _create_table(self, drop_table):
        """Create the legacy fees table in PostgreSQL."""
        drop_sql = """

        DROP TABLE IF EXISTS legacy_fees;

        """

        create_sql = """

        CREATE TABLE legacy_fees (

            effective_date TIMESTAMP,

            effective_term_id VARCHAR(50),

            detail VARCHAR(50),

            fixed_var VARCHAR(10),

            type VARCHAR(20),

            short_desc VARCHAR(100),

            local DECIMAL(10,2),

            foreign DECIMAL(10,2),

            pay_advisors DECIMAL(10,2),

            pay_committee DECIMAL(10,2),

            student_min INTEGER,

            student_max INTEGER,

            is_valid INTEGER,

            credits INTEGER,

            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        );



        CREATE INDEX idx_legacy_fees_date ON legacy_fees(effective_date);

        CREATE INDEX idx_legacy_fees_term ON legacy_fees(effective_term_id);

        CREATE INDEX idx_legacy_fees_detail ON legacy_fees(detail);

        CREATE INDEX idx_legacy_fees_type ON legacy_fees(type);

        """

        with connection.cursor() as cursor:
            if drop_table:
                cursor.execute(drop_sql)

                self.stdout.write(self.style.SUCCESS("Dropped existing legacy_fees table"))

            cursor.execute(create_sql)

            self.stdout.write(self.style.SUCCESS("Created legacy_fees table"))

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
            "effective_date": clean_value(row["EffectiveDate"], "datetime"),
            "effective_term_id": clean_value(row["EffectiveTermid"]),
            "detail": clean_value(row["Detail"]),
            "fixed_var": clean_value(row["FixedVar"]),
            "type": clean_value(row["Type"]),
            "short_desc": clean_value(row["ShortDesc"]),
            "local": clean_value(row["Local"], "decimal"),
            "foreign": clean_value(row["Foreign"], "decimal"),
            "pay_advisors": clean_value(row["PayAdvisors"], "decimal"),
            "pay_committee": clean_value(row["PayCommittee"], "decimal"),
            "student_min": clean_value(row["StudentMin"], "integer"),
            "student_max": clean_value(row["StudentMax"], "integer"),
            "is_valid": clean_value(row["Is_valid"], "integer"),
            "credits": clean_value(row["credits"], "integer"),
        }

        # Insert the record

        insert_sql = """

        INSERT INTO legacy_fees (

            effective_date, effective_term_id, detail, fixed_var, type, short_desc,

            local, foreign, pay_advisors, pay_committee, student_min, student_max,

            is_valid, credits

        ) VALUES (

            %(effective_date)s, %(effective_term_id)s, %(detail)s, %(fixed_var)s,

            %(type)s, %(short_desc)s, %(local)s, %(foreign)s, %(pay_advisors)s,

            %(pay_committee)s, %(student_min)s, %(student_max)s, %(is_valid)s,

            %(credits)s

        )

        """

        with connection.cursor() as cursor:
            cursor.execute(insert_sql, record_data)
