"""Admin mixins for common functionality across Django admin interfaces.

These mixins provide reusable functionality without requiring changes
to existing admin class implementations.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


class SidebarToggleMixin:
    """Mixin to add a toggle button that collapses the entire filter sidebar.

    This gives more horizontal space to the main data table by hiding
    the filter column when not needed.

    Usage:
        class MyModelAdmin(SidebarToggleMixin, admin.ModelAdmin):
            list_filter = ['field1', 'field2', 'field3']

    Features:
    - Toggle button on the right side of screen
    - Keyboard shortcut: Ctrl+B (or Cmd+B on Mac)
    - Remembers collapsed state using localStorage
    - Simple hide/show without layout interference
    """

    class Media:
        css = {"all": ("admin/css/simple_sidebar_toggle.css",)}
        js = ("admin/js/sidebar_toggle.js",)


class CollapsibleFilterMixin:
    """Mixin to add collapsible filters to Django admin changelist pages.

    Simply inherit from this mixin to enable collapsible filter sections:

    Usage:
        class MyModelAdmin(CollapsibleFilterMixin, admin.ModelAdmin):
            list_filter = ['field1', 'field2', 'field3']

    Features:
    - Click any filter section header to collapse/expand
    - Remembers collapsed state using localStorage
    - Responsive design (auto-collapses on mobile)
    - Keyboard accessible (Enter/Space to toggle)
    - No code changes required for existing admin classes
    """

    class Media:
        css = {"all": ("admin/css/collapsible_filters.css",)}
        js = ("admin/js/collapsible_filters.js",)


class CompactAdminMixin:
    """Mixin to provide more compact admin interface styling.

    Reduces padding and font sizes for a denser information display.
    Useful for admin interfaces with lots of data.

    Usage:
        class MyModelAdmin(CompactAdminMixin, admin.ModelAdmin):
            list_display = ['field1', 'field2', 'field3']
    """

    class Media:
        css = {"all": ("admin/css/compact_admin.css",)}


class EnhancedAdminMixin(SidebarToggleMixin, CollapsibleFilterMixin, CompactAdminMixin):
    """Combined mixin that provides sidebar toggle, collapsible filters, and compact styling.

    Best choice for admin interfaces that need maximum space-saving features.

    Usage:
        class MyModelAdmin(EnhancedAdminMixin, admin.ModelAdmin):
            list_filter = ['field1', 'field2']
            list_display = ['field1', 'field2', 'field3']

    Features:
    - Sidebar toggle button (collapse entire filter column)
    - Individual filter section collapse/expand
    - Compact styling for dense information display
    - Keyboard shortcuts and responsive design
    """

    class Media:
        css = {
            "all": (
                "admin/css/simple_sidebar_toggle.css",
                "admin/css/collapsible_filters.css",
                "admin/css/compact_admin.css",
            ),
        }
        js = (
            "admin/js/sidebar_toggle.js",
            "admin/js/collapsible_filters.js",
        )


class UltraCompactMixin:
    """Ultra-compact admin styling for maximum data density.

    Dramatically reduces padding, font sizes, and spacing to fit
    much more data on screen without any code changes.

    Note: Student ID formatting is now handled globally by the admin base template.

    Usage:
        class MyModelAdmin(UltraCompactMixin, admin.ModelAdmin):
            list_display = ['field1', 'field2', 'field3']
    """

    class Media:
        css = {"all": ("admin/css/ultra_compact.css",)}


class SpaceSaverMixin(SidebarToggleMixin, CompactAdminMixin):
    """Mixin that provides sidebar toggle and compact styling without individual filter collapse.

    Good choice when you want maximum table space but don't need individual filter collapsing.

    Usage:
        class MyModelAdmin(SpaceSaverMixin, admin.ModelAdmin):
            list_filter = ['field1', 'field2']
            list_display = ['field1', 'field2', 'field3']
    """

    class Media:
        css = {
            "all": (
                "admin/css/simple_sidebar_toggle.css",
                "admin/css/compact_admin.css",
            ),
        }
        js = ("admin/js/sidebar_toggle.js",)


class MaximumDataMixin(SidebarToggleMixin, UltraCompactMixin):
    """Maximum data visibility mixin - combines sidebar toggle with ultra-compact styling.

    Perfect for data-heavy admin pages where you need to see as much as possible.

    Usage:
        class MyModelAdmin(MaximumDataMixin, admin.ModelAdmin):
            list_filter = ['field1', 'field2']
            list_display = ['field1', 'field2', 'field3']

    Features:
    - Collapsible sidebar for full-width table
    - Ultra-compact styling for maximum data density
    - Responsive design for different screen sizes
    """

    class Media:
        css = {
            "all": (
                "admin/css/simple_sidebar_toggle.css",
                "admin/css/ultra_compact.css",
            ),
        }
        js = ("admin/js/sidebar_toggle.js",)


class ComprehensiveAuditMixin:
    """Admin mixin that adds a collapsed audit trail fieldset for UserAuditModel instances.

    This mixin automatically adds an "Audit Trail" fieldset that shows:
    - Created by and creation date
    - Updated by and last update date
    - Soft delete information (if applicable)

    The fieldset is collapsed by default to avoid cluttering the interface
    but provides full audit transparency when expanded.

    Usage:
        class MyModelAdmin(ComprehensiveAuditMixin, admin.ModelAdmin):
            list_display = ['name', 'created_by_display', 'updated_by_display']
    """

    def get_readonly_fields(self, request, obj=None):
        """Add audit fields to readonly fields."""
        readonly_fields = list(super().get_readonly_fields(request, obj))

        # Add audit fields that should always be readonly
        audit_fields = [
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
            "is_deleted",
            "deleted_at",
        ]

        # Only add fields that exist on the model
        if obj:
            for field in audit_fields:
                if hasattr(obj, field) and field not in readonly_fields:
                    readonly_fields.append(field)

        return readonly_fields

    def get_fieldsets(self, request, obj=None):
        """Add audit trail fieldset to existing fieldsets."""
        fieldsets = list(super().get_fieldsets(request, obj))

        # Only add audit fieldset if object exists (not for new objects)
        if obj and hasattr(obj, "created_at"):
            audit_fieldset = (
                _("🔍 Audit Trail"),
                {
                    "classes": ("collapse",),
                    "fields": self._get_audit_fields(obj),
                    "description": _("Track who created and modified this record. Click to expand."),
                },
            )
            fieldsets.append(audit_fieldset)

        return fieldsets

    def _get_audit_fields(self, obj):
        """Get available audit fields for the object."""
        fields = []

        # Creation audit
        if hasattr(obj, "created_at"):
            fields.append("created_at")
        if hasattr(obj, "created_by"):
            fields.append("created_by")

        # Update audit
        if hasattr(obj, "updated_at"):
            fields.append("updated_at")
        if hasattr(obj, "updated_by"):
            fields.append("updated_by")

        # Soft delete audit
        if hasattr(obj, "is_deleted"):
            fields.append("is_deleted")
        if hasattr(obj, "deleted_at"):
            fields.append("deleted_at")

        return fields

    @admin.display(description=_("Created By"))
    def created_by_display(self, obj):
        """Display created by user with formatting."""
        if not hasattr(obj, "created_by"):
            return "-"
        if obj.created_by:
            return format_html(
                "<strong>{}</strong><br><small>{}</small>",
                obj.created_by.get_full_name() or obj.created_by.email,
                obj.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            )
        return format_html("<em>{}</em>", _("System"))

    @admin.display(description=_("Last Updated By"))
    def updated_by_display(self, obj):
        """Display updated by user with formatting."""
        if not hasattr(obj, "updated_by"):
            return "-"
        if obj.updated_by:
            return format_html(
                "<strong>{}</strong><br><small>{}</small>",
                obj.updated_by.get_full_name() or obj.updated_by.email,
                obj.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            )
        return format_html("<em>{}</em>", _("System"))

    def save_model(self, request, obj, form, change):
        """Automatically set created_by and updated_by fields."""
        if hasattr(obj, "created_by") and not obj.created_by:
            obj.created_by = request.user
        if hasattr(obj, "updated_by"):
            obj.updated_by = request.user
        super().save_model(request, obj, form, change)


class AuditListMixin:
    """Admin mixin that adds audit information to list displays.

    This mixin adds columns for created_by and updated_by to list views,
    allowing administrators to quickly see who made changes.

    Usage:
        class MyModelAdmin(AuditListMixin, admin.ModelAdmin):
            list_display = ['name', 'created_by_display', 'updated_by_display']
    """

    def get_list_display(self, request):
        """Add audit columns to list display."""
        list_display = list(super().get_list_display(request))

        # Add audit columns if not already present
        if "created_by_display" not in list_display:
            list_display.append("created_by_display")
        if "updated_by_display" not in list_display:
            list_display.append("updated_by_display")

        return list_display

    def get_list_filter(self, request):
        """Add audit filters to list filters."""
        list_filter = list(super().get_list_filter(request))

        # Add audit filters if not already present
        audit_filters = ["created_by", "updated_by", "created_at", "updated_at"]
        for filter_field in audit_filters:
            if filter_field not in list_filter:
                list_filter.append(filter_field)

        return list_filter


class FullAuditMixin(ComprehensiveAuditMixin, AuditListMixin):
    """Complete audit mixin that combines both detail and list audit functionality.

    This mixin provides:
    - Audit trail fieldset in detail views (collapsed by default)
    - Audit columns in list views
    - Audit filters in list views
    - Automatic user assignment on save

    Usage:
        class MyModelAdmin(FullAuditMixin, admin.ModelAdmin):
            list_display = ['name', 'status']
            list_filter = ['status']
    """

    pass
