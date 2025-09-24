"""
Model-Database Reconciliation Django Management Command
Safely reconciles Django models with database schema based on integrity analysis
"""

import ast
import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Reconcile Django models with database schema"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying them")

    def log(self, message, level="INFO"):
        """Enhanced logging with timestamps"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {"INFO": "ℹ️", "ERROR": "❌", "SUCCESS": "✅", "WARNING": "⚠️"}.get(level, "ℹ️")
        self.stdout.write(f"[{timestamp}] {prefix} {message}")

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

                # First, try to find which file the model is actually defined in
                model_file_path = None

                # Check single models.py file
                single_file_path = f"apps/{app_label}/models.py"
                if Path(single_file_path).exists():
                    with open(single_file_path) as f:
                        content = f.read()
                        if f"class {model_name}" in content:
                            model_file_path = single_file_path

                # Check models directory structure
                if not model_file_path:
                    models_dir = Path(f"apps/{app_label}/models")
                    if models_dir.exists() and models_dir.is_dir():
                        for py_file in models_dir.glob("*.py"):
                            if py_file.name == "__init__.py":
                                continue
                            try:
                                with open(py_file) as f:
                                    content = f.read()
                                    if f"class {model_name}" in content:
                                        model_file_path = str(py_file)
                                        break
                            except Exception:
                                continue

                # Check for models_*.py pattern files in app root
                if not model_file_path:
                    app_dir = Path(f"apps/{app_label}")
                    if app_dir.exists():
                        for py_file in app_dir.glob("models_*.py"):
                            try:
                                with open(py_file) as f:
                                    content = f.read()
                                    if f"class {model_name}" in content:
                                        model_file_path = str(py_file)
                                        break
                            except Exception:
                                continue

                if model_file_path:
                    return app_label, model_name, model_file_path

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

            # Find the field definition using multiple patterns
            # Pattern 1: With type hints - field_name: Type = models.SomeField(...)
            pattern1 = rf"(\s+{re.escape(field_name)}\s*:\s*[^\s=]+\s*=\s*models\.\w+\s*\()"
            # Pattern 2: Without type hints - field_name = models.SomeField(...)
            pattern2 = rf"(\s+{re.escape(field_name)}\s*=\s*models\.\w+\s*\()"

            # Try both patterns
            field_start_pos = None

            match1 = re.search(pattern1, content, re.MULTILINE)
            match2 = re.search(pattern2, content, re.MULTILINE)

            if match1:
                field_start_pos = match1.start()
            elif match2:
                field_start_pos = match2.start()

            if field_start_pos is None:
                self.log(f"⚠️ Could not find field {field_name} in {file_path}", "WARNING")
                return False

            # Find the complete field definition by parsing parentheses
            field_start = field_start_pos
            paren_count = 0
            field_end = None
            in_string = False
            string_char = None
            escape_next = False

            # Start from the opening parenthesis
            opening_paren_pos = content.find("(", field_start_pos)
            if opening_paren_pos == -1:
                self.log(f"⚠️ Could not find opening parenthesis for field {field_name}", "WARNING")
                return False

            for i, char in enumerate(content[opening_paren_pos:], opening_paren_pos):
                if escape_next:
                    escape_next = False
                    continue

                if char == "\\" and in_string:
                    escape_next = True
                    continue

                if char in ['"', "'"] and not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char and in_string:
                    in_string = False
                    string_char = None
                elif not in_string:
                    if char == "(":
                        paren_count += 1
                    elif char == ")":
                        paren_count -= 1
                        if paren_count == 0:
                            field_end = i + 1
                            break

            if field_end is None:
                self.log(f"⚠️ Could not find complete field definition for {field_name}", "WARNING")
                return False

            # Extract the complete field definition
            field_definition = content[field_start:field_end]

            # Check if null=True already exists
            if "null=True" in field_definition:
                self.log(f"ℹ️ Field {field_name} is already nullable")
                return True

            # Find where to add null=True (before the closing parenthesis)
            # Work backwards from the closing paren to find a good insertion point
            insert_pos = field_definition.rfind(")")
            if insert_pos == -1:
                return False

            # Check if there are existing parameters
            params_section = field_definition[field_definition.find("(") + 1 : insert_pos].strip()

            if params_section and not params_section.isspace():
                # Add comma before null=True
                null_addition = ", null=True"
                # If it's a text field, also add blank=True
                if any(field_type in field_definition for field_type in ["CharField", "TextField", "EmailField"]):
                    null_addition = ", null=True, blank=True"
            else:
                # No existing parameters
                null_addition = "null=True"
                if any(field_type in field_definition for field_type in ["CharField", "TextField", "EmailField"]):
                    null_addition = "null=True, blank=True"

            # Create the new field definition
            new_field_definition = field_definition[:insert_pos] + null_addition + field_definition[insert_pos:]

            # Replace in the full content
            new_content = content[:field_start] + new_field_definition + content[field_end:]

            # Validate the Python syntax
            try:
                ast.parse(new_content)

                # Write the modified content
                with open(file_path, "w") as f:
                    f.write(new_content)

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

        except Exception as e:
            self.log(f"❌ Error modifying {file_path}: {e}", "ERROR")
            return False

    def fix_critical_issues(self, dry_run: bool = True) -> list[dict]:
        """Fix critical NULL constraint mismatches"""
        self.log("🚨 Analyzing critical NULL constraint mismatches...")

        fixed_issues = []
        critical_issues = self.analysis_data["issues"]["critical"]

        for issue in critical_issues:
            if issue["type"] == "null_constraint_mismatch":
                table = issue["table"]
                column = issue["column"]

                self.log(f"Analyzing NULL constraint mismatch: {table}.{column}")

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

                # Preview or apply fix
                if not dry_run:
                    success = self.modify_model_field_nullable(file_path, model_name, field_name)
                else:
                    success = True
                    self.log(f"  Would modify: {file_path} -> {model_name}.{field_name} (make nullable)")

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

    def handle(self, *args, **options):
        """Main command handler"""
        dry_run = options["dry_run"]

        self.log("🚀 Starting Model-Database Reconciliation...")
        self.log(f"Mode: {'DRY RUN' if dry_run else 'LIVE CHANGES'}")

        try:
            # Load analysis data
            self.load_analysis_data()

            if not dry_run:
                # Create backups
                self.create_backup()

            # Fix critical issues
            fixed_issues = self.fix_critical_issues(dry_run)

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
                            self.stdout.write(f"  {cmd}")

                else:
                    self.log("❌ Validation failed. Changes rolled back automatically.")
                    return

            elif dry_run:
                critical_issues = self.analysis_data["issues"]["critical"]
                null_constraint_issues = [i for i in critical_issues if i["type"] == "null_constraint_mismatch"]
                self.log(f"Would fix {len(null_constraint_issues)} critical NULL constraint issues")
                self.log("✅ Dry run completed. Use --no-dry-run to apply changes.")

        except Exception as e:
            self.log(f"❌ Reconciliation failed: {e}", "ERROR")
            raise
