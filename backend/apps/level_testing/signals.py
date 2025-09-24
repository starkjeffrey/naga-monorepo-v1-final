"""Signal handlers for level testing app.

This module contains Django signal handlers that automatically trigger
business logic when models are created or updated. Follows clean architecture
principles by keeping business logic in services.

Signal handlers:
- TestPayment creation/update → Finance integration
- PotentialStudent status changes → Workflow automation
- DuplicateCandidate creation → Notification handling
"""

import logging

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.level_testing.finance_integration import (
    create_test_fee_transaction,
    update_test_payment_status,
)
from apps.level_testing.models import (
    ApplicationStatus,
    DuplicateCandidate,
    PotentialStudent,
    TestPayment,
)
from apps.level_testing.services import TestWorkflowService

logger = logging.getLogger(__name__)


@receiver(post_save, sender=TestPayment)
def handle_test_payment_created(sender, instance, created, **kwargs):
    """Handle TestPayment creation and updates.

    Automatically creates finance transactions and updates payment status.
    """
    if created:
        # Create finance transaction for new test payment
        try:
            result = create_test_fee_transaction(instance)

            if result.get("success"):
                logger.info(
                    "Finance transaction created for test payment %s: Transaction %s",
                    instance.id,
                    result.get("transaction_id"),
                )
            else:
                logger.error(
                    "Failed to create finance transaction for test payment %s: %s",
                    instance.id,
                    result.get("error"),
                )

        except Exception as e:
            logger.exception(
                "Error creating finance transaction for test payment %s: %s",
                instance.id,
                e,
            )

    elif instance.is_paid and instance.finance_transaction_id:
        # Update existing transaction when payment is received
        try:
            result = update_test_payment_status(instance, payment_received=True)

            if result.get("success"):
                logger.info(
                    "Updated finance transaction %s for paid test payment %s",
                    instance.finance_transaction_id,
                    instance.id,
                )
            else:
                logger.warning(
                    "Failed to update finance transaction for test payment %s: %s",
                    instance.id,
                    result.get("error"),
                )

        except Exception as e:
            logger.exception(
                "Error updating finance transaction for test payment %s: %s",
                instance.id,
                e,
            )


@receiver(post_save, sender=TestPayment)
def handle_payment_status_change(sender, instance, created, **kwargs):
    """Handle payment status changes to advance potential student workflow."""
    if not created and instance.is_paid:
        potential_student = instance.potential_student

        # Advance to PAID status if payment is received and student is registered
        if potential_student.status == ApplicationStatus.REGISTERED:
            try:
                potential_student.advance_status(
                    ApplicationStatus.PAID,
                    f"Test fee payment received via {instance.payment_method}",
                    user=instance.received_by,
                )

                logger.info(
                    "Advanced %s to PAID status after payment received",
                    potential_student.full_name_eng,
                )

            except Exception as e:
                logger.exception(
                    "Failed to advance status for %s after payment: %s",
                    potential_student.full_name_eng,
                    e,
                )


@receiver(pre_save, sender=PotentialStudent)
def handle_potential_student_status_change(sender, instance, **kwargs):
    """Handle PotentialStudent status changes for workflow automation."""
    if instance.pk:  # Only for existing records
        try:
            # Get the old instance to compare status
            old_instance = PotentialStudent.objects.get(pk=instance.pk)

            # Check if status is changing to REGISTERED
            if old_instance.status != ApplicationStatus.REGISTERED and instance.status == ApplicationStatus.REGISTERED:
                # Trigger duplicate detection if not already performed
                if not instance.duplicate_check_performed:
                    # This will be handled by TestWorkflowService in post_save
                    pass

        except PotentialStudent.DoesNotExist:
            # New instance, will be handled in post_save
            pass
        except Exception as e:
            logger.exception(
                "Error in pre_save for PotentialStudent %s: %s",
                instance.id,
                e,
            )


@receiver(post_save, sender=PotentialStudent)
def handle_potential_student_workflow(sender, instance, created, **kwargs):
    """Handle PotentialStudent workflow automation."""
    if created:
        logger.info(
            "New potential student created: %s (%s)",
            instance.full_name_eng,
            instance.test_number,
        )
        return

    # Handle status transitions that require business logic
    if instance.status == ApplicationStatus.REGISTERED and not instance.duplicate_check_performed:
        try:
            workflow_service = TestWorkflowService()
            success = workflow_service.process_registration(instance)

            if success:
                logger.info(
                    "Processed registration workflow for %s",
                    instance.full_name_eng,
                )
            else:
                logger.error(
                    "Failed to process registration workflow for %s",
                    instance.full_name_eng,
                )

        except Exception as e:
            logger.exception(
                "Error processing registration workflow for %s: %s",
                instance.full_name_eng,
                e,
            )


@receiver(post_save, sender=DuplicateCandidate)
def handle_duplicate_candidate_created(sender, instance, created, **kwargs):
    """Handle DuplicateCandidate creation for high-priority notifications."""
    if created and instance.risk_level == "HIGH":
        logger.warning(
            "HIGH RISK duplicate candidate created: %s → %s (confidence: %s, debt: %s)",
            instance.potential_student.full_name_eng,
            instance.matched_name,
            instance.confidence_score,
            instance.has_outstanding_debt,
        )

        # TODO: Implement notification system for staff alerts
        # This could send email notifications, create admin alerts, etc.

        if instance.has_outstanding_debt:
            logger.critical(
                "DEBT CONCERN: %s matches %s who has outstanding debt of $%s",
                instance.potential_student.full_name_eng,
                instance.matched_name,
                instance.debt_amount or "unknown amount",
            )


@receiver(post_save, sender=TestPayment)
def create_test_payment_on_registration(sender, **kwargs):
    """Automatically create TestPayment when PotentialStudent reaches REGISTERED status.

    Note: This is handled separately to ensure TestPayment exists for finance integration.
    """
    # This signal is triggered by TestPayment saves, so we don't create payments here
    # Instead, TestPayment creation is handled in the workflow service


# Additional signal for ensuring test number generation
@receiver(pre_save, sender=PotentialStudent)
def ensure_test_number_generation(sender, instance, **kwargs):
    """Ensure test number is generated when status changes to REGISTERED."""
    if instance.status == ApplicationStatus.REGISTERED and not instance.test_number:
        try:
            instance.test_number = PotentialStudent.generate_test_number()
            logger.info(
                "Generated test number %s for %s",
                instance.test_number,
                instance.full_name_eng,
            )
        except Exception as e:
            logger.exception(
                "Failed to generate test number for %s: %s",
                instance.full_name_eng,
                e,
            )
