"""Django management command to import legacy academic course takers data from
leg_academiccoursetakers.csv.

This contains student enrollment and grade data for academic courses
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils.dateparse import parse_datetime


class Command(BaseCommand):
    help = "Import legacy academic course takers data from leg_academiccoursetakers.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/legacy/leg_academiccoursetakers.csv",
            help="Path to the CSV file with legacy academic course takers data",
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

        self.stdout.write(f"Processing legacy academic course takers file: {file_path}")

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
                            if limit and row_num > limit + 1:  # +1 for header
                                break

                            if not dry_run:
                                self._insert_record(row)

                            else:
                                self._validate_record(row)

                            imported_count += 1

                            if row_num % 5000 == 0:
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
            self.stdout.write(
                self.style.SUCCESS(f"DRY RUN: Would import {imported_count} academic course taker records"),
            )

        else:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully imported {imported_count} academic course taker records"),
            )

    def _create_table(self, drop_table):
        """Create the legacy academic course takers table in PostgreSQL."""
        drop_sql = """

        DROP TABLE IF EXISTS legacy_academic_course_takers;

        """

        create_sql = """

        CREATE TABLE legacy_academic_course_takers (

            ipk INTEGER PRIMARY KEY,

            student_id VARCHAR(10),

            class_id VARCHAR(255),

            repeat_num INTEGER,

            l_score DECIMAL(5,2),

            u_score DECIMAL(5,2),

            credit INTEGER,

            grade_point DECIMAL(5,2),

            total_point DECIMAL(5,2),

            grade VARCHAR(10),

            previous_grade VARCHAR(10),

            comment VARCHAR(100),

            passed INTEGER,

            remarks VARCHAR(50),

            color DECIMAL(10,2),

            register_mode VARCHAR(20),

            attendance VARCHAR(20),

            fore_color BIGINT,

            back_color BIGINT,

            quick_note VARCHAR(50),

            pos DECIMAL(10,2),

            g_pos DECIMAL(10,2),

            adder DECIMAL(10,2),

            add_time TIMESTAMP,

            last_update TIMESTAMP,

            created_date TIMESTAMP,

            modified_date TIMESTAMP,

            section VARCHAR(10),

            time_slot VARCHAR(10),

            parsed_term_id VARCHAR(50),

            parsed_course_code VARCHAR(100),

            parsed_lang_course VARCHAR(255),

            normalized_lang_course VARCHAR(15),

            normalized_lang_part VARCHAR(15),

            normalized_section VARCHAR(15),

            normalized_tod VARCHAR(10),

            imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

        );



        CREATE INDEX idx_legacy_act_student_id ON legacy_academic_course_takers(student_id);

        CREATE INDEX idx_legacy_act_class_id ON legacy_academic_course_takers(class_id);

        CREATE INDEX idx_legacy_act_parsed_term ON legacy_academic_course_takers(parsed_term_id);

        CREATE INDEX idx_legacy_act_parsed_course ON legacy_academic_course_takers(parsed_course_code);

        CREATE INDEX idx_legacy_act_lang_course ON legacy_academic_course_takers(parsed_lang_course);

        CREATE INDEX idx_legacy_act_grade ON legacy_academic_course_takers(grade);

        CREATE INDEX idx_legacy_act_passed ON legacy_academic_course_takers(passed);

        """

        with connection.cursor() as cursor:
            if drop_table:
                cursor.execute(drop_sql)

                self.stdout.write(self.style.SUCCESS("Dropped existing legacy_academic_course_takers table"))

            cursor.execute(create_sql)

            self.stdout.write(self.style.SUCCESS("Created legacy_academic_course_takers table"))

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
            "class_id": clean_value(row["ClassID"]),
            "repeat_num": clean_value(row["RepeatNum"], "integer"),
            "l_score": clean_value(row["LScore"], "decimal"),
            "u_score": clean_value(row["UScore"], "decimal"),
            "credit": clean_value(row["Credit"], "integer"),
            "grade_point": clean_value(row["GradePoint"], "decimal"),
            "total_point": clean_value(row["TotalPoint"], "decimal"),
            "grade": clean_value(row["Grade"]),
            "previous_grade": clean_value(row["PreviousGrade"]),
            "comment": clean_value(row["Comment"]),
            "passed": clean_value(row["Passed"], "integer"),
            "remarks": clean_value(row["Remarks"]),
            "color": clean_value(row["Color"], "decimal"),
            "register_mode": clean_value(row["RegisterMode"]),
            "attendance": clean_value(row["Attendance"]),
            "fore_color": clean_value(row["ForeColor"], "integer"),
            "back_color": clean_value(row["BackColor"], "integer"),
            "quick_note": clean_value(row["QuickNote"]),
            "pos": clean_value(row["Pos"], "decimal"),
            "g_pos": clean_value(row["GPos"], "decimal"),
            "adder": clean_value(row["Adder"], "decimal"),
            "add_time": clean_value(row["AddTime"], "datetime"),
            "last_update": clean_value(row["LastUpdate"], "datetime"),
            "created_date": clean_value(row["CreatedDate"], "datetime"),
            "modified_date": clean_value(row["ModifiedDate"], "datetime"),
            "section": clean_value(row["section"]),
            "time_slot": clean_value(row["time_slot"]),
            "parsed_term_id": clean_value(row["parsed_termid"]),
            "parsed_course_code": clean_value(row["parsed_coursecode"]),
            "parsed_lang_course": clean_value(row["parsed_langcourse"]),
            "normalized_lang_course": clean_value(row["NormalizedLangCourse"]),
            "normalized_lang_part": clean_value(row["NormalizedLangPart"]),
            "normalized_section": clean_value(row["NormalizedSection"]),
            "normalized_tod": clean_value(row["NormalizedTOD"]),
        }

        # Insert the record

        insert_sql = """

        INSERT INTO legacy_academic_course_takers (

            ipk, student_id, class_id, repeat_num, l_score, u_score, credit,

            grade_point, total_point, grade, previous_grade, comment, passed,

            remarks, color, register_mode, attendance, fore_color, back_color,

            quick_note, pos, g_pos, adder, add_time, last_update, created_date,

            modified_date, section, time_slot, parsed_term_id, parsed_course_code,

            parsed_lang_course, normalized_lang_course, normalized_lang_part,

            normalized_section, normalized_tod

        ) VALUES (

            %(ipk)s, %(student_id)s, %(class_id)s, %(repeat_num)s, %(l_score)s,

            %(u_score)s, %(credit)s, %(grade_point)s, %(total_point)s, %(grade)s,

            %(previous_grade)s, %(comment)s, %(passed)s, %(remarks)s, %(color)s,

            %(register_mode)s, %(attendance)s, %(fore_color)s, %(back_color)s,

            %(quick_note)s, %(pos)s, %(g_pos)s, %(adder)s, %(add_time)s,

            %(last_update)s, %(created_date)s, %(modified_date)s, %(section)s,

            %(time_slot)s, %(parsed_term_id)s, %(parsed_course_code)s,

            %(parsed_lang_course)s, %(normalized_lang_course)s, %(normalized_lang_part)s,

            %(normalized_section)s, %(normalized_tod)s

        )

        """

        with connection.cursor() as cursor:
            cursor.execute(insert_sql, record_data)
