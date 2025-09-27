"""Enrollment app constants for business rules and thresholds.

This module centralizes all hardcoded values and business rules for the
enrollment system to improve maintainability and make policy changes easier.
"""

from decimal import Decimal

# GPA Thresholds
HIGH_GPA_THRESHOLD = Decimal("3.5")  # B+ average (3.5 on 4.0 scale)
PASSING_GRADE_THRESHOLD = Decimal("2.0")  # D grade (2.0 on 4.0 scale)
MIN_PREREQUISITE_GRADE = Decimal("2.0")  # D or better for prerequisites

# Credit and Course Limits
MAX_COURSES_PER_TERM = 3  # Maximum courses per term
MAX_CREDITS_PER_TERM = 9  # Maximum credits per term (3 courses * 3 credits each)

# Override Permissions
CAN_MANAGE_ENROLLMENTS = "enrollment.can_manage_enrollments"
CAN_OVERRIDE_CAPACITY = "enrollment.can_override_capacity"
CAN_OVERRIDE_PREREQUISITES = "enrollment.can_override_prerequisites"
CAN_OVERRIDE_CREDIT_LIMITS = "enrollment.can_override_credit_limits"

# Enrollment Status Constants (matching model choices)
ENROLLMENT_STATUS_ENROLLED = "ENROLLED"
ENROLLMENT_STATUS_DROPPED = "DROPPED"
ENROLLMENT_STATUS_COMPLETED = "COMPLETED"
ENROLLMENT_STATUS_FAILED = "FAILED"

# Program Enrollment Status Constants
PROGRAM_STATUS_ACTIVE = "ACTIVE"
PROGRAM_STATUS_INACTIVE = "INACTIVE"
PROGRAM_STATUS_COMPLETED = "COMPLETED"
PROGRAM_STATUS_WITHDRAWN = "WITHDRAWN"

# System User Configuration
SYSTEM_USER_EMAIL = "system@naga-sis.local"
SYSTEM_USER_FIRST_NAME = "System"
SYSTEM_USER_LAST_NAME = "User"

# Grade Scale Configuration
GPA_SCALE_MAX = Decimal("4.0")  # 4.0 scale maximum
GRADE_POINTS = {
    "A+": Decimal("4.0"),
    "A": Decimal("4.0"),
    "A-": Decimal("3.7"),
    "B+": Decimal("3.3"),
    "B": Decimal("3.0"),
    "B-": Decimal("2.7"),
    "C+": Decimal("2.3"),
    "C": Decimal("2.0"),
    "C-": Decimal("1.7"),
    "D+": Decimal("1.3"),
    "D": Decimal("1.0"),
    "D-": Decimal("0.7"),
    "F": Decimal("0.0"),
}

# Time Configuration for Schedule Conflicts
SCHEDULE_BUFFER_MINUTES = 0  # No buffer time between classes for now
DEFAULT_CLASS_DURATION_MINUTES = 50  # Default class duration

# Days of Week Constants
WEEKDAYS = {
    "MON": "Monday",
    "TUE": "Tuesday",
    "WED": "Wednesday",
    "THU": "Thursday",
    "FRI": "Friday",
    "SAT": "Saturday",
    "SUN": "Sunday",
}

# Course Type Constants
COURSE_TYPE_ACADEMIC = "ACAD"
COURSE_TYPE_LANGUAGE = "LANG"

# Validation Messages
MESSAGES = {
    "capacity_full": "Class is at capacity. No spots available.",
    "prerequisite_missing": "Student does not meet prerequisite requirements.",
    "schedule_conflict": "Schedule conflict detected with existing enrollment.",
    "already_enrolled": "Student is already enrolled in this course.",
    "credit_limit_exceeded": "Enrollment would exceed maximum credits per term.",
    "course_limit_exceeded": "Enrollment would exceed maximum courses per term.",
    "wrong_major": "Course is not available for student's current major.",
    "course_closed": "Course is closed for enrollment.",
    "financial_hold": "Student has a financial hold preventing enrollment.",
    "academic_hold": "Student has an academic hold preventing enrollment.",
}
