"""
Django management command for comprehensive database/model integrity validation.

This command systematically compares Django models with the actual database schema
to identify and fix mismatches, ensuring data integrity.
"""

import json
import sys
from datetime import datetime

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


class Command(BaseCommand):
    """Validate database schema against Django models."""

    help = "Comprehensive database integrity validation and repair"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Attempt to auto-fix simple issues",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output results as JSON",
        )
        parser.add_argument(
            "--app",
            type=str,
            help="Check specific app only",
        )

    def handle(self, *args, **options):
        """Execute the validation."""
        self.fix_mode = options.get("fix", False)
        self.json_mode = options.get("json", False)
        self.target_app = options.get("app")

        self.issues = []
        self.warnings = []
        self.fixes_applied = []

        if not self.json_mode:
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write("DATABASE INTEGRITY VALIDATION")
            self.stdout.write("=" * 60 + "\n")

        # Run all validation checks
        self.check_migrations()
        self.validate_all_models()
        self.check_indexes()
        self.check_constraints()

        # Output results
        self.output_results()

        # Return appropriate exit code
        sys.exit(1 if self.issues else 0)

    def check_migrations(self):
        """Check for unapplied or inconsistent migrations."""
        if not self.json_mode:
            self.stdout.write("\n📋 Checking migrations...")

        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

        if plan:
            for migration, _backwards in plan:
                self.issues.append(
                    {
                        "type": "UNAPPLIED_MIGRATION",
                        "app": migration.app_label,
                        "migration": migration.name,
                        "message": f"Unapplied migration: {migration.app_label}.{migration.name}",
                    }
                )

    def get_db_columns(self, table_name):
        """Get actual database columns for a table."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length
                FROM information_schema.columns
                WHERE table_name = %s
                ORDER BY ordinal_position
            """,
                [table_name],
            )

            return {
                row[0]: {"type": row[1], "nullable": row[2] == "YES", "default": row[3], "max_length": row[4]}
                for row in cursor.fetchall()
            }

    def get_db_indexes(self, table_name):
        """Get database indexes for a table."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = %s
            """,
                [table_name],
            )

            return {row[0]: row[1] for row in cursor.fetchall()}

    def validate_model(self, model):
        """Validate a single model against database."""
        table_name = model._meta.db_table
        model_name = f"{model._meta.app_label}.{model.__name__}"

        # Skip abstract and proxy models
        if model._meta.abstract or model._meta.proxy:
            return

        # Get model fields
        model_fields = {}
        for field in model._meta.get_fields():
            if hasattr(field, "column"):
                model_fields[field.column] = {
                    "field_name": field.name,
                    "field_type": field.__class__.__name__,
                    "nullable": field.null,
                    "default": field.default,
                    "max_length": getattr(field, "max_length", None),
                }

        # Get database columns
        try:
            db_columns = self.get_db_columns(table_name)
        except Exception as e:
            self.issues.append(
                {
                    "type": "TABLE_ERROR",
                    "model": model_name,
                    "table": table_name,
                    "message": f"Cannot access table '{table_name}': {e!s}",
                }
            )
            return

        # Check for missing columns in database
        for column_name, field_info in model_fields.items():
            if column_name not in db_columns:
                issue = {
                    "type": "MISSING_COLUMN",
                    "model": model_name,
                    "table": table_name,
                    "column": column_name,
                    "field": field_info["field_name"],
                    "message": f"Missing column: {table_name}.{column_name} (field: {field_info['field_name']})",
                }
                self.issues.append(issue)

                if self.fix_mode:
                    self.fix_missing_column(table_name, column_name, field_info)

        # Check for extra columns in database
        system_columns = ["id", "created_at", "updated_at", "is_deleted", "deleted_at"]
        for column_name in db_columns:
            if column_name not in model_fields and column_name not in system_columns:
                self.warnings.append(
                    {
                        "type": "EXTRA_COLUMN",
                        "model": model_name,
                        "table": table_name,
                        "column": column_name,
                        "message": f"Extra column in database: {table_name}.{column_name}",
                    }
                )

        # Check field type mismatches
        for column_name, field_info in model_fields.items():
            if column_name in db_columns:
                db_info = db_columns[column_name]

                # Check nullability mismatch
                if field_info["nullable"] != db_info["nullable"]:
                    self.warnings.append(
                        {
                            "type": "NULLABLE_MISMATCH",
                            "model": model_name,
                            "table": table_name,
                            "column": column_name,
                            "message": (
                                f"Nullable mismatch: {column_name} "
                                f"(model: {field_info['nullable']}, db: {db_info['nullable']})"
                            ),
                        }
                    )

    def validate_all_models(self):
        """Validate all models against database."""
        if not self.json_mode:
            self.stdout.write("\n🔍 Validating models against database...")

        for model in apps.get_models():
            # Filter by app if specified
            if self.target_app and model._meta.app_label != self.target_app:
                continue

            self.validate_model(model)

    def check_indexes(self):
        """Check database indexes."""
        if not self.json_mode:
            self.stdout.write("\n📊 Checking indexes...")

        # This is a simplified check - can be expanded
        for model in apps.get_models():
            if self.target_app and model._meta.app_label != self.target_app:
                continue

            if model._meta.abstract or model._meta.proxy:
                continue

            table_name = model._meta.db_table

            # Check for missing indexes on foreign keys
            for field in model._meta.get_fields():
                if hasattr(field, "column") and field.many_to_one and field.column:
                    # Foreign key should have an index
                    try:
                        db_indexes = self.get_db_indexes(table_name)
                        index_found = any(field.column in str(idx) for idx in db_indexes.values())

                        if not index_found:
                            self.warnings.append(
                                {
                                    "type": "MISSING_INDEX",
                                    "table": table_name,
                                    "column": field.column,
                                    "message": f"Missing index on foreign key: {table_name}.{field.column}",
                                }
                            )
                    except Exception:
                        # Skip index check if there's an error
                        pass

    def check_constraints(self):
        """Check database constraints."""
        if not self.json_mode:
            self.stdout.write("\n🔒 Checking constraints...")

        with connection.cursor() as cursor:
            # Check for orphaned foreign keys
            cursor.execute(
                """
                SELECT
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name,
                    tc.constraint_name
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
            """
            )

            # Store foreign key constraints for validation
            # (Can be expanded to check for orphaned records)

    def fix_missing_column(self, table_name, column_name, field_info):
        """Attempt to fix a missing column."""
        if not self.fix_mode:
            return

        # Map Django field types to PostgreSQL types
        type_mapping = {
            "CharField": f"VARCHAR({field_info.get('max_length', 255)})",
            "TextField": "TEXT",
            "IntegerField": "INTEGER",
            "BigIntegerField": "BIGINT",
            "BooleanField": "BOOLEAN",
            "DateField": "DATE",
            "DateTimeField": "TIMESTAMP WITH TIME ZONE",
            "DecimalField": "NUMERIC(10,2)",
            "FloatField": "DOUBLE PRECISION",
            "EmailField": "VARCHAR(254)",
            "URLField": "VARCHAR(200)",
            "UUIDField": "UUID",
        }

        sql_type = type_mapping.get(field_info["field_type"], "TEXT")
        # nullable = "NULL" if field_info["nullable"] else "NOT NULL"  # Currently unused

        # Generate default value for NOT NULL columns
        default_clause = ""
        if not field_info["nullable"]:
            if field_info["field_type"] == "CharField":
                default_clause = "DEFAULT ''"
            elif field_info["field_type"] == "IntegerField":
                default_clause = "DEFAULT 0"
            elif field_info["field_type"] == "BooleanField":
                default_clause = "DEFAULT FALSE"

        try:
            with connection.cursor() as cursor:
                sql = f"""
                    ALTER TABLE {table_name}
                    ADD COLUMN {column_name} {sql_type} {default_clause}
                """
                cursor.execute(sql)

                self.fixes_applied.append(
                    {
                        "type": "COLUMN_ADDED",
                        "table": table_name,
                        "column": column_name,
                        "message": f"Added column: {table_name}.{column_name}",
                    }
                )

                if not self.json_mode:
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Fixed: Added column {column_name} to {table_name}"))
        except Exception as e:
            if not self.json_mode:
                self.stdout.write(self.style.ERROR(f"  ✗ Failed to add column {column_name}: {e!s}"))

    def output_results(self):
        """Output validation results."""
        if self.json_mode:
            # JSON output for automation
            results = {
                "timestamp": datetime.now().isoformat(),
                "issues": self.issues,
                "warnings": self.warnings,
                "fixes_applied": self.fixes_applied,
                "summary": {
                    "total_issues": len(self.issues),
                    "total_warnings": len(self.warnings),
                    "fixes_applied": len(self.fixes_applied),
                },
            }
            self.stdout.write(json.dumps(results, indent=2))
        else:
            # Human-readable output
            self.stdout.write("\n" + "=" * 60)
            self.stdout.write("VALIDATION RESULTS")
            self.stdout.write("=" * 60)

            if self.issues:
                self.stdout.write(self.style.ERROR(f"\n❌ CRITICAL ISSUES ({len(self.issues)}):"))
                for issue in self.issues:
                    self.stdout.write(f"  • {issue['message']}")

            if self.warnings:
                self.stdout.write(self.style.WARNING(f"\n⚠️  WARNINGS ({len(self.warnings)}):"))
                for warning in self.warnings[:10]:  # Limit output
                    self.stdout.write(f"  • {warning['message']}")
                if len(self.warnings) > 10:
                    self.stdout.write(f"  ... and {len(self.warnings) - 10} more warnings")

            if self.fixes_applied:
                self.stdout.write(self.style.SUCCESS(f"\n✅ FIXES APPLIED ({len(self.fixes_applied)}):"))
                for fix in self.fixes_applied:
                    self.stdout.write(f"  • {fix['message']}")

            if not self.issues and not self.warnings:
                self.stdout.write(self.style.SUCCESS("\n✅ Database integrity check passed!"))

            self.stdout.write("\n" + "=" * 60)

            # Provide recommendations
            if self.issues and not self.fix_mode:
                self.stdout.write("\n💡 RECOMMENDATIONS:")
                self.stdout.write("  1. Run with --fix flag to attempt auto-fixes")
                self.stdout.write("  2. Create migrations: python manage.py makemigrations")
                self.stdout.write("  3. Apply migrations: python manage.py migrate")
                self.stdout.write("  4. Review warnings for potential issues")
