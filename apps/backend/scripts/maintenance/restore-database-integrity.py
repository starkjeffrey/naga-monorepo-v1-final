#!/usr/bin/env python
"""
Database Integrity Restoration Tool for Naga SIS
==================================================
Comprehensive tool to analyze and fix database/model mismatches.

Usage:
    python restore-database-integrity.py --analyze    # Analyze issues only
    python restore-database-integrity.py --fix        # Apply safe fixes
    python restore-database-integrity.py --fix --force # Apply all fixes including risky ones
    python restore-database-integrity.py --dry-run    # Show what would be fixed
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import datetime
from enum import Enum
from typing import Any

# Django setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django

django.setup()

from django.apps import apps
from django.core.management import call_command
from django.core.management.color import color_style
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

# Color styling
style = color_style()


class IssueSeverity(Enum):
    """Issue severity levels."""

    CRITICAL = "CRITICAL"  # Could cause runtime errors
    HIGH = "HIGH"  # Data integrity issues
    MEDIUM = "MEDIUM"  # Schema inconsistencies
    LOW = "LOW"  # Cosmetic issues
    INFO = "INFO"  # Informational only


@dataclass
class IntegrityIssue:
    """Represents a database integrity issue."""

    severity: IssueSeverity
    category: str
    table: str
    description: str
    details: dict[str, Any] = dataclass_field(default_factory=dict)
    fix_available: bool = False
    fix_command: str = ""
    fix_risk: str = "low"  # low, medium, high


class DatabaseIntegrityChecker:
    """Main integrity checker and fixer."""

    def __init__(self, fix_mode=False, force=False, dry_run=False):
        self.fix_mode = fix_mode
        self.force = force
        self.dry_run = dry_run
        self.issues: list[IntegrityIssue] = []
        self.fixes_applied = 0
        self.report_dir = "project-docs/migration-reports"

        # Ensure report directory exists
        os.makedirs(self.report_dir, exist_ok=True)

        # Tables that should NEVER be touched or reported as issues
        self.protected_tables = {
            "legacy_students",
            "legacy_academic_classes",
            "legacy_course_takers",
            "legacy_receipt_headers",
            "django_migrations",  # Critical Django table
            "django_content_type",  # Django framework table
            "django_session",  # Django sessions
            "django_admin_log",  # Django admin logs
        }

        # Legacy tables specifically (subset of protected)
        self.legacy_tables = {
            "legacy_students",
            "legacy_academic_classes",
            "legacy_course_takers",
            "legacy_receipt_headers",
        }

        # Known orphaned ManyToMany tables
        self.orphaned_m2m_tables = {
            "people_teacherleaverequest_affected_class_parts",
            "curriculum_course_majors",
            "curriculum_courseparttemplate_textbooks",
            "enrollment_seniorprojectgroup_students",
            "scheduling_combinedcoursetemplate_courses",
            "scheduling_classpart_textbooks",
            "enrollment_studentcourseeligibility_missing_prerequisites",
            "finance_reconciliation_status_matched_enrollments",
            "scheduling_testperiodreset_specific_classes",
            "curriculum_seniorprojectgroup_students",
        }

    def run(self):
        """Main execution method."""
        print(style.MIGRATE_HEADING("\n" + "=" * 70))
        print(style.MIGRATE_HEADING("    DATABASE INTEGRITY RESTORATION TOOL"))
        print(style.MIGRATE_HEADING("=" * 70))

        # Step 1: Analyze issues
        print(style.MIGRATE_LABEL("\n[1/6] Checking migration status..."))
        self.check_migrations()

        print(style.MIGRATE_LABEL("\n[2/6] Analyzing extra tables..."))
        self.check_extra_tables()

        print(style.MIGRATE_LABEL("\n[3/6] Analyzing extra columns..."))
        self.check_extra_columns()

        print(style.MIGRATE_LABEL("\n[4/6] Analyzing NULL constraint mismatches..."))
        self.check_null_constraints()

        print(style.MIGRATE_LABEL("\n[5/6] Analyzing missing columns..."))
        self.check_missing_columns()

        # Step 2: Generate report
        print(style.MIGRATE_LABEL("\n[6/6] Generating report..."))
        report_file = self.generate_report()

        # Step 3: Apply fixes if requested
        if self.fix_mode:
            self.apply_fixes()

        # Step 4: Summary
        self.print_summary(report_file)

    def check_migrations(self):
        """Check for unapplied migrations."""
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

        if plan:
            issue = IntegrityIssue(
                severity=IssueSeverity.CRITICAL,
                category="Unapplied Migrations",
                table="N/A",
                description=f"{len(plan)} unapplied migrations found",
                details={"migrations": [str(m[0]) for m in plan]},
                fix_available=True,
                fix_command="python manage.py migrate",
                fix_risk="low",
            )
            self.issues.append(issue)

    def check_extra_tables(self):
        """Check for tables in database but not in models."""
        with connection.cursor() as cursor:
            # Get all tables in database
            cursor.execute(
                """
                SELECT tablename FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename
            """
            )
            db_tables = {row[0] for row in cursor.fetchall()}

            # Get all model tables
            model_tables = set()
            for model in apps.get_models():
                if not model._meta.abstract and not model._meta.proxy:
                    model_tables.add(model._meta.db_table)
                    # Add ManyToMany through tables
                    for field in model._meta.many_to_many:
                        if field.remote_field.through._meta.db_table:
                            model_tables.add(field.remote_field.through._meta.db_table)

            # Find extra tables
            extra_tables = db_tables - model_tables

            for table in extra_tables:
                # Skip all protected tables completely
                if table in self.protected_tables:
                    continue  # Don't even report these

                # Skip ANY table starting with legacy_
                if table.startswith("legacy_"):
                    continue  # Don't report any legacy_ tables

                if table in self.legacy_tables:
                    severity = IssueSeverity.INFO
                    category = "Legacy Table"
                    fix_available = False
                    description = f"Legacy import table '{table}' (keep for audit)"
                elif table in self.orphaned_m2m_tables:
                    severity = IssueSeverity.HIGH
                    category = "Orphaned M2M Table"
                    fix_available = True
                    description = f"Orphaned ManyToMany table '{table}'"
                    fix_risk = "medium"
                else:
                    severity = IssueSeverity.MEDIUM
                    category = "Extra Table"
                    fix_available = True
                    description = f"Unknown extra table '{table}'"
                    fix_risk = "high"

                issue = IntegrityIssue(
                    severity=severity,
                    category=category,
                    table=table,
                    description=description,
                    fix_available=fix_available and table not in self.legacy_tables,
                    fix_command=f"DROP TABLE IF EXISTS {table} CASCADE",
                    fix_risk=fix_risk if table not in self.legacy_tables else "none",
                )
                self.issues.append(issue)

    def check_extra_columns(self):
        """Check for columns in database but not in models."""
        # Tables to skip column checking for now
        skip_column_check = {
            "enrollment_academicjourney",  # Skip until investigated
        }

        for model in apps.get_models():
            if model._meta.abstract or model._meta.proxy:
                continue

            table_name = model._meta.db_table

            # Skip column checking for specific tables
            if table_name in skip_column_check:
                continue

            # Get model fields
            model_fields = set()
            for field in model._meta.get_fields():
                if hasattr(field, "column"):
                    model_fields.add(field.column)
                elif hasattr(field, "attname"):
                    model_fields.add(field.attname.replace("_id", ""))

            # Get database columns
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = %s
                """,
                    [table_name],
                )
                db_columns = {row[0] for row in cursor.fetchall()}

            # Find extra columns
            extra_columns = db_columns - model_fields - {"id"}

            for column in extra_columns:
                # Special handling for finance app
                if table_name == "finance_cashier_session" and column in [
                    "date",
                    "opening_time",
                    "closing_time",
                    "status",
                    "opening_cash",
                    "closing_cash",
                    "expected_cash",
                    "variance",
                ]:
                    severity = IssueSeverity.HIGH
                    description = f"Orphaned finance column '{column}' in {table_name}"
                    fix_risk = "medium"
                else:
                    severity = IssueSeverity.MEDIUM
                    description = f"Extra column '{column}' in {table_name}"
                    fix_risk = "low"

                issue = IntegrityIssue(
                    severity=severity,
                    category="Extra Column",
                    table=table_name,
                    description=description,
                    details={"column": column},
                    fix_available=True,
                    fix_command=f"ALTER TABLE {table_name} DROP COLUMN {column}",
                    fix_risk=fix_risk,
                )
                self.issues.append(issue)

    def check_null_constraints(self):
        """Check for NULL constraint mismatches."""
        for model in apps.get_models():
            if model._meta.abstract or model._meta.proxy:
                continue

            table_name = model._meta.db_table

            for field in model._meta.get_fields():
                if not hasattr(field, "column"):
                    continue

                column_name = field.column
                model_nullable = field.null

                # Check database constraint
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT is_nullable
                        FROM information_schema.columns
                        WHERE table_name = %s AND column_name = %s
                    """,
                        [table_name, column_name],
                    )
                    result = cursor.fetchone()

                    if result:
                        db_nullable = result[0] == "YES"

                        if model_nullable != db_nullable:
                            issue = IntegrityIssue(
                                severity=IssueSeverity.CRITICAL,
                                category="NULL Constraint Mismatch",
                                table=table_name,
                                description=f"Column '{column_name}': model={model_nullable}, db={db_nullable}",
                                details={"column": column_name, "model_null": model_nullable, "db_null": db_nullable},
                                fix_available=True,
                                fix_command=f"ALTER TABLE {table_name} ALTER COLUMN {column_name} "
                                f"{'DROP' if model_nullable else 'SET'} NOT NULL",
                                fix_risk="medium",
                            )
                            self.issues.append(issue)

    def check_missing_columns(self):
        """Check for columns in models but not in database."""
        for model in apps.get_models():
            if model._meta.abstract or model._meta.proxy:
                continue

            table_name = model._meta.db_table

            # Get database columns
            with connection.cursor() as cursor:
                try:
                    cursor.execute(
                        """
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_name = %s
                    """,
                        [table_name],
                    )
                    db_columns = {row[0] for row in cursor.fetchall()}
                except Exception:
                    # Table doesn't exist
                    continue

            # Check each model field
            for field in model._meta.get_fields():
                if not hasattr(field, "column"):
                    continue

                column_name = field.column

                if column_name not in db_columns:
                    issue = IntegrityIssue(
                        severity=IssueSeverity.CRITICAL,
                        category="Missing Column",
                        table=table_name,
                        description=f"Column '{column_name}' missing in database",
                        details={"column": column_name, "field_type": field.__class__.__name__},
                        fix_available=True,
                        fix_command="python manage.py makemigrations && python manage.py migrate",
                        fix_risk="low",
                    )
                    self.issues.append(issue)

    def apply_fixes(self):
        """Apply fixes for detected issues."""
        if self.dry_run:
            print(style.WARNING("\n🔍 DRY RUN MODE - No changes will be made"))
        else:
            print(style.WARNING("\n⚠️  APPLYING FIXES - Database will be modified"))

        # Group issues by risk level
        low_risk = [i for i in self.issues if i.fix_available and i.fix_risk == "low"]
        medium_risk = [i for i in self.issues if i.fix_available and i.fix_risk == "medium"]
        high_risk = [i for i in self.issues if i.fix_available and i.fix_risk == "high"]

        # Apply low risk fixes automatically
        if low_risk:
            print(style.SUCCESS(f"\n✅ Applying {len(low_risk)} low-risk fixes..."))
            for issue in low_risk:
                self.apply_single_fix(issue)

        # Apply medium risk fixes with confirmation
        if medium_risk and (self.force or self.dry_run):
            print(style.WARNING(f"\n⚠️  Applying {len(medium_risk)} medium-risk fixes..."))
            for issue in medium_risk:
                self.apply_single_fix(issue)

        # Only apply high risk with force flag
        if high_risk and self.force:
            print(style.ERROR(f"\n🚨 Applying {len(high_risk)} high-risk fixes..."))
            for issue in high_risk:
                self.apply_single_fix(issue)

    def apply_single_fix(self, issue: IntegrityIssue):
        """Apply a single fix."""
        print(f"  • {issue.description}")

        if self.dry_run:
            print(f"    Would run: {issue.fix_command}")
            return

        try:
            if issue.fix_command.startswith("python manage.py"):
                # Django management command
                cmd_parts = issue.fix_command.replace("python manage.py ", "").split()
                call_command(*cmd_parts)
            elif issue.fix_command.startswith("ALTER") or issue.fix_command.startswith("DROP"):
                # Direct SQL
                with connection.cursor() as cursor:
                    cursor.execute(issue.fix_command)

            self.fixes_applied += 1
            print(style.SUCCESS("    ✓ Fixed"))
        except Exception as e:
            print(style.ERROR(f"    ✗ Failed: {e!s}"))

    def generate_report(self):
        """Generate detailed report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = os.path.join(self.report_dir, f"integrity-restoration-{timestamp}.json")

        report_data = {
            "timestamp": timestamp,
            "total_issues": len(self.issues),
            "fixes_applied": self.fixes_applied,
            "issues_by_severity": {},
            "issues_by_category": {},
            "detailed_issues": [],
        }

        # Group by severity
        for severity in IssueSeverity:
            severity_issues = [i for i in self.issues if i.severity == severity]
            report_data["issues_by_severity"][severity.value] = len(severity_issues)

        # Group by category
        categories = {i.category for i in self.issues}
        for category in categories:
            category_issues = [i for i in self.issues if i.category == category]
            report_data["issues_by_category"][category] = len(category_issues)

        # Add detailed issues
        for issue in self.issues:
            report_data["detailed_issues"].append(
                {
                    "severity": issue.severity.value,
                    "category": issue.category,
                    "table": issue.table,
                    "description": issue.description,
                    "details": issue.details,
                    "fix_available": issue.fix_available,
                    "fix_risk": issue.fix_risk,
                    "fix_command": issue.fix_command,
                }
            )

        # Write report
        with open(report_file, "w") as f:
            json.dump(report_data, f, indent=2)

        return report_file

    def print_summary(self, report_file):
        """Print summary of findings."""
        print(style.MIGRATE_HEADING("\n" + "=" * 70))
        print(style.MIGRATE_HEADING("                        SUMMARY"))
        print(style.MIGRATE_HEADING("=" * 70))

        # Count by severity
        critical = len([i for i in self.issues if i.severity == IssueSeverity.CRITICAL])
        high = len([i for i in self.issues if i.severity == IssueSeverity.HIGH])
        medium = len([i for i in self.issues if i.severity == IssueSeverity.MEDIUM])
        low = len([i for i in self.issues if i.severity == IssueSeverity.LOW])
        info = len([i for i in self.issues if i.severity == IssueSeverity.INFO])

        print(f"\nTotal Issues Found: {len(self.issues)}")
        if critical:
            print(style.ERROR(f"  🚨 CRITICAL: {critical}"))
        if high:
            print(style.WARNING(f"  ⚠️  HIGH: {high}"))
        if medium:
            print(style.WARNING(f"  ⚠️  MEDIUM: {medium}"))
        if low:
            print(f"  ℹ️  LOW: {low}")
        if info:
            print(f"  ℹ️  INFO: {info}")

        if self.fix_mode and not self.dry_run:
            print(style.SUCCESS(f"\n✅ Fixes Applied: {self.fixes_applied}"))

        print(f"\n📋 Report saved to: {report_file}")

        # Recommendations
        if critical > 0:
            print(style.ERROR("\n🚨 CRITICAL ISSUES DETECTED!"))
            print("   Run with --fix to apply safe fixes")
            print("   Run with --fix --force to apply all fixes (CAREFUL!)")

        return critical == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Database Integrity Restoration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python restore-database-integrity.py --analyze      # Analysis only
  python restore-database-integrity.py --fix          # Apply safe fixes
  python restore-database-integrity.py --fix --force  # Apply all fixes
  python restore-database-integrity.py --dry-run      # Preview changes
        """,
    )

    parser.add_argument("--analyze", action="store_true", help="Analyze issues only (default)")

    parser.add_argument("--fix", action="store_true", help="Apply fixes for detected issues")

    parser.add_argument("--force", action="store_true", help="Force application of risky fixes")

    parser.add_argument("--dry-run", action="store_true", help="Show what would be fixed without making changes")

    args = parser.parse_args()

    # Default to analyze mode if nothing specified
    if not args.fix and not args.analyze:
        args.analyze = True

    # Create and run checker
    checker = DatabaseIntegrityChecker(fix_mode=args.fix, force=args.force, dry_run=args.dry_run)

    try:
        checker.run()
    except KeyboardInterrupt:
        print(style.ERROR("\n\n❌ Interrupted by user"))
        sys.exit(1)
    except Exception as e:
        print(style.ERROR(f"\n\n❌ Error: {e!s}"))
        sys.exit(1)


if __name__ == "__main__":
    main()
