"""Schema definitions for enrollment API endpoints.

This module contains Django-Ninja schemas for serializing and deserializing
enrollment data including program enrollments, major declarations, class
enrollments, and related academic data.
"""

from datetime import date
from decimal import Decimal

from ninja import Schema


class MajorSchema(Schema):
    """Major/program schema."""

    id: int
    name: str
    short_name: str
    program_type: str
    degree_type: str
    division_name: str
    cycle_name: str
    is_active: bool


class ProgramEnrollmentSchema(Schema):
    """Program enrollment schema."""

    id: int
    student_id: int
    student_name: str
    major: MajorSchema
    enrollment_type: str
    enrollment_status: str
    division: str
    cycle: str

    # Date tracking
    start_date: date | None = None
    end_date: date | None = None
    expected_graduation: date | None = None

    # Language program specific
    entry_level: int | None = None
    finishing_level: int | None = None

    # Progress tracking
    terms_active: int
    terms_on_hold: int
    overall_gpa: Decimal | None = None

    # Status info
    is_active: bool
    is_current: bool


class MajorDeclarationSchema(Schema):
    """Major declaration schema."""

    id: int
    student_id: int
    student_name: str
    major: MajorSchema
    declaration_date: date
    is_active: bool
    is_prospective: bool
    intended_graduation_term: str | None = None
    notes: str


class ClassHeaderSchema(Schema):
    """Class header (scheduled class) schema."""

    id: int
    class_number: str
    course_code: str
    course_name: str
    term_name: str
    teacher_name: str | None = None
    room_name: str | None = None
    max_enrollment: int | None = None
    current_enrollment: int


class ClassHeaderEnrollmentSchema(Schema):
    """Class header enrollment schema."""

    id: int
    student: dict  # Basic student info
    class_header: ClassHeaderSchema
    enrollment_date: date
    status: str
    grade_override: str | None = None
    is_auditing: bool
    notes: str

    # Financial info
    tuition_waived: bool
    discount_percentage: Decimal | None = None


class StudentEnrollmentSummarySchema(Schema):
    """Student enrollment summary schema."""

    student_id: int
    student_name: str
    current_status: str

    # Program enrollments
    active_program_enrollments: list[ProgramEnrollmentSchema] = []
    major_declarations: list[MajorDeclarationSchema] = []

    # Current term enrollments
    current_class_enrollments: list[ClassHeaderEnrollmentSchema] = []

    # Summary stats
    total_active_enrollments: int
    total_completed_courses: int
    current_term_credit_hours: Decimal


class ClassEnrollmentListSchema(Schema):
    """Simplified class enrollment for lists."""

    id: int
    class_number: str
    course_code: str
    course_name: str
    term_name: str
    student_count: int
    max_enrollment: int | None = None
    enrollment_percentage: float | None = None
    teacher_name: str | None = None


class EnrollmentStatsSchema(Schema):
    """Enrollment statistics schema."""

    total_students: int
    active_students: int
    total_enrollments: int
    current_term_enrollments: int

    # By status
    status_breakdown: dict

    # By program type
    program_type_breakdown: dict

    # By division
    division_breakdown: dict


# Request schemas
class CreateProgramEnrollmentSchema(Schema):
    """Schema for creating program enrollment."""

    student_id: int
    major_id: int
    enrollment_type: str
    division: str
    cycle: str
    start_date: date | None = None
    entry_level: int | None = None


class UpdateProgramEnrollmentSchema(Schema):
    """Schema for updating program enrollment."""

    enrollment_status: str | None = None
    end_date: date | None = None
    expected_graduation: date | None = None
    finishing_level: int | None = None
    overall_gpa: Decimal | None = None


class CreateMajorDeclarationSchema(Schema):
    """Schema for creating major declaration."""

    student_id: int
    major_id: int
    declaration_date: date | None = None
    is_prospective: bool = True
    intended_graduation_term: str | None = None
    notes: str = ""


class CreateClassEnrollmentSchema(Schema):
    """Schema for creating class enrollment."""

    student_id: int
    class_header_id: int
    enrollment_date: date | None = None
    is_auditing: bool = False
    tuition_waived: bool = False
    discount_percentage: Decimal | None = None
    notes: str = ""


class UpdateClassEnrollmentSchema(Schema):
    """Schema for updating class enrollment."""

    status: str | None = None
    grade_override: str | None = None
    is_auditing: bool | None = None
    tuition_waived: bool | None = None
    discount_percentage: Decimal | None = None
    notes: str | None = None


# Pagination schemas
class PaginatedProgramEnrollmentsSchema(Schema):
    """Paginated program enrollments response."""

    count: int
    next: str | None = None
    previous: str | None = None
    results: list[ProgramEnrollmentSchema]


class PaginatedMajorDeclarationsSchema(Schema):
    """Paginated major declarations response."""

    count: int
    next: str | None = None
    previous: str | None = None
    results: list[MajorDeclarationSchema]


class PaginatedClassEnrollmentsSchema(Schema):
    """Paginated class enrollments response."""

    count: int
    next: str | None = None
    previous: str | None = None
    results: list[ClassHeaderEnrollmentSchema]


class PaginatedClassListSchema(Schema):
    """Paginated class list response."""

    count: int
    next: str | None = None
    previous: str | None = None
    results: list[ClassEnrollmentListSchema]
