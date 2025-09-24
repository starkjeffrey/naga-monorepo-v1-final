"""
Test Data Pipeline Models

Tests for Django models including PipelineRun, DataProfile, ValidationError, etc.
"""

import pytest
from django.test import TestCase

from data_pipeline.models import (
    CleaningRule,
    DataProfile,
    PipelineRun,
    ProcessingStatistics,
)
from data_pipeline.models import (
    ValidationError as ValidationErrorModel,
)


class TestPipelineRun(TestCase):
    """Test PipelineRun model"""

    def test_pipeline_run_creation(self):
        """Test basic pipeline run creation"""
        run = PipelineRun.objects.create(
            table_name="test_table",
            stage=1,
            status="running",
            source_file="/path/to/test.csv",
            source_file_size=1024,
            config_snapshot={"test": "config"},
        )

        self.assertEqual(run.table_name, "test_table")
        self.assertEqual(run.stage, 1)
        self.assertEqual(run.status, "running")
        self.assertIsNotNone(run.started_at)
        self.assertIsNone(run.completed_at)

    def test_pipeline_run_completion(self):
        """Test marking pipeline run as completed"""
        run = PipelineRun.objects.create(
            table_name="test_table", stage=1, status="running", source_file="/path/to/test.csv"
        )

        # Mark as completed
        run.mark_completed()

        self.assertEqual(run.status, "completed")
        self.assertIsNotNone(run.completed_at)

        # Execution time should be calculated
        execution_time = run.get_execution_time()
        self.assertIsNotNone(execution_time)
        self.assertGreaterEqual(execution_time, 0)

    def test_pipeline_run_failure(self):
        """Test marking pipeline run as failed"""
        run = PipelineRun.objects.create(
            table_name="test_table", stage=1, status="running", source_file="/path/to/test.csv"
        )

        # Mark as failed
        error_message = "Test error occurred"
        run.mark_failed(error_message)

        self.assertEqual(run.status, "failed")
        self.assertEqual(run.error_message, error_message)
        self.assertIsNotNone(run.completed_at)

    def test_pipeline_run_stage_update(self):
        """Test updating pipeline run stage"""
        run = PipelineRun.objects.create(
            table_name="test_table", stage=1, status="running", source_file="/path/to/test.csv"
        )

        # Update stage
        stage_data = {"records_processed": 100, "encoding": "utf-8"}
        run.update_stage(2, stage_data)

        self.assertEqual(run.stage, 2)
        # Stage data should be stored somewhere (implementation dependent)

    def test_pipeline_run_str_representation(self):
        """Test string representation"""
        run = PipelineRun.objects.create(
            table_name="test_table", stage=1, status="running", source_file="/path/to/test.csv"
        )

        str_repr = str(run)
        self.assertIn("test_table", str_repr)
        self.assertIn(str(run.id), str_repr)


class TestDataProfile(TestCase):
    """Test DataProfile model"""

    def setUp(self):
        """Set up test data"""
        self.pipeline_run = PipelineRun.objects.create(
            table_name="test_table", stage=2, status="running", source_file="/path/to/test.csv"
        )

    def test_data_profile_creation(self):
        """Test data profile creation"""
        profile = DataProfile.objects.create(
            pipeline_run=self.pipeline_run,
            column_name="test_column",
            data_type="string",
            total_count=1000,
            null_count=50,
            unique_count=800,
            min_length=1,
            max_length=50,
            avg_length=15.5,
            sample_values=["sample1", "sample2", "sample3"],
        )

        self.assertEqual(profile.column_name, "test_column")
        self.assertEqual(profile.data_type, "string")
        self.assertEqual(profile.total_count, 1000)
        self.assertEqual(profile.null_count, 50)

    def test_data_profile_completeness_calculation(self):
        """Test completeness percentage calculation"""
        profile = DataProfile.objects.create(
            pipeline_run=self.pipeline_run,
            column_name="test_column",
            data_type="string",
            total_count=100,
            null_count=20,
            unique_count=80,
        )

        completeness = profile.get_completeness_percentage()
        self.assertEqual(completeness, 80.0)  # (100-20)/100 * 100

    def test_data_profile_uniqueness_calculation(self):
        """Test uniqueness percentage calculation"""
        profile = DataProfile.objects.create(
            pipeline_run=self.pipeline_run,
            column_name="test_column",
            data_type="string",
            total_count=100,
            null_count=0,
            unique_count=75,
        )

        uniqueness = profile.get_uniqueness_percentage()
        self.assertEqual(uniqueness, 75.0)  # 75/100 * 100

    def test_data_profile_sample_values_json(self):
        """Test sample values JSON handling"""
        sample_data = ["value1", "value2", "value3"]
        profile = DataProfile.objects.create(
            pipeline_run=self.pipeline_run,
            column_name="test_column",
            data_type="string",
            total_count=100,
            sample_values=sample_data,
        )

        # Should handle JSON serialization/deserialization
        retrieved_profile = DataProfile.objects.get(id=profile.id)
        self.assertEqual(retrieved_profile.sample_values, sample_data)


