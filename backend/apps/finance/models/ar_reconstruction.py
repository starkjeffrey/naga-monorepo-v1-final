"""A/R Reconstruction models for legacy financial data processing."""

from decimal import Decimal
from typing import ClassVar

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimestampedModel, UserTrackingModel


class ARReconstructionBatch(TimestampedModel, UserTrackingModel):
    """Batch tracking for A/R reconstruction runs."""

    class BatchStatus(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        PROCESSING = "PROCESSING", _("Processing")
        COMPLETED = "COMPLETED", _("Completed")
        FAILED = "FAILED", _("Failed")
        PAUSED = "PAUSED", _("Paused for Review")
        CANCELLED = "CANCELLED", _("Cancelled")

    class ProcessingMode(models.TextChoices):
        SUPERVISED = "SUPERVISED", _("Supervised Processing")
        AUTOMATED = "AUTOMATED", _("Automated Processing")
        REPROCESSING = "REPROCESSING", _("Reprocessing Run")

    # === BATCH IDENTIFICATION ===
    batch_id: models.CharField = models.CharField(
        _("Batch ID"),
        max_length=50,
        unique=True,
        help_text=_("Unique batch identifier"),
    )

    term_id: models.CharField = models.CharField(
        _("Term ID"),
        max_length=50,
        null=True,
        blank=True,
        help_text=_("Academic term being processed (null for multi-term batches)"),
    )

    processing_mode: models.CharField = models.CharField(
        _("Processing Mode"),
        max_length=20,
        choices=ProcessingMode.choices,
        default=ProcessingMode.SUPERVISED,
    )

    # === PROCESSING DETAILS ===
    status: models.CharField = models.CharField(
        _("Status"),
        max_length=20,
        choices=BatchStatus.choices,
        default=BatchStatus.PENDING,
    )

    total_receipts: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Total Receipts"),
        default=0,
        help_text=_("Total receipt_headers records to process"),
    )

    processed_receipts: models.PositiveIntegerField = models.PositiveIntegerField(_("Processed Receipts"), default=0)

    successful_reconstructions: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Successful Reconstructions"), default=0
    )

    failed_reconstructions: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Failed Reconstructions"), default=0
    )

    pending_review_count: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Pending Review Count"),
        default=0,
        help_text=_("Records requiring manual review"),
    )

    # === TIMING ===
    started_at: models.DateTimeField = models.DateTimeField(_("Started At"), null=True, blank=True)

    completed_at: models.DateTimeField = models.DateTimeField(_("Completed At"), null=True, blank=True)

    # === CONFIGURATION ===
    processing_parameters: models.JSONField = models.JSONField(
        _("Processing Parameters"),
        default=dict,
        help_text=_("Batch configuration and parameters"),
    )

    # === RESULTS ===
    variance_summary: models.JSONField = models.JSONField(
        _("Variance Summary"), default=dict, help_text=_("Summary of variances found")
    )

    processing_log: models.TextField = models.TextField(
        _("Processing Log"), blank=True, help_text=_("Detailed processing log")
    )

    class Meta:
        db_table = "finance_ar_reconstruction_batch"
        verbose_name = _("A/R Reconstruction Batch")
        verbose_name_plural = _("A/R Reconstruction Batches")
        ordering = ["-created_at"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["term_id", "processing_mode"]),
        ]

    def __str__(self):
        return f"Batch {self.batch_id} - {self.term_id}"

    @property
    def success_rate(self) -> Decimal:
        """Calculate batch success rate."""
        if self.processed_receipts > 0:
            return Decimal(self.successful_reconstructions) / Decimal(self.processed_receipts) * 100
        return Decimal("0")


