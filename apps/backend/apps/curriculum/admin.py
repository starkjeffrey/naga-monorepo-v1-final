"""Curriculum app admin interfaces.

Provides comprehensive admin interfaces for managing academic structure,
courses, terms, and curriculum requirements following clean architecture
principles.

Key features:
- Hierarchical organization (Division → Cycle → Major)
- Course management with prerequisite tracking
- Term management with important dates
- Textbook and requirement management
- Enhanced usability with inlines and filters
"""

from django.contrib import admin
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    Course,
    CoursePartTemplate,
    CoursePrerequisite,
    Cycle,
    Division,
    Major,
    Term,
    Textbook,
)


class CycleInline(admin.TabularInline):
    """Inline for viewing cycles within a division."""

    model = Cycle
    extra = 0
    fields = [
        "name",
        "short_name",
        "typical_duration_terms",
        "is_active",
        "display_order",
    ]
    readonly_fields = []


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    """Admin interface for academic divisions."""

    list_display = [
        "name",
        "short_name",
        "cycle_count",
        "course_count",
        "is_active",
        "display_order",
        "created_at",
    ]
    list_filter = [
        "is_active",
        "created_at",
    ]
    search_fields = [
        "name",
        "short_name",
        "description",
    ]
    ordering = ["display_order", "name"]
    readonly_fields = ["created_at", "updated_at"]
    list_editable = ["display_order", "is_active"]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "name",
                    "short_name",
                    "description",
                ),
            },
        ),
        (
            "Configuration",
            {
                "fields": (
                    "is_active",
                    "display_order",
                ),
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    inlines = [CycleInline]

    def get_queryset(self, request):
        """Optimize the queryset with annotated counts to prevent N+1 queries."""
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            active_cycle_count=Count("cycles", filter=Q(cycles__is_active=True), distinct=True),
            active_course_count=Count(
                "cycles__majors__courses", filter=Q(cycles__majors__courses__is_active=True), distinct=True
            ),
        )
        return queryset

    @admin.display(description="Active Cycles", ordering="active_cycle_count")
    def cycle_count(self, obj):
        """Display annotated cycle count."""
        return getattr(obj, "active_cycle_count", 0)

    @admin.display(description="Active Courses", ordering="active_course_count")
    def course_count(self, obj):
        """Display annotated course count."""
        return getattr(obj, "active_course_count", 0)


class MajorInline(admin.TabularInline):
    """Inline for viewing majors within a cycle."""

    model = Major
    extra = 0
    fields = [
        "name",
        "short_name",
        "code",
        "total_credits_required",
        "is_active",
        "display_order",
    ]


@admin.register(Cycle)
class CycleAdmin(admin.ModelAdmin):
    """Admin interface for academic cycles."""

    list_display = [
        "name",
        "division",
        "short_name",
        "typical_duration_terms",
        "major_count",
        "is_active",
        "display_order",
    ]
    list_select_related = ["division"]
    list_filter = [
        "division",
        "is_active",
        "created_at",
    ]
    search_fields = [
        "name",
        "short_name",
        "description",
        "division__name",
    ]
    ordering = ["division", "display_order", "name"]
    readonly_fields = ["created_at", "updated_at"]
    list_editable = ["typical_duration_terms", "display_order", "is_active"]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "division",
                    "name",
                    "short_name",
                    "description",
                ),
            },
        ),
        (
            "Academic Details",
            {
                "fields": ("typical_duration_terms",),
            },
        ),
        (
            "Configuration",
            {
                "fields": (
                    "is_active",
                    "display_order",
                ),
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    inlines = [MajorInline]

    def get_queryset(self, request):
        """Optimize the queryset with annotated counts to prevent N+1 queries."""
        queryset = super().get_queryset(request)
        queryset = queryset.annotate(
            active_major_count=Count("majors", filter=Q(majors__is_active=True), distinct=True)
        )
        return queryset

    @admin.display(description="Active Majors", ordering="active_major_count")
    def major_count(self, obj):
        """Display annotated major count."""
        return getattr(obj, "active_major_count", 0)


@admin.register(Major)
class MajorAdmin(admin.ModelAdmin):
    """Admin interface for academic majors."""

    list_display = [
        "name",
        "cycle",
        "division_name",
        "code",
        "degree_awarded",
        "program_type",
        "total_credits_required",
        "display_order",
        "is_active",
    ]
    list_select_related = ["cycle", "cycle__division"]
    list_filter = [
        "cycle__division",
        "cycle",
        "degree_awarded",
        "program_type",
        "is_active",
        "created_at",
    ]
    search_fields = [
        "name",
        "short_name",
        "code",
        "description",
        "cycle__name",
        "cycle__division__name",
    ]
    ordering = ["cycle", "display_order", "name"]
    readonly_fields = ["created_at", "updated_at", "full_hierarchy_name"]
    list_editable = ["display_order", "is_active"]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "cycle",
                    "name",
                    "short_name",
                    "code",
                    "description",
                    "full_hierarchy_name",
                ),
            },
        ),
        (
            "Program Details",
            {
                "fields": (
                    "program_type",
                    "degree_awarded",
                    "faculty_display_name",
                    "faculty_code",
                ),
            },
        ),
        ("Academic Requirements", {"fields": ("total_credits_required",)}),
        (
            "Configuration",
            {
                "fields": (
                    "is_active",
                    "display_order",
                ),
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(
        description="Division",
        ordering="cycle__division__name",
    )
    def division_name(self, obj):
        """Display division name for this major."""
        return obj.cycle.division.name


@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    """Admin interface for academic terms."""

    list_display = [
        "code",
        "term_type_display",
        "start_date",
        "end_date",
        "discount_end_date",
        "enrollment_status",
        "is_active",
    ]
    list_filter = [
        "term_type",
        "is_active",
        "start_date",
        "created_at",
    ]
    search_fields = [
        "code",
        "description",
    ]
    ordering = ["-start_date"]
    readonly_fields = ["created_at", "updated_at"]
    date_hierarchy = "start_date"

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "code",
                    "description",
                    "term_type",
                ),
            },
        ),
        (
            "Academic Calendar",
            {
                "fields": (
                    "start_date",
                    "end_date",
                ),
            },
        ),
        (
            "Important Deadlines",
            {
                "fields": (
                    "discount_end_date",
                    "add_date",
                    "drop_date",
                    "payment_deadline_date",
                ),
            },
        ),
        ("Configuration", {"fields": ("is_active",)}),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Term Type", ordering="term_type")
    def term_type_display(self, obj):
        """Display term type with visual formatting."""
        if not obj.term_type:
            return format_html('<span style="color: #999; font-style: italic;">Not Set</span>')

        # Color coding for different term types
        colors = {
            "ENG A": "#2196F3",  # Blue
            "ENG B": "#4CAF50",  # Green
            "BA": "#FF9800",  # Orange
            "MA": "#9C27B0",  # Purple
            "X": "#F44336",  # Red
        }

        color = colors.get(obj.term_type, "#666")
        return format_html(
            '<span style="color: {}; font-weight: bold; padding: 2px 6px; '
            'background: {}22; border-radius: 3px;">{}</span>',
            color,
            color,
            obj.term_type,
        )

    @admin.display(description="Status")
    def enrollment_status(self, obj):
        """Display enrollment status based on current date."""
        today = timezone.now().date()

        if not obj.is_active:
            return format_html('<span style="color: red;">Inactive</span>')
        if today < obj.start_date:
            return format_html('<span style="color: blue;">Upcoming</span>')
        if today <= obj.end_date:
            return format_html('<span style="color: green;">Current</span>')
        return format_html('<span style="color: gray;">Past</span>')


