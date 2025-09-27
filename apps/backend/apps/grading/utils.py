"""Utility functions for grading app.

This module provides common utilities for grade calculations,
conversions, and validation operations.
"""

from decimal import Decimal
from typing import Any, cast

from django.core.cache import cache
from django.db.models import QuerySet

from .models import ClassPartGrade, GradingScale


def get_cached_grading_scale(scale_type: str) -> GradingScale | None:
    """Get grading scale with caching for better performance.

    Args:
        scale_type: Type of grading scale to retrieve

    Returns:
        GradingScale instance or None if not found
    """
    cache_key = f"grading_scale_{scale_type}"
    scale: GradingScale | None = cast("GradingScale | None", cache.get(cache_key))

    if scale is None:
        try:
            scale = GradingScale.objects.get(scale_type=scale_type, is_active=True)
            # Cache for 1 hour
            cache.set(cache_key, scale, 3600)
        except GradingScale.DoesNotExist:
            return None

    return scale


def bulk_grade_validation(grades_data: list[dict[str, Any]]) -> dict[str, Any]:
    """Validate multiple grades before bulk operations.

    Args:
        grades_data: List of grade dictionaries to validate

    Returns:
        Dict with validation results and errors
    """
    valid_grades = []
    errors = []

    for i, grade_data in enumerate(grades_data):
        try:
            # Validate required fields
            if not grade_data.get("enrollment_id"):
                errors.append({"row": i + 1, "error": "Missing enrollment_id"})
                continue

            if not grade_data.get("class_part_id"):
                errors.append({"row": i + 1, "error": "Missing class_part_id"})
                continue

            # Validate grade values
            numeric_score = grade_data.get("numeric_score")
            letter_grade = grade_data.get("letter_grade")

            if not numeric_score and not letter_grade:
                errors.append({"row": i + 1, "error": "Must provide either numeric_score or letter_grade"})
                continue

            if numeric_score is not None:
                try:
                    score = Decimal(str(numeric_score))
                    if not (0 <= score <= 100):
                        errors.append({"row": i + 1, "error": f"Numeric score {score} must be between 0-100"})
                        continue
                except (ValueError, TypeError):
                    errors.append({"row": i + 1, "error": f"Invalid numeric score format: {numeric_score}"})
                    continue

            valid_grades.append(grade_data)

        except Exception as e:
            errors.append({"row": i + 1, "error": f"Validation error: {e}"})

    return {
        "valid_grades": valid_grades,
        "errors": errors,
        "valid_count": len(valid_grades),
        "error_count": len(errors),
    }


def optimize_grade_queryset(queryset: QuerySet) -> QuerySet:
    """Apply standard optimizations to grade querysets.

    Args:
        queryset: Base grade queryset to optimize

    Returns:
        Optimized queryset with select_related and prefetch_related
    """
    return queryset.select_related(
        "enrollment__student__person", "class_part__class_session__class_header__course", "entered_by", "approved_by"
    ).prefetch_related("change_history__changed_by")


def get_grade_statistics(class_part_id: int) -> dict[str, Any]:
    """Get grade statistics for a class part.

    Args:
        class_part_id: ID of the class part

    Returns:
        Dict with grade statistics
    """
    cache_key = f"grade_stats_{class_part_id}"
    stats: dict[str, Any] | None = cast("dict[str, Any] | None", cache.get(cache_key))

    if stats is None:
        grades = ClassPartGrade.objects.filter(
            class_part_id=class_part_id, grade_status__in=["APPROVED", "FINALIZED"]
        ).exclude(numeric_score__isnull=True)

        if not grades.exists():
            return {"count": 0}

        scores = [float(g.numeric_score) for g in grades if g.numeric_score]

        if scores:
            stats = {
                "count": len(scores),
                "average": sum(scores) / len(scores),
                "highest": max(scores),
                "lowest": min(scores),
                "passing_count": len([s for s in scores if s >= 60]),
                "failing_count": len([s for s in scores if s < 60]),
            }
        else:
            stats = {"count": 0}

        # Cache for 30 minutes
        cache.set(cache_key, stats, 1800)

    # At this point, stats is not None due to the guard above
    return cast(dict[str, Any], stats)
