"""Grade entry and management views for the web interface."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from apps.enrollment.models import ClassHeaderEnrollment
from apps.grading.models import ClassPartGrade, GradingScale
from apps.scheduling.models import ClassHeader, ClassPart

if TYPE_CHECKING:
    from django.db.models import QuerySet


class GradeEntryView(LoginRequiredMixin, TemplateView):
    """Main grade entry interface with Excel-like navigation."""

    template_name = "web_interface/pages/academic/grade_entry.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add grade entry context data."""
        context = super().get_context_data(**kwargs)

        # Get user's assigned classes for grade entry
        user_classes = self.get_user_classes()

        context.update(
            {
                "user_classes": user_classes,
                "grading_scales": GradingScale.objects.filter(is_active=True),
                "page_title": _("Grade Entry"),
            }
        )

        return context

    def get_user_classes(self) -> QuerySet[ClassHeader]:
        """Get classes that the current user can enter grades for."""
        # For now, get all active classes
        # Future enhancement: Filter based on user permissions/assignments for teacher-specific access
        return (
            ClassHeader.objects.filter(
                is_active=True,
                classsession__is_active=True,
            )
            .select_related("course", "term")
            .distinct()
        )


@login_required
@require_http_methods(["GET"])
def grade_entry_class_data(request: HttpRequest, class_id: int) -> HttpResponse:
    """HTMX endpoint to load grade entry data for a specific class."""
    class_header = get_object_or_404(ClassHeader, id=class_id, is_active=True)

    # Get all enrollments for this class with prefetched data
    enrollments = (
        ClassHeaderEnrollment.objects.filter(
            class_header=class_header,
            is_active=True,
        )
        .select_related("student__person")
        .prefetch_related("class_part_grades__class_part")
        .order_by("student__person__last_name", "student__person__first_name")
    )

    # Get all class parts for this class
    class_parts = (
        ClassPart.objects.filter(
            class_session__class_header=class_header,
            class_session__is_active=True,
        )
        .select_related("class_session")
        .order_by("class_session__session_number", "part_name")
    )

    # Get grading scale for this class
    grading_scale = None
    if class_header.course and hasattr(class_header.course, "grading_scale"):
        grading_scale = class_header.course.grading_scale
    else:
        # Default to Language Standard scale
        grading_scale = GradingScale.objects.filter(
            scale_type=GradingScale.ScaleType.LANGUAGE_STANDARD, is_active=True
        ).first()

    # Get grade conversions for this scale
    grade_conversions = []
    if grading_scale:
        grade_conversions = list(grading_scale.grade_conversions.all().order_by("display_order"))

    context = {
        "class_header": class_header,
        "enrollments": enrollments,
        "class_parts": class_parts,
        "grading_scale": grading_scale,
        "grade_conversions": grade_conversions,
    }

    return render(request, "web_interface/partials/grade_entry/grade_grid.html", context)


