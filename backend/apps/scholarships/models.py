"""Scholarships app models following clean architecture principles.

This module contains models for managing sponsorships, scholarships, and
student financial aid. All models are designed to avoid circular dependencies
while providing comprehensive scholarship and sponsorship management.

Key architectural decisions:
- Clean dependencies: scholarships → people + curriculum (no circular dependencies)
- Separation from finance: focuses on aid relationships, not billing
- Single responsibility: student financial aid and sponsorship management
- Historical tracking via base model mixins
- No direct references to scheduling or grading apps

Models:
- Sponsor: Organizations that sponsor students through MOUs
- SponsoredStudent: Links between sponsors and their sponsored students
- Scholarship: Merit-based or need-based financial aid awards
- ScholarshipApplication: Student applications for scholarships
"""

from decimal import Decimal
from typing import ClassVar

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import (
    BooleanField,
    CharField,
    DateField,
    DecimalField,
    EmailField,
    ForeignKey,
    IntegerField,
    TextField,
)
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import UserAuditModel, SoftDeleteManager


class PaymentMode(models.TextChoices):
    """Payment modes for NGO-funded scholarships."""

    DIRECT = "DIRECT", _("Direct Payment - Student pays with NGO funds")
    BULK_INVOICE = "BULK_INVOICE", _("Bulk Invoice - NGO pays directly")


class BillingCycle(models.TextChoices):
    """Billing cycle options for NGO bulk invoicing."""

    MONTHLY = "MONTHLY", _("Monthly")
    TERM = "TERM", _("Per Academic Term")
    QUARTERLY = "QUARTERLY", _("Quarterly")
    YEARLY = "YEARLY", _("Yearly")


