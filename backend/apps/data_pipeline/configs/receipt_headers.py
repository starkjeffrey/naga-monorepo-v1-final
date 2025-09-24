"""
Receipt Headers Table Configuration

Configuration for processing the Receipt_Headers table - payment receipt header records.
This table contains 31 columns with payment transaction headers including amounts,
discounts, and payment details. Critical for financial reporting and audit trails.
"""

from ..configs.base import ColumnMapping, TableConfig
from ..validators.receipt_headers import ReceiptHeaderValidator

RECEIPT_HEADERS_CONFIG = TableConfig(
    table_name="receipt_headers",
    source_file_pattern="receipt_headers.csv",
    description="Payment receipt headers with transaction amounts and payment details",
    # Table naming follows convention
    raw_table_name="raw_receipt_headers",
    cleaned_table_name="cleaned_receipt_headers",
    validated_table_name="validated_receipt_headers",
    column_mappings=[
        # Primary and foreign key identifiers
        ColumnMapping(
            source_name="ID",
            target_name="student_id",
            data_type="nvarchar(50)",
            nullable=False,
            cleaning_rules=["trim", "uppercase"],
            validation_priority=1,  # Critical foreign key to students
            description="Student ID who made payment",
            examples=["ST001", "ST002", "MS2010001"],
        ),
        ColumnMapping(
            source_name="TermID",
            target_name="term_id",
            data_type="nvarchar(100)",
            nullable=True,
            cleaning_rules=["trim", "uppercase"],
            validation_priority=2,  # Important for term-based billing
            description="Academic term for payment",
            examples=["2009T1E", "2009T2E", "2010T1E"],
        ),
        ColumnMapping(
            source_name="Program",
            target_name="program_id",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_int"],
            validation_priority=2,
            description="Program ID associated with payment",
        ),
        # Receipt identification
        ColumnMapping(
            source_name="IntReceiptNo",
            target_name="internal_receipt_number",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_int"],
            validation_priority=1,  # Critical for tracking
            description="Internal system receipt number",
        ),
        ColumnMapping(
            source_name="ReceiptNo",
            target_name="receipt_number",
            data_type="nvarchar(150)",
            nullable=True,
            cleaning_rules=["trim"],
            validation_priority=1,  # Critical for external reference
            description="Official receipt number for external use",
        ),
        ColumnMapping(
            source_name="ReceiptID",
            target_name="receipt_id",
            data_type="nvarchar(250)",
            nullable=False,
            cleaning_rules=["trim", "uppercase"],
            validation_priority=1,  # Primary business identifier
            description="Unique receipt identifier",
            examples=["REC-2009-001", "PAY-ST001-2009T1"],
        ),
        ColumnMapping(
            source_name="recID",
            target_name="rec_id_alt",
            data_type="char(150)",
            nullable=True,
            cleaning_rules=["trim"],
            description="Alternative receipt ID field",
        ),
        # Payment date and transaction details
        ColumnMapping(
            source_name="PmtDate",
            target_name="payment_date",
            data_type="datetime(23, 3)",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_mssql_datetime"],
            validation_priority=1,  # Critical for financial records
            description="Date payment was received",
        ),
        ColumnMapping(
            source_name="PmtType",
            target_name="payment_type",
            data_type="char(50)",
            nullable=True,
            cleaning_rules=["trim"],
            validation_priority=2,
            description="Payment method type",
            examples=["Cash", "Check", "Bank Transfer", "Credit Card"],
        ),
        ColumnMapping(
            source_name="CheckNo",
            target_name="check_number",
            data_type="char(50)",
            nullable=True,
            cleaning_rules=["trim"],
            description="Check number if payment by check",
        ),
        ColumnMapping(
            source_name="TransType",
            target_name="transaction_type",
            data_type="char(100)",
            nullable=True,
            cleaning_rules=["trim"],
            description="Type of financial transaction",
        ),
        # Financial amounts - critical for accuracy
        ColumnMapping(
            source_name="Amount",
            target_name="gross_amount",
            data_type="real(24)",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_decimal"],
            validation_priority=1,  # Critical financial data
            description="Gross payment amount before deductions",
        ),
        ColumnMapping(
            source_name="NetAmount",
            target_name="net_amount",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_decimal"],
            validation_priority=1,  # Critical financial data
            description="Net payment amount after all deductions",
        ),
        ColumnMapping(
            source_name="NetDiscount",
            target_name="discount_amount",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_decimal"],
            validation_priority=2,
            description="Total discount applied",
        ),
        ColumnMapping(
            source_name="ScholarGrant",
            target_name="scholarship_amount",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_decimal"],
            validation_priority=2,
            description="Scholarship or grant amount applied",
        ),
        ColumnMapping(
            source_name="Balance",
            target_name="remaining_balance",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_decimal"],
            validation_priority=2,
            description="Remaining balance after payment",
        ),
        ColumnMapping(
            source_name="OtherDeduct",
            target_name="other_deductions",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_decimal"],
            description="Other miscellaneous deductions",
        ),
        ColumnMapping(
            source_name="LateFee",
            target_name="late_fee",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_decimal"],
            description="Late payment fee charged",
        ),
        ColumnMapping(
            source_name="PrepaidFee",
            target_name="prepaid_fee",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_decimal"],
            description="Prepaid fee amount",
        ),
        # Student information (duplicated for reporting)
        ColumnMapping(
            source_name="name",
            target_name="student_name",
            data_type="varchar(120)",
            nullable=True,
            cleaning_rules=["trim", "fix_encoding"],
            description="Student name (duplicated from Students table)",
        ),
        ColumnMapping(
            source_name="Gender",
            target_name="student_gender",
            data_type="char(10)",
            nullable=True,
            cleaning_rules=["trim", "normalize_gender"],
            description="Student gender (duplicated from Students table)",
        ),
        ColumnMapping(
            source_name="CurLevel",
            target_name="student_current_level",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_int"],
            description="Student's current academic level",
        ),
        # Receipt and term information
        ColumnMapping(
            source_name="TermName",
            target_name="term_name",
            data_type="nvarchar(80)",
            nullable=True,
            cleaning_rules=["trim", "fix_encoding"],
            description="Human-readable term name",
        ),
        ColumnMapping(
            source_name="ReceiptType",
            target_name="receipt_type",
            data_type="nvarchar(100)",
            nullable=True,
            cleaning_rules=["trim"],
            description="Type or category of receipt",
            examples=["Tuition", "Registration", "Late Fee", "Refund"],
        ),
        # Administrative fields
        ColumnMapping(
            source_name="Notes",
            target_name="notes",
            data_type="varchar(500)",
            nullable=True,
            cleaning_rules=["trim", "fix_encoding"],
            description="Administrative notes about payment",
        ),
        ColumnMapping(
            source_name="Receiver",
            target_name="received_by_user_id",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_int"],
            description="User ID who received/processed payment",
        ),
        ColumnMapping(
            source_name="Deleted",
            target_name="is_deleted",
            data_type="int",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_boolean"],
            validation_priority=2,
            description="Deletion flag (1=deleted, 0=active)",
        ),
        ColumnMapping(
            source_name="Cash_received",
            target_name="cash_received_flag",
            data_type="int",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_boolean"],
            description="Flag indicating if cash was physically received",
        ),
        # Auto-generated identity column - not mapped as it's handled by DB
        # IPK field is not included in mappings as it's an identity column
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
    # Cleaning configuration - critical for financial accuracy
    cleaning_rules={
        "date_format": "mssql_datetime",  # Standard MSSQL datetime format
        "null_patterns": ["NULL", "NA", "", " ", "0.00", "-1"],
        "encoding_fix": True,  # Names and notes may have encoding issues
        "currency_precision": 2,  # Financial amounts need proper precision
        "gender_normalization": True,  # Standardize M/F values
    },
    # Performance settings
    chunk_size=2500,  # Financial data, moderate chunk size
    # Quality thresholds - very strict for financial data
    min_completeness_score=90.0,  # Financial records should be complete
    min_consistency_score=95.0,  # Financial data must be highly consistent
    max_error_rate=2.0,  # Very strict for money transactions
    # Business context
    dependencies=["students", "terms"],  # Requires students and optionally terms
    target_django_model="apps.finance.models.ReceiptHeader",
    validator_class=ReceiptHeaderValidator,
)
