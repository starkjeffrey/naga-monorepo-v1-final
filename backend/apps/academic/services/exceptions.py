"""Student exception and override services.

This module provides business logic for managing student-specific exceptions
to canonical requirements and course overrides.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.academic.models import StudentCourseOverride, StudentRequirementException
from apps.academic.services.canonical import CanonicalRequirementService
from apps.common.models import StudentActivityLog, SystemAuditLog

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

    type UserType = AbstractUser
else:
    type UserType = get_user_model()


class StudentRequirementExceptionService:
    """Service for managing student requirement exceptions."""

    @classmethod
    @transaction.atomic
    def approve_exception(
        cls,
        exception: StudentRequirementException,
        user: UserType,
        notes: str = "",
    ) -> StudentRequirementException:
        """Approve a student requirement exception.

        Args:
            exception: StudentRequirementException instance to approve
            user: User performing the approval
            notes: Optional approval notes

        Returns:
            Updated StudentRequirementException instance

        Raises:
            ValidationError: If exception cannot be approved
        """
        if exception.approval_status != StudentRequirementException.ApprovalStatus.PENDING:
            raise ValidationError("Can only approve pending exceptions")

        # Update exception
        exception.approval_status = StudentRequirementException.ApprovalStatus.APPROVED
        exception.approved_by = user
        exception.approval_date = timezone.now()
        if notes:
            exception.notes = f"{exception.notes}\n\nApproval: {notes}".strip()

        exception.save(update_fields=["approval_status", "approved_by", "approval_date", "notes"])

        # Update degree progress
        CanonicalRequirementService.update_degree_progress(exception.student, exception.canonical_requirement.major)

        # Create audit logs
        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get_for_model(exception)

        SystemAuditLog.objects.create(
            performed_by=user,
            action_type=SystemAuditLog.ActionType.ACADEMIC_POLICY_OVERRIDE,
            content_type=content_type,
            object_id=exception.id,  # type: ignore[attr-defined]
            target_app="academic",
            target_model="StudentRequirementException",
            override_reason=f"Requirement exception approved for {exception.canonical_requirement}",
            original_restriction="Academic requirement completion",
            override_details={
                "student_id": getattr(exception, "student_id", getattr(exception.student, "pk", None)),
                "canonical_requirement_id": getattr(
                    exception, "canonical_requirement_id", getattr(exception.canonical_requirement, "pk", None)
                ),
                "exception_type": exception.exception_type,
                "credits": str(exception.exception_credits),
            },
        )

        StudentActivityLog.objects.create(
            student_number=exception.student.student_id
            if hasattr(exception.student, "student_id")
            else str(exception.student.id),
            student_name=str(exception.student),
            activity_type=StudentActivityLog.ActivityType.MANAGEMENT_OVERRIDE,
            description=f"Requirement exception approved: {exception.canonical_requirement}",
            term_name=getattr(exception, "term_name", ""),
            program_name=getattr(exception, "program_name", ""),
        )

        # Trigger student notification for mobile app integration
        cls._notify_student_of_status_change(
            student=exception.student,
            notification_type="EXCEPTION_APPROVED",
            data={
                "requirement": str(exception.canonical_requirement),
                "approval_date": exception.approval_date.isoformat() if exception.approval_date else None,
                "notes": notes or "",
            },
        )

        return exception

    @classmethod
    @transaction.atomic
    def reject_exception(
        cls,
        exception: StudentRequirementException,
        user: UserType,
        reason: str,
    ) -> StudentRequirementException:
        """Reject a student requirement exception.

        Args:
            exception: StudentRequirementException instance to reject
            user: User performing the rejection
            reason: Rejection reason (required)

        Returns:
            Updated StudentRequirementException instance

        Raises:
            ValidationError: If exception cannot be rejected
        """
        if exception.approval_status != StudentRequirementException.ApprovalStatus.PENDING:
            raise ValidationError("Can only reject pending exceptions")

        if not reason:
            raise ValidationError("Rejection reason is required")

        # Update exception
        exception.approval_status = StudentRequirementException.ApprovalStatus.REJECTED
        exception.approved_by = user
        exception.approval_date = timezone.now()
        exception.rejection_reason = reason

        exception.save(
            update_fields=[
                "approval_status",
                "approved_by",
                "approval_date",
                "rejection_reason",
            ]
        )

        # Create audit logs
        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get_for_model(exception)

        SystemAuditLog.objects.create(
            performed_by=user,
            action_type=SystemAuditLog.ActionType.ACADEMIC_POLICY_OVERRIDE,
            content_type=content_type,
            object_id=exception.id,  # type: ignore[attr-defined]
            target_app="academic",
            target_model="StudentRequirementException",
            override_reason=f"Requirement exception rejected: {reason}",
            original_restriction="Academic requirement completion",
            override_details={
                "student_id": getattr(exception, "student_id", getattr(exception.student, "pk", None)),
                "canonical_requirement_id": getattr(
                    exception, "canonical_requirement_id", getattr(exception.canonical_requirement, "pk", None)
                ),
                "reason": reason,
            },
        )

        StudentActivityLog.objects.create(
            student_number=exception.student.student_id
            if hasattr(exception.student, "student_id")
            else str(exception.student.id),
            student_name=str(exception.student),
            activity_type=StudentActivityLog.ActivityType.MANAGEMENT_OVERRIDE,
            description=f"Requirement exception rejected: {exception.canonical_requirement}",
            term_name=getattr(exception, "term_name", ""),
            program_name=getattr(exception, "program_name", ""),
        )

        # Trigger student notification for mobile app integration
        cls._notify_student_of_status_change(
            student=exception.student,
            notification_type="EXCEPTION_REJECTED",
            data={
                "requirement": str(exception.canonical_requirement),
                "rejection_date": exception.approval_date.isoformat() if exception.approval_date else None,
                "reason": reason or "",
            },
        )

        return exception

    @classmethod
    def get_student_exceptions(
        cls, student: Any, major: Any = None, approved_only: bool = False
    ) -> QuerySet[StudentRequirementException]:
        """Get all requirement exceptions for a student.

        Args:
            student: StudentProfile instance
            major: Optional major to filter by
            approved_only: Whether to return only approved exceptions

        Returns:
            QuerySet of StudentRequirementException instances
        """
        exceptions = (
            StudentRequirementException.objects.filter(student=student)
            .select_related(
                "canonical_requirement",
                "canonical_requirement__required_course",
                "canonical_requirement__major",
                "fulfilling_course",
                "fulfilling_transfer_credit",
                "approved_by",
            )
            .order_by("canonical_requirement__sequence_number")
        )

        if major:
            exceptions = exceptions.filter(canonical_requirement__major=major)

        if approved_only:
            exceptions = exceptions.filter(approval_status=StudentRequirementException.ApprovalStatus.APPROVED)

        return exceptions

    @classmethod
    @transaction.atomic
    def create_transfer_credit_exception(
        cls, transfer_credit: Any, canonical_requirement: Any, user: UserType
    ) -> StudentRequirementException:
        """Create an exception based on an approved transfer credit.

        Args:
            transfer_credit: Approved TransferCredit instance
            canonical_requirement: CanonicalRequirement to fulfill
            user: User creating the exception

        Returns:
            Created StudentRequirementException instance
        """
        if transfer_credit.approval_status != transfer_credit.ApprovalStatus.APPROVED:
            raise ValidationError("Transfer credit must be approved first")

        exception = StudentRequirementException.objects.create(
            student=transfer_credit.student,
            canonical_requirement=canonical_requirement,
            exception_type=StudentRequirementException.ExceptionType.TRANSFER_CREDIT,
            fulfilling_transfer_credit=transfer_credit,
            reason=f"Transfer credit from {transfer_credit.external_institution}",
            effective_term=canonical_requirement.effective_term,
            approval_status=StudentRequirementException.ApprovalStatus.APPROVED,
            requested_by=user,
            approved_by=user,
            approval_date=timezone.now(),
        )

        # Update degree progress
        CanonicalRequirementService.update_degree_progress(transfer_credit.student, canonical_requirement.major)

        return exception

    @classmethod
    def _notify_student_of_status_change(cls, student: Any, notification_type: str, data: dict[str, Any]) -> None:
        """Send notification to student about status changes.

        This method provides a centralized way to notify students about
        academic status changes through the mobile app integration.

        Args:
            student: StudentProfile instance
            notification_type: Type of notification (EXCEPTION_APPROVED, etc.)
            data: Notification payload data
        """
        # Create a student activity log entry that can be consumed by notification service
        StudentActivityLog.objects.create(
            student_number=student.student_id if hasattr(student, "student_id") else str(student.id),
            student_name=str(student),
            activity_type=StudentActivityLog.ActivityType.PROFILE_UPDATE,
            description=f"Mobile app notification: {notification_type}",
            activity_details=data if isinstance(data, dict) else {"data": str(data)},  # Store notification data
            performed_by_id=1,  # System user
        )

        # In a full implementation, this would integrate with:
        # - Push notification service (Firebase/APNs)
        # - WebSocket connections for real-time updates
        # - Email notification service as fallback
        # For now, we store the notification data for later processing


class StudentCourseOverrideService:
    """Service for managing student course overrides."""

    @classmethod
    @transaction.atomic
    def approve_override(
        cls, override: StudentCourseOverride, user: UserType, notes: str = ""
    ) -> StudentCourseOverride:
        """Approve a student course override.

        Args:
            override: StudentCourseOverride instance to approve
            user: User performing the approval
            notes: Optional approval notes

        Returns:
            Updated StudentCourseOverride instance

        Raises:
            ValidationError: If override cannot be approved
        """
        if override.approval_status != StudentCourseOverride.ApprovalStatus.PENDING:
            raise ValidationError("Can only approve pending overrides")

        # Update override
        override.approval_status = StudentCourseOverride.ApprovalStatus.APPROVED
        override.approved_by = user
        override.approval_date = timezone.now()
        if notes:
            override.academic_advisor_notes = f"{override.academic_advisor_notes}\n\nApproval: {notes}".strip()

        override.save(
            update_fields=[
                "approval_status",
                "approved_by",
                "approval_date",
                "academic_advisor_notes",
            ]
        )

        # Create audit logs
        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get_for_model(override)

        SystemAuditLog.objects.create(
            performed_by=user,
            action_type=SystemAuditLog.ActionType.ACADEMIC_POLICY_OVERRIDE,
            content_type=content_type,
            object_id=override.id,  # type: ignore[attr-defined]
            target_app="academic",
            target_model="StudentCourseOverride",
            override_reason=(
                f"Course override approved: {override.original_course.code} → {override.substitute_course.code}"
            ),
            original_restriction="Course requirement completion",
            override_details={
                "student_id": override.student_id,
                "original_course": override.original_course.code,
                "substitute_course": override.substitute_course.code,
            },
        )

        StudentActivityLog.objects.create(
            student_number=override.student.student_id
            if hasattr(override.student, "student_id")
            else str(override.student.id),
            student_name=str(override.student),
            activity_type=StudentActivityLog.ActivityType.MANAGEMENT_OVERRIDE,
            description=(
                f"Course override approved: {override.original_course.code} → {override.substitute_course.code}"
            ),
            class_code=override.substitute_course.code if override.substitute_course else "",
        )

        # Trigger student notification for mobile app integration
        cls._notify_student_of_status_change(
            student=override.student,
            notification_type="COURSE_OVERRIDE_APPROVED",
            data={
                "original_course": override.original_course.code,
                "substitute_course": override.substitute_course.code,
                "approval_date": override.approval_date.isoformat() if override.approval_date else None,
                "notes": notes or "",
            },
        )

        return override

    @classmethod
    @transaction.atomic
    def reject_override(cls, override: StudentCourseOverride, user: UserType, reason: str) -> StudentCourseOverride:
        """Reject a student course override.

        Args:
            override: StudentCourseOverride instance to reject
            user: User performing the rejection
            reason: Rejection reason (required)

        Returns:
            Updated StudentCourseOverride instance

        Raises:
            ValidationError: If override cannot be rejected
        """
        if override.approval_status != StudentCourseOverride.ApprovalStatus.PENDING:
            raise ValidationError("Can only reject pending overrides")

        if not reason:
            raise ValidationError("Rejection reason is required")

        # Update override
        override.approval_status = StudentCourseOverride.ApprovalStatus.REJECTED
        override.approved_by = user
        override.approval_date = timezone.now()
        override.rejection_reason = reason

        override.save(
            update_fields=[
                "approval_status",
                "approved_by",
                "approval_date",
                "rejection_reason",
            ]
        )

        # Create audit logs
        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get_for_model(override)

        SystemAuditLog.objects.create(
            performed_by=user,
            action_type=SystemAuditLog.ActionType.ACADEMIC_POLICY_OVERRIDE,
            content_type=content_type,
            object_id=override.id,  # type: ignore[attr-defined]
            target_app="academic",
            target_model="StudentCourseOverride",
            override_reason=f"Course override rejected: {reason}",
            original_restriction="Course requirement completion",
            override_details={
                "student_id": getattr(override, "student_id", getattr(override.student, "pk", None)),
                "original_course": override.original_course.code,
                "substitute_course": override.substitute_course.code,
                "reason": reason,
            },
        )

        StudentActivityLog.objects.create(
            student_number=override.student.student_id
            if hasattr(override.student, "student_id")
            else str(override.student.id),
            student_name=str(override.student),
            activity_type=StudentActivityLog.ActivityType.MANAGEMENT_OVERRIDE,
            description=(
                f"Course override rejected: {override.original_course.code} → {override.substitute_course.code}"
            ),
            class_code=override.substitute_course.code if override.substitute_course else "",
        )

        # Trigger student notification for mobile app integration
        cls._notify_student_of_status_change(
            student=override.student,
            notification_type="COURSE_OVERRIDE_REJECTED",
            data={
                "original_course": override.original_course.code,
                "substitute_course": override.substitute_course.code,
                "rejection_date": override.approval_date.isoformat() if override.approval_date else None,
                "reason": reason or "",
            },
        )

        return override

    @classmethod
    def get_student_overrides(cls, student: Any, approved_only: bool = False) -> QuerySet[StudentCourseOverride]:
        """Get all course overrides for a student.

        Args:
            student: StudentProfile instance
            approved_only: Whether to return only approved overrides

        Returns:
            QuerySet of StudentCourseOverride instances
        """
        overrides = (
            StudentCourseOverride.objects.filter(student=student)
            .select_related(
                "original_course",
                "substitute_course",
                "effective_term",
                "expiration_term",
                "requested_by",
                "approved_by",
            )
            .order_by("-request_date")
        )

        if approved_only:
            overrides = overrides.filter(approval_status=StudentCourseOverride.ApprovalStatus.APPROVED)

        return overrides

    @classmethod
    def check_override_validity(cls, override: StudentCourseOverride, term: Any = None) -> bool:
        """Check if an override is valid for a given term.

        Args:
            override: StudentCourseOverride instance
            term: Optional term to check (defaults to current)

        Returns:
            True if override is valid
        """
        if override.approval_status != StudentCourseOverride.ApprovalStatus.APPROVED:
            return False

        # Get current term if not provided
        if term is None:
            from apps.curriculum.models import Term

            term = Term.get_current_term()
            if not term:
                return False

        # Check if term is within validity period
        if override.effective_term and term.start_date < override.effective_term.start_date:
            return False

        if override.expiration_term and term.start_date >= override.expiration_term.start_date:
            return False

        return True

    @classmethod
    def _notify_student_of_status_change(cls, student: Any, notification_type: str, data: dict[str, Any]) -> None:
        """Send notification to student about status changes.

        This method provides a centralized way to notify students about
        academic status changes through the mobile app integration.

        Args:
            student: StudentProfile instance
            notification_type: Type of notification (COURSE_OVERRIDE_APPROVED, etc.)
            data: Notification payload data
        """
        # Create a student activity log entry that can be consumed by notification service
        StudentActivityLog.objects.create(
            student_number=student.student_id if hasattr(student, "student_id") else str(student.id),
            student_name=str(student),
            activity_type=StudentActivityLog.ActivityType.PROFILE_UPDATE,
            description=f"Mobile app notification: {notification_type}",
            activity_details=data if isinstance(data, dict) else {"data": str(data)},  # Store notification data
            performed_by_id=1,  # System user
        )

        # In a full implementation, this would integrate with:
        # - Push notification service (Firebase/APNs)
        # - WebSocket connections for real-time updates
        # - Email notification service as fallback
        # For now, we store the notification data for later processing
