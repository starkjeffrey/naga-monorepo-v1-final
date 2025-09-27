"""Student management forms for the web interface."""

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.people.forms import StudentProfileForm as BaseStudentProfileForm
from apps.people.models import StudentProfile


class StudentCreateForm(BaseStudentProfileForm):
    """Form for creating students in the web interface."""

    class Meta(BaseStudentProfileForm.Meta):
        widgets = {
            **BaseStudentProfileForm.Meta.widgets,
            "student_id": forms.NumberInput(
                attrs={"class": "form-input", "min": 10000, "max": 99999, "placeholder": "Enter 5-digit student ID"}
            ),
            "current_status": forms.Select(attrs={"class": "form-select"}),
            "study_time_preference": forms.Select(attrs={"class": "form-select"}),
            "is_monk": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "is_transfer_student": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Add CSS classes to person fields when creating new person
        person_fields = ["family_name", "personal_name", "khmer_name", "personal_email", "school_email"]
        for field_name in person_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({"class": "form-input"})

        if "preferred_gender" in self.fields:
            self.fields["preferred_gender"].widget.attrs.update({"class": "form-select"})

        if "date_of_birth" in self.fields:
            self.fields["date_of_birth"].widget.attrs.update({"class": "form-input"})


class StudentSearchForm(forms.Form):
    """Form for searching students."""

    query = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": _("Search by name, student ID, or email..."),
            }
        ),
        label=_("Search"),
    )

    status = forms.ChoiceField(
        choices=[("", _("All Status")), *list(StudentProfile.Status.choices)],
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        label=_("Status"),
    )

    is_monk = forms.BooleanField(
        required=False, widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}), label=_("Monks only")
    )

    is_transfer_student = forms.BooleanField(
        required=False, widget=forms.CheckboxInput(attrs={"class": "form-checkbox"}), label=_("Transfer students only")
    )

    study_time_preference = forms.ChoiceField(
        choices=[("", _("All Time Preferences")), *list(StudentProfile.STUDY_TIME_CHOICES)],
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        label=_("Study Time"),
    )


class StudentUpdateForm(forms.ModelForm):
    """Form for updating student profiles."""

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
            "student_id": forms.NumberInput(attrs={"class": "form-input", "min": 10000, "max": 99999}),
            "current_status": forms.Select(attrs={"class": "form-select"}),
            "study_time_preference": forms.Select(attrs={"class": "form-select"}),
            "is_monk": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
            "is_transfer_student": forms.CheckboxInput(attrs={"class": "form-checkbox"}),
        }
        help_texts = {
            "student_id": _("5-digit unique student identifier"),
            "is_monk": _("Check if student is a monk (special scheduling considerations apply)"),
            "is_transfer_student": _("Check if student transferred from another institution"),
        }
