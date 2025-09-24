"""Language app models for language program specific functionality.

This module contains models specific to language program management including
level progression, term preparation, and auto-promotion tracking.

All models follow clean architecture principles with minimal dependencies.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import AuditModel


class LanguageProgramPromotion(AuditModel):
    """Tracks automatic promotion activities for language programs.

    Records bulk promotion events where students are automatically advanced
    to the next level and classes are cloned for new terms.

    Key features:
    - Tracks promotion events by term and program
    - Records which students were promoted
    - Links to cloned classes
    - Audit trail for term preparation activities
    """

    class PromotionStatus(models.TextChoices):
        """Status of promotion process."""

        INITIATED = "INITIATED", _("Promotion Initiated")
        IN_PROGRESS = "IN_PROGRESS", _("In Progress")
        COMPLETED = "COMPLETED", _("Completed")
        FAILED = "FAILED", _("Failed")

    # Term and program information
    source_term: models.ForeignKey = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.PROTECT,
        related_name="language_promotions_from",
        verbose_name=_("Source Term"),
        help_text=_("Term from which students are being promoted"),
    )
    target_term: models.ForeignKey = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.PROTECT,
        related_name="language_promotions_to",
        verbose_name=_("Target Term"),
        help_text=_("Term to which students are being promoted"),
    )
    program: models.CharField = models.CharField(
        _("Language Program"),
        max_length=20,
        help_text=_("Language program being promoted (EHSS, GESL, etc.)"),
    )

    # Promotion details
    status: models.CharField = models.CharField(
        _("Promotion Status"),
        max_length=20,
        choices=PromotionStatus.choices,
        default=PromotionStatus.INITIATED,
        help_text=_("Current status of the promotion process"),
    )
    students_promoted_count: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Students Promoted Count"),
        default=0,
        help_text=_("Number of students successfully promoted"),
    )
    classes_cloned_count: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Classes Cloned Count"),
        default=0,
        help_text=_("Number of classes cloned for the new term"),
    )

    # Administrative details
    initiated_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="language_promotions_initiated",
        verbose_name=_("Initiated By"),
        help_text=_("Staff member who initiated the promotion"),
    )
    initiated_at: models.DateTimeField = models.DateTimeField(
        _("Initiated At"),
        default=timezone.now,
        help_text=_("When the promotion was initiated"),
    )
    completed_at: models.DateTimeField = models.DateTimeField(
        _("Completed At"),
        null=True,
        blank=True,
        help_text=_("When the promotion was completed"),
    )
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Notes about this promotion process"),
    )

    class Meta:
        verbose_name = _("Language Program Promotion")
        verbose_name_plural = _("Language Program Promotions")
        ordering = ["-initiated_at"]
        unique_together = [["source_term", "target_term", "program"]]
        indexes = [
            models.Index(fields=["program", "status"]),
            models.Index(fields=["source_term", "target_term"]),
            models.Index(fields=["initiated_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.program} promotion: {self.source_term} → {self.target_term}"

    def mark_completed(self, students_count: int = 0, classes_count: int = 0) -> None:
        """Mark the promotion as completed with counts."""
        self.status = self.PromotionStatus.COMPLETED
        self.completed_at = timezone.now()
        self.students_promoted_count = students_count
        self.classes_cloned_count = classes_count
        self.save(
            update_fields=[
                "status",
                "completed_at",
                "students_promoted_count",
                "classes_cloned_count",
            ]
        )

    def mark_failed(self, reason: str = "") -> None:
        """Mark the promotion as failed with optional reason."""
        self.status = self.PromotionStatus.FAILED
        if reason:
            self.notes = f"{self.notes}\n\nFailed: {reason}".strip()
        self.save(update_fields=["status", "notes"])

    def is_completed(self) -> bool:
        """Check if the promotion is completed."""
        return self.status == self.PromotionStatus.COMPLETED

    def is_in_progress(self) -> bool:
        """Check if the promotion is in progress."""
        return self.status == self.PromotionStatus.IN_PROGRESS

    def get_success_rate(self) -> float:
        """Calculate the success rate of the promotion."""
        total_students = self.student_promotions.count()  # type: ignore[attr-defined]
        if total_students == 0:
            return 0.0

        successful_promotions = self.student_promotions.filter(  # type: ignore[attr-defined]
            result=LanguageStudentPromotion.PromotionResult.PROMOTED
        ).count()

        return (successful_promotions / total_students) * 100

    def get_duration_days(self) -> int | None:
        """Get the duration of the promotion in days."""
        if self.completed_at:
            return (self.completed_at.date() - self.initiated_at.date()).days
        return None


class LanguageStudentPromotion(AuditModel):
    """Individual student promotion records within a bulk promotion.

    Tracks individual student advancement from one level to the next,
    maintaining audit trail for academic progression.
    """

    class PromotionResult(models.TextChoices):
        """Result of individual student promotion."""

        PROMOTED = "PROMOTED", _("Promoted")
        LEVEL_SKIPPED = "LEVEL_SKIPPED", _("Level Skipped - Advanced Placement")
        FAILED_COURSE = "FAILED_COURSE", _("Failed Course - Not Promoted")
        WITHDRAWN = "WITHDRAWN", _("Withdrawn")
        NO_SHOW = "NO_SHOW", _("No Show")

    promotion_batch: models.ForeignKey = models.ForeignKey(
        LanguageProgramPromotion,
        on_delete=models.CASCADE,
        related_name="student_promotions",
        verbose_name=_("Promotion Batch"),
        help_text=_("Bulk promotion batch this student is part of"),
    )
    student: models.ForeignKey = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.PROTECT,
        related_name="language_promotions",
        verbose_name=_("Student"),
        help_text=_("Student being promoted"),
    )

    # Level progression
    from_level: models.CharField = models.CharField(
        _("From Level"),
        max_length=50,
        help_text=_("Language level the student is being promoted from"),
    )
    to_level = models.CharField(
        _("To Level"),
        max_length=50,
        help_text=_("Language level the student is being promoted to"),
    )

    # Class information
    source_class = models.ForeignKey(
        "scheduling.ClassHeader",
        on_delete=models.PROTECT,
        related_name="language_promotions_from",
        verbose_name=_("Source Class"),
        help_text=_("Class the student was enrolled in"),
    )
    target_class = models.ForeignKey(
        "scheduling.ClassHeader",
        on_delete=models.PROTECT,
        related_name="language_promotions_to",
        null=True,
        blank=True,
        verbose_name=_("Target Class"),
        help_text=_("Class the student was promoted to (if successful)"),
    )

    # Promotion result
    result = models.CharField(
        _("Promotion Result"),
        max_length=20,
        choices=PromotionResult.choices,
        default=PromotionResult.PROMOTED,
        help_text=_("Result of the promotion attempt"),
    )
    final_grade = models.CharField(
        _("Final Grade"),
        max_length=10,
        blank=True,
        help_text=_("Final grade from the source course"),
    )
    notes = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this student's promotion"),
    )

    class Meta:
        verbose_name = _("Language Student Promotion")
        verbose_name_plural = _("Language Student Promotions")
        ordering = ["promotion_batch", "student"]
        unique_together = [["promotion_batch", "student"]]
        indexes = [
            models.Index(fields=["promotion_batch", "result"]),
            models.Index(fields=["student"]),
            models.Index(fields=["from_level", "to_level"]),
        ]

    # Override information
    has_level_skip_override = models.BooleanField(
        _("Has Level Skip Override"),
        default=False,
        help_text=_("Whether this promotion includes level skipping with management override"),
    )
    skip_reason = models.TextField(
        _("Level Skip Reason"),
        blank=True,
        help_text=_("Reason for level skipping (re-test results, misevaluation, etc.)"),
    )
    skip_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_level_skips",
        verbose_name=_("Skip Approved By"),
        help_text=_("Manager who approved the level skip"),
    )

    def __str__(self) -> str:
        skip_indicator = " (SKIP)" if self.has_level_skip_override else ""
        return f"{self.student}: {self.from_level} → {self.to_level} ({self.result}){skip_indicator}"

    def was_promoted(self) -> bool:
        """Check if the student was successfully promoted."""
        return self.result == self.PromotionResult.PROMOTED

    def had_level_skip(self) -> bool:
        """Check if this promotion involved level skipping."""
        return self.result == self.PromotionResult.LEVEL_SKIPPED or self.has_level_skip_override

    def get_levels_advanced(self) -> int:
        """Calculate how many levels the student advanced."""
        try:
            from_num = int(self.from_level.split("-")[-1])
            to_num = int(self.to_level.split("-")[-1])
            return to_num - from_num
        except (ValueError, IndexError):
            return 1  # Default to 1 level advancement


class LanguageLevelSkipRequest(AuditModel):
    """Request for a student to skip one or more language levels.

    Tracks requests for students to advance beyond their normal progression
    due to re-testing, misevaluation, or demonstrated competency. Requires
    management approval and comprehensive audit trail.
    """

    class SkipReason(models.TextChoices):
        """Reasons for level skip requests."""

        RETEST_HIGHER = "RETEST_HIGHER", _("Re-test Shows Higher Level")
        MISEVALUATION = "MISEVALUATION", _("Initial Placement Misevaluation")
        TRANSFER_CREDIT = "TRANSFER_CREDIT", _("Transfer Credit from Other Institution")
        DEMONSTRATED_COMPETENCY = "DEMONSTRATED_COMPETENCY", _("Demonstrated Advanced Competency")
        ACCELERATED_LEARNING = "ACCELERATED_LEARNING", _("Accelerated Learning Progress")
        OTHER = "OTHER", _("Other Reason")

    class RequestStatus(models.TextChoices):
        """Status of skip request."""

        PENDING = "PENDING", _("Pending Review")
        APPROVED = "APPROVED", _("Approved")
        DENIED = "DENIED", _("Denied")
        IMPLEMENTED = "IMPLEMENTED", _("Implemented")

    student = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.PROTECT,
        related_name="level_skip_requests",
        verbose_name=_("Student"),
        help_text=_("Student requesting level skip"),
    )

    # Current and target levels
    current_level = models.CharField(
        _("Current Level"),
        max_length=50,
        help_text=_("Student's current language level"),
    )
    target_level = models.CharField(
        _("Target Level"),
        max_length=50,
        help_text=_("Requested target language level"),
    )
    program = models.CharField(
        _("Language Program"),
        max_length=20,
        help_text=_("Language program (EHSS, GESL, etc.)"),
    )
    levels_skipped = models.PositiveSmallIntegerField(
        _("Levels Skipped"),
        default=1,
        help_text=_("Number of levels being skipped"),
    )

    # Request details
    reason_category = models.CharField(
        _("Reason Category"),
        max_length=30,
        choices=SkipReason.choices,
        help_text=_("Category of reason for level skip"),
    )
    detailed_reason = models.TextField(
        _("Detailed Reason"),
        help_text=_("Detailed explanation for the level skip request"),
    )
    supporting_evidence = models.TextField(
        _("Supporting Evidence"),
        blank=True,
        help_text=_("Supporting evidence (test scores, instructor observations, etc.)"),
    )

    # Request processing
    status = models.CharField(
        _("Request Status"),
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING,
        help_text=_("Current status of the skip request"),
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="submitted_level_skip_requests",
        verbose_name=_("Requested By"),
        help_text=_("Staff member who submitted the request"),
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_level_skip_requests",
        verbose_name=_("Reviewed By"),
        help_text=_("Manager who reviewed the request"),
    )
    reviewed_at = models.DateTimeField(
        _("Reviewed At"),
        null=True,
        blank=True,
        help_text=_("When the request was reviewed"),
    )
    review_notes = models.TextField(
        _("Review Notes"),
        blank=True,
        help_text=_("Notes from the reviewer"),
    )

    # Implementation tracking
    implemented_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="implemented_level_skip_requests",
        verbose_name=_("Implemented By"),
        help_text=_("Staff member who implemented the skip"),
    )
    implemented_at = models.DateTimeField(
        _("Implemented At"),
        null=True,
        blank=True,
        help_text=_("When the skip was implemented"),
    )
    new_enrollment = models.ForeignKey(
        "enrollment.ClassHeaderEnrollment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="level_skip_enrollments",
        verbose_name=_("New Enrollment"),
        help_text=_("Enrollment created as result of level skip"),
    )

    class Meta:
        verbose_name = _("Language Level Skip Request")
        verbose_name_plural = _("Language Level Skip Requests")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["student", "status"]),
            models.Index(fields=["program", "status"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["reviewed_by", "reviewed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.student}: {self.current_level} → {self.target_level} ({self.status})"

    def approve(self, reviewed_by, review_notes: str = "") -> None:
        """Approve the level skip request."""
        self.status = self.RequestStatus.APPROVED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.review_notes = review_notes
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_notes"])

    def deny(self, reviewed_by, review_notes: str = "") -> None:
        """Deny the level skip request."""
        self.status = self.RequestStatus.DENIED
        self.reviewed_by = reviewed_by
        self.reviewed_at = timezone.now()
        self.review_notes = review_notes
        self.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_notes"])

    def mark_implemented(self, implemented_by, new_enrollment=None) -> None:
        """Mark the level skip as implemented."""
        self.status = self.RequestStatus.IMPLEMENTED
        self.implemented_by = implemented_by
        self.implemented_at = timezone.now()
        if new_enrollment:
            self.new_enrollment = new_enrollment
        self.save(
            update_fields=[
                "status",
                "implemented_by",
                "implemented_at",
                "new_enrollment",
            ]
        )

    def is_pending(self) -> bool:
        """Check if the request is pending review."""
        return self.status == self.RequestStatus.PENDING

    def is_approved(self) -> bool:
        """Check if the request has been approved."""
        return self.status == self.RequestStatus.APPROVED

    def is_implemented(self) -> bool:
        """Check if the request has been implemented."""
        return self.status == self.RequestStatus.IMPLEMENTED

    def can_be_approved(self) -> bool:
        """Check if the request can be approved."""
        return self.status == self.RequestStatus.PENDING

    def can_be_implemented(self) -> bool:
        """Check if the request can be implemented."""
        return self.status == self.RequestStatus.APPROVED

    def get_processing_time_days(self) -> int | None:
        """Get the processing time in days."""
        if self.reviewed_at:
            return (self.reviewed_at.date() - self.created_at.date()).days
        return None

    def get_implementation_time_days(self) -> int | None:
        """Get the implementation time in days."""
        if self.implemented_at and self.reviewed_at:
            return (self.implemented_at.date() - self.reviewed_at.date()).days
        return None
