"""Grading app models following clean architecture principles.

This module contains models for comprehensive grade management including:
- Multiple grading scales for different programs (Language Standard, IEAP, Academic)
- Hierarchical grade storage (ClassPart → ClassSession → ClassHeader)
- GPA calculations limited to current major requirements
- Grade change auditing and notification management
- Teacher grade entry workflows

Key architectural decisions:
- Clean dependencies: grading → enrollment + scheduling + curriculum + people
- Hierarchical grade calculation respecting session and part weights
- Program-specific grading scales with configurable breakpoints
- Comprehensive audit trails for all grade changes
- Support for both numeric and letter grade entry
"""

from __future__ import annotations

from typing import ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import UserAuditModel


class GradingScale(UserAuditModel):
    """Grading scales for different academic programs.

    Defines the grading systems used across different divisions:
    - LANGUAGE_STANDARD: A, B, C, D, F with F<50% (EHSS, GESL, WKEND)
    - LANGUAGE_IEAP: A, B, C, D, F with F<60% and different breakpoints
    - ACADEMIC: A+, A, A-, B+, B, B-, C+, C, C-, D+, D, D-, F with F<60%
    """

    class ScaleType(models.TextChoices):
        """Types of grading scales used in the institution."""

        LANGUAGE_STANDARD = "LANGUAGE_STANDARD", _("Language Standard (A-F, F<50%)")
        LANGUAGE_IEAP = "LANGUAGE_IEAP", _("Language IEAP (A-F, F<60%)")
        ACADEMIC = "ACADEMIC", _("Academic (A+ to F, F<60%)")

    name: models.CharField = models.CharField(
        _("Scale Name"),
        max_length=100,
        help_text=_("Descriptive name for this grading scale"),
    )
    scale_type: models.CharField = models.CharField(
        _("Scale Type"),
        max_length=20,
        choices=ScaleType.choices,
        unique=True,
        help_text=_("Type of grading scale"),
    )
    description: models.TextField = models.TextField(
        _("Description"),
        blank=True,
        help_text=_("Detailed description of this grading scale"),
    )
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this grading scale is currently in use"),
    )

    class Meta:
        verbose_name = _("Grading Scale")
        verbose_name_plural = _("Grading Scales")
        ordering = ["scale_type"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["scale_type", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_scale_type_display()})"  # type: ignore[attr-defined]


class GradeConversion(UserAuditModel):
    """Grade conversion mappings within grading scales.

    Maps letter grades to numeric ranges and GPA points for each grading scale.
    Supports different grade structures across programs.
    """

    grading_scale: models.ForeignKey = models.ForeignKey(
        GradingScale,
        on_delete=models.CASCADE,
        related_name="grade_conversions",
        verbose_name=_("Grading Scale"),
    )
    letter_grade: models.CharField = models.CharField(
        _("Letter Grade"),
        max_length=5,
        help_text=_("Letter grade (A+, A, A-, B+, etc.)"),
    )
    min_percentage: models.DecimalField = models.DecimalField(
        _("Minimum Percentage"),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Minimum percentage for this grade"),
    )
    max_percentage: models.DecimalField = models.DecimalField(
        _("Maximum Percentage"),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Maximum percentage for this grade"),
    )
    gpa_points: models.DecimalField = models.DecimalField(
        _("GPA Points"),
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(4)],
        help_text=_("GPA points for this grade"),
    )
    display_order: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Display Order"),
        default=0,
        help_text=_("Order for displaying grades (0 = highest)"),
    )

    class Meta:
        verbose_name = _("Grade Conversion")
        verbose_name_plural = _("Grade Conversions")
        unique_together = [
            ["grading_scale", "letter_grade"],
            ["grading_scale", "min_percentage"],
            ["grading_scale", "max_percentage"],
        ]
        ordering = ["grading_scale", "display_order"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["grading_scale", "display_order"]),
            models.Index(fields=["letter_grade"]),
        ]

    def __str__(self) -> str:
        return f"{self.grading_scale.name}: {self.letter_grade} ({self.min_percentage}-{self.max_percentage}%)"  # type: ignore[attr-defined]

    def clean(self) -> None:
        """Validate grade conversion data."""
        super().clean()

        if self.min_percentage >= self.max_percentage:
            raise ValidationError(
                {
                    "max_percentage": _(
                        "Maximum percentage must be greater than minimum percentage.",
                    ),
                },
            )


