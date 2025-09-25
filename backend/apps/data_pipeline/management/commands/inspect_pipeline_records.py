"""
Pipeline Record Inspector

Management command to inspect records through all pipeline stages for audit and validation purposes.
Supports random sampling, specific record tracking, and stage-by-stage comparison.
"""

import csv
import json
import random
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.data_pipeline.core.registry import get_registry


class Command(BaseCommand):
    help = "Inspect pipeline records through all stages for audit and validation"

    def add_arguments(self, parser):
        parser.add_argument("table_name", type=str, help="Table to inspect (e.g., students, academicclasses)")
        parser.add_argument(
            "--sample-size", type=int, default=10, help="Number of random records to sample (default: 10)"
        )
        parser.add_argument("--source-row", type=int, help="Inspect specific record by source row number")
        parser.add_argument("--stage-comparison", type=str, help="Compare specific stages (e.g., '3,4' or '1,3,5')")
        parser.add_argument("--export-csv", type=str, help="Export results to CSV file")
        parser.add_argument(
            "--show-all-columns", action="store_true", help="Show all columns instead of key columns only"
        )
        parser.add_argument(
            "--business-rules-only", action="store_true", help="Focus on business rule validation fields"
        )
        parser.add_argument("--include-invalid", action="store_true", help="Include invalid records from Stage 4")

    def handle(self, *args, **options):
        """Main command handler"""
        table_name = options["table_name"]

        try:
            # Validate table exists in registry
            registry = get_registry()
            registry.get_config(table_name)

            self.stdout.write(f"🔍 Inspecting pipeline records for table: {table_name}")
            self.stdout.write(f"{'=' * 80}")

            # Get stage table information
            stage_info = self._get_stage_table_info(table_name)
            self._show_stage_summary(stage_info)

            # Determine which records to inspect
            if options["source_row"]:
                records_to_inspect = [options["source_row"]]
                self.stdout.write(f"\n📌 Inspecting specific record: Row {options['source_row']}")
            else:
                records_to_inspect = self._get_sample_records(table_name, options["sample_size"])
                self.stdout.write(f"\n🎲 Inspecting {len(records_to_inspect)} random records")

            # Perform inspection
            if options["stage_comparison"]:
                self._compare_specific_stages(table_name, records_to_inspect, options)
            else:
                self._inspect_all_stages(table_name, records_to_inspect, options)

            # Export if requested
            if options["export_csv"]:
                self._export_to_csv(table_name, records_to_inspect, options)

        except Exception as e:
            raise CommandError(f"Inspection failed: {e}") from e

    def _get_stage_table_info(self, table_name: str) -> dict[str, dict]:
        """Get information about all stage tables for the given table"""
        stage_tables = {
            1: f"{table_name}_stage1_raw",
            2: f"{table_name}_stage1_raw",  # Stage 2 uses same table as Stage 1
            3: f"{table_name}_stage3_cleaned",
            4: {"valid": f"{table_name}_stage4_valid", "invalid": f"{table_name}_stage4_invalid"},
            5: f"{table_name}_stage5_transformed",
            6: {"headers": f"{table_name}_headers", "lines": f"{table_name}_lines"},
        }

        stage_info = {}

        with connection.cursor() as cursor:
            for stage, table_spec in stage_tables.items():
                if isinstance(table_spec, str):
                    # Single table for this stage
                    if self._table_exists(cursor, table_spec):
                        count = self._get_table_count(cursor, table_spec)
                        stage_info[stage] = {"table": table_spec, "count": count}
                elif isinstance(table_spec, dict):
                    # Multiple tables for this stage
                    stage_tables_info = {}
                    for sub_type, sub_table in table_spec.items():
                        if self._table_exists(cursor, sub_table):
                            count = self._get_table_count(cursor, sub_table)
                            stage_tables_info[sub_type] = {"table": sub_table, "count": count}
                    if stage_tables_info:
                        stage_info[stage] = stage_tables_info

        return stage_info

    def _table_exists(self, cursor, table_name: str) -> bool:
        """Check if table exists in database"""
        cursor.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """,
            [table_name],
        )
        return cursor.fetchone()[0]

    def _get_table_count(self, cursor, table_name: str) -> int:
        """Get record count for table"""
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]

    def _show_stage_summary(self, stage_info: dict):
        """Show summary of available stages and record counts"""
        self.stdout.write("\n📊 Pipeline Stage Summary:")

        for stage in sorted(stage_info.keys()):
            info = stage_info[stage]

            if isinstance(info, dict) and "table" in info:
                # Single table
                self.stdout.write(f"   Stage {stage}: {info['table']} ({info['count']:,} records)")
            elif isinstance(info, dict):
                # Multiple tables
                self.stdout.write(f"   Stage {stage}:")
                for sub_type, sub_info in info.items():
                    self.stdout.write(f"     - {sub_type}: {sub_info['table']} ({sub_info['count']:,} records)")

    def _get_sample_records(self, table_name: str, sample_size: int) -> list[int]:
        """Get random sample of source row numbers"""
        stage1_table = f"{table_name}_stage1_raw"

        with connection.cursor() as cursor:
            if not self._table_exists(cursor, stage1_table):
                raise CommandError(f"Stage 1 table not found: {stage1_table}")

            # Get all source row numbers
            cursor.execute(f"SELECT _row_number FROM {stage1_table} WHERE _row_number IS NOT NULL")
            all_rows = [row[0] for row in cursor.fetchall()]

            if not all_rows:
                raise CommandError("No source row numbers found in Stage 1 table")

            # Sample random records
            sample_size = min(sample_size, len(all_rows))
            return random.sample(all_rows, sample_size)

    def _inspect_all_stages(self, table_name: str, records_to_inspect: list[int], options: dict):
        """Inspect records through all available stages"""
        stage_info = self._get_stage_table_info(table_name)

        for record_num, source_row in enumerate(records_to_inspect, 1):
            self.stdout.write(f"\n{'─' * 80}")
            self.stdout.write(f"🔍 Record {record_num}/{len(records_to_inspect)} - Source Row: {source_row}")
            self.stdout.write(f"{'─' * 80}")

            # Track record through all stages
            for stage in sorted(stage_info.keys()):
                info = stage_info[stage]
                self._show_stage_record(table_name, stage, info, source_row, options)

    def _show_stage_record(self, table_name: str, stage: int, info: dict, source_row: int, options: dict):
        """Show record data for a specific stage"""
        stage_names = {
            1: "Raw Import",
            2: "Data Profiling",
            3: "Data Cleaning",
            4: "Validation",
            5: "Transformation",
            6: "Record Splitting",
        }

        self.stdout.write(f"\n   📋 Stage {stage} - {stage_names.get(stage, 'Unknown')}")

        if isinstance(info, dict) and "table" in info:
            # Single table
            self._show_table_record(info["table"], source_row, options, f"Stage {stage}")
        elif isinstance(info, dict):
            # Multiple tables
            for sub_type, sub_info in info.items():
                if sub_type == "invalid" and not options["include_invalid"]:
                    continue
                self._show_table_record(sub_info["table"], source_row, options, f"Stage {stage} ({sub_type})")

    def _show_table_record(self, table_name: str, source_row: int, options: dict, context: str):
        """Show record data from specific table"""
        with connection.cursor() as cursor:
            # Get column names
            cursor.execute(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position
            """,
                [table_name],
            )
            columns_info = cursor.fetchall()

            if not columns_info:
                self.stdout.write(f"     ⚠️  No record found in {table_name}")
                return

            # Select columns to show
            columns_to_show = self._select_columns_to_show([col[0] for col in columns_info], table_name, options)

            # Get record data
            columns_str = ", ".join(columns_to_show)
            cursor.execute(
                f"""
                SELECT {columns_str}
                FROM {table_name}
                WHERE _row_number = %s
                LIMIT 1
            """,
                [source_row],
            )

            record = cursor.fetchone()

            if not record:
                self.stdout.write(f"     ⚠️  No record found in {table_name} for source row {source_row}")
                return

            # Display record data
            self.stdout.write(f"     📂 {context} ({table_name}):")

            for _i, (col_name, value) in enumerate(zip(columns_to_show, record, strict=False)):
                # Format value for display
                display_value = self._format_display_value(value)
                self.stdout.write(f"        {col_name}: {display_value}")

    def _select_columns_to_show(self, all_columns: list[str], table_name: str, options: dict) -> list[str]:
        """Select which columns to show based on options"""
        if options["show_all_columns"]:
            return all_columns

        if options["business_rules_only"]:
            return self._get_business_rule_columns(table_name, all_columns)

        # Default: show key columns
        return self._get_key_columns(table_name, all_columns)

    def _get_key_columns(self, table_name: str, all_columns: list[str]) -> list[str]:
        """Get key columns for display"""
        # Always include audit columns
        key_columns = []
        audit_columns = ["_row_number", "_source_file", "_import_timestamp"]

        for col in audit_columns:
            if col in all_columns:
                key_columns.append(col)

        # Add table-specific key columns (Stage 1 uses original column names)
        table_key_mapping = {
            "students": ['"ID"', '"Name"', '"KName"', '"BirthDate"', '"Gender"'],
            "academicclasses": ["classid", "classname", "term"],
            "academiccoursetakers": ["studentid", "classid", "termid"],
            "terms": ["termid", "termname", "startdate", "enddate"],
            "receipt_headers": ["receiptid", "studentid", "amount", "date"],
            "receipt_items": ["receiptid", "description", "amount"],
        }

        base_table = table_name.split("_stage")[0].split("_")[0]
        specific_columns = table_key_mapping.get(base_table, [])

        for col in specific_columns:
            if col.lower() in [c.lower() for c in all_columns]:
                # Find exact case match
                exact_match = next((c for c in all_columns if c.lower() == col.lower()), col)
                if exact_match not in key_columns:
                    key_columns.append(exact_match)

        return key_columns

    def _get_business_rule_columns(self, table_name: str, all_columns: list[str]) -> list[str]:
        """Get business rule validation columns"""
        business_rule_columns = ["_row_number"]

        # Table-specific business rule columns
        if "students" in table_name:
            br_columns = [
                "name",
                "clean_name",
                "is_frozen",
                "is_sponsored",
                "sponsor_name",
                "has_admin_fees",
                "birthdate",
                "birth_date_normalized",
                "emergency_contact_name",
                "_validation_errors",
                "_validation_score",
            ]
        elif "academicclasses" in table_name:
            br_columns = ["classid", "classname", "term", "_validation_errors", "_validation_score"]
        elif "academiccoursetakers" in table_name:
            br_columns = ["studentid", "classid", "termid", "_validation_errors", "_validation_score"]
        else:
            br_columns = ["_validation_errors", "_validation_score"]

        for col in br_columns:
            if col.lower() in [c.lower() for c in all_columns]:
                exact_match = next((c for c in all_columns if c.lower() == col.lower()), col)
                if exact_match not in business_rule_columns:
                    business_rule_columns.append(exact_match)

        return business_rule_columns

    def _format_display_value(self, value: Any) -> str:
        """Format value for display"""
        if value is None:
            return "NULL"
        elif isinstance(value, str):
            if len(value) > 100:
                return f'"{value[:97]}..."'
            return f'"{value}"'
        elif isinstance(value, (dict, list)):
            return json.dumps(value, indent=None, separators=(",", ":"))[:200]
        else:
            return str(value)

    def _compare_specific_stages(self, table_name: str, records_to_inspect: list[int], options: dict):
        """Compare records between specific stages"""
        stages_str = options["stage_comparison"]
        stages = [int(s.strip()) for s in stages_str.split(",")]

        self.stdout.write(f"\n🔀 Comparing stages: {' → '.join(map(str, stages))}")

        stage_info = self._get_stage_table_info(table_name)

        for record_num, source_row in enumerate(records_to_inspect, 1):
            self.stdout.write(f"\n{'─' * 80}")
            self.stdout.write(f"📊 Record {record_num}/{len(records_to_inspect)} - Source Row: {source_row}")
            self.stdout.write(f"{'─' * 80}")

            # Get data from each requested stage
            stage_data = {}
            for stage in stages:
                if stage in stage_info:
                    info = stage_info[stage]
                    if isinstance(info, dict) and "table" in info:
                        stage_data[stage] = self._get_record_data(info["table"], source_row)
                    elif isinstance(info, dict) and "valid" in info:
                        # For stage 4, prefer valid records
                        stage_data[stage] = self._get_record_data(info["valid"]["table"], source_row)
                        if not stage_data[stage] and options["include_invalid"]:
                            stage_data[stage] = self._get_record_data(info["invalid"]["table"], source_row)

            # Show comparison
            self._show_stage_comparison(stages, stage_data, options)

    def _get_record_data(self, table_name: str, source_row: int) -> dict | None:
        """Get record data as dictionary"""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position
            """,
                [table_name],
            )
            columns = [row[0] for row in cursor.fetchall()]

            if not columns:
                return None

            columns_str = ", ".join(columns)
            cursor.execute(
                f"""
                SELECT {columns_str}
                FROM {table_name}
                WHERE _row_number = %s
                LIMIT 1
            """,
                [source_row],
            )

            record = cursor.fetchone()
            if not record:
                return None

            return dict(zip(columns, record, strict=False))

    def _show_stage_comparison(self, stages: list[int], stage_data: dict, options: dict):
        """Show side-by-side stage comparison"""
        stage_names = {
            1: "Raw Import",
            2: "Data Profiling",
            3: "Data Cleaning",
            4: "Validation",
            5: "Transformation",
            6: "Record Splitting",
        }

        # Find common columns across stages
        all_columns = set()
        for data in stage_data.values():
            if data:
                all_columns.update(data.keys())

        # Show header
        header_parts = [f"Stage {stage} ({stage_names.get(stage, 'Unknown')})" for stage in stages]
        self.stdout.write(f"   {' | '.join(header_parts)}")
        self.stdout.write(f"   {' | '.join(['─' * len(part) for part in header_parts])}")

        # Show data for each column
        for column in sorted(all_columns):
            if column.startswith("_") and not options["show_all_columns"]:
                continue

            values = []
            for stage in stages:
                data = stage_data.get(stage, {})
                if data and column in data:
                    value = self._format_display_value(data[column])
                    if len(value) > 30:
                        value = value[:27] + "..."
                else:
                    value = "—"
                values.append(value)

            self.stdout.write(f"   {column}: {' | '.join(values)}")

    def _export_to_csv(self, table_name: str, records_to_inspect: list[int], options: dict):
        """Export inspection results to CSV"""
        export_file = Path(options["export_csv"])

        self.stdout.write(f"\n📤 Exporting audit report to: {export_file}")

        stage_info = self._get_stage_table_info(table_name)

        # Collect all data
        export_data = []
        for source_row in records_to_inspect:
            row_data = {"source_row": source_row}

            for stage in sorted(stage_info.keys()):
                info = stage_info[stage]
                if isinstance(info, dict) and "table" in info:
                    data = self._get_record_data(info["table"], source_row)
                    if data:
                        for col, val in data.items():
                            row_data[f"stage_{stage}_{col}"] = val
                elif isinstance(info, dict) and "valid" in info:
                    # Stage 4 valid records
                    data = self._get_record_data(info["valid"]["table"], source_row)
                    if data:
                        for col, val in data.items():
                            row_data[f"stage_{stage}_valid_{col}"] = val

                    # Stage 4 invalid records if requested
                    if options["include_invalid"]:
                        data = self._get_record_data(info["invalid"]["table"], source_row)
                        if data:
                            for col, val in data.items():
                                row_data[f"stage_{stage}_invalid_{col}"] = val

            export_data.append(row_data)

        # Write CSV
        if export_data:
            with open(export_file, "w", newline="", encoding="utf-8") as csvfile:
                fieldnames = set()
                for row in export_data:
                    fieldnames.update(row.keys())

                writer = csv.DictWriter(csvfile, fieldnames=sorted(fieldnames))
                writer.writeheader()
                writer.writerows(export_data)

            self.stdout.write(self.style.SUCCESS(f"✅ Exported {len(export_data)} records to {export_file}"))
        else:
            self.stdout.write(self.style.WARNING("⚠️  No data to export"))
