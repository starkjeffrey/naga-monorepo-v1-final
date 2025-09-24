"""
Academic Classes Table Configuration

Header table that provides cleaned classid values for academiccoursetakers.
Only processes records where is_shadow=0.
"""

from ..configs.base import ColumnMapping, TableConfig
from ..validators.academicclasses import AcademicClassValidator as AcademicClassesValidator

ACADEMICCLASSES_CONFIG = TableConfig(
    table_name="academicclasses",
    source_file_pattern="academicclasses.csv",
    description="Academic class definitions (headers) - provides cleaned classid for enrollments",
    # Table naming follows convention
    raw_table_name="raw_academicclasses",
    cleaned_table_name="cleaned_academicclasses",
    validated_table_name="validated_academicclasses",
    # NEW: Dependency configuration
    provides_shared_fields=["classid"],  # Fields this table provides to other tables
    table_filters={"is_shadow": 0},  # Only process non-shadow classes
    column_mappings=[
        # Primary identifier - SHARED FIELD
        ColumnMapping(
            source_name="classid",
            target_name="class_id_clean",
            data_type="nvarchar(50)",
            nullable=False,
            cleaning_rules=["trim", "uppercase", "normalize_class_id"],
            validation_priority=1,  # Critical shared field
            is_shared_field=True,  # NEW: Mark as shared field
            description="Class ID - cleaned and normalized for sharing with enrollments",
            examples=["MATH101-01", "ENG200-A", "HIST150-B"],
        ),
        # Class information
        ColumnMapping(
            source_name="class_name",
            target_name="class_name",
            data_type="nvarchar(200)",
            nullable=False,
            cleaning_rules=["trim", "fix_encoding"],
            validation_priority=1,
            description="Class name/title",
        ),
        ColumnMapping(
            source_name="course_code",
            target_name="course_code",
            data_type="nvarchar(20)",
            nullable=True,
            cleaning_rules=["trim", "uppercase"],
            description="Course code (subject + number)",
            examples=["MATH101", "ENG200", "HIST150"],
        ),
        ColumnMapping(
            source_name="section",
            target_name="section",
            data_type="nvarchar(10)",
            nullable=True,
            cleaning_rules=["trim", "uppercase"],
            description="Class section identifier",
            examples=["01", "A", "B"],
        ),
        ColumnMapping(
            source_name="term",
            target_name="term",
            data_type="nvarchar(20)",
            nullable=True,
            cleaning_rules=["trim", "standardize_term"],
            description="Academic term",
            examples=["Fall2023", "Spring2024"],
        ),
        ColumnMapping(
            source_name="instructor",
            target_name="instructor",
            data_type="nvarchar(100)",
            nullable=True,
            cleaning_rules=["trim", "fix_encoding"],
            description="Primary instructor name",
        ),
        ColumnMapping(
            source_name="credits",
            target_name="credits",
            data_type="int",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_int"],
            validation_priority=2,
            description="Credit hours for this class",
        ),
        ColumnMapping(
            source_name="max_enrollment",
            target_name="max_enrollment",
            data_type="int",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_int"],
            description="Maximum student enrollment",
        ),
        ColumnMapping(
            source_name="schedule_info",
            target_name="schedule_info",
            data_type="nvarchar(200)",
            nullable=True,
            cleaning_rules=["trim"],
            description="Class schedule information",
        ),
        ColumnMapping(
            source_name="is_shadow",
            target_name="is_shadow",
            data_type="int",
            nullable=False,
            cleaning_rules=["parse_boolean"],
            validation_priority=1,
            description="Shadow class flag (0=real class, 1=shadow/placeholder)",
        ),
        # Audit fields
        ColumnMapping(
            source_name="created_date",
            target_name="created_date",
            data_type="datetime(23, 3)",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_mssql_datetime"],
            description="Record creation timestamp",
        ),
        ColumnMapping(
            source_name="modified_date",
            target_name="modified_date",
            data_type="datetime(23, 3)",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_mssql_datetime"],
            description="Last modification timestamp",
        ),
    ],
    # Cleaning configuration
    cleaning_rules={
        "date_format": "mssql_datetime",
        "null_patterns": ["NULL", "NA", "", " "],
        "encoding_fix": True,
        "class_id_normalization": True,  # Special handling for classid
    },
    # Performance settings
    chunk_size=1000,  # Classes table is smaller than students
    # Quality thresholds
    min_completeness_score=80.0,
    min_consistency_score=85.0,
    max_error_rate=5.0,  # Class definitions should be cleaner
    # Business context
    dependencies=[],  # Header table has no dependencies
    target_django_model="apps.curriculum.models.AcademicClass",
    validator_class=AcademicClassesValidator,
)