@login_required
@require_http_methods(["POST"])
def save_grade(request: HttpRequest) -> JsonResponse:
    """HTMX endpoint to save individual grade."""
    try:
        # Parse request data
        enrollment_id = request.POST.get("enrollment_id")
        class_part_id = request.POST.get("class_part_id")
        grade_value = request.POST.get("grade_value", "").strip()

        if not enrollment_id or not class_part_id:
            return JsonResponse({"success": False, "error": _("Missing required data")}, status=400)

        enrollment = get_object_or_404(ClassHeaderEnrollment, id=enrollment_id)
        class_part = get_object_or_404(ClassPart, id=class_part_id)

        # Validate that enrollment and class part are related
        if enrollment.class_header != class_part.class_session.class_header:
            return JsonResponse({"success": False, "error": _("Enrollment and class part do not match")}, status=400)

        with transaction.atomic():
            # Get or create grade record
            grade, created = ClassPartGrade.objects.get_or_create(
                enrollment=enrollment,
                class_part=class_part,
                defaults={
                    "entered_by": request.user,
                    "grade_source": ClassPartGrade.GradeSource.MANUAL_TEACHER,
                },
            )

            # Parse and validate grade value
            if not grade_value:
                # Delete grade if empty
                if not created:
                    grade.delete()
                return JsonResponse(
                    {
                        "success": True,
                        "message": _("Grade cleared"),
                        "grade_display": "",
                    }
                )

            # Try to parse as numeric score first
            numeric_score = None
            letter_grade = ""

            try:
                numeric_score = Decimal(grade_value)
                if not (0 <= numeric_score <= 100):
                    return JsonResponse(
                        {"success": False, "error": _("Numeric score must be between 0 and 100")}, status=400
                    )
            except (ValueError, TypeError):
                # Treat as letter grade
                letter_grade = grade_value.upper()

                # Validate letter grade against grading scale
                grading_scale = get_grading_scale_for_class(class_part.class_session.class_header)
                if grading_scale:
                    grade_conversion = grading_scale.grade_conversions.filter(letter_grade=letter_grade).first()
                    if not grade_conversion:
                        return JsonResponse(
                            {"success": False, "error": _("Invalid letter grade for this grading scale")}, status=400
                        )

                    # Set numeric score and GPA points from conversion
                    numeric_score = (grade_conversion.min_percentage + grade_conversion.max_percentage) / 2
                    grade.gpa_points = grade_conversion.gpa_points

            # Update grade record
            grade.numeric_score = numeric_score
            grade.letter_grade = letter_grade
            grade.entered_by = request.user
            grade.entered_at = timezone.now()
            grade.grade_status = ClassPartGrade.GradeStatus.DRAFT

            # Convert numeric to letter if needed
            if numeric_score and not letter_grade:
                grading_scale = get_grading_scale_for_class(class_part.class_session.class_header)
                if grading_scale:
                    grade_conversion = grading_scale.grade_conversions.filter(
                        min_percentage__lte=numeric_score, max_percentage__gte=numeric_score
                    ).first()
                    if grade_conversion:
                        grade.letter_grade = grade_conversion.letter_grade
                        grade.gpa_points = grade_conversion.gpa_points

            grade.full_clean()
            grade.save()

            return JsonResponse(
                {
                    "success": True,
                    "message": _("Grade saved successfully"),
                    "grade_display": getattr(grade, "get_grade_display", lambda: grade.letter_grade or (str(grade.numeric_score) if grade.numeric_score is not None else ""))(),
                    "grade_id": getattr(grade, "pk", None),
                }
            )

    except ValidationError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)
    except Exception:
        return JsonResponse({"success": False, "error": _("An error occurred while saving the grade")}, status=500)


@login_required
@require_http_methods(["POST"])
def bulk_grade_update(request: HttpRequest) -> JsonResponse:
    """HTMX endpoint for bulk grade operations."""
    try:
        data = json.loads(request.body)
        operation = data.get("operation")
        grade_ids = data.get("grade_ids", [])

        if not operation or not grade_ids:
            return JsonResponse({"success": False, "error": _("Missing operation or grade IDs")}, status=400)

        grades = ClassPartGrade.objects.filter(
            id__in=grade_ids, enrollment__class_header__in=get_user_classes_for_grading(request.user)
        )

        with transaction.atomic():
            if operation == "submit":
                grades.update(
                    grade_status=ClassPartGrade.GradeStatus.SUBMITTED,
                    approved_by=request.user,
                    approved_at=timezone.now(),
                )
                message = _("Grades submitted successfully")

            elif operation == "approve":
                grades.update(
                    grade_status=ClassPartGrade.GradeStatus.APPROVED,
                    approved_by=request.user,
                    approved_at=timezone.now(),
                )
                message = _("Grades approved successfully")

            elif operation == "finalize":
                grades.update(
                    grade_status=ClassPartGrade.GradeStatus.FINALIZED,
                    approved_by=request.user,
                    approved_at=timezone.now(),
                )
                message = _("Grades finalized successfully")

            else:
                return JsonResponse({"success": False, "error": _("Invalid operation")}, status=400)

        return JsonResponse({"success": True, "message": message, "updated_count": grades.count()})

    except Exception:
        return JsonResponse({"success": False, "error": _("An error occurred during bulk operation")}, status=500)


def get_grading_scale_for_class(class_header: ClassHeader) -> GradingScale | None:
    """Get the appropriate grading scale for a class."""
    # Try to get from course settings first
    if hasattr(class_header.course, "grading_scale") and class_header.course.grading_scale:
        return class_header.course.grading_scale

    # Default to Language Standard scale
    return GradingScale.objects.filter(scale_type=GradingScale.ScaleType.LANGUAGE_STANDARD, is_active=True).first()


def get_user_classes_for_grading(user) -> QuerySet[ClassHeader]:
    """Get classes that a user can enter grades for."""
    # Future enhancement: Implement role-based permission checking for teacher/admin access
    # For now, return all active classes
    return ClassHeader.objects.filter(is_active=True)
