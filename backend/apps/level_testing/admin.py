"""Django admin configuration for level testing models.

Provides comprehensive admin interfaces for managing test applications,
payments, duplicates, and test sessions. Follows clean architecture
principles with organized, searchable, and filterable interfaces.
"""

from django.contrib import admin
from django.contrib.admin import DateFieldListFilter
from django.urls import reverse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.level_testing.models import (
    DuplicateCandidate,
    PlacementTest,
    PotentialStudent,
    TestAttempt,
    TestPayment,
    TestSession,
)

# Test session constants
ENROLLMENT_WARNING_THRESHOLD = 80
ENROLLMENT_DANGER_THRESHOLD = 100


@admin.register(PotentialStudent)
class PotentialStudentAdmin(admin.ModelAdmin):
    """Admin interface for potential student applications."""

    list_display = [
        "test_number",
        "full_name_eng",
        "phone_number",
        "preferred_program",
        "status",
        "duplicate_status_display",
        "payment_status_display",
        "created_at",
    ]

    list_filter = [
        "status",
        "duplicate_check_status",
        "preferred_program",
        "preferred_time_slot",
        "current_school",
        "birth_province",
        ("created_at", DateFieldListFilter),
        ("date_of_birth", DateFieldListFilter),
    ]

    search_fields = [
        "test_number",
        "personal_name_eng",
        "family_name_eng",
        "personal_name_khm",
        "family_name_khm",
        "phone_number",
        "telegram_number",
        "personal_email",
    ]

    readonly_fields = [
        "application_id",
        "test_number",
        "current_age",
        "status_history",
        "duplicate_check_performed",
        "duplicate_check_cleared_at",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            _("Application Information"),
            {
                "fields": (
                    "application_id",
                    "test_number",
                    "status",
                    "status_history",
                    "created_at",
                    "updated_at",
                ),
            },
        ),
        (
            _("Personal Information"),
            {
                "fields": (
                    ("personal_name_eng", "family_name_eng"),
                    ("personal_name_khm", "family_name_khm"),
                    "preferred_gender",
                    ("date_of_birth", "current_age"),
                    "birth_province",
                ),
            },
        ),
        (
            _("Contact Information"),
            {
                "fields": (
                    "phone_number",
                    "telegram_number",
                    "personal_email",
                ),
            },
        ),
        (
            _("Educational Background"),
            {
                "fields": (
                    "current_school",
                    "other_school_name",
                    ("current_grade", "is_graduate"),
                    "last_english_school",
                    "last_english_level",
                    "last_english_textbook",
                    "last_english_date",
                ),
            },
        ),
        (
            _("Program Preferences"),
            {
                "fields": (
                    "preferred_program",
                    "preferred_time_slot",
                    "preferred_start_term",
                ),
            },
        ),
        (
            _("Additional Information"),
            {
                "fields": (
                    "first_time_at_puc",
                    "how_did_you_hear",
                    "comments",
                ),
            },
        ),
        (
            _("Conversion Information"),
            {
                "fields": (
                    "converted_person_id",
                    "converted_student_number",
                ),
            },
        ),
        (
            _("Duplicate Detection"),
            {
                "fields": (
                    "duplicate_check_performed",
                    "duplicate_check_status",
                    "duplicate_check_notes",
                    "duplicate_check_cleared_by",
                    "duplicate_check_cleared_at",
                ),
            },
        ),
    )

    actions = ["mark_as_registered", "mark_as_paid", "export_applications"]

    @admin.display(description=_("Duplicate Status"))
    def duplicate_status_display(self, obj):
        """Display duplicate check status with color coding."""
        status = obj.get_duplicate_check_status_display()
        colors = {
            "PENDING": "orange",
            "CONFIRMED_NEW": "green",
            "CONFIRMED_DUPLICATE": "red",
            "DEBT_CONCERN": "red",
            "MANUAL_REVIEW": "orange",
        }
        color = colors.get(obj.duplicate_check_status, "gray")
        return format_html('<span style="color: {};">{}</span>', color, status)

    @admin.display(description=_("Payment Status"))
    def payment_status_display(self, obj):
        """Display payment status with link to payment record."""
        try:
            payment = obj.test_payment
            if payment.is_paid:
                return format_html(
                    '<span style="color: green;">✓ ${}</span>',
                    payment.amount,
                )
            return format_html(
                '<span style="color: red;">✗ ${}</span>',
                payment.amount,
            )
        except TestPayment.DoesNotExist:
            return format_html('<span style="color: gray;">No payment record</span>')

    @admin.action(description=_("Mark selected applications as registered"))
    def mark_as_registered(self, request, queryset):
        """Admin action to mark selected applications as registered."""
        updated = 0
        for obj in queryset:
            if obj.status == "INITIATED":
                obj.advance_status(
                    "REGISTERED",
                    "Marked as registered via admin",
                    request.user,
                )
                updated += 1

        self.message_user(request, f"{updated} application(s) marked as registered.")

    @admin.action(description=_("Export selected applications"))
    def export_applications(self, request, queryset):
        """Export selected applications to CSV."""
        # This would implement CSV export functionality
        self.message_user(
            request,
            f"Export functionality coming soon for {queryset.count()} applications.",
        )


