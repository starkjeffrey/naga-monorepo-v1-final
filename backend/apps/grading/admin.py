"""Django admin configuration for grading models.

This module provides comprehensive admin interfaces for:
- Grading scales and grade conversions management
- Class part grade entry and review
- Grade change history tracking
- GPA record monitoring
- Bulk grade operations

Following clean admin design with proper filtering, search,
and bulk actions for efficient grade management.
"""

from django.contrib import admin, messages
from django.contrib.admin import ModelAdmin
from django.core.exceptions import ValidationError
from django.db.models import QuerySet
from django.forms import ModelForm
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import (
    ClassPartGrade,
    ClassSessionGrade,
    GPARecord,
    GradeChangeHistory,
    GradeConversion,
    GradingScale,
)
from .services import (
    ClassPartGradeService,
    ClassSessionGradeService,
    GPACalculationService,
)


class GradeConversionInline(admin.TabularInline):
    """Inline admin for grade conversions within grading scales."""

    model = GradeConversion
    extra = 0
    ordering = ["display_order"]
    fields = [
        "letter_grade",
        "min_percentage",
        "max_percentage",
        "gpa_points",
        "display_order",
    ]


@admin.register(GradingScale)
class GradingScaleAdmin(ModelAdmin):
    """Admin interface for grading scales."""

    list_display = [
        "name",
        "scale_type",
        "is_active",
        "conversion_count",
        "created_at",
    ]
    list_filter = [
        "scale_type",
        "is_active",
        "created_at",
    ]
    search_fields = [
        "name",
        "description",
    ]
    ordering = ["scale_type", "name"]
    inlines = [GradeConversionInline]

    fieldsets = (
        (None, {"fields": ("name", "scale_type", "description", "is_active")}),
        (
            _("Audit Information"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description=_("Conversions"))
    def conversion_count(self, obj) -> int:
        """Get count of grade conversions for this scale."""
        return obj.grade_conversions.count()

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset with prefetch_related."""
        return super().get_queryset(request).prefetch_related("grade_conversions")


@admin.register(GradeConversion)
class GradeConversionAdmin(ModelAdmin):
    """Admin interface for individual grade conversions."""

    list_display = [
        "grading_scale",
        "letter_grade",
        "percentage_range",
        "gpa_points",
        "display_order",
    ]
    list_filter = [
        "grading_scale__scale_type",
        "grading_scale",
        "gpa_points",
    ]
    search_fields = [
        "letter_grade",
        "grading_scale__name",
    ]
    ordering = ["grading_scale", "display_order"]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "grading_scale",
                    "letter_grade",
                    "min_percentage",
                    "max_percentage",
                    "gpa_points",
                    "display_order",
                ),
            },
        ),
        (
            _("Audit Information"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description=_("Percentage Range"))
    def percentage_range(self, obj) -> str:
        """Display percentage range as formatted string."""
        return f"{obj.min_percentage}% - {obj.max_percentage}%"


class ClassPartGradeForm(ModelForm):
    """Custom form for class part grade with validation."""

    class Meta:
        model = ClassPartGrade
        fields = [
            "enrollment",
            "class_part",
            "numeric_score",
            "letter_grade",
            "gpa_points",
            "grade_status",
            "entered_by",
            "notes",
        ]

    def clean(self) -> dict:
        """Custom validation for grade data."""
        cleaned_data = super().clean()
        if cleaned_data is None:
            return {}
        numeric_score = cleaned_data.get("numeric_score")
        letter_grade = cleaned_data.get("letter_grade")

        if not numeric_score and not letter_grade:
            raise ValidationError(
                _("Either numeric score or letter grade must be provided."),
            )

        return cleaned_data


@admin.register(ClassPartGrade)
class ClassPartGradeAdmin(ModelAdmin):
    """Admin interface for class part grades."""

    form = ClassPartGradeForm

    list_display = [
        "student_name",
        "class_info",
        "grade_display",
        "grade_status",
        "grade_source",
        "entered_by",
        "entered_at",
    ]
    list_filter = [
        "grade_status",
        "grade_source",
        "class_part__class_session__class_header__term",
        "entered_at",
        "student_notified",
    ]
    search_fields = [
        "enrollment__student__person__personal_name",
        "enrollment__student__person__family_name",
        "enrollment__student__student_id",
        "class_part__name",
        "class_part__class_session__class_header__course__code",
    ]
    ordering = ["-entered_at"]

    fieldsets = (
        (
            _("Grade Information"),
            {
                "fields": (
                    "enrollment",
                    "class_part",
                    "numeric_score",
                    "letter_grade",
                    "gpa_points",
                ),
            },
        ),
        (
            _("Grade Metadata"),
            {
                "fields": (
                    "grade_source",
                    "grade_status",
                    "notes",
                ),
            },
        ),
        (
            _("Audit Trail"),
            {
                "fields": (
                    "entered_by",
                    "entered_at",
                    "approved_by",
                    "approved_at",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Notification"),
            {
                "fields": (
                    "student_notified",
                    "notification_date",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["gpa_points", "entered_at"]

    @admin.display(
        description=_("Student"),
        ordering="enrollment__student__person__family_name",
    )
    def student_name(self, obj) -> str:
        """Get student name for display."""
        return str(obj.student)

    @admin.display(description=_("Class"))
    def class_info(self, obj) -> str:
        """Get class information for display."""
        return f"{obj.class_part.class_session.class_header} - {obj.class_part.name}"

    @admin.display(description=_("Grade"))
    def grade_display(self, obj) -> str:
        """Display grade with color coding."""
        if obj.letter_grade:
            grade_text = obj.letter_grade
            if obj.numeric_score:
                grade_text += f" ({obj.numeric_score}%)"
        elif obj.numeric_score:
            grade_text = f"{obj.numeric_score}%"
        else:
            grade_text = "No Grade"

        # Color code based on grade status
        color = {
            "DRAFT": "#6c757d",
            "SUBMITTED": "#007bff",
            "APPROVED": "#28a745",
            "FINALIZED": "#17a2b8",
        }.get(obj.grade_status, "#6c757d")

        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            grade_text,
        )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset with select_related."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "enrollment__student__person",
                "class_part__class_session__class_header__course",
                "entered_by",
                "approved_by",
            )
        )

    actions = [
        "recalculate_session_grades",
        "approve_selected_grades",
        "finalize_selected_grades",
        "notify_students",
        "export_grades_csv",
        "bulk_update_status",
    ]

    @admin.action(description=_("Recalculate session grades"))
    def recalculate_session_grades(
        self,
        request: HttpRequest,
        queryset: QuerySet,
    ) -> None:
        """Recalculate session grades for selected class part grades."""
        sessions_processed = set()

        for grade in queryset:
            session_key = (grade.enrollment.id, grade.class_part.class_session.id)
            if session_key not in sessions_processed:
                ClassSessionGradeService.calculate_session_grade(
                    enrollment=grade.enrollment,
                    class_session=grade.class_part.class_session,
                    force_recalculate=True,
                )
                sessions_processed.add(session_key)

        self.message_user(
            request,
            f"Recalculated grades for {len(sessions_processed)} class sessions.",
        )

    @admin.action(description=_("Approve selected grades"))
    def approve_selected_grades(self, request: HttpRequest, queryset: QuerySet) -> None:
        """Approve selected grades."""
        updated = 0
        for grade in queryset.filter(grade_status="SUBMITTED"):
            ClassPartGradeService.change_grade_status(
                grade=grade,
                new_status="APPROVED",
                changed_by=request.user,
                reason="Bulk approval from admin",
            )
            updated += 1

        self.message_user(request, f"Approved {updated} grades.")

    @admin.action(description=_("Finalize selected grades"))
    def finalize_selected_grades(
        self,
        request: HttpRequest,
        queryset: QuerySet,
    ) -> None:
        """Finalize selected grades."""
        updated = 0
        for grade in queryset.filter(grade_status="APPROVED"):
            ClassPartGradeService.change_grade_status(
                grade=grade,
                new_status="FINALIZED",
                changed_by=request.user,
                reason="Bulk finalization from admin",
            )
            updated += 1

        self.message_user(request, f"Finalized {updated} grades.")

    @admin.action(description=_("Mark students as notified"))
    def notify_students(self, request: HttpRequest, queryset: QuerySet) -> None:
        """Mark students as notified for selected grades."""
        updated = queryset.filter(student_notified=False).update(
            student_notified=True,
            notification_date=timezone.now(),
        )

        self.message_user(request, f"Marked {updated} students as notified.")

    @admin.action(description=_("Export grades to CSV"))
    def export_grades_csv(self, request: HttpRequest, queryset: QuerySet) -> HttpResponse:
        """Export selected grades to CSV format."""
        import csv

        from django.http import HttpResponse

        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="grades_export.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Student ID",
                "Student Name",
                "Course",
                "Class Part",
                "Numeric Score",
                "Letter Grade",
                "GPA Points",
                "Status",
                "Entered Date",
            ]
        )

        for grade in queryset.select_related(
            "enrollment__student__person", "class_part__class_session__class_header__course"
        ):
            writer.writerow(
                [
                    grade.enrollment.student.student_id,
                    str(grade.enrollment.student),
                    grade.class_part.class_session.class_header.course.code,
                    grade.class_part.name,
                    grade.numeric_score or "",
                    grade.letter_grade or "",
                    grade.gpa_points or "",
                    grade.grade_status,
                    grade.entered_at.strftime("%Y-%m-%d %H:%M:%S"),
                ]
            )

        return response

    @admin.action(description=_("Bulk update grade status"))
    def bulk_update_status(self, request: HttpRequest, queryset: QuerySet) -> HttpResponse:
        """Bulk update grade status with confirmation."""
        if "apply" in request.POST:
            new_status = request.POST.get("new_status")
            if new_status in dict(ClassPartGrade.GradeStatus.choices):
                updated = 0
                for grade in queryset:
                    ClassPartGradeService.change_grade_status(
                        grade=grade,
                        new_status=new_status,
                        changed_by=request.user,
                        reason=f"Bulk status update to {new_status}",
                    )
                    updated += 1

                messages.success(request, f"Updated status for {updated} grades to {new_status}")
                return redirect(request.get_full_path())

        # Show confirmation form
        context = {
            "title": "Bulk Update Grade Status",
            "queryset": queryset,
            "action_checkbox_name": admin.ACTION_CHECKBOX_NAME,
            "status_choices": ClassPartGrade.GradeStatus.choices,
        }

        return admin.site.admin_view(lambda r: r.render("admin/grading/bulk_status_update.html", context))(request)


@admin.register(ClassSessionGrade)
class ClassSessionGradeAdmin(ModelAdmin):
    """Admin interface for class session grades."""

    list_display = [
        "student_name",
        "session_info",
        "calculated_score",
        "letter_grade",
        "gpa_points",
        "calculated_at",
    ]
    list_filter = [
        "class_session__class_header__term",
        "class_session__class_header__course",
        "calculated_at",
    ]
    search_fields = [
        "enrollment__student__person__personal_name",
        "enrollment__student__person__family_name",
        "enrollment__student__student_id",
        "class_session__class_header__course__code",
    ]
    ordering = ["-calculated_at"]

    fieldsets = (
        (
            _("Session Grade"),
            {
                "fields": (
                    "enrollment",
                    "class_session",
                    "calculated_score",
                    "letter_grade",
                    "gpa_points",
                ),
            },
        ),
        (
            _("Calculation Details"),
            {
                "fields": (
                    "calculated_at",
                    "calculation_details",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = [
        "calculated_score",
        "letter_grade",
        "gpa_points",
        "calculated_at",
        "calculation_details",
    ]

    @admin.display(description=_("Student"))
    def student_name(self, obj) -> str:
        """Get student name for display."""
        return str(obj.enrollment.student)

    @admin.display(description=_("Session"))
    def session_info(self, obj) -> str:
        """Get session information for display."""
        return f"{obj.class_session.class_header} - {obj.class_session.name}"

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset with select_related."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "enrollment__student__person",
                "class_session__class_header__course",
            )
        )

    actions = ["recalculate_selected_grades"]

    @admin.action(description=_("Recalculate selected grades"))
    def recalculate_selected_grades(
        self,
        request: HttpRequest,
        queryset: QuerySet,
    ) -> None:
        """Recalculate selected session grades."""
        updated = 0
        for session_grade in queryset:
            ClassSessionGradeService.calculate_session_grade(
                enrollment=session_grade.enrollment,
                class_session=session_grade.class_session,
                force_recalculate=True,
            )
            updated += 1

        self.message_user(request, f"Recalculated {updated} session grades.")


@admin.register(GradeChangeHistory)
class GradeChangeHistoryAdmin(ModelAdmin):
    """Admin interface for grade change history."""

    list_display = [
        "grade_info",
        "change_type",
        "changed_by",
        "changed_at",
        "grade_change_summary",
    ]
    list_filter = [
        "change_type",
        "changed_at",
        "changed_by",
    ]
    search_fields = [
        "class_part_grade__enrollment__student__person__personal_name",
        "class_part_grade__enrollment__student__person__family_name",
        "class_part_grade__enrollment__student__student_id",
        "reason",
        "changed_by__email",
    ]
    ordering = ["-changed_at"]

    fieldsets = (
        (
            _("Change Information"),
            {
                "fields": (
                    "class_part_grade",
                    "change_type",
                    "changed_by",
                    "changed_at",
                    "reason",
                ),
            },
        ),
        (
            _("Previous Values"),
            {
                "fields": (
                    "previous_numeric_score",
                    "previous_letter_grade",
                    "previous_status",
                ),
            },
        ),
        (
            _("New Values"),
            {
                "fields": (
                    "new_numeric_score",
                    "new_letter_grade",
                    "new_status",
                ),
            },
        ),
        (
            _("Additional Details"),
            {
                "fields": ("additional_details",),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = [
        "class_part_grade",
        "change_type",
        "changed_by",
        "changed_at",
        "previous_numeric_score",
        "previous_letter_grade",
        "previous_status",
        "new_numeric_score",
        "new_letter_grade",
        "new_status",
        "reason",
        "additional_details",
    ]

    @admin.display(description=_("Grade"))
    def grade_info(self, obj) -> str:
        """Get grade information for display."""
        return f"{obj.class_part_grade.student} - {obj.class_part_grade.class_part}"

    @admin.display(description=_("Change Summary"))
    def grade_change_summary(self, obj) -> str:
        """Display grade change summary."""
        if obj.previous_letter_grade and obj.new_letter_grade:
            return f"{obj.previous_letter_grade} → {obj.new_letter_grade}"
        if obj.previous_numeric_score and obj.new_numeric_score:
            return f"{obj.previous_numeric_score}% → {obj.new_numeric_score}%"
        if obj.previous_status and obj.new_status:
            return f"{obj.previous_status} → {obj.new_status}"
        return "Status change"

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset with select_related."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "class_part_grade__enrollment__student__person",
                "class_part_grade__class_part",
                "changed_by",
            )
        )

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Disable manual addition of change history."""
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        """Disable editing of change history."""
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        """Disable deletion of change history."""
        return False


@admin.register(GPARecord)
class GPARecordAdmin(ModelAdmin):
    """Admin interface for GPA records."""

    list_display = [
        "student_name",
        "term",
        "major",
        "gpa_type",
        "gpa_value",
        "credit_hours_display",
        "calculated_at",
    ]
    list_filter = [
        "gpa_type",
        "term",
        "major",
        "calculated_at",
    ]
    search_fields = [
        "student__person__personal_name",
        "student__person__family_name",
        "student__student_id",
        "major__name",
        "term__code",
    ]
    ordering = ["-calculated_at", "student__person__family_name"]

    fieldsets = (
        (
            _("GPA Information"),
            {
                "fields": (
                    "student",
                    "term",
                    "major",
                    "gpa_type",
                    "gpa_value",
                ),
            },
        ),
        (
            _("Credit Hours"),
            {
                "fields": (
                    "quality_points",
                    "credit_hours_attempted",
                    "credit_hours_earned",
                ),
            },
        ),
        (
            _("Calculation Details"),
            {
                "fields": (
                    "calculated_at",
                    "calculation_details",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = [
        "gpa_value",
        "quality_points",
        "credit_hours_attempted",
        "credit_hours_earned",
        "calculated_at",
        "calculation_details",
    ]

    @admin.display(
        description=_("Student"),
        ordering="student__person__family_name",
    )
    def student_name(self, obj) -> str:
        """Get student name for display."""
        return str(obj.student)

    @admin.display(description=_("Credits (Earned/Attempted)"))
    def credit_hours_display(self, obj) -> str:
        """Display credit hours attempted/earned."""
        return f"{obj.credit_hours_earned}/{obj.credit_hours_attempted}"

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset with select_related."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "student__person",
                "term",
                "major",
            )
        )

    actions = ["recalculate_selected_gpas"]

    @admin.action(description=_("Recalculate selected GPAs"))
    def recalculate_selected_gpas(
        self,
        request: HttpRequest,
        queryset: QuerySet,
    ) -> None:
        """Recalculate selected GPA records."""
        updated = 0
        for gpa_record in queryset:
            if gpa_record.gpa_type == "TERM":
                GPACalculationService.calculate_term_gpa(
                    student=gpa_record.student,
                    term=gpa_record.term,
                    major=gpa_record.major,
                    force_recalculate=True,
                )
            else:
                GPACalculationService.calculate_cumulative_gpa(
                    student=gpa_record.student,
                    current_term=gpa_record.term,
                    major=gpa_record.major,
                    force_recalculate=True,
                )
            updated += 1

        self.message_user(request, f"Recalculated {updated} GPA records.")

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Disable manual addition of GPA records."""
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        """Disable editing of GPA records."""
        return False
