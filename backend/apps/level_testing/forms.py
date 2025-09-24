"""Forms for level testing application process.

This module contains Django forms for the level testing workflow, designed
for mobile-first responsive interface. Forms are organized into logical steps
for a wizard-style application process.

Key features:
- Mobile-first responsive design
- Multi-step wizard workflow
- Comprehensive validation
- Bilingual support (English/Khmer)
- Clean field organization
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.constants import CAMBODIAN_PROVINCE_CHOICES
from apps.level_testing.models import (
    CurrentStudyStatusChoices,
    HighSchoolChoices,
    HowDidYouHearChoices,
    LastEnglishStudyChoices,
    PaymentMethod,
    ProgramChoices,
    SchoolChoices,
    TestPayment,
    TimeSlotChoices,
    UniversityChoices,
    WorkFieldChoices,
)
from apps.people.models import Gender


class BaseTestingForm(forms.Form):
    """Base form class with common styling and mobile-first design."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Apply consistent styling to all fields
        for field in self.fields.values():
            # Add CSS classes for mobile-first design
            css_classes = [
                "form-input",
                "w-full",
                "px-3",
                "py-2",
                "border",
                "border-gray-300",
                "rounded-md",
                "shadow-sm",
                "focus:outline-none",
                "focus:ring-2",
                "focus:ring-blue-500",
                "focus:border-blue-500",
            ]

            if isinstance(field.widget, forms.TextInput):
                css_classes.extend(["text-base", "md:text-sm"])
            elif isinstance(field.widget, forms.Select):
                css_classes.extend(["text-base", "md:text-sm", "bg-white"])
            elif isinstance(field.widget, forms.Textarea):
                css_classes.extend(["text-base", "md:text-sm", "resize-none"])
            elif isinstance(field.widget, forms.CheckboxInput):
                css_classes = [
                    "form-checkbox",
                    "h-5",
                    "w-5",
                    "text-blue-600",
                    "border-gray-300",
                    "rounded",
                    "focus:ring-2",
                    "focus:ring-blue-500",
                ]

            field.widget.attrs.update(
                {
                    "class": " ".join(css_classes),
                },
            )

            # Add placeholders for better UX
            if hasattr(field, "label") and isinstance(
                field.widget,
                forms.TextInput | forms.EmailInput,
            ):
                field.widget.attrs["placeholder"] = field.label


