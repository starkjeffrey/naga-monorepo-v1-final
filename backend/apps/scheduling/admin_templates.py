"""Admin interface for class part templates."""

from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.scheduling.models_templates import (
    ClassPartTemplate,
    ClassPartTemplateSet,
    ClassPromotionRule,
)


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
                ]
            },
        ),
        (
            _("Configuration"),
            {
                "fields": [
                    "auto_apply_on_promotion",
                    "preserve_section_cohort",
                ]
            },
        ),
    ]

    inlines = [ClassPartTemplateInline]

    @admin.display(description=_("Level Code"), ordering="program_code")
    def level_code(self, obj):
        """Display level code."""
        return obj.level_code

    @admin.display(description=_("Parts"))
    def template_count(self, obj):
        """Count of templates in this set."""
        return obj.templates.filter(is_active=True).count()

    @admin.display(description=_("Status"))
    def is_current_display(self, obj):
        """Display whether template is currently active."""
        if obj.is_current():
            return format_html('<span style="color: green;">✓ Current</span>')
        return format_html('<span style="color: gray;">-</span>')

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
                ]
            },
        ),
        (
            _("Schedule"),
            {
                "fields": [
                    "meeting_days_pattern",
                    "grade_weight",
                ]
            },
        ),
        (
            _("Resources"),
            {
                "fields": [
                    "default_textbooks",
                    "notes",
                    "is_active",
                ]
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
                ]
            },
        ),
        (
            _("Destination"),
            {
                "fields": [
                    "destination_program",
                    "destination_level",
                ]
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
                ]
            },
        ),
    ]

    @admin.display(description=_("From"))
    def source_display(self, obj):
        """Display source level."""
        return f"{obj.source_program}-{obj.source_level:02d}"

    @admin.display(description=_("To"))
    def destination_display(self, obj):
        """Display destination level."""
        return f"{obj.destination_program}-{obj.destination_level:02d}"
