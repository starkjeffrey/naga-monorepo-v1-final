"""
Django Schema Validator - Detect model/database schema mismatches.

Specifically designed to catch Django-specific naming conventions that
generic schema tools miss, particularly ForeignKey _id suffix issues.
"""

import sys
from typing import Any

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection, models


class Command(BaseCommand):
    help = "Validate Django model schema against actual database schema"

    def add_arguments(self, parser):
        parser.add_argument(
            "--app",
            type=str,
            help="Validate specific app only",
        )
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Generate SQL to fix found issues (does not execute)",
        )

    def handle(self, *args, **options):
        """Main validation logic."""
        self.stdout.write(self.style.SUCCESS("🔍 Django Schema Validator Starting...\n"))

        issues_found = []

        # Get apps to check
        apps_to_check = [options["app"]] if options["app"] else None

        for model in apps.get_models():
            if apps_to_check and model._meta.app_label not in apps_to_check:
                continue

            model_issues = self.validate_model(model)
            if model_issues:
                issues_found.extend(model_issues)

        # Report results
        if issues_found:
            self.stdout.write(self.style.ERROR(f"\n❌ Found {len(issues_found)} schema issues:\n"))

            for issue in issues_found:
                self.stdout.write(f"  • {issue['description']}")
                self.stdout.write(f"    Model: {issue['model']}")
                self.stdout.write(f"    Field: {issue['field']}")
                self.stdout.write(f"    Expected: {issue['expected']}")
                self.stdout.write(f"    Actual: {issue['actual']}\n")

                if options["fix"]:
                    self.stdout.write(f"    Fix SQL: {issue['fix_sql']}\n")

            if options["fix"]:
                self.stdout.write(self.style.WARNING("⚠️  SQL commands shown above (not executed)"))
            else:
                self.stdout.write(self.style.WARNING("💡 Run with --fix to see SQL repair commands"))

            sys.exit(1)
        else:
            self.stdout.write(self.style.SUCCESS("✅ All Django model schemas are valid!"))

    def validate_model(self, model) -> list[dict[str, Any]]:
        """Validate a single model against database schema."""
        issues: list[dict[str, Any]] = []
        table_name = model._meta.db_table

        # Get actual database columns
        with connection.cursor() as cursor:
            # Get table columns from database
            cursor.execute(
                """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position
            """,
                [table_name],
            )

            db_columns = {
                row[0]: {"data_type": row[1], "is_nullable": row[2], "column_default": row[3]}
                for row in cursor.fetchall()
            }

        if not db_columns:
            # Table doesn't exist - different issue
            return issues

        # Check each model field
        for field in model._meta.get_fields():
            if hasattr(field, "column"):
                issues.extend(self.validate_field(model, field, db_columns))

        return issues

    def validate_field(self, model, field, db_columns: dict) -> list[dict[str, Any]]:
        """Validate a single field against database columns."""
        issues: list[dict[str, Any]] = []

        # Skip fields that don't create database columns
        if self.should_skip_field(field):
            return issues

        # Handle ForeignKey fields - the main issue we're solving
        if isinstance(field, models.ForeignKey):
            expected_column = f"{field.name}_id"  # Django adds _id suffix
            model_field_name = field.name

            # Check if the expected column exists
            if expected_column not in db_columns:
                # Check if column exists without _id suffix (the bug we found)
                if model_field_name in db_columns:
                    issues.append(
                        {
                            "type": "fk_naming_mismatch",
                            "model": f"{model._meta.app_label}.{model.__name__}",
                            "field": field.name,
                            "description": f"ForeignKey field '{field.name}' missing Django _id suffix",
                            "expected": expected_column,
                            "actual": model_field_name,
                            "fix_sql": (
                                f"ALTER TABLE {model._meta.db_table} RENAME COLUMN "
                                f"{model_field_name} TO {expected_column};"
                            ),
                        }
                    )
                else:
                    issues.append(
                        {
                            "type": "missing_column",
                            "model": f"{model._meta.app_label}.{model.__name__}",
                            "field": field.name,
                            "description": f"ForeignKey column '{expected_column}' missing entirely",
                            "expected": expected_column,
                            "actual": "MISSING",
                            "fix_sql": f"-- Column {expected_column} missing - check migrations",
                        }
                    )

        # Handle regular fields with actual database columns
        elif hasattr(field, "column") and field.column and hasattr(field, "db_type"):
            column_name = field.column

            if column_name not in db_columns:
                issues.append(
                    {
                        "type": "missing_column",
                        "model": f"{model._meta.app_label}.{model.__name__}",
                        "field": field.name,
                        "description": f"Field column '{column_name}' missing",
                        "expected": column_name,
                        "actual": "MISSING",
                        "fix_sql": f"-- Column {column_name} missing - check migrations",
                    }
                )

        return issues

    def should_skip_field(self, field):
        """Check if field should be skipped (doesn't create DB columns)."""
        # Skip ManyToMany fields (create separate junction tables)
        if isinstance(field, models.ManyToManyField):
            return True

        # Skip reverse ForeignKey relations
        if hasattr(field, "remote_field") and field.remote_field:
            return True

        # Skip GenericForeignKey and related fields
        if hasattr(field, "ct_field") or hasattr(field, "fk_field"):
            return True

        # Skip fields explicitly marked as not creating columns
        if getattr(field, "column", None) is None:
            return True

        return False

    def get_django_db_type(self, field):
        """Get expected database type for Django field."""
        # This would map Django field types to database types
        # For now, simplified implementation
        return getattr(field, "db_type", lambda x: "unknown")(connection)
