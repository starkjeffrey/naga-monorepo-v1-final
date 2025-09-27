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

# Import enhanced consumers with advanced features
from config.enhanced_consumers import (
    EnhancedGradeEntryCollaborationConsumer,
    RealTimeDashboardConsumer,
    NotificationConsumer
)

websocket_urlpatterns = [
    # Legacy WebSocket consumers (v1)
    path("ws/enrollment/", EnrollmentConsumer.as_asgi()),
    path("ws/attendance/", AttendanceConsumer.as_asgi()),
    path("ws/payments/", PaymentConsumer.as_asgi()),

    # Enhanced v2 WebSocket consumers with advanced features
    path("ws/v2/grades/collaboration/<str:class_id>/", EnhancedGradeEntryCollaborationConsumer.as_asgi()),
    path("ws/v2/dashboard/metrics/", RealTimeDashboardConsumer.as_asgi()),
    path("ws/v2/notifications/", NotificationConsumer.as_asgi()),

    # Innovation Features WebSocket Routes
    path("ws/v2/innovation/student-success/<str:student_id>/", RealTimeDashboardConsumer.as_asgi()),
    path("ws/v2/innovation/predictions/", RealTimeDashboardConsumer.as_asgi()),
    path("ws/v2/innovation/document-processing/", RealTimeDashboardConsumer.as_asgi()),
    path("ws/v2/innovation/collaboration/<str:workspace_id>/", EnhancedGradeEntryCollaborationConsumer.as_asgi()),

    # Financial Real-time Features
    path("ws/v2/finance/fraud-detection/", RealTimeDashboardConsumer.as_asgi()),
    path("ws/v2/finance/payment-processing/", RealTimeDashboardConsumer.as_asgi()),

    # Legacy v2 consumers (maintained for compatibility)
    path("ws/grades/live-entry/<str:class_id>/", GradeEntryCollaborationConsumer.as_asgi()),
    path("ws/dashboard/metrics/", DashboardMetricsConsumer.as_asgi()),
    path("ws/communications/<str:room_id>/", CommunicationConsumer.as_asgi()),

    # GraphQL subscriptions endpoint
    # Note: GraphQL WebSocket support will be handled by Strawberry's built-in consumer
]
