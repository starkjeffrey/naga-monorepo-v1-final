"""Django admin configuration for scholarships app.

Provides comprehensive admin interfaces for managing sponsors, scholarships,
and sponsored students with proper filtering and search capabilities.

Enhanced features for NGO scholarship management:
- Payment mode configuration for sponsors
- Bulk operations for NGO students
- Quick filters for payment modes
- Dashboard links for NGO management
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.common.utils import format_student_id

from .forms import ScholarshipAdminForm
from .models import PaymentMode, Scholarship, Sponsor, SponsoredStudent


@admin.register(Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    """Admin interface for Sponsor model with NGO payment mode support."""

    list_display = [
        "code",
        "name",
        "contact_name",
        "contact_email",
        "payment_mode_display",
        "default_discount_percentage",
        "is_mou_active",
        "active_students_count",
        "is_active",
    ]
    list_filter = [
        "is_active",
        "payment_mode",
        "billing_cycle",
        "requests_attendance_reporting",
        "requests_grade_reporting",
        "requests_scheduling_reporting",
        "requests_consolidated_invoicing",
    ]
    search_fields = ["code", "name", "contact_name", "contact_email"]
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries for active student count."""
        from django.db import models

        today = timezone.now().date()

        return (
            super()
            .get_queryset(request)
            .annotate(
                active_students_count=models.Count(
                    "sponsored_students",
                    filter=models.Q(
                        sponsored_students__start_date__lte=today,
                        sponsored_students__end_date__isnull=True,
                    )
                    | models.Q(
                        sponsored_students__start_date__lte=today,
                        sponsored_students__end_date__gte=today,
                    ),
                ),
            )
        )

    fieldsets = (
        (_("Basic Information"), {"fields": ("code", "name", "is_active")}),
        (
            _("Contact Information"),
            {
                "fields": (
                    "contact_name",
                    "contact_email",
                    "contact_phone",
                    "billing_email",
                )
            },
        ),
        (
            _("MOU Details"),
            {
                "fields": (
                    "mou_start_date",
                    "mou_end_date",
                    "default_discount_percentage",
                )
            },
        ),
        (
            _("NGO Payment Configuration"),
            {
                "fields": (
                    "payment_mode",
                    "billing_cycle",
                    "invoice_generation_day",
                    "payment_terms_days",
                ),
                "description": "Configure how sponsored students pay for their tuition.",
            },
        ),
        (
            _("Billing Preferences"),
            {
                "fields": (
                    "requests_tax_addition",
                    "requests_consolidated_invoicing",
                    "admin_fee_exempt_until",
                )
            },
        ),
        (
            _("Reporting Requirements"),
            {
                "fields": (
                    "requests_attendance_reporting",
                    "requests_grade_reporting",
                    "requests_scheduling_reporting",
                )
            },
        ),
        (_("Additional Information"), {"fields": ("notes",)}),
        (
            _("System Information"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    @admin.display(description=_("Payment Mode"))
    def payment_mode_display(self, obj):
        """Display payment mode with icon."""
        if obj.payment_mode == PaymentMode.DIRECT:
            return format_html('<span style="color: #2e7d32;">💵 Direct Payment</span>')
        else:
            return format_html('<span style="color: #1565c0;">📄 Bulk Invoice</span>')

    @admin.display(description=_("MOU Status"))
    def is_mou_active(self, obj):
        """Display MOU active status with CSS classes."""
        if obj.is_mou_active:
            return format_html('<span class="mou-active">✓ Active</span>')
        return format_html('<span class="mou-inactive">✗ Inactive</span>')

    @admin.display(description=_("Active Students"))
    def active_students_count(self, obj):
        """Display count of active sponsored students using annotation."""
        # Use annotated count from get_queryset() optimization
        count = getattr(obj, "active_students_count", obj.get_active_sponsored_students_count())
        return f"{count} student{'s' if count != 1 else ''}"


@admin.register(SponsoredStudent)
class SponsoredStudentAdmin(admin.ModelAdmin):
    """Admin interface for SponsoredStudent model."""

    list_display = [
        "sponsor_code",
        "student_name",
        "student_id",
        "sponsorship_type",
        "start_date",
        "end_date",
        "is_active",
    ]
    list_filter = ["sponsorship_type", "sponsor", "start_date", "end_date"]
    search_fields = [
        "sponsor__code",
        "sponsor__name",
        "student__person__family_name",
        "student__person__personal_name",
        "student__student_id",
    ]
    readonly_fields = ["created_at", "updated_at"]

    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries for student and sponsor access."""
        return super().get_queryset(request).select_related("sponsor", "student__person")

    fieldsets = (
        (
            _("Sponsorship Details"),
            {"fields": ("sponsor", "student", "sponsorship_type")},
        ),
        (_("Date Range"), {"fields": ("start_date", "end_date")}),
        (_("Additional Information"), {"fields": ("notes",)}),
        (
            _("System Information"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    @admin.display(
        description=_("Sponsor"),
        ordering="sponsor__code",
    )
    def sponsor_code(self, obj):
        """Display sponsor code."""
        return obj.sponsor.code

    @admin.display(
        description=_("Student Name"),
        ordering="student__person__family_name",
    )
    def student_name(self, obj):
        """Display student name."""
        return obj.student.person.full_name

    @admin.display(
        description=_("Student ID"),
        ordering="student__student_id",
    )
    def student_id(self, obj):
        """Display student ID."""
        return format_student_id(obj.student.student_id)

    @admin.display(description=_("Status"))
    def is_active(self, obj):
        """Display active status with CSS classes."""
        if obj.is_currently_active:
            return format_html('<span class="status-active">✓ Active</span>')
        return format_html('<span class="status-inactive">✗ Inactive</span>')


@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):
    """Admin interface for Scholarship model."""

    form = ScholarshipAdminForm
    list_display = [
        "name",
        "student_name",
        "cycle_name",
        "scholarship_type",
        "award_display_admin",
        "status",
        "start_date",
        "end_date",
        "is_active",
    ]
    list_filter = ["scholarship_type", "status", "cycle", "start_date"]
    search_fields = [
        "name",
        "student__person__family_name",
        "student__person__personal_name",
        "student__student_id",
    ]
    readonly_fields = ["created_at", "updated_at"]
    raw_id_fields = ["student", "sponsored_student"]

    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries for student, sponsor, and cycle access."""
        return (
            super()
            .get_queryset(request)
            .select_related("student__person", "sponsored_student__sponsor", "cycle__division")
        )

    fieldsets = (
        (
            _("Basic Information"),
            {"fields": ("name", "scholarship_type", "student", "cycle")},
        ),
        (_("Award Details"), {"fields": ("award_percentage", "award_amount")}),
        (_("Dates & Status"), {"fields": ("start_date", "end_date", "status")}),
        (
            _("Optional"),
            {"fields": ("sponsored_student", "description", "conditions", "notes"), "classes": ("collapse",)},
        ),
        (
            _("System Information"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    @admin.display(
        description=_("Student"),
        ordering="student__person__family_name",
    )
    def student_name(self, obj):
        """Display student name."""
        return obj.student.person.full_name

    @admin.display(
        description=_("Cycle"),
        ordering="cycle__short_name",
    )
    def cycle_name(self, obj):
        """Display cycle name."""
        if obj.cycle:
            return f"{obj.cycle.short_name} ({obj.cycle.division.short_name})"
        return "—"

    @admin.display(description=_("Award"))
    def award_display_admin(self, obj):
        """Display award amount/percentage."""
        return obj.award_display

    @admin.display(description=_("Active"))
    def is_active(self, obj):
        """Display active status with CSS classes."""
        if obj.is_currently_active:
            return format_html('<span class="scholarship-active">✓ Active</span>')
        return format_html('<span class="status-inactive">✗ Inactive</span>')
