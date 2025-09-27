"""Pricing models for course and fee pricing with historical tracking."""

from datetime import date
from decimal import Decimal
from typing import ClassVar

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.mixins import DateRangeValidationMixin
from apps.common.models import UserAuditModel


class BasePricingModel(UserAuditModel):
    """Abstract base class for all pricing models.

    Provides common fields and functionality for pricing validation,
    effective date tracking, and business rule enforcement.
    """

    effective_date: models.DateField = models.DateField(
        _("Effective Date"),
        default=date.today,
        help_text=_("When this pricing becomes effective"),
    )
    end_date: models.DateField = models.DateField(
        _("End Date"),
        null=True,
        blank=True,
        help_text=_("When this pricing expires (null = current)"),
    )
    notes: models.TextField = models.TextField(
        _("Notes"), blank=True, help_text=_("Internal notes about this pricing")
    )

    class Meta:
        abstract = True

    def clean(self) -> None:
        """Validate pricing data."""
        super().clean()

        if self.end_date and self.end_date <= self.effective_date:
            raise ValidationError({"end_date": _("End date must be after effective date.")})

    @property
    def is_current(self) -> bool:
        """Check if this pricing is currently active."""
        today = timezone.now().date()
        return self.effective_date <= today and (self.end_date is None or today <= self.end_date)


