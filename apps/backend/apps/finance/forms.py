"""
Finance app forms for handling special validation requirements.
"""

from django import forms
from django.core.exceptions import ValidationError

from .models import DiscountRule


class DiscountRuleAdminForm(forms.ModelForm):
    """Custom admin form for DiscountRule to handle JSONField validation."""

    class Meta:
        model = DiscountRule
        fields = [
            "rule_name",
            "rule_type",
            "pattern_text",
            "discount_percentage",
            "fixed_amount",
            "applies_to_cycle",
            "applies_to_terms",
            "applies_to_programs",
            "is_active",
            "effective_date",
            "times_applied",
            "last_applied_date",
        ]
        widgets = {
            "applies_to_terms": forms.Textarea(attrs={"rows": 3, "cols": 40}),
            "applies_to_programs": forms.Textarea(attrs={"rows": 3, "cols": 40}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make JSONFields not required so they can be left blank
        self.fields["applies_to_terms"].required = False
        self.fields["applies_to_programs"].required = False

        # Update help text
        self.fields[
            "applies_to_terms"
        ].help_text = "List of term codes (one per line) this rule applies to. Leave completely empty for all terms."
        self.fields[
            "applies_to_programs"
        ].help_text = (
            "List of program codes (one per line) this rule applies to. Leave completely empty for all programs."
        )

        # Add help text for pattern_text based on rule type
        self.fields["pattern_text"].help_text = (
            "Text pattern that triggers this rule:\n"
            "• MONK: Enter 'monk' or 'Monk' to match monk students\n"
            "• EARLY_BIRD: Enter discount text like '10% early bird'\n"
            "• CASH_PLAN: Enter 'cash payment' or similar\n"
            "• WEEKEND: Enter 'weekend' to match weekend classes\n"
            "• CUSTOM: Enter your custom pattern"
        )

        # Add validation help for discount fields
        self.fields[
            "discount_percentage"
        ].help_text = "Percentage discount (e.g., 50 for 50% off). Use this OR fixed_amount, not both."
        self.fields[
            "fixed_amount"
        ].help_text = (
            "Fixed discount amount in dollars (e.g., 50 for $50 off). Use this OR discount_percentage, not both."
        )

    def clean_applies_to_terms(self):
        """Clean the terms field to handle empty input."""
        value = self.cleaned_data.get("applies_to_terms")

        # If it's a string, try to parse it as a list
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            # Split by newlines or commas
            terms = [t.strip() for t in value.replace(",", "\n").split("\n") if t.strip()]
            return terms

        # If it's already a list or None, handle accordingly
        if value is None or value == "":
            return []

        return value

    def clean_applies_to_programs(self):
        """Clean the programs field to handle empty input."""
        value = self.cleaned_data.get("applies_to_programs")

        # If it's a string, try to parse it as a list
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            # Split by newlines or commas
            programs = [p.strip() for p in value.replace(",", "\n").split("\n") if p.strip()]
            return programs

        # If it's already a list or None, handle accordingly
        if value is None or value == "":
            return []

        return value

    def clean(self):
        """Validate the entire form."""
        cleaned_data = super().clean()

        discount_percentage = cleaned_data.get("discount_percentage")
        fixed_amount = cleaned_data.get("fixed_amount")
        rule_type = cleaned_data.get("rule_type")
        pattern_text = cleaned_data.get("pattern_text")

        # Validate that either percentage or fixed amount is provided, not both
        if discount_percentage and fixed_amount:
            raise ValidationError("Please provide either a discount percentage OR a fixed amount, not both.")

        if not discount_percentage and not fixed_amount:
            raise ValidationError("Please provide either a discount percentage or a fixed amount.")

        # Validate pattern_text based on rule type
        if rule_type == "MONK" and pattern_text:
            # Ensure pattern can match monk
            if "monk" not in pattern_text.lower():
                self.add_error(
                    "pattern_text", "For MONK rule type, pattern should contain 'monk' to match monk students."
                )

        return cleaned_data
