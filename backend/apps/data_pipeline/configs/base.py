"""
Base Configuration Classes

Defines the configuration framework for table-specific pipeline processing.
Each table gets its own configuration that inherits from these base classes.
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ColumnMapping:
    """Maps source MSSQL column to target with cleaning and validation rules"""

    # Column identification
    source_name: str  # Original MSSQL column name (case-sensitive)
    target_name: str  # Cleaned target column name
    data_type: str  # Original MSSQL data type from DDL
    nullable: bool  # Whether NULL values are allowed

    # Cleaning configuration
    cleaning_rules: list[str] = field(default_factory=list)  # ['trim', 'null_standardize', 'date_parse']
    custom_cleaner: Callable | None = None  # Custom cleaning function

    # Cross-table optimization (NEW)
    is_shared_field: bool = False  # Whether this field is shared with other tables for optimization

    # Validation hints for Stage 4
    business_rules: list[str] = field(default_factory=list)  # Business validation rules
    validation_priority: int = 1  # 1=critical, 2=important, 3=optional

    # Documentation
    description: str = ""  # Human-readable description
    examples: list[str] = field(default_factory=list)  # Example values
    known_issues: list[str] = field(default_factory=list)  # Known data quality problems

    def __post_init__(self):
        """Validate configuration after initialization"""
        if not self.source_name or not self.target_name:
            raise ValueError("Both source_name and target_name are required")

        if not self.data_type:
            raise ValueError("data_type is required")


@dataclass
class TransformationRule:
    """
    Defines a single transformation to apply.
    Each rule specifies what column to transform, how to transform it,
    and whether to keep the original value.
    """

    source_column: str  # Column to transform from
    target_column: str  # Column to write result to (can be same as source)
    transformer: str  # Name of transformer in registry (e.g., "khmer.limon_to_unicode")
    preserve_original: bool = False  # If True, keeps original in {source_column}_original
    condition: str | None = None  # Optional transformer to check if transformation should apply


@dataclass
class TableConfig:
    """Complete pipeline configuration for one table"""

    # Basic table information
    table_name: str  # Logical table name (e.g., 'students')
    source_file_pattern: str  # CSV filename pattern (e.g., 'students.csv')
    description: str = ""  # Human-readable description

    # Stage naming convention (follows pattern)
    raw_table_name: str = ""  # Will auto-generate if empty: "raw_{table_name}"
    profile_table_name: str = ""  # Stage 2 analysis: "profile_{table_name}"
    cleaned_table_name: str = ""  # Stage 3 output: "cleaned_{table_name}"
    validated_table_name: str = ""  # Stage 4 output: "validated_{table_name}"

    # Column configuration
    column_mappings: list[ColumnMapping] = field(default_factory=list)

    # Stage 3 cleaning configuration
    cleaning_rules: dict[str, Any] = field(default_factory=dict)
    encoding_handling: str = "auto"  # 'auto', 'utf-8', 'latin-1', 'cp1252'
    date_formats: list[str] = field(default_factory=list)  # Expected date formats
    null_patterns: list[str] = field(default_factory=lambda: ["NULL", "NA", "", " "])

    # Stage 4 validation configuration
    validator_class: type | None = None  # Pydantic model class
    validation_mode: str = "strict"  # 'strict', 'lenient', 'warn_only'
    max_validation_errors: int = 10000  # Stop after this many errors

    # Stage 5 configuration (NEW) - Domain transformations
    transformed_table_name: str = ""  # Stage 5 output: "transformed_{table_name}"
    transformation_rules: list[TransformationRule] = field(default_factory=list)  # List of transformations to apply

    # Stage 6 configuration - Record splitting (for enrollment data)
    supports_record_splitting: bool = False  # Whether this table supports record splitting

    # Performance tuning
    chunk_size: int = 10000  # Process in chunks for large tables
    memory_limit_mb: int = 1024  # Memory usage limit

    # Business context (Stage 5 hints)
    target_django_model: str | None = None
    business_transformations: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)  # Tables this depends on

    # Cross-table dependency optimization (NEW)
    provides_shared_fields: list[str] = field(default_factory=list)  # Fields this table provides to others
    table_filters: dict[str, Any] = field(
        default_factory=dict
    )  # Filters to apply when processing (e.g., {"is_shadow": 0})

    # Quality thresholds
    min_completeness_score: float = 70.0  # Minimum data completeness %
    min_consistency_score: float = 80.0  # Minimum data consistency %
    max_error_rate: float = 10.0  # Maximum validation error %

    def __post_init__(self):
        """Auto-generate table names and validate configuration"""
        if not self.raw_table_name:
            self.raw_table_name = f"raw_{self.table_name}"
        if not self.profile_table_name:
            self.profile_table_name = f"profile_{self.table_name}"
        if not self.cleaned_table_name:
            self.cleaned_table_name = f"cleaned_{self.table_name}"
        if not self.validated_table_name:
            self.validated_table_name = f"validated_{self.table_name}"
        if not self.transformed_table_name:
            self.transformed_table_name = f"transformed_{self.table_name}"

        # Validate required fields
        if not self.table_name or not self.source_file_pattern:
            raise ValueError("table_name and source_file_pattern are required")

        # Validate column mappings
        if self.column_mappings:
            source_names = [cm.source_name for cm in self.column_mappings]
            if len(source_names) != len(set(source_names)):
                raise ValueError("Duplicate source column names in mappings")

    def get_column_mapping(self, source_name: str) -> ColumnMapping | None:
        """Get column mapping by source name"""
        for mapping in self.column_mappings:
            if mapping.source_name == source_name:
                return mapping
        return None

    def get_critical_columns(self) -> list[ColumnMapping]:
        """Get columns marked as critical (validation_priority = 1)"""
        return [cm for cm in self.column_mappings if cm.validation_priority == 1]

    def get_required_columns(self) -> list[ColumnMapping]:
        """Get columns that cannot be NULL"""
        return [cm for cm in self.column_mappings if not cm.nullable]

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors"""
        errors = []

        # Check validator class is set
        if not self.validator_class:
            errors.append(f"validator_class is required for {self.table_name}")

        # Check column mappings exist
        if not self.column_mappings:
            errors.append(f"column_mappings cannot be empty for {self.table_name}")

        # Validate cleaning rules - must match cleaning engine available rules
        valid_cleaning_rules = {
            "trim",
            "null_standardize",
            "uppercase",
            "lowercase",
            "title_case",
            "fix_encoding",
            "fix_khmer_encoding",
            "parse_mssql_datetime",
            "parse_float",
            "parse_int",
            "parse_boolean",
            "parse_decimal",
            "standardize_phone",
            "normalize_phone",  # Alias for standardize_phone
            "standardize_gender",
            "normalize_gender",  # Alias for standardize_gender
            "standardize_marital",
            "validate_email",
            "pad_zeros",
            "parse_student_name",
            "parse_emergency_contact",
            "normalize_birth_date",
            "normalize_class_id",
        }

        for mapping in self.column_mappings:
            invalid_rules = set(mapping.cleaning_rules) - valid_cleaning_rules
            if invalid_rules:
                errors.append(f"Invalid cleaning rules for {mapping.source_name}: {invalid_rules}")

        return errors


