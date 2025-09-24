"""Django management command to import legacy students data from leg_students.csv.

Contains complete student demographic and profile information
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils.dateparse import parse_date, parse_datetime


class Command(BaseCommand):
    help = "Import legacy students data from leg_students.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/legacy/leg_students.csv",
            help="Path to the CSV file with legacy students data",
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

        self.stdout.write(f"Processing legacy students file: {file_path}")

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
            self.stdout.write(self.style.SUCCESS(f"DRY RUN: Would import {imported_count} student records"))

        else:
            self.stdout.write(self.style.SUCCESS(f"Successfully imported {imported_count} student records"))

    def _create_table(self, drop_table):
        """Create the legacy students table in PostgreSQL."""
        drop_sql = """

        DROP TABLE IF EXISTS legacy_students;

        """

        create_sql = """

        CREATE TABLE legacy_students (

            student_id VARCHAR(10) PRIMARY KEY,

            name VARCHAR(200),

            khmer_name VARCHAR(200),

            birth_date TIMESTAMP,

            birth_place VARCHAR(100),

            gender VARCHAR(10),

            marital_status VARCHAR(20),

            nationality VARCHAR(50),

            home_address TEXT,

            home_phone VARCHAR(50),

            email VARCHAR(100),

            mobile_phone VARCHAR(50),

            emergency_contact VARCHAR(200),

            emergency_phone VARCHAR(100),

            current_program VARCHAR(100),

            selected_program VARCHAR(200),

            selected_major VARCHAR(200),

            selected_faculty VARCHAR(200),

            admission_date TIMESTAMP,

            graduation_date TIMESTAMP,

            ba_grad_date TIMESTAMP,

            ma_grad_date TIMESTAMP,

            first_term VARCHAR(50),

            paid_term VARCHAR(50),

            batch_id VARCHAR(50),

            status VARCHAR(50),

            school_email VARCHAR(100),

            notes TEXT,

            last_enroll TIMESTAMP,

            first_enroll TIMESTAMP,

            first_enroll_lang TIMESTAMP,

            first_enroll_ba TIMESTAMP,

            first_enroll_ma TIMESTAMP,

            transfer VARCHAR(50),

            deleted INTEGER,

            created_date TIMESTAMP,

            modified_date TIMESTAMP,

            ipk INTEGER,

            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        );



        CREATE INDEX idx_legacy_students_name ON legacy_students(name);

        CREATE INDEX idx_legacy_students_status ON legacy_students(status);

        CREATE INDEX idx_legacy_students_program ON legacy_students(current_program);

        CREATE INDEX idx_legacy_students_batch ON legacy_students(batch_id);

        """

        with connection.cursor() as cursor:
            if drop_table:
                cursor.execute(drop_sql)

                self.stdout.write(self.style.SUCCESS("Dropped existing legacy_students table"))

            cursor.execute(create_sql)

            self.stdout.write(self.style.SUCCESS("Created legacy_students table"))

    def _validate_record(self, row):
        """Validate a CSV row without inserting."""
        required_fields = ["ID"]

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

            elif field_type == "date":
                if value:
                    try:
                        return parse_date(value)

                    except (ValueError, TypeError):
                        return None

                return None

            elif field_type == "datetime":
                if value:
                    try:
                        return parse_datetime(value)

                    except (ValueError, TypeError):
                        return None

                return None

            return value.strip() if value else None

        # Map CSV columns to database columns based on actual CSV structure

        record_data = {
            "student_id": clean_value(row["ID"]),
            "name": clean_value(row["Name"]),
            "khmer_name": clean_value(row["KName"]),
            "birth_date": clean_value(row["BirthDate"], "datetime"),
            "birth_place": clean_value(row["BirthPlace"]),
            "gender": clean_value(row["Gender"]),
            "marital_status": clean_value(row["MaritalStatus"]),
            "nationality": clean_value(row["Nationality"]),
            "home_address": clean_value(row["HomeAddress"]),
            "home_phone": clean_value(row["HomePhone"]),
            "email": clean_value(row["Email"]),
            "mobile_phone": clean_value(row["MobilePhone"]),
            "emergency_contact": clean_value(row["Emg_ContactPerson"]),
            "emergency_phone": clean_value(row["ContactPersonPhone"]),
            "current_program": clean_value(row["CurrentProgram"]),
            "selected_program": clean_value(row["SelectedProgram"]),
            "selected_major": clean_value(row["SelectedMajor"]),
            "selected_faculty": clean_value(row["SelectedFaculty"]),
            "admission_date": clean_value(row["AdmissionDate"], "datetime"),
            "graduation_date": clean_value(row["GraduationDate"], "datetime"),
            "ba_grad_date": clean_value(row["BAGradDate"], "datetime"),
            "ma_grad_date": clean_value(row["MAGradDate"], "datetime"),
            "first_term": clean_value(row["FirstTerm"]),
            "paid_term": clean_value(row["PaidTerm"]),
            "batch_id": clean_value(row["BatchID"]),
            "status": clean_value(row["Status"]),
            "school_email": clean_value(row["SchoolEmail"]),
            "notes": clean_value(row["Notes"]),
            "last_enroll": clean_value(row["Lastenroll"], "datetime"),
            "first_enroll": clean_value(row["Firstenroll"], "datetime"),
            "first_enroll_lang": clean_value(row["Firstenroll_Lang"], "datetime"),
            "first_enroll_ba": clean_value(row["Firstenroll_BA"], "datetime"),
            "first_enroll_ma": clean_value(row["Firstenroll_MA"], "datetime"),
            "transfer": clean_value(row["Transfer"]),
            "deleted": clean_value(row["Deleted"], "integer"),
            "created_date": clean_value(row["CreatedDate"], "datetime"),
            "modified_date": clean_value(row["ModifiedDate"], "datetime"),
            "ipk": clean_value(row["IPK"], "integer"),
        }

        # Insert the record

        insert_sql = """

        INSERT INTO legacy_students (

            student_id, name, khmer_name, birth_date, birth_place, gender,

            marital_status, nationality, home_address, home_phone, email,

            mobile_phone, emergency_contact, emergency_phone, current_program,

            selected_program, selected_major, selected_faculty, admission_date,

            graduation_date, ba_grad_date, ma_grad_date, first_term, paid_term,

            batch_id, status, school_email, notes, last_enroll, first_enroll,

            first_enroll_lang, first_enroll_ba, first_enroll_ma, transfer,

            deleted, created_date, modified_date, ipk

        ) VALUES (

            %(student_id)s, %(name)s, %(khmer_name)s, %(birth_date)s, %(birth_place)s,

            %(gender)s, %(marital_status)s, %(nationality)s, %(home_address)s,

            %(home_phone)s, %(email)s, %(mobile_phone)s, %(emergency_contact)s,

            %(emergency_phone)s, %(current_program)s, %(selected_program)s,

            %(selected_major)s, %(selected_faculty)s, %(admission_date)s,

            %(graduation_date)s, %(ba_grad_date)s, %(ma_grad_date)s, %(first_term)s,

            %(paid_term)s, %(batch_id)s, %(status)s, %(school_email)s, %(notes)s,

            %(last_enroll)s, %(first_enroll)s, %(first_enroll_lang)s,

            %(first_enroll_ba)s, %(first_enroll_ma)s, %(transfer)s, %(deleted)s,

            %(created_date)s, %(modified_date)s, %(ipk)s

        )

        """

        with connection.cursor() as cursor:
            cursor.execute(insert_sql, record_data)
