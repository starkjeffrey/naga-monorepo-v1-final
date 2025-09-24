"""Enrollment app models following clean architecture principles.

This module contains models for student enrollment in classes, programs, and
academic activities. All models are designed to avoid circular dependencies
while providing comprehensive enrollment management functionality.

Key architectural decisions:
- Clean dependencies: enrollment → curriculum + people + scheduling (no circular dependencies)
- Clear naming: ClassHeaderEnrollment and ClassPartEnrollment for consistency
- Comprehensive enrollment lifecycle management
- Program enrollment with level tracking for language programs
- Course eligibility caching for performance
- Audit trails for enrollment actions

Models:
- ProgramEnrollment: Student enrollment in academic programs/majors
- MajorDeclaration: Student prospective major declarations
- ClassHeaderEnrollment: Student enrollment in scheduled classes
- ClassPartEnrollment: Student enrollment in class components
- ClassSessionExemption: Session exemptions for IEAP repeat students
- StudentCourseEligibility: Cached course eligibility calculations
- StudentCycleStatus: Tracks students who have changed academic cycles
"""

from datetime import date
from decimal import Decimal
from typing import ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import (
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    DecimalField,
    ForeignKey,
    JSONField,
    ManyToManyField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    Q,
    TextField,
)
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import AuditModel, UserAuditModel