class DefaultPricing(BasePricingModel):
    """Default pricing for regular courses by cycle.

    Simple per-cycle pricing that applies when no other specific
    pricing rules are configured. Supports domestic/foreign rates.
    """

    cycle: models.ForeignKey = models.ForeignKey(
        "curriculum.Cycle",
        on_delete=models.PROTECT,
        related_name="default_pricing",
        verbose_name=_("Cycle"),
        help_text=_("Academic cycle (BA/MA/LANG)"),
    )
    domestic_price: models.DecimalField = models.DecimalField(
        _("Domestic Price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Price for domestic students"),
    )
    foreign_price: models.DecimalField = models.DecimalField(
        _("Foreign Price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Price for international students"),
    )

    class Meta:
        db_table = "finance_default_pricing"
        verbose_name = _("Default Pricing")
        verbose_name_plural = _("Default Pricing")
        ordering = ["cycle", "-effective_date"]
        constraints = [
            models.UniqueConstraint(fields=["cycle", "effective_date"], name="unique_default_per_cycle_date"),
            # Prevent overlapping effective periods
            models.UniqueConstraint(
                fields=["cycle"],
                condition=models.Q(end_date__isnull=True),
                name="unique_current_default_per_cycle",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["cycle", "effective_date"]),
            models.Index(fields=["effective_date", "end_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.cycle} Default - ${self.domestic_price}/{self.foreign_price} (Effective: {self.effective_date})"

    def get_price_for_student(self, is_foreign: bool = False) -> Decimal:
        """Get the appropriate price for a student."""
        return self.foreign_price if is_foreign else self.domestic_price


class CourseFixedPricing(DateRangeValidationMixin, BasePricingModel):
    """Fixed pricing for specific courses that override defaults.

    Direct course overrides for courses that don't follow standard
    cycle pricing. Examples: special programs, intensive courses.
    """

    # DateRangeValidationMixin configuration
    date_range_fields: ClassVar[list[str]] = ["effective_date", "end_date"]
    date_range_scope_fields: ClassVar[list[str]] = ["course"]

    course: models.ForeignKey = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.CASCADE,
        related_name="fixed_pricing",
        verbose_name=_("Course"),
        help_text=_("Course with fixed pricing"),
    )
    domestic_price: models.DecimalField = models.DecimalField(
        _("Domestic Price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Price for domestic students"),
    )
    foreign_price: models.DecimalField = models.DecimalField(
        _("Foreign Price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Price for international students"),
    )

    class Meta:
        db_table = "finance_course_fixed_pricing"
        verbose_name = _("Course Fixed Pricing")
        verbose_name_plural = _("Course Fixed Pricing")
        ordering = ["course", "-effective_date"]
        constraints = [
            models.UniqueConstraint(fields=["course", "effective_date"], name="unique_fixed_per_course_date"),
            # Prevent overlapping effective periods for same course
            models.UniqueConstraint(
                fields=["course"],
                condition=models.Q(end_date__isnull=True),
                name="unique_current_fixed_per_course",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["course", "effective_date"]),
            models.Index(fields=["effective_date", "end_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.course.code} Fixed - ${self.domestic_price}/{self.foreign_price}"

    def get_price_for_student(self, is_foreign: bool = False) -> Decimal:
        """Get the appropriate price for a student."""
        return self.foreign_price if is_foreign else self.domestic_price


class SeniorProjectPricing(BasePricingModel):
    """Individual pricing for senior projects based on group size.

    Each student pays the FULL individual price - prices are NOT split among group.
    Price is higher when there are fewer students in the group (tiered individual pricing).
    Charged after admin finalizes groups.
    """

    class GroupSizeTier(models.TextChoices):
        ONE_STUDENT = "1", _("1 Student")
        TWO_STUDENTS = "2", _("2 Students")
        THREE_FOUR_STUDENTS = "3-4", _("3-4 Students")
        FIVE_STUDENTS = "5", _("5 Students")

    tier: models.CharField = models.CharField(
        _("Group Size Tier"),
        max_length=10,
        choices=GroupSizeTier.choices,
        help_text=_("Student group size tier"),
    )
    individual_price: models.DecimalField = models.DecimalField(
        _("Individual Price"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Price each student pays individually (NOT split among group)"),
    )
    foreign_individual_price: models.DecimalField = models.DecimalField(
        _("Foreign Individual Price"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Price each foreign student pays individually (NOT split among group)"),
    )
    advisor_payment: models.DecimalField = models.DecimalField(
        _("Advisor Payment"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Payment to project advisor"),
    )
    committee_payment: models.DecimalField = models.DecimalField(
        _("Committee Payment"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Payment to each committee member"),
    )

    class Meta:
        db_table = "finance_senior_project_pricing"
        verbose_name = _("Senior Project Pricing")
        verbose_name_plural = _("Senior Project Pricing")
        ordering = ["tier", "-effective_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["tier", "effective_date"],
                name="unique_senior_project_tier_date",
            ),
            # Prevent overlapping effective periods for same tier
            models.UniqueConstraint(
                fields=["tier"],
                condition=models.Q(end_date__isnull=True),
                name="unique_current_senior_project_tier",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["tier", "effective_date"]),
            models.Index(fields=["effective_date", "end_date"]),
        ]

    def __str__(self) -> str:
        return f"Senior Project {self.tier}: ${self.individual_price}/${self.foreign_individual_price}"

    def get_individual_price(self, is_foreign: bool = False) -> Decimal:
        """Get individual price for a student (NOT divided by group size)."""
        price = self.foreign_individual_price if is_foreign else self.individual_price
        if price is None:
            raise ValueError(
                f"{'Foreign individual' if is_foreign else 'Individual'} price not set for tier {self.tier}"
            )
        return price


class SeniorProjectCourse(UserAuditModel):
    """Configuration for which courses use senior project pricing.

    Only 4 courses are senior project courses (one per major except TESOL):
    - BUS-489 (Business Administration)
    - IR-489 (International Relations)
    - FIN-489 (Finance)
    - THM-433 (Theology/Ministry)

    TESOL students do individual projects, not group projects.
    """

    course: models.OneToOneField = models.OneToOneField(
        "curriculum.Course",
        on_delete=models.CASCADE,
        related_name="senior_project_config",
        verbose_name=_("Course"),
    )
    project_code: models.CharField = models.CharField(
        _("Project Code"),
        max_length=20,
        blank=True,
        null=True,
        help_text=_("Project identification code (e.g., BUS-489, IR-489, FIN-489, THM-433)"),
    )
    major_name: models.CharField = models.CharField(
        _("Major Name"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("Name of the major this project serves (e.g., Business Administration, International Relations)"),
    )
    allows_groups: models.BooleanField = models.BooleanField(
        _("Allows Groups"),
        default=True,
        help_text=_("Whether this project type allows group work (TESOL is individual only)"),
    )
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this course uses senior project pricing"),
    )

    class Meta:
        db_table = "finance_senior_project_course"
        verbose_name = _("Senior Project Course")
        verbose_name_plural = _("Senior Project Courses")
        ordering = ["course__code"]

    def __str__(self) -> str:
        status = "Active" if self.is_active else "Inactive"
        project_info = f" ({self.project_code})" if self.project_code else ""
        return f"{self.course.code} Senior Project{project_info} ({status})"


class ReadingClassPricing(BasePricingModel):
    """Pricing for reading/request classes based on enrollment size.

    Tier-based pricing where fewer students pay more per person.
    Admin locks pricing when enrollment is finalized.
    """

    class ClassSizeTier(models.TextChoices):
        TUTORIAL = "1-2", _("1-2 Students (Tutorial)")
        SMALL = "3-5", _("3-5 Students (Small Class)")
        MEDIUM = "6-15", _("6-15 Students (Medium Class)")

    cycle: models.ForeignKey = models.ForeignKey(
        "curriculum.Cycle",
        on_delete=models.PROTECT,
        related_name="reading_class_pricing",
        verbose_name=_("Cycle"),
    )
    tier: models.CharField = models.CharField(
        _("Class Size Tier"),
        max_length=10,
        choices=ClassSizeTier.choices,
        help_text=_("Class enrollment size tier"),
    )
    domestic_price: models.DecimalField = models.DecimalField(
        _("Domestic Price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Price per student for domestic students"),
        default=0,
    )
    foreign_price: models.DecimalField = models.DecimalField(
        _("Foreign Price"),
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Price per student for international students"),
        default=0,
    )

    class Meta:
        db_table = "finance_reading_class_pricing"
        verbose_name = _("Reading Class Pricing")
        verbose_name_plural = _("Reading Class Pricing")
        ordering = ["cycle", "tier", "-effective_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["cycle", "tier", "effective_date"],
                name="unique_reading_per_cycle_tier_date",
            ),
            # Prevent overlapping effective periods for same cycle/tier
            models.UniqueConstraint(
                fields=["cycle", "tier"],
                condition=models.Q(end_date__isnull=True),
                name="unique_current_reading_per_cycle_tier",
            ),
        ]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["cycle", "tier", "effective_date"]),
            models.Index(fields=["effective_date", "end_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.cycle} Reading {self.tier}: ${self.domestic_price}/${self.foreign_price}"

    def get_price_for_student(self, is_foreign: bool) -> Decimal:
        """Get the appropriate price for a student based on their status."""
        return self.foreign_price if is_foreign else self.domestic_price


class FeeType(models.TextChoices):
    """Types of fees that can be charged."""

    REGISTRATION = "REGISTRATION", _("Registration Fee")
    APPLICATION = "APPLICATION", _("Application Fee")
    LATE_PAYMENT = "LATE_PAYMENT", _("Late Payment Fee")
    MATERIAL = "MATERIAL", _("Material Fee")
    TECHNOLOGY = "TECHNOLOGY", _("Technology Fee")
    LIBRARY = "LIBRARY", _("Library Fee")
    STUDENT_SERVICES = "STUDENT_SERVICES", _("Student Services Fee")
    GRADUATION = "GRADUATION", _("Graduation Fee")
    DOCUMENT = "DOCUMENT", _("Document Fee")
    ID_CARD = "ID_CARD", _("ID Card Fee")
    PARKING = "PARKING", _("Parking Fee")
    OTHER = "OTHER", _("Other Fee")


class FeePricing(UserAuditModel):
    """Administrative and other fees with flexible pricing rules.

    Supports both fixed fees and per-course fees with separate
    local and foreign pricing and effective date tracking.
    """

    name: models.CharField = models.CharField(
        _("Fee Name"),
        max_length=100,
        help_text=_("Name of the fee"),
    )
    fee_type: models.CharField = models.CharField(
        _("Fee Type"),
        max_length=20,
        choices=FeeType,
        help_text=_("Category of this fee"),
    )
    local_amount: models.DecimalField = models.DecimalField(
        _("Local Amount"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Fee amount for local students"),
    )
    foreign_amount: models.DecimalField = models.DecimalField(
        _("Foreign Amount"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Fee amount for foreign students"),
    )
    currency: models.CharField = models.CharField(
        _("Currency"),
        max_length=3,
        choices=[("USD", "US Dollar")],
        default="USD",
        help_text=_("Fee currency"),
    )
    effective_date: models.DateField = models.DateField(
        _("Effective Date"),
        default=date.today,
        help_text=_("When this fee pricing becomes effective"),
    )
    end_date: models.DateField = models.DateField(
        _("End Date"),
        null=True,
        blank=True,
        help_text=_("When this fee pricing expires (null = current)"),
    )
    description: models.TextField = models.TextField(
        _("Description"),
        blank=True,
        help_text=_("Detailed description of what this fee covers"),
    )
    is_mandatory: models.BooleanField = models.BooleanField(
        _("Is Mandatory"),
        default=True,
        help_text=_("If true: automatically charged to all applicable students. If false: optional/on-request fee."),
    )
    is_per_course: models.BooleanField = models.BooleanField(
        _("Is Per Course"),
        default=False,
        help_text=_("Charged once for EACH course enrollment (e.g., $10 per course for material fee)"),
    )
    is_per_term: models.BooleanField = models.BooleanField(
        _("Is Per Term"),
        default=False,
        help_text=_("Charged once per term regardless of course count (e.g., $50 registration fee per term)"),
    )
    is_per_document: models.BooleanField = models.BooleanField(
        _("Is Per Document"),
        default=False,
        help_text=_("Charged for each document requested (e.g., $5 per transcript, $10 per certificate)"),
    )

    class Meta:
        db_table = "finance_fee_pricing"
        verbose_name = _("Fee Pricing")
        verbose_name_plural = _("Fee Pricing")
        ordering = ["fee_type", "name", "-effective_date"]
        constraints = [
            models.UniqueConstraint(fields=["name", "effective_date"], name="unique_fee_per_name_date"),
        ]
        indexes = [
            models.Index(fields=["fee_type", "effective_date"]),
            models.Index(fields=["effective_date", "end_date"]),
            models.Index(fields=["is_mandatory", "is_per_course", "is_per_term", "is_per_document"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_fee_type_display()})"  # type: ignore[attr-defined]

    @property
    def is_active(self) -> bool:
        """Check if this fee pricing is currently active."""
        today = timezone.now().date()
        return self.effective_date <= today and (self.end_date is None or today <= self.end_date)

    def get_amount_for_student(self, is_foreign: bool = False) -> Decimal:
        """Get the appropriate fee amount for a student."""
        amount = self.foreign_amount if is_foreign else self.local_amount
        if amount is None:
            raise ValueError(f"{'Foreign' if is_foreign else 'Local'} amount not set for fee {self.name}")
        return amount

    def clean(self) -> None:
        """Validate fee pricing data."""
        super().clean()

        # At least one amount must be set
        if self.local_amount is None and self.foreign_amount is None:
            raise ValidationError(_("At least one of local or foreign amount must be set."))

        # End date validation
        if self.end_date and self.end_date <= self.effective_date:
            raise ValidationError({"end_date": _("End date must be after effective date.")})

        # Frequency validation - only one frequency type allowed
        frequency_count = sum([self.is_per_course, self.is_per_term, self.is_per_document])
        if frequency_count > 1:
            raise ValidationError(_("Fee can only have one frequency: per-course OR per-term OR per-document."))
