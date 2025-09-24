"""Django signals for automatic course combination and scheduling integrity management.

This module handles:
1. Automatic creation and management of course combinations when ClassHeaders are created or modified
2. Automatic integrity enforcement for ClassHeader/ClassSession/ClassPart structure
"""

from __future__ import annotations

import logging
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from .class_part_types import ClassPartType
from .models import ClassHeader, ClassPart, ClassSession, CombinedClassInstance
from .services import CombinedClassAutomationService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ClassHeader)
def auto_create_course_combinations(sender, instance: ClassHeader, created: bool, **kwargs):
    """Automatically create or join course combinations when a ClassHeader is created.

    This signal:
    1. Checks if the course belongs to any active CombinedCourseTemplate
    2. Creates a new CombinedClassInstance if needed
    3. Links the ClassHeader to the appropriate instance
    4. Logs the activity for administrative tracking
    """
    if not created:
        return  # Only handle new ClassHeaders

    try:
        combination_instance = CombinedClassAutomationService.handle_class_header_creation(instance)

        if combination_instance:
            logger.info(
                "ClassHeader %s automatically joined combination '%s' for term %s",
                instance,
                combination_instance.template.name,
                instance.term,
                extra={
                    "class_header_id": getattr(instance, "pk", None),
                    "course_code": getattr(instance.course, "code", ""),
                    "combination_instance_id": combination_instance.id,
                    "template_name": combination_instance.template.name,
                    "term": str(instance.term),
                    "auto_created": combination_instance.auto_created,
                },
            )
        else:
            logger.debug(
                "ClassHeader %s - no active combination templates found for course %s",
                instance,
                instance.course.code,
                extra={
                    "class_header_id": getattr(instance, "pk", None),
                    "course_code": getattr(instance.course, "code", ""),
                    "term": str(instance.term),
                },
            )

    except Exception as e:
        logger.error(
            "Failed to process course combination for ClassHeader %s: %s",
            instance,
            str(e),
            extra={
                "class_header_id": instance.id,
                "course_code": instance.course.code,
                "term": str(instance.term),
                "error": str(e),
            },
            exc_info=True,
        )


@receiver(post_save, sender=CombinedClassInstance)
def auto_apply_shared_resources(sender, instance: CombinedClassInstance, created: bool, **kwargs):
    """Automatically apply shared resources when they are assigned to a CombinedClassInstance.

    This signal:
    1. Applies shared teacher/room to all member ClassParts
    2. Logs resource application for administrative tracking
    3. Handles errors gracefully
    """
    if created:
        return  # Skip on creation - resources not assigned yet

    # Check if we have shared resources to apply
    if not (instance.primary_teacher or instance.primary_room):
        return

    try:
        # Apply shared resources to all member class parts
        result = CombinedClassAutomationService.apply_shared_resources(instance)

        if result["updated_parts"] > 0:
            logger.info(
                "Applied shared resources for combination '%s' - updated %d class parts",
                instance.template.name,
                result["updated_parts"],
                extra={
                    "combination_instance_id": instance.id,
                    "template_name": instance.template.name,
                    "term": str(instance.term),
                    "updated_parts": result["updated_parts"],
                    "primary_teacher": (str(instance.primary_teacher) if instance.primary_teacher else None),
                    "primary_room": (str(instance.primary_room) if instance.primary_room else None),
                },
            )

    except Exception as e:
        logger.error(
            "Failed to apply shared resources for combination '%s': %s",
            instance.template.name,
            str(e),
            extra={
                "combination_instance_id": instance.id,
                "template_name": instance.template.name,
                "term": str(instance.term),
                "error": str(e),
            },
            exc_info=True,
        )


# ========== SCHEDULING INTEGRITY SIGNAL HANDLERS ==========


@receiver(post_save, sender=ClassHeader)
def ensure_class_header_integrity(sender, instance: ClassHeader, created: bool, **kwargs):
    """Automatically create appropriate sessions when ClassHeader is created."""
    if created:
        try:
            created_count, sessions = instance.ensure_sessions_exist()
            if created_count > 0:
                logger.info(
                    "Auto-created %d session(s) for %s",
                    created_count,
                    instance,
                    extra={
                        "class_header_id": instance.id,
                        "course_code": instance.course.code,
                        "sessions_created": created_count,
                        "is_ieap_class": instance.is_ieap_class(),
                        "term": str(instance.term),
                    },
                )
        except Exception as e:
            logger.error(
                "Failed to create sessions for ClassHeader %s: %s",
                instance,
                str(e),
                extra={
                    "class_header_id": instance.id,
                    "course_code": instance.course.code,
                    "error": str(e),
                },
                exc_info=True,
            )


@receiver(post_save, sender=ClassSession)
def ensure_session_has_part(sender, instance: ClassSession, created: bool, **kwargs):
    """Ensure every session has at least one part."""
    if created:
        try:
            # Create a default part if none exist
            if not instance.class_parts.exists():
                ClassPart.objects.create(
                    class_session=instance,
                    class_part_code="A",
                    class_part_type=ClassPartType.MAIN,
                    grade_weight=Decimal("1.0"),
                )
                logger.info(
                    "Auto-created default part for %s",
                    instance,
                    extra={
                        "class_session_id": instance.id,
                        "class_header_id": instance.class_header.id,
                        "course_code": instance.class_header.course.code,
                        "session_number": instance.session_number,
                    },
                )
        except Exception as e:
            logger.error(
                "Failed to create default part for ClassSession %s: %s",
                instance,
                str(e),
                extra={
                    "class_session_id": getattr(instance, "pk", None),
                    "class_header_id": getattr(instance.class_header, "pk", None),
                    "error": str(e),
                },
                exc_info=True,
            )


@receiver(pre_delete, sender=ClassSession)
def prevent_last_session_deletion(sender, instance: ClassSession, **kwargs):
    """Prevent deletion of the last session in a ClassHeader."""
    try:
        class_header = instance.class_header
        session_count = getattr(class_header, "class_sessions").count()

        if not class_header.is_ieap_class() and session_count <= 1:
            raise ValidationError("Cannot delete the only session of a regular class")

        if class_header.is_ieap_class() and session_count <= 2:
            raise ValidationError("Cannot delete sessions from IEAP class (must have exactly 2)")

    except Exception as e:
        logger.error(
            "Session deletion validation failed for ClassSession %s: %s",
            instance,
            str(e),
            extra={
                "class_session_id": getattr(instance, "pk", None),
                "class_header_id": getattr(instance.class_header, "pk", None),
                "error": str(e),
            },
            exc_info=True,
        )
        # Re-raise to prevent deletion
        raise
