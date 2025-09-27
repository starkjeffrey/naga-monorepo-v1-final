"""Scheduling app constants and configuration values.

Centralizes hardcoded values and thresholds used throughout the scheduling app
to improve maintainability and make policy changes easier.
"""

# Reading Class Configuration
READING_CLASS_CONVERSION_THRESHOLD = 15
READING_CLASS_MAX_TARGET_ENROLLMENT = 15

# Tier Thresholds for Reading Classes
READING_CLASS_TIER_THRESHOLDS = {
    "TIER_1": 2,  # 1-2 students
    "TIER_2": 5,  # 3-5 students
    "TIER_3": 15,  # 6-15 students
}

# Class Configuration
DEFAULT_MAX_ENROLLMENT = 30
SECTION_ID_PATTERN = r"^[A-Z]$"

# Session Configuration
MIN_SESSION_NUMBER = 1
MAX_SESSION_NUMBER = 5

# Meeting Days
VALID_MEETING_DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]

# Test Period Reset Configuration
STANDARD_FINAL_OFFSET_DAYS = 14  # Days before term end for standard final

# Grade Weight Constraints
MIN_GRADE_WEIGHT = 0.000
MAX_GRADE_WEIGHT = 1.000

# Language Division Identifier
LANGUAGE_DIVISION_SHORT_NAME = "LANG"
