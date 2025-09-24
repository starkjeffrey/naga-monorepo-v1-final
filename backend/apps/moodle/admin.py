"""Moodle integration Django admin configuration."""

from typing import Any, cast

from django.contrib import admin
from django.utils.html import format_html

from .models import (
    MoodleAPILog,
    MoodleCourseMapping,
    MoodleEnrollmentMapping,
    MoodleGradeMapping,
    MoodleSyncStatus,
    MoodleUserMapping,
)


@admin.register(MoodleSyncStatus)
class MoodleSyncStatusAdmin(admin.ModelAdmin):
    """Admin interface for Moodle sync status."""

    list_display = [
        "content_object",
        "moodle_id",
        "sync_status",
        "last_synced",
        "retry_count",
        "error_summary",
    ]
    list_filter = ["sync_status", "content_type", "last_synced"]
    search_fields = ["moodle_id", "error_message"]
    readonly_fields = ["content_type", "object_id", "last_synced"]

    def error_summary(self, obj):
        """Display truncated error message."""
        if obj.error_message:
            return obj.error_message[:100] + "..." if len(obj.error_message) > 100 else obj.error_message
        return "-"

    cast("Any", error_summary).short_description = "Error Summary"

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("content_type")


@admin.register(MoodleUserMapping)
class MoodleUserMappingAdmin(admin.ModelAdmin):
    """Admin interface for Moodle user mappings."""

    list_display = [
        "sis_person",
        "moodle_user_id",
        "moodle_username",
        "moodle_email",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "created_at"]
    search_fields = [
        "sis_person__first_name",
        "sis_person__last_name",
        "moodle_username",
        "moodle_email",
    ]
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("sis_person")


@admin.register(MoodleCourseMapping)
class MoodleCourseMappingAdmin(admin.ModelAdmin):
    """Admin interface for Moodle course mappings."""

    list_display = [
        "sis_course",
        "moodle_course_id",
        "moodle_shortname",
        "moodle_category_id",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "moodle_category_id", "created_at"]
    search_fields = [
        "sis_course__code",
        "sis_course__title",
        "moodle_shortname",
    ]
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("sis_course")


@admin.register(MoodleEnrollmentMapping)
class MoodleEnrollmentMappingAdmin(admin.ModelAdmin):
    """Admin interface for Moodle enrollment mappings."""

    list_display = [
        "sis_enrollment",
        "moodle_enrolment_id",
        "moodle_role_id",
        "role_name",
        "is_active",
        "created_at",
    ]
    list_filter = ["moodle_role_id", "is_active", "created_at"]
    search_fields = [
        "sis_enrollment__student__first_name",
        "sis_enrollment__student__last_name",
    ]
    readonly_fields = ["created_at", "updated_at"]

    def role_name(self, obj):
        """Display human-readable role name."""
        role_map = {3: "Teacher", 5: "Student", 1: "Manager", 2: "Course Creator"}
        return role_map.get(obj.moodle_role_id, f"Role {obj.moodle_role_id}")

    cast("Any", role_name).short_description = "Role"

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return (
            super().get_queryset(request).select_related("sis_enrollment__student", "sis_enrollment__class_instance")
        )


@admin.register(MoodleGradeMapping)
class MoodleGradeMappingAdmin(admin.ModelAdmin):
    """Admin interface for Moodle grade mappings."""

    list_display = [
        "moodle_grade_id",
        "moodle_grade_item_id",
        "last_synced_value",
        "is_active",
        "created_at",
    ]
    list_filter = ["is_active", "created_at"]
    search_fields = ["moodle_grade_id", "moodle_grade_item_id"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(MoodleAPILog)
class MoodleAPILogAdmin(admin.ModelAdmin):
    """Admin interface for Moodle API logs."""

    list_display = [
        "endpoint",
        "method",
        "status_code",
        "execution_time_ms",
        "formatted_execution_time",
        "created_at",
        "has_error",
    ]
    list_filter = ["method", "status_code", "created_at"]
    search_fields = ["endpoint", "error_message"]
    readonly_fields = ["created_at"]
    date_hierarchy = "created_at"

    def formatted_execution_time(self, obj):
        """Display execution time with units."""
        if obj.execution_time_ms < 1000:
            return f"{obj.execution_time_ms}ms"
        else:
            return f"{obj.execution_time_ms / 1000:.2f}s"

    cast("Any", formatted_execution_time).short_description = "Execution Time"

    def has_error(self, obj):
        """Display whether the API call had errors."""
        if obj.error_message:
            return format_html('<span style="color: red;">Yes</span>')
        return format_html('<span style="color: green;">No</span>')

    cast("Any", has_error).short_description = "Error"
    cast("Any", has_error).admin_order_field = "error_message"

    def get_queryset(self, request):
        """Order by most recent first."""
        return super().get_queryset(request).order_by("-created_at")


# Custom admin actions
@admin.action(description="Retry failed syncs")
def retry_failed_syncs(modeladmin, request, queryset):
    """Admin action to retry failed syncs."""
    from .tasks import async_sync_person_to_moodle

    for sync_status in queryset.filter(sync_status="failed"):
        # Trigger retry based on content type
        if sync_status.content_type.model == "person":
            async_sync_person_to_moodle.send(person_id=sync_status.object_id)


# Add the action to MoodleSyncStatus admin
MoodleSyncStatusAdmin.actions = [retry_failed_syncs]
