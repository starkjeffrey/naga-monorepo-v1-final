"""Constants for scholarships app.

Centralized configuration values for scholarships, sponsors, and financial aid
to improve maintainability and reduce magic strings throughout the codebase.
"""

from decimal import Decimal

# Scholarship Types
SCHOLARSHIP_TYPES = {
    "MERIT": "Merit-Based",
    "NEED": "Need-Based",
    "SPONSORED": "Sponsor-Funded",
    "EMERGENCY": "Emergency Aid",
    "ATHLETIC": "Athletic Scholarship",
    "ACADEMIC": "Academic Excellence",
}

# Award Status Options
SCHOLARSHIP_STATUSES = {
    "PENDING": "Pending Review",
    "APPROVED": "Approved",
    "ACTIVE": "Active",
    "SUSPENDED": "Suspended",
    "COMPLETED": "Completed",
    "CANCELLED": "Cancelled",
}

# Sponsorship Types
SPONSORSHIP_TYPES = {
    "FULL": "Full Sponsorship",
    "PARTIAL": "Partial Sponsorship",
    "EMERGENCY": "Emergency Support",
    "SCHOLARSHIP": "Scholarship",
}

# Standard Discount Percentages
STANDARD_DISCOUNTS = {
    "FULL_SPONSORSHIP": Decimal("100.00"),
    "PARTIAL_75": Decimal("75.00"),
    "PARTIAL_50": Decimal("50.00"),
    "PARTIAL_25": Decimal("25.00"),
    "NO_DISCOUNT": Decimal("0.00"),
}

# Business Rules
MAX_DISCOUNT_PERCENTAGE = Decimal("100.00")
MIN_DISCOUNT_PERCENTAGE = Decimal("0.00")

# Scholarship business rules
SCHOLARSHIPS_STACK = False  # Never stack scholarships
SCHOLARSHIPS_APPLY_TO_FEES = False  # Only apply to tuition
MONKS_USE_FIXED_AMOUNTS = True  # Monks get fixed amounts, others get percentages

# NGO/Sponsor Configuration
DEFAULT_MOU_DURATION_YEARS = 3
DEFAULT_ADMIN_FEE_EXEMPTION_YEARS = 1

# Common Sponsor Organizations (for factories and validation)
COMMON_SPONSORS = {
    "CRST": "Christian Reformed Service Team",
    "PLF": "Presbyterian Leadership Foundation",
    "USAID": "United States Agency for International Development",
    "KOICA": "Korea International Cooperation Agency",
    "JICA": "Japan International Cooperation Agency",
    "WFP": "World Food Programme",
    "UNESCO": "United Nations Educational, Scientific and Cultural Organization",
    "UNDP": "United Nations Development Programme",
    "ADB": "Asian Development Bank",
    "WORLDBANK": "World Bank Group",
    "AUSAID": "Australian Aid Programme",
    "CIDA": "Canadian International Development Agency",
    "DFID": "Department for International Development",
    "GIZ": "Deutsche Gesellschaft für Internationale Zusammenarbeit",
    "AFD": "Agence Française de Développement",
    "DANIDA": "Danish International Development Agency",
    "SIDA": "Swedish International Development Cooperation Agency",
    "NORAD": "Norwegian Agency for Development Cooperation",
}

# Reporting Configuration
BILLING_AFFECTING_STATUSES = ["APPROVED", "ACTIVE", "SUSPENDED", "CANCELLED"]

# Merit Scholarship Definitions
MERIT_SCHOLARSHIP_TYPES = [
    "Academic Excellence Award",
    "Merit-Based Achievement Award",
    "Leadership Development Scholarship",
    "Community Service Award",
    "Outstanding Student Scholarship",
    "First Generation Student Award",
    "Rural Student Support Fund",
    "Women in Leadership Scholarship",
    "STEM Excellence Award",
    "Language Proficiency Scholarship",
    "Cultural Heritage Scholarship",
    "Environmental Leadership Award",
    "Innovation and Technology Scholarship",
]

# Need-Based Aid Amounts (in USD)
STANDARD_NEED_BASED_AMOUNTS = [
    Decimal("1000.00"),
    Decimal("1500.00"),
    Decimal("2000.00"),
    Decimal("2500.00"),
    Decimal("3000.00"),
]

# Emergency Aid Amounts (in USD)
EMERGENCY_AID_AMOUNTS = [Decimal("200.00"), Decimal("500.00"), Decimal("1000.00")]

# Validation Constants
MAX_SCHOLARSHIP_NAME_LENGTH = 200
MAX_SPONSOR_CODE_LENGTH = 10
MAX_SPONSOR_NAME_LENGTH = 100
MAX_CONTACT_NAME_LENGTH = 100
MAX_PHONE_LENGTH = 20

# GPA Requirements (if used for merit scholarships)
MIN_GPA_FOR_MERIT = Decimal("3.0")
MIN_GPA_FOR_ACADEMIC_EXCELLENCE = Decimal("3.5")

# Default Scholarship Conditions
DEFAULT_MERIT_CONDITIONS = (
    "Maintain minimum GPA of 3.0, demonstrate continued merit achievement, and submit progress reports each semester."
)

DEFAULT_NEED_CONDITIONS = (
    "Demonstrate financial need, maintain academic standing, and submit financial documentation annually."
)

DEFAULT_EMERGENCY_CONDITIONS = "Demonstrate urgent financial need and maintain enrollment."

# File Paths (configurable)
DEFAULT_V0_FIXTURE_PATH = "data/fixtures/sponsors_v0.json"
BACKUP_V0_FIXTURE_PATH = "scratchpad/sponsors_v0.json"

# Audit and Logging
SCHOLARSHIP_CHANGE_LOG_ACTIONS = [
    "scholarship_created",
    "scholarship_status_changed",
    "scholarship_amount_changed",
    "scholarship_suspended",
    "scholarship_cancelled",
    "sponsorship_created",
    "sponsorship_ended",
    "sponsor_mou_updated",
]
