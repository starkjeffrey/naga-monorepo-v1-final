"""Cashier interface views for payment collection and cash management.

Provides comprehensive cashier functionality including:
- Student payment collection
- Cash drawer management
- Receipt generation
- Session tracking
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.finance.models import (
    Invoice,
    Payment,
)
from apps.finance.services import CashierService, PaymentService, ReceiptService
from apps.people.models import StudentProfile

logger = logging.getLogger(__name__)


@runtime_checkable
class PaymentLike(Protocol):
    id: int
    currency: Any


class CashierDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Main cashier dashboard for payment collection."""

    template_name = "finance/cashier/dashboard.html"
    permission_required = "finance.add_payment"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        # Get current cashier session
        session = CashierService.get_or_create_session(self.request.user)

        # Get today's statistics
        today = timezone.now().date()
        start_datetime = datetime.combine(today, datetime.min.time())
        end_datetime = datetime.combine(today, datetime.max.time())
        today_payments = Payment.objects.filter(
            processed_by=self.request.user,
            payment_date__gte=start_datetime,
            payment_date__lte=end_datetime,
            status=Payment.PaymentStatus.COMPLETED,
        )

        # Calculate totals by payment method
        payment_totals = today_payments.values("payment_method").annotate(total=Sum("amount"), count=Sum("id"))

        context.update(
            {
                "session": session,
                "today_total": today_payments.aggregate(Sum("amount"))["amount__sum"] or Decimal("0.00"),
                "today_count": today_payments.count(),
                "payment_totals": {
                    item["payment_method"]: {
                        "total": item["total"],
                        "count": item["count"],
                    }
                    for item in payment_totals
                },
                "recent_payments": today_payments.select_related("invoice__student__person").order_by(
                    "-processed_date",
                )[:10],
            },
        )

        return context


class StudentSearchView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """AJAX endpoint for student search with autocomplete."""

    permission_required = "finance.add_payment"

    def get(self, request: HttpRequest) -> JsonResponse:
        query = request.GET.get("q", "").strip()
        if len(query) < 2:
            return JsonResponse({"results": []})

        # Search by student ID, name, or phone
        students = StudentProfile.objects.select_related("person").filter(
            Q(student_id__icontains=query)
            | Q(person__first_name__icontains=query)
            | Q(person__last_name__icontains=query)
            | Q(person__phone__icontains=query),
        )[:20]

        results = []
        for student in students:
            # Get current balance
            balance = PaymentService.get_student_balance(student)

            results.append(
                {
                    "id": student.id,
                    "student_id": student.student_id,
                    "name": str(student),
                    "phone": student.person.phone or "",
                    "program": student.get_current_program_display(),
                    "balance": float(balance),
                    "photo_url": (student.person.photo.url if student.person.photo else None),
                },
            )

        return JsonResponse({"results": results})


class PaymentCollectionView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Handle payment collection for a student."""

    permission_required = "finance.add_payment"

    def get(self, request: HttpRequest, student_id: int) -> HttpResponse:
        """Display payment collection form."""
        student = get_object_or_404(StudentProfile, id=student_id)

        # Get student's outstanding invoices
        outstanding_invoices = Invoice.objects.filter(
            student=student,
            status__in=[
                Invoice.InvoiceStatus.SENT,
                Invoice.InvoiceStatus.PARTIALLY_PAID,
            ],
        ).order_by("due_date")

        # Calculate total balance
        total_balance = sum(invoice.amount_due for invoice in outstanding_invoices)

        # Get payment methods
        payment_methods = [{"value": method[0], "label": method[1]} for method in Payment.PaymentMethod.choices]

        context = {
            "student": student,
            "outstanding_invoices": outstanding_invoices,
            "total_balance": total_balance,
            "payment_methods": payment_methods,
            "today": timezone.now().date(),
        }

        return render(request, "finance/cashier/payment_collection.html", context)

    @transaction.atomic
    def post(self, request: HttpRequest, student_id: int) -> HttpResponse:
        """Process payment collection."""
        student = get_object_or_404(StudentProfile, id=student_id)

        try:
            # Parse payment data
            amount = Decimal(request.POST.get("amount", "0"))
            payment_method = request.POST.get("payment_method")
            reference = request.POST.get("reference", "")
            notes = request.POST.get("notes", "")

            # Validate amount
            if amount <= 0:
                raise ValueError("Payment amount must be greater than zero")

            # Get invoices to apply payment to
            invoice_ids = request.POST.getlist("invoice_ids[]")
            if not invoice_ids:
                # Apply to oldest invoices first
                invoices = Invoice.objects.filter(
                    student=student,
                    status__in=[
                        Invoice.InvoiceStatus.SENT,
                        Invoice.InvoiceStatus.PARTIALLY_PAID,
                    ],
                ).order_by("due_date")
            else:
                invoices = Invoice.objects.filter(id__in=invoice_ids)

            # Process payment
            from typing import cast

            payment: PaymentLike = cast(
                "PaymentLike",
                PaymentService.process_payment(
                    student=student,
                    amount=amount,
                    payment_method=payment_method,
                    invoices=list(invoices),
                    reference=reference,
                    notes=notes,
                    processed_by=request.user,
                ),
            )

            # Generate receipt
            receipt_url = reverse("finance:cashier-receipt", kwargs={"payment_id": payment.id})

            messages.success(
                request,
                f"Payment of {amount} {payment.currency} collected successfully.",
            )

            return JsonResponse(
                {
                    "success": True,
                    "payment_id": payment.id,
                    "receipt_url": receipt_url,
                    "remaining_balance": float(PaymentService.get_student_balance(student)),
                },
            )

        except Exception as e:
            logger.error(f"Payment collection error: {e}")
            return JsonResponse({"success": False, "error": str(e)}, status=400)


class ReceiptView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Generate and display payment receipt."""

    permission_required = "finance.view_payment"

    def get(self, request: HttpRequest, payment_id: int) -> HttpResponse:
        """Display receipt."""
        payment: PaymentLike = get_object_or_404(
            Payment.objects.select_related("invoice__student__person", "processed_by"),
            id=payment_id,
        )

        context = {
            "payment": payment,
            "institution_name": "Pannasastra University of Cambodia",
            "institution_address": "Siem Reap Campus",
            "print_time": timezone.now(),
        }

        # Check if PDF requested
        if request.GET.get("format") == "pdf":
            from typing import cast

            return ReceiptService.generate_pdf_receipt(cast("Any", payment))

        return render(request, "finance/cashier/receipt.html", context)


