"""Transfer credit and course equivalency services.

This module provides business logic for managing transfer credits,
course equivalencies, and their approval workflows.
"""

from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.academic.models import CourseEquivalency, TransferCredit
from apps.common.models import StudentActivityLog, SystemAuditLog

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

    from users.models import User
else:
    User = get_user_model()


class TransferCreditService:
    """Service for managing transfer credit business logic."""

    @classmethod
    @transaction.atomic
    def approve_transfer(cls, transfer_credit: TransferCredit, user: "User", notes: str = "") -> TransferCredit:
        """Approve a transfer credit with full transaction control.

        Args:
            transfer_credit: TransferCredit instance to approve
            user: User performing the approval
            notes: Optional approval notes

        Returns:
            Updated TransferCredit instance

        Raises:
            ValidationError: If transfer credit cannot be approved
        """
        if transfer_credit.approval_status != TransferCredit.ApprovalStatus.PENDING:
            raise ValidationError("Can only approve pending transfer credits")

        # Update transfer credit
        transfer_credit.approval_status = TransferCredit.ApprovalStatus.APPROVED
        transfer_credit.reviewed_by = user
        transfer_credit.review_date = timezone.now()
        if notes:
            transfer_credit.review_notes = f"{transfer_credit.review_notes}\n\nApproval: {notes}".strip()

        transfer_credit.save(
            update_fields=[
                "approval_status",
                "reviewed_by",
                "review_date",
                "review_notes",
            ]
        )

        # Create audit logs
        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get_for_model(transfer_credit)

        SystemAuditLog.objects.create(
            action_type=SystemAuditLog.ActionType.ACADEMIC_POLICY_OVERRIDE,
            performed_by=user,
            content_type=content_type,
            object_id=transfer_credit.id,  # type: ignore[attr-defined]
            target_app="academic",
            target_model="TransferCredit",
            override_reason=f"Transfer credit approved: {transfer_credit.external_course_code}",
            original_restriction="External course credit transfer restrictions",
            override_details={
                "student_id": transfer_credit.student_id,  # type: ignore[attr-defined]
                "external_course": transfer_credit.external_course_code,
                "awarded_credits": str(transfer_credit.awarded_credits),
            },
        )

        StudentActivityLog.objects.create(
            student_number=transfer_credit.student.student_id
            if hasattr(transfer_credit.student, "student_id")
            else str(transfer_credit.student.id),
            student_name=str(transfer_credit.student),
            activity_type=StudentActivityLog.ActivityType.GRADE_ASSIGNMENT,
            description=f"Transfer credit approved: {transfer_credit.external_course_code}",
            activity_details={
                "transfer_credit_id": transfer_credit.id,  # type: ignore[attr-defined]
                "external_course": transfer_credit.external_course_code,
                "performed_by": user.get_full_name(),
            },
            performed_by=user,
        )

        # Trigger student notification for mobile app integration
        cls._notify_student_of_transfer_status(
            student=transfer_credit.student,
            notification_type="TRANSFER_CREDIT_APPROVED",
            data={
                "course_code": transfer_credit.external_course_code,
                "external_institution": transfer_credit.external_institution,
                "awarded_credits": float(transfer_credit.awarded_credits),
                "approval_date": transfer_credit.review_date.isoformat() if transfer_credit.review_date else None,
                "notes": notes or "",
            },
        )

        return transfer_credit

    @classmethod
    @transaction.atomic
    def reject_transfer(cls, transfer_credit: TransferCredit, user: "User", reason: str) -> TransferCredit:
        """Reject a transfer credit with full transaction control.

        Args:
            transfer_credit: TransferCredit instance to reject
            user: User performing the rejection
            reason: Rejection reason (required)

        Returns:
            Updated TransferCredit instance

        Raises:
            ValidationError: If transfer credit cannot be rejected
        """
        if transfer_credit.approval_status != TransferCredit.ApprovalStatus.PENDING:
            raise ValidationError("Can only reject pending transfer credits")

        if not reason:
            raise ValidationError("Rejection reason is required")

        # Update transfer credit
        transfer_credit.approval_status = TransferCredit.ApprovalStatus.REJECTED
        transfer_credit.reviewed_by = user
        transfer_credit.review_date = timezone.now()
        transfer_credit.review_notes = reason

        transfer_credit.save(
            update_fields=[
                "approval_status",
                "reviewed_by",
                "review_date",
                "review_notes",
            ]
        )

        # Create audit logs
        from django.contrib.contenttypes.models import ContentType

        content_type = ContentType.objects.get_for_model(transfer_credit)

        SystemAuditLog.objects.create(
            action_type=SystemAuditLog.ActionType.ACADEMIC_POLICY_OVERRIDE,
            performed_by=user,
            content_type=content_type,
            object_id=transfer_credit.id,  # type: ignore[attr-defined]
            target_app="academic",
            target_model="TransferCredit",
            override_reason=f"Transfer credit rejected: {reason}",
            original_restriction="External course credit transfer restrictions",
            override_details={
                "student_id": transfer_credit.student_id,  # type: ignore[attr-defined]
                "external_course": transfer_credit.external_course_code,
                "reason": reason,
            },
        )

        StudentActivityLog.objects.create(
            student_number=transfer_credit.student.student_id
            if hasattr(transfer_credit.student, "student_id")
            else str(transfer_credit.student.id),
            student_name=str(transfer_credit.student),
            activity_type=StudentActivityLog.ActivityType.GRADE_CHANGE,
            description=f"Transfer credit rejected: {transfer_credit.external_course_code}",
            activity_details={
                "transfer_credit_id": transfer_credit.id,  # type: ignore[attr-defined]
                "external_course": transfer_credit.external_course_code,
                "rejection_reason": reason,
                "performed_by": user.get_full_name(),
            },
            performed_by=user,
        )

        # Trigger student notification for mobile app integration
        cls._notify_student_of_transfer_status(
            student=transfer_credit.student,
            notification_type="TRANSFER_CREDIT_REJECTED",
            data={
                "course_code": transfer_credit.external_course_code,
                "external_institution": transfer_credit.external_institution,
                "rejection_date": transfer_credit.review_date.isoformat() if transfer_credit.review_date else None,
                "reason": reason or "",
            },
        )

        return transfer_credit

    @classmethod
    def get_pending_transfers(cls, reviewer: "AbstractUser | None" = None) -> QuerySet[TransferCredit]:
        """Get pending transfer credits for review.

        Args:
            reviewer: Optional user to filter by assigned reviewer

        Returns:
            QuerySet of pending transfer credits
        """
        transfers = (
            TransferCredit.objects.filter(approval_status=TransferCredit.ApprovalStatus.PENDING)
            .select_related(
                "student",
                "student__person",
                "equivalent_course",
            )
            .order_by("-created_at")
        )

        return transfers

    @classmethod
    def get_student_transfers(cls, student, approved_only: bool = False) -> QuerySet[TransferCredit]:
        """Get all transfer credits for a student.

        Args:
            student: StudentProfile instance
            approved_only: Whether to return only approved transfers

        Returns:
            QuerySet of transfer credits
        """
        transfers = (
            TransferCredit.objects.filter(student=student)
            .select_related(
                "equivalent_course",
                "reviewed_by",
            )
            .order_by("-created_at")
        )

        if approved_only:
            transfers = transfers.filter(approval_status=TransferCredit.ApprovalStatus.APPROVED)

        return transfers

    @classmethod
    def _notify_student_of_transfer_status(cls, student, notification_type: str, data: dict) -> None:
        """Send notification to student about transfer credit status changes.

        This method provides a centralized way to notify students about
        transfer credit status changes through the mobile app integration.

        Args:
            student: StudentProfile instance
            notification_type: Type of notification (TRANSFER_CREDIT_APPROVED, etc.)
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


class CourseEquivalencyService:
    """Service for managing course equivalencies."""

    @classmethod
    def find_equivalencies(cls, course, term=None, bidirectional: bool = True) -> QuerySet[CourseEquivalency]:
        """Find all equivalencies for a course.

        Args:
            course: Course instance
            term: Optional term to check effective equivalencies
            bidirectional: Whether to include reverse equivalencies

        Returns:
            QuerySet of CourseEquivalency instances
        """
        # Base query for direct equivalencies
        query = Q(original_course=course, is_active=True)

        # Include reverse equivalencies if bidirectional
        if bidirectional:
            query |= Q(equivalent_course=course, bidirectional=True, is_active=True)

        equivalencies = CourseEquivalency.objects.filter(query).select_related(
            "original_course",
            "equivalent_course",
            "effective_term",
            "end_term",
            "approved_by",
        )

        # Filter by term if provided
        if term:
            equivalencies = equivalencies.filter(effective_term__start_date__lte=term.start_date).filter(
                Q(end_term__isnull=True) | Q(end_term__start_date__gt=term.start_date),
            )

        return equivalencies

    @classmethod
    def check_circular_equivalency(cls, original_course, equivalent_course, visited: set | None = None) -> bool:
        """Check if creating an equivalency would create a circular dependency.

        Args:
            original_course: Original course
            equivalent_course: Proposed equivalent course
            visited: Set of visited course IDs (for recursion)

        Returns:
            True if circular dependency would be created
        """
        if visited is None:
            visited = set()

        if original_course.id in visited:
            return True

        visited.add(original_course.id)

        # Check all equivalencies from the equivalent course
        existing_equivalencies = CourseEquivalency.objects.filter(original_course=equivalent_course, is_active=True)

        for equiv in existing_equivalencies:
            if cls.check_circular_equivalency(equiv.equivalent_course, original_course, visited.copy()):
                return True

        return False

    @classmethod
    @transaction.atomic
    def create_equivalency(cls, original_course, equivalent_course, user, **kwargs):
        """Create a new course equivalency with validation.

        Args:
            original_course: Original course
            equivalent_course: Equivalent course
            user: User creating the equivalency
            **kwargs: Additional fields for CourseEquivalency

        Returns:
            Created CourseEquivalency instance

        Raises:
            ValidationError: If equivalency is invalid
        """
        # Check for circular dependency
        if cls.check_circular_equivalency(original_course, equivalent_course):
            raise ValidationError("This equivalency would create a circular dependency")

        # Create equivalency
        equivalency = CourseEquivalency.objects.create(
            original_course=original_course,
            equivalent_course=equivalent_course,
            approved_by=user,
            approval_date=timezone.now().date(),
            **kwargs,
        )

        # Create audit log
        SystemAuditLog.objects.create(
            action_type=SystemAuditLog.ActionType.ACADEMIC_POLICY_OVERRIDE,
            performed_by=user,
            content_object=equivalency,
            override_reason=f"Course equivalency created: {original_course.code} ≡ {equivalent_course.code}",
            outcome_description="Course equivalency created successfully",
            activity_details={
                "original_course": original_course.code,
                "equivalent_course": equivalent_course.code,
                "bidirectional": equivalency.bidirectional,
            },
        )

        return equivalency
