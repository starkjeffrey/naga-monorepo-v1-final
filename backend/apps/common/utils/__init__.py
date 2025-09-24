# Common utilities for Naga SIS V1

from datetime import date

from django.utils import timezone

from .student_id_formatter import format_student_display_name, format_student_id

__all__ = ["format_student_display_name", "format_student_id", "get_current_date"]


def get_current_date() -> date:
    """Get the current date."""
    return timezone.now().date()
