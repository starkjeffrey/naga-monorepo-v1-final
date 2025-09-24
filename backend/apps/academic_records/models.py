"""Refactored Academic Records models with flexible document system.

This module provides a generalized document request and generation system
that can handle multiple document types without code duplication.

Key improvements:
- Generic DocumentRequest model replacing transcript-specific model
- Factory pattern for document type handling
- Flexible configuration system
- Strategy pattern for generation logic
"""

import uuid
from typing import Any, ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import (
    BooleanField,
    CharField,
    ForeignKey,
    PositiveIntegerField,
    TextField,
    UUIDField,
)
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import UserAuditModel
from apps.people.models import StudentProfile


class DocumentTypeConfig(models.Model):
    """Configuration for different document types.

    Defines the behavior, requirements, and workflow for each document type
    without requiring code changes for new document types.
    """

    class DocumentCategory(models.TextChoices):
        """Categories for organizing document types."""

        ACADEMIC_TRANSCRIPT = "academic_transcript", _("Academic Transcript")
        GRADE_REPORT = "grade_report", _("Grade Report")
        ATTENDANCE_REPORT = "attendance_report", _("Attendance Report")
        ENROLLMENT_VERIFICATION = "enrollment_verification", _("Enrollment Verification")
        OFFICIAL_LETTER = "official_letter", _("Official Letter")
        DEGREE_VERIFICATION = "degree_verification", _("Degree Verification")
        CONDUCT_REPORT = "conduct_report", _("Conduct Report")

    # Document type identification
    code: CharField = models.CharField(
        _("Document Type Code"),
        max_length=50,
        unique=True,
        help_text=_("Unique code for this document type (e.g., OFFICIAL_TRANSCRIPT)"),
    )
    name: CharField = models.CharField(
        _("Document Name"),
        max_length=200,
        help_text=_("Human-readable name for this document type"),
    )
    category: CharField = models.CharField(
        _("Document Category"),
        max_length=30,
        choices=DocumentCategory.choices,
        help_text=_("Category this document type belongs to"),
    )
    description: TextField = models.TextField(
        _("Description"),
        blank=True,
        help_text=_("Detailed description of what this document contains"),
    )

    # Processing configuration
    requires_approval: BooleanField = models.BooleanField(
        _("Requires Approval"),
        default=True,
        help_text=_("Whether requests for this document type require approval"),
    )
    auto_generate: BooleanField = models.BooleanField(
        _("Auto Generate"),
        default=False,
        help_text=_("Whether this document can be automatically generated"),
    )
    processing_time_hours: PositiveIntegerField = models.PositiveIntegerField(
        _("Processing Time (Hours)"),
        default=24,
        help_text=_("Expected processing time in hours"),
    )

    # Data requirements
    requires_grade_data: BooleanField = models.BooleanField(
        _("Requires Grade Data"),
        default=False,
        help_text=_("Whether this document requires access to grade information"),
    )
    requires_attendance_data: BooleanField = models.BooleanField(
        _("Requires Attendance Data"),
        default=False,
        help_text=_("Whether this document requires attendance information"),
    )
    requires_manual_input: BooleanField = models.BooleanField(
        _("Requires Manual Input"),
        default=False,
        help_text=_("Whether this document requires manual staff input/review"),
    )

    # Delivery options
    allows_email_delivery: BooleanField = models.BooleanField(
        _("Allows Email Delivery"),
        default=True,
        help_text=_("Whether this document can be delivered via email"),
    )
    allows_pickup: BooleanField = models.BooleanField(
        _("Allows Pickup"),
        default=True,
        help_text=_("Whether this document can be picked up in person"),
    )
    allows_mail_delivery: BooleanField = models.BooleanField(
        _("Allows Mail Delivery"),
        default=False,
        help_text=_("Whether this document can be mailed"),
    )
    allows_third_party_delivery: BooleanField = models.BooleanField(
        _("Allows Third Party Delivery"),
        default=False,
        help_text=_("Whether this document can be sent to third parties"),
    )

    # Permissions and financial configuration
    required_permission: CharField = models.CharField(
        _("Required Permission"),
        max_length=100,
        blank=True,
        help_text=_("Django permission required to request this document type"),
    )

    # Document fee configuration
    has_fee: BooleanField = models.BooleanField(
        _("Has Fee"),
        default=False,
        help_text=_("Whether this document type has an associated fee"),
    )
    fee_amount: models.DecimalField = models.DecimalField(
        _("Fee Amount"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Fee amount for this document type (if applicable)"),
    )
    fee_currency: models.CharField = models.CharField(
        _("Fee Currency"),
        max_length=3,
        default="USD",
        help_text=_("Currency for the document fee"),
    )

    # Free allowance configuration
    free_allowance_per_term: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Free Allowance Per Term"),
        default=0,
        help_text=_("Number of free documents of this type per academic term"),
    )
    free_allowance_per_year: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Free Allowance Per Year"),
        default=0,
        help_text=_("Number of free documents of this type per academic year"),
    )
    free_allowance_lifetime: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Free Allowance Lifetime"),
        default=0,
        help_text=_("Total number of free documents of this type allowed"),
    )

    # Quota configuration
    unit_cost: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Unit Cost"), default=1, help_text=_("Number of quota units required for this document type")
    )

    # Status and ordering
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this document type is currently available for requests"),
    )
    display_order: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Display Order"),
        default=100,
        help_text=_("Order in which this document type appears in lists"),
    )

    class Meta:
        verbose_name = _("Document Type Configuration")
        verbose_name_plural = _("Document Type Configurations")
        ordering = ["display_order", "name"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["code"]),
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["display_order"]),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def available_delivery_methods(self) -> list[str]:
        """Get list of available delivery methods for this document type."""
        methods = []
        if self.allows_email_delivery:
            methods.append("EMAIL")
        if self.allows_pickup:
            methods.append("PICKUP")
        if self.allows_mail_delivery:
            methods.append("MAIL")
        if self.allows_third_party_delivery:
            methods.append("THIRD_PARTY")
        return methods


