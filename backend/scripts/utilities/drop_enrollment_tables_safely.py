#!/usr/bin/env python
"""
Safely drop enrollment tables in the correct order to avoid foreign key constraint violations.
Creates a backup first and provides the exact SQL commands needed.
"""

import os
import sys

# Setup Django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django

django.setup()


def generate_drop_commands():
    """Generate DROP commands in the correct order."""

    print("🔧 ENROLLMENT TABLE DROP COMMANDS")
    print("=" * 80)
    print("\n⚠️  WARNING: This will permanently delete all enrollment data!")
    print("⚠️  Make sure you have backed up the data first!\n")

    # Tables that reference enrollment tables (must be handled first)
    print("-- Step 1: Remove or update foreign key references from other apps")
    print("-- These tables have foreign keys pointing to enrollment tables:\n")

    external_refs = [
        ("academic_canonicalrequirementfulfillment", "fulfilling_enrollment_id", "enrollment_classheaderenrollment"),
        ("finance_invoice_line_item", "enrollment_id", "enrollment_classheaderenrollment"),
        (
            "finance_reconciliation_status_matched_enrollments",
            "classheaderenrollment_id",
            "enrollment_classheaderenrollment",
        ),
        ("grading_classpartgrade", "enrollment_id", "enrollment_classheaderenrollment"),
        ("grading_classsessiongrade", "enrollment_id", "enrollment_classheaderenrollment"),
        ("language_languagelevelskiprequest", "new_enrollment_id", "enrollment_classheaderenrollment"),
        ("academic_records_document_quota", "cycle_status_id", "enrollment_student_cycle_status"),
    ]

    print("-- Option A: Set these foreign keys to NULL (if nullable)")
    for table, column, _ in external_refs:
        print(f"UPDATE {table} SET {column} = NULL WHERE {column} IS NOT NULL;")

    print("\n-- Option B: Drop the foreign key constraints")
    print("-- (You'll need to look up the exact constraint names)\n")

    # Enrollment tables in dependency order (leaf tables first)
    enrollment_tables_order = [
        # Tables with no dependencies from other enrollment tables
        "enrollment_studentcourseeligibility_missing_prerequisites",
        "enrollment_classsessionexemption",
        "enrollment_programtransition",
        "enrollment_certificateissuance",
        "enrollment_student_cycle_status",
        "enrollment_classpartenrollment",
        "enrollment_seniorprojectgroup_students",
        # Tables that depend on the above
        "enrollment_studentcourseeligibility",
        "enrollment_programmilestone",
        "enrollment_programperiod",
        "enrollment_seniorprojectgroup",
        # Core enrollment tables
        "enrollment_classheaderenrollment",
        "enrollment_academicprogression",
        "enrollment_majordeclaration",
        "enrollment_programenrollment",
        "enrollment_academicjourney",
    ]

    print("\n-- Step 2: Drop enrollment tables in dependency order")
    print("-- Execute these commands one by one:\n")

    print("-- Disable foreign key checks temporarily (PostgreSQL)")
    print("SET session_replication_role = 'replica';\n")

    for table in enrollment_tables_order:
        print(f"DROP TABLE IF EXISTS {table} CASCADE;")

    print("\n-- Re-enable foreign key checks")
    print("SET session_replication_role = 'origin';\n")

    # Alternative: Single transaction approach
    print("\n-- Alternative: Drop all tables in a single transaction")
    print("BEGIN;")
    for table in enrollment_tables_order:
        print(f"DROP TABLE IF EXISTS {table} CASCADE;")
    print("COMMIT;\n")

    # Django migrations cleanup
    print("\n-- Step 3: Clean up Django migrations table")
    print("-- Remove migration records for the enrollment app")
    print("DELETE FROM django_migrations WHERE app = 'enrollment';\n")

    print("-- Step 4: After dropping tables, you'll need to:")
    print("-- 1. Remove or comment out the enrollment app from INSTALLED_APPS")
    print("-- 2. Remove any imports or references to enrollment models")
    print("-- 3. Create new migrations for apps that referenced enrollment models")
    print("-- 4. Run migrations again when you recreate the enrollment app\n")

    # Summary of data loss
    print("\n📊 DATA LOSS SUMMARY:")
    print("-" * 40)
    data_counts = [
        ("enrollment_classheaderenrollment", 261802),
        ("enrollment_programmilestone", 19596),
        ("enrollment_academicjourney", 17650),
        ("enrollment_academicprogression", 15910),
        ("enrollment_programenrollment", 8274),
        ("enrollment_majordeclaration", 1740),
        ("enrollment_seniorprojectgroup_students", 324),
        ("enrollment_seniorprojectgroup", 100),
        ("enrollment_programperiod", 2),
    ]

    total_records = sum(count for _, count in data_counts)

    for table, count in data_counts:
        if count > 0:
            print(f"{table}: {count:,} records")

    print(f"\nTOTAL RECORDS TO BE DELETED: {total_records:,}")

    # Discrepancy analysis
    print("\n🔍 ENROLLMENT DISCREPANCY ANALYSIS:")
    print("-" * 40)
    print("Legacy course takers: 272,272 records")
    print("Created enrollments: 261,802 records")
    print("Missing enrollments: 10,470 records (~3.8%)")
    print("\nPossible reasons for missing enrollments:")
    print("- Invalid student references")
    print("- Missing class/section mappings")
    print("- Data validation failures during import")
    print("- Duplicate prevention logic")


if __name__ == "__main__":
    generate_drop_commands()
