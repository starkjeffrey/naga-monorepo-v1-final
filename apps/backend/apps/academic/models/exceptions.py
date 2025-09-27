"""Student-specific exceptions and overrides to canonical requirements.

This module handles all cases where a student's degree plan differs from
the canonical requirements: transfers, study abroad, course substitutions,
administrative overrides, etc.

Key features:
- Exception-based overrides to canonical requirements
- Course substitution management
- Comprehensive approval workflows
- Term-based validity periods
"""

from decimal import Decimal
from typing import ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import AuditModel


class StudentRequirementException(AuditModel):
    """Student-specific exceptions to canonical requirements.

    This model handles all cases where a student's degree plan differs from
    the canonical requirements: transfer credits, study abroad courses,
    course substitutions, administrative overrides, etc.

    Key features:
    - Links to specific canonical requirement being modified
    - Tracks original canonical course and substitute fulfillment
    - Comprehensive approval workflow
    - Credits calculated from actual courses (Course.credits)
    - Term-based validity periods
    - Detailed reason tracking and documentation

    Operational considerations:
    - Academic advisors can see exactly how each student deviates from canonical plan
    - Transfer credit evaluation creates exceptions automatically
    - Study abroad courses require exception approval
    - Course substitutions require detailed justification
    - All exceptions require administrative approval
    """

    class ExceptionType(models.TextChoices):
        """Types of requirement exceptions."""

        TRANSFER_CREDIT = "TRANSFER", _("Transfer Credit")
        STUDY_ABROAD = "ABROAD", _("Study Abroad")
        COURSE_SUBSTITUTION = "SUBSTITUTION", _("Course Substitution")
        ADMINISTRATIVE_OVERRIDE = "ADMIN", _("Administrative Override")
        EXAM_CREDIT = "EXAM", _("Exam Credit (AP, CLEP, etc.)")
        PORTFOLIO_CREDIT = "PORTFOLIO", _("Portfolio Credit")
        WAIVER = "WAIVER", _("Requirement Waiver")

    class ApprovalStatus(models.TextChoices):
        """Exception approval statuses."""

        PENDING = "PENDING", _("Pending Review")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")
        CONDITIONAL = "CONDITIONAL", _("Conditionally Approved")
        EXPIRED = "EXPIRED", _("Expired")

    student = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.CASCADE,
        related_name="requirement_exceptions",
        verbose_name=_("Student"),
    )
    canonical_requirement = models.ForeignKey(
        "academic.CanonicalRequirement",
        on_delete=models.CASCADE,
        related_name="student_exceptions",
        verbose_name=_("Canonical Requirement"),
        help_text=_("The canonical requirement being modified"),
    )

    # Exception details
    exception_type = models.CharField(
        _("Exception Type"),
        max_length=20,
        choices=ExceptionType.choices,
        help_text=_("Type of exception being requested"),
    )

    # Fulfillment method (exactly one of these should be set)
    fulfilling_course = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="fulfills_via_exception",
        verbose_name=_("Fulfilling Course"),
        help_text=_("Internal course that fulfills this requirement"),
    )
    fulfilling_transfer_credit = models.ForeignKey(
        "academic.TransferCredit",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="canonical_requirement_exceptions",
        verbose_name=_("Fulfilling Transfer Credit"),
        help_text=_("Transfer credit that fulfills this requirement"),
    )
    is_waived = models.BooleanField(
        _("Is Waived"),
        default=False,
        help_text=_("Whether this requirement is completely waived"),
    )

    # Justification and documentation
    reason = models.TextField(
        _("Reason for Exception"),
        help_text=_("Detailed justification for this exception"),
    )
    supporting_documentation = models.TextField(
        _("Supporting Documentation"),
        blank=True,
        help_text=_("Description of supporting documentation provided"),
    )

    # Validity period
    effective_term = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.PROTECT,
        related_name="exceptions_starting",
        verbose_name=_("Effective Term"),
        help_text=_("Term when this exception becomes effective"),
    )
    expiration_term = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.PROTECT,
        related_name="exceptions_expiring",
        null=True,
        blank=True,
        verbose_name=_("Expiration Term"),
        help_text=_("Term when this exception expires (optional)"),
    )

    # Approval workflow
    approval_status = models.CharField(
        _("Approval Status"),
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        db_index=True,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_requirement_exceptions",
        verbose_name=_("Requested By"),
        help_text=_("Person who submitted the exception request"),
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_requirement_exceptions",
        verbose_name=_("Approved By"),
    )
    approval_date = models.DateTimeField(
        _("Approval Date"),
        null=True,
        blank=True,
    )
    rejection_reason = models.TextField(
        _("Rejection Reason"),
        blank=True,
        help_text=_("Reason for rejection if status is rejected"),
    )

    # Administrative details
    notes = models.TextField(
        _("Administrative Notes"),
        blank=True,
        help_text=_("Internal notes about this exception"),
    )

    class Meta:
        app_label = "academic"
        verbose_name = _("Student Requirement Exception")
        verbose_name_plural = _("Student Requirement Exceptions")
        unique_together = [
            ["student", "canonical_requirement", "effective_term"],
        ]
        ordering = ["student", "canonical_requirement__sequence_number"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "approval_status"]),
            models.Index(fields=["canonical_requirement", "approval_status"]),
            models.Index(fields=["approval_status", "effective_term"]),
            models.Index(fields=["exception_type", "approval_status"]),
        ]
        permissions = [
            ("can_approve_requirement_exception", "Can approve requirement exceptions"),
            ("can_reject_requirement_exception", "Can reject requirement exceptions"),
        ]

    def __str__(self) -> str:
        canonical_req = self.canonical_requirement
        return f"{self.student} - {canonical_req.major.code} #{canonical_req.sequence_number} Exception"

    @property
    def exception_credits(self) -> Decimal:
        """Calculate credits awarded by this exception."""
        if self.is_waived:
            return self.canonical_requirement.canonical_credits
        if self.fulfilling_course:
            return Decimal(str(self.fulfilling_course.credits))
        if self.fulfilling_transfer_credit:
            return self.fulfilling_transfer_credit.awarded_credits
        return Decimal("0.00")

    @property
    def is_currently_valid(self) -> bool:
        """Check if exception is currently valid."""
        if self.approval_status != self.ApprovalStatus.APPROVED:
            return False

        # Check if expired based on expiration term
        # This would require current term tracking
        return self.expiration_term is None

    def clean(self) -> None:
        """Validate exception data."""
        super().clean()

        # Exactly one fulfillment method must be specified (or waiver)
        fulfillment_count = sum(
            [
                bool(self.fulfilling_course),
                bool(self.fulfilling_transfer_credit),
                self.is_waived,
            ],
        )

        if fulfillment_count == 0:
            raise ValidationError(
                _("Must specify fulfillment method: course, transfer credit, or waiver."),
            )
        if fulfillment_count > 1:
            raise ValidationError(
                _("Cannot specify multiple fulfillment methods for one exception."),
            )

        # Validate approval status requirements
        if self.approval_status == self.ApprovalStatus.REJECTED and not self.rejection_reason:
            raise ValidationError(
                {"rejection_reason": _("Rejection reason is required for rejected exceptions.")},
            )

        # Validate term ordering
        if (
            self.expiration_term
            and self.effective_term_id
            and self.expiration_term_id
            and self.effective_term.start_date >= self.expiration_term.start_date
        ):
            raise ValidationError(
                {"expiration_term": _("Expiration term must be after effective term.")},
            )


