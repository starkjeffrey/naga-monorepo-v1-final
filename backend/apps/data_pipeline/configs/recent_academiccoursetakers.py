"""
Recent Academic Course Takers Configuration

Focused dataset for the 3 most recent active terms:
- 241007E-T4AE (2,694 students) - Term 4AE, Oct 2024
- 241125B-T4 (1,437 students) - Term 4 BA, Nov 2024
- 240821B-T3 (1,392 students) - Term 3 BA, Aug 2024

Total: ~5,500+ enrollment records for testing and immediate system use.
"""

from ..configs.base import ColumnMapping, TableConfig
from ..validators.academiccoursetakers import AcademicCourseTakerValidator

RECENT_ACADEMICCOURSETAKERS_CONFIG = TableConfig(
    table_name="recent_academiccoursetakers",
    source_file_pattern="recent_academiccoursetakers.csv",
    description="Recent academic course takers from 3 most active terms (2024)",
    # Table naming follows convention
    raw_table_name="raw_recent_academiccoursetakers",
    cleaned_table_name="cleaned_recent_academiccoursetakers",
    validated_table_name="validated_recent_academiccoursetakers",
    column_mappings=[
        # Primary identifiers - critical for joining
        ColumnMapping(
            source_name="ID",
            target_name="student_id",
            data_type="nvarchar(10)",
            nullable=False,
            cleaning_rules=["trim", "uppercase"],
            validation_priority=1,  # Critical foreign key
            description="Student ID reference",
            examples=["ST001", "ST002", "MS2010001"],
        ),
        ColumnMapping(
            source_name="ClassID",
            target_name="class_id",
            data_type="nvarchar(255)",
            nullable=False,
            cleaning_rules=["trim", "uppercase"],
            validation_priority=1,  # Critical foreign key
            description="Academic class section identifier",
            examples=["241007E-T4AE!$582!$E!$E4A!$COM-4A", "241125B-T4!$87!$M!$BA-04M!$SOC-204"],
        ),
        # Academic performance - core grading data
        ColumnMapping(
            source_name="Credit",
            target_name="credit_hours",
            data_type="int",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_int"],
            validation_priority=1,  # Critical for degree calculation
            description="Credit hours for this course",
            examples=["3", "4", "6"],
        ),
        ColumnMapping(
            source_name="GradePoint",
            target_name="grade_points",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_float"],
            validation_priority=1,  # Critical for GPA calculation
            description="Grade points earned (GPA scale)",
            examples=["4.0", "3.7", "2.0"],
        ),
        ColumnMapping(
            source_name="TotalPoint",
            target_name="total_points",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_float"],
            validation_priority=2,
            description="Total points calculation (GradePoint * Credit)",
        ),
        ColumnMapping(
            source_name="Grade",
            target_name="final_grade",
            data_type="char(10)",
            nullable=True,
            cleaning_rules=["trim", "uppercase"],
            validation_priority=1,  # Critical for transcripts
            description="Final letter grade assigned",
            examples=["A", "A-", "B+", "B", "C", "F", "W", "I", "IP"],
        ),
        ColumnMapping(
            source_name="Passed",
            target_name="is_passed",
            data_type="int",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_boolean"],
            validation_priority=2,
            description="Whether student passed the course (1=passed, 0=failed)",
        ),
        ColumnMapping(
            source_name="Remarks",
            target_name="administrative_remarks",
            data_type="nvarchar(50)",
            nullable=True,
            cleaning_rules=["trim", "fix_encoding"],
            description="Administrative remarks or notes",
        ),
        ColumnMapping(
            source_name="Attendance",
            target_name="attendance_status",
            data_type="char(20)",
            nullable=True,
            cleaning_rules=["trim"],
            description="Overall attendance status for course",
        ),
        # Audit and tracking
        ColumnMapping(
            source_name="AddTime",
            target_name="added_timestamp",
            data_type="datetime(23, 3)",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_mssql_datetime"],
            description="When enrollment record was added",
        ),
        ColumnMapping(
            source_name="LastUpdate",
            target_name="last_updated",
            data_type="datetime(23, 3)",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_mssql_datetime"],
            description="Last time record was updated",
        ),
        ColumnMapping(
            source_name="IPK",
            target_name="legacy_id",
            data_type="bigint",
            nullable=False,
            cleaning_rules=["parse_int"],
            description="Legacy system auto-increment primary key",
        ),
        ColumnMapping(
            source_name="CreatedDate",
            target_name="created_date",
            data_type="datetime(23, 3)",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_mssql_datetime"],
            description="Record creation timestamp",
        ),
        ColumnMapping(
            source_name="ModifiedDate",
            target_name="modified_date",
            data_type="datetime(23, 3)",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_mssql_datetime"],
            description="Last modification timestamp",
        ),
    ],
    # Cleaning configuration - critical for grade data
    cleaning_rules={
        "date_format": "mssql_datetime",  # Standard MSSQL datetime format
        "null_patterns": ["NULL", "NA", "", " ", "0", "-1"],
        "encoding_fix": True,  # Comments may have encoding issues
        "grade_normalization": True,  # Standardize grade formats
        "gpa_validation": True,  # Validate GPA scale values
    },
    # Performance settings - smaller dataset, larger chunks
    chunk_size=2000,  # Recent dataset is smaller, use larger chunks
    # Quality thresholds - strict for academic records
    min_completeness_score=85.0,  # Academic data should be complete
    min_consistency_score=90.0,  # Grade data must be consistent
    max_error_rate=5.0,  # Very strict for transcript data
    # Business context
    dependencies=["students", "academicclasses"],  # Requires both students and classes
    target_django_model="apps.enrollment.models.CourseEnrollment",
    validator_class=AcademicCourseTakerValidator,
)
