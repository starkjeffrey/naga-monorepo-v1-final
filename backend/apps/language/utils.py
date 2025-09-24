"""Utility functions for language app.

This module provides common utilities for language program operations,
level management, and promotion workflows.
"""

import re
from typing import Any

from django.core.cache import cache
from django.db.models import QuerySet

from .models import LanguageProgramPromotion, LanguageStudentPromotion


def parse_course_level(course_code: str) -> dict[str, Any]:
    """Parse course code to extract program and level information.

    Args:
        course_code: Course code in format 'PROGRAM-##' or 'PROGRAM##'

    Returns:
        Dict with program, level, and validation info
    """
    # Handle different course code formats
    patterns = [
        r"^([A-Z]+)-(\d+)$",  # EHSS-05, GESL-12
        r"^([A-Z]+)(\d+)$",  # EHSS05, GESL12
        r"^([A-Z]+)-([A-Z]\d+)$",  # IEAP-A1, IEAP-B2
    ]

    for pattern in patterns:
        match = re.match(pattern, course_code.upper())
        if match:
            program = match.group(1)
            level_str = match.group(2)

            # Extract numeric level
            level_num = None
            if level_str.isdigit():
                level_num = int(level_str)
            elif len(level_str) > 1 and level_str[1:].isdigit():
                # Handle IEAP-A1 format
                level_num = int(level_str[1:])

            return {
                "program": program,
                "level_str": level_str,
                "level_num": level_num,
                "valid": True,
                "format": "standard" if "-" in course_code else "compact",
            }

    return {
        "program": None,
        "level_str": None,
        "level_num": None,
        "valid": False,
        "error": f"Invalid course code format: {course_code}",
    }


def get_next_level_course_code(current_code: str) -> str | None:
    """Generate next level course code.

    Args:
        current_code: Current course code

    Returns:
        Next level course code or None if invalid
    """
    parsed = parse_course_level(current_code)

    if not parsed["valid"] or parsed["level_num"] is None:
        return None

    next_level = parsed["level_num"] + 1

    # Format based on original format
    if parsed["format"] == "standard":
        return f"{parsed['program']}-{next_level:02d}"
    else:
        return f"{parsed['program']}{next_level:02d}"


def get_promotion_progress_summary(batch_id: int) -> dict[str, Any]:
    """Get summary of promotion batch progress.

    Args:
        batch_id: ID of the promotion batch

    Returns:
        Dict with progress summary
    """
    cache_key = f"promotion_progress_{batch_id}"
    summary = cache.get(cache_key)

    if summary is None:
        try:
            batch = LanguageProgramPromotion.objects.get(id=batch_id)

            # Get student promotion counts by result
            student_promotions = LanguageStudentPromotion.objects.filter(promotion_batch=batch)

            result_counts = {}
            for result_choice in LanguageStudentPromotion.PromotionResult.choices:
                result_counts[result_choice[0]] = student_promotions.filter(result=result_choice[0]).count()

            summary = {
                "batch_id": batch_id,
                "program": batch.program,
                "source_term": batch.source_term.code,
                "target_term": batch.target_term.code,
                "status": batch.status,
                "total_students": student_promotions.count(),
                "students_promoted_count": batch.students_promoted_count,
                "classes_cloned_count": batch.classes_cloned_count,
                "result_breakdown": result_counts,
                "success_rate": (batch.students_promoted_count / max(student_promotions.count(), 1) * 100),
                "initiated_by": batch.initiated_by.get_full_name(),
                "initiated_at": batch.initiated_at.isoformat(),
                "completed_at": batch.completed_at.isoformat() if batch.completed_at else None,
            }

            # Cache for 15 minutes
            cache.set(cache_key, summary, 900)

        except LanguageProgramPromotion.DoesNotExist:
            return {"error": f"Promotion batch {batch_id} not found"}

    return summary


def validate_level_skip_logic(current_level: str, target_level: str, max_skip: int = 3) -> dict[str, Any]:
    """Validate level skip request logic.

    Args:
        current_level: Current level string
        target_level: Target level string
        max_skip: Maximum levels allowed to skip

    Returns:
        Dict with validation results
    """
    current_parsed = parse_course_level(current_level)
    target_parsed = parse_course_level(target_level)

    # Validate level formats
    if not current_parsed["valid"]:
        return {"valid": False, "error": f"Invalid current level format: {current_level}"}

    if not target_parsed["valid"]:
        return {"valid": False, "error": f"Invalid target level format: {target_level}"}

    # Check if same program
    if current_parsed["program"] != target_parsed["program"]:
        return {"valid": False, "error": "Current and target levels must be in the same program"}

    # Check level progression
    if current_parsed["level_num"] is None or target_parsed["level_num"] is None:
        return {"valid": False, "error": "Could not parse level numbers"}

    if target_parsed["level_num"] <= current_parsed["level_num"]:
        return {"valid": False, "error": "Target level must be higher than current level"}

    levels_skipped = target_parsed["level_num"] - current_parsed["level_num"]

    if levels_skipped > max_skip:
        return {"valid": False, "error": f"Cannot skip more than {max_skip} levels (requested: {levels_skipped})"}

    return {
        "valid": True,
        "levels_skipped": levels_skipped,
        "program": current_parsed["program"],
        "current_level_num": current_parsed["level_num"],
        "target_level_num": target_parsed["level_num"],
    }


def optimize_promotion_queryset(queryset: QuerySet) -> QuerySet:
    """Apply standard optimizations to promotion querysets.

    Args:
        queryset: Base promotion queryset to optimize

    Returns:
        Optimized queryset with select_related and prefetch_related
    """
    return queryset.select_related("source_term", "target_term", "initiated_by").prefetch_related(
        "student_promotions__student__person"
    )
