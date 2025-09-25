"""Enrollment API endpoints for managing student enrollments and academic programs.

This module provides RESTful API endpoints for React queries to access and
manage enrollment data including program enrollments, major declarations,
class enrollments, and related academic information.
"""


from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router

from apps.curriculum.models import Term
from apps.enrollment.models import (
    ClassHeaderEnrollment,
    MajorDeclaration,
    ProgramEnrollment,
)
from apps.people.models import StudentProfile
from apps.scheduling.models import ClassHeader

from .auth import jwt_auth
from .enrollment_schemas import (
    EnrollmentStatsSchema,
    MajorDeclarationSchema,
    PaginatedClassEnrollmentsSchema,
    PaginatedClassListSchema,
    PaginatedMajorDeclarationsSchema,
    PaginatedProgramEnrollmentsSchema,
    ProgramEnrollmentSchema,
    StudentEnrollmentSummarySchema,
)

router = Router(auth=jwt_auth, tags=["enrollment"])


# Helper serialization functions
def serialize_major(major) -> dict:
    """Serialize major information."""
    return {
        "id": major.id,
        "name": major.name,
        "short_name": major.short_name,
        "program_type": major.program_type,
        "degree_type": major.degree_type,
        "division_name": major.division.name if major.division else "",
        "cycle_name": major.cycle.name if major.cycle else "",
        "is_active": major.is_active,
    }


def serialize_program_enrollment(enrollment) -> dict:
    """Serialize program enrollment."""
    return {
        "id": enrollment.id,
        "student_id": enrollment.student.student_id,
        "student_name": enrollment.student.person.full_name,
        "major": serialize_major(enrollment.major),
        "enrollment_type": enrollment.enrollment_type,
        "enrollment_status": enrollment.enrollment_status,
        "division": enrollment.division,
        "cycle": enrollment.cycle,
        "start_date": enrollment.start_date,
        "end_date": enrollment.end_date,
        "expected_graduation": enrollment.expected_graduation,
        "entry_level": enrollment.entry_level,
        "finishing_level": enrollment.finishing_level,
        "terms_active": enrollment.terms_active,
        "terms_on_hold": enrollment.terms_on_hold,
        "overall_gpa": enrollment.overall_gpa,
        "is_active": enrollment.is_active,
        "is_current": enrollment.is_current,
    }


def serialize_major_declaration(declaration) -> dict:
    """Serialize major declaration."""
    return {
        "id": declaration.id,
        "student_id": declaration.student.student_id,
        "student_name": declaration.student.person.full_name,
        "major": serialize_major(declaration.major),
        "declaration_date": declaration.declaration_date,
        "is_active": declaration.is_active,
        "is_prospective": declaration.is_prospective,
        "intended_graduation_term": declaration.intended_graduation_term,
        "notes": declaration.notes,
    }


