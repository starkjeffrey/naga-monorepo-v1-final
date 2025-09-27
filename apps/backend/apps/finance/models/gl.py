"""General Ledger and accounting integration models."""

from datetime import date
from decimal import Decimal
from functools import cached_property
from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import UserAuditModel

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser
    from django.db.models import ForeignKey


from .pricing import FeeType


class GLAccount(UserAuditModel):
    """General Ledger account for financial reporting and integration.

    Per user requirements: "Support G/L account mapping" for level testing fees
    and other financial transactions. Provides chart of accounts functionality
    for proper accounting integration.
    """

    class AccountType(models.TextChoices):
        """Types of G/L accounts."""

        ASSET = "ASSET", _("Asset")
        LIABILITY = "LIABILITY", _("Liability")
        EQUITY = "EQUITY", _("Equity")
        REVENUE = "REVENUE", _("Revenue")
        EXPENSE = "EXPENSE", _("Expense")

    class AccountCategory(models.TextChoices):
        """Account categories for reporting."""

        CURRENT_ASSET = "CURRENT_ASSET", _("Current Asset")
        FIXED_ASSET = "FIXED_ASSET", _("Fixed Asset")
        CURRENT_LIABILITY = "CURRENT_LIABILITY", _("Current Liability")
        LONG_TERM_LIABILITY = "LONG_TERM_LIABILITY", _("Long-term Liability")
        OPERATING_REVENUE = "OPERATING_REVENUE", _("Operating Revenue")
        NON_OPERATING_REVENUE = "NON_OPERATING_REVENUE", _("Non-operating Revenue")
        OPERATING_EXPENSE = "OPERATING_EXPENSE", _("Operating Expense")
        ADMINISTRATIVE_EXPENSE = "ADMINISTRATIVE_EXPENSE", _("Administrative Expense")

    account_code: models.CharField = models.CharField(
        _("Account Code"),
        max_length=20,
        unique=True,
        help_text=_("Unique G/L account code (e.g., '4100-LT')"),
    )
    account_name: models.CharField = models.CharField(
        _("Account Name"),
        max_length=100,
        help_text=_("Descriptive name for this account"),
    )
    account_type: models.CharField = models.CharField(
        _("Account Type"),
        max_length=20,
        choices=AccountType.choices,
        help_text=_("Primary classification of this account"),
    )
    account_category: models.CharField = models.CharField(
        _("Account Category"),
        max_length=30,
        choices=AccountCategory.choices,
        help_text=_("Detailed category for reporting purposes"),
    )
    parent_account: "ForeignKey[GLAccount | None, GLAccount | None]" = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="sub_accounts",
        verbose_name=_("Parent Account"),
        help_text=_("Parent account for hierarchical reporting"),
    )
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this account is currently in use"),
    )
    requires_department: models.BooleanField = models.BooleanField(
        _("Requires Department"),
        default=False,
        help_text=_("Whether transactions to this account require department codes"),
    )
    description: models.TextField = models.TextField(
        _("Description"),
        blank=True,
        help_text=_("Detailed description of this account's purpose"),
    )

    class Meta:
        db_table = "finance_gl_account"
        verbose_name = _("G/L Account")
        verbose_name_plural = _("G/L Accounts")
        ordering = ["account_code"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["account_type", "account_category"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["parent_account"]),
        ]

    def __str__(self) -> str:
        return f"{self.account_code} - {self.account_name}"

    @cached_property
    def full_account_path(self) -> str:
        """Get full hierarchical path for this account (cached)."""
        if self.parent_account:
            return f"{self.parent_account.full_account_path} > {self.account_name}"
        return self.account_name

    def clean(self) -> None:
        """Validate G/L account data."""
        super().clean()

        # Validate account code format
        if not self.account_code.replace("-", "").replace("_", "").isalnum():
            raise ValidationError(
                {"account_code": _("Account code must contain only letters, numbers, hyphens, and underscores.")},
            )

        # Prevent circular parent references
        if self.parent_account == self:
            raise ValidationError({"parent_account": _("Account cannot be its own parent.")})

    def save(self, *args, **kwargs):
        """Override save to clear cached properties when relevant fields change."""
        # Clear cached property if account_name or parent_account changes
        if hasattr(self, "_full_account_path"):
            del self._full_account_path
        super().save(*args, **kwargs)


