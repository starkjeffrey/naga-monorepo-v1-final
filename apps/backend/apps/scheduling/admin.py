"""Scheduling app Django admin configuration with enhanced forms and actions.

This module provides administrative interfaces for scheduling models including:
- Class scheduling and management with bulk operations
- Combined course template configuration with validation
- Reading class tier management and bulk conversions
- Test period reset automation and scheduling
- Room and teacher assignment workflows

Key features:
- Custom forms with business rule validation
- Bulk operations for efficient scheduling workflows
- Permission-based access control for sensitive operations
- Advanced filtering and search for large datasets
- Inline editing for related scheduling components
"""

from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import models
from django.forms import CheckboxSelectMultiple
from django.utils.translation import gettext_lazy as _

from .models import (
    ClassHeader,
    ClassPart,
    ClassSession,
    CombinedClassGroup,
    CombinedClassInstance,
    CombinedCourseTemplate,
    ReadingClass,
    TestPeriodReset,
)
from .models_templates import (
    ClassPartTemplate,
    ClassPartTemplateSet,
    ClassPromotionRule,
)
from .services import (
    ReadingClassService,
    SchedulingPermissionService,
    TestPeriodResetService,
)

# ========== INTEGRITY-AWARE INLINES ==========


class ClassPartInline(admin.TabularInline):
    """Inline for managing ClassParts within ClassSessions."""

    model = ClassPart
    extra = 1
    fields = [
        "class_part_code",
        "class_part_type",
        "teacher",
        "room",
        "meeting_days",
        "start_time",
        "end_time",
        "grade_weight",
    ]

    def get_queryset(self, request):
        """Ensure parts are properly ordered."""
        qs = super().get_queryset(request)
        return qs.order_by("class_part_code")