class CoursePrerequisiteInline(admin.TabularInline):
    """Inline for managing course prerequisites."""

    model = CoursePrerequisite
    fk_name = "course"
    extra = 0
    fields = [
        "prerequisite",
        "notes",
        "start_date",
        "end_date",
        "is_active",
    ]
    verbose_name = "Prerequisite Required"
    verbose_name_plural = "Prerequisites Required for This Course"


class CourseEnablesInline(admin.TabularInline):
    """Inline for viewing courses this course enables."""

    model = CoursePrerequisite
    fk_name = "prerequisite"
    extra = 0
    fields = [
        "course",
        "notes",
        "start_date",
        "end_date",
        "is_active",
    ]
    readonly_fields = ["course", "notes", "start_date", "end_date", "is_active"]
    verbose_name = "Course This Enables"
    verbose_name_plural = "Courses This Course Enables"

    def has_add_permission(self, request, obj):
        return False


class CoursePartTemplateInline(admin.TabularInline):
    """Inline for managing course part templates."""

    model = CoursePartTemplate
    extra = 0
    fields = [
        "part_type",
        "part_code",
        "name",
        "session_number",
        "meeting_days",
        "grade_weight",
        "display_order",
        "is_active",
    ]
    readonly_fields = []
    verbose_name = "Part Template"
    verbose_name_plural = "Course Part Templates"


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """Admin interface for courses."""

    list_display = [
        "code",
        "title",
        "credits",
        "cycle",
        "division_name",
        "start_date",
        "end_date",
        "is_currently_active_display",
        "is_active",
        "is_foundation_year",
    ]
    list_select_related = ["cycle", "cycle__division"]
    list_filter = [
        "cycle__division",
        "cycle",
        "credits",
        "start_date",
        "is_foundation_year",
        "is_active",
        "created_at",
    ]
    search_fields = [
        "code",
        "title",
        "short_title",
        "description",
    ]
    ordering = ["code", "start_date"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "is_currently_active",
    ]
    filter_horizontal = ["majors"]
    list_editable = ["is_active"]
    actions = ["activate_courses", "deactivate_courses"]

    def activate_courses(self, request, queryset):
        """Activate selected courses."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Activated {updated} course(s).")

    # activate_courses.short_description = "Activate selected courses"  # Deprecated in newer Django

    def deactivate_courses(self, request, queryset):
        """Deactivate selected courses."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} course(s).")

    # deactivate_courses.short_description = "Deactivate selected courses"  # Deprecated in newer Django

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "code",
                    "title",
                    "short_title",
                    "description",
                ),
            },
        ),
        (
            "Academic Organization",
            {
                "fields": (
                    "cycle",
                    "majors",
                ),
            },
        ),
        (
            "Course Properties",
            {
                "fields": (
                    "credits",
                    "is_foundation_year",
                ),
            },
        ),
        (
            "Course Progression",
            {
                "fields": (
                    "recommended_term",
                    "earliest_term",
                    "latest_term",
                    "failure_retry_priority",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Effective Dates",
            {
                "fields": (
                    "start_date",
                    "end_date",
                    "is_currently_active",
                ),
                "description": "Date range when this course is available for enrollment",
            },
        ),
        ("Configuration", {"fields": ("is_active",)}),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    inlines = [CoursePartTemplateInline, CoursePrerequisiteInline, CourseEnablesInline]

    @admin.display(description="Currently Active")
    def is_currently_active_display(self, obj):
        """Display current active status with visual indicator."""
        if obj.is_currently_active:
            return format_html('<span style="color: green;">✓ Active</span>')
        return format_html('<span style="color: red;">✗ Not Active</span>')

    @admin.display(description="Division", ordering="cycle__division__name")
    def division_name(self, obj):
        """Display division name through cycle."""
        return obj.division.name if obj.division else "—"


@admin.register(Textbook)
class TextbookAdmin(admin.ModelAdmin):
    """Admin interface for textbooks."""

    list_display = [
        "title",
        "author",
        "publisher",
        "edition",
        "year",
        "isbn",
        "created_at",
    ]
    list_filter = [
        "publisher",
        "year",
        "created_at",
    ]
    search_fields = [
        "title",
        "author",
        "isbn",
        "publisher",
    ]
    ordering = ["title", "author"]
    readonly_fields = ["created_at", "updated_at", "citation"]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "title",
                    "author",
                ),
            },
        ),
        (
            "Publication Details",
            {
                "fields": (
                    "publisher",
                    "edition",
                    "year",
                    "isbn",
                ),
            },
        ),
        (
            "Additional Information",
            {
                "fields": (
                    "notes",
                    "citation",
                ),
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )


@admin.register(CoursePrerequisite)
class CoursePrerequisiteAdmin(admin.ModelAdmin):
    """Admin interface for course prerequisites."""

    list_display = [
        "prerequisite_code",
        "course_code",
        "relationship_display",
        "start_date",
        "end_date",
        "is_active",
    ]
    list_filter = [
        "prerequisite__cycle__division",
        "course__cycle__division",
        "is_active",
        "start_date",
        "created_at",
    ]
    search_fields = [
        "prerequisite__code",
        "prerequisite__title",
        "course__code",
        "course__title",
        "notes",
    ]
    ordering = ["course__code", "prerequisite__code"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = (
        (
            "Prerequisite Relationship",
            {
                "fields": (
                    "prerequisite",
                    "course",
                    "notes",
                ),
            },
        ),
        (
            "Effective Period",
            {
                "fields": (
                    "start_date",
                    "end_date",
                ),
            },
        ),
        ("Configuration", {"fields": ("is_active",)}),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(
        description="Prerequisite",
        ordering="prerequisite__code",
    )
    def prerequisite_code(self, obj):
        """Display prerequisite course code."""
        return obj.prerequisite.code

    @admin.display(
        description="Course",
        ordering="course__code",
    )
    def course_code(self, obj):
        """Display main course code."""
        return obj.course.code

    @admin.display(description="Relationship")
    def relationship_display(self, obj):
        """Display the prerequisite relationship visually."""
        return format_html(
            '<span style="font-family: monospace;">{} → {}</span>',
            obj.prerequisite.code,
            obj.course.code,
        )


@admin.register(CoursePartTemplate)
class CoursePartTemplateAdmin(admin.ModelAdmin):
    """Admin interface for course part templates."""

    list_display = [
        "course_code",
        "name",
        "part_type",
        "part_code",
        "session_number",
        "meeting_days",
        "grade_weight",
        "textbook_count",
        "is_active",
        "display_order",
    ]
    list_filter = [
        "course__cycle__division",
        "part_type",
        "session_number",
        "is_active",
        "created_at",
    ]
    search_fields = [
        "course__code",
        "course__title",
        "name",
        "part_type",
        "part_code",
    ]
    ordering = ["course__code", "session_number", "display_order"]
    readonly_fields = ["created_at", "updated_at", "full_name"]
    filter_horizontal = ["textbooks"]

    fieldsets = (
        (
            "Course and Part Identity",
            {
                "fields": (
                    "course",
                    "part_type",
                    "part_code",
                    "name",
                    "full_name",
                ),
            },
        ),
        (
            "Session Configuration",
            {
                "fields": (
                    "session_number",
                    "grade_weight",
                ),
            },
        ),
        (
            "Schedule Template",
            {
                "fields": ("meeting_days",),
                "description": "Default meeting pattern - can be adjusted during actual scheduling",
            },
        ),
        (
            "Required Resources",
            {
                "fields": ("textbooks",),
            },
        ),
        (
            "Organization",
            {
                "fields": (
                    "display_order",
                    "is_active",
                ),
            },
        ),
        (
            "Audit Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Course", ordering="course__code")
    def course_code(self, obj):
        """Display course code."""
        return obj.course.code

    @admin.display(description="Textbooks")
    def textbook_count(self, obj):
        """Display number of textbooks assigned."""
        return obj.textbooks.count()

    def get_queryset(self, request):
        """Optimize queryset for admin display with comprehensive related data."""
        return (
            super()
            .get_queryset(request)
            .select_related("course", "course__cycle", "course__cycle__division")
            .prefetch_related("textbooks")
        )
