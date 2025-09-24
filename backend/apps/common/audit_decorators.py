"""Audit logging decorators for the Naga SIS project.

This module provides configurable decorators to automatically log student
activities and system actions. Designed to work with StudentActivityLog
while maintaining clean architecture through string-based references.

USAGE PATTERNS:

1. Basic student activity logging:
   @audit_student_activity(activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT)
   def enroll_student(student, class_header):
       # Your enrollment logic
       pass

2. Custom description:
   @audit_student_activity(
       activity_type=StudentActivityLog.ActivityType.GRADE_CHANGE,
       description_template="Grade changed from {old_grade} to {new_grade}"
   )
   def update_grade(student, old_grade, new_grade):
       # Your grade update logic
       pass

3. System-generated activities:
   @audit_student_activity(
       activity_type=StudentActivityLog.ActivityType.ATTENDANCE_RECORD,
       is_system_generated=True
   )
   def process_attendance_batch():
       # Your batch processing logic
       pass

4. Extract student from different sources:
   @audit_student_activity(
       activity_type=StudentActivityLog.ActivityType.CLASS_WITHDRAWAL,
       student_source="enrollment.student"  # Extract from nested object
   )
   def withdraw_from_class(enrollment):
       # Your withdrawal logic
       pass
"""

import functools
import logging
from collections.abc import Callable
from typing import Any, TypeVar

from django.contrib.auth import get_user_model
from django.db import transaction

logger = logging.getLogger(__name__)
User = get_user_model()

# Type variable for decorator return type
F = TypeVar("F", bound=Callable[..., Any])


