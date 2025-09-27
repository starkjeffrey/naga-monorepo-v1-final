"""
Modal views for HTMX-powered modal forms.

This module contains views that return modal templates for various forms
like student creation, invoice generation, and payment processing.
"""

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.generic import TemplateView

from apps.finance.models import Invoice
from apps.people.forms import PersonForm, StudentProfileForm
from apps.people.models import StudentProfile

from ..permissions import FinanceRequiredMixin, StaffRequiredMixin
from ..utils import is_htmx_request


class StudentCreateModalView(StaffRequiredMixin, TemplateView):
    """Modal view for creating new students."""

    template_name = "web_interface/modals/student_create_modal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "modal_title": _("Add New Student"),
                "person_form": PersonForm(),
                "student_form": StudentProfileForm(),
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        """Return modal template wrapped in base modal."""
        if not is_htmx_request(request):
            return JsonResponse({"error": "HTMX request required"}, status=400)

        context = self.get_context_data(**kwargs)
        return render(request, self.template_name, context)


class InvoiceCreateModalView(FinanceRequiredMixin, TemplateView):
    """Modal view for creating new invoices."""

    template_name = "web_interface/modals/invoice_create_modal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Check if student is pre-selected
        student_id = self.request.GET.get("student_id")
        selected_student = None
        if student_id:
            try:
                selected_student = StudentProfile.objects.get(id=student_id)
            except StudentProfile.DoesNotExist:
                pass

        context.update(
            {
                "modal_title": _("Generate Invoice"),
                "selected_student": selected_student,
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        """Return modal template wrapped in base modal."""
        if not is_htmx_request(request):
            return JsonResponse({"error": "HTMX request required"}, status=400)

        context = self.get_context_data(**kwargs)
        return render(request, self.template_name, context)


class PaymentProcessModalView(FinanceRequiredMixin, TemplateView):
    """Modal view for processing payments."""

    template_name = "web_interface/modals/payment_process_modal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Check if invoice is pre-selected
        invoice_id = self.request.GET.get("invoice_id")
        selected_invoice = None
        if invoice_id:
            try:
                selected_invoice = Invoice.objects.select_related("student__person").get(id=invoice_id)
            except Invoice.DoesNotExist:
                pass

        context.update(
            {
                "modal_title": _("Process Payment"),
                "selected_invoice": selected_invoice,
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        """Return modal template wrapped in base modal."""
        if not is_htmx_request(request):
            return JsonResponse({"error": "HTMX request required"}, status=400)

        context = self.get_context_data(**kwargs)
        return render(request, self.template_name, context)


class QuickPaymentModalView(FinanceRequiredMixin, TemplateView):
    """Modal view for quick payment processing with student search."""

    template_name = "web_interface/modals/quick_payment_modal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Check if student is pre-selected
        student_id = self.request.GET.get("student_id")
        selected_student = None
        outstanding_invoices = []

        if student_id:
            try:
                selected_student = StudentProfile.objects.get(id=student_id)
                outstanding_invoices = Invoice.objects.filter(
                    student=selected_student, status__in=["SENT", "PARTIALLY_PAID", "OVERDUE"]
                ).order_by("due_date")
            except StudentProfile.DoesNotExist:
                pass

        context.update(
            {
                "modal_title": _("Quick Payment"),
                "selected_student": selected_student,
                "outstanding_invoices": outstanding_invoices,
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        """Return modal template wrapped in base modal."""
        if not is_htmx_request(request):
            return JsonResponse({"error": "HTMX request required"}, status=400)

        context = self.get_context_data(**kwargs)
        return render(request, self.template_name, context)


class StudentEnrollModalView(StaffRequiredMixin, TemplateView):
    """Modal view for enrolling students in courses."""

    template_name = "web_interface/modals/student_enroll_modal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get student from URL parameter
        student_id = self.kwargs.get("student_id")
        student = get_object_or_404(StudentProfile, id=student_id)

        context.update(
            {
                "modal_title": _("Enroll Student in Course"),
                "student": student,
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        """Return modal template wrapped in base modal."""
        if not is_htmx_request(request):
            return JsonResponse({"error": "HTMX request required"}, status=400)

        context = self.get_context_data(**kwargs)
        return render(request, self.template_name, context)


class ConfirmationModalView(LoginRequiredMixin, TemplateView):
    """Generic confirmation modal for various actions."""

    template_name = "web_interface/modals/confirmation_modal.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get parameters from request
        action = self.request.GET.get("action", "confirm")
        title = self.request.GET.get("title", _("Confirm Action"))
        message = self.request.GET.get("message", _("Are you sure you want to proceed?"))
        confirm_text = self.request.GET.get("confirm_text", _("Confirm"))
        confirm_url = self.request.GET.get("confirm_url", "")

        context.update(
            {
                "modal_title": title,
                "message": message,
                "confirm_text": confirm_text,
                "confirm_url": confirm_url,
                "action": action,
            }
        )
        return context

    def get(self, request, *args, **kwargs):
        """Return modal template wrapped in base modal."""
        if not is_htmx_request(request):
            return JsonResponse({"error": "HTMX request required"}, status=400)

        context = self.get_context_data(**kwargs)
        return render(request, self.template_name, context)
