#!/usr/bin/env python3
"""
Add missing students from legacy data to current SIS.

Steps:
1. Add missing legacy students starting from student_id 18320
2. Total missing students: ~78 (due to improved Pydantic validation vs previous sloppy import)

Usage:
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/legacy_imports/add_missing_legacy_students.py
"""

import os
import sys
from pathlib import Path

import django
from uuid_extensions import uuid7

# Setup Django
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.db import connection, transaction


def get_current_max_student_id():
    """Get the current maximum student_id to determine where to start adding new students."""

    with connection.cursor() as cursor:
        cursor.execute("SELECT MAX(student_id) FROM people_studentprofile")
        max_id = cursor.fetchone()[0]

    print(f"📊 Current maximum student_id: {max_id}")
    return max_id


def get_missing_students():
    """Get all students from legacy that are missing from current SIS."""

    print("🔍 Finding missing students from legacy data...")

    # First, check for garbage IDs that can't be converted
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT id, name FROM legacy_students_validated
            WHERE id !~ '^[0-9]+$' OR id LIKE '%/%' OR id LIKE '%.%' OR id LIKE '%-%'
            LIMIT 10
        """
        )
        garbage_records = cursor.fetchall()

        if garbage_records:
            print(f"⚠️  Found {len(garbage_records)} garbage ID records (will be skipped):")
            for record_id, name in garbage_records:
                print(f"   Skipping: ID='{record_id}', Name='{name}'")

    # Get clean missing students with proper integer conversion
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
                lsv.id as legacy_student_id,
                lsv.name,
                lsv.kname,
                lsv.birth_date,
                lsv.gender,
                lsv.email,
                lsv.mobile_phone,
                lsv.current_program,
                lsv.status,
                lsv.batch_id,
                lsv.first_term,
                CAST(lsv.id AS INTEGER) as numeric_id
            FROM legacy_students_validated lsv
            LEFT JOIN people_studentprofile ps ON CAST(lsv.id AS INTEGER) = ps.student_id
            WHERE ps.student_id IS NULL
            AND lsv.id ~ '^[0-9]+$'
            AND lsv.id NOT LIKE '%/%'
            AND lsv.id NOT LIKE '%.%'
            AND lsv.id NOT LIKE '%-%'
            ORDER BY CAST(lsv.id AS INTEGER)
        """
        )
        missing_students = cursor.fetchall()

    print(f"✅ Found {len(missing_students)} clean missing students (garbage IDs filtered out)")
    return missing_students


