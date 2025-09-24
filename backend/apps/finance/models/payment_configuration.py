"""Payment configuration models.

This model was moved from apps.settings to maintain proper domain boundaries.
It handles payment method configuration with processing fees and settings.
"""

from decimal import Decimal
from typing import ClassVar

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import UserAuditModel


class PaymentConfiguration(UserAuditModel):
    """Configurable payment methods with processing fees and settings.

    This model allows configuration of payment methods including their
    processing fees, approval requirements, and method-specific settings.
    """

    class MethodType(models.TextChoices):
        CASH = "cash", _("Cash")
        BANK_TRANSFER = "bank_transfer", _("Bank Transfer")
        CREDIT_CARD = "credit_card", _("Credit Card")
        MOBILE_PAYMENT = "mobile_payment", _("Mobile Payment")
        SCHOLARSHIP = "scholarship", _("Scholarship")
        INSTALLMENT = "installment", _("Installment Plan")

    name: models.CharField = models.CharField(
        _("Method Name"), max_length=100, help_text=_("Display name for this payment method")
    )
    method_type: models.CharField = models.CharField(
        _("Method Type"), max_length=20, choices=MethodType.choices, help_text=_("Type of payment method")
    )
    description: models.TextField = models.TextField(
        _("Description"), blank=True, help_text=_("Detailed description or instructions")
    )
    is_enabled: models.BooleanField = models.BooleanField(
        _("Is Enabled"), default=True, help_text=_("Whether this method is currently available")
    )
    requires_approval: models.BooleanField = models.BooleanField(
        _("Requires Approval"), default=False, help_text=_("Whether payments require manual approval")
    )
    processing_fee_percentage: models.DecimalField = models.DecimalField(
        _("Processing Fee Percentage"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Processing fee as percentage of payment amount"),
    )
    processing_fee_fixed: models.DecimalField = models.DecimalField(
        _("Processing Fee Fixed"),
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0)],
        help_text=_("Fixed processing fee amount"),
    )
    configuration = models.JSONField(
        _("Configuration"), default=dict, blank=True, help_text=_("Method-specific configuration options")
    )
    display_order: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Display Order"), default=0, help_text=_("Order for displaying methods")
    )

    class Meta:
        verbose_name = _("Payment Configuration")
        verbose_name_plural = _("Payment Configurations")
        ordering = ["display_order", "name"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["method_type", "is_enabled"]),
            models.Index(fields=["display_order"]),
        ]

    def __str__(self):
        return self.name

    def calculate_total_fee(self, amount):
        """Calculate total processing fee for a given amount."""
        percentage_fee = amount * (self.processing_fee_percentage / 100)
        return percentage_fee + self.processing_fee_fixed