@dataclass
class PipelineResult:
    """Result object returned by pipeline execution"""

    table_name: str
    stage_completed: int
    success: bool

    # Processing statistics
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0

    # Performance metrics
    execution_time: float = 0.0
    memory_usage_mb: float = 0.0

    # Quality metrics
    completeness_score: float = 0.0
    consistency_score: float = 0.0
    error_rate: float = 0.0

    # Error details
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # Stage-specific results
    stage_results: dict[int, dict[str, Any]] = field(default_factory=dict)

    def add_error(self, message: str):
        """Add an error message"""
        self.errors.append(message)
        self.success = False

    def add_warning(self, message: str):
        """Add a warning message"""
        self.warnings.append(message)

    def set_stage_result(self, stage: int, result: dict[str, Any]):
        """Store result from a specific stage"""
        self.stage_results[stage] = result


class ConfigurationError(Exception):
    """Raised when there are configuration validation errors"""

    pass


class PipelineLogger:
    """Centralized logging for pipeline operations"""

    def __init__(self, table_name: str, run_id: int | None = None):
        self.table_name = table_name
        self.run_id = run_id
        self.logger = logging.getLogger(f"data_pipeline.{table_name}")

        # Configure logger if not already configured
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(f"%(asctime)s - Pipeline[{table_name}] - %(levelname)s - %(message)s")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def info(self, message: str, **kwargs):
        """Log info message with optional context"""
        self.logger.info(message, extra={"run_id": self.run_id, **kwargs})

    def warning(self, message: str, **kwargs):
        """Log warning message with optional context"""
        self.logger.warning(message, extra={"run_id": self.run_id, **kwargs})

    def error(self, message: str, **kwargs):
        """Log error message with optional context"""
        self.logger.error(message, extra={"run_id": self.run_id, **kwargs})

    def debug(self, message: str, **kwargs):
        """Log debug message with optional context"""
        self.logger.debug(message, extra={"run_id": self.run_id, **kwargs})


# Utility functions for configuration validation
def validate_date_format(date_string: str, formats: list[str]) -> bool:
    """Test if date string matches any of the expected formats"""
    from datetime import datetime

    for fmt in formats:
        try:
            datetime.strptime(date_string.strip(), fmt)
            return True
        except ValueError:
            continue
    return False


def detect_encoding_issues(text: str) -> bool:
    """Detect if text contains character encoding problems"""
    if not text:
        return False

    # Common encoding issue patterns
    encoding_indicators = [
        "\ufffd",  # Unicode replacement character
        "â€™",  # Smart quote encoding issue
        "Ã¡",
        "Ã©",
        "Ã­",
        "Ã³",
        "Ãº",  # Latin-1 to UTF-8 issues
        "©",
        "â",
        "ä",
        "ò",
        "ü",  # Common garbled characters
    ]

    return any(indicator in text for indicator in encoding_indicators)


def generate_sample_config() -> TableConfig:
    """Generate a sample configuration for reference/testing"""
    return TableConfig(
        table_name="sample",
        source_file_pattern="sample.csv",
        description="Sample configuration for testing",
        column_mappings=[
            ColumnMapping(
                source_name="ID",
                target_name="id",
                data_type="nvarchar(10)",
                nullable=False,
                cleaning_rules=["trim", "pad_zeros"],
                description="Primary identifier",
            ),
            ColumnMapping(
                source_name="Name",
                target_name="full_name",
                data_type="nvarchar(100)",
                nullable=False,
                cleaning_rules=["trim", "title_case"],
                description="Full name",
            ),
        ],
        cleaning_rules={"date_format": "mssql_datetime", "encoding_fix": True},
    )
