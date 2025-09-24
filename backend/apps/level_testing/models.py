"""Level testing models for potential student applications and test administration.

This module contains models for managing the level testing process from initial
application through test completion and potential student conversion. All models
follow clean architecture principles with minimal dependencies.

Key workflow:
INITIATED → REGISTERED → PAID → SCHEDULED → TESTED → GRADED → COMMUNICATED → ENROLLED/DECLINED

Models:
- PotentialStudent: Core application data for prospective students
- TestSession: Test scheduling and administration
- PlacementTest: Test definition and configuration
- TestAttempt: Individual test results and scoring
- TestPayment: Payment tracking for test fees
- DuplicateCandidate: Potential duplicate detection results
"""

import logging
import secrets
import string
import uuid
from datetime import timedelta
from decimal import Decimal
from typing import ClassVar
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import (
    BooleanField,
    CharField,
    DateField,
    EmailField,
    JSONField,
    PositiveSmallIntegerField,
    TextField,
    UUIDField,
)
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.constants import CAMBODIAN_PROVINCE_CHOICES
from apps.common.models import AuditModel
from apps.finance.models.core import Payment
from apps.people.models import Gender

# Use PaymentMethod from finance app for consistency
PaymentMethod = Payment.PaymentMethod

logger = logging.getLogger(__name__)


def calculate_luhn_check_digit(base_code: str) -> str:
    """Calculate Luhn check digit for 6-digit base code.

    Args:
        base_code: 6-digit string to calculate check digit for

    Returns:
        Single digit check digit as string
    """
    digits = [int(d) for d in base_code]

    # Double every second digit from right to left
    for i in range(len(digits) - 2, -1, -2):
        digits[i] *= 2
        if digits[i] > 9:
            digits[i] = digits[i] // 10 + digits[i] % 10

    # Sum all digits
    total = sum(digits)

    # Check digit makes total multiple of 10
    return str((10 - (total % 10)) % 10)


def validate_luhn_code(full_code: str) -> bool:
    """Validate 7-digit code with Luhn check digit.

    Args:
        full_code: 7-digit string to validate

    Returns:
        True if code has valid Luhn check digit
    """
    if len(full_code) != 7 or not full_code.isdigit():
        return False

    base_code = full_code[:6]
    check_digit = full_code[6]

    return calculate_luhn_check_digit(base_code) == check_digit


# PaymentMethod removed - now imported from finance.models.core.Payment.PaymentMethod
# This ensures consistency across the system


class TestAccessToken(AuditModel):
    """Pre-application payment token with QR code.

    This model tracks payments made BEFORE the application form is filled.
    Students must pay first to receive an access code that allows them to
    complete the application form.
    """

    # Unique identifier (7-digit with Luhn check)
    access_code = models.CharField(
        _("Access Code"),
        max_length=7,
        unique=True,
        db_index=True,
        help_text=_("7-digit unique access code with Luhn check digit"),
    )

    # Payment tracking
    payment_amount = models.DecimalField(
        _("Payment Amount"), max_digits=8, decimal_places=2, help_text=_("Amount paid in USD")
    )
    payment_method = models.CharField(
        _("Payment Method"), max_length=20, choices=PaymentMethod.choices, default=PaymentMethod.CASH
    )
    payment_received_at = models.DateTimeField(_("Payment Received At"), help_text=_("When payment was received"))
    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="issued_access_tokens",
        verbose_name=_("Cashier"),
        help_text=_("Staff member who collected payment"),
    )

    # QR Code data
    qr_code_url = models.URLField(_("QR Code URL"), blank=True, help_text=_("Full URL encoded in QR code"))
    qr_code_data = models.JSONField(
        _("QR Code Data"), default=dict, blank=True, help_text=_("Additional QR code metadata")
    )

    # Student pre-registration info
    student_name = models.CharField(_("Student Name"), max_length=100, help_text=_("Student's full name for receipt"))
    student_phone = models.CharField(
        _("Student Phone"), max_length=20, help_text=_("Student's phone number for contact")
    )

    # Usage tracking
    is_used = models.BooleanField(
        _("Is Used"), default=False, help_text=_("Whether this token has been used to start an application")
    )
    used_at = models.DateTimeField(
        _("Used At"), null=True, blank=True, help_text=_("When the token was used to start application")
    )
    application = models.OneToOneField(
        "PotentialStudent",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="access_token",
        verbose_name=_("Application"),
        help_text=_("The application created with this token"),
    )

    # Telegram integration
    telegram_id = models.CharField(
        _("Telegram ID"), max_length=50, blank=True, help_text=_("Telegram user ID after verification")
    )
    telegram_username = models.CharField(
        _("Telegram Username"), max_length=50, blank=True, help_text=_("Telegram username")
    )
    telegram_verified = models.BooleanField(
        _("Telegram Verified"), default=False, help_text=_("Whether Telegram has been verified")
    )
    telegram_verification_code = models.CharField(
        _("Telegram Verification Code"),
        max_length=6,
        blank=True,
        help_text=_("6-digit verification code sent via Telegram"),
    )
    telegram_verified_at = models.DateTimeField(
        _("Telegram Verified At"), null=True, blank=True, help_text=_("When Telegram was verified")
    )

    # Token expiration
    expires_at = models.DateTimeField(_("Expires At"), help_text=_("When this token expires (24 hours from creation)"))

    class Meta:
        verbose_name = _("Test Access Token")
        verbose_name_plural = _("Test Access Tokens")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["access_code"]),
            models.Index(fields=["student_phone"]),
            models.Index(fields=["is_used"]),
            models.Index(fields=["telegram_id"]),
        ]

    def __str__(self):
        return f"Token {self.access_code} - {self.student_name}"

    def save(self, *args, **kwargs):
        if not self.access_code:
            self.access_code = self.generate_access_code()
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)

    @classmethod
    def generate_access_code(cls):
        """Generate a unique 7-digit access code with Luhn check digit."""
        while True:
            # Generate 6 random digits
            digits = "".join(secrets.choice(string.digits) for _ in range(6))

            # Calculate Luhn check digit using existing function
            check_digit = calculate_luhn_check_digit(digits)
            code = digits + check_digit

            # Check if code already exists
            if not cls.objects.filter(access_code=code).exists():
                return code

    @property
    def is_expired(self):
        """Check if token has expired."""
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        """Check if token is valid for use."""
        return not self.is_used and not self.is_expired

    def mark_as_used(self, application):
        """Mark token as used when application is started."""
        self.is_used = True
        self.used_at = timezone.now()
        self.application = application
        self.save()