class Sponsor(UserAuditModel):
    """Organizations that sponsor students through MOUs with the school.

    Sponsors sign Memorandums of Understanding (MOUs) with the school and provide
    financial support for students. This model tracks all sponsor information,
    contact details, and partnership preferences.

    Key features:
    - MOU date range tracking with validation
    - Default discount percentage for sponsored students
    - Consolidated invoicing preferences
    - Reporting requirements tracking
    - Administrative fee exemption periods
    - Contact information management
    """

    # Basic sponsor information
    code: CharField = models.CharField(
        _("Sponsor Code"),
        max_length=10,
        unique=True,
        help_text=_("Short code or abbreviation for the sponsor (e.g., CRST, PLF)"),
    )
    name: CharField = models.CharField(
        _("Sponsor Name"),
        max_length=100,
        help_text=_("Full formal name of the sponsoring organization"),
    )

    # Contact information
    contact_name: CharField = models.CharField(
        _("Contact Person"),
        max_length=100,
        blank=True,
        help_text=_("Name of the primary contact person at the sponsor organization"),
    )
    contact_email: EmailField = models.EmailField(
        _("Contact Email"),
        blank=True,
        help_text=_("Email address of the primary contact person"),
    )
    contact_phone: CharField = models.CharField(
        _("Contact Phone"),
        max_length=20,
        blank=True,
        help_text=_("Phone number of the primary contact person"),
    )
    billing_email: EmailField = models.EmailField(
        _("Billing Email"),
        blank=True,
        help_text=_("Email address for sending invoices and billing communications"),
    )

    # MOU (Memorandum of Understanding) tracking
    mou_start_date: DateField = models.DateField(
        _("MOU Start Date"),
        help_text=_("Start date of the Memorandum of Understanding"),
    )
    mou_end_date: DateField = models.DateField(
        _("MOU End Date"),
        null=True,
        blank=True,
        help_text=_("End date of the MOU (leave blank for ongoing agreements)"),
    )

    # Financial preferences
    default_discount_percentage: DecimalField = models.DecimalField(
        _("Default Discount Percentage"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
        help_text=_("Standard discount percentage for sponsored students (0.00 to 100.00)"),
    )

    # Billing preferences
    requests_tax_addition: BooleanField = models.BooleanField(
        _("Add Tax to Invoices"),
        default=False,
        help_text=_("Whether to add tax on top of invoices for this sponsor"),
    )
    requests_consolidated_invoicing: BooleanField = models.BooleanField(
        _("Consolidated Invoicing"),
        default=False,
        help_text=_("Whether to group all sponsored students into one consolidated invoice"),
    )

    # Administrative fee configuration
    admin_fee_exempt_until: DateField = models.DateField(
        _("Admin Fee Exemption Until"),
        null=True,
        blank=True,
        help_text=_("Date until which sponsored students are exempt from administrative fees"),
    )

    # Reporting requirements
    requests_attendance_reporting: BooleanField = models.BooleanField(
        _("Attendance Reporting"),
        default=False,
        help_text=_("Whether sponsor requests attendance reports for their students"),
    )
    requests_grade_reporting: BooleanField = models.BooleanField(
        _("Grade Reporting"),
        default=False,
        help_text=_("Whether sponsor requests grade reports for their students"),
    )
    requests_scheduling_reporting: BooleanField = models.BooleanField(
        _("Scheduling Reporting"),
        default=False,
        help_text=_("Whether sponsor requests class schedule reports for their students"),
    )

    # Payment configuration for NGO-funded scholarships
    payment_mode: CharField = models.CharField(
        _("Payment Mode"),
        max_length=20,
        choices=PaymentMode.choices,
        default=PaymentMode.DIRECT,
        help_text=_("How sponsored students pay for their tuition"),
    )
    billing_cycle: CharField = models.CharField(
        _("Billing Cycle"),
        max_length=20,
        choices=BillingCycle.choices,
        default=BillingCycle.TERM,
        help_text=_("Frequency of bulk invoice generation (only for BULK_INVOICE mode)"),
    )
    invoice_generation_day: IntegerField = models.IntegerField(
        _("Invoice Generation Day"),
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(28)],
        help_text=_("Day of month/term to generate bulk invoices (1-28)"),
    )
    payment_terms_days: IntegerField = models.IntegerField(
        _("Payment Terms (Days)"),
        default=30,
        validators=[MinValueValidator(0), MaxValueValidator(90)],
        help_text=_("Number of days for payment after invoice generation"),
    )

    # Status tracking
    is_active: BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this sponsor is currently active"),
    )
    notes: TextField = models.TextField(_("Notes"), blank=True, help_text=_("Additional notes about this sponsor"))

    class Meta:
        verbose_name = _("Sponsor")
        verbose_name_plural = _("Sponsors")
        ordering: ClassVar[list[str]] = ["name"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["code"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["mou_start_date", "mou_end_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"

    def clean(self) -> None:
        """Validate sponsor data."""
        super().clean()

        # Validate MOU date range
        if self.mou_end_date and self.mou_start_date:
            if self.mou_end_date <= self.mou_start_date:
                raise ValidationError({"mou_end_date": _("MOU end date must be after start date")})

    @property
    def is_mou_active(self) -> bool:
        """Check if the MOU is currently active."""
        today = timezone.now().date()
        if today < self.mou_start_date:
            return False
        if self.mou_end_date and today > self.mou_end_date:
            return False
        return self.is_active

    def get_active_sponsored_students_count(self) -> int:
        """Get count of currently sponsored students."""
        return (
            self.sponsored_students.filter(start_date__lte=timezone.now().date())  # type: ignore[attr-defined]
            .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=timezone.now().date()))
            .count()
        )


class SponsoredStudentManager(SoftDeleteManager["SponsoredStudent"]):
    """Custom manager for SponsoredStudent with reusable query methods."""

    def get_active_for_student(self, student):
        """Get active sponsorships for a student."""
        from django.utils import timezone

        today = timezone.now().date()
        return self.filter(student=student, start_date__lte=today).filter(
            models.Q(end_date__isnull=True) | models.Q(end_date__gte=today),
        )


class SponsoredStudent(UserAuditModel):
    """Links between sponsoring organizations and their sponsored students.

    This model creates the relationship between sponsors and students, tracking
    the sponsorship period, type, and associated financial benefits. It maintains
    a clean relationship between the sponsor and student domains.

    Key features:
    - Date range tracking for sponsorship periods
    - Multiple sponsorship types (full, partial, etc.)
    - Integration with scholarship systems
    - Historical tracking of sponsorship changes
    """

    class SponsorshipType(models.TextChoices):
        """Types of sponsorship arrangements."""

        FULL = "FULL", _("Full Sponsorship")
        PARTIAL = "PARTIAL", _("Partial Sponsorship")
        EMERGENCY = "EMERGENCY", _("Emergency Support")
        SCHOLARSHIP = "SCHOLARSHIP", _("Scholarship")

    sponsor: ForeignKey = models.ForeignKey(
        Sponsor,
        on_delete=models.PROTECT,
        related_name="sponsored_students",
        verbose_name=_("Sponsor"),
    )
    student: ForeignKey = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.PROTECT,
        related_name="sponsorships",
        verbose_name=_("Student"),
    )

    # Sponsorship details
    sponsorship_type: CharField = models.CharField(
        _("Sponsorship Type"),
        max_length=20,
        choices=SponsorshipType.choices,
        default=SponsorshipType.FULL,
        help_text=_("Type of sponsorship arrangement"),
    )

    # Date range tracking
    start_date: DateField = models.DateField(_("Start Date"), help_text=_("Date when sponsorship begins"))
    end_date: DateField = models.DateField(
        _("End Date"),
        null=True,
        blank=True,
        help_text=_("Date when sponsorship ends (leave blank for ongoing)"),
    )

    # Additional information
    notes: TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this sponsorship arrangement"),
    )

    objects = SponsoredStudentManager()

    class Meta:
        verbose_name = _("Sponsored Student")
        verbose_name_plural = _("Sponsored Students")
        ordering: ClassVar[list[str]] = ["-start_date", "sponsor", "student"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["sponsor", "start_date"]),
            models.Index(fields=["student", "start_date"]),
            models.Index(fields=["start_date", "end_date"]),
        ]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["sponsor", "student", "start_date"],
                name="unique_sponsorship_per_start_date",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.sponsor.code} → {self.student} ({self.sponsorship_type})"  # type: ignore[attr-defined]

    def clean(self) -> None:
        """Validate sponsored student data."""
        super().clean()

        # Validate date range
        if self.end_date and self.start_date:
            if self.end_date <= self.start_date:
                raise ValidationError({"end_date": _("End date must be after start date")})

        # Check for overlapping sponsorships from the same sponsor
        overlapping = (
            SponsoredStudent.objects.filter(
                sponsor=self.sponsor,
                student=self.student,
                start_date__lte=self.end_date or timezone.now().date(),
            )
            .filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=self.start_date))
            .exclude(pk=self.pk)
        )

        if overlapping.exists():
            raise ValidationError(_("This student already has an overlapping sponsorship from the same sponsor"))

    @property
    def is_currently_active(self) -> bool:
        """Check if this sponsorship is currently active."""
        today = timezone.now().date()
        if today < self.start_date:
            return False
        return not (self.end_date and today > self.end_date)

    @property
    def duration_days(self) -> int | None:
        """Calculate the duration of sponsorship in days."""
        if not self.end_date:
            return None
        return (self.end_date - self.start_date).days


