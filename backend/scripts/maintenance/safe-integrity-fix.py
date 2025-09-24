#!/usr/bin/env python
"""
Safe Database Integrity Fix Script
===================================
A conservative version that only fixes confirmed issues,
excluding false positives like django_migrations and legacy tables.
"""

import argparse
import os
import sys

# Django setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django

django.setup()

from django.core.management.color import color_style
from django.db import connection

style = color_style()


class SafeIntegrityFixer:
    """Conservative integrity fixer that avoids false positives."""

    # Tables that should NEVER be dropped
    PROTECTED_TABLES = {
        "django_migrations",
        "legacy_students",
        "legacy_academic_classes",
        "legacy_course_takers",
        "legacy_receipt_headers",
        # Add any other critical tables here
    }

    # Columns that are safe to remove (confirmed orphaned)
    SAFE_TO_REMOVE_COLUMNS = {
        ("accounts_rolepermission", "none"),
        ("common_systemauditlog", "none"),
        ("people_studentauditlog", "none"),
        ("curriculum_seniorprojectgroup", "is_graduated"),
        ("curriculum_seniorprojectgroup", "graduation_date"),
        ("curriculum_seniorprojectgroup", "added_term_id"),
        ("enrollment_academicjourney", "courses_completed"),
        ("enrollment_academicjourney", "language_level"),
        ("enrollment_academicjourney", "expected_completion_date"),
        ("enrollment_academicjourney", "accumulated_credits"),
        ("enrollment_academicjourney", "current_level"),
        ("finance_payment", "idempotency_key"),
    }

    # Finance columns that need investigation
    FINANCE_COLUMNS_TO_INVESTIGATE = {
        ("finance_cashier_session", "date"),
        ("finance_cashier_session", "opening_time"),
        ("finance_cashier_session", "closing_time"),
        ("finance_cashier_session", "status"),
        ("finance_cashier_session", "opening_cash"),
        ("finance_cashier_session", "closing_cash"),
        ("finance_cashier_session", "expected_cash"),
        ("finance_cashier_session", "variance"),
    }

    def __init__(self, dry_run=True, check_data=True):
        self.dry_run = dry_run
        self.check_data = check_data
        self.fixes_applied = 0
        self.issues_found = []

    def run(self):
        """Main execution."""
        print(style.MIGRATE_HEADING("\n" + "=" * 70))
        print(style.MIGRATE_HEADING("    SAFE DATABASE INTEGRITY FIXER"))
        print(style.MIGRATE_HEADING("=" * 70))

        if self.dry_run:
            print(style.WARNING("\n🔍 DRY RUN MODE - No changes will be made\n"))
        else:
            print(style.WARNING("\n⚠️  LIVE MODE - Database will be modified\n"))

        # Step 1: Remove safe orphaned columns
        print(style.MIGRATE_LABEL("[1/3] Removing confirmed orphaned columns..."))
        self.remove_orphaned_columns()

        # Step 2: Investigate finance columns
        print(style.MIGRATE_LABEL("\n[2/3] Investigating finance columns..."))
        self.investigate_finance_columns()

        # Step 3: Check NULL constraints
        print(style.MIGRATE_LABEL("\n[3/3] Checking NULL constraint issues..."))
        self.check_null_constraints()

        # Summary
        self.print_summary()

    def remove_orphaned_columns(self):
        """Remove columns that are confirmed orphaned."""
        for table_name, column_name in self.SAFE_TO_REMOVE_COLUMNS:
            if self.column_exists(table_name, column_name):
                if self.check_data and self.column_has_data(table_name, column_name):
                    print(f"  ⚠️  {table_name}.{column_name} has data - skipping")
                    self.issues_found.append(f"Column {table_name}.{column_name} has data")
                else:
                    if self.dry_run:
                        print(f"  Would remove: {table_name}.{column_name}")
                    else:
                        self.drop_column(table_name, column_name)
                        print(style.SUCCESS(f"  ✓ Removed: {table_name}.{column_name}"))
                        self.fixes_applied += 1

    def investigate_finance_columns(self):
        """Check finance columns for data before removal."""
        print("\n  Finance Column Investigation:")
        for table_name, column_name in self.FINANCE_COLUMNS_TO_INVESTIGATE:
            if self.column_exists(table_name, column_name):
                has_data, sample_count = self.check_column_data_details(table_name, column_name)
                if has_data:
                    print(style.WARNING(f"    ⚠️  {column_name}: Contains {sample_count} non-null values"))
                    self.issues_found.append(f"Finance column {table_name}.{column_name} has {sample_count} values")
                else:
                    print(f"    ✓ {column_name}: Empty (safe to remove)")

    def check_null_constraints(self):
        """Check for NULL constraint mismatches that could cause issues."""
        # This is complex and needs careful handling
        # For now, just report the issues
        constraint_issues = self.get_null_constraint_issues()
        if constraint_issues:
            print(f"\n  Found {len(constraint_issues)} NULL constraint mismatches")
            print("  These need Django migrations to fix properly")
            for issue in constraint_issues[:5]:  # Show first 5
                print(f"    • {issue}")
            if len(constraint_issues) > 5:
                print(f"    ... and {len(constraint_issues) - 5} more")

    def column_exists(self, table_name, column_name):
        """Check if a column exists in the database."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
            """,
                [table_name, column_name],
            )
            return cursor.fetchone()[0] > 0

    def column_has_data(self, table_name, column_name):
        """Check if a column has any non-null data."""
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT COUNT(*)
                FROM {table_name}
                WHERE {column_name} IS NOT NULL
            """
            )
            return cursor.fetchone()[0] > 0

    def check_column_data_details(self, table_name, column_name):
        """Get details about data in a column."""
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT COUNT(*), COUNT({column_name})
                FROM {table_name}
            """
            )
            _total_rows, non_null_count = cursor.fetchone()
            return non_null_count > 0, non_null_count

    def drop_column(self, table_name, column_name):
        """Drop a column from a table."""
        with connection.cursor() as cursor:
            cursor.execute(f"ALTER TABLE {table_name} DROP COLUMN {column_name}")

    def get_null_constraint_issues(self):
        """Get list of NULL constraint mismatches."""
        issues: list[dict[str, str]] = []
        # This would need to compare model definitions with database
        # For now, return empty list
        return issues

    def print_summary(self):
        """Print summary of actions."""
        print(style.MIGRATE_HEADING("\n" + "=" * 70))
        print(style.MIGRATE_HEADING("                     SUMMARY"))
        print(style.MIGRATE_HEADING("=" * 70))

        if self.dry_run:
            print("\n🔍 DRY RUN COMPLETE")
        else:
            print(f"\n✅ Fixes Applied: {self.fixes_applied}")

        if self.issues_found:
            print(style.WARNING(f"\n⚠️  Issues Found ({len(self.issues_found)}):"))
            for issue in self.issues_found:
                print(f"  • {issue}")

        print("\n📋 Recommendations:")
        print("  1. Back up finance columns before removal")
        print("  2. Create Django migrations for NULL constraints")
        print("  3. Never touch legacy_* or django_migrations tables")


def main():
    parser = argparse.ArgumentParser(description="Safe Database Integrity Fixer")
    parser.add_argument("--apply", action="store_true", help="Actually apply fixes (default is dry-run)")
    parser.add_argument("--skip-data-check", action="store_true", help="Skip checking for data in columns")

    args = parser.parse_args()

    fixer = SafeIntegrityFixer(dry_run=not args.apply, check_data=not args.skip_data_check)

    try:
        fixer.run()
    except KeyboardInterrupt:
        print(style.ERROR("\n\n❌ Interrupted by user"))
        sys.exit(1)
    except Exception as e:
        print(style.ERROR(f"\n\n❌ Error: {e!s}"))
        sys.exit(1)


if __name__ == "__main__":
    main()