class ApplicationStatus(models.TextChoices):
    """Status workflow for potential student applications."""

    INITIATED = "INITIATED", _("Application Started")
    REGISTERED = "REGISTERED", _("Registration Complete")
    DUPLICATE_CHECK = "DUPLICATE_CHECK", _("Pending Duplicate Review")
    PAID = "PAID", _("Test Fee Paid")
    SCHEDULED = "SCHEDULED", _("Test Session Scheduled")
    TESTED = "TESTED", _("Test Completed")
    GRADED = "GRADED", _("Test Results Available")
    COMMUNICATED = "COMMUNICATED", _("Results Communicated")
    ENROLLED = "ENROLLED", _("Converted to Student")
    DECLINED = "DECLINED", _("Application Declined")
    CANCELLED = "CANCELLED", _("Application Cancelled")


class ProgramChoices(models.TextChoices):
    """Available English programs for testing placement."""

    GENERAL = "GENERAL", _("General English (GESL)")
    ACADEMIC = "ACADEMIC", _("Academic English (IEAP)")
    BUSINESS = "BUSINESS", _("Business English")
    HIGHSCHOOL = "HIGHSCHOOL", _("English for High School (EHSS)")
    SATURDAY = "SATURDAY", _("Weekend Express Saturday")
    SUNDAY = "SUNDAY", _("Weekend Express Sunday")
    BACHELORS = "BACHELORS", _("Bachelor's Degree Program")
    MASTERS = "MASTERS", _("Master's Degree Program")


class TimeSlotChoices(models.TextChoices):
    """Preferred study time slots."""

    MORNING = "MORNING", _("Morning (7:00 AM - 11:00 AM)")
    AFTERNOON = "AFTERNOON", _("Afternoon (1:00 PM - 5:00 PM)")
    EVENING = "EVENING", _("Evening (5:30 PM - 9:30 PM)")
    WEEKEND = "WEEKEND", _("Weekend (Saturday/Sunday)")
    FLEXIBLE = "FLEXIBLE", _("Flexible Schedule")


class HowDidYouHearChoices(models.TextChoices):
    """Choices for how applicants heard about the school."""

    FRIEND = "friend", _("My friend studied/studies here")
    FACEBOOK = "facebook", _("Facebook")
    INSTAGRAM = "instagram", _("Instagram")
    AT_SCHOOL = "at_school", _("At my school")
    FROM_FAMILY = "family", _("From family")
    POSTER_BANNER = "poster", _("Outside poster/banner")
    OTHER = "other", _("Other")


class LastEnglishStudyChoices(models.TextChoices):
    """Choices for when applicant last studied English."""

    STUDYING_NOW = "studying_now", _("Studying now in school")
    NEVER_STUDIED = "never_studied", _("Never studied")
    THREE_MONTHS = "3_months", _("3 months ago")
    SIX_MONTHS = "6_months", _("6 months ago")
    OVER_ONE_YEAR = "over_1_year", _("Over 1 year ago")


class CurrentStudyStatusChoices(models.TextChoices):
    """Choices for current studying status."""

    HIGH_SCHOOL = "high_school", _("High School")
    UNIVERSITY = "university", _("University")
    NOT_STUDYING = "not_studying", _("Not studying")


class HighSchoolChoices(models.TextChoices):
    """Common high schools in Cambodia."""

    AHS = "AHS", _("Angkor High School")
    JAN10 = "JAN10", _("10 January High School")
    SAMPOVEUHS = "SAMPOVEUHS", _("Sampov Eu High School")
    NORTHBRIDGE = "NORTHBRIDGE", _("Northbridge International School")
    ISPP = "ISPP", _("International School of Phnom Penh")
    WESTLINE = "WESTLINE", _("Westline School")
    ICAN = "ICAN", _("iCAN British International School")
    LOGOS = "LOGOS", _("Logos International School")
    PUBLIC_HIGH_SCHOOL = "PUBLIC_HS", _("Public High School")
    PRIVATE_HIGH_SCHOOL = "PRIVATE_HS", _("Private High School")
    OTHER_HIGH_SCHOOL = "OTHER_HS", _("Other High School")


class UniversityChoices(models.TextChoices):
    """Common universities in Cambodia."""

    BELTEI = "BELTEI", _("Beltei International University")
    NORTON = "NORTON", _("Norton University")
    ROYAL = "ROYAL", _("Royal University of Phnom Penh")
    ZAMAN = "ZAMAN", _("Zaman University")
    PUC = "PUC", _("Pannasastra University of Cambodia")
    IFL = "IFL", _("Institute for Foreign Languages (IFL)")
    BUILD_BRIGHT = "BUILD_BRIGHT", _("Build Bright University")
    CAMBODIA_MEKONG = "CAMBODIA_MEKONG", _("Cambodia Mekong University")
    OTHER_UNIVERSITY = "OTHER_UNI", _("Other University")


class WorkFieldChoices(models.TextChoices):
    """Work field choices for non-students."""

    HOTEL_RESTAURANT = "hotel_restaurant", _("Hotel / Restaurant")
    MEDICAL_PHARMACY = "medical_pharmacy", _("Medical office / Pharmacy")
    SMALL_COMPANY = "small_company", _("Small Company")
    NOT_WORKING = "not_working", _("Not working")


class SchoolChoices(models.TextChoices):
    """Common schools in Cambodia for current education."""

    NORTHBRIDGE = "NORTHBRIDGE", _("Northbridge International School")
    ISPP = "ISPP", _("International School of Phnom Penh")
    WESTLINE = "WESTLINE", _("Westline School")
    BELTEI = "BELTEI", _("Beltei International University")
    NORTON = "NORTON", _("Norton University")
    ROYAL = "ROYAL", _("Royal University of Phnom Penh")
    ZAMAN = "ZAMAN", _("Zaman University")
    PUBLIC_SCHOOL = "PUBLIC", _("Public School")
    PRIVATE_SCHOOL = "PRIVATE", _("Private School")
    INTERNATIONAL = "INTERNATIONAL", _("International School")
    OTHER = "OTHER", _("Other School")