class ClassSessionInline(admin.TabularInline):
    """Inline for managing ClassSessions within ClassHeaders with integrity awareness."""

    model = ClassSession
    extra = 0
    fields = ["session_number", "session_name", "grade_weight"]

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of required sessions."""
        if obj:  # obj is the ClassHeader
            if not obj.is_ieap_class():
                return False  # Can't delete the single session
            # For IEAP, could add logic to prevent going below 2 sessions
        return super().has_delete_permission(request, obj)

    def get_extra(self, request, obj=None, **kwargs):
        """Provide correct number of extra forms."""
        if obj:
            if obj.is_ieap_class() and obj.class_sessions.count() < 2:
                return 2 - obj.class_sessions.count()
            elif not obj.is_ieap_class() and obj.class_sessions.count() < 1:
                return 1
        return 0


class CombinedCourseTemplateForm(forms.ModelForm):
    """Custom form for CombinedCourseTemplate with proper validation."""

    class Meta:
        model = CombinedCourseTemplate
        fields = ["name", "courses", "description", "status", "created_by", "notes"]

    def clean_courses(self):
        """Validate that at least 2 courses are selected."""
        courses = self.cleaned_data.get("courses")

        # Handle both QuerySet and list cases for M2M fields
        if courses:
            # If it's a QuerySet, use count()
            if hasattr(courses, "count"):
                course_count = courses.count()
            # If it's a list/iterable (common in forms), use len()
            else:
                course_count = len(courses)

            if course_count < 2:
                raise ValidationError(_("A combination must include at least 2 courses."))
        return courses

    def clean(self):
        """Additional validation for active templates."""
        cleaned_data = super().clean()
        if not cleaned_data:
            return cleaned_data
        courses = cleaned_data.get("courses")
        status = cleaned_data.get("status")

        if status == CombinedCourseTemplate.StatusChoices.ACTIVE and courses:
            # Handle both QuerySet and list cases for M2M fields
            if hasattr(courses, "count"):
                course_count = courses.count()
            else:
                course_count = len(courses)

            # Skip overlap check if we don't have enough courses
            if course_count >= 2:
                overlapping_templates = (
                    CombinedCourseTemplate.objects.filter(
                        status=CombinedCourseTemplate.StatusChoices.ACTIVE,
                        is_deleted=False,
                        courses__in=courses,
                    )
                    .exclude(pk=self.instance.pk if self.instance and self.instance.pk else 0)
                    .distinct()
                )

                if overlapping_templates.exists():
                    overlapping_names = list(overlapping_templates.values_list("name", flat=True))
                    raise ValidationError(
                        {
                            "courses": _(
                                f"Some courses are already in active templates: {', '.join(overlapping_names)}",
                            ),
                        },
                    )

        return cleaned_data


@admin.register(CombinedCourseTemplate)
class CombinedCourseTemplateAdmin(admin.ModelAdmin):
    """Admin interface for course combination templates."""

    form = CombinedCourseTemplateForm
    list_display = [
        "name",
        "course_count",
        "course_codes",
        "status",
        "active_instances_count",
        "created_by",
        "created_at",
    ]
    list_filter = ["status", "created_at", "created_by"]
    search_fields = ["name", "description", "courses__code", "courses__title"]
    filter_horizontal = ["courses"]
    raw_id_fields = ["created_by"]
    readonly_fields = [
        "course_count",
        "active_instances_count",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            "Template Configuration",
            {
                "fields": ("name", "description", "status"),
                "description": "Basic template information and status.",
            },
        ),
        (
            "Course Selection",
            {
                "fields": ("courses", "course_count"),
                "description": (
                    "Select courses that should always be scheduled together. "
                    "Choose 2-3 courses that will share the same teacher and room."
                ),
            },
        ),
        (
            "Administrative",
            {
                "fields": ("created_by", "notes", "active_instances_count"),
                "classes": ("collapse",),
            },
        ),
        (
            "Audit Information",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["activate_templates", "deactivate_templates", "preview_combinations"]

    @admin.action(description="Activate selected templates")
    def activate_templates(self, request, queryset):
        """Activate selected course combination templates."""
        # Check permissions
        if not request.user.has_perm("scheduling.can_manage_course_combinations"):
            msg = "You don't have permission to manage course combination templates."
            raise PermissionDenied(msg)

        updated = queryset.update(status=CombinedCourseTemplate.StatusChoices.ACTIVE)
        self.message_user(
            request,
            f"Activated {updated} course combination templates.",
            messages.SUCCESS,
        )

    @admin.action(description="Deactivate selected templates")
    def deactivate_templates(self, request, queryset):
        """Deactivate selected course combination templates."""
        # Check permissions
        if not request.user.has_perm("scheduling.can_manage_course_combinations"):
            msg = "You don't have permission to manage course combination templates."
            raise PermissionDenied(msg)

        updated = queryset.update(status=CombinedCourseTemplate.StatusChoices.INACTIVE)
        self.message_user(
            request,
            f"Deactivated {updated} course combination templates.",
            messages.SUCCESS,
        )

    @admin.action(description="Preview course combinations")
    def preview_combinations(self, request, queryset):
        """Show a preview of course combinations."""
        preview_data = []
        for template in queryset:
            courses = list(template.courses.values_list("code", flat=True))
            preview_data.append(f"{template.name}: {', '.join(courses)}")

        preview_text = "\n".join(preview_data)
        self.message_user(
            request,
            f"Course Combinations Preview:\n{preview_text}",
            messages.INFO,
        )

    def save_model(self, request, obj, form, change):
        """Set created_by field on new objects."""
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class CombinedClassInstanceInline(admin.TabularInline):
    """Inline for showing member ClassHeaders in CombinedClassInstance."""

    model = ClassHeader
    fk_name = "combined_class_instance"
    fields = ["course", "section_id", "status", "enrollment_count"]
    readonly_fields = ["course", "section_id", "status", "enrollment_count"]
    extra = 0
    can_delete = False
    max_num = 0  # No adding new ones through inline

    def has_add_permission(self, request, obj=None):
        """Prevent adding new ClassHeaders through this inline."""
        return False


@admin.register(CombinedClassInstance)
class CombinedClassInstanceAdmin(admin.ModelAdmin):
    """Admin interface for combined class instances."""

    list_display = [
        "template",
        "term",
        "section_id",
        "status",
        "member_count",
        "total_enrollment",
        "primary_teacher",
        "primary_room",
        "is_fully_scheduled",
    ]
    list_filter = [
        "status",
        "term",
        "template",
        "primary_teacher",
        "auto_created",
    ]
    search_fields = [
        "template__name",
        "term__code",
        "notes",
        "primary_teacher__person__family_name",
        "primary_room__name",
    ]
    raw_id_fields = ["template", "term", "primary_teacher", "primary_room"]
    readonly_fields = [
        "member_count",
        "total_enrollment",
        "course_codes",
        "is_fully_scheduled",
        "auto_created",
        "created_at",
        "updated_at",
    ]
    inlines = [CombinedClassInstanceInline]

    fieldsets = (
        (
            "Instance Configuration",
            {
                "fields": ("template", "term", "section_id", "status"),
                "description": "Basic instance configuration. Template and term are set when the instance is created.",
            },
        ),
        (
            "Shared Resources",
            {
                "fields": ("primary_teacher", "primary_room"),
                "description": (
                    "Teacher and room shared by all courses in this combination. "
                    "These will be applied to all member ClassParts."
                ),
            },
        ),
        (
            "Instance Status",
            {
                "fields": (
                    "member_count",
                    "course_codes",
                    "total_enrollment",
                    "max_enrollment",
                    "is_fully_scheduled",
                ),
                "description": "Current status and enrollment information.",
            },
        ),
        (
            "Administrative",
            {
                "fields": ("notes", "auto_created"),
                "classes": ("collapse",),
            },
        ),
        (
            "Audit Information",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["apply_shared_resources", "activate_instances", "complete_instances"]

    @admin.action(description="Apply shared resources to all member class parts")
    def apply_shared_resources(self, request, queryset):
        """Apply shared teacher/room to all member ClassParts."""
        # Check permissions
        if not request.user.has_perm("scheduling.can_manage_combined_instances"):
            msg = "You don't have permission to manage combined class instances."
            raise PermissionDenied(msg)

        total_updated = 0
        for instance in queryset:
            if instance.primary_teacher or instance.primary_room:
                updated = instance.apply_shared_resources_to_parts()
                total_updated += updated

        self.message_user(
            request,
            f"Applied shared resources to {total_updated} class parts across {queryset.count()} instances.",
            messages.SUCCESS,
        )

    @admin.action(description="Activate selected instances")
    def activate_instances(self, request, queryset):
        """Activate selected combined class instances."""
        updated = queryset.update(status=CombinedClassInstance.StatusChoices.ACTIVE)
        self.message_user(request, f"Activated {updated} combined class instances.", messages.SUCCESS)

    @admin.action(description="Mark selected instances as completed")
    def complete_instances(self, request, queryset):
        """Mark selected instances as completed."""
        updated = queryset.update(status=CombinedClassInstance.StatusChoices.COMPLETED)
        self.message_user(request, f"Marked {updated} instances as completed.", messages.SUCCESS)


@admin.register(CombinedClassGroup)
class CombinedClassGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "term", "member_count", "created_at"]
    list_filter = ["term", "created_at"]
    search_fields = ["name", "description"]
    filter_horizontal = []


@admin.register(ClassHeader)
class ClassHeaderAdmin(admin.ModelAdmin):
    list_display = [
        "course",
        "section_id",
        "term",
        "class_type",
        "status",
        "time_of_day",
        "is_combined",
        "combined_course_codes",
        "get_session_count",
        "get_part_count",
    ]
    list_filter = [
        "term",
        "class_type",
        "status",
        "time_of_day",
        "is_paired",
        "combined_class_instance",
    ]
    search_fields = ["course__code", "course__name", "section_id"]
    raw_id_fields = [
        "course",
        "term",
        "combined_class_instance",
        "paired_with",
    ]
    readonly_fields = [
        "is_combined",
        "combined_course_codes",
        "shared_teacher",
        "shared_room",
        "enrollment_count",
        "available_spots",
        "get_session_count",
        "get_part_count",
    ]
    inlines = [ClassSessionInline]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "course",
                    "term",
                    "section_id",
                    "class_type",
                    "status",
                    "time_of_day",
                ),
            },
        ),
        (
            "Combined Class Information",
            {
                "fields": (
                    "combined_class_instance",
                    "is_combined",
                    "combined_course_codes",
                    "shared_teacher",
                    "shared_room",
                ),
                "description": (
                    "Information about course combinations. When a class is part of a combination, "
                    "it shares teacher and room with other courses."
                ),
            },
        ),
        (
            "Session Structure",
            {
                "fields": ("get_session_count", "get_part_count"),
                "description": "Class structure info. Regular classes have 1 session, IEAP classes have 2 sessions.",
            },
        ),
        (
            "Legacy Pairing (Deprecated)",
            {
                "fields": ("is_paired", "paired_with"),
                "classes": ("collapse",),
                "description": "Legacy pairing system. Use Combined Class Instances instead.",
            },
        ),
        (
            "Enrollment",
            {
                "fields": ("max_enrollment", "enrollment_count", "available_spots"),
            },
        ),
        (
            "Additional Information",
            {
                "fields": ("notes", "legacy_class_id"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_session_count(self, obj):
        """Get count of sessions for this class."""
        return obj.class_sessions.count()

    get_session_count.short_description = "Sessions"  # type: ignore[attr-defined]

    def get_part_count(self, obj):
        """Get total count of parts across all sessions."""
        return sum(s.class_parts.count() for s in obj.class_sessions.all())

    get_part_count.short_description = "Total Parts"  # type: ignore[attr-defined]

    def save_model(self, request, obj, form, change):
        """Ensure integrity after saving."""
        super().save_model(request, obj, form, change)
        obj.ensure_sessions_exist()

    def save_related(self, request, form, formsets, change):
        """Validate structure after saving related objects."""
        super().save_related(request, form, formsets, change)

        # Validate the structure
        validation = form.instance.validate_session_structure()
        if not validation["valid"]:
            # Show errors to the user
            for error in validation["errors"]:
                self.message_user(request, f"Structure Error: {error}", level=messages.ERROR)

        # Show warnings if any
        for warning in validation.get("warnings", []):
            self.message_user(request, f"Structure Warning: {warning}", level=messages.WARNING)

    def get_queryset(self, request):
        """Optimize queryset with select_related for better performance."""
        return super().get_queryset(request).select_related("course", "term", "combined_class_instance", "paired_with")


@admin.register(ClassSession)
class ClassSessionAdmin(admin.ModelAdmin):
    list_display = [
        "class_header",
        "session_number",
        "session_name",
        "grade_weight",
        "get_part_count",
    ]
    list_filter = ["session_number", "grade_weight"]
    search_fields = ["class_header__course__code", "session_name"]
    raw_id_fields = ["class_header"]
    readonly_fields = ["is_ieap_session", "get_part_count"]
    exclude = ["internal_session_id"]
    inlines = [ClassPartInline]

    def get_part_count(self, obj):
        """Get count of parts in this session."""
        return obj.class_parts.count()

    get_part_count.short_description = "Parts"  # type: ignore[attr-defined]

    def save_model(self, request, obj, form, change):
        """Ensure session has appropriate parts."""
        super().save_model(request, obj, form, change)
        obj.ensure_parts_exist()

    def save_related(self, request, form, formsets, change):
        """Validate parts structure after saving related objects."""
        super().save_related(request, form, formsets, change)

        # Validate the parts structure
        validation = form.instance.validate_parts_structure()
        if not validation["valid"]:
            # Show errors to the user
            for error in validation["errors"]:
                self.message_user(request, f"Parts Error: {error}", level=messages.ERROR)

        # Show warnings if any
        for warning in validation.get("warnings", []):
            self.message_user(request, f"Parts Warning: {warning}", level=messages.WARNING)


@admin.register(ClassPart)
class ClassPartAdmin(admin.ModelAdmin):
    list_display = [
        "class_session",
        "class_part_type",
        "class_part_code",
        "teacher",
        "room",
        "meeting_days",
        "start_time",
        "end_time",
    ]
    list_filter = [
        "class_part_type",
        "start_time",
        "meeting_days",
        "class_session__class_header__term",
    ]
    search_fields = [
        "class_session__class_header__course__code",
        "name",
        "teacher__person__family_name",
        "teacher__person__personal_name",
        "teacher__person__full_name",
        "room__name",
    ]
    raw_id_fields = ["class_session", "teacher", "room"]
    filter_horizontal = ["textbooks"]
    readonly_fields = ["class_header", "duration_minutes", "enrollment_count"]
    exclude = ["internal_part_id"]


@admin.register(ReadingClass)
class ReadingClassAdmin(admin.ModelAdmin):
    list_display = [
        "class_header",
        "tier",
        "target_enrollment",
        "enrollment_status",
        "enrollment_count",
    ]
    list_filter = ["tier", "enrollment_status"]
    search_fields = ["class_header__course__code", "description"]
    raw_id_fields = ["class_header"]
    readonly_fields = ["enrollment_count", "can_convert_to_standard"]

    actions = ["update_tier", "convert_to_standard"]

    @admin.action(description="Update tier based on enrollment")
    def update_tier(self, request, queryset):
        # Check permissions
        if not SchedulingPermissionService.can_manage_reading_classes(request.user):
            msg = "You don't have permission to manage reading class tiers."
            raise PermissionDenied(msg)

        try:
            updated = ReadingClassService.bulk_update_tiers(queryset)
            self.message_user(request, f"Updated {updated} reading class tiers.", messages.SUCCESS)
        except Exception as e:
            self.message_user(request, f"Error updating tiers: {e}", messages.ERROR)

    @admin.action(description="Convert eligible classes to standard")
    def convert_to_standard(self, request, queryset):
        # Check permissions
        if not SchedulingPermissionService.can_manage_reading_classes(request.user):
            msg = "You don't have permission to convert reading classes."
            raise PermissionDenied(msg)

        try:
            converted = ReadingClassService.bulk_convert_to_standard(queryset, user=request.user)
            self.message_user(
                request,
                f"Converted {converted} reading classes to standard.",
                messages.SUCCESS,
            )
        except Exception as e:
            self.message_user(request, f"Error converting classes: {e}", messages.ERROR)


@admin.register(TestPeriodReset)
class TestPeriodResetAdmin(admin.ModelAdmin):
    """Admin interface for test period reset management with bulk entry support."""

    list_display = [
        "term",
        "test_type",
        "reset_date",
        "applies_to_all_language_classes",
        "applicable_classes_count",
        "created_at",
    ]
    list_filter = [
        "term",
        "test_type",
        "applies_to_all_language_classes",
        "reset_date",
        "created_at",
    ]
    search_fields = ["term__code", "notes", "specific_classes__course__code"]
    date_hierarchy = "reset_date"
    raw_id_fields = ["term"]
    filter_horizontal = ["specific_classes"]
    readonly_fields = ["applicable_classes_count", "created_at", "updated_at"]

    fieldsets = (
        (
            "Reset Configuration",
            {"fields": ("term", "test_type", "reset_date", "notes")},
        ),
        (
            "Class Application",
            {
                "fields": (
                    "applies_to_all_language_classes",
                    "specific_classes",
                    "applicable_classes_count",
                ),
                "description": (
                    "Configure which classes this reset applies to. "
                    "Use 'All Language Classes' for bulk entry (recommended)."
                ),
            },
        ),
        (
            "Audit Information",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    # Use checkboxes for better UX with many classes
    formfield_overrides = {
        models.ManyToManyField: {"widget": CheckboxSelectMultiple},
    }

    actions = ["duplicate_to_next_term", "create_standard_test_schedule"]

    @admin.action(description="Duplicate selected resets to next term")
    def duplicate_to_next_term(self, request, queryset):
        """Duplicate reset schedules to the next term with proper date adjustment."""
        # Check permissions
        if not SchedulingPermissionService.can_manage_test_resets(request.user):
            msg = "You don't have permission to manage test period resets."
            raise PermissionDenied(msg)

        try:
            duplicated = TestPeriodResetService.duplicate_resets_to_next_term(queryset)
            if duplicated > 0:
                self.message_user(
                    request,
                    f"Duplicated {duplicated} reset schedules to next term with adjusted dates.",
                    messages.SUCCESS,
                )
            else:
                self.message_user(
                    request,
                    "No resets could be duplicated. Check if next terms exist.",
                    messages.WARNING,
                )
        except Exception as e:
            self.message_user(request, f"Error duplicating resets: {e}", messages.ERROR)

    @admin.action(description="Create standard test schedule for term")
    def create_standard_test_schedule(self, request, queryset):
        """Create standard midterm and final schedule for selected terms."""
        # Check permissions
        if not SchedulingPermissionService.can_manage_test_resets(request.user):
            msg = "You don't have permission to create test schedules."
            raise PermissionDenied(msg)

        try:
            # Extract unique terms from the selected resets
            terms = {reset.term for reset in queryset}
            from apps.curriculum.models import Term

            terms_queryset = Term.objects.filter(id__in=[t.id for t in terms])

            created = TestPeriodResetService.create_standard_test_schedule(terms_queryset)
            self.message_user(
                request,
                f"Created {created} standard reset schedules.",
                messages.SUCCESS,
            )
        except Exception as e:
            self.message_user(request, f"Error creating standard schedules: {e}", messages.ERROR)

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("term")

    def save_model(self, request, obj, form, change):
        """Save model with standard Django validation flow."""
        # Let Django handle validation naturally through clean() and form validation
        # ValidationErrors will be displayed to the user automatically
        super().save_model(request, obj, form, change)


# ========== CLASS PART TEMPLATE ADMIN ==========


class ClassPartTemplateInline(admin.TabularInline):
    """Inline admin for class part templates."""

    model = ClassPartTemplate
    extra = 1
    fields = [
        "class_part_code",
        "name",
        "class_part_type",
        "meeting_days_pattern",
        "grade_weight",
        "sequence_order",
        "is_active",
    ]
    ordering = ["sequence_order", "class_part_code"]


@admin.register(ClassPartTemplateSet)
class ClassPartTemplateSetAdmin(admin.ModelAdmin):
    """Admin interface for class part template sets."""

    list_display = [
        "level_code",
        "name",
        "version",
        "effective_date",
        "expiry_date",
        "is_active",
        "template_count",
        "is_current_display",
    ]
    list_filter = [
        "program_code",
        "is_active",
        "effective_date",
        "auto_apply_on_promotion",
    ]
    search_fields = [
        "program_code",
        "name",
        "description",
    ]
    ordering = ["-effective_date", "program_code", "level_number"]

    fieldsets = [
        (
            _("Program & Level"),
            {
                "fields": [
                    "program_code",
                    "level_number",
                    "name",
                    "description",
                ]
            },
        ),
        (
            _("Versioning"),
            {
                "fields": [
                    "version",
                    "effective_date",
                    "expiry_date",
                    "is_active",
                ],
                "description": "Only one template can be active per program/level at any time.",
            },
        ),
        (
            _("Configuration"),
            {
                "fields": [
                    "auto_apply_on_promotion",
                    "preserve_section_cohort",
                ],
                "description": "Settings for automatic template application during promotions.",
            },
        ),
    ]

    inlines = [ClassPartTemplateInline]

    def level_code(self, obj):
        """Display level code."""
        return obj.level_code

    level_code.short_description = _("Level Code")  # type: ignore[attr-defined]
    level_code.admin_order_field = "program_code"  # type: ignore[attr-defined]

    def template_count(self, obj):
        """Count of templates in this set."""
        return obj.templates.filter(is_active=True).count()

    template_count.short_description = _("Parts")  # type: ignore[attr-defined]

    def is_current_display(self, obj):
        """Display whether template is currently active."""
        from django.utils.html import format_html

        if obj.is_current():
            return format_html('<span style="color: green;">✓ Current</span>')
        return format_html('<span style="color: gray;">-</span>')

    is_current_display.short_description = _("Status")  # type: ignore[attr-defined]

    def get_queryset(self, request):
        """Optimize queryset with prefetch."""
        qs = super().get_queryset(request)
        return qs.prefetch_related("templates")


@admin.register(ClassPartTemplate)
class ClassPartTemplateAdmin(admin.ModelAdmin):
    """Admin interface for individual class part templates."""

    list_display = [
        "__str__",
        "template_set",
        "class_part_type",
        "meeting_days_pattern",
        "grade_weight",
        "sequence_order",
        "is_active",
    ]
    list_filter = [
        "template_set__program_code",
        "class_part_type",
        "is_active",
    ]
    search_fields = [
        "name",
        "template_set__program_code",
        "notes",
    ]
    ordering = ["template_set", "sequence_order"]

    fieldsets = [
        (
            _("Template Set"),
            {"fields": ["template_set"]},
        ),
        (
            _("Part Configuration"),
            {
                "fields": [
                    "class_part_code",
                    "name",
                    "class_part_type",
                    "sequence_order",
                ],
                "description": "Define the part's identity and ordering.",
            },
        ),
        (
            _("Schedule"),
            {
                "fields": [
                    "meeting_days_pattern",
                    "grade_weight",
                ],
                "description": "Schedule pattern (e.g., 'MON,WED' or 'TUE,THU').",
            },
        ),
        (
            _("Resources"),
            {
                "fields": [
                    "default_textbooks",
                    "notes",
                    "is_active",
                ],
                "description": "Default textbooks will be copied to actual class parts.",
            },
        ),
    ]

    filter_horizontal = ["default_textbooks"]


@admin.register(ClassPromotionRule)
class ClassPromotionRuleAdmin(admin.ModelAdmin):
    """Admin interface for class promotion rules."""

    list_display = [
        "__str__",
        "source_display",
        "destination_display",
        "preserve_cohort",
        "auto_create_classes",
        "apply_template",
        "is_active",
    ]
    list_filter = [
        "source_program",
        "destination_program",
        "preserve_cohort",
        "auto_create_classes",
        "apply_template",
        "is_active",
    ]
    search_fields = [
        "source_program",
        "destination_program",
        "notes",
    ]
    ordering = ["source_program", "source_level"]

    fieldsets = [
        (
            _("Source"),
            {
                "fields": [
                    "source_program",
                    "source_level",
                ],
                "description": "Program and level students are promoted from.",
            },
        ),
        (
            _("Destination"),
            {
                "fields": [
                    "destination_program",
                    "destination_level",
                ],
                "description": "Program and level students are promoted to.",
            },
        ),
        (
            _("Configuration"),
            {
                "fields": [
                    "preserve_cohort",
                    "auto_create_classes",
                    "apply_template",
                    "is_active",
                    "notes",
                ],
                "description": "Promotion behavior settings.",
            },
        ),
    ]

    def source_display(self, obj):
        """Display source level."""
        return f"{obj.source_program}-{obj.source_level:02d}"

    source_display.short_description = _("From")  # type: ignore[attr-defined]

    def destination_display(self, obj):
        """Display destination level."""
        return f"{obj.destination_program}-{obj.destination_level:02d}"

    destination_display.short_description = _("To")  # type: ignore[attr-defined]