class Scholarship(UserAuditModel):
    """Merit-based or need-based financial aid awards for students.

    This model tracks scholarships that may or may not be linked to sponsors.
    It provides flexibility for both sponsored scholarships and independent
    merit/need-based awards.

    Key features:
    - Support for both sponsored and independent scholarships
    - Percentage or fixed amount awards
    - Date range validity
    - Award status tracking
    - Integration with student financial aid
    - Cycle-specific scholarships (Language, BA, MA) - students must re-enter when transitioning between cycles

    Business Rule: Scholarships are cycle-specific. If a student receives a scholarship
    in Language programs and then moves to BA programs, they must re-enter the
    scholarship system for the new cycle.
    """

    class ScholarshipType(models.TextChoices):
        """Types of scholarships."""

        MERIT = "MERIT", _("Merit-Based")
        NEED = "NEED", _("Need-Based")
        SPONSORED = "SPONSORED", _("Sponsor-Funded")
        EMERGENCY = "EMERGENCY", _("Emergency Aid")
        STAFF = "STAFF", _("Staff Scholarship")
        ACADEMIC = "ACADEMIC", _("Academic Excellence")

    class AwardStatus(models.TextChoices):
        """Status of the scholarship award."""

        PENDING = "PENDING", _("Pending Review")
        APPROVED = "APPROVED", _("Approved")
        ACTIVE = "ACTIVE", _("Active")
        SUSPENDED = "SUSPENDED", _("Suspended")
        COMPLETED = "COMPLETED", _("Completed")
        CANCELLED = "CANCELLED", _("Cancelled")

    # Basic scholarship information
    name: CharField = models.CharField(
        _("Scholarship Name"),
        max_length=200,
        help_text=_("Name or title of the scholarship"),
    )
    scholarship_type: CharField = models.CharField(
        _("Scholarship Type"),
        max_length=20,
        choices=ScholarshipType.choices,
        help_text=_("Type of scholarship"),
    )

    # Student and sponsor links
    student: ForeignKey = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.PROTECT,
        related_name="scholarships",
        verbose_name=_("Student"),
    )
    cycle: ForeignKey = models.ForeignKey(
        "curriculum.Cycle",
        on_delete=models.PROTECT,
        related_name="scholarships",
        verbose_name=_("Academic Cycle"),
        null=True,
        blank=True,
        help_text=_(
            "Academic cycle this scholarship applies to (Language, BA, or MA). "
            "Students must re-enter scholarships when transitioning between cycles."
        ),
    )
    sponsored_student: models.OneToOneField = models.OneToOneField(
        SponsoredStudent,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="scholarship",
        verbose_name=_("Sponsored Student"),
        help_text=_("Link to sponsored student record (if applicable)"),
    )

    # Award details
    award_percentage: DecimalField = models.DecimalField(
        _("Award Percentage"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("0.00")),
            MaxValueValidator(Decimal("100.00")),
        ],
        help_text=_("Percentage of costs covered (0.00 to 100.00)"),
    )
    award_amount: DecimalField = models.DecimalField(
        _("Fixed Award Amount"),
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.00"))],
        help_text=_("Fixed amount of the award (alternative to percentage)"),
    )

    # Validity period
    start_date: DateField = models.DateField(_("Start Date"), help_text=_("Date when scholarship becomes effective"))
    end_date: DateField = models.DateField(
        _("End Date"),
        null=True,
        blank=True,
        help_text=_("Date when scholarship expires (leave blank for ongoing)"),
    )

    # Status and administration
    status: CharField = models.CharField(
        _("Status"),
        max_length=20,
        choices=AwardStatus.choices,
        default=AwardStatus.PENDING,
        help_text=_("Current status of this scholarship"),
    )
    description: TextField = models.TextField(
        _("Description"),
        blank=True,
        help_text=_("Detailed description of the scholarship"),
    )
    conditions: TextField = models.TextField(
        _("Conditions"),
        blank=True,
        help_text=_("Conditions or requirements for maintaining the scholarship"),
    )
    notes: TextField = models.TextField(_("Notes"), blank=True, help_text=_("Additional notes about this scholarship"))

    class Meta:
        verbose_name = _("Scholarship")
        verbose_name_plural = _("Scholarships")
        ordering: ClassVar[list[str]] = ["-start_date", "student"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "status"]),
            models.Index(fields=["student", "cycle", "status"]),
            models.Index(fields=["cycle", "status"]),
            models.Index(fields=["scholarship_type", "status"]),
            models.Index(fields=["start_date", "end_date"]),
            models.Index(fields=["status", "-start_date"]),
        ]
        constraints: ClassVar[list[models.BaseConstraint]] = [
            models.UniqueConstraint(
                fields=["student", "cycle", "scholarship_type", "start_date"],
                name="unique_scholarship_per_student_cycle_type_date",
                condition=models.Q(status__in=["APPROVED", "ACTIVE"]) & models.Q(cycle__isnull=False),
            ),
        ]

    def __str__(self) -> str:
        cycle_info = f" ({self.cycle.short_name})" if self.cycle else ""  # type: ignore[attr-defined]
        return f"{self.name} - {self.student}{cycle_info}"

    def clean(self) -> None:
        """Validate scholarship data."""
        super().clean()

        errors = {}

        # Validate cycle is active (only if cycle is loaded and has the is_active attribute)
        if self.cycle and hasattr(self.cycle, "is_active") and not self.cycle.is_active:
            errors["cycle"] = _("Cannot assign scholarships to inactive cycles")

        # Validate date range
        if self.end_date and self.start_date:
            if self.end_date <= self.start_date:
                errors["end_date"] = _("End date must be after start date")

        # Validate that either percentage or amount is provided, but not both
        # Only validate if we're not creating a new object (pk exists) or if values are set
        if self.pk or self.award_percentage is not None or self.award_amount is not None:
            if self.award_percentage and self.award_amount:
                errors["award_percentage"] = _("Scholarship cannot have both percentage and fixed amount")
                errors["award_amount"] = _("Scholarship cannot have both percentage and fixed amount")

            if not self.award_percentage and not self.award_amount:
                errors["award_percentage"] = _("Scholarship must have either percentage or fixed amount")
                errors["award_amount"] = _("Scholarship must have either percentage or fixed amount")

        if errors:
            raise ValidationError(errors)

    @property
    def is_currently_active(self) -> bool:
        """Check if this scholarship is currently active."""
        if self.status not in [self.AwardStatus.APPROVED, self.AwardStatus.ACTIVE]:
            return False

        today = timezone.now().date()
        if today < self.start_date:
            return False
        return not (self.end_date and today > self.end_date)

    @property
    def award_display(self) -> str:
        """Get display string for the award amount."""
        if self.award_percentage:
            return f"{self.award_percentage}%"
        if self.award_amount:
            return f"${self.award_amount}"
        return "No amount set"
