"""Finance staff dashboard and management views.

Provides comprehensive financial management interfaces including:
- Executive dashboard with key metrics
- Revenue tracking and analysis
- Outstanding balance management
- Fee and pricing management
- Scholarship oversight
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import (
    Avg,
    Case,
    Count,
    F,
    IntegerField,
    Q,
    Sum,
    When,
)
from django.urls import reverse
from django.utils import timezone
from django.views.generic import TemplateView

from apps.curriculum.models import Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.finance.models import (
    CourseFixedPricing,
    DefaultPricing,
    FeePricing,
    FinancialTransaction,
    Invoice,
    Payment,
)
from apps.finance.services import FinancialReportService
from apps.people.models import StudentProfile

# from apps.scholarships.models import ScholarshipAward, SponsorPayment  # Models not available yet

logger = logging.getLogger(__name__)


class FinanceDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Main finance dashboard with key metrics and visualizations."""

    template_name = "finance/staff/dashboard.html"
    permission_required = "finance.view_financialtransaction"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        # Get current term - get_current_term() method doesn't exist, so we'll get the latest active term
        try:
            current_term = Term.objects.filter(is_active=True).order_by("-start_date").first()
        except Exception:
            current_term = None
        current_year = None  # AcademicYear not available in this architecture

        # Date ranges
        today = timezone.now().date()
        month_start = today.replace(day=1)
        week_start = today - timedelta(days=today.weekday())

        # Key metrics
        context.update(
            {
                "current_term": current_term,
                "current_year": current_year,
                "today": today,
                # Revenue metrics
                "today_revenue": self._get_revenue_for_period(today, today),
                "week_revenue": self._get_revenue_for_period(week_start, today),
                "month_revenue": self._get_revenue_for_period(month_start, today),
                "term_revenue": self._get_term_revenue(current_term),
                # Outstanding balances
                "total_outstanding": self._get_total_outstanding(),
                "overdue_amount": self._get_overdue_amount(),
                "students_with_balance": self._get_students_with_balance_count(),
                # Payment statistics
                "payment_method_breakdown": self._get_payment_method_breakdown(month_start, today),
                "daily_revenue_trend": self._get_daily_revenue_trend(),
                # Student enrollment vs payment
                "enrollment_payment_stats": self._get_enrollment_payment_stats(current_term),
                # Scholarship statistics
                "scholarship_stats": self._get_scholarship_stats(current_term),
                # Recent activity
                "recent_payments": self._get_recent_payments(10),
                "recent_invoices": self._get_recent_invoices(10),
            },
        )

        return context

    def _get_revenue_for_period(self, start_date: date, end_date: date) -> Decimal:
        """Calculate total revenue for a given period."""
        return Payment.objects.filter(
            payment_date__gte=start_date,
            payment_date__lte=end_date,
            status=Payment.PaymentStatus.COMPLETED,
        ).aggregate(total=Sum("amount", default=Decimal("0.00")))["total"]

    def _get_term_revenue(self, term: Term) -> dict[str, Decimal]:
        """Get revenue breakdown for the current term."""
        if not term:
            return {
                "tuition": Decimal("0.00"),
                "fees": Decimal("0.00"),
                "total": Decimal("0.00"),
            }

        # Get invoices for this term
        term_invoices = Invoice.objects.filter(term=term)

        # Calculate tuition revenue (from paid invoices)
        tuition_revenue = term_invoices.filter(
            status__in=[
                Invoice.InvoiceStatus.PAID,
                Invoice.InvoiceStatus.PARTIALLY_PAID,
            ],
        ).aggregate(total=Sum("paid_amount", default=Decimal("0.00")))["total"]

        # Calculate fee revenue
        fee_revenue = FinancialTransaction.objects.filter(
            transaction_date__gte=term.start_date,
            transaction_date__lte=term.end_date,
            transaction_type=FinancialTransaction.TransactionType.PAYMENT_RECEIVED,
        ).aggregate(total=Sum("amount", default=Decimal("0.00")))["total"]

        return {
            "tuition": tuition_revenue,
            "fees": fee_revenue,
            "total": tuition_revenue + fee_revenue,
        }

    def _get_total_outstanding(self) -> Decimal:
        """Calculate total outstanding balance across all students."""
        return Invoice.objects.filter(
            status__in=[
                Invoice.InvoiceStatus.SENT,
                Invoice.InvoiceStatus.PARTIALLY_PAID,
            ],
        ).aggregate(total=Sum(F("total_amount") - F("paid_amount"), default=Decimal("0.00")))["total"]

    def _get_overdue_amount(self) -> Decimal:
        """Calculate total overdue amount."""
        return Invoice.objects.filter(status=Invoice.InvoiceStatus.OVERDUE).aggregate(
            total=Sum(F("total_amount") - F("paid_amount"), default=Decimal("0.00")),
        )["total"]

    def _get_students_with_balance_count(self) -> int:
        """Count students with outstanding balances."""
        return (
            StudentProfile.objects.filter(
                invoices__status__in=[
                    Invoice.InvoiceStatus.SENT,
                    Invoice.InvoiceStatus.PARTIALLY_PAID,
                    Invoice.InvoiceStatus.OVERDUE,
                ],
            )
            .distinct()
            .count()
        )

    def _get_payment_method_breakdown(self, start_date: date, end_date: date) -> list[dict]:
        """Get payment breakdown by method for the period."""
        breakdown = (
            Payment.objects.filter(
                payment_date__gte=start_date,
                payment_date__lte=end_date,
                status=Payment.PaymentStatus.COMPLETED,
            )
            .values("payment_method")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")
        )

        # Add display names
        for item in breakdown:
            item["display_name"] = dict(Payment.PaymentMethod.choices).get(
                item["payment_method"],
                item["payment_method"],
            )

        return list(breakdown)

    def _get_daily_revenue_trend(self, days: int = 30) -> list[dict]:
        """Get daily revenue trend for the last N days."""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days - 1)

        # Get daily totals
        daily_totals = (
            Payment.objects.filter(
                payment_date__gte=start_date,
                payment_date__lte=end_date,
                status=Payment.PaymentStatus.COMPLETED,
            )
            .values("payment_date")
            .annotate(total=Sum("amount"))
            .order_by("payment_date")
        )

        # Create complete date range
        date_range = []
        current_date = start_date
        totals_dict = {item["payment_date"]: item["total"] for item in daily_totals}

        while current_date <= end_date:
            date_range.append(
                {
                    "date": current_date.isoformat(),
                    "total": float(totals_dict.get(current_date, Decimal("0.00"))),
                },
            )
            current_date += timedelta(days=1)

        return date_range

    def _get_enrollment_payment_stats(self, term: Term) -> dict:
        """Get enrollment vs payment statistics for the term."""
        if not term:
            return {
                "total_enrolled": 0,
                "fully_paid": 0,
                "partially_paid": 0,
                "unpaid": 0,
                "payment_rate": 0,
            }

        # Get enrollment counts
        enrolled_students = (
            ClassHeaderEnrollment.objects.filter(
                class_header__term=term,
                status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            )
            .values("student")
            .distinct()
            .count()
        )

        # Get payment status counts
        student_payment_status = (
            StudentProfile.objects.filter(
                class_header_enrollments__class_header__term=term,
                class_header_enrollments__status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            )
            .annotate(
                has_invoice=Count("invoices", filter=Q(invoices__term=term)),
                invoice_status=Case(
                    When(
                        invoices__term=term,
                        invoices__status=Invoice.InvoiceStatus.PAID,
                        then=1,
                    ),
                    When(
                        invoices__term=term,
                        invoices__status=Invoice.InvoiceStatus.PARTIALLY_PAID,
                        then=2,
                    ),
                    default=3,
                    output_field=IntegerField(),
                ),
            )
            .values("invoice_status")
            .annotate(count=Count("id", distinct=True))
        )

        status_counts = {1: 0, 2: 0, 3: 0}
        for item in student_payment_status:
            status_counts[item["invoice_status"]] = item["count"]

        fully_paid = status_counts[1]
        partially_paid = status_counts[2]
        unpaid = enrolled_students - fully_paid - partially_paid

        return {
            "total_enrolled": enrolled_students,
            "fully_paid": fully_paid,
            "partially_paid": partially_paid,
            "unpaid": unpaid,
            "payment_rate": ((fully_paid / enrolled_students * 100) if enrolled_students > 0 else 0),
        }

    def _get_scholarship_stats(self, term: Term) -> dict:
        """Get scholarship statistics for the term."""
        # Scholarship models not yet available
        return {
            "total_awards": 0,
            "total_amount": Decimal("0.00"),
            "students_count": 0,
            "sponsor_payments": Decimal("0.00"),
        }

    def _get_recent_payments(self, limit: int) -> list[Payment]:
        """Get recent payments."""
        qs = Payment.objects.select_related("invoice__student__person").order_by("-processed_date")[:limit]
        return list(qs)

    def _get_recent_invoices(self, limit: int) -> list[Invoice]:
        """Get recently created invoices."""
        qs = Invoice.objects.select_related("student__person", "term").order_by("-created_at")[:limit]
        return list(qs)


