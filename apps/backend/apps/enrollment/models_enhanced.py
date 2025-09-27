"""Enhanced ProgramEnrollment model design for tracking student program journeys.

This file shows the proposed enhancements to the existing ProgramEnrollment model
to better track student transitions, completion status, and program analytics.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class EnhancedProgramEnrollmentFields:
    """Additional fields to add to the existing ProgramEnrollment model.

    These fields enable comprehensive tracking of student program journeys,
    including division/cycle classification, credit progress, and exit reasons.
    """

    class Division(models.TextChoices):
        """Academic division classification."""

        LANGUAGE = "LANG", _("Language Programs")
        ACADEMIC = "ACAD", _("Academic Programs")
        PREPARATORY = "PREP", _("Preparatory Programs")
        PROFESSIONAL = "PROF", _("Professional Development")

    class Cycle(models.TextChoices):
        """Academic cycle/level."""

        HIGH_SCHOOL = "HS", _("High School (EHSS)")
        CERTIFICATE = "CERT", _("Certificate Program")
        PREPARATORY = "PREP", _("Preparatory (IEAP/Foundation)")
        BACHELOR = "BA", _("Bachelor's Degree")
        MASTER = "MA", _("Master's Degree")
        DOCTORAL = "PHD", _("Doctoral Degree")

    class ExitReason(models.TextChoices):
        """Reasons for program exit."""

        GRADUATED = "GRAD", _("Graduated")
        COMPLETED_NO_CEREMONY = "COMP", _("Completed without Graduation")
        TRANSFERRED_INTERNAL = "TRAN_INT", _("Transferred to Another Program")
        TRANSFERRED_EXTERNAL = "TRAN_EXT", _("Transferred to Another Institution")
        ACADEMIC_DISMISSAL = "DISM", _("Academic Dismissal")
        FINANCIAL = "FIN", _("Financial Reasons")
        PERSONAL = "PERS", _("Personal Reasons")
        MEDICAL = "MED", _("Medical Leave")
        VISA = "VISA", _("Visa/Immigration Issues")
        NO_SHOW = "NS", _("Never Attended")
        UNKNOWN = "UNK", _("Unknown/Not Specified")

    # Division and Cycle Classification
    division: models.CharField = models.CharField(
        _("Division"),
        max_length=10,
        choices=Division.choices,
        db_index=True,
        help_text=_("Academic division (Language/Academic/etc)"),
    )

    cycle: models.CharField = models.CharField(
        _("Cycle"),
        max_length=10,
        choices=Cycle.choices,
        db_index=True,
        help_text=_("Academic cycle or degree level"),
    )

    # Credit Tracking
    credits_earned: models.DecimalField = models.DecimalField(
        _("Credits Earned"),
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text=_("Total credits earned in this program"),
    )

    credits_required: models.DecimalField = models.DecimalField(
        _("Credits Required"),
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Total credits required for program completion"),
    )

    gpa_at_exit: models.DecimalField = models.DecimalField(
        _("GPA at Exit"),
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Cumulative GPA when leaving the program"),
    )

    # Program Journey Tracking
    exit_reason: models.CharField = models.CharField(
        _("Exit Reason"),
        max_length=15,
        choices=ExitReason.choices,
        blank=True,
        db_index=True,
        help_text=_("Reason for leaving the program"),
    )

    is_deduced: models.BooleanField = models.BooleanField(
        _("Major Deduced"),
        default=False,
        help_text=_("Whether major was deduced from course enrollment patterns"),
    )

    deduction_confidence: models.DecimalField = models.DecimalField(
        _("Deduction Confidence"),
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Confidence score (0-1) for deduced major"),
    )

    # Completion Tracking
    completion_percentage: models.DecimalField = models.DecimalField(
        _("Completion Percentage"),
        max_digits=5,
        decimal_places=2,
        default=0,
        help_text=_("Percentage of program requirements completed"),
    )

    expected_completion_date: models.DateField = models.DateField(
        _("Expected Completion"),
        null=True,
        blank=True,
        help_text=_("Originally expected completion date"),
    )

    # Analytics Support
    time_to_completion: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Time to Completion"),
        null=True,
        blank=True,
        help_text=_("Days from start to completion/exit"),
    )

    enrollment_gaps = models.JSONField(
        _("Enrollment Gaps"),
        default=list,
        blank=True,
        help_text=_("List of terms with no enrollment"),
    )

    # Section tracking (from legacy data)
    legacy_section_code: models.CharField = models.CharField(
        _("Legacy Section Code"),
        max_length=10,
        blank=True,
        db_index=True,
        help_text=_("Section code from legacy system (87=BA, 147=MA, etc)"),
    )


class ProgramTransition(models.Model):
    """Track transitions between programs for journey analysis.

    This model captures when students move from one program to another,
    enabling analysis of common pathways and transition patterns.
    """

    class TransitionType(models.TextChoices):
        """Types of program transitions."""

        PROGRESSION = "PROG", _("Natural Progression (e.g., IEAP to BA)")
        MAJOR_CHANGE = "MAJOR", _("Change of Major")
        LEVEL_CHANGE = "LEVEL", _("Level Change (e.g., BA to MA)")
        LATERAL = "LAT", _("Lateral Move (e.g., between language programs)")
        RESTART = "RESTART", _("Program Restart")

    from_enrollment: models.ForeignKey = models.ForeignKey(
        "ProgramEnrollment",
        on_delete=models.CASCADE,
        related_name="transitions_from",
        verbose_name=_("From Program"),
    )

    to_enrollment: models.ForeignKey = models.ForeignKey(
        "ProgramEnrollment",
        on_delete=models.CASCADE,
        related_name="transitions_to",
        verbose_name=_("To Program"),
    )

    transition_date: models.DateField = models.DateField(_("Transition Date"), db_index=True)

    transition_term: models.ForeignKey = models.ForeignKey(
        "curriculum.Term", on_delete=models.PROTECT, null=True, blank=True
    )

    transition_type: models.CharField = models.CharField(
        _("Transition Type"), max_length=10, choices=TransitionType.choices
    )

    transition_reason: models.TextField = models.TextField(_("Transition Reason"), blank=True)

    credits_transferred: models.DecimalField = models.DecimalField(
        _("Credits Transferred"), max_digits=6, decimal_places=2, default=0
    )

    gap_days: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Gap Days"), default=0, help_text=_("Days between programs")
    )

    class Meta:
        verbose_name = _("Program Transition")
        verbose_name_plural = _("Program Transitions")
        ordering = ["from_enrollment__student", "transition_date"]
        indexes = [
            models.Index(fields=["transition_date"]),
            models.Index(fields=["transition_type"]),
        ]


class StudentProgramJourney(models.Model):
    """Aggregate model for analyzing complete student journeys.

    This model provides a high-level view of a student's entire academic
    journey, useful for analytics and reporting.
    """

    class JourneyType(models.TextChoices):
        """Types of student journeys."""

        LINEAR = "LINEAR", _("Linear Progression")
        INTERRUPTED = "INT", _("Interrupted/Returning")
        COMPLEX = "COMP", _("Complex/Multiple Changes")
        INCOMPLETE = "INC", _("Incomplete/Dropped")

    student: models.OneToOneField = models.OneToOneField(
        "people.StudentProfile",
        on_delete=models.CASCADE,
        related_name="program_journey",
    )

    journey_type: models.CharField = models.CharField(_("Journey Type"), max_length=10, choices=JourneyType.choices)

    first_enrollment_date: models.DateField = models.DateField()
    last_activity_date: models.DateField = models.DateField()

    total_programs: models.PositiveIntegerField = models.PositiveIntegerField(default=0)
    completed_programs: models.PositiveIntegerField = models.PositiveIntegerField(default=0)

    total_credits_earned: models.DecimalField = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    overall_gpa: models.DecimalField = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)

    has_graduated: models.BooleanField = models.BooleanField(default=False)
    graduation_date: models.DateField = models.DateField(null=True, blank=True)

    journey_summary = models.JSONField(default=dict, help_text=_("Structured summary of program transitions"))

    risk_score: models.DecimalField = models.DecimalField(
        _("Risk Score"),
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Dropout risk score (0-1)"),
    )

    last_calculated: models.DateTimeField = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Student Program Journey")
        verbose_name_plural = _("Student Program Journeys")
        ordering = ["student"]
