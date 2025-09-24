"""URL configuration for the attendance app."""

from django.urls import path

from .views import attendance_views

app_name = "attendance"

urlpatterns = [
    # Main dashboard
    path("", attendance_views.AttendanceDashboardView.as_view(), name="dashboard"),
    # Class attendance management
    path("class/<int:class_header_id>/", attendance_views.class_attendance_view, name="class_attendance"),
    path("class/<int:class_header_id>/roster/", attendance_views.attendance_roster, name="attendance_roster"),
    path("class/<int:class_header_id>/report/", attendance_views.attendance_report, name="attendance_report"),
    # HTMX endpoints for real-time attendance marking
    path("mark/<int:class_header_id>/", attendance_views.mark_attendance, name="mark_attendance"),
    path("quick-mark/<int:class_header_id>/", attendance_views.quick_mark_all, name="quick_mark_all"),
    path("bulk-update/", attendance_views.bulk_attendance_update, name="bulk_update"),
    # Student search and utilities
    path("search-students/", attendance_views.student_attendance_search, name="student_search"),
]