class RevenueAnalysisView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Detailed revenue analysis and tracking."""

    template_name = "finance/staff/revenue_analysis.html"
    permission_required = "finance.view_financialtransaction"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        # Get date range from request
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=30)

        if self.request.GET.get("start_date"):
            start_date = datetime.strptime(self.request.GET["start_date"], "%Y-%m-%d").date()
        if self.request.GET.get("end_date"):
            end_date = datetime.strptime(self.request.GET["end_date"], "%Y-%m-%d").date()

        # Get revenue data
        # Use Any to avoid leaking private service internals into typing
        service: Any = FinancialReportService()

        context.update(
            {
                "start_date": start_date,
                "end_date": end_date,
                "revenue_by_type": service.get_revenue_by_type(start_date, end_date),
                "revenue_by_program": service.get_revenue_by_program(start_date, end_date),
                "revenue_by_payment_method": service.get_revenue_by_payment_method(start_date, end_date),
                "daily_revenue": service.get_daily_revenue(start_date, end_date),
                "top_revenue_courses": service.get_top_revenue_courses(start_date, end_date),
            },
        )

        return context


class OutstandingBalancesView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """View and manage outstanding student balances."""

    template_name = "finance/staff/outstanding_balances.html"
    permission_required = "finance.view_invoice"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        # Get filter parameters
        min_balance = Decimal(self.request.GET.get("min_balance", "0"))
        status_filter = self.request.GET.get("status", "all")
        program_filter = self.request.GET.get("program", "")

        # Base queryset
        students = (
            StudentProfile.objects.annotate(
                total_balance=Sum(
                    "invoices__total_amount",
                    filter=Q(
                        invoices__status__in=[
                            Invoice.InvoiceStatus.SENT,
                            Invoice.InvoiceStatus.PARTIALLY_PAID,
                            Invoice.InvoiceStatus.OVERDUE,
                        ],
                    ),
                )
                - Sum(
                    "invoices__paid_amount",
                    filter=Q(
                        invoices__status__in=[
                            Invoice.InvoiceStatus.SENT,
                            Invoice.InvoiceStatus.PARTIALLY_PAID,
                            Invoice.InvoiceStatus.OVERDUE,
                        ],
                    ),
                ),
            )
            .filter(total_balance__gt=min_balance)
            .select_related("person")
        )

        # Apply filters
        if status_filter == "overdue":
            students = students.filter(invoices__status=Invoice.InvoiceStatus.OVERDUE).distinct()

        if program_filter:
            students = students.filter(
                class_header_enrollments__class_header__course__program__id=program_filter,
            ).distinct()

        # Order by balance
        students = students.order_by("-total_balance")

        # Calculate totals
        totals = students.aggregate(
            total_outstanding=Sum("total_balance", default=Decimal("0.00")),
            student_count=Count("id"),
        )

        context.update(
            {
                "students": students[:100],  # Limit to top 100
                "total_outstanding": totals["total_outstanding"],
                "student_count": totals["student_count"],
                "filters": {
                    "min_balance": min_balance,
                    "status": status_filter,
                    "program": program_filter,
                },
            },
        )

        return context


class FeeManagementView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Manage fees and pricing tiers."""

    template_name = "finance/staff/fee_management.html"
    permission_required = "finance.view_feepricing"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        # Get current default pricing
        default_pricing = DefaultPricing.objects.filter(end_date__isnull=True).order_by("cycle__name")

        # Get fee pricing
        fee_pricing = FeePricing.objects.order_by("fee_type", "name")

        # Get course pricing summary
        course_pricing_summary = (
            CourseFixedPricing.objects.filter(end_date__isnull=True)
            .values("course__cycle__name")
            .annotate(
                course_count=Count("course"),
                avg_domestic_price=Avg("domestic_price"),
                avg_foreign_price=Avg("foreign_price"),
            )
        )

        context.update(
            {
                "default_pricing": default_pricing,
                "fee_pricing": fee_pricing,
                "course_pricing_summary": course_pricing_summary,
            },
        )

        return context