class FeeGLMapping(UserAuditModel):
    """Mapping between fee types and G/L accounts for accounting integration.

    Per user requirements: Maps level testing fees and other fee types to
    appropriate G/L accounts for financial reporting and audit trails.
    """

    fee_type: models.CharField = models.CharField(
        _("Fee Type"),
        max_length=20,
        choices=FeeType,
        help_text=_("Type of fee this mapping applies to"),
    )
    fee_code: models.CharField = models.CharField(
        _("Fee Code"),
        max_length=50,
        help_text=_("Internal fee code (e.g., 'LT_PLACEMENT')"),
    )
    revenue_account: models.ForeignKey = models.ForeignKey(
        GLAccount,
        on_delete=models.PROTECT,
        related_name="fee_revenue_mappings",
        verbose_name=_("Revenue Account"),
        help_text=_("G/L account for recording fee revenue"),
    )
    receivable_account: "ForeignKey[GLAccount | None, GLAccount | None]" = models.ForeignKey(
        GLAccount,
        on_delete=models.PROTECT,
        related_name="fee_receivable_mappings",
        null=True,
        blank=True,
        verbose_name=_("Receivable Account"),
        help_text=_("G/L account for unpaid fees (optional)"),
    )
    effective_date: models.DateField = models.DateField(
        _("Effective Date"),
        default=date.today,
        help_text=_("Date this mapping becomes effective"),
    )
    end_date: models.DateField = models.DateField(
        _("End Date"),
        null=True,
        blank=True,
        help_text=_("Date this mapping expires (null = indefinite)"),
    )

    class Meta:
        db_table = "finance_fee_gl_mapping"
        verbose_name = _("Fee G/L Mapping")
        verbose_name_plural = _("Fee G/L Mappings")
        unique_together = [["fee_code", "effective_date"]]
        ordering = ["fee_code", "-effective_date"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["fee_code", "effective_date"]),
            models.Index(fields=["fee_type"]),
            models.Index(fields=["revenue_account"]),
        ]

    def __str__(self) -> str:
        return f"{self.fee_code} → {self.revenue_account.account_code}"  # type: ignore[attr-defined]

    @property
    def is_active(self) -> bool:
        """Check if this mapping is currently active."""
        today = timezone.now().date()
        return self.effective_date <= today and (self.end_date is None or today <= self.end_date)

    def clean(self) -> None:
        """Validate fee G/L mapping data."""
        super().clean()

        if self.end_date and self.end_date <= self.effective_date:
            raise ValidationError({"end_date": _("End date must be after effective date.")})

        # Validate that revenue account is actually a revenue account
        if self.revenue_account and self.revenue_account.account_type != GLAccount.AccountType.REVENUE:  # type: ignore[attr-defined]
            raise ValidationError({"revenue_account": _("Revenue account must be of type 'Revenue'.")})


