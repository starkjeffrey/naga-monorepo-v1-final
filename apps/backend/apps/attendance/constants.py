"""Attendance app constants.

This module contains constants used throughout the attendance app to avoid
magic numbers and improve code maintainability.
"""


class AttendanceConstants:
    """Constants for attendance operations."""

    # Time thresholds
    LATE_THRESHOLD_MINUTES = 15  # Minutes after class start to be marked as late

    # Attendance status values
    STATUS_PRESENT = "PRESENT"
    STATUS_ABSENT = "ABSENT"
    STATUS_LATE = "LATE"
    STATUS_EXCUSED = "EXCUSED"

    # Business rules
    MAX_ALLOWED_ABSENCES = 3  # Maximum absences before academic warning
    ATTENDANCE_PASSING_PERCENTAGE = 80  # Minimum attendance percentage required

    # QR Code
    QR_CODE_EXPIRY_MINUTES = 15  # How long a QR code remains valid
    QR_CODE_REFRESH_INTERVAL = 30  # Seconds between QR code refreshes

    # Session tracking
    SESSION_TIMEOUT_MINUTES = 120  # Maximum class session duration
    CHECK_IN_WINDOW_MINUTES = 30  # Window for checking in before/after class start
