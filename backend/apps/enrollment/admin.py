import csv

from django.contrib import admin, messages
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from apps.common.admin_mixins import CollapsibleFilterMixin
from apps.common.utils import format_student_id
from apps.curriculum.models import Major, Term

from .models import (
    ClassHeaderEnrollment,
    ClassPartEnrollment,
    ClassSessionExemption,
    MajorDeclaration,
    ProgramEnrollment,
    SeniorProjectGroup,
    StudentCourseEligibility,
    StudentCycleStatus,
)
from .models_progression import (
    AcademicJourney,
    AcademicProgression,
    CertificateIssuance,
    ProgramMilestone,
    ProgramPeriod,
)
from .services import (
    EnrollmentService,
    MajorDeclarationService,
    PrerequisiteService,
)


class LimitedTermFilter(admin.SimpleListFilter):
    """Filter to show only the most recent 25 terms."""

    title = "Term (25 most recent)"
    parameter_name = "term"

    def lookups(self, request, model_admin):
        recent_terms = Term.objects.order_by("-start_date")[:25]
        return [(term.id, term.code) for term in recent_terms]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(class_header__term_id=self.value())
        return queryset


@admin.register(ProgramEnrollment)
class ProgramEnrollmentAdmin(admin.ModelAdmin):
    list_display = [
        "student_display",
        "program_display",
        "enrollment_type",
        "status",
        "start_date",
        "end_date",
        "terms_active",
    ]
    list_filter = [
        "enrollment_type",
        "status",
        "start_term",
        "is_joint",
        "start_date",
    ]
    search_fields = [
        "student__person__family_name",
        "student__person__personal_name",
        "student__person__full_name",
        "student__student_id",
        "program__name",
        "program__code",
    ]
    autocomplete_fields = [
        "student",
        "program",
        "start_term",
        "end_term",
        "enrolled_by",
    ]
    readonly_fields = ["is_active", "is_current"]
    date_hierarchy = "start_date"

    @admin.display(
        description="Student",
        ordering="student__student_id",
    )
    def student_display(self, obj):
        """Enhanced student display with left-zero padded student_id."""
        student_url = reverse(
            "admin:people_studentprofile_change",
            args=[obj.student.pk],
        )
        return format_html(
            '<a href="{}">{} ({})</a>',
            student_url,
            obj.student.person.full_name,
            format_student_id(obj.student.student_id),
        )

    @admin.display(
        description="Program",
        ordering="program__name",
    )
    def program_display(self, obj):
        """Enhanced program display with code and name."""
        program_url = reverse(
            "admin:curriculum_major_change",
            args=[obj.program.pk],
        )
        return format_html(
            '<a href="{}">{}</a><br><small>{}</small>',
            program_url,
            obj.program.name,
            f"Code: {obj.program.code}",
        )


