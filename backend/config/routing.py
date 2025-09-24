"""WebSocket URL routing configuration."""

from django.urls import path

from apps.attendance.consumers import AttendanceConsumer

# Import WebSocket consumers from apps
from apps.enrollment.consumers import EnrollmentConsumer
from apps.finance.consumers import PaymentConsumer
from apps.web_interface.consumers import NotificationConsumer

websocket_urlpatterns = [
    # Enrollment real-time updates
    path("ws/enrollment/", EnrollmentConsumer.as_asgi()),
    # Attendance real-time updates
    path("ws/attendance/", AttendanceConsumer.as_asgi()),
    # Payment real-time updates
    path("ws/payments/", PaymentConsumer.as_asgi()),
    # General notifications
    path("ws/notifications/", NotificationConsumer.as_asgi()),
]
