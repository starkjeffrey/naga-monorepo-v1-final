"""URL configuration for level testing app.

This module defines URL patterns for the level testing application process,
including both student-facing wizard interface and staff administration tools.

URL structure:
- Application wizard: /test-application/
- Staff administration: /admin/level-testing/
- API endpoints: /api/level-testing/
"""

from django.urls import path

from apps.level_testing.views import (
    ApplicationCompleteView,
    ApplicationListView,
    ApplicationPendingView,
    ApplicationReviewStepView,
    ApplicationStartView,
    DuplicateReviewView,
    EducationBackgroundStepView,
    PaymentProcessingView,
    PaymentStepView,
    PersonalInfoStepView,
    ProgramPreferencesStepView,
    StaffDashboardView,
    WizardStepValidationView,
    application_status_check,
)

# Import payment-first workflow views
from apps.level_testing.views_payment_first import (
    AccessErrorView,
    CashierPaymentView,
    MobileApplicationView,
    QRCodeLandingView,
    SaveProgressView,
    TelegramVerificationView,
)

app_name = "level_testing"

urlpatterns = [
    # Payment-First Workflow (New)
    # Cashier interface for payment collection
    path("cashier/collect-payment/", CashierPaymentView.as_view(), name="cashier_payment"),
    # Mobile application flow (accessed via QR code)
    path("apply/<str:access_code>/", QRCodeLandingView.as_view(), name="qr_landing"),
    path("apply/<str:access_code>/telegram-verify/", TelegramVerificationView.as_view(), name="telegram_verify"),
    path("apply/<str:access_code>/application/", MobileApplicationView.as_view(), name="mobile_application"),
    path("apply/<str:access_code>/status/", ApplicationPendingView.as_view(), name="application_status"),
    # Error pages
    path("access-error/", AccessErrorView.as_view(), name="access_error"),
    # AJAX endpoints for payment-first workflow
    path("api/save-progress/", SaveProgressView.as_view(), name="save_progress"),
    # ============================================================
    # Legacy Student Application Wizard
    # NOTE: Preserved for backward compatibility with existing links
    # New applications should use payment-first workflow above
    # ============================================================
    path("", ApplicationStartView.as_view(), name="application_start"),
    path(
        "step/personal-info/",
        PersonalInfoStepView.as_view(),
        name="step_personal_info",
    ),
    path(
        "step/education/",
        EducationBackgroundStepView.as_view(),
        name="step_education",
    ),
    path(
        "step/preferences/",
        ProgramPreferencesStepView.as_view(),
        name="step_preferences",
    ),
    path("step/review/", ApplicationReviewStepView.as_view(), name="step_review"),
    path("step/payment/", PaymentStepView.as_view(), name="step_payment"),
    # Application Status Pages
    path(
        "complete/<int:pk>/",
        ApplicationCompleteView.as_view(),
        name="application_complete",
    ),
    path(
        "pending/<int:pk>/",
        ApplicationPendingView.as_view(),
        name="application_pending",
    ),
    # Staff Administration
    path("staff/", StaffDashboardView.as_view(), name="staff_dashboard"),
    path(
        "staff/applications/",
        ApplicationListView.as_view(),
        name="staff_applications",
    ),
    path(
        "staff/duplicate-review/<int:pk>/",
        DuplicateReviewView.as_view(),
        name="duplicate_review",
    ),
    path(
        "staff/payment/<int:pk>/",
        PaymentProcessingView.as_view(),
        name="payment_processing",
    ),
    # HTMX/AJAX Endpoints
    path(
        "api/status/<int:pk>/",
        application_status_check,
        name="application_status_check",
    ),
    path("api/validate/", WizardStepValidationView.as_view(), name="wizard_validation"),
]
