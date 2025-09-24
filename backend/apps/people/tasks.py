"""Dramatiq background tasks for the people app.

This module contains asynchronous tasks for photo management including:
- Photo update reminders
- Photo processing
- Batch operations
"""

import logging

import dramatiq
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from apps.people.models import StudentPhoto
from apps.people.utils import PhotoReminder

logger = logging.getLogger(__name__)


@dramatiq.actor(queue_name="default", max_retries=3)
def check_photo_reminders():
    """Daily task to check for students needing photo update reminders.

    This task:
    1. Finds all students with photos needing reminders
    2. Sends email notifications
    3. Updates reminder tracking
    4. Logs actions for audit trail
    """
    logger.info("Starting photo reminder check")

    # Get students needing reminders
    photos_needing_reminder = PhotoReminder.get_students_needing_reminders()
    reminder_count = photos_needing_reminder.count()

    logger.info(f"Found {reminder_count} students needing photo reminders")

    successful_reminders = 0
    failed_reminders = 0

    for photo in photos_needing_reminder:
        try:
            # Send reminder notification
            send_photo_reminder.send(photo.id)
            successful_reminders += 1
        except Exception as e:
            logger.error(f"Failed to queue reminder for photo {photo.id}: {e!s}", exc_info=True)
            failed_reminders += 1

    # Check for overdue photos (for admin notification)
    overdue_photos = PhotoReminder.get_overdue_students()
    overdue_count = overdue_photos.count()

    if overdue_count > 0:
        notify_admin_overdue_photos.send(overdue_count)

    logger.info(
        f"Photo reminder check complete. "
        f"Sent: {successful_reminders}, Failed: {failed_reminders}, "
        f"Overdue: {overdue_count}",
    )


@dramatiq.actor(queue_name="default", max_retries=3)
def send_photo_reminder(photo_id: int):
    """Send a photo update reminder to a specific student.

    Args:
        photo_id: ID of the StudentPhoto needing reminder
    """
    try:
        photo = StudentPhoto.objects.select_related("person", "person__student_profile").get(id=photo_id)
    except StudentPhoto.DoesNotExist:
        logger.error(f"StudentPhoto {photo_id} not found")
        return

    person = photo.person
    student_profile = person.student_profile if hasattr(person, "student_profile") else None

    if not student_profile:
        logger.warning(f"No student profile found for person {person.id}")
        return

    # Determine reminder urgency
    age_months = photo.age_in_months
    is_monk = student_profile.is_monk

    if is_monk:
        deadline_months = 12
        warning_months = 11
    else:
        deadline_months = 6
        warning_months = 5

    # Determine reminder type
    if age_months >= deadline_months:
        reminder_type = "overdue"
        subject = "Your Student Photo is Overdue for Update"
    elif age_months >= warning_months + 0.5:
        reminder_type = "urgent"
        subject = "Urgent: Please Update Your Student Photo Soon"
    else:
        reminder_type = "gentle"
        subject = "Reminder: Time to Update Your Student Photo"

    # Prepare email content
    context = {
        "person": person,
        "student": student_profile,
        "photo_age_days": photo.age_in_days,
        "photo_age_months": round(age_months, 1),
        "deadline_months": deadline_months,
        "reminder_type": reminder_type,
        "upload_date": photo.upload_timestamp,
        "is_monk": is_monk,
    }

    try:
        # Try school email first, then personal email
        recipient_email = person.school_email or person.personal_email

        if not recipient_email:
            logger.warning(f"No email address found for student {student_profile.student_id}")
            return

        # Note: You'll need to create these email templates
        html_message = render_to_string("people/emails/photo_reminder.html", context)
        text_message = render_to_string("people/emails/photo_reminder.txt", context)

        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient_email],
            html_message=html_message,
            fail_silently=False,
        )

        # Update reminder tracking
        photo.send_reminder()

        logger.info(
            f"Sent {reminder_type} photo reminder to {recipient_email} for student {student_profile.student_id}",
        )

    except Exception as e:
        logger.error(
            f"Failed to send photo reminder for student {student_profile.student_id}: {e!s}",
            exc_info=True,
        )
        raise


@dramatiq.actor(queue_name="default", max_retries=1)
def notify_admin_overdue_photos(overdue_count: int):
    """Notify administrators about overdue photos.

    Args:
        overdue_count: Number of students with overdue photos
    """
    admin_emails = getattr(settings, "PHOTO_ADMIN_EMAILS", [])

    if not admin_emails:
        logger.warning("No admin emails configured for photo notifications")
        return

    subject = f"Alert: {overdue_count} Students Have Overdue Photos"

    context = {
        "overdue_count": overdue_count,
        "check_date": timezone.now(),
    }

    try:
        html_message = render_to_string("people/emails/admin_overdue_photos.html", context)
        text_message = render_to_string("people/emails/admin_overdue_photos.txt", context)

        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=admin_emails,
            html_message=html_message,
            fail_silently=False,
        )

        logger.info(f"Sent overdue photo notification to {len(admin_emails)} admins")

    except Exception as e:
        logger.error(
            f"Failed to send admin notification for overdue photos: {e!s}",
            exc_info=True,
        )


@dramatiq.actor(queue_name="default", max_retries=3)
def process_uploaded_photo(photo_id: int):
    """Process a newly uploaded photo asynchronously.

    This can be used for additional processing that doesn't need to
    happen during the upload request, such as:
    - Additional image analysis
    - Backup to cloud storage
    - Face detection/validation
    - Quality assessment

    Args:
        photo_id: ID of the StudentPhoto to process
    """
    try:
        StudentPhoto.objects.get(id=photo_id)

        # Add any additional processing here
        # For example:
        # - Run face detection to ensure it's a valid portrait
        # - Check image quality metrics
        # - Create additional size variants
        # - Backup to S3/cloud storage

        logger.info(f"Successfully processed photo {photo_id}")

    except StudentPhoto.DoesNotExist:
        logger.error(f"StudentPhoto {photo_id} not found for processing")
    except Exception as e:
        logger.error(f"Failed to process photo {photo_id}: {e!s}", exc_info=True)
        raise
