"""
Run Pipeline Management Command

Main command for executing the data pipeline on specified tables.
Supports dry-run, stage-specific execution, and comprehensive error handling.
"""

import sys
import time
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.data_pipeline.core.pipeline import PipelineOrchestrator
from apps.data_pipeline.core.registry import get_registry
from apps.data_pipeline.models import PipelineRun


class Command(BaseCommand):
    help = "Run data pipeline for specified tables"

    def add_arguments(self, parser):
        parser.add_argument(
            "--tables", nargs="+", default=["all"], help="Tables to process (default: all registered tables)"
        )
        parser.add_argument(
            "--stage",
            type=int,
            choices=[1, 2, 3, 4],
            default=4,
            help="Run up to specified stage only (default: all 4 stages)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate configuration and show what would be processed without making changes",
        )
        parser.add_argument(
            "--source-dir",
            type=str,
            default="data/legacy/data_pipeline/inputs",
            help="Directory containing source CSV files",
        )
        parser.add_argument(
            "--continue-on-error", action="store_true", help="Continue processing other tables if one fails"
        )
        parser.add_argument("--chunk-size", type=int, help="Override chunk size for processing (default: from config)")
        parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
        parser.add_argument("--dependency-order", action="store_true", help="Process tables in dependency order")

    def handle(self, *args, **options):
        """Main command handler"""
        start_time = time.time()

        # Set verbosity
        if options["verbose"]:
            self.verbosity = 2

        try:
            # Validate source directory
            source_dir = Path(options["source_dir"])
            if not source_dir.exists():
                raise CommandError(f"Source directory does not exist: {source_dir}")

            # Determine which tables to process
            tables_to_process = self._get_tables_to_process(options)

            if not tables_to_process:
                self.stdout.write(self.style.WARNING("No tables to process"))
                return

            # Show processing plan
            self._show_processing_plan(tables_to_process, options, source_dir)

            if options["dry_run"]:
                self.stdout.write(self.style.WARNING("\n🔍 DRY RUN MODE - No data will be modified\n"))

            # Process each table
            results = {}
            total_success = 0
            total_failed = 0

            for table_name in tables_to_process:
                self.stdout.write(f"\n{'=' * 60}")
                self.stdout.write(f"🔄 Processing table: {table_name}")
                self.stdout.write(f"{'=' * 60}")

                try:
                    result = self._process_table(table_name, options, source_dir)
                    results[table_name] = result

                    if result.success:
                        total_success += 1
                        self.stdout.write(self.style.SUCCESS(f"✅ {table_name} completed successfully"))
                    else:
                        total_failed += 1
                        self.stdout.write(self.style.ERROR(f"❌ {table_name} failed"))

                        if not options["continue_on_error"]:
                            break

                except Exception as e:
                    total_failed += 1
                    error_msg = f"❌ {table_name} failed with error: {e!s}"
                    self.stdout.write(self.style.ERROR(error_msg))
                    results[table_name] = None

                    if not options["continue_on_error"]:
                        raise CommandError(f"Pipeline failed for {table_name}: {e!s}") from e

            # Show final summary
            total_time = time.time() - start_time
            self._show_final_summary(results, total_success, total_failed, total_time, options)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Pipeline execution failed: {e!s}"))
            sys.exit(1)

    def _get_tables_to_process(self, options) -> list:
        """Determine which tables to process based on options"""
        tables = options["tables"]

        if "all" in tables:
            registry = get_registry()
            if options["dependency_order"]:
                return registry.get_pipeline_order()
            else:
                return registry.list_tables()
        else:
            # Validate that all specified tables exist
            registry = get_registry()
            available_tables = registry.list_tables()
            invalid_tables = set(tables) - set(available_tables)

            if invalid_tables:
                raise CommandError(f"Unknown tables: {list(invalid_tables)}. Available: {available_tables}")

            return tables

    def _show_processing_plan(self, tables: list, options: dict, source_dir: Path):
        """Show what will be processed"""
        self.stdout.write("📋 Processing Plan:")
        self.stdout.write(f"   Source directory: {source_dir}")
        self.stdout.write(f"   Max stage: {options.get('stage', 4)}")
        self.stdout.write(f"   Continue on error: {options['continue_on_error']}")
        self.stdout.write(f"   Tables ({len(tables)}):")

        for i, table_name in enumerate(tables, 1):
            try:
                registry = get_registry()
                config = registry.get_config(table_name)
                source_file = source_dir / config.source_file_pattern
                file_status = "✅" if source_file.exists() else "❌"
                columns = len(config.column_mappings)

                self.stdout.write(f"     {i}. {table_name} - {columns} columns - {file_status}")

                if not source_file.exists():
                    self.stdout.write(self.style.WARNING(f"        Missing file: {source_file}"))

            except Exception as e:
                self.stdout.write(f"     {i}. {table_name} - ❌ Config error: {e!s}")

        self.stdout.write("")

    def _process_table(self, table_name: str, options: dict, source_dir: Path):
        """Process a single table through the pipeline"""
        # Get table configuration
        registry = get_registry()
        config = registry.get_config(table_name)

        # Validate source file exists
        source_file = source_dir / config.source_file_pattern
        if not source_file.exists():
            raise FileNotFoundError(f"Source file not found: {source_file}")

        # Override chunk size if specified
        if options.get("chunk_size"):
            config.chunk_size = options["chunk_size"]

        # Create pipeline run record
        run = None
        if not options["dry_run"]:
            run = PipelineRun.objects.create(
                table_name=table_name,
                stage=1,
                status="running",
                source_file=str(source_file),
                source_file_size=source_file.stat().st_size,
                config_snapshot=self._serialize_config(config),
            )

            self.stdout.write(f"📝 Created pipeline run: #{run.id}")

        try:
            # Initialize and run pipeline
            pipeline = PipelineOrchestrator(config, run_id=run.id if run else None)

            max_stage = options.get("stage", 4)

            # Show stage progress
            self.stdout.write(f"🚀 Executing stages 1-{max_stage}")

            # Execute pipeline
            result = pipeline.execute(source_file=source_file, end_stage=max_stage, dry_run=options["dry_run"])

            # Update run record if not dry run
            if run and not options["dry_run"]:
                run.stage = result.stage_completed
                run.records_processed = result.total_records
                run.records_valid = result.valid_records
                run.records_invalid = result.invalid_records
                run.mark_completed()

            # Show results
            self._show_table_results(table_name, result, options["verbose"])

            return result

        except Exception as e:
            if run:
                run.mark_failed(str(e))
            raise

    def _serialize_config(self, config) -> dict:
        """Serialize configuration for audit trail"""
        return {
            "table_name": config.table_name,
            "source_file_pattern": config.source_file_pattern,
            "column_count": len(config.column_mappings),
            "cleaning_rules_count": len(config.cleaning_rules),
            "validator_class": config.validator_class.__name__ if config.validator_class else None,
            "chunk_size": config.chunk_size,
            "min_completeness_score": config.min_completeness_score,
            "min_consistency_score": config.min_consistency_score,
            "max_error_rate": config.max_error_rate,
        }

    def _show_table_results(self, table_name: str, result, verbose: bool):
        """Show results for a single table"""
        self.stdout.write(f"\n📊 Results for {table_name}:")
        self.stdout.write(f"   Stage completed: {result.stage_completed}/4")
        self.stdout.write(f"   Execution time: {result.execution_time:.2f}s")
        self.stdout.write(f"   Total records: {result.total_records:,}")

        if result.stage_completed >= 2:
            self.stdout.write(f"   Completeness score: {result.completeness_score:.1f}%")
            self.stdout.write(f"   Consistency score: {result.consistency_score:.1f}%")

        if result.stage_completed >= 4:
            self.stdout.write(f"   Valid records: {result.valid_records:,}")
            self.stdout.write(f"   Invalid records: {result.invalid_records:,}")
            self.stdout.write(f"   Success rate: {100 - result.error_rate:.1f}%")

        # Show warnings
        if result.warnings:
            self.stdout.write("⚠️  Warnings:")
            for warning in result.warnings:
                self.stdout.write(f"     • {warning}")

        # Show errors
        if result.errors:
            self.stdout.write("❌ Errors:")
            for error in result.errors:
                self.stdout.write(f"     • {error}")

        # Verbose output
        if verbose and result.stage_results:
            for stage_num, stage_result in result.stage_results.items():
                self._show_stage_details(stage_num, stage_result)

    def _show_stage_details(self, stage_num: int, stage_result: dict):
        """Show detailed results for a specific stage"""
        stage_names = {1: "Raw Import", 2: "Data Profiling", 3: "Data Cleaning", 4: "Validation"}

        self.stdout.write(f"\n   📋 Stage {stage_num} - {stage_names.get(stage_num, 'Unknown')}:")

        if stage_num == 1:
            self.stdout.write(f"      Encoding: {stage_result.get('encoding_detected', 'unknown')}")
            self.stdout.write(f"      Columns: {stage_result.get('data_columns', 0)}")
            issues = stage_result.get("detected_issues", [])
            if issues:
                self.stdout.write(f"      Issues detected: {len(issues)}")

        elif stage_num == 2:
            quality = stage_result.get("quality_summary", {})
            self.stdout.write(f"      Columns profiled: {stage_result.get('total_columns_profiled', 0)}")
            self.stdout.write(f"      Encoding issues: {quality.get('encoding_issues_count', 0)}")
            self.stdout.write(f"      NULL pattern issues: {quality.get('multiple_null_patterns_count', 0)}")

        elif stage_num == 3:
            improvements = stage_result.get("quality_improvements", {})
            self.stdout.write(f"      Rows cleaned: {stage_result.get('total_rows_cleaned', 0):,}")
            self.stdout.write(f"      NULL standardizations: {improvements.get('null_standardizations', 0)}")
            self.stdout.write(f"      Encoding fixes: {improvements.get('encoding_fixes', 0)}")

        elif stage_num == 4:
            self.stdout.write(f"      Validation errors: {stage_result.get('total_validation_errors', 0):,}")
            error_summary = stage_result.get("error_summary", {})
            if error_summary.get("most_common_error"):
                self.stdout.write(f"      Most common error: {error_summary['most_common_error']}")

    def _show_final_summary(
        self, results: dict, success_count: int, failed_count: int, total_time: float, options: dict
    ):
        """Show final execution summary"""
        self.stdout.write(f"\n{'=' * 60}")
        self.stdout.write("🎯 PIPELINE EXECUTION SUMMARY")
        self.stdout.write(f"{'=' * 60}")

        self.stdout.write(f"Total execution time: {total_time:.2f}s")
        self.stdout.write(f"Tables processed: {len(results)}")
        self.stdout.write(f"Successful: {success_count}")
        self.stdout.write(f"Failed: {failed_count}")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN - No data was modified"))

        # Show per-table summary
        if results:
            self.stdout.write("\n📊 Per-table summary:")
            for table_name, result in results.items():
                if result:
                    status = "✅" if result.success else "❌"
                    records = f"{result.total_records:,}" if result.total_records else "0"
                    time_taken = f"{result.execution_time:.1f}s" if result.execution_time else "0s"
                    self.stdout.write(f"   {status} {table_name:<20} {records:>10} records  {time_taken:>8}")
                else:
                    self.stdout.write(f"   ❌ {table_name:<20} {'ERROR':>10}          {'N/A':>8}")

        # Final status
        if failed_count == 0:
            self.stdout.write(self.style.SUCCESS("\n🎉 All tables processed successfully!"))
        elif success_count > 0:
            self.stdout.write(self.style.WARNING(f"\n⚠️  {success_count} successful, {failed_count} failed"))
        else:
            self.stdout.write(self.style.ERROR(f"\n💥 All {failed_count} tables failed"))

        self.stdout.write("")
