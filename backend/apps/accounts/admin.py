"""from datetime import date
Django admin configuration for accounts app.

This module provides comprehensive admin interfaces for managing
departments, roles, permissions, and user role assignments.
All admin classes follow Django best practices with proper
list displays, filters, search capabilities, and inline editing.
"""

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import models
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import Department, Permission, Role, RolePermission, UserRole

User = get_user_model()


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """Admin interface for Department model."""

    list_display = [
        "name",
        "code",
        "display_order",
        "is_active",
        "role_count",
        "user_count",
        "created_at",
    ]
    list_filter = ["is_active", "created_at"]
    search_fields = ["name", "code", "description"]
    ordering = ["display_order", "name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            None,
            {
                "fields": ("name", "code", "description"),
            },
        ),
        (
            _("Settings"),
            {
                "fields": ("is_active", "display_order"),
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description=_("Active Roles"))
    def role_count(self, obj: Department) -> int:
        """Count of roles in this department."""
        return obj.roles.filter(is_active=True).count()  # type: ignore[attr-defined]

    @admin.display(description=_("Active Users"))
    def user_count(self, obj: Department) -> int:
        """Count of users assigned to this department."""
        return obj.user_roles.filter(is_active=True).values("user").distinct().count()  # type: ignore[attr-defined]


class RolePermissionInline(admin.TabularInline):
    """Inline admin for role permissions."""

    model = RolePermission
    extra = 0
    fields = ["permission", "department", "is_active", "notes"]
    autocomplete_fields = ["permission", "department"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin interface for Role model."""

    list_display = [
        "name",
        "role_type",
        "department",
        "parent_role",
        "permission_flags",
        "is_active",
        "user_count",
        "created_at",
    ]
    list_filter = [
        "role_type",
        "is_active",
        "can_approve",
        "can_edit",
        "can_view",
        "department",
        "created_at",
    ]
    search_fields = ["name", "description", "role_type"]
    ordering = ["department", "role_type", "name"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["department", "parent_role"]
    inlines = [RolePermissionInline]

    fieldsets = (
        (
            None,
            {
                "fields": ("name", "role_type", "department", "description"),
            },
        ),
        (
            _("Hierarchy"),
            {
                "fields": ("parent_role",),
                "description": _("Set parent role for permission inheritance"),
            },
        ),
        (
            _("Permissions"),
            {
                "fields": ("can_approve", "can_edit", "can_view"),
                "description": _("Basic permission flags for this role"),
            },
        ),
        (
            _("Settings"),
            {
                "fields": ("is_active",),
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description=_("Permission Flags"))
    def permission_flags(self, obj: Role) -> str:
        """Display permission flags as badges."""
        flags = []
        if obj.can_approve:
            flags.append('<span class="badge badge-success">Approve</span>')
        if obj.can_edit:
            flags.append('<span class="badge badge-info">Edit</span>')
        if obj.can_view:
            flags.append('<span class="badge badge-secondary">View</span>')
        return format_html(" ".join(flags)) if flags else "-"

    @admin.display(description=_("Active Users"))
    def user_count(self, obj: Role) -> int:
        """Count of users assigned to this role."""
        return getattr(obj, "user_assignments").filter(is_active=True).count()

    def get_queryset(self, request: HttpRequest):
        """Optimize queryset with select_related."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "department",
                "parent_role",
            )
        )


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    """Admin interface for UserRole model."""

    list_display = [
        "user",
        "role",
        "department",
        "is_active",
        "assigned_date",
        "role_type_display",
    ]
    list_filter = [
        "is_active",
        "role__role_type",
        "department",
        "assigned_date",
        "role__is_active",
    ]
    search_fields = [
        "user__email",
        "user__first_name",
        "user__last_name",
        "role__name",
        "department__name",
        "department__code",
    ]
    ordering = ["-assigned_date"]
    readonly_fields = ["assigned_date", "created_at", "updated_at"]
    autocomplete_fields = ["user", "role", "department"]

    fieldsets = (
        (
            None,
            {
                "fields": ("user", "role", "department"),
            },
        ),
        (
            _("Status"),
            {
                "fields": ("is_active", "assigned_date"),
            },
        ),
        (
            _("Notes"),
            {
                "fields": ("notes",),
                "classes": ("collapse",),
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description=_("Role Type"))
    def role_type_display(self, obj: UserRole) -> str:
        """Display role type with styling."""
        role_type = obj.role.role_type
        css_class = {
            "DIRECTOR": "badge-danger",
            "HEAD": "badge-warning",
            "SUPERVISOR": "badge-info",
            "TEACHER": "badge-success",
            "STAFF": "badge-secondary",
            "STUDENT": "badge-primary",
            "PARENT": "badge-light",
            "EXTERNAL": "badge-dark",
        }.get(role_type, "badge-secondary")

        return format_html(
            '<span class="badge {}">{}</span>',
            css_class,
            getattr(obj.role, "get_role_type_display", lambda: obj.role.role_type)(),
        )

    def get_queryset(self, request: HttpRequest):
        """Optimize queryset with select_related."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "user",
                "role",
                "department",
            )
        )


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Admin interface for Permission model."""

    list_display = [
        "name",
        "codename",
        "content_type",
        "is_active",
        "role_count",
        "created_at",
    ]
    list_filter = ["is_active", "content_type", "created_at"]
    search_fields = ["name", "codename", "description"]
    ordering = ["content_type", "name"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            None,
            {
                "fields": ("name", "codename", "content_type"),
            },
        ),
        (
            _("Description"),
            {
                "fields": ("description",),
            },
        ),
        (
            _("Settings"),
            {
                "fields": ("is_active",),
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description=_("Active Role Assignments"))
    def role_count(self, obj: Permission) -> int:
        """Count of roles that have this permission."""
        return getattr(obj, "role_assignments").filter(is_active=True).count()


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    """Admin interface for RolePermission model."""

    list_display = [
        "role",
        "permission",
        "department",
        "is_object_level",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "is_active",
        "role__role_type",
        "department",
        "permission__content_type",
        "created_at",
    ]
    search_fields = [
        "role__name",
        "permission__name",
        "permission__codename",
        "department__name",
        "notes",
    ]
    ordering = ["role", "permission"]
    readonly_fields = ["created_at", "updated_at"]
    autocomplete_fields = ["role", "permission", "department"]

    fieldsets = (
        (
            None,
            {
                "fields": ("role", "permission", "department"),
            },
        ),
        (
            _("Object-Level Permissions"),
            {
                "fields": ("content_type", "object_id"),
                "description": _(
                    "Optional: Restrict this permission to a specific object instance",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Status"),
            {
                "fields": ("is_active",),
            },
        ),
        (
            _("Notes"),
            {
                "fields": ("notes",),
                "classes": ("collapse",),
            },
        ),
        (
            _("Timestamps"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(
        description=_("Object Level"),
        boolean=True,
    )
    def is_object_level(self, obj: RolePermission) -> bool:
        """Check if this is an object-level permission."""
        return obj.is_object_level

    def get_queryset(self, request: HttpRequest):
        """Optimize queryset with select_related."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "role",
                "permission",
                "department",
                "content_type",
            )
        )


# Custom admin actions


@admin.action(description=_("Activate selected items"))
def activate_items(
    modeladmin: admin.ModelAdmin,
    request: HttpRequest,
    queryset: models.QuerySet,
) -> None:
    """Admin action to activate selected items."""
    updated = queryset.update(is_active=True)
    modeladmin.message_user(
        request,
        _("Successfully activated {} items.").format(updated),
    )


@admin.action(description=_("Deactivate selected items"))
def deactivate_items(
    modeladmin: admin.ModelAdmin,
    request: HttpRequest,
    queryset: models.QuerySet,
) -> None:
    """Admin action to deactivate selected items."""
    updated = queryset.update(is_active=False)
    modeladmin.message_user(
        request,
        _("Successfully deactivated {} items.").format(updated),
    )


# Add actions to all relevant admin classes
# Add common actions to admin classes using setattr to avoid mypy generic class access issues
for admin_cls in [
    DepartmentAdmin,
    RoleAdmin,
    UserRoleAdmin,
    PermissionAdmin,
    RolePermissionAdmin,
]:
    admin_cls.actions = [activate_items, deactivate_items]


# Customize admin site
admin.site.site_header = _("Naga SIS Administration")
admin.site.site_title = _("Naga SIS Admin")
admin.site.index_title = _("Welcome to Naga SIS Administration")
