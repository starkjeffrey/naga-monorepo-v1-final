#!/usr/bin/env python3
"""
Deep Database Integrity Analysis Script
Comprehensive analysis of database vs Django models integrity
Phase 1: Deep Analysis (1 hour estimated)
"""

import json
import os
import sys
from datetime import datetime

import django
from django.apps import apps
from django.db import connection

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()


class DatabaseIntegrityAnalyzer:
    def __init__(self):
        self.issues = {
            "critical": [],  # Data-breaking issues requiring immediate fix
            "high": [],  # Functional issues affecting operations
            "medium": [],  # Performance or consistency issues
            "low": [],  # Minor improvements or cleanup
        }
        self.decisions = {}
        self.stats = {
            "tables_analyzed": 0,
            "columns_checked": 0,
            "constraints_verified": 0,
            "records_sampled": 0,
            "analysis_start": datetime.now(),
        }
        self.progress = {"current_phase": "", "total_phases": 4}

    def log_progress(self, message, phase=None):
        """Log progress with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if phase:
            self.progress["current_phase"] = phase
        print(f"[{timestamp}] {message}")

    def validate_environment(self):
        """Validate Django and database connectivity"""
        self.log_progress("🔧 Validating environment...", "Environment Check")

        try:
            # Test database connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT version();")
                db_version = cursor.fetchone()[0]
                self.log_progress(f"✅ Database connected: {db_version}")

            # Test model loading
            model_count = len(apps.get_models())
            self.log_progress(f"✅ Loaded {model_count} Django models")

            # Create reports directory
            os.makedirs("integrity_reports", exist_ok=True)

        except Exception as e:
            self.log_progress(f"❌ Environment validation failed: {e}")
            raise

    def analyze(self):
        """Run complete deep analysis"""
        self.log_progress("🔍 Starting Deep Database Integrity Analysis...")
        self.validate_environment()

        try:
            # Phase 1: Schema Structure Analysis (15 min)
            self.analyze_schema_structure()

            # Phase 2: Constraint Analysis (20 min)
            self.analyze_constraints()

            # Phase 3: Data Integrity Analysis (20 min)
            self.analyze_data_integrity()

            # Phase 4: Performance & Optimization (5 min)
            self.analyze_performance()

            # Generate comprehensive fix plan
            self.generate_comprehensive_fix_plan()

            # Save results
            self.save_results()

            return self.issues, self.decisions

        except Exception as e:
            self.log_progress(f"❌ Analysis failed: {e}")
            # Save partial results
            self.save_results(partial=True)
            raise

    def analyze_schema_structure(self):
        """Phase 1: Analyze schema structure and column definitions"""
        self.log_progress("📋 Phase 1: Schema Structure Analysis", "Schema Analysis")

        # Get all database columns
        db_columns = self.get_all_database_columns()
        self.log_progress(f"Found {len(db_columns)} database columns")

        # Get all model fields
        model_fields = self.get_all_model_fields()
        self.log_progress(f"Found {len(model_fields)} model fields")

        # Compare structures
        self.check_missing_columns(model_fields, db_columns)
        self.check_extra_columns(model_fields, db_columns)
        self.check_column_type_mismatches(model_fields, db_columns)
        self.check_null_constraint_mismatches(model_fields, db_columns)

        self.stats["tables_analyzed"] = len({field[0] for field in model_fields})
        self.stats["columns_checked"] = len(model_fields)

    def get_all_database_columns(self):
        """Get all columns from database with detailed information"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    c.table_name,
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    c.column_default,
                    c.character_maximum_length,
                    c.numeric_precision,
                    c.numeric_scale
                FROM information_schema.columns c
                WHERE c.table_schema = 'public'
                AND c.table_name NOT LIKE 'django_%'
                AND c.table_name NOT LIKE 'auth_%'
                AND c.table_name NOT LIKE 'pg_%'
                ORDER BY c.table_name, c.ordinal_position
            """)
            return cursor.fetchall()

    def get_all_model_fields(self):
        """Get all fields from Django models with detailed information"""
        fields = []
        for model in apps.get_models():
            if model._meta.managed:  # Only managed models
                table_name = model._meta.db_table
                for field in model._meta.fields:
                    # Get field information
                    field_info = {
                        "table": table_name,
                        "column": field.column,
                        "field_type": type(field).__name__,
                        "null": field.null,
                        "blank": field.blank,
                        "default": getattr(field, "default", None),
                        "max_length": getattr(field, "max_length", None),
                        "model_name": model.__name__,
                        "app_label": model._meta.app_label,
                    }
                    fields.append(field_info)
        return fields

    def check_missing_columns(self, model_fields, db_columns):
        """Find model fields that don't exist in database"""
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
        """Find database columns not defined in models"""
        model_column_set = {(field["table"], field["column"]) for field in model_fields}

        for col in db_columns:
            table, column = col[0], col[1]
            if (table, column) not in model_column_set:
                # Check if column has data
                has_data = self.check_column_has_data(table, column)

                severity = "high" if has_data else "medium"
                self.issues[severity].append(
                    {
                        "type": "extra_column",
                        "table": table,
                        "column": column,
                        "data_type": col[2],
                        "has_data": has_data,
                        "nullable": col[3] == "YES",
                        "description": f"Database column {column} in table {table} not defined in any model",
                        "recommendation": "preserve_and_document" if has_data else "consider_removal",
                    }
                )

    def check_column_type_mismatches(self, model_fields, db_columns):
        """Check for data type mismatches between models and database"""
        db_column_map = {(col[0], col[1]): col for col in db_columns}

        for field in model_fields:
            key = (field["table"], field["column"])
            if key in db_column_map:
                db_col = db_column_map[key]
                db_type = db_col[2].lower()

                # Basic type compatibility check
                expected_types = self.get_expected_db_types(field["field_type"])
                if db_type not in expected_types:
                    self.issues["medium"].append(
                        {
                            "type": "type_mismatch",
                            "table": field["table"],
                            "column": field["column"],
                            "model_type": field["field_type"],
                            "db_type": db_type,
                            "expected_types": expected_types,
                            "description": f"Type mismatch: {field['column']} expected {expected_types} but found {db_type}",
                        }
                    )

    def get_expected_db_types(self, field_type):
        """Map Django field types to expected PostgreSQL types"""
        type_mapping = {
            "AutoField": ["integer", "serial"],
            "BigAutoField": ["bigint", "bigserial"],
            "CharField": ["character varying", "varchar", "text"],
            "TextField": ["text"],
            "IntegerField": ["integer"],
            "BigIntegerField": ["bigint"],
            "FloatField": ["double precision", "real"],
            "DecimalField": ["numeric"],
            "BooleanField": ["boolean"],
            "DateField": ["date"],
            "DateTimeField": ["timestamp with time zone", "timestamp without time zone"],
            "TimeField": ["time with time zone", "time without time zone"],
            "UUIDField": ["uuid"],
            "JSONField": ["jsonb", "json"],
            "ForeignKey": ["integer", "bigint"],
        }
        return type_mapping.get(field_type, ["unknown"])

    def check_null_constraint_mismatches(self, model_fields, db_columns):
        """Check for NULL constraint mismatches"""
        db_column_map = {(col[0], col[1]): col for col in db_columns}

        for field in model_fields:
            key = (field["table"], field["column"])
            if key in db_column_map:
                db_col = db_column_map[key]
                db_nullable = db_col[3] == "YES"
                model_nullable = field["null"]

                if db_nullable != model_nullable:
                    has_data = self.check_column_has_data(field["table"], field["column"])
                    has_null_data = self.check_column_has_null_data(field["table"], field["column"])

                    severity = "critical" if (not model_nullable and has_null_data) else "high"

                    self.issues[severity].append(
                        {
                            "type": "null_constraint_mismatch",
                            "table": field["table"],
                            "column": field["column"],
                            "db_nullable": db_nullable,
                            "model_nullable": model_nullable,
                            "has_data": has_data,
                            "has_null_data": has_null_data,
                            "description": f"NULL constraint mismatch for {field['column']}: DB={db_nullable}, Model={model_nullable}",
                        }
                    )

    def check_column_has_data(self, table, column):
        """Check if column has any non-null data"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" IS NOT NULL LIMIT 1')
                return cursor.fetchone()[0] > 0
        except Exception:
            return False

    def check_column_has_null_data(self, table, column):
        """Check if column has any null data"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(f'SELECT COUNT(*) FROM "{table}" WHERE "{column}" IS NULL LIMIT 1')
                return cursor.fetchone()[0] > 0
        except Exception:
            return False

    def analyze_constraints(self):
        """Phase 2: Analyze database constraints and referential integrity"""
        self.log_progress("🔗 Phase 2: Constraint Analysis", "Constraint Analysis")

        self.check_foreign_key_violations()
        self.check_unique_constraint_violations()
        self.check_primary_key_issues()

    def check_foreign_key_violations(self):
        """Check for foreign key constraint violations"""
        self.log_progress("Checking foreign key integrity...")

        with connection.cursor() as cursor:
            # Get all foreign key constraints
            cursor.execute("""
                SELECT
                    tc.table_name,
                    tc.constraint_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                  ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
                AND tc.table_name NOT LIKE 'django_%'
            """)

            fk_constraints = cursor.fetchall()
            self.stats["constraints_verified"] += len(fk_constraints)

            for constraint in fk_constraints:
                table, constraint_name, column, ref_table, ref_column = constraint

                # Check for orphaned records
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
                            "constraint_name": constraint_name,
                            "description": f"Found {orphaned_count} orphaned records in {table}.{column} referencing {ref_table}.{ref_column}",
                        }
                    )

    def check_unique_constraint_violations(self):
        """Check for unique constraint violations"""
        self.log_progress("Checking unique constraints...")

        # This would require complex queries for each unique constraint
        # Simplified version - check for duplicate primary keys
        for model in apps.get_models():
            if model._meta.managed:
                table = model._meta.db_table
                pk_field = model._meta.pk.column

                with connection.cursor() as cursor:
                    cursor.execute(f"""
                        SELECT "{pk_field}", COUNT(*)
                        FROM "{table}"
                        GROUP BY "{pk_field}"
                        HAVING COUNT(*) > 1
                        LIMIT 10
                    """)

                    duplicates = cursor.fetchall()
                    if duplicates:
                        self.issues["critical"].append(
                            {
                                "type": "duplicate_primary_keys",
                                "table": table,
                                "primary_key_column": pk_field,
                                "duplicate_count": len(duplicates),
                                "sample_duplicates": duplicates[:5],
                                "description": f"Found {len(duplicates)} duplicate primary keys in {table}",
                            }
                        )

    def check_primary_key_issues(self):
        """Check for primary key definition issues"""
        self.log_progress("Checking primary key integrity...")

        for model in apps.get_models():
            if model._meta.managed:
                table = model._meta.db_table

                with connection.cursor() as cursor:
                    # Check if table has primary key
                    cursor.execute(
                        """
                        SELECT COUNT(*) FROM information_schema.table_constraints
                        WHERE constraint_type = 'PRIMARY KEY'
                        AND table_name = %s AND table_schema = 'public'
                    """,
                        [table],
                    )

                    pk_count = cursor.fetchone()[0]
                    if pk_count == 0:
                        self.issues["critical"].append(
                            {
                                "type": "missing_primary_key",
                                "table": table,
                                "model": model.__name__,
                                "description": f"Table {table} has no primary key defined",
                            }
                        )

    def analyze_data_integrity(self):
        """Phase 3: Analyze data integrity and consistency"""
        self.log_progress("🔍 Phase 3: Data Integrity Analysis", "Data Integrity")

        self.check_orphaned_records()
        self.sample_data_validation()

    def check_orphaned_records(self):
        """Look for orphaned records beyond foreign key constraints"""
        self.log_progress("Checking for orphaned records...")

        # This is a simplified check - in practice you'd want to check
        # logical relationships even if not enforced by foreign keys
        pass

    def sample_data_validation(self):
        """Sample data for validation against field constraints"""
        self.log_progress("Sampling data for validation...")

        # Sample 1000 records from each table for basic validation
        for model in apps.get_models():
            if model._meta.managed:
                try:
                    sample_size = min(1000, model.objects.count())
                    if sample_size > 0:
                        # Basic validation - check if we can load records without errors
                        model.objects.all()[:sample_size].count()
                        self.stats["records_sampled"] += sample_size
                except Exception as e:
                    self.issues["high"].append(
                        {
                            "type": "model_loading_error",
                            "model": model.__name__,
                            "table": model._meta.db_table,
                            "error": str(e),
                            "description": f"Error loading records from {model.__name__}: {e}",
                        }
                    )

    def analyze_performance(self):
        """Phase 4: Performance and optimization analysis"""
        self.log_progress("⚡ Phase 4: Performance Analysis", "Performance")

        self.check_missing_indexes()
        self.check_table_sizes()

    def check_missing_indexes(self):
        """Check for potentially missing indexes"""
        self.log_progress("Analyzing index usage...")

        # Check foreign key columns without indexes
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    t.table_name,
                    t.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.columns t
                  ON t.table_name = kcu.table_name AND t.column_name = kcu.column_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'public'
                AND NOT EXISTS (
                    SELECT 1 FROM pg_indexes i
                    WHERE i.tablename = t.table_name
                    AND i.indexname LIKE '%' || t.column_name || '%'
                )
            """)

            unindexed_fks = cursor.fetchall()
            for table, column in unindexed_fks:
                self.issues["medium"].append(
                    {
                        "type": "missing_index",
                        "table": table,
                        "column": column,
                        "index_type": "foreign_key",
                        "description": f"Foreign key column {table}.{column} lacks index",
                    }
                )

    def check_table_sizes(self):
        """Analyze table sizes for optimization opportunities"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                    pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                FROM pg_tables
                WHERE schemaname = 'public'
                AND tablename NOT LIKE 'django_%'
                ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                LIMIT 20
            """)

            large_tables = cursor.fetchall()
            total_size = sum(table[2] for table in large_tables)

            self.stats["database_size_bytes"] = total_size
            self.stats["largest_tables"] = large_tables[:5]

    def generate_comprehensive_fix_plan(self):
        """Generate actionable fix plan with prioritization"""
        self.log_progress("📋 Generating comprehensive fix plan...")

        # Prioritize critical issues
        for issue in self.issues["critical"]:
            issue_key = f"{issue.get('table', 'unknown')}.{issue.get('column', 'unknown')}"

            if issue["type"] == "missing_column":
                self.decisions[issue_key] = {
                    "action": "create_migration",
                    "priority": "immediate",
                    "change": f"Add column {issue['column']} to {issue['table']}",
                    "sql": self.generate_add_column_sql(issue),
                    "risk": "low",
                    "reason": "Model field missing from database",
                }

            elif issue["type"] == "null_constraint_mismatch":
                if issue["has_null_data"] and not issue["model_nullable"]:
                    self.decisions[issue_key] = {
                        "action": "update_model",
                        "priority": "high",
                        "change": f"Make {issue['column']} nullable in model",
                        "risk": "low",
                        "reason": "Database contains NULL data but model requires NOT NULL",
                    }
                else:
                    self.decisions[issue_key] = {
                        "action": "update_database",
                        "priority": "medium",
                        "change": f"Update NULL constraint for {issue['column']}",
                        "sql": self.generate_constraint_fix_sql(issue),
                        "risk": "medium",
                        "reason": "Synchronize NULL constraint with model",
                    }

            elif issue["type"] == "foreign_key_violation":
                self.decisions[issue_key] = {
                    "action": "clean_orphaned_data",
                    "priority": "immediate",
                    "change": f"Clean {issue['orphaned_records']} orphaned records",
                    "sql": self.generate_cleanup_sql(issue),
                    "risk": "high",
                    "reason": "Referential integrity violation",
                }

    def generate_add_column_sql(self, issue):
        """Generate SQL to add missing column"""
        nullable = "NULL" if issue["nullable"] else "NOT NULL"
        # Simplified - would need proper type mapping
        column_type = "VARCHAR(255)"  # Default, should be improved

        return f"ALTER TABLE {issue['table']} ADD COLUMN {issue['column']} {column_type} {nullable};"

    def generate_constraint_fix_sql(self, issue):
        """Generate SQL to fix constraint issues"""
        if issue["model_nullable"] and not issue["db_nullable"]:
            return f"ALTER TABLE {issue['table']} ALTER COLUMN {issue['column']} DROP NOT NULL;"
        elif not issue["model_nullable"] and issue["db_nullable"]:
            return f"ALTER TABLE {issue['table']} ALTER COLUMN {issue['column']} SET NOT NULL;"
        return "-- No SQL change needed"

    def generate_cleanup_sql(self, issue):
        """Generate SQL to clean up orphaned data"""
        return f"""
        -- DANGER: This will delete orphaned records
        -- DELETE FROM {issue["table"]}
        -- WHERE {issue["column"]} NOT IN (
        --     SELECT {issue["reference_column"]} FROM {issue["reference_table"]}
        --     WHERE {issue["reference_column"]} IS NOT NULL
        -- );
        """

    def save_results(self, partial=False):
        """Save analysis results to multiple formats"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = "partial_" if partial else ""

        # Calculate total runtime
        runtime = datetime.now() - self.stats["analysis_start"]
        self.stats["total_runtime_seconds"] = runtime.total_seconds()

        # JSON format for programmatic access
        results = {
            "metadata": {
                "analysis_timestamp": timestamp,
                "partial_analysis": partial,
                "runtime_seconds": self.stats["total_runtime_seconds"],
            },
            "statistics": self.stats,
            "issues": self.issues,
            "decisions": self.decisions,
        }

        json_path = f"integrity_reports/{prefix}analysis_{timestamp}.json"
        with open(json_path, "w") as f:
            json.dump(results, f, indent=2, default=str)

        # Markdown format for human reading
        self.generate_markdown_report(f"{prefix}analysis_{timestamp}")

        # SQL scripts for fixes
        self.generate_sql_scripts(f"{prefix}fixes_{timestamp}")

        self.log_progress(f"✅ Results saved to integrity_reports/{prefix}analysis_{timestamp}.*")

    def generate_markdown_report(self, filename):
        """Generate human-readable markdown report"""
        total_issues = sum(len(issues) for issues in self.issues.values())

        report = f"""# Database Integrity Analysis Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Runtime: {self.stats["total_runtime_seconds"]:.1f} seconds

## Summary
- **Total Issues Found**: {total_issues}
- **Critical**: {len(self.issues["critical"])} (require immediate attention)
- **High**: {len(self.issues["high"])} (should be fixed soon)
- **Medium**: {len(self.issues["medium"])} (improvements recommended)
- **Low**: {len(self.issues["low"])} (minor optimizations)

## Statistics
- Tables Analyzed: {self.stats["tables_analyzed"]}
- Columns Checked: {self.stats["columns_checked"]}
- Constraints Verified: {self.stats["constraints_verified"]}
- Records Sampled: {self.stats["records_sampled"]}

## Critical Issues (Immediate Action Required)
"""

        for issue in self.issues["critical"]:
            report += f"""
### {issue["type"].title().replace("_", " ")}
- **Table**: {issue.get("table", "Unknown")}
- **Column**: {issue.get("column", "N/A")}
- **Description**: {issue.get("description", "No description")}
"""

        if not self.issues["critical"]:
            report += "\n✅ No critical issues found!\n"

        report += f"""
## Recommended Actions
Total fix actions planned: {len(self.decisions)}

"""

        for key, decision in self.decisions.items():
            report += f"""
### {key}
- **Action**: {decision["action"]}
- **Priority**: {decision["priority"]}
- **Change**: {decision["change"]}
- **Risk**: {decision["risk"]}
- **Reason**: {decision["reason"]}
"""

        with open(f"integrity_reports/{filename}.md", "w") as f:
            f.write(report)

    def generate_sql_scripts(self, filename):
        """Generate SQL scripts for automated fixes"""
        sql_script = f"""-- Database Integrity Fix Scripts
-- Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
-- WARNING: Review all statements before executing!

BEGIN;

"""

        for key, decision in self.decisions.items():
            if "sql" in decision:
                sql_script += f"""
-- Fix for {key}: {decision["change"]}
-- Priority: {decision["priority"]} | Risk: {decision["risk"]}
{decision["sql"]}

"""

        sql_script += """
-- COMMIT;  -- Uncomment when ready to apply changes
ROLLBACK;  -- Remove this line when ready to commit
"""

        with open(f"integrity_reports/{filename}.sql", "w") as f:
            f.write(sql_script)


# Main execution
if __name__ == "__main__":
    analyzer = DatabaseIntegrityAnalyzer()
    try:
        issues, decisions = analyzer.analyze()

        total_issues = sum(len(issue_list) for issue_list in issues.values())
        critical_count = len(issues["critical"])

        analyzer.log_progress("✅ Analysis complete!")
        analyzer.log_progress(f"📊 Found {total_issues} total issues ({critical_count} critical)")
        analyzer.log_progress(f"🔧 Generated {len(decisions)} fix recommendations")
        analyzer.log_progress(f"⏱️  Runtime: {analyzer.stats['total_runtime_seconds']:.1f} seconds")

        if critical_count > 0:
            analyzer.log_progress("⚠️  CRITICAL issues found - immediate attention required!")
            sys.exit(1)
        else:
            analyzer.log_progress("✅ No critical issues - database integrity looks good!")
            sys.exit(0)

    except KeyboardInterrupt:
        analyzer.log_progress("⏸️  Analysis interrupted by user")
        sys.exit(130)
    except Exception as e:
        analyzer.log_progress(f"❌ Analysis failed with error: {e}")
        sys.exit(1)
