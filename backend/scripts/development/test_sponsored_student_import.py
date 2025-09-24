#!/usr/bin/env python
"""Test script to import a specific sponsored student and verify sponsorship detection.

This script imports student 12540 (RON PHANICH <CRST>) to test the sponsorship
detection and linking logic without duplicating existing students.
"""

import os
import sys
from pathlib import Path

import django

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Set Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.db import connection, transaction

from apps.people.models import StudentProfile
from apps.scholarships.models import SponsoredStudent


def test_sponsored_student_import():
    """Import and test a specific sponsored student."""
    # Find the specific student in legacy data
    target_student_id = "12540"
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT student_id, name, khmer_name, birth_date, birth_place, gender,
                   nationality, email, school_email, transfer, last_enroll,
                   emergency_contact, emergency_phone
            FROM legacy_students
            WHERE student_id = %s
        """,
            [target_student_id],
        )

        row = cursor.fetchone()
        if not row:
            return

    # Check if student already exists
    try:
        existing_student = StudentProfile.objects.get(student_id=int(target_student_id))

        # Check existing sponsorship
        existing_sponsorship = SponsoredStudent.objects.filter(student=existing_student).first()
        if existing_sponsorship:
            pass
        else:
            pass
        return

    except StudentProfile.DoesNotExist:
        pass

    # Import using the migration script logic
    from scripts.migration_environment.migrate_legacy_students_250626 import Command

    command = Command()
    command._load_sponsor_cache()

    # Process the specific student
    try:
        with transaction.atomic():
            command._process_student_record(row)

        # Verify the import
        student = StudentProfile.objects.get(student_id=int(target_student_id))

        # Check sponsorship
        sponsorship = SponsoredStudent.objects.filter(student=student).first()
        if sponsorship:
            pass
        else:
            pass

        # Test the name parsing directly
        family, personal, sponsor_code, fees = command._parse_name_and_sponsor(row[1])

        if (sponsor_code and sponsor_code in command.sponsor_cache) or sponsor_code:
            pass
        else:
            pass

    except Exception:
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    test_sponsored_student_import()
