"""URL configuration for finance app views."""

from django.urls import path

from apps.finance.views.cashier import (
    CashDrawerManagementView,
    CashierDashboardView,
    PaymentCollectionView,
    ReceiptView,
    RefundProcessingView,
    StudentSearchView,
    TransactionHistoryView,
)
from apps.finance.views.daily_reports import (
    DailyCashierReconciliationView,
    DailyCashReceiptsPDFView,
    DailyCashReceiptsView,
    DailyPaymentSummaryView,
)
from apps.finance.views.finance_dashboard import (
    FeeManagementView,
    FinanceDashboardView,
    FinancialReportsHubView,
    OutstandingBalancesView,
    RevenueAnalysisView,
    ScholarshipOverviewView,
)
from apps.finance.views.quickbooks_reports import (
    GenerateQuickBooksReportView,
    QuickBooksReportPreviewView,
    QuickBooksReportView,
)

app_name = "finance"

urlpatterns = [
    # Finance dashboard and management
    path("", FinanceDashboardView.as_view(), name="dashboard"),
    path("revenue-analysis/", RevenueAnalysisView.as_view(), name="revenue-analysis"),
    path(
        "outstanding-balances/",
        OutstandingBalancesView.as_view(),
        name="outstanding-balances",
    ),
    path("fee-management/", FeeManagementView.as_view(), name="fee-management"),
    path(
        "scholarship-overview/",
        ScholarshipOverviewView.as_view(),
        name="scholarship-overview",
    ),
    path("reports/", FinancialReportsHubView.as_view(), name="reports-hub"),
    # QuickBooks report generation
    path("quickbooks-reports/", QuickBooksReportView.as_view(), name="quickbooks_reports"),
    path(
        "quickbooks-reports/generate/",
        GenerateQuickBooksReportView.as_view(),
        name="generate_quickbooks_report",
    ),
    path(
        "quickbooks-reports/preview/",
        QuickBooksReportPreviewView.as_view(),
        name="preview_quickbooks_report",
    ),
    # Cashier interface
    path("cashier/", CashierDashboardView.as_view(), name="cashier-dashboard"),
    path("cashier/search/", StudentSearchView.as_view(), name="student-search"),
    path(
        "cashier/collect/<int:student_id>/",
        PaymentCollectionView.as_view(),
        name="payment-collection",
    ),
    path(
        "cashier/receipt/<int:payment_id>/",
        ReceiptView.as_view(),
        name="cashier-receipt",
    ),
    path("cashier/cash-drawer/", CashDrawerManagementView.as_view(), name="cash-drawer"),
    path(
        "cashier/transactions/",
        TransactionHistoryView.as_view(),
        name="transaction-history",
    ),
    path(
        "cashier/refund/<int:payment_id>/",
        RefundProcessingView.as_view(),
        name="process-refund",
    ),
    # Daily reports
    path(
        "reports/daily-cash-receipts/",
        DailyCashReceiptsView.as_view(),
        name="daily-cash-receipts",
    ),
    path(
        "reports/daily-cashier-reconciliation/",
        DailyCashierReconciliationView.as_view(),
        name="daily-cashier-reconciliation",
    ),
    path(
        "reports/daily-payment-summary/",
        DailyPaymentSummaryView.as_view(),
        name="daily-payment-summary",
    ),
    path(
        "reports/daily-cash-receipts/pdf/",
        DailyCashReceiptsPDFView.as_view(),
        name="daily-cash-receipts-pdf",
    ),
    # Weekly reports (placeholder URLs for now)
    path(
        "reports/weekly-revenue-analysis/",
        FinanceDashboardView.as_view(),
        name="weekly-revenue-analysis",
    ),
    path(
        "reports/weekly-payment-trends/",
        FinanceDashboardView.as_view(),
        name="weekly-payment-trends",
    ),
    path(
        "reports/weekly-outstanding-balances/",
        FinanceDashboardView.as_view(),
        name="weekly-outstanding-balances",
    ),
    # Monthly reports (placeholder URLs for now)
    path(
        "reports/monthly-financial-statement/",
        FinanceDashboardView.as_view(),
        name="monthly-financial-statement",
    ),
    path(
        "reports/monthly-revenue-report/",
        FinanceDashboardView.as_view(),
        name="monthly-revenue-report",
    ),
    path(
        "reports/monthly-aging-report/",
        FinanceDashboardView.as_view(),
        name="monthly-aging-report",
    ),
    # Term reports (placeholder URLs for now)
    path(
        "reports/term-revenue-summary/",
        FinanceDashboardView.as_view(),
        name="term-revenue-summary",
    ),
    path(
        "reports/term-enrollment-payment/",
        FinanceDashboardView.as_view(),
        name="term-enrollment-payment",
    ),
    path(
        "reports/term-scholarship-report/",
        FinanceDashboardView.as_view(),
        name="term-scholarship-report",
    ),
]
