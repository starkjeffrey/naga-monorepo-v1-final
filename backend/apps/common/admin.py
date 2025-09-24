"""Admin configuration for the common app.

This module configures the Django admin interface for common models
and provides shared admin utilities that other apps can use.

CLEAN ARCHITECTURE BENEFITS:
- Centralized admin utilities and mixins
- Consistent admin interfaces across apps
- No circular dependencies with other apps
- Reusable admin components
"""

from typing import Any, cast

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .admin_audit import StudentActivityLogAdmin
from .models import Holiday, Room, StudentActivityLog, SystemAuditLog


class ReadOnlyAdminMixin:
    """
    Disables all editing capabilities for users in read-only groups.

    This mixin checks if a user belongs to either 'Read-Only Staff' or
    'Read-Only Admin' groups and removes their ability to add, change,
    or delete records while maintaining view permissions.
    """

    # Define the read-only group names
    READ_ONLY_GROUPS = ["Read-Only Staff", "Read-Only Admin"]

    def has_add_permission(self, request):
        """Prevent read-only users from adding new records."""
        if request.user.groups.filter(name__in=self.READ_ONLY_GROUPS).exists():
            return False
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        """
        Allow read-only users to view but not change records.

        Note: We return True here to allow viewing in the admin,
        but the save functionality will be disabled by has_add_permission
        and the readonly fields.
        """
        if request.user.groups.filter(name__in=self.READ_ONLY_GROUPS).exists():
            # Return True to allow viewing, but make all fields readonly
            return True
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        """Prevent read-only users from deleting records."""
        if request.user.groups.filter(name__in=self.READ_ONLY_GROUPS).exists():
            return False
        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        """Make all fields readonly for read-only users."""
        if request.user.groups.filter(name__in=self.READ_ONLY_GROUPS).exists():
            # Get all fields from the model
            if obj:
                return [field.name for field in obj._meta.fields]
            elif self.model:
                return [field.name for field in self.model._meta.fields]
        return super().get_readonly_fields(request, obj)

    def get_actions(self, request):
        """Remove bulk actions for read-only users."""
        actions = super().get_actions(request)
        if request.user.groups.filter(name__in=self.READ_ONLY_GROUPS).exists():
            # Remove all actions including 'delete_selected'
            return {}
        return actions


class FinanceRestrictedMixin:
    """
    Restricts access to finance-related models for 'Read-Only Staff' users.

    This mixin completely hides finance models from users in the 'Read-Only Staff'
    group while allowing 'Read-Only Admin' users to view them.
    """

    def has_module_permission(self, request):
        """Control whether the user can see this app in the admin index."""
        # If user is in Read-Only Staff group, deny access to finance app
        if request.user.groups.filter(name="Read-Only Staff").exists():
            # Check if this is a finance-related model
            if self.model._meta.app_label == "finance":
                return False
        return super().has_module_permission(request)

    def has_view_permission(self, request, obj=None):
        """Control whether the user can view records."""
        # If user is in Read-Only Staff group, deny access to finance models
        if request.user.groups.filter(name="Read-Only Staff").exists():
            if self.model._meta.app_label == "finance":
                return False
        return super().has_view_permission(request, obj)


class TimestampedModelAdmin(admin.ModelAdmin):
    """Base admin class for models that inherit from TimestampedModel.

    Provides consistent handling of created_at and updated_at fields
    across all admin interfaces.
    """

    readonly_fields = ("created_at", "updated_at")

    def get_fieldsets(self, request, obj=None):
        """Add timestamp fields to the end of fieldsets."""
        fieldsets = super().get_fieldsets(request, obj)
        if fieldsets:
            # Add timestamps to the last fieldset
            fieldsets = list(fieldsets)
            last_fieldset = fieldsets[-1]
            if isinstance(last_fieldset[1], dict) and "fields" in last_fieldset[1]:
                fields = list(last_fieldset[1]["fields"])
                fields.extend(["created_at", "updated_at"])
                fieldsets[-1] = (
                    last_fieldset[0],
                    {**last_fieldset[1], "fields": fields},
                )
        return fieldsets


