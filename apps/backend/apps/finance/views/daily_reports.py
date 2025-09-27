"""Daily financial report views for cashier reconciliation and payment summaries.

Provides comprehensive daily reporting including:
- Cash drawer reconciliation reports
- Daily payment summaries by method
- Daily revenue breakdowns
- Cashier performance metrics
"""

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.utils import timezone
from django.views.generic import TemplateView, View
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from apps.finance.models import CashierSession, Payment
from apps.finance.services import FinancialReportService

logger = logging.getLogger(__name__)


class DailyCashReceiptsView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Daily cash receipts summary report."""

    template_name = "finance/reports/daily_cash_receipts.html"
    permission_required = "finance.view_payment"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        # Get date from request or use today
        report_date_str = self.request.GET.get("date")
        if report_date_str:
            report_date: date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
        else:
            report_date = timezone.now().date()

        # Get all payments for the date
        start_datetime = datetime.combine(report_date, datetime.min.time())
        end_datetime = datetime.combine(report_date, datetime.max.time())
        payments = Payment.objects.filter(
            payment_date__gte=start_datetime,
            payment_date__lte=end_datetime,
            status=Payment.PaymentStatus.COMPLETED,
        ).select_related("invoice__student__person", "processed_by")

        # Calculate totals by payment method
        payment_summary = (
            payments.values("payment_method")
            .annotate(count=Count("id"), total=Sum("amount"))
            .order_by("payment_method")
        )

        # Get cashier sessions for the day
        sessions = CashierSession.objects.filter(date=report_date).select_related("cashier")

        # Calculate overall totals
        total_amount = payments.aggregate(total=Sum("amount", default=Decimal("0.00")))["total"]

        context.update(
            {
                "report_date": report_date,
                "payments": payments,
                "payment_summary": payment_summary,
                "sessions": sessions,
                "total_amount": total_amount,
                "payment_count": payments.count(),
            },
        )

        return context


class DailyCashierReconciliationView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Daily cashier drawer reconciliation report."""

    template_name = "finance/reports/daily_cashier_reconciliation.html"
    permission_required = "finance.view_cashiersession"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        # Get date from request or use today
        report_date_str = self.request.GET.get("date")
        if report_date_str:
            report_date: date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
        else:
            report_date = timezone.now().date()

        # Get all cashier sessions for the date
        sessions = CashierSession.objects.filter(date=report_date).select_related("cashier").order_by("opening_time")

        session_details = []
        total_variance = Decimal("0.00")

        for session in sessions:
            # Get payments for this cashier during their session
            session_payments = Payment.objects.filter(
                processed_by=session.cashier,
                processed_date__gte=session.opening_time,
                processed_date__lte=(session.closing_time if session.closing_time else timezone.now()),
                status=Payment.PaymentStatus.COMPLETED,
            )

            # Calculate cash payments
            cash_payments = session_payments.filter(payment_method=Payment.PaymentMethod.CASH).aggregate(
                total=Sum("amount", default=Decimal("0.00")),
            )["total"]

            # Calculate expected cash
            expected_cash = (session.opening_cash or Decimal("0.00")) + cash_payments

            # Calculate variance
            if session.closing_cash is not None:
                variance = session.closing_cash - expected_cash
            else:
                variance = None

            session_details.append(
                {
                    "session": session,
                    "cash_payments": cash_payments,
                    "expected_cash": expected_cash,
                    "variance": variance,
                    "payment_count": session_payments.count(),
                },
            )

            if variance is not None:
                total_variance += variance

        context.update(
            {
                "report_date": report_date,
                "session_details": session_details,
                "total_variance": total_variance,
            },
        )

        return context