@admin.register(TestPayment)
class TestPaymentAdmin(admin.ModelAdmin):
    """Admin interface for test fee payments."""

    list_display = [
        "potential_student_name",
        "test_number",
        "amount",
        "payment_method",
        "payment_status_display",
        "paid_at",
        "received_by",
    ]

    list_filter = [
        "is_paid",
        "payment_method",
        ("paid_at", DateFieldListFilter),
        ("created_at", DateFieldListFilter),
    ]

    search_fields = [
        "potential_student__test_number",
        "potential_student__personal_name_eng",
        "potential_student__family_name_eng",
        "potential_student__phone_number",
        "payment_reference",
    ]

    readonly_fields = [
        "finance_transaction_id",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            _("Payment Information"),
            {
                "fields": (
                    "potential_student",
                    "amount",
                    "payment_method",
                    "payment_reference",
                ),
            },
        ),
        (
            _("Payment Status"),
            {
                "fields": (
                    "is_paid",
                    "paid_at",
                    "received_by",
                ),
            },
        ),
        (_("Finance Integration"), {"fields": ("finance_transaction_id",)}),
        (
            _("Audit Information"),
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
            },
        ),
    )

    @admin.display(description=_("Student Name"))
    def potential_student_name(self, obj):
        """Display potential student name with link."""
        return format_html(
            '<a href="{}">{}</a>',
            reverse(
                "admin:level_testing_potentialstudent_change",
                args=[obj.potential_student.id],
            ),
            obj.potential_student.full_name_eng,
        )

    @admin.display(description=_("Test Number"))
    def test_number(self, obj):
        """Display test number."""
        return obj.potential_student.test_number

    @admin.display(description=_("Status"))
    def payment_status_display(self, obj):
        """Display payment status with color coding."""
        if obj.is_paid:
            return format_html('<span style="color: green;">✓ Paid</span>')
        return format_html('<span style="color: red;">✗ Unpaid</span>')


@admin.register(DuplicateCandidate)
class DuplicateCandidateAdmin(admin.ModelAdmin):
    """Admin interface for duplicate candidate records."""

    list_display = [
        "potential_student_name",
        "matched_name",
        "match_type",
        "confidence_score",
        "risk_level_display",
        "reviewed",
        "is_confirmed_duplicate",
        "created_at",
    ]

    list_filter = [
        "match_type",
        "reviewed",
        "is_confirmed_duplicate",
        "has_outstanding_debt",
        ("created_at", DateFieldListFilter),
    ]

    search_fields = [
        "potential_student__personal_name_eng",
        "potential_student__family_name_eng",
        "potential_student__test_number",
        "matched_name",
    ]

    readonly_fields = [
        "existing_person_id",
        "confidence_score",
        "matched_name",
        "matched_birth_date",
        "matched_phone",
        "has_outstanding_debt",
        "debt_amount",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            _("Match Information"),
            {
                "fields": (
                    "potential_student",
                    "existing_person_id",
                    "match_type",
                    "confidence_score",
                ),
            },
        ),
        (
            _("Matched Data"),
            {
                "fields": (
                    "matched_name",
                    "matched_birth_date",
                    "matched_phone",
                ),
            },
        ),
        (
            _("Financial Concerns"),
            {
                "fields": (
                    "has_outstanding_debt",
                    "debt_amount",
                ),
            },
        ),
        (
            _("Review Status"),
            {
                "fields": (
                    "reviewed",
                    "is_confirmed_duplicate",
                    "review_notes",
                    "reviewed_by",
                    "reviewed_at",
                ),
            },
        ),
    )

    @admin.display(description=_("Potential Student"))
    def potential_student_name(self, obj):
        """Display potential student name with link."""
        return format_html(
            '<a href="{}">{}</a>',
            reverse(
                "admin:level_testing_potentialstudent_change",
                args=[obj.potential_student.id],
            ),
            obj.potential_student.full_name_eng,
        )

    @admin.display(description=_("Risk Level"))
    def risk_level_display(self, obj):
        """Display risk level with color coding."""
        risk = obj.risk_level
        colors = {
            "HIGH": "red",
            "MEDIUM": "orange",
            "LOW": "green",
        }
        color = colors.get(risk, "gray")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            risk,
        )


