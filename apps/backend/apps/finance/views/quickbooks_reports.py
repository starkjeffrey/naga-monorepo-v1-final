"""Views for generating QuickBooks reports through the web interface.

Provides a simple interface for accounting staff to generate monthly
financial reports that can be copied into QuickBooks.
"""

import logging
from datetime import timedelta

from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from apps.finance.services import QuickBooksReportService

# Constants for month names
MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}

logger = logging.getLogger(__name__)


class QuickBooksReportView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """Main view for QuickBooks report generation.

    Provides a simple form to select month and report type.
    """

    template_name = "finance/quickbooks_reports.html"
    permission_required = "finance.view_financialtransaction"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get available months (last 12 months)
        today = timezone.now().date()
        months = []

        for i in range(12):
            date = today.replace(day=1) - timedelta(days=i * 30)
            months.append(
                {
                    "value": f"{date.year}-{date.month:02d}",
                    "display": date.strftime("%B %Y"),
                    "year": date.year,
                    "month": date.month,
                },
            )

        context["available_months"] = months
        context["current_month"] = months[1]["value"]  # Default to previous month

        return context


class GenerateQuickBooksReportView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Generate and download QuickBooks reports.

    Handles the actual report generation based on form submission.
    """

    permission_required = "finance.view_financialtransaction"

    def post(self, request, *args, **kwargs):
        """Generate report based on form data."""
        # Parse form data
        period = request.POST.get("period", "")
        report_type = request.POST.get("report_type", "summary")
        format_type = request.POST.get("format", "readable")

        try:
            # Parse year and month
            year, month = period.split("-")
            year = int(year)
            month = int(month)

            service = QuickBooksReportService()
            if report_type == "journal":
                content = service.generate_quickbooks_journal_entry(year, month)
                filename = f"quickbooks_journal_{year}_{month:02d}.txt"

            elif report_type == "deposits":
                content = service.generate_daily_deposits_report(year, month, format=format_type)
                ext = "csv" if format_type == "csv" else "txt"
                filename = f"daily_deposits_{year}_{month:02d}.{ext}"

            else:  # summary
                content = service.generate_monthly_cash_receipts_summary(year, month, format=format_type)
                ext = "csv" if format_type == "csv" else "txt"
                filename = f"cash_receipts_{year}_{month:02d}.{ext}"

            # Return as downloadable file
            response = HttpResponse(
                content,
                content_type="text/csv" if format_type == "csv" else "text/plain",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}"'
        except (ValueError, TypeError, AttributeError) as e:
            logger.exception("Error generating QuickBooks report")
            return render(request, "finance/quickbooks_reports_error.html", {"error": str(e)})
        else:
            return response


class QuickBooksReportPreviewView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Preview QuickBooks reports in the browser.

    Shows the report content without downloading.
    """

    permission_required = "finance.view_financialtransaction"

    def post(self, request, *args, **kwargs):
        """Generate and display report preview."""
        # Parse form data
        period = request.POST.get("period", "")
        report_type = request.POST.get("report_type", "summary")

        try:
            # Parse year and month
            year, month = period.split("-")
            year = int(year)
            month = int(month)

            service = QuickBooksReportService()
            if report_type == "journal":
                content = service.generate_quickbooks_journal_entry(year, month)
                title = f"QuickBooks Journal Entry - {MONTH_NAMES[month]} {year}"

            elif report_type == "deposits":
                content = service.generate_daily_deposits_report(year, month)
                title = f"Daily Deposits Report - {MONTH_NAMES[month]} {year}"

            else:  # summary
                content = service.generate_monthly_cash_receipts_summary(year, month)
                title = f"Cash Receipts Summary - {MONTH_NAMES[month]} {year}"

            context = {
                "title": title,
                "content": content,
                "year": year,
                "month": month,
                "report_type": report_type,
            }

            return render(request, "finance/quickbooks_report_preview.html", context)

        except Exception as e:
            logger.exception("Error previewing QuickBooks report")
            return render(request, "finance/quickbooks_reports_error.html", {"error": str(e)})