class DuplicateStatus(models.TextChoices):
    """Status for duplicate checking process."""

    PENDING = "PENDING", _("Awaiting Review")
    CONFIRMED_NEW = "CONFIRMED_NEW", _("Confirmed New Student")
    CONFIRMED_DUPLICATE = "CONFIRMED_DUPLICATE", _("Confirmed Duplicate")
    DEBT_CONCERN = "DEBT_CONCERN", _("Outstanding Debt Concern")
    MANUAL_REVIEW = "MANUAL_REVIEW", _("Requires Manual Review")


class PotentialStudent(AuditModel):
    """Core model for potential students applying for level testing.

    Captures all necessary information for the application process
    while maintaining clean dependencies with minimal imports.
    """

    # Link to access token (for payment-first workflow)
    access_token_link = models.OneToOneField(
        "TestAccessToken",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="potential_student_link",
        verbose_name=_("Access Token Link"),
        help_text=_("Access token used to create this application"),
    )

    # Unique identifiers
    application_id: UUIDField = models.UUIDField(
        _("Application ID"),
        default=uuid.uuid4,
        unique=True,
        help_text=_("Unique identifier for this application"),
    )
    test_number: CharField = models.CharField(
        _("Test Number"),
        max_length=10,
        unique=True,
        blank=True,
        help_text=_("Generated test number (T0012345 format)"),
    )

    # Personal Information
    family_name_eng: CharField = models.CharField(
        _("Family Name (English)"),
        max_length=50,
        help_text=_("Last name in English"),
    )
    personal_name_eng: CharField = models.CharField(
        _("Personal Name (English)"),
        max_length=50,
        help_text=_("First/given name in English"),
    )
    family_name_khm: CharField = models.CharField(
        _("Family Name (Khmer)"),
        max_length=50,
        blank=True,
        help_text=_("Last name in Khmer script"),
    )
    personal_name_khm: CharField = models.CharField(
        _("Personal Name (Khmer)"),
        max_length=50,
        blank=True,
        help_text=_("First/given name in Khmer script"),
    )
    preferred_gender: CharField = models.CharField(
        _("Preferred Gender"),
        max_length=1,
        choices=Gender.choices,
        help_text=_("Gender identity preference"),
    )
    date_of_birth: DateField = models.DateField(
        _("Date of Birth"),
        help_text=_("Birth date for age verification and duplicate checking"),
    )
    birth_province: CharField = models.CharField(
        _("Birth Province"),
        max_length=50,
        choices=CAMBODIAN_PROVINCE_CHOICES,
        help_text=_("Province of birth for duplicate detection"),
    )

    # Contact Information
    phone_number: CharField = models.CharField(
        _("Phone Number"),
        max_length=20,
        help_text=_("Primary contact phone number"),
    )
    telegram_number: CharField = models.CharField(
        _("Telegram Number"),
        max_length=20,
        blank=True,
        help_text=_("Telegram contact if different from phone"),
    )
    personal_email: EmailField = models.EmailField(
        _("Email Address"),
        blank=True,
        help_text=_("Personal email address for communications"),
    )

    # Emergency Contact Information
    emergency_contact_name: CharField = models.CharField(
        _("Emergency Contact Name"),
        max_length=100,
        blank=True,
        help_text=_("Name of emergency contact person"),
    )
    emergency_contact_phone: CharField = models.CharField(
        _("Emergency Contact Phone"),
        max_length=20,
        blank=True,
        help_text=_("Phone number of emergency contact"),
    )
    emergency_contact_relationship: CharField = models.CharField(
        _("Emergency Contact Relationship"),
        max_length=15,
        blank=True,
        choices=[
            ("FATHER", _("Father")),
            ("MOTHER", _("Mother")),
            ("SPOUSE", _("Spouse")),
            ("PARTNER", _("Partner")),
            ("SIBLING", _("Sibling")),
            ("GRANDPARENT", _("Grandparent")),
            ("GUARDIAN", _("Legal Guardian")),
            ("FRIEND", _("Friend")),
            ("OTHER", _("Other")),
        ],
        help_text=_("Relationship to emergency contact"),
    )

    # Educational Background - New Structure
    current_study_status: CharField = models.CharField(
        _("Where are you currently studying?"),
        max_length=20,
        choices=CurrentStudyStatusChoices.choices,
        blank=True,
        help_text=_("Your current educational status"),
    )
    current_high_school: CharField = models.CharField(
        _("Current High School"),
        max_length=20,
        choices=HighSchoolChoices.choices,
        blank=True,
        help_text=_("High school you are currently attending"),
    )
    current_university: CharField = models.CharField(
        _("Current University"),
        max_length=20,
        choices=UniversityChoices.choices,
        blank=True,
        help_text=_("University you are currently attending"),
    )
    work_field: CharField = models.CharField(
        _("Work Field"),
        max_length=20,
        choices=WorkFieldChoices.choices,
        blank=True,
        help_text=_("Your current work field"),
    )
    other_school_name: CharField = models.CharField(
        _("Other School Name"),
        max_length=100,
        blank=True,
        help_text=_("School name if 'Other' is selected"),
    )

    # Legacy field - kept for migration compatibility
    current_school: CharField = models.CharField(
        _("Current School"),
        max_length=20,
        choices=SchoolChoices,
        default=SchoolChoices.OTHER,
        help_text=_("Current educational institution"),
    )
    current_grade: PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Current Grade"),
        validators=[MinValueValidator(6), MaxValueValidator(12)],
        null=True,
        blank=True,
        help_text=_("Current grade level (6-12) if in high school"),
    )
    is_graduate: BooleanField = models.BooleanField(
        _("High School Graduate"),
        default=False,
        help_text=_("Check if already graduated from high school"),
    )

    # English Learning History
    last_english_school: CharField = models.CharField(
        _("Last English School"),
        max_length=100,
        blank=True,
        help_text=_("Previous English language institution"),
    )
    last_english_level: CharField = models.CharField(
        _("Last English Level"),
        max_length=50,
        blank=True,
        help_text=_("Previous English level achieved"),
    )
    last_english_textbook: CharField = models.CharField(
        _("Last Textbook Used"),
        max_length=100,
        blank=True,
        help_text=_("Most recent English textbook series"),
    )
    last_english_study_period: CharField = models.CharField(
        _("When Did You Last Study English"),
        max_length=20,
        choices=LastEnglishStudyChoices.choices,
        blank=True,
        null=True,
        help_text=_("When you last studied English formally"),
    )

    # DEPRECATED: Use last_english_study_period instead
    # This field is kept for migration compatibility only
    # Will be removed after all data is migrated
    last_english_date: DateField = models.DateField(
        _("Last English Study Date"),
        null=True,
        blank=True,
        help_text=_("DEPRECATED - Use last_english_study_period instead"),
    )

    # Program Preferences
    preferred_program: CharField = models.CharField(
        _("Preferred Program"),
        max_length=20,
        choices=ProgramChoices,
        help_text=_("Desired English program"),
    )
    preferred_time_slot: CharField = models.CharField(
        _("Preferred Time Slot"),
        max_length=20,
        choices=TimeSlotChoices,
        help_text=_("Preferred study schedule"),
    )
    preferred_start_term: CharField = models.CharField(
        _("Preferred Start Term"),
        max_length=50,
        blank=True,
        help_text=_("When you would like to begin studies"),
    )

    # Application Flow
    status: CharField = models.CharField(
        _("Application Status"),
        max_length=20,
        choices=ApplicationStatus,
        default=ApplicationStatus.INITIATED,
        help_text=_("Current stage in the application process"),
    )
    status_history: JSONField = models.JSONField(
        _("Status History"),
        default=list,
        help_text=_("Historical tracking of status changes"),
    )

    # Additional Information
    first_time_at_puc: BooleanField = models.BooleanField(
        _("First Time at PUC"),
        default=True,
        help_text=_("Is this your first time applying to PUC?"),
    )
    how_did_you_hear: CharField = models.CharField(
        _("How Did You Hear About Us"),
        max_length=20,
        choices=HowDidYouHearChoices.choices,
        blank=True,
        help_text=_("Marketing research: how you learned about our school"),
    )
    comments: TextField = models.TextField(
        _("Additional Comments"),
        blank=True,
        help_text=_("Any additional information or special requests"),
    )

    # Links and References
    converted_person_id: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Converted Person ID"),
        null=True,
        blank=True,
        help_text=_("Person record ID if converted to student"),
    )
    converted_student_number: models.CharField = models.CharField(
        _("Student Number"),
        max_length=10,
        blank=True,
        help_text=_("Official student number if enrolled"),
    )

    # Duplicate Detection
    duplicate_check_performed: models.BooleanField = models.BooleanField(
        _("Duplicate Check Performed"),
        default=False,
        help_text=_("Whether duplicate detection has been completed"),
    )
    duplicate_check_status: models.CharField = models.CharField(
        _("Duplicate Check Status"),
        max_length=20,
        choices=DuplicateStatus,
        default=DuplicateStatus.PENDING,
        help_text=_("Result of duplicate detection process"),
    )
    duplicate_check_notes: models.TextField = models.TextField(
        _("Duplicate Check Notes"),
        blank=True,
        help_text=_("Notes from staff review of potential duplicates"),
    )
    duplicate_check_cleared_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cleared_duplicates",
        verbose_name=_("Duplicate Check Cleared By"),
        help_text=_("Staff member who cleared duplicate concerns"),
    )
    duplicate_check_cleared_at: models.DateTimeField = models.DateTimeField(
        _("Duplicate Check Cleared At"),
        null=True,
        blank=True,
        help_text=_("When duplicate concerns were resolved"),
    )

    class Meta:
        verbose_name = _("Potential Student")
        verbose_name_plural = _("Potential Students")
        ordering = ["-created_at"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["test_number"]),
            models.Index(fields=["status"]),
            models.Index(fields=["family_name_eng", "personal_name_eng"]),
            models.Index(fields=["date_of_birth", "birth_province"]),
            models.Index(fields=["phone_number"]),
            models.Index(fields=["personal_email"]),
            models.Index(fields=["duplicate_check_status"]),
        ]

    def __str__(self) -> str:
        return f"{self.personal_name_eng} {self.family_name_eng} ({self.test_number or 'No Test Number'})"

    @property
    def full_name_eng(self) -> str:
        """Full name in English."""
        return f"{self.personal_name_eng} {self.family_name_eng}"

    @property
    def full_name_khm(self) -> str:
        """Full name in Khmer."""
        if self.family_name_khm and self.personal_name_khm:
            return f"{self.family_name_khm} {self.personal_name_khm}"
        return ""

    @property
    def current_age(self) -> int:
        """Calculate current age."""
        today = timezone.now().date()
        return (
            today.year
            - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )

    @property
    def is_minor(self) -> bool:
        """Check if student is under 18."""
        return self.current_age < 18

    @property
    def has_duplicate_concerns(self) -> bool:
        """Check if there are unresolved duplicate concerns."""
        return self.duplicate_check_status in [
            DuplicateStatus.PENDING,
            DuplicateStatus.DEBT_CONCERN,
            DuplicateStatus.MANUAL_REVIEW,
        ]

    @property
    def can_proceed_to_payment(self) -> bool:
        """Check if application can proceed to payment stage."""
        return (
            self.status == ApplicationStatus.REGISTERED
            and self.duplicate_check_status == DuplicateStatus.CONFIRMED_NEW
        )

    def save(self, *args, **kwargs) -> None:
        """Generate test number on first save to REGISTERED status."""
        if not self.test_number and self.status == ApplicationStatus.REGISTERED:
            self.test_number = self.generate_test_number()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        """Validate model data."""
        super().clean()

        # Require other school name if OTHER is selected
        if self.current_school == SchoolChoices.OTHER and not self.other_school_name:
            raise ValidationError(
                {
                    "other_school_name": _(
                        "School name is required when 'Other' is selected.",
                    ),
                },
            )

        # Validate age requirements
        if self.current_age < 12:
            raise ValidationError(
                {
                    "date_of_birth": _("Applicant must be at least 12 years old."),
                },
            )

        if self.current_age > 65:
            raise ValidationError(
                {
                    "date_of_birth": _(
                        "Please verify birth date. Age appears unusually high.",
                    ),
                },
            )

        # Validate grade level for non-graduates
        if not self.is_graduate and not self.current_grade:
            raise ValidationError(
                {
                    "current_grade": _("Current grade is required for non-graduates."),
                },
            )

    @classmethod
    def generate_test_number(cls) -> str:
        """Generate next sequential test number in T0012345 format.

        Returns:
            Next available test number with T prefix
        """
        last_test = (
            cls.objects.filter(
                test_number__startswith="T",
            )
            .exclude(
                test_number="",
            )
            .order_by("test_number")
            .last()
        )

        if last_test and last_test.test_number:
            # Extract number part and increment
            try:
                last_number = int(last_test.test_number[1:])  # Remove 'T' prefix
                next_number = last_number + 1
            except (ValueError, IndexError):
                next_number = 1
        else:
            next_number = 1

        return f"T{next_number:07d}"  # T0000001 format

    def advance_status(self, new_status: str, notes: str = "", user=None) -> bool:
        """Advance application to new status with audit trail.

        Args:
            new_status: Target status from ApplicationStatus choices
            notes: Optional notes about the status change
            user: User making the change for audit purposes

        Returns:
            True if status was successfully changed
        """
        if new_status not in [choice[0] for choice in ApplicationStatus.choices]:
            return False

        old_status = self.status
        self.status = new_status

        # Add to status history
        history_entry = {
            "from_status": old_status,
            "to_status": new_status,
            "timestamp": timezone.now().isoformat(),
            "notes": notes,
            "user": user.email if user else "system",
        }

        if not isinstance(self.status_history, list):
            self.status_history = []

        self.status_history.append(history_entry)

        self.save(update_fields=["status", "status_history"])
        return True


