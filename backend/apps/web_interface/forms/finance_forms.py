"""Finance management forms for the web interface."""

from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.finance.models import Invoice, Payment
from apps.people.models import StudentProfile


class InvoiceCreateForm(forms.ModelForm):
    """Form for creating invoices."""

    # Add student selection field
    student = forms.ModelChoiceField(
        queryset=StudentProfile.objects.filter(current_status__in=["ACTIVE", "ENROLLED"]),
        widget=forms.Select(attrs={"class": "form-select select2", "data-placeholder": _("Select a student...")}),
        label=_("Student"),
        help_text=_("Select the student for this invoice"),
    )

    class Meta:
        model = Invoice
        fields = [
            "student",
            "issue_date",
            "due_date",
            "notes",
            "subtotal",
            "tax_amount",
            "total_amount",
            "status",
        ]
        widgets = {
            "issue_date": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "due_date": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "notes": forms.Textarea(
                attrs={"class": "form-textarea", "rows": 3, "placeholder": _("Additional notes for the invoice...")}
            ),
            "subtotal": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "min": "0"}),
            "tax_amount": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "min": "0"}),
            "total_amount": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "min": "0"}),
            "status": forms.Select(attrs={"class": "form-select"}),
        }
        help_texts = {
            "subtotal": _("Amount before tax"),
            "tax_amount": _("Tax amount (if applicable)"),
            "total_amount": _("Final amount to be paid"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Set default values
        if not self.instance.pk:
            import datetime

            self.fields["issue_date"].initial = datetime.date.today()
            # Default due date is 30 days from issue date
            self.fields["due_date"].initial = datetime.date.today() + datetime.timedelta(days=30)

    def clean(self):
        cleaned_data = super().clean()

        # Validate date logic
        issue_date = cleaned_data.get("issue_date")
        due_date = cleaned_data.get("due_date")

        if issue_date and due_date and due_date < issue_date:
            raise ValidationError(_("Due date cannot be before issue date."))

        # Validate amounts
        subtotal = cleaned_data.get("subtotal", Decimal("0"))
        tax_amount = cleaned_data.get("tax_amount", Decimal("0"))
        total_amount = cleaned_data.get("total_amount", Decimal("0"))

        expected_total = subtotal + tax_amount
        if abs(total_amount - expected_total) > Decimal("0.01"):
            raise ValidationError(
                _("Total amount (%(total)s) does not match subtotal + tax (%(expected)s)")
                % {"total": total_amount, "expected": expected_total}
            )

        return cleaned_data


class PaymentProcessForm(forms.ModelForm):
    """Form for processing payments."""

    class Meta:
        model = Payment
        fields = [
            "payment_method",
            "amount",
            "payment_date",
            "external_reference",
            "notes",
        ]
        widgets = {
            "payment_method": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(attrs={"class": "form-input", "step": "0.01", "min": "0.01"}),
            "payment_date": forms.DateInput(attrs={"type": "date", "class": "form-input"}),
            "external_reference": forms.TextInput(
                attrs={"class": "form-input", "placeholder": _("Transaction reference number...")}
            ),
            "notes": forms.Textarea(
                attrs={"class": "form-textarea", "rows": 2, "placeholder": _("Additional notes (optional)...")}
            ),
        }
        help_texts = {
            "amount": _("Amount being paid"),
            "external_reference": _("Bank transaction or receipt number"),
            "notes": _("Optional notes about this payment"),
        }

    def __init__(self, *args, invoice=None, **kwargs):
        self.invoice = invoice
        super().__init__(*args, **kwargs)

        # Set default values
        if not self.instance.pk:
            import datetime

            self.fields["payment_date"].initial = datetime.date.today()

            # If we have an invoice, suggest the amount due
            if self.invoice:
                self.fields["amount"].initial = self.invoice.amount_due

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")

        if amount and amount <= 0:
            raise ValidationError(_("Payment amount must be greater than zero."))

        # Check if payment amount exceeds invoice amount due
        if self.invoice and amount and amount > self.invoice.amount_due:
            raise ValidationError(
                _("Payment amount (%(amount)s) cannot exceed amount due (%(due)s).")
                % {"amount": amount, "due": self.invoice.amount_due}
            )

        return amount


class InvoiceSearchForm(forms.Form):
    """Form for searching invoices."""

    search = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-input",
                "placeholder": _("Search by invoice number, student name..."),
            }
        ),
        label=_("Search"),
    )

    status = forms.ChoiceField(
        choices=[("", _("All Status")), *list(Invoice.InvoiceStatus.choices)],
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
        label=_("Status"),
    )

    date_from = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date", "class": "form-input"}), label=_("From Date")
    )

    date_to = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date", "class": "form-input"}), label=_("To Date")
    )

    def clean(self):
        cleaned_data = super().clean()

        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")

        if date_from and date_to and date_from > date_to:
            raise ValidationError(_("From date cannot be after to date."))

        return cleaned_data
