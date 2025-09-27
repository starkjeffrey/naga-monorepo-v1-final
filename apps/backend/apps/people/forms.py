"""Forms for the People app."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Contact, Gender, Person, StudentProfile


class PersonForm(forms.ModelForm):
    """Form for creating/editing Person records."""

    class Meta:
        model = Person
        fields = [
            "family_name",
            "personal_name",
            "khmer_name",
            "preferred_gender",
            "date_of_birth",
            "citizenship",
            "birth_province",
            "school_email",
            "personal_email",
            "alternate_family_name",
            "alternate_personal_name",
            "use_legal_name_for_documents",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
        }
        help_texts = {
            "use_legal_name_for_documents": _("Check this if legal name differs from preferred name"),
            "alternate_family_name": _("Legal family name (if different from preferred)"),
            "alternate_personal_name": _("Legal personal name (if different from preferred)"),
        }


class StudentProfileForm(forms.ModelForm):
    """Form for creating/editing StudentProfile records."""

    # Add person selection for create view
    person = forms.ModelChoiceField(
        queryset=Person.objects.filter(student_profile__isnull=True),
        required=False,
        help_text=_("Select an existing person or create new below"),
        widget=forms.Select(attrs={"class": "select2"}),
    )

    # Person fields for inline creation
    create_new_person = forms.BooleanField(
        required=False,
        initial=False,
        help_text=_("Check to create a new person record"),
    )
    family_name = forms.CharField(required=False, max_length=100)
    personal_name = forms.CharField(required=False, max_length=100)
    khmer_name = forms.CharField(required=False, max_length=200)
    preferred_gender = forms.ChoiceField(choices=[("", "---"), *list(Gender.choices)], required=False)
    date_of_birth = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}))
    personal_email = forms.EmailField(required=False)
    school_email = forms.EmailField(required=False)

    class Meta:
        model = StudentProfile
        fields = [
            "student_id",
            "is_monk",
            "is_transfer_student",
            "study_time_preference",
            "current_status",
        ]
        widgets = {
            "student_id": forms.NumberInput(attrs={"min": 10000, "max": 99999}),
        }
        help_texts = {
            "student_id": _("5-digit unique student identifier"),
            "is_monk": _("Check if student is a monk (special scheduling considerations apply)"),
            "is_transfer_student": _("Check if student transferred from another institution"),
        }

    def __init__(self, *args, **kwargs):
        # Extract user from kwargs if provided
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        # For update view, don't show person selection
        if self.instance.pk:
            self.fields.pop("person", None)
            self.fields.pop("create_new_person", None)
            self.fields.pop("family_name", None)
            self.fields.pop("personal_name", None)
            self.fields.pop("khmer_name", None)
            self.fields.pop("preferred_gender", None)
            self.fields.pop("date_of_birth", None)
            self.fields.pop("personal_email", None)
            self.fields.pop("school_email", None)

    def clean(self):
        """Validate form data."""
        cleaned_data = super().clean()

        # For create view
        if not self.instance.pk:
            person = cleaned_data.get("person")
            create_new = cleaned_data.get("create_new_person")

            if not person and not create_new:
                raise ValidationError(_("You must either select an existing person or create a new one."))

            if person and create_new:
                raise ValidationError(_("You cannot both select an existing person and create a new one."))

            if create_new:
                # Validate required person fields
                required_fields = [
                    "family_name",
                    "personal_name",
                    "preferred_gender",
                    "date_of_birth",
                ]
                for field in required_fields:
                    if not cleaned_data.get(field):
                        self.add_error(
                            field,
                            _("This field is required when creating a new person."),
                        )

        return cleaned_data

    def save(self, commit=True):
        """Save the form using the StudentProfileService."""
        from .services import StudentProfileService

        # Architecture note: This form is still complex ("fat form"). Consider further extracting
        # the data preparation logic into the service layer for better separation of concerns.

        # For update view, use the regular save
        if self.instance.pk:
            return super().save(commit)

        # For create view, use the service
        if self.cleaned_data.get("create_new_person"):
            person_data = {
                "family_name": self.cleaned_data["family_name"],
                "personal_name": self.cleaned_data["personal_name"],
                "khmer_name": self.cleaned_data.get("khmer_name", ""),
                "preferred_gender": self.cleaned_data["preferred_gender"],
                "date_of_birth": self.cleaned_data["date_of_birth"],
                "personal_email": self.cleaned_data.get("personal_email", ""),
                "school_email": self.cleaned_data.get("school_email", ""),
                "citizenship": "KH",  # Default to Cambodian
            }
            existing_person = None
        else:
            person_data = None
            existing_person = self.cleaned_data["person"]

        student_data = {
            "student_id": self.cleaned_data.get("student_id"),
            "is_monk": self.cleaned_data.get("is_monk", False),
            "is_transfer_student": self.cleaned_data.get("is_transfer_student", False),
            "study_time_preference": self.cleaned_data.get("study_time_preference", "evening"),
            "current_status": self.cleaned_data.get("current_status", StudentProfile.Status.ACTIVE),
        }

        # Get the current user from the form's request if available
        created_by = getattr(self, "user", None)

        if commit:
            return StudentProfileService.create_student_with_profile(
                person_data=person_data,
                student_data=student_data,
                existing_person=existing_person,
                created_by=created_by,
            )
        else:
            # If not committing, prepare the instance
            if person_data:
                self.instance.person = Person(**person_data)
            else:
                self.instance.person = existing_person
            for key, value in student_data.items():
                setattr(self.instance, key, value)
            return self.instance


class StudentStatusChangeForm(forms.Form):
    """Form for changing student status."""

    new_status = forms.ChoiceField(
        choices=StudentProfile.Status.choices,
        label=_("New Status"),
        help_text=_("Select the new status for this student"),
    )

    effective_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_("Effective Date"),
        help_text=_("Date when this status change takes effect"),
    )

    notes = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 4}),
        label=_("Notes"),
        required=False,
        help_text=_("Additional notes about this status change"),
    )

    send_notification = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Send Email Notification"),
        help_text=_("Send notification to student about status change"),
    )

    def __init__(self, *args, **kwargs):
        self.student = kwargs.pop("student", None)
        super().__init__(*args, **kwargs)

        if self.student:
            # Remove current status from choices
            choices = [choice for choice in StudentProfile.Status.choices if choice[0] != self.student.current_status]
            self.fields["new_status"].choices = choices


class ContactForm(forms.ModelForm):
    """Form for emergency contacts."""

    class Meta:
        model = Contact
        fields = [
            "name",
            "relationship",
            "primary_phone",
            "secondary_phone",
            "email",
            "address",
            "is_emergency_contact",
            "is_general_contact",
        ]
        widgets = {
            "address": forms.Textarea(attrs={"rows": 3}),
        }
        help_texts = {
            "is_emergency_contact": _("Check if this contact should be called for medical emergencies"),
            "is_general_contact": _("Check if this contact should be called for misbehavior/absences"),
            "secondary_phone": _("Optional secondary phone number"),
        }
