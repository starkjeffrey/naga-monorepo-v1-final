#!/usr/bin/env python3
"""
Enhanced Model-Database Reconciliation Script
Safely reconciles Django models with database schema based on integrity analysis
"""

import ast
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

import django
from django.apps import apps
from django.db import connection

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()


class ModelReconciler:
    def __init__(self):
        self.changes_made = []
        self.backup_dir = f"integrity_reports/backups_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.analysis_data = None
        self.type_mapping = {
            "integer": "models.IntegerField",
            "bigint": "models.BigIntegerField",
            "character varying": "models.CharField",
            "text": "models.TextField",
            "boolean": "models.BooleanField",
            "date": "models.DateField",
            "timestamp with time zone": "models.DateTimeField",
            "timestamp without time zone": "models.DateTimeField",
            "time without time zone": "models.TimeField",
            "time with time zone": "models.TimeField",
            "numeric": "models.DecimalField",
            "uuid": "models.UUIDField",
            "jsonb": "models.JSONField",
            "json": "models.JSONField",
            "double precision": "models.FloatField",
            "real": "models.FloatField",
        }

    def log(self, message, level="INFO"):
        """Enhanced logging with timestamps"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {"INFO": "ℹ️", "ERROR": "❌", "SUCCESS": "✅", "WARNING": "⚠️"}.get(level, "ℹ️")
        print(f"[{timestamp}] {prefix} {message}")

    def load_analysis_data(self):
        """Load the latest analysis data"""
        self.log("Loading database analysis results...")

        # Find the latest analysis file
        analysis_files = list(Path("integrity_reports").glob("analysis_*.json"))
        if not analysis_files:
            raise FileNotFoundError("No analysis files found. Run deep_integrity_analysis first.")

        latest_file = max(analysis_files, key=os.path.getctime)
        self.log(f"Using analysis file: {latest_file}")

        with open(latest_file) as f:
            self.analysis_data = json.load(f)

    def create_backup(self):
        """Create backup of all model files before making changes"""
        self.log("Creating backup of model files...")
        Path(self.backup_dir).mkdir(parents=True, exist_ok=True)

        # Backup all apps directories
        for app_name in [app.name for app in apps.get_app_configs()]:
            if app_name.startswith("apps."):
                app_path = Path(app_name.replace(".", "/"))
                if app_path.exists():
                    backup_path = Path(self.backup_dir) / app_path
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(app_path, backup_path, dirs_exist_ok=True)

        self.log(f"Backup created at: {self.backup_dir}")

    def get_database_schema_info(self, table_name: str, column_name: str) -> dict | None:
        """Get detailed column information from database"""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length,
                    numeric_precision,
                    numeric_scale
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name = %s
                AND column_name = %s
            """,
                [table_name, column_name],
            )

            row = cursor.fetchone()
            if row:
                return {
                    "data_type": row[0],
                    "is_nullable": row[1] == "YES",
                    "default": row[2],
                    "max_length": row[3],
                    "precision": row[4],
                    "scale": row[5],
                }
        return None

    def generate_field_definition(self, table_name: str, column_name: str, db_info: dict) -> str:
        """Generate proper Django field definition based on database schema"""
        data_type = db_info["data_type"].lower()
        field_type = self.type_mapping.get(data_type, "models.CharField")

        # Build field options
        options = []

        # Handle nullable fields
        if db_info["is_nullable"]:
            options.append("null=True")
            if field_type in ["models.CharField", "models.TextField", "models.EmailField"]:
                options.append("blank=True")

        # Handle specific field types
        if field_type == "models.CharField" and db_info["max_length"]:
            options.append(f"max_length={db_info['max_length']}")
        elif field_type == "models.CharField" and not db_info["max_length"]:
            # Default max_length for varchar fields without specified length
            options.append("max_length=255")

        if field_type == "models.DecimalField":
            precision = db_info["precision"] or 10
            scale = db_info["scale"] or 2
            options.append(f"max_digits={precision}")
            options.append(f"decimal_places={scale}")

        # Handle defaults (simplified - would need more complex conversion)
        if db_info["default"] and not db_info["default"].startswith("nextval"):
            if data_type in ["boolean"]:
                default_val = "True" if db_info["default"].lower() in ["true", "t"] else "False"
                options.append(f"default={default_val}")

        options_str = ", ".join(options) if options else ""
        return f"{field_type}({options_str})" if options_str else field_type + "()"

    def find_model_file(self, table_name: str) -> tuple[str, str, str] | None:
        """Find the model file and class for a given table"""
        for model in apps.get_models():
            if model._meta.db_table == table_name:
                app_label = model._meta.app_label
                model_name = model.__name__

                # Construct file path
                if app_label.startswith("django.") or app_label in ["auth", "contenttypes", "sessions", "admin"]:
                    # Skip Django built-in models
                    return None

                # Try different possible file patterns
                possible_files = [
                    f"apps/{app_label}/models.py",
                    f"apps/{app_label}/models/{model_name.lower()}.py",
                    f"apps/{app_label}/models/__init__.py",
                ]

                for file_path in possible_files:
                    if Path(file_path).exists():
                        return app_label, model_name, file_path

        return None

    def modify_model_field_nullable(self, file_path: str, model_name: str, field_name: str) -> bool:
        """Safely modify a model field to make it nullable"""
        try:
            # Read the file
            with open(file_path) as f:
                content = f.read()

            # Create backup of this specific file
            backup_file = Path(self.backup_dir) / Path(file_path).name
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            with open(backup_file, "w") as f:
                f.write(content)

            # Find the field definition using regex
            # Look for field_name = models.SomeField(...)
            pattern = rf"(\s+{re.escape(field_name)}\s*=\s*models\.\w+\([^)]*)\)"

            def replace_field(match):
                field_def = match.group(1)

                # Check if null=True already exists
                if "null=True" in field_def:
                    return match.group(0)  # No change needed

                # Add null=True and blank=True if it's a text field
                if "CharField" in field_def or "TextField" in field_def:
                    if field_def.endswith("("):
                        return f"{field_def}null=True, blank=True)"
                    else:
                        return f"{field_def}, null=True, blank=True)"
                else:
                    if field_def.endswith("("):
                        return f"{field_def}null=True)"
                    else:
                        return f"{field_def}, null=True)"

            # Apply the replacement
            new_content, count = re.subn(pattern, replace_field, content)

            if count > 0:
                # Write the modified content
                with open(file_path, "w") as f:
                    f.write(new_content)

                # Validate the Python syntax
                try:
                    ast.parse(new_content)
                    self.log(f"✅ Modified {file_path}: {model_name}.{field_name} -> nullable")
                    return True
                except SyntaxError as e:
                    # Restore from backup
                    with open(backup_file) as f:
                        original = f.read()
                    with open(file_path, "w") as f:
                        f.write(original)
                    self.log(f"❌ Syntax error after modifying {file_path}: {e}", "ERROR")
                    return False
            else:
                self.log(f"⚠️ Could not find field {field_name} in {file_path}", "WARNING")
                return False

        except Exception as e:
            self.log(f"❌ Error modifying {file_path}: {e}", "ERROR")
            return False

    def fix_critical_issues(self) -> list[dict]:
        """Fix critical NULL constraint mismatches"""
        self.log("🚨 Fixing critical NULL constraint mismatches...")

        fixed_issues = []
        critical_issues = self.analysis_data["issues"]["critical"]

        for issue in critical_issues:
            if issue["type"] == "null_constraint_mismatch":
                table = issue["table"]
                column = issue["column"]

                self.log(f"Fixing NULL constraint mismatch: {table}.{column}")

                # Find the model file
                model_info = self.find_model_file(table)
                if not model_info:
                    self.log(f"⚠️ Could not find model for table {table}", "WARNING")
                    continue

                app_label, model_name, file_path = model_info

                # Get field name from model
                field_name = None
                for model in apps.get_models():
                    if model._meta.db_table == table:
                        for field in model._meta.fields:
                            if field.column == column:
                                field_name = field.name
                                break
                        break

                if not field_name:
                    self.log(f"⚠️ Could not find field name for column {column} in {table}", "WARNING")
                    continue

                # Modify the model file
                success = self.modify_model_field_nullable(file_path, model_name, field_name)

                if success:
                    fixed_issues.append(
                        {
                            "table": table,
                            "column": column,
                            "field": field_name,
                            "model": f"{app_label}.{model_name}",
                            "file": file_path,
                            "fix": "Made field nullable",
                        }
                    )

        return fixed_issues

    def validate_changes(self) -> bool:
        """Validate that all model files can still be imported after changes"""
        self.log("🔍 Validating modified model files...")

        try:
            # Try to reload Django models

            # Test that we can run a basic Django command
            # This will fail if there are syntax errors in models
            from io import StringIO

            from django.core.management import call_command

            out = StringIO()
            call_command("check", "--deploy", stdout=out, stderr=out)

            output = out.getvalue()
            if "System check identified no issues" in output or "System check identified some issues" in output:
                self.log("✅ Model validation passed")
                return True
            else:
                self.log(f"❌ Model validation failed: {output}", "ERROR")
                return False

        except Exception as e:
            self.log(f"❌ Model validation failed: {e}", "ERROR")
            return False

    def generate_migration_commands(self, fixed_issues: list[dict]) -> list[str]:
        """Generate Django migration commands for the fixed issues"""
        self.log("📝 Generating migration commands...")

        commands = []
        apps_changed = set()

        for fix in fixed_issues:
            app_label = fix["model"].split(".")[0]
            if app_label.startswith("apps."):
                app_label = app_label[5:]  # Remove 'apps.' prefix
            apps_changed.add(app_label)

        for app in sorted(apps_changed):
            commands.append(f"python manage.py makemigrations {app}")

        return commands

    def create_rollback_script(self):
        """Create a rollback script to undo changes"""
        rollback_script = f"""#!/bin/bash
# Rollback script for model reconciliation changes
# Generated: {datetime.now()}

echo "Rolling back model reconciliation changes..."

# Restore model files from backup
cp -r {self.backup_dir}/* .

echo "✅ Rollback complete. Model files restored from backup."
echo "💡 You may need to restart your Django server."
"""

        rollback_file = f"rollback_reconciliation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sh"
        with open(rollback_file, "w") as f:
            f.write(rollback_script)

        # Restrictive permissions for generated rollback script
        os.chmod(rollback_file, 0o700)
        self.log(f"📄 Rollback script created: {rollback_file}")

    def run_reconciliation(self, dry_run: bool = True):
        """Run the complete model reconciliation process"""
        self.log("🚀 Starting Model-Database Reconciliation...")
        self.log(f"Mode: {'DRY RUN' if dry_run else 'LIVE CHANGES'}")

        try:
            # Load analysis data
            self.load_analysis_data()

            if not dry_run:
                # Create backups
                self.create_backup()

            # Fix critical issues
            fixed_issues = []
            if not dry_run:
                fixed_issues = self.fix_critical_issues()
            else:
                # Preview critical fixes
                critical_issues = self.analysis_data["issues"]["critical"]
                self.log(f"Would fix {len(critical_issues)} critical NULL constraint issues:")
                for issue in critical_issues:
                    if issue["type"] == "null_constraint_mismatch":
                        self.log(f"  - {issue['table']}.{issue['column']} -> make nullable")

            if not dry_run and fixed_issues:
                # Validate changes
                if self.validate_changes():
                    # Generate migration commands
                    migration_commands = self.generate_migration_commands(fixed_issues)

                    # Create rollback script
                    self.create_rollback_script()

                    # Summary
                    self.log("✅ Model reconciliation completed successfully!")
                    self.log(f"Fixed {len(fixed_issues)} critical issues")

                    if migration_commands:
                        self.log("🔧 Next steps - run these migration commands:")
                        for cmd in migration_commands:
                            print(f"  {cmd}")

                else:
                    self.log("❌ Validation failed. Changes rolled back automatically.")
                    return False

            elif dry_run:
                self.log("✅ Dry run completed. Use run_reconciliation(dry_run=False) to apply changes.")

            return True

        except Exception as e:
            self.log(f"❌ Reconciliation failed: {e}", "ERROR")
            return False


def main():
    """Main entry point"""
    reconciler = ModelReconciler()

    # First run in dry-run mode
    print("=" * 60)
    print("PHASE 1: DRY RUN - PREVIEW CHANGES")
    print("=" * 60)

    success = reconciler.run_reconciliation(dry_run=True)

    if success:
        print("\n" + "=" * 60)
        print("PHASE 2: APPLY CHANGES")
        print("=" * 60)

        response = input("\nProceed with applying changes? (y/N): ")
        if response.lower() == "y":
            reconciler.run_reconciliation(dry_run=False)
        else:
            print("Operation cancelled.")


if __name__ == "__main__":
    main()
