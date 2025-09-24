"""Academic app admin interfaces.

Provides comprehensive admin interfaces for managing academic requirements,
transfer credits, course equivalencies, and student academic progression
following clean architecture principles.

Key features:
- Canonical requirement management
- Transfer credit approval workflow
- Course equivalency management
- Student progress tracking and exceptions
- Mobile app integration support
"""

from typing import Any

from django.contrib import admin
from django.http import HttpRequest
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    CanonicalRequirement,
    CourseEquivalency,
    StudentCourseOverride,
    StudentDegreeProgress,
    StudentRequirementException,
    TransferCredit,
)
from .services import (
    StudentCourseOverrideService,
    StudentRequirementExceptionService,
    TransferCreditService,
)


# Generic filter factory to reduce code duplication
def create_program_filter(
    filter_name,
    filter_title,
    program_type=None,
    only_with_requirements=False,
):
    """Generic factory function to create program-specific filters.

    Args:
        filter_name: Parameter name for the filter
        filter_title: Display title for the filter
        program_type: Optional program type filter (ACADEMIC or LANGUAGE)
        only_with_requirements: Whether to filter only programs with requirements

    Returns:
        A filter class for the specified criteria
    """

    class ProgramFilter(admin.SimpleListFilter):
        title = filter_title
        parameter_name = filter_name

        def lookups(self, request: HttpRequest, model_admin) -> list[tuple[Any, str]]:
            """Return program options for the filter."""
            from apps.curriculum.models import Major

            # Base queryset
            majors = Major.objects.all()

            # Apply program type filter if specified
            if program_type:
                majors = majors.filter(program_type=program_type)

            # Filter for programs with requirements if specified
            if only_with_requirements:
                majors = majors.filter(canonical_requirements__isnull=False).distinct()

            return [(major.id, major.name) for major in majors.order_by("name")]

        def queryset(self, request: HttpRequest, queryset):
            """Filter queryset based on selected major."""
            if self.value():
                return queryset.filter(major_id=self.value())
            return queryset

    return ProgramFilter


# Create specific filters using the factory
AcademicMajorFilter = create_program_filter(
    filter_name="academic_major",
    filter_title="Academic Major",
    program_type="ACADEMIC",
    only_with_requirements=True,
)