class JournalEntry(UserAuditModel):
    """Journal entry for G/L integration and financial reporting.

    Represents a complete journal entry with multiple line items following
    double-entry bookkeeping principles. Used for monthly summarization
    and G/L feed generation.
    """

    class EntryType(models.TextChoices):
        """Types of journal entries for service accounting (cash basis)."""

        REVENUE = "REVENUE", _("Revenue Receipt")  # Cash received
        PAYMENT = "PAYMENT", _("Payment Receipt")
        REFUND = "REFUND", _("Refund Issued")
        ADJUSTMENT = "ADJUSTMENT", _("Adjustment Entry")
        TRANSFER = "TRANSFER", _("Transfer Entry")
        REVERSAL = "REVERSAL", _("Reversal Entry")
        CLOSING = "CLOSING", _("Closing Entry")

    class EntryStatus(models.TextChoices):
        """Journal entry statuses."""

        DRAFT = "DRAFT", _("Draft")
        PENDING_REVIEW = "PENDING_REVIEW", _("Pending Review")
        APPROVED = "APPROVED", _("Approved")
        POSTED = "POSTED", _("Posted to G/L")
        REVERSED = "REVERSED", _("Reversed")
        REJECTED = "REJECTED", _("Rejected")

    entry_number: models.CharField = models.CharField(
        _("Entry Number"),
        max_length=50,
        unique=True,
        help_text=_("Unique journal entry number (e.g., 'JE-2025-01-001')"),
    )
    entry_date: models.DateField = models.DateField(
        _("Entry Date"),
        help_text=_("Effective date of this journal entry"),
    )
    accounting_period: models.CharField = models.CharField(
        _("Accounting Period"),
        max_length=7,
        help_text=_("Accounting period (YYYY-MM format)"),
        db_index=True,
    )
    entry_type: models.CharField = models.CharField(
        _("Entry Type"),
        max_length=20,
        choices=EntryType.choices,
        help_text=_("Type of journal entry"),
    )
    status: models.CharField = models.CharField(
        _("Status"),
        max_length=20,
        choices=EntryStatus.choices,
        default=EntryStatus.DRAFT,
        help_text=_("Current status of this entry"),
    )
    description: models.CharField = models.CharField(
        _("Description"),
        max_length=200,
        help_text=_("Brief description of this journal entry"),
    )
    reference_number: models.CharField = models.CharField(
        _("Reference Number"),
        max_length=50,
        blank=True,
        help_text=_("External reference number if applicable"),
    )

    # Totals (cached for performance)
    total_debits: models.DecimalField = models.DecimalField(
        _("Total Debits"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Sum of all debit amounts"),
    )
    total_credits: models.DecimalField = models.DecimalField(
        _("Total Credits"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Sum of all credit amounts"),
    )

    # Workflow fields
    prepared_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="journal_entries_prepared",
        verbose_name=_("Prepared By"),
        help_text=_("User who prepared this entry"),
    )
    approved_by: "ForeignKey[AbstractUser | None, AbstractUser | None]" = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="journal_entries_approved",
        verbose_name=_("Approved By"),
        help_text=_("User who approved this entry"),
    )
    approved_date: models.DateTimeField = models.DateTimeField(
        _("Approved Date"),
        null=True,
        blank=True,
        help_text=_("When this entry was approved"),
    )
    posted_date: models.DateTimeField = models.DateTimeField(
        _("Posted Date"),
        null=True,
        blank=True,
        help_text=_("When this entry was posted to G/L"),
    )

    # Reversal tracking
    reverses_entry: "ForeignKey[JournalEntry | None, JournalEntry | None]" = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reversal_entries",
        verbose_name=_("Reverses Entry"),
        help_text=_("Original entry being reversed"),
    )

    # Additional metadata
    source_system: models.CharField = models.CharField(
        _("Source System"),
        max_length=50,
        default="NAGA_SIS",
        help_text=_("System that generated this entry"),
    )
    batch_id: models.CharField = models.CharField(
        _("Batch ID"),
        max_length=50,
        blank=True,
        db_index=True,
        help_text=_("Batch identifier for grouped processing"),
    )
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes or comments"),
    )

    class Meta:
        db_table = "finance_journal_entry"
        verbose_name = _("Journal Entry")
        verbose_name_plural = _("Journal Entries")
        ordering = ["-entry_date", "-entry_number"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["accounting_period", "status"]),
            models.Index(fields=["entry_type", "entry_date"]),
            models.Index(fields=["batch_id"]),
            models.Index(fields=["status", "posted_date"]),
        ]
        permissions = [
            ("can_approve_journal_entries", "Can approve journal entries"),
            ("can_post_journal_entries", "Can post journal entries to G/L"),
        ]

    def __str__(self) -> str:
        return f"{self.entry_number} - {self.description}"

    @property
    def is_balanced(self) -> bool:
        """Check if journal entry is balanced (debits = credits)."""
        # An entry with no lines is not balanced
        if self.total_debits == Decimal("0.00") and self.total_credits == Decimal("0.00"):
            return False
        return self.total_debits == self.total_credits

    @property
    def balance_amount(self) -> Decimal:
        """Get the imbalance amount (should be zero)."""
        return abs(self.total_debits - self.total_credits)

    def clean(self) -> None:
        """Validate journal entry data."""
        super().clean()

        # Validate accounting period format
        import re

        if self.accounting_period and not re.match(r"^\d{4}-\d{2}$", self.accounting_period):
            raise ValidationError({"accounting_period": _("Accounting period must be in YYYY-MM format.")})

        # Validate entry date is within accounting period
        if self.entry_date and self.accounting_period:
            period_year, period_month = self.accounting_period.split("-")
            if self.entry_date.year != int(period_year) or self.entry_date.month != int(period_month):
                raise ValidationError({"entry_date": _("Entry date must be within the specified accounting period.")})

    def calculate_totals(self) -> None:
        """Recalculate total debits and credits from line items."""
        from django.db.models import Sum

        totals = self.line_items.aggregate(total_debits=Sum("debit_amount"), total_credits=Sum("credit_amount"))

        self.total_debits = totals["total_debits"] or Decimal("0.00")
        self.total_credits = totals["total_credits"] or Decimal("0.00")
        self.save(update_fields=["total_debits", "total_credits"])

    def approve(self, user) -> None:
        """Approve this journal entry."""
        if not self.is_balanced:
            raise ValidationError(_("Cannot approve unbalanced journal entry."))

        self.status = self.EntryStatus.APPROVED
        self.approved_by = user
        self.approved_date = timezone.now()
        self.save(update_fields=["status", "approved_by", "approved_date"])

    def post_to_gl(self) -> None:
        """Mark entry as posted to G/L."""
        if self.status != self.EntryStatus.APPROVED:
            raise ValidationError(_("Only approved entries can be posted to G/L."))

        self.status = self.EntryStatus.POSTED
        self.posted_date = timezone.now()
        self.save(update_fields=["status", "posted_date"])


