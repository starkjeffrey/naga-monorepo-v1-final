#!/usr/bin/env python
"""
Database Integrity Monitor for CI/CD Pipeline
==============================================
Automated monitoring to detect database/model divergence early.
Designed for GitHub Actions / GitLab CI integration.

Exit codes:
  0 - All checks passed
  1 - Issues detected
  2 - Critical issues requiring immediate attention
"""

import json
import os
import subprocess
import sys
from datetime import datetime

# Django setup
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")

import django

django.setup()

from django.apps import apps
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


class IntegrityMonitor:
    """Automated integrity monitoring for CI/CD."""

    def __init__(self, output_format="json", slack_webhook=None):
        self.output_format = output_format
        self.slack_webhook = slack_webhook
        self.issues = []
        self.warnings = []
        self.exit_code = 0

    def run(self):
        """Run all integrity checks."""
        results = {
            "timestamp": datetime.now().isoformat(),
            "environment": os.getenv("ENVIRONMENT", "development"),
            "checks": {},
            "issues": [],
            "warnings": [],
            "exit_code": 0,
        }

        # Check 1: Unapplied migrations
        print("🔍 Checking migrations...")
        migration_issues = self.check_migrations()
        results["checks"]["migrations"] = {
            "status": "FAIL" if migration_issues else "PASS",
            "issues": migration_issues,
        }

        # Check 2: Model changes without migrations
        print("🔍 Checking for unmigrated changes...")
        model_changes = self.check_model_changes()
        results["checks"]["model_changes"] = {"status": "FAIL" if model_changes else "PASS", "issues": model_changes}

        # Check 3: Schema mismatches
        print("🔍 Checking schema integrity...")
        schema_issues = self.check_schema_integrity()
        results["checks"]["schema_integrity"] = {
            "status": "FAIL" if schema_issues["critical"] else "WARN" if schema_issues["warnings"] else "PASS",
            "critical": schema_issues["critical"],
            "warnings": schema_issues["warnings"],
        }

        # Check 4: NULL constraint mismatches
        print("🔍 Checking NULL constraints...")
        constraint_issues = self.check_null_constraints()
        results["checks"]["null_constraints"] = {
            "status": "FAIL" if constraint_issues else "PASS",
            "issues": constraint_issues,
        }

        # Check 5: Foreign key integrity
        print("🔍 Checking foreign key integrity...")
        fk_issues = self.check_foreign_keys()
        results["checks"]["foreign_keys"] = {"status": "FAIL" if fk_issues else "PASS", "issues": fk_issues}

        # Compile results
        results["issues"] = self.issues
        results["warnings"] = self.warnings
        results["exit_code"] = self.exit_code

        # Output results
        self.output_results(results)

        # Send alerts if configured
        if self.slack_webhook and self.exit_code > 0:
            self.send_slack_alert(results)

        return self.exit_code

    def check_migrations(self) -> list[str]:
        """Check for unapplied migrations."""
        issues = []
        try:
            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())

            if plan:
                for migration, _backwards in plan:
                    issue = f"Unapplied migration: {migration.app_label}.{migration.name}"
                    issues.append(issue)
                    self.issues.append(issue)
                    self.exit_code = max(self.exit_code, 2)  # Critical
        except Exception as e:
            issues.append(f"Error checking migrations: {e!s}")
            self.exit_code = max(self.exit_code, 1)

        return issues

    def check_model_changes(self) -> list[str]:
        """Check for model changes without migrations."""
        issues = []
        try:
            # Run makemigrations --dry-run
            result = subprocess.run(
                ["python", "manage.py", "makemigrations", "--dry-run", "--check"],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                issues.append("Model changes detected without migrations")
                self.issues.append("Model changes require new migrations")
                self.exit_code = max(self.exit_code, 2)  # Critical
        except subprocess.TimeoutExpired:
            issues.append("Timeout checking for model changes")
            self.warnings.append("Model change check timed out")
        except Exception as e:
            issues.append(f"Error checking model changes: {e!s}")

        return issues

    def check_schema_integrity(self) -> dict:
        """Check for schema mismatches between models and database."""
        critical = []
        warnings = []

        for model in apps.get_models():
            if model._meta.abstract or model._meta.proxy:
                continue

            table_name = model._meta.db_table

            try:
                # Get database columns
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT column_name, is_nullable, data_type
                        FROM information_schema.columns
                        WHERE table_name = %s
                    """,
                        [table_name],
                    )
                    db_columns = {row[0]: {"nullable": row[1] == "YES", "type": row[2]} for row in cursor.fetchall()}

                # Check model fields
                for field in model._meta.get_fields():
                    if not hasattr(field, "column"):
                        continue

                    column_name = field.column

                    if column_name not in db_columns:
                        issue = f"Missing column: {table_name}.{column_name}"
                        critical.append(issue)
                        self.issues.append(issue)
                        self.exit_code = max(self.exit_code, 2)

                # Check for extra columns (less critical)
                model_columns = {field.column for field in model._meta.get_fields() if hasattr(field, "column")}

                for db_col in db_columns:
                    if db_col not in model_columns and db_col != "id":
                        # Skip ManyToMany columns
                        if not db_col.endswith("_id"):
                            warning = f"Extra column: {table_name}.{db_col}"
                            warnings.append(warning)
                            self.warnings.append(warning)
                            self.exit_code = max(self.exit_code, 1)

            except Exception as e:
                warning = f"Error checking table {table_name}: {e!s}"
                warnings.append(warning)
                self.warnings.append(warning)

        return {"critical": critical, "warnings": warnings}

    def check_null_constraints(self) -> list[str]:
        """Check for NULL constraint mismatches."""
        issues = []

        for model in apps.get_models():
            if model._meta.abstract or model._meta.proxy:
                continue

            table_name = model._meta.db_table

            for field in model._meta.get_fields():
                if not hasattr(field, "column"):
                    continue

                column_name = field.column
                model_nullable = field.null

                try:
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
                                issue = (
                                    f"NULL mismatch: {table_name}.{column_name} "
                                    f"(model={model_nullable}, db={db_nullable})"
                                )
                                issues.append(issue)
                                self.issues.append(issue)
                                self.exit_code = max(self.exit_code, 2)
                except Exception:
                    pass  # Skip if error

        return issues

    def check_foreign_keys(self) -> list[str]:
        """Check foreign key integrity."""
        issues = []

        try:
            with connection.cursor() as cursor:
                # Check for orphaned foreign key records
                cursor.execute(
                    """
                    SELECT
                        tc.table_name,
                        kcu.column_name,
                        ccu.table_name AS foreign_table_name
                    FROM
                        information_schema.table_constraints AS tc
                        JOIN information_schema.key_column_usage AS kcu
                          ON tc.constraint_name = kcu.constraint_name
                        JOIN information_schema.constraint_column_usage AS ccu
                          ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                """
                )

                for row in cursor.fetchall():
                    table_name, column_name, foreign_table = row

                    # Check for orphaned records
                    cursor.execute(
                        f"""
                        SELECT COUNT(*)
                        FROM {table_name} t1
                        LEFT JOIN {foreign_table} t2 ON t1.{column_name} = t2.id
                        WHERE t1.{column_name} IS NOT NULL AND t2.id IS NULL
                    """
                    )

                    orphaned_count = cursor.fetchone()[0]
                    if orphaned_count > 0:
                        issue = f"Orphaned FK records: {table_name}.{column_name} ({orphaned_count} records)"
                        issues.append(issue)
                        self.warnings.append(issue)
                        self.exit_code = max(self.exit_code, 1)

        except Exception as e:
            self.warnings.append(f"Error checking foreign keys: {e!s}")

        return issues

    def output_results(self, results: dict):
        """Output results in specified format."""
        if self.output_format == "json":
            print(json.dumps(results, indent=2))
        elif self.output_format == "github":
            # GitHub Actions format
            if results["exit_code"] == 2:
                print("::error::Critical database integrity issues detected!")
            elif results["exit_code"] == 1:
                print("::warning::Database integrity warnings detected")

            for issue in results["issues"]:
                print(f"::error::{issue}")
            for warning in results["warnings"]:
                print(f"::warning::{warning}")
        elif self.output_format == "gitlab":
            # GitLab CI format
            if results["exit_code"] > 0:
                print(f"[FAILED] Database integrity check failed with {len(results['issues'])} issues")
            else:
                print("[PASSED] Database integrity check passed")

    def send_slack_alert(self, results: dict):
        """Send alert to Slack webhook."""
        if not self.slack_webhook:
            return

        try:
            import requests

            # Build Slack message
            color = "danger" if results["exit_code"] == 2 else "warning"

            message = {
                "attachments": [
                    {
                        "color": color,
                        "title": "Database Integrity Check Failed",
                        "text": f"Environment: {results['environment']}",
                        "fields": [
                            {"title": "Issues", "value": f"{len(results['issues'])} critical issues", "short": True},
                            {"title": "Warnings", "value": f"{len(results['warnings'])} warnings", "short": True},
                        ],
                        "footer": "Naga SIS Integrity Monitor",
                        "ts": int(datetime.now().timestamp()),
                    }
                ]
            }

            # Add issue details
            if results["issues"]:
                message["attachments"][0]["fields"].append(
                    {
                        "title": "Critical Issues",
                        "value": "\n".join(results["issues"][:5]),  # First 5 issues
                    }
                )

            requests.post(self.slack_webhook, json=message, timeout=5)
        except Exception as e:
            print(f"Failed to send Slack alert: {e!s}")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Database Integrity Monitor")
    parser.add_argument("--format", choices=["json", "github", "gitlab", "text"], default="json", help="Output format")
    parser.add_argument("--slack-webhook", help="Slack webhook URL for alerts")
    parser.add_argument("--fail-on-warning", action="store_true", help="Exit with non-zero code on warnings")

    args = parser.parse_args()

    # Run monitor
    monitor = IntegrityMonitor(output_format=args.format, slack_webhook=args.slack_webhook)

    exit_code = monitor.run()

    # Adjust exit code if fail-on-warning
    if args.fail_on_warning and monitor.warnings:
        exit_code = max(exit_code, 1)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
