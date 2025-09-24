"""
Test Pipeline Execution

Tests for the 4-stage data pipeline including stage execution,
error handling, and end-to-end integration.
"""

import csv
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from django.test import TestCase

from data_pipeline.cleaners.engine import CleaningEngine
from data_pipeline.configs.base import ColumnMapping, TableConfig
from data_pipeline.core.pipeline import DataPipeline, PipelineResult
from data_pipeline.core.stages import Stage1RawImport, Stage2DataProfiling
from data_pipeline.models import PipelineRun
from data_pipeline.validators.terms import TermValidator


class TestPipelineStages(TestCase):
    """Test individual pipeline stages"""

    def setUp(self):
        """Set up test data and configuration"""
        self.test_config = TableConfig(
            table_name="test_table",
            source_file_pattern="test.csv",
            column_mappings=[
                ColumnMapping(
                    source_name="ID",
                    target_name="id",
                    data_type="nvarchar(10)",
                    nullable=False,
                    cleaning_rules=["trim", "uppercase"],
                ),
                ColumnMapping(
                    source_name="Name",
                    target_name="name",
                    data_type="nvarchar(100)",
                    nullable=True,
                    cleaning_rules=["trim", "fix_encoding"],
                ),
                ColumnMapping(
                    source_name="Date",
                    target_name="date_field",
                    data_type="datetime(23, 3)",
                    nullable=True,
                    cleaning_rules=["parse_mssql_datetime"],
                ),
            ],
            chunk_size=100,
        )

        # Create temporary test CSV file
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "test.csv"

        # Sample test data with various data quality issues
        test_data = [
            ["ID", "Name", "Date"],
            ["  st001  ", "John Doe", "Jan 15 2020 12:00AM"],
            ["ST002", "  Mary Smith  ", "Feb 20 2020 12:00AM"],
            ["", "Invalid User", "Invalid Date"],  # Missing ID
            ["ST003", "", "Mar 10 2020 12:00AM"],  # Missing name
            ["st004", "Test User", ""],  # Missing date
            ["ST005", "Unicode Tëst", "Apr 1 2020 12:00AM"],  # Unicode
            ["DUPLICATE", "First Instance", "May 1 2020 12:00AM"],
            ["DUPLICATE", "Second Instance", "May 2 2020 12:00AM"],  # Duplicate ID
        ]

        with open(self.test_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(test_data)

    def test_stage1_raw_import(self):
        """Test Stage 1 - Raw Import"""
        stage1 = Stage1RawImport(self.test_config)

        # Test execution
        result = stage1.execute(self.test_file, dry_run=True)

        # Verify results
        self.assertTrue(result["success"])
        self.assertEqual(result["stage"], 1)
        self.assertGreater(result["total_records"], 0)
        self.assertIn("encoding_detected", result)
        self.assertIn("data_columns", result)

        # Should detect 3 columns
        self.assertEqual(result["data_columns"], 3)

        # Should detect UTF-8 encoding
        self.assertEqual(result["encoding_detected"], "utf-8")

    def test_stage2_data_profiling(self):
        """Test Stage 2 - Data Profiling"""
        stage2 = Stage2DataProfiling(self.test_config)

        # Mock Stage 1 completion (raw data exists)
        with patch.object(stage2, "_load_raw_data") as mock_load:
            mock_load.return_value = [
                {"id": "  st001  ", "name": "John Doe", "date_field": "Jan 15 2020 12:00AM"},
                {"id": "ST002", "name": "  Mary Smith  ", "date_field": "Feb 20 2020 12:00AM"},
                {"id": "", "name": "Invalid User", "date_field": "Invalid Date"},
                {"id": "ST003", "name": "", "date_field": "Mar 10 2020 12:00AM"},
            ]

            result = stage2.execute(dry_run=True)

            # Verify profiling results
            self.assertTrue(result["success"])
            self.assertEqual(result["stage"], 2)
            self.assertIn("total_columns_profiled", result)
            self.assertIn("quality_summary", result)

            # Should profile 3 columns
            self.assertEqual(result["total_columns_profiled"], 3)

            # Quality summary should contain key metrics
            quality = result["quality_summary"]
            self.assertIn("completeness_score", quality)
            self.assertIn("consistency_score", quality)

    def test_cleaning_engine(self):
        """Test data cleaning engine"""
        engine = CleaningEngine(self.test_config)

        # Test individual cleaning rules
        test_cases = [
            ("trim", "  test  ", "test"),
            ("uppercase", "test", "TEST"),
            ("lowercase", "TEST", "test"),
            ("null_standardize", "NULL", None),
            ("null_standardize", "", None),
            ("null_standardize", " ", None),
        ]

        for rule, input_val, expected in test_cases:
            result = engine.apply_cleaning_rules("test_col", input_val, [rule])
            self.assertEqual(result, expected, f"Rule {rule} failed: {input_val} -> {result} != {expected}")

    def test_date_parsing(self):
        """Test MSSQL datetime parsing"""
        engine = CleaningEngine(self.test_config)

        test_dates = [
            ("Jan 15 2020 12:00AM", datetime(2020, 1, 15, 0, 0)),
            ("Feb 29 2020 11:59PM", datetime(2020, 2, 29, 23, 59)),
            ("Invalid Date", None),
            ("", None),
            ("NULL", None),
        ]

        for input_date, expected in test_dates:
            result = engine.apply_cleaning_rules("date_field", input_date, ["parse_mssql_datetime"])
            if expected is None:
                self.assertIsNone(result, f"Expected None for '{input_date}', got {result}")
            else:
                self.assertEqual(result, expected, f"Date parsing failed: {input_date} -> {result}")


class TestPipelineExecution(TestCase):
    """Test complete pipeline execution"""

    def setUp(self):
        """Set up test pipeline"""
        self.test_config = TableConfig(
            table_name="pipeline_test",
            source_file_pattern="pipeline_test.csv",
            column_mappings=[
                ColumnMapping(
                    source_name="TermID",
                    target_name="term_id",
                    data_type="nvarchar(200)",
                    nullable=False,
                    cleaning_rules=["trim", "uppercase"],
                ),
                ColumnMapping(
                    source_name="TermName",
                    target_name="term_name",
                    data_type="nvarchar(50)",
                    nullable=False,
                    cleaning_rules=["trim"],
                ),
            ],
            validator_class=TermValidator,
            chunk_size=50,
        )

        # Create test data file
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = Path(self.temp_dir) / "pipeline_test.csv"

        test_data = [
            ["TermID", "TermName"],
            ["  2020t1e  ", "Term 1 (Spring 2020)"],
            ["2020T2E", "  Term 2 (Summer 2020)  "],
            ["2021T1E", "Term 1 (Spring 2021)"],
            ["", "Invalid Term"],  # Missing ID - should fail validation
            ["2021T2E", "Term 2 (Summer 2021)"],
        ]

        with open(self.test_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(test_data)

    def test_pipeline_initialization(self):
        """Test pipeline initialization"""
        pipeline = DataPipeline(self.test_config)

        self.assertEqual(pipeline.config, self.test_config)
        self.assertIsNone(pipeline.run_id)

        # Test with run_id
        pipeline_with_run = DataPipeline(self.test_config, run_id=123)
        self.assertEqual(pipeline_with_run.run_id, 123)

    def test_dry_run_execution(self):
        """Test pipeline dry run (no database changes)"""
        pipeline = DataPipeline(self.test_config)

        result = pipeline.run(
            source_file=self.test_file,
            max_stage=2,  # Only run first 2 stages
            dry_run=True,
        )

        # Verify result structure
        self.assertIsInstance(result, PipelineResult)
        self.assertTrue(result.success)
        self.assertEqual(result.stage_completed, 2)
        self.assertGreater(result.total_records, 0)
        self.assertGreater(result.execution_time, 0)

        # Should have stage results
        self.assertIn(1, result.stage_results)
        self.assertIn(2, result.stage_results)

    @patch("data_pipeline.models.PipelineRun.objects.get")
    def test_pipeline_with_run_tracking(self, mock_get):
        """Test pipeline execution with run tracking"""
        # Mock pipeline run
        mock_run = Mock(spec=PipelineRun)
        mock_run.id = 1
        mock_run.update_stage.return_value = None
        mock_get.return_value = mock_run

        pipeline = DataPipeline(self.test_config, run_id=1)

        # Test stage update
        pipeline._update_run_stage(2, {"test": "data"})
        mock_run.update_stage.assert_called_once_with(2, {"test": "data"})

    def test_pipeline_error_handling(self):
        """Test pipeline error handling"""
        # Create invalid file path
        invalid_file = Path(self.temp_dir) / "nonexistent.csv"

        pipeline = DataPipeline(self.test_config)

        result = pipeline.run(source_file=invalid_file, dry_run=True)

        # Should fail gracefully
        self.assertFalse(result.success)
        self.assertGreater(len(result.errors), 0)
        self.assertEqual(result.stage_completed, 0)  # No stages completed


class TestValidationIntegration(TestCase):
    """Test Pydantic validation integration"""

    def test_terms_validator_integration(self):
        """Test terms validator with realistic data"""
        # Valid term data
        valid_data = {
            "term_id": "2020T1E",
            "term_name": "Term 1 (Spring 2020)",
            "start_date": datetime(2020, 1, 15),
            "end_date": datetime(2020, 5, 15),
            "payment_period": "21",
            "school_year": 2020,
        }

        # Should validate successfully
        validator = TermValidator(**valid_data)
        self.assertEqual(validator.term_id, "2020T1E")
        self.assertEqual(validator.school_year, 2020)

        quality_score = validator.get_quality_score()
        self.assertGreater(quality_score, 0.8)  # Should be high quality

    def test_terms_validator_error_cases(self):
        """Test terms validator error handling"""
        # Invalid term data
        invalid_cases = [
            # Missing required field
            {"term_name": "Test Term"},
            # Invalid date range
            {
                "term_id": "2020T1E",
                "term_name": "Test Term",
                "start_date": datetime(2020, 5, 15),
                "end_date": datetime(2020, 1, 15),  # End before start
                "payment_period": "21",
            },
            # Invalid payment period
            {
                "term_id": "2020T1E",
                "term_name": "Test Term",
                "payment_period": "invalid",  # Not a number
            },
        ]

        for invalid_data in invalid_cases:
            with self.assertRaises(Exception):  # Should raise validation error
                TermValidator(**invalid_data)

    def test_validation_quality_scoring(self):
        """Test validation quality scoring"""
        # Minimal data - should have lower score
        minimal_data = {"term_id": "2020T1E", "term_name": "Test", "payment_period": "21"}

        minimal_validator = TermValidator(**minimal_data)
        minimal_score = minimal_validator.get_quality_score()

        # Rich data - should have higher score
        rich_data = {
            "term_id": "2020T1E",
            "term_name": "Term 1 (Spring 2020)",
            "start_date": datetime(2020, 1, 15),
            "end_date": datetime(2020, 5, 15),
            "payment_period": "21",
            "school_year": 2020,
            "term_type": "ENG A",
            "description": "Spring semester 2020",
        }

        rich_validator = TermValidator(**rich_data)
        rich_score = rich_validator.get_quality_score()

        # Rich data should have higher quality score
        self.assertGreater(rich_score, minimal_score)


class TestPipelineResult(TestCase):
    """Test PipelineResult functionality"""

    def test_pipeline_result_creation(self):
        """Test PipelineResult creation and properties"""
        result = PipelineResult(
            success=True,
            stage_completed=4,
            total_records=1000,
            valid_records=950,
            invalid_records=50,
            execution_time=45.5,
            completeness_score=95.0,
            consistency_score=90.0,
            error_rate=5.0,
        )

        self.assertTrue(result.success)
        self.assertEqual(result.stage_completed, 4)
        self.assertEqual(result.total_records, 1000)
        self.assertEqual(result.error_rate, 5.0)

    def test_pipeline_result_calculations(self):
        """Test calculated properties"""
        result = PipelineResult(success=True, total_records=100, valid_records=85, invalid_records=15)

        # Error rate should be calculated correctly
        expected_error_rate = (15 / 100) * 100
        self.assertEqual(result.error_rate, expected_error_rate)


if __name__ == "__main__":
    pytest.main([__file__])