@admin.register(MajorDeclaration)
class MajorDeclarationAdmin(admin.ModelAdmin):
    list_display = [
        "student_display",
        "major_display",
        "effective_date",
        "status_display",
        "declared_date",
        "consistency_display",
        "approval_status",
    ]
    list_filter = [
        "is_active",
        "effective_date",
        "declared_date",
        "requires_approval",
        "approved_date",
        "is_self_declared",
        "major__cycle__division",
        "major",
    ]
    search_fields = [
        "student__person__personal_name",
        "student__person__family_name",
        "student__student_id",
        "major__name",
    ]
    autocomplete_fields = [
        "student",
        "major",
        "declared_by",
        "approved_by",
        "previous_declaration",
    ]
    readonly_fields = [
        "is_effective",
        "is_pending_approval",
        "is_major_change",
        "consistency_report",
        "declaration_analysis",
    ]
    date_hierarchy = "effective_date"

    actions = ["approve_declarations", "generate_consistency_reports"]

    def get_queryset(self, request):
        """Optimize the queryset to prevent N+1 queries in the list display."""
        queryset = super().get_queryset(request)
        # Pre-fetch related objects needed by the display methods
        queryset = queryset.select_related("student__person", "major__cycle", "approved_by")
        return queryset

    fieldsets = (
        (
            "Declaration Information",
            {
                "fields": (
                    "student",
                    "major",
                    "effective_date",
                    "declared_date",
                    "is_active",
                ),
            },
        ),
        (
            "Change Management",
            {
                "fields": (
                    "previous_declaration",
                    "change_reason",
                    "supporting_documents",
                ),
            },
        ),
        (
            "Administrative Details",
            {
                "fields": (
                    "declared_by",
                    "is_self_declared",
                    "requires_approval",
                    "approved_by",
                    "approved_date",
                    "notes",
                ),
            },
        ),
        (
            "System Information",
            {
                "fields": (
                    "is_effective",
                    "is_pending_approval",
                    "is_major_change",
                    "consistency_report",
                    "declaration_analysis",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(
        description="Student",
        ordering="student__student_id",
    )
    def student_display(self, obj):
        """Enhanced student display with link to student admin."""
        student_url = reverse(
            "admin:people_studentprofile_change",
            args=[obj.student.pk],
        )
        return format_html(
            '<a href="{}">{} ({})</a>',
            student_url,
            obj.student.person.full_name,
            format_student_id(obj.student.student_id),
        )

    @admin.display(
        description="Major",
        ordering="major__name",
    )
    def major_display(self, obj):
        """Enhanced major display with link to major admin."""
        major_url = reverse(
            "admin:curriculum_major_change",
            args=[obj.major.pk],
        )
        return format_html(
            '<a href="{}">{}</a><br><small>{}</small>',
            major_url,
            obj.major.name,
            obj.major.cycle.name if obj.major.cycle else "No Cycle",
        )

    @admin.display(
        description="Status",
        ordering="is_active",
    )
    def status_display(self, obj):
        """Enhanced status display with color coding."""
        if not obj.is_active:
            return format_html('<span style="color: gray;">✗ Inactive</span>')
        if obj.is_effective:
            return format_html('<span style="color: green; font-weight: bold;">✓ Active & Effective</span>')
        return format_html('<span style="color: orange;">⏳ Active (Future)</span>')

    @admin.display(description="Consistency")
    def consistency_display(self, obj):
        """Display major declaration consistency status."""
        if not obj.pk:
            return "Save to check"

        # Get enrollment history major
        enrollment_major = obj.student.enrollment_history_major

        # If no enrollment history, nothing to check
        if not enrollment_major:
            return format_html('<span style="color: blue;">i No enrollment history</span>')

        # Check if enrollment major is a language program (IEAP, etc.)
        if enrollment_major.program_type == Major.ProgramType.LANGUAGE:
            # Language programs don't conflict with academic majors
            return format_html('<span style="color: gray;">Language: {}</span>', enrollment_major.name)

        # Both are academic programs - check for conflict
        has_conflict = obj.student.has_major_conflict

        if has_conflict:
            return format_html(
                '<span style="color: red;">⚠ Conflict with {}</span>',
                enrollment_major.name,
            )
        else:
            return format_html(
                '<span style="color: green;">✓ Consistent with {}</span>',
                enrollment_major.name,
            )

    @admin.display(description="Approval")
    def approval_status(self, obj):
        """Display approval status."""
        if not obj.requires_approval:
            return format_html('<span style="color: green;">No approval needed</span>')
        if obj.approved_date:
            return format_html(
                '<span style="color: green;">✓ Approved by {}</span>',
                obj.approved_by.get_full_name() if obj.approved_by else "Unknown",
            )
        return format_html('<span style="color: red;">⏳ Pending Approval</span>')

    @admin.display(description="Consistency Report")
    def consistency_report(self, obj):
        """Generate detailed consistency report."""
        if not obj.pk:
            return "Save declaration to see consistency report"

        report = MajorDeclarationService.generate_declaration_report(obj.student)

        # Format the report for display
        output = []

        # Current status
        output.append(f"<strong>Current Declaration:</strong> {report['current_declaration']['major'] or 'None'}")
        output.append(f"<strong>Enrollment History Major:</strong> {report['enrollment_history_major'] or 'None'}")

        # Consistency analysis
        if report["consistency_analysis"]["is_consistent"]:
            output.append('<span style="color: green;"><strong>Status:</strong> ✓ Consistent</span>')
        else:
            output.append('<span style="color: red;"><strong>Status:</strong> ⚠ Issues Found</span>')

            if report["consistency_analysis"]["issues"]:
                output.append("<strong>Issues:</strong>")
                for issue in report["consistency_analysis"]["issues"]:
                    output.append(f"• {issue}")

            if report["consistency_analysis"]["conflicting_courses"]:
                output.append("<strong>Conflicting Courses:</strong>")
                for course in report["consistency_analysis"]["conflicting_courses"]:
                    output.append(f"• {course}")

        return format_html("<br>".join(output))

    @admin.display(description="Declaration Analysis")
    def declaration_analysis(self, obj):
        """Generate detailed declaration analysis."""
        if not obj.pk:
            return "Save declaration to see analysis"

        report = MajorDeclarationService.generate_declaration_report(obj.student)

        output = []

        # Declaration history
        if report["declaration_history"]:
            output.append("<strong>Declaration History:</strong>")
            for _i, decl in enumerate(report["declaration_history"][:3]):  # Show last 3
                status = "✓" if decl["is_active"] else "✗"
                output.append(f"{status} {decl['major']} (effective {decl['effective_date']})")
            if len(report["declaration_history"]) > 3:
                output.append(f"... and {len(report['declaration_history']) - 3} more")

        # Recommendations
        if report["recommendations"]:
            output.append("<br><strong>Recommendations:</strong>")
            for rec in report["recommendations"]:
                output.append(f"• {rec}")

        return format_html("<br>".join(output))

    @admin.action(description="Approve selected declarations")
    def approve_declarations(self, request, queryset):
        """Approve selected declarations that require approval."""
        approved_count = 0
        for declaration in queryset.filter(requires_approval=True, approved_date__isnull=True):
            declaration.approve_declaration(user=request.user, notes="Approved via admin bulk action")
            approved_count += 1

        if approved_count:
            messages.success(request, f"Approved {approved_count} major declarations.")
        else:
            messages.warning(request, "No declarations were eligible for approval.")

    @admin.action(description="Generate consistency reports")
    def generate_consistency_reports(self, request, queryset):
        """Generate consistency reports for selected declarations."""
        issues_found = 0
        total_checked = 0

        for declaration in queryset:
            report = MajorDeclarationService.generate_declaration_report(declaration.student)
            total_checked += 1
            if not report["consistency_analysis"]["is_consistent"]:
                issues_found += 1

        messages.info(
            request,
            f"Checked {total_checked} declarations. Found {issues_found} with consistency issues. "
            f"See individual records for details.",
        )


@admin.register(ClassHeaderEnrollment)
class ClassHeaderEnrollmentAdmin(CollapsibleFilterMixin, admin.ModelAdmin):
    list_display = [
        "student_display",
        "class_display",
        "term_display",
        "status_display",
        "enrollment_date",
        "final_grade",
    ]
    list_filter = [
        "status",
        "enrollment_date",
        "completion_date",
        "is_audit",
        "late_enrollment",
        LimitedTermFilter,  # Limited to 25 most recent terms
        "class_header__course__cycle__division",
        "class_header__course",
    ]

    # Removed the forced ACTIVE filter to allow viewing all enrollment records

    search_fields = [
        "student__person__personal_name",
        "student__person__family_name",
        "student__student_id",
        "class_header__course__code",
        "class_header__course__title",
    ]
    autocomplete_fields = ["student", "class_header", "enrolled_by"]
    readonly_fields = [
        "is_active",
        "is_completed",
        "enrollment_summary",
        "eligibility_check",
    ]
    date_hierarchy = "enrollment_date"

    actions = [
        "drop_selected_enrollments",
        "check_prerequisites",
        "export_class_roster",
    ]

    fieldsets = (
        (
            "Enrollment Information",
            {
                "fields": (
                    "student",
                    "class_header",
                    "status",
                    "enrollment_date",
                    "enrolled_by",
                ),
            },
        ),
        (
            "Academic Information",
            {
                "fields": (
                    "final_grade",
                    "grade_points",
                    "credits_earned",
                    "completion_date",
                    "is_audit",
                ),
            },
        ),
        (
            "Administrative",
            {"fields": ("late_enrollment", "notes", "is_active", "is_completed")},
        ),
        (
            "System Information",
            {
                "fields": ("enrollment_summary", "eligibility_check"),
                "classes": ("collapse",),
            },
        ),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "enrollment-wizard/",
                self.admin_site.admin_view(self.enrollment_wizard_view),
                name="enrollment_wizard",
            ),
            path(
                "bulk-enroll/",
                self.admin_site.admin_view(self.bulk_enroll_view),
                name="enrollment_bulk_enroll",
            ),
        ]
        return custom_urls + urls

    @admin.display(
        description="Student",
        ordering="student__student_id",
    )
    def student_display(self, obj):
        """Enhanced student display with link to student admin."""
        student_url = reverse(
            "admin:people_studentprofile_change",
            args=[obj.student.pk],
        )
        return format_html(
            '<a href="{}">{} ({})</a>',
            student_url,
            obj.student.person.full_name,
            format_student_id(obj.student.student_id),
        )

    @admin.display(
        description="Class",
        ordering="class_header__course__code",
    )
    def class_display(self, obj):
        """Enhanced class display with course and section info."""
        class_url = reverse(
            "admin:scheduling_classheader_change",
            args=[obj.class_header.pk],
        )
        return format_html(
            '<a href="{}">{} Section {}</a><br><small>{}</small>',
            class_url,
            obj.class_header.course.code,
            obj.class_header.section_id,
            obj.class_header.course.title,
        )

    @admin.display(
        description="Term",
        ordering="class_header__term__start_date",
    )
    def term_display(self, obj):
        """Enhanced term display with term name and start date stacked."""
        term_url = reverse(
            "admin:curriculum_term_change",
            args=[obj.class_header.term.pk],
        )
        return format_html(
            '<a href="{}">{}</a><br><small>{}</small>',
            term_url,
            obj.class_header.term.code,
            (
                obj.class_header.term.start_date.strftime("%b %d, %Y")
                if obj.class_header.term.start_date
                else "No Date"
            ),
        )

    @admin.display(
        description="Status",
        ordering="status",
    )
    def status_display(self, obj):
        """Enhanced status display with color coding."""
        status_colors = {
            "ENROLLED": "green",
            "ACTIVE": "blue",
            "DROPPED": "red",
            "COMPLETED": "purple",
            "FAILED": "darkred",
        }
        color = status_colors.get(obj.status, "black")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    def get_queryset(self, request):
        """Optimize queryset with proper select_related fields."""
        qs = super().get_queryset(request)
        return qs.select_related(
            "student__person",
            "class_header__course",
            "class_header__term",
            "class_header__instructor__person",
            "enrolled_by",
        )

    @admin.display(description="Enrollment Summary")
    def enrollment_summary(self, obj):
        """Comprehensive enrollment summary."""
        if not obj.pk:
            return "Save enrollment to see summary"

        summary = []
        summary.append(f"<strong>Enrollment Date:</strong> {obj.enrollment_date}")
        summary.append(f"<strong>Enrolled By:</strong> {obj.enrolled_by}")

        if obj.notes:
            summary.append(f"<strong>Notes:</strong> {obj.notes}")

        return format_html("<br>".join(summary))

    @admin.display(description="Eligibility Status")
    def eligibility_check(self, obj):
        """Show course eligibility information."""
        if not obj.pk:
            return "Save enrollment to check eligibility"

        eligibility = PrerequisiteService.check_course_eligibility(
            obj.student,
            obj.class_header.course,
            obj.class_header.term,
        )

        if eligibility.eligible:
            status = '<span style="color: green;">✓ Eligible</span>'
        else:
            status = '<span style="color: red;">✗ Not Eligible</span>'

        details = []
        if eligibility.requirements_met:
            details.append(
                "<strong>Requirements Met:</strong><br>" + "<br>".join(eligibility.requirements_met),
            )
        if eligibility.requirements_missing:
            details.append(
                "<strong>Missing Requirements:</strong><br>" + "<br>".join(eligibility.requirements_missing),
            )
        if eligibility.warnings:
            details.append(
                "<strong>Warnings:</strong><br>" + "<br>".join(eligibility.warnings),
            )

        return format_html("{}<br><br>{}", status, "<br><br>".join(details))

    @admin.action(description="Drop selected enrollments")
    def drop_selected_enrollments(self, request, queryset):
        """Drop selected enrollments."""
        dropped_count = 0
        for enrollment in queryset.filter(
            status__in=["ENROLLED", "ACTIVE"],
        ):
            result = EnrollmentService.drop_student(
                enrollment,
                request.user,
                "Dropped via admin action",
            )
            if result.success:
                dropped_count += 1

        if dropped_count:
            messages.success(
                request,
                f"Dropped {dropped_count} enrollments.",
            )
        else:
            messages.warning(request, "No enrollments could be dropped.")

    @admin.action(description="Check prerequisites")
    def check_prerequisites(self, request, queryset):
        """Check prerequisites for selected enrollments."""
        checked_count = 0
        issues_found = 0

        for enrollment in queryset:
            eligibility = PrerequisiteService.check_course_eligibility(
                enrollment.student,
                enrollment.class_header.course,
                enrollment.class_header.term,
            )
            checked_count += 1
            if not eligibility.eligible:
                issues_found += 1

        messages.info(
            request,
            f"Checked {checked_count} enrollments. Found {issues_found} prerequisite issues. "
            f"Check individual records for details.",
        )

    @admin.action(description="Export class roster to CSV")
    def export_class_roster(self, request, queryset):
        """Export class roster to CSV."""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="class_roster.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Student ID",
                "Student Name",
                "Class",
                "Section",
                "Status",
                "Enrollment Date",
                "Grade",
            ],
        )

        for enrollment in queryset:
            writer.writerow(
                [
                    format_student_id(enrollment.student.student_id),
                    enrollment.student.person.full_name,
                    enrollment.class_header.course.code,
                    enrollment.class_header.section_id,
                    enrollment.status,
                    enrollment.enrollment_date,
                    enrollment.final_grade or "",
                ],
            )

        return response

    def enrollment_wizard_view(self, request):
        """Guided enrollment wizard for staff."""
        context = {
            "title": "Enrollment Wizard",
            "opts": self.model._meta,
        }

        if request.method == "POST":
            # Handle enrollment wizard form submission
            # This would contain the enrollment wizard logic
            pass

        return TemplateResponse(
            request,
            "admin/enrollment/enrollment_wizard.html",
            context,
        )

    def bulk_enroll_view(self, request):
        """Bulk enrollment interface."""
        context = {
            "title": "Bulk Enrollment",
            "opts": self.model._meta,
        }

        if request.method == "POST":
            # Handle bulk enrollment
            # This would contain bulk enrollment logic
            pass

        return TemplateResponse(request, "admin/enrollment/bulk_enroll.html", context)


@admin.register(ClassPartEnrollment)
class ClassPartEnrollmentAdmin(CollapsibleFilterMixin, admin.ModelAdmin):
    list_display = [
        "student_display",
        "class_part",
        "is_active",
        "enrollment_date",
    ]
    list_filter = [
        "is_active",
        "enrollment_date",
        "class_part__class_part_type",
        "class_part__class_session__class_header__term",
    ]
    search_fields = [
        "student__person__family_name",
        "student__person__personal_name",
        "student__person__full_name",
        "class_part__class_session__class_header__course__code",
    ]
    autocomplete_fields = ["student", "class_part"]

    @admin.display(
        description="Student",
        ordering="student__student_id",
    )
    def student_display(self, obj):
        """Enhanced student display with left-zero padded student_id."""
        student_url = reverse(
            "admin:people_studentprofile_change",
            args=[obj.student.pk],
        )
        return format_html(
            '<a href="{}">{} ({})</a>',
            student_url,
            obj.student.person.full_name,
            format_student_id(obj.student.student_id),
        )

    date_hierarchy = "enrollment_date"


@admin.register(ClassSessionExemption)
class ClassSessionExemptionAdmin(admin.ModelAdmin):
    list_display = [
        "class_header_enrollment",
        "class_session",
        "exemption_reason",
        "exempted_by",
        "exemption_date",
    ]
    list_filter = [
        "exemption_date",
        "class_session__session_number",
        "class_session__class_header__term",
        "class_session__class_header__course",
    ]
    search_fields = [
        "class_header_enrollment__student__person__family_name",
        "class_header_enrollment__student__person__personal_name",
        "class_header_enrollment__student__person__full_name",
        "class_session__class_header__course__code",
        "exemption_reason",
    ]
    autocomplete_fields = ["class_header_enrollment", "class_session", "exempted_by"]
    date_hierarchy = "exemption_date"


@admin.register(StudentCourseEligibility)
class StudentCourseEligibilityAdmin(admin.ModelAdmin):
    list_display = [
        "student_display",
        "course",
        "term",
        "is_eligible",
        "is_retake",
        "previous_attempts",
        "last_calculated",
    ]
    list_filter = [
        "is_eligible",
        "is_retake",
        "term",
        "last_calculated",
        "retry_priority_score",
    ]
    search_fields = [
        "student__person__family_name",
        "student__person__personal_name",
        "student__person__full_name",
        "course__code",
        "course__name",
    ]
    autocomplete_fields = ["student", "course", "term"]

    @admin.display(
        description="Student",
        ordering="student__student_id",
    )
    def student_display(self, obj):
        """Enhanced student display with left-zero padded student_id."""
        student_url = reverse(
            "admin:people_studentprofile_change",
            args=[obj.student.pk],
        )
        return format_html(
            '<a href="{}">{} ({})</a>',
            student_url,
            obj.student.person.full_name,
            format_student_id(obj.student.student_id),
        )

    filter_horizontal = ["missing_prerequisites"]
    readonly_fields = ["eligibility_summary", "last_calculated"]

    actions = ["recalculate_eligibility"]

    @admin.action(description="Recalculate eligibility status")
    def recalculate_eligibility(self, request, queryset):
        updated = 0
        for eligibility in queryset:
            eligibility.recalculate_eligibility()
            updated += 1
        self.message_user(request, f"Recalculated {updated} eligibility records.")


# Academic Progression Admin Classes


class ProgramMilestoneInline(admin.TabularInline):
    """Inline for program milestones in academic journey."""

    model = ProgramMilestone
    extra = 0
    fields = ["milestone_type", "milestone_date", "program", "level", "is_inferred", "confidence_score"]
    readonly_fields = ["is_inferred", "confidence_score"]
    ordering = ["milestone_date"]


class ProgramPeriodInline(admin.TabularInline):
    """Inline for program periods showing complete academic trajectory."""

    model = ProgramPeriod
    extra = 0
    fields = [
        "period_display",
        "transition_date",
        "duration_display",
        "credits_display",
        "gpa_display",
        "completion_status",
    ]
    readonly_fields = fields  # All fields are read-only
    ordering = ["sequence_number"]
    can_delete = False
    verbose_name = "Program Period"
    verbose_name_plural = "Academic Trajectory - Program Periods"

    def has_add_permission(self, request, obj=None):
        return False

    def period_display(self, obj):
        """Display program period with transition info."""
        if obj.transition_type == "INITIAL":
            prefix = "Started with"
        elif obj.transition_type == "CHANGE":
            prefix = f"Changed from {obj.from_program_type} to"
        elif obj.transition_type == "PROGRESSION":
            prefix = "Progressed to"
        else:
            prefix = "Continued in"

        program = f"{obj.to_program_type} - {obj.program_name}"
        if obj.language_level:
            program += f" (Level {obj.language_level})"

        return f"{prefix} {program}"

    period_display.short_description = "Program Transition"

    def duration_display(self, obj):
        """Display duration in a readable format."""
        return f"{obj.duration_months:.1f} months ({obj.term_count} terms)"

    duration_display.short_description = "Duration"

    def credits_display(self, obj):
        """Display credits with completion rate."""
        if obj.total_credits > 0:
            completion_rate = (obj.completed_credits / obj.total_credits) * 100
            return f"{obj.completed_credits:.0f}/{obj.total_credits:.0f} ({completion_rate:.0f}%)"
        return "N/A"

    credits_display.short_description = "Credits (Completed/Total)"

    def gpa_display(self, obj):
        """Display GPA with formatting."""
        if obj.gpa:
            return f"{obj.gpa:.2f}"
        return "N/A"

    gpa_display.short_description = "GPA"


@admin.register(ProgramPeriod)
class ProgramPeriodAdmin(admin.ModelAdmin):
    """Admin for viewing all program periods across students."""

    list_display = [
        "student_display",
        "program_display",
        "transition_date",
        "duration_months",
        "completed_credits",
        "gpa",
        "completion_status",
    ]

    list_filter = [
        "to_program_type",
        "completion_status",
        "transition_type",
        ("transition_date", admin.DateFieldListFilter),
    ]

    search_fields = [
        "journey__student__student_id",
        "journey__student__person__family_name",
        "journey__student__person__given_name",
        "program_name",
    ]

    ordering = ["-transition_date"]

    readonly_fields = [
        "journey",
        "transition_type",
        "transition_date",
        "from_program_type",
        "to_program_type",
        "to_program",
        "program_name",
        "duration_days",
        "duration_months",
        "term_count",
        "total_credits",
        "completed_credits",
        "gpa",
        "completion_status",
        "language_level",
        "sequence_number",
        "confidence_score",
        "notes",
    ]

    @admin.display(description="Student", ordering="journey__student__student_id")
    def student_display(self, obj):
        """Display student with link."""
        student = obj.journey.student
        url = reverse("admin:people_studentprofile_change", args=[student.pk])
        return format_html(
            '<a href="{}">{} ({})</a>',
            url,
            student.person.full_name,
            format_student_id(student.student_id),
        )

    @admin.display(description="Program")
    def program_display(self, obj):
        """Display program with transition info."""
        if obj.transition_type == "INITIAL":
            arrow = "➡️"
        elif obj.transition_type == "CHANGE":
            arrow = "🔄"
        elif obj.transition_type == "PROGRESSION":
            arrow = "⬆️"
        else:
            arrow = "➡️"

        program = f"{arrow} {obj.to_program_type}"
        if obj.language_level:
            program += f" (L{obj.language_level})"

        return program


@admin.register(AcademicJourney)
class AcademicJourneyAdmin(admin.ModelAdmin):
    """Admin for academic journey with review workflow."""

    list_display = [
        "student_display",
        "program_type",
        "program_display",
        "transition_status",
        "start_date",
        "stop_date",
        "duration_in_terms",
        "confidence_score_display",
        "requires_review_display",
    ]

    list_filter = [
        "transition_status",
        "program_type",
        "requires_review",
        "confidence_score",
        "data_source",
        "program",
        "start_date",
    ]

    search_fields = [
        "student__person__family_name",
        "student__person__personal_name",
        "student__person__full_name",
        "student__student_id",
    ]

    readonly_fields = [
        "data_source",
        "confidence_score",
        "data_issues",
        "last_manual_review",
    ]

    fieldsets = (
        ("Student Information", {"fields": ("student", "program_type", "program")}),
        (
            "Period Details",
            {
                "fields": (
                    "start_date",
                    "stop_date",
                    "start_term",
                    "term_code",
                    "duration_in_terms",
                    "transition_status",
                )
            },
        ),
        (
            "Data Quality",
            {
                "fields": (
                    "data_source",
                    "confidence_score",
                    "data_issues",
                    "requires_review",
                    "last_manual_review",
                    "notes",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    inlines = [ProgramPeriodInline, ProgramMilestoneInline]

    actions = ["mark_as_reviewed", "recalculate_journey", "export_low_confidence"]

    @admin.display(description="Student", ordering="student__student_id")
    def student_display(self, obj):
        """Enhanced student display."""
        student_url = reverse("admin:people_studentprofile_change", args=[obj.student.pk])
        return format_html(
            '<a href="{}">{} ({})</a>',
            student_url,
            obj.student.person.full_name,
            format_student_id(obj.student.student_id),
        )

    @admin.display(description="Confidence", ordering="confidence_score")
    def confidence_score_display(self, obj):
        """Display confidence score with color coding."""
        score = obj.confidence_score
        if score >= 0.8:
            color = "green"
            icon = "✅"
        elif score >= 0.6:
            color = "orange"
            icon = "⚠️"
        else:
            color = "red"
            icon = "❌"

        return format_html('<span style="color: {};">{} {}</span>', color, icon, f"{float(score):.2f}")

    @admin.display(description="Review", boolean=True, ordering="requires_review")
    def requires_review_display(self, obj):
        """Display review requirement status."""
        return obj.requires_review

    @admin.display(description="Program", ordering="program__name")
    def program_display(self, obj):
        """Display program name."""
        if obj.program:
            return obj.program.name
        return obj.program_type

    @admin.display(description="Academic Trajectory")
    def trajectory_summary(self, obj):
        """Display a summary of the student's academic trajectory."""
        periods = obj.program_periods.all().order_by("sequence_number")
        if not periods:
            return "No program data"

        trajectory_parts = []
        for period in periods:
            # Format each period
            status_icon = (
                "✅"
                if period.completion_status == "GRADUATED"
                else "📚"
                if period.completion_status == "ACTIVE"
                else "❌"
            )
            period_summary = f"{period.to_program_type}"
            if period.to_program_type in ["BA", "MA"]:
                period_summary += f" ({period.completed_credits:.0f}cr, {period.gpa:.2f}GPA)"
            elif period.language_level:
                period_summary += f" (L{period.language_level})"
            trajectory_parts.append(f"{status_icon}{period_summary}")

        return " → ".join(trajectory_parts)

    @admin.display(description="Complete Academic Journey")
    def journey_visualization(self, obj):
        """Display a detailed visualization of the student's academic journey."""
        periods = obj.program_periods.all().order_by("sequence_number")
        if not periods:
            return "No program data available"

        html_parts = ['<div style="font-family: monospace; line-height: 1.8;">']

        for i, period in enumerate(periods):
            # Status icon
            if period.completion_status == "GRADUATED":
                status_icon = "🎓"
                status_color = "green"
            elif period.completion_status == "COMPLETED":
                status_icon = "✅"
                status_color = "green"
            elif period.completion_status == "ACTIVE":
                status_icon = "📚"
                status_color = "blue"
            elif period.completion_status == "DROPPED":
                status_icon = "❌"
                status_color = "red"
            else:
                status_icon = "⏸️"
                status_color = "gray"

            # Build the period display
            html_parts.append(f'<div style="margin: 10px 0; padding: 10px; border-left: 3px solid {status_color};">')

            # Period header
            html_parts.append(f"<strong>{status_icon} {period.to_program_type} - {period.program_name}</strong><br>")

            # Duration and dates
            html_parts.append(
                f"📅 {period.transition_date} ({period.duration_months:.1f} months, {period.term_count} terms)<br>"
            )

            # Academic performance
            if period.to_program_type in ["BA", "MA"]:
                completion_rate = (
                    (period.completed_credits / period.total_credits * 100) if period.total_credits > 0 else 0
                )
                html_parts.append(
                    f"📊 Credits: {period.completed_credits:.0f}/{period.total_credits:.0f} ({completion_rate:.0f}%)"
                )
                if period.gpa:
                    html_parts.append(f" | GPA: {period.gpa:.2f}")
                html_parts.append("<br>")
            elif period.language_level:
                html_parts.append(f"📈 Level: {period.language_level}<br>")

            # Status
            html_parts.append(
                f'Status: <span style="color: {status_color}; font-weight: bold;">{period.completion_status}</span>'
            )

            html_parts.append("</div>")

            # Add arrow between periods
            if i < len(periods) - 1:
                html_parts.append('<div style="text-align: center; font-size: 20px;">⬇️</div>')

        html_parts.append("</div>")

        return format_html("".join(html_parts))

    @admin.action(description="Mark selected journeys as reviewed")
    def mark_as_reviewed(self, request, queryset):
        """Mark journeys as manually reviewed."""
        count = 0
        for journey in queryset:
            journey.mark_reviewed(user=request.user, notes="Bulk review from admin")
            count += 1

        self.message_user(request, f"Successfully marked {count} journeys as reviewed.", messages.SUCCESS)

    @admin.action(description="Recalculate academic journeys")
    def recalculate_journey(self, request, queryset):
        """Recalculate selected journeys."""
        # This would use the ProgressionBuilder service
        self.message_user(request, "Journey recalculation not yet implemented.", messages.WARNING)

    @admin.action(description="Export low confidence records")
    def export_low_confidence(self, request, queryset):
        """Export low confidence records to CSV."""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="low_confidence_journeys.csv"'

        writer = csv.writer(response)
        writer.writerow(
            ["Student ID", "Student Name", "Confidence Score", "Data Issues", "Current Program", "Journey Status"]
        )

        for journey in queryset.filter(confidence_score__lt=0.7):
            writer.writerow(
                [
                    journey.student.student_id,
                    journey.student.person.full_name,
                    float(journey.confidence_score),
                    ", ".join(journey.data_issues),
                    journey.program.name if journey.program else "Unknown",
                    journey.get_transition_status_display(),
                ]
            )

        return response

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        # Only select_related on non-nullable fields to avoid issues
        return qs.select_related(
            "student__person",
            "program",
        ).prefetch_related(
            "start_term",  # Use prefetch_related for nullable FK
        )


@admin.register(ProgramMilestone)
class ProgramMilestoneAdmin(admin.ModelAdmin):
    """Admin for program milestones."""

    list_display = [
        "journey_student",
        "milestone_type",
        "milestone_date",
        "program",
        "level",
        "is_inferred",
        "confidence_score",
    ]

    list_filter = [
        "milestone_type",
        "is_inferred",
        "confidence_score",
        "program",
        "academic_term",
    ]

    search_fields = [
        "journey__student__person__family_name",
        "journey__student__person__personal_name",
        "journey__student__student_id",
    ]

    date_hierarchy = "milestone_date"

    @admin.display(description="Student", ordering="journey__student")
    def journey_student(self, obj):
        """Display student from journey."""
        return f"{obj.journey.student.person.full_name} ({obj.journey.student.student_id})"


@admin.register(AcademicProgression)
class AcademicProgressionAdmin(admin.ModelAdmin):
    """Admin for denormalized progression view."""

    list_display = [
        "student_name",
        "student_id_number",
        "current_status",
        "ba_major",
        "ba_completion_status",
        "time_to_ba_days",
        "last_updated",
    ]

    list_filter = [
        "current_status",
        "ba_completion_status",
        "ma_completion_status",
        "language_completion_status",
        "ba_major",
        "ma_program",
    ]

    search_fields = [
        "student_name",
        "student_id_number",
    ]

    readonly_fields = [field.name for field in AcademicProgression._meta.fields]

    def has_add_permission(self, request):
        """Prevent adding records (populated automatically)."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deleting records."""
        return False


@admin.register(CertificateIssuance)
class CertificateIssuanceAdmin(admin.ModelAdmin):
    """Admin for certificate issuance tracking."""

    list_display = [
        "certificate_number",
        "student_display",
        "certificate_type",
        "program",
        "issue_date",
        "is_collected",
        "collected_date",
    ]

    list_filter = [
        "certificate_type",
        "issue_date",
        ("collected_date", admin.EmptyFieldListFilter),
        "program",
    ]

    search_fields = [
        "certificate_number",
        "student__person__family_name",
        "student__person__personal_name",
        "student__student_id",
    ]

    date_hierarchy = "issue_date"

    fieldsets = (
        (
            "Certificate Information",
            {
                "fields": (
                    "student",
                    "certificate_type",
                    "certificate_number",
                    "issue_date",
                )
            },
        ),
        (
            "Academic Details",
            {
                "fields": (
                    "program",
                    "completion_level",
                    "gpa",
                    "honors",
                )
            },
        ),
        (
            "Collection Tracking",
            {
                "fields": (
                    "issued_by",
                    "printed_date",
                    "collected_date",
                    "collected_by",
                )
            },
        ),
        (
            "Notes",
            {
                "fields": ("notes",),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["mark_as_collected", "export_certificates"]

    @admin.display(description="Student", ordering="student")
    def student_display(self, obj):
        """Enhanced student display."""
        return f"{obj.student.person.full_name} ({obj.student.student_id})"

    @admin.display(description="Collected", boolean=True)
    def is_collected(self, obj):
        """Check if certificate has been collected."""
        return obj.is_collected

    @admin.action(description="Mark certificates as collected")
    def mark_as_collected(self, request, queryset):
        """Mark certificates as collected."""
        count = 0
        for cert in queryset.filter(collected_date__isnull=True):
            cert.mark_collected()
            count += 1

        self.message_user(request, f"Marked {count} certificates as collected.", messages.SUCCESS)

    @admin.action(description="Export certificate list")
    def export_certificates(self, request, queryset):
        """Export certificates to CSV."""
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="certificates.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "Certificate Number",
                "Student ID",
                "Student Name",
                "Certificate Type",
                "Program",
                "Issue Date",
                "Collected",
            ]
        )

        for cert in queryset:
            writer.writerow(
                [
                    cert.certificate_number,
                    cert.student.student_id,
                    cert.student.person.full_name,
                    cert.get_certificate_type_display(),
                    cert.program.name if cert.program else "",
                    cert.issue_date,
                    "Yes" if cert.is_collected else "No",
                ]
            )

        return response


@admin.register(SeniorProjectGroup)
class SeniorProjectGroupAdmin(admin.ModelAdmin):
    """Admin interface for senior project groups."""

    list_display = [
        "project_title_display",
        "team_members_display",
        "course",
        "term_display",
        "advisor_display",
        "status_display",
        "defense_date",
        "is_graduated",
    ]

    list_filter = [
        "status",
        "is_graduated",
        "course",
        "term",
        "registration_term",
        "defense_date",
        "registration_date",
        "advisor",
    ]

    search_fields = [
        "project_title",
        "course__code",
        "course__title",
        "advisor__person__full_name",
        "students__person__full_name",
        "students__student_id",
        "notes",
    ]

    autocomplete_fields = [
        "course",
        "term",
        "registration_term",
        "advisor",
    ]

    filter_horizontal = ["students"]

    readonly_fields = [
        "team_size",
        "created_at",
        "updated_at",
    ]

    date_hierarchy = "defense_date"

    fieldsets = (
        (
            "Project Information",
            {
                "fields": (
                    "project_title",
                    "course",
                    "term",
                    "advisor",
                    "status",
                ),
            },
        ),
        (
            "Team Members",
            {
                "fields": (
                    "students",
                    "team_size",
                ),
            },
        ),
        (
            "Registration Details",
            {
                "fields": (
                    "registration_date",
                    "registration_term",
                ),
            },
        ),
        (
            "Completion Status",
            {
                "fields": (
                    "defense_date",
                    "graduation_date",
                    "is_graduated",
                ),
            },
        ),
        (
            "Additional Information",
            {
                "fields": ("notes",),
                "classes": ("collapse",),
            },
        ),
        (
            "System Information",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Project Title", ordering="project_title")
    def project_title_display(self, obj):
        """Display truncated project title."""
        title = obj.project_title or "Untitled Project"
        if len(title) > 50:
            return f"{title[:47]}..."
        return title

    @admin.display(description="Term", ordering="term__start_date")
    def term_display(self, obj):
        """Enhanced term display with link."""
        if not obj.term:
            return "No Term"
        term_url = reverse("admin:curriculum_term_change", args=[obj.term.pk])
        return format_html('<a href="{}">{}</a>', term_url, obj.term.code)

    @admin.display(description="Advisor", ordering="advisor__person__full_name")
    def advisor_display(self, obj):
        """Enhanced advisor display with link."""
        if not obj.advisor:
            return "No Advisor"
        advisor_url = reverse("admin:people_teacherprofile_change", args=[obj.advisor.pk])
        return format_html(
            '<a href="{}">{}</a>',
            advisor_url,
            obj.advisor.person.full_name,
        )

    @admin.display(description="Team Members")
    def team_members_display(self, obj):
        """Display team members in format: NAME (ID), NAME (ID)."""
        students = obj.students.select_related("person").order_by("person__family_name", "person__personal_name")
        if not students.exists():
            return format_html('<span style="color: gray; font-style: italic;">No members</span>')

        members = []
        for student in students:
            # Format student ID with left zero padding
            formatted_id = f"{student.student_id:05d}"
            member_str = f"{student.person.full_name} ({formatted_id})"
            members.append(member_str)

        # Join with comma and space, but wrap long lists
        member_text = ", ".join(members)
        if len(member_text) > 80:  # If too long, show on multiple lines
            return format_html("<br>".join(members))
        else:
            return member_text

    @admin.display(description="Team Size")
    def team_size(self, obj):
        """Display number of students in the team."""
        return obj.students.count()

    @admin.display(description="Status", ordering="status")
    def status_display(self, obj):
        """Enhanced status display with color coding."""
        status_colors = {
            "PROPOSED": "blue",
            "APPROVED": "green",
            "IN_PROGRESS": "orange",
            "COMPLETED": "purple",
            "CANCELLED": "red",
        }
        color = status_colors.get(obj.status, "black")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    def get_queryset(self, request):
        """Optimize queryset with prefetch_related for students and their person data."""
        qs = super().get_queryset(request)
        return qs.select_related(
            "course",
            "term",
            "registration_term",
            "advisor__person",
        ).prefetch_related(
            "students__person",
        )


@admin.register(StudentCycleStatus)
class StudentCycleStatusAdmin(admin.ModelAdmin):
    """Admin interface for student cycle status tracking."""

    list_display = [
        "student",
        "cycle_type",
        "source_program",
        "target_program",
        "detected_date",
        "is_active",
        "deactivated_date",
    ]
    list_filter = [
        "cycle_type",
        "is_active",
        "detected_date",
        "target_program__program_type",
    ]
    search_fields = [
        "student__student_id",
        "student__person__first_name",
        "student__person__last_name",
        "target_program__name",
        "source_program__name",
    ]
    date_hierarchy = "detected_date"
    readonly_fields = ["detected_date", "created_at", "updated_at"]
    autocomplete_fields = ["student", "source_program", "target_program"]

    fieldsets = (
        ("Student Information", {"fields": ("student", "cycle_type")}),
        ("Program Transition", {"fields": ("source_program", "target_program")}),
        ("Status", {"fields": ("is_active", "detected_date", "deactivated_date", "deactivation_reason")}),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ["collapse"]}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("student__person", "source_program", "target_program")


# @admin.register(ProgramTransition)
class ProgramTransitionAdminDisabled(admin.ModelAdmin):
    """Admin for viewing program transitions."""

    list_display = [
        "student_display",
        "sequence_number",
        "transition_type",
        "from_program_type",
        "to_program_type",
        "program_name",
        "transition_date",
        "duration_display",
        "credits_display",
        "gpa_display",
        "completion_status_display",
    ]

    list_filter = [
        "transition_type",
        "to_program_type",
        "completion_status",
        "transition_date",
        ("journey__student__current_status", admin.ChoicesFieldListFilter),
    ]

    search_fields = [
        "journey__student__student_id",
        "journey__student__person__family_name",
        "journey__student__person__personal_name",
        "program_name",
    ]

    date_hierarchy = "transition_date"
    ordering = ["journey__student", "sequence_number"]

    readonly_fields = [
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "duration_years_display",
    ]

    fieldsets = (
        ("Student Information", {"fields": ("journey", "sequence_number")}),
        (
            "Transition Details",
            {
                "fields": (
                    "transition_type",
                    "transition_date",
                    "from_program_type",
                    "to_program_type",
                    "to_program",
                    "program_name",
                )
            },
        ),
        (
            "Duration & Performance",
            {
                "fields": (
                    "duration_days",
                    "duration_months",
                    "duration_years_display",
                    "term_count",
                    "total_credits",
                    "completed_credits",
                    "gpa",
                )
            },
        ),
        (
            "Completion",
            {
                "fields": (
                    "completion_status",
                    "language_level",
                    "confidence_score",
                    "notes",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "created_at",
                    "created_by",
                    "updated_at",
                    "updated_by",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description="Student", ordering="journey__student__student_id")
    def student_display(self, obj):
        """Display student with formatted ID."""
        student = obj.journey.student
        return format_html("{} ({})", student.person.full_name, format_student_id(student.student_id))

    @admin.display(description="Duration")
    def duration_display(self, obj):
        """Display duration in human-readable format."""
        if obj.duration_months < 12:
            return f"{obj.duration_months:.1f} months"
        else:
            years = obj.duration_years
            return f"{years:.1f} years"

    @admin.display(description="Credits")
    def credits_display(self, obj):
        """Display credits earned/attempted."""
        if obj.total_credits == 0:
            return "—"
        return format_html("{:.1f}/{:.1f}", obj.completed_credits, obj.total_credits)

    @admin.display(description="GPA")
    def gpa_display(self, obj):
        """Display GPA with formatting."""
        if obj.gpa is None:
            return "—"
        return f"{obj.gpa:.2f}"

    @admin.display(description="Status")
    def completion_status_display(self, obj):
        """Display completion status with color coding."""
        status_colors = {
            "ACTIVE": "green",
            "COMPLETED": "blue",
            "GRADUATED": "purple",
            "DROPPED": "red",
            "INACTIVE": "orange",
            "TRANSFERRED": "gray",
        }
        color = status_colors.get(obj.completion_status, "black")

        # Add level for language programs
        status_text = obj.get_completion_status_display()
        if obj.is_language_program and obj.language_level:
            status_text += f" (Level {obj.language_level})"

        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, status_text)

    @admin.display(description="Duration (Years)")
    def duration_years_display(self, obj):
        """Display duration in years."""
        return f"{obj.duration_years:.2f} years"

    def get_queryset(self, request):
        """Optimize queryset."""
        qs = super().get_queryset(request)
        return qs.select_related(
            "journey__student__person",
            "to_program",
        )