class StudentCourseOverride(AuditModel):
    """Student-specific course substitutions and academic petitions.

    Allows for individual student exceptions where they can use one course
    in place of another for degree requirements. Supports approval workflow
    and term-based validity.

    Key features:
    - Student-specific course substitution rules
    - Reason categorization for common override scenarios
    - Approval workflow with documentation
    - Term-based validity periods
    - Integration with academic advising process
    """

    class OverrideReason(models.TextChoices):
        """Reasons for course overrides."""

        DISCONTINUED = "DISCONTINUED", _("Course Discontinued")
        SCHEDULING = "SCHEDULING", _("Scheduling Conflict")
        TRANSFER = "TRANSFER", _("Transfer Equivalency")
        ACADEMIC = "ACADEMIC", _("Academic Exception")
        MEDICAL = "MEDICAL", _("Medical Accommodation")
        OTHER = "OTHER", _("Other Reason")

    class ApprovalStatus(models.TextChoices):
        """Override approval statuses."""

        PENDING = "PENDING", _("Pending Approval")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")
        EXPIRED = "EXPIRED", _("Expired")

    # Student and course information
    student = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.CASCADE,
        related_name="course_overrides",
        verbose_name=_("Student"),
    )
    original_course = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.PROTECT,
        related_name="overridden_by_students",
        verbose_name=_("Original Course"),
        help_text=_("The course that should be replaced"),
    )
    substitute_course = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.PROTECT,
        related_name="substitutes_for_students",
        verbose_name=_("Substitute Course"),
        help_text=_("The course to use as a substitute"),
    )

    # Override details
    reason = models.CharField(
        _("Override Reason"),
        max_length=15,
        choices=OverrideReason.choices,
        default=OverrideReason.OTHER,
    )
    detailed_reason = models.TextField(
        _("Detailed Reason"),
        help_text=_("Detailed explanation for this override request"),
    )

    # Term validity
    effective_term = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.PROTECT,
        related_name="effective_overrides",
        verbose_name=_("Effective Term"),
        help_text=_("Term when this override becomes effective"),
    )
    expiration_term = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.PROTECT,
        related_name="expiring_overrides",
        verbose_name=_("Expiration Term"),
        null=True,
        blank=True,
        help_text=_("Term when this override expires"),
    )

    # Approval workflow
    approval_status = models.CharField(
        _("Approval Status"),
        max_length=10,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="requested_overrides",
        verbose_name=_("Requested By"),
        help_text=_("User who requested this override"),
    )
    request_date = models.DateTimeField(
        _("Request Date"),
        auto_now_add=True,
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_course_overrides",
        verbose_name=_("Approved By"),
        null=True,
        blank=True,
    )
    approval_date = models.DateTimeField(
        _("Approval Date"),
        null=True,
        blank=True,
    )
    rejection_reason = models.TextField(
        _("Rejection Reason"),
        blank=True,
        help_text=_("Reason for rejection if applicable"),
    )

    # Documentation
    supporting_documentation = models.TextField(
        _("Supporting Documentation"),
        blank=True,
        help_text=_("Details of any supporting documentation"),
    )
    academic_advisor_notes = models.TextField(
        _("Academic Advisor Notes"),
        blank=True,
        help_text=_("Notes from academic advisor"),
    )

    class Meta:
        verbose_name = _("Student Course Override")
        verbose_name_plural = _("Student Course Overrides")
        unique_together = [
            ["student", "original_course", "substitute_course", "effective_term"],
        ]
        ordering = ["student", "-request_date"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "approval_status"]),
            models.Index(fields=["original_course", "substitute_course"]),
            models.Index(fields=["approval_status", "effective_term"]),
        ]

    def __str__(self) -> str:
        return f"{self.student}: {self.original_course.code} → {self.substitute_course.code}"

    @property
    def is_currently_valid(self) -> bool:
        """Check if override is currently valid."""
        if self.approval_status != self.ApprovalStatus.APPROVED:
            return False

        # Use cached current term to avoid database hits
        from apps.curriculum.models import Term

        current_term = getattr(self, "_current_term", None)
        if current_term is None:
            # Only hit database once per instance
            current_term = Term.get_current_term()
            self._current_term = current_term

        # Check if expired based on expiration term
        if self.expiration_term and current_term and current_term.start_date > self.expiration_term.start_date:
            return False

        return True

    def clean(self) -> None:
        """Validate course override data."""
        super().clean()

        # Cannot substitute course for itself
        if self.original_course == self.substitute_course:
            raise ValidationError(_("A course cannot be substituted for itself."))

        if self.approval_status == self.ApprovalStatus.REJECTED and not self.rejection_reason:
            raise ValidationError(
                {
                    "rejection_reason": _(
                        "Rejection reason is required for rejected overrides.",
                    ),
                },
            )

        # Validate term ordering
        if (
            self.expiration_term
            and self.effective_term_id
            and self.expiration_term_id
            and self.effective_term.start_date >= self.expiration_term.start_date
        ):
            raise ValidationError(
                {"expiration_term": _("Expiration term must be after effective term.")},
            )