class TestSession(AuditModel):
    """Test sessions for scheduling placement tests.

    Manages when and where tests are administered with capacity tracking.
    """

    session_date: models.DateTimeField = models.DateTimeField(
        _("Session Date & Time"),
        help_text=_("When the test session will be conducted"),
    )
    location: models.CharField = models.CharField(
        _("Test Location"),
        max_length=100,
        default="Main Computer Lab",
        help_text=_("Where the test will be administered"),
    )
    max_capacity: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Maximum Capacity"),
        default=20,
        validators=[MinValueValidator(1), MaxValueValidator(50)],
        help_text=_("Maximum number of test takers for this session"),
    )
    administrator: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="administered_test_sessions",
        verbose_name=_("Test Administrator"),
        help_text=_("Staff member responsible for this test session"),
    )
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this session is available for booking"),
    )
    session_notes: models.TextField = models.TextField(
        _("Session Notes"),
        blank=True,
        help_text=_("Special instructions or notes for this session"),
    )

    class Meta:
        verbose_name = _("Test Session")
        verbose_name_plural = _("Test Sessions")
        ordering = ["session_date"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["session_date", "is_active"]),
            models.Index(fields=["administrator"]),
        ]

    def __str__(self) -> str:
        return f"Test Session {self.session_date.strftime('%Y-%m-%d %H:%M')} - {self.location}"

    @property
    def enrolled_count(self) -> int:
        """Count of students scheduled for this session."""
        return self.test_attempts.filter(
            potential_student__status__in=[
                ApplicationStatus.SCHEDULED,
                ApplicationStatus.TESTED,
                ApplicationStatus.GRADED,
            ],
        ).count()

    @property
    def available_spots(self) -> int:
        """Number of available spots remaining."""
        return max(0, self.max_capacity - self.enrolled_count)

    @property
    def is_full(self) -> bool:
        """Check if session is at capacity."""
        return self.available_spots == 0

    @property
    def is_upcoming(self) -> bool:
        """Check if session is in the future."""
        return self.session_date > timezone.now()

    @property
    def can_book(self) -> bool:
        """Check if session accepts new bookings."""
        return self.is_active and self.is_upcoming and not self.is_full

    def clean(self) -> None:
        """Validate session data."""
        super().clean()

        # Ensure session is in the future when creating
        if self.pk is None and self.session_date <= timezone.now():
            raise ValidationError(
                {
                    "session_date": _("Test session must be scheduled for the future."),
                },
            )


