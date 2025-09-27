"""WebSocket URL routing configuration."""

from django.urls import path

from apps.attendance.consumers import AttendanceConsumer

# Import WebSocket consumers from apps
from apps.enrollment.consumers import EnrollmentConsumer
from apps.finance.consumers import PaymentConsumer
from apps.web_interface.consumers import NotificationConsumer

# Import enhanced v2 consumers
from config.consumers import (
    GradeEntryCollaborationConsumer,
    DashboardMetricsConsumer,
    CommunicationConsumer
)

websocket_urlpatterns = [
    # Legacy WebSocket consumers (v1)
    path("ws/enrollment/", EnrollmentConsumer.as_asgi()),
    path("ws/attendance/", AttendanceConsumer.as_asgi()),
    path("ws/payments/", PaymentConsumer.as_asgi()),
    path("ws/notifications/", NotificationConsumer.as_asgi()),

    # Enhanced v2 WebSocket consumers
    path("ws/grades/live-entry/<str:class_id>/", GradeEntryCollaborationConsumer.as_asgi()),
    path("ws/dashboard/metrics/", DashboardMetricsConsumer.as_asgi()),
    path("ws/communications/<str:room_id>/", CommunicationConsumer.as_asgi()),

    # GraphQL subscriptions endpoint
    # Note: GraphQL WebSocket support will be handled by Strawberry's built-in consumer
]