class ClassPartGrade(UserAuditModel):
    """Individual component grades for class parts.

    Stores grades for specific class components (Grammar, Conversation, etc.)
    with support for both numeric and letter grade entry.
    """

    class GradeSource(models.TextChoices):
        """Sources of grade entry."""

        MANUAL_TEACHER = "MANUAL_TEACHER", _("Manual Entry (Teacher)")
        MANUAL_CLERK = "MANUAL_CLERK", _("Manual Entry (Clerk)")
        MOODLE_IMPORT = "MOODLE_IMPORT", _("Moodle Import")
        CALCULATED = "CALCULATED", _("Calculated")
        MIGRATED = "MIGRATED", _("Migrated from Legacy System")

    class GradeStatus(models.TextChoices):
        """Grade entry statuses."""

        DRAFT = "DRAFT", _("Draft")
        SUBMITTED = "SUBMITTED", _("Submitted")
        APPROVED = "APPROVED", _("Approved")
        FINALIZED = "FINALIZED", _("Finalized")

    enrollment: models.ForeignKey = models.ForeignKey(
        "enrollment.ClassHeaderEnrollment",
        on_delete=models.CASCADE,
        related_name="class_part_grades",
        verbose_name=_("Enrollment"),
        help_text=_("Student enrollment this grade belongs to"),
    )
    class_part: models.ForeignKey = models.ForeignKey(
        "scheduling.ClassPart",
        on_delete=models.CASCADE,
        related_name="class_part_grades",
        verbose_name=_("Class Part"),
        help_text=_("Class component this grade is for"),
    )

    # Grade data
    numeric_score: models.DecimalField = models.DecimalField(
        _("Numeric Score"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Numeric score (0-100)"),
    )
    letter_grade: models.CharField = models.CharField(
        _("Letter Grade"),
        max_length=5,
        blank=True,
        help_text=_("Letter grade (A+, A, A-, etc.)"),
    )
    gpa_points: models.DecimalField = models.DecimalField(
        _("GPA Points"),
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(4)],
        help_text=_("GPA points for this grade"),
    )

    # Grade metadata
    grade_source: models.CharField = models.CharField(
        _("Grade Source"),
        max_length=20,
        choices=GradeSource.choices,
        default=GradeSource.MANUAL_TEACHER,
        help_text=_("How this grade was entered"),
    )
    grade_status: models.CharField = models.CharField(
        _("Grade Status"),
        max_length=15,
        choices=GradeStatus.choices,
        default=GradeStatus.DRAFT,
        help_text=_("Current status of this grade"),
    )

    # Audit and tracking
    entered_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="entered_class_part_grades",
        verbose_name=_("Entered By"),
        help_text=_("User who entered this grade"),
    )
    entered_at: models.DateTimeField = models.DateTimeField(
        _("Entered At"),
        default=timezone.now,
        help_text=_("When this grade was entered"),
    )
    approved_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_class_part_grades",
        verbose_name=_("Approved By"),
        help_text=_("User who approved this grade"),
    )
    approved_at: models.DateTimeField = models.DateTimeField(
        _("Approved At"),
        null=True,
        blank=True,
        help_text=_("When this grade was approved"),
    )

    # Notification tracking
    student_notified: models.BooleanField = models.BooleanField(
        _("Student Notified"),
        default=False,
        help_text=_("Whether student has been notified of this grade"),
    )
    notification_date: models.DateTimeField = models.DateTimeField(
        _("Notification Date"),
        null=True,
        blank=True,
        help_text=_("When student was notified"),
    )

    # Additional details
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this grade"),
    )

    class Meta:
        verbose_name = _("Class Part Grade")
        verbose_name_plural = _("Class Part Grades")
        unique_together = [["enrollment", "class_part"]]
        ordering = ["enrollment", "class_part"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["enrollment", "grade_status"]),
            models.Index(fields=["class_part", "grade_status"]),
            models.Index(fields=["entered_at"]),
            models.Index(fields=["student_notified"]),
            models.Index(fields=["grade_source", "grade_status"]),
            models.Index(fields=["entered_by", "entered_at"]),
            # Composite index for common filtering
            models.Index(fields=["enrollment", "class_part", "grade_status"]),
        ]

    def __str__(self) -> str:
        grade_display = self.letter_grade or f"{self.numeric_score}%" if self.numeric_score else "No Grade"
        return f"{self.enrollment.student} - {self.class_part}: {grade_display}"  # type: ignore[attr-defined]

    @property
    def student(self):
        """Get student from enrollment."""
        return self.enrollment.student

    @property
    def class_header(self):
        """Get class header from enrollment."""
        return self.enrollment.class_header

    @property
    def class_session(self):
        """Get class session from class part."""
        return self.class_part.class_session

    def clean(self) -> None:
        """Validate grade data."""
        super().clean()

        # Must have either numeric score or letter grade
        if not self.numeric_score and not self.letter_grade:
            raise ValidationError(
                _("Grade must have either numeric score or letter grade."),
            )

        # Validate enrollment and class part belong to same class header
        if self.enrollment.class_header != self.class_part.class_session.class_header:  # type: ignore[attr-defined]
            raise ValidationError(
                {
                    "class_part": _(
                        "Class part must belong to the same class as the enrollment.",
                    ),
                },
            )

    def is_passing_grade(self) -> bool:
        """Check if this is a passing grade."""
        if self.gpa_points is not None:
            return self.gpa_points >= 1.0

        # Fallback check based on letter grade
        failing_grades = ["F", "F+", "F-"]
        return self.letter_grade not in failing_grades if self.letter_grade else False

    def is_finalized(self) -> bool:
        """Check if this grade is finalized."""
        return self.grade_status == self.GradeStatus.FINALIZED

    def can_be_modified(self) -> bool:
        """Determine if this grade can still be modified."""
        return self.grade_status in [self.GradeStatus.DRAFT, self.GradeStatus.SUBMITTED]

    def get_grade_display(self) -> str:
        """Get formatted grade display."""
        if self.letter_grade:
            return f"{self.letter_grade} ({self.numeric_score}%)" if self.numeric_score else self.letter_grade
        elif self.numeric_score:
            return f"{self.numeric_score}%"
        return "No Grade"


