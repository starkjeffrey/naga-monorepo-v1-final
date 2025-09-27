"""
Deep Database Integrity Analysis Command
Comprehensive analysis of database vs Django models integrity
"""

import json
from datetime import datetime

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Run deep database integrity analysis"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.issues = {"critical": [], "high": [], "medium": [], "low": []}
        self.decisions = {}
        self.stats = {
            "tables_analyzed": 0,
            "columns_checked": 0,
            "constraints_verified": 0,
            "records_sampled": 0,
            "analysis_start": datetime.now(),
        }

    def add_arguments(self, parser):
        parser.add_argument("--quick", action="store_true", help="Run quick analysis (skip data sampling)")

    def handle(self, *args, **options):
        self.stdout.write("🔍 Starting Deep Database Integrity Analysis...")

        try:
            self.validate_environment()
            self.analyze_schema_structure()
            self.analyze_constraints()

            if not options["quick"]:
                self.analyze_data_integrity()

            self.analyze_performance()
            self.generate_fix_plan()
            self.save_results()

            total_issues = sum(len(issues) for issues in self.issues.values())
            critical_count = len(self.issues["critical"])

            self.stdout.write(
                self.style.SUCCESS(f"✅ Analysis complete! Found {total_issues} issues ({critical_count} critical)")
            )

            if critical_count > 0:
                self.stdout.write(self.style.ERROR("⚠️ CRITICAL issues found - see integrity_reports/analysis_*.json"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Analysis failed: {e}"))
            raise

    def validate_environment(self):
        """Validate Django and database connectivity"""
        self.stdout.write("🔧 Validating environment...")

        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT version();")
            db_version = cursor.fetchone()[0]
            self.stdout.write(f"✅ Database: {db_version[:50]}...")

        # Test model loading
        model_count = len(apps.get_models())
        self.stdout.write(f"✅ Loaded {model_count} Django models")

        # Create reports directory
        import os

        os.makedirs("integrity_reports", exist_ok=True)

    def analyze_schema_structure(self):
        """Phase 1: Analyze schema structure"""
        self.stdout.write("📋 Phase 1: Schema Structure Analysis")

        # Get database columns
        db_columns = self.get_database_columns()
        model_fields = self.get_model_fields()

        self.check_missing_columns(model_fields, db_columns)
        self.check_extra_columns(model_fields, db_columns)
        self.check_null_constraint_mismatches(model_fields, db_columns)

        self.stats["tables_analyzed"] = len({field["table"] for field in model_fields})
        self.stats["columns_checked"] = len(model_fields)

    def get_database_columns(self):
        """Get all database columns"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    table_name, column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name NOT LIKE 'pg_%'
                ORDER BY table_name, ordinal_position
            """)
            return cursor.fetchall()

    def get_model_fields(self):
        """Get all Django model fields"""
        fields = []
        for model in apps.get_models():
            if model._meta.managed:
                table_name = model._meta.db_table
                for field in model._meta.fields:
                    fields.append(
                        {
                            "table": table_name,
                            "column": field.column,
                            "field_type": type(field).__name__,
                            "null": field.null,
                            "model_name": model.__name__,
                            "app_label": model._meta.app_label,
                        }
                    )
        return fields

    def check_missing_columns(self, model_fields, db_columns):
        """Find model fields missing from database"""
        db_column_set = {(col[0], col[1]) for col in db_columns}

        for field in model_fields:
            if (field["table"], field["column"]) not in db_column_set:
                severity = "critical" if not field["null"] else "high"
                self.issues[severity].append(
                    {
                        "type": "missing_column",
                        "table": field["table"],
                        "column": field["column"],
                        "field_type": field["field_type"],
                        "nullable": field["null"],
                        "model": f"{field['app_label']}.{field['model_name']}",
                        "description": f"Model field {field['column']} missing from database table {field['table']}",
                    }
                )

    def check_extra_columns(self, model_fields, db_columns):
        """Find database columns not in models"""
        model_column_set = {(field["table"], field["column"]) for field in model_fields}

        for col in db_columns:
            table, column = col[0], col[1]
            if (table, column) not in model_column_set:
                has_data = self.check_column_has_data(table, column)

                severity = "high" if has_data else "medium"
                self.issues[severity].append(
                    {
                        "type": "extra_column",
                        "table": table,
                        "column": column,
                        "data_type": col[2],
                        "has_data": has_data,
                        "description": f"Database column {column} in table {table} not defined in any model",
                    }
                )

    def check_null_constraint_mismatches(self, model_fields, db_columns):
        """Check NULL constraint mismatches"""
        db_column_map = {(col[0], col[1]): col for col in db_columns}

        for field in model_fields:
            key = (field["table"], field["column"])
            if key in db_column_map:
                db_col = db_column_map[key]
                db_nullable = db_col[3] == "YES"
                model_nullable = field["null"]

                if db_nullable != model_nullable:
                    has_null_data = self.check_column_has_null_data(field["table"], field["column"])

                    severity = "critical" if (not model_nullable and has_null_data) else "high"

                    self.issues[severity].append(
                        {
                            "type": "null_constraint_mismatch",
                            "table": field["table"],
                            "column": field["column"],
                            "db_nullable": db_nullable,
                            "model_nullable": model_nullable,
                            "has_null_data": has_null_data,
                            "description": (
                                f"NULL constraint mismatch: DB nullable={db_nullable}, Model nullable={model_nullable}"
                            ),
                        }
                    )

    def check_column_has_data(self, table, column):
        """Check if column has data"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" IS NOT NULL LIMIT 1')
                return cursor.fetchone()[0] > 0
        except Exception:
            return False

    def check_column_has_null_data(self, table, column):
        """Check if column has null data"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" IS NULL LIMIT 1')
                return cursor.fetchone()[0] > 0
        except Exception:
            return False

    def analyze_constraints(self):
        """Phase 2: Analyze constraints"""
        self.stdout.write("🔗 Phase 2: Constraint Analysis")

        self.check_foreign_key_violations()
        self.check_primary_key_issues()

    def check_foreign_key_violations(self):
        """Check foreign key violations"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    tc.table_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table,
                    ccu.column_name AS foreign_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                  ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
                AND tc.table_name NOT LIKE 'pg_%'
            """)

            constraints = cursor.fetchall()
            self.stats["constraints_verified"] += len(constraints)

            for table, column, ref_table, ref_column in constraints:
                try:
                    cursor.execute(f"""
                        SELECT COUNT(*) FROM "{table}" t
                        LEFT JOIN "{ref_table}" r ON t."{column}" = r."{ref_column}"
                        WHERE t."{column}" IS NOT NULL AND r."{ref_column}" IS NULL
                    """)

                    orphaned_count = cursor.fetchone()[0]
                    if orphaned_count > 0:
                        self.issues["critical"].append(
                            {
                                "type": "foreign_key_violation",
                                "table": table,
                                "column": column,
                                "reference_table": ref_table,
                                "reference_column": ref_column,
                                "orphaned_records": orphaned_count,
                                "description": f"Found {orphaned_count} orphaned records",
                            }
                        )
                except Exception as e:
                    self.stdout.write(f"Warning: Could not check FK {table}.{column}: {e}")

    def check_primary_key_issues(self):
        """Check primary key issues"""
        for model in apps.get_models():
            if model._meta.managed:
                table = model._meta.db_table
                pk_field = model._meta.pk.column if model._meta.pk else None

                if pk_field:
                    with connection.cursor() as cursor:
                        try:
                            cursor.execute(f"""
                                SELECT "{pk_field}", COUNT(*)
                                FROM "{table}"
                                GROUP BY "{pk_field}"
                                HAVING COUNT(*) > 1
                                LIMIT 5
                            """)

                            duplicates = cursor.fetchall()
                            if duplicates:
                                self.issues["critical"].append(
                                    {
                                        "type": "duplicate_primary_keys",
                                        "table": table,
                                        "primary_key_column": pk_field,
                                        "duplicate_count": len(duplicates),
                                        "description": f"Found duplicate primary keys in {table}",
                                    }
                                )
                        except Exception as e:
                            self.stdout.write(f"Warning: Could not check PK for {table}: {e}")

    def analyze_data_integrity(self):
        """Phase 3: Data integrity analysis"""
        self.stdout.write("🔍 Phase 3: Data Integrity Analysis")

        # Sample data validation
        for model in apps.get_models():
            if model._meta.managed:
                try:
                    count = model.objects.count()
                    if count > 0:
                        # Try to load a sample
                        sample = model.objects.first()
                        if sample:
                            self.stats["records_sampled"] += 1
                except Exception as e:
                    self.issues["high"].append(
                        {
                            "type": "model_loading_error",
                            "model": model.__name__,
                            "table": model._meta.db_table,
                            "error": str(e),
                            "description": f"Error loading records from {model.__name__}",
                        }
                    )

    def analyze_performance(self):
        """Phase 4: Performance analysis"""
        self.stdout.write("⚡ Phase 4: Performance Analysis")

        with connection.cursor() as cursor:
            # Check table sizes
            cursor.execute("""
                SELECT
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)),
                    pg_total_relation_size(schemaname||'.'||tablename)
                FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename NOT LIKE 'pg_%'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 10
            """)

            large_tables = cursor.fetchall()
            self.stats["largest_tables"] = large_tables

    def generate_fix_plan(self):
        """Generate fix plan"""
        self.stdout.write("📋 Generating fix plan...")

        for issue in self.issues["critical"]:
            key = f"{issue.get('table', 'unknown')}.{issue.get('column', 'unknown')}"

            if issue["type"] == "missing_column":
                self.decisions[key] = {
                    "action": "create_migration",
                    "priority": "immediate",
                    "change": f"Add column {issue['column']} to {issue['table']}",
                    "risk": "low",
                }
            elif issue["type"] == "null_constraint_mismatch":
                if issue["has_null_data"] and not issue.get("model_nullable", True):
                    self.decisions[key] = {
                        "action": "update_model",
                        "priority": "high",
                        "change": f"Make {issue['column']} nullable in model",
                        "risk": "low",
                    }

    def save_results(self):
        """Save analysis results"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        runtime = datetime.now() - self.stats["analysis_start"]
        self.stats["runtime_seconds"] = runtime.total_seconds()

        results = {
            "metadata": {"timestamp": timestamp, "runtime_seconds": self.stats["runtime_seconds"]},
            "statistics": self.stats,
            "issues": self.issues,
            "decisions": self.decisions,
        }

        # Save JSON
        json_path = f"integrity_reports/analysis_{timestamp}.json"
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2, default=str)

        # Generate summary
        total_issues = sum(len(issues) for issues in self.issues.values())

        summary = f"""# Database Integrity Analysis Summary
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Results
- **Total Issues**: {total_issues}
- **Critical**: {len(self.issues["critical"])}
- **High**: {len(self.issues["high"])}
- **Medium**: {len(self.issues["medium"])}
- **Low**: {len(self.issues["low"])}

## Statistics
- Runtime: {self.stats["runtime_seconds"]:.1f} seconds
- Tables Analyzed: {self.stats["tables_analyzed"]}
- Columns Checked: {self.stats["columns_checked"]}
- Constraints Verified: {self.stats["constraints_verified"]}

"""

        if self.issues["critical"]:
            summary += "## Critical Issues\n"
            for issue in self.issues["critical"]:
                summary += f"- {issue['type']}: {issue.get('description', 'No description')}\n"

        with open(f"integrity_reports/summary_{timestamp}.md", "w") as f:
            f.write(summary)

        self.stdout.write(f"Results saved: integrity_reports/analysis_{timestamp}.*")
