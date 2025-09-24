"""Moodle integration signals for automatic synchronization."""

import logging

from django.conf import settings
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .tasks import (
    async_create_moodle_course,
    async_enroll_student,
    async_sync_person_to_moodle,
    async_unenroll_student,
)

logger = logging.getLogger(__name__)


def is_moodle_enabled() -> bool:
    """Check if Moodle integration is enabled."""
    return getattr(settings, "MOODLE_INTEGRATION", {}).get("ENABLED", False)


def is_auto_sync_enabled() -> bool:
    """Check if automatic synchronization is enabled."""
    return getattr(settings, "MOODLE_INTEGRATION", {}).get("AUTO_SYNC", True)


@receiver(post_save, sender="people.Person")
def sync_person_to_moodle(sender, instance, created, **kwargs):
    """Sync person to Moodle when created or updated.

    Args:
        sender: Model class (Person)
        instance: Person instance
        created: True if this is a new instance
        **kwargs: Additional signal data
    """
    if not is_moodle_enabled():
        return

    if not is_auto_sync_enabled():
        logger.debug("Auto-sync disabled, skipping person sync for %s", instance.id)
        return

    logger.info("Triggering Moodle sync for person %s (created=%s)", instance.id, created)

    # Use background task for non-blocking sync
    async_sync_person_to_moodle.send(person_id=instance.id, created=created)


@receiver(post_save, sender="curriculum.Course")
def sync_course_to_moodle(sender, instance, created, **kwargs):
    """Sync course to Moodle when created or updated.

    Args:
        sender: Model class (Course)
        instance: Course instance
        created: True if this is a new instance
        **kwargs: Additional signal data
    """
    if not is_moodle_enabled():
        return

    if not is_auto_sync_enabled():
        logger.debug("Auto-sync disabled, skipping course sync for %s", instance.id)
        return

    if created:
        logger.info("Triggering Moodle course creation for course %s", instance.id)
        async_create_moodle_course.send(course_id=instance.id)
    else:
        logger.info("Course %s updated, sync may be needed", instance.id)
        # TODO: Implement course update sync


@receiver(post_save, sender="enrollment.Enrollment")
def sync_enrollment_to_moodle(sender, instance, created, **kwargs):
    """Sync enrollment to Moodle when created or updated.

    Args:
        sender: Model class (Enrollment)
        instance: Enrollment instance
        created: True if this is a new enrollment
        **kwargs: Additional signal data
    """
    if not is_moodle_enabled():
        return

    if not is_auto_sync_enabled():
        logger.debug("Auto-sync disabled, skipping enrollment sync for %s", instance.id)
        return

    if created:
        logger.info("Triggering Moodle enrollment for enrollment %s", instance.id)
        async_enroll_student.send(enrollment_id=instance.id)
    else:
        # Check if enrollment status changed to inactive
        if hasattr(instance, "_state") and instance._state.adding is False:
            # This is an update, check if we need to unenroll
            logger.info("Enrollment %s updated, checking if unenrollment needed", instance.id)
            # TODO: Implement logic to detect when unenrollment is needed


@receiver(post_delete, sender="enrollment.Enrollment")
def unenroll_from_moodle(sender, instance, **kwargs):
    """Unenroll student from Moodle when enrollment is deleted.

    Args:
        sender: Model class (Enrollment)
        instance: Enrollment instance being deleted
        **kwargs: Additional signal data
    """
    if not is_moodle_enabled():
        return

    logger.info("Triggering Moodle unenrollment for deleted enrollment %s", instance.id)
    async_unenroll_student.send(enrollment_id=instance.id)


# TODO: Add signals for grading app when it's implemented
# @receiver(post_save, sender="grading.Grade")
# def sync_grade_to_moodle(sender, instance, created, **kwargs):
#     """Sync grade to Moodle when created or updated."""
#     pass