class ClassSessionGrade(UserAuditModel):
    """Calculated grades for class sessions.

    Aggregated grades for sessions, calculated from weighted ClassPart grades.
    Primarily used for IEAP courses with multiple sessions.
    """

    enrollment: models.ForeignKey = models.ForeignKey(
        "enrollment.ClassHeaderEnrollment",
        on_delete=models.CASCADE,
        related_name="class_session_grades",
        verbose_name=_("Enrollment"),
    )
    class_session: models.ForeignKey = models.ForeignKey(
        "scheduling.ClassSession",
        on_delete=models.CASCADE,
        related_name="class_session_grades",
        verbose_name=_("Class Session"),
    )

    # Calculated grade data
    calculated_score: models.DecimalField = models.DecimalField(
        _("Calculated Score"),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Weighted average of class part grades"),
    )
    letter_grade: models.CharField = models.CharField(
        _("Letter Grade"),
        max_length=5,
        help_text=_("Converted letter grade"),
    )
    gpa_points: models.DecimalField = models.DecimalField(
        _("GPA Points"),
        max_digits=4,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(4)],
        help_text=_("GPA points for this session grade"),
    )

    # Calculation metadata
    calculated_at: models.DateTimeField = models.DateTimeField(
        _("Calculated At"),
        default=timezone.now,
        help_text=_("When this grade was calculated"),
    )
    calculation_details: models.JSONField = models.JSONField(
        _("Calculation Details"),
        default=dict,
        help_text=_("Details of how this grade was calculated"),
    )

    class Meta:
        verbose_name = _("Class Session Grade")
        verbose_name_plural = _("Class Session Grades")
        unique_together = [["enrollment", "class_session"]]
        ordering = ["enrollment", "class_session"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["enrollment", "calculated_at"]),
            models.Index(fields=["class_session"]),
        ]

    def __str__(self) -> str:
        return f"{self.enrollment.student} - {self.class_session}: {self.letter_grade}"  # type: ignore[attr-defined]