class ScholarshipOverviewView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Overview of scholarships and sponsor payments."""

    template_name = "finance/staff/scholarship_overview.html"
    permission_required = "finance.view_payment"  # Changed permission since scholarships app not available

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        try:
            current_term = Term.objects.filter(is_active=True).order_by("-start_date").first()
        except Exception:
            current_term = None

        # Scholarship functionality not yet available
        context.update(
            {
                "current_term": current_term,
                "active_awards": [],
                "stats": {
                    "total_awards": 0,
                    "total_amount": Decimal("0.00"),
                    "students_count": 0,
                    "sponsors_count": 0,
                },
                "recent_payments": [],
                "sponsor_balances": [],
            },
        )

        return context


class FinancialReportsHubView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Central hub for accessing all financial reports."""

    template_name = "finance/staff/reports_hub.html"
    permission_required = "finance.view_financialtransaction"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        # Available reports grouped by category
        context["report_categories"] = [
            {
                "name": "Daily Reports",
                "icon": "calendar-day",
                "reports": [
                    {
                        "name": "Daily Cash Receipts",
                        "description": "Cash receipts summary for a specific day",
                        "url": reverse("finance:daily-cash-receipts"),
                        "params": ["date"],
                    },
                    {
                        "name": "Daily Cashier Reconciliation",
                        "description": "Cashier drawer reconciliation report",
                        "url": reverse("finance:daily-cashier-reconciliation"),
                        "params": ["date"],
                    },
                    {
                        "name": "Daily Payment Summary",
                        "description": "Summary of all payments by method",
                        "url": reverse("finance:daily-payment-summary"),
                        "params": ["date"],
                    },
                ],
            },
            {
                "name": "Weekly Reports",
                "icon": "calendar-week",
                "reports": [
                    {
                        "name": "Weekly Revenue Analysis",
                        "description": "Revenue trends and analysis for the week",
                        "url": reverse("finance:weekly-revenue-analysis"),
                        "params": ["week_start"],
                    },
                    {
                        "name": "Weekly Payment Trends",
                        "description": "Payment patterns and trends",
                        "url": reverse("finance:weekly-payment-trends"),
                        "params": ["week_start"],
                    },
                    {
                        "name": "Weekly Outstanding Balances",
                        "description": "Changes in outstanding balances",
                        "url": reverse("finance:weekly-outstanding-balances"),
                        "params": ["week_start"],
                    },
                ],
            },
            {
                "name": "Monthly Reports",
                "icon": "calendar-month",
                "reports": [
                    {
                        "name": "Monthly Financial Statement",
                        "description": "Comprehensive financial statement",
                        "url": reverse("finance:monthly-financial-statement"),
                        "params": ["year", "month"],
                    },
                    {
                        "name": "Monthly Revenue Report",
                        "description": "Detailed revenue breakdown",
                        "url": reverse("finance:monthly-revenue-report"),
                        "params": ["year", "month"],
                    },
                    {
                        "name": "Monthly Aging Report",
                        "description": "Accounts receivable aging analysis",
                        "url": reverse("finance:monthly-aging-report"),
                        "params": ["year", "month"],
                    },
                    {
                        "name": "QuickBooks Export",
                        "description": "Export data for QuickBooks import",
                        "url": reverse("finance:quickbooks_reports"),
                        "params": ["year", "month"],
                    },
                ],
            },
            {
                "name": "Term Reports",
                "icon": "graduation-cap",
                "reports": [
                    {
                        "name": "Term Revenue Summary",
                        "description": "Revenue summary for an academic term",
                        "url": reverse("finance:term-revenue-summary"),
                        "params": ["term_id"],
                    },
                    {
                        "name": "Term Enrollment vs Payment",
                        "description": "Compare enrollment to payment status",
                        "url": reverse("finance:term-enrollment-payment"),
                        "params": ["term_id"],
                    },
                    {
                        "name": "Term Scholarship Report",
                        "description": "Scholarship utilization for the term",
                        "url": reverse("finance:term-scholarship-report"),
                        "params": ["term_id"],
                    },
                ],
            },
        ]

        # Recent report generation history (if implemented)
        context["recent_reports"] = []

        return context