class ProgramEnrollment(UserAuditModel):
    """Student enrollment in academic programs or majors over time.

    Tracks a student's enrollment in specific academic programs (majors) with
    support for language and academic tracks, joint programs, and level progression.
    Provides comprehensive enrollment lifecycle management with audit trails.

    Key features:
    - Support for language, academic, and joint program types
    - Entry and finishing level tracking for language programs
    - Date range tracking with term integration
    - Joint program enrollment handling
    - Terms active tracking for progress monitoring
    - Clean dependency on people and curriculum apps
    """

    class EnrollmentType(models.TextChoices):
        """Types of program enrollment."""

        LANGUAGE = "LANG", _("Language Program")
        ACADEMIC = "ACAD", _("Academic Program")
        JOINT = "JOINT", _("Joint Program")

    class EnrollmentStatus(models.TextChoices):
        """Program enrollment statuses."""

        ACTIVE = "ACTIVE", _("Active")
        INACTIVE = "INACTIVE", _("Inactive")
        COMPLETED = "COMPLETED", _("Completed")
        WITHDRAWN = "WITHDRAWN", _("Withdrawn")
        SUSPENDED = "SUSPENDED", _("Suspended")
        TRANSFERRED = "TRANSFERRED", _("Transferred")
        DROPPED = "DROPPED", _("Dropped")
        FAILED = "FAILED", _("Failed")
        NO_SHOW_ACADEMIC = "NO_SHOW_ACADEMIC", _("No Show (Academic)")
        NO_SHOW_LANGUAGE = "NO_SHOW_LANGUAGE", _("No Show (Language)")

    class Division(models.TextChoices):
        """Academic division classification."""

        LANG = "LANG", _("Language Programs")
        ACAD = "ACAD", _("Academic Programs")
        PREP = "PREP", _("Preparatory Programs")
        PROF = "PROF", _("Professional Development")

    class Cycle(models.TextChoices):
        """Academic cycle/level."""

        HS = "HS", _("High School (EHSS)")
        CERT = "CERT", _("Certificate Program")
        PREP = "PREP", _("Preparatory (IEAP/Foundation)")
        BA = "BA", _("Bachelor's Degree")
        MA = "MA", _("Master's Degree")
        PHD = "PHD", _("Doctoral Degree")

    class ExitReason(models.TextChoices):
        """Reasons for program exit."""

        GRAD = "GRAD", _("Graduated")
        COMP = "COMP", _("Completed without Graduation")
        TRAN_INT = "TRAN_INT", _("Transferred to Another Program")
        TRAN_EXT = "TRAN_EXT", _("Transferred to Another Institution")
        DISM = "DISM", _("Academic Dismissal")
        FIN = "FIN", _("Financial Reasons")
        PERS = "PERS", _("Personal Reasons")
        MED = "MED", _("Medical Leave")
        VISA = "VISA", _("Visa/Immigration Issues")
        NS = "NS", _("Never Attended")
        UNK = "UNK", _("Unknown/Not Specified")

    student: ForeignKey = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.PROTECT,
        related_name="program_enrollments",
        verbose_name=_("Student"),
        help_text=_("Student enrolled in this program"),
    )
    program: ForeignKey = models.ForeignKey(
        "curriculum.Major",
        on_delete=models.PROTECT,
        related_name="program_enrollments",
        verbose_name=_("Program"),
        help_text=_("Academic program or major"),
    )

    # Enrollment details
    enrollment_type: CharField = models.CharField(
        _("Enrollment Type"),
        max_length=10,
        choices=EnrollmentType.choices,
        default=EnrollmentType.ACADEMIC,
        db_index=True,
        help_text=_("Type of program enrollment"),
    )
    status: CharField = models.CharField(
        _("Enrollment Status"),
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ACTIVE,
        db_index=True,
        help_text=_("Current enrollment status"),
    )

    # Date tracking
    start_date: DateField = models.DateField(
        _("Start Date"),
        db_index=True,
        help_text=_("Date when program enrollment began"),
    )
    end_date: DateField = models.DateField(
        _("End Date"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Date when program enrollment ended (if applicable)"),
    )

    # Term tracking
    start_term: ForeignKey = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.PROTECT,
        related_name="program_enrollments_starting",
        null=True,
        blank=True,
        verbose_name=_("Start Term"),
        help_text=_("Term when enrollment began (optional for legacy data)"),
    )
    end_term: ForeignKey = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.PROTECT,
        related_name="program_enrollments_ending",
        null=True,
        blank=True,
        verbose_name=_("End Term"),
        help_text=_("Term when enrollment ended (optional)"),
    )

    # Level tracking for language programs
    entry_level: CharField = models.CharField(
        _("Entry Level"),
        max_length=50,
        blank=True,
        help_text=_("Student's level when entering the program"),
    )
    finishing_level: CharField = models.CharField(
        _("Finishing Level"),
        max_length=50,
        blank=True,
        help_text=_("Student's expected or actual finishing level"),
    )

    # Progress tracking
    terms_active: PositiveIntegerField = models.PositiveIntegerField(
        _("Terms Active"),
        default=0,
        help_text=_("Number of terms the student has been active in this program"),
    )
    is_joint: BooleanField = models.BooleanField(
        _("Joint Program"),
        default=False,
        help_text=_("Whether this is part of a joint program enrollment"),
    )

    # Administrative details
    enrolled_by: ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="program_enrollments_created",
        null=True,
        blank=True,
        verbose_name=_("Enrolled By"),
        help_text=_("Staff member who processed the enrollment (null for system-generated)"),
    )
    is_system_generated: BooleanField = models.BooleanField(
        _("System Generated"),
        default=False,
        help_text=_("Whether this enrollment was automatically created/updated by system"),
    )
    last_status_update: DateTimeField = models.DateTimeField(
        _("Last Status Update"),
        auto_now=True,
        help_text=_("When the status was last updated (for tracking automated updates)"),
    )
    notes: TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this program enrollment"),
    )

    # Enhanced fields for program journey tracking
    division: CharField = models.CharField(
        _("Division"),
        max_length=10,
        choices=Division.choices,
        default=Division.ACAD,
        db_index=True,
        help_text=_("Academic division (Language/Academic/etc)"),
    )

    cycle: CharField = models.CharField(
        _("Cycle"),
        max_length=10,
        choices=Cycle.choices,
        default=Cycle.BA,
        db_index=True,
        help_text=_("Academic cycle or degree level"),
    )

    credits_earned: DecimalField = models.DecimalField(
        _("Credits Earned"),
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text=_("Total credits earned in this program"),
    )

    credits_required: DecimalField = models.DecimalField(
        _("Credits Required"),
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Total credits required for program completion"),
    )

    gpa_at_exit: DecimalField = models.DecimalField(
        _("GPA at Exit"),
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Cumulative GPA when leaving the program"),
    )

    exit_reason: CharField = models.CharField(
        _("Exit Reason"),
        max_length=15,
        choices=ExitReason.choices,
        blank=True,
        db_index=True,
        help_text=_("Reason for leaving the program"),
    )

    is_deduced: BooleanField = models.BooleanField(
        _("Major Deduced"),
        default=False,
        help_text=_("Whether major was deduced from course enrollment patterns"),
    )

    deduction_confidence: DecimalField = models.DecimalField(
        _("Deduction Confidence"),
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Confidence score (0-1) for deduced major"),
    )

    completion_percentage: DecimalField = models.DecimalField(
        _("Completion Percentage"),
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text=_("Percentage of program requirements completed"),
    )

    expected_completion_date: DateField = models.DateField(
        _("Expected Completion"),
        null=True,
        blank=True,
        help_text=_("Originally expected completion date"),
    )

    time_to_completion: PositiveIntegerField = models.PositiveIntegerField(
        _("Time to Completion"),
        null=True,
        blank=True,
        help_text=_("Days from start to completion/exit"),
    )

    enrollment_gaps: JSONField = models.JSONField(
        _("Enrollment Gaps"),
        default=list,
        blank=True,
        help_text=_("List of terms with no enrollment"),
    )

    legacy_section_code: CharField = models.CharField(
        _("Legacy Section Code"),
        max_length=10,
        blank=True,
        db_index=True,
        help_text=_("Section code from legacy system (87=BA, 147=MA, etc)"),
    )

    class Meta:
        verbose_name = _("Program Enrollment")
        verbose_name_plural = _("Program Enrollments")
        ordering = ["student", "-start_date"]
        unique_together = [["student", "program", "start_date"]]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "status"]),
            models.Index(fields=["program", "enrollment_type"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["start_term", "end_term"]),
            models.Index(fields=["division", "cycle"], name="enrollment_division_cycle_idx"),
            models.Index(fields=["exit_reason", "status"], name="enrollment_exit_status_idx"),
            models.Index(
                fields=["is_deduced", "deduction_confidence"],
                name="enrollment_deduction_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.student} - {self.program} ({self.get_enrollment_type_display()})"

    @property
    def is_active(self) -> bool:
        """Check if enrollment is currently active."""
        return self.status == self.EnrollmentStatus.ACTIVE

    @property
    def is_current(self) -> bool:
        """Check if enrollment is current based on dates."""
        today = timezone.now().date()
        if self.end_date:
            return self.start_date <= today <= self.end_date
        return self.start_date <= today

    def end_enrollment(
        self,
        end_date: date | None = None,
        end_term=None,
        reason: str = "",
        user=None,
    ) -> None:
        """End the program enrollment with proper audit trail."""
        self.status = self.EnrollmentStatus.COMPLETED
        self.end_date = end_date or timezone.now().date()
        if end_term:
            self.end_term = end_term
        if reason:
            self.notes = f"{self.notes}\n\nEnded: {reason}".strip()
        self.save(update_fields=["status", "end_date", "end_term", "notes"])

    def withdraw_enrollment(
        self,
        withdrawal_date: date | None = None,
        reason: str = "",
        user=None,
    ) -> None:
        """Withdraw from program enrollment."""
        self.status = self.EnrollmentStatus.WITHDRAWN
        self.end_date = withdrawal_date or timezone.now().date()
        if reason:
            self.notes = f"{self.notes}\n\nWithdrawn: {reason}".strip()
        self.save(update_fields=["status", "end_date", "notes"])

    @classmethod
    def get_most_recent_for_student(cls, student):
        """Get the most recent (latest start_date) program enrollment for a student."""
        return cls.objects.filter(student=student).order_by("-start_date").first()

    def update_status_by_system(self, new_status: str, reason: str = "") -> None:
        """Update status via automated system with proper tracking."""
        self.status = new_status
        self.is_system_generated = True
        # Import here to avoid circular import
        from apps.enrollment.services import get_system_user

        self.enrolled_by = get_system_user()  # Use system user for audit trail
        if reason:
            timestamp = timezone.now().strftime("%Y-%m-%d %H:%M")
            system_note = f"[{timestamp} SYSTEM] Status changed to {new_status}: {reason}"
            self.notes = f"{self.notes}\n{system_note}".strip()
        self.save(
            update_fields=[
                "status",
                "is_system_generated",
                "enrolled_by",
                "notes",
                "last_status_update",
            ]
        )

    def clean(self) -> None:
        """Validate program enrollment data."""
        super().clean()

        # Validate date range
        if self.end_date and self.start_date >= self.end_date:
            raise ValidationError({"end_date": _("End date must be after start date.")})

        # Validate term range
        if (
            self.end_term
            and self.start_term
            and self.start_term_id
            and self.end_term_id
            and self.start_term.start_date >= self.end_term.start_date
        ):
            raise ValidationError({"end_term": _("End term must be after start term.")})

        # Language program validation
        if self.enrollment_type == self.EnrollmentType.LANGUAGE:
            if not self.entry_level:
                raise ValidationError(
                    {
                        "entry_level": _(
                            "Entry level is required for language program enrollments.",
                        ),
                    },
                )


class StudentCourseEligibility(UserAuditModel):
    """Cached course eligibility calculations for students by term.

    Tracks which courses students are eligible to take in specific terms,
    with caching for performance and detailed tracking of eligibility factors.
    Supports prerequisite tracking, retake management, and priority scoring.

    Key features:
    - Performance-optimized eligibility caching
    - Missing prerequisite tracking
    - Retake identification and priority scoring
    - Term-specific eligibility calculations
    - Comprehensive eligibility reasoning
    - Clean dependency on people and curriculum apps
    """

    student: ForeignKey = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.PROTECT,
        related_name="course_eligibilities",
        verbose_name=_("Student"),
        help_text=_("Student whose eligibility is being tracked"),
    )
    course: ForeignKey = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.CASCADE,
        related_name="student_eligibilities",
        verbose_name=_("Course"),
        help_text=_("Course for which eligibility is being checked"),
    )
    term: ForeignKey = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.CASCADE,
        related_name="course_eligibilities",
        verbose_name=_("Term"),
        help_text=_("Term for which eligibility applies"),
    )

    # Eligibility status
    is_eligible: BooleanField = models.BooleanField(
        _("Is Eligible"),
        default=False,
        db_index=True,
        help_text=_("Whether the student is eligible for this course in this term"),
    )

    # Eligibility details
    missing_prerequisites: ManyToManyField = models.ManyToManyField(
        "curriculum.Course",
        related_name="blocking_eligibilities",
        blank=True,
        verbose_name=_("Missing Prerequisites"),
        help_text=_("Prerequisites the student has not yet completed"),
    )

    # Retake management
    is_retake: BooleanField = models.BooleanField(
        _("Is Retake"),
        default=False,
        db_index=True,
        help_text=_("Whether this would be a retake of the course"),
    )
    previous_attempts: PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Previous Attempts"),
        default=0,
        help_text=_("Number of previous attempts at this course"),
    )
    retry_priority_score: PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Retry Priority Score"),
        default=0,
        help_text=_("Priority score for retake scheduling (higher = more priority)"),
    )

    # Calculation metadata
    last_calculated: DateTimeField = models.DateTimeField(
        _("Last Calculated"),
        auto_now=True,
        help_text=_("When eligibility was last calculated"),
    )
    calculation_notes: TextField = models.TextField(
        _("Calculation Notes"),
        blank=True,
        help_text=_("Notes about how eligibility was determined"),
    )

    class Meta:
        verbose_name = _("Student Course Eligibility")
        verbose_name_plural = _("Student Course Eligibilities")
        unique_together = [["student", "course", "term"]]
        ordering = ["student", "term", "course"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "term", "is_eligible"]),
            models.Index(fields=["course", "term", "is_eligible"]),
            models.Index(fields=["is_retake", "retry_priority_score"]),
            models.Index(fields=["last_calculated"]),
        ]

    def __str__(self) -> str:
        status = "✓" if self.is_eligible else "✗"
        retake = " (retake)" if self.is_retake else ""
        return f"{status} {self.student} - {self.course.code} ({self.term}){retake}"

    @property
    def eligibility_summary(self) -> str:
        """Get a human-readable eligibility summary."""
        if self.is_eligible:
            if self.is_retake:
                return f"Eligible for retake (attempt #{self.previous_attempts + 1})"
            return "Eligible"

        if self.missing_prerequisites.exists():
            max_display_prereqs = 3
            missing = ", ".join(
                [p.code for p in self.missing_prerequisites.all()[:max_display_prereqs]],
            )
            count = self.missing_prerequisites.count()
            if count > max_display_prereqs:
                missing += f" (+{count - max_display_prereqs} more)"
            return f"Missing prerequisites: {missing}"

        return "Not eligible"

    def recalculate_eligibility(self) -> bool:
        """Recalculate eligibility status (placeholder for business logic)."""
        # This would contain the actual eligibility calculation logic
        self.last_calculated = timezone.now()
        self.save(update_fields=["last_calculated"])
        return self.is_eligible