class PlacementTest(AuditModel):
    """Definition of placement tests available for different programs.

    Configures test parameters and scoring for program placement.
    """

    name: models.CharField = models.CharField(
        _("Test Name"),
        max_length=100,
        help_text=_("Descriptive name for this placement test"),
    )
    program: models.CharField = models.CharField(
        _("Target Program"),
        max_length=20,
        choices=ProgramChoices,
        help_text=_("Program this test is designed for"),
    )
    test_type: models.CharField = models.CharField(
        _("Test Type"),
        max_length=20,
        choices=[
            ("ONLINE", _("Online Test")),
            ("PAPER", _("Paper Test")),
            ("INTERVIEW", _("Oral Interview")),
            ("COMBINED", _("Combined Format")),
        ],
        default="ONLINE",
        help_text=_("Format of the test administration"),
    )
    max_score: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Maximum Score"),
        default=100,
        validators=[MinValueValidator(1), MaxValueValidator(1000)],
        help_text=_("Highest possible score on this test"),
    )
    passing_score: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Minimum Passing Score"),
        default=60,
        help_text=_("Minimum score required to place into program"),
    )
    duration_minutes: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Test Duration (Minutes)"),
        default=90,
        validators=[MinValueValidator(15), MaxValueValidator(300)],
        help_text=_("Time allowed to complete the test"),
    )
    instructions: models.TextField = models.TextField(
        _("Test Instructions"),
        blank=True,
        help_text=_("Instructions given to test takers"),
    )
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this test is currently in use"),
    )

    class Meta:
        verbose_name = _("Placement Test")
        verbose_name_plural = _("Placement Tests")
        ordering = ["program", "name"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["program", "is_active"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_program_display()})"

    def clean(self) -> None:
        """Validate test configuration."""
        super().clean()

        if self.passing_score > self.max_score:
            raise ValidationError(
                {
                    "passing_score": _("Passing score cannot exceed maximum score."),
                },
            )