class PersonalInfoForm(BaseTestingForm):
    """Step 1: Personal information collection.

    Collects basic personal details including bilingual names,
    gender, birth information, and contact details.
    """

    # English names (required) - Family name first
    family_name_eng = forms.CharField(
        label=_("Last Name (English)"),
        max_length=50,
        help_text=_("Your family/last name in English"),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "family-name",
                "required": True,
            },
        ),
    )

    personal_name_eng = forms.CharField(
        label=_("First Name (English)"),
        max_length=50,
        help_text=_("Your first/given name in English"),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "given-name",
                "required": True,
            },
        ),
    )

    # Khmer names (optional) - Family name first
    family_name_khm = forms.CharField(
        label=_("Last Name (Khmer)"),
        max_length=50,
        required=False,
        help_text=_("Your family/last name in Khmer script (optional)"),
        widget=forms.TextInput(
            attrs={
                "lang": "km",
            },
        ),
    )

    personal_name_khm = forms.CharField(
        label=_("First Name (Khmer)"),
        max_length=50,
        required=False,
        help_text=_("Your first/given name in Khmer script (optional)"),
        widget=forms.TextInput(
            attrs={
                "lang": "km",
            },
        ),
    )

    # Gender and birth information
    preferred_gender = forms.ChoiceField(
        label=_("Gender"),
        choices=Gender.choices,
        help_text=_("Your gender identity preference"),
        widget=forms.Select(attrs={"required": True}),
    )

    date_of_birth = forms.DateField(
        label=_("Date of Birth"),
        help_text=_("Your birth date (MM/DD/YYYY)"),
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "required": True,
                "max": timezone.now().date().isoformat(),  # Prevent future dates
            },
        ),
    )

    birth_province = forms.ChoiceField(
        label=_("Birth Province"),
        choices=CAMBODIAN_PROVINCE_CHOICES,
        help_text=_("Province where you were born"),
        widget=forms.Select(attrs={"required": True}),
    )

    # Contact information
    phone_number = forms.CharField(
        label=_("Phone Number"),
        max_length=20,
        help_text=_("Your primary phone number"),
        widget=forms.TextInput(
            attrs={
                "type": "tel",
                "autocomplete": "tel",
                "required": True,
                "pattern": r"[0-9\+\-\s\(\)]+",
            },
        ),
    )

    telegram_number = forms.CharField(
        label=_("Telegram Number"),
        max_length=20,
        required=False,
        help_text=_("Telegram contact if different from phone (optional)"),
        widget=forms.TextInput(
            attrs={
                "type": "tel",
                "pattern": r"[0-9\+\-\s\(\)]+",
            },
        ),
    )

    personal_email = forms.EmailField(
        label=_("Email Address"),
        required=False,
        help_text=_("Your email address for communications (optional)"),
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
            },
        ),
    )

    def clean_date_of_birth(self):
        """Validate birth date for age requirements."""
        birth_date = self.cleaned_data.get("date_of_birth")

        if birth_date:
            today = timezone.now().date()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

            if age < 12:
                raise ValidationError(_("You must be at least 12 years old to apply."))

            if age > 65:
                raise ValidationError(
                    _("Please verify your birth date. Age appears unusually high."),
                )

        return birth_date

    def clean_phone_number(self):
        """Validate phone number format."""
        phone = self.cleaned_data.get("phone_number")

        if phone:
            # Remove non-digit characters for validation
            digits_only = "".join(filter(str.isdigit, phone))

            if len(digits_only) < 8:
                raise ValidationError(_("Phone number must contain at least 8 digits."))

            if len(digits_only) > 15:
                raise ValidationError(_("Phone number is too long."))

        return phone


