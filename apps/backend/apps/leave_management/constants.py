"""Constants for the leave management app."""

from decimal import Decimal

# Contract Types
CONTRACT_TYPE_FULL_TIME = "FULL_TIME"
CONTRACT_TYPE_PART_TIME = "PART_TIME"
CONTRACT_TYPE_CONTRACT = "CONTRACT"
CONTRACT_TYPE_SUBSTITUTE = "SUBSTITUTE"

CONTRACT_TYPE_CHOICES = [
    (CONTRACT_TYPE_FULL_TIME, "Full Time"),
    (CONTRACT_TYPE_PART_TIME, "Part Time"),
    (CONTRACT_TYPE_CONTRACT, "Contract"),
    (CONTRACT_TYPE_SUBSTITUTE, "Substitute"),
]

# Default Leave Policies by Contract Type
DEFAULT_LEAVE_POLICIES = {
    CONTRACT_TYPE_FULL_TIME: {
        "SICK": {
            "annual_days": Decimal("10"),
            "accrual_rate": Decimal("0.833"),  # 10 days / 12 months
            "carries_forward": False,
            "max_carryover": None,
            "requires_documentation": True,
            "max_consecutive_days": 5,
            "advance_notice_days": 0,
        },
        "PERSONAL": {
            "annual_days": Decimal("5"),
            "accrual_rate": Decimal("0"),  # Granted annually
            "carries_forward": False,
            "max_carryover": None,
            "requires_documentation": False,
            "max_consecutive_days": 3,
            "advance_notice_days": 2,
        },
        "VACATION": {
            "annual_days": Decimal("15"),
            "accrual_rate": Decimal("1.25"),  # 15 days / 12 months
            "carries_forward": True,
            "max_carryover": Decimal("5"),
            "requires_documentation": False,
            "max_consecutive_days": None,
            "advance_notice_days": 14,
        },
    },
    CONTRACT_TYPE_PART_TIME: {
        "SICK": {
            "annual_days": Decimal("5"),
            "accrual_rate": Decimal("0.417"),  # 5 days / 12 months
            "carries_forward": False,
            "max_carryover": None,
            "requires_documentation": True,
            "max_consecutive_days": 3,
            "advance_notice_days": 0,
        },
        "PERSONAL": {
            "annual_days": Decimal("2"),
            "accrual_rate": Decimal("0"),
            "carries_forward": False,
            "max_carryover": None,
            "requires_documentation": False,
            "max_consecutive_days": 2,
            "advance_notice_days": 2,
        },
        "VACATION": {
            "annual_days": Decimal("7"),
            "accrual_rate": Decimal("0.583"),
            "carries_forward": True,
            "max_carryover": Decimal("3"),
            "requires_documentation": False,
            "max_consecutive_days": None,
            "advance_notice_days": 14,
        },
    },
    CONTRACT_TYPE_CONTRACT: {
        "SICK": {
            "annual_days": Decimal("3"),
            "accrual_rate": Decimal("0"),
            "carries_forward": False,
            "max_carryover": None,
            "requires_documentation": True,
            "max_consecutive_days": 3,
            "advance_notice_days": 0,
        },
        "UNPAID": {
            "annual_days": Decimal("10"),
            "accrual_rate": Decimal("0"),
            "carries_forward": False,
            "max_carryover": None,
            "requires_documentation": True,
            "max_consecutive_days": 10,
            "advance_notice_days": 7,
        },
    },
}

# Notification Settings
NOTIFICATION_CHANNELS = {
    "EMAIL": "email",
    "SMS": "sms",
    "PUSH": "push",
    "IN_APP": "in_app",
}

DEFAULT_NOTIFICATION_SETTINGS = {
    "leave_request_submitted": ["EMAIL", "IN_APP"],
    "leave_request_approved": ["EMAIL", "SMS", "IN_APP", "PUSH"],
    "leave_request_rejected": ["EMAIL", "IN_APP", "PUSH"],
    "substitute_assigned": ["EMAIL", "SMS", "IN_APP", "PUSH"],
    "substitute_confirmed": ["EMAIL", "IN_APP"],
    "substitute_declined": ["EMAIL", "SMS", "IN_APP", "PUSH"],
    "reminder_upcoming_leave": ["EMAIL", "IN_APP"],
    "roster_shared": ["EMAIL", "IN_APP"],
}

# Timing Constants
SUBSTITUTE_ASSIGNMENT_DEADLINE_HOURS = 24  # Hours before leave starts to assign substitute
LEAVE_REQUEST_AUTO_EXPIRE_DAYS = 30  # Days to auto-expire unprocessed requests
ROSTER_SHARE_DAYS_BEFORE = 1  # Days before leave to share roster with substitute
BALANCE_RESET_MONTH = 1  # January - when annual balances reset

# Substitute Coverage Rules
SUBSTITUTE_REQUIRED_MIN_DAYS = 1  # Minimum days of leave requiring substitute
SUBSTITUTE_AUTO_ASSIGN_THRESHOLD = 3  # Days - auto-suggest substitute for longer leaves
MAX_CLASSES_PER_SUBSTITUTE_PER_DAY = 6  # Maximum classes a substitute can cover per day

# Report Settings
MONTHLY_REPORT_GENERATION_DAY = 5  # Day of month to generate previous month's report
QUARTERLY_REPORT_MONTHS = [3, 6, 9, 12]  # March, June, September, December
ANNUAL_REPORT_MONTH = 12  # December

# Leave Request Priority Thresholds
EMERGENCY_NOTICE_HOURS = 24  # Less than 24 hours notice = emergency
HIGH_PRIORITY_NOTICE_DAYS = 3  # Less than 3 days notice = high priority

# Validation Rules
MIN_LEAVE_DURATION_HOURS = 1  # Minimum leave duration
MAX_LEAVE_DURATION_DAYS = 365  # Maximum leave duration in days
MAX_ADVANCE_REQUEST_DAYS = 365  # How far in advance can request leave

# Permission Transfer Settings
PERMISSION_GRANT_BUFFER_HOURS = 2  # Hours before class to grant permissions
PERMISSION_REVOKE_DELAY_HOURS = 24  # Hours after leave ends to revoke permissions

# Success Rate Targets (for reporting)
SUBSTITUTE_COVERAGE_TARGET_PERCENT = 80  # Target: 80% of requests have substitutes
APPROVAL_TIME_TARGET_HOURS = 48  # Target: Approve/reject within 48 hours
SUBSTITUTE_CONFIRMATION_TARGET_HOURS = 24  # Target: Substitute confirms within 24 hours