class ProgramTransition(models.Model):
    """Track transitions between programs for journey analysis.

    This model captures when students move from one program to another,
    enabling analysis of common pathways and transition patterns.
    """

    class TransitionType(models.TextChoices):
        """Types of program transitions."""

        PROG = "PROG", _("Natural Progression (e.g., IEAP to BA)")
        MAJOR = "MAJOR", _("Change of Major")
        LEVEL = "LEVEL", _("Level Change (e.g., BA to MA)")
        LAT = "LAT", _("Lateral Move (e.g., between language programs)")
        RESTART = "RESTART", _("Program Restart")

    from_enrollment: ForeignKey = models.ForeignKey(
        "ProgramEnrollment",
        on_delete=models.CASCADE,
        related_name="transitions_from",
        verbose_name=_("From Program"),
        null=True,
        blank=True,
    )

    to_enrollment: ForeignKey = models.ForeignKey(
        "ProgramEnrollment",
        on_delete=models.CASCADE,
        related_name="transitions_to",
        verbose_name=_("To Program"),
        null=True,
        blank=True,
    )

    transition_date: DateField = models.DateField(_("Transition Date"), db_index=True)

    transition_term: ForeignKey = models.ForeignKey("curriculum.Term", on_delete=models.PROTECT, null=True, blank=True)

    transition_type: CharField = models.CharField(_("Transition Type"), max_length=10, choices=TransitionType.choices)

    transition_reason: TextField = models.TextField(_("Transition Reason"), blank=True)

    credits_transferred: DecimalField = models.DecimalField(
        _("Credits Transferred"), max_digits=6, decimal_places=2, default=0
    )

    gap_days: PositiveIntegerField = models.PositiveIntegerField(
        _("Gap Days"), default=0, help_text=_("Days between programs")
    )

    class Meta:
        verbose_name = _("Program Transition")
        verbose_name_plural = _("Program Transitions")
        ordering = ["from_enrollment__student", "transition_date"]
        indexes = [
            models.Index(fields=["transition_date"], name="transition_date_idx"),
            models.Index(fields=["transition_type"], name="transition_type_idx"),
        ]


