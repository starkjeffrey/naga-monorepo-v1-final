"""Canonical requirement fulfillment tracking models.

This module provides models for tracking how students fulfill specific
canonical requirements through various means (courses, transfers, exceptions).
"""

from __future__ import annotations

from typing import Any, ClassVar

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import AuditModel


class StudentDegreeProgress(AuditModel):
    """Tracks individual student progress through degree requirements.

    This model records how students fulfill specific canonical requirements
    through various means (courses, transfers, exceptions). It provides both
    detailed fulfillment tracking and overall degree progress calculations.

    Key features:
    - Links student to specific canonical requirement fulfillment
    - Records fulfillment method (course, transfer, exception, waiver)
    - Tracks when and how each requirement was satisfied
    - Supports multiple fulfillment sources
    - Integrates with degree audit system
    - Calculates comprehensive progress summaries

    Business rules:
    - Each student-requirement pair should have at most one active fulfillment
    - Fulfillment can be through course completion, transfer credit, or exception
    - Credits earned may differ from canonical credits (e.g., transfer conversions)
    """

    class FulfillmentMethod(models.TextChoices):
        """How the requirement was fulfilled."""

        COURSE_COMPLETION = "COURSE", _("Course Completion")
        TRANSFER_CREDIT = "TRANSFER", _("Transfer Credit")
        EXCEPTION_SUBSTITUTION = "SUBSTITUTION", _("Course Substitution")
        WAIVER = "WAIVER", _("Requirement Waived")
        EXAM_CREDIT = "EXAM", _("Exam Credit")

    student = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.CASCADE,
        related_name="requirement_fulfillments",
        verbose_name=_("Student"),
    )

    canonical_requirement = models.ForeignKey(
        "academic.CanonicalRequirement",
        on_delete=models.PROTECT,
        related_name="student_fulfillments",
        verbose_name=_("Canonical Requirement"),
        help_text=_("The specific requirement being fulfilled"),
    )

    # Fulfillment details
    fulfillment_method = models.CharField(
        _("Fulfillment Method"),
        max_length=20,
        choices=FulfillmentMethod.choices,
        help_text=_("How this requirement was fulfilled"),
    )

    fulfillment_date = models.DateField(
        _("Fulfillment Date"),
        help_text=_("Date when requirement was fulfilled"),
    )

    # Links to fulfillment sources (only one should be set based on method)
    fulfilling_enrollment = models.ForeignKey(
        "enrollment.ClassHeaderEnrollment",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="requirement_fulfillments",
        verbose_name=_("Fulfilling Enrollment"),
        help_text=_("Class enrollment that fulfilled this requirement"),
    )

    fulfilling_transfer = models.ForeignKey(
        "academic.TransferCredit",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="requirement_fulfillments",
        verbose_name=_("Fulfilling Transfer Credit"),
        help_text=_("Transfer credit that fulfilled this requirement"),
    )

    fulfilling_exception = models.ForeignKey(
        "academic.StudentRequirementException",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="requirement_fulfillments",
        verbose_name=_("Fulfilling Exception"),
        help_text=_("Exception that allowed fulfillment of this requirement"),
    )

    # Credit tracking
    credits_earned = models.DecimalField(
        _("Credits Earned"),
        max_digits=4,
        decimal_places=2,
        help_text=_("Actual credits earned toward this requirement"),
    )

    grade = models.CharField(
        _("Grade"),
        max_length=10,
        blank=True,
        help_text=_("Grade earned (if applicable)"),
    )

    # Administrative
    is_active = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this fulfillment is currently valid"),
    )

    notes = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Administrative notes about this fulfillment"),
    )

    # Additional fields for consolidation compatibility
    completion_status = models.CharField(
        _("Completion Status"),
        max_length=20,
        choices=[
            ("IN_PROGRESS", _("In Progress")),
            ("COMPLETED", _("Completed")),
            ("ON_HOLD", _("On Hold")),
            ("WITHDRAWN", _("Withdrawn")),
        ],
        default="COMPLETED",  # Individual fulfillments are completed by definition
        help_text=_("Status of this individual requirement fulfillment"),
    )

    # Progress tracking metadata
    last_updated = models.DateTimeField(
        _("Last Updated"),
        auto_now=True,
        help_text=_("When this fulfillment was last modified"),
    )

    class Meta:
        app_label = "academic"
        verbose_name = _("Student Degree Progress")
        verbose_name_plural = _("Student Degree Progress")
        ordering = ["student", "canonical_requirement__sequence_number"]
        unique_together = [
            ["student", "canonical_requirement"],  # One fulfillment per requirement
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "is_active"]),
            models.Index(fields=["canonical_requirement", "is_active"]),
            models.Index(fields=["fulfillment_method"]),
            models.Index(fields=["fulfillment_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.student} - {self.canonical_requirement}: {self.get_fulfillment_method_display()}"

    def clean(self) -> None:
        """Validate fulfillment data."""
        super().clean()

        # Ensure only one fulfillment source is set based on method
        source_count = sum(
            [
                bool(self.fulfilling_enrollment_id),
                bool(self.fulfilling_transfer_id),
                bool(self.fulfilling_exception_id),
            ],
        )

        if self.fulfillment_method == self.FulfillmentMethod.COURSE_COMPLETION:
            if not self.fulfilling_enrollment_id:
                raise ValidationError({"fulfilling_enrollment": _("Course completion requires an enrollment.")})
            if source_count > 1:
                raise ValidationError(_("Only enrollment should be set for course completion."))

        elif self.fulfillment_method == self.FulfillmentMethod.TRANSFER_CREDIT:
            if not self.fulfilling_transfer_id:
                raise ValidationError({"fulfilling_transfer": _("Transfer credit method requires a transfer credit.")})
            if source_count > 1:
                raise ValidationError(_("Only transfer credit should be set for transfer method."))

        elif self.fulfillment_method in [
            self.FulfillmentMethod.EXCEPTION_SUBSTITUTION,
            self.FulfillmentMethod.WAIVER,
        ]:
            if not self.fulfilling_exception_id:
                raise ValidationError(
                    {"fulfilling_exception": _("Exception/waiver method requires an exception record.")},
                )
            if source_count > 1:
                raise ValidationError(_("Only exception should be set for exception/waiver method."))

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Auto-populate fields based on fulfillment source."""
        # Auto-set fulfillment date if not provided
        if not self.fulfillment_date:
            if self.fulfilling_enrollment_id:
                # Use term end date or current date
                enrollment = self.fulfilling_enrollment
                if enrollment:
                    self.fulfillment_date = enrollment.class_header.term.end_date or timezone.now().date()
            elif self.fulfilling_transfer_id:
                # Use review date or creation date
                transfer = self.fulfilling_transfer
                if transfer:
                    self.fulfillment_date = transfer.review_date or transfer.created_at.date()
            elif self.fulfilling_exception_id:
                # Use approval date or creation date
                exception = self.fulfilling_exception
                if exception:
                    self.fulfillment_date = exception.approval_date or exception.created_at.date()
            else:
                self.fulfillment_date = timezone.now().date()

        super().save(*args, **kwargs)

    @classmethod
    def get_student_progress(cls, student: Any, major: Any) -> dict[str, Any]:
        """Calculate comprehensive progress summary from individual fulfillments.

        This replaces the old StudentDegreeProgress functionality by aggregating
        individual requirement fulfillments.
        """
        from .canonical import CanonicalRequirement

        # Get all active fulfillments for this student-major combination
        fulfillments = cls.objects.filter(
            student=student, canonical_requirement__major=major, is_active=True
        ).select_related("canonical_requirement")

        # Get total requirements for this major
        total_requirements = CanonicalRequirement.objects.filter(major=major, is_active=True).count()

        # Calculate summary statistics
        completed_count = fulfillments.count()
        credits_completed = sum(f.credits_earned for f in fulfillments)
        completion_percentage = (completed_count / total_requirements * 100) if total_requirements else 0

        # Calculate total credits required (sum of all canonical requirement credits)
        total_credits_required = sum(
            req.canonical_credits
            for req in CanonicalRequirement.objects.filter(major=major, is_active=True).select_related(
                "required_course"
            )
        )

        # Determine overall completion status
        if completion_percentage == 100:
            overall_status = "COMPLETED"
        elif completion_percentage > 0:
            overall_status = "IN_PROGRESS"
        else:
            overall_status = "IN_PROGRESS"

        return {
            "student": student,
            "major": major,
            "total_requirements": total_requirements,
            "completed_requirements": completed_count,
            "total_credits_required": float(total_credits_required),
            "credits_completed": float(credits_completed),
            "completion_percentage": round(completion_percentage, 1),
            "remaining_requirements": max(0, total_requirements - completed_count),
            "remaining_credits": max(0, float(total_credits_required) - float(credits_completed)),
            "is_graduation_eligible": completion_percentage == 100,
            "completion_status": overall_status,
            "fulfillments": list(fulfillments),
        }

    @classmethod
    def get_unfulfilled_requirements(cls, student, major):
        """Get list of requirements not yet fulfilled by the student."""
        from .canonical import CanonicalRequirement

        fulfilled_requirement_ids = cls.objects.filter(
            student=student, canonical_requirement__major=major, is_active=True
        ).values_list("canonical_requirement_id", flat=True)

        return (
            CanonicalRequirement.objects.filter(major=major, is_active=True)
            .exclude(id__in=fulfilled_requirement_ids)
            .order_by("sequence_number")
        )

    @property
    def is_passing_fulfillment(self):
        """Check if this fulfillment represents a passing completion."""
        if self.fulfillment_method == self.FulfillmentMethod.WAIVER:
            return True
        elif self.grade:
            # Basic passing grade logic - can be enhanced later
            grade_upper = self.grade.upper().replace("+", "").replace("-", "")
            return grade_upper in ["A", "B", "C", "D"]
        else:
            # If no grade recorded, assume it's passing (for transfers, exceptions)
            return True
