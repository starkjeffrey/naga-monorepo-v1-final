#!/usr/bin/env python3
"""
Clean up ClassHeaderEnrollment and all related records to prepare for reimport.

This will delete:
1. All records that reference ClassHeaderEnrollment (foreign keys)
2. All ClassHeaderEnrollment records

Usage:
    docker compose -f docker-compose.local.yml run --rm django \
        python scripts/legacy_imports/cleanup_enrollment_records.py
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


def check_related_records():
    """Check what records will be affected by the cleanup."""

    print("📊 Checking related records before cleanup...")

    related_tables = [
        "enrollment_classsessionexemption",
        "finance_invoice_line_item",
        "grading_classpartgrade",
        "grading_classsessiongrade",
        "language_languagelevelskiprequest",
        "academic_studentdegreeprogress",
        "finance_reconciliation_status_matched_enrollments",
    ]

    with connection.cursor() as cursor:
        for table in related_tables:
            # Count records that reference ClassHeaderEnrollment
            if table == "enrollment_classsessionexemption":
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE class_header_enrollment_id IS NOT NULL")
            elif table == "language_languagelevelskiprequest":
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE new_enrollment_id IS NOT NULL")
            elif table == "academic_studentdegreeprogress":
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE fulfilling_enrollment_id IS NOT NULL")
            elif table == "finance_reconciliation_status_matched_enrollments":
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
            else:
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE enrollment_id IS NOT NULL")

            count = cursor.fetchone()[0]
            print(f"   {table}: {count:,} records")

        # Check main table
        cursor.execute("SELECT COUNT(*) FROM enrollment_classheaderenrollment")
        main_count = cursor.fetchone()[0]
        print(f"   enrollment_classheaderenrollment: {main_count:,} records")


def cleanup_related_records():
    """Delete all records that reference ClassHeaderEnrollment."""

    print("🧹 Cleaning up related records...")

    try:
        with transaction.atomic():
            # Delete in order of dependencies (child tables first)
            deletions = []

            with connection.cursor() as cursor:
                # 1. ClassSessionExemption
                cursor.execute(
                    "DELETE FROM enrollment_classsessionexemption WHERE class_header_enrollment_id IS NOT NULL"
                )
                deletions.append(("enrollment_classsessionexemption", cursor.rowcount))

                # 2. Finance invoice line items
                cursor.execute("DELETE FROM finance_invoice_line_item WHERE enrollment_id IS NOT NULL")
                deletions.append(("finance_invoice_line_item", cursor.rowcount))

                # 3. Grading records
                cursor.execute("DELETE FROM grading_classpartgrade WHERE enrollment_id IS NOT NULL")
                deletions.append(("grading_classpartgrade", cursor.rowcount))

                cursor.execute("DELETE FROM grading_classsessiongrade WHERE enrollment_id IS NOT NULL")
                deletions.append(("grading_classsessiongrade", cursor.rowcount))

                # 4. Language level skip requests
                cursor.execute("DELETE FROM language_languagelevelskiprequest WHERE new_enrollment_id IS NOT NULL")
                deletions.append(("language_languagelevelskiprequest", cursor.rowcount))

                # 5. Academic degree progress
                cursor.execute("DELETE FROM academic_studentdegreeprogress WHERE fulfilling_enrollment_id IS NOT NULL")
                deletions.append(("academic_studentdegreeprogress", cursor.rowcount))

                # 6. Finance reconciliation matched enrollments
                cursor.execute("DELETE FROM finance_reconciliation_status_matched_enrollments")
                deletions.append(("finance_reconciliation_status_matched_enrollments", cursor.rowcount))

            for table_name, count in deletions:
                if count > 0:
                    print(f"   ✅ Deleted {count:,} records from {table_name}")
                else:
                    print(f"   ⚪ No records to delete from {table_name}")

            print("✅ Related records cleanup completed")

    except Exception as e:
        print(f"❌ Error during related records cleanup: {e!s}")
        raise


def cleanup_main_enrollment_records():
    """Delete all ClassHeaderEnrollment records."""

    print("🧹 Cleaning up main enrollment records...")

    try:
        with transaction.atomic():
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM enrollment_classheaderenrollment")
                cursor.fetchone()[0]

                cursor.execute("DELETE FROM enrollment_classheaderenrollment")
                deleted_count = cursor.rowcount

                print(f"   ✅ Deleted {deleted_count:,} ClassHeaderEnrollment records")

                # Verify deletion
                cursor.execute("SELECT COUNT(*) FROM enrollment_classheaderenrollment")
                count_after = cursor.fetchone()[0]

                if count_after == 0:
                    print("   ✅ All enrollment records successfully deleted")
                else:
                    print(f"   ⚠️  Warning: {count_after} records remain")

    except Exception as e:
        print(f"❌ Error during main records cleanup: {e!s}")
        raise


def verify_cleanup():
    """Verify that all enrollment records have been deleted."""

    print("📊 Verifying cleanup results...")

    with connection.cursor() as cursor:
        # Check main table
        cursor.execute("SELECT COUNT(*) FROM enrollment_classheaderenrollment")
        enrollment_count = cursor.fetchone()[0]

        # Check some key related tables
        cursor.execute("SELECT COUNT(*) FROM grading_classsessiongrade WHERE enrollment_id IS NOT NULL")
        grade_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM finance_invoice_line_item WHERE enrollment_id IS NOT NULL")
        invoice_count = cursor.fetchone()[0]

    print("📈 Cleanup Results:")
    print(f"   ClassHeaderEnrollment records: {enrollment_count}")
    print(f"   Grading records with enrollment_id: {grade_count}")
    print(f"   Invoice line items with enrollment_id: {invoice_count}")

    if enrollment_count == 0 and grade_count == 0 and invoice_count == 0:
        print("🎉 SUCCESS: All enrollment records and dependencies cleaned up!")
        return True
    else:
        print("⚠️  WARNING: Some records may not have been cleaned up")
        return False


def main():
    """Main execution function."""

    print("🧹 ClassHeaderEnrollment Cleanup")
    print("=" * 60)
    print("⚠️  This will delete ALL enrollment and related records!")
    print("   Use this to prepare for reimporting from refreshed legacy data")
    print("=" * 60)

    try:
        # Step 1: Check what we're about to delete
        check_related_records()

        print("\n⚠️  Proceeding with cleanup in 3 seconds...")
        import time

        time.sleep(3)

        # Step 2: Delete related records first
        cleanup_related_records()

        # Step 3: Delete main enrollment records
        cleanup_main_enrollment_records()

        # Step 4: Verify cleanup
        success = verify_cleanup()

        print("=" * 60)
        if success:
            print("🎉 Cleanup completed successfully!")
            print("Ready to reimport enrollment data from legacy")
        else:
            print("⚠️  Cleanup completed with warnings - check results")

    except Exception as e:
        print(f"❌ Fatal error: {e!s}")
        sys.exit(1)


if __name__ == "__main__":
    main()
