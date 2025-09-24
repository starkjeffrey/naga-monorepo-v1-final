"""Student ID formatting utilities for system-wide consistent representation.

This module provides utilities to ensure all student IDs are displayed
consistently as 5-digit zero-padded numbers throughout the system.
"""


def format_student_id(student_id):
    """Format a student ID to 5-digit zero-padded string.

    Args:
        student_id: Integer or string student ID

    Returns:
        str: 5-digit zero-padded student ID (e.g., "00123")

    Examples:
        >>> format_student_id(123)
        '00123'
        >>> format_student_id("1234")
        '01234'
        >>> format_student_id(12345)
        '12345'
    """
    if student_id is None:
        return "00000"

    return str(student_id).zfill(5)


def format_student_display_name(student, show_id=True):
    """Format a student's display name with optional formatted student ID.

    Args:
        student: Student object with person and student_id attributes
        show_id: Whether to include the formatted student ID in parentheses

    Returns:
        str: Formatted display name (e.g., "John Doe (00123)")
    """
    if not student:
        return "Unknown Student"

    full_name = getattr(student.person, "full_name", "Unknown Name")

    if show_id:
        formatted_id = format_student_id(student.student_id)
        return f"{full_name} ({formatted_id})"
    return full_name
