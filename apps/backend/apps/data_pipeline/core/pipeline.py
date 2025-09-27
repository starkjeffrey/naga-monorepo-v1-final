"""
Main Data Pipeline Orchestrator

Coordinates the 6-stage data processing pipeline:
1. Import - Load raw CSV data preserving all original values
2. Profile - Analyze data patterns and quality issues
3. Clean - Standardize formats, parse complex fields, fix encoding
4. Validate - Apply business rules and data quality checks
5. Transform - Apply domain-specific transformations (Limon→Unicode, etc.)
6. Split - Generate multiple output records from single input (headers/lines)
"""

import time
from pathlib import Path

from django.db import transaction

from ..configs.base import PipelineLogger, PipelineResult, TableConfig


class PipelineOrchestrator:
    """Main pipeline coordinator - manages all 6 stages"""

    def __init__(self, config: TableConfig, run_id: int | None = None):
        self.config = config
        self.run_id = run_id
        self.logger = PipelineLogger(config.table_name, run_id)

        # Validate configuration
        config_errors = config.validate()
        if config_errors:
            raise ValueError(f"Configuration errors: {config_errors}")

    def execute(
        self,
        source_file: Path,
        start_stage: int = 1,
        end_stage: int = 6,
        dry_run: bool = False,
    ) -> PipelineResult:
        """
        Execute pipeline stages from start_stage to end_stage.

        Args:
            source_file: Path to CSV file
            start_stage: Stage to start from (1-6)
            end_stage: Stage to end at (1-6)
            dry_run: If True, rollback all changes
        """
        from .stages import (
            Stage1Import,
            Stage2Profile,
            Stage3Clean,
            Stage4Validate,
            Stage5Transform,
            Stage6Split,
        )

        pipeline_start_time = time.time()

        try:
            self.logger.info(
                f"Starting pipeline for {self.config.table_name} (stages {start_stage}-{end_stage}, dry_run={dry_run})"
            )

            result = PipelineResult(table_name=self.config.table_name, stage_completed=0, success=False)

            # Track intermediate results between stages
            stage_outputs = {}

            # Only use atomic transaction for dry runs to enable rollback
            if dry_run:
                transaction_context = transaction.atomic()
            else:
                # Use a dummy context manager for normal runs
                from contextlib import nullcontext

                transaction_context = nullcontext()

            with transaction_context:
                # Stage 1: Import Raw Data
                if start_stage <= 1 <= end_stage:
                    stage1 = Stage1Import(self.config, self.logger)
                    stage_outputs[1] = stage1.execute(source_file, dry_run)
                    result.set_stage_result(1, stage_outputs[1])
                    result.stage_completed = 1
                    result.total_records = stage_outputs[1]["total_rows"]
                    self.logger.info(f"Stage 1 completed: {stage_outputs[1]['total_rows']} rows imported")

                # Stage 2: Profile Data
                if start_stage <= 2 <= end_stage:
                    stage2 = Stage2Profile(self.config, self.logger, self.run_id)
                    stage_outputs[2] = stage2.execute(stage_outputs.get(1, {}), dry_run)
                    result.set_stage_result(2, stage_outputs[2])
                    result.stage_completed = 2
                    self.logger.info(
                        f"Stage 2 completed: {stage_outputs[2]['total_columns_profiled']} columns profiled"
                    )

                # Stage 3: Clean & Parse Data
                if start_stage <= 3 <= end_stage:
                    stage3 = Stage3Clean(self.config, self.logger, self.run_id)
                    stage_outputs[3] = stage3.execute(stage_outputs.get(2, {}), dry_run)
                    result.set_stage_result(3, stage_outputs[3])
                    result.stage_completed = 3
                    self.logger.info(f"Stage 3 completed: {stage_outputs[3]['total_rows_cleaned']} rows cleaned")

                # Stage 4: Validate Data
                if start_stage <= 4 <= end_stage:
                    stage4 = Stage4Validate(self.config, self.logger, self.run_id)
                    stage_outputs[4] = stage4.execute(stage_outputs.get(3, {}), dry_run)
                    result.set_stage_result(4, stage_outputs[4])
                    result.stage_completed = 4
                    result.valid_records = stage_outputs[4]["total_rows_valid"]
                    result.invalid_records = stage_outputs[4]["total_rows_invalid"]
                    self.logger.info(f"Stage 4 completed: {stage_outputs[4]['success_rate_percent']:.1f}% valid")

                # Stage 5: Transform Data
                if start_stage <= 5 <= end_stage:
                    stage5 = Stage5Transform(self.config, self.logger, self.run_id)
                    stage_outputs[5] = stage5.execute(stage_outputs.get(4, {}), dry_run)
                    result.set_stage_result(5, stage_outputs[5])
                    result.stage_completed = 5
                    self.logger.info(
                        f"Stage 5 completed: {stage_outputs[5]['records_transformed']} records transformed"
                    )

                # Stage 6: Split Records (for enrollment data)
                if start_stage <= 6 <= end_stage:
                    if self.config.supports_record_splitting:
                        stage6 = Stage6Split(self.config, self.logger, self.run_id)
                        stage_outputs[6] = stage6.execute(stage_outputs.get(5, {}), dry_run)
                        result.set_stage_result(6, stage_outputs[6])
                        result.stage_completed = 6
                        self.logger.info(
                            f"Stage 6 completed: {stage_outputs[6]['headers_created']} headers, "
                            f"{stage_outputs[6]['lines_created']} lines created"
                        )
                    else:
                        self.logger.info("Stage 6 skipped: record splitting not configured")

                # Calculate final metrics
                result.execution_time = time.time() - pipeline_start_time
                result.success = True

                # Rollback if dry run
                if dry_run:
                    transaction.set_rollback(True)
                    self.logger.info("Dry run completed - no data committed")

            self.logger.info(f"Pipeline completed successfully in {result.execution_time:.2f}s")
            return result

        except Exception as e:
            result.add_error(f"Pipeline failed: {e!s}")
            result.execution_time = time.time() - pipeline_start_time
            self.logger.error(f"Pipeline failed after {result.execution_time:.2f}s: {e!s}")
            raise

    def resume_from_stage(self, stage_number: int, dry_run: bool = False) -> PipelineResult:
        """Resume pipeline from a specific stage using persisted data"""
        # This assumes data from previous stages is already in database
        # You would need to reconstruct the stage_outputs from DB
        pass
