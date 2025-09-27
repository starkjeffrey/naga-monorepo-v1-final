"""Academic Progression Tracking Models

This module implements a comprehensive system for tracking student academic journeys
through language programs, bachelor's degrees, and master's degrees at PUCSR.

Key Features:
- Handles unreliable legacy data with confidence scoring
- Optimized for performance with denormalized views
- Tracks complete student journeys with milestones
- Supports certificate and degree issuance tracking

Models:
- AcademicJourney: Program period tracking (multiple records per student)
- ProgramMilestone: Individual academic events
- AcademicProgression: Denormalized view for fast queries
- CertificateIssuance: Official certificates and degrees
- ProgramPeriod: Detailed program transition tracking
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser
    from django.db.models import ForeignKey

    from apps.curriculum.models import Major, Term

from django.conf import settings
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
    PositiveIntegerField,
    TextField,
)
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import UserAuditModel


class AcademicJourney(UserAuditModel):
    """Tracks each program period in a student's academic journey at PUCSR.

    Multiple records per student - one for each program/major period. Each record
    represents a continuous period in a specific program with transition details.
    """

    class TransitionStatus(models.TextChoices):
        """Status indicating how this program period ended."""

        ACTIVE = "ACTIVE", _("Currently Active")
        GRADUATED = "GRADUATED", _("Graduated")
        CHANGED_PROGRAM = "CHANGED_PROGRAM", _("Changed Program/Major")
        DROPPED_OUT = "DROPPED_OUT", _("Dropped Out")
        SUSPENDED = "SUSPENDED", _("Suspended")
        TRANSFERRED = "TRANSFERRED", _("Transferred Out")
        COMPLETED_LEVEL = "COMPLETED_LEVEL", _("Completed Language Level")
        UNKNOWN = "UNKNOWN", _("Unknown Status")

    class ProgramType(models.TextChoices):
        """Program type for this period."""

        LANGUAGE = "LANGUAGE", _("Language Program")
        BA = "BA", _("Bachelor's Degree")
        MA = "MA", _("Master's Degree")
        PHD = "PHD", _("Doctoral Degree")
        CERTIFICATE = "CERT", _("Certificate Program")

    class DataSource(models.TextChoices):
        """Source of journey data."""

        LEGACY = "LEGACY", _("Imported from Legacy System")
        MANUAL = "MANUAL", _("Manually Entered")
        SYSTEM = "SYSTEM", _("System Generated")
        MIXED = "MIXED", _("Multiple Sources")

    # Core Fields
    student: ForeignKey = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.PROTECT,
        related_name="academic_journeys",
        verbose_name=_("Student"),
        help_text=_("Student whose program period is being tracked"),
    )

    # Program Information
    program_type: CharField = models.CharField(
        _("Program Type"),
        max_length=20,
        choices=ProgramType.choices,
        db_index=True,
        help_text=_("Type of program for this period"),
    )
    program: "ForeignKey[Major | None, Major | None]" = models.ForeignKey(
        "curriculum.Major",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="journey_periods",
        verbose_name=_("Program/Major"),
        help_text=_("Specific program or major for this period"),
    )

    # Period Dates
    start_date: DateField = models.DateField(
        _("Start Date"), null=True, blank=True, db_index=True, help_text=_("Date when this program period started")
    )
    stop_date: DateField = models.DateField(
        _("Stop Date"), null=True, blank=True, help_text=_("Date when this program period ended")
    )
    start_term: "ForeignKey[Term | None, Term | None]" = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="journey_starts",
        verbose_name=_("Start Term"),
        help_text=_("Term when this program period started"),
    )
    term_code: CharField = models.CharField(
        _("Term Code"),
        max_length=20,
        help_text=_("Term code when the change took place"),
    )

    # Duration and Status
    duration_in_terms: PositiveIntegerField = models.PositiveIntegerField(
        _("Duration in Terms"), default=0, help_text=_("Number of terms in this program period")
    )
    transition_status: CharField = models.CharField(
        _("Transition Status"),
        max_length=20,
        choices=TransitionStatus.choices,
        default=TransitionStatus.ACTIVE,
        db_index=True,
        help_text=_("Status indicating how this program period ended"),
    )

    # Data Quality Fields
    data_source: CharField = models.CharField(
        _("Data Source"),
        max_length=20,
        choices=DataSource.choices,
        default=DataSource.SYSTEM,
        help_text=_("Primary source of journey data"),
    )
    confidence_score: DecimalField = models.DecimalField(
        _("Confidence Score"),
        max_digits=3,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("1.00"))],
        help_text=_("Overall confidence in journey data (0.0-1.0)"),
    )
    data_issues: JSONField = models.JSONField(
        _("Data Issues"), default=list, blank=True, help_text=_("List of identified data quality issues")
    )
    requires_review: BooleanField = models.BooleanField(
        _("Requires Review"), default=False, db_index=True, help_text=_("Whether this journey needs manual review")
    )
    last_manual_review: DateTimeField = models.DateTimeField(
        _("Last Manual Review"), null=True, blank=True, help_text=_("When this journey was last manually reviewed")
    )

    # Additional Metadata
    notes: TextField = models.TextField(_("Notes"), blank=True, help_text=_("Administrative notes about this journey"))

    class Meta:
        verbose_name = _("Academic Journey")
        verbose_name_plural = _("Academic Journeys")
        ordering = ["student", "start_date"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "start_date"]),
            models.Index(fields=["transition_status", "program_type"]),
            models.Index(fields=["program", "transition_status"]),
            models.Index(fields=["requires_review", "confidence_score"]),
            models.Index(fields=["data_source", "confidence_score"]),
        ]

    def __str__(self) -> str:
        program_name = self.program.name if self.program else self.program_type
        return f"{self.student} - {program_name} ({self.start_date})"

    @property
    def is_active(self) -> bool:
        """Check if this program period is currently active."""
        return self.transition_status == self.TransitionStatus.ACTIVE

    @property
    def needs_review(self) -> bool:
        """Check if journey needs manual review based on confidence."""
        return self.requires_review or self.confidence_score < Decimal("0.7")

    def add_data_issue(self, issue: str) -> None:
        """Add a data quality issue to the journey."""
        if issue not in self.data_issues:
            self.data_issues.append(issue)
            self.save(update_fields=["data_issues"])

    def mark_reviewed(self, user=None, notes: str = "") -> None:
        """Mark journey as manually reviewed."""
        self.requires_review = False
        self.last_manual_review = timezone.now()
        if notes:
            self.notes = f"{self.notes}\n\n[Review {timezone.now():%Y-%m-%d}] {notes}".strip()
        self.save(update_fields=["requires_review", "last_manual_review", "notes"])


class ProgramMilestone(UserAuditModel):
    """Records key events in a student's academic journey.

    Multiple records per student tracking significant academic events like
    program starts, level completions, major changes, and graduations.
    """

    class MilestoneType(models.TextChoices):
        """Types of academic milestones."""

        # Enrollments
        PROGRAM_START = "PROG_START", _("Program Start")
        LEVEL_ADVANCE = "LEVEL_ADV", _("Level Advancement")
        MAJOR_DECLARE = "MAJOR_DEC", _("Major Declaration")
        MAJOR_CHANGE = "MAJOR_CHG", _("Major Change")

        # Completions
        LEVEL_COMPLETE = "LEVEL_COMP", _("Level Completion")
        PROGRAM_COMPLETE = "PROG_COMP", _("Program Completion")
        DEGREE_EARNED = "DEGREE", _("Degree Earned")
        CERTIFICATE_EARNED = "CERT", _("Certificate Earned")

        # Exits
        WITHDRAWAL = "WITHDRAW", _("Withdrawal")
        DISMISSAL = "DISMISS", _("Academic Dismissal")
        LEAVE_OF_ABSENCE = "LOA", _("Leave of Absence")
        TRANSFER = "TRANSFER", _("Transfer")

        # Other
        READMISSION = "READMIT", _("Readmission")
        STATUS_CHANGE = "STATUS", _("Status Change")

    # Core Fields
    journey: ForeignKey = models.ForeignKey(
        AcademicJourney,
        on_delete=models.CASCADE,
        related_name="milestones",
        verbose_name=_("Academic Journey"),
        help_text=_("Parent journey record"),
    )
    milestone_type: CharField = models.CharField(
        _("Milestone Type"),
        max_length=20,
        choices=MilestoneType.choices,
        db_index=True,
        help_text=_("Type of academic milestone"),
    )
    milestone_date: DateField = models.DateField(
        _("Milestone Date"), db_index=True, help_text=_("Date when milestone occurred")
    )
    academic_term: "ForeignKey[Term | None, Term | None]" = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="program_milestones",
        verbose_name=_("Academic Term"),
        help_text=_("Term when milestone occurred"),
    )

    # Context Fields
    program: "ForeignKey[Major | None, Major | None]" = models.ForeignKey(
        "curriculum.Major",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="milestones",
        verbose_name=_("Program"),
        help_text=_("Program associated with milestone"),
    )
    from_program: "ForeignKey[Major | None, Major | None]" = models.ForeignKey(
        "curriculum.Major",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="transitions_from_milestones",
        verbose_name=_("From Program"),
        help_text=_("Previous program (for changes/transitions)"),
    )
    level: CharField = models.CharField(
        _("Level"), max_length=10, blank=True, help_text=_("Level for language programs")
    )

    # Data Quality Fields
    is_inferred: BooleanField = models.BooleanField(
        _("Is Inferred"), default=False, help_text=_("Whether milestone was deduced from enrollment data")
    )
    confidence_score: DecimalField = models.DecimalField(
        _("Confidence Score"),
        max_digits=3,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("1.00"))],
        help_text=_("Confidence in milestone accuracy (0.0-1.0)"),
    )
    inference_method: CharField = models.CharField(
        _("Inference Method"), max_length=50, blank=True, help_text=_("Method used to infer milestone")
    )

    # Metadata
    recorded_by: "ForeignKey[AbstractUser | None, AbstractUser | None]" = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="recorded_milestones",
        verbose_name=_("Recorded By"),
        help_text=_("User who recorded milestone"),
    )
    notes: TextField = models.TextField(_("Notes"), blank=True, help_text=_("Additional notes about milestone"))

    class Meta:
        verbose_name = _("Program Milestone")
        verbose_name_plural = _("Program Milestones")
        ordering = ["journey", "milestone_date"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["journey", "milestone_date"]),
            models.Index(fields=["milestone_type", "milestone_date"]),
            models.Index(fields=["program", "milestone_type"]),
            models.Index(fields=["is_inferred", "confidence_score"]),
        ]

    def __str__(self) -> str:
        return f"{self.journey.student} - {self.get_milestone_type_display()} ({self.milestone_date})"  # type: ignore[attr-defined]

    @property
    def is_completion(self) -> bool:
        """Check if this is a completion milestone."""
        return self.milestone_type in [
            self.MilestoneType.LEVEL_COMPLETE,
            self.MilestoneType.PROGRAM_COMPLETE,
            self.MilestoneType.DEGREE_EARNED,
            self.MilestoneType.CERTIFICATE_EARNED,
        ]

    @property
    def is_exit(self) -> bool:
        """Check if this is an exit milestone."""
        return self.milestone_type in [
            self.MilestoneType.WITHDRAWAL,
            self.MilestoneType.DISMISSAL,
            self.MilestoneType.TRANSFER,
        ]


class AcademicProgression(models.Model):
    """Denormalized view for high-performance queries and reporting.

    This model provides a flattened view of student progression data,
    optimized for fast queries and dashboard displays. Updated via
    triggers or periodic tasks from the source journey and milestone data.
    """

    # Student Reference
    student: models.OneToOneField = models.OneToOneField(
        "people.StudentProfile",
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="progression_summary",
        verbose_name=_("Student"),
    )
    student_name: models.CharField = models.CharField(
        _("Student Name"), max_length=200, help_text=_("Denormalized student full name")
    )
    student_id_number: models.CharField = models.CharField(
        _("Student ID"), max_length=20, db_index=True, help_text=_("Denormalized student ID number")
    )

    # Program Journey Summary
    entry_program: models.CharField = models.CharField(
        _("Entry Program"), max_length=50, help_text=_("First program enrolled in")
    )
    entry_date: models.DateField = models.DateField(
        _("Entry Date"), db_index=True, help_text=_("Date of first enrollment")
    )
    entry_term: models.CharField = models.CharField(
        _("Entry Term"), max_length=20, help_text=_("Term code of first enrollment")
    )

    # Language Program Summary
    language_start_date: models.DateField = models.DateField(
        _("Language Start Date"), null=True, blank=True, help_text=_("Start date of language program")
    )
    language_end_date: models.DateField = models.DateField(
        _("Language End Date"), null=True, blank=True, help_text=_("End date of language program")
    )
    language_terms: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Language Terms"), default=0, help_text=_("Number of terms in language programs")
    )
    language_final_level: models.CharField = models.CharField(
        _("Language Final Level"), max_length=20, blank=True, help_text=_("Final level achieved in language program")
    )
    language_completion_status: models.CharField = models.CharField(
        _("Language Completion Status"),
        max_length=20,
        blank=True,
        db_index=True,
        help_text=_("COMPLETED, BYPASSED, DROPPED, etc."),
    )

    # BA Program Summary
    ba_start_date: models.DateField = models.DateField(
        _("BA Start Date"), null=True, blank=True, help_text=_("Start date of BA program")
    )
    ba_major: models.CharField = models.CharField(
        _("BA Major"), max_length=100, blank=True, db_index=True, help_text=_("Bachelor's degree major")
    )
    ba_major_changes: models.PositiveIntegerField = models.PositiveIntegerField(
        _("BA Major Changes"), default=0, help_text=_("Number of major changes during BA")
    )
    ba_terms: models.PositiveIntegerField = models.PositiveIntegerField(
        _("BA Terms"), default=0, help_text=_("Number of terms enrolled in BA")
    )
    ba_credits: models.DecimalField = models.DecimalField(
        _("BA Credits"), max_digits=6, decimal_places=2, default=0, help_text=_("Total credits earned in BA")
    )
    ba_gpa: models.DecimalField = models.DecimalField(
        _("BA GPA"), max_digits=3, decimal_places=2, null=True, blank=True, help_text=_("Final BA GPA")
    )
    ba_completion_date: models.DateField = models.DateField(
        _("BA Completion Date"), null=True, blank=True, help_text=_("BA graduation date")
    )
    ba_completion_status: models.CharField = models.CharField(
        _("BA Completion Status"),
        max_length=20,
        blank=True,
        db_index=True,
        help_text=_("GRADUATED, DROPPED, ACTIVE, etc."),
    )

    # MA Program Summary
    ma_start_date: models.DateField = models.DateField(
        _("MA Start Date"), null=True, blank=True, help_text=_("Start date of MA program")
    )
    ma_program: models.CharField = models.CharField(
        _("MA Program"), max_length=100, blank=True, db_index=True, help_text=_("Master's degree program")
    )
    ma_terms: models.PositiveIntegerField = models.PositiveIntegerField(
        _("MA Terms"), default=0, help_text=_("Number of terms enrolled in MA")
    )
    ma_credits: models.DecimalField = models.DecimalField(
        _("MA Credits"), max_digits=6, decimal_places=2, default=0, help_text=_("Total credits earned in MA")
    )
    ma_gpa: models.DecimalField = models.DecimalField(
        _("MA GPA"), max_digits=3, decimal_places=2, null=True, blank=True, help_text=_("Final MA GPA")
    )
    ma_completion_date: models.DateField = models.DateField(
        _("MA Completion Date"), null=True, blank=True, help_text=_("MA graduation date")
    )
    ma_completion_status: models.CharField = models.CharField(
        _("MA Completion Status"),
        max_length=20,
        blank=True,
        db_index=True,
        help_text=_("GRADUATED, DROPPED, ACTIVE, etc."),
    )

    # Overall Journey Metrics
    total_terms: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Total Terms"), default=0, help_text=_("Total terms enrolled across all programs")
    )
    total_gap_terms: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Total Gap Terms"), default=0, help_text=_("Number of terms with no enrollment")
    )
    time_to_ba_days: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Time to BA (Days)"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Days from first enrollment to BA graduation"),
    )
    time_to_ma_days: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Time to MA (Days)"),
        null=True,
        blank=True,
        db_index=True,
        help_text=_("Days from BA graduation to MA graduation"),
    )

    # Current Status
    current_status: models.CharField = models.CharField(
        _("Current Status"), max_length=50, db_index=True, help_text=_("Current enrollment status")
    )
    last_enrollment_term: models.CharField = models.CharField(
        _("Last Enrollment Term"), max_length=20, help_text=_("Most recent term with enrollment")
    )
    last_updated: models.DateTimeField = models.DateTimeField(
        _("Last Updated"), auto_now=True, help_text=_("When this summary was last updated")
    )

    class Meta:
        verbose_name = _("Academic Progression")
        verbose_name_plural = _("Academic Progressions")
        ordering = ["-last_updated"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["current_status", "entry_program"]),
            models.Index(fields=["ba_major", "ba_completion_status"]),
            models.Index(fields=["ma_program", "ma_completion_status"]),
            models.Index(fields=["time_to_ba_days"]),
            models.Index(fields=["time_to_ma_days"]),
            models.Index(fields=["language_completion_status", "language_final_level"]),
        ]

    def __str__(self) -> str:
        return f"{self.student_name} ({self.student_id_number}) - {self.current_status}"

    @property
    def has_language_program(self) -> bool:
        """Check if student went through language program."""
        return self.language_start_date is not None

    @property
    def has_ba_degree(self) -> bool:
        """Check if student has BA degree."""
        return self.ba_completion_status == "GRADUATED"

    @property
    def has_ma_degree(self) -> bool:
        """Check if student has MA degree."""
        return self.ma_completion_status == "GRADUATED"


class ProgramPeriod(UserAuditModel):
    """Records each distinct program period in a student's journey.

    This model captures every period a student spends in a program,
    including transitions between language programs (IEAP/GESL/EHSS),
    progression to BA/MA, and any returns to previous programs.
    """

    class TransitionType(models.TextChoices):
        """Type of program transition."""

        INITIAL = "INITIAL", _("Initial Enrollment")
        PROGRESSION = "PROGRESSION", _("Natural Progression")
        CHANGE = "CHANGE", _("Program Change")
        RETURN = "RETURN", _("Return to Previous Program")
        CONTINUATION = "CONTINUATION", _("Continuation in Same Program")
        GAP = "GAP", _("Gap Period")

    class ProgramType(models.TextChoices):
        """Program types for tracking."""

        IEAP = "IEAP", _("Intensive English for Academic Purposes")
        GESL = "GESL", _("General English as a Second Language")
        EHSS = "EHSS", _("English for High School Students")
        LANGUAGE_OTHER = "LANG_OTHER", _("Other Language Program")
        BA = "BA", _("Bachelor of Arts")
        MA = "MA", _("Master of Arts")
        PHD = "PHD", _("Doctoral Program")
        CERTIFICATE = "CERT", _("Certificate Program")

    class CompletionStatus(models.TextChoices):
        """Status at end of this program period."""

        ACTIVE = "ACTIVE", _("Currently Active")
        COMPLETED = "COMPLETED", _("Completed Successfully")
        GRADUATED = "GRADUATED", _("Graduated with Degree")
        DROPPED = "DROPPED", _("Dropped Out")
        INACTIVE = "INACTIVE", _("Inactive")
        TRANSFERRED = "TRANSFERRED", _("Transferred")

    # Core Fields
    journey: models.ForeignKey = models.ForeignKey(
        AcademicJourney,
        on_delete=models.CASCADE,
        related_name="program_periods",
        verbose_name=_("Academic Journey"),
        help_text=_("Parent journey record"),
    )

    # Transition Details
    transition_type: models.CharField = models.CharField(
        _("Transition Type"),
        max_length=20,
        choices=TransitionType.choices,
        help_text=_("Type of transition"),
    )
    transition_date: models.DateField = models.DateField(
        _("Transition Date"),
        db_index=True,
        help_text=_("Date when this program period started"),
    )

    # Program Information
    from_program_type: models.CharField = models.CharField(
        _("From Program Type"),
        max_length=20,
        choices=ProgramType.choices,
        null=True,
        blank=True,
        help_text=_("Previous program type"),
    )
    to_program_type: models.CharField = models.CharField(
        _("To Program Type"),
        max_length=20,
        choices=ProgramType.choices,
        help_text=_("New program type"),
    )
    to_program: "ForeignKey[Major | None, Major | None]" = models.ForeignKey(
        "curriculum.Major",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="program_periods",
        verbose_name=_("Program/Major"),
        help_text=_("Specific program or major (for BA/MA)"),
    )
    program_name: models.CharField = models.CharField(
        _("Program Name"),
        max_length=200,
        help_text=_("Full program name for display"),
    )

    # Duration and Metrics
    duration_days: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Duration (Days)"),
        help_text=_("Days spent in this program period"),
    )
    duration_months: models.DecimalField = models.DecimalField(
        _("Duration (Months)"),
        max_digits=5,
        decimal_places=1,
        help_text=_("Months spent in this program period"),
    )
    term_count: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Term Count"),
        default=0,
        help_text=_("Number of terms enrolled in this period"),
    )

    # Academic Performance
    total_credits: models.DecimalField = models.DecimalField(
        _("Total Credits"),
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text=_("Total credits attempted in this period"),
    )
    completed_credits: models.DecimalField = models.DecimalField(
        _("Completed Credits"),
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text=_("Credits successfully completed"),
    )
    gpa: models.DecimalField = models.DecimalField(
        _("GPA"),
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("4.00"))],
        help_text=_("GPA for this period"),
    )

    # Completion Details
    completion_status: models.CharField = models.CharField(
        _("Completion Status"),
        max_length=20,
        choices=CompletionStatus.choices,
        help_text=_("Status at end of this period"),
    )
    language_level: models.CharField = models.CharField(
        _("Language Level"),
        max_length=10,
        blank=True,
        help_text=_("Final level achieved (for language programs)"),
    )

    # Sequencing
    sequence_number: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Sequence Number"),
        help_text=_("Order in student's journey (1-based)"),
    )

    # Data Quality
    confidence_score: models.DecimalField = models.DecimalField(
        _("Confidence Score"),
        max_digits=3,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("1.00"))],
        help_text=_("Confidence in transition data (0.0-1.0)"),
    )

    # Metadata
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this transition"),
    )

    class Meta:
        verbose_name = _("Program Period")
        verbose_name_plural = _("Program Periods")
        ordering = ["journey", "sequence_number"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["journey", "sequence_number"]),
            models.Index(fields=["transition_date", "to_program_type"]),
            models.Index(fields=["completion_status", "to_program_type"]),
        ]
        unique_together = [["journey", "sequence_number"]]

    def __str__(self) -> str:
        return f"{self.journey.student} - {self.program_name} ({self.transition_date})"  # type: ignore[attr-defined]

    @property
    def duration_years(self) -> float:
        """Get duration in years."""
        return self.duration_days / 365.25

    @property
    def is_language_program(self) -> bool:
        """Check if this is a language program."""
        return self.to_program_type in ["IEAP", "GESL", "EHSS", "LANG_OTHER"]

    @property
    def is_degree_program(self) -> bool:
        """Check if this is a degree program."""
        return self.to_program_type in ["BA", "MA", "PHD"]


class CertificateIssuance(UserAuditModel):
    """Official record of all certificates and degrees issued.

    Tracks the issuance of academic credentials including language certificates,
    degrees, transcripts, and other official documents.
    """

    class CertificateType(models.TextChoices):
        """Types of certificates that can be issued."""

        # Language Certificates
        IEAP_CERT = "IEAP", _("IEAP Completion Certificate")
        GESL_CERT = "GESL", _("GESL Completion Certificate")
        EHSS_CERT = "EHSS", _("EHSS Completion Certificate")

        # Degrees
        BA_DEGREE = "BA", _("Bachelor of Arts")
        MA_DEGREE = "MA", _("Master of Arts")
        PHD_DEGREE = "PHD", _("Doctor of Philosophy")

        # Other Documents
        TRANSCRIPT = "TRANS", _("Official Transcript")
        LETTER = "LETTER", _("Completion Letter")
        CERTIFICATE = "CERT", _("General Certificate")

    # Core Fields
    student: models.ForeignKey = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.PROTECT,
        related_name="certificates_issued",
        verbose_name=_("Student"),
        help_text=_("Student receiving certificate"),
    )
    certificate_type: models.CharField = models.CharField(
        _("Certificate Type"),
        max_length=20,
        choices=CertificateType.choices,
        db_index=True,
        help_text=_("Type of certificate issued"),
    )
    issue_date: models.DateField = models.DateField(
        _("Issue Date"), db_index=True, help_text=_("Date certificate was issued")
    )

    # Program Details
    program: "ForeignKey[Major | None, Major | None]" = models.ForeignKey(
        "curriculum.Major",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="certificates",
        verbose_name=_("Program"),
        help_text=_("Academic program for degree/certificate"),
    )
    completion_level: models.CharField = models.CharField(
        _("Completion Level"), max_length=20, blank=True, help_text=_("Level completed (for language programs)")
    )
    gpa: models.DecimalField = models.DecimalField(
        _("GPA"),
        max_digits=3,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00")), MaxValueValidator(Decimal("4.00"))],
        help_text=_("GPA at time of graduation"),
    )
    honors: models.CharField = models.CharField(
        _("Honors"), max_length=50, blank=True, help_text=_("Academic honors (e.g., Magna Cum Laude)")
    )

    # Document Tracking
    certificate_number: models.CharField = models.CharField(
        _("Certificate Number"), max_length=50, unique=True, help_text=_("Unique certificate identifier")
    )
    issued_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="certificates_issued_by",
        verbose_name=_("Issued By"),
        help_text=_("Staff member who issued certificate"),
    )
    printed_date: models.DateField = models.DateField(
        _("Printed Date"), null=True, blank=True, help_text=_("Date certificate was printed")
    )
    collected_date: models.DateField = models.DateField(
        _("Collected Date"), null=True, blank=True, help_text=_("Date certificate was collected by student")
    )
    collected_by: models.CharField = models.CharField(
        _("Collected By"), max_length=100, blank=True, help_text=_("Person who collected certificate")
    )

    # Additional Information
    notes: models.TextField = models.TextField(_("Notes"), blank=True, help_text=_("Additional notes about issuance"))

    class Meta:
        verbose_name = _("Certificate Issuance")
        verbose_name_plural = _("Certificate Issuances")
        ordering = ["-issue_date", "student"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "certificate_type"]),
            models.Index(fields=["issue_date", "certificate_type"]),
            models.Index(fields=["certificate_number"]),
            models.Index(fields=["program", "certificate_type"]),
        ]

    def __str__(self) -> str:
        display = getattr(self, "get_certificate_type_display", lambda: str(self.certificate_type))()
        return f"{self.student} - {display} ({self.certificate_number})"

    @property
    def is_degree(self) -> bool:
        """Check if this is a degree certificate."""
        return self.certificate_type in [
            self.CertificateType.BA_DEGREE,
            self.CertificateType.MA_DEGREE,
            self.CertificateType.PHD_DEGREE,
        ]

    @property
    def is_collected(self) -> bool:
        """Check if certificate has been collected."""
        return self.collected_date is not None

    def mark_collected(self, collected_by: str = "", date: date | None = None) -> None:
        """Mark certificate as collected."""
        self.collected_date = date or timezone.now().date()
        self.collected_by = collected_by or "Student"
        self.save(update_fields=["collected_date", "collected_by"])
