#!/usr/bin/env python3
"""Script to fix duplicate ClassHeader records created by import.

This script:
1. Identifies ClassHeaders that represent the same logical class (same course+term+time)
2. Consolidates enrollments to the preferred ClassHeader
3. Removes duplicate ClassHeaders
"""

import os
import sys
from collections import defaultdict

import django
from django.db import transaction

# Setup Django
sys.path.append("/app")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.enrollment.models import ClassHeaderEnrollment
from apps.scheduling.models import ClassHeader


def find_duplicate_classheaders():
    """Find ClassHeaders that represent the same logical class."""
    print("=== Finding Duplicate ClassHeaders ===")

    # Group ClassHeaders by course+term+time_of_day
    class_groups = defaultdict(list)

    for ch in ClassHeader.objects.all():
        key = (ch.course.code, ch.term.code, ch.time_of_day)
        class_groups[key].append(ch)

    # Find groups with multiple ClassHeaders
    duplicates = {k: v for k, v in class_groups.items() if len(v) > 1}

    print(f"Found {len(duplicates)} course+term combinations with duplicate ClassHeaders")

    total_duplicate_headers = sum(len(headers) - 1 for headers in duplicates.values())
    print(f"Total duplicate ClassHeaders to remove: {total_duplicate_headers}")

    return duplicates


def consolidate_enrollments(duplicate_groups):
    """Consolidate enrollments to preferred ClassHeaders and remove duplicates."""
    print("\n=== Consolidating Enrollments ===")

    consolidated_count = 0
    removed_headers = 0

    with transaction.atomic():
        for (
            course_code,
            term_code,
            time_of_day,
        ), class_headers in duplicate_groups.items():
            print(f"\nProcessing: {course_code} - {term_code} ({time_of_day})")
            print(f"  Found {len(class_headers)} ClassHeaders: {[ch.id for ch in class_headers]}")

            # Choose the preferred ClassHeader (lowest ID = oldest)
            preferred_header = min(class_headers, key=lambda x: x.id)
            duplicate_headers = [ch for ch in class_headers if ch.id != preferred_header.id]

            print(f"  Keeping ClassHeader {preferred_header.id}")
            print(f"  Removing ClassHeaders: {[ch.id for ch in duplicate_headers]}")

            # Move all enrollments to the preferred ClassHeader
            for duplicate_header in duplicate_headers:
                enrollments = ClassHeaderEnrollment.objects.filter(class_header=duplicate_header)
                enrollment_count = enrollments.count()

                if enrollment_count > 0:
                    print(f"    Processing {enrollment_count} enrollments from {duplicate_header.id}")

                    # Check for conflicts before moving enrollments
                    moved_count = 0
                    deleted_count = 0

                    for enrollment in enrollments:
                        # Check if student already has enrollment in preferred ClassHeader
                        existing = ClassHeaderEnrollment.objects.filter(
                            student=enrollment.student,
                            class_header=preferred_header,
                        ).first()

                        if existing:
                            # Student already enrolled in preferred ClassHeader - delete duplicate
                            print(f"      Deleting duplicate enrollment for student {enrollment.student.student_id}")
                            enrollment.delete()
                            deleted_count += 1
                        else:
                            # Move enrollment to preferred ClassHeader
                            enrollment.class_header = preferred_header
                            enrollment.save()
                            moved_count += 1

                    print(f"      Moved: {moved_count}, Deleted duplicates: {deleted_count}")
                    consolidated_count += moved_count

                # Remove the duplicate ClassHeader
                print(f"    Deleting ClassHeader {duplicate_header.id}")
                duplicate_header.delete()
                removed_headers += 1

    print("\n✅ Consolidation complete:")
    print(f"   - Moved {consolidated_count} enrollments")
    print(f"   - Removed {removed_headers} duplicate ClassHeaders")


def verify_fix():
    """Verify that the fix worked correctly."""
    print("\n=== Verification ===")

    # Check for remaining duplicates
    duplicates = find_duplicate_classheaders()

    if len(duplicates) == 0:
        print("✅ No duplicate ClassHeaders found - fix successful!")
    else:
        print(f"❌ Still found {len(duplicates)} duplicate groups - fix incomplete")

    # Check student 10774 as example
    from apps.people.models import StudentProfile

    try:
        student = StudentProfile.objects.get(student_id="10774")
        enrollments = ClassHeaderEnrollment.objects.filter(student=student)
        unique_courses = (
            enrollments.values("class_header__course__code", "class_header__term__code").distinct().count()
        )

        print("\nStudent 10774 verification:")
        print(f"  Total enrollment records: {enrollments.count()}")
        print(f"  Unique courses: {unique_courses}")

        if enrollments.count() == unique_courses:
            print("✅ Student 10774 now has 1 enrollment per course (no duplicates)")
        else:
            print("❌ Student 10774 still has duplicate enrollments")

    except Exception as e:
        print(f"❌ Error checking student 10774: {e}")


def main():
    """Main execution function."""
    print("🔧 Fixing Duplicate ClassHeader Records")
    print("=" * 50)

    # Find duplicates
    duplicates = find_duplicate_classheaders()

    if len(duplicates) == 0:
        print("✅ No duplicate ClassHeaders found - nothing to fix!")
        return

    # Auto-proceed for script execution
    print(f"\nProceeding with consolidating {len(duplicates)} duplicate groups...")

    # Consolidate enrollments and remove duplicates
    consolidate_enrollments(duplicates)

    # Verify the fix
    verify_fix()

    print("\n🎉 Duplicate ClassHeader cleanup complete!")


if __name__ == "__main__":
    main()
