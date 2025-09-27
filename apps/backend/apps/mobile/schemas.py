"""Mobile app Pydantic schemas for Django-Ninja integration.

These schemas define the input/output data structures for mobile API endpoints.
Django-Ninja uses Pydantic for automatic validation and serialization.
"""

from datetime import datetime

from ninja import Schema


class AttendanceSchema(Schema):
    """Schema for attendance record data."""

    id: int
    student_id: int
    class_header_id: int
    session_date: datetime
    status: str
    check_in_time: datetime | None = None
    check_out_time: datetime | None = None
    notes: str | None = None
    recorded_by: str | None = None
    created_at: datetime
    updated_at: datetime


class AttendanceCreateSchema(Schema):
    """Schema for creating attendance records."""

    student_id: int
    class_header_id: int
    session_date: datetime
    status: str
    check_in_time: datetime | None = None
    check_out_time: datetime | None = None
    notes: str | None = None


class AttendanceUpdateSchema(Schema):
    """Schema for updating attendance records."""

    status: str | None = None
    check_in_time: datetime | None = None
    check_out_time: datetime | None = None
    notes: str | None = None


class StudentProfileSchema(Schema):
    """Schema for student profile data."""

    id: int
    student_id: str
    full_name: str
    email: str
    phone: str | None = None
    current_status: str
    primary_major: str | None = None
    enrollment_date: datetime | None = None
    graduation_date: datetime | None = None


class ClassScheduleSchema(Schema):
    """Schema for class schedule data."""

    id: int
    course_code: str
    course_name: str
    section: str
    instructor: str | None = None
    schedule: str | None = None
    location: str | None = None
    term: str


class GradeSchema(Schema):
    """Schema for grade data."""

    id: int
    course_code: str
    course_name: str
    section: str
    grade: str | None = None
    points: float | None = None
    credits: float
    term: str
    instructor: str | None = None


class NotificationSchema(Schema):
    """Schema for mobile notifications."""

    id: int
    title: str
    message: str
    category: str
    is_read: bool = False
    created_at: datetime
    expires_at: datetime | None = None


# Legacy alias for backward compatibility with any remaining test references
AttendanceSerializer = AttendanceSchema