class TestValidationError(TestCase):
    """Test ValidationError model"""

    def setUp(self):
        """Set up test data"""
        self.pipeline_run = PipelineRun.objects.create(
            table_name="test_table", stage=4, status="running", source_file="/path/to/test.csv"
        )

    def test_validation_error_creation(self):
        """Test validation error creation"""
        error = ValidationErrorModel.objects.create(
            pipeline_run=self.pipeline_run,
            record_id="TEST001",
            column_name="test_column",
            error_type="format_error",
            severity="high",
            error_message="Invalid format detected",
            invalid_value="bad_value",
            suggested_fix="Use format: YYYY-MM-DD",
        )

        self.assertEqual(error.record_id, "TEST001")
        self.assertEqual(error.column_name, "test_column")
        self.assertEqual(error.error_type, "format_error")
        self.assertEqual(error.severity, "high")

    def test_validation_error_severity_choices(self):
        """Test severity choices validation"""
        # Valid severity
        error = ValidationErrorModel.objects.create(
            pipeline_run=self.pipeline_run,
            record_id="TEST001",
            column_name="test_column",
            error_type="test_error",
            severity="medium",
            error_message="Test error",
        )

        self.assertEqual(error.severity, "medium")

        # Invalid severity should be handled by Django validation
        # (This test would depend on how the choices are implemented)

    def test_validation_error_grouping(self):
        """Test error grouping and counting"""
        # Create multiple errors of same type
        for i in range(5):
            ValidationErrorModel.objects.create(
                pipeline_run=self.pipeline_run,
                record_id=f"TEST{i:03d}",
                column_name="test_column",
                error_type="format_error",
                severity="medium",
                error_message="Invalid format detected",
            )

        # Should be able to count errors by type
        format_errors = ValidationErrorModel.objects.filter(
            pipeline_run=self.pipeline_run, error_type="format_error"
        ).count()

        self.assertEqual(format_errors, 5)


class TestCleaningRule(TestCase):
    """Test CleaningRule model"""

    def test_cleaning_rule_creation(self):
        """Test cleaning rule creation"""
        rule = CleaningRule.objects.create(
            name="trim_whitespace",
            description="Remove leading and trailing whitespace",
            rule_type="transformation",
            pattern=r"^\s+|\s+$",
            replacement="",
            priority=1,
            is_active=True,
        )

        self.assertEqual(rule.name, "trim_whitespace")
        self.assertEqual(rule.rule_type, "transformation")
        self.assertTrue(rule.is_active)
        self.assertEqual(rule.priority, 1)

    def test_cleaning_rule_application_tracking(self):
        """Test tracking rule applications"""
        rule = CleaningRule.objects.create(
            name="test_rule",
            description="Test rule",
            rule_type="validation",
            is_active=True,
            applications_count=0,
            success_count=0,
        )

        # Simulate rule application
        rule.applications_count = 10
        rule.success_count = 8
        rule.save()

        # Calculate success rate
        success_rate = (rule.success_count / rule.applications_count) * 100
        self.assertEqual(success_rate, 80.0)

    def test_cleaning_rule_ordering(self):
        """Test rule priority ordering"""
        CleaningRule.objects.create(
            name="rule1", description="First rule", rule_type="transformation", priority=2, is_active=True
        )

        rule2 = CleaningRule.objects.create(
            name="rule2", description="Second rule", rule_type="transformation", priority=1, is_active=True
        )

        # Rules should be ordered by priority
        rules = CleaningRule.objects.filter(is_active=True).order_by("priority")
        self.assertEqual(rules.first(), rule2)  # Priority 1 comes first


class TestProcessingStatistics(TestCase):
    """Test ProcessingStatistics model"""

    def setUp(self):
        """Set up test data"""
        self.pipeline_run = PipelineRun.objects.create(
            table_name="test_table", stage=4, status="completed", source_file="/path/to/test.csv"
        )

    def test_processing_statistics_creation(self):
        """Test statistics creation"""
        stat = ProcessingStatistics.objects.create(
            pipeline_run=self.pipeline_run,
            metric_name="records_processed",
            metric_value=1000.0,
            category="performance",
            description="Total records processed in pipeline",
        )

        self.assertEqual(stat.metric_name, "records_processed")
        self.assertEqual(stat.metric_value, 1000.0)
        self.assertEqual(stat.category, "performance")

    def test_processing_statistics_metadata(self):
        """Test metadata JSON field"""
        metadata = {"stage": 2, "processing_time": 45.5, "memory_usage": "128MB"}

        stat = ProcessingStatistics.objects.create(
            pipeline_run=self.pipeline_run,
            metric_name="stage_performance",
            metric_value=45.5,
            category="performance",
            metadata=metadata,
        )

        # Should handle JSON serialization
        retrieved_stat = ProcessingStatistics.objects.get(id=stat.id)
        self.assertEqual(retrieved_stat.metadata, metadata)

    def test_processing_statistics_aggregation(self):
        """Test statistics aggregation"""
        # Create multiple statistics
        stats_data = [
            ("records_processed", 1000, "volume"),
            ("records_valid", 950, "quality"),
            ("records_invalid", 50, "quality"),
            ("execution_time", 60.5, "performance"),
        ]

        for metric_name, value, category in stats_data:
            ProcessingStatistics.objects.create(
                pipeline_run=self.pipeline_run, metric_name=metric_name, metric_value=float(value), category=category
            )

        # Should be able to aggregate by category
        quality_stats = ProcessingStatistics.objects.filter(pipeline_run=self.pipeline_run, category="quality")

        self.assertEqual(quality_stats.count(), 2)

        # Should be able to calculate totals
        total_records = sum(
            stat.metric_value for stat in quality_stats if stat.metric_name in ["records_valid", "records_invalid"]
        )

        self.assertEqual(total_records, 1000.0)


if __name__ == "__main__":
    pytest.main([__file__])