class ClassHeaderEnrollment(UserAuditModel):
    """Student enrollment in scheduled classes (ClassHeader).

    Represents a student's enrollment in a specific class offering with
    comprehensive status tracking, grade management, and audit trails.
    Supports enrollment workflows, waitlisting, and completion tracking.

    Key features:
    - Comprehensive enrollment status management
    - Grade tracking and final grade calculation
    - Enrollment workflow support (enrolled → completed/withdrawn)
    - Waitlist management
    - Administrative notes and audit trails
    - Clean dependency on people and scheduling apps
    """

    class EnrollmentStatus(models.TextChoices):
        """Class enrollment statuses for academic and language programs."""

        # Common statuses
        ENROLLED = "ENROLLED", _("Enrolled")
        ACTIVE = "ACTIVE", _("Active")  # For classes currently in session
        DROPPED = "DROPPED", _("Dropped")
        COMPLETED = "COMPLETED", _("Completed")
        FAILED = "FAILED", _("Failed")
        INCOMPLETE = "INCOMPLETE", _("Incomplete")  # Grade 'I' - term ended but work not completed

        # Academic program specific
        WITHDRAWN = "WITHDRAWN", _("Withdrawn")  # Teacher gave 'W' grade
        AUDIT = "AUDIT", _("Audit")  # Not for credit
        NO_SHOW_ACADEMIC = "NO_SHOW_ACADEMIC", _("No Show (Academic)")

        # Language program specific
        NO_SHOW_LANGUAGE = "NO_SHOW_LANGUAGE", _("No Show (Language)")

    student: ForeignKey = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.PROTECT,
        related_name="class_header_enrollments",
        verbose_name=_("Student"),
        db_index=True,
        help_text=_("Student enrolled in this class"),
    )
    class_header: ForeignKey = models.ForeignKey(
        "scheduling.ClassHeader",
        on_delete=models.CASCADE,
        related_name="class_header_enrollments",
        verbose_name=_("Class"),
        db_index=True,
        help_text=_("Scheduled class the student is enrolled in"),
    )

    # Enrollment status
    status: CharField = models.CharField(
        _("Enrollment Status"),
        max_length=20,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.ENROLLED,
        db_index=True,
        help_text=_("Current enrollment status"),
    )

    # Grade tracking
    final_grade: CharField = models.CharField(
        _("Final Grade"),
        max_length=10,
        blank=True,
        db_index=True,
        help_text=_("Final grade awarded for the class"),
    )
    grade_points: DecimalField = models.DecimalField(
        _("Grade Points"),
        max_digits=4,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("4.00")),
        ],
        help_text=_("Grade points for GPA calculation"),
    )

    # Enrollment dates
    enrollment_date: DateTimeField = models.DateTimeField(
        _("Enrollment Date"),
        default=timezone.now,
        db_index=True,
        help_text=_("When the student was enrolled"),
    )
    completion_date: DateTimeField = models.DateTimeField(
        _("Completion Date"),
        null=True,
        blank=True,
        help_text=_("When the student completed or withdrew from the class"),
    )

    # Administrative details
    enrolled_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="class_enrollments_created",
        verbose_name=_("Enrolled By"),
        help_text=_("Staff member who processed the enrollment"),
    )
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Administrative notes about this enrollment"),
    )

    @classmethod
    def get_active_enrollments(cls, use_cache: bool = True):
        """Get all ACTIVE enrollments with optional caching for fast response time.

        Args:
            use_cache: Whether to use Django cache framework for results

        Returns:
            QuerySet of ACTIVE ClassHeaderEnrollment records
        """
        from django.core.cache import cache

        if use_cache:
            cache_key = "active_enrollments_qs"
            cached_ids = cache.get(cache_key)

            if cached_ids is not None:
                # Return queryset from cached IDs
                return cls.objects.filter(id__in=cached_ids).select_related(
                    "student__person",
                    "class_header__course",
                    "class_header__term",
                )

        # Build fresh queryset with optimizations
        queryset = (
            cls.objects.filter(status=cls.EnrollmentStatus.ACTIVE)
            .select_related("student__person", "class_header__course", "class_header__term")
            .only(
                "id",
                "student_id",
                "class_header_id",
                "status",
                "enrollment_date",
                "final_grade",
                "student__person__personal_name",
                "student__person__family_name",
                "class_header__course__code",
                "class_header__course__title",
                "class_header__term__code",
                "class_header__section_id",
            )
        )

        if use_cache:
            # Cache the IDs for 15 minutes
            enrollment_ids = list(queryset.values_list("id", flat=True))
            cache.set(cache_key, enrollment_ids, 900)  # 15 minutes

        return queryset

    @classmethod
    def clear_active_enrollments_cache(cls):
        """Clear the cached active enrollments."""
        from django.core.cache import cache

        cache.delete("active_enrollments_qs")

    # Override tracking
    has_override: models.BooleanField = models.BooleanField(
        _("Has Override"),
        default=False,
        help_text=_("Whether this enrollment was created with management override"),
    )
    override_type: models.CharField = models.CharField(
        _("Override Type"),
        max_length=50,
        blank=True,
        help_text=_("Type of override applied (if any)"),
    )
    override_reason: models.TextField = models.TextField(
        _("Override Reason"),
        blank=True,
        help_text=_("Reason for management override (if any)"),
    )

    # Special flags
    is_audit: models.BooleanField = models.BooleanField(
        _("Audit Only"),
        default=False,
        help_text=_("Whether student is auditing (not for credit)"),
    )
    late_enrollment: models.BooleanField = models.BooleanField(
        _("Late Enrollment"),
        default=False,
        help_text=_("Whether student enrolled after normal deadline"),
    )

    class Meta:
        verbose_name = _("Class Header Enrollment")
        verbose_name_plural = _("Class Header Enrollments")
        unique_together = [["student", "class_header"]]
        ordering = ["student", "-enrollment_date"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "status"]),
            models.Index(fields=["class_header", "status"]),
            models.Index(fields=["enrollment_date"]),
            models.Index(fields=["status", "completion_date"]),
            models.Index(fields=["status"], name="enrollment_status_idx"),  # Optimize ACTIVE status queries
        ]
        constraints = [
            # Prevent duplicate active enrollments for same student and class
            models.UniqueConstraint(
                fields=["student", "class_header"],
                condition=Q(status__in=["ENROLLED", "ACTIVE"]),
                name="unique_active_enrollment_per_class",
            ),
            # Ensure grade points are valid when set
            models.CheckConstraint(
                check=Q(grade_points__isnull=True) | (Q(grade_points__gte=0) & Q(grade_points__lte=4)),
                name="valid_grade_points_range",
            ),
        ]
        permissions = [
            ("can_manage_enrollments", "Can manage student enrollments"),
            ("can_override_capacity", "Can override class capacity limits"),
            ("can_override_prerequisites", "Can override prerequisite requirements"),
            ("can_override_credit_limits", "Can override credit/course limits"),
        ]

    def __str__(self) -> str:
        return f"{self.student} → Class #{self.class_header_id} ({self.get_status_display()})"

    @property
    def is_active(self) -> bool:
        """Check if enrollment is currently active."""
        return self.status in [
            self.EnrollmentStatus.ACTIVE,  # ACTIVE = ENROLLED (active enrollment)
            self.EnrollmentStatus.AUDIT,
        ]

    @property
    def is_completed(self) -> bool:
        """Check if enrollment is completed (passed or failed)."""
        return self.status in [
            self.EnrollmentStatus.COMPLETED,
            self.EnrollmentStatus.FAILED,
        ]

    def complete_enrollment(
        self,
        final_grade: str = "",
        grade_points: Decimal | None = None,
        notes: str = "",
        user=None,
    ) -> None:
        """Complete the enrollment with final grade."""
        self.status = self.EnrollmentStatus.COMPLETED
        self.completion_date = timezone.now()
        if final_grade:
            self.final_grade = final_grade
        if grade_points is not None:
            self.grade_points = grade_points
        if notes:
            self.notes = f"{self.notes}\n\nCompleted: {notes}".strip()
        self.save(
            update_fields=[
                "status",
                "completion_date",
                "final_grade",
                "grade_points",
                "notes",
            ],
        )

    def withdraw_enrollment(self, reason: str = "", user=None) -> None:
        """Withdraw from the class enrollment."""
        self.status = self.EnrollmentStatus.WITHDRAWN
        self.completion_date = timezone.now()
        if reason:
            self.notes = f"{self.notes}\n\nWithdrawn: {reason}".strip()
        self.save(update_fields=["status", "completion_date", "notes"])

    def clean(self) -> None:
        """Validate class header enrollment data."""
        super().clean()

        # Validate completion requirements
        if self.status == self.EnrollmentStatus.COMPLETED:
            if not self.final_grade:
                raise ValidationError(
                    {
                        "final_grade": _(
                            "Final grade is required for completed enrollments.",
                        ),
                    },
                )

        # Validate grade points range
        max_gpa = 4.0
        min_gpa = 0.0
        if self.grade_points is not None:
            if not (min_gpa <= self.grade_points <= max_gpa):
                raise ValidationError(
                    {
                        "grade_points": _(
                            "Grade points must be between {min_gpa:.2f} and {max_gpa:.2f}.".format(
                                min_gpa=min_gpa,
                                max_gpa=max_gpa,
                            ),
                        ),
                    },
                )