class EducationBackgroundForm(BaseTestingForm):
    """Step 2: Educational background information.

    Collects current school information, grade level, and
    previous English learning experience.
    """

    # Current education - new conditional structure
    current_study_status = forms.ChoiceField(
        label=_("Where are you currently studying?"),
        choices=[("", _("Select an option...")), *list(CurrentStudyStatusChoices.choices)],
        required=False,
        help_text=_("Your current educational or work status"),
        widget=forms.Select(attrs={"id": "id_current_study_status", "onchange": "toggleStudyFields(this.value)"}),
    )

    current_high_school = forms.ChoiceField(
        label=_("High School"),
        choices=[("", _("Select a high school...")), *list(HighSchoolChoices.choices)],
        required=False,
        widget=forms.Select(attrs={"class": "conditional-field high-school-field", "style": "display: none;"}),
    )

    current_university = forms.ChoiceField(
        label=_("University"),
        choices=[("", _("Select a university...")), *list(UniversityChoices.choices)],
        required=False,
        widget=forms.Select(attrs={"class": "conditional-field university-field", "style": "display: none;"}),
    )

    work_field = forms.ChoiceField(
        label=_("If you are working, what field do you work in?"),
        choices=[("", _("Select a work field...")), *list(WorkFieldChoices.choices)],
        required=False,
        widget=forms.Select(attrs={"class": "conditional-field work-field", "style": "display: none;"}),
    )

    current_grade = forms.ChoiceField(
        label=_("Current Grade"),
        choices=[("", _("Select grade..."))] + [(i, f"Grade {i}") for i in range(6, 13)],
        required=False,
        help_text=_("Your current grade level (only for high school students)"),
        widget=forms.Select(attrs={"class": "conditional-field high-school-field", "style": "display: none;"}),
    )

    other_school_name = forms.CharField(
        label=_("Other School Name"),
        max_length=100,
        required=False,
        help_text=_("Name of your school if not listed above"),
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Enter school name if you selected 'Other'"),
                "class": "conditional-field other-field",
                "style": "display: none;",
            },
        ),
    )

    is_graduate = forms.BooleanField(
        label=_("High School Graduate"),
        required=False,
        help_text=_("Check if you have already graduated from high school"),
        widget=forms.CheckboxInput(),
    )

    # English learning history
    last_english_school = forms.CharField(
        label=_("Previous English School"),
        max_length=100,
        required=False,
        help_text=_("Last place where you studied English (optional)"),
        widget=forms.TextInput(),
    )

    last_english_level = forms.CharField(
        label=_("Previous English Level"),
        max_length=50,
        required=False,
        help_text=_("Highest English level you completed (optional)"),
        widget=forms.TextInput(
            attrs={
                "placeholder": _("e.g., Beginner, Elementary, Intermediate"),
            },
        ),
    )

    last_english_textbook = forms.CharField(
        label=_("Previous Textbook"),
        max_length=100,
        required=False,
        help_text=_("English textbook you used most recently (optional)"),
        widget=forms.TextInput(
            attrs={
                "placeholder": _("e.g., Ventures, American English File"),
            },
        ),
    )

    last_english_study_period = forms.ChoiceField(
        label=_("When did you last study English?"),
        choices=[("", _("Select an option...")), *list(LastEnglishStudyChoices.choices)],
        required=False,
        help_text=_("When did you last study English formally? (optional)"),
        widget=forms.Select(),
    )

    def clean(self):
        """Cross-field validation for education background."""
        cleaned_data = super().clean()

        current_school = cleaned_data.get("current_school")
        other_school_name = cleaned_data.get("other_school_name")
        current_grade = cleaned_data.get("current_grade")
        is_graduate = cleaned_data.get("is_graduate")

        # Require other school name if OTHER is selected
        if current_school == SchoolChoices.OTHER and not other_school_name:
            raise ValidationError(
                {
                    "other_school_name": _(
                        "Please enter your school name when 'Other' is selected.",
                    ),
                },
            )

        # Require grade if not graduated
        if not is_graduate and not current_grade:
            raise ValidationError(
                {
                    "current_grade": _(
                        "Please select your current grade if you haven't graduated.",
                    ),
                },
            )

        return cleaned_data


class ProgramPreferencesForm(BaseTestingForm):
    """Step 3: Program preferences and study plans.

    Collects information about desired programs, schedules,
    and study preferences.
    """

    preferred_program = forms.ChoiceField(
        label=_("Preferred Program"),
        choices=ProgramChoices.choices,
        help_text=_("Which English program interests you most?"),
        widget=forms.Select(attrs={"required": True}),
    )

    preferred_time_slot = forms.ChoiceField(
        label=_("Preferred Schedule"),
        choices=TimeSlotChoices.choices,
        help_text=_("When would you prefer to study?"),
        widget=forms.Select(attrs={"required": True}),
    )

    preferred_start_term = forms.CharField(
        label=_("When would you like to start?"),
        max_length=50,
        required=False,
        help_text=_("Preferred starting term or month (optional)"),
        widget=forms.TextInput(
            attrs={
                "placeholder": _("e.g., Next month, January 2025"),
            },
        ),
    )

    first_time_at_puc = forms.BooleanField(
        label=_("First time at PUC"),
        initial=True,
        required=False,
        help_text=_("Is this your first time applying to study at PUC?"),
        widget=forms.CheckboxInput(),
    )

    how_did_you_hear = forms.ChoiceField(
        label=_("How did you hear about us?"),
        choices=[("", _("Select an option...")), *list(HowDidYouHearChoices.choices)],
        required=False,
        help_text=_("How did you learn about our school? (optional)"),
        widget=forms.Select(),
    )

    comments = forms.CharField(
        label=_("Additional Comments"),
        required=False,
        help_text=_("Any questions or special requests? (optional)"),
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": _("Tell us anything else we should know..."),
            },
        ),
    )