# Program Enrollment endpoints
@router.get("/program-enrollments/", response=PaginatedProgramEnrollmentsSchema)
def list_program_enrollments(
    request,
    student_id: int | None = Query(None, description="Filter by student ID"),
    major_id: int | None = Query(None, description="Filter by major"),
    status: str | None = Query(None, description="Filter by enrollment status"),
    enrollment_type: str | None = Query(None, description="Filter by enrollment type"),
    active_only: bool = Query(False, description="Show only active enrollments"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List program enrollments with filtering."""
    queryset = ProgramEnrollment.objects.select_related("student__person", "major__division", "major__cycle")

    if student_id:
        queryset = queryset.filter(student__student_id=student_id)

    if major_id:
        queryset = queryset.filter(major_id=major_id)

    if status:
        queryset = queryset.filter(enrollment_status=status)

    if enrollment_type:
        queryset = queryset.filter(enrollment_type=enrollment_type)

    if active_only:
        queryset = queryset.filter(is_active=True)

    queryset = queryset.order_by("-start_date", "student__student_id")

    # Paginate
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    results = [serialize_program_enrollment(enrollment) for enrollment in page_obj]

    return {"count": paginator.count, "next": None, "previous": None, "results": results}


@router.get("/program-enrollments/{enrollment_id}/", response=ProgramEnrollmentSchema)
def get_program_enrollment(request, enrollment_id: int):
    """Get specific program enrollment."""
    enrollment = get_object_or_404(
        ProgramEnrollment.objects.select_related("student__person", "major__division", "major__cycle"),
        id=enrollment_id,
    )
    return serialize_program_enrollment(enrollment)


# Major Declaration endpoints
@router.get("/major-declarations/", response=PaginatedMajorDeclarationsSchema)
def list_major_declarations(
    request,
    student_id: int | None = Query(None, description="Filter by student ID"),
    major_id: int | None = Query(None, description="Filter by major"),
    active_only: bool = Query(True, description="Show only active declarations"),
    prospective_only: bool = Query(False, description="Show only prospective declarations"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List major declarations with filtering."""
    queryset = MajorDeclaration.objects.select_related("student__person", "major__division", "major__cycle")

    if student_id:
        queryset = queryset.filter(student__student_id=student_id)

    if major_id:
        queryset = queryset.filter(major_id=major_id)

    if active_only:
        queryset = queryset.filter(is_active=True)

    if prospective_only:
        queryset = queryset.filter(is_prospective=True)

    queryset = queryset.order_by("-declaration_date", "student__student_id")

    # Paginate
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    results = [serialize_major_declaration(declaration) for declaration in page_obj]

    return {"count": paginator.count, "next": None, "previous": None, "results": results}


@router.get("/major-declarations/{declaration_id}/", response=MajorDeclarationSchema)
def get_major_declaration(request, declaration_id: int):
    """Get specific major declaration."""
    declaration = get_object_or_404(
        MajorDeclaration.objects.select_related("student__person", "major__division", "major__cycle"),
        id=declaration_id,
    )
    return serialize_major_declaration(declaration)


# Class Enrollment endpoints
@router.get("/class-enrollments/", response=PaginatedClassEnrollmentsSchema)
def list_class_enrollments(
    request,
    student_id: int | None = Query(None, description="Filter by student ID"),
    class_header_id: int | None = Query(None, description="Filter by class"),
    term_id: int | None = Query(None, description="Filter by term"),
    status: str | None = Query(None, description="Filter by enrollment status"),
    current_term_only: bool = Query(False, description="Show only current term enrollments"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List class enrollments with filtering."""
    queryset = ClassHeaderEnrollment.objects.select_related(
        "student__person", "class_header__course", "class_header__term", "class_header__teacher__person"
    )

    if student_id:
        queryset = queryset.filter(student__student_id=student_id)

    if class_header_id:
        queryset = queryset.filter(class_header_id=class_header_id)

    if term_id:
        queryset = queryset.filter(class_header__term_id=term_id)

    if status:
        queryset = queryset.filter(status=status)

    if current_term_only:
        current_term = Term.objects.filter(is_current=True).first()
        if current_term:
            queryset = queryset.filter(class_header__term=current_term)

    queryset = queryset.order_by("-enrollment_date")

    # Paginate
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    results = []
    for enrollment in page_obj:
        class_header = enrollment.class_header
        result = {
            "id": enrollment.id,
            "student": {
                "id": enrollment.student.id,
                "student_id": enrollment.student.student_id,
                "name": enrollment.student.person.full_name,
            },
            "class_header": {
                "id": class_header.id,
                "class_number": class_header.class_number,
                "course_code": class_header.course.code,
                "course_name": class_header.course.name,
                "term_name": class_header.term.name,
                "teacher_name": class_header.teacher.person.full_name if class_header.teacher else None,
                "room_name": class_header.room.name if class_header.room else None,
                "max_enrollment": class_header.max_enrollment,
                "current_enrollment": class_header.enrollments.filter(status="ENROLLED").count(),
            },
            "enrollment_date": enrollment.enrollment_date,
            "status": enrollment.status,
            "grade_override": enrollment.grade_override,
            "is_auditing": enrollment.is_auditing,
            "notes": enrollment.notes,
            "tuition_waived": enrollment.tuition_waived,
            "discount_percentage": enrollment.discount_percentage,
        }
        results.append(result)

    return {"count": paginator.count, "next": None, "previous": None, "results": results}


# Student-specific enrollment summary
@router.get("/students/{student_id}/enrollment-summary/", response=StudentEnrollmentSummarySchema)
def get_student_enrollment_summary(request, student_id: int):
    """Get comprehensive enrollment summary for a student."""
    student = get_object_or_404(StudentProfile.objects.select_related("person"), student_id=student_id)

    # Get active program enrollments
    program_enrollments = ProgramEnrollment.objects.filter(student=student, is_active=True).select_related(
        "major__division", "major__cycle"
    )

    # Get major declarations
    major_declarations = MajorDeclaration.objects.filter(student=student, is_active=True).select_related(
        "major__division", "major__cycle"
    )

    # Get current term class enrollments
    current_term = Term.objects.filter(is_current=True).first()
    current_enrollments = []
    if current_term:
        current_enrollments = ClassHeaderEnrollment.objects.filter(
            student=student, class_header__term=current_term, status__in=["ENROLLED", "WAITLISTED"]
        ).select_related("class_header__course", "class_header__term", "class_header__teacher__person")

    # Calculate statistics
    total_active_enrollments = program_enrollments.count()
    total_completed_courses = ClassHeaderEnrollment.objects.filter(student=student, status="COMPLETED").count()

    # Calculate current term credit hours
    current_term_credits = sum(
        enrollment.class_header.course.credit_hours or 0
        for enrollment in current_enrollments
        if enrollment.status == "ENROLLED" and not enrollment.is_auditing
    )

    return {
        "student_id": student.student_id,
        "student_name": student.person.full_name,
        "current_status": student.current_status,
        "active_program_enrollments": [serialize_program_enrollment(enrollment) for enrollment in program_enrollments],
        "major_declarations": [serialize_major_declaration(declaration) for declaration in major_declarations],
        "current_class_enrollments": [
            {
                "id": enrollment.id,
                "student": {
                    "id": student.id,
                    "student_id": student.student_id,
                    "name": student.person.full_name,
                },
                "class_header": {
                    "id": enrollment.class_header.id,
                    "class_number": enrollment.class_header.class_number,
                    "course_code": enrollment.class_header.course.code,
                    "course_name": enrollment.class_header.course.name,
                    "term_name": enrollment.class_header.term.name,
                    "teacher_name": enrollment.class_header.teacher.person.full_name
                    if enrollment.class_header.teacher
                    else None,
                    "room_name": enrollment.class_header.room.name if enrollment.class_header.room else None,
                    "max_enrollment": enrollment.class_header.max_enrollment,
                    "current_enrollment": enrollment.class_header.enrollments.filter(status="ENROLLED").count(),
                },
                "enrollment_date": enrollment.enrollment_date,
                "status": enrollment.status,
                "grade_override": enrollment.grade_override,
                "is_auditing": enrollment.is_auditing,
                "notes": enrollment.notes,
                "tuition_waived": enrollment.tuition_waived,
                "discount_percentage": enrollment.discount_percentage,
            }
            for enrollment in current_enrollments
        ],
        "total_active_enrollments": total_active_enrollments,
        "total_completed_courses": total_completed_courses,
        "current_term_credit_hours": current_term_credits,
    }


# Classes with enrollment information
@router.get("/classes/", response=PaginatedClassListSchema)
def list_classes_with_enrollments(
    request,
    term_id: int | None = Query(None, description="Filter by term"),
    course_id: int | None = Query(None, description="Filter by course"),
    teacher_id: int | None = Query(None, description="Filter by teacher"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List classes with enrollment counts."""
    queryset = ClassHeader.objects.select_related("course", "term", "teacher__person", "room").annotate(
        student_count=Count("enrollments", filter=Q(enrollments__status="ENROLLED"))
    )

    if term_id:
        queryset = queryset.filter(term_id=term_id)

    if course_id:
        queryset = queryset.filter(course_id=course_id)

    if teacher_id:
        queryset = queryset.filter(teacher_id=teacher_id)

    queryset = queryset.order_by("class_number")

    # Paginate
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    results = []
    for class_header in page_obj:
        enrollment_percentage = None
        if class_header.max_enrollment and class_header.max_enrollment > 0:
            enrollment_percentage = (class_header.student_count / class_header.max_enrollment) * 100

        results.append(
            {
                "id": class_header.id,
                "class_number": class_header.class_number,
                "course_code": class_header.course.code,
                "course_name": class_header.course.name,
                "term_name": class_header.term.name,
                "student_count": class_header.student_count,
                "max_enrollment": class_header.max_enrollment,
                "enrollment_percentage": enrollment_percentage,
                "teacher_name": class_header.teacher.person.full_name if class_header.teacher else None,
            }
        )

    return {"count": paginator.count, "next": None, "previous": None, "results": results}


# Enrollment statistics
@router.get("/statistics/", response=EnrollmentStatsSchema)
def get_enrollment_statistics(request):
    """Get enrollment statistics overview."""
    total_students = StudentProfile.objects.count()
    active_students = StudentProfile.objects.filter(current_status="ACTIVE").count()

    total_enrollments = ProgramEnrollment.objects.count()

    current_term = Term.get_current_term()
    current_term_enrollments = 0
    if current_term:
        current_term_enrollments = ClassHeaderEnrollment.objects.filter(
            class_header__term=current_term, status="ENROLLED"
        ).count()

    # Status breakdown
    status_breakdown = {}
    for status, count in StudentProfile.objects.values_list("current_status").annotate(count=Count("id")):
        status_breakdown[status] = count

    # Program type breakdown
    program_type_breakdown = {}
    for program_type, count in (
        ProgramEnrollment.objects.filter(is_active=True).values_list("major__program_type").annotate(count=Count("id"))
    ):
        program_type_breakdown[program_type] = count

    # Division breakdown
    division_breakdown = {}
    for division, count in (
        ProgramEnrollment.objects.filter(is_active=True).values_list("division").annotate(count=Count("id"))
    ):
        division_breakdown[division] = count

    return {
        "total_students": total_students,
        "active_students": active_students,
        "total_enrollments": total_enrollments,
        "current_term_enrollments": current_term_enrollments,
        "status_breakdown": status_breakdown,
        "program_type_breakdown": program_type_breakdown,
        "division_breakdown": division_breakdown,
    }


# Utility endpoints for React dropdowns
@router.get("/enrollment-statuses/", response=list[dict])
def get_enrollment_statuses(request):
    """Get enrollment status choices."""
    return [{"value": choice[0], "label": choice[1]} for choice in ProgramEnrollment.EnrollmentStatus.choices]


@router.get("/enrollment-types/", response=list[dict])
def get_enrollment_types(request):
    """Get enrollment type choices."""
    return [{"value": choice[0], "label": choice[1]} for choice in ProgramEnrollment.EnrollmentType.choices]
