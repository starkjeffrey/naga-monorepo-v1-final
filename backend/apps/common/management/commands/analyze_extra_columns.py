"""
Extra Column Analysis Django Management Command
Intelligently categorizes database columns not defined in Django models
and provides recommendations for cleanup or model addition.
"""

import json
import os
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Analyze and categorize extra database columns not defined in Django models"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.analysis_data = None
        self.extra_columns = []
        self.categorized_columns = {
            "legacy_migration": [],  # Old columns from data migration
            "audit_tracking": [],  # Created/modified timestamps, etc.
            "soft_delete": [],  # Deleted_at, is_deleted, etc.
            "caching_denorm": [],  # Cached/denormalized data
            "external_integration": [],  # External system IDs/references
            "unused_experiment": [],  # Experimental/unused columns
            "business_critical": [],  # Contains important business data
            "metadata": [],  # System metadata columns
            "unknown": [],  # Needs manual review
        }
        self.table_patterns = {
            # Legacy patterns
            "legacy_migration": [
                r".*_old$",
                r".*_backup$",
                r".*_temp$",
                r".*_orig$",
                r"legacy_.*",
                r"old_.*",
                r"backup_.*",
            ],
            # Audit/tracking patterns
            "audit_tracking": [
                r"created_by.*",
                r"updated_by.*",
                r"modified_by.*",
                r"created_at.*",
                r"updated_at.*",
                r"modified_at.*",
                r".*_timestamp$",
                r".*_date$",
                r"last_.*",
                r"version$",
                r"revision$",
            ],
            # Soft delete patterns
            "soft_delete": [
                r"deleted_at.*",
                r"is_deleted",
                r".*_deleted$",
                r"archived_at.*",
                r"is_archived",
                r".*_archived$",
                r"active$",
                r"is_active",
                r"status$",
            ],
            # Caching/denormalization patterns
            "caching_denorm": [r".*_count$", r".*_total$", r".*_sum$", r"cached_.*", r"computed_.*", r"calculated_.*"],
            # External integration patterns
            "external_integration": [
                r".*_external_id$",
                r"external_.*",
                r".*_uuid$",
                r".*_reference$",
                r".*_ref$",
                r"sync_.*",
                r"import_.*",
                r".*_source_id$",
            ],
            # Metadata patterns
            "metadata": [r".*_metadata$", r".*_properties$", r".*_config$", r"settings$", r"options$", r"flags$"],
        }

    def add_arguments(self, parser):
        parser.add_argument(
            "--generate-scripts", action="store_true", help="Generate cleanup scripts for safe-to-drop columns"
        )

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

    def extract_extra_columns(self):
        """Extract extra column issues from analysis data"""
        self.log("Extracting extra columns from analysis...")

        # Get high-priority issues that are extra columns
        all_issues = self.analysis_data["issues"]["high"] + self.analysis_data["issues"]["medium"]

        for issue in all_issues:
            if issue.get("type") == "extra_column":
                self.extra_columns.append(issue)

        self.log(f"Found {len(self.extra_columns)} extra columns to analyze")

    def get_column_data_sample(self, table: str, column: str, limit: int = 10) -> list:
        """Get sample data from a column to understand its usage"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT DISTINCT "{column}"
                    FROM "{table}"
                    WHERE "{column}" IS NOT NULL
                    ORDER BY "{column}"
                    LIMIT %s
                """,
                    [limit],
                )
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            self.log(f"Error sampling {table}.{column}: {e}", "WARNING")
            return []

    def analyze_column_usage_patterns(self, table: str, column: str) -> dict:
        """Analyze column usage patterns"""
        try:
            with connection.cursor() as cursor:
                # Get basic statistics
                cursor.execute(f"""
                    SELECT
                        COUNT(*) as total_rows,
                        COUNT("{column}") as non_null_rows,
                        COUNT(DISTINCT "{column}") as distinct_values
                    FROM "{table}"
                """)
                total, non_null, distinct = cursor.fetchone()

                # Get data type info
                cursor.execute(
                    """
                    SELECT data_type, character_maximum_length
                    FROM information_schema.columns
                    WHERE table_name = %s AND column_name = %s
                """,
                    [table, column],
                )

                type_info = cursor.fetchone()
                data_type = type_info[0] if type_info else "unknown"
                max_length = type_info[1] if type_info else None

                return {
                    "total_rows": total,
                    "non_null_rows": non_null,
                    "distinct_values": distinct,
                    "null_percentage": ((total - non_null) / total * 100) if total > 0 else 0,
                    "data_type": data_type,
                    "max_length": max_length,
                    "fill_rate": (non_null / total * 100) if total > 0 else 0,
                }
        except Exception as e:
            self.log(f"Error analyzing {table}.{column}: {e}", "WARNING")
            return {}

    def categorize_column_by_pattern(self, table: str, column: str) -> str | None:
        """Categorize column based on name patterns"""
        column_lower = column.lower()
        table_lower = table.lower()

        # Check each category pattern
        for category, patterns in self.table_patterns.items():
            for pattern in patterns:
                if re.match(pattern, column_lower):
                    return category

        # Special business logic patterns
        if "cashier" in table_lower:
            if any(term in column_lower for term in ["session", "drawer", "till", "balance"]):
                return "business_critical"

        if "receipt" in table_lower:
            if any(term in column_lower for term in ["total", "amount", "tax", "discount"]):
                return "business_critical"

        if "enrollment" in table_lower:
            if any(term in column_lower for term in ["status", "date", "fee", "payment"]):
                return "business_critical"

        return None

    def categorize_column_by_data(self, table: str, column: str, usage_stats: dict, sample_data: list) -> str:
        """Categorize column based on data analysis"""

        # Very low fill rate - likely unused
        if usage_stats.get("fill_rate", 0) < 1:
            return "unused_experiment"

        # High null percentage might be soft delete or optional feature
        if usage_stats.get("null_percentage", 0) > 80:
            if any(term in column.lower() for term in ["deleted", "archived", "active"]):
                return "soft_delete"
            return "unused_experiment"

        # Check sample data for patterns
        if sample_data:
            # UUID-like patterns
            if any(isinstance(val, str) and len(val) == 36 and val.count("-") == 4 for val in sample_data[:3]):
                return "external_integration"

            # Timestamp-like patterns
            if any(isinstance(val, str) and re.match(r"\d{4}-\d{2}-\d{2}", str(val)) for val in sample_data[:3]):
                return "audit_tracking"

            # Boolean-like patterns for soft delete
            if {str(v).lower() for v in sample_data if v is not None}.issubset({"true", "false", "1", "0", "t", "f"}):
                if any(term in column.lower() for term in ["active", "deleted", "enabled"]):
                    return "soft_delete"

        # Check for numeric patterns that might be counts/totals
        if usage_stats.get("data_type") in ["integer", "bigint", "numeric"]:
            if any(term in column.lower() for term in ["count", "total", "sum", "balance"]):
                return "caching_denorm"

        # Default to business critical if we can't determine otherwise
        return "business_critical"

    def analyze_extra_columns(self):
        """Analyze and categorize all extra columns"""
        self.log("🔍 Analyzing extra columns...")

        for i, column_issue in enumerate(self.extra_columns, 1):
            table = column_issue["table"]
            column = column_issue["column"]

            self.log(f"Analyzing {i}/{len(self.extra_columns)}: {table}.{column}")

            # Get usage statistics
            usage_stats = self.analyze_column_usage_patterns(table, column)

            # Get sample data
            sample_data = self.get_column_data_sample(table, column, 5)

            # Try pattern-based categorization first
            category = self.categorize_column_by_pattern(table, column)

            # If no pattern match, use data-based categorization
            if not category:
                category = self.categorize_column_by_data(table, column, usage_stats, sample_data)

            # Enrich the column information
            enriched_column = {
                **column_issue,
                "category": category,
                "usage_stats": usage_stats,
                "sample_data": sample_data[:3],  # Only keep first 3 samples
                "recommendation": self.get_recommendation(category, table, column, usage_stats),
            }

            self.categorized_columns[category].append(enriched_column)

        self.log("✅ Extra column analysis complete")

    def get_recommendation(self, category: str, table: str, column: str, usage_stats: dict) -> dict:
        """Generate specific recommendations for each category"""
        recommendations = {
            "legacy_migration": {
                "action": "DROP",
                "priority": "HIGH",
                "risk": "LOW",
                "description": f"Drop legacy column {column} - appears to be from old migration",
                "sql": f'ALTER TABLE "{table}" DROP COLUMN "{column}";',
            },
            "audit_tracking": {
                "action": "EVALUATE",
                "priority": "MEDIUM",
                "risk": "MEDIUM",
                "description": f"Evaluate if {column} should be added to Django model for audit tracking",
                "sql": None,
            },
            "soft_delete": {
                "action": "ADD_TO_MODEL",
                "priority": "HIGH",
                "risk": "MEDIUM",
                "description": f"Add {column} to Django model - likely used for soft delete functionality",
                "sql": None,
            },
            "caching_denorm": {
                "action": "EVALUATE",
                "priority": "LOW",
                "risk": "MEDIUM",
                "description": f"Evaluate if cached column {column} is still needed or can be dropped",
                "sql": f'-- Consider: ALTER TABLE "{table}" DROP COLUMN "{column}";',
            },
            "external_integration": {
                "action": "ADD_TO_MODEL",
                "priority": "HIGH",
                "risk": "HIGH",
                "description": f"Add {column} to Django model - likely used for external system integration",
                "sql": None,
            },
            "unused_experiment": {
                "action": "DROP",
                "priority": "MEDIUM",
                "risk": "LOW",
                "description": (
                    f"Drop unused experimental column {column} (fill rate: {usage_stats.get('fill_rate', 0):.1f}%)"
                ),
                "sql": f'ALTER TABLE "{table}" DROP COLUMN "{column}";',
            },
            "business_critical": {
                "action": "ADD_TO_MODEL",
                "priority": "CRITICAL",
                "risk": "HIGH",
                "description": f"URGENT: Add {column} to Django model - contains business-critical data",
                "sql": None,
            },
            "metadata": {
                "action": "EVALUATE",
                "priority": "LOW",
                "risk": "LOW",
                "description": f"Evaluate metadata column {column} - may be safe to drop or add to model",
                "sql": None,
            },
            "unknown": {
                "action": "MANUAL_REVIEW",
                "priority": "HIGH",
                "risk": "HIGH",
                "description": f"Manual review required for {column} - unclear purpose and usage",
                "sql": None,
            },
        }

        return recommendations.get(category, recommendations["unknown"])

    def generate_summary_report(self) -> str:
        """Generate comprehensive summary report"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = f"""# Extra Column Analysis Report