@admin.register(TestSession)
class TestSessionAdmin(admin.ModelAdmin):
    """Admin interface for test sessions."""

    list_display = [
        "session_date",
        "location",
        "administrator",
        "capacity_display",
        "is_active",
        "is_upcoming",
    ]

    list_filter = [
        "is_active",
        "administrator",
        "location",
        ("session_date", DateFieldListFilter),
    ]

    search_fields = [
        "location",
        "administrator__username",
        "administrator__first_name",
        "administrator__last_name",
    ]

    fieldsets = (
        (
            _("Session Information"),
            {
                "fields": (
                    "session_date",
                    "location",
                    "administrator",
                    "is_active",
                ),
            },
        ),
        (_("Capacity Management"), {"fields": ("max_capacity",)}),
        (_("Notes"), {"fields": ("session_notes",)}),
    )

    @admin.display(description=_("Capacity (Used/Max)"))
    def capacity_display(self, obj):
        """Display session capacity with current enrollment."""
        enrolled = obj.enrolled_count
        max_cap = obj.max_capacity
        percentage = (enrolled / max_cap * 100) if max_cap > 0 else 0

        color = (
            "green"
            if percentage < ENROLLMENT_WARNING_THRESHOLD
            else "orange"
            if percentage < ENROLLMENT_DANGER_THRESHOLD
            else "red"
        )

        return format_html(
            '<span style="color: {};">{}/{} ({}%)</span>',
            color,
            enrolled,
            max_cap,
            int(percentage),
        )


@admin.register(PlacementTest)
class PlacementTestAdmin(admin.ModelAdmin):
    """Admin interface for placement test configurations."""

    list_display = [
        "name",
        "program",
        "test_type",
        "max_score",
        "passing_score",
        "duration_minutes",
        "is_active",
    ]

    list_filter = [
        "program",
        "test_type",
        "is_active",
    ]

    search_fields = [
        "name",
        "program",
    ]

    fieldsets = (
        (
            _("Test Configuration"),
            {
                "fields": (
                    "name",
                    "program",
                    "test_type",
                    "is_active",
                ),
            },
        ),
        (
            _("Scoring"),
            {
                "fields": (
                    "max_score",
                    "passing_score",
                    "duration_minutes",
                ),
            },
        ),
        (_("Instructions"), {"fields": ("instructions",)}),
    )


@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    """Admin interface for test attempts and results."""

    list_display = [
        "potential_student_name",
        "test_session",
        "placement_test",
        "score_display",
        "is_passed",
        "is_completed",
        "is_graded",
        "scheduled_at",
    ]

    list_filter = [
        "placement_test",
        "is_completed",
        "is_graded",
        ("scheduled_at", DateFieldListFilter),
        ("completed_at", DateFieldListFilter),
    ]

    search_fields = [
        "potential_student__test_number",
        "potential_student__personal_name_eng",
        "potential_student__family_name_eng",
    ]

    readonly_fields = [
        "duration_taken",
        "percentage_score",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            _("Test Information"),
            {
                "fields": (
                    "potential_student",
                    "test_session",
                    "placement_test",
                ),
            },
        ),
        (
            _("Scheduling"),
            {
                "fields": (
                    "scheduled_at",
                    "started_at",
                    "completed_at",
                    "duration_taken",
                ),
            },
        ),
        (
            _("Results"),
            {
                "fields": (
                    "raw_score",
                    "percentage_score",
                    "recommended_level",
                    "is_completed",
                    "is_graded",
                ),
            },
        ),
        (
            _("Administration Notes"),
            {
                "fields": (
                    "proctor_notes",
                    "technical_issues",
                ),
            },
        ),
    )

    @admin.display(description=_("Student"))
    def potential_student_name(self, obj):
        """Display potential student name with link."""
        return format_html(
            '<a href="{}">{}</a>',
            reverse(
                "admin:level_testing_potentialstudent_change",
                args=[obj.potential_student.id],
            ),
            obj.potential_student.full_name_eng,
        )

    @admin.display(description=_("Score"))
    def score_display(self, obj):
        """Display test score with pass/fail indication."""
        if obj.raw_score is not None:
            passed = obj.is_passed
            color = "green" if passed else "red"
            symbol = "✓" if passed else "✗"
            return format_html(
                '<span style="color: {};">{} {}/{} ({}%)</span>',
                color,
                symbol,
                obj.raw_score,
                obj.placement_test.max_score,
                int(obj.percentage_score) if obj.percentage_score else 0,
            )
        return "-"


# Customize admin site header and title
admin.site.site_header = _("PUCSR Student Information System")
admin.site.site_title = _("PUCSR Siem Reap Admin")
admin.site.index_title = _("Level Testing Management")