class ApplicationReviewForm(BaseTestingForm):
    """Step 4: Application review and confirmation.

    Displays summary of entered information for review
    and collects final confirmation.
    """

    information_accurate = forms.BooleanField(
        label=_("I confirm that all information provided is accurate"),
        required=True,
        help_text=_("Please review your information carefully before submitting"),
        widget=forms.CheckboxInput(),
    )

    agree_to_test = forms.BooleanField(
        label=_("I agree to take the placement test"),
        required=True,
        help_text=_("The placement test helps us determine your appropriate level"),
        widget=forms.CheckboxInput(),
    )

    understand_fee = forms.BooleanField(
        label=_("I understand there is a $5 test fee"),
        required=True,
        help_text=_("The test fee must be paid before taking the placement test"),
        widget=forms.CheckboxInput(),
    )


class PaymentInfoForm(BaseTestingForm):
    """Step 5: Payment information collection.

    Collects payment method and reference information
    for the $5 test fee.
    """

    payment_method = forms.ChoiceField(
        label=_("Payment Method"),
        choices=PaymentMethod.choices,
        help_text=_("How will you pay the $5 test fee?"),
        widget=forms.Select(attrs={"required": True}),
    )

    payment_reference = forms.CharField(
        label=_("Payment Reference"),
        max_length=50,
        required=False,
        help_text=_("Transaction ID or reference number (if applicable)"),
        widget=forms.TextInput(
            attrs={
                "placeholder": _(
                    "Enter reference number for bank transfer/mobile payment",
                ),
            },
        ),
    )


class StaffDuplicateReviewForm(forms.Form):
    """Staff form for reviewing duplicate candidates.

    Used by staff to review potential duplicates and make decisions
    about whether to allow application to proceed.
    """

    action = forms.ChoiceField(
        label=_("Review Decision"),
        choices=[
            ("confirm_new", _("Confirm New Student - Allow to Proceed")),
            ("confirm_duplicate", _("Confirm Duplicate - Block Application")),
            ("needs_more_info", _("Needs More Information - Manual Review")),
        ],
        widget=forms.RadioSelect(),
        required=True,
    )

    review_notes = forms.CharField(
        label=_("Review Notes"),
        widget=forms.Textarea(attrs={"rows": 4}),
        required=True,
        help_text=_("Please document your decision and any relevant details"),
    )

    def __init__(self, *args, **kwargs):
        self.potential_student = kwargs.pop("potential_student", None)
        self.duplicate_candidates = kwargs.pop("duplicate_candidates", None)
        super().__init__(*args, **kwargs)