class DocumentRequest(UserAuditModel):
    """Generic document request model that can handle any document type.

    Replaces the transcript-specific TranscriptRequest with a flexible
    system that works for all document types through configuration.
    """

    class RequestStatus(models.TextChoices):
        """Status of document requests."""

        PENDING = "PENDING", _("Pending Review")
        APPROVED = "APPROVED", _("Approved")
        IN_PROGRESS = "IN_PROGRESS", _("In Progress")
        COMPLETED = "COMPLETED", _("Completed")
        CANCELLED = "CANCELLED", _("Cancelled")
        REJECTED = "REJECTED", _("Rejected")
        ON_HOLD = "ON_HOLD", _("On Hold")

    class DeliveryMethod(models.TextChoices):
        """Methods for document delivery."""

        EMAIL = "EMAIL", _("Email")
        PICKUP = "PICKUP", _("In-Person Pickup")
        MAIL = "MAIL", _("Postal Mail")
        THIRD_PARTY = "THIRD_PARTY", _("Third Party Institution")

    class Priority(models.TextChoices):
        """Priority levels for document requests."""

        LOW = "LOW", _("Low")
        NORMAL = "NORMAL", _("Normal")
        HIGH = "HIGH", _("High")
        URGENT = "URGENT", _("Urgent")

    # Request identification
    request_id: UUIDField = models.UUIDField(
        _("Request ID"),
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text=_("Unique identifier for this document request"),
    )

    # Document type and student
    document_type: ForeignKey = models.ForeignKey(
        DocumentTypeConfig,
        on_delete=models.PROTECT,
        related_name="requests",
        verbose_name=_("Document Type"),
        help_text=_("Type of document being requested"),
    )
    student: ForeignKey = models.ForeignKey(
        StudentProfile,
        on_delete=models.PROTECT,
        related_name="document_requests",
        verbose_name=_("Student"),
        help_text=_("Student requesting the document"),
    )

    # Request status and metadata
    request_status: CharField = models.CharField(
        _("Request Status"),
        max_length=20,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING,
        help_text=_("Current status of the request"),
    )
    priority: CharField = models.CharField(
        _("Priority"),
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
        help_text=_("Priority level for processing this request"),
    )

    # Delivery information
    delivery_method: CharField = models.CharField(
        _("Delivery Method"),
        max_length=20,
        choices=DeliveryMethod.choices,
        default=DeliveryMethod.EMAIL,
        help_text=_("How the document should be delivered"),
    )
    recipient_name: models.CharField = models.CharField(
        _("Recipient Name"),
        max_length=200,
        blank=True,
        help_text=_("Name of person or institution receiving the document"),
    )
    recipient_address: models.TextField = models.TextField(
        _("Recipient Address"),
        blank=True,
        help_text=_("Mailing address for document delivery"),
    )
    recipient_email: models.EmailField = models.EmailField(
        _("Recipient Email"),
        blank=True,
        help_text=_("Email address for electronic delivery"),
    )

    # Request details and custom fields
    request_notes: models.TextField = models.TextField(
        _("Request Notes"),
        blank=True,
        help_text=_("Additional notes about the document request"),
    )
    custom_data: models.JSONField = models.JSONField(
        _("Custom Data"),
        default=dict,
        blank=True,
        help_text=_("Document-type specific data (e.g., date ranges, special requirements)"),
    )

    # Financial integration
    has_fee: models.BooleanField = models.BooleanField(
        _("Has Fee"),
        default=False,
        help_text=_("Whether this request requires payment"),
    )
    fee_amount: models.DecimalField = models.DecimalField(
        _("Fee Amount"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Fee amount for this specific request"),
    )
    is_free_allowance: models.BooleanField = models.BooleanField(
        _("Is Free Allowance"),
        default=False,
        help_text=_("Whether this request uses the student's free allowance"),
    )
    payment_required: models.BooleanField = models.BooleanField(
        _("Payment Required"),
        default=False,
        help_text=_("Whether payment is required before processing"),
    )
    payment_status: models.CharField = models.CharField(
        _("Payment Status"),
        max_length=20,
        choices=[
            ("NOT_REQUIRED", _("Not Required")),
            ("PENDING", _("Payment Pending")),
            ("PAID", _("Paid")),
            ("WAIVED", _("Waived")),
        ],
        default="NOT_REQUIRED",
        help_text=_("Status of payment for this request"),
    )

    # Finance system integration (optional foreign key to avoid circular dependency)
    finance_invoice_id: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Finance Invoice ID"),
        null=True,
        blank=True,
        help_text=_("ID of associated invoice in finance system"),
    )

    # Processing information
    requested_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="document_requests_made",
        verbose_name=_("Requested By"),
        help_text=_("User who submitted the request"),
    )
    assigned_to: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="document_requests_assigned",
        verbose_name=_("Assigned To"),
        null=True,
        blank=True,
        help_text=_("Staff member assigned to process this request"),
    )
    processed_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="document_requests_processed",
        verbose_name=_("Processed By"),
        null=True,
        blank=True,
        help_text=_("User who completed the request"),
    )

    # Important dates
    requested_date: models.DateTimeField = models.DateTimeField(
        _("Requested Date"),
        default=timezone.now,
        help_text=_("Date and time the request was submitted"),
    )
    due_date: models.DateTimeField = models.DateTimeField(
        _("Due Date"),
        null=True,
        blank=True,
        help_text=_("Expected completion date based on processing time"),
    )
    approved_date: models.DateTimeField = models.DateTimeField(
        _("Approved Date"),
        null=True,
        blank=True,
        help_text=_("Date and time the request was approved"),
    )
    completed_date: models.DateTimeField = models.DateTimeField(
        _("Completed Date"),
        null=True,
        blank=True,
        help_text=_("Date and time the document was delivered"),
    )

    class Meta:
        verbose_name = _("Document Request")
        verbose_name_plural = _("Document Requests")
        ordering = ["-requested_date"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "request_status"]),
            models.Index(fields=["document_type", "request_status"]),
            models.Index(fields=["request_status", "requested_date"]),
            models.Index(fields=["request_id"]),
            models.Index(fields=["due_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.document_type.name} - {self.student} ({self.get_request_status_display()})"

    def save(self, *args, **kwargs):
        """Override save to set due date and fee information based on document type."""
        if self.document_type:
            # Set due date based on processing time
            if not self.due_date:
                from datetime import timedelta

                self.due_date = self.requested_date + timedelta(hours=self.document_type.processing_time_hours)

            # Set fee information based on document type
            if not hasattr(self, "_skip_fee_calculation"):
                self.has_fee = self.document_type.has_fee
                if self.has_fee and not self.fee_amount:
                    self.fee_amount = self.document_type.fee_amount

        super().save(*args, **kwargs)

    def clean(self):
        """Validate request data against document type configuration."""
        super().clean()

        if self.document_type and self.delivery_method:
            available_methods = self.document_type.available_delivery_methods
            if self.delivery_method not in available_methods:
                raise ValidationError(
                    {
                        "delivery_method": _(
                            f"Delivery method '{self.delivery_method}' is not available "
                            f"for document type '{self.document_type.name}'. "
                            f"Available methods: {', '.join(available_methods)}",
                        ),
                    },
                )

        # Validate delivery information based on method
        if self.delivery_method == self.DeliveryMethod.EMAIL and not self.recipient_email:
            raise ValidationError({"recipient_email": _("Email address is required for email delivery")})

        if self.delivery_method == self.DeliveryMethod.MAIL and not self.recipient_address:
            raise ValidationError({"recipient_address": _("Mailing address is required for postal delivery")})

    @property
    def is_completed(self) -> bool:
        """Check if the request has been completed."""
        return self.request_status == self.RequestStatus.COMPLETED

    @property
    def is_pending_approval(self) -> bool:
        """Check if the request is pending approval."""
        return self.request_status == self.RequestStatus.PENDING

    @property
    def is_overdue(self) -> bool:
        """Check if the request is overdue."""
        if not self.due_date or self.is_completed:
            return False
        return timezone.now() > self.due_date

    @property
    def days_until_due(self) -> int | None:
        """Get number of days until due date."""
        if not self.due_date or self.is_completed:
            return None
        delta = self.due_date - timezone.now()
        return delta.days


class GeneratedDocument(UserAuditModel):
    """Generated documents with verification features.

    Stores metadata about generated documents with security features
    for verification and audit trails. Works with any document type.
    """

    # Document identification
    document_id: models.UUIDField = models.UUIDField(
        _("Document ID"),
        default=uuid.uuid4,
        unique=True,
        editable=False,
        help_text=_("Unique identifier for this document"),
    )

    # Associated request and type
    document_request: models.ForeignKey = models.ForeignKey(
        DocumentRequest,
        on_delete=models.CASCADE,
        related_name="generated_documents",
        verbose_name=_("Document Request"),
        help_text=_("Request that generated this document"),
    )
    student: models.ForeignKey = models.ForeignKey(
        StudentProfile,
        on_delete=models.PROTECT,
        related_name="generated_documents",
        verbose_name=_("Student"),
        help_text=_("Student this document belongs to"),
    )

    # Content and generation
    file_path: models.CharField = models.CharField(
        _("File Path"),
        max_length=500,
        blank=True,
        help_text=_("Path to the generated document file"),
    )
    file_size: models.PositiveIntegerField = models.PositiveIntegerField(
        _("File Size"),
        null=True,
        blank=True,
        help_text=_("Size of the document file in bytes"),
    )
    content_hash: models.CharField = models.CharField(
        _("Content Hash"),
        max_length=64,
        blank=True,
        help_text=_("SHA-256 hash of document content for verification"),
    )

    # Security and verification
    verification_code: models.CharField = models.CharField(
        _("Verification Code"),
        max_length=32,
        unique=True,
        blank=True,
        help_text=_("Unique code for document verification"),
    )
    qr_code_data: models.TextField = models.TextField(
        _("QR Code Data"), blank=True, help_text=_("QR code data for verification")
    )

    # Generation metadata
    generated_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="documents_generated",
        verbose_name=_("Generated By"),
        help_text=_("User who generated this document"),
    )
    generated_date: models.DateTimeField = models.DateTimeField(
        _("Generated Date"),
        default=timezone.now,
        help_text=_("Date and time the document was generated"),
    )

    # Document-specific metadata
    document_data: models.JSONField = models.JSONField(
        _("Document Data"),
        default=dict,
        blank=True,
        help_text=_("Document-specific metadata (e.g., as_of_date, included_terms)"),
    )

    # Access tracking
    access_count: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Access Count"),
        default=0,
        help_text=_("Number of times this document has been accessed"),
    )
    last_accessed: models.DateTimeField = models.DateTimeField(
        _("Last Accessed"),
        null=True,
        blank=True,
        help_text=_("Date and time the document was last accessed"),
    )

    class Meta:
        verbose_name = _("Generated Document")
        verbose_name_plural = _("Generated Documents")
        ordering = ["-generated_date"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "document_request"]),
            models.Index(fields=["verification_code"]),
            models.Index(fields=["document_id"]),
            models.Index(fields=["generated_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.document_request.document_type.name} - {self.student} ({self.generated_date.date()})"

    def save(self, *args, **kwargs):
        """Override save to generate verification code."""
        if not self.verification_code:
            self.verification_code = str(uuid.uuid4()).replace("-", "")[:16].upper()
        super().save(*args, **kwargs)

    @property
    def document_type(self) -> DocumentTypeConfig:
        """Get the document type through the request."""
        return self.document_request.document_type

    @property
    def is_official(self) -> bool:
        """Check if this is an official document based on document type."""
        return self.document_type.category in [
            DocumentTypeConfig.DocumentCategory.ACADEMIC_TRANSCRIPT,
            DocumentTypeConfig.DocumentCategory.DEGREE_VERIFICATION,
            DocumentTypeConfig.DocumentCategory.OFFICIAL_LETTER,
        ]

    @property
    def verification_url(self) -> str:
        """Get the verification URL for this document."""
        return reverse(
            "academic_records:verify_document",
            kwargs={"verification_code": self.verification_code},
        )


class DocumentRequestComment(UserAuditModel):
    """Comments and status updates on document requests.

    Provides communication trail for document processing workflow.
    """

    document_request: models.ForeignKey = models.ForeignKey(
        DocumentRequest,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name=_("Document Request"),
        help_text=_("Request this comment belongs to"),
    )
    comment_text: models.TextField = models.TextField(_("Comment"), help_text=_("Comment or status update text"))
    is_internal: models.BooleanField = models.BooleanField(
        _("Internal Comment"),
        default=False,
        help_text=_("Whether this comment is for staff only"),
    )
    author: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="document_comments",
        verbose_name=_("Author"),
        help_text=_("User who wrote this comment"),
    )

    class Meta:
        verbose_name = _("Document Request Comment")
        verbose_name_plural = _("Document Request Comments")
        ordering = ["created_at"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["document_request", "created_at"]),
            models.Index(fields=["is_internal"]),
        ]

    def __str__(self) -> str:
        return f"Comment on {self.document_request} by {self.author}"