class CashDrawerManagementView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Manage cash drawer operations."""

    permission_required = "finance.add_payment"

    def get(self, request: HttpRequest) -> HttpResponse:
        """Display cash drawer management form."""
        session = CashierService.get_or_create_session(request.user)

        # Get cash denominations
        denominations = [
            {"value": 100, "label": "$100"},
            {"value": 50, "label": "$50"},
            {"value": 20, "label": "$20"},
            {"value": 10, "label": "$10"},
            {"value": 5, "label": "$5"},
            {"value": 1, "label": "$1"},
        ]

        context = {
            "session": session,
            "denominations": denominations,
            "current_cash": CashierService.get_current_cash_balance(request.user),
        }

        return render(request, "finance/cashier/cash_drawer.html", context)

    def post(self, request: HttpRequest) -> HttpResponse:
        """Process cash drawer operations."""
        action = request.POST.get("action")

        try:
            if action == "open":
                # Process opening count
                opening_cash = Decimal(request.POST.get("opening_cash", "0"))
                CashierService.open_cash_drawer(request.user, opening_cash)
                messages.success(request, "Cash drawer opened successfully.")

            elif action == "close":
                # Process closing count
                closing_cash = Decimal(request.POST.get("closing_cash", "0"))
                variance = CashierService.close_cash_drawer(request.user, closing_cash)

                if abs(variance) > Decimal("0.01"):
                    messages.warning(request, f"Cash drawer closed with variance of ${variance}")
                else:
                    messages.success(request, "Cash drawer balanced and closed.")

            return redirect("finance:cashier-dashboard")

        except Exception as e:
            logger.error(f"Cash drawer error: {e}")
            messages.error(request, str(e))
            return redirect("finance:cash-drawer")


class TransactionHistoryView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """View transaction history for current cashier."""

    model = Payment
    template_name = "finance/cashier/transaction_history.html"
    context_object_name = "payments"
    paginate_by = 50
    permission_required = "finance.view_payment"

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by current user
        queryset = queryset.filter(processed_by=self.request.user)

        # Filter by date range
        date_from = self.request.GET.get("date_from")
        date_to = self.request.GET.get("date_to")

        if date_from:
            queryset = queryset.filter(payment_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(payment_date__lte=date_to)

        # Filter by payment method
        payment_method = self.request.GET.get("payment_method")
        if payment_method:
            queryset = queryset.filter(payment_method=payment_method)

        # Filter by status
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        return queryset.select_related("invoice__student__person").order_by("-payment_date", "-processed_date")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Add filter options
        context["payment_methods"] = Payment.PaymentMethod.choices
        context["payment_statuses"] = Payment.PaymentStatus.choices

        # Calculate totals for filtered results
        totals = self.get_queryset().aggregate(total_amount=Sum("amount"), total_count=Sum("id"))
        context["total_amount"] = totals["total_amount"] or Decimal("0.00")
        context["total_count"] = self.get_queryset().count()

        return context


class RefundProcessingView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Process payment refunds with supervisor approval."""

    permission_required = "finance.add_payment"

    def post(self, request: HttpRequest, payment_id: int) -> HttpResponse:
        """Process refund request."""
        payment = get_object_or_404(Payment, id=payment_id)

        try:
            amount = Decimal(request.POST.get("amount", "0"))
            reason = request.POST.get("reason", "")

            # Process refund
            from typing import cast

            refund: PaymentLike = cast(
                "PaymentLike",
                PaymentService.process_refund(
                    payment=payment,
                    amount=amount,
                    reason=reason,
                    processed_by=request.user,
                ),
            )

            messages.success(request, f"Refund of {amount} {refund.currency} processed successfully.")

            return JsonResponse(
                {
                    "success": True,
                    "refund_id": refund.id,
                },
            )

        except Exception as e:
            logger.error(f"Refund processing error: {e}")
            return JsonResponse({"success": False, "error": str(e)}, status=400)