class ClassPartEnrollment(UserAuditModel):
    """Student enrollment in specific class components (ClassPart).

    Links students to individual components of classes, typically created
    automatically when students enroll in the parent ClassHeader. Supports
    the language program's multi-part class structure.

    Key features:
    - Automatic creation from ClassHeader enrollment
    - Individual component tracking for multi-part classes
    - Active/inactive status management
    - Date tracking for enrollment history
    - Clean dependency on people and scheduling apps
    """

    student: models.ForeignKey = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.PROTECT,
        related_name="class_part_enrollments",
        verbose_name=_("Student"),
        db_index=True,
        help_text=_("Student enrolled in this class part"),
    )
    class_part: models.ForeignKey = models.ForeignKey(
        "scheduling.ClassPart",
        on_delete=models.CASCADE,
        related_name="class_part_enrollments",
        verbose_name=_("Class Part"),
        db_index=True,
        help_text=_("Specific class component the student is enrolled in"),
    )

    # Enrollment tracking
    enrollment_date: models.DateTimeField = models.DateTimeField(
        _("Enrollment Date"),
        default=timezone.now,
        help_text=_("When the student was enrolled in this class part"),
    )
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        db_index=True,
        help_text=_("Whether this enrollment is currently active"),
    )

    # Administrative details
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this class part enrollment"),
    )

    class Meta:
        verbose_name = _("Class Part Enrollment")
        verbose_name_plural = _("Class Part Enrollments")
        unique_together = [["student", "class_part", "is_active"]]
        ordering = ["student", "class_part"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "is_active"]),
            models.Index(fields=["class_part", "is_active"]),
            models.Index(fields=["enrollment_date"]),
        ]

    def __str__(self) -> str:
        status = "✓" if self.is_active else "✗"
        return f"{status} {self.student} → Part #{self.class_part_id}"

    def deactivate(self, reason: str = "") -> None:
        """Deactivate this class part enrollment."""
        self.is_active = False
        if reason:
            self.notes = f"{self.notes}\n\nDeactivated: {reason}".strip()
        self.save(update_fields=["is_active", "notes"])

    def reactivate(self, reason: str = "") -> None:
        """Reactivate this class part enrollment."""
        self.is_active = True
        if reason:
            self.notes = f"{self.notes}\n\nReactivated: {reason}".strip()
        self.save(update_fields=["is_active", "notes"])