class ClerkPaymentForm(forms.ModelForm):
    """Clerk form for processing test fee payments.

    Used by staff to record payment receipt and update
    payment status in the system.
    """

    class Meta:
        model = TestPayment
        fields = ["payment_method", "payment_reference", "is_paid"]
        widgets = {
            "payment_method": forms.Select(attrs={"class": "form-select"}),
            "payment_reference": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": _("Transaction ID or reference"),
                },
            ),
            "is_paid": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    received_at = forms.DateTimeField(
        label=_("Payment Received At"),
        required=False,
        widget=forms.DateTimeInput(
            attrs={
                "type": "datetime-local",
                "class": "form-input",
            },
        ),
        help_text=_("When was the payment received? (leave blank for now)"),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set default received time to now if payment is being marked as paid
        if self.instance and not self.instance.paid_at:
            self.fields["received_at"].initial = timezone.now()

    def save(self, commit=True):
        """Save with additional payment processing."""
        instance = super().save(commit=False)

        # Set payment timestamp if marked as paid
        if instance.is_paid and not instance.paid_at:
            instance.paid_at = self.cleaned_data.get("received_at") or timezone.now()

        if commit:
            instance.save()

        return instance


class QuickPaymentForm(BaseTestingForm):
    """Quick payment collection form for cashiers.

    Used at the registration desk to collect payment and generate
    access tokens with QR codes for the payment-first workflow.
    """

    student_name = forms.CharField(
        label=_("Student Full Name"),
        max_length=100,
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Enter student's full name"),
                "autocomplete": "name",
            }
        ),
        help_text=_("Student's full name as it will appear on the receipt"),
    )

    student_phone = forms.CharField(
        label=_("Phone Number"),
        max_length=20,
        required=True,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Enter phone number"),
                "autocomplete": "tel",
                "pattern": r"[0-9+\-\s]+",
            }
        ),
        help_text=_("Primary contact number for the student"),
    )

    amount = forms.DecimalField(
        label=_("Payment Amount"),
        max_digits=8,
        decimal_places=2,
        initial=5.00,
        required=True,
        widget=forms.NumberInput(
            attrs={
                "step": "0.01",
                "min": "0",
                "placeholder": _("5.00"),
            }
        ),
        help_text=_("Test fee amount in USD"),
    )

    payment_method = forms.ChoiceField(
        label=_("Payment Method"),
        choices=PaymentMethod.choices,
        initial=PaymentMethod.CASH,
        required=True,
        widget=forms.Select(),
    )

    payment_reference = forms.CharField(
        label=_("Payment Reference"),
        max_length=50,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Receipt number or transaction ID (optional)"),
            }
        ),
        help_text=_("Optional reference number for non-cash payments"),
    )

    print_receipt = forms.BooleanField(
        label=_("Print Receipt"),
        required=False,
        initial=True,
        help_text=_("Print thermal receipt with QR code"),
        widget=forms.CheckboxInput(),
    )

    def clean_student_phone(self):
        """Validate and normalize phone number."""
        phone = self.cleaned_data.get("student_phone", "")

        # Remove common separators
        phone = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")

        # Ensure it starts with country code or add Cambodia code
        if not phone.startswith("+"):
            if phone.startswith("0"):
                phone = "+855" + phone[1:]  # Cambodia country code
            else:
                phone = "+855" + phone

        # Basic validation
        if len(phone) < 10 or len(phone) > 15:
            raise ValidationError(_("Please enter a valid phone number"))

        return phone

    def clean_amount(self):
        """Validate payment amount."""
        amount = self.cleaned_data.get("amount")

        if amount <= 0:
            raise ValidationError(_("Amount must be greater than zero"))

        # You could add business logic here to validate against configured fees
        min_fee = 5.00  # This should come from settings or database
        if amount < min_fee:
            raise ValidationError(_("Minimum test fee is $%(fee)s") % {"fee": min_fee})

        return amount


class TelegramVerificationForm(BaseTestingForm):
    """Form for Telegram verification process.

    Handles both sending verification codes and verifying them
    to link student's Telegram account.
    """

    action = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
    )

    phone_number = forms.CharField(
        label=_("Phone Number"),
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Enter your phone number"),
                "autocomplete": "tel",
            }
        ),
        help_text=_("Phone number associated with your Telegram account"),
    )

    verification_code = forms.CharField(
        label=_("Verification Code"),
        max_length=6,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": _("Enter 6-digit code"),
                "pattern": "[0-9]{6}",
                "maxlength": "6",
                "autocomplete": "off",
                "inputmode": "numeric",
            }
        ),
        help_text=_("Enter the 6-digit code sent to your Telegram"),
    )

    def clean_verification_code(self):
        """Validate verification code format."""
        code = self.cleaned_data.get("verification_code", "")

        if code and not code.isdigit():
            raise ValidationError(_("Code must contain only numbers"))

        if code and len(code) != 6:
            raise ValidationError(_("Code must be exactly 6 digits"))

        return code

    def clean(self):
        """Validate based on action."""
        cleaned_data = super().clean()
        action = cleaned_data.get("action")

        if action == "send_code":
            if not cleaned_data.get("phone_number"):
                self.add_error("phone_number", _("Phone number is required"))

        elif action == "verify_code":
            if not cleaned_data.get("verification_code"):
                self.add_error("verification_code", _("Verification code is required"))

        return cleaned_data
