"""Financial report service for generating various financial reports.

Handles generation of daily, weekly, and monthly financial reports
for management and operational purposes.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any

from django.db.models import Count, Q, Sum

from apps.common.utils import get_current_date
from apps.finance.models import (
    FinancialTransaction,
    Invoice,
    Payment,
)


class FinancialReportService:
    """Service for generating financial reports and analysis.

    Provides comprehensive reporting capabilities for:
    - Daily transaction summaries
    - Weekly revenue analysis
    - Monthly financial statements
    - Custom period reporting
    """

    @staticmethod
    def get_daily_transaction_summary(
        report_date: date | None = None,
    ) -> dict[str, Any]:
        """Get daily transaction summary for a specific date.

        Args:
            report_date: Date to generate report for (defaults to today)

        Returns:
            Dictionary with daily transaction summary
        """
        if report_date is None:
            report_date = get_current_date()

        # Get all payments for the date
        start_datetime = datetime.combine(report_date, datetime.min.time())
        end_datetime = datetime.combine(report_date, datetime.max.time())
        payments = Payment.objects.filter(
            payment_date__gte=start_datetime, payment_date__lte=end_datetime, status=Payment.PaymentStatus.COMPLETED
        )

        # Get all invoices created on the date
        invoices_created = Invoice.objects.filter(issue_date=report_date)

        # Summarize payments by method
        payments_by_method = payments.values("payment_method").annotate(total=Sum("amount"), count=Count("id"))

        # Get refunds
        refunds = payments.filter(amount__lt=0)

        return {
            "date": report_date,
            "payments": {
                "total_amount": payments.filter(amount__gt=0).aggregate(Sum("amount"))["amount__sum"]
                or Decimal("0.00"),
                "total_count": payments.filter(amount__gt=0).count(),
                "by_method": list(payments_by_method),
            },
            "refunds": {
                "total_amount": abs(refunds.aggregate(Sum("amount"))["amount__sum"] or Decimal("0.00")),
                "total_count": refunds.count(),
            },
            "invoices": {
                "created_count": invoices_created.count(),
                "created_amount": invoices_created.aggregate(Sum("total_amount"))["total_amount__sum"]
                or Decimal("0.00"),
            },
            "net_cash_receipts": payments.aggregate(Sum("amount"))["amount__sum"] or Decimal("0.00"),
        }

    @staticmethod
    def get_weekly_revenue_analysis(start_date: date | None = None, end_date: date | None = None) -> dict[str, Any]:
        """Get weekly revenue analysis.

        Args:
            start_date: Start date (defaults to 7 days ago)
            end_date: End date (defaults to today)

        Returns:
            Dictionary with weekly revenue analysis
        """
        if end_date is None:
            end_date = get_current_date()
        if start_date is None:
            start_date = end_date - timedelta(days=6)

        # Get all completed payments in the period (use datetimes for clarity)
        start_dt = datetime.combine(start_date, datetime.min.time())
        end_dt = datetime.combine(end_date, datetime.max.time())
        payments = Payment.objects.filter(
            payment_date__gte=start_dt,
            payment_date__lte=end_dt,
            status=Payment.PaymentStatus.COMPLETED,
            amount__gt=0,
        )

        # Daily revenue
        daily_revenue = []
        current_date = start_date
        while current_date <= end_date:
            start_datetime = datetime.combine(current_date, datetime.min.time())
            end_datetime = datetime.combine(current_date, datetime.max.time())
            day_payments = payments.filter(payment_date__gte=start_datetime, payment_date__lte=end_datetime)
            daily_revenue.append(
                {
                    "date": current_date,
                    "revenue": day_payments.aggregate(Sum("amount"))["amount__sum"] or Decimal("0.00"),
                    "count": day_payments.count(),
                },
            )
            current_date += timedelta(days=1)

        # Revenue by payment method
        revenue_by_method = (
            payments.values("payment_method").annotate(total=Sum("amount"), count=Count("id")).order_by("-total")
        )

        # Top paying students
        top_students = (
            payments.values(
                "invoice__student__student_id",
                "invoice__student__person__first_name",
                "invoice__student__person__last_name",
            )
            .annotate(total_paid=Sum("amount"))
            .order_by("-total_paid")[:10]
        )

        return {
            "period": {
                "start_date": start_date,
                "end_date": end_date,
            },
            "summary": {
                "total_revenue": payments.aggregate(Sum("amount"))["amount__sum"] or Decimal("0.00"),
                "total_transactions": payments.count(),
                "average_transaction": payments.aggregate(avg=Sum("amount") / Count("id"))["avg"] or Decimal("0.00"),
            },
            "daily_revenue": daily_revenue,
            "revenue_by_method": list(revenue_by_method),
            "top_students": list(top_students),
        }

    @staticmethod
    def get_monthly_financial_statement(year: int, month: int) -> dict[str, Any]:
        """Get monthly financial statement.

        Args:
            year: Year for the statement
            month: Month for the statement (1-12)

        Returns:
            Dictionary with monthly financial statement data
        """
        # Calculate month boundaries
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(year, month + 1, 1) - timedelta(days=1)

        # Get all transactions for the month
        transactions = FinancialTransaction.objects.filter(
            transaction_date__gte=start_date,
            transaction_date__lte=end_date,
        )

        # Revenue (payments received)
        revenue = transactions.filter(
            transaction_type=FinancialTransaction.TransactionType.PAYMENT_RECEIVED,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Refunds
        refunds = transactions.filter(
            transaction_type=FinancialTransaction.TransactionType.PAYMENT_REFUNDED,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        # Invoices
        invoices = Invoice.objects.filter(issue_date__gte=start_date, issue_date__lte=end_date)

        # Outstanding balances
        outstanding_invoices = Invoice.objects.filter(
            Q(status=Invoice.InvoiceStatus.SENT)
            | Q(status=Invoice.InvoiceStatus.PARTIALLY_PAID)
            | Q(status=Invoice.InvoiceStatus.OVERDUE),
        )

        # Calculate collection rate
        invoiced_amount = invoices.aggregate(Sum("total_amount"))["total_amount__sum"] or Decimal("0.00")
        collected_amount = revenue
        collection_rate = (collected_amount / invoiced_amount * 100) if invoiced_amount > 0 else Decimal("0.00")

        return {
            "period": {
                "year": year,
                "month": month,
                "start_date": start_date,
                "end_date": end_date,
            },
            "revenue": {
                "gross_receipts": revenue,
                "refunds": abs(refunds),
                "net_receipts": revenue + refunds,  # refunds are negative
            },
            "invoicing": {
                "invoices_created": invoices.count(),
                "total_invoiced": invoiced_amount,
                "invoices_paid": invoices.filter(status=Invoice.InvoiceStatus.PAID).count(),
                "collection_rate": float(collection_rate),
            },
            "outstanding": {
                "count": outstanding_invoices.count(),
                "total_amount": outstanding_invoices.aggregate(total=Sum("total_amount") - Sum("paid_amount"))["total"]
                or Decimal("0.00"),
            },
            "transaction_summary": {
                "total_transactions": transactions.count(),
                "by_type": list(
                    transactions.values("transaction_type").annotate(count=Count("id"), total=Sum("amount")),
                ),
            },
        }

    @staticmethod
    def get_outstanding_balances_report() -> dict[str, Any]:
        """Get report of all outstanding balances by student.

        Returns:
            Dictionary with outstanding balance information
        """
        outstanding_invoices = Invoice.objects.filter(
            Q(status=Invoice.InvoiceStatus.SENT)
            | Q(status=Invoice.InvoiceStatus.PARTIALLY_PAID)
            | Q(status=Invoice.InvoiceStatus.OVERDUE),
        ).select_related("student__person")

        # Group by student
        student_balances: dict[int, dict[str, Any]] = {}
        for invoice in outstanding_invoices:
            student_key = invoice.student.id
            if student_key not in student_balances:
                student_balances[student_key] = {
                    "student_id": invoice.student.student_id,
                    "student_name": str(invoice.student),
                    "invoices": [],
                    "total_outstanding": Decimal("0.00"),
                }

            amount_due = invoice.amount_due
            student_balances[student_key]["invoices"].append(
                {
                    "invoice_number": invoice.invoice_number,
                    "issue_date": invoice.issue_date,
                    "due_date": invoice.due_date,
                    "total_amount": invoice.total_amount,
                    "paid_amount": invoice.paid_amount,
                    "amount_due": amount_due,
                    "status": invoice.status,
                    "is_overdue": invoice.is_overdue,
                },
            )
            student_balances[student_key]["total_outstanding"] += amount_due

        # Convert to list and sort by total outstanding
        student_list = list(student_balances.values())
        student_list.sort(key=lambda x: x["total_outstanding"], reverse=True)

        return {
            "report_date": get_current_date(),
            "summary": {
                "total_students": len(student_list),
                "total_outstanding": sum(s["total_outstanding"] for s in student_list),
                "total_invoices": outstanding_invoices.count(),
            },
            "students": student_list,
        }
