"""Reconciliation models for payment and enrollment matching.

This module contains models specifically for the reconciliation process,
tracking payment matching status, adjustments, audit trails, and
refinement strategies during legacy data migration.
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import UserAuditModel

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser
    from django.db.models import ForeignKey

    from apps.curriculum.models import Term
    from apps.finance.models import GLAccount, JournalEntry
    from apps.people.models import StudentProfile


class ReconciliationBatch(UserAuditModel):
    """Batch processing for reconciliation runs."""

    class BatchStatus(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        PROCESSING = "PROCESSING", _("Processing")
        COMPLETED = "COMPLETED", _("Completed")
        FAILED = "FAILED", _("Failed")
        PARTIAL = "PARTIAL", _("Partially Completed")

    class BatchType(models.TextChoices):
        INITIAL = "INITIAL", _("Initial Reconciliation")
        REFINEMENT = "REFINEMENT", _("Refinement Pass")
        MANUAL = "MANUAL", _("Manual Review")
        SCHEDULED = "SCHEDULED", _("Scheduled Run")

    batch_id: models.CharField = models.CharField(_("Batch ID"), max_length=50, unique=True)
    batch_type: models.CharField = models.CharField(
        _("Batch Type"),
        max_length=20,
        choices=BatchType.choices,
        default=BatchType.SCHEDULED,
    )
    start_date: models.DateField = models.DateField(_("Start Date"))
    end_date: models.DateField = models.DateField(_("End Date"))
    status: models.CharField = models.CharField(
        _("Status"),
        max_length=20,
        choices=BatchStatus.choices,
        default=BatchStatus.PENDING,
    )

    # Processing details
    total_payments: models.PositiveIntegerField = models.PositiveIntegerField(_("Total Payments"), default=0)
    processed_payments: models.PositiveIntegerField = models.PositiveIntegerField(_("Processed Payments"), default=0)
    successful_matches: models.PositiveIntegerField = models.PositiveIntegerField(_("Successful Matches"), default=0)
    failed_matches: models.PositiveIntegerField = models.PositiveIntegerField(_("Failed Matches"), default=0)

    # Timing
    started_at: models.DateTimeField = models.DateTimeField(_("Started At"), null=True, blank=True)
    completed_at: models.DateTimeField = models.DateTimeField(_("Completed At"), null=True, blank=True)

    # Configuration
    parameters: models.JSONField = models.JSONField(
        _("Parameters"), default=dict, help_text=_("Batch processing parameters")
    )

    # Results summary
    results_summary: models.JSONField = models.JSONField(_("Results Summary"), default=dict)
    error_log: models.TextField = models.TextField(_("Error Log"), blank=True)

    class Meta:
        db_table = "finance_reconciliation_batch"
        verbose_name = _("Reconciliation Batch")
        verbose_name_plural = _("Reconciliation Batches")
        ordering = ["-created_at"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["batch_type", "created_at"]),
        ]

    def __str__(self):
        return f"Batch {self.batch_id} ({self.get_status_display()})"

    @property
    def success_rate(self) -> Decimal:
        """Calculate success rate."""
        if self.processed_payments > 0:
            return Decimal(self.successful_matches) / Decimal(self.processed_payments) * 100
        return Decimal("0")


class ReconciliationStatus(UserAuditModel):
    """Track reconciliation status for each payment with refinement capabilities."""

    class Status(models.TextChoices):
        FULLY_RECONCILED = "FULLY_RECONCILED", _("Fully Reconciled")
        AUTO_ALLOCATED = "AUTO_ALLOCATED", _("Auto-Allocated")
        SCHOLARSHIP_VERIFIED = "SCHOLARSHIP_VERIFIED", _("Scholarship Verified")
        PENDING_REVIEW = "PENDING_REVIEW", _("Pending Review")
        EXCEPTION_ERROR = "EXCEPTION_ERROR", _("Exception/Error")
        UNMATCHED = "UNMATCHED", _("Unmatched")

    class ConfidenceLevel(models.TextChoices):
        HIGH = "HIGH", _("High (95%+)")
        MEDIUM = "MEDIUM", _("Medium (80-94%)")
        LOW = "LOW", _("Low (<80%)")
        NONE = "NONE", _("No Confidence")

    class PricingMethod(models.TextChoices):
        DEFAULT_PRICING = "DEFAULT", _("Default Pricing")
        FIXED_PRICING = "FIXED", _("Course Fixed Pricing")
        SENIOR_PROJECT = "SENIOR", _("Senior Project Pricing")
        READING_CLASS = "READING", _("Reading Class Pricing")
        HISTORICAL_MATCH = "HISTORICAL", _("Historical Pattern Match")
        SCHOLARSHIP_VERIFICATION = "SCHOLARSHIP", _("Scholarship Verification")
        MANUAL_OVERRIDE = "MANUAL", _("Manual Override")
        HYBRID_MATCH = "HYBRID", _("Hybrid/Multiple Methods")

    payment: models.OneToOneField = models.OneToOneField(
        "finance.Payment",
        on_delete=models.CASCADE,
        related_name="reconciliation_status",
    )
    status: models.CharField = models.CharField(
        _("Status"), max_length=20, choices=Status.choices, default=Status.UNMATCHED
    )
    confidence_level: models.CharField = models.CharField(
        _("Confidence Level"),
        max_length=10,
        choices=ConfidenceLevel.choices,
        default=ConfidenceLevel.NONE,
    )
    confidence_score: models.DecimalField = models.DecimalField(
        _("Confidence Score"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Numeric confidence score (0-100)"),
    )
    pricing_method_applied: models.CharField = models.CharField(
        _("Pricing Method Applied"),
        max_length=20,
        choices=PricingMethod.choices,
        null=True,
        blank=True,
    )

    # Reconciliation details
    matched_enrollments: models.ManyToManyField = models.ManyToManyField(
        "enrollment.ClassHeaderEnrollment",
        blank=True,
        related_name="reconciliation_matches",
    )
    variance_amount: models.DecimalField = models.DecimalField(
        _("Variance Amount"),
        max_digits=10,
        decimal_places=2,
        default=0,
        help_text=_("Difference between expected and actual"),
    )
    variance_percentage: models.DecimalField = models.DecimalField(
        _("Variance Percentage"), max_digits=5, decimal_places=2, null=True, blank=True
    )

    # Refinement tracking
    refinement_attempts: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Refinement Attempts"),
        default=0,
        help_text=_("Number of times refinement has been attempted"),
    )
    last_attempt_date: models.DateTimeField = models.DateTimeField(_("Last Attempt Date"), null=True, blank=True)
    confidence_history: models.JSONField = models.JSONField(
        _("Confidence History"),
        default=list,
        help_text=_("Track confidence evolution over refinement attempts"),
    )
    refinement_strategies_tried: models.JSONField = models.JSONField(
        _("Strategies Tried"),
        default=list,
        help_text=_("List of refinement strategies that have been attempted"),
    )

    # Audit trail
    reconciled_date: models.DateTimeField = models.DateTimeField(_("Reconciled Date"), null=True, blank=True)
    reconciled_by: "ForeignKey[AbstractUser | None, AbstractUser | None]" = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reconciliations_performed",
    )
    notes: models.TextField = models.TextField(_("Notes"), blank=True)

    # Error tracking
    error_category: models.CharField = models.CharField(_("Error Category"), max_length=50, blank=True)
    error_details: models.JSONField = models.JSONField(_("Error Details"), default=dict)

    # Batch processing
    reconciliation_batch: "ForeignKey[ReconciliationBatch | None, ReconciliationBatch | None]" = models.ForeignKey(
        ReconciliationBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reconciliation_statuses",
    )

    class Meta:
        db_table = "finance_reconciliation_status"
        verbose_name = _("Reconciliation Status")
        verbose_name_plural = _("Reconciliation Statuses")
        ordering = ["-created_at"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["status", "confidence_score"]),
            models.Index(fields=["last_attempt_date"]),
            models.Index(fields=["reconciliation_batch"]),
        ]

    def __str__(self):
        return f"Payment {self.payment.payment_reference} - {self.get_status_display()}"

    def record_confidence_change(self, new_confidence: Decimal, method: str, reason: str):
        """Track how confidence changes over time."""
        self.confidence_history.append(
            {
                "timestamp": timezone.now().isoformat(),
                "old_confidence": (float(self.confidence_score) if self.confidence_score else 0),
                "new_confidence": float(new_confidence),
                "method": method,
                "reason": reason,
            }
        )
        self.confidence_score = new_confidence
        self._update_confidence_level()
        self.save()

    def _update_confidence_level(self) -> None:
        """Update confidence level based on score."""
        if self.confidence_score and self.confidence_score >= 95:
            self.confidence_level = self.ConfidenceLevel.HIGH
        elif self.confidence_score and self.confidence_score >= 80:
            self.confidence_level = self.ConfidenceLevel.MEDIUM
        elif self.confidence_score and self.confidence_score > 0:
            self.confidence_level = self.ConfidenceLevel.LOW
        else:
            self.confidence_level = self.ConfidenceLevel.NONE

    def add_refinement_attempt(self, strategy: str) -> None:
        """Record that a refinement strategy was attempted."""
        self.refinement_attempts += 1
        self.last_attempt_date = timezone.now()
        if strategy not in self.refinement_strategies_tried:
            self.refinement_strategies_tried.append(strategy)
        self.save()


class ReconciliationAdjustment(UserAuditModel):
    """Track reconciliation adjustments for audit trail."""

    class AdjustmentType(models.TextChoices):
        PRICING_VARIANCE = "PRICING", _("Pricing Variance")
        MISSING_ENROLLMENT = "MISSING_ENR", _("Missing Enrollment")
        MISSING_PAYMENT = "MISSING_PAY", _("Missing Payment")
        DUPLICATE_PAYMENT = "DUPLICATE", _("Duplicate Payment")
        CURRENCY_DIFFERENCE = "CURRENCY", _("Currency Difference")
        CLERICAL_ERROR = "CLERICAL", _("Clerical Error")
        DISCOUNT_APPLIED = "DISCOUNT", _("Discount Applied")
        FEE_ADJUSTMENT = "FEE_ADJ", _("Fee Adjustment")
        TIMING_DIFFERENCE = "TIMING", _("Timing Difference")
        SCHOLARSHIP_VARIANCE = "SCHOLARSHIP_VAR", _("Scholarship Application Variance")
        SCHOLARSHIP_OVERAPPLIED = "SCHOLARSHIP_OVER", _("Scholarship Over-Applied")
        SCHOLARSHIP_UNDERAPPLIED = "SCHOLARSHIP_UNDER", _("Scholarship Under-Applied")
        MISSING_SCHOLARSHIP_RECORD = "MISSING_SCHOLARSHIP", _("Missing Scholarship Record")

    gl_account: "ForeignKey[GLAccount | None, GLAccount | None]" = models.ForeignKey(
        "finance.GLAccount",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text=_("Reconciliation GL account (e.g., 9999-RECON)"),
    )
    adjustment_type: models.CharField = models.CharField(
        _("Adjustment Type"), max_length=20, choices=AdjustmentType.choices
    )
    description: models.CharField = models.CharField(_("Description"), max_length=200)

    # Amounts
    original_amount: models.DecimalField = models.DecimalField(_("Original Amount"), max_digits=10, decimal_places=2)
    adjusted_amount: models.DecimalField = models.DecimalField(_("Adjusted Amount"), max_digits=10, decimal_places=2)
    variance: models.DecimalField = models.DecimalField(_("Variance"), max_digits=10, decimal_places=2)

    # References
    payment: models.ForeignKey = models.ForeignKey(
        "finance.Payment",
        on_delete=models.CASCADE,
        related_name="reconciliation_adjustments",
    )
    journal_entry: "ForeignKey[JournalEntry | None, JournalEntry | None]" = models.ForeignKey(
        "finance.JournalEntry", on_delete=models.CASCADE, null=True, blank=True
    )
    reconciliation_status: models.ForeignKey = models.ForeignKey(
        ReconciliationStatus, on_delete=models.CASCADE, related_name="adjustments"
    )

    # Categorization for reporting
    student: "ForeignKey[StudentProfile | None, StudentProfile | None]" = models.ForeignKey(
        "people.StudentProfile", on_delete=models.PROTECT, null=True, blank=True
    )
    term: "ForeignKey[Term | None, Term | None]" = models.ForeignKey(
        "curriculum.Term", on_delete=models.PROTECT, null=True, blank=True
    )
    reconciliation_batch: "ForeignKey[ReconciliationBatch | None, ReconciliationBatch | None]" = models.ForeignKey(
        ReconciliationBatch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="adjustments",
    )

    # Approval workflow
    requires_approval: models.BooleanField = models.BooleanField(
        _("Requires Approval"),
        default=False,
        help_text=_("True if variance exceeds materiality threshold"),
    )
    approved_by: "ForeignKey[AbstractUser | None, AbstractUser | None]" = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_adjustments",
    )
    approved_date: models.DateTimeField = models.DateTimeField(_("Approved Date"), null=True, blank=True)

    class Meta:
        db_table = "finance_reconciliation_adjustment"
        verbose_name = _("Reconciliation Adjustment")
        verbose_name_plural = _("Reconciliation Adjustments")
        ordering = ["-created_at"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["adjustment_type", "created_at"]),
            models.Index(fields=["student", "term"]),
            models.Index(fields=["reconciliation_batch"]),
            models.Index(fields=["requires_approval", "approved_date"]),
        ]

    def __str__(self):
        return f"{self.get_adjustment_type_display()} - ${self.variance}"

    def clean(self):
        """Validate adjustment data."""
        super().clean()

        # Calculate variance if not set
        if self.original_amount is not None and self.adjusted_amount is not None:
            calculated_variance = self.adjusted_amount - self.original_amount
            if self.variance != calculated_variance:
                self.variance = calculated_variance


class ReconciliationRule(UserAuditModel):
    """Configurable rules for automated reconciliation."""

    class RuleType(models.TextChoices):
        AMOUNT_TOLERANCE = "AMOUNT_TOL", _("Amount Tolerance")
        DATE_RANGE = "DATE_RANGE", _("Date Range Matching")
        PATTERN_MATCH = "PATTERN", _("Pattern Matching")
        STUDENT_HISTORY = "HISTORY", _("Student History")
        COURSE_COMBINATION = "COURSE_COMBO", _("Course Combination")

    rule_name: models.CharField = models.CharField(_("Rule Name"), max_length=100, unique=True, default="Default Rule")
    rule_type: models.CharField = models.CharField(_("Rule Type"), max_length=20, choices=RuleType.choices)
    description: models.TextField = models.TextField(
        _("Description"), help_text=_("Detailed description of what this rule does")
    )

    # Rule configuration
    is_active: models.BooleanField = models.BooleanField(_("Is Active"), default=True)
    priority: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Priority"), default=100, help_text=_("Lower numbers = higher priority")
    )
    confidence_threshold: models.DecimalField = models.DecimalField(
        _("Confidence Threshold"),
        max_digits=5,
        decimal_places=2,
        default=80.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    # Rule parameters
    parameters: models.JSONField = models.JSONField(
        _("Parameters"), default=dict, help_text=_("Rule-specific parameters")
    )

    # Usage tracking
    times_applied: models.PositiveIntegerField = models.PositiveIntegerField(_("Times Applied"), default=0)
    success_count: models.PositiveIntegerField = models.PositiveIntegerField(_("Success Count"), default=0)
    last_applied: models.DateTimeField = models.DateTimeField(_("Last Applied"), null=True, blank=True)

    class Meta:
        db_table = "finance_reconciliation_rule"
        verbose_name = _("Reconciliation Rule")
        verbose_name_plural = _("Reconciliation Rules")
        ordering = ["priority", "rule_name"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["is_active", "priority"]),
            models.Index(fields=["rule_type", "is_active"]),
        ]

    def __str__(self):
        return f"{self.rule_name} (Priority: {self.priority})"

    @property
    def success_rate(self) -> Decimal:
        """Calculate rule success rate."""
        if self.times_applied > 0:
            return Decimal(self.success_count) / Decimal(self.times_applied) * 100
        return Decimal("0")


class MaterialityThreshold(UserAuditModel):
    """Configurable materiality thresholds for different contexts."""

    class ThresholdContext(models.TextChoices):
        INDIVIDUAL_PAYMENT = "INDIVIDUAL", _("Individual Payment")
        STUDENT_ACCOUNT = "STUDENT", _("Student Account Total")
        BATCH_TOTAL = "BATCH", _("Batch Total")
        PERIOD_AGGREGATE = "PERIOD", _("Period Aggregate")
        ERROR_CATEGORY = "ERROR_CAT", _("Error Category Total")

    context: models.CharField = models.CharField(
        _("Context"), max_length=20, choices=ThresholdContext.choices, unique=True
    )
    absolute_threshold: models.DecimalField = models.DecimalField(
        _("Absolute Threshold"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Absolute dollar amount threshold"),
    )
    percentage_threshold: models.DecimalField = models.DecimalField(
        _("Percentage Threshold"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Percentage threshold (if applicable)"),
    )
    effective_date: models.DateField = models.DateField(_("Effective Date"), default=date.today)
    notes: models.TextField = models.TextField(_("Notes"), blank=True)

    class Meta:
        db_table = "finance_materiality_threshold"
        verbose_name = _("Materiality Threshold")
        verbose_name_plural = _("Materiality Thresholds")
        ordering = ["context", "-effective_date"]

    def __str__(self):
        return f"{self.get_context_display()}: ${self.absolute_threshold}"

    @classmethod
    def get_threshold(cls, context: str) -> "MaterialityThreshold | None":
        """Get the current threshold for a given context."""
        return (
            cls.objects.filter(context=context, effective_date__lte=timezone.now().date())
            .order_by("-effective_date")
            .first()
        )
