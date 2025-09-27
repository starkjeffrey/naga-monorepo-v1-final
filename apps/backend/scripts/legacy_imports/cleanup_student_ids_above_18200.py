#!/usr/bin/env python3
"""
Clean up Person/StudentProfile/SponsoredStudent records with student_id > 18200
to prepare for adding missing students from legacy data starting at 18201.

Usage:
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/legacy_imports/cleanup_student_ids_above_18200.py
"""

import os
import sys
from pathlib import Path

import django

# Setup Django
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.db import connection, transaction


def cleanup_student_records_above_18200():
    """Delete Person/StudentProfile/SponsoredStudent records with student_id > 18200."""

    print("🧹 Cleaning up records with student_id > 18200")
    print("=" * 60)

    # First, check what we have
    with connection.cursor() as cursor:
        # Check StudentProfile records
        cursor.execute("SELECT COUNT(*) FROM people_studentprofile WHERE student_id > 18200")
        student_profile_count = cursor.fetchone()[0]

        # Check linked Person records
        cursor.execute("""
            SELECT COUNT(*) FROM people_person p
            JOIN people_studentprofile sp ON p.id = sp.person_id
            WHERE sp.student_id > 18200
        """)
        person_count = cursor.fetchone()[0]

        # Check linked SponsoredStudent records
        cursor.execute("""
            SELECT COUNT(*) FROM scholarships_sponsoredstudent ss
            JOIN people_studentprofile sp ON ss.student_id = sp.id
            WHERE sp.student_id > 18200
        """)
        sponsored_count = cursor.fetchone()[0]

    print("📊 Records to delete:")
    print(f"   StudentProfile: {student_profile_count}")
    print(f"   Person (linked): {person_count}")
    print(f"   SponsoredStudent (linked): {sponsored_count}")

    if student_profile_count == 0:
        print("✅ No records to delete - cleanup already done or not needed")
        return

    print(f"\n⚠️  About to delete {student_profile_count} student records with ID > 18200")
    print("This will clear the way for adding missing legacy students starting at 18201")

    try:
        with transaction.atomic():
            # Step 1: Delete SponsoredStudent records first (foreign key constraint)
            if sponsored_count > 0:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM scholarships_sponsoredstudent ss
                        USING people_studentprofile sp
                        WHERE ss.student_id = sp.id
                        AND sp.student_id > 18200
                    """)
                    deleted_sponsored = cursor.rowcount
                print(f"✅ Deleted {deleted_sponsored} SponsoredStudent records")

            # Step 2: Delete StudentProfile records (cascades to Person due to FK)
            with connection.cursor() as cursor:
                # Get the person IDs before deletion for cleanup
                cursor.execute("""
                    SELECT person_id FROM people_studentprofile WHERE student_id > 18200
                """)
                person_ids = [row[0] for row in cursor.fetchall()]

                # Delete StudentProfile records
                cursor.execute("DELETE FROM people_studentprofile WHERE student_id > 18200")
                deleted_profiles = cursor.rowcount
                print(f"✅ Deleted {deleted_profiles} StudentProfile records")

                # Delete the orphaned Person records
                if person_ids:
                    cursor.execute("DELETE FROM people_person WHERE id = ANY(%s)", [person_ids])
                    deleted_persons = cursor.rowcount
                    print(f"✅ Deleted {deleted_persons} Person records")

            print("✅ Cleanup completed successfully!")

    except Exception as e:
        print(f"❌ Error during cleanup: {e!s}")
        raise

    # Verify cleanup
    print("\n📊 Verification after cleanup:")
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM people_studentprofile WHERE student_id > 18200")
        remaining_profiles = cursor.fetchone()[0]

        cursor.execute("SELECT MAX(student_id) FROM people_studentprofile")
        max_student_id = cursor.fetchone()[0]

        print(f"   StudentProfile with ID > 18200: {remaining_profiles}")
        print(f"   Maximum student_id now: {max_student_id}")

    print("=" * 60)


def main():
    """Main execution function."""

    try:
        cleanup_student_records_above_18200()
        print("🎉 Cleanup completed! Ready to add missing students starting from 18201")

    except Exception as e:
        print(f"❌ Fatal error: {e!s}")
        sys.exit(1)


if __name__ == "__main__":
    main()
