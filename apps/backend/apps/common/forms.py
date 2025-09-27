"""Forms for the common app.

This module provides forms used across the common app, including
advanced filtering forms for the admin interface.
"""

from datetime import date, timedelta
from typing import Any

from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

from .models import StudentActivityLog

User = get_user_model()


class StudentActivityLogFilterForm(forms.Form):
    """Advanced filtering form for StudentActivityLog admin interface.

    Provides date range picker, multiple student selection, and
    comprehensive filtering options for activity logs.
    """

    # Date range filters
    date_from = forms.DateField(
        label=_("From Date"),
        required=False,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
                "placeholder": _("Start date"),
            },
        ),
        help_text=_("Filter logs from this date onwards"),
    )

    date_to = forms.DateField(
        label=_("To Date"),
        required=False,
        widget=forms.DateInput(
            attrs={
                "type": "date",
                "class": "form-control",
                "placeholder": _("End date"),
            },
        ),
        help_text=_("Filter logs up to this date"),
    )

    # Quick date range options
    QUICK_DATE_CHOICES = [
        ("", _("Custom Range")),
        ("today", _("Today")),
        ("yesterday", _("Yesterday")),
        ("last_7_days", _("Last 7 Days")),
        ("last_30_days", _("Last 30 Days")),
        ("last_90_days", _("Last 90 Days")),
        ("this_month", _("This Month")),
        ("last_month", _("Last Month")),
        ("this_year", _("This Year")),
    ]

    quick_date_range = forms.ChoiceField(
        label=_("Quick Date Range"),
        choices=QUICK_DATE_CHOICES,
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    # Student filters
    student_numbers = forms.CharField(
        label=_("Student Numbers"),
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": _("Enter student numbers separated by commas or new lines"),
            },
        ),
        help_text=_("Multiple student numbers can be entered"),
    )

    # Activity type filter with all choices
    activity_types = forms.MultipleChoiceField(
        label=_("Activity Types"),
        choices=StudentActivityLog.ActivityType.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple(),
        help_text=_("Select one or more activity types to filter"),
    )

    # Term filter
    term_name = forms.CharField(
        label=_("Term"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("e.g., 2023-24-Fall"),
            },
        ),
    )

    # Class filter
    class_code = forms.CharField(
        label=_("Class Code"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("e.g., CS101"),
            },
        ),
    )

    # Visibility filter
    visibility_levels = forms.MultipleChoiceField(
        label=_("Visibility Levels"),
        choices=StudentActivityLog.VisibilityLevel.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple(),
    )

    # System generated filter
    is_system_generated = forms.ChoiceField(
        label=_("Log Source"),
        choices=[
            ("", _("All")),
            ("true", _("System Generated Only")),
            ("false", _("User Actions Only")),
        ],
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
    )

    # Performed by filter
    performed_by = forms.ModelChoiceField(
        label=_("Performed By"),
        queryset=User.objects.filter(is_staff=True).order_by("email"),
        required=False,
        widget=forms.Select(attrs={"class": "form-control"}),
        empty_label=_("Any Staff Member"),
    )

    # Search in description
    description_search = forms.CharField(
        label=_("Search in Description"),
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": _("Search text in descriptions"),
            },
        ),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize form with dynamic choices if needed."""
        super().__init__(*args, **kwargs)

        # Set initial date range if quick_date_range is selected
        if self.data.get("quick_date_range"):
            self._apply_quick_date_range()

    def _apply_quick_date_range(self) -> None:
        """Apply quick date range selection to date fields."""
        quick_range = self.data.get("quick_date_range")
        today = date.today()

        date_ranges = {
            "today": (today, today),
            "yesterday": (today - timedelta(days=1), today - timedelta(days=1)),
            "last_7_days": (today - timedelta(days=7), today),
            "last_30_days": (today - timedelta(days=30), today),
            "last_90_days": (today - timedelta(days=90), today),
            "this_month": (today.replace(day=1), today),
            "last_month": self._get_last_month_range(),
            "this_year": (today.replace(month=1, day=1), today),
        }

        if quick_range in date_ranges:
            date_from, date_to = date_ranges[quick_range]
            self.fields["date_from"].initial = date_from
            self.fields["date_to"].initial = date_to

    def _get_last_month_range(self) -> tuple[date, date]:
        """Get the date range for last month."""
        today = date.today()
        first_day_this_month = today.replace(day=1)
        last_day_last_month = first_day_this_month - timedelta(days=1)
        first_day_last_month = last_day_last_month.replace(day=1)
        return first_day_last_month, last_day_last_month

    def clean_student_numbers(self) -> list[str]:
        """Clean and parse student numbers input."""
        raw_input = self.cleaned_data.get("student_numbers", "")
        if not raw_input:
            return []

        # Split by commas and newlines, strip whitespace
        numbers = []
        for line in raw_input.replace(",", "\n").split("\n"):
            cleaned = line.strip()
            if cleaned:
                numbers.append(cleaned)

        return numbers

    def clean(self) -> dict[str, Any]:
        """Validate form data."""
        cleaned_data = super().clean()

        # Validate date range
        date_from = cleaned_data.get("date_from") if cleaned_data else None
        date_to = cleaned_data.get("date_to") if cleaned_data else None

        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError(
                {
                    "date_to": _("End date must be after start date."),
                },
            )

        return cleaned_data

    def get_queryset_filters(self) -> dict[str, Any]:
        """Convert form data to queryset filters.

        Returns a dictionary that can be used with QuerySet.filter(**filters).
        """
        if not self.is_valid():
            return {}

        filters = {}

        # Date filters
        if self.cleaned_data.get("date_from"):
            filters["created_at__gte"] = self.cleaned_data["date_from"]

        if self.cleaned_data.get("date_to"):
            filters["created_at__lt"] = self.cleaned_data["date_to"] + timedelta(days=1)

        # Student numbers filter
        student_numbers = self.clean_student_numbers()
        if student_numbers:
            filters["student_number__in"] = student_numbers

        # Activity types filter
        if self.cleaned_data.get("activity_types"):
            filters["activity_type__in"] = self.cleaned_data["activity_types"]

        # Term filter
        if self.cleaned_data.get("term_name"):
            filters["term_name__icontains"] = self.cleaned_data["term_name"]

        # Class filter
        if self.cleaned_data.get("class_code"):
            filters["class_code__icontains"] = self.cleaned_data["class_code"]

        # Visibility filter
        if self.cleaned_data.get("visibility_levels"):
            filters["visibility__in"] = self.cleaned_data["visibility_levels"]

        # System generated filter
        is_system = self.cleaned_data.get("is_system_generated")
        if is_system == "true":
            filters["is_system_generated"] = True
        elif is_system == "false":
            filters["is_system_generated"] = False

        # Performed by filter
        if self.cleaned_data.get("performed_by"):
            filters["performed_by"] = self.cleaned_data["performed_by"]

        # Description search
        if self.cleaned_data.get("description_search"):
            filters["description__icontains"] = self.cleaned_data["description_search"]

        return filters


class DateRangeForm(forms.Form):
    """Simple date range form for various filtering needs."""

    start_date = forms.DateField(
        label=_("Start Date"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )

    end_date = forms.DateField(
        label=_("End Date"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )

    def clean(self) -> dict[str, Any]:
        """Validate that end date is after start date."""
        cleaned_data = super().clean()
        if cleaned_data is None:
            return {}
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError(
                {
                    "end_date": _("End date must be after start date."),
                },
            )

        return cleaned_data
