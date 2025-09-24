"""
URL configuration for the web interface app.

This module defines all URL patterns for the user-facing web interface.
URLs are organized by functionality with proper namespacing.
"""

from django.urls import include, path
from django.views.generic import TemplateView

from .views import (
    academic_views,
    auth_views,
    dashboard_views,
    finance_views,
    grade_views,
    modal_views,
    reports_views,
    schedule_views,
    student_locator_views,
    student_views,
)
from .views.simple_student_view import SimpleStudentListView

app_name = "web_interface"

urlpatterns = [
    # Authentication - Now using the beautiful centered login as default!
    path("", auth_views.LoginCenteredView.as_view(), name="login"),
    path("login/", auth_views.LoginCenteredView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("role-switch/", auth_views.RoleSwitchView.as_view(), name="role-switch"),
    # Dashboard (role-specific)
    path("dashboard/", dashboard_views.DashboardView.as_view(), name="dashboard"),
    # Student Management
    path(
        "students/",
        include(
            [
                path("", student_views.StudentListView.as_view(), name="student-list"),
                path("locator/", student_locator_views.StudentLocatorView.as_view(), name="student-locator"),
                path(
                    "locator/results/",
                    student_locator_views.StudentLocatorResultsView.as_view(),
                    name="student-locator-results",
                ),
                path(
                    "locator/export/",
                    student_locator_views.StudentLocatorExportView.as_view(),
                    name="student-locator-export",
                ),
                path("advanced-search/", student_views.StudentListView.as_view(), name="student-advanced-search"),
                path("simple/", SimpleStudentListView.as_view(), name="simple-student-list"),
                path("new/", student_views.StudentCreateView.as_view(), name="student-create"),
                path("<int:pk>/", student_views.StudentDetailView.as_view(), name="student-detail"),
                path("<int:pk>/edit/", student_views.StudentUpdateView.as_view(), name="student-update"),
                path("<int:pk>/enrollment/", student_views.StudentEnrollmentView.as_view(), name="student-enrollment"),
            ]
        ),
    ),
    # Academic Management
    path(
        "academic/",
        include(
            [
                path("courses/", academic_views.CourseListView.as_view(), name="course-list"),
                path("enrollment/", academic_views.EnrollmentManagementView.as_view(), name="enrollment-management"),
                path("grades/", academic_views.GradeManagementView.as_view(), name="grades"),
                path("grade-entry/", grade_views.GradeEntryView.as_view(), name="grade-entry"),
                path("schedules/", academic_views.ScheduleView.as_view(), name="schedules"),
                path("schedule-builder/", schedule_views.ScheduleBuilderView.as_view(), name="schedule-builder"),
                path("transcripts/", academic_views.TranscriptView.as_view(), name="transcripts"),
            ]
        ),
    ),
    # Finance Management
    path(
        "finance/",
        include(
            [
                path("billing/", finance_views.BillingListView.as_view(), name="billing"),
                path("invoice/<int:pk>/", finance_views.InvoiceDetailView.as_view(), name="invoice-detail"),
                path("invoice/create/", finance_views.InvoiceCreateView.as_view(), name="invoice-create"),
                path("payments/", finance_views.PaymentProcessingView.as_view(), name="payment-processing"),
                path("payments/quick/", finance_views.QuickPaymentView.as_view(), name="quick-payment"),
                path("accounts/<int:student_id>/", finance_views.StudentAccountView.as_view(), name="student-account"),
                path("cashier/", finance_views.CashierSessionView.as_view(), name="cashier"),
                path("reports/", reports_views.ReportsDashboardView.as_view(), name="reports-dashboard"),
            ]
        ),
    ),
    # HTMX Cashier endpoints
    path(
        "cashier/",
        include(
            [
                path("student-search/", finance_views.cashier_student_search, name="cashier-student-search"),
                path("student/<int:student_id>/", finance_views.cashier_student_detail, name="cashier-student-detail"),
                path("process-payment/", finance_views.process_payment, name="process-payment"),
                path("cash-drawer/", finance_views.cash_drawer_management, name="cash-drawer-management"),
                path("receipt/<int:payment_id>/", finance_views.payment_receipt, name="payment-receipt"),
            ]
        ),
    ),
    # Modal endpoints
    path(
        "modals/",
        include(
            [
                path("student/create/", modal_views.StudentCreateModalView.as_view(), name="modal-student-create"),
                path("invoice/create/", modal_views.InvoiceCreateModalView.as_view(), name="modal-invoice-create"),
                path("payment/process/", modal_views.PaymentProcessModalView.as_view(), name="modal-payment-process"),
                path("payment/quick/", modal_views.QuickPaymentModalView.as_view(), name="modal-quick-payment"),
                path("confirmation/", modal_views.ConfirmationModalView.as_view(), name="modal-confirmation"),
            ]
        ),
    ),
    # HTMX search endpoints
    path(
        "search/",
        include(
            [
                path("students/", student_views.StudentSearchView.as_view(), name="student-search"),
                path("students/quick/", student_views.student_quick_search, name="student-quick-search"),
                path("finance/students/", finance_views.StudentSearchView.as_view(), name="finance-student-search"),
            ]
        ),
    ),
    # HTMX enrollment endpoints
    path(
        "enrollment/",
        include(
            [
                path("class/<int:class_id>/status/", academic_views.class_card_status, name="class-card-status"),
                path("class/<int:class_id>/roster/", academic_views.class_roster_modal, name="class-roster-modal"),
                path(
                    "class/<int:class_id>/enroll-form/",
                    academic_views.quick_enrollment_form,
                    name="quick-enrollment-form",
                ),
                path(
                    "class/<int:class_id>/process-enrollment/",
                    academic_views.process_quick_enrollment,
                    name="process-quick-enrollment",
                ),
                path("student-search/", student_views.student_search_for_enrollment, name="student-search-enrollment"),
                # 3 Enrollment Template Systems
                path("wizard/", academic_views.EnrollmentWizardView.as_view(), name="enrollment-wizard"),
                path("quick-form/", academic_views.QuickEnrollmentModalView.as_view(), name="quick-enrollment-modal"),
                path("class-cards/", academic_views.EnhancedClassCardsView.as_view(), name="enhanced-class-cards"),
            ]
        ),
    ),
    # HTMX grade entry endpoints
    path(
        "grades/",
        include(
            [
                path("class/<int:class_id>/data/", grade_views.grade_entry_class_data, name="grade-entry-class-data"),
                path("save/", grade_views.save_grade, name="save-grade"),
                path("bulk-update/", grade_views.bulk_grade_update, name="bulk-grade-update"),
            ]
        ),
    ),
    # HTMX schedule builder endpoints
    path(
        "schedule/",
        include(
            [
                path("term/<int:term_id>/data/", schedule_views.schedule_data, name="schedule-data"),
                path("create/", schedule_views.create_class_schedule, name="create-class-schedule"),
                path(
                    "class/<int:class_header_id>/update/",
                    schedule_views.update_class_schedule,
                    name="update-class-schedule",
                ),
                path(
                    "class/<int:class_header_id>/delete/",
                    schedule_views.delete_class_schedule,
                    name="delete-class-schedule",
                ),
                path("conflicts/check/", schedule_views.check_schedule_conflicts, name="check-schedule-conflicts"),
            ]
        ),
    ),
    # HTMX reports endpoints
    path(
        "reports/",
        include(
            [
                path("dashboard-data/", reports_views.reports_dashboard_data, name="reports-dashboard-data"),
                path("daily-cash/", reports_views.daily_cash_report, name="daily-cash-report"),
                path("student-balances/", reports_views.student_balances_report, name="student-balances-report"),
                path("export/<str:report_type>/", reports_views.export_report, name="export-report"),
            ]
        ),
    ),
    # HTMX notification endpoints
    path(
        "notifications/",
        include(
            [
                path("user/", reports_views.get_user_notifications, name="user-notifications"),
                path("activity/", reports_views.get_activity_feed, name="activity-feed"),
                path(
                    "<int:notification_id>/read/", reports_views.mark_notification_read, name="mark-notification-read"
                ),
                path("read-all/", reports_views.mark_all_notifications_read, name="mark-all-notifications-read"),
            ]
        ),
    ),
    # Placeholder URLs for navigation (to be implemented)
    path(
        "teachers/",
        TemplateView.as_view(template_name="web_interface/pages/common/placeholder.html"),
        name="teacher-list",
    ),
    path(
        "classes/",
        TemplateView.as_view(template_name="web_interface/pages/common/placeholder.html"),
        name="class-list",
    ),
    path(
        "users/", TemplateView.as_view(template_name="web_interface/pages/common/placeholder.html"), name="user-list"
    ),
    path("backup/", TemplateView.as_view(template_name="web_interface/pages/common/placeholder.html"), name="backup"),
    path(
        "my-courses/",
        TemplateView.as_view(template_name="web_interface/pages/common/placeholder.html"),
        name="my-courses",
    ),
    path(
        "my-schedule/",
        TemplateView.as_view(template_name="web_interface/pages/common/placeholder.html"),
        name="my-schedule",
    ),
    path(
        "my-grades/",
        TemplateView.as_view(template_name="web_interface/pages/common/placeholder.html"),
        name="my-grades",
    ),
    path(
        "my-transcript/",
        TemplateView.as_view(template_name="web_interface/pages/common/placeholder.html"),
        name="my-transcript",
    ),
    path(
        "course-registration/",
        TemplateView.as_view(template_name="web_interface/pages/common/placeholder.html"),
        name="course-registration",
    ),
    path(
        "drop-add/", TemplateView.as_view(template_name="web_interface/pages/common/placeholder.html"), name="drop-add"
    ),
    path(
        "my-balance/",
        TemplateView.as_view(template_name="web_interface/pages/common/placeholder.html"),
        name="my-balance",
    ),
    path(
        "make-payment/",
        TemplateView.as_view(template_name="web_interface/pages/common/placeholder.html"),
        name="make-payment",
    ),
    path(
        "payment-history/",
        TemplateView.as_view(template_name="web_interface/pages/common/placeholder.html"),
        name="payment-history",
    ),
    path(
        "my-classes/",
        TemplateView.as_view(template_name="web_interface/pages/common/placeholder.html"),
        name="my-classes",
    ),
    path(
        "attendance/",
        TemplateView.as_view(template_name="web_interface/pages/common/placeholder.html"),
        name="attendance",
    ),
    path(
        "my-students/",
        TemplateView.as_view(template_name="web_interface/pages/common/placeholder.html"),
        name="my-students",
    ),
    path(
        "teaching-reports/",
        TemplateView.as_view(template_name="web_interface/pages/common/placeholder.html"),
        name="teaching-reports",
    ),
]
