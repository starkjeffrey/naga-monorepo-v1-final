"""Grading API endpoints for v1 API.

This module provides REST API endpoints for:
- Teacher grade entry and updates
- Grade validation and conversion
- Bulk grade operations
- Grade history and audit trails
- GPA calculations and reports

Migrated from apps.grading.api to unified v1 API structure.
"""

from typing import Any, cast

from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from ninja import Router, Schema
from ninja.errors import HttpError

# Import business logic from apps
from apps.enrollment.models import ClassHeaderEnrollment
from apps.grading.models import ClassPartGrade
from apps.grading.services import (
    ClassPartGradeService,
    GradeCalculationError,
)
from apps.scheduling.models import ClassPart

# Import from unified authentication system
from .auth import jwt_auth
from .permissions import check_admin_access, check_teacher_access

# Create router
router = Router(tags=["Grading"], auth=jwt_auth)


# Schemas for API requests and responses
class GradeEntrySchema(Schema):
    """Schema for grade entry requests."""

    enrollment_id: int
    class_part_id: int
    numeric_score: float | None = None
    letter_grade: str | None = None
    notes: str | None = ""
    grade_source: str | None = "MANUAL_TEACHER"


class GradeUpdateSchema(Schema):
    """Schema for grade update requests."""

    numeric_score: float | None = None
    letter_grade: str | None = None
    notes: str | None = None
    reason: str


class GradeResponseSchema(Schema):
    """Schema for grade response data."""

    id: int
    enrollment_id: int
    class_part_id: int
    student_name: str
    class_part_name: str
    numeric_score: float | None
    letter_grade: str | None
    gpa_points: float | None
    grade_status: str
    grade_source: str
    entered_at: str
    notes: str | None


class BulkGradeImportSchema(Schema):
    """Schema for bulk grade import requests."""

    grade_data: list[dict[str, Any]]
    grade_source: str | None = "MOODLE_IMPORT"


# Grade Entry Endpoints
@router.post("/grades", response=GradeResponseSchema)
def create_grade_entry(request, data: GradeEntrySchema):
    """Create a new grade entry for a student in a class part."""
    # Check teacher authorization
    if not check_teacher_access(request.user):
        raise HttpError(403, "Teacher access required")

    try:
        # Get the class part and enrollment
        class_part = get_object_or_404(ClassPart, id=data.class_part_id)
        enrollment = get_object_or_404(ClassHeaderEnrollment, id=data.enrollment_id)

        # Verify teacher is assigned to this class
        u = cast(Any, request.user)
        if hasattr(u, "person") and hasattr(u.person, "teacher_profile"):
            teacher = u.person.teacher_profile
            if cast(Any, class_part).teacher != teacher:
                raise HttpError(403, "Not authorized for this class")

        # Create grade using service
        grade = cast(Any, ClassPartGradeService).create_or_update_grade(
            enrollment=enrollment,
            class_part=class_part,
            numeric_score=data.numeric_score,
            letter_grade=data.letter_grade,
            notes=data.notes,
            grade_source=data.grade_source,
            entered_by=request.user,
        )

        g = cast(Any, grade)
        enr = cast(Any, enrollment)
        cp = cast(Any, class_part)

        return GradeResponseSchema(
            id=g.id,
            enrollment_id=enr.id,
            class_part_id=cp.id,
            student_name=enr.student.person.full_name,
            class_part_name=str(cp),
            numeric_score=g.numeric_score,
            letter_grade=g.letter_grade,
            gpa_points=g.gpa_points,
            grade_status=g.grade_status,
            grade_source=g.grade_source,
            entered_at=g.entered_at.isoformat(),
            notes=g.notes,
        )

    except ValidationError as e:
        raise HttpError(400, f"Validation error: {e!s}") from e
    except GradeCalculationError as e:
        raise HttpError(400, f"Grade calculation error: {e!s}") from e
    except Exception as e:
        raise HttpError(500, f"Internal error: {e!s}") from e


