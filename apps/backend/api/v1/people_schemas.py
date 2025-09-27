"""Schema definitions for people API endpoints.

This module contains Django-Ninja schemas for serializing and deserializing
people, student profiles, teacher profiles, and related data. All schemas
are designed to support React queries and maintain consistency with the
frontend type system.
"""

from datetime import date

from ninja import Schema


class PersonBaseSchema(Schema):
    """Base person information schema."""

    unique_id: str
    family_name: str
    personal_name: str
    full_name: str
    khmer_name: str
    preferred_gender: str

    # Contact information
    school_email: str | None = None
    personal_email: str | None = None

    # Birth and citizenship
    date_of_birth: date | None = None
    birth_province: str | None = None
    citizenship: str

    # Computed properties
    age: int | None = None
    display_name: str
    current_photo_url: str | None = None
    current_thumbnail_url: str | None = None


class PhoneNumberSchema(Schema):
    """Phone number schema."""

    id: int
    number: str
    comment: str
    is_preferred: bool
    is_telegram: bool
    is_verified: bool


class EmergencyContactSchema(Schema):
    """Emergency contact schema."""

    id: int
    name: str
    relationship: str
    primary_phone: str
    secondary_phone: str
    email: str
    address: str
    is_primary: bool


class StudentProfileSchema(Schema):
    """Student profile information schema."""

    id: int
    student_id: int
    formatted_student_id: str
    legacy_ipk: int | None = None

    # Student characteristics
    is_monk: bool
    is_transfer_student: bool
    current_status: str
    study_time_preference: str
    last_enrollment_date: date | None = None

    # Computed properties
    is_student_active: bool
    has_major_conflict: bool

    # Related major info (computed)
    declared_major_name: str | None = None
    enrollment_history_major_name: str | None = None


class TeacherProfileSchema(Schema):
    """Teacher profile information schema."""

    id: int
    terminal_degree: str
    status: str
    start_date: date
    end_date: date | None = None
    is_teacher_active: bool


class StaffProfileSchema(Schema):
    """Staff profile information schema."""

    id: int
    position: str
    status: str
    start_date: date
    end_date: date | None = None
    is_staff_active: bool


class PersonDetailSchema(PersonBaseSchema):
    """Detailed person information with all profiles."""

    # Related profiles (optional)
    student_profile: StudentProfileSchema | None = None
    teacher_profile: TeacherProfileSchema | None = None
    staff_profile: StaffProfileSchema | None = None

    # Related contact data
    phone_numbers: list[PhoneNumberSchema] = []
    emergency_contacts: list[EmergencyContactSchema] = []

    # Role flags
    has_student_role: bool
    has_teacher_role: bool
    has_staff_role: bool


class StudentListSchema(Schema):
    """Simplified student schema for lists."""

    person_id: int
    student_id: int
    formatted_student_id: str
    full_name: str
    khmer_name: str
    school_email: str | None = None
    current_status: str
    study_time_preference: str
    is_monk: bool
    current_thumbnail_url: str | None = None
    declared_major_name: str | None = None


class TeacherListSchema(Schema):
    """Simplified teacher schema for lists."""

    person_id: int
    full_name: str
    khmer_name: str
    school_email: str | None = None
    terminal_degree: str
    status: str
    is_teacher_active: bool
    current_thumbnail_url: str | None = None


class StaffListSchema(Schema):
    """Simplified staff schema for lists."""

    person_id: int
    full_name: str
    khmer_name: str
    school_email: str | None = None
    position: str
    status: str
    is_staff_active: bool
    current_thumbnail_url: str | None = None


class PersonSearchResultSchema(Schema):
    """Schema for person search results."""

    person_id: int
    full_name: str
    khmer_name: str
    school_email: str | None = None
    current_thumbnail_url: str | None = None

    # Role information
    roles: list[str]  # e.g., ['student', 'teacher']

    # Student info if applicable
    student_id: int | None = None
    formatted_student_id: str | None = None
    student_status: str | None = None

    # Teacher info if applicable
    teacher_status: str | None = None
    position: str | None = None  # Staff position


# Request schemas for creating/updating
class CreatePersonSchema(Schema):
    """Schema for creating a new person."""

    family_name: str
    personal_name: str
    khmer_name: str = ""
    preferred_gender: str = "X"  # Default to prefer not to say

    # Optional fields
    school_email: str | None = None
    personal_email: str | None = None
    date_of_birth: date | None = None
    birth_province: str | None = None
    citizenship: str = "KH"


class UpdatePersonSchema(Schema):
    """Schema for updating person information."""

    family_name: str | None = None
    personal_name: str | None = None
    khmer_name: str | None = None
    preferred_gender: str | None = None
    school_email: str | None = None
    personal_email: str | None = None
    date_of_birth: date | None = None
    birth_province: str | None = None
    citizenship: str | None = None


class CreateStudentProfileSchema(Schema):
    """Schema for creating student profile."""

    student_id: int
    is_monk: bool = False
    is_transfer_student: bool = False
    study_time_preference: str = "evening"
    current_status: str = "ACTIVE"


class UpdateStudentProfileSchema(Schema):
    """Schema for updating student profile."""

    is_monk: bool | None = None
    is_transfer_student: bool | None = None
    study_time_preference: str | None = None
    current_status: str | None = None


# Pagination schemas
class PaginatedStudentsSchema(Schema):
    """Paginated students response."""

    count: int
    next: str | None = None
    previous: str | None = None
    results: list[StudentListSchema]


class PaginatedTeachersSchema(Schema):
    """Paginated teachers response."""

    count: int
    next: str | None = None
    previous: str | None = None
    results: list[TeacherListSchema]


class PaginatedStaffSchema(Schema):
    """Paginated staff response."""

    count: int
    next: str | None = None
    previous: str | None = None
    results: list[StaffListSchema]


class PaginatedSearchResultsSchema(Schema):
    """Paginated search results response."""

    count: int
    next: str | None = None
    previous: str | None = None
    results: list[PersonSearchResultSchema]