Generated: {timestamp}

## Summary
Total extra columns analyzed: {len(self.extra_columns)}

"""

        # Category breakdown
        report += "## Category Breakdown\n"
        for category, columns in self.categorized_columns.items():
            if columns:
                report += f"- **{category.replace('_', ' ').title()}**: {len(columns)} columns\n"

        report += "\n## Recommendations by Priority\n\n"

        # Group by priority
        priority_groups = defaultdict(list)
        for _category, columns in self.categorized_columns.items():
            for col in columns:
                priority = col["recommendation"]["priority"]
                priority_groups[priority].append(col)

        priority_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        for priority in priority_order:
            if priority in priority_groups:
                report += f"### {priority} Priority ({len(priority_groups[priority])} items)\n\n"
                for col in priority_groups[priority]:
                    report += f"**{col['table']}.{col['column']}** ({col['category']})\n"
                    report += f"- Action: {col['recommendation']['action']}\n"
                    report += f"- Description: {col['recommendation']['description']}\n"
                    if col["usage_stats"]:
                        report += f"- Fill Rate: {col['usage_stats'].get('fill_rate', 0):.1f}%\n"
                    if col["recommendation"]["sql"]:
                        report += f"- SQL: ```sql\n{col['recommendation']['sql']}\n```\n"
                    report += "\n"

        return report

    def generate_cleanup_scripts(self):
        """Generate SQL cleanup scripts for safe-to-drop columns"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Safe to drop categories with low risk
        safe_categories = ["legacy_migration", "unused_experiment"]

        drop_script = f"""-- Extra Column Cleanup Script
-- Generated: {datetime.now()}
-- WARNING: Review carefully before executing!

-- Backup recommended before running:
-- pg_dump -h localhost -U debug -d naga_local > backup_before_cleanup_{timestamp}.sql

BEGIN;

"""

        drop_count = 0
        for category in safe_categories:
            if self.categorized_columns[category]:
                drop_script += f"\n-- {category.replace('_', ' ').title()} columns\n"
                for col in self.categorized_columns[category]:
                    if col["recommendation"]["action"] == "DROP" and col["recommendation"]["risk"] == "LOW":
                        drop_script += f"-- {col['description']}\n"
                        drop_script += f"{col['recommendation']['sql']}\n"
                        drop_count += 1

        drop_script += f"""
-- Total columns to be dropped: {drop_count}
COMMIT;
"""

        # Save script
        script_path = f"cleanup_extra_columns_{timestamp}.sql"
        with open(script_path, "w") as f:
            f.write(drop_script)

        self.log(f"📄 Cleanup script generated: {script_path}")
        return script_path

    def handle(self, *args, **options):
        """Main command handler"""
        self.log("🚀 Starting Extra Column Analysis...")

        try:
            # Load analysis data
            self.load_analysis_data()

            # Extract extra columns
            self.extract_extra_columns()

            if not self.extra_columns:
                self.log("✅ No extra columns found to analyze")
                return

            # Analyze and categorize
            self.analyze_extra_columns()

            # Generate reports
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Save detailed JSON results
            results = {
                "metadata": {"timestamp": timestamp, "total_columns_analyzed": len(self.extra_columns)},
                "categorized_columns": self.categorized_columns,
                "summary": {
                    category: len(columns) for category, columns in self.categorized_columns.items() if columns
                },
            }

            json_path = f"integrity_reports/extra_columns_analysis_{timestamp}.json"
            with open(json_path, "w") as f:
                json.dump(results, f, indent=2, default=str)

            # Generate summary report
            summary_report = self.generate_summary_report()
            report_path = f"integrity_reports/extra_columns_report_{timestamp}.md"
            with open(report_path, "w") as f:
                f.write(summary_report)

            # Generate cleanup scripts if requested
            if options["generate_scripts"]:
                self.generate_cleanup_scripts()

            # Print summary
            total_analyzed = len(self.extra_columns)
            critical_count = len(self.categorized_columns["business_critical"])
            drop_safe_count = len(self.categorized_columns["legacy_migration"]) + len(
                self.categorized_columns["unused_experiment"]
            )

            self.log("✅ Extra column analysis completed!")
            self.log(f"📊 Analyzed {total_analyzed} extra columns")
            self.log(f"🚨 {critical_count} business-critical columns found")
            self.log(f"🗑️ {drop_safe_count} columns are safe to drop")
            self.log(f"📄 Reports saved: {json_path}, {report_path}")

        except Exception as e:
            self.log(f"❌ Analysis failed: {e}", "ERROR")
            raise