def audit_student_activity(
    activity_type: str,
    description: str = "",
    description_template: str = "",
    student_source: str = "student",
    user_source: str = "user",
    is_system_generated: bool = False,
    extract_context: bool = True,
    visibility: str = "STAFF_ONLY",
    skip_on_error: bool = True,
) -> Callable[[F], F]:
    """Decorator to automatically log student activities.

    This decorator extracts student and user information from function arguments
    and creates an audit log entry after successful execution.

    Args:
        activity_type: Activity type from StudentActivityLog.ActivityType choices
        description: Static description for the activity
        description_template: Template for dynamic descriptions (format string)
        student_source: How to extract student from function args (dot notation supported)
        user_source: How to extract user from function args (dot notation supported)
        is_system_generated: Whether this is a system-generated activity
        extract_context: Whether to automatically extract term/class/program context
        visibility: Who can see this log entry (STAFF_ONLY, STUDENT_VISIBLE, PUBLIC)
        skip_on_error: Whether to skip logging if the function raises an exception

    Examples:
        # Basic usage with student as first argument
        @audit_student_activity(activity_type="CLASS_ENROLLMENT")
        def enroll_student(student, class_header, user):
            pass

        # Extract student from nested object
        @audit_student_activity(
            activity_type="GRADE_ASSIGNMENT",
            student_source="grade.enrollment.student",
            description_template="Assigned grade {grade.letter_grade}"
        )
        def assign_grade(grade, user):
            pass

        # System-generated activity
        @audit_student_activity(
            activity_type="ATTENDANCE_RECORD",
            is_system_generated=True,
            user_source="self.modified_by"
        )
        def process_attendance(self):
            pass
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Import here to avoid circular imports
            from apps.common.models import StudentActivityLog

            # Execute the wrapped function first
            try:
                result = func(*args, **kwargs)
                if skip_on_error:
                    should_log = True
                else:
                    should_log = True
            except Exception:
                if skip_on_error:
                    should_log = False
                    result = None
                    # Re-raise the exception after deciding not to log
                    raise
                else:
                    should_log = True
                    result = None
                    # Will log even on error
                    raise

            # Only log if the function succeeded (or skip_on_error is False)
            if should_log:
                try:
                    # Extract student
                    student = _extract_value_from_source(args, kwargs, student_source)
                    if not student:
                        logger.warning(
                            "Could not extract student for audit logging in %s",
                            func.__name__,
                        )
                        return result

                    # Extract user
                    user = _extract_value_from_source(args, kwargs, user_source)
                    if not user and not is_system_generated:
                        # Try to get user from request if available
                        request = kwargs.get("request") or _find_request_in_args(args)
                        if request and hasattr(request, "user") and request.user.is_authenticated:
                            user = request.user
                        else:
                            logger.warning(
                                "Could not extract user for audit logging in %s",
                                func.__name__,
                            )
                            return result

                    # Build description
                    if description_template:
                        format_context = {
                            "result": result,
                            **kwargs,
                        }
                        # Add positional args with generic names
                        for i, arg in enumerate(args):
                            format_context[f"arg{i}"] = arg

                        # Try to format, fall back to static description
                        try:
                            final_description = description_template.format(**format_context)
                        except (KeyError, AttributeError) as e:
                            logger.warning(
                                "Could not format description template for %s: %s",
                                func.__name__,
                                e,
                            )
                            final_description = description or f"{activity_type} performed"
                    else:
                        final_description = description or f"{activity_type} performed"

                    # Extract context if requested
                    context_data = {}
                    if extract_context:
                        # Try to extract term, class_header, program from args/kwargs
                        for context_key in [
                            "term",
                            "class_header",
                            "program",
                            "course",
                        ]:
                            context_value = kwargs.get(context_key) or _find_in_args(args, context_key)
                            if context_value:
                                context_data[context_key] = context_value

                    # Build activity details
                    activity_details = {
                        "function": func.__name__,
                        "module": func.__module__,
                        "visibility": visibility,
                    }
                    if context_data:
                        activity_details["context"] = context_data

                    # Extract student info
                    student_number = None
                    student_name = None

                    if hasattr(student, "student_id"):
                        # It's a StudentProfile
                        student_number = str(student.student_id)
                        if hasattr(student, "person") and hasattr(student.person, "full_name"):
                            student_name = student.person.full_name
                    elif hasattr(student, "student_number"):
                        # Some other object with student_number
                        student_number = student.student_number
                        if hasattr(student, "student_name"):
                            student_name = student.student_name
                    elif isinstance(student, str):
                        # Assume it's a student number
                        student_number = student

                    if not student_number:
                        logger.warning(
                            "Could not extract student number for audit logging in %s",
                            func.__name__,
                        )
                        return result

                    # Create the log entry
                    with transaction.atomic():
                        StudentActivityLog.objects.create(
                            student_number=student_number,
                            student_name=student_name or "",
                            activity_type=activity_type,
                            description=final_description,
                            performed_by=user or User.objects.get(username="system"),
                            is_system_generated=is_system_generated,
                            activity_details=activity_details,
                            **_extract_standard_context(context_data),
                        )

                except Exception as e:
                    # Log the error but don't fail the original function
                    logger.error(
                        "Failed to create audit log for %s: %s",
                        func.__name__,
                        e,
                        exc_info=True,
                    )

            return result

        return wrapper

    return decorator


def _extract_value_from_source(args: tuple, kwargs: dict, source: str) -> Any:
    """Extract a value from function arguments using dot notation.

    Args:
        args: Function positional arguments
        kwargs: Function keyword arguments
        source: Dot-notation path to extract value (e.g., "student" or "enrollment.student")

    Returns:
        Extracted value or None
    """
    # First try kwargs
    if "." not in source:
        # Simple case - direct argument
        if source in kwargs:
            return kwargs[source]
        # Try positional args by name
        if source == "self" and args:
            return args[0]
        if source == "student" and len(args) > 1:
            # Common pattern: first arg is self, second is student
            return args[1] if args[0].__class__.__name__ != "student" else args[0]
        if source == "user":
            # Try to find user in args
            for arg in args:
                if hasattr(arg, "is_authenticated"):
                    return arg
        return None

    # Handle dot notation
    parts = source.split(".")
    current = None

    # Start with kwargs or args
    if parts[0] in kwargs:
        current = kwargs[parts[0]]
    elif parts[0] == "self" and args:
        current = args[0]
    elif parts[0] == "arg0" and args:
        current = args[0]
    elif parts[0] == "arg1" and len(args) > 1:
        current = args[1]
    else:
        # Try to find in args by type/attribute
        for arg in args:
            if hasattr(arg, parts[0]):
                current = arg
                break

    # Navigate through the path
    for part in parts[1:] if current else []:
        try:
            if hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        except (AttributeError, KeyError):
            return None

    return current


def _find_request_in_args(args: tuple) -> Any:
    """Find a Django request object in function arguments."""
    for arg in args:
        if hasattr(arg, "user") and hasattr(arg, "META"):
            return arg
    return None


def _find_in_args(args: tuple, attr_name: str) -> Any:
    """Find an object with a specific attribute in function arguments."""
    for arg in args:
        if hasattr(arg, attr_name):
            return getattr(arg, attr_name)
    return None


def _extract_standard_context(context_data: dict) -> dict:
    """Extract standard context fields for StudentActivityLog.

    Args:
        context_data: Dictionary with context objects

    Returns:
        Dictionary with extracted field values
    """
    result = {}

    # Extract term information
    term = context_data.get("term")
    if term and hasattr(term, "code"):
        result["term_name"] = term.code

    # Extract class information
    class_header = context_data.get("class_header")
    if class_header:
        if hasattr(class_header, "course") and hasattr(class_header.course, "code"):
            result["class_code"] = class_header.course.code
        if hasattr(class_header, "section_id"):
            result["class_section"] = class_header.section_id

    # Extract course information (if no class_header)
    if not class_header:
        course = context_data.get("course")
        if course and hasattr(course, "code"):
            result["class_code"] = course.code

    # Extract program information
    program = context_data.get("program")
    if program and hasattr(program, "name"):
        result["program_name"] = program.name

    return result
