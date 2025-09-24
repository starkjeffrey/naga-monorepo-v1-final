"""Transfer credit and course equivalency models.

This module contains models for managing external credit recognition,
course equivalencies, and transfer credit approval workflows.

Key features:
- Transfer credit approval workflow
- Course equivalency mapping with term-based versioning
- External institution tracking
- Bidirectional and unidirectional equivalencies
"""

from decimal import Decimal
from typing import ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import AuditModel


class CourseEquivalency(AuditModel):
    """Defines course equivalencies with term-based versioning.

    Maps equivalent courses for curriculum changes, course renumbering, and
    universal substitutions. Supports term-based versioning to handle changes
    in course equivalencies over time.

    Key features:
    - Original course to equivalent course mapping
    - Term-based versioning for equivalency changes
    - Bidirectional or unidirectional equivalencies
    - Clean dependency on curriculum app
    """

    original_course = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.CASCADE,
        related_name="equivalency_mappings",
        verbose_name=_("Original Course"),
        help_text=_("The course that needs an equivalent"),
    )
    equivalent_course = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.CASCADE,
        related_name="reverse_equivalency_mappings",
        verbose_name=_("Equivalent Course"),
        help_text=_("The course that can be used as equivalent"),
    )
    bidirectional = models.BooleanField(
        _("Bidirectional"),
        default=False,
        help_text=_("Whether the equivalency works in both directions"),
    )

    # Term-based versioning
    effective_term = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.PROTECT,
        related_name="effective_equivalencies",
        verbose_name=_("Effective Term"),
        help_text=_("Term when this equivalency becomes effective"),
    )
    end_term = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.PROTECT,
        related_name="ended_equivalencies",
        verbose_name=_("End Term"),
        null=True,
        blank=True,
        help_text=_("Term when this equivalency is no longer effective"),
    )

    # Administrative fields
    reason = models.TextField(
        _("Reason"),
        help_text=_("Reason for establishing this equivalency"),
    )
    is_active = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this equivalency is currently active"),
    )
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_equivalencies",
        verbose_name=_("Approved By"),
        help_text=_("User who approved this equivalency"),
    )
    approval_date = models.DateField(
        _("Approval Date"),
        help_text=_("Date when this equivalency was approved"),
    )

    class Meta:
        verbose_name = _("Course Equivalency")
        verbose_name_plural = _("Course Equivalencies")
        unique_together = [["original_course", "equivalent_course", "effective_term"]]
        ordering = ["original_course", "equivalent_course"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["original_course", "effective_term"]),
            models.Index(fields=["equivalent_course", "effective_term"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        arrow = "↔" if self.bidirectional else "→"
        return f"{self.original_course.code} {arrow} {self.equivalent_course.code}"

    def clean(self) -> None:
        """Validate equivalency data."""
        super().clean()

        # Cannot have equivalency between same course
        if self.original_course_id == self.equivalent_course_id:
            raise ValidationError(_("A course cannot be equivalent to itself."))

        # Validate term ordering
        if (
            self.end_term
            and self.effective_term_id
            and self.end_term_id
            and self.effective_term.start_date >= self.end_term.start_date
        ):
            raise ValidationError(
                {"end_term": _("End term must be after effective term.")},
            )


class TransferCredit(AuditModel):
    """External credit recognition and approval workflow.

    Represents credits transferred from external institutions with comprehensive
    approval tracking. Supports both course-specific transfers and general
    credit awards.

    Key features:
    - Links to students from people app (clean dependency)
    - Optional course mapping for credit transfers
    - Multi-stage approval workflow
    - External institution and course details
    - Credits and grade tracking
    - Administrative notes and documentation
    """

    class CreditType(models.TextChoices):
        """Types of transfer credits."""

        COURSE = "COURSE", _("Course Transfer")
        EXAM = "EXAM", _("Examination Credit")
        LIFE = "LIFE", _("Life Experience")
        MILITARY = "MILITARY", _("Military Credit")

    class ApprovalStatus(models.TextChoices):
        """Transfer credit approval statuses."""

        PENDING = "PENDING", _("Pending Review")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")
        MORE_INFO = "INFO", _("More Information Required")

    # Student link
    student = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.CASCADE,
        related_name="transfer_credits",
        verbose_name=_("Student"),
    )

    # External course information
    external_institution = models.CharField(
        _("External Institution"),
        max_length=200,
        help_text=_("Name of the institution where credit was earned"),
    )
    external_course_code = models.CharField(
        _("External Course Code"),
        max_length=20,
        help_text=_("Course code at the external institution"),
    )
    external_course_name = models.CharField(
        _("External Course Name"),
        max_length=200,
        help_text=_("Course name at the external institution"),
    )
    external_credits = models.DecimalField(
        _("External Credits"),
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.0")),
            MaxValueValidator(Decimal("12.0")),
        ],
        help_text=_("Number of credits earned at external institution"),
    )
    external_grade = models.CharField(
        _("External Grade"),
        max_length=10,
        blank=True,
        help_text=_("Grade received at external institution"),
    )

    # Internal mapping
    equivalent_course = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.PROTECT,
        related_name="transfer_equivalents",
        verbose_name=_("Equivalent Course"),
        null=True,
        blank=True,
        help_text=_("Internal course this transfer credit maps to"),
    )
    awarded_credits = models.DecimalField(
        _("Awarded Credits"),
        max_digits=5,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.0")),
            MaxValueValidator(Decimal("12.0")),
        ],
        help_text=_("Number of credits awarded for this transfer"),
    )

    # Metadata
    credit_type = models.CharField(
        _("Credit Type"),
        max_length=10,
        choices=CreditType.choices,
        default=CreditType.COURSE,
    )
    term_taken = models.CharField(
        _("Term Taken"),
        max_length=50,
        blank=True,
        help_text=_("Term/semester when course was taken externally"),
    )
    year_taken = models.PositiveSmallIntegerField(
        _("Year Taken"),
        null=True,
        blank=True,
        help_text=_("Year when course was taken externally"),
    )

    # Approval workflow
    approval_status = models.CharField(
        _("Approval Status"),
        max_length=10,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reviewed_transfer_credits",
        verbose_name=_("Reviewed By"),
        null=True,
        blank=True,
    )
    review_date = models.DateTimeField(
        _("Review Date"),
        null=True,
        blank=True,
    )
    review_notes = models.TextField(
        _("Review Notes"),
        blank=True,
        help_text=_("Notes from the review process"),
    )

    # Documentation
    documentation = models.TextField(
        _("Documentation"),
        blank=True,
        help_text=_("Details about supporting documentation provided"),
    )

    class Meta:
        verbose_name = _("Transfer Credit")
        verbose_name_plural = _("Transfer Credits")
        unique_together = [
            ["student", "external_institution", "external_course_code"],
        ]
        ordering = ["student", "external_institution", "external_course_code"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "approval_status"]),
            models.Index(fields=["equivalent_course"]),
            models.Index(fields=["approval_status", "review_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.student}: {self.external_course_code} from {self.external_institution}"

    @property
    def is_approved(self) -> bool:
        """Check if transfer credit is approved."""
        return self.approval_status == self.ApprovalStatus.APPROVED

    def clean(self) -> None:
        """Validate transfer credit data."""
        super().clean()

        # Validate awarded credits don't exceed external credits
        if self.awarded_credits and self.external_credits and self.awarded_credits > self.external_credits:
            raise ValidationError(
                {
                    "awarded_credits": _(
                        "Awarded credits cannot exceed external credits earned.",
                    ),
                },
            )

        # Require review notes for rejected status
        if self.approval_status == self.ApprovalStatus.REJECTED and not self.review_notes:
            raise ValidationError(
                {
                    "review_notes": _(
                        "Review notes are required when rejecting transfer credits.",
                    ),
                },
            )
