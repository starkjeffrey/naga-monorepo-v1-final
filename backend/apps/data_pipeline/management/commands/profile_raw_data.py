"""
Profile Raw Data Management Command

Analyzes raw data quality and provides insights for cleaning rule development.
Useful for understanding data patterns before running the full pipeline.
"""

import csv
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.data_pipeline.core.registry import PipelineRegistry
from apps.data_pipeline.models import DataProfile


class Command(BaseCommand):
    help = "Profile raw data to analyze quality and inform cleaning rules"

    def add_arguments(self, parser):
        parser.add_argument("--table", required=True, help="Table to profile (must be registered in registry)")
        parser.add_argument("--raw-table-name", help="Override raw table name (default: raw_{table})")
        parser.add_argument(
            "--output-format",
            choices=["summary", "json", "csv"],
            default="summary",
            help="Output format (default: summary)",
        )
        parser.add_argument("--output-file", help="Output file path (default: stdout)")
        parser.add_argument(
            "--sample-size", type=int, default=1000, help="Sample size for detailed analysis (default: 1000)"
        )
        parser.add_argument("--include-recommendations", action="store_true", help="Include cleaning recommendations")

    def handle(self, *args, **options):
        """Main command handler"""
        table_name = options["table"]

        try:
            # Get table configuration
            config = PipelineRegistry().get_config(table_name)
            raw_table_name = options.get("raw_table_name") or config.raw_table_name

            # Check if raw table exists
            if not self._table_exists(raw_table_name):
                raise CommandError(f"Raw table does not exist: {raw_table_name}")

            self.stdout.write(f"🔍 Profiling table: {raw_table_name}")

            # Get existing profiles from database or generate new ones
            profiles = self._get_or_generate_profiles(table_name, raw_table_name, options["sample_size"])

            if not profiles:
                self.stdout.write(self.style.WARNING("No profile data found"))
                return

            # Generate output based on format
            output_format = options["output_format"]

            if output_format == "summary":
                output = self._generate_summary(profiles, options["include_recommendations"])
            elif output_format == "json":
                output = self._generate_json(profiles)
            elif output_format == "csv":
                output = self._generate_csv(profiles)

            # Write output
            if options.get("output_file"):
                output_path = Path(options["output_file"])
                output_path.parent.mkdir(parents=True, exist_ok=True)

                if output_format == "csv":
                    with open(output_path, "w", newline="") as f:
                        f.write(output)
                else:
                    with open(output_path, "w") as f:
                        f.write(output)

                self.stdout.write(f"📄 Profile saved to: {output_path}")
            else:
                self.stdout.write(output)

        except Exception as e:
            raise CommandError(f"Profiling failed: {e!s}") from e

    def _table_exists(self, table_name: str) -> bool:
        """Check if table exists in database"""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = %s
                )
            """,
                [table_name],
            )
            return cursor.fetchone()[0]

    def _get_or_generate_profiles(self, table_name: str, raw_table_name: str, sample_size: int) -> dict:
        """Get existing profiles from database or generate new ones"""
        # Try to get existing profiles from most recent run
        latest_profiles = DataProfile.objects.filter(table_name=table_name).order_by("-created_at")

        if latest_profiles.exists():
            self.stdout.write("📊 Using existing profile data from database")
            profiles = {}
            for profile in latest_profiles:
                profiles[profile.column_name] = {
                    "total_rows": profile.total_rows,
                    "null_count": profile.null_count,
                    "unique_count": profile.unique_count,
                    "avg_length": profile.avg_length,
                    "common_values": profile.common_values,
                    "null_patterns": profile.null_patterns,
                    "detected_type": profile.detected_type,
                    "completeness_score": profile.completeness_score,
                    "consistency_score": profile.consistency_score,
                    "has_encoding_issues": profile.has_encoding_issues,
                    "has_date_patterns": profile.has_date_patterns,
                    "has_numeric_patterns": profile.has_numeric_patterns,
                }
            return profiles

        else:
            self.stdout.write(f"🔄 Generating new profiles (sample size: {sample_size})")
            return self._generate_profiles(raw_table_name, sample_size)

    def _generate_profiles(self, raw_table_name: str, sample_size: int) -> dict:
        """Generate new profiles by analyzing raw table"""
        profiles = {}

        with connection.cursor() as cursor:
            # Get column names (excluding metadata columns)
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s AND column_name NOT LIKE '_%%'
                ORDER BY ordinal_position
            """,
                [raw_table_name],
            )

            columns = [row[0] for row in cursor.fetchall()]

            # Get total row count
            cursor.execute(f'SELECT COUNT(*) FROM "{raw_table_name}"')
            total_rows = cursor.fetchone()[0]

            # Profile each column
            for column in columns:
                self.stdout.write(f"   Analyzing column: {column}")
                profile = self._analyze_column(cursor, raw_table_name, column, total_rows, sample_size)
                profiles[column] = profile

        return profiles

    def _analyze_column(self, cursor, table_name: str, column_name: str, total_rows: int, sample_size: int) -> dict:
        """Analyze a single column comprehensively"""
        # Basic statistics
        cursor.execute(f'''
            SELECT
                COUNT("{column_name}") as non_null_count,
                COUNT(DISTINCT "{column_name}") as unique_count,
                MIN(LENGTH("{column_name}")) as min_length,
                MAX(LENGTH("{column_name}")) as max_length,
                AVG(LENGTH("{column_name}"))::numeric(10,2) as avg_length
            FROM "{table_name}"
            WHERE "{column_name}" IS NOT NULL AND "{column_name}" != ''
        ''')

        stats = cursor.fetchone()
        non_null_count = stats[0] if stats[0] else 0
        null_count = total_rows - non_null_count

        # Common values (top 20)
        cursor.execute(f'''
            SELECT "{column_name}", COUNT(*) as frequency
            FROM "{table_name}"
            WHERE "{column_name}" IS NOT NULL
            GROUP BY "{column_name}"
            ORDER BY frequency DESC
            LIMIT 20
        ''')

        common_values = [{"value": row[0], "count": row[1]} for row in cursor.fetchall()]

        # NULL pattern analysis
        null_patterns = self._analyze_null_patterns(cursor, table_name, column_name)

        # Sample data for pattern analysis
        cursor.execute(
            f'''
            SELECT "{column_name}"
            FROM "{table_name}"
            WHERE "{column_name}" IS NOT NULL AND "{column_name}" != ''
            ORDER BY RANDOM()
            LIMIT %s
        ''',
            [sample_size],
        )

        sample_values = [row[0] for row in cursor.fetchall()]

        # Pattern analysis
        patterns = self._analyze_patterns(sample_values)

        # Quality scoring
        completeness_score = (non_null_count / total_rows * 100) if total_rows > 0 else 0
        consistency_score = self._calculate_consistency_score(common_values, non_null_count)

        return {
            "total_rows": total_rows,
            "null_count": null_count,
            "unique_count": stats[1] if stats else 0,
            "min_length": stats[2] if stats else 0,
            "max_length": stats[3] if stats else 0,
            "avg_length": float(stats[4]) if stats and stats[4] else 0,
            "common_values": common_values[:10],  # Limit for display
            "null_patterns": null_patterns,
            "detected_type": patterns["detected_type"],
            "completeness_score": completeness_score,
            "consistency_score": consistency_score,
            "has_encoding_issues": patterns["has_encoding_issues"],
            "has_date_patterns": patterns["has_date_patterns"],
            "has_numeric_patterns": patterns["has_numeric_patterns"],
            "sample_values": sample_values[:5],  # Show 5 examples
        }

    def _analyze_null_patterns(self, cursor, table_name: str, column_name: str) -> list:
        """Find different NULL representations"""
        cursor.execute(f'''
            SELECT "{column_name}", COUNT(*) as cnt
            FROM "{table_name}"
            WHERE TRIM(UPPER("{column_name}")) IN ('NULL', 'NA', 'N/A', '', 'NONE', 'NIL', 'EMPTY')
               OR "{column_name}" ~ '^\\s*$'
            GROUP BY "{column_name}"
            ORDER BY cnt DESC
        ''')

        return [row[0] for row in cursor.fetchall()]

    def _analyze_patterns(self, sample_values: list) -> dict:
        """Analyze patterns in sample values"""

        if not sample_values:
            return {
                "detected_type": "empty",
                "has_encoding_issues": False,
                "has_date_patterns": False,
                "has_numeric_patterns": False,
            }

        # Pattern counters
        encoding_issues = 0
        date_patterns = 0
        numeric_patterns = 0

        for value in sample_values:
            value_str = str(value).strip()

            # Check for encoding issues
            if self._has_encoding_issues(value_str):
                encoding_issues += 1

            # Check for date patterns
            if self._looks_like_date(value_str):
                date_patterns += 1

            # Check for numeric patterns
            if self._is_numeric(value_str):
                numeric_patterns += 1

        total = len(sample_values)

        # Determine primary data type
        if date_patterns / total > 0.7:
            detected_type = "datetime"
        elif numeric_patterns / total > 0.8:
            detected_type = "numeric"
        elif all(len(str(v).strip()) <= 1 for v in sample_values[:20]):
            detected_type = "boolean"
        else:
            detected_type = "text"

        return {
            "detected_type": detected_type,
            "has_encoding_issues": encoding_issues / total > 0.1,
            "has_date_patterns": date_patterns / total > 0.3,
            "has_numeric_patterns": numeric_patterns / total > 0.5,
        }

    def _has_encoding_issues(self, text: str) -> bool:
        """Check for encoding issues"""
        indicators = ["\ufffd", "â€™", "Ã¡", "Ã©", "Ã­", "Ã³", "Ãº"]
        return any(indicator in text for indicator in indicators)

    def _looks_like_date(self, text: str) -> bool:
        """Check if text looks like a date"""
        import re

        if len(text.strip()) < 6:
            return False

        patterns = [
            r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
            r"\d{4}[/-]\d{1,2}[/-]\d{1,2}",
            r"[A-Za-z]{3}\s+\d{1,2}\s+\d{4}",
        ]

        return any(re.search(pattern, text) for pattern in patterns)

    def _is_numeric(self, value: str) -> bool:
        """Check if value is numeric"""
        try:
            float(value)
            return True
        except (ValueError, TypeError):
            return False

    def _calculate_consistency_score(self, common_values: list, total_count: int) -> float:
        """Calculate consistency score"""
        if not common_values or total_count == 0:
            return 0.0

        # Simple approach: higher score if few values dominate
        if len(common_values) == 1:
            return 100.0

        top_value_count = common_values[0]["count"]
        consistency = (top_value_count / total_count) * 100

        return min(consistency, 100.0)

    def _generate_summary(self, profiles: dict, include_recommendations: bool) -> str:
        """Generate human-readable summary"""
        lines = []
        lines.append("=" * 80)
        lines.append("DATA QUALITY PROFILE SUMMARY")
        lines.append("=" * 80)
        lines.append("")

        # Overall statistics
        total_columns = len(profiles)
        if total_columns == 0:
            return "No profile data available"

        total_rows = next(iter(profiles.values()))["total_rows"]
        avg_completeness = sum(p["completeness_score"] for p in profiles.values()) / total_columns

        lines.append("Dataset Overview:")
        lines.append(f"  Total rows: {total_rows:,}")
        lines.append(f"  Total columns: {total_columns}")
        lines.append(f"  Average completeness: {avg_completeness:.1f}%")
        lines.append("")

        # Column-by-column analysis
        lines.append("Column Analysis:")
        lines.append(f"{'Column':<25} {'Type':<12} {'Complete':<10} {'Unique':<10} {'Issues':<20}")
        lines.append("-" * 80)

        for column_name, profile in profiles.items():
            col_name = column_name[:24]
            data_type = profile["detected_type"][:11]
            completeness = f"{profile['completeness_score']:.1f}%"
            uniqueness = f"{profile['unique_count']:,}"

            issues = []
            if profile["has_encoding_issues"]:
                issues.append("encoding")
            if len(profile["null_patterns"]) > 1:
                issues.append("nulls")
            if profile["completeness_score"] < 50:
                issues.append("incomplete")

            issues_str = ",".join(issues[:2]) if issues else "none"

            lines.append(f"{col_name:<25} {data_type:<12} {completeness:<10} {uniqueness:<10} {issues_str:<20}")

        lines.append("")

        # Data quality issues summary
        encoding_issues = sum(1 for p in profiles.values() if p["has_encoding_issues"])
        null_pattern_issues = sum(1 for p in profiles.values() if len(p["null_patterns"]) > 1)
        low_completeness = sum(1 for p in profiles.values() if p["completeness_score"] < 70)

        lines.append("Data Quality Issues:")
        lines.append(f"  Columns with encoding issues: {encoding_issues}")
        lines.append(f"  Columns with multiple NULL patterns: {null_pattern_issues}")
        lines.append(f"  Columns with low completeness (<70%): {low_completeness}")
        lines.append("")

        # Recommendations
        if include_recommendations:
            recommendations = self._generate_recommendations(profiles)
            if recommendations:
                lines.append("Cleaning Recommendations:")
                for i, rec in enumerate(recommendations, 1):
                    lines.append(f"  {i}. {rec}")
                lines.append("")

        # Sample values for problematic columns
        problematic_columns = [
            col
            for col, profile in profiles.items()
            if profile["has_encoding_issues"] or len(profile["null_patterns"]) > 1
        ]

        if problematic_columns:
            lines.append("Sample Values from Problematic Columns:")
            for col in problematic_columns[:5]:  # Show up to 5 columns
                profile = profiles[col]
                lines.append(f"  {col}:")

                if "sample_values" in profile:
                    for sample in profile["sample_values"][:3]:
                        lines.append(f"    • '{sample}'")

                if profile["null_patterns"]:
                    lines.append(f"    NULL patterns: {profile['null_patterns']}")

                lines.append("")

        return "\n".join(lines)

    def _generate_json(self, profiles: dict) -> str:
        """Generate JSON output"""
        return json.dumps(profiles, indent=2, default=str)

    def _generate_csv(self, profiles: dict) -> str:
        """Generate CSV output"""
        if not profiles:
            return ""

        import io

        output = io.StringIO()

        # CSV headers
        headers = [
            "column_name",
            "detected_type",
            "total_rows",
            "null_count",
            "unique_count",
            "completeness_score",
            "consistency_score",
            "avg_length",
            "min_length",
            "max_length",
            "has_encoding_issues",
            "has_date_patterns",
            "has_numeric_patterns",
            "null_patterns_count",
        ]

        writer = csv.writer(output)
        writer.writerow(headers)

        # Write data rows
        for column_name, profile in profiles.items():
            row = [
                column_name,
                profile["detected_type"],
                profile["total_rows"],
                profile["null_count"],
                profile["unique_count"],
                profile["completeness_score"],
                profile["consistency_score"],
                profile["avg_length"],
                profile["min_length"],
                profile["max_length"],
                profile["has_encoding_issues"],
                profile["has_date_patterns"],
                profile["has_numeric_patterns"],
                len(profile["null_patterns"]),
            ]
            writer.writerow(row)

        return output.getvalue()

    def _generate_recommendations(self, profiles: dict) -> list:
        """Generate cleaning recommendations"""
        recommendations = []

        for col_name, profile in profiles.items():
            # Encoding issues
            if profile["has_encoding_issues"]:
                recommendations.append(f"Apply encoding fix to column '{col_name}' - detected character corruption")

            # Multiple NULL patterns
            if len(profile["null_patterns"]) > 1:
                patterns = ", ".join([f"'{p}'" for p in profile["null_patterns"][:3]])
                recommendations.append(f"Standardize NULL patterns in '{col_name}': {patterns}")

            # Low completeness
            if profile["completeness_score"] < 50:
                recommendations.append(
                    f"Column '{col_name}' has low completeness ({profile['completeness_score']:.1f}%) - "
                    f"verify if this is expected"
                )

            # Date patterns but not detected as date
            if profile["has_date_patterns"] and profile["detected_type"] != "datetime":
                recommendations.append(
                    f"Column '{col_name}' contains dates but detected as '{profile['detected_type']}' - "
                    f"consider date parsing"
                )

        return recommendations
