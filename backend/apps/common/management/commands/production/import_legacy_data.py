"""from datetime import date
Django management command to import all legacy MSSQL CSV files into PostgreSQL.

This command creates separate legacy_* tables in PostgreSQL that are NOT part of
the Django SIS models. They are stored for convenience and migration analysis only.

The legacy tables created:
- legacy_students: Student demographic data from all_students_20250612.csv
- legacy_academiccoursetakers: Course enrollment data from all_academiccoursetakers_20250612.csv
- legacy_receipt_headers: Payment header data from all_receipt_headers_20250612.csv
- legacy_receipt_items: Payment line items from all_receipt_items_20250612.csv
- legacy_terms: Academic terms from all_terms_20250612.csv
- legacy_moodle: Moodle integration data from all_moo.csv
- legacy_fees: Fee structure data from leg_fees.csv
- legacy_ba_requirements: BA requirements from ba_req.csv

Usage:
    python manage.py import_legacy_data
    python manage.py import_legacy_data --drop-tables
    python manage.py import_legacy_data --dry-run
    python manage.py import_legacy_data --limit 1000
"""

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils.dateparse import parse_date, parse_datetime


class Command(BaseCommand):
    help = "Import all legacy MSSQL CSV files into PostgreSQL legacy_* tables"

    def add_arguments(self, parser):
        parser.add_argument(
            "--drop-tables",
            action="store_true",
            help="Drop existing legacy tables before importing",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without actually importing",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of records to import per table (for testing)",
        )
        parser.add_argument(
            "--table",
            type=str,
            help="Import only specific table (students, academiccoursetakers, etc.)",
        )

    def handle(self, *args, **options):
        self.dry_run = options["dry_run"]
        self.drop_tables = options["drop_tables"]
        self.limit = options.get("limit")
        self.single_table = options.get("table")

        self.stdout.write(self.style.SUCCESS("🚀 Starting legacy MSSQL data import..."))

        if self.dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No data will be modified"))

        if self.limit:
            self.stdout.write(f"Limiting import to {self.limit} records per table")

        # Define all legacy imports
        legacy_imports = [
            {
                "name": "students",
                "file": "data/migrate/all_students_250624.csv",
                "table": "legacy_students",
                "description": "Legacy Students",
            },
            {
                "name": "academiccoursetakers",
                "file": "data/migrate/all_academiccoursetakrers_250624.csv",
                "table": "legacy_academiccoursetakers",
                "description": "Legacy Academic Course Takers",
            },
            {
                "name": "receipt_headers",
                "file": "data/legacy/all_receipt_headers_20250612.csv",
                "table": "legacy_receipt_headers",
                "description": "Legacy Receipt Headers",
            },
            {
                "name": "receipt_items",
                "file": "data/legacy/all_receipt_items_20250612.csv",
                "table": "legacy_receipt_items",
                "description": "Legacy Receipt Items",
            },
            {
                "name": "terms",
                "file": "data/migrate/all_terms_250624.csv",
                "table": "legacy_terms",
                "description": "Legacy Terms",
            },
            {
                "name": "moodle",
                "file": "data/legacy/all_moo.csv",
                "table": "legacy_moodle",
                "description": "Legacy Moodle Data",
            },
            {
                "name": "fees",
                "file": "data/legacy/leg_fees.csv",
                "table": "legacy_fees",
                "description": "Legacy Fees",
            },
            {
                "name": "ba_requirements",
                "file": "data/legacy/ba_req.csv",
                "table": "legacy_ba_requirements",
                "description": "Legacy BA Requirements",
            },
        ]

        # Filter to single table if specified
        if self.single_table:
            legacy_imports = [imp for imp in legacy_imports if imp["name"] == self.single_table]
            if not legacy_imports:
                available_tables = ", ".join([imp["name"] for imp in legacy_imports])
                msg = f"Table '{self.single_table}' not found. Available tables: {available_tables}"
                raise CommandError(msg)

        total_imported = 0

        try:
            for import_config in legacy_imports:
                imported_count = self.import_table(import_config)
                total_imported += imported_count

        except (ValueError, TypeError, ImportError) as e:
            self.stdout.write(self.style.ERROR(f"Import failed: {e}"))
            msg = f"Legacy data import failed: {e}"
            raise CommandError(msg) from e

        if not self.dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Successfully imported {total_imported} total records across all legacy tables"
                ),
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"✅ Dry run completed - would import {total_imported} total records"),
            )

    def import_table(self, config: dict[str, str]) -> int:
        """Import a single legacy table from CSV."""
        name = config["name"]
        file_path = config["file"]
        table_name = config["table"]
        description = config["description"]

        self.stdout.write(f"\\n📊 Importing {description}...")
        self.stdout.write(f"   File: {file_path}")
        self.stdout.write(f"   Table: {table_name}")

        # Check if file exists
        if not Path(file_path).exists():
            self.stdout.write(self.style.WARNING(f"   ⚠️  File not found: {file_path} - skipping"))
            return 0

        # Create table if not dry run
        if not self.dry_run:
            getattr(self, f"_create_{name}_table")(table_name)

        imported_count = 0
        errors = []

        try:
            with Path(file_path).open(encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)

                if not self.dry_run:
                    with transaction.atomic():
                        for row_num, row in enumerate(reader, start=2):
                            try:
                                if self.limit and row_num > self.limit + 1:
                                    break

                                getattr(self, f"_insert_{name}_record")(table_name, row)
                                imported_count += 1

                                if row_num % 10000 == 0:
                                    self.stdout.write(f"   📈 Processed {row_num:,} rows...")

                            except (ValueError, TypeError, AttributeError) as e:
                                error_msg = f"Row {row_num}: {e}"
                                errors.append(error_msg)
                                max_errors_to_show = 10
                                if len(errors) <= max_errors_to_show:
                                    self.stdout.write(self.style.WARNING(f"   ⚠️  {error_msg}"))
                else:
                    # Dry run - just count rows
                    for row_num, _row in enumerate(reader, start=2):
                        if self.limit and row_num > self.limit + 1:
                            break
                        imported_count += 1

                        if row_num % 10000 == 0:
                            self.stdout.write(f"   📈 Would process {row_num:,} rows...")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Failed to read {file_path}: {e}"))
            return 0

        if errors:
            self.stdout.write(self.style.WARNING(f"   ⚠️  {len(errors)} errors occurred during import"))

        self.stdout.write(self.style.SUCCESS(f"   ✅ Imported {imported_count:,} records into {table_name}"))

        return imported_count

    def _create_students_table(self, table_name: str):
        """Create the legacy students table."""
        if self.drop_tables:
            with connection.cursor() as cursor:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
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

        CREATE INDEX IF NOT EXISTS idx_{table_name}_student_id ON {table_name}(student_id);
        CREATE INDEX IF NOT EXISTS idx_{table_name}_status ON {table_name}(status);
        CREATE INDEX IF NOT EXISTS idx_{table_name}_program ON {table_name}(current_program);
        """

        with connection.cursor() as cursor:
            cursor.execute(create_sql)

    def _insert_students_record(self, table_name: str, row: dict[str, Any]):
        """Insert a student record."""

        # Helper function to parse dates
        def parse_date_field(date_str):
            if not date_str or date_str.strip() == "":
                return None
            try:
                return parse_datetime(date_str) or parse_date(date_str)
            except (ValueError, TypeError):
                return None

        # Helper function to clean integer fields
        def clean_int(value):
            if not value or value == "":
                return None
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        insert_sql = f"""
        INSERT INTO {table_name} (
            student_id, name, khmer_name, birth_date, birth_place, gender,
            marital_status, nationality, home_address, home_phone, email,
            mobile_phone, emergency_contact, emergency_phone, current_program,
            selected_program, selected_major, selected_faculty, admission_date,
            graduation_date, ba_grad_date, ma_grad_date, first_term, paid_term,
            batch_id, status, school_email, notes, last_enroll, first_enroll,
            first_enroll_lang, first_enroll_ba, first_enroll_ma, transfer,
            deleted, created_date, modified_date, ipk
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s
        )
        ON CONFLICT (student_id) DO UPDATE SET
            name = EXCLUDED.name,
            khmer_name = EXCLUDED.khmer_name,
            birth_date = EXCLUDED.birth_date,
            modified_date = EXCLUDED.modified_date,
            imported_at = CURRENT_TIMESTAMP
        """

        with connection.cursor() as cursor:
            cursor.execute(
                insert_sql,
                [
                    row.get("ID", ""),
                    row.get("Name", ""),
                    row.get("KhmerName", ""),
                    parse_date_field(row.get("BirthDate")),
                    row.get("BirthPlace", ""),
                    row.get("Gender", ""),
                    row.get("MaritalStatus", ""),
                    row.get("Nationality", ""),
                    row.get("HomeAddress", ""),
                    row.get("HomePhone", ""),
                    row.get("Email", ""),
                    row.get("MobilePhone", ""),
                    row.get("EmergencyContact", ""),
                    row.get("EmergencyPhone", ""),
                    row.get("CurrentProgram", ""),
                    row.get("SelectedProgram", ""),
                    row.get("SelectedMajor", ""),
                    row.get("SelectedFaculty", ""),
                    parse_date_field(row.get("AdmissionDate")),
                    parse_date_field(row.get("GraduationDate")),
                    parse_date_field(row.get("BAGradDate")),
                    parse_date_field(row.get("MAGradDate")),
                    row.get("FirstTerm", ""),
                    row.get("PaidTerm", ""),
                    row.get("BatchID", ""),
                    row.get("Status", ""),
                    row.get("SchoolEmail", ""),
                    row.get("Notes", ""),
                    parse_date_field(row.get("LastEnroll")),
                    parse_date_field(row.get("FirstEnroll")),
                    parse_date_field(row.get("FirstEnrollLang")),
                    parse_date_field(row.get("FirstEnrollBA")),
                    parse_date_field(row.get("FirstEnrollMA")),
                    row.get("Transfer", ""),
                    clean_int(row.get("Deleted")),
                    parse_date_field(row.get("CreatedDate")),
                    parse_date_field(row.get("ModifiedDate")),
                    clean_int(row.get("IPK")),
                ],
            )

    # Additional table creation and insertion methods for other tables would go here

    def _create_academiccoursetakers_table(self, table_name: str):
        """Create the legacy academic course takers table."""
        if self.drop_tables:
            with connection.cursor() as cursor:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            student_id VARCHAR(10),
            course_id VARCHAR(20),
            course_name VARCHAR(200),
            term VARCHAR(50),
            grade VARCHAR(10),
            credits INTEGER,
            points DECIMAL(5,2),
            semester VARCHAR(20),
            academic_year VARCHAR(20),
            enrollment_date TIMESTAMP,
            completion_date TIMESTAMP,
            status VARCHAR(50),
            instructor VARCHAR(100),
            section VARCHAR(10),
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_{table_name}_student_id ON {table_name}(student_id);
        CREATE INDEX IF NOT EXISTS idx_{table_name}_course_id ON {table_name}(course_id);
        CREATE INDEX IF NOT EXISTS idx_{table_name}_term ON {table_name}(term);
        CREATE INDEX IF NOT EXISTS idx_{table_name}_grade ON {table_name}(grade);
        """

        with connection.cursor() as cursor:
            cursor.execute(create_sql)

    def _insert_academiccoursetakers_record(self, table_name: str, row: dict[str, Any]):
        """Insert an academic course taker record."""

        def parse_date_field(date_str):
            if not date_str or date_str.strip() == "":
                return None
            try:
                return parse_datetime(date_str) or parse_date(date_str)
            except (ValueError, TypeError):
                return None

        def clean_decimal(value):
            if not value or value == "":
                return None
            try:
                return Decimal(str(value))
            except (ValueError, TypeError, InvalidOperation):
                return None

        def clean_int(value):
            if not value or value == "":
                return None
            try:
                return int(value)
            except (ValueError, TypeError):
                return None

        insert_sql = f"""
        INSERT INTO {table_name} (
            student_id, course_id, course_name, term, grade, credits,
            points, semester, academic_year, enrollment_date, completion_date,
            status, instructor, section
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """

        with connection.cursor() as cursor:
            cursor.execute(
                insert_sql,
                [
                    row.get("StudentID", ""),
                    row.get("CourseID", ""),
                    row.get("CourseName", ""),
                    row.get("Term", ""),
                    row.get("Grade", ""),
                    clean_int(row.get("Credits")),
                    clean_decimal(row.get("Points")),
                    row.get("Semester", ""),
                    row.get("AcademicYear", ""),
                    parse_date_field(row.get("EnrollmentDate")),
                    parse_date_field(row.get("CompletionDate")),
                    row.get("Status", ""),
                    row.get("Instructor", ""),
                    row.get("Section", ""),
                ],
            )

    # Placeholder methods for other tables - implement these based on CSV structure
    def _create_receipt_headers_table(self, table_name: str):
        """Create legacy receipt headers table."""
        if self.drop_tables:
            with connection.cursor() as cursor:
                cursor.execute(f"DROP TABLE IF EXISTS {table_name}")

        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id SERIAL PRIMARY KEY,
            receipt_number VARCHAR(50),
            student_id VARCHAR(10),
            receipt_date TIMESTAMP,
            total_amount DECIMAL(10,2),
            currency VARCHAR(10),
            payment_method VARCHAR(50),
            term VARCHAR(50),
            academic_year VARCHAR(20),
            status VARCHAR(50),
            notes TEXT,
            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_{table_name}_receipt_number ON {table_name}(receipt_number);
        CREATE INDEX IF NOT EXISTS idx_{table_name}_student_id ON {table_name}(student_id);
        CREATE INDEX IF NOT EXISTS idx_{table_name}_receipt_date ON {table_name}(receipt_date);
        """

        with connection.cursor() as cursor:
            cursor.execute(create_sql)

    def _insert_receipt_headers_record(self, table_name: str, row: dict[str, Any]):
        """Insert a receipt header record."""
        # Implementation would go here based on actual CSV structure

    def _create_receipt_items_table(self, table_name: str):
        """Create legacy receipt items table."""
        # Implementation would go here

    def _insert_receipt_items_record(self, table_name: str, row: dict[str, Any]):
        """Insert a receipt item record."""
        # Implementation would go here

    def _create_terms_table(self, table_name: str):
        """Create legacy terms table."""
        # Implementation would go here

    def _insert_terms_record(self, table_name: str, row: dict[str, Any]):
        """Insert a terms record."""
        # Implementation would go here

    def _create_moodle_table(self, table_name: str):
        """Create legacy moodle table."""
        # Implementation would go here

    def _insert_moodle_record(self, table_name: str, row: dict[str, Any]):
        """Insert a moodle record."""
        # Implementation would go here

    def _create_fees_table(self, table_name: str):
        """Create legacy fees table."""
        # Implementation would go here

    def _insert_fees_record(self, table_name: str, row: dict[str, Any]):
        """Insert a fees record."""
        # Implementation would go here

    def _create_ba_requirements_table(self, table_name: str):
        """Create legacy BA requirements table."""
        # Implementation would go here

    def _insert_ba_requirements_record(self, table_name: str, row: dict[str, Any]):
        """Insert a BA requirements record."""
        # Implementation would go here
