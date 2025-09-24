#!/usr/bin/env python
"""
Safely drop scheduling tables (ClassHeader, ClassSession, ClassPart) in the correct order
to avoid foreign key constraint violations. This is needed to re-import with new ClassPartType choices.
"""

import os
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django

django.setup()

from django.db import connection


def get_table_counts():
    """Get current record counts for scheduling tables."""
    tables_to_check = [
        "scheduling_classpart",
        "scheduling_classsession",
        "scheduling_classheader",
        "scheduling_classparttemplate",
        "scheduling_classparttemplate_default_textbooks",
        "scheduling_classparttemplateset",
    ]

    counts = {}
    with connection.cursor() as cursor:
        for table in tables_to_check:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                counts[table] = cursor.fetchone()[0]
            except Exception as e:
                counts[table] = f"Error: {e}"

    return counts


def generate_drop_commands():
    """Generate DROP commands for scheduling tables in correct order."""

    print("🗂️  SCHEDULING TABLE DROP COMMANDS")
    print("=" * 80)
    print("\n⚠️  WARNING: This will permanently delete all scheduling data!")
    print("⚠️  Make sure you understand the implications!\n")

    # Get current counts
    print("📊 CURRENT TABLE COUNTS:")
    print("-" * 40)
    counts = get_table_counts()
    total_records = 0

    for table, count in counts.items():
        if isinstance(count, int):
            print(f"{table}: {count:,} records")
            total_records += count
        else:
            print(f"{table}: {count}")

    print(f"\nTOTAL RECORDS TO BE DELETED: {total_records:,}")

    # External references that need to be handled
    print("\n-- Step 1: Check for foreign key references from other apps")
    print("-- These tables may reference scheduling tables:\n")

    external_refs = [
        ("enrollment_classheaderenrollment", "class_header_id", "scheduling_classheader"),
        ("enrollment_classpartenrollment", "class_part_id", "scheduling_classpart"),
        ("grading_classpartgrade", "class_part_id", "scheduling_classpart"),
        ("grading_classsessiongrade", "class_session_id", "scheduling_classsession"),
        ("attendance_attendancesession", "class_part_id", "scheduling_classpart"),
        ("attendance_attendancearchive", "class_part_id", "scheduling_classpart"),
        ("attendance_permissionrequest", "class_part_id", "scheduling_classpart"),
        ("attendance_rostersync", "class_part_id", "scheduling_classpart"),
        ("people_teacherleaverequest_affected_class_parts", "classpart_id", "scheduling_classpart"),
        ("scheduling_testperiodreset_specific_classes", "classheader_id", "scheduling_classheader"),
    ]

    print("-- Check which tables have data referencing scheduling tables:")
    with connection.cursor() as cursor:
        for table, column, ref_table in external_refs:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE {column} IS NOT NULL")
                count = cursor.fetchone()[0]
                if count > 0:
                    print(f"-- {table}.{column}: {count:,} references to {ref_table}")
            except Exception as e:
                print(f"-- {table}.{column}: Error checking - {e}")

    print("\n-- Step 2: Drop scheduling tables in dependency order")
    print("-- Execute these commands carefully:\n")

    # Scheduling tables in dependency order (leaf tables first)
    scheduling_tables_order = [
        # Tables with no dependencies within scheduling
        "scheduling_classpart_textbooks",  # M2M table for ClassPart textbooks
        "scheduling_classparttemplate_default_textbooks",  # M2M table for templates
        "scheduling_testperiodreset_specific_classes",  # M2M table referencing ClassHeader
        # Core scheduling tables (in dependency order)
        "scheduling_classpart",  # References ClassSession
        "scheduling_classsession",  # References ClassHeader
        "scheduling_classheader",  # References Course, Term, Room, Teacher
        # Template tables (these are independent)
        "scheduling_classparttemplate",  # References ClassPartTemplateSet
        "scheduling_classparttemplateset",
        # Other scheduling tables
        "scheduling_combinedclassinstance",
        "scheduling_combinedclassgroup",
        "scheduling_classpromotionrule",
        "scheduling_readingclass",
    ]

    print("-- Option A: Use CASCADE to handle dependencies automatically")
    print("BEGIN;")
    for table in scheduling_tables_order:
        print(f"DROP TABLE IF EXISTS {table} CASCADE;")
    print("COMMIT;\n")

    print("-- Option B: Drop one by one with foreign key checks disabled")
    print("SET session_replication_role = 'replica';")
    for table in scheduling_tables_order:
        print(f"DROP TABLE IF EXISTS {table} CASCADE;")
    print("SET session_replication_role = 'origin';\n")

    # Django migrations cleanup
    print("-- Step 3: Clean up Django migrations table")
    print("-- Remove migration records for scheduling tables")
    print("DELETE FROM django_migrations WHERE app = 'scheduling';\n")

    print("-- Step 4: After dropping tables, you'll need to:")
    print("-- 1. Run: docker compose -f docker-compose.local.yml run --rm django python manage.py migrate")
    print(
        "-- 2. Re-import data with: docker compose -f docker-compose.local.yml run --rm django python manage.py import_academiccoursetakers_enhanced"
    )
    print("-- 3. Verify the new ClassPartType choices and original NormalizedPart names\n")

    print("🎯 PURPOSE:")
    print("-" * 40)
    print("This drop is needed to:")
    print("- Replace 'Main' ClassPartType with proper choices (ONLINE, BA, READING, etc.)")
    print("- Store original NormalizedPart data in ClassPart.name field")
    print("- Clean up the current data that has generic 'Main' everywhere")