class TestAttempt(AuditModel):
    """Individual test attempt linking student to session with results.

    Records test performance and placement recommendations.
    """

    potential_student: models.ForeignKey = models.ForeignKey(
        PotentialStudent,
        on_delete=models.CASCADE,
        related_name="test_attempts",
        verbose_name=_("Potential Student"),
    )
    test_session: models.ForeignKey = models.ForeignKey(
        TestSession,
        on_delete=models.CASCADE,
        related_name="test_attempts",
        verbose_name=_("Test Session"),
    )
    placement_test: models.ForeignKey = models.ForeignKey(
        PlacementTest,
        on_delete=models.PROTECT,
        related_name="test_attempts",
        verbose_name=_("Placement Test"),
    )

    # Test Administration
    scheduled_at: models.DateTimeField = models.DateTimeField(
        _("Scheduled Time"),
        help_text=_("When the test was scheduled"),
    )
    started_at: models.DateTimeField = models.DateTimeField(
        _("Test Started"),
        null=True,
        blank=True,
        help_text=_("When the student began the test"),
    )
    completed_at: models.DateTimeField = models.DateTimeField(
        _("Test Completed"),
        null=True,
        blank=True,
        help_text=_("When the student finished the test"),
    )

    # Test Results
    raw_score: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Raw Score"),
        null=True,
        blank=True,
        help_text=_("Actual score achieved on the test"),
    )
    percentage_score: models.DecimalField = models.DecimalField(
        _("Percentage Score"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Score as percentage of maximum possible"),
    )
    recommended_level: models.CharField = models.CharField(
        _("Recommended Level"),
        max_length=20,
        blank=True,
        help_text=_("Suggested program level based on score"),
    )

    # Administration Notes
    proctor_notes: models.TextField = models.TextField(
        _("Proctor Notes"),
        blank=True,
        help_text=_("Observations during test administration"),
    )
    technical_issues: models.TextField = models.TextField(
        _("Technical Issues"),
        blank=True,
        help_text=_("Any technical problems encountered"),
    )

    # Status Tracking
    is_completed: models.BooleanField = models.BooleanField(
        _("Test Completed"),
        default=False,
        help_text=_("Whether the test was finished"),
    )
    is_graded: models.BooleanField = models.BooleanField(
        _("Results Recorded"),
        default=False,
        help_text=_("Whether scores have been entered"),
    )

    class Meta:
        verbose_name = _("Test Attempt")
        verbose_name_plural = _("Test Attempts")
        ordering = ["-scheduled_at"]
        unique_together = [["potential_student", "test_session"]]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["test_session", "is_completed"]),
            models.Index(fields=["placement_test", "is_graded"]),
            models.Index(fields=["scheduled_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.potential_student.full_name_eng} - {self.test_session}"

    @property
    def duration_taken(self) -> int | None:
        """Calculate test duration in minutes."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() / 60)
        return None

    @property
    def is_passed(self) -> bool | None:
        """Check if test was passed."""
        if self.raw_score is not None:
            return self.raw_score >= self.placement_test.passing_score
        return None

    def calculate_percentage(self) -> None:
        """Calculate percentage score from raw score."""
        if self.raw_score is not None and self.placement_test:
            self.percentage_score = Decimal(
                (self.raw_score / self.placement_test.max_score) * 100,
            ).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs) -> None:
        """Auto-calculate percentage score on save."""
        if self.raw_score is not None:
            self.calculate_percentage()
        super().save(*args, **kwargs)

    def clean(self) -> None:
        """Validate test attempt data."""
        super().clean()

        # Validate score range
        if self.raw_score is not None:
            if self.raw_score > self.placement_test.max_score:
                raise ValidationError(
                    {
                        "raw_score": _(
                            f"Score cannot exceed maximum of {self.placement_test.max_score}",
                        ),
                    },
                )

        # Validate completion times
        if self.started_at and self.completed_at:
            if self.completed_at <= self.started_at:
                raise ValidationError(
                    {
                        "completed_at": _("Completion time must be after start time."),
                    },
                )


class TestPayment(AuditModel):
    """Payment tracking for test fees with finance integration.

    Links to finance app for accounting and reporting purposes.
    """

    potential_student: models.OneToOneField = models.OneToOneField(
        PotentialStudent,
        on_delete=models.CASCADE,
        related_name="test_payment",
        verbose_name=_("Potential Student"),
    )
    amount: models.DecimalField = models.DecimalField(
        _("Test Fee Amount"),
        max_digits=8,
        decimal_places=2,
        default=Decimal("5.00"),
        help_text=_("Amount charged for the placement test"),
    )
    payment_method: models.CharField = models.CharField(
        _("Payment Method"),
        max_length=20,
        choices=PaymentMethod,
        default=PaymentMethod.CASH,
        help_text=_("How the fee was paid"),
    )
    payment_reference: models.CharField = models.CharField(
        _("Payment Reference"),
        max_length=50,
        blank=True,
        help_text=_("Transaction ID or reference number"),
    )
    paid_at: models.DateTimeField = models.DateTimeField(
        _("Payment Date"),
        null=True,
        blank=True,
        help_text=_("When the payment was received"),
    )
    received_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="received_test_payments",
        verbose_name=_("Received By"),
        help_text=_("Staff member who processed the payment"),
    )
    is_paid: models.BooleanField = models.BooleanField(
        _("Payment Received"),
        default=False,
        help_text=_("Whether payment has been received"),
    )

    # Finance Integration
    finance_transaction_id: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Finance Transaction ID"),
        null=True,
        blank=True,
        help_text=_("Link to finance app transaction record"),
    )

    class Meta:
        verbose_name = _("Test Payment")
        verbose_name_plural = _("Test Payments")
        ordering = ["-paid_at"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["is_paid", "paid_at"]),
            models.Index(fields=["payment_method"]),
        ]

    def __str__(self) -> str:
        status = "Paid" if self.is_paid else "Pending"
        return f"{self.potential_student.full_name_eng} - ${self.amount} ({status})"

    def mark_paid(self, user=None, reference: str = "") -> None:
        """Mark payment as received with audit trail."""
        self.is_paid = True
        self.paid_at = timezone.now()
        self.received_by = user
        if reference:
            self.payment_reference = reference
        self.save(
            update_fields=["is_paid", "paid_at", "received_by", "payment_reference"],
        )


class DuplicateCandidate(AuditModel):
    """Potential duplicate records identified during application review.

    Stores results of duplicate detection algorithm for staff review.
    """

    potential_student: models.ForeignKey = models.ForeignKey(
        PotentialStudent,
        on_delete=models.CASCADE,
        related_name="duplicate_candidates",
        verbose_name=_("Potential Student"),
    )

    # Reference to existing person (stored as ID to avoid circular dependency)
    existing_person_id: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Existing Person ID"),
        help_text=_("ID of potentially matching person in people app"),
    )

    # Match Details
    match_type: models.CharField = models.CharField(
        _("Match Type"),
        max_length=20,
        choices=[
            ("EXACT_NAME", _("Exact Name Match")),
            ("SIMILAR_NAME", _("Similar Name")),
            ("PHONE_MATCH", _("Phone Number Match")),
            ("EMAIL_MATCH", _("Email Match")),
            ("DOB_MATCH", _("Date of Birth Match")),
            ("COMBINED", _("Multiple Criteria")),
        ],
        help_text=_("Type of potential match detected"),
    )
    confidence_score: models.DecimalField = models.DecimalField(
        _("Confidence Score"),
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text=_("Algorithm confidence (0.0 - 1.0)"),
    )

    # Match Data
    matched_name: models.CharField = models.CharField(
        _("Matched Name"),
        max_length=100,
        help_text=_("Name from existing person record"),
    )
    matched_birth_date: models.DateField = models.DateField(
        _("Matched Birth Date"),
        null=True,
        blank=True,
        help_text=_("Birth date from existing person record"),
    )
    matched_phone: models.CharField = models.CharField(
        _("Matched Phone"),
        max_length=20,
        blank=True,
        help_text=_("Phone number from existing person record"),
    )

    # Financial Concerns
    has_outstanding_debt: models.BooleanField = models.BooleanField(
        _("Has Outstanding Debt"),
        default=False,
        help_text=_("Whether existing person has unpaid balances"),
    )
    debt_amount: models.DecimalField = models.DecimalField(
        _("Outstanding Debt Amount"),
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=_("Amount of outstanding debt"),
    )

    # Review Status
    reviewed: models.BooleanField = models.BooleanField(
        _("Reviewed"),
        default=False,
        help_text=_("Whether staff has reviewed this potential match"),
    )
    is_confirmed_duplicate: models.BooleanField = models.BooleanField(
        _("Confirmed Duplicate"),
        default=False,
        help_text=_("Staff confirmed this is the same person"),
    )
    review_notes: models.TextField = models.TextField(
        _("Review Notes"),
        blank=True,
        help_text=_("Staff notes about duplicate review"),
    )
    reviewed_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_duplicates",
        verbose_name=_("Reviewed By"),
        help_text=_("Staff member who reviewed this potential duplicate"),
    )
    reviewed_at: models.DateTimeField = models.DateTimeField(
        _("Reviewed At"),
        null=True,
        blank=True,
        help_text=_("When the duplicate review was completed"),
    )

    class Meta:
        verbose_name = _("Duplicate Candidate")
        verbose_name_plural = _("Duplicate Candidates")
        ordering = ["-confidence_score", "-created_at"]
        unique_together = [["potential_student", "existing_person_id"]]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["potential_student", "reviewed"]),
            models.Index(fields=["confidence_score"]),
            models.Index(fields=["has_outstanding_debt"]),
        ]

    def __str__(self) -> str:
        return f"Potential duplicate: {self.potential_student.full_name_eng} → {self.matched_name}"

    @property
    def risk_level(self) -> str:
        """Assess risk level of this potential duplicate."""
        if self.has_outstanding_debt or self.confidence_score >= 0.9:
            return "HIGH"
        if self.confidence_score >= 0.7:
            return "MEDIUM"
        return "LOW"


class TestCompletion(AuditModel):
    """Test completion tracking with internal QR codes for cross-app integration.

    Generated automatically when a TestAttempt is marked as completed. Creates
    an internal 7-digit code with Luhn check digit for linking payments,
    Telegram registration, and student profiles across apps.

    Workflow:
    1. Student completes test → TestAttempt.is_completed = True
    2. TestCompletion automatically generated with internal_code
    3. QR code slip printed with student name + internal code
    4. Finance uses code to link payments
    5. Telegram bot uses code to register student contact info
    """

    # Core linking
    test_attempt: models.OneToOneField = models.OneToOneField(
        TestAttempt,
        on_delete=models.CASCADE,
        related_name="completion",
        verbose_name=_("Test Attempt"),
        help_text=_("The test attempt this completion record represents"),
    )

    # Internal tracking code (7 digits with Luhn check)
    internal_code: models.CharField = models.CharField(
        _("Internal Code"),
        max_length=7,
        unique=True,
        db_index=True,
        help_text=_("7-digit code with Luhn check digit for cross-app linking"),
    )

    # QR Code and Slip Data
    qr_code_data: models.JSONField = models.JSONField(
        _("QR Code Data"),
        default=dict,
        help_text=_("Complete QR code payload including URL and metadata"),
    )
    slip_printed_at: models.DateTimeField = models.DateTimeField(
        _("Slip Printed At"),
        null=True,
        blank=True,
        help_text=_("When the completion slip was printed"),
    )

    # Cross-app Integration Status
    is_payment_linked: models.BooleanField = models.BooleanField(
        _("Payment Linked"),
        default=False,
        help_text=_("Whether this code has been linked to a payment"),
    )
    is_telegram_linked: models.BooleanField = models.BooleanField(
        _("Telegram Linked"),
        default=False,
        help_text=_("Whether student has registered Telegram via this code"),
    )

    # Integration Data
    payment_transaction_id: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Payment Transaction ID"),
        null=True,
        blank=True,
        help_text=_("Link to finance app transaction record"),
    )
    telegram_data: models.JSONField = models.JSONField(
        _("Telegram Data"),
        default=dict,
        help_text=_("Telegram username, phone, and registration details"),
    )

    # Status tracking
    completion_notes: models.TextField = models.TextField(
        _("Completion Notes"),
        blank=True,
        help_text=_("Additional notes about test completion or code usage"),
    )

    class Meta:
        verbose_name = _("Test Completion")
        verbose_name_plural = _("Test Completions")
        ordering = ["-created_at"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["internal_code"]),
            models.Index(fields=["is_payment_linked", "is_telegram_linked"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"Completion {self.internal_code} - {self.test_attempt.potential_student.full_name_eng}"

    @property
    def student_full_name_eng(self) -> str:
        """Get student's full English name in family_name personal_name order."""
        student = self.test_attempt.potential_student
        return f"{student.family_name_eng} {student.personal_name_eng}"

    @property
    def external_test_number(self) -> str:
        """Get the external test number (T0001234 format)."""
        return self.test_attempt.potential_student.test_number or ""

    @property
    def program_display(self) -> str:
        """Get the program display name."""
        return self.test_attempt.potential_student.get_preferred_program_display()

    @classmethod
    def generate_internal_code(cls) -> str:
        """Generate next sequential internal code with Luhn check digit.

        Returns:
            7-digit code in format 1234568 (6 digits + 1 check digit)
        """
        # Get the last completion record to determine next number
        last_completion = cls.objects.order_by("internal_code").last()

        if last_completion and last_completion.internal_code:
            try:
                # Extract base number from last code (first 6 digits)
                last_number = int(last_completion.internal_code[:6])
                next_number = last_number + 1
            except (ValueError, IndexError):
                next_number = 1
        else:
            next_number = 1

        # Handle overflow (unlikely but safe)
        if next_number > 999999:
            next_number = 1

        # Format as 6-digit base code
        base_code = f"{next_number:06d}"

        # Calculate and append check digit
        check_digit = calculate_luhn_check_digit(base_code)

        return base_code + check_digit

    def generate_qr_code_data(self) -> dict:
        """Generate complete QR code data structure.

        Returns:
            Dictionary containing all QR code information
        """
        base_url = getattr(settings, "BASE_URL", "https://naga.test")
        completion_url = f"{base_url}/completion/{self.internal_code}"

        # Query parameters for the URL
        query_params = {
            "name": self.student_full_name_eng,
            "test": self.external_test_number,
            "program": self.test_attempt.potential_student.preferred_program,
        }

        full_url = f"{completion_url}?{urlencode(query_params)}"

        qr_data = {
            "internal_code": self.internal_code,
            "url": completion_url,
            "full_url": full_url,
            "student_name": self.student_full_name_eng,
            "external_test_number": self.external_test_number,
            "program": self.test_attempt.potential_student.preferred_program,
            "test_date": self.test_attempt.completed_at.isoformat() if self.test_attempt.completed_at else None,
            "generated_at": timezone.now().isoformat(),
        }

        return qr_data

    def save(self, *args, **kwargs) -> None:
        """Generate internal code and QR data on first save."""
        if not self.internal_code:
            # Try to generate unique code (with collision protection)
            max_attempts = 5
            for _attempt in range(max_attempts):
                candidate_code = self.generate_internal_code()
                if not TestCompletion.objects.filter(internal_code=candidate_code).exists():
                    self.internal_code = candidate_code
                    break
            else:
                # Fallback to UUID if we somehow get collisions (extremely unlikely)
                self.internal_code = str(uuid.uuid4())[:7].upper()

        # Generate QR code data
        if not self.qr_code_data:
            self.qr_code_data = self.generate_qr_code_data()

        super().save(*args, **kwargs)

    def mark_payment_linked(self, transaction_id: int, notes: str = "") -> None:
        """Mark this completion as linked to a payment transaction.

        Args:
            transaction_id: ID of the finance transaction
            notes: Optional notes about the payment linking
        """
        self.is_payment_linked = True
        self.payment_transaction_id = transaction_id
        if notes:
            self.completion_notes += f"\nPayment linked: {notes}"
        self.save(update_fields=["is_payment_linked", "payment_transaction_id", "completion_notes"])

    def register_telegram(self, username: str, phone: str = "", notes: str = "") -> None:
        """Register Telegram information for this completion.

        Args:
            username: Telegram username
            phone: Phone number if available
            notes: Additional registration notes
        """
        self.is_telegram_linked = True
        self.telegram_data = {
            "username": username,
            "phone": phone,
            "registered_at": timezone.now().isoformat(),
            "notes": notes,
        }
        if notes:
            self.completion_notes += f"\nTelegram registered: {notes}"
        self.save(update_fields=["is_telegram_linked", "telegram_data", "completion_notes"])

    def clean(self) -> None:
        """Validate test completion data."""
        super().clean()

        # Validate internal code format if provided
        if self.internal_code and not validate_luhn_code(self.internal_code):
            raise ValidationError(
                {"internal_code": _("Invalid internal code format or check digit.")},
            )


# Signal handlers for automatic TestCompletion generation


@receiver(post_save, sender=TestAttempt)
def create_test_completion_on_completion(sender, instance, created, **kwargs):
    """Automatically create TestCompletion when TestAttempt is marked completed.

    Triggers when:
    - TestAttempt.is_completed changes to True
    - TestAttempt.completed_at is set
    - No existing TestCompletion exists for this attempt
    """
    # Only create completion record if test is marked as completed
    if instance.is_completed and instance.completed_at:
        # Check if TestCompletion already exists to avoid duplicates
        if not hasattr(instance, "completion") or instance.completion is None:
            try:
                # Create the TestCompletion record
                completion = TestCompletion.objects.create(test_attempt=instance)

                # Log the creation for audit purposes
                logger.info(
                    f"TestCompletion created: {completion.internal_code} for "
                    f"{instance.potential_student.full_name_eng}"
                )

                # Trigger thermal printing
                from .printing import print_completion_slip

                print_success = print_completion_slip(completion)
                if not print_success:
                    logger.warning(f"Failed to print completion slip for {completion.internal_code}")

            except Exception as e:
                # Log error but don't fail the TestAttempt save
                logger.error(f"Error creating TestCompletion for TestAttempt {instance.id}: {e}")


@receiver(post_save, sender=TestCompletion)
def mark_slip_printed_on_creation(sender, instance, created, **kwargs):
    """Mark slip as printed immediately when TestCompletion is created.

    In production, this would trigger actual thermal printing.
    For now, we just mark the timestamp.
    """
    if created and not instance.slip_printed_at:
        # Mark slip as printed (in production, this would happen after successful printing)
        instance.slip_printed_at = timezone.now()
        instance.save(update_fields=["slip_printed_at"])

        # In production, this would trigger actual thermal printing
        logger.info(f"Completion slip marked as printed for code {instance.internal_code}")
        logger.debug(f"QR Code URL: {instance.qr_code_data.get('full_url', 'N/A')}")
