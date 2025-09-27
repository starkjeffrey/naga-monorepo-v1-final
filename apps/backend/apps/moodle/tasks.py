"""Moodle integration background tasks using Dramatiq."""

import logging

import dramatiq
from django.apps import apps

from .services import MoodleCourseService, MoodleEnrollmentService, MoodleUserService

logger = logging.getLogger(__name__)


@dramatiq.actor(max_retries=3, min_backoff=30000, max_backoff=600000)
def async_sync_person_to_moodle(person_id: int, created: bool = False):
    """Background task to sync person to Moodle.

    Args:
        person_id: Person instance ID
        created: Whether this is a new person
    """
    try:
        Person = apps.get_model("people", "Person")
        person = Person.objects.get(id=person_id)

        service = MoodleUserService()
        success = service.sync_person_to_moodle(person)

        if success:
            logger.info("Successfully synced person %s to Moodle", person_id)
        else:
            logger.error("Failed to sync person %s to Moodle", person_id)

    except Person.DoesNotExist:
        logger.error("Person %s not found for Moodle sync", person_id)
    except Exception as e:
        logger.error("Error syncing person %s to Moodle: %s", person_id, e)
        raise


@dramatiq.actor(max_retries=3, min_backoff=30000, max_backoff=600000)
def async_create_moodle_course(course_id: int):
    """Background task to create course in Moodle.

    Args:
        course_id: Course instance ID
    """
    try:
        Course = apps.get_model("curriculum", "Course")
        course = Course.objects.get(id=course_id)

        service = MoodleCourseService()
        success = service.sync_course_to_moodle(course)

        if success:
            logger.info("Successfully created Moodle course for SIS course %s", course_id)
        else:
            logger.error("Failed to create Moodle course for SIS course %s", course_id)

    except Course.DoesNotExist:
        logger.error("Course %s not found for Moodle sync", course_id)
    except Exception as e:
        logger.error("Error creating Moodle course for SIS course %s: %s", course_id, e)
        raise


@dramatiq.actor(max_retries=3, min_backoff=30000, max_backoff=600000)
def async_enroll_student(enrollment_id: int):
    """Background task to enroll student in Moodle.

    Args:
        enrollment_id: Enrollment instance ID
    """
    try:
        Enrollment = apps.get_model("enrollment", "Enrollment")
        enrollment = Enrollment.objects.get(id=enrollment_id)

        service = MoodleEnrollmentService()
        success = service.enroll_student(enrollment)

        if success:
            logger.info(
                "Successfully enrolled student in Moodle for enrollment %s",
                enrollment_id,
            )
        else:
            logger.error("Failed to enroll student in Moodle for enrollment %s", enrollment_id)

    except Enrollment.DoesNotExist:
        logger.error("Enrollment %s not found for Moodle sync", enrollment_id)
    except Exception as e:
        logger.error("Error enrolling student in Moodle for enrollment %s: %s", enrollment_id, e)
        raise


@dramatiq.actor(max_retries=3, min_backoff=30000, max_backoff=600000)
def async_unenroll_student(enrollment_id: int):
    """Background task to unenroll student from Moodle.

    Args:
        enrollment_id: Enrollment instance ID
    """
    try:
        MoodleEnrollmentService()
        # Note: We can't get the enrollment instance since it's deleted
        # We'll need to store the mapping data separately or pass required data
        logger.info("Processing unenrollment for enrollment %s", enrollment_id)
        # TODO: Implement unenrollment logic

    except Exception as e:
        logger.error(
            "Error unenrolling student from Moodle for enrollment %s: %s",
            enrollment_id,
            e,
        )
        raise


@dramatiq.actor
def bulk_sync_users_to_moodle():
    """Background task for bulk user synchronization.

    This task can be scheduled to run periodically to sync all users
    or to handle large batches of users.
    """
    try:
        Person = apps.get_model("people", "Person")
        service = MoodleUserService()

        # Get all persons that need syncing
        persons = Person.objects.filter(
            # Add filters for persons that need syncing
            # For example: moodle_mapping__isnull=True
        )

        success_count = 0
        error_count = 0

        for person in persons:
            try:
                if service.sync_person_to_moodle(person):
                    success_count += 1
                else:
                    error_count += 1
            except Exception as e:
                logger.error("Error syncing person %s in bulk sync: %s", person.id, e)
                error_count += 1

        logger.info(
            "Bulk user sync completed: %s successful, %s errors",
            success_count,
            error_count,
        )

    except Exception as e:
        logger.error("Error in bulk user sync: %s", e)
        raise


@dramatiq.actor
def moodle_health_check():
    """Background task to check Moodle connectivity and log status.

    This task can be scheduled to run periodically to monitor
    Moodle integration health.
    """
    try:
        from .services import MoodleAPIClient

        client = MoodleAPIClient()
        is_healthy = client.test_connection()

        if is_healthy:
            logger.info("Moodle health check: OK")
        else:
            logger.error("Moodle health check: FAILED")

        # TODO: Store health check results in database for monitoring

    except Exception as e:
        logger.error("Error in Moodle health check: %s", e)
        raise


@dramatiq.actor
def cleanup_old_api_logs():
    """Background task to clean up old API logs.

    This task removes old API logs to prevent database bloat.
    Can be scheduled to run daily or weekly.
    """
    try:
        from datetime import datetime, timedelta

        from .models import MoodleAPILog

        # Keep logs for 30 days
        cutoff_date = datetime.now() - timedelta(days=30)

        deleted_count, _ = MoodleAPILog.objects.filter(created_at__lt=cutoff_date).delete()

        logger.info("Cleaned up %s old Moodle API logs", deleted_count)

    except Exception as e:
        logger.error("Error cleaning up Moodle API logs: %s", e)
        raise