class ClassSessionExemption(UserAuditModel):
    """Session exemptions for IEAP repeat students.

    Allows repeat students to be exempted from specific sessions within
    an IEAP class while still being enrolled at the ClassHeader level.
    Supports business need for students repeating only part of IEAP.

    Key features:
    - Session-specific exemptions within IEAP classes
    - Handles repeat student scenarios gracefully
    - Maintains clean enrollment hierarchy
    - Administrative tracking for exemption reasons
    """

    class ExemptionType(models.TextChoices):
        """Types of session exemptions."""

        MEDICAL = "MEDICAL", _("Medical")
        ACADEMIC = "ACADEMIC", _("Academic")
        PERSONAL = "PERSONAL", _("Personal")
        ADMINISTRATIVE = "ADMIN", _("Administrative")

    class_header_enrollment: models.ForeignKey = models.ForeignKey(
        ClassHeaderEnrollment,
        on_delete=models.CASCADE,
        related_name="session_exemptions",
        verbose_name=_("Class Header Enrollment"),
        help_text=_("The class enrollment this exemption applies to"),
    )
    class_session: models.ForeignKey = models.ForeignKey(
        "scheduling.ClassSession",
        on_delete=models.CASCADE,
        related_name="session_exemptions",
        verbose_name=_("Class Session"),
        help_text=_("Session the student is exempted from"),
    )

    # Exemption details
    exemption_reason: models.CharField = models.CharField(
        _("Exemption Reason"),
        max_length=100,
        help_text=_("Reason for session exemption (e.g., 'Already passed Session 1')"),
    )
    exempted_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="session_exemptions_created",
        verbose_name=_("Exempted By"),
        help_text=_("Staff member who approved the exemption"),
    )
    exemption_date: models.DateTimeField = models.DateTimeField(
        _("Exemption Date"),
        default=timezone.now,
        help_text=_("When the exemption was granted"),
    )

    # Administrative details
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this session exemption"),
    )

    class Meta:
        verbose_name = _("Class Session Exemption")
        verbose_name_plural = _("Class Session Exemptions")
        unique_together = [["class_header_enrollment", "class_session"]]
        ordering = ["class_header_enrollment", "class_session"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["class_header_enrollment"]),
            models.Index(fields=["class_session"]),
            models.Index(fields=["exemption_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.class_header_enrollment.student} exempted from {self.class_session}"

    def clean(self) -> None:
        """Validate session exemption data."""
        super().clean()

        # Validate that session belongs to the same class header
        if (
            self.class_session
            and self.class_header_enrollment
            and self.class_session.class_header != self.class_header_enrollment.class_header
        ):
            raise ValidationError(
                {
                    "class_session": _(
                        "Session must belong to the same class as the enrollment.",
                    ),
                },
            )


class MajorDeclaration(UserAuditModel):
    """Student declaration of intended major/program.

    Tracks a student's prospective choice of major, which may differ from their
    historical ProgramEnrollment record. This model stores the student's CHOICE
    of major, including cases where they change major but haven't taken classes
    in the new major yet (since ProgramEnrollment is retrospective).

    Key features:
    - Prospective major tracking (student's current choice)
    - Date-based major change tracking with effective dates
    - Support for both language programs (IEAP) and academic majors (BA/MA)
    - Paperwork and reasoning documentation for major changes
    - Validation against conflicting course registrations
    - Clean dependency on people and curriculum apps

    Business logic:
    - MajorDeclaration represents student's intended/declared major
    - ProgramEnrollment represents historical major based on course taking
    - Both must be consistent when viewed together for course registration
    """

    student: models.ForeignKey = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.PROTECT,
        related_name="major_declarations",
        verbose_name=_("Student"),
        help_text=_("Student making the major declaration"),
    )
    major: models.ForeignKey = models.ForeignKey(
        "curriculum.Major",
        on_delete=models.PROTECT,
        related_name="major_declarations",
        verbose_name=_("Declared Major"),
        help_text=_("Major or program the student has declared"),
    )

    # Date tracking
    effective_date: models.DateField = models.DateField(
        _("Effective Date"),
        default=date.today,
        db_index=True,
        help_text=_("Date when this major declaration becomes effective"),
    )
    declared_date: models.DateTimeField = models.DateTimeField(
        _("Declaration Date"),
        default=timezone.now,
        db_index=True,
        help_text=_("When the student made this declaration"),
    )

    # Status tracking
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        db_index=True,
        help_text=_("Whether this declaration is currently active"),
    )

    # Administrative details and paperwork
    declared_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="major_declarations_processed",
        null=True,
        blank=True,
        verbose_name=_("Declared By"),
        help_text=_("Staff member who processed the declaration (null for student self-declaration)"),
    )
    is_self_declared: models.BooleanField = models.BooleanField(
        _("Self Declared"),
        default=True,
        help_text=_("Whether student declared this themselves via mobile app"),
    )

    # Change management
    previous_declaration: models.ForeignKey = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="superseded_by",
        verbose_name=_("Previous Declaration"),
        help_text=_("Previous major declaration that this one supersedes"),
    )
    change_reason: models.TextField = models.TextField(
        _("Change Reason"),
        blank=True,
        help_text=_("Reason for major change (required for major changes)"),
    )
    supporting_documents: models.TextField = models.TextField(
        _("Supporting Documents"),
        blank=True,
        help_text=_("Reference to paperwork or documents supporting this declaration"),
    )

    # Approval workflow
    requires_approval: models.BooleanField = models.BooleanField(
        _("Requires Approval"),
        default=False,
        help_text=_("Whether this declaration requires administrative approval"),
    )
    approved_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="major_declarations_approved",
        null=True,
        blank=True,
        verbose_name=_("Approved By"),
        help_text=_("Staff member who approved the declaration (if required)"),
    )
    approved_date: models.DateTimeField = models.DateTimeField(
        _("Approval Date"),
        null=True,
        blank=True,
        help_text=_("When the declaration was approved"),
    )

    # Notes and tracking
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this major declaration"),
    )

    class Meta:
        verbose_name = _("Major Declaration")
        verbose_name_plural = _("Major Declarations")
        ordering = ["student", "-effective_date", "-declared_date"]
        unique_together = [["student", "effective_date", "is_active"]]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "is_active", "effective_date"]),
            models.Index(fields=["major", "is_active"]),
            models.Index(fields=["effective_date", "is_active"]),
            models.Index(fields=["declared_date"]),
            models.Index(fields=["requires_approval", "approved_by"]),
        ]

    def __str__(self) -> str:
        status = "✓" if self.is_active else "✗"
        approval = " (pending)" if self.requires_approval and not self.approved_date else ""
        return f"{status} {self.student} → {self.major} (effective {self.effective_date}){approval}"

    @property
    def is_effective(self) -> bool:
        """Check if declaration is currently effective based on date."""
        return self.is_active and self.effective_date <= date.today()

    @property
    def is_pending_approval(self) -> bool:
        """Check if declaration is pending approval."""
        return self.requires_approval and not self.approved_date

    @property
    def is_major_change(self) -> bool:
        """Check if this represents a change from previous major."""
        return self.previous_declaration is not None

    @classmethod
    def get_current_declaration(cls, student):
        """Get the current active major declaration for a student."""
        return (
            cls.objects.filter(
                student=student,
                is_active=True,
                effective_date__lte=timezone.now().date(),
            )
            .order_by("-effective_date")
            .first()
        )

    @classmethod
    def get_future_declaration(cls, student):
        """Get future major declaration for a student (not yet effective)."""
        return (
            cls.objects.filter(
                student=student,
                is_active=True,
                effective_date__gt=timezone.now().date(),
            )
            .order_by("effective_date")
            .first()
        )

    def activate_declaration(self, user=None):
        """Activate this declaration and deactivate conflicting ones."""
        from .exceptions import OverlappingMajorDeclarationError

        # Check for overlapping active declarations
        overlapping = MajorDeclaration.objects.filter(
            student=self.student,
            is_active=True,
            effective_date=self.effective_date,
        ).exclude(pk=self.pk)

        if overlapping.exists():
            msg = f"Student {self.student} already has an active declaration for {self.effective_date}"
            raise OverlappingMajorDeclarationError(msg)

        # Deactivate previous declarations that this supersedes
        if self.previous_declaration:
            self.previous_declaration.is_active = False
            self.previous_declaration.save(update_fields=["is_active"])

        # Activate this declaration
        self.is_active = True
        if user:
            self.declared_by = user
        self.save(update_fields=["is_active", "declared_by"])

    def approve_declaration(self, user, notes: str = ""):
        """Approve a declaration that requires approval."""
        if not self.requires_approval:
            return

        self.approved_by = user
        self.approved_date = timezone.now()
        if notes:
            self.notes = f"{self.notes}\n\nApproved: {notes}".strip()
        self.save(update_fields=["approved_by", "approved_date", "notes"])

    def validate_against_enrollment_history(self):
        """Validate declaration against student's enrollment history.

        Raises MajorConflictError if declaration conflicts with course registrations
        or enrollment patterns that would be inconsistent.
        """
        # Get student's most recent program enrollment
        recent_enrollment = ProgramEnrollment.get_most_recent_for_student(self.student)

        if recent_enrollment and recent_enrollment.program != self.major:
            # Check if student has active enrollments in courses that conflict
            # with their new major declaration - this would be implemented
            # with business logic specific to program requirements
            pass  # Placeholder for detailed validation logic

    def clean(self) -> None:
        """Validate major declaration data."""
        super().clean()

        # Validate effective date
        if self.effective_date and self.declared_date:
            if self.effective_date < self.declared_date.date():
                raise ValidationError({"effective_date": _("Effective date cannot be before declaration date.")})

        # Validate approval requirements
        if self.approved_date and not self.requires_approval:
            raise ValidationError({"approved_date": _("Approval date should not be set if approval is not required.")})

        if self.requires_approval and self.approved_date and not self.approved_by:
            raise ValidationError({"approved_by": _("Approved by is required when approval date is set.")})

        # Validate major change requirements
        if self.is_major_change and not self.change_reason:
            raise ValidationError({"change_reason": _("Change reason is required when changing majors.")})

        # Validate against enrollment history
        try:
            self.validate_against_enrollment_history()
        except Exception as e:
            # Convert to ValidationError for form handling
            raise ValidationError(str(e)) from e


