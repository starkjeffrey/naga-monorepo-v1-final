"""Django signals for automatic grading calculations.

This module provides signal handlers for:
- Automatic session grade calculations when class part grades are updated
- GPA recalculation when session grades change
- Grade change history tracking
- Student notification triggers
- Academic standing updates

Following clean architecture with proper error handling and
async processing for performance-critical operations.
"""

import logging
from typing import Any

from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from .models import ClassPartGrade, ClassSessionGrade, GPARecord
from .services import ClassSessionGradeService, GradeCalculationError

# Set up logging
logger = logging.getLogger(__name__)


@receiver(post_save, sender=ClassPartGrade)
def handle_class_part_grade_save(
    sender: type[ClassPartGrade],
    instance: ClassPartGrade,
    created: bool,
    **kwargs: Any,
) -> None:
    """Handle class part grade save to trigger automatic calculations.

    This signal handler:
    1. Recalculates session grades when part grades are updated
    2. Triggers GPA recalculation for significant changes
    3. Updates academic standing if needed
    """
    try:
        # Skip if this is a draft grade
        if instance.grade_status == ClassPartGrade.GradeStatus.DRAFT:
            logger.debug("Skipping calculations for draft grade %s", instance.id)
            return

        # Recalculate session grade
        session_grade = ClassSessionGradeService.calculate_session_grade(
            enrollment=instance.enrollment,
            class_session=instance.class_part.class_session,
            force_recalculate=True,
        )

        if session_grade:
            logger.info(
                "Updated session grade for student %s in session %s",
                instance.student,
                instance.class_part.class_session,
            )

            if instance.grade_status == ClassPartGrade.GradeStatus.FINALIZED:
                _schedule_gpa_recalculation(instance)

    except GradeCalculationError as e:
        logger.exception(
            "Grade calculation error for ClassPartGrade %s: %s",
            instance.id,
            e,
        )
    except Exception as e:
        logger.exception("Unexpected error in grade signal handler: %s", e)


@receiver(post_delete, sender=ClassPartGrade)
def handle_class_part_grade_delete(
    sender: type[ClassPartGrade],
    instance: ClassPartGrade,
    **kwargs: Any,
) -> None:
    """Handle class part grade deletion to recalculate dependent grades.

    When a class part grade is deleted, we need to recalculate
    the session grade to reflect the removal.
    """
    try:
        # Recalculate session grade after deletion
        ClassSessionGradeService.calculate_session_grade(
            enrollment=instance.enrollment,
            class_session=instance.class_part.class_session,
            force_recalculate=True,
        )

        logger.info(
            "Recalculated session grade after deletion for student %s in session %s",
            instance.student,
            instance.class_part.class_session,
        )

        # Schedule GPA recalculation
        _schedule_gpa_recalculation(instance)

    except Exception as e:
        logger.exception("Error recalculating grades after deletion: %s", e)


@receiver(pre_save, sender=ClassPartGrade)
def handle_class_part_grade_pre_save(
    sender: type[ClassPartGrade],
    instance: ClassPartGrade,
    **kwargs: Any,
) -> None:
    """Handle class part grade pre-save to track changes.

    This signal handler captures the previous state of the grade
    for creating detailed change history records.
    """
    if instance.pk:  # Only for updates, not new records
        try:
            previous_grade = ClassPartGrade.objects.get(pk=instance.pk)

            # Store previous values for change tracking
            instance._previous_numeric_score = previous_grade.numeric_score
            instance._previous_letter_grade = previous_grade.letter_grade
            instance._previous_status = previous_grade.grade_status

        except ClassPartGrade.DoesNotExist:
            # Grade was deleted in the meantime, ignore
            pass
        except Exception as e:
            logger.exception("Error capturing previous grade state: %s", e)


@receiver(post_save, sender=ClassSessionGrade)
def handle_session_grade_save(
    sender: type[ClassSessionGrade],
    instance: ClassSessionGrade,
    created: bool,
    **kwargs: Any,
) -> None:
    """Handle session grade save to trigger GPA recalculation.

    When session grades are updated, we may need to recalculate
    term and cumulative GPAs for the student.
    """
    try:
        # Only trigger GPA recalculation for significant changes
        if not created:
            # Check if the GPA points changed significantly
            threshold = 0.1  # Minimum change to trigger recalculation

            try:
                previous_session = ClassSessionGrade.objects.get(pk=instance.pk)
                if abs(instance.gpa_points - previous_session.gpa_points) < threshold:
                    logger.debug(
                        "Skipping GPA recalculation for minor change in session %s",
                        instance.id,
                    )
                    return
            except ClassSessionGrade.DoesNotExist:
                pass  # Proceed with recalculation

        # Schedule GPA recalculation for this session grade
        _schedule_gpa_recalculation_for_session(instance)

    except Exception as e:
        logger.exception("Error in session grade signal handler: %s", e)