def execute_drop_safely():
    """Execute the drop commands safely with user confirmation."""
    print("\n" + "=" * 60)
    print("🚨 FINAL CONFIRMATION REQUIRED")
    print("=" * 60)

    counts = get_table_counts()
    total_records = sum(count for count in counts.values() if isinstance(count, int))

    print(f"\nThis will DELETE {total_records:,} records from scheduling tables!")
    print("This action cannot be undone.")
    print("\nType 'DELETE ALL SCHEDULING DATA' to confirm:")

    confirmation = input("> ")

    if confirmation != "DELETE ALL SCHEDULING DATA":
        print("❌ Operation cancelled. No data was deleted.")
        return False

    print("\n🔄 Executing DROP commands...")

    # Drop tables in correct order
    scheduling_tables_order = [
        "scheduling_classpart_textbooks",
        "scheduling_classparttemplate_default_textbooks",
        "scheduling_testperiodreset_specific_classes",
        "scheduling_classpart",
        "scheduling_classsession",
        "scheduling_classheader",
        "scheduling_classparttemplate",
        "scheduling_classparttemplateset",
        "scheduling_combinedclassinstance",
        "scheduling_combinedclassgroup",
        "scheduling_classpromotionrule",
        "scheduling_readingclass",
    ]

    try:
        with connection.cursor() as cursor:
            cursor.execute("BEGIN;")

            for table in scheduling_tables_order:
                print(f"  Dropping {table}...")
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")

            # Clean up migrations
            print("  Cleaning up Django migrations...")
            cursor.execute("DELETE FROM django_migrations WHERE app = 'scheduling';")

            cursor.execute("COMMIT;")

        print("\n✅ Scheduling tables dropped successfully!")
        print("\nNext steps:")
        print("1. Run migrations: docker compose -f docker-compose.local.yml run --rm django python manage.py migrate")
        print(
            "2. Re-import data: docker compose -f docker-compose.local.yml run --rm django python manage.py import_academiccoursetakers_enhanced"
        )
        return True

    except Exception as e:
        print(f"\n❌ Error dropping tables: {e}")
        print("Database state may be inconsistent. Check manually.")
        return False


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Drop scheduling tables safely")
    parser.add_argument("--execute", action="store_true", help="Actually execute the drop (requires confirmation)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be dropped without executing")

    args = parser.parse_args()

    if args.execute:
        execute_drop_safely()
    else:
        generate_drop_commands()
