"""
Data Pipeline Models

Models for tracking pipeline execution, data profiling results, and validation errors.
Provides complete audit trail and monitoring capabilities.
"""

from datetime import timedelta
from typing import ClassVar

from django.db import models
from django.db.models import JSONField
from django.utils import timezone


class PipelineRun(models.Model):
    """Track pipeline execution with complete audit trail"""

    STAGE_CHOICES: ClassVar[list[tuple[int, str]]] = [
        (1, "Raw Import"),
        (2, "Data Profiling"),
        (3, "Data Cleaning"),
        (4, "Validation"),
    ]

    STATUS_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("pending", "Pending"),
        ("running", "Running"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    # Basic run information
    table_name: models.CharField = models.CharField(max_length=100, help_text="Name of the table being processed")
    stage: models.IntegerField = models.IntegerField(choices=STAGE_CHOICES, help_text="Current/final pipeline stage")
    status: models.CharField = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")

    # Timing information
    started_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    completed_at: models.DateTimeField = models.DateTimeField(null=True, blank=True)

    # Source file information
    source_file: models.CharField = models.CharField(max_length=500, help_text="Path to source CSV file")
    source_file_size: models.BigIntegerField = models.BigIntegerField(
        null=True, blank=True, help_text="File size in bytes"
    )
    source_encoding: models.CharField = models.CharField(
        max_length=50, null=True, blank=True, help_text="Detected file encoding"
    )

    # Processing statistics
    records_processed: models.IntegerField = models.IntegerField(default=0, help_text="Total records processed")
    records_valid: models.IntegerField = models.IntegerField(default=0, help_text="Records passing validation")
    records_invalid: models.IntegerField = models.IntegerField(default=0, help_text="Records failing validation")

    # Error tracking
    error_log: JSONField = JSONField(default=dict, blank=True, help_text="Detailed error information")
    warnings: JSONField = JSONField(default=list, blank=True, help_text="Non-fatal warnings during processing")

    # Configuration snapshot
    config_snapshot: JSONField = JSONField(default=dict, blank=True, help_text="Configuration used for this run")

    class Meta:
        ordering = ["-started_at"]
        indexes = [
            models.Index(fields=["table_name", "status"]),
            models.Index(fields=["started_at"]),
        ]

    def __str__(self):
        return f"{self.table_name} - Stage {self.stage} - {self.status}"

    @property
    def duration(self) -> timedelta | None:
        """Calculate execution duration"""
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        elif self.status == "running":
            return timezone.now() - self.started_at
        return None

    @property
    def success_rate(self) -> float:
        """Calculate validation success rate as percentage"""
        if self.records_processed > 0:
            return (self.records_valid / self.records_processed) * 100
        return 0.0

    def mark_completed(self) -> None:
        """Mark run as completed"""
        self.status = "completed"
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])

    def mark_failed(self, error_message: str | None = None) -> None:
        """Mark run as failed with optional error message"""
        self.status = "failed"
        self.completed_at = timezone.now()
        if error_message:
            self.error_log = {"error": error_message, "timestamp": timezone.now().isoformat()}
        self.save(update_fields=["status", "completed_at", "error_log"])


class DataProfile(models.Model):
    """Store profiling results from Stage 2 to inform cleaning decisions"""

    pipeline_run: models.ForeignKey = models.ForeignKey(PipelineRun, on_delete=models.CASCADE, related_name="profiles")
    table_name: models.CharField = models.CharField(max_length=100, help_text="Source table name")
    column_name: models.CharField = models.CharField(max_length=100, help_text="Column being profiled")

    # Basic statistics
    total_rows: models.IntegerField = models.IntegerField(help_text="Total number of rows")
    null_count: models.IntegerField = models.IntegerField(help_text="Number of NULL/empty values")
    unique_count: models.IntegerField = models.IntegerField(help_text="Number of unique values")

    # Value analysis
    min_value: models.TextField = models.TextField(null=True, blank=True, help_text="Minimum value found")
    max_value: models.TextField = models.TextField(null=True, blank=True, help_text="Maximum value found")
    avg_length: models.FloatField = models.FloatField(null=True, blank=True, help_text="Average string length")

    # Pattern analysis
    common_values: JSONField = JSONField(default=list, help_text="Most common values with frequencies")
    null_patterns: JSONField = JSONField(default=list, help_text="Different NULL representations found")
    detected_type: models.CharField = models.CharField(max_length=50, help_text="Probable data type")

    # Quality metrics
    completeness_score: models.FloatField = models.FloatField(
        null=True, blank=True, help_text="Data completeness (0-100)"
    )
    consistency_score: models.FloatField = models.FloatField(
        null=True, blank=True, help_text="Data consistency (0-100)"
    )

    # Special pattern flags
    has_encoding_issues: models.BooleanField = models.BooleanField(
        default=False, help_text="Contains encoding problems"
    )
    has_date_patterns: models.BooleanField = models.BooleanField(
        default=False, help_text="Contains date-like patterns"
    )
    has_numeric_patterns: models.BooleanField = models.BooleanField(
        default=False, help_text="Contains numeric patterns"
    )

    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "data_pipeline_dataprofile"
        unique_together = [["pipeline_run", "column_name"]]
        indexes = [
            models.Index(fields=["table_name", "column_name"]),
            models.Index(fields=["detected_type"]),
        ]

    def __str__(self):
        return f"{self.table_name}.{self.column_name} - {self.detected_type}"

    @property
    def null_percentage(self) -> float:
        """Calculate null percentage"""
        if self.total_rows > 0:
            return (self.null_count / self.total_rows) * 100
        return 0.0