class JournalEntryLine(UserAuditModel):
    """Individual line item within a journal entry.

    Represents a single debit or credit to a G/L account as part of
    a journal entry. Follows double-entry bookkeeping principles.
    """

    journal_entry: models.ForeignKey = models.ForeignKey(
        JournalEntry,
        on_delete=models.CASCADE,
        related_name="line_items",
        verbose_name=_("Journal Entry"),
        help_text=_("Parent journal entry"),
    )
    line_number: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Line Number"),
        help_text=_("Sequential line number within the entry"),
    )
    gl_account: models.ForeignKey = models.ForeignKey(
        GLAccount,
        on_delete=models.PROTECT,
        related_name="journal_lines",
        verbose_name=_("G/L Account"),
        help_text=_("General ledger account"),
    )

    # Amounts (only one should be non-zero)
    debit_amount: models.DecimalField = models.DecimalField(
        _("Debit Amount"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
        help_text=_("Debit amount (increases assets/expenses)"),
    )
    credit_amount: models.DecimalField = models.DecimalField(
        _("Credit Amount"),
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
        help_text=_("Credit amount (increases liabilities/revenue)"),
    )

    # Reference information
    description: models.CharField = models.CharField(
        _("Line Description"),
        max_length=200,
        help_text=_("Description of this line item"),
    )
    reference_type: models.CharField = models.CharField(
        _("Reference Type"),
        max_length=50,
        blank=True,
        help_text=_("Type of reference (e.g., 'INVOICE', 'PAYMENT')"),
    )
    reference_id: models.CharField = models.CharField(
        _("Reference ID"),
        max_length=50,
        blank=True,
        help_text=_("ID of referenced object"),
    )

    # Optional dimensions
    department_code: models.CharField = models.CharField(
        _("Department Code"),
        max_length=20,
        blank=True,
        help_text=_("Department code for cost allocation"),
    )
    project_code: models.CharField = models.CharField(
        _("Project Code"),
        max_length=20,
        blank=True,
        help_text=_("Project code for tracking"),
    )

    class Meta:
        db_table = "finance_journal_entry_line"
        verbose_name = _("Journal Entry Line")
        verbose_name_plural = _("Journal Entry Lines")
        ordering = ["journal_entry", "line_number"]
        unique_together = [["journal_entry", "line_number"]]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["gl_account", "journal_entry"]),
            models.Index(fields=["reference_type", "reference_id"]),
        ]

    def __str__(self) -> str:
        if self.debit_amount > 0:
            return f"Dr {self.gl_account.account_code} {self.debit_amount}"  # type: ignore[attr-defined]
        return f"Cr {self.gl_account.account_code} {self.credit_amount}"  # type: ignore[attr-defined]

    def clean(self) -> None:
        """Validate journal entry line data."""
        super().clean()

        # Ensure only debit or credit is set, not both
        if self.debit_amount > 0 and self.credit_amount > 0:
            raise ValidationError(_("A line can have either debit or credit amount, not both."))

        # Ensure at least one amount is set
        if self.debit_amount == 0 and self.credit_amount == 0:
            raise ValidationError(_("Either debit or credit amount must be greater than zero."))

        # Validate department requirement
        if self.gl_account and self.gl_account.requires_department and not self.department_code:  # type: ignore[attr-defined]
            raise ValidationError({"department_code": _("Department code is required for this G/L account.")})