class DocumentUsageTracker(UserAuditModel):
    """Tracks document request usage for quota and billing management.

    Maintains counts of documents requested by students per document type
    for enforcing free allowances and billing purposes.
    """

    student: models.ForeignKey = models.ForeignKey(
        StudentProfile,
        on_delete=models.PROTECT,
        related_name="document_usage",
        verbose_name=_("Student"),
        help_text=_("Student this usage record belongs to"),
    )
    document_type: models.ForeignKey = models.ForeignKey(
        DocumentTypeConfig,
        on_delete=models.CASCADE,
        related_name="usage_records",
        verbose_name=_("Document Type"),
        help_text=_("Document type this usage applies to"),
    )

    # Usage counts by period
    total_requested: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Total Requested"),
        default=0,
        help_text=_("Total number of documents of this type ever requested"),
    )
    total_completed: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Total Completed"),
        default=0,
        help_text=_("Total number of documents of this type successfully completed"),
    )
    total_free_used: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Total Free Used"),
        default=0,
        help_text=_("Total number of free allowances used for this document type"),
    )
    total_paid: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Total Paid"),
        default=0,
        help_text=_("Total number of paid documents of this type"),
    )

    # Current academic period counts
    current_term_count: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Current Term Count"),
        default=0,
        help_text=_("Number of documents requested in current term"),
    )
    current_year_count: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Current Year Count"),
        default=0,
        help_text=_("Number of documents requested in current academic year"),
    )

    # Last request tracking
    last_request_date: models.DateTimeField = models.DateTimeField(
        _("Last Request Date"),
        null=True,
        blank=True,
        help_text=_("Date of most recent request for this document type"),
    )
    last_completed_date: models.DateTimeField = models.DateTimeField(
        _("Last Completed Date"),
        null=True,
        blank=True,
        help_text=_("Date of most recent completed document of this type"),
    )

    class Meta:
        verbose_name = _("Document Usage Tracker")
        verbose_name_plural = _("Document Usage Trackers")
        unique_together = [["student", "document_type"]]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "document_type"]),
            models.Index(fields=["total_requested"]),
            models.Index(fields=["last_request_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.student} - {self.document_type.name} ({self.total_requested} requested)"

    @property
    def remaining_free_term(self) -> int:
        """Calculate remaining free allowance for current term."""
        if not self.document_type.free_allowance_per_term:
            return 0
        return max(0, self.document_type.free_allowance_per_term - self.current_term_count)

    @property
    def remaining_free_year(self) -> int:
        """Calculate remaining free allowance for current year."""
        if not self.document_type.free_allowance_per_year:
            return 0
        return max(0, self.document_type.free_allowance_per_year - self.current_year_count)

    @property
    def remaining_free_lifetime(self) -> int:
        """Calculate remaining lifetime free allowance."""
        if not self.document_type.free_allowance_lifetime:
            return 0
        return max(0, self.document_type.free_allowance_lifetime - self.total_free_used)

    @property
    def has_free_allowance_available(self) -> bool:
        """Check if student has any free allowance remaining."""
        return self.remaining_free_term > 0 or self.remaining_free_year > 0 or self.remaining_free_lifetime > 0

    def increment_usage(self, is_free: bool = False, completed: bool = False) -> None:
        """Increment usage counters."""
        self.total_requested += 1
        self.current_term_count += 1
        self.current_year_count += 1
        self.last_request_date = timezone.now()

        if is_free:
            self.total_free_used += 1
        else:
            self.total_paid += 1

        if completed:
            self.total_completed += 1
            self.last_completed_date = timezone.now()

        self.save()


class DocumentFeeCalculator:
    """Service class for calculating document fees and managing free allowances.

    Handles the business logic for determining whether a document request
    should be free or paid, and calculates the appropriate fee amount.
    """

    @staticmethod
    def calculate_fee(student: StudentProfile, document_type: DocumentTypeConfig) -> dict[str, Any]:
        """Calculate fee for a document request.

        Returns:
            dict with keys: is_free, fee_amount, reason, remaining_allowances
        """
        # Get or create usage tracker
        usage, _ = DocumentUsageTracker.objects.get_or_create(
            student=student,
            document_type=document_type,
            defaults={
                "total_requested": 0,
                "total_completed": 0,
                "total_free_used": 0,
                "total_paid": 0,
                "current_term_count": 0,
                "current_year_count": 0,
            },
        )

        # Check if document type has no fee
        if not document_type.has_fee:
            return {
                "is_free_allowance": True,
                "fee_amount": 0,
                "reason": "Document type has no associated fee",
                "remaining_free_term": None,
                "remaining_free_year": None,
                "remaining_free_lifetime": None,
            }

        # Check free allowances (prioritize most restrictive)
        result = {
            "is_free_allowance": False,
            "fee_amount": float(document_type.fee_amount or 0),
            "reason": "",
            "remaining_free_term": usage.remaining_free_term,
            "remaining_free_year": usage.remaining_free_year,
            "remaining_free_lifetime": usage.remaining_free_lifetime,
        }

        # Check lifetime allowance first
        if usage.remaining_free_lifetime > 0:
            result.update(
                {
                    "is_free_allowance": True,
                    "fee_amount": 0,
                    "reason": f"Using lifetime free allowance ({usage.remaining_free_lifetime} remaining)",
                },
            )

        # Check yearly allowance
        elif usage.remaining_free_year > 0:
            result.update(
                {
                    "is_free_allowance": True,
                    "fee_amount": 0,
                    "reason": f"Using yearly free allowance ({usage.remaining_free_year} remaining)",
                },
            )

        # Check term allowance
        elif usage.remaining_free_term > 0:
            result.update(
                {
                    "is_free_allowance": True,
                    "fee_amount": 0,
                    "reason": f"Using term free allowance ({usage.remaining_free_term} remaining)",
                },
            )

        else:
            result["reason"] = "No free allowances remaining - fee required"

        return result

    @staticmethod
    def create_request_with_fee_calculation(
        student: StudentProfile,
        document_type: DocumentTypeConfig,
        **request_data,
    ) -> tuple[DocumentRequest, dict[str, Any]]:
        """Create a document request with automatic fee calculation.

        Returns:
            tuple of (DocumentRequest instance, fee_calculation_result)
        """
        fee_calc = DocumentFeeCalculator.calculate_fee(student, document_type)

        # Create the request with fee information
        request = DocumentRequest.objects.create(
            student=student,
            document_type=document_type,
            has_fee=not fee_calc["is_free_allowance"],
            fee_amount=fee_calc["fee_amount"] if fee_calc["fee_amount"] > 0 else None,
            is_free_allowance=fee_calc["is_free_allowance"],
            payment_required=not fee_calc["is_free_allowance"] and fee_calc["fee_amount"] > 0,
            payment_status=("NOT_REQUIRED" if fee_calc["is_free_allowance"] else "PENDING"),
            **request_data,
        )

        # Update usage tracker
        usage, _ = DocumentUsageTracker.objects.get_or_create(student=student, document_type=document_type)
        usage.increment_usage(is_free=fee_calc["is_free_allowance"])

        return request, fee_calc


class DocumentQuota(UserAuditModel):
    """Tracks document quotas included with administrative fees.

    Each term, students with active cycle change status receive a quota of
    document units as part of their administrative fee. This model tracks
    the allocation and usage of these units.

    Document units are consumed based on the unit_cost of each document type.
    Once quota is exhausted, additional document requests incur excess fees.
    """

    student: models.ForeignKey = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.PROTECT,
        related_name="document_quotas",
        verbose_name=_("Student"),
        help_text=_("Student who owns this document quota"),
    )
    term: models.ForeignKey = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.PROTECT,
        related_name="document_quotas",
        verbose_name=_("Term"),
        help_text=_("Term this quota applies to"),
    )
    cycle_status: models.ForeignKey = models.ForeignKey(
        "enrollment.StudentCycleStatus",
        on_delete=models.PROTECT,
        related_name="document_quotas",
        verbose_name=_("Cycle Status"),
        help_text=_("Associated cycle status that triggered this quota"),
    )

    # Quota allocation
    total_units: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Total Units"), default=10, help_text=_("Total document units allocated for this term")
    )
    used_units: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Used Units"), default=0, help_text=_("Document units already used")
    )

    # Financial link
    admin_fee_line_item: models.ForeignKey = models.ForeignKey(
        "finance.InvoiceLineItem",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="document_quotas",
        verbose_name=_("Administrative Fee Line Item"),
        help_text=_("Administrative fee invoice line item that included this quota"),
    )

    # Status tracking
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"), default=True, help_text=_("Whether this quota is currently usable")
    )
    expires_date: models.DateField = models.DateField(_("Expires Date"), help_text=_("Date when this quota expires"))

    class Meta:
        verbose_name = _("Document Quota")
        verbose_name_plural = _("Document Quotas")
        db_table = "academic_records_document_quota"
        unique_together = [["student", "term"]]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "term", "is_active"]),
            models.Index(fields=["expires_date"]),
            models.Index(fields=["cycle_status"]),
        ]

    def __str__(self) -> str:
        return f"{self.student} - {self.term} ({self.remaining_units}/{self.total_units} units)"

    @property
    def remaining_units(self) -> int:
        """Calculate remaining document units."""
        return max(0, self.total_units - self.used_units)

    @property
    def is_expired(self) -> bool:
        """Check if quota has expired."""
        return timezone.now().date() > self.expires_date

    @property
    def usage_percentage(self) -> float:
        """Calculate percentage of quota used."""
        if self.total_units == 0:
            return 0.0
        return (self.used_units / self.total_units) * 100

    def consume_units(self, units: int) -> bool:
        """Consume the specified number of units if available.

        Returns:
            True if units were consumed, False if insufficient units.
        """
        if self.remaining_units >= units:
            self.used_units += units
            self.save(update_fields=["used_units", "updated_at"])
            return True
        return False