@router.put("/grades/{grade_id}", response=GradeResponseSchema)
def update_grade_entry(request, grade_id: int, data: GradeUpdateSchema):
    """Update an existing grade entry."""
    # Check teacher authorization
    if not check_teacher_access(request.user) and not check_admin_access(request.user):
        raise HttpError(403, "Teacher or admin access required")

    try:
        grade = get_object_or_404(ClassPartGrade, id=grade_id)

        # Verify authorization for this specific grade
        if not check_admin_access(request.user):
            # Teachers can only edit grades for their own classes
            u = cast(Any, request.user)
            if hasattr(u, "person") and hasattr(u.person, "teacher_profile"):
                teacher = u.person.teacher_profile
                if cast(Any, grade.class_part).teacher != teacher:
                    raise HttpError(403, "Not authorized to edit this grade")
            else:
                raise HttpError(403, "Not authorized to edit grades")

        # Update grade using service
        updated_grade = cast(Any, ClassPartGradeService).create_or_update_grade(
            grade=grade,
            numeric_score=data.numeric_score,
            letter_grade=data.letter_grade,
            notes=data.notes,
            reason=data.reason,
            updated_by=request.user,
        )

        ug = cast(Any, updated_grade)
        return GradeResponseSchema(
            id=ug.id,
            enrollment_id=ug.enrollment.id,
            class_part_id=ug.class_part.id,
            student_name=ug.enrollment.student.person.full_name,
            class_part_name=str(ug.class_part),
            numeric_score=ug.numeric_score,
            letter_grade=ug.letter_grade,
            gpa_points=ug.gpa_points,
            grade_status=ug.grade_status,
            grade_source=ug.grade_source,
            entered_at=ug.entered_at.isoformat(),
            notes=ug.notes,
        )

    except ValidationError as e:
        raise HttpError(400, f"Validation error: {e!s}") from e
    except GradeCalculationError as e:
        raise HttpError(400, f"Grade calculation error: {e!s}") from e
    except Exception as e:
        raise HttpError(500, f"Internal error: {e!s}") from e


@router.get("/grades/class-part/{class_part_id}", response=list[GradeResponseSchema])
def get_class_grades(request, class_part_id: int):
    """Get all grades for a specific class part."""
    # Check teacher authorization
    if not check_teacher_access(request.user) and not check_admin_access(request.user):
        raise HttpError(403, "Teacher or admin access required")

    try:
        class_part = get_object_or_404(ClassPart, id=class_part_id)

        # Verify authorization for this class
        if not check_admin_access(request.user):
            # Teachers can only view grades for their own classes
            u = cast(Any, request.user)
            if hasattr(u, "person") and hasattr(u.person, "teacher_profile"):
                teacher = u.person.teacher_profile
                if cast(Any, class_part).teacher != teacher:
                    raise HttpError(403, "Not authorized to view these grades")
            else:
                raise HttpError(403, "Not authorized to view grades")

        # Get grades for the class part
        grades = ClassPartGrade.objects.filter(class_part=class_part).select_related(
            "enrollment__student__person", "class_part"
        )

        results: list[GradeResponseSchema] = []
        for grade in grades:
            gr = cast(Any, grade)
            results.append(
                GradeResponseSchema(
                    id=gr.id,
                    enrollment_id=gr.enrollment.id,
                    class_part_id=gr.class_part.id,
                    student_name=gr.enrollment.student.person.full_name,
                    class_part_name=str(gr.class_part),
                    numeric_score=gr.numeric_score,
                    letter_grade=gr.letter_grade,
                    gpa_points=gr.gpa_points,
                    grade_status=gr.grade_status,
                    grade_source=gr.grade_source,
                    entered_at=gr.entered_at.isoformat(),
                    notes=gr.notes,
                ),
            )
        return results

    except Exception as e:
        raise HttpError(500, f"Internal error: {e!s}") from e


# Note: This is a partial migration showing the core grading endpoints.
# Additional endpoints for bulk operations, GPA calculations, etc.
# would follow the same pattern with unified auth and error handling.


# Export the router
__all__ = ["router"]
