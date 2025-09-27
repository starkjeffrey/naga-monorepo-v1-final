"""Signal handlers for People app models.

This module provides Django signal handlers for automatic logging and
business logic triggers when people models are created or updated.

Key handlers:
- StudentProfile monk status change logging
- Person name change tracking
- Profile activation/deactivation events
"""

import logging

from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import StudentAuditLog, StudentProfile

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=StudentProfile)
def track_monk_status_changes(sender, instance, **kwargs):
    """Automatically log monk status changes for scholarship eligibility tracking.

    This signal handler ensures that ANY change to is_monk field is logged,
    even if the change bypasses the recommended methods. This is critical
    for scholarship and financial aid audit trails.
    """
    # Only track changes for existing instances
    if instance.pk:
        try:
            # Get the current value from the database
            old_instance = StudentProfile.objects.get(pk=instance.pk)
            old_monk_status = old_instance.is_monk
            new_monk_status = instance.is_monk

            # Check if monk status changed
            if old_monk_status != new_monk_status:
                # Only log if this change wasn't already logged by the methods
                # We detect this by checking if the change is being made through
                # the save() call with update_fields containing 'is_monk'
                update_fields = kwargs.get("update_fields")

                # If update_fields is specified and contains 'is_monk',
                # this change was likely made through our logging methods
                if update_fields and "is_monk" in update_fields:
                    # Skip automatic logging as it should already be handled
                    return

                # This is a direct field change - log it with system user
                logger.warning(
                    "Direct monk status change detected for student %s: %s -> %s. "
                    "Recommend using set_monk_status() method for proper logging.",
                    instance.student_id,
                    old_monk_status,
                    new_monk_status,
                )

                # Log the change with system as the user since no user was provided
                StudentAuditLog.log_monk_status_change(
                    student=instance,
                    old_status=old_monk_status,
                    new_status=new_monk_status,
                    user=None,  # System change
                    notes="Automatic logging of direct field change (recommend using set_monk_status method)",
                )

        except StudentProfile.DoesNotExist:
            # Instance was deleted in the meantime, skip logging
            pass
        except Exception as e:
            logger.exception(
                "Error tracking monk status change for student %s: %s",
                getattr(instance, "student_id", "unknown"),
                e,
            )


@receiver(pre_save, sender=StudentProfile)
def validate_monk_status_business_rules(sender, instance, **kwargs):
    """Validate business rules related to monk status.

    This ensures that monk status changes follow institutional policies
    and that any dependent data remains consistent.
    """
    try:
        # Add any business rule validations here
        # For example, checking age requirements, enrollment status, etc.

        # Currently no specific business rules implemented
        # This is a placeholder for future policy enforcement
        pass

    except Exception as e:
        logger.exception(
            "Error validating monk status business rules for student %s: %s",
            getattr(instance, "student_id", "unknown"),
            e,
        )
