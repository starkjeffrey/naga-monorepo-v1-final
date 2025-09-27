"""Financial reports dashboard views for the web interface."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import models
from django.db.models import Avg, Case, Count, F, Sum, When
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView

from apps.common.models import ActivityLog, Notification
from apps.finance.models import Invoice, Payment


class ReportsDashboardView(LoginRequiredMixin, TemplateView):
    """Main financial reports dashboard with key metrics and charts."""

    template_name = "web_interface/pages/finance/reports_dashboard.html"

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        """Add reports dashboard context data."""
        context = super().get_context_data(**kwargs)

        # Get date range from query params
        date_range = self.request.GET.get("range", "30")
        try:
            days = int(date_range)
        except (ValueError, TypeError):
            days = 30

        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)

        # Get financial metrics
        revenue_data = self.get_revenue_metrics(start_date, end_date)
        daily_revenue = self.get_daily_revenue(start_date, end_date)
        outstanding_data = self.get_outstanding_metrics()
        payment_methods = self.get_payment_methods_data(start_date, end_date)

        context.update(
            {
                "revenue_data": revenue_data,
                "daily_revenue": json.dumps(daily_revenue),
                "outstanding_data": outstanding_data,
                "payment_methods": json.dumps(payment_methods),
                "date_range": date_range,
                "start_date": start_date,
                "end_date": end_date,
                "page_title": _("Financial Reports Dashboard"),
            }
        )

        return context

    def get_revenue_metrics(self, start_date, end_date) -> dict[str, Any]:
        """Get revenue metrics for the date range."""
        payments = Payment.objects.filter(
            payment_date__range=[start_date, end_date], status=Payment.PaymentStatus.COMPLETED
        )

        metrics = payments.aggregate(total=Sum("amount"), count=Count("id"), average=Avg("amount"))

        # Calculate growth compared to previous period
        previous_start = start_date - (end_date - start_date)
        previous_payments = Payment.objects.filter(
            payment_date__range=[previous_start, start_date], status=Payment.PaymentStatus.COMPLETED
        )

        previous_total = previous_payments.aggregate(total=Sum("amount"))["total"] or 0

        current_total = metrics["total"] or 0

        if previous_total > 0:
            growth_rate = ((current_total - previous_total) / previous_total) * 100
        else:
            growth_rate = 100 if current_total > 0 else 0

        return {
            "total": current_total,
            "count": metrics["count"] or 0,
            "average": metrics["average"] or 0,
            "growth_rate": round(growth_rate, 1),
        }

    def get_daily_revenue(self, start_date, end_date) -> list[dict[str, Any]]:
        """Get daily revenue data for chart."""
        daily_data = (
            Payment.objects.filter(payment_date__range=[start_date, end_date], status=Payment.PaymentStatus.COMPLETED)
            .extra({"payment_day": "DATE(payment_date)"})
            .values("payment_day")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("payment_day")
        )

        return [
            {
                "date": item["payment_day"].strftime("%Y-%m-%d"),
                "total": float(item["total"] or 0),
                "count": item["count"],
            }
            for item in daily_data
        ]

    def get_outstanding_metrics(self) -> dict[str, Any]:
        """Get outstanding balances metrics."""
        outstanding_invoices = Invoice.objects.filter(
            status__in=[Invoice.InvoiceStatus.SENT, Invoice.InvoiceStatus.OVERDUE]
        )

        metrics = outstanding_invoices.aggregate(
            total=Sum(
                Case(
                    When(total_amount__gt=F("paid_amount"), then=F("total_amount") - F("paid_amount")),
                    default=0,
                    output_field=models.DecimalField(),
                )
            ),
            count=Count("id"),
        )

        # Get overdue count
        overdue_count = outstanding_invoices.filter(status=Invoice.InvoiceStatus.OVERDUE).count()

        return {
            "total": metrics["total"] or 0,
            "count": metrics["count"] or 0,
            "overdue_count": overdue_count,
        }

    def get_payment_methods_data(self, start_date, end_date) -> list[dict[str, Any]]:
        """Get payment methods breakdown for chart."""
        payment_methods = (
            Payment.objects.filter(payment_date__range=[start_date, end_date], status=Payment.PaymentStatus.COMPLETED)
            .values("payment_method")
            .annotate(total=Sum("amount"), count=Count("id"))
            .order_by("-total")
        )

        return [
            {
                "method": item["payment_method"],
                "total": float(item["total"] or 0),
                "count": item["count"],
                "label": dict(Payment.PaymentMethod.choices).get(item["payment_method"], item["payment_method"]),
            }
            for item in payment_methods
        ]


@login_required
@require_http_methods(["GET"])
def reports_dashboard_data(request: HttpRequest) -> HttpResponse:
    """HTMX endpoint to reload dashboard data with new date range."""
    request.GET.get("range", "30")

    # Create a temporary view instance to reuse the logic
    view = ReportsDashboardView()
    view.request = request

    context = view.get_context_data()

    return render(request, "web_interface/partials/reports/dashboard_content.html", context)


@login_required
@require_http_methods(["GET"])
def daily_cash_report(request: HttpRequest) -> HttpResponse:
    """Generate daily cash report."""
    report_date = request.GET.get("date", timezone.now().date())

    if isinstance(report_date, str):
        try:
            report_date = datetime.strptime(report_date, "%Y-%m-%d").date()
        except ValueError:
            report_date = timezone.now().date()

    # Get cash payments for the day
    cash_payments = (
        Payment.objects.filter(
            payment_date__date=report_date,
            payment_method=Payment.PaymentMethod.CASH,
            status=Payment.PaymentStatus.COMPLETED,
        )
        .select_related("invoice", "processed_by")
        .order_by("payment_date")
    )

    # Calculate totals
    total_cash = cash_payments.aggregate(total=Sum("amount"))["total"] or 0

    # Get cashier breakdown
    cashier_breakdown = (
        cash_payments.values("processed_by__first_name", "processed_by__last_name")
        .annotate(total=Sum("amount"), count=Count("id"))
        .order_by("-total")
    )

    context = {
        "report_date": report_date,
        "cash_payments": cash_payments,
        "total_cash": total_cash,
        "cashier_breakdown": cashier_breakdown,
        "payment_count": cash_payments.count(),
    }

    return render(request, "web_interface/pages/finance/daily_cash_report.html", context)


@login_required
@require_http_methods(["GET"])
def student_balances_report(request: HttpRequest) -> HttpResponse:
    """Generate student outstanding balances report."""
    # Get all students with outstanding balances
    outstanding_invoices = (
        Invoice.objects.filter(
            total_amount__gt=F("paid_amount"), status__in=[Invoice.InvoiceStatus.SENT, Invoice.InvoiceStatus.OVERDUE]
        )
        .select_related("student")
        .annotate(amount_due=F("total_amount") - F("paid_amount"))
        .order_by("-amount_due")
    )

    # Group by student
    student_balances = {}
    for invoice in outstanding_invoices:
        student_id = invoice.student.id
        if student_id not in student_balances:
            student_balances[student_id] = {
                "student": invoice.student,
                "total_due": 0,
                "invoice_count": 0,
                "overdue_count": 0,
                "invoices": [],
            }

        student_balances[student_id]["total_due"] += invoice.amount_due
        student_balances[student_id]["invoice_count"] += 1
        if invoice.status == Invoice.InvoiceStatus.OVERDUE:
            student_balances[student_id]["overdue_count"] += 1
        student_balances[student_id]["invoices"].append(invoice)

    # Convert to list and sort by total due
    balances_list = sorted(student_balances.values(), key=lambda x: float(str(x["total_due"] or 0)), reverse=True)

    # Calculate summary
    total_outstanding = sum(balance["total_due"] for balance in balances_list)
    total_students = len(balances_list)
    students_with_overdue = len([b for b in balances_list if b["overdue_count"] > 0])

    context = {
        "student_balances": balances_list,
        "total_outstanding": total_outstanding,
        "total_students": total_students,
        "students_with_overdue": students_with_overdue,
    }

    return render(request, "web_interface/pages/finance/student_balances_report.html", context)


@login_required
@require_http_methods(["GET"])
def enhanced_student_analytics(request: HttpRequest) -> HttpResponse:
    """Enhanced student analytics report with AI insights."""
    from apps.people.models import StudentProfile
    from apps.enrollment.models import ProgramEnrollment, ClassHeaderEnrollment

    # Get actual data from your database
    context = {
        'page_title': 'Enhanced Student Analytics Report',
        'total_students': StudentProfile.objects.count(),
        'active_students': StudentProfile.objects.filter(status='ACTIVE').count(),
        'students_by_status': list(StudentProfile.objects.values('status').annotate(count=models.Count('id'))),
        'students_by_gender': list(StudentProfile.objects.values('person__gender').annotate(count=models.Count('id'))),
        'program_enrollments': ProgramEnrollment.objects.select_related('program', 'student__person').filter(status='ACTIVE')[:20],
        'recent_enrollments': ClassHeaderEnrollment.objects.select_related('student__person', 'class_header__course').order_by('-enrollment_date')[:15],
        'enrollment_trends': ClassHeaderEnrollment.objects.extra({'date': "DATE(enrollment_date)"}).values('date').annotate(count=models.Count('id')).order_by('-date')[:30],
    }

    return render(request, "web_interface/pages/reports/student_analytics.html", context)


@login_required
@require_http_methods(["GET"])
def export_report(request: HttpRequest, report_type: str) -> HttpResponse:
    """Export reports to PDF or Excel."""
    # Future enhancement: Implement report export functionality
    # This would use libraries like ReportLab for PDF or openpyxl for Excel

    return JsonResponse({"success": False, "message": "Report export functionality coming soon"})


@login_required
@require_http_methods(["GET"])
def get_activity_feed(request: HttpRequest) -> HttpResponse:
    """Get recent system activity for notifications."""
    activities = ActivityLog.objects.select_related("user", "content_type").order_by("-created_at")[:20]

    context = {"activities": activities}

    return render(request, "web_interface/partials/notifications/activity_feed.html", context)


@login_required
@require_http_methods(["GET"])
def get_user_notifications(request: HttpRequest) -> HttpResponse:
    """Get user notifications for the notification panel."""
    notifications = Notification.objects.filter(user=request.user, is_read=False).order_by("-created_at")[:10]

    context = {"notifications": notifications}

    return render(request, "web_interface/partials/notifications/user_notifications.html", context)


@login_required
@require_http_methods(["POST"])
def mark_notification_read(request: HttpRequest, notification_id: int) -> JsonResponse:
    """Mark a notification as read."""
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.mark_as_read()

        return JsonResponse({"success": True, "message": _("Notification marked as read")})
    except Notification.DoesNotExist:
        return JsonResponse({"success": False, "error": _("Notification not found")}, status=404)


@login_required
@require_http_methods(["POST"])
def mark_all_notifications_read(request: HttpRequest) -> JsonResponse:
    """Mark all user notifications as read."""
    updated_count = Notification.objects.filter(user=request.user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )

    return JsonResponse(
        {"success": True, "message": _("All notifications marked as read"), "updated_count": updated_count}
    )
