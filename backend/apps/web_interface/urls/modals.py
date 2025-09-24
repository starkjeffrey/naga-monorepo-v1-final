"""
URL patterns for modal views.
"""

from django.urls import path

from ..views.modal_views import (
    ConfirmationModalView,
    InvoiceCreateModalView,
    PaymentProcessModalView,
    QuickPaymentModalView,
    StudentCreateModalView,
    StudentEnrollModalView,
)

app_name = "modals"

urlpatterns = [
    # Student modals
    path("student/create/", StudentCreateModalView.as_view(), name="student-create"),
    path("student/<int:student_id>/enroll/", StudentEnrollModalView.as_view(), name="student-enroll"),
    # Finance modals
    path("invoice/create/", InvoiceCreateModalView.as_view(), name="invoice-create"),
    path("payment/process/", PaymentProcessModalView.as_view(), name="payment-process"),
    path("payment/quick/", QuickPaymentModalView.as_view(), name="quick-payment"),
    # Generic modals
    path("confirmation/", ConfirmationModalView.as_view(), name="confirmation"),
]
