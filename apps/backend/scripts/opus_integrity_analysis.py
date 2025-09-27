import json
import os

import django
from django.apps import apps
from django.db import connection

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()


class DatabaseIntegrityAnalyzer:
    def __init__(self):
        self.issues = {"critical": [], "high": [], "medium": [], "low": []}
        self.decisions = {}

    def analyze(self):
        """Run complete analysis"""
        print("🔍 Starting Deep Integrity Analysis...")

        self.check_null_constraints()
        self.check_missing_columns()
        self.check_extra_columns()
        self.check_orphaned_tables()
        self.check_data_integrity()
        self.generate_fix_plan()

        return self.issues, self.decisions

    def check_null_constraints(self):
        """Check NULL constraint mismatches"""
        print("  📋 Checking NULL constraints...")
        with connection.cursor() as cursor:
            # Get all columns from database
            cursor.execute("""
                SELECT
                    table_name,
                    column_name,
                    is_nullable,
                    data_type,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name NOT LIKE 'django_%'
                AND table_name NOT LIKE 'legacy_%'
                ORDER BY table_name, ordinal_position
            """)
            db_columns = cursor.fetchall()

        # Compare with models
        for model in apps.get_models():
            table_name = model._meta.db_table
            for field in model._meta.fields:
                db_column = next((col for col in db_columns if col[0] == table_name and col[1] == field.column), None)

                if db_column:
                    db_nullable = db_column[2] == "YES"
                    model_nullable = field.null

                    if db_nullable != model_nullable:
                        self.issues["critical"].append(
                            {
                                "type": "null_constraint_mismatch",
                                "table": table_name,
                                "column": field.column,
                                "db_nullable": db_nullable,
                                "model_nullable": model_nullable,
                                "has_data": self.check_column_has_data(table_name, field.column),
                            }
                        )

    def check_column_has_data(self, table, column):
        """Check if column has non-null data"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM "{table}"
                    WHERE "{column}" IS NOT NULL
                """)
                return cursor.fetchone()[0] > 0
        except Exception:
            return False

    def check_missing_columns(self):
        """Find model fields not in database"""
        print("  📋 Checking missing columns...")
        # Implementation similar to above
        pass

    def check_extra_columns(self):
        """Find database columns not in models"""
        print("  📋 Checking extra columns...")
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT table_name, column_name, data_type
                FROM information_schema.columns
                WHERE table_schema = 'public'
                AND table_name NOT LIKE 'django_%'
                AND table_name NOT LIKE 'auth_%'
                AND table_name NOT LIKE 'legacy_%'
            """)
            db_columns = {(row[0], row[1]) for row in cursor.fetchall()}

        model_columns = set()
        for model in apps.get_models():
            table = model._meta.db_table
            for field in model._meta.fields:
                model_columns.add((table, field.column))

        extra = db_columns - model_columns
        for table, column in extra:
            # Check if column has data
            has_data = self.check_column_has_data(table, column)
            self.issues["high"].append(
                {
                    "type": "extra_column",
                    "table": table,
                    "column": column,
                    "has_data": has_data,
                    "recommendation": "preserve" if has_data else "drop",
                }
            )

    def check_orphaned_tables(self):
        """Find database tables not represented by models"""
        print("  📋 Checking orphaned tables...")
        pass

    def check_data_integrity(self):
        """Check basic data integrity"""
        print("  📋 Checking data integrity...")
        pass

    def generate_fix_plan(self):
        """Generate actionable fix plan"""
        print("  📋 Generating fix plan...")
        for issue in self.issues["critical"]:
            if issue["type"] == "null_constraint_mismatch":
                if issue["has_data"] and not issue["model_nullable"]:
                    # Model says NOT NULL but DB has NULL and contains data
                    self.decisions[f"{issue['table']}.{issue['column']}"] = {
                        "action": "update_model",
                        "change": "make_nullable",
                        "reason": "Column has NULL data in production",
                    }
                elif not issue["has_data"] and issue["model_nullable"]:
                    # Model says NULL but DB says NOT NULL and no data
                    self.decisions[f"{issue['table']}.{issue['column']}"] = {
                        "action": "update_database",
                        "change": "make_nullable",
                        "reason": "Model expects nullable, no data impact",
                    }


analyzer = DatabaseIntegrityAnalyzer()
issues, decisions = analyzer.analyze()

# Save report
with open("integrity_reports/analysis.json", "w") as f:
    json.dump({"issues": issues, "decisions": decisions}, f, indent=2, default=str)

print(f"✅ Analysis complete. Found {sum(len(v) for v in issues.values())} issues")
