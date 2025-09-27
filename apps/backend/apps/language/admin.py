"""Admin interface for language app models.

Provides administrative interface for managing language program promotions
and viewing promotion history.
"""

from django.contrib import admin, messages
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils.html import format_html

from .models import LanguageLevelSkipRequest, LanguageProgramPromotion, LanguageStudentPromotion


@admin.register(LanguageProgramPromotion)
class LanguageProgramPromotionAdmin(admin.ModelAdmin):
    """Admin interface for language program promotions."""

    list_display = [
        "program",
        "source_term",
        "target_term",
        "status",
        "students_promoted_count",
        "classes_cloned_count",
        "initiated_by",
        "initiated_at",
    ]
    list_filter = ["program", "status", "initiated_at", "source_term__term_type"]
    search_fields = [
        "program",
        "source_term__code",
        "target_term__code",
        "initiated_by__username",
    ]
    readonly_fields = [
        "initiated_at",
        "completed_at",
        "students_promoted_count",
        "classes_cloned_count",
    ]
    fieldsets = [
        (
            "Basic Information",
            {"fields": ["program", "source_term", "target_term", "status"]},
        ),
        (
            "Progress Tracking",
            {"fields": ["students_promoted_count", "classes_cloned_count"]},
        ),
        (
            "Administrative Details",
            {"fields": ["initiated_by", "initiated_at", "completed_at", "notes"]},
        ),
    ]

    def get_readonly_fields(self, request, obj=None):
        """Make certain fields readonly after creation."""
        readonly = list(self.readonly_fields)
        if obj:  # Editing existing object
            readonly.extend(["program", "source_term", "target_term", "initiated_by"])
        return readonly

    actions = ["export_promotion_report", "mark_as_completed"]

    @admin.action(description="Export promotion report")
    def export_promotion_report(self, request: HttpRequest, queryset: QuerySet) -> HttpResponse:
        """Export promotion batch details to CSV."""
        import csv

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="promotion_report.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Program",
                "Source Term",
                "Target Term",
                "Status",
                "Students Promoted",
                "Classes Cloned",
                "Initiated By",
                "Initiated Date",
            ]
        )

        for promotion in queryset.select_related("source_term", "target_term", "initiated_by"):
            writer.writerow(
                [
                    promotion.program,
                    promotion.source_term.code,
                    promotion.target_term.code,
                    promotion.status,
                    promotion.students_promoted_count,
                    promotion.classes_cloned_count,
                    promotion.initiated_by.email,
                    promotion.initiated_at.strftime("%Y-%m-%d %H:%M:%S"),
                ]
            )

        return response

    @admin.action(description="Mark selected promotions as completed")
    def mark_as_completed(self, request: HttpRequest, queryset: QuerySet) -> None:
        """Mark promotion batches as completed."""
        updated = 0
        for promotion in queryset.filter(status__in=["INITIATED", "IN_PROGRESS"]):
            promotion.mark_completed()
            updated += 1

        messages.success(request, f"Marked {updated} promotions as completed.")


class LanguageStudentPromotionInline(admin.TabularInline):
    """Inline for student promotions within a batch."""

    model = LanguageStudentPromotion
    extra = 0
    readonly_fields = ["student", "from_level", "to_level", "result", "final_grade"]
    fields = ["student", "from_level", "to_level", "result", "final_grade", "notes"]

    def has_add_permission(self, request, obj=None):
        """Disable adding individual promotions through admin."""
        return False


@admin.register(LanguageStudentPromotion)
class LanguageStudentPromotionAdmin(admin.ModelAdmin):
    """Admin interface for individual student promotions."""

    list_display = [
        "student",
        "promotion_batch",
        "from_level",
        "to_level",
        "result",
        "final_grade",
    ]
    list_filter = ["result", "promotion_batch__program", "promotion_batch__source_term"]
    search_fields = [
        "student__user__first_name",
        "student__user__last_name",
        "student__student_number",
        "from_level",
        "to_level",
    ]
    readonly_fields = [
        "promotion_batch",
        "student",
        "from_level",
        "to_level",
        "source_class",
        "target_class",
    ]

    fieldsets = [
        ("Student Information", {"fields": ["student", "promotion_batch"]}),
        (
            "Level Progression",
            {"fields": ["from_level", "to_level", "result", "final_grade"]},
        ),
        ("Class Information", {"fields": ["source_class", "target_class"]}),
        ("Additional Notes", {"fields": ["notes"]}),
    ]

    def get_readonly_fields(self, request, obj=None):
        """Make most fields readonly - this is primarily for viewing."""
        readonly = list(self.readonly_fields)
        if obj:  # Editing existing object
            readonly.extend(["result"])
        return readonly


# Add student promotion inline to the main promotion admin
LanguageProgramPromotionAdmin.inlines = [LanguageStudentPromotionInline]


@admin.register(LanguageLevelSkipRequest)
class LanguageLevelSkipRequestAdmin(admin.ModelAdmin):
    """Admin interface for language level skip requests."""

    list_display = [
        "student_info",
        "level_progression",
        "reason_category",
        "status",
        "requested_by",
        "created_at",
    ]
    list_filter = [
        "status",
        "reason_category",
        "program",
        "created_at",
        "reviewed_at",
    ]
    search_fields = [
        "student__person__personal_name",
        "student__person__family_name",
        "student__student_number",
        "current_level",
        "target_level",
    ]
    readonly_fields = [
        "created_at",
        "updated_at",
        "reviewed_at",
        "implemented_at",
    ]

    fieldsets = [
        (
            "Student Information",
            {
                "fields": [
                    "student",
                    "program",
                    "current_level",
                    "target_level",
                    "levels_skipped",
                ]
            },
        ),
        (
            "Request Details",
            {
                "fields": [
                    "reason_category",
                    "detailed_reason",
                    "supporting_evidence",
                ]
            },
        ),
        (
            "Processing Information",
            {
                "fields": [
                    "status",
                    "requested_by",
                    "created_at",
                ]
            },
        ),
        (
            "Review Information",
            {
                "fields": [
                    "reviewed_by",
                    "reviewed_at",
                    "review_notes",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            "Implementation",
            {
                "fields": [
                    "implemented_by",
                    "implemented_at",
                    "new_enrollment",
                ],
                "classes": ["collapse"],
            },
        ),
    ]

    @admin.display(description="Student")
    def student_info(self, obj) -> str:
        """Display student information."""
        return f"{obj.student.person.full_name} ({obj.student.student_number})"

    @admin.display(description="Level Progression")
    def level_progression(self, obj) -> str:
        """Display level progression with visual indicator."""
        color = "green" if obj.status == "APPROVED" else "orange"
        return format_html(
            '<span style="color: {};">{} → {} ({} levels)</span>',
            color,
            obj.current_level,
            obj.target_level,
            obj.levels_skipped,
        )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset with select_related."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "student__person",
                "requested_by",
                "reviewed_by",
                "implemented_by",
                "new_enrollment",
            )
        )

    def get_readonly_fields(self, request: HttpRequest, obj=None):
        """Make certain fields readonly based on status."""
        readonly = list(self.readonly_fields)
        if obj and obj.status != LanguageLevelSkipRequest.RequestStatus.PENDING:
            readonly.extend(
                [
                    "student",
                    "program",
                    "current_level",
                    "target_level",
                    "reason_category",
                    "detailed_reason",
                    "supporting_evidence",
                ]
            )
        return readonly
