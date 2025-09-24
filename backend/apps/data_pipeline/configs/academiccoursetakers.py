"""
Academic Course Takers Table Configuration

Detail table for student enrollments that uses cleaned classid from academicclasses.
This is the largest and most complex table with 40 columns representing student course
registrations, grades, and academic performance data. Critical for transcript generation.

DEPENDENCY: Requires academicclasses to be processed first for classid optimization.
"""

from ..configs.base import ColumnMapping, TableConfig
from ..validators.academiccoursetakers import AcademicCourseTakerValidator

ACADEMICCOURSETAKERS_CONFIG = TableConfig(
    table_name="academiccoursetakers",
    source_file_pattern="academiccoursetakers.csv",
    description="Student course enrollments with grades and academic performance tracking",
    # Table naming follows convention
    raw_table_name="raw_academiccoursetakers",
    cleaned_table_name="cleaned_academiccoursetakers",
    validated_table_name="validated_academiccoursetakers",
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
            examples=["ENG101-001-2009T1", "HIST200-002-2009T1"],
        ),
        # Academic performance - core grading data
        ColumnMapping(
            source_name="RepeatNum",
            target_name="repeat_count",
            data_type="int",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_int"],
            validation_priority=2,
            description="Number of times course was repeated (0 = first attempt)",
            examples=["0", "1", "2"],
        ),
        ColumnMapping(
            source_name="LScore",
            target_name="lab_score",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_float"],
            description="Laboratory or practical component score",
        ),
        ColumnMapping(
            source_name="UScore",
            target_name="unit_score",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_float"],
            description="Unit test or module score",
        ),
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
            examples=["A", "A-", "B+", "B", "C", "F", "W", "I"],
        ),
        ColumnMapping(
            source_name="PreviousGrade",
            target_name="previous_grade",
            data_type="char(10)",
            nullable=True,
            cleaning_rules=["trim", "uppercase"],
            description="Previous grade if course was repeated",
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
        # Registration and enrollment details
        ColumnMapping(
            source_name="RegisterMode",
            target_name="registration_mode",
            data_type="nvarchar(20)",
            nullable=True,
            cleaning_rules=["trim"],
            description="How student registered (online, in-person, etc.)",
        ),
        ColumnMapping(
            source_name="Attendance",
            target_name="attendance_status",
            data_type="char(20)",
            nullable=True,
            cleaning_rules=["trim"],
            description="Overall attendance status for course",
        ),
        # Comments and notes
        ColumnMapping(
            source_name="Comment",
            target_name="instructor_comment",
            data_type="char(100)",
            nullable=True,
            cleaning_rules=["trim", "fix_encoding"],
            description="Instructor comments about student performance",
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
            source_name="QuickNote",
            target_name="quick_note",
            data_type="char(50)",
            nullable=True,
            cleaning_rules=["trim", "fix_encoding"],
            description="Quick administrative note",
        ),
        # Visual and UI elements
        ColumnMapping(
            source_name="Color",
            target_name="color_code",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_int"],
            description="Color coding for visual organization",
        ),
        ColumnMapping(
            source_name="ForeColor",
            target_name="foreground_color",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_int"],
            description="Foreground color for UI display",
        ),
        ColumnMapping(
            source_name="BackColor",
            target_name="background_color",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_int"],
            description="Background color for UI display",
        ),
        # Position and ordering
        ColumnMapping(
            source_name="Pos",
            target_name="position",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_int"],
            description="Position or ordering within student's transcript",
        ),
        ColumnMapping(
            source_name="GPos",
            target_name="group_position",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_int"],
            description="Group-based position indicator",
        ),
        # Audit and tracking
        ColumnMapping(
            source_name="Adder",
            target_name="added_by_user_id",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_int"],
            description="User ID who added this enrollment record",
        ),
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
        # Parsed and normalized fields (added later for analysis)
        ColumnMapping(
            source_name="section",
            target_name="parsed_section",
            data_type="nvarchar(255)",
            nullable=True,
            cleaning_rules=["trim"],
            description="Parsed section information from ClassID",
        ),
        ColumnMapping(
            source_name="time_slot",
            target_name="parsed_time_slot",
            data_type="nvarchar(255)",
            nullable=True,
            cleaning_rules=["trim"],
            description="Parsed time slot information from ClassID",
        ),
        ColumnMapping(
            source_name="parsed_termid",
            target_name="parsed_term_id",
            data_type="nvarchar(255)",
            nullable=True,
            cleaning_rules=["trim", "uppercase"],
            description="Term ID parsed from ClassID",
        ),
        ColumnMapping(
            source_name="parsed_coursecode",
            target_name="parsed_course_code",
            data_type="nvarchar(255)",
            nullable=True,
            cleaning_rules=["trim", "uppercase"],
            description="Course code parsed from ClassID",
        ),
        ColumnMapping(
            source_name="parsed_langcourse",
            target_name="parsed_language_course",
            data_type="nvarchar(255)",
            nullable=True,
            cleaning_rules=["trim"],
            description="Language course indicator parsed from ClassID",
        ),
        # Normalized fields (standardization effort)
        ColumnMapping(
            source_name="NormalizedCourse",
            target_name="normalized_course",
            data_type="nvarchar(15)",
            nullable=True,
            cleaning_rules=["trim", "uppercase"],
            description="Standardized course code format",
        ),
        ColumnMapping(
            source_name="NormalizedPart",
            target_name="normalized_part",
            data_type="nvarchar(255)",
            nullable=True,
            cleaning_rules=["trim"],
            description="Standardized course part/component",
        ),
        ColumnMapping(
            source_name="NormalizedSection",
            target_name="normalized_section",
            data_type="nvarchar(15)",
            nullable=True,
            cleaning_rules=["trim"],
            description="Standardized section identifier",
        ),
        ColumnMapping(
            source_name="NormalizedTOD",
            target_name="normalized_time_of_day",
            data_type="nvarchar(10)",
            nullable=True,
            cleaning_rules=["trim"],
            description="Standardized time of day code",
        ),
        # Legacy system primary key - preserve but exclude from profiling
        ColumnMapping(
            source_name="IPK",
            target_name="legacy_id",
            data_type="bigint",
            nullable=False,
            cleaning_rules=["parse_int"],
            description="Legacy system auto-increment primary key",
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
    # Performance settings - largest table, smallest chunks
    chunk_size=1000,  # Very large table, use small chunks for memory efficiency
    # Quality thresholds - strict for academic records
    min_completeness_score=85.0,  # Academic data should be complete
    min_consistency_score=90.0,  # Grade data must be consistent
    max_error_rate=5.0,  # Very strict for transcript data
    # Business context
    dependencies=["students", "academicclasses"],  # Requires both students and classes
    target_django_model="apps.enrollment.models.CourseEnrollment",
    validator_class=AcademicCourseTakerValidator,
)
