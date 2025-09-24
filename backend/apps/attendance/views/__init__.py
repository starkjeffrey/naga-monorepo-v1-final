"""Attendance app views for real-time attendance tracking.

This module provides comprehensive attendance management including:
- Real-time attendance marking with HTMX
- Class roster management with quick actions
- Barcode/QR code scanning for attendance
- Attendance reporting and analytics
- Mobile-optimized interfaces for teachers
"""

from .attendance_views import (
    AttendanceDashboardView,
    attendance_report,
    attendance_roster,
    bulk_attendance_update,
    class_attendance_view,
    mark_attendance,
    quick_mark_all,
    student_attendance_search,
)

__all__ = [
    "AttendanceDashboardView",
    "attendance_report",
    "attendance_roster",
    "bulk_attendance_update",
    "class_attendance_view",
    "mark_attendance",
    "quick_mark_all",
    "student_attendance_search",
]
