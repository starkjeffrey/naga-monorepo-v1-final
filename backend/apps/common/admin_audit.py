"""Admin configuration for student activity audit logging.

This module provides comprehensive admin interfaces for viewing and managing
student activity logs with advanced filtering, search, and export capabilities.
"""

import csv
from datetime import datetime, timedelta
from typing import Any

from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.db.models import Count, QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import StudentActivityLog

User = get_user_model()


class StudentActivityLogAdmin(admin.ModelAdmin):
    """Comprehensive admin interface for StudentActivityLog with advanced features.

    Features:
    - Colored visibility badges for quick identification
    - Advanced filtering by date, student, activity type, and visibility
    - Search across multiple fields
    - Bulk operations for visibility management
    - CSV export functionality
    - Performance optimized with select_related
    - Summary statistics display
    """

    # List display configuration
    list_display = [
        "created_at_display",
        "student_number",
        "student_name_display",
        "activity_type_display",
        "description_truncated",
        "term_name",
        "class_info",
        "performed_by_display",
        "visibility_badge",
        "is_system_generated",
    ]

    # Filter configuration
    list_filter = [
        "activity_type",
        "visibility",
        "is_system_generated",
        "created_at",
        "term_name",
        "performed_by",
    ]

    # Search configuration
    search_fields = [
        "student_number",
        "student_name",
        "description",
        "class_code",
        "class_section",
        "program_name",
        "performed_by__username",
        "performed_by__first_name",
        "performed_by__last_name",
    ]

    # Date hierarchy for easy navigation
    date_hierarchy = "created_at"

    # Ordering
    ordering = ["-created_at"]

    # Read-only fields (audit logs should not be edited)
    readonly_fields = [
        "created_at",
        "student_number",
        "student_name",
        "activity_type",
        "description",
        "term_name",
        "class_code",
        "class_section",
        "program_name",
        "activity_details",
        "performed_by",
        "is_system_generated",
        "visibility",
        "activity_details_formatted",
    ]

    # Fieldsets for detailed view
    fieldsets = (
        (
            _("Activity Information"),
            {
                "fields": (
                    "created_at",
                    "activity_type",
                    "description",
                    "visibility",
                    "is_system_generated",
                ),
            },
        ),
        (
            _("Student Information"),
            {
                "fields": (
                    "student_number",
                    "student_name",
                ),
            },
        ),
        (
            _("Academic Context"),
            {
                "fields": (
                    "term_name",
                    "class_code",
                    "class_section",
                    "program_name",
                ),
                "classes": ["collapse"],
            },
        ),
        (
            _("Administrative Details"),
            {
                "fields": (
                    "performed_by",
                    "activity_details_formatted",
                ),
            },
        ),
    )

    # Pagination
    list_per_page = 50

    # Actions
    actions = ["export_as_csv", "mark_as_staff_only", "mark_as_student_visible"]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset with select_related for better performance."""
        queryset = super().get_queryset(request)
        return queryset.select_related("performed_by")

    # Custom display methods
    def created_at_display(self, obj: StudentActivityLog) -> str:
        """Format created_at timestamp."""
        return obj.created_at.strftime("%Y-%m-%d %H:%M")

    created_at_display.short_description = _("Date/Time")  # type: ignore[attr-defined]
    created_at_display.admin_order_field = "created_at"  # type: ignore[attr-defined]

    def student_name_display(self, obj: StudentActivityLog) -> str:
        """Display student name with tooltip."""
        if obj.student_name:
            return format_html(
                '<span title="Student #{}">{}</span>',
                obj.student_number,
                (obj.student_name[:30] + "..." if len(obj.student_name) > 30 else obj.student_name),
            )
        return "-"

    student_name_display.short_description = _("Student Name")  # type: ignore[attr-defined]

    def activity_type_display(self, obj: StudentActivityLog) -> str:
        """Display activity type with color coding."""
        color_map = {
            "CLASS_ENROLLMENT": "#28a745",  # Green
            "CLASS_WITHDRAWAL": "#dc3545",  # Red
            "CLASS_COMPLETION": "#007bff",  # Blue
            "LANGUAGE_PROMOTION": "#17a2b8",  # Cyan
            "GRADE_ASSIGNMENT": "#6c757d",  # Gray
            "GRADE_CHANGE": "#ffc107",  # Yellow
            "MANAGEMENT_OVERRIDE": "#e83e8c",  # Pink
            "SCHOLARSHIP_ASSIGNED": "#20c997",  # Teal
            "PROFILE_UPDATE": "#6f42c1",  # Purple
        }

        color = color_map.get(obj.activity_type, "#6c757d")
        return format_html(  # type: ignore[attr-defined]
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            getattr(obj, "get_activity_type_display", lambda: obj.activity_type)(),
        )

    activity_type_display.short_description = _("Activity Type")  # type: ignore[attr-defined]
    activity_type_display.admin_order_field = "activity_type"  # type: ignore[attr-defined]

    def description_truncated(self, obj: StudentActivityLog) -> str:
        """Truncate long descriptions with full text in tooltip."""
        if len(obj.description) > 50:
            return format_html(
                '<span title="{}">{}</span>',
                obj.description,
                obj.description[:50] + "...",
            )
        return obj.description

    description_truncated.short_description = _("Description")  # type: ignore[attr-defined]

    def class_info(self, obj: StudentActivityLog) -> str:
        """Combine class code and section."""
        if obj.class_code:
            section = f"-{obj.class_section}" if obj.class_section else ""
            return f"{obj.class_code}{section}"
        return "-"

    class_info.short_description = _("Class")  # type: ignore[attr-defined]
    class_info.admin_order_field = "class_code"  # type: ignore[attr-defined]

    def performed_by_display(self, obj: StudentActivityLog) -> str:
        """Display who performed the action."""
        if obj.performed_by:
            full_name = getattr(obj.performed_by, "get_full_name", lambda: "")()  # type: ignore[attr-defined]
            email = getattr(obj.performed_by, "email", "")  # type: ignore[attr-defined]
            if full_name:
                return format_html('<span title="{}">{}</span>', email, full_name)
            return f"{email}"
        return "-"

    performed_by_display.short_description = _("Performed By")  # type: ignore[attr-defined]
    performed_by_display.admin_order_field = "performed_by"  # type: ignore[attr-defined]

    def visibility_badge(self, obj: StudentActivityLog) -> str:
        """Display visibility level with colored badge."""
        badge_styles = {
            StudentActivityLog.VisibilityLevel.STAFF_ONLY: "background-color: #dc3545; color: white;",  # Red
            StudentActivityLog.VisibilityLevel.STUDENT_VISIBLE: "background-color: #28a745; color: white;",  # Green
            StudentActivityLog.VisibilityLevel.PUBLIC: "background-color: #007bff; color: white;",  # Blue
        }

        style = badge_styles.get(obj.visibility, "")
        return format_html(
            '<span style="padding: 3px 8px; border-radius: 3px; font-size: 11px; {}">{}</span>',
            style,
            getattr(obj, "get_visibility_display", lambda: obj.visibility)(),
        )

    visibility_badge.short_description = _("Visibility")  # type: ignore[attr-defined]
    visibility_badge.admin_order_field = "visibility"  # type: ignore[attr-defined]

    def activity_details_formatted(self, obj: StudentActivityLog) -> str:
        """Format activity details JSON for display."""
        if obj.activity_details:
            import json

            formatted = json.dumps(obj.activity_details, indent=2, ensure_ascii=False)
            return format_html('<pre style="margin: 0;">{}</pre>', formatted)
        return "-"

    activity_details_formatted.short_description = _("Activity Details (JSON)")  # type: ignore[attr-defined]

    # Custom actions
    def export_as_csv(self, request: HttpRequest, queryset: QuerySet) -> HttpResponse:
        """Export selected logs as CSV."""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="student_activity_logs_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        )

        writer = csv.writer(response)
        writer.writerow(
            [
                "Date/Time",
                "Student Number",
                "Student Name",
                "Activity Type",
                "Description",
                "Term",
                "Class",
                "Program",
                "Performed By",
                "Visibility",
                "System Generated",
            ],
        )

        for log in queryset.select_related("performed_by"):
            writer.writerow(
                [
                    log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    log.student_number,
                    log.student_name,
                    getattr(log, "get_activity_type_display", lambda log=log: log.activity_type)(),
                    log.description,
                    log.term_name,
                    f"{log.class_code}-{log.class_section}" if log.class_code else "",
                    log.program_name,
                    (getattr(log.performed_by, "get_full_name", lambda: "")() if log.performed_by else ""),
                    getattr(log, "get_visibility_display", lambda log=log: log.visibility)(),
                    "Yes" if log.is_system_generated else "No",
                ],
            )

        self.message_user(
            request,
            f"Exported {queryset.count()} activity logs to CSV.",
            messages.SUCCESS,
        )
        return response

    export_as_csv.short_description = _("Export selected logs as CSV")  # type: ignore[attr-defined]

    def mark_as_staff_only(self, request: HttpRequest, queryset: QuerySet) -> None:
        """Mark selected logs as staff only."""
        updated = queryset.update(visibility=StudentActivityLog.VisibilityLevel.STAFF_ONLY)
        self.message_user(request, f"Marked {updated} logs as staff only.", messages.SUCCESS)

    mark_as_staff_only.short_description = _("Mark as Staff Only")  # type: ignore[attr-defined]

    def mark_as_student_visible(self, request: HttpRequest, queryset: QuerySet) -> None:
        """Mark selected logs as student visible."""
        updated = queryset.update(visibility=StudentActivityLog.VisibilityLevel.STUDENT_VISIBLE)
        self.message_user(request, f"Marked {updated} logs as student visible.", messages.SUCCESS)

    mark_as_student_visible.short_description = _("Mark as Student Visible")  # type: ignore[attr-defined]

    def changelist_view(self, request: HttpRequest, extra_context: dict[str, Any] | None = None) -> HttpResponse:
        """Add summary statistics to the changelist view."""
        extra_context = extra_context or {}

        # Get date range for statistics (last 30 days by default)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)

        # Calculate summary statistics
        qs = self.get_queryset(request)
        recent_qs = qs.filter(created_at__gte=start_date)

        stats = {
            "total_logs": qs.count(),
            "recent_logs": recent_qs.count(),
            "activity_breakdown": recent_qs.values("activity_type").annotate(count=Count("id")).order_by("-count")[:5],
            "visibility_breakdown": recent_qs.values("visibility").annotate(count=Count("id")),
            "top_students": recent_qs.values("student_number", "student_name")
            .annotate(count=Count("id"))
            .order_by("-count")[:5],
        }

        extra_context["activity_stats"] = stats
        extra_context["date_range"] = f"{start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}"

        return super().changelist_view(request, extra_context=extra_context)

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Prevent manual addition of audit logs."""
        return False

    def has_delete_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Only superusers can delete audit logs."""
        return request.user.is_superuser

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        """Audit logs are read-only."""
        return False

    class Media:
        css = {"all": ("admin/css/student_activity_log.css",)}
        js = ("admin/js/student_activity_log.js",)
