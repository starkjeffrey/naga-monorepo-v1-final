"""
Terms Table Configuration

Configuration for processing the Terms table - academic term/semester data.
This is the simplest table with 15 columns and clear data patterns.
"""

from ..configs.base import ColumnMapping, TableConfig
from ..validators.terms import TermValidator

TERMS_CONFIG = TableConfig(
    table_name="terms",
    source_file_pattern="terms.csv",
    description="Academic terms/semesters with start/end dates and term types",
    # Table naming follows convention
    raw_table_name="raw_terms",
    cleaned_table_name="cleaned_terms",
    validated_table_name="validated_terms",
    column_mappings=[
        # Primary identifier
        ColumnMapping(
            source_name="TermID",
            target_name="term_id",
            data_type="nvarchar(200)",
            nullable=False,
            cleaning_rules=["trim", "uppercase"],
            description="Term identifier like '2009T1E', '2009T2E'",
            examples=["2009T1E", "2009T2E", "2010T1E"],
        ),
        # Term description
        ColumnMapping(
            source_name="TermName",
            target_name="term_name",
            data_type="nvarchar(50)",
            nullable=False,
            cleaning_rules=["trim"],
            description="Human-readable term name",
            examples=["Term 1E (27-Apr-2009)", "Term 2E (25-Jun-2009)"],
        ),
        # Date fields - critical for academic scheduling
        ColumnMapping(
            source_name="StartDate",
            target_name="start_date",
            data_type="datetime(23, 3)",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_mssql_datetime"],
            validation_priority=1,  # Critical field
            description="Term start date",
            examples=["Apr 27 2009 12:00AM", "Jun 25 2009 12:00AM"],
        ),
        ColumnMapping(
            source_name="EndDate",
            target_name="end_date",
            data_type="datetime(23, 3)",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_mssql_datetime"],
            validation_priority=1,  # Critical field
            description="Term end date",
            examples=["Jul 28 2009 12:00AM", "Sep 17 2009 12:00AM"],
        ),
        ColumnMapping(
            source_name="LDPDate",
            target_name="last_drop_date",
            data_type="datetime(23, 3)",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_mssql_datetime"],
            description="Last date to drop courses",
        ),
        ColumnMapping(
            source_name="AddDate",
            target_name="add_date",
            data_type="datetime(23, 3)",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_mssql_datetime"],
            description="Last date to add courses",
        ),
        ColumnMapping(
            source_name="DropDate",
            target_name="drop_date",
            data_type="datetime(23, 3)",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_mssql_datetime"],
            description="Course drop deadline",
        ),
        ColumnMapping(
            source_name="LeaveDate",
            target_name="leave_date",
            data_type="datetime(23, 3)",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_mssql_datetime"],
            description="Leave of absence deadline",
        ),
        # Term metadata
        ColumnMapping(
            source_name="PmtPeriod",
            target_name="payment_period",
            data_type="nvarchar(50)",
            nullable=False,
            cleaning_rules=["trim", "parse_int"],
            description="Payment period in days",
            examples=["21"],
        ),
        ColumnMapping(
            source_name="MaxTerms",
            target_name="max_terms",
            data_type="nvarchar(50)",
            nullable=True,
            cleaning_rules=["trim", "parse_int"],
            description="Maximum terms allowed",
        ),
        ColumnMapping(
            source_name="schoolyear",
            target_name="school_year",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_int"],
            validation_priority=2,
            description="School year (2009, 2010, etc.)",
            examples=["2009", "2010", "2011"],
        ),
        ColumnMapping(
            source_name="TermType",
            target_name="term_type",
            data_type="nvarchar(5)",
            nullable=True,
            cleaning_rules=["trim", "uppercase"],
            description="Term type code (ENG A, X, etc.)",
            examples=["ENG A", "X"],
        ),
        ColumnMapping(
            source_name="Desp",
            target_name="description",
            data_type="nvarchar(200)",
            nullable=True,
            cleaning_rules=["trim"],
            description="Additional description or notes",
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
    # Cleaning configuration
    cleaning_rules={
        "date_format": "mssql_datetime",  # "Apr 27 2009 12:00AM" format
        "null_patterns": ["NULL", "NA", "", " "],
        "encoding_fix": False,  # Terms data is clean ASCII
    },
    # Performance settings
    chunk_size=5000,  # Terms table is small
    # Quality thresholds
    min_completeness_score=80.0,  # Allow some missing optional fields
    min_consistency_score=85.0,
    max_error_rate=5.0,  # Very strict for academic data
    # Business context
    dependencies=[],  # Terms don't depend on other tables
    target_django_model="apps.curriculum.models.Term",
    validator_class=TermValidator,
)