class SeniorProjectGroup(AuditModel):
    """Senior project groups for BA-level capstone projects.

    Senior projects are conducted by 1-5 students working together on a
    research project under faculty supervision. Groups form themselves
    and are charged tiered pricing based on group size.

    Key features:
    - Links to senior project course (BUS-489, FIN-489, IR-489, THM-433, EDUC-408)
    - Tracks 1-5 student members with tiered pricing
    - Project topic and final paper title tracking
    - Faculty advisor assignment
    - Important milestone dates
    - Project status management
    """

    class ProjectStatus(models.TextChoices):
        """Status of the senior project."""

        PROPOSED = "PROPOSED", _("Proposed")
        APPROVED = "APPROVED", _("Approved")
        IN_PROGRESS = "IN_PROGRESS", _("In Progress")
        SUBMITTED = "SUBMITTED", _("Submitted")
        DEFENDED = "DEFENDED", _("Defended")
        COMPLETED = "COMPLETED", _("Completed")
        WITHDRAWN = "WITHDRAWN", _("Withdrawn")

    # Core project information
    course: models.ForeignKey = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.PROTECT,
        related_name="senior_project_groups",
        verbose_name=_("Senior Project Course"),
        help_text=_("Course this senior project is associated with"),
        limit_choices_to={"is_senior_project": True},
    )
    term: models.ForeignKey = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.PROTECT,
        related_name="senior_project_groups",
        verbose_name=_("Term"),
        help_text=_("Term when this project is being conducted"),
    )

    # Group members (1-5 students)
    students: models.ManyToManyField = models.ManyToManyField(
        "people.StudentProfile",
        related_name="senior_project_groups",
        verbose_name=_("Group Members"),
        help_text=_("Students participating in this senior project (1-5 students)"),
    )

    # Faculty supervision
    advisor: models.ForeignKey = models.ForeignKey(
        "people.TeacherProfile",
        on_delete=models.PROTECT,
        related_name="advised_senior_projects",
        verbose_name=_("Faculty Advisor"),
        help_text=_("Faculty member supervising this project"),
    )

    # Project details
    project_title: models.CharField = models.CharField(
        _("Project Title"),
        max_length=255,
        help_text=_("Working title of the senior project"),
    )
    final_title: models.CharField = models.CharField(
        _("Final Paper Title"),
        max_length=255,
        blank=True,
        help_text=_("Final title of the completed research paper"),
    )
    project_description: models.TextField = models.TextField(
        _("Project Description"),
        blank=True,
        help_text=_("Detailed description of the project scope and objectives"),
    )

    # Status and timeline
    status: models.CharField = models.CharField(
        _("Project Status"),
        max_length=20,
        choices=ProjectStatus.choices,
        default=ProjectStatus.PROPOSED,
        db_index=True,
        help_text=_("Current status of the project"),
    )

    # Important dates
    proposal_date: models.DateField = models.DateField(
        _("Proposal Date"),
        null=True,
        blank=True,
        help_text=_("Date when project proposal was submitted"),
    )
    approval_date: models.DateField = models.DateField(
        _("Approval Date"),
        null=True,
        blank=True,
        help_text=_("Date when project was approved by advisor/committee"),
    )
    submission_date: models.DateField = models.DateField(
        _("Submission Date"),
        null=True,
        blank=True,
        help_text=_("Date when final paper was submitted"),
    )
    defense_date: models.DateField = models.DateField(
        _("Defense Date"),
        null=True,
        blank=True,
        help_text=_("Date of project defense/presentation"),
    )
    completion_date: models.DateField = models.DateField(
        _("Completion Date"),
        null=True,
        blank=True,
        help_text=_("Date when project was officially completed"),
    )

    # CSV Import fields (added for data migration)
    registration_date: models.DateField = models.DateField(
        _("Registration Date"),
        blank=True,
        null=True,
        help_text=_("Date when students were first registered for the senior project"),
    )
    registration_term: models.ForeignKey = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="registered_senior_projects",
        verbose_name=_("Registration Term"),
        help_text=_("Term that contains the registration date (automatically determined)"),
    )
    graduation_date: models.DateField = models.DateField(
        _("Graduation Date"),
        blank=True,
        null=True,
        help_text=_("Date when students graduated (from CSV data)"),
    )
    is_graduated: models.BooleanField = models.BooleanField(
        _("Is Graduated"),
        default=False,
        help_text=_("Whether the students in this group have graduated"),
    )

    # Administrative
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Administrative notes about the project"),
    )

    class Meta:
        verbose_name = _("Senior Project Group")
        verbose_name_plural = _("Senior Project Groups")
        ordering = ["-created_at"]
        unique_together = [["course", "term", "project_title"]]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["course", "term"]),
            models.Index(fields=["status"]),
            models.Index(fields=["advisor"]),
        ]

    def __str__(self) -> str:
        return f"{self.course.code} - {self.project_title} ({self.get_group_size()} students)"

    @property
    def group_size(self) -> int:
        """Get the number of students in this project group."""
        return self.students.count()

    def get_group_size(self) -> int:
        """Get the number of students in this project group (for admin display)."""
        return self.students.count()

    @property
    def pricing_tier_code(self) -> str | None:
        """Get the appropriate pricing tier code based on group size."""
        size = self.group_size
        if size <= 2:
            return "SENIOR_1_2"
        if size <= 5:
            return "SENIOR_3_5"
        return None  # Invalid group size

    def clean(self) -> None:
        """Validate senior project group data."""
        super().clean()

        # Validate that the course is actually a senior project
        if self.course and not getattr(self.course, "is_senior_project", False):
            raise ValidationError({"course": _("Selected course must be marked as a senior project.")})

        # Auto-determine registration term from registration date
        if self.registration_date and not self.registration_term:
            from apps.curriculum.models import Term

            matching_terms = Term.objects.filter(
                start_date__lte=self.registration_date, end_date__gte=self.registration_date
            )
            if matching_terms.exists():
                self.registration_term = matching_terms.first()

    def add_student(self, student) -> bool:
        """Add a student to the project group if within size limits."""
        if self.group_size >= 5:
            return False
        self.students.add(student)
        return True

    def remove_student(self, student) -> bool:
        """Remove a student from the project group."""
        if self.group_size <= 1:
            return False  # Must have at least one student
        self.students.remove(student)
        return True

    def approve_project(self, approved_by=None) -> None:
        """Mark project as approved and set approval date."""
        if self.status == self.ProjectStatus.PROPOSED:
            self.status = self.ProjectStatus.APPROVED
            self.approval_date = timezone.now().date()
            self.save(update_fields=["status", "approval_date"])

    def submit_project(self) -> None:
        """Mark project as submitted and set submission date."""
        if self.status == self.ProjectStatus.IN_PROGRESS:
            self.status = self.ProjectStatus.SUBMITTED
            self.submission_date = timezone.now().date()
            self.save(update_fields=["status", "submission_date"])

    def complete_project(self) -> None:
        """Mark project as completed and set completion date."""
        if self.status in [self.ProjectStatus.DEFENDED, self.ProjectStatus.SUBMITTED]:
            self.status = self.ProjectStatus.COMPLETED
            self.completion_date = timezone.now().date()
            self.save(update_fields=["status", "completion_date"])


