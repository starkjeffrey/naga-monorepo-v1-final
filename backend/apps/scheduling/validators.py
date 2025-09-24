"""Validators for scheduling app with template requirements.

This module ensures that language classes can only be created when
proper ClassPartTemplate configurations exist.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError

from apps.scheduling.models_templates import ClassPartTemplateSet

if TYPE_CHECKING:
    from apps.curriculum.models import Course
    from apps.scheduling.models import ClassHeader


def validate_language_class_creation(course: Course) -> None:
    """Validate that a language class can be created.

    For language programs (EHSS, GESL, IEAP, EXPRESS), this ensures
    that a ClassPartTemplate exists before allowing class creation.

    Args:
        course: The course to create a class for

    Raises:
        ValidationError: If this is a language course without a template
    """
    # Check if this is a language course
    if not course.code:
        return

    # Language courses follow the pattern: PROGRAM-LEVEL (e.g., EHSS-07, IEAP-03)
    language_programs = ["EHSS", "GESL", "IEAP", "EXPRESS", "W_EXPR"]

    # Check if course code matches language pattern
    parts = course.code.split("-")
    if len(parts) != 2:
        # Not a language course format
        return

    program_code = parts[0]
    if program_code not in language_programs:
        # Not a language program, no template required
        return

    # This is a language course - template is MANDATORY
    try:
        level_number = int(parts[1])
    except ValueError:
        # Invalid level number, but let other validators handle this
        return

    # Check for template existence
    template_set = ClassPartTemplateSet.get_current_for_level(
        program_code=program_code,
        level_number=level_number,
    )

    if not template_set:
        raise ValidationError(
            f"Cannot create class for {course.code}: No ClassPartTemplate defined. "
            f"Language classes require templates to define their structure. "
            f"Please create a ClassPartTemplateSet for {program_code} Level {level_number} first."
        )

    # Validate template has active parts
    if not template_set.templates.filter(is_active=True).exists():
        raise ValidationError(
            f"Cannot create class for {course.code}: Template exists but has no active parts. "
            f"Please define at least one ClassPartTemplate for the template set."
        )


def validate_class_has_proper_structure(class_header: ClassHeader) -> dict:
    """Validate that a class has the proper structure based on its type.

    Args:
        class_header: The class to validate

    Returns:
        Dictionary with 'valid' boolean and 'errors' list
    """
    errors = []

    # Check if this is a language class
    if class_header.course and class_header.course.code:
        parts = class_header.course.code.split("-")
        if len(parts) == 2 and parts[0] in ["EHSS", "GESL", "IEAP", "EXPRESS", "W_EXPR"]:
            # This is a language class - must have parts

            # Check sessions exist
            sessions = class_header.class_sessions.all()
            if not sessions.exists():
                errors.append(f"Language class {class_header.course.code} has no sessions")

            # Check parts exist in sessions
            total_parts = 0
            for session in sessions:
                part_count = session.class_parts.count()
                total_parts += part_count

                if part_count == 0:
                    errors.append(f"Session {session} has no class parts")

            if total_parts == 0:
                errors.append(
                    f"Language class {class_header.course.code} has no parts. "
                    f"This should not happen if created from template."
                )

            # Check if marked as template-derived
            for session in sessions:
                for part in session.class_parts.all():
                    if not part.template_derived:
                        errors.append(
                            f"Part {part.class_part_code} was not created from template. "
                            f"All language class parts should be template-derived."
                        )

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }


def can_promote_without_template(from_course: Course, to_course: Course) -> bool:
    """Check if promotion can proceed without a template.

    This is NEVER true for language courses - templates are mandatory.

    Args:
        from_course: Source course
        to_course: Target course

    Returns:
        False for language courses, True for BA/MA courses
    """
    # Check if target is a language course
    if to_course.code:
        parts = to_course.code.split("-")
        if len(parts) == 2 and parts[0] in ["EHSS", "GESL", "IEAP", "EXPRESS", "W_EXPR"]:
            # Language course - template is MANDATORY
            return False

    # BA/MA courses don't require templates (they don't have parts)
    return True
