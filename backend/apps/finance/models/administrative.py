"""Administrative fee models for cycle-change students.

This module contains models for managing administrative fees charged to students
who change academic cycles (Language→Bachelor, Bachelor→Master) or are new students.
These fees include document quotas and are charged every term until graduation.
"""

from decimal import Decimal
from typing import ClassVar

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import UserAuditModel


class AdministrativeFeeConfig(UserAuditModel):
    """Configuration for administrative fees by cycle type.

    Defines the administrative fee amounts and included document quotas
    for different types of cycle changes. These configurations are used
    to automatically generate charges each term for eligible students.
    """

    class CycleType(models.TextChoices):
        """Types of cycle changes that trigger administrative fees."""

        NEW_STUDENT = "NEW", _("New Student")
        LANG_TO_BA = "L2B", _("Language to Bachelor")
        BA_TO_MA = "B2M", _("Bachelor to Master")

    cycle_type = models.CharField(
        _("Cycle Type"),
        max_length=3,
        choices=CycleType.choices,
        unique=True,
        help_text=_("Type of cycle change this fee applies to"),
    )
    fee_amount = models.DecimalField(
        _("Fee Amount"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Administrative fee amount per term"),
    )
    included_document_units = models.PositiveIntegerField(
        _("Included Document Units"), default=10, help_text=_("Number of document units included with this fee")
    )
    quota_validity_days = models.PositiveIntegerField(
        _("Quota Validity Days"), default=120, help_text=_("Number of days the document quota is valid")
    )
    is_active = models.BooleanField(
        _("Is Active"), default=True, help_text=_("Whether this fee configuration is currently active")
    )
    effective_date = models.DateField(
        _("Effective Date"), help_text=_("Date when this configuration becomes effective")
    )
    end_date = models.DateField(
        _("End Date"), null=True, blank=True, help_text=_("Date when this configuration expires (null = current)")
    )
    notes = models.TextField(_("Notes"), blank=True, help_text=_("Internal notes about this fee configuration"))

    class Meta:
        verbose_name = _("Administrative Fee Configuration")
        verbose_name_plural = _("Administrative Fee Configurations")
        db_table = "finance_administrative_fee_config"
        ordering = ["cycle_type", "-effective_date"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["cycle_type", "is_active"]),
            models.Index(fields=["effective_date"]),
            models.Index(fields=["cycle_type", "effective_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_cycle_type_display()} - ${self.fee_amount}"

    @property
    def is_current(self) -> bool:
        """Check if this configuration is currently active."""
        today = timezone.now().date()
        return self.is_active and self.effective_date <= today and (self.end_date is None or today <= self.end_date)

    def clean(self) -> None:
        """Validate configuration data."""
        super().clean()

        if self.end_date and self.end_date <= self.effective_date:
            raise ValidationError({"end_date": _("End date must be after effective date.")})


class DocumentExcessFee(UserAuditModel):
    """Fees charged for documents exceeding quota.

    When a student requests documents that exceed their available quota,
    this model tracks the excess units and associated charges. Links to
    the invoice line item and the specific document request.
    """

    invoice_line_item = models.ForeignKey(
        "finance.InvoiceLineItem",
        on_delete=models.CASCADE,
        related_name="document_excess_fees",
        verbose_name=_("Invoice Line Item"),
        help_text=_("Invoice line item for this excess fee"),
    )
    document_request = models.ForeignKey(
        "academic_records.DocumentRequest",
        on_delete=models.PROTECT,
        related_name="excess_fees",
        verbose_name=_("Document Request"),
        help_text=_("Document request that triggered this excess fee"),
    )
    units_charged = models.PositiveIntegerField(_("Units Charged"), help_text=_("Number of excess units charged"))
    unit_price = models.DecimalField(
        _("Unit Price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Price per excess unit"),
    )

    class Meta:
        verbose_name = _("Document Excess Fee")
        verbose_name_plural = _("Document Excess Fees")
        db_table = "finance_document_excess_fee"
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["invoice_line_item"]),
            models.Index(fields=["document_request"]),
        ]

    def __str__(self) -> str:
        return f"{self.document_request} - {self.units_charged} units"

    @property
    def total_amount(self) -> Decimal:
        """Calculate total excess fee amount."""
        return Decimal(str(self.units_charged)) * self.unit_price


# Extend the InvoiceLineItem type choices
class ExtendedLineItemType(models.TextChoices):
    """Extended line item types including administrative fees."""

    # Existing types (these would be imported/extended from the main model)
    TUITION = "TUITION", _("Tuition")
    FEE = "FEE", _("Fee")
    CHARGE = "CHARGE", _("Charge")
    CREDIT = "CREDIT", _("Credit")
    DISCOUNT = "DISCOUNT", _("Discount")

    # New types for administrative fees
    ADMINISTRATIVE_FEE = "ADMIN_FEE", _("Administrative Fee")
    DOCUMENT_EXCESS = "DOC_EXCESS", _("Document Excess Fee")
