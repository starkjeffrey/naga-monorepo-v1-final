#!/usr/bin/env python3
"""Import all V1 legacy tables from CSV files into PostgreSQL migration database.
This script creates legacy tables for data migration purposes using the actual V1 data files.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.migration")

import django

django.setup()

import csv

from django.db import connection


def create_legacy_students_table():
    """Create legacy_students table based on V1 CSV structure."""
    drop_sql = "DROP TABLE IF EXISTS legacy_students;"

    create_sql = """
    CREATE TABLE legacy_students (
        yui VARCHAR(50),
        pw VARCHAR(100),
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
        employment_place VARCHAR(200),
        position VARCHAR(100),
        father_name VARCHAR(200),
        spouse_name VARCHAR(200),
        emg_contact_person VARCHAR(200),
        relationship VARCHAR(50),
        contact_person_address TEXT,
        contact_person_phone VARCHAR(100),
        high_school_program_school VARCHAR(200),
        high_school_program_province VARCHAR(100),
        high_school_program_year VARCHAR(20),
        high_school_program_diploma VARCHAR(100),
        english_program_school VARCHAR(200),
        english_program_level VARCHAR(50),
        english_program_year VARCHAR(20),
        less_than_four_year_program_school VARCHAR(200),
        less_than_four_year_program_year VARCHAR(20),
        four_year_program_school VARCHAR(200),
        four_year_program_degree VARCHAR(100),
        four_year_program_major VARCHAR(100),
        four_year_program_year VARCHAR(20),
        graduate_program_school VARCHAR(200),
        graduate_program_degree VARCHAR(100),
        graduate_program_major VARCHAR(100),
        graduate_program_year VARCHAR(20),
        post_graduate_program_school VARCHAR(200),
        post_graduate_program_degree VARCHAR(100),
        post_graduate_program_major VARCHAR(100),
        post_graduate_program_year VARCHAR(20),
        current_program VARCHAR(100),
        sel_program VARCHAR(100),
        selected_program VARCHAR(200),
        sel_major VARCHAR(100),
        selected_major VARCHAR(200),
        sel_faculty VARCHAR(100),
        selected_faculty VARCHAR(200),
        selected_degree_type VARCHAR(50),
        admission_date TIMESTAMP,
        admission_date_for_under TIMESTAMP,
        admission_date_for_master TIMESTAMP,
        admission_date_for_doctor TIMESTAMP,
        previous_degree VARCHAR(100),
        previous_institution VARCHAR(200),
        year_awarded VARCHAR(20),
        other_credit_transfer_institution VARCHAR(200),
        degree_awarded VARCHAR(100),
        graduation_date TIMESTAMP,
        first_term VARCHAR(50),
        paid_term VARCHAR(50),
        batch_id VARCHAR(50),
        batch_id_for_under VARCHAR(50),
        batch_id_for_master VARCHAR(50),
        batch_id_for_doctor VARCHAR(50),
        group_id VARCHAR(50),
        int_group_id INTEGER,
        color VARCHAR(20),
        admitted INTEGER,
        deleted INTEGER,
        status VARCHAR(50),
        school_email VARCHAR(100),
        ba_grad_date TIMESTAMP,
        ma_grad_date TIMESTAMP,
        notes TEXT,
        last_enroll TIMESTAMP,
        first_enroll TIMESTAMP,
        first_enroll_lang TIMESTAMP,
        first_enroll_ba TIMESTAMP,
        first_enroll_ma TIMESTAMP,
        transfer VARCHAR(50),
        khmer_name2 VARCHAR(200),
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
        cursor.execute(drop_sql)
        cursor.execute(create_sql)


def create_legacy_terms_table():
    """Create legacy_terms table based on V1 CSV structure."""
    drop_sql = "DROP TABLE IF EXISTS legacy_terms;"

    create_sql = """
    CREATE TABLE legacy_terms (
        term_id VARCHAR(20) PRIMARY KEY,
        term_name VARCHAR(100),
        term_type VARCHAR(50),
        start_date TIMESTAMP,
        end_date TIMESTAMP,
        enroll_start TIMESTAMP,
        enroll_end TIMESTAMP,
        drop_deadline TIMESTAMP,
        withdraw_deadline TIMESTAMP,
        is_current INTEGER,
        is_active INTEGER,
        academic_year VARCHAR(10),
        term_number INTEGER,
        description TEXT,
        created_date TIMESTAMP,
        modified_date TIMESTAMP,
        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX idx_legacy_terms_academic_year ON legacy_terms(academic_year);
    CREATE INDEX idx_legacy_terms_is_current ON legacy_terms(is_current);
    """

    with connection.cursor() as cursor:
        cursor.execute(drop_sql)
        cursor.execute(create_sql)


def create_legacy_academiccoursetakers_table():
    """Create legacy_academiccoursetakers table based on V1 CSV structure."""
    drop_sql = "DROP TABLE IF EXISTS legacy_academiccoursetakers;"

    create_sql = """
    CREATE TABLE legacy_academiccoursetakers (
        id SERIAL PRIMARY KEY,
        student_id VARCHAR(10),
        course_id VARCHAR(20),
        term_id VARCHAR(20),
        section VARCHAR(10),
        enrollment_date TIMESTAMP,
        grade VARCHAR(5),
        credit_hours DECIMAL(4,2),
        grade_points DECIMAL(5,2),
        status VARCHAR(20),
        attempt_number INTEGER,
        course_name VARCHAR(200),
        instructor VARCHAR(100),
        final_grade VARCHAR(5),
        midterm_grade VARCHAR(5),
        created_date TIMESTAMP,
        modified_date TIMESTAMP,
        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX idx_legacy_academiccoursetakers_student ON legacy_academiccoursetakers(student_id);
    CREATE INDEX idx_legacy_academiccoursetakers_course ON legacy_academiccoursetakers(course_id);
    CREATE INDEX idx_legacy_academiccoursetakers_term ON legacy_academiccoursetakers(term_id);
    """

    with connection.cursor() as cursor:
        cursor.execute(drop_sql)
        cursor.execute(create_sql)


def create_legacy_receipt_headers_table():
    """Create legacy_receipt_headers table."""
    drop_sql = "DROP TABLE IF EXISTS legacy_receipt_headers;"

    create_sql = """
    CREATE TABLE legacy_receipt_headers (
        receipt_id VARCHAR(50) PRIMARY KEY,
        student_id VARCHAR(10),
        receipt_date TIMESTAMP,
        total_amount DECIMAL(10,2),
        payment_method VARCHAR(50),
        reference_number VARCHAR(100),
        term_id VARCHAR(20),
        academic_year VARCHAR(10),
        status VARCHAR(20),
        notes TEXT,
        created_by VARCHAR(100),
        created_date TIMESTAMP,
        modified_date TIMESTAMP,
        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX idx_legacy_receipt_headers_student ON legacy_receipt_headers(student_id);
    CREATE INDEX idx_legacy_receipt_headers_date ON legacy_receipt_headers(receipt_date);
    CREATE INDEX idx_legacy_receipt_headers_term ON legacy_receipt_headers(term_id);
    """

    with connection.cursor() as cursor:
        cursor.execute(drop_sql)
        cursor.execute(create_sql)


def create_legacy_receipt_items_table():
    """Create legacy_receipt_items table."""
    drop_sql = "DROP TABLE IF EXISTS legacy_receipt_items;"

    create_sql = """
    CREATE TABLE legacy_receipt_items (
        id SERIAL PRIMARY KEY,
        receipt_id VARCHAR(50),
        item_type VARCHAR(50),
        description VARCHAR(200),
        amount DECIMAL(10,2),
        quantity INTEGER DEFAULT 1,
        unit_price DECIMAL(10,2),
        course_id VARCHAR(20),
        fee_type VARCHAR(50),
        created_date TIMESTAMP,
        modified_date TIMESTAMP,
        imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX idx_legacy_receipt_items_receipt ON legacy_receipt_items(receipt_id);
    CREATE INDEX idx_legacy_receipt_items_type ON legacy_receipt_items(item_type);
    CREATE INDEX idx_legacy_receipt_items_course ON legacy_receipt_items(course_id);
    """

    with connection.cursor() as cursor:
        cursor.execute(drop_sql)
        cursor.execute(create_sql)


def import_students_data():
    """Import students data from CSV."""
    file_path = "data/legacy/all_students_20250612.csv"

    if not Path(file_path).exists():
        return

    # Clean and simplified field mapping
    field_mapping = [
        "yui",
        "pw",
        "student_id",
        "name",
        "khmer_name",
        "birth_date",
        "birth_place",
        "gender",
        "marital_status",
        "nationality",
        "home_address",
        "home_phone",
        "email",
        "mobile_phone",
        "employment_place",
        "position",
        "father_name",
        "spouse_name",
        "emg_contact_person",
        "relationship",
        "contact_person_address",
        "contact_person_phone",
        "high_school_program_school",
        "high_school_program_province",
        "high_school_program_year",
        "high_school_program_diploma",
        "english_program_school",
        "english_program_level",
        "english_program_year",
        "less_than_four_year_program_school",
        "less_than_four_year_program_year",
        "four_year_program_school",
        "four_year_program_degree",
        "four_year_program_major",
        "four_year_program_year",
        "graduate_program_school",
        "graduate_program_degree",
        "graduate_program_major",
        "graduate_program_year",
        "post_graduate_program_school",
        "post_graduate_program_degree",
        "post_graduate_program_major",
        "post_graduate_program_year",
        "current_program",
        "sel_program",
        "selected_program",
        "sel_major",
        "selected_major",
        "sel_faculty",
        "selected_faculty",
        "selected_degree_type",
        "admission_date",
        "admission_date_for_under",
        "admission_date_for_master",
        "admission_date_for_doctor",
        "previous_degree",
        "previous_institution",
        "year_awarded",
        "other_credit_transfer_institution",
        "degree_awarded",
        "graduation_date",
        "first_term",
        "paid_term",
        "batch_id",
        "batch_id_for_under",
        "batch_id_for_master",
        "batch_id_for_doctor",
        "group_id",
        "int_group_id",
        "color",
        "admitted",
        "deleted",
        "status",
        "school_email",
        "ba_grad_date",
        "ma_grad_date",
        "notes",
        "last_enroll",
        "first_enroll",
        "first_enroll_lang",
        "first_enroll_ba",
        "first_enroll_ma",
        "transfer",
        "khmer_name2",
        "created_date",
        "modified_date",
        "ipk",
    ]

    placeholders = ", ".join([f"%({field})s" for field in field_mapping])
    columns = ", ".join(field_mapping)

    insert_sql = f"""
    INSERT INTO legacy_students ({columns})
    VALUES ({placeholders})
    """

    imported_count = 0
    with Path(file_path).open(encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        with connection.cursor() as cursor:
            for row in reader:
                # Clean data
                clean_row = {}
                for i, field in enumerate(field_mapping):
                    csv_header = list(reader.fieldnames)[i]
                    value = row.get(csv_header, "").strip()

                    # Handle NULL values and empty strings
                    if value in ("NULL", "", "null", None):
                        clean_row[field] = None
                    elif field in ["int_group_id", "admitted", "deleted", "ipk"]:
                        try:
                            clean_row[field] = int(float(value)) if value else None
                        except (ValueError, TypeError):
                            clean_row[field] = None
                    elif "date" in field:
                        # Handle date fields
                        if value and value != "NULL":
                            try:
                                # Simple date parsing - PostgreSQL will handle various formats
                                clean_row[field] = value
                            except (ValueError, TypeError):
                                clean_row[field] = None
                        else:
                            clean_row[field] = None
                    else:
                        clean_row[field] = value[:500] if value else None  # Limit string length

                try:
                    cursor.execute(insert_sql, clean_row)
                    imported_count += 1

                    if imported_count % 1000 == 0:
                        pass

                except Exception:
                    continue


def import_terms_data():
    """Import terms data from CSV."""
    file_path = "data/legacy/all_terms_20250612.csv"

    if not Path(file_path).exists():
        return

    imported_count = 0
    with Path(file_path).open(encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        insert_sql = """
        INSERT INTO legacy_terms (
            term_id, term_name, term_type, start_date, end_date, enroll_start,
            enroll_end, drop_deadline, withdraw_deadline, is_current, is_active,
            academic_year, term_number, description, created_date, modified_date
        ) VALUES (
            %(term_id)s, %(term_name)s, %(term_type)s, %(start_date)s, %(end_date)s,
            %(enroll_start)s, %(enroll_end)s, %(drop_deadline)s, %(withdraw_deadline)s,
            %(is_current)s, %(is_active)s, %(academic_year)s, %(term_number)s,
            %(description)s, %(created_date)s, %(modified_date)s
        )
        """

        with connection.cursor() as cursor:
            for row in reader:
                # Map CSV columns to our fields based on actual CSV structure
                clean_row = {
                    "term_id": row.get("TermID", "").strip() or None,
                    "term_name": row.get("TermName", "").strip() or None,
                    "term_type": row.get("TermType", "").strip() or None,
                    "start_date": row.get("StartDate", "").strip() or None,
                    "end_date": row.get("EndDate", "").strip() or None,
                    "enroll_start": row.get("AddDate", "").strip() or None,  # AddDate for enrollment start
                    "enroll_end": row.get("LDPDate", "").strip() or None,  # LDPDate for last day to pay
                    "drop_deadline": row.get("DropDate", "").strip() or None,
                    "withdraw_deadline": row.get("LeaveDate", "").strip() or None,
                    "is_current": None,  # Not in CSV
                    "is_active": None,  # Not in CSV
                    "academic_year": row.get("schoolyear", "").strip() or None,
                    "term_number": row.get("IPK", "").strip() or None,  # IPK might be term sequence
                    "description": row.get("Desp", "").strip() or None,
                    "created_date": None,  # Not in CSV
                    "modified_date": None,  # Not in CSV
                }

                # Handle NULL values properly
                for key, value in clean_row.items():
                    if value in ("NULL", "", "null"):
                        clean_row[key] = None

                try:
                    cursor.execute(insert_sql, clean_row)
                    imported_count += 1
                except Exception:
                    continue


def main():
    """Main import process."""
    # Create tables
    create_legacy_students_table()
    create_legacy_terms_table()
    create_legacy_academiccoursetakers_table()
    create_legacy_receipt_headers_table()
    create_legacy_receipt_items_table()

    # Import data
    import_students_data()
    import_terms_data()

    # Check what tables were created
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name LIKE 'legacy_%'
            ORDER BY table_name
        """
        )

        legacy_tables = cursor.fetchall()
        if legacy_tables:
            for table in legacy_tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                cursor.fetchone()[0]
        else:
            pass


if __name__ == "__main__":
    main()