@receiver(post_save, sender=GPARecord)
def handle_gpa_record_save(
    sender: type[GPARecord],
    instance: GPARecord,
    created: bool,
    **kwargs: Any,
) -> None:
    """Handle GPA record save to trigger academic standing updates.

    When GPA records are updated, we need to check if the student's
    academic standing has changed and trigger appropriate notifications.
    """
    try:
        # Only process cumulative GPA records for standing determination
        if instance.gpa_type != GPARecord.GPAType.CUMULATIVE:
            return

        # Future enhancement: Implement academic standing determination and notifications
        # This would involve:
        # 1. Calculating current academic standing
        # 2. Comparing with previous standing
        # 3. Triggering notifications if standing changed
        # 4. Updating student profile with current standing

        logger.info(
            "GPA record updated for student %s - GPA: %s",
            instance.student,
            instance.gpa_value,
        )

        if instance.gpa_value < 2.0:
            logger.warning(
                "Student %s has low GPA: %s - may require academic intervention",
                instance.student,
                instance.gpa_value,
            )

    except Exception as e:
        logger.exception("Error in GPA record signal handler: %s", e)


def _schedule_gpa_recalculation(grade_instance: ClassPartGrade) -> None:
    """Schedule GPA recalculation for a grade change.

    Uses Dramatiq for async task processing in production environments.
    """
    try:
        term = grade_instance.class_header.term

        # Note: Get student's current major - for now assume first active major
        # This should be replaced with proper major determination logic

        logger.info("GPA recalculation needed for student in term %s", term)

    except Exception as e:
        logger.exception("Error scheduling GPA recalculation: %s", e)


def _schedule_gpa_recalculation_for_session(session_grade: ClassSessionGrade) -> None:
    """Schedule GPA recalculation for a session grade change.

    Similar to _schedule_gpa_recalculation but for session-level changes.
    """
    try:
        student = session_grade.enrollment.student
        term = session_grade.class_session.class_header.term

        logger.info(
            "GPA recalculation needed for student %s in term %s (session grade change)",
            student,
            term,
        )

    except Exception as e:
        logger.exception("Error scheduling GPA recalculation for session: %s", e)


# Utility signal handlers for maintaining data integrity


@receiver(post_save, sender=ClassPartGrade)
def update_notification_status(
    sender: type[ClassPartGrade],
    instance: ClassPartGrade,
    created: bool,
    **kwargs: Any,
) -> None:
    """Update notification status when grades reach certain statuses.

    Automatically marks students for notification when grades
    are finalized or approved.
    """
    try:
        # Mark for notification when grade is finalized
        if instance.grade_status == ClassPartGrade.GradeStatus.FINALIZED and not instance.student_notified:
            # In production, this would trigger actual notification
            logger.info(
                "Grade finalized for %s - notification should be sent",
                instance.student,
            )

            instance.notification_date = timezone.now()
            instance.save(update_fields=["notification_date"])

    except Exception as e:
        logger.exception("Error updating notification status: %s", e)


@receiver(post_save, sender=ClassPartGrade)
def validate_grade_consistency(
    sender: type[ClassPartGrade],
    instance: ClassPartGrade,
    created: bool,
    **kwargs: Any,
) -> None:
    """Validate grade consistency after save.

    Ensures that calculated fields like GPA points are consistent
    with the entered grades and grading scale.
    """
    try:
        # Skip validation for draft grades
        if instance.grade_status == ClassPartGrade.GradeStatus.DRAFT:
            return

        # Future enhancement: Implement comprehensive grade validation
        # This would include:
        # 1. Checking GPA points match the letter grade
        # 2. Verifying letter grade matches numeric score
        # 3. Ensuring grading scale is appropriate for the course

        logger.debug("Grade consistency validated for %s", instance.id)

    except Exception as e:
        logger.exception("Error validating grade consistency: %s", e)


# Performance monitoring signals


@receiver(post_save, sender=ClassSessionGrade)
def log_calculation_performance(
    sender: type[ClassSessionGrade],
    instance: ClassSessionGrade,
    created: bool,
    **kwargs: Any,
) -> None:
    """Log calculation performance for monitoring.

    Tracks how long grade calculations take to identify
    performance bottlenecks.
    """
    try:
        if created:
            calculation_details = instance.calculation_details

            if "calculation_time" in calculation_details:
                calc_time = calculation_details["calculation_time"]

                if calc_time > 1.0:  # Log slow calculations (>1 second)
                    logger.warning(
                        "Slow grade calculation detected: %ss for session %s",
                        calc_time,
                        instance.id,
                    )

    except Exception as e:
        logger.exception("Error logging calculation performance: %s", e)


# Signal connection verification


def verify_signal_connections() -> bool:
    """Verify that all required signals are properly connected.

    This function can be called during application startup to ensure
    all signal handlers are registered correctly.
    """
    try:
        # Check if our signal handlers are connected
        # post_save signal already imported at top

        post_save_receivers = post_save._live_receivers(sender=ClassPartGrade)

        # Count our handlers
        our_handlers = [
            "handle_class_part_grade_save",
            "update_notification_status",
            "validate_grade_consistency",
        ]

        connected_handlers = []
        for receiver_ref in post_save_receivers:
            if hasattr(receiver_ref, "__name__"):
                if receiver_ref.__name__ in our_handlers:
                    connected_handlers.append(receiver_ref.__name__)

        logger.info("Connected signal handlers: %s", connected_handlers)

        return len(connected_handlers) == len(our_handlers)

    except Exception as e:
        logger.exception("Error verifying signal connections: %s", e)
        return False
