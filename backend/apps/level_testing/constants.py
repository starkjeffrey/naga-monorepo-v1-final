"""Level Testing app constants.

Contains configuration values, fee codes, and other constants to avoid
hardcoded values throughout the application per code review recommendations.
"""

from decimal import Decimal

# Test Fee Configuration
DEFAULT_TEST_FEE_AMOUNT = Decimal("5.00")
TEST_FEE_CURRENCY = "USD"


# Test Fee Types and Internal Codes
class TestFeeCode:
    """Internal codes for level testing fees.

    Per user requirements: "All fees should be in a configurable price list
    with internal codes, human names, and prices."
    """

    # Primary test fees
    PLACEMENT_TEST = "LT_PLACEMENT"
    RETEST_FEE = "LT_RETEST"
    LATE_REGISTRATION = "LT_LATE_REG"
    RUSH_PROCESSING = "LT_RUSH"

    # Administrative fees
    APPLICATION_PROCESSING = "LT_APP_PROC"
    DUPLICATE_REVIEW = "LT_DUP_REV"
    DOCUMENT_VERIFICATION = "LT_DOC_VER"

    # Special fees
    MAKEUP_TEST = "LT_MAKEUP"
    REMOTE_TEST = "LT_REMOTE"
    SPECIAL_ACCOMMODATION = "LT_SPECIAL"


# Human-readable fee names
TEST_FEE_NAMES = {
    TestFeeCode.PLACEMENT_TEST: "Placement Test Fee",
    TestFeeCode.RETEST_FEE: "Retake Test Fee",
    TestFeeCode.LATE_REGISTRATION: "Late Registration Fee",
    TestFeeCode.RUSH_PROCESSING: "Rush Processing Fee",
    TestFeeCode.APPLICATION_PROCESSING: "Application Processing Fee",
    TestFeeCode.DUPLICATE_REVIEW: "Duplicate Review Fee",
    TestFeeCode.DOCUMENT_VERIFICATION: "Document Verification Fee",
    TestFeeCode.MAKEUP_TEST: "Makeup Test Fee",
    TestFeeCode.REMOTE_TEST: "Remote Test Fee",
    TestFeeCode.SPECIAL_ACCOMMODATION: "Special Accommodation Fee",
}


# G/L Account Codes (Chart of Accounts Integration)
class GLAccountCode:
    """General Ledger account codes for level testing revenue and expenses.

    Per user requirements: "Support G/L account mapping"
    """

    # Revenue accounts
    TEST_FEE_REVENUE = "4100-LT"
    LATE_FEE_REVENUE = "4110-LT"
    ADMIN_FEE_REVENUE = "4120-LT"

    # Expense accounts (for cost allocation)
    TEST_ADMINISTRATION_EXPENSE = "6100-LT"
    SYSTEM_PROCESSING_EXPENSE = "6110-LT"
    STAFF_TIME_EXPENSE = "6120-LT"

    # Asset accounts (for prepaid fees)
    PREPAID_TEST_FEES = "1200-LT"


# Pricing Tier Mappings for Local/Foreign Rates
class PricingTierCode:
    """Pricing tier codes for local vs foreign student rates.

    Per user requirements: "Support local/foreign rate differentiation"
    """

    LOCAL_STUDENT = "LOCAL"
    FOREIGN_STUDENT = "INTL"
    CORPORATE_SPONSORED = "CORP"
    GOVERNMENT_SPONSORED = "GOVT"
    STAFF_DEPENDENT = "STAFF"


# Default local/foreign rate multipliers
LOCAL_RATE_MULTIPLIER = Decimal("1.0")  # Base rate
FOREIGN_RATE_MULTIPLIER = Decimal("1.5")  # 50% premium for international students

# Application status progression constants
MIN_CONFIDENCE_SCORE_FOR_DUPLICATE = 0.3
HIGH_CONFIDENCE_DUPLICATE_THRESHOLD = 0.8
DEBT_CONCERN_THRESHOLD = Decimal("50.00")

# Test session configuration
DEFAULT_TEST_SESSION_CAPACITY = 20
MAX_TEST_SESSION_CAPACITY = 50
TEST_SESSION_ADVANCE_BOOKING_DAYS = 7

# Duplicate detection algorithm weights (per user requirements)
DUPLICATE_DETECTION_WEIGHTS = {
    "exact_name_match": 0.4,
    "similar_name_match": 0.3,
    "exact_birthdate_match": 0.32,  # DOB_MATCH_WEIGHT * 0.4
    "similar_birthdate_match": 0.18,  # SIMILAR_DOB_WEIGHT * 0.3
    "phone_match": 0.225,  # PHONE_MATCH_WEIGHT * 0.25
    "email_match": 0.18,  # EMAIL_MATCH_WEIGHT * 0.2
    "province_match": 0.06,  # PROVINCE_MATCH_WEIGHT * 0.1
    "program_level_match": 0.08,  # PROGRAM_LEVEL_MATCH_WEIGHT * 0.2
}

# File upload limits
MAX_DOCUMENT_SIZE_MB = 10
ALLOWED_DOCUMENT_TYPES = [".pdf", ".jpg", ".jpeg", ".png", ".doc", ".docx"]

TEST_CONFIRMATION_EMAIL_TEMPLATE = "level_testing/emails/test_confirmation.html"
DUPLICATE_ALERT_EMAIL_TEMPLATE = "level_testing/emails/duplicate_alert.html"
PAYMENT_RECEIPT_EMAIL_TEMPLATE = "level_testing/emails/payment_receipt.html"

# Cache timeout values (in seconds)
DUPLICATE_DETECTION_CACHE_TIMEOUT = 3600  # 1 hour
FEE_CALCULATION_CACHE_TIMEOUT = 1800  # 30 minutes
TEST_SESSION_AVAILABILITY_CACHE_TIMEOUT = 300  # 5 minutes