def add_missing_students(missing_students, start_student_id):
    """Add missing students starting from the next available student_id."""

    print(f"👥 Adding {len(missing_students)} missing students starting from student_id {start_student_id}")

    # start_student_id is passed as parameter
    batch_size = 100
    total_added = 0

    try:
        with transaction.atomic():
            for i, student_data in enumerate(missing_students):
                current_student_id = start_student_id + i

                (
                    legacy_id,
                    name,
                    kname,
                    birth_date,
                    gender,
                    email,
                    mobile_phone,
                    current_program,
                    status,
                    batch_id,
                    first_term,
                    numeric_id,
                ) = student_data

                # Parse the name into family_name and personal_name
                name_parts = name.strip().split() if name else ["Unknown"]
                if len(name_parts) == 1:
                    family_name = name_parts[0]
                    personal_name = ""
                else:
                    family_name = name_parts[0]
                    personal_name = " ".join(name_parts[1:])

                # Handle gender and monk status
                is_monk = False
                processed_gender = "U"  # Default

                if gender:
                    gender_lower = gender.lower().strip()
                    if gender_lower == "monk":
                        is_monk = True
                        processed_gender = "M"  # Monks are male
                    elif gender_lower in ["male", "m"]:
                        processed_gender = "M"
                    elif gender_lower in ["female", "f"]:
                        processed_gender = "F"
                    else:
                        processed_gender = gender[:1].upper() if gender else "U"

                # Create Person record
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO people_person (
                            created_at, updated_at, is_deleted, deleted_at,
                            unique_id, family_name, personal_name, full_name, khmer_name,
                            preferred_gender, use_legal_name_for_documents,
                            alternate_family_name, alternate_personal_name, alternate_khmer_name, alternate_gender,
                            personal_email, date_of_birth, citizenship
                        ) VALUES (
                            NOW(), NOW(), FALSE, NULL,
                            %s, %s, %s, %s, %s,
                            %s, TRUE,
                            %s, %s, %s, %s,
                            %s, %s, 'KH'
                        ) RETURNING id
                    """,
                        [
                            uuid7(),  # Generate UUID7 with timestamp
                            family_name,
                            personal_name,
                            name,
                            kname or "",
                            processed_gender,
                            family_name,  # alternate_family_name (same as family_name)
                            personal_name or "",  # alternate_personal_name
                            kname or "",  # alternate_khmer_name
                            processed_gender,  # alternate_gender
                            email,
                            birth_date,
                        ],
                    )
                    person_id = cursor.fetchone()[0]

                # Create StudentProfile record
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO people_studentprofile (
                            created_at, updated_at, is_deleted, deleted_at,
                            student_id, is_monk, is_transfer_student,
                            current_status, study_time_preference,
                            last_enrollment_date, person_id
                        ) VALUES (
                            NOW(), NOW(), FALSE, NULL,
                            %s, %s, FALSE,
                            %s, 'Flexible',
                            NULL, %s
                        )
                    """,
                        [current_student_id, is_monk, status or "Active", person_id],
                    )

                total_added += 1

                # Progress reporting
                if total_added % batch_size == 0:
                    print(
                        f"⏳ Added {total_added}/{len(missing_students)} students... (current ID: {current_student_id})"
                    )

        print(f"✅ Successfully added {total_added} students!")
        print(f"   Student IDs: 18317 to {start_student_id + len(missing_students) - 1}")

    except Exception as e:
        print(f"❌ Error adding students: {e!s}")
        raise


def verify_results():
    """Verify the results of the import."""

    print("📊 Verifying import results...")

    with connection.cursor() as cursor:
        # Check new totals
        cursor.execute("SELECT COUNT(*) FROM people_studentprofile")
        total_profiles = cursor.fetchone()[0]

        cursor.execute("SELECT MAX(student_id) FROM people_studentprofile")
        max_student_id = cursor.fetchone()[0]

        cursor.execute("SELECT MIN(student_id) FROM people_studentprofile WHERE student_id >= 18320")
        min_new_id = cursor.fetchone()[0]

        # Check for any remaining missing students (with proper integer conversion)
        cursor.execute(
            """
            SELECT COUNT(*) FROM legacy_students_validated lsv
            LEFT JOIN people_studentprofile ps ON CAST(lsv.id AS INTEGER) = ps.student_id
            WHERE ps.student_id IS NULL
            AND lsv.id ~ '^[0-9]+$'
        """
        )
        remaining_missing = cursor.fetchone()[0]

    print("📈 Import Results:")
    print(f"   Total StudentProfile records: {total_profiles}")
    print(f"   Maximum student_id: {max_student_id}")
    print(f"   New students start at: {min_new_id}")
    print(f"   Remaining missing students: {remaining_missing}")

    if remaining_missing == 0:
        print("🎉 SUCCESS: All legacy students have been imported!")
    else:
        print(f"⚠️  WARNING: {remaining_missing} students still missing")


def main():
    """Main execution function."""

    print("👥 Legacy Student Import - Add Missing Students")
    print("=" * 60)

    try:
        # Step 1: Get current max student_id
        current_max_id = get_current_max_student_id()
        next_student_id = current_max_id + 1

        # Step 2: Get missing students
        missing_students = get_missing_students()

        if not missing_students:
            print("✅ No missing students to add!")
            return

        # Step 3: Add missing students
        add_missing_students(missing_students, next_student_id)

        # Step 4: Verify results
        verify_results()

        print("=" * 60)
        print("🎉 Student import completed successfully!")

    except Exception as e:
        print(f"❌ Fatal error: {e!s}")
        sys.exit(1)


if __name__ == "__main__":
    main()