class LegacyReceiptMapping(TimestampedModel, UserTrackingModel):
    """Bidirectional mapping between legacy receipts and reconstructed records."""

    # === LEGACY REFERENCE ===
    legacy_ipk: models.IntegerField = models.IntegerField(
        _("Legacy IPK"),
        null=True,
        blank=True,
        help_text=_("Original IPK primary key from receipt_headers - TRUE unique identifier"),
    )

    legacy_receipt_number: models.CharField = models.CharField(
        _("Legacy Receipt Number"),
        max_length=20,
        help_text=_("Original ReceiptNo from receipt_headers (display only)"),
    )

    legacy_receipt_id: models.CharField = models.CharField(
        _("Legacy Receipt ID"),
        max_length=200,
        help_text=_("Full ReceiptID with clerk information"),
    )

    legacy_student_id: models.CharField = models.CharField(
        _("Legacy Student ID"),
        max_length=10,
        help_text=_("ID field from receipt_headers (5-digit student number)"),
    )

    legacy_term_id: models.CharField = models.CharField(
        _("Legacy Term ID"), max_length=50, help_text=_("TermID from receipt_headers")
    )

    # === RECONSTRUCTED RECORDS ===
    generated_invoice: models.ForeignKey = models.ForeignKey(
        "finance.Invoice", on_delete=models.CASCADE, related_name="legacy_mappings"
    )

    generated_payment: models.ForeignKey = models.ForeignKey(
        "finance.Payment", on_delete=models.CASCADE, related_name="legacy_mappings"
    )

    # === FINANCIAL RECONCILIATION ===
    legacy_amount: models.DecimalField = models.DecimalField(
        _("Legacy Amount"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Original Amount from receipt_headers"),
    )

    legacy_net_amount: models.DecimalField = models.DecimalField(
        _("Legacy Net Amount"),
        max_digits=10,
        decimal_places=2,
        help_text=_("NetAmount from receipt_headers"),
    )

    legacy_discount: models.DecimalField = models.DecimalField(
        _("Legacy Discount"),
        max_digits=10,
        decimal_places=2,
        help_text=_("NetDiscount from receipt_headers"),
    )

    reconstructed_total: models.DecimalField = models.DecimalField(
        _("Reconstructed Total"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Total amount in reconstructed invoice"),
    )

    variance_amount: models.DecimalField = models.DecimalField(
        _("Variance Amount"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Difference between legacy and reconstructed amounts"),
    )

    # === PROCESSING METADATA ===
    reconstruction_batch: models.ForeignKey = models.ForeignKey(
        ARReconstructionBatch, on_delete=models.CASCADE, related_name="mappings"
    )

    processing_date: models.DateTimeField = models.DateTimeField(_("Processing Date"), auto_now_add=True)

    validation_status: models.CharField = models.CharField(
        _("Validation Status"),
        max_length=20,
        choices=[
            ("VALIDATED", _("Validated")),
            ("PENDING", _("Pending Review")),
            ("APPROVED", _("Manually Approved")),
            ("REJECTED", _("Rejected - Needs Reprocessing")),
        ],
        default="PENDING",
    )

    validation_notes: models.TextField = models.TextField(
        _("Validation Notes"), blank=True, help_text=_("Manual validation notes")
    )

    # === NOTES PROCESSING FIELDS ===
    legacy_notes: models.TextField = models.TextField(
        _("Legacy Notes"),
        blank=True,
        default="",
        help_text=_("Original notes from legacy receipt"),
    )

    parsed_note_type: models.CharField = models.CharField(
        _("Parsed Note Type"),
        max_length=50,
        blank=True,
        default="",
        help_text=_("Type of note as parsed by processing system"),
    )

    parsed_amount_adjustment: models.DecimalField = models.DecimalField(
        _("Parsed Amount Adjustment"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Amount adjustment parsed from notes"),
    )

    parsed_percentage_adjustment: models.DecimalField = models.DecimalField(
        _("Parsed Percentage Adjustment"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Percentage adjustment parsed from notes"),
    )

    parsed_authority: models.CharField = models.CharField(
        _("Parsed Authority"),
        max_length=100,
        null=True,
        blank=True,
        help_text=_("Authority/approver parsed from notes"),
    )

    parsed_reason: models.CharField = models.CharField(
        _("Parsed Reason"),
        max_length=200,
        null=True,
        blank=True,
        help_text=_("Reason parsed from notes"),
    )

    ar_transaction_mapping: models.CharField = models.CharField(
        _("A/R Transaction Mapping"),
        max_length=100,
        blank=True,
        default="",
        help_text=_("How this maps to A/R transaction types"),
    )

    normalized_note: models.TextField = models.TextField(
        _("Normalized Note"),
        blank=True,
        default="",
        help_text=_("Normalized note string for database storage"),
    )

    notes_processing_confidence: models.DecimalField = models.DecimalField(
        _("Notes Processing Confidence"),
        max_digits=3,
        decimal_places=2,
        default=0.0,
        help_text=_("Confidence score from notes processing"),
    )

    # structured_notes_json = models.JSONField(
    #     _("Structured Notes JSON"),
    #     default=dict,
    #     blank=True,
    #     help_text=_("G/L compatible structured notes with discount and fee categorization")
    # )

    # gl_discount_type = models.CharField(
    #     _("G/L Discount Type"),
    #     max_length=50,
    #     blank=True,
    #     default='',
    #     help_text=_("General Ledger discount category for accounting")
    # )

    class Meta:
        db_table = "finance_legacy_receipt_mapping"
        verbose_name = _("Legacy Receipt Mapping")
        verbose_name_plural = _("Legacy Receipt Mappings")
        unique_together = [["legacy_ipk"]]  # IPK is globally unique
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["legacy_ipk"]),  # Primary lookup field
            models.Index(fields=["legacy_receipt_number", "legacy_term_id"]),  # Display queries
            models.Index(fields=["legacy_student_id", "legacy_term_id"]),
            models.Index(fields=["validation_status"]),
            models.Index(fields=["reconstruction_batch"]),
        ]

    def __str__(self):
        return f"Receipt {self.legacy_receipt_number} → Invoice {self.generated_invoice.invoice_number}"


class ReconstructionScholarshipEntry(TimestampedModel, UserTrackingModel):
    """Scholarship entries discovered during reconstruction."""

    class ScholarshipType(models.TextChoices):
        SCHOOL_GRANTED = "SCHOOL", _("School-Granted Scholarship")
        STAFF_SCHOLARSHIP = "STAFF", _("Staff Scholarship")
        NGO_SCHOLARSHIP = "NGO", _("NGO Scholarship")
        OTHER = "OTHER", _("Other Scholarship")

    # === STUDENT & TERM ===
    student: models.ForeignKey = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.CASCADE,
        related_name="reconstruction_scholarship_entries",
    )

    term: models.ForeignKey = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.CASCADE,
        related_name="reconstruction_scholarship_entries",
    )

    # === SCHOLARSHIP DETAILS ===
    scholarship_type: models.CharField = models.CharField(
        _("Scholarship Type"), max_length=20, choices=ScholarshipType.choices
    )

    scholarship_amount: models.DecimalField = models.DecimalField(
        _("Scholarship Amount"), max_digits=10, decimal_places=2
    )

    scholarship_percentage: models.DecimalField = models.DecimalField(
        _("Scholarship Percentage"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # === DISCOVERY SOURCE ===
    discovered_from_receipt: models.CharField = models.CharField(
        _("Discovered from Receipt"),
        max_length=20,
        help_text=_("Receipt number where scholarship was discovered"),
    )

    discovery_notes: models.TextField = models.TextField(
        _("Discovery Notes"), help_text=_("How/why this scholarship was identified")
    )

    # === PROCESSING STATUS ===
    requires_reprocessing: models.BooleanField = models.BooleanField(
        _("Requires Reprocessing"),
        default=True,
        help_text=_("True if student needs reprocessing with this scholarship"),
    )

    applied_to_reconstruction: models.BooleanField = models.BooleanField(
        _("Applied to Reconstruction"),
        default=False,
        help_text=_("True if already applied in reconstruction"),
    )

    class Meta:
        db_table = "finance_reconstruction_scholarship_entry"
        verbose_name = _("Reconstruction Scholarship Entry")
        verbose_name_plural = _("Reconstruction Scholarship Entries")
        unique_together = [["student", "term", "scholarship_type"]]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["requires_reprocessing"]),
            models.Index(fields=["discovered_from_receipt"]),
        ]

    def __str__(self):
        return f"{self.student} - {self.term} - {self.get_scholarship_type_display()}"


class ClerkIdentification(TimestampedModel, UserTrackingModel):
    """Extracted clerk identification from legacy ReceiptID patterns."""

    # === CLERK DETAILS ===
    clerk_name: models.CharField = models.CharField(
        _("Clerk Name"), max_length=100, help_text=_("Extracted clerk name/identifier")
    )

    computer_identifier: models.CharField = models.CharField(
        _("Computer Identifier"),
        max_length=100,
        blank=True,
        help_text=_("Computer/terminal identifier from ReceiptID"),
    )

    # === PATTERN MATCHING ===
    receipt_id_pattern: models.CharField = models.CharField(
        _("Receipt ID Pattern"),
        max_length=200,
        help_text=_("Example ReceiptID pattern for this clerk"),
    )

    extraction_confidence: models.CharField = models.CharField(
        _("Extraction Confidence"),
        max_length=10,
        choices=[
            ("HIGH", _("High Confidence")),
            ("MEDIUM", _("Medium Confidence")),
            ("LOW", _("Low Confidence")),
            ("MANUAL", _("Manual Entry")),
        ],
        default="MEDIUM",
    )

    # === USAGE TRACKING ===
    first_seen_date: models.DateTimeField = models.DateTimeField(
        _("First Seen Date"), help_text=_("First receipt date for this clerk")
    )

    last_seen_date: models.DateTimeField = models.DateTimeField(
        _("Last Seen Date"), help_text=_("Most recent receipt date for this clerk")
    )

    receipt_count: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Receipt Count"),
        default=0,
        help_text=_("Number of receipts processed by this clerk"),
    )

    # === VERIFICATION ===
    verified_by_user: models.BooleanField = models.BooleanField(
        _("Verified by User"),
        default=False,
        help_text=_("True if clerk identification verified manually"),
    )

    verification_notes: models.TextField = models.TextField(
        _("Verification Notes"), blank=True, help_text=_("Manual verification notes")
    )

    class Meta:
        db_table = "finance_clerk_identification"
        verbose_name = _("Clerk Identification")
        verbose_name_plural = _("Clerk Identifications")
        unique_together = [["clerk_name", "computer_identifier"]]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["clerk_name"]),
            models.Index(fields=["verified_by_user"]),
        ]

    def __str__(self):
        return f"{self.clerk_name} ({self.computer_identifier})"