# Import progression models


class StudentCycleStatus(AuditModel):
    """Tracks students who have changed academic cycles or are new.

    This model identifies and tracks students who have transitioned between
    academic levels (Language→Bachelor, Bachelor→Master) or are new students.
    These students are subject to administrative fees every term until graduation.

    The status remains active throughout their enrollment in the target program
    and is deactivated upon graduation or withdrawal.
    """

    class CycleChangeType(models.TextChoices):
        """Types of cycle changes that trigger administrative fees."""

        NEW_STUDENT = "NEW", _("New Student")
        LANG_TO_BA = "L2B", _("Language to Bachelor")
        BA_TO_MA = "B2M", _("Bachelor to Master")

    student: models.ForeignKey = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.PROTECT,
        related_name="cycle_statuses",
        verbose_name=_("Student"),
        help_text=_("Student with cycle change status"),
    )
    cycle_type: models.CharField = models.CharField(
        _("Cycle Type"), max_length=3, choices=CycleChangeType.choices, help_text=_("Type of cycle change")
    )
    detected_date: models.DateField = models.DateField(
        _("Detected Date"), help_text=_("Date when cycle change was detected")
    )
    source_program: models.ForeignKey = models.ForeignKey(
        "curriculum.Major",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cycle_departures",
        verbose_name=_("Source Program"),
        help_text=_("Program student was in before change (null for new students)"),
    )
    target_program: models.ForeignKey = models.ForeignKey(
        "curriculum.Major",
        on_delete=models.PROTECT,
        related_name="cycle_arrivals",
        verbose_name=_("Target Program"),
        help_text=_("Program student changed to"),
    )
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"), default=True, help_text=_("Active until student graduates from target program")
    )
    deactivated_date: models.DateField = models.DateField(
        _("Deactivated Date"),
        null=True,
        blank=True,
        help_text=_("Date when status was deactivated (graduation/withdrawal)"),
    )
    deactivation_reason: models.CharField = models.CharField(
        _("Deactivation Reason"),
        max_length=50,
        blank=True,
        choices=[
            ("GRADUATED", _("Graduated")),
            ("WITHDRAWN", _("Withdrawn")),
            ("TRANSFERRED", _("Transferred")),
            ("OTHER", _("Other")),
        ],
        help_text=_("Reason for deactivation"),
    )
    notes: models.TextField = models.TextField(
        _("Notes"), blank=True, help_text=_("Additional notes about this cycle change")
    )

    class Meta:
        verbose_name = _("Student Cycle Status")
        verbose_name_plural = _("Student Cycle Statuses")
        db_table = "enrollment_student_cycle_status"
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "is_active"]),
            models.Index(fields=["cycle_type", "is_active"]),
            models.Index(fields=["detected_date"]),
            models.Index(fields=["target_program", "is_active"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "cycle_type", "target_program"], name="unique_student_cycle_program"
            )
        ]

    def __str__(self) -> str:
        return f"{self.student} - {self.get_cycle_type_display()} → {self.target_program}"

    def deactivate(self, reason: str = "GRADUATED") -> None:
        """Deactivate this cycle status with the given reason."""
        self.is_active = False
        self.deactivated_date = timezone.now().date()
        self.deactivation_reason = reason
        self.save(update_fields=["is_active", "deactivated_date", "deactivation_reason"])
