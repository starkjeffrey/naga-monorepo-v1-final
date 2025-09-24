"""
Finance management views for the web interface.

This module contains views for billing, payments, and financial management.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib import messages
from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.generic import DetailView, ListView, TemplateView

from apps.finance.models import Invoice, Payment
from apps.people.models import StudentProfile

from ..permissions import FinanceRequiredMixin
from ..utils import is_htmx_request


class BillingListView(FinanceRequiredMixin, ListView):
    """List view for student billing and invoices."""

    model = Invoice
    template_name = "web_interface/pages/finance/billing.html"
    context_object_name = "invoices"
    paginate_by = 20

    def get_queryset(self):
        """Filter invoices based on search and status parameters."""
        queryset = Invoice.objects.select_related("student__person").prefetch_related("payments")

        # Search functionality
        search = self.request.GET.get("search")
        if search:
            queryset = queryset.filter(
                Q(invoice_number__icontains=search)
                | Q(student__person__full_name__icontains=search)
                | Q(student__student_id__startswith=search)  # Optimized: students search by ID prefix
            )

        # Status filtering
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        # Date filtering
        date_from = self.request.GET.get("date_from")
        date_to = self.request.GET.get("date_to")
        if date_from:
            queryset = queryset.filter(issue_date__gte=date_from)
        if date_to:
            queryset = queryset.filter(issue_date__lte=date_to)

        return queryset.order_by("-issue_date")

    def get_template_names(self):
        """Return appropriate template for HTMX requests."""
        if is_htmx_request(self.request):
            return ["web_interface/pages/finance/billing_content.html"]
        return [self.template_name]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get billing statistics
        billing_stats = {
            "total_invoices": Invoice.objects.count(),
            "pending_invoices": Invoice.objects.filter(status__in=["SENT", "PARTIALLY_PAID"]).count(),
            "overdue_invoices": Invoice.objects.filter(status="OVERDUE").count(),
            "total_amount": Invoice.objects.aggregate(total=Sum("total_amount"))["total"] or Decimal("0"),
            "pending_amount": Invoice.objects.filter(status__in=["SENT", "PARTIALLY_PAID", "OVERDUE"]).aggregate(
                total=Sum("total_amount")
            )["total"]
            or Decimal("0"),
        }

        context.update(
            {
                "page_title": _("Billing & Invoices"),
                "current_page": "billing",
                "search_query": self.request.GET.get("search", ""),
                "selected_status": self.request.GET.get("status", ""),
                "date_from": self.request.GET.get("date_from", ""),
                "date_to": self.request.GET.get("date_to", ""),
                "status_choices": Invoice.InvoiceStatus.choices,
                "billing_stats": billing_stats,
            }
        )
        return context


class InvoiceDetailView(FinanceRequiredMixin, DetailView):
    """Detail view for individual invoice."""

    model = Invoice
    template_name = "web_interface/pages/finance/invoice_detail.html"
    context_object_name = "invoice"

    def get_queryset(self):
        """Optimize queries with related data."""
        return Invoice.objects.select_related("student__person").prefetch_related("line_items", "payments")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice = self.get_object()

        # Calculate payment summary
        total_paid = invoice.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0")

        remaining_balance = invoice.total_amount - total_paid

        payment_summary = {
            "total_amount": invoice.total_amount,
            "total_paid": total_paid,
            "remaining_balance": remaining_balance,
            "payment_count": invoice.payments.count(),
        }

        context.update(
            {
                "page_title": _("Invoice Details - {}").format(invoice.invoice_number),
                "current_page": "billing",
                "payment_summary": payment_summary,
            }
        )
        return context


class InvoiceCreateView(FinanceRequiredMixin, TemplateView):
    """View for creating new invoices."""

    template_name = "web_interface/pages/finance/invoice_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get student from query parameter if provided
        student_id = self.request.GET.get("student_id")
        selected_student = None
        if student_id:
            try:
                selected_student = StudentProfile.objects.get(id=student_id)
            except StudentProfile.DoesNotExist:
                pass

        context.update(
            {
                "page_title": _("Generate Invoice"),
                "current_page": "billing",
                "selected_student": selected_student,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        """Handle invoice creation."""
        try:
            student_id = request.POST.get("student_id")
            amount = Decimal(request.POST.get("amount", "0"))
            description = request.POST.get("description", "")

            if not student_id or amount <= 0:
                raise ValueError(_("Invalid student or amount"))

            student = StudentProfile.objects.get(id=student_id)

            # Create invoice
            with transaction.atomic():
                invoice = Invoice.objects.create(
                    student=student,
                    invoice_number=f"INV-{timezone.now().strftime('%Y%m%d')}-{student.id}",
                    issue_date=date.today(),
                    due_date=date.today() + timedelta(days=30),
                    total_amount=amount,
                    status="SENT",
                    description=description,
                )

                # Create line item (simplified)
                invoice.line_items.create(
                    description=description,
                    quantity=1,
                    unit_price=amount,
                    total_price=amount,
                )

            messages.success(
                request,
                _("Invoice {} created successfully for {}").format(invoice.invoice_number, student.person.full_name),
            )

            if is_htmx_request(request):
                return JsonResponse(
                    {
                        "success": True,
                        "redirect_url": reverse_lazy("web_interface:invoice-detail", kwargs={"pk": invoice.pk}),
                        "message": _("Invoice created successfully"),
                    }
                )

            return redirect("web_interface:invoice-detail", pk=invoice.pk)

        except Exception as e:
            messages.error(request, _("Error creating invoice: {}").format(str(e)))

            if is_htmx_request(request):
                # Re-render the modal form with errors
                context = self.get_context_data()
                context.update(
                    {
                        "modal_title": _("Generate Invoice"),
                        "form_errors": [str(e)],
                    }
                )
                return render(request, "web_interface/modals/invoice_create_modal.html", context, status=400)

            return self.render_to_response(self.get_context_data())


class PaymentProcessingView(FinanceRequiredMixin, TemplateView):
    """View for processing payments."""

    template_name = "web_interface/pages/finance/payments.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get recent payments
        recent_payments = Payment.objects.select_related("invoice__student__person").order_by("-payment_date")[:20]

        # Get payment statistics
        today = date.today()
        payment_stats = {
            "total_payments": Payment.objects.count(),
            "today_payments": Payment.objects.filter(payment_date=today).count(),
            "today_amount": Payment.objects.filter(payment_date=today).aggregate(total=Sum("amount"))["total"]
            or Decimal("0"),
            "month_amount": Payment.objects.filter(
                payment_date__month=today.month, payment_date__year=today.year
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0"),
        }

        # Get outstanding invoices
        outstanding_invoices = (
            Invoice.objects.filter(status__in=["SENT", "PARTIALLY_PAID", "OVERDUE"])
            .select_related("student__person")
            .order_by("due_date")[:10]
        )

        context.update(
            {
                "page_title": _("Payment Processing"),
                "current_page": "payments",
                "recent_payments": recent_payments,
                "payment_stats": payment_stats,
                "outstanding_invoices": outstanding_invoices,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        """Process a payment."""
        try:
            invoice_id = request.POST.get("invoice_id")
            amount = Decimal(request.POST.get("amount", "0"))
            payment_method = request.POST.get("payment_method", "CASH")
            notes = request.POST.get("notes", "")

            if not invoice_id or amount <= 0:
                raise ValueError(_("Invalid invoice or payment amount"))

            invoice = Invoice.objects.get(id=invoice_id)

            # Calculate remaining balance
            total_paid = invoice.payments.aggregate(total=Sum("amount"))["total"] or Decimal("0")
            remaining_balance = invoice.total_amount - total_paid

            if amount > remaining_balance:
                raise ValueError(_("Payment amount exceeds remaining balance"))

            # Create payment
            with transaction.atomic():
                Payment.objects.create(
                    invoice=invoice,
                    amount=amount,
                    payment_date=date.today(),
                    payment_method=payment_method,
                    notes=notes,
                    processed_by=request.user,
                )

                # Update invoice status
                new_total_paid = total_paid + amount
                if new_total_paid >= invoice.total_amount:
                    invoice.status = "PAID"
                else:
                    invoice.status = "PARTIALLY_PAID"
                invoice.save()

            messages.success(
                request,
                _("Payment of ${} processed successfully for invoice {}").format(amount, invoice.invoice_number),
            )

            if is_htmx_request(request):
                return JsonResponse(
                    {
                        "success": True,
                        "message": _("Payment processed successfully"),
                        "remaining_balance": float(remaining_balance - amount),
                    }
                )

        except Exception as e:
            messages.error(request, _("Error processing payment: {}").format(str(e)))

            if is_htmx_request(request):
                # Re-render the modal form with errors
                context = self.get_context_data()
                context.update(
                    {
                        "modal_title": _("Process Payment"),
                        "form_errors": [str(e)],
                    }
                )
                return render(request, "web_interface/modals/payment_process_modal.html", context, status=400)

        return redirect("web_interface:payment-processing")


class StudentAccountView(FinanceRequiredMixin, DetailView):
    """View for individual student financial account."""

    model = StudentProfile
    template_name = "web_interface/pages/finance/student_account.html"
    context_object_name = "student"
    pk_url_kwarg = "student_id"

    def get_queryset(self):
        """Optimize queries with financial data."""
        return StudentProfile.objects.select_related("person").prefetch_related(
            "invoices__payments", "invoices__line_items"
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.get_object()

        # Calculate account summary
        total_invoiced = student.invoices.aggregate(total=Sum("total_amount"))["total"] or Decimal("0")

        total_paid = Payment.objects.filter(invoice__student=student).aggregate(total=Sum("amount"))[
            "total"
        ] or Decimal("0")

        account_balance = total_invoiced - total_paid

        account_summary = {
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "account_balance": account_balance,
            "invoice_count": student.invoices.count(),
            "payment_count": Payment.objects.filter(invoice__student=student).count(),
        }

        # Get recent transactions
        recent_invoices = student.invoices.order_by("-issue_date")[:10]
        recent_payments = (
            Payment.objects.filter(invoice__student=student).select_related("invoice").order_by("-payment_date")[:10]
        )

        context.update(
            {
                "page_title": _("Student Account - {}").format(student.person.full_name),
                "current_page": "accounts",
                "account_summary": account_summary,
                "recent_invoices": recent_invoices,
                "recent_payments": recent_payments,
            }
        )
        return context


class CashierSessionView(FinanceRequiredMixin, TemplateView):
    """Enhanced cashier session management with payment processing."""

    template_name = "web_interface/pages/finance/cashier_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        from apps.finance.services import CashierService

        # Get or create current cashier session
        session = CashierService.get_or_create_session(self.request.user)

        today = timezone.now().date()

        # Get today's transactions for this user
        today_payments = Payment.objects.filter(
            payment_date__date=today, processed_by=self.request.user, status=Payment.PaymentStatus.COMPLETED
        ).select_related("invoice__student__person")

        # Calculate cashier statistics
        cashier_stats = {
            "session_number": session.session_number,
            "session_opened": session.opened_at,
            "transactions_today": today_payments.count(),
            "cash_received": today_payments.filter(payment_method=Payment.PaymentMethod.CASH).aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0"),
            "card_received": today_payments.filter(payment_method__in=[Payment.PaymentMethod.CREDIT_CARD]).aggregate(
                total=Sum("amount")
            )["total"]
            or Decimal("0"),
            "other_received": today_payments.exclude(
                payment_method__in=[Payment.PaymentMethod.CASH, Payment.PaymentMethod.CREDIT_CARD]
            ).aggregate(total=Sum("amount"))["total"]
            or Decimal("0"),
            "total_received": today_payments.aggregate(total=Sum("amount"))["total"] or Decimal("0"),
            "opening_balance": session.opening_balance,
            "expected_balance": session.opening_balance
            + (
                today_payments.filter(payment_method=Payment.PaymentMethod.CASH).aggregate(total=Sum("amount"))[
                    "total"
                ]
                or Decimal("0")
            ),
        }

        # Get payment method summary
        payment_methods = (
            today_payments.values("payment_method").annotate(count=Count("id"), total=Sum("amount")).order_by("-total")
        )

        # Get recent transactions for display
        recent_transactions = today_payments.order_by("-payment_date", "-processed_date")[:10]

        # Get pending transactions (for quick access)
        pending_invoices = (
            Invoice.objects.filter(status__in=[Invoice.InvoiceStatus.SENT, Invoice.InvoiceStatus.PARTIALLY_PAID])
            .select_related("student__person")
            .order_by("due_date")[:5]
        )

        context.update(
            {
                "page_title": _("Cashier Dashboard"),
                "current_page": "cashier",
                "session": session,
                "today_payments": recent_transactions,
                "cashier_stats": cashier_stats,
                "payment_methods": payment_methods,
                "pending_invoices": pending_invoices,
                "payment_method_choices": Payment.PaymentMethod.choices,
                "currency_choices": ["USD", "KHR"],
            }
        )
        return context


class FinancialReportsView(FinanceRequiredMixin, TemplateView):
    """View for financial reports and analytics."""

    template_name = "web_interface/pages/finance/reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get date range from request
        date_from = self.request.GET.get("date_from")
        date_to = self.request.GET.get("date_to")

        if not date_from:
            date_from = date.today() - timedelta(days=30)
        else:
            date_from = date.fromisoformat(date_from)

        if not date_to:
            date_to = date.today()
        else:
            date_to = date.fromisoformat(date_to)

        # Revenue report
        revenue_data = Payment.objects.filter(payment_date__range=[date_from, date_to]).aggregate(
            total_revenue=Sum("amount"), transaction_count=Count("id"), avg_payment=Avg("amount")
        )

        # Outstanding balances
        outstanding_data = Invoice.objects.filter(status__in=["SENT", "PARTIALLY_PAID", "OVERDUE"]).aggregate(
            total_outstanding=Sum("total_amount"),
            overdue_count=Count("id", filter=Q(status="OVERDUE")),
            pending_count=Count("id", filter=Q(status__in=["SENT", "PARTIALLY_PAID"])),
        )

        # Payment method breakdown
        payment_methods = (
            Payment.objects.filter(payment_date__range=[date_from, date_to])
            .values("payment_method")
            .annotate(count=Count("id"), total=Sum("amount"))
            .order_by("-total")
        )

        # Daily revenue trend
        daily_revenue = (
            Payment.objects.filter(payment_date__range=[date_from, date_to])
            .values("payment_date")
            .annotate(daily_total=Sum("amount"), daily_count=Count("id"))
            .order_by("payment_date")
        )

        context.update(
            {
                "page_title": _("Financial Reports"),
                "current_page": "reports",
                "date_from": date_from,
                "date_to": date_to,
                "revenue_data": revenue_data,
                "outstanding_data": outstanding_data,
                "payment_methods": payment_methods,
                "daily_revenue": daily_revenue,
            }
        )
        return context


class QuickPaymentView(FinanceRequiredMixin, TemplateView):
    """HTMX view for quick payment processing."""

    template_name = "web_interface/pages/finance/quick_payment.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get student from query parameter
        student_id = self.request.GET.get("student_id")
        if student_id:
            try:
                student = StudentProfile.objects.get(id=student_id)
                # Get outstanding invoices for this student
                outstanding_invoices = student.invoices.filter(
                    status__in=["SENT", "PARTIALLY_PAID", "OVERDUE"]
                ).order_by("due_date")

                context.update(
                    {
                        "student": student,
                        "outstanding_invoices": outstanding_invoices,
                    }
                )
            except StudentProfile.DoesNotExist:
                pass

        return context


class StudentSearchView(FinanceRequiredMixin, TemplateView):
    """HTMX search endpoint for students in finance context."""

    template_name = "web_interface/pages/finance/student_search_results.html"

    def get(self, request, *args, **kwargs):
        """Handle HTMX search requests."""
        search_query = request.GET.get("q", "").strip()

        if len(search_query) < 2:
            return JsonResponse({"results": [], "message": _("Please enter at least 2 characters to search")})

        # Search students with outstanding balances or recent financial activity
        students = (
            StudentProfile.objects.filter(
                Q(person__full_name__icontains=search_query)
                | Q(person__family_name__icontains=search_query)
                | Q(student_id__startswith=search_query)  # Optimized: students search by ID prefix
            )
            .select_related("person")
            .annotate(
                total_invoiced=Sum("invoices__total_amount"),
                outstanding_balance=Sum(
                    "invoices__total_amount", filter=Q(invoices__status__in=["SENT", "PARTIALLY_PAID", "OVERDUE"])
                ),
            )[:10]
        )

        if is_htmx_request(request):
            context = {"students": students, "search_query": search_query}
            return render(request, self.template_name, context)

        results = []
        for student in students:
            results.append(
                {
                    "id": student.id,
                    "name": student.person.full_name,
                    "student_id": student.student_id,
                    "outstanding_balance": float(student.outstanding_balance or 0),
                    "url": reverse_lazy("web_interface:student-account", kwargs={"student_id": student.pk}),
                }
            )

        return JsonResponse({"results": results, "count": len(results)})


# Enhanced HTMX Cashier Endpoints


def cashier_student_search(request):
    """HTMX endpoint for student search with financial balance info"""
    from django.shortcuts import render

    query = request.GET.get("q", "")

    if len(query) < 2:
        return render(request, "web_interface/partials/cashier/student_search_empty.html")

    students = (
        StudentProfile.objects.filter(
            Q(student_id__startswith=query)  # Optimized: students search by ID prefix
            | Q(person__full_name__icontains=query)
            | Q(person__khmer_name__icontains=query)
            | Q(person__email__icontains=query)
            | Q(person__phone__icontains=query)
        )
        .select_related("person")
        .annotate(
            outstanding_balance=Sum(
                "invoices__total_amount",
                filter=Q(
                    invoices__status__in=[
                        Invoice.InvoiceStatus.SENT,
                        Invoice.InvoiceStatus.PARTIALLY_PAID,
                        Invoice.InvoiceStatus.OVERDUE,
                    ]
                ),
            )
            - Sum(
                "invoices__payments__amount",
                filter=Q(
                    invoices__status__in=[
                        Invoice.InvoiceStatus.SENT,
                        Invoice.InvoiceStatus.PARTIALLY_PAID,
                        Invoice.InvoiceStatus.OVERDUE,
                    ]
                ),
            )
        )[:10]
    )

    return render(
        request, "web_interface/partials/cashier/student_search_results.html", {"students": students, "query": query}
    )


def cashier_student_detail(request, student_id):
    """HTMX endpoint for student financial details"""
    from django.shortcuts import get_object_or_404, render

    student = get_object_or_404(
        StudentProfile.objects.select_related("person").prefetch_related("invoices__payments", "invoices__line_items"),
        id=student_id,
    )

    # Calculate student financial summary
    outstanding_invoices = student.invoices.filter(
        status__in=[Invoice.InvoiceStatus.SENT, Invoice.InvoiceStatus.PARTIALLY_PAID, Invoice.InvoiceStatus.OVERDUE]
    ).order_by("due_date")

    total_outstanding = sum(invoice.amount_due for invoice in outstanding_invoices)

    # Get recent payment history
    recent_payments = (
        Payment.objects.filter(invoice__student=student, status=Payment.PaymentStatus.COMPLETED)
        .select_related("invoice")
        .order_by("-payment_date")[:5]
    )

    return render(
        request,
        "web_interface/partials/cashier/student_detail.html",
        {
            "student": student,
            "outstanding_invoices": outstanding_invoices,
            "total_outstanding": total_outstanding,
            "recent_payments": recent_payments,
            "payment_method_choices": Payment.PaymentMethod.choices,
        },
    )


def process_payment(request):
    """HTMX endpoint to process payment"""
    from django.shortcuts import get_object_or_404, render

    if request.method != "POST":
        return JsonResponse({"error": "Only POST requests allowed"}, status=405)

    try:
        student_id = request.POST.get("student_id")
        amount = Decimal(request.POST.get("amount", "0"))
        payment_method = request.POST.get("payment_method", Payment.PaymentMethod.CASH)
        currency = request.POST.get("currency", "USD")
        notes = request.POST.get("notes", "")

        if not student_id or amount <= 0:
            return render(
                request,
                "web_interface/partials/cashier/payment_message.html",
                {"message": _("Please select a student and enter a valid amount"), "type": "error"},
            )

        student = get_object_or_404(StudentProfile, id=student_id)

        # Use the existing payment service from the finance app

        # Get the oldest outstanding invoice for this student
        outstanding_invoice = (
            student.invoices.filter(
                status__in=[
                    Invoice.InvoiceStatus.SENT,
                    Invoice.InvoiceStatus.PARTIALLY_PAID,
                    Invoice.InvoiceStatus.OVERDUE,
                ]
            )
            .order_by("due_date")
            .first()
        )

        if not outstanding_invoice:
            return render(
                request,
                "web_interface/partials/cashier/payment_message.html",
                {"message": _("No outstanding invoices found for this student"), "type": "warning"},
            )

        # Process payment using the existing service
        with transaction.atomic():
            # Generate unique payment reference
            payment_reference = f"PAY-{timezone.now().strftime('%Y%m%d%H%M%S')}-{student.id}"

            payment = Payment.objects.create(
                payment_reference=payment_reference,
                invoice=outstanding_invoice,
                amount=amount,
                currency=currency,
                payment_method=payment_method,
                status=Payment.PaymentStatus.COMPLETED,
                payment_date=timezone.now(),
                processed_date=timezone.now(),
                processed_by=request.user,
                notes=notes,
            )

            # Update invoice status and paid amount
            total_paid = outstanding_invoice.payments.filter(status=Payment.PaymentStatus.COMPLETED).aggregate(
                total=Sum("amount")
            )["total"] or Decimal("0")

            outstanding_invoice.paid_amount = total_paid

            if total_paid >= outstanding_invoice.total_amount:
                outstanding_invoice.status = Invoice.InvoiceStatus.PAID
            else:
                outstanding_invoice.status = Invoice.InvoiceStatus.PARTIALLY_PAID

            outstanding_invoice.save()

        # Generate success response with payment details
        remaining_balance = outstanding_invoice.total_amount - total_paid

        return render(
            request,
            "web_interface/partials/cashier/payment_success.html",
            {
                "payment": payment,
                "student": student,
                "invoice": outstanding_invoice,
                "remaining_balance": remaining_balance,
                "new_status": outstanding_invoice.get_status_display(),
            },
        )

    except Exception as e:
        return render(
            request,
            "web_interface/partials/cashier/payment_message.html",
            {"message": _("Error processing payment: {}").format(str(e)), "type": "error"},
        )


def cash_drawer_management(request):
    """HTMX endpoint for cash drawer operations"""
    from django.shortcuts import render

    from apps.finance.services import CashierService

    if request.method == "POST":
        action = request.POST.get("action")

        try:
            if action == "open":
                opening_amount = Decimal(request.POST.get("opening_amount", "0"))
                session = CashierService.open_cash_drawer(request.user, opening_amount)

                return render(
                    request,
                    "web_interface/partials/cashier/drawer_message.html",
                    {
                        "message": _("Cash drawer opened with ${}".format(opening_amount)),
                        "type": "success",
                        "session": session,
                    },
                )

            elif action == "close":
                closing_amount = Decimal(request.POST.get("closing_amount", "0"))
                variance = CashierService.close_cash_drawer(request.user, closing_amount)

                message_type = "success" if abs(variance) <= Decimal("0.01") else "warning"
                message = _("Cash drawer closed. Variance: ${}".format(variance))

                return render(
                    request,
                    "web_interface/partials/cashier/drawer_message.html",
                    {"message": message, "type": message_type, "variance": variance},
                )

        except Exception as e:
            return render(
                request,
                "web_interface/partials/cashier/drawer_message.html",
                {"message": _("Error: {}").format(str(e)), "type": "error"},
            )

    # GET request - show cash drawer form
    session = CashierService.get_or_create_session(request.user)
    current_cash = CashierService.get_current_cash_balance(request.user)

    return render(
        request,
        "web_interface/partials/cashier/cash_drawer_form.html",
        {
            "session": session,
            "current_cash": current_cash,
            "denominations": [
                {"value": 100, "label": "$100"},
                {"value": 50, "label": "$50"},
                {"value": 20, "label": "$20"},
                {"value": 10, "label": "$10"},
                {"value": 5, "label": "$5"},
                {"value": 1, "label": "$1"},
            ],
        },
    )


def payment_receipt(request, payment_id):
    """Generate payment receipt"""
    from django.shortcuts import get_object_or_404, render

    payment = get_object_or_404(
        Payment.objects.select_related("invoice__student__person", "processed_by"), id=payment_id
    )

    context = {
        "payment": payment,
        "student": payment.invoice.student,
        "invoice": payment.invoice,
        "institution_name": "Pannasastra University of Cambodia",
        "institution_address": "Siem Reap Campus",
        "print_time": timezone.now(),
    }

    if request.GET.get("format") == "modal":
        return render(request, "web_interface/modals/payment_receipt_modal.html", context)

    return render(request, "web_interface/pages/finance/payment_receipt.html", context)