class DailyPaymentSummaryView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Daily payment summary by type and category."""

    template_name = "finance/reports/daily_payment_summary.html"
    permission_required = "finance.view_payment"

    def get_context_data(self, **kwargs) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)

        # Get date from request or use today
        report_date_str = self.request.GET.get("date")
        if report_date_str:
            report_date: date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
        else:
            report_date = timezone.now().date()

        # Initialize report service
        FinancialReportService()

        # Get payment breakdown by method
        start_datetime = datetime.combine(report_date, datetime.min.time())
        end_datetime = datetime.combine(report_date, datetime.max.time())
        payment_by_method = (
            Payment.objects.filter(
                payment_date__gte=start_datetime,
                payment_date__lte=end_datetime,
                status=Payment.PaymentStatus.COMPLETED,
            )
            .values("payment_method")
            .annotate(count=Count("id"), total=Sum("amount"))
            .order_by("-total")
        )

        # Get payment breakdown by fee type
        payment_by_type = (
            Payment.objects.filter(
                payment_date__gte=start_datetime,
                payment_date__lte=end_datetime,
                status=Payment.PaymentStatus.COMPLETED,
            )
            .values("invoice__invoice_type")
            .annotate(count=Count("id"), total=Sum("amount"))
            .order_by("-total")
        )

        # Get hourly payment distribution
        hourly_payments = []
        for hour in range(8, 18):  # 8 AM to 6 PM
            hour_start = timezone.make_aware(datetime.combine(report_date, datetime.min.time().replace(hour=hour)))
            hour_end = hour_start + timedelta(hours=1)

            hour_payments = Payment.objects.filter(
                processed_date__gte=hour_start,
                processed_date__lt=hour_end,
                status=Payment.PaymentStatus.COMPLETED,
            ).aggregate(count=Count("id"), total=Sum("amount", default=Decimal("0.00")))

            hourly_payments.append(
                {
                    "hour": f"{hour:02d}:00",
                    "count": hour_payments["count"],
                    "total": hour_payments["total"],
                },
            )

        # Get cashier performance
        cashier_performance = (
            Payment.objects.filter(
                payment_date__gte=start_datetime,
                payment_date__lte=end_datetime,
                status=Payment.PaymentStatus.COMPLETED,
            )
            .values("processed_by__first_name", "processed_by__last_name")
            .annotate(count=Count("id"), total=Sum("amount"))
            .order_by("-total")
        )

        # Calculate totals
        total_stats = Payment.objects.filter(
            payment_date__gte=start_datetime,
            payment_date__lte=end_datetime,
            status=Payment.PaymentStatus.COMPLETED,
        ).aggregate(total_amount=Sum("amount", default=Decimal("0.00")), total_count=Count("id"))

        context.update(
            {
                "report_date": report_date,
                "payment_by_method": payment_by_method,
                "payment_by_type": payment_by_type,
                "hourly_payments": hourly_payments,
                "cashier_performance": cashier_performance,
                "total_amount": total_stats["total_amount"],
                "total_count": total_stats["total_count"],
                "average_payment": (
                    total_stats["total_amount"] / total_stats["total_count"]
                    if total_stats["total_count"] > 0
                    else Decimal("0.00")
                ),
            },
        )

        return context


class DailyCashReceiptsPDFView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Generate PDF version of daily cash receipts report."""

    permission_required = "finance.view_payment"

    def get(self, request, *args, **kwargs):
        # Get date from request or use today
        report_date = request.GET.get("date")
        if report_date:
            report_date = datetime.strptime(report_date, "%Y-%m-%d").date()
        else:
            report_date = timezone.now().date()

        # Create PDF response
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="daily_cash_receipts_{report_date}.pdf"'

        # Create PDF document
        doc = SimpleDocTemplate(response, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        # Title
        title = Paragraph(
            f"Daily Cash Receipts Report - {report_date.strftime('%B %d, %Y')}",
            styles["Title"],
        )
        story.append(title)
        story.append(Spacer(1, 0.5 * inch))

        # Get payment data
        payments = (
            Payment.objects.filter(payment_date=report_date, status=Payment.PaymentStatus.COMPLETED)
            .select_related("invoice__student__person")
            .order_by("processed_date")
        )

        # Summary table
        summary_data = [["Payment Method", "Count", "Total Amount"]]
        payment_summary = (
            payments.values("payment_method")
            .annotate(count=Count("id"), total=Sum("amount"))
            .order_by("payment_method")
        )

        total_count = 0
        total_amount = Decimal("0.00")

        for item in payment_summary:
            method_display = dict(Payment.PaymentMethod.choices).get(item["payment_method"], item["payment_method"])
            summary_data.append([method_display, str(item["count"]), f"${item['total']:,.2f}"])
            total_count += item["count"]
            total_amount += item["total"]

        summary_data.append(["TOTAL", str(total_count), f"${total_amount:,.2f}"])

        summary_table = Table(summary_data, colWidths=[2 * inch, 1 * inch, 1.5 * inch])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 14),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.lightgrey),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                ],
            ),
        )

        story.append(summary_table)
        story.append(Spacer(1, 0.5 * inch))

        # Detail table
        story.append(Paragraph("Payment Details", styles["Heading2"]))
        story.append(Spacer(1, 0.25 * inch))

        detail_data = [["Time", "Student", "Amount", "Method", "Reference"]]

        for payment in payments:
            detail_data.append(
                [
                    payment.processed_date.strftime("%I:%M %p"),
                    payment.invoice.student.person.full_name[:30],
                    f"${payment.amount:,.2f}",
                    payment.get_payment_method_display()[:10],
                    payment.reference_number or "",
                ],
            )

        detail_table = Table(detail_data, colWidths=[1 * inch, 2 * inch, 1 * inch, 1 * inch, 1.5 * inch])
        detail_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 12),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                    ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                ],
            ),
        )

        story.append(detail_table)

        # Build PDF
        doc.build(story)

        return response
