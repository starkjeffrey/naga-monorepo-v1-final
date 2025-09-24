"""
Receipt Items Table Configuration

Configuration for processing the Receipt_Items table - individual line items for receipts.
This table contains 16 columns representing detailed line items that make up receipt totals.
Essential for detailed financial reporting and audit trails.
"""

from ..configs.base import ColumnMapping, TableConfig
from ..validators.receipt_items import ReceiptItemValidator

RECEIPT_ITEMS_CONFIG = TableConfig(
    table_name="receipt_items",
    source_file_pattern="receipt_items.csv",
    description="Receipt line items with individual charges, quantities, and amounts",
    # Table naming follows convention
    raw_table_name="raw_receipt_items",
    cleaned_table_name="cleaned_receipt_items",
    validated_table_name="validated_receipt_items",
    column_mappings=[
        # Foreign key identifiers linking to receipts and students
        ColumnMapping(
            source_name="ID",
            target_name="student_id",
            data_type="nvarchar(20)",
            nullable=False,
            cleaning_rules=["trim", "uppercase"],
            validation_priority=1,  # Critical foreign key to students
            description="Student ID associated with this line item",
            examples=["ST001", "ST002", "MS2010001"],
        ),
        ColumnMapping(
            source_name="ReceiptNo",
            target_name="receipt_number",
            data_type="nvarchar(50)",
            nullable=True,
            cleaning_rules=["trim"],
            validation_priority=1,  # Links to receipt header
            description="Receipt number this line item belongs to",
        ),
        ColumnMapping(
            source_name="ReceiptID",
            target_name="receipt_id",
            data_type="nvarchar(250)",
            nullable=False,
            cleaning_rules=["trim", "uppercase"],
            validation_priority=1,  # Critical foreign key to receipt headers
            description="Receipt identifier linking to Receipt_Headers table",
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
        # Context information
        ColumnMapping(
            source_name="TermID",
            target_name="term_id",
            data_type="nvarchar(50)",
            nullable=True,
            cleaning_rules=["trim", "uppercase"],
            validation_priority=2,  # Important for term-based billing
            description="Academic term this charge applies to",
            examples=["2009T1E", "2009T2E", "2010T1E"],
        ),
        ColumnMapping(
            source_name="Program",
            target_name="program_id",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_int"],
            validation_priority=2,
            description="Program ID associated with this charge",
        ),
        # Line item details - core business data
        ColumnMapping(
            source_name="Item",
            target_name="item_description",
            data_type="nvarchar(250)",
            nullable=False,
            cleaning_rules=["trim", "fix_encoding"],
            validation_priority=1,  # Critical for understanding charges
            description="Description of the charged item or service",
            examples=["Tuition - Term 1", "Registration Fee", "Late Payment Fee", "Books", "Lab Fee"],
        ),
        ColumnMapping(
            source_name="UnitCost",
            target_name="unit_cost",
            data_type="nvarchar(50)",  # Note: stored as nvarchar, needs parsing
            nullable=True,
            cleaning_rules=["trim", "parse_float"],
            validation_priority=2,  # Important for cost calculations
            description="Cost per unit (stored as text, needs parsing)",
        ),
        ColumnMapping(
            source_name="Quantity",
            target_name="quantity",
            data_type="nvarchar(150)",  # Note: stored as nvarchar, needs parsing
            nullable=True,
            cleaning_rules=["trim", "parse_float"],
            validation_priority=2,  # Important for quantity calculations
            description="Quantity of items charged (stored as text, needs parsing)",
        ),
        ColumnMapping(
            source_name="Discount",
            target_name="discount_amount",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_float"],
            validation_priority=2,
            description="Discount applied to this line item",
        ),
        ColumnMapping(
            source_name="Amount",
            target_name="line_total",
            data_type="float",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_float"],
            validation_priority=1,  # Critical for financial accuracy
            description="Total amount for this line item (quantity * unit_cost - discount)",
        ),
        # Administrative fields
        ColumnMapping(
            source_name="Notes",
            target_name="notes",
            data_type="nvarchar(100)",
            nullable=True,
            cleaning_rules=["trim", "fix_encoding"],
            description="Additional notes or comments about this line item",
        ),
        ColumnMapping(
            source_name="Deleted",
            target_name="is_deleted",
            data_type="int",
            nullable=True,
            cleaning_rules=["null_standardize", "parse_int"],
            validation_priority=2,
            description="Deletion flag (1=deleted, 0=active)",
        ),
        # Auto-generated identity column - not mapped as it's handled by DB
        # IPK field is not included in mappings as it's an identity column
    ],
    # Cleaning configuration - handle text-stored numbers
    cleaning_rules={
        "null_patterns": ["NULL", "NA", "", " ", "0.00", "-1"],
        "encoding_fix": True,  # Item descriptions may have encoding issues
        "currency_precision": 2,  # Financial amounts need proper precision
        "parse_text_numbers": True,  # UnitCost and Quantity stored as text
    },
    # Performance settings
    chunk_size=3000,  # Line items table, can handle larger chunks
    # Quality thresholds - strict for financial line items
    min_completeness_score=85.0,  # Line items should be fairly complete
    min_consistency_score=90.0,  # Financial data must be consistent
    max_error_rate=5.0,  # Strict for financial transactions
    # Business context
    dependencies=["receipt_headers"],  # Must have receipt headers first
    target_django_model="apps.finance.models.ReceiptItem",
    validator_class=ReceiptItemValidator,
)
