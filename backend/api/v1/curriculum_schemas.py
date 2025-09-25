"""Schema definitions for curriculum API endpoints.

This module contains Django-Ninja schemas for serializing and deserializing
curriculum data including divisions, cycles, majors, terms, courses, and
academic structure information.
"""

from datetime import date
from decimal import Decimal

from ninja import Schema


class DivisionSchema(Schema):
    """Division schema."""

    id: int
    name: str
    short_name: str
    description: str
    is_active: bool
    display_order: int


class CycleSchema(Schema):
    """Cycle schema."""

    id: int
    name: str
    short_name: str
    description: str
    division: DivisionSchema
    level_order: int
    is_active: bool


class MajorSchema(Schema):
    """Major/program schema."""

    id: int
    name: str
    short_name: str
    description: str
    program_type: str
    degree_type: str
    division: DivisionSchema
    cycle: CycleSchema

    # Academic requirements
    required_credits: Decimal | None = None
    max_terms: int | None = None

    # Status
    is_active: bool
    is_accepting_students: bool
    display_order: int


class TermSchema(Schema):
    """Academic term schema."""

    id: int
    name: str
    short_name: str
    start_date: date
    end_date: date

    # Term characteristics
    term_type: str
    academic_year: int
    is_current: bool
    is_registration_open: bool

    # Cohort tracking
    cohort_year: int | None = None


class CourseSchema(Schema):
    """Course schema."""

    id: int
    code: str
    name: str
    description: str

    # Academic info
    credit_hours: Decimal | None = None
    level: int | None = None
    course_type: str

    # Organizational
    division: DivisionSchema

    # Status
    is_active: bool
    can_repeat: bool


class CourseDetailSchema(CourseSchema):
    """Detailed course information."""

    # Prerequisites
    prerequisites: list[CourseSchema] = []

    # Textbooks
    textbooks: list[dict] = []  # Textbook info

    # Part templates (for language courses)
    part_templates: list[dict] = []


class TextbookSchema(Schema):
    """Textbook schema."""

    id: int
    title: str
    author: str
    publisher: str
    isbn: str | None = None
    edition: str | None = None
    publication_year: int | None = None
    is_required: bool


class CoursePrerequisiteSchema(Schema):
    """Course prerequisite relationship."""

    id: int
    course: CourseSchema
    prerequisite_course: CourseSchema
    is_strict: bool
    notes: str


# List schemas for simplified views
class MajorListSchema(Schema):
    """Simplified major for lists."""

    id: int
    name: str
    short_name: str
    program_type: str
    degree_type: str
    division_name: str
    cycle_name: str
    is_active: bool
    is_accepting_students: bool
    student_count: int | None = None


class CourseListSchema(Schema):
    """Simplified course for lists."""

    id: int
    code: str
    name: str
    credit_hours: Decimal | None = None
    level: int | None = None
    course_type: str
    division_name: str
    is_active: bool
    class_count: int | None = None  # Number of scheduled classes


class TermListSchema(Schema):
    """Simplified term for lists."""

    id: int
    name: str
    short_name: str
    start_date: date
    end_date: date
    term_type: str
    academic_year: int
    is_current: bool
    is_registration_open: bool
    enrollment_count: int | None = None


# Academic structure overview
class AcademicStructureSchema(Schema):
    """Complete academic structure overview."""

    divisions: list[DivisionSchema]
    cycles: list[CycleSchema]
    majors: list[MajorSchema]
    current_term: TermSchema | None = None


# Request schemas
class CreateDivisionSchema(Schema):
    """Schema for creating division."""

    name: str
    short_name: str = ""
    description: str = ""
    display_order: int = 100


class UpdateDivisionSchema(Schema):
    """Schema for updating division."""

    name: str | None = None
    short_name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    display_order: int | None = None


class CreateCycleSchema(Schema):
    """Schema for creating cycle."""

    name: str
    short_name: str = ""
    description: str = ""
    division_id: int
    level_order: int = 1


class CreateMajorSchema(Schema):
    """Schema for creating major."""

    name: str
    short_name: str = ""
    description: str = ""
    program_type: str
    degree_type: str
    division_id: int
    cycle_id: int
    required_credits: Decimal | None = None
    max_terms: int | None = None


class UpdateMajorSchema(Schema):
    """Schema for updating major."""

    name: str | None = None
    short_name: str | None = None
    description: str | None = None
    program_type: str | None = None
    degree_type: str | None = None
    required_credits: Decimal | None = None
    max_terms: int | None = None
    is_active: bool | None = None
    is_accepting_students: bool | None = None


class CreateTermSchema(Schema):
    """Schema for creating term."""

    name: str
    short_name: str = ""
    start_date: date
    end_date: date
    term_type: str
    academic_year: int
    cohort_year: int | None = None


class UpdateTermSchema(Schema):
    """Schema for updating term."""

    name: str | None = None
    short_name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_registration_open: bool | None = None


class CreateCourseSchema(Schema):
    """Schema for creating course."""

    code: str
    name: str
    description: str = ""
    credit_hours: Decimal | None = None
    level: int | None = None
    course_type: str
    division_id: int
    can_repeat: bool = False


class UpdateCourseSchema(Schema):
    """Schema for updating course."""

    code: str | None = None
    name: str | None = None
    description: str | None = None
    credit_hours: Decimal | None = None
    level: int | None = None
    course_type: str | None = None
    is_active: bool | None = None
    can_repeat: bool | None = None


# Pagination schemas
class PaginatedMajorsSchema(Schema):
    """Paginated majors response."""

    count: int
    next: str | None = None
    previous: str | None = None
    results: list[MajorListSchema]


class PaginatedCoursesSchema(Schema):
    """Paginated courses response."""

    count: int
    next: str | None = None
    previous: str | None = None
    results: list[CourseListSchema]


class PaginatedTermsSchema(Schema):
    """Paginated terms response."""

    count: int
    next: str | None = None
    previous: str | None = None
    results: list[TermListSchema]


# Statistics schemas
class CurriculumStatsSchema(Schema):
    """Curriculum statistics overview."""

    total_majors: int
    active_majors: int
    total_courses: int
    active_courses: int
    total_terms: int
    current_term_id: int | None = None

    # Breakdown by division
    division_breakdown: dict

    # Breakdown by program type
    program_type_breakdown: dict

    # Course type breakdown
    course_type_breakdown: dict