@admin.register(Room)
class RoomAdmin(TimestampedModelAdmin):
    """Admin interface for Room model.

    Provides comprehensive room management with filtering and search
    capabilities for efficient room administration.
    """

    list_display = [
        "building",
        "name",
        "room_type",
        "capacity",
        "has_projector",
        "has_whiteboard",
        "has_computers",
        "is_active",
        "created_at",
    ]

    list_filter = [
        "building",
        "room_type",
        "has_projector",
        "has_whiteboard",
        "has_computers",
        "is_active",
        "created_at",
    ]

    search_fields = [
        "name",
        "building",
        "notes",
    ]

    ordering = ["building", "name"]

    fieldsets = (
        (
            _("Basic Information"),
            {
                "fields": ("building", "name", "room_type", "capacity"),
            },
        ),
        (
            _("Equipment & Features"),
            {
                "fields": (
                    "has_projector",
                    "has_whiteboard",
                    "has_computers",
                ),
            },
        ),
        (
            _("Status & Notes"),
            {
                "fields": ("is_active", "notes"),
            },
        ),
    )


# Register StudentActivityLog with its custom admin
admin.site.register(StudentActivityLog, StudentActivityLogAdmin)


@admin.register(Holiday)
class HolidayAdmin(TimestampedModelAdmin):
    """Admin interface for Holiday model.

    Provides holiday management for academic calendar planning.
    """

    list_display = [
        "eng_name",
        "khmer_name",
        "start_date",
        "end_date",
        "duration_days",
        "is_active",
        "created_at",
    ]

    list_filter = [
        "is_active",
        "start_date",
        "created_at",
    ]

    search_fields = [
        "eng_name",
        "khmer_name",
        "notes",
    ]

    ordering = ["start_date"]

    fieldsets = (
        (
            _("Holiday Information"),
            {
                "fields": ("eng_name", "khmer_name"),
            },
        ),
        (
            _("Dates"),
            {
                "fields": ("start_date", "end_date"),
            },
        ),
        (
            _("Status & Notes"),
            {
                "fields": ("is_active", "notes"),
            },
        ),
    )


@admin.register(SystemAuditLog)
class SystemAuditLogAdmin(admin.ModelAdmin):
    """Admin interface for SystemAuditLog model.

    Provides viewing of system-wide audit logs for management overrides
    and policy exceptions.
    """

    list_display = [
        "created_at",
        "action_type",
        "performed_by",
        "target_info",
        "override_reason_truncated",
        "ip_address",
    ]

    list_filter = [
        "action_type",
        "created_at",
        "performed_by",
    ]

    search_fields = [
        "performed_by__username",
        "performed_by__first_name",
        "performed_by__last_name",
        "override_reason",
        "original_restriction",
        "target_object_id",
    ]

    date_hierarchy = "created_at"

    ordering = ["-created_at"]

    readonly_fields = [
        "created_at",
        "action_type",
        "performed_by",
        "content_type",
        "object_id",
        "content_object",
        "override_reason",
        "original_restriction",
        "override_details",
        "ip_address",
        "user_agent",
    ]

    fieldsets = (
        (
            _("Audit Information"),
            {
                "fields": (
                    "created_at",
                    "action_type",
                    "performed_by",
                ),
            },
        ),
        (
            _("Target Object"),
            {
                "fields": (
                    "content_type",
                    "object_id",
                    "content_object",
                ),
            },
        ),
        (
            _("Override Details"),
            {
                "fields": (
                    "override_reason",
                    "original_restriction",
                    "override_details",
                ),
            },
        ),
        (
            _("Request Information"),
            {
                "fields": (
                    "ip_address",
                    "user_agent",
                ),
                "classes": ["collapse"],
            },
        ),
    )

    def target_info(self, obj):
        """Display target object information."""
        if obj.content_object:
            return f"{obj.content_type} #{obj.object_id}"
        return f"{obj.target_app}.{obj.target_model} #{obj.target_object_id}"

    cast("Any", target_info).short_description = _("Target")

    def override_reason_truncated(self, obj):
        """Truncate long override reasons."""
        if len(obj.override_reason) > 100:
            return obj.override_reason[:100] + "..."
        return obj.override_reason

    cast("Any", override_reason_truncated).short_description = _("Override Reason")

    def has_add_permission(self, request):
        """Prevent manual addition of audit logs."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete audit logs."""
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        """Audit logs are read-only."""
        return False
