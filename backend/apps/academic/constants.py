"""Academic app constants.

This module contains constants used throughout the academic app to avoid
magic numbers and improve code maintainability.
"""

from decimal import Decimal


class AcademicConstants:
    """Constants for academic operations."""

    # Grade thresholds
    PASSING_GRADE = Decimal("60.00")  # D+ or better
    MINIMUM_CUMULATIVE_GPA = Decimal("2.0")
    ACADEMIC_PROBATION_GPA = Decimal("1.7")

    # Transfer credit limits
    MAX_TRANSFER_CREDITS = 60
    TRANSFER_CREDIT_RATIO = Decimal("1.5")  # Max internal credits per external credit

    # Progress display thresholds
    COMPLETION_FULL = 100
    COMPLETION_GOOD = 75
    COMPLETION_WARNING = 50

    # Academic standing
    GRADUATION_MINIMUM_CREDITS = 120
    RESIDENCY_REQUIREMENT_CREDITS = 30  # Minimum credits required at institution

    # Time limits
    MAX_DEGREE_COMPLETION_YEARS = 8
    ACADEMIC_PROBATION_TERMS = 2

    # Course level ranges
    LOWER_DIVISION_MIN = 100
    LOWER_DIVISION_MAX = 299
    UPPER_DIVISION_MIN = 300
    UPPER_DIVISION_MAX = 499
    GRADUATE_LEVEL_MIN = 500

    # Validation limits
    MAX_CREDIT_HOURS_PER_COURSE = 6
    MIN_CREDIT_HOURS_PER_COURSE = 1
    MAX_COURSES_PER_TERM = 8
    MIN_COURSES_PER_TERM = 1

    # Administrative
    COURSE_CODE_MAX_LENGTH = 10
    COURSE_TITLE_MAX_LENGTH = 200
    REQUIREMENT_NAME_MAX_LENGTH = 200
    INSTITUTION_NAME_MAX_LENGTH = 200

    # Business rules
    REPEAT_COURSE_LIMIT = 3
    WITHDRAWAL_LIMIT_PER_TERM = 2
    PREREQUISITE_GRADE_REQUIREMENT = PASSING_GRADE

    # Division names
    ACADEMIC_DIVISION_NAME = "Academic Division"
    LANGUAGE_DIVISION_NAME = "Language Division"

    # BA Degree Requirements
    BA_TOTAL_REQUIREMENTS = 43
    BA_TOTAL_CREDITS_REQUIRED = 129

    # MA Degree Requirements
    MA_TOTAL_REQUIREMENTS = 24
    MA_TOTAL_CREDITS_REQUIRED = 60

    # Late attendance (from attendance app)
    LATE_THRESHOLD_MINUTES = 15

    # Completion percentages for progress tracking
    COMPLETION_PERCENTAGE_FULL = 100
    COMPLETION_PERCENTAGE_EXCELLENT = 90
    COMPLETION_PERCENTAGE_GOOD = 75
    COMPLETION_PERCENTAGE_HALFWAY = 50
    COMPLETION_PERCENTAGE_STARTED = 25

    # Maximum sequence numbers
    MAX_BA_SEQUENCE_NUMBER = 50
    MAX_MA_SEQUENCE_NUMBER = 30