class ValidationError(models.Model):
    """Track validation errors from Stage 4 for analysis and correction"""

    ERROR_TYPE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("required_field", "Required Field Missing"),
        ("data_type", "Data Type Mismatch"),
        ("format_error", "Format Validation Failed"),
        ("range_error", "Value Out of Range"),
        ("pattern_error", "Pattern Validation Failed"),
        ("business_rule", "Business Rule Violation"),
        ("foreign_key", "Foreign Key Constraint"),
        ("unique_constraint", "Unique Constraint Violation"),
    ]

    pipeline_run: models.ForeignKey = models.ForeignKey(
        PipelineRun, on_delete=models.CASCADE, related_name="validation_errors"
    )

    # Error location
    row_number: models.IntegerField = models.IntegerField(help_text="Row number in source data")
    column_name: models.CharField = models.CharField(max_length=100, help_text="Column where error occurred")

    # Error details
    error_type: models.CharField = models.CharField(max_length=100, choices=ERROR_TYPE_CHOICES)
    error_message: models.TextField = models.TextField(help_text="Detailed error description")
    raw_value: models.TextField = models.TextField(help_text="Original value that caused error")
    expected_format: models.CharField = models.CharField(
        max_length=200, null=True, blank=True, help_text="Expected format/pattern"
    )

    # Context information
    validation_rule: models.CharField = models.CharField(
        max_length=200, null=True, blank=True, help_text="Validation rule that failed"
    )
    suggested_fix: models.TextField = models.TextField(null=True, blank=True, help_text="Suggested correction")

    # Processing flags
    is_critical: models.BooleanField = models.BooleanField(
        default=False, help_text="Critical error preventing processing"
    )
    is_correctable: models.BooleanField = models.BooleanField(
        default=True, help_text="Error can be automatically corrected"
    )

    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "data_pipeline_validationerror"
        indexes = [
            models.Index(fields=["pipeline_run", "error_type"]),
            models.Index(fields=["column_name", "error_type"]),
            models.Index(fields=["is_critical"]),
        ]

    def __str__(self):
        return f"Row {self.row_number}: {self.column_name} - {self.error_type}"


class CleaningRule(models.Model):
    """Store and version cleaning rules for reproducibility"""

    RULE_TYPE_CHOICES: ClassVar[list[tuple[str, str]]] = [
        ("null_standardization", "NULL Standardization"),
        ("date_parsing", "Date Format Parsing"),
        ("encoding_fix", "Character Encoding Fix"),
        ("text_normalization", "Text Normalization"),
        ("numeric_conversion", "Numeric Data Conversion"),
        ("custom_mapping", "Custom Value Mapping"),
    ]

    name: models.CharField = models.CharField(max_length=100, unique=True)
    rule_type: models.CharField = models.CharField(max_length=50, choices=RULE_TYPE_CHOICES)
    description: models.TextField = models.TextField(help_text="Human-readable description of the rule")

    # Rule configuration
    parameters: JSONField = JSONField(default=dict, help_text="Rule parameters and settings")
    applies_to_tables: models.JSONField = models.JSONField(default=list, help_text="Tables this rule applies to")
    applies_to_columns: models.JSONField = models.JSONField(default=list, help_text="Columns this rule applies to")

    # Version control
    version: models.CharField = models.CharField(max_length=20, default="1.0")
    is_active: models.BooleanField = models.BooleanField(default=True)

    # Audit fields
    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)
    updated_at: models.DateTimeField = models.DateTimeField(auto_now=True)
    created_by: models.CharField = models.CharField(max_length=100, null=True, blank=True)

    class Meta:
        db_table = "data_pipeline_cleaningrule"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} v{self.version}"


class ProcessingStatistics(models.Model):
    """Aggregate statistics for monitoring and reporting"""

    # Time period
    date: models.DateField = models.DateField(help_text="Statistics date")
    table_name: models.CharField = models.CharField(max_length=100)

    # Volume metrics
    total_runs: models.IntegerField = models.IntegerField(default=0)
    successful_runs: models.IntegerField = models.IntegerField(default=0)
    failed_runs: models.IntegerField = models.IntegerField(default=0)

    # Performance metrics
    avg_processing_time: models.DurationField = models.DurationField(null=True, blank=True)
    max_processing_time: models.DurationField = models.DurationField(null=True, blank=True)
    total_records_processed: models.BigIntegerField = models.BigIntegerField(default=0)

    # Quality metrics
    avg_success_rate: models.FloatField = models.FloatField(null=True, blank=True)
    common_error_types: JSONField = JSONField(default=list)

    created_at: models.DateTimeField = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "data_pipeline_processingstatistics"
        unique_together = [["date", "table_name"]]
        ordering = ["-date", "table_name"]

    def __str__(self):
        return f"{self.table_name} - {self.date}"