class GLBatch(UserAuditModel):
    """Batch of journal entries for G/L export.

    Groups journal entries for batch processing and export to external
    G/L systems. Tracks export status and provides audit trail.
    """

    class BatchStatus(models.TextChoices):
        """Batch processing statuses."""

        PENDING = "PENDING", _("Pending")
        PROCESSING = "PROCESSING", _("Processing")
        EXPORTED = "EXPORTED", _("Exported")
        FAILED = "FAILED", _("Failed")
        PARTIAL = "PARTIAL", _("Partially Exported")

    batch_number: models.CharField = models.CharField(
        _("Batch Number"),
        max_length=50,
        unique=True,
        help_text=_("Unique batch identifier"),
    )
    batch_date: models.DateField = models.DateField(
        _("Batch Date"),
        default=date.today,
        help_text=_("Date this batch was created"),
    )
    accounting_period: models.CharField = models.CharField(
        _("Accounting Period"),
        max_length=7,
        help_text=_("Accounting period for this batch (YYYY-MM)"),
        db_index=True,
    )
    status: models.CharField = models.CharField(
        _("Status"),
        max_length=20,
        choices=BatchStatus.choices,
        default=BatchStatus.PENDING,
        help_text=_("Current batch status"),
    )

    # Statistics
    total_entries: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Total Entries"),
        default=0,
        help_text=_("Number of journal entries in this batch"),
    )
    total_amount: models.DecimalField = models.DecimalField(
        _("Total Amount"),
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text=_("Total debit amount in this batch"),
    )

    # Export tracking
    export_file: models.CharField = models.CharField(
        _("Export File"),
        max_length=255,
        blank=True,
        help_text=_("Path to exported file"),
    )
    exported_by: "ForeignKey[AbstractUser | None, AbstractUser | None]" = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="gl_batches_exported",
        verbose_name=_("Exported By"),
        help_text=_("User who exported this batch"),
    )
    exported_date: models.DateTimeField = models.DateTimeField(
        _("Exported Date"),
        null=True,
        blank=True,
        help_text=_("When this batch was exported"),
    )

    # Error tracking
    error_message: models.TextField = models.TextField(
        _("Error Message"),
        blank=True,
        help_text=_("Error details if export failed"),
    )

    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this batch"),
    )

    class Meta:
        db_table = "finance_gl_batch"
        verbose_name = _("G/L Batch")
        verbose_name_plural = _("G/L Batches")
        ordering = ["-batch_date", "-batch_number"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["accounting_period", "status"]),
            models.Index(fields=["status", "batch_date"]),
        ]

    def __str__(self) -> str:
        return f"Batch {self.batch_number} - {self.accounting_period}"

    def add_journal_entry(self, journal_entry: JournalEntry) -> None:
        """Add a journal entry to this batch."""
        journal_entry.batch_id = self.batch_number
        journal_entry.save(update_fields=["batch_id"])

        # Update statistics
        self.total_entries = JournalEntry.objects.filter(batch_id=self.batch_number).count()
        self.total_amount = JournalEntry.objects.filter(batch_id=self.batch_number).aggregate(
            total=models.Sum("total_debits"),
        )["total"] or Decimal("0.00")

        self.save(update_fields=["total_entries", "total_amount"])