class DocumentQuotaUsage(UserAuditModel):
    """Records individual document requests against quotas.

    Provides an audit trail of how document quota units are consumed,
    linking each usage to the specific document request that consumed them.
    """

    quota: models.ForeignKey = models.ForeignKey(
        DocumentQuota,
        on_delete=models.PROTECT,
        related_name="usage_records",
        verbose_name=_("Document Quota"),
        help_text=_("Quota from which units were consumed"),
    )
    document_request: models.ForeignKey = models.ForeignKey(
        "academic_records.DocumentRequest",
        on_delete=models.PROTECT,
        related_name="quota_usage",
        verbose_name=_("Document Request"),
        help_text=_("Document request that consumed these units"),
    )
    units_consumed: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Units Consumed"), help_text=_("Number of units consumed for this document")
    )
    usage_date: models.DateTimeField = models.DateTimeField(
        _("Usage Date"), auto_now_add=True, help_text=_("When the units were consumed")
    )

    class Meta:
        verbose_name = _("Document Quota Usage")
        verbose_name_plural = _("Document Quota Usage Records")
        db_table = "academic_records_document_quota_usage"
        ordering = ["-usage_date"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["quota", "usage_date"]),
            models.Index(fields=["document_request"]),
        ]

    def __str__(self) -> str:
        return f"{self.quota} - {self.units_consumed} units on {self.usage_date}"
