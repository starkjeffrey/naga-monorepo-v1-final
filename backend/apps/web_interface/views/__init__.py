"""
Web interface views module.

This module contains all views for the user-facing web interface of Naga SIS.
Views are organized by functionality:
- auth_views: Authentication and login
- dashboard_views: Role-based dashboards
- student_views: Student management
- academic_views: Academic operations
- finance_views: Financial operations
- common_views: Shared utilities
"""

# Sub-modules are imported individually below
from .academic_views import (
    CourseListView,
    EnrollmentApprovalView,
    EnrollmentManagementView,
    GradeEntryView,
    GradeManagementView,
    ScheduleView,
    StudentGradeView,
    TranscriptView,
)
from .auth_views import (
    LogoutView,
    ProfileView,
    RoleSwitchView,
    SessionInfoView,
    auth_context_processor,
)
from .common_views import AboutView, HelpView, SettingsView
from .dashboard_views import DashboardView
from .finance_views import (
    BillingListView,
    CashierSessionView,
    FinancialReportsView,
    InvoiceCreateView,
    InvoiceDetailView,
    PaymentProcessingView,
    QuickPaymentView,
    StudentAccountView,
)
from .finance_views import (
    StudentSearchView as FinanceStudentSearchView,
)
from .modal_views import (
    ConfirmationModalView,
    InvoiceCreateModalView,
    PaymentProcessModalView,
    QuickPaymentModalView,
    StudentCreateModalView,
    StudentEnrollModalView,
)
from .student_views import (
    StudentCreateView,
    StudentDetailView,
    StudentEnrollmentView,
    StudentListView,
    StudentSearchView,
    StudentUpdateView,
)

__all__ = [
    # Common views
    "AboutView",
    # Finance views
    "BillingListView",
    "CashierSessionView",
    "ConfirmationModalView",
    # Academic views
    "CourseListView",
    # Dashboard views
    "DashboardView",
    "EnrollmentApprovalView",
    "EnrollmentManagementView",
    "FinanceStudentSearchView",
    "FinancialReportsView",
    "GradeEntryView",
    "GradeManagementView",
    "HelpView",
    "InvoiceCreateModalView",
    "InvoiceCreateView",
    "InvoiceDetailView",
    # Auth views
    "LogoutView",
    "PaymentProcessModalView",
    "PaymentProcessingView",
    "ProfileView",
    "QuickPaymentModalView",
    "QuickPaymentView",
    "RoleSwitchView",
    "ScheduleView",
    "SessionInfoView",
    "SettingsView",
    "StudentAccountView",
    # Modal views
    "StudentCreateModalView",
    "StudentCreateView",
    "StudentDetailView",
    "StudentEnrollModalView",
    "StudentEnrollmentView",
    "StudentGradeView",
    # Student views
    "StudentListView",
    "StudentSearchView",
    "StudentUpdateView",
    "TranscriptView",
    "auth_context_processor",
]
