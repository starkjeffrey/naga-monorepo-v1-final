"""Custom forms for scholarships admin."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import Scholarship


class ScholarshipAdminForm(forms.ModelForm):
    """Custom admin form for Scholarship with enhanced validation and error handling."""

    class Meta:
        model = Scholarship
        fields = [
            "name",
            "scholarship_type",
            "student",
            "cycle",
            "sponsored_student",
            "award_percentage",
            "award_amount",
            "start_date",
            "end_date",
            "status",
            "description",
            "conditions",
            "notes",
        ]

    def __init__(self, *args, **kwargs):
        """Initialize the form with optimized querysets."""
        super().__init__(*args, **kwargs)

        # Optimize cycle queryset to only show active cycles
        if "cycle" in self.fields and hasattr(self.fields["cycle"], "queryset"):
            self.fields["cycle"].queryset = (
                self.fields["cycle"].queryset.select_related("division").filter(is_active=True)
            )

        # Make cycle optional for new scholarships
        if not self.instance.pk:
            self.fields["cycle"].required = False

    def clean(self):
        """Enhanced form validation with better error messages."""
        cleaned_data = super().clean()

        if cleaned_data is None:
            return None

        award_percentage = cleaned_data.get("award_percentage")
        award_amount = cleaned_data.get("award_amount")
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        # Validate award amount/percentage
        if award_percentage and award_amount:
            raise ValidationError(
                {
                    "award_percentage": _("Cannot specify both percentage and fixed amount."),
                    "award_amount": _("Cannot specify both percentage and fixed amount."),
                }
            )

        if not award_percentage and not award_amount:
            raise ValidationError(
                {
                    "award_percentage": _("Must specify either percentage or fixed amount."),
                    "award_amount": _("Must specify either percentage or fixed amount."),
                }
            )

        # Validate date range
        if start_date and end_date and end_date <= start_date:
            raise ValidationError({"end_date": _("End date must be after start date.")})

        return cleaned_data
