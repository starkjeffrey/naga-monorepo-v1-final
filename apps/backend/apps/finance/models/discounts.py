"""Discount models for the finance application.

This module contains the core discount infrastructure that should be used
throughout the system, including by the AR reconstruction process.
"""

from datetime import date
from typing import ClassVar

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.common.models import TimestampedModel, UserTrackingModel


class DiscountRule(TimestampedModel, UserTrackingModel):
    """Configurable discount rules for the finance system.

    These rules define how discounts are applied throughout the system.
    The AR reconstruction process should use these rules via the
    AutomaticDiscountService rather than implementing its own logic.
    """

    class RuleType(models.TextChoices):
        EARLY_BIRD = "EARLY_BIRD", _("Early Bird Discount")
        CASH_PAYMENT_PLAN = "CASH_PLAN", _("Cash Payment Plan")
        WEEKEND_CLASS = "WEEKEND", _("Weekend Class Discount")
        MONK_PRICING = "MONK", _("Monk Special Pricing")
        ADMIN_FEE = "ADMIN_FEE", _("Administrative Fee")
        CUSTOM = "CUSTOM", _("Custom Rule")

    # === RULE IDENTIFICATION ===
    rule_name = models.CharField(_("Rule Name"), max_length=100, unique=True)

    rule_type = models.CharField(_("Rule Type"), max_length=20, choices=RuleType.choices)

    # === RULE CONFIGURATION ===
    pattern_text = models.CharField(
        _("Pattern Text"),
        max_length=200,
        help_text=_("Text pattern that triggers this rule (from Notes field)"),
    )

    discount_percentage = models.DecimalField(
        _("Discount Percentage"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Percentage discount (if applicable)"),
    )

    fixed_amount = models.DecimalField(
        _("Fixed Amount"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Fixed fee/discount amount"),
    )

    # === APPLICABILITY ===
    applies_to_cycle = models.CharField(
        _("Applies to Cycle"),
        max_length=10,
        blank=True,
        choices=[
            ("HS", _("High School (EHSS)")),
            ("CERT", _("Certificate Program")),
            ("PREP", _("Preparatory (IEAP/Foundation)")),
            ("BA", _("Bachelor's Degree")),
            ("MA", _("Master's Degree")),
            ("PHD", _("Doctoral Degree")),
        ],
        help_text=_("Academic cycle this rule applies to (empty = all cycles)"),
    )

    applies_to_terms = models.JSONField(
        _("Applies to Terms"),
        default=list,
        blank=True,
        help_text=_("List of terms this rule applies to (empty = all terms)"),
    )

    applies_to_programs = models.JSONField(
        _("Applies to Programs"),
        default=list,
        blank=True,
        help_text=_("List of program codes this rule applies to (empty = all programs)"),
    )

    # === RULE STATUS ===
    is_active = models.BooleanField(_("Is Active"), default=True)

    effective_date = models.DateField(_("Effective Date"), default=date.today)

    # === USAGE TRACKING ===
    times_applied = models.PositiveIntegerField(_("Times Applied"), default=0)

    last_applied_date = models.DateTimeField(_("Last Applied Date"), null=True, blank=True)

    class Meta:
        db_table = "finance_discount_rule"
        verbose_name = _("Discount Rule")
        verbose_name_plural = _("Discount Rules")
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["rule_type", "is_active"]),
            models.Index(fields=["pattern_text"]),
        ]

    def __str__(self):
        return f"{self.rule_name} ({self.get_rule_type_display()})"


class DiscountApplication(TimestampedModel, UserTrackingModel):
    """Record of a discount being applied to a student's charges.

    This model tracks when and how discounts are applied, providing
    an audit trail for financial reconciliation.
    """

    # === STUDENT & FINANCIAL RECORDS ===
    student = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.CASCADE,
        related_name="discount_applications",
    )

    invoice = models.ForeignKey(
        "finance.Invoice",
        on_delete=models.CASCADE,
        related_name="discount_applications",
        null=True,
        blank=True,
        help_text=_("Invoice this discount was applied to"),
    )

    payment = models.ForeignKey(
        "finance.Payment",
        on_delete=models.CASCADE,
        related_name="discount_applications",
        null=True,
        blank=True,
        help_text=_("Payment associated with this discount"),
    )

    # === DISCOUNT DETAILS ===
    discount_rule = models.ForeignKey(
        DiscountRule,
        on_delete=models.PROTECT,
        related_name="applications",
        help_text=_("The rule that triggered this discount"),
    )

    term = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.CASCADE,
        related_name="discount_applications",
    )

    original_amount = models.DecimalField(
        _("Original Amount"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Amount before discount"),
    )

    discount_amount = models.DecimalField(
        _("Discount Amount"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Amount of discount applied"),
    )

    final_amount = models.DecimalField(
        _("Final Amount"),
        max_digits=10,
        decimal_places=2,
        help_text=_("Amount after discount"),
    )

    # === APPLICATION METADATA ===
    applied_date = models.DateTimeField(
        _("Applied Date"),
        auto_now_add=True,
        help_text=_("When the discount was applied"),
    )

    payment_date = models.DateField(
        _("Payment Date"),
        help_text=_("Date of payment (for early bird eligibility)"),
    )

    authority = models.CharField(
        _("Authority"),
        max_length=50,
        default="SYSTEM",
        help_text=_("Who authorized the discount (SYSTEM, MANUAL, etc.)"),
    )

    approval_status = models.CharField(
        _("Approval Status"),
        max_length=20,
        choices=[
            ("APPROVED", _("Approved")),
            ("PENDING_APPROVAL", _("Pending Approval")),
            ("REJECTED", _("Rejected")),
        ],
        default="APPROVED",
    )

    notes = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this discount application"),
    )

    # === AR RECONSTRUCTION LINK ===
    legacy_receipt_ipk = models.IntegerField(
        _("Legacy Receipt IPK"),
        null=True,
        blank=True,
        help_text=_("Link to legacy receipt if applied during reconstruction"),
    )

    class Meta:
        db_table = "finance_discount_application"
        verbose_name = _("Discount Application")
        verbose_name_plural = _("Discount Applications")
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "term"]),
            models.Index(fields=["discount_rule", "applied_date"]),
            models.Index(fields=["approval_status"]),
            models.Index(fields=["legacy_receipt_ipk"]),
        ]

    def __str__(self):
        return f"{self.student} - {self.discount_rule} - ${self.discount_amount}"