class GradeChangeHistory(UserAuditModel):
    """Audit trail for all grade changes.

    Tracks all modifications to grades with detailed information about
    what changed, who made the change, and why.
    """

    class ChangeType(models.TextChoices):
        """Types of grade changes."""

        INITIAL_ENTRY = "INITIAL_ENTRY", _("Initial Entry")
        CORRECTION = "CORRECTION", _("Correction")
        RECALCULATION = "RECALCULATION", _("Recalculation")
        STATUS_CHANGE = "STATUS_CHANGE", _("Status Change")
        BULK_UPDATE = "BULK_UPDATE", _("Bulk Update")
        MIGRATION = "MIGRATION", _("Migration")

    # Reference to the grade that was changed
    class_part_grade: models.ForeignKey = models.ForeignKey(
        ClassPartGrade,
        on_delete=models.CASCADE,
        related_name="change_history",
        verbose_name=_("Class Part Grade"),
    )

    # Change details
    change_type: models.CharField = models.CharField(
        _("Change Type"),
        max_length=20,
        choices=ChangeType.choices,
        help_text=_("Type of change made"),
    )
    changed_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="grade_changes",
        verbose_name=_("Changed By"),
    )
    changed_at: models.DateTimeField = models.DateTimeField(
        _("Changed At"),
        default=timezone.now,
    )

    # Previous values
    previous_numeric_score: models.DecimalField = models.DecimalField(
        _("Previous Numeric Score"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    previous_letter_grade: models.CharField = models.CharField(
        _("Previous Letter Grade"),
        max_length=5,
        blank=True,
    )
    previous_status: models.CharField = models.CharField(
        _("Previous Status"),
        max_length=15,
        blank=True,
    )

    # New values
    new_numeric_score: models.DecimalField = models.DecimalField(
        _("New Numeric Score"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    new_letter_grade: models.CharField = models.CharField(
        _("New Letter Grade"),
        max_length=5,
        blank=True,
    )
    new_status: models.CharField = models.CharField(
        _("New Status"),
        max_length=15,
        blank=True,
    )

    # Change justification
    reason: models.TextField = models.TextField(
        _("Reason"),
        help_text=_("Reason for this grade change"),
    )
    additional_details: models.JSONField = models.JSONField(
        _("Additional Details"),
        default=dict,
        help_text=_("Additional details about the change"),
    )

    class Meta:
        verbose_name = _("Grade Change History")
        verbose_name_plural = _("Grade Change History")
        ordering = ["-changed_at"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["class_part_grade", "-changed_at"]),
            models.Index(fields=["changed_by", "-changed_at"]),
            models.Index(fields=["change_type", "-changed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.class_part_grade} - {self.get_change_type_display()} by {self.changed_by}"  # type: ignore[attr-defined]


class GPARecord(UserAuditModel):
    """Calculated GPA records for students.

    Stores term and cumulative GPA calculations limited to courses
    in the student's current major requirements.
    """

    class GPAType(models.TextChoices):
        """Types of GPA calculations."""

        TERM = "TERM", _("Term GPA")
        CUMULATIVE = "CUMULATIVE", _("Cumulative GPA")

    student: models.ForeignKey = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.PROTECT,
        related_name="gpa_records",
        verbose_name=_("Student"),
    )
    term: models.ForeignKey = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.CASCADE,
        related_name="gpa_records",
        verbose_name=_("Term"),
        help_text=_("Term this GPA calculation is for"),
    )
    major: models.ForeignKey = models.ForeignKey(
        "curriculum.Major",
        on_delete=models.CASCADE,
        related_name="gpa_records",
        verbose_name=_("Major"),
        help_text=_("Major this GPA calculation is based on"),
    )

    # GPA data
    gpa_type: models.CharField = models.CharField(
        _("GPA Type"),
        max_length=15,
        choices=GPAType.choices,
        help_text=_("Type of GPA calculation"),
    )
    gpa_value: models.DecimalField = models.DecimalField(
        _("GPA Value"),
        max_digits=4,
        decimal_places=3,
        validators=[MinValueValidator(0), MaxValueValidator(4)],
        help_text=_("Calculated GPA value"),
    )
    quality_points: models.DecimalField = models.DecimalField(
        _("Quality Points"),
        max_digits=8,
        decimal_places=2,
        help_text=_("Total quality points earned"),
    )
    credit_hours_attempted: models.DecimalField = models.DecimalField(
        _("Credit Hours Attempted"),
        max_digits=6,
        decimal_places=2,
        help_text=_("Total credit hours attempted"),
    )
    credit_hours_earned: models.DecimalField = models.DecimalField(
        _("Credit Hours Earned"),
        max_digits=6,
        decimal_places=2,
        help_text=_("Total credit hours earned (passing grades)"),
    )

    # Calculation metadata
    calculated_at: models.DateTimeField = models.DateTimeField(
        _("Calculated At"),
        default=timezone.now,
    )
    calculation_details: models.JSONField = models.JSONField(
        _("Calculation Details"),
        default=dict,
        help_text=_("Details of courses included in calculation"),
    )

    class Meta:
        verbose_name = _("GPA Record")
        verbose_name_plural = _("GPA Records")
        unique_together = [["student", "term", "major", "gpa_type"]]
        ordering = ["student", "-term", "gpa_type"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "term"]),
            models.Index(fields=["major", "term"]),
            models.Index(fields=["gpa_type", "-calculated_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.student} - {self.term} {self.get_gpa_type_display()}: {self.gpa_value}"  # type: ignore[attr-defined]
