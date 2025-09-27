"""Django management command to import legacy courses data from leg_courses.csv.

Maps MSSQL table structure to PostgreSQL equivalent
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


class Command(BaseCommand):
    help = "Import legacy courses data from leg_courses.csv into PostgreSQL"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/legacy/leg_courses.csv",
            help="Path to the CSV file with legacy courses data",
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

    def handle(self, *args, **options):
        file_path = options["file"]

        dry_run = options["dry_run"]

        drop_table = options["drop_table"]

        self.stdout.write(f"Processing legacy courses file: {file_path}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No data will be modified"))

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
                            if not dry_run:
                                self._insert_course_record(row)

                            else:
                                self._validate_course_record(row)

                            imported_count += 1

                            if row_num % 100 == 0:
                                self.stdout.write(f"Processed {row_num} rows...")

                        except Exception as e:
                            error_msg = f"Row {row_num}: {e!s} - Data: {row}"

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

        if dry_run:
            self.stdout.write(self.style.SUCCESS(f"DRY RUN: Would import {imported_count} course records"))

        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully imported {imported_count} course records"))

    def _create_table(self, drop_table):
        """Create the legacy courses table in PostgreSQL."""
        drop_sql = """

        DROP TABLE IF EXISTS legacy_courses;

        """

        create_sql = """

        CREATE TABLE legacy_courses (

            ipk INTEGER PRIMARY KEY,

            course_code VARCHAR(100),

            course_title VARCHAR(255),

            course_type VARCHAR(50),

            description VARCHAR(255),

            lec_hour INTEGER,

            lab_hour INTEGER,

            fore_col VARCHAR(20),

            credit VARCHAR(5),

            is_academic INTEGER,

            short_course_title VARCHAR(50),

            bad INTEGER,

            fin INTEGER,

            tou INTEGER,

            int INTEGER,

            tes INTEGER,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        );



        CREATE INDEX idx_legacy_courses_code ON legacy_courses(course_code);

        CREATE INDEX idx_legacy_courses_academic ON legacy_courses(is_academic);

        CREATE INDEX idx_legacy_courses_majors ON legacy_courses(bad, fin, tou, int, tes);

        """

        with connection.cursor() as cursor:
            if drop_table:
                cursor.execute(drop_sql)

                self.stdout.write(self.style.SUCCESS("Dropped existing legacy_courses table"))

            cursor.execute(create_sql)

            self.stdout.write(self.style.SUCCESS("Created legacy_courses table"))

    def _validate_course_record(self, row):
        """Validate a CSV row without inserting."""
        required_fields = ["CourseCode", "IPK"]

        for field in required_fields:
            if not row.get(field):
                msg = f"Missing required field: {field}"

                raise ValueError(msg)

        # Validate IPK is numeric

        try:
            int(row["IPK"])

        except (ValueError, TypeError) as e:
            msg = f"IPK must be numeric: {row['IPK']}"

            raise ValueError(msg) from e

    def _insert_course_record(self, row):
        """Insert a course record into the database."""

        def clean_value(value, field_type="string"):
            """Clean CSV values, handling NULL and empty strings."""
            if value in ("NULL", "", None):
                return None

            if field_type == "integer":
                try:
                    return int(value) if value else None

                except (ValueError, TypeError):
                    return None

            return value.strip() if value else None

        # Map CSV columns to database columns

        course_data = {
            "ipk": clean_value(row["IPK"], "integer"),
            "course_code": clean_value(row["CourseCode"]),
            "course_title": clean_value(row["CourseTitle"]),
            "course_type": clean_value(row["CourseType"]),
            "description": clean_value(row["Description"]),
            "lec_hour": clean_value(row["LecHour"], "integer"),
            "lab_hour": clean_value(row["LabHour"], "integer"),
            "fore_col": clean_value(row["ForeCol"]),
            "credit": clean_value(row["Credit"]),
            "is_academic": clean_value(row["isAcademic"], "integer"),
            "short_course_title": clean_value(row["ShortCourseTitle"]),
            "bad": clean_value(row["BAD"], "integer"),
            "fin": clean_value(row["FIN"], "integer"),
            "tou": clean_value(row["TOU"], "integer"),
            "int": clean_value(row["INT"], "integer"),
            "tes": clean_value(row["TES"], "integer"),
        }

        # Insert the record

        insert_sql = """

        INSERT INTO legacy_courses (

            ipk, course_code, course_title, course_type, description,

            lec_hour, lab_hour, fore_col, credit, is_academic,

            short_course_title, bad, fin, tou, int, tes

        ) VALUES (

            %(ipk)s, %(course_code)s, %(course_title)s, %(course_type)s, %(description)s,

            %(lec_hour)s, %(lab_hour)s, %(fore_col)s, %(credit)s, %(is_academic)s,

            %(short_course_title)s, %(bad)s, %(fin)s, %(tou)s, %(int)s, %(tes)s

        )

        """

        with connection.cursor() as cursor:
            cursor.execute(insert_sql, course_data)
