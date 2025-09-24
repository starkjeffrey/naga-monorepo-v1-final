from django.urls import path

from . import views

app_name = "scheduling"

urlpatterns = [
    # Main views with real data integration
    path("", views.SchedulingDashboardView.as_view(), name="dashboard"),
    path("classes/", views.SchedulingClassListView.as_view(), name="class_list"),
    path(
        "classes/<int:pk>/",
        views.SchedulingClassDetailView.as_view(),
        name="class_detail",
    ),
    # Main section views (placeholder implementations)
    path("enrollments/", views.SchedulingEnrollmentsView.as_view(), name="enrollments"),
    path("schedule/", views.SchedulingScheduleView.as_view(), name="schedule_view"),
    path("reports/", views.SchedulingReportsView.as_view(), name="reports"),
    path("archive/", views.SchedulingArchiveView.as_view(), name="archive"),
    # Class Enrollment Display System
    path("enrollment-display/", views.ClassScheduleView.as_view(), name="class_schedule"),
    path("api/classes/", views.ClassDataAPIView.as_view(), name="class_data_api"),
    path("api/enroll/", views.EnrollStudentView.as_view(), name="enroll_student_api"),
    path("api/class/<int:class_id>/", views.ClassDetailView.as_view(), name="class_detail_api"),
    path("export/schedule/", views.ExportScheduleView.as_view(), name="export_schedule"),
    # HTMX API endpoints with real functionality
    path("api/set-term/<int:term_id>/", views.SetTermView.as_view(), name="set_term"),
    path(
        "api/dashboard-stats/",
        views.DashboardStatsView.as_view(),
        name="dashboard_stats",
    ),
    # Placeholder routes for future implementation
    # These will be replaced with proper views as features are developed
    path("classes/create/", views.SchedulingDashboardView.as_view(), name="class_create"),
    path(
        "classes/<int:pk>/edit/",
        views.SchedulingDashboardView.as_view(),
        name="class_edit",
    ),
    path(
        "classes/<int:pk>/enrollments/",
        views.SchedulingDashboardView.as_view(),
        name="class_enrollments",
    ),
    path(
        "classes/<int:pk>/modal/",
        views.SchedulingDashboardView.as_view(),
        name="class_detail_modal",
    ),
    path(
        "classes/<int:pk>/copy/",
        views.SchedulingDashboardView.as_view(),
        name="class_copy",
    ),
    path(
        "classes/<int:pk>/cancel/",
        views.SchedulingDashboardView.as_view(),
        name="class_cancel",
    ),
    path(
        "classes/<int:pk>/waitlist/",
        views.SchedulingDashboardView.as_view(),
        name="class_waitlist",
    ),
    path(
        "classes/<int:pk>/roster/",
        views.SchedulingDashboardView.as_view(),
        name="class_roster",
    ),
    path("export/", views.SchedulingDashboardView.as_view(), name="export_classes"),
    # API endpoints for future implementation
    path(
        "api/student-search/",
        views.SchedulingDashboardView.as_view(),
        name="student_search",
    ),
    path(
        "api/enroll/<int:class_pk>/",
        views.SchedulingDashboardView.as_view(),
        name="enroll_student",
    ),
    path(
        "api/drop/<int:enrollment_pk>/",
        views.SchedulingDashboardView.as_view(),
        name="drop_student",
    ),
]