@admin.register(CourseEquivalency)
class CourseEquivalencyAdmin(admin.ModelAdmin):
    """Admin interface for course equivalencies."""

    list_display = [
        "source_course_code",
        "source_course_title",
        "arrow_indicator",
        "target_course_code",
        "target_course_title",
        "bidirectional",
        "is_active",
        "effective_period",
    ]
    list_filter = [
        "bidirectional",
        "is_active",
        "effective_term",
        "created_at",
    ]
    search_fields = [
        "original_course__code",
        "original_course__title",
        "equivalent_course__code",
        "equivalent_course__title",
        "reason",
    ]
    ordering = ["original_course__code", "equivalent_course__code"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "approved_by",
        "approval_date",
    ]
    autocomplete_fields = ["original_course", "equivalent_course"]

    fieldsets = (
        (
            "Course Mapping",
            {
                "fields": (
                    "original_course",
                    "equivalent_course",
                    "bidirectional",
                ),
            },
        ),
        (
            "Validity Period",
            {
                "fields": (
                    "effective_term",
                    "end_term",
                ),
            },
        ),
        (
            "Approval Information",
            {
                "fields": (
                    "reason",
                    "approved_by",
                    "approval_date",
                ),
            },
        ),
        (
            "Configuration",
            {
                "fields": ("is_active",),
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

    @admin.display(description="Source Course")
    def source_course_code(self, obj):
        """Display source course code."""
        return obj.original_course.code

    @admin.display(description="Source Title")
    def source_course_title(self, obj):
        """Display source course title."""
        return obj.original_course.title

    @admin.display(description="Direction")
    def arrow_indicator(self, obj):
        """Display directional arrow."""
        return "↔" if obj.bidirectional else "→"

    @admin.display(description="Target Course")
    def target_course_code(self, obj):
        """Display target course code."""
        return obj.equivalent_course.code

    @admin.display(description="Target Title")
    def target_course_title(self, obj):
        """Display target course title."""
        return obj.equivalent_course.title

    @admin.display(description="Effective Period")
    def effective_period(self, obj):
        """Display effective period."""
        start = obj.effective_term.code if obj.effective_term else "N/A"
        end = obj.end_term.code if obj.end_term else "Current"
        return f"{start} - {end}"

    def get_queryset(self, request):
        """Optimize queryset with select_related for better performance."""
        return (
            super()
            .get_queryset(request)
            .select_related("original_course", "equivalent_course", "effective_term", "end_term", "approved_by")
        )

    def save_model(self, request, obj, form, change):
        """Set approval fields when creating new course equivalencies."""
        if not change:  # New object being created
            obj.approved_by = request.user
            obj.approval_date = timezone.now().date()
        super().save_model(request, obj, form, change)


@admin.register(TransferCredit)
class TransferCreditAdmin(admin.ModelAdmin):
    """Admin interface for transfer credit management."""

    list_display = [
        "student_name",
        "external_institution",
        "external_course_code",
        "external_course_name",
        "external_credits",
        "internal_equivalent",
        "awarded_credits",
        "status_display",
        "reviewed_date",
    ]
    list_select_related = ["student", "student__person", "equivalent_course", "reviewed_by"]
    list_filter = [
        "approval_status",
        "credit_type",
        "year_taken",
        "created_at",
        "review_date",
    ]
    search_fields = [
        "student__person__family_name",
        "student__person__personal_name",
        "external_institution",
        "external_course_code",
        "external_course_name",
        "equivalent_course__code",
        "equivalent_course__title",
    ]
    ordering = ["-created_at"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "reviewed_by",
        "review_date",
    ]
    autocomplete_fields = ["student", "equivalent_course"]

    fieldsets = (
        (
            "Student Information",
            {"fields": ("student",)},
        ),
        (
            "External Course Details",
            {
                "fields": (
                    "external_institution",
                    "external_course_code",
                    "external_course_name",
                    "external_credits",
                    "external_grade",
                    "term_taken",
                    "year_taken",
                ),
            },
        ),
        (
            "Internal Mapping",
            {
                "fields": (
                    "equivalent_course",
                    "awarded_credits",
                    "credit_type",
                ),
            },
        ),
        (
            "Approval Workflow",
            {
                "fields": (
                    "approval_status",
                    "reviewed_by",
                    "review_date",
                    "review_notes",
                ),
            },
        ),
        (
            "Documentation",
            {
                "fields": ("documentation",),
                "classes": ("collapse",),
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

    @admin.display(description="Student")
    def student_name(self, obj):
        """Display student full name."""
        return obj.student.person.full_name

    @admin.display(description="Internal Equivalent")
    def internal_equivalent(self, obj):
        """Display internal equivalent course."""
        if obj.equivalent_course:
            return f"{obj.equivalent_course.code}: {obj.equivalent_course.title}"
        return "—"

    @admin.display(description="Status")
    def status_display(self, obj):
        """Display approval status with color coding."""
        status_colors = {
            TransferCredit.ApprovalStatus.PENDING: "orange",
            TransferCredit.ApprovalStatus.APPROVED: "green",
            TransferCredit.ApprovalStatus.REJECTED: "red",
            TransferCredit.ApprovalStatus.MORE_INFO: "blue",
        }
        color = status_colors.get(obj.approval_status, "black")
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_approval_status_display(),
        )

    @admin.display(description="Review Date")
    def reviewed_date(self, obj):
        """Display formatted review date."""
        if obj.review_date:
            return obj.review_date.strftime("%Y-%m-%d")
        return "—"

    actions = ["approve_credits", "reject_credits", "request_more_info"]

    def approve_credits(self, request, queryset):
        """Approve selected transfer credits using service layer."""
        updated = 0
        for credit in queryset.filter(approval_status=TransferCredit.ApprovalStatus.PENDING):
            try:
                TransferCreditService.approve_transfer(credit, request.user, "Approved via admin action")
                updated += 1
            except Exception as e:
                self.message_user(request, f"Error approving credit {credit.id}: {e!s}", level="ERROR")
        self.message_user(request, f"Successfully approved {updated} transfer credit(s).")

    approve_credits.short_description = "Approve selected transfer credits"  # type: ignore

    def reject_credits(self, request, queryset):
        """Reject selected transfer credits using service layer."""
        updated = 0
        for credit in queryset.filter(approval_status=TransferCredit.ApprovalStatus.PENDING):
            try:
                TransferCreditService.reject_transfer(credit, request.user, "Rejected via admin action")
                updated += 1
            except Exception as e:
                self.message_user(request, f"Error rejecting credit {credit.id}: {e!s}", level="ERROR")
        self.message_user(request, f"Successfully rejected {updated} transfer credit(s).")

    reject_credits.short_description = "Reject selected transfer credits"  # type: ignore

    def request_more_info(self, request, queryset):
        """Request more information for selected transfer credits."""
        updated = queryset.filter(approval_status=TransferCredit.ApprovalStatus.PENDING).update(
            approval_status=TransferCredit.ApprovalStatus.MORE_INFO,
            reviewed_by=request.user,
            review_date=timezone.now(),
            review_notes="Additional information required - please provide official transcripts.",
        )
        self.message_user(request, f"Requested more information for {updated} transfer credit(s).")

    request_more_info.short_description = "Request more information"  # type: ignore

    # Remove this method since we now use list_select_related


@admin.register(StudentCourseOverride)
class StudentCourseOverrideAdmin(admin.ModelAdmin):
    """Admin interface for student course overrides."""

    list_display = [
        "student_name",
        "course_substitution",
        "reason",
        "status_display",
        "validity_period",
        "requested_date",
    ]
    list_select_related = [
        "student",
        "student__person",
        "original_course",
        "substitute_course",
        "effective_term",
        "expiration_term",
        "requested_by",
        "approved_by",
    ]
    list_filter = [
        "approval_status",
        "reason",
        "effective_term",
        "request_date",
        "created_at",
    ]
    search_fields = [
        "student__person__family_name",
        "student__person__personal_name",
        "original_course__code",
        "original_course__title",
        "substitute_course__code",
        "substitute_course__title",
        "detailed_reason",
    ]
    ordering = ["-request_date"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "requested_by",
        "request_date",
        "approved_by",
        "approval_date",
        "is_currently_valid",
    ]
    autocomplete_fields = [
        "student",
        "original_course",
        "substitute_course",
    ]

    fieldsets = (
        (
            "Student and Courses",
            {
                "fields": (
                    "student",
                    "original_course",
                    "substitute_course",
                ),
            },
        ),
        (
            "Override Details",
            {
                "fields": (
                    "reason",
                    "detailed_reason",
                ),
            },
        ),
        (
            "Validity Period",
            {
                "fields": (
                    "effective_term",
                    "expiration_term",
                    "is_currently_valid",
                ),
            },
        ),
        (
            "Approval Workflow",
            {
                "fields": (
                    "approval_status",
                    "requested_by",
                    "request_date",
                    "approved_by",
                    "approval_date",
                    "rejection_reason",
                ),
            },
        ),
        (
            "Documentation",
            {
                "fields": (
                    "supporting_documentation",
                    "academic_advisor_notes",
                ),
                "classes": ("collapse",),
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

    @admin.display(description="Student")
    def student_name(self, obj):
        """Display student full name."""
        return obj.student.person.full_name

    @admin.display(description="Course Substitution")
    def course_substitution(self, obj):
        """Display course substitution mapping."""
        return f"{obj.original_course.code} → {obj.substitute_course.code}"

    @admin.display(description="Status")
    def status_display(self, obj):
        """Display approval status with visual indicator."""
        status_icons = {
            StudentCourseOverride.ApprovalStatus.PENDING: "⏳",
            StudentCourseOverride.ApprovalStatus.APPROVED: "✅",
            StudentCourseOverride.ApprovalStatus.REJECTED: "❌",
            StudentCourseOverride.ApprovalStatus.EXPIRED: "⌛",
        }
        icon = status_icons.get(obj.approval_status, "")
        return f"{icon} {obj.get_approval_status_display()}"

    @admin.display(description="Valid Period")
    def validity_period(self, obj):
        """Display validity period."""
        start = obj.effective_term.name if obj.effective_term else "N/A"
        end = obj.expiration_term.name if obj.expiration_term else "No Expiry"
        return f"{start} - {end}"

    @admin.display(description="Request Date")
    def requested_date(self, obj):
        """Display formatted request date."""
        return obj.request_date.strftime("%Y-%m-%d")

    actions = ["approve_overrides", "reject_overrides"]

    def approve_overrides(self, request, queryset):
        """Approve selected course overrides using service layer."""
        updated = 0
        for override in queryset.filter(approval_status=StudentCourseOverride.ApprovalStatus.PENDING):
            try:
                StudentCourseOverrideService.approve_override(override, request.user, "Approved via admin action")
                updated += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Error approving override {override.id}: {e!s}",
                    level="ERROR",
                )
        self.message_user(request, f"Successfully approved {updated} course override(s).")

    approve_overrides.short_description = "Approve selected overrides"  # type: ignore

    def reject_overrides(self, request, queryset):
        """Reject selected course overrides using service layer."""
        updated = 0
        for override in queryset.filter(approval_status=StudentCourseOverride.ApprovalStatus.PENDING):
            try:
                StudentCourseOverrideService.reject_override(override, request.user, "Rejected via admin action")
                updated += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Error rejecting override {override.id}: {e!s}",
                    level="ERROR",
                )
        self.message_user(request, f"Successfully rejected {updated} course override(s).")

    reject_overrides.short_description = "Reject selected overrides"  # type: ignore

    # Remove this method since we now use list_select_related


@admin.register(CanonicalRequirement)
class CanonicalRequirementAdmin(admin.ModelAdmin):
    """Admin interface for canonical degree requirements."""

    list_display = [
        "major",
        "required_course_display",
        "name",
        "credits_display",
        "is_active",
    ]
    list_select_related = [
        "major",
        "required_course",
        "effective_term",
        "end_term",
    ]
    list_filter = [
        AcademicMajorFilter,
        "is_active",
        "created_at",
    ]
    search_fields = [
        "required_course__code",
        "required_course__title",
        "name",
        "notes",
    ]
    ordering = ["major", "name"]
    readonly_fields = [
        "canonical_credits",
        "created_at",
        "updated_at",
    ]
    autocomplete_fields = ["major", "required_course", "effective_term", "end_term"]

    fieldsets = (
        (
            "Requirement Definition",
            {
                "fields": (
                    "major",
                    "required_course",
                    "name",
                    "description",
                ),
            },
        ),
        (
            "Validity Period",
            {
                "fields": (
                    "effective_term",
                    "end_term",
                ),
            },
        ),
        (
            "Details",
            {
                "fields": (
                    "canonical_credits",
                    "is_active",
                    "notes",
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

    @admin.display(description="Required Course", ordering="required_course__code")
    def required_course_display(self, obj):
        """Display course information."""
        if obj.required_course:
            return f"{obj.required_course.code}: {obj.required_course.title}"
        return "-"

    @admin.display(description="Credits")
    def credits_display(self, obj):
        """Display credit value from course."""
        return obj.canonical_credits

    def get_queryset(self, request):
        """Optimize queryset with prefetch_related for student_exceptions."""
        return super().get_queryset(request).prefetch_related("student_exceptions")


@admin.register(StudentDegreeProgress)
class StudentDegreeProgressAdmin(admin.ModelAdmin):
    """Admin interface for canonical requirement fulfillments (student progress tracking)."""

    list_display = [
        "student_name",
        "requirement_display",
        "fulfillment_display",
        "fulfillment_method",
        "grade",
        "credits_earned",
        "fulfillment_date",
        "is_active",
    ]
    list_select_related = [
        "student",
        "student__person",
        "canonical_requirement",
        "canonical_requirement__major",
        "canonical_requirement__required_course",
        "fulfilling_enrollment",
        "fulfilling_enrollment__class_header",
        "fulfilling_enrollment__class_header__course",
        "fulfilling_enrollment__class_header__term",
        "fulfilling_transfer",
        "fulfilling_exception",
        "fulfilling_exception__fulfilling_course",
    ]
    list_filter = [
        "fulfillment_method",
        "is_active",
        "fulfillment_date",
        "canonical_requirement__major",
        "created_at",
    ]
    search_fields = [
        "student__person__family_name",
        "student__person__personal_name",
        "student__student_id",
        "canonical_requirement__required_course__code",
        "canonical_requirement__name",
        "grade",
        "notes",
    ]
    ordering = ["-fulfillment_date", "student__person__family_name"]
    readonly_fields = [
        "created_at",
        "updated_at",
    ]
    autocomplete_fields = [
        "student",
        "canonical_requirement",
        "fulfilling_enrollment",
        "fulfilling_transfer",
        "fulfilling_exception",
    ]

    fieldsets = (
        (
            "Student and Requirement",
            {
                "fields": (
                    "student",
                    "canonical_requirement",
                ),
            },
        ),
        (
            "Fulfillment Details",
            {
                "fields": (
                    "fulfillment_method",
                    "fulfillment_date",
                    "grade",
                    "credits_earned",
                ),
            },
        ),
        (
            "Fulfillment Sources",
            {
                "fields": (
                    "fulfilling_enrollment",
                    "fulfilling_transfer",
                    "fulfilling_exception",
                ),
                "description": "Only one source should be set based on the fulfillment method.",
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "is_active",
                    "notes",
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

    @admin.display(description="Student", ordering="student__person__family_name")
    def student_name(self, obj):
        """Display student full name."""
        return obj.student.person.full_name

    @admin.display(description="Requirement", ordering="canonical_requirement__sequence_number")
    def requirement_display(self, obj):
        """Display requirement information."""
        req = obj.canonical_requirement
        if req.required_course:
            return f"#{req.sequence_number}: {req.required_course.code}"
        return f"#{req.sequence_number}: {req.name}"

    @admin.display(description="Fulfilled By")
    def fulfillment_display(self, obj):
        """Display how the requirement was fulfilled."""
        if obj.fulfilling_enrollment:
            enrollment = obj.fulfilling_enrollment
            course_code = enrollment.class_header.course.code
            term_code = enrollment.class_header.term.code
            return f"Course: {course_code} ({term_code})"
        elif obj.fulfilling_transfer:
            transfer = obj.fulfilling_transfer
            return f"Transfer: {transfer.external_course_code} from {transfer.external_institution}"
        elif obj.fulfilling_exception:
            exception = obj.fulfilling_exception
            if exception.is_waived:
                return "Waived"
            elif exception.fulfilling_course:
                return f"Exception: {exception.fulfilling_course.code}"
            else:
                return "Exception (other)"
        return "—"

    actions = ["mark_inactive", "mark_active", "recalculate_credits", "show_progress_summary"]

    def mark_inactive(self, request, queryset):
        """Mark selected fulfillments as inactive."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Marked {updated} fulfillment(s) as inactive.")

    mark_inactive.short_description = "Mark selected fulfillments as inactive"  # type: ignore

    def mark_active(self, request, queryset):
        """Mark selected fulfillments as active."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"Marked {updated} fulfillment(s) as active.")

    mark_active.short_description = "Mark selected fulfillments as active"  # type: ignore

    def recalculate_credits(self, request, queryset):
        """Recalculate credits earned for selected fulfillments."""
        updated = 0
        for fulfillment in queryset:
            if fulfillment.fulfilling_enrollment:
                # Use course credits as earned credits for passing grades
                enrollment = fulfillment.fulfilling_enrollment
                course_credits = enrollment.class_header.course.credits or 1
                if fulfillment.grade and fulfillment.grade.upper().replace("+", "").replace("-", "") in [
                    "A",
                    "B",
                    "C",
                    "D",
                ]:
                    fulfillment.credits_earned = course_credits
                    fulfillment.save()
                    updated += 1
            elif fulfillment.fulfilling_transfer:
                # Use transfer credit awarded credits
                transfer = fulfillment.fulfilling_transfer
                if transfer.awarded_credits:
                    fulfillment.credits_earned = transfer.awarded_credits
                    fulfillment.save()
                    updated += 1

        self.message_user(request, f"Recalculated credits for {updated} fulfillment(s).")

    recalculate_credits.short_description = "Recalculate credits earned"  # type: ignore

    def show_progress_summary(self, request, queryset):
        """Show degree progress summary for selected students."""
        from collections import defaultdict

        # Group by student-major combinations
        student_majors = defaultdict(set)
        for fulfillment in queryset.select_related("student", "canonical_requirement__major"):
            student_majors[fulfillment.student].add(fulfillment.canonical_requirement.major)

        summaries = []
        for student, majors in student_majors.items():
            for major in majors:
                progress = StudentDegreeProgress.get_student_progress(student, major)
                summaries.append(progress)

        # Display summary
        message_parts = ["<br><strong>Degree Progress Summary:</strong><br>"]
        for summary in summaries:
            completion = summary["completion_percentage"]
            color = "green" if completion >= 75 else "orange" if completion >= 50 else "red"

            message_parts.append(
                f"<div style='margin: 5px 0; padding: 5px; border-left: 3px solid {color};'>"
                f"<strong>{summary['student']}</strong> - {summary['major']}<br>"
                f"Progress: <strong style='color: {color};'>{completion}%</strong> "
                f"({summary['completed_requirements']}/{summary['total_requirements']} requirements)<br>"
                f"Credits: {summary['credits_completed']:.1f}/{summary['total_credits_required']:.1f}"
                f"</div>"
            )

        from django.utils.safestring import mark_safe

        self.message_user(request, mark_safe("".join(message_parts)))

    show_progress_summary.short_description = "Show degree progress summary for selected students"  # type: ignore

    # Remove this method since we now use list_select_related


@admin.register(StudentRequirementException)
class StudentRequirementExceptionAdmin(admin.ModelAdmin):
    """Admin interface for student requirement exceptions."""

    list_display = [
        "student_name",
        "requirement_display",
        "exception_display",
        "exception_type",
        "status_display",
        "approved_date",
    ]
    list_select_related = [
        "student",
        "student__person",
        "canonical_requirement",
        "canonical_requirement__major",
        "canonical_requirement__required_course",
        "fulfilling_course",
        "fulfilling_transfer_credit",
        "effective_term",
        "expiration_term",
        "requested_by",
        "approved_by",
    ]
    list_filter = [
        "exception_type",
        "approval_status",
        "effective_term",
        "created_at",
    ]
    search_fields = [
        "student__person__family_name",
        "student__person__personal_name",
        "canonical_requirement__required_course__code",
        "fulfilling_course__code",
        "reason",
    ]
    ordering = ["-created_at"]
    readonly_fields = [
        "exception_credits",
        "created_at",
        "updated_at",
        "requested_by",
        "approved_by",
        "approval_date",
    ]
    autocomplete_fields = [
        "student",
        "canonical_requirement",
        "fulfilling_course",
        "fulfilling_transfer_credit",
        "effective_term",
        "expiration_term",
    ]

    fieldsets = (
        (
            "Student and Requirement",
            {
                "fields": (
                    "student",
                    "canonical_requirement",
                ),
            },
        ),
        (
            "Exception Details",
            {
                "fields": (
                    "exception_type",
                    "fulfilling_course",
                    "fulfilling_transfer_credit",
                    "is_waived",
                    "exception_credits",
                ),
            },
        ),
        (
            "Justification",
            {
                "fields": (
                    "reason",
                    "supporting_documentation",
                ),
            },
        ),
        (
            "Validity",
            {
                "fields": (
                    "effective_term",
                    "expiration_term",
                ),
            },
        ),
        (
            "Approval Workflow",
            {
                "fields": (
                    "approval_status",
                    "requested_by",
                    "approved_by",
                    "approval_date",
                    "rejection_reason",
                    "notes",
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

    @admin.display(description="Student")
    def student_name(self, obj):
        """Display student full name."""
        return obj.student.person.full_name

    @admin.display(
        description="Requirement",
        ordering="canonical_requirement__sequence_number",
    )
    def requirement_display(self, obj):
        """Display requirement information."""
        req = obj.canonical_requirement
        if req.required_course:
            return f"#{req.sequence_number}: {req.required_course.code}"
        return f"#{req.sequence_number}: {req.name}"

    @admin.display(description="Exception")
    def exception_display(self, obj):
        """Display exception details."""
        if obj.is_waived:
            return "→ Waived"
        elif obj.fulfilling_course:
            return f"→ {obj.fulfilling_course.code}"
        elif obj.fulfilling_transfer_credit:
            return f"→ Transfer: {obj.fulfilling_transfer_credit.external_course_code}"
        return "—"

    @admin.display(description="Status")
    def status_display(self, obj):
        """Display approval status with color."""
        status_colors = {
            obj.ApprovalStatus.PENDING: "orange",
            obj.ApprovalStatus.APPROVED: "green",
            obj.ApprovalStatus.REJECTED: "red",
            obj.ApprovalStatus.CONDITIONAL: "blue",
            obj.ApprovalStatus.EXPIRED: "gray",
        }
        color = status_colors.get(obj.approval_status, "black")
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            obj.get_approval_status_display(),
        )

    @admin.display(description="Approved")
    def approved_date(self, obj):
        """Display approval date."""
        if obj.approval_date:
            return obj.approval_date.strftime("%Y-%m-%d")
        return "—"

    actions = ["approve_exceptions", "reject_exceptions"]

    def approve_exceptions(self, request, queryset):
        """Approve selected exceptions using service layer."""
        updated = 0
        for exception in queryset.filter(approval_status=StudentRequirementException.ApprovalStatus.PENDING):
            try:
                StudentRequirementExceptionService.approve_exception(
                    exception,
                    request.user,
                    notes="Approved via admin action",
                )
                updated += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Error approving exception {exception.id}: {e!s}",
                    level="ERROR",
                )
        self.message_user(request, f"Successfully approved {updated} exception(s).")

    approve_exceptions.short_description = "Approve selected exceptions"  # type: ignore

    def reject_exceptions(self, request, queryset):
        """Reject selected exceptions using service layer."""
        updated = 0
        for exception in queryset.filter(approval_status=StudentRequirementException.ApprovalStatus.PENDING):
            try:
                StudentRequirementExceptionService.reject_exception(
                    exception,
                    request.user,
                    reason="Rejected via admin action",
                )
                updated += 1
            except Exception as e:
                self.message_user(
                    request,
                    f"Error rejecting exception {exception.id}: {e!s}",
                    level="ERROR",
                )
        self.message_user(request, f"Successfully rejected {updated} exception(s).")

    reject_exceptions.short_description = "Reject selected exceptions"  # type: ignore

    # Remove this method since we now use list_select_related


# Original StudentDegreeProgress model eliminated - was cached data that can be calculated dynamically
# Use the "Show student progress summary" action in StudentDegreeProgressAdmin to view progress summaries
