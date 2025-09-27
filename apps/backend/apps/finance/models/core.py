"""Core finance models: invoices, payments, and transactions."""

from datetime import date
from decimal import Decimal
from functools import cached_property
from typing import TYPE_CHECKING

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import (
    CharField,
    DateField,
    ForeignKey,
    Sum,
)
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import UserAuditModel

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

    from apps.enrollment.models import ClassHeaderEnrollment
    from apps.finance.models.ar_reconstruction import ARReconstructionBatch
    from apps.finance.models.pricing import FeePricing


class Currency(models.TextChoices):
    """Currency choices for financial transactions."""

    USD = "USD", _("US Dollar")
    KHR = "KHR", _("Cambodian Riel")


class Invoice(UserAuditModel):
    """Student invoice model for billing management."""

    class InvoiceStatus(models.TextChoices):
        DRAFT = "DRAFT", _("Draft")
        SENT = "SENT", _("Sent")
        PAID = "PAID", _("Paid")
        PARTIALLY_PAID = "PARTIALLY_PAID", _("Partially Paid")
        OVERDUE = "OVERDUE", _("Overdue")
        CANCELLED = "CANCELLED", _("Cancelled")
        REFUNDED = "REFUNDED", _("Refunded")

    # Invoice identification
    invoice_number: CharField = models.CharField(
        _("Invoice Number"),
        max_length=50,
        unique=True,
        help_text=_("Unique invoice identifier"),
    )

    # Student and term relationships
    student: ForeignKey = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.PROTECT,
        related_name="invoices",
        verbose_name=_("Student"),
        help_text=_("Student this invoice is for"),
    )

    term: ForeignKey = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.PROTECT,
        related_name="invoices",
        verbose_name=_("Term"),
        help_text=_("Academic term for this invoice"),
    )

    # Invoice details
    status: CharField = models.CharField(
        _("Status"),
        max_length=20,
        choices=InvoiceStatus.choices,
        default=InvoiceStatus.DRAFT,
        help_text=_("Current invoice status"),
    )

    # Dates
    issue_date: DateField = models.DateField(
        _("Issue Date"),
        default=date.today,
        help_text=_("Date invoice was issued"),
    )
    due_date: models.DateField = models.DateField(
        _("Due Date"),
        help_text=_("Date payment is due"),
    )
    sent_date: models.DateTimeField = models.DateTimeField(
        _("Sent Date"),
        null=True,
        blank=True,
        help_text=_("When invoice was sent to student"),
    )

    # Financial amounts
    subtotal: models.DecimalField = models.DecimalField(
        _("Subtotal"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Subtotal before tax"),
    )
    tax_amount: models.DecimalField = models.DecimalField(
        _("Tax Amount"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total tax amount"),
    )
    total_amount: models.DecimalField = models.DecimalField(
        _("Total Amount"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total invoice amount"),
    )
    paid_amount: models.DecimalField = models.DecimalField(
        _("Paid Amount"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Amount already paid"),
    )

    currency: models.CharField = models.CharField(
        _("Currency"),
        max_length=3,
        choices=Currency.choices,
        default=Currency.USD,
        help_text=_("Invoice currency"),
    )

    # Version tracking for optimistic locking
    version: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Version"),
        default=1,
        help_text=_("Version number for optimistic locking"),
    )

    # Additional information
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes for this invoice"),
    )

    # === LEGACY DATA PRESERVATION FIELDS ===
    is_historical: models.BooleanField = models.BooleanField(
        _("Is Historical"),
        default=False,
        help_text=_("True for invoices reconstructed from legacy data"),
    )

    legacy_ipk: models.IntegerField = models.IntegerField(
        _("Legacy IPK"),
        null=True,
        blank=True,
        help_text=_("Original IPK primary key - TRUE unique identifier"),
    )

    legacy_receipt_number: models.CharField = models.CharField(
        _("Legacy Receipt Number"),
        max_length=50,
        blank=True,
        help_text=_("Original receipt number from legacy system (display only)"),
    )

    legacy_receipt_id: models.CharField = models.CharField(
        _("Legacy Receipt ID"),
        max_length=200,
        null=True,
        blank=True,
        help_text=_("Full receipt ID with clerk information from legacy system"),
    )

    legacy_notes: models.TextField = models.TextField(
        _("Legacy Notes"),
        blank=True,
        help_text=_("Original notes from legacy receipt"),
    )

    legacy_processing_clerk: models.CharField = models.CharField(
        _("Legacy Processing Clerk"),
        max_length=100,
        blank=True,
        help_text=_("Clerk who processed the original receipt"),
    )

    original_amount: models.DecimalField = models.DecimalField(
        _("Original Amount"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Original amount from legacy receipt before discounts"),
    )

    discount_applied: models.DecimalField = models.DecimalField(
        _("Discount Applied"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total discount applied from legacy receipt"),
    )

    reconstruction_status: models.CharField = models.CharField(
        _("Reconstruction Status"),
        max_length=20,
        blank=True,
        help_text=_("Status of A/R reconstruction process"),
    )

    reconstruction_batch: "ForeignKey[ARReconstructionBatch | None, ARReconstructionBatch | None]" = models.ForeignKey(
        "finance.ARReconstructionBatch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reconstructed_invoices",
        help_text=_("A/R reconstruction batch that created this invoice"),
    )

    needs_reprocessing: models.BooleanField = models.BooleanField(
        _("Needs Reprocessing"),
        default=False,
        help_text=_("True if invoice needs reprocessing due to new data"),
    )

    reprocessing_reason: models.TextField = models.TextField(
        _("Reprocessing Reason"),
        blank=True,
        help_text=_("Why this invoice needs reprocessing"),
    )

    class Meta:
        db_table = "finance_invoice"
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")
        ordering = ["-issue_date", "invoice_number"]
        indexes = [
            models.Index(fields=["student", "term"]),
            models.Index(fields=["status", "due_date"]),
            models.Index(fields=["issue_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.invoice_number} - {self.student}"

    @cached_property
    def amount_due(self) -> Decimal:
        """Calculate amount still due on this invoice."""
        return max(Decimal("0.00"), self.total_amount - self.paid_amount)

    @cached_property
    def is_overdue(self) -> bool:
        """Check if invoice is overdue."""
        return date.today() > self.due_date and self.amount_due > 0

    def calculate_totals(self) -> None:
        """Recalculate invoice totals from line items."""
        line_items = self.line_items.all()
        self.subtotal = sum(item.line_total for item in line_items)
        # Tax calculation would go here if needed
        self.total_amount = self.subtotal + self.tax_amount


class InvoiceLineItem(UserAuditModel):
    """Individual line items on student invoices."""

    class LineItemType(models.TextChoices):
        COURSE = "COURSE", _("Course Enrollment")
        FEE = "FEE", _("Fee")
        ADJUSTMENT = "ADJUSTMENT", _("Adjustment")
        REFUND = "REFUND", _("Refund")
        ADMIN_FEE = "ADMIN_FEE", _("Administrative Fee")
        DOC_EXCESS = "DOC_EXCESS", _("Document Excess Fee")

    # Parent invoice
    invoice: models.ForeignKey = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="line_items",
        verbose_name=_("Invoice"),
    )

    # Line item details
    line_item_type: models.CharField = models.CharField(
        _("Line Item Type"),
        max_length=20,
        choices=LineItemType.choices,
        help_text=_("Type of charge"),
    )

    description: models.CharField = models.CharField(
        _("Description"),
        max_length=255,
        help_text=_("Description of this charge"),
    )

    # Pricing information
    unit_price: models.DecimalField = models.DecimalField(
        _("Unit Price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Price per unit"),
    )

    quantity: models.DecimalField = models.DecimalField(
        _("Quantity"),
        max_digits=6,
        decimal_places=2,
        default=Decimal("1.00"),
        validators=[MinValueValidator(Decimal("0.01"))],
        help_text=_("Quantity being charged"),
    )

    line_total: models.DecimalField = models.DecimalField(
        _("Line Total"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Total for this line (unit_price x quantity)"),
    )

    # Optional references to source records
    enrollment: "ForeignKey[ClassHeaderEnrollment | None, ClassHeaderEnrollment | None]" = models.ForeignKey(
        "enrollment.ClassHeaderEnrollment",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_line_items",
        verbose_name=_("Enrollment"),
        help_text=_("Class enrollment this charge is for (if applicable)"),
    )

    fee_pricing: "ForeignKey[FeePricing | None, FeePricing | None]" = models.ForeignKey(
        "finance.FeePricing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoice_line_items",
        verbose_name=_("Fee Pricing"),
        help_text=_("Fee pricing record this charge is based on"),
    )

    # === LEGACY DATA PRESERVATION FIELDS ===
    legacy_program_code: models.CharField = models.CharField(
        _("Legacy Program Code"),
        max_length=50,
        blank=True,
        help_text=_("Program code from legacy receipt"),
    )

    legacy_course_level: models.CharField = models.CharField(
        _("Legacy Course Level"),
        max_length=50,
        blank=True,
        help_text=_("Course level from legacy receipt"),
    )

    pricing_method_used: models.CharField = models.CharField(
        _("Pricing Method Used"),
        max_length=50,
        blank=True,
        help_text=_("Method used to determine pricing"),
    )

    pricing_confidence: models.CharField = models.CharField(
        _("Pricing Confidence"),
        max_length=20,
        blank=True,
        help_text=_("Confidence level of pricing reconstruction"),
    )

    base_amount: models.DecimalField = models.DecimalField(
        _("Base Amount"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Base amount before discounts"),
    )

    discount_amount: models.DecimalField = models.DecimalField(
        _("Discount Amount"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Discount applied to this line item"),
    )

    discount_reason: models.TextField = models.TextField(
        _("Discount Reason"),
        blank=True,
        help_text=_("Reason for discount from legacy notes"),
    )

    class Meta:
        db_table = "finance_invoice_line_item"
        verbose_name = _("Invoice Line Item")
        verbose_name_plural = _("Invoice Line Items")
        ordering = ["invoice", "id"]

    def __str__(self) -> str:
        return f"{self.invoice.invoice_number} - {self.description}"  # type: ignore[attr-defined]

    def save(self, *args, **kwargs):
        """Calculate line total on save."""
        self.line_total = self.unit_price * self.quantity
        super().save(*args, **kwargs)


class Payment(UserAuditModel):
    """Payment records for invoice payments."""

    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        COMPLETED = "COMPLETED", _("Completed")
        FAILED = "FAILED", _("Failed")
        CANCELLED = "CANCELLED", _("Cancelled")
        REFUNDED = "REFUNDED", _("Refunded")

    class PaymentMethod(models.TextChoices):
        CASH = "CASH", _("Cash")
        CREDIT_CARD = "CREDIT_CARD", _("Credit Card")
        BANK_TRANSFER = "BANK_TRANSFER", _("Bank Transfer")
        CHECK = "CHECK", _("Check")
        ONLINE = "ONLINE", _("Online Payment")
        SCHOLARSHIP = "SCHOLARSHIP", _("Scholarship")
        OTHER = "OTHER", _("Other")

    # Payment identification
    payment_reference: models.CharField = models.CharField(
        _("Payment Reference"),
        max_length=50,
        unique=True,
        help_text=_("Unique payment reference number"),
    )

    # Invoice relationship
    invoice: models.ForeignKey = models.ForeignKey(
        Invoice,
        on_delete=models.PROTECT,
        related_name="payments",
        verbose_name=_("Invoice"),
        help_text=_("Invoice this payment is for"),
    )

    # Payment details
    amount: models.DecimalField = models.DecimalField(
        _("Amount"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Payment amount (negative for refunds)"),
    )

    currency: models.CharField = models.CharField(
        _("Currency"),
        max_length=3,
        choices=Currency.choices,
        default=Currency.USD,
        help_text=_("Payment currency"),
    )

    payment_method: models.CharField = models.CharField(
        _("Payment Method"),
        max_length=20,
        choices=PaymentMethod.choices,
        help_text=_("How payment was made"),
    )

    status: models.CharField = models.CharField(
        _("Status"),
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        help_text=_("Current payment status"),
    )

    # Dates
    payment_date: models.DateTimeField = models.DateTimeField(
        _("Payment Date"),
        help_text=_("When payment was made"),
    )
    processed_date: models.DateTimeField = models.DateTimeField(
        _("Processed Date"),
        null=True,
        blank=True,
        help_text=_("When payment was processed"),
    )

    # Payer information
    payer_name: models.CharField = models.CharField(
        _("Payer Name"),
        max_length=255,
        blank=True,
        help_text=_("Name of person making payment"),
    )

    external_reference: models.CharField = models.CharField(
        _("External Reference"),
        max_length=100,
        blank=True,
        help_text=_("External system reference (bank ref, transaction ID, etc.)"),
    )

    # Processing information
    processed_by: "ForeignKey[AbstractUser | None, AbstractUser | None]" = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="processed_payments",
        verbose_name=_("Processed By"),
        help_text=_("User who processed this payment"),
    )

    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this payment"),
    )

    # === LEGACY DATA PRESERVATION FIELDS ===
    is_historical_payment: models.BooleanField = models.BooleanField(
        _("Is Historical Payment"),
        default=False,
        help_text=_("True for payments reconstructed from legacy data"),
    )

    legacy_ipk: models.IntegerField = models.IntegerField(
        _("Legacy IPK"),
        null=True,
        blank=True,
        help_text=_("Original IPK primary key - TRUE unique identifier"),
    )

    legacy_receipt_reference: models.CharField = models.CharField(
        _("Legacy Receipt Reference"),
        max_length=50,
        blank=True,
        help_text=_("Original receipt reference from legacy system (display only)"),
    )

    legacy_processing_clerk: models.CharField = models.CharField(
        _("Legacy Processing Clerk"),
        max_length=100,
        blank=True,
        help_text=_("Clerk who processed the original receipt"),
    )

    legacy_business_notes: models.TextField = models.TextField(
        _("Legacy Business Notes"),
        blank=True,
        help_text=_("Original business notes from legacy receipt"),
    )

    legacy_receipt_full_id: models.CharField = models.CharField(
        _("Legacy Receipt Full ID"),
        max_length=200,
        blank=True,
        help_text=_("Full receipt ID from legacy system"),
    )

    legacy_program_code: models.CharField = models.CharField(
        _("Legacy Program Code"),
        max_length=50,
        blank=True,
        help_text=_("Program code from legacy receipt"),
    )

    class Meta:
        db_table = "finance_payment"
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        ordering = ["-payment_date"]
        indexes = [
            models.Index(fields=["invoice", "status"]),
            models.Index(fields=["payment_date"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.payment_reference} - {self.amount} {self.currency}"


class FinancialTransaction(UserAuditModel):
    """Comprehensive financial transaction log for audit trails."""

    class TransactionType(models.TextChoices):
        INVOICE_CREATED = "INVOICE_CREATED", _("Invoice Created")
        PAYMENT_RECEIVED = "PAYMENT_RECEIVED", _("Payment Received")
        PAYMENT_REFUNDED = "PAYMENT_REFUNDED", _("Payment Refunded")
        ADJUSTMENT = "ADJUSTMENT", _("Manual Adjustment")
        WRITEOFF = "WRITEOFF", _("Bad Debt Write-off")

    # Transaction identification
    transaction_id: models.CharField = models.CharField(
        _("Transaction ID"),
        max_length=50,
        unique=True,
        help_text=_("Unique transaction identifier"),
    )

    transaction_type: models.CharField = models.CharField(
        _("Transaction Type"),
        max_length=20,
        choices=TransactionType.choices,
        help_text=_("Type of financial transaction"),
    )

    # Student and financial details
    student: models.ForeignKey = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.PROTECT,
        related_name="financial_transactions",
        verbose_name=_("Student"),
        help_text=_("Student this transaction affects"),
    )

    amount: models.DecimalField = models.DecimalField(
        _("Amount"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Transaction amount (positive for charges, negative for credits)"),
    )

    currency: models.CharField = models.CharField(
        _("Currency"),
        max_length=3,
        choices=Currency.choices,
        default=Currency.USD,
        help_text=_("Transaction currency"),
    )

    # Transaction details
    transaction_date: models.DateTimeField = models.DateTimeField(
        _("Transaction Date"),
        default=timezone.now,
        help_text=_("When transaction occurred"),
    )

    description: models.CharField = models.CharField(
        _("Description"),
        max_length=255,
        help_text=_("Description of the transaction"),
    )

    # Related records
    invoice: "ForeignKey[Invoice | None, Invoice | None]" = models.ForeignKey(
        Invoice,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
        verbose_name=_("Invoice"),
        help_text=_("Related invoice (if applicable)"),
    )

    payment: "ForeignKey[Payment | None, Payment | None]" = models.ForeignKey(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
        verbose_name=_("Payment"),
        help_text=_("Related payment (if applicable)"),
    )

    # Processing information
    processed_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="processed_transactions",
        verbose_name=_("Processed By"),
        help_text=_("User who processed this transaction"),
    )

    reference_data: models.JSONField = models.JSONField(
        _("Reference Data"),
        default=dict,
        blank=True,
        help_text=_("Additional reference data for this transaction"),
    )

    class Meta:
        db_table = "finance_financialtransaction"
        verbose_name = _("Financial Transaction")
        verbose_name_plural = _("Financial Transactions")
        ordering = ["-transaction_date"]
        indexes = [
            models.Index(fields=["student", "transaction_date"]),
            models.Index(fields=["transaction_type", "transaction_date"]),
            models.Index(fields=["invoice"]),
            models.Index(fields=["payment"]),
        ]

    def __str__(self) -> str:
        return f"{self.transaction_id} - {self.transaction_type}"


class CashierSession(UserAuditModel):
    """Cashier session tracking for daily cash handling."""

    # Session identification
    session_number: models.CharField = models.CharField(
        _("Session Number"),
        max_length=50,
        unique=True,
        null=True,
        blank=True,
        default="DEFAULT-001",
        help_text=_("Unique session identifier"),
    )

    cashier: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="cashier_sessions",
        verbose_name=_("Cashier"),
        help_text=_("User operating the cashier session"),
    )

    # Session timing
    opened_at: models.DateTimeField = models.DateTimeField(
        _("Opened At"),
        null=True,
        blank=True,
        default=timezone.now,
        help_text=_("When session was opened"),
    )

    closed_at: models.DateTimeField = models.DateTimeField(
        _("Closed At"),
        null=True,
        blank=True,
        help_text=_("When session was closed"),
    )

    # Financial totals
    opening_balance: models.DecimalField = models.DecimalField(
        _("Opening Balance"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        default=Decimal("0.00"),
        help_text=_("Cash drawer opening balance"),
    )

    closing_balance: models.DecimalField = models.DecimalField(
        _("Closing Balance"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Cash drawer closing balance"),
    )

    expected_balance: models.DecimalField = models.DecimalField(
        _("Expected Balance"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Expected balance based on transactions"),
    )

    # Session status
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"),
        null=True,
        blank=True,
        default=True,
        help_text=_("Whether this session is currently active"),
    )

    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Session notes and observations"),
    )

    class Meta:
        db_table = "finance_cashier_session"
        verbose_name = _("Cashier Session")
        verbose_name_plural = _("Cashier Sessions")
        ordering = ["-opened_at"]
        indexes = [
            models.Index(fields=["cashier", "opened_at"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.session_number} - {self.cashier.email}"  # type: ignore[attr-defined]

    @cached_property
    def cash_payments_total(self) -> Decimal:
        """Calculate total cash payments for this session."""
        if not self.is_active and not self.closed_at:
            return Decimal("0.00")

        end_time = self.closed_at or timezone.now()

        cash_payments = Payment.objects.filter(
            payment_method=Payment.PaymentMethod.CASH,
            payment_date__gte=self.opened_at,
            payment_date__lt=end_time,
            status=Payment.PaymentStatus.COMPLETED,
        ).aggregate(total=Sum("amount"))

        return cash_payments["total"] or Decimal("0.00")

    @cached_property
    def variance(self) -> Decimal:
        """Calculate variance between expected and actual closing balance."""
        if not self.closing_balance or not self.expected_balance:
            return Decimal("0.00")
        return self.closing_balance - self.expected_balance

    def close_session(self, closing_balance: Decimal, closed_by) -> None:
        """Close the cashier session."""
        self.closing_balance = closing_balance
        self.expected_balance = self.opening_balance + self.cash_payments_total
        self.closed_at = timezone.now()
        self.is_active = False
        self.updated_by = closed_by
        self.save()
