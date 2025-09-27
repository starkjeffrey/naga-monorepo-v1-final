"""Django admin configuration for finance models.

This module provides comprehensive admin interfaces for:
- Pricing management (tiers, course pricing, fee pricing)
- Invoice and billing management
- Payment processing and tracking
- Financial transaction monitoring
- Bulk financial operations

Following clean admin design with proper filtering, search,
and bulk actions for efficient financial management.
"""

from typing import Any

from django.contrib import admin
from django.contrib.admin import ModelAdmin
from django.db.models import Prefetch, QuerySet
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.common.admin import FinanceRestrictedMixin, ReadOnlyAdminMixin
from apps.common.admin_mixins import ComprehensiveAuditMixin
from apps.common.utils import format_student_id

from .forms import DiscountRuleAdminForm
from .models import (
    AdministrativeFeeConfig,
    ARReconstructionBatch,
    ClerkIdentification,
    CourseFixedPricing,
    DefaultPricing,
    DiscountRule,
    DocumentExcessFee,
    FeeGLMapping,
    FeePricing,
    FinancialTransaction,
    GLAccount,
    GLBatch,
    InvoiceLineItem,
    JournalEntry,
    JournalEntryLine,
    LegacyReceiptMapping,
    MaterialityThreshold,
    Payment,
    ReadingClassPricing,
    ReconciliationAdjustment,
    ReconciliationBatch,
    ReconciliationRule,
    ReconciliationStatus,
    ReconstructionScholarshipEntry,
    SeniorProjectCourse,
    SeniorProjectPricing,
)

# Deprecated admin classes removed - using separated pricing models instead


@admin.register(FeePricing)
class FeePricingAdmin(ModelAdmin):
    """Admin interface for fee pricing."""

    list_display = [
        "name",
        "fee_type",
        "local_amount",
        "foreign_amount",
        "currency",
        "fee_frequency",
        "is_mandatory",
        "is_active_display",
    ]
    list_filter = [
        "fee_type",
        "currency",
        "is_mandatory",
        "is_per_course",
        "is_per_term",
    ]
    search_fields = [
        "name",
        "description",
    ]
    ordering = ["fee_type", "name"]
    list_per_page = 50

    fieldsets = (
        (
            _("Fee Information"),
            {"fields": ("name", "fee_type", "description")},
        ),
        (
            _("Pricing Details"),
            {
                "fields": (
                    "local_amount",
                    "foreign_amount",
                    "currency",
                    "is_per_course",
                    "is_per_term",
                    "is_mandatory",
                ),
            },
        ),
        (_("Effective Period"), {"fields": ("effective_date", "end_date")}),
        (
            _("Audit Information"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description=_("Frequency"))
    def fee_frequency(self, obj) -> str:
        """Display fee frequency."""
        if obj.is_per_course:
            return "Per Course"
        if obj.is_per_term:
            return "Per Term"
        return "One-time"

    @admin.display(description=_("Status"))
    def is_active_display(self, obj) -> str:
        """Display active status with color coding."""
        if obj.is_active:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Active</span>',
            )
        return format_html('<span style="color: red;">✗ Inactive</span>')

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset for performance."""
        return super().get_queryset(request).select_related("effective_term", "end_term")


class InvoiceLineItemInline(admin.TabularInline):
    """Inline admin for invoice line items."""

    model = InvoiceLineItem
    extra = 0
    fields = [
        "line_item_type",
        "description",
        "unit_price",
        "quantity",
        "line_total",
        "enrollment",
        "fee_pricing",
    ]
    readonly_fields = ["line_total"]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset to prevent N+1 queries."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "enrollment__class_header__course",
                "fee_pricing",
            )
        )


@admin.register(Payment)
class PaymentAdmin(ReadOnlyAdminMixin, FinanceRestrictedMixin, ComprehensiveAuditMixin, ModelAdmin):
    """Admin interface for payments."""

    list_display = [
        "payment_reference",
        "invoice_display",
        "amount_display",
        "payment_method",
        "payment_date",
        "status_display",
        "processed_by",
        "processed_date",
    ]
    list_filter = [
        "status",
        "payment_method",
        "currency",
        "payment_date",
        "processed_date",
    ]
    search_fields = [
        "payment_reference",
        "invoice__invoice_number",
        "invoice__student__person__first_name",
        "invoice__student__person__last_name",
        "payer_name",
        "external_reference",
    ]
    ordering = ["-processed_date"]

    fieldsets = (
        (
            _("Payment Information"),
            {
                "fields": (
                    "payment_reference",
                    "invoice",
                    "amount",
                    "currency",
                    "payment_method",
                    "status",
                ),
            },
        ),
        (_("Dates"), {"fields": ("payment_date", "processed_date")}),
        (_("Payer Information"), {"fields": ("payer_name", "external_reference")}),
        (_("Processing"), {"fields": ("processed_by", "notes")}),
        (
            _("Audit Information"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["processed_date", "created_at", "updated_at"]
    list_per_page = 50

    @admin.display(description=_("Invoice"))
    def invoice_display(self, obj) -> str:
        """Display invoice information."""
        return f"{obj.invoice.invoice_number} ({obj.invoice.student})"

    @admin.display(description=_("Amount"))
    def amount_display(self, obj) -> str:
        """Display amount with color coding for refunds."""
        if obj.amount < 0:
            return format_html(
                '<span style="color: red;">-{} {}</span>',
                abs(obj.amount),
                obj.currency,
            )
        return format_html(
            '<span style="color: green;">{} {}</span>',
            obj.amount,
            obj.currency,
        )

    @admin.display(description=_("Status"))
    def status_display(self, obj) -> str:
        """Display status with color coding."""
        color_map = {
            "PENDING": "#ffc107",
            "COMPLETED": "#28a745",
            "FAILED": "#dc3545",
            "CANCELLED": "#6c757d",
            "REFUNDED": "#17a2b8",
        }

        color = color_map.get(obj.status, "#6c757d")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("invoice__student__person", "invoice", "processed_by")

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Disable manual addition of payments - use API instead."""
        return False


@admin.register(FinancialTransaction)
class FinancialTransactionAdmin(ReadOnlyAdminMixin, FinanceRestrictedMixin, ModelAdmin):
    """Admin interface for financial transactions."""

    list_display = [
        "transaction_id",
        "transaction_type",
        "student_display",
        "amount_display",
        "transaction_date",
        "invoice_display",
        "payment_display",
        "processed_by",
    ]
    list_filter = [
        "transaction_type",
        "currency",
        "transaction_date",
    ]
    search_fields = [
        "transaction_id",
        "student__person__first_name",
        "student__person__last_name",
        "student__student_id",
        "description",
        "invoice__invoice_number",
        "payment__payment_reference",
    ]
    ordering = ["-transaction_date"]

    fieldsets = (
        (
            _("Transaction Information"),
            {
                "fields": (
                    "transaction_id",
                    "transaction_type",
                    "student",
                    "description",
                ),
            },
        ),
        (_("Amount and Date"), {"fields": ("amount", "currency", "transaction_date")}),
        (_("Related Records"), {"fields": ("invoice", "payment")}),
        (_("Processing"), {"fields": ("processed_by", "reference_data")}),
        (
            _("Audit Information"),
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["transaction_id", "transaction_date", "created_at", "updated_at"]
    list_per_page = 50

    @admin.display(description=_("Student"))
    def student_display(self, obj) -> str:
        """Display student information."""
        student_id = getattr(obj.student, "student_id", None)
        if student_id is not None:
            formatted_id = format_student_id(student_id)
            return f"{obj.student} ({formatted_id})"
        return f"{obj.student} (N/A)"

    @admin.display(description=_("Amount"))
    def amount_display(self, obj) -> str:
        """Display amount with color coding."""
        if obj.amount < 0:
            return format_html(
                '<span style="color: red;">-{} {}</span>',
                abs(obj.amount),
                obj.currency,
            )
        return format_html(
            '<span style="color: green;">{} {}</span>',
            obj.amount,
            obj.currency,
        )

    @admin.display(description=_("Invoice"))
    def invoice_display(self, obj) -> str | None:
        """Display related invoice."""
        return obj.invoice.invoice_number if obj.invoice else None

    @admin.display(description=_("Payment"))
    def payment_display(self, obj) -> str | None:
        """Display related payment."""
        return obj.payment.payment_reference if obj.payment else None

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("student__person", "invoice", "payment", "processed_by")

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Disable manual addition of transactions - generated automatically."""
        return False

    def has_change_permission(self, request: HttpRequest, obj=None) -> bool:
        """Disable editing of transactions - immutable audit trail."""
        return False

    def has_delete_permission(self, request: HttpRequest, obj=None) -> bool:
        """Disable deletion of transactions - immutable audit trail."""
        return False


# G/L Integration Admin Classes


@admin.register(GLAccount)
class GLAccountAdmin(ModelAdmin):
    """Admin interface for G/L accounts."""

    list_display = [
        "account_code",
        "account_name",
        "account_type",
        "account_category",
        "parent_account",
        "is_active",
        "requires_department",
    ]
    list_filter = [
        "account_type",
        "account_category",
        "is_active",
        "requires_department",
    ]
    search_fields = [
        "account_code",
        "account_name",
        "description",
    ]
    ordering = ["account_code"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = [
        (
            _("Basic Information"),
            {
                "fields": [
                    "account_code",
                    "account_name",
                    "account_type",
                    "account_category",
                    "parent_account",
                ],
            },
        ),
        (
            _("Configuration"),
            {
                "fields": [
                    "is_active",
                    "requires_department",
                    "description",
                ],
            },
        ),
        (
            _("Metadata"),
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]


@admin.register(FeeGLMapping)
class FeeGLMappingAdmin(ModelAdmin):
    """Admin interface for fee to G/L mappings."""

    list_display = [
        "fee_code",
        "fee_type",
        "revenue_account",
        "effective_date",
        "end_date",
        "is_active",
    ]
    list_filter = [
        "fee_type",
        "effective_date",
        ("revenue_account", admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = [
        "fee_code",
        "revenue_account__account_code",
        "revenue_account__account_name",
    ]
    date_hierarchy = "effective_date"
    ordering = ["fee_type", "-effective_date"]
    readonly_fields = ["created_at", "updated_at"]

    fieldsets = [
        (
            _("Mapping Information"),
            {
                "fields": [
                    "fee_type",
                    "fee_code",
                    "revenue_account",
                    "receivable_account",
                ],
            },
        ),
        (
            _("Effective Dates"),
            {
                "fields": [
                    "effective_date",
                    "end_date",
                    "is_active",
                ],
            },
        ),
        (
            _("Metadata"),
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]


class JournalEntryLineInline(admin.TabularInline):
    """Inline admin for journal entry lines."""

    model = JournalEntryLine
    extra = 2
    fields = [
        "line_number",
        "gl_account",
        "debit_amount",
        "credit_amount",
        "description",
        "department_code",
        "project_code",
    ]
    ordering = ["line_number"]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset to prevent N+1 queries."""
        return super().get_queryset(request).select_related("gl_account")


@admin.register(JournalEntry)
class JournalEntryAdmin(ModelAdmin):
    """Admin interface for journal entries."""

    list_display = [
        "entry_number",
        "entry_date",
        "accounting_period",
        "entry_type",
        "description",
        "get_debit_total",
        "get_credit_total",
        "is_balanced",
        "status",
        "batch_id",
    ]
    list_filter = [
        "status",
        "entry_type",
        "accounting_period",
        "entry_date",
    ]
    search_fields = [
        "entry_number",
        "description",
        "batch_id",
        "reference_number",
    ]
    date_hierarchy = "entry_date"
    ordering = ["-entry_date", "-entry_number"]
    readonly_fields = [
        "created_at",
        "updated_at",
        "approved_date",
        "posted_date",
        "total_debits",
        "total_credits",
        "is_balanced",
        "balance_amount",
    ]
    inlines = [JournalEntryLineInline]
    list_per_page = 50

    fieldsets = [
        (
            _("Entry Information"),
            {
                "fields": [
                    "entry_number",
                    "entry_date",
                    "accounting_period",
                    "entry_type",
                    "description",
                    "reference_number",
                ],
            },
        ),
        (
            _("Status and Workflow"),
            {
                "fields": [
                    "status",
                    "prepared_by",
                    "approved_by",
                    "approved_date",
                    "posted_date",
                ],
            },
        ),
        (
            _("Totals and Balance"),
            {
                "fields": [
                    "total_debits",
                    "total_credits",
                    "is_balanced",
                    "balance_amount",
                ],
            },
        ),
        (
            _("Additional Information"),
            {
                "fields": [
                    "batch_id",
                    "source_system",
                    "reverses_entry",
                    "notes",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            _("Metadata"),
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    @admin.display(description=_("Total Debits"))
    def get_debit_total(self, obj):
        """Display formatted debit total."""
        return f"${obj.total_debits:,.2f}"

    @admin.display(description=_("Total Credits"))
    def get_credit_total(self, obj):
        """Display formatted credit total."""
        return f"${obj.total_credits:,.2f}"

    @admin.display(description=_("Balanced"), boolean=True)
    def is_balanced(self, obj):
        """Display balanced status with icon."""
        if obj.is_balanced:
            return format_html('<img src="/static/admin/img/icon-yes.svg" alt="Yes">')
        return format_html('<img src="/static/admin/img/icon-no.svg" alt="No">')

    actions = ["approve_entries", "post_to_gl", "recalculate_totals"]

    def approve_entries(self, request: HttpRequest, queryset: QuerySet[Any]) -> None:
        """Bulk approve journal entries."""
        approved = 0
        for entry in queryset.filter(status=JournalEntry.EntryStatus.DRAFT):
            try:
                entry.approve(request.user)
                approved += 1
            except (ValueError, AttributeError, TypeError) as e:
                self.message_user(
                    request,
                    f"Error approving {entry.entry_number}: {e!s}",
                    level="ERROR",
                )

        if approved:
            self.message_user(
                request,
                f"Successfully approved {approved} journal entries.",
                level="SUCCESS",
            )

    approve_entries.short_description = _("Approve selected journal entries")  # type: ignore[attr-defined]

    def post_to_gl(self, request: HttpRequest, queryset: QuerySet[Any]) -> None:
        """Bulk post journal entries to G/L."""
        posted = 0
        for entry in queryset.filter(status=JournalEntry.EntryStatus.APPROVED):
            try:
                entry.post_to_gl()
                posted += 1
            except (ValueError, AttributeError, TypeError) as e:
                self.message_user(
                    request,
                    f"Error posting {entry.entry_number}: {e!s}",
                    level="ERROR",
                )

        if posted:
            self.message_user(
                request,
                f"Successfully posted {posted} journal entries to G/L.",
                level="SUCCESS",
            )

    post_to_gl.short_description = _("Post selected entries to G/L")  # type: ignore[attr-defined]

    def recalculate_totals(self, request: HttpRequest, queryset: QuerySet[Any]) -> None:
        """Recalculate totals for selected entries."""
        for entry in queryset:
            entry.calculate_totals()

        self.message_user(
            request,
            f"Recalculated totals for {queryset.count()} journal entries.",
            level="SUCCESS",
        )

    recalculate_totals.short_description = _("Recalculate totals")  # type: ignore[attr-defined]

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset to prevent N+1 queries."""
        qs = super().get_queryset(request)

        # Select related for commonly accessed fields
        qs = qs.select_related(
            "prepared_by",
            "approved_by",
        )

        # Prefetch lines for detail view
        if request.resolver_match and request.resolver_match.url_name == "finance_journalentry_change":
            lines_qs = JournalEntryLine.objects.select_related("gl_account")
            qs = qs.prefetch_related(Prefetch("lines", queryset=lines_qs))

        return qs


@admin.register(GLBatch)
class GLBatchAdmin(ModelAdmin):
    """Admin interface for G/L batches."""

    list_display = [
        "batch_number",
        "accounting_period",
        "batch_date",
        "status",
        "total_entries",
        "get_total_amount",
        "exported_by",
        "exported_date",
    ]
    list_filter = [
        "status",
        "accounting_period",
        "batch_date",
    ]
    search_fields = [
        "batch_number",
        "notes",
    ]
    date_hierarchy = "batch_date"
    ordering = ["-batch_date", "-batch_number"]
    readonly_fields = [
        "total_entries",
        "total_amount",
        "created_at",
        "updated_at",
        "exported_date",
    ]

    fieldsets = [
        (
            _("Batch Information"),
            {
                "fields": [
                    "batch_number",
                    "accounting_period",
                    "batch_date",
                ],
            },
        ),
        (
            _("Status and Processing"),
            {
                "fields": [
                    "status",
                    "exported_by",
                    "exported_date",
                ],
            },
        ),
        (
            _("Totals"),
            {
                "fields": [
                    "total_entries",
                    "total_amount",
                ],
            },
        ),
        (
            _("Additional Information"),
            {
                "fields": [
                    "export_file",
                    "error_message",
                    "notes",
                ],
                "classes": ["collapse"],
            },
        ),
        (
            _("Metadata"),
            {
                "fields": ["created_at", "updated_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    @admin.display(description=_("Total Amount"))
    def get_total_amount(self, obj):
        """Display formatted total amount."""
        return f"${obj.total_amount:,.2f}"


# =====================================================================
# NEW SEPARATED PRICING MODEL ADMIN INTERFACES
# =====================================================================


@admin.register(DefaultPricing)
class DefaultPricingAdmin(ComprehensiveAuditMixin, ModelAdmin):
    """Admin interface for default cycle-based pricing."""

    list_display = [
        "cycle",
        "domestic_price",
        "foreign_price",
        "effective_date",
        "end_date",
        "is_current_display",
        "notes_preview",
    ]
    list_filter = ["cycle", "effective_date", "end_date"]
    search_fields = ["cycle__name", "notes"]
    ordering = ["cycle", "-effective_date"]

    fieldsets = (
        (None, {"fields": ("cycle", "effective_date", "end_date")}),
        (_("Pricing"), {"fields": ("domestic_price", "foreign_price")}),
        (_("Notes"), {"fields": ("notes",), "classes": ("collapse",)}),
        (
            _("Audit Information"),
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at", "created_by", "updated_by"]

    @admin.display(boolean=True, description="Current")
    def is_current_display(self, obj):
        """Show if this is the current active pricing."""
        return obj.is_current

    @admin.display(description="Notes")
    def notes_preview(self, obj):
        """Show truncated notes."""
        return obj.notes[:50] + "..." if len(obj.notes) > 50 else obj.notes

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset to prevent N+1 queries."""
        return super().get_queryset(request).select_related("cycle")


@admin.register(CourseFixedPricing)
class CourseFixedPricingAdmin(ComprehensiveAuditMixin, ModelAdmin):
    """Admin interface for course-specific fixed pricing."""

    list_display = [
        "course_code",
        "course_title",
        "course_credits",
        "course_cycle",
        "course_date_range",
        "domestic_price",
        "foreign_price",
        "effective_date",
        "end_date",
        "is_current_display",
    ]
    list_filter = [
        "course__cycle__division",
        "course__cycle",
        "effective_date",
        "end_date",
    ]
    search_fields = ["course__code", "course__title"]
    autocomplete_fields = ["course"]
    ordering = ["course__code", "-effective_date"]

    fieldsets = (
        (
            _("Course"),
            {
                "fields": ("course",),
                "description": "Select the course that needs custom pricing",
            },
        ),
        (_("Pricing"), {"fields": ("domestic_price", "foreign_price")}),
        (_("Effective Period"), {"fields": ("effective_date", "end_date")}),
        (_("Notes"), {"fields": ("notes",), "classes": ("collapse",)}),
        (
            _("Audit Information"),
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at", "created_by", "updated_by"]

    @admin.display(description="Code")
    def course_code(self, obj):
        return obj.course.code

    @admin.display(description="Title")
    def course_title(self, obj):
        return obj.course.title[:40] + "..." if len(obj.course.title) > 40 else obj.course.title

    @admin.display(description="Credits", ordering="course__credits")
    def course_credits(self, obj):
        return f"{obj.course.credits} cr"

    @admin.display(description="Cycle", ordering="course__cycle__name")
    def course_cycle(self, obj):
        return obj.course.cycle.short_name if obj.course.cycle else "N/A"

    @admin.display(description="Course Period")
    def course_date_range(self, obj):
        start = obj.course.start_date
        end = obj.course.end_date

        if end:
            return f"{start.strftime('%m/%y')}-{end.strftime('%m/%y')}"
        return f"{start.strftime('%m/%y')}+ (Active)"

    @admin.display(boolean=True, description="Current")
    def is_current_display(self, obj):
        return obj.is_current

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset to prevent N+1 queries."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "course__cycle__division",
                "course__cycle",
            )
        )


@admin.register(SeniorProjectPricing)
class SeniorProjectPricingAdmin(ComprehensiveAuditMixin, ModelAdmin):
    """Admin interface for senior project individual pricing."""

    list_display = [
        "tier",
        "individual_price",
        "foreign_individual_price",
        "advisor_payment",
        "committee_payment",
        "effective_date",
        "end_date",
        "is_current_display",
    ]
    list_filter = ["tier", "effective_date", "end_date"]
    ordering = ["tier", "-effective_date"]

    fieldsets = (
        (
            _("Group Size Tier"),
            {"fields": ("tier",), "description": "Select the student group size tier"},
        ),
        (
            _("Individual Pricing"),
            {
                "fields": ("individual_price", "foreign_individual_price"),
                "description": "Individual price each student pays (NOT split among group)",
            },
        ),
        (
            _("Faculty Payments"),
            {
                "fields": ("advisor_payment", "committee_payment"),
                "description": "Payments to advisor and committee members",
            },
        ),
        (_("Effective Period"), {"fields": ("effective_date", "end_date")}),
        (_("Notes"), {"fields": ("notes",), "classes": ("collapse",)}),
        (
            _("Audit Information"),
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at", "created_by", "updated_by"]

    @admin.display(boolean=True, description="Current")
    def is_current_display(self, obj):
        return obj.is_current


@admin.register(SeniorProjectCourse)
class SeniorProjectCourseAdmin(ComprehensiveAuditMixin, ModelAdmin):
    """Admin interface for configuring which courses use senior project pricing."""

    list_display = [
        "project_code",
        "major_name",
        "course_code",
        "course_title",
        "allows_groups",
        "is_active",
    ]
    list_filter = ["is_active", "allows_groups", "course__cycle"]
    search_fields = ["project_code", "major_name", "course__code", "course__title"]
    autocomplete_fields = ["course"]
    ordering = ["course__code"]

    fieldsets = (
        (
            _("Project Configuration"),
            {
                "fields": ("project_code", "major_name", "allows_groups"),
                "description": "Project details and group allowance settings",
            },
        ),
        (
            _("Course Configuration"),
            {
                "fields": ("course", "is_active"),
                "description": (
                    "Select courses that should use senior project pricing (e.g., IR-489, FIN-489, BUS-489, THM-433)"
                ),
            },
        ),
        (
            _("Audit Information"),
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at", "created_by", "updated_by"]

    @admin.display(description="Code")
    def course_code(self, obj):
        return obj.course.code

    @admin.display(description="Title")
    def course_title(self, obj):
        return obj.course.title

    @admin.display(description="Cycle")
    def cycle_display(self, obj):
        return obj.course.cycle


@admin.register(ReadingClassPricing)
class ReadingClassPricingAdmin(ComprehensiveAuditMixin, ModelAdmin):
    """Admin interface for reading/request class size-based pricing."""

    list_display = [
        "cycle",
        "tier",
        "domestic_price",
        "foreign_price",
        "effective_date",
        "end_date",
        "is_current_display",
    ]
    list_filter = ["cycle", "tier", "effective_date", "end_date"]
    ordering = ["cycle", "tier", "-effective_date"]

    fieldsets = (
        (_("Academic Cycle"), {"fields": ("cycle",)}),
        (
            _("Class Size Tier"),
            {
                "fields": ("tier",),
                "description": "Select the class enrollment size tier",
            },
        ),
        (
            _("Pricing"),
            {
                "fields": ("domestic_price", "foreign_price"),
                "description": "Price per student for domestic and international students",
            },
        ),
        (_("Effective Period"), {"fields": ("effective_date", "end_date")}),
        (_("Notes"), {"fields": ("notes",), "classes": ("collapse",)}),
        (
            _("Audit Information"),
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at", "created_by", "updated_by"]

    @admin.display(boolean=True, description="Current")
    def is_current_display(self, obj):
        return obj.is_current

    def get_list_display_links(self, request, list_display):
        # Make the entire row clickable for better UX
        return ["cycle", "tier"]


# =====================================================================
# RECONCILIATION ADMIN INTERFACES
# =====================================================================


class ReconciliationAdjustmentInline(admin.TabularInline):
    """Inline admin for reconciliation adjustments."""

    model = ReconciliationAdjustment
    extra = 0
    fields = [
        "adjustment_type",
        "description",
        "variance",
        "requires_approval",
        "approved_by",
        "approved_date",
    ]
    readonly_fields = ["variance", "approved_date"]


@admin.register(ReconciliationBatch)
class ReconciliationBatchAdmin(ComprehensiveAuditMixin, ModelAdmin):
    """Admin interface for reconciliation batches."""

    list_display = [
        "batch_id",
        "batch_type",
        "start_date",
        "end_date",
        "status_display",
        "success_rate_display",
        "total_payments",
        "processed_payments",
        "successful_matches",
        "failed_matches",
    ]
    list_filter = [
        "status",
        "batch_type",
        "start_date",
        "end_date",
    ]
    search_fields = [
        "batch_id",
        "parameters",
    ]
    ordering = ["-created_at"]
    list_per_page = 50

    fieldsets = (
        (
            _("Batch Information"),
            {"fields": ("batch_id", "batch_type", "start_date", "end_date", "status")},
        ),
        (
            _("Processing Details"),
            {
                "fields": (
                    "total_payments",
                    "processed_payments",
                    "successful_matches",
                    "failed_matches",
                )
            },
        ),
        (_("Timing"), {"fields": ("started_at", "completed_at")}),
        (_("Configuration"), {"fields": ("parameters",), "classes": ("collapse",)}),
        (
            _("Results"),
            {"fields": ("results_summary", "error_log"), "classes": ("collapse",)},
        ),
        (
            _("Audit Information"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at", "started_at", "completed_at"]

    @admin.display(description=_("Status"))
    def status_display(self, obj) -> str:
        """Display status with color coding."""
        color_map = {
            "PENDING": "#ffc107",
            "PROCESSING": "#007bff",
            "COMPLETED": "#28a745",
            "FAILED": "#dc3545",
            "PARTIAL": "#fd7e14",
        }

        color = color_map.get(obj.status, "#6c757d")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description=_("Success Rate"))
    def success_rate_display(self, obj) -> str:
        """Display success rate with color coding."""
        try:
            rate = float(obj.success_rate)
        except (TypeError, ValueError):
            rate = 0.0

        if rate >= 95:
            color = "#28a745"  # Green
        elif rate >= 80:
            color = "#ffc107"  # Yellow
        else:
            color = "#dc3545"  # Red

        # Use separate format_html calls to avoid the SafeString issue
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, f"{rate:.1f}%")


@admin.register(ReconciliationStatus)
class ReconciliationStatusAdmin(ComprehensiveAuditMixin, ModelAdmin):
    """Admin interface for reconciliation status tracking."""

    list_display = [
        "payment_reference",
        "student_display",
        "status_display",
        "confidence_display",
        "variance_amount_display",
        "pricing_method_applied",
        "reconciled_date",
        "refinement_attempts",
    ]
    list_filter = [
        "status",
        "confidence_level",
        "pricing_method_applied",
        "reconciliation_batch",
        "reconciled_date",
    ]
    search_fields = [
        "payment__payment_reference",
        "payment__invoice__student__person__first_name",
        "payment__invoice__student__person__last_name",
        "payment__invoice__student__student_id",
        "notes",
    ]
    ordering = ["-created_at"]
    inlines = [ReconciliationAdjustmentInline]
    list_per_page = 50

    fieldsets = (
        (
            _("Payment Information"),
            {"fields": ("payment", "status", "reconciled_by", "reconciled_date")},
        ),
        (
            _("Confidence Analysis"),
            {
                "fields": (
                    "confidence_level",
                    "confidence_score",
                    "pricing_method_applied",
                )
            },
        ),
        (_("Variance Details"), {"fields": ("variance_amount", "variance_percentage")}),
        (_("Matched Enrollments"), {"fields": ("matched_enrollments",)}),
        (
            _("Refinement Tracking"),
            {
                "fields": (
                    "refinement_attempts",
                    "last_attempt_date",
                    "refinement_strategies_tried",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Error Information"),
            {"fields": ("error_category", "error_details"), "classes": ("collapse",)},
        ),
        (_("History"), {"fields": ("confidence_history",), "classes": ("collapse",)}),
        (_("Batch Processing"), {"fields": ("reconciliation_batch",)}),
        (_("Notes"), {"fields": ("notes",)}),
        (
            _("Audit Information"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = [
        "created_at",
        "updated_at",
        "reconciled_date",
        "last_attempt_date",
        "refinement_attempts",
        "confidence_history",
    ]
    filter_horizontal = ["matched_enrollments"]

    @admin.display(description=_("Payment"))
    def payment_reference(self, obj) -> str:
        """Display payment reference."""
        return obj.payment.payment_reference

    @admin.display(description=_("Student"))
    def student_display(self, obj) -> str:
        """Display student information."""
        student = obj.payment.invoice.student
        student_id = getattr(student, "student_id", None)
        if student_id is not None:
            formatted_id = format_student_id(student_id)
            return f"{student} ({formatted_id})"
        return f"{student} (N/A)"

    @admin.display(description=_("Status"))
    def status_display(self, obj) -> str:
        """Display status with color coding."""
        color_map = {
            "FULLY_RECONCILED": "#28a745",
            "AUTO_ALLOCATED": "#007bff",
            "PENDING_REVIEW": "#ffc107",
            "EXCEPTION_ERROR": "#dc3545",
            "UNMATCHED": "#6c757d",
        }

        color = color_map.get(obj.status, "#6c757d")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description=_("Confidence"))
    def confidence_display(self, obj) -> str:
        """Display confidence with score and level."""
        if obj.confidence_score:
            level_color = {
                "HIGH": "#28a745",
                "MEDIUM": "#ffc107",
                "LOW": "#fd7e14",
                "NONE": "#6c757d",
            }
            color = level_color.get(obj.confidence_level, "#6c757d")
            return format_html(
                '<span style="color: {};">{:.1f}% ({})</span>',
                color,
                obj.confidence_score,
                obj.get_confidence_level_display(),
            )
        return format_html('<span style="color: #6c757d;">None</span>')

    @admin.display(description=_("Variance"))
    def variance_amount_display(self, obj) -> str:
        """Display variance amount with color coding."""
        if obj.variance_amount:
            if abs(obj.variance_amount) <= 1:
                color = "#28a745"  # Green for small variances
            elif abs(obj.variance_amount) <= 50:
                color = "#ffc107"  # Yellow for medium variances
            else:
                color = "#dc3545"  # Red for large variances

            return format_html('<span style="color: {};">${:.2f}</span>', color, obj.variance_amount)
        return format_html('<span style="color: #6c757d;">$0.00</span>')

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "payment__invoice__student__person",
                "payment",
                "reconciled_by",
                "reconciliation_batch",
            )
            .prefetch_related("matched_enrollments")
        )


@admin.register(ReconciliationAdjustment)
class ReconciliationAdjustmentAdmin(ComprehensiveAuditMixin, ModelAdmin):
    """Admin interface for reconciliation adjustments."""

    list_display = [
        "payment_reference",
        "adjustment_type",
        "description_short",
        "variance_display",
        "student_display",
        "term",
        "requires_approval",
        "approved_by",
        "approved_date",
    ]
    list_filter = [
        "adjustment_type",
        "requires_approval",
        "term",
        "reconciliation_batch",
        "approved_date",
    ]
    search_fields = [
        "payment__payment_reference",
        "description",
        "student__person__first_name",
        "student__person__last_name",
        "student__student_id",
    ]
    ordering = ["-created_at"]

    fieldsets = (
        (
            _("Adjustment Information"),
            {"fields": ("adjustment_type", "description", "gl_account")},
        ),
        (_("Amounts"), {"fields": ("original_amount", "adjusted_amount", "variance")}),
        (
            _("References"),
            {"fields": ("payment", "journal_entry", "reconciliation_status")},
        ),
        (_("Categorization"), {"fields": ("student", "term", "reconciliation_batch")}),
        (
            _("Approval Workflow"),
            {"fields": ("requires_approval", "approved_by", "approved_date")},
        ),
        (
            _("Audit Information"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at", "variance", "approved_date"]

    @admin.display(description=_("Payment"))
    def payment_reference(self, obj) -> str:
        """Display payment reference."""
        return obj.payment.payment_reference

    @admin.display(description=_("Description"))
    def description_short(self, obj) -> str:
        """Display shortened description."""
        return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description

    @admin.display(description=_("Variance"))
    def variance_display(self, obj) -> str:
        """Display variance with color coding."""
        if obj.variance > 0:
            return format_html('<span style="color: #28a745;">+${:.2f}</span>', obj.variance)
        elif obj.variance < 0:
            return format_html('<span style="color: #dc3545;">-${:.2f}</span>', abs(obj.variance))
        return format_html('<span style="color: #6c757d;">$0.00</span>')

    @admin.display(description=_("Student"))
    def student_display(self, obj) -> str:
        """Display student information."""
        student_id = getattr(obj.student, "student_id", None)
        if student_id is not None:
            formatted_id = format_student_id(student_id)
            return f"{obj.student} ({formatted_id})"
        return f"{obj.student} (N/A)"

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "payment",
                "student__person",
                "term",
                "gl_account",
                "approved_by",
                "reconciliation_batch",
            )
        )


@admin.register(ReconciliationRule)
class ReconciliationRuleAdmin(ComprehensiveAuditMixin, ModelAdmin):
    """Admin interface for reconciliation rules."""

    list_display = [
        "rule_name",
        "rule_type",
        "priority",
        "confidence_threshold",
        "is_active",
        "success_rate_display",
        "times_applied",
        "last_applied",
    ]
    list_filter = [
        "rule_type",
        "is_active",
        "priority",
        "last_applied",
    ]
    search_fields = [
        "rule_name",
        "description",
    ]
    ordering = ["priority", "rule_name"]
    list_per_page = 50

    fieldsets = (
        (_("Rule Information"), {"fields": ("rule_name", "rule_type", "description")}),
        (
            _("Configuration"),
            {"fields": ("is_active", "priority", "confidence_threshold")},
        ),
        (_("Parameters"), {"fields": ("parameters",), "classes": ("collapse",)}),
        (
            _("Usage Statistics"),
            {
                "fields": ("times_applied", "success_count", "last_applied"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Audit Information"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = [
        "created_at",
        "updated_at",
        "times_applied",
        "success_count",
        "last_applied",
    ]

    @admin.display(description=_("Success Rate"))
    def success_rate_display(self, obj) -> str:
        """Display success rate with color coding."""
        try:
            rate = float(obj.success_rate)
        except (TypeError, ValueError):
            rate = 0.0

        if rate >= 90:
            color = "#28a745"  # Green
        elif rate >= 70:
            color = "#ffc107"  # Yellow
        else:
            color = "#dc3545"  # Red

        # Use separate format_html calls to avoid the SafeString issue
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, f"{rate:.1f}%")

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset for performance."""
        return super().get_queryset(request)


@admin.register(MaterialityThreshold)
class MaterialityThresholdAdmin(ComprehensiveAuditMixin, ModelAdmin):
    """Admin interface for materiality thresholds."""

    list_display = [
        "context",
        "absolute_threshold",
        "percentage_threshold",
        "effective_date",
        "notes_preview",
    ]
    list_filter = [
        "context",
        "effective_date",
    ]
    search_fields = [
        "notes",
    ]
    ordering = ["context", "-effective_date"]
    list_per_page = 50

    fieldsets = (
        (_("Threshold Information"), {"fields": ("context", "effective_date")}),
        (
            _("Threshold Values"),
            {"fields": ("absolute_threshold", "percentage_threshold")},
        ),
        (_("Notes"), {"fields": ("notes",)}),
        (
            _("Audit Information"),
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description=_("Notes"))
    def notes_preview(self, obj) -> str:
        """Display shortened notes."""
        return obj.notes[:50] + "..." if len(obj.notes) > 50 else obj.notes

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset for performance."""
        return super().get_queryset(request)


# =====================================================================
# A/R RECONSTRUCTION ADMIN INTERFACES
# =====================================================================


@admin.register(DiscountRule)
class DiscountRuleAdmin(ComprehensiveAuditMixin, ModelAdmin):
    """Admin interface for discount rules management."""

    form = DiscountRuleAdminForm

    list_display = [
        "rule_name",
        "rule_type",
        "pattern_text_short",
        "discount_percentage",
        "fixed_amount",
        "terms_count",
        "programs_count",
        "is_active",
        "times_applied",
        "last_applied_date",
    ]
    list_filter = [
        "rule_type",
        "is_active",
        "effective_date",
        "last_applied_date",
    ]
    search_fields = [
        "rule_name",
        "pattern_text",
    ]
    ordering = ["rule_type", "rule_name"]
    list_per_page = 50

    fieldsets = (
        (
            _("Rule Identification"),
            {
                "fields": ("rule_name", "rule_type"),
                "description": "Basic rule identification and categorization",
            },
        ),
        (
            _("Pattern Configuration"),
            {
                "fields": ("pattern_text",),
                "description": "Text pattern that triggers this rule (from Notes field)",
            },
        ),
        (
            _("Discount Configuration"),
            {
                "fields": ("discount_percentage", "fixed_amount"),
                "description": "Either percentage discount OR fixed amount (not both)",
            },
        ),
        (
            _("Applicability Rules"),
            {
                "fields": ("applies_to_terms", "applies_to_programs"),
                "description": "Leave empty to apply to all terms/programs",
                "classes": ("collapse",),
            },
        ),
        (
            _("Rule Status"),
            {
                "fields": ("is_active", "effective_date"),
            },
        ),
        (
            _("Usage Statistics"),
            {
                "fields": ("times_applied", "last_applied_date"),
                "classes": ("collapse",),
            },
        ),
        (
            _("Audit Information"),
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = [
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "times_applied",
        "last_applied_date",
    ]

    @admin.display(description=_("Pattern"))
    def pattern_text_short(self, obj) -> str:
        """Display shortened pattern text."""
        return obj.pattern_text[:30] + "..." if len(obj.pattern_text) > 30 else obj.pattern_text

    @admin.display(description=_("Terms"))
    def terms_count(self, obj) -> str:
        """Display count of applicable terms."""
        if not obj.applies_to_terms:
            return "All terms"
        return f"{len(obj.applies_to_terms)} terms"

    @admin.display(description=_("Programs"))
    def programs_count(self, obj) -> str:
        """Display count of applicable programs."""
        if not obj.applies_to_programs:
            return "All programs"
        return f"{len(obj.applies_to_programs)} programs"

    def save_model(self, request, obj, form, change):
        """Set user tracking on save."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset to prevent N+1 queries."""
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                "applies_to_terms",
                "applies_to_programs",
            )
        )


@admin.register(ARReconstructionBatch)
class ARReconstructionBatchAdmin(ComprehensiveAuditMixin, ModelAdmin):
    """Admin interface for A/R reconstruction batches."""

    list_display = [
        "batch_id",
        "term_id",
        "processing_mode",
        "status_display",
        "success_rate_display",
        "total_receipts",
        "processed_receipts",
        "successful_reconstructions",
        "failed_reconstructions",
        "started_at",
        "completed_at",
    ]
    list_filter = [
        "status",
        "processing_mode",
        "term_id",
        "started_at",
        "completed_at",
    ]
    search_fields = [
        "batch_id",
        "term_id",
    ]
    ordering = ["-created_at"]
    list_per_page = 50
    readonly_fields = [
        "batch_id",
        "success_rate",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    ]

    fieldsets = (
        (
            _("Batch Information"),
            {
                "fields": ("batch_id", "term_id", "processing_mode", "status"),
            },
        ),
        (
            _("Processing Counts"),
            {
                "fields": (
                    "total_receipts",
                    "processed_receipts",
                    "successful_reconstructions",
                    "failed_reconstructions",
                    "pending_review_count",
                ),
            },
        ),
        (
            _("Timing"),
            {
                "fields": ("started_at", "completed_at"),
            },
        ),
        (
            _("Configuration & Results"),
            {
                "fields": (
                    "processing_parameters",
                    "variance_summary",
                    "processing_log",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Audit Information"),
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description=_("Status"))
    def status_display(self, obj) -> str:
        """Display status with color coding."""
        color_map = {
            "PENDING": "#ffc107",
            "PROCESSING": "#007bff",
            "COMPLETED": "#28a745",
            "FAILED": "#dc3545",
            "PAUSED": "#fd7e14",
            "CANCELLED": "#6c757d",
        }
        color = color_map.get(obj.status, "#6c757d")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    @admin.display(description=_("Success Rate"))
    def success_rate_display(self, obj) -> str:
        """Display success rate with color coding."""
        try:
            rate = float(obj.success_rate)
        except (TypeError, ValueError):
            rate = 0.0

        if rate >= 95:
            color = "#28a745"  # Green
        elif rate >= 80:
            color = "#ffc107"  # Yellow
        else:
            color = "#dc3545"  # Red
        # Use separate format_html calls to avoid the SafeString issue
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', color, f"{rate:.1f}%")

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset to prevent N+1 queries."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "created_by",
                "updated_by",
            )
        )


@admin.register(LegacyReceiptMapping)
class LegacyReceiptMappingAdmin(ComprehensiveAuditMixin, ModelAdmin):
    """Admin interface for legacy receipt mappings."""

    list_display = [
        "legacy_receipt_number",
        "legacy_student_id",
        "legacy_term_id",
        "legacy_amount",
        "legacy_net_amount",
        "legacy_discount",
        "variance_amount_display",
        "validation_status_display",
        "notes_processing_confidence",
        "reconstruction_batch",
    ]
    list_filter = [
        "validation_status",
        "legacy_term_id",
        "reconstruction_batch",
        "parsed_note_type",
        "processing_date",
    ]
    search_fields = [
        "legacy_receipt_number",
        "legacy_receipt_id",
        "legacy_student_id",
        "legacy_notes",
        "parsed_reason",
        "parsed_authority",
    ]
    ordering = ["-processing_date"]
    list_per_page = 50
    readonly_fields = [
        "legacy_receipt_number",
        "legacy_receipt_id",
        "legacy_student_id",
        "legacy_term_id",
        "legacy_amount",
        "legacy_net_amount",
        "legacy_discount",
        "reconstructed_total",
        "variance_amount",
        "processing_date",
        "notes_processing_confidence",
        "created_at",
        "updated_at",
    ]

    fieldsets = (
        (
            _("Legacy Receipt Information"),
            {
                "fields": (
                    "legacy_receipt_number",
                    "legacy_receipt_id",
                    "legacy_student_id",
                    "legacy_term_id",
                ),
            },
        ),
        (
            _("Financial Amounts"),
            {
                "fields": (
                    "legacy_amount",
                    "legacy_net_amount",
                    "legacy_discount",
                    "reconstructed_total",
                    "variance_amount",
                ),
            },
        ),
        (
            _("Django Objects"),
            {
                "fields": ("generated_invoice", "generated_payment"),
            },
        ),
        (
            _("Processing Status"),
            {
                "fields": (
                    "reconstruction_batch",
                    "processing_date",
                    "validation_status",
                    "validation_notes",
                ),
            },
        ),
        (
            _("Notes Processing"),
            {
                "fields": (
                    "legacy_notes",
                    "parsed_note_type",
                    "parsed_amount_adjustment",
                    "parsed_percentage_adjustment",
                    "parsed_authority",
                    "parsed_reason",
                    "notes_processing_confidence",
                    "normalized_note",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            _("Audit Information"),
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )

    @admin.display(description=_("Variance"))
    def variance_amount_display(self, obj) -> str:
        """Display variance amount with color coding."""
        if obj.variance_amount:
            if abs(obj.variance_amount) <= 1:
                color = "#28a745"  # Green for small variances
            elif abs(obj.variance_amount) <= 50:
                color = "#ffc107"  # Yellow for medium variances
            else:
                color = "#dc3545"  # Red for large variances
            return format_html('<span style="color: {};">${:.2f}</span>', color, obj.variance_amount)
        return format_html('<span style="color: #6c757d;">$0.00</span>')

    @admin.display(description=_("Status"))
    def validation_status_display(self, obj) -> str:
        """Display validation status with color coding."""
        color_map = {
            "VALIDATED": "#28a745",
            "PENDING": "#ffc107",
            "APPROVED": "#007bff",
            "REJECTED": "#dc3545",
        }
        color = color_map.get(obj.validation_status, "#6c757d")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_validation_status_display(),
        )

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset to prevent N+1 queries."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "generated_invoice__student__person",
                "generated_invoice__term",
                "generated_payment",
                "reconstruction_batch",
                "created_by",
                "updated_by",
            )
        )


@admin.register(ReconstructionScholarshipEntry)
class ReconstructionScholarshipEntryAdmin(ComprehensiveAuditMixin, ModelAdmin):
    """Admin interface for reconstruction scholarship entries."""

    list_display = [
        "student_display",
        "term",
        "scholarship_type",
        "scholarship_amount",
        "scholarship_percentage",
        "discovered_from_receipt",
        "requires_reprocessing",
        "applied_to_reconstruction",
    ]
    list_filter = [
        "scholarship_type",
        "term",
        "requires_reprocessing",
        "applied_to_reconstruction",
    ]
    search_fields = [
        "student__person__first_name",
        "student__person__last_name",
        "student__student_id",
        "discovered_from_receipt",
        "discovery_notes",
    ]
    ordering = ["-created_at"]
    list_per_page = 50

    fieldsets = (
        (
            _("Student & Term"),
            {
                "fields": ("student", "term"),
            },
        ),
        (
            _("Scholarship Details"),
            {
                "fields": (
                    "scholarship_type",
                    "scholarship_amount",
                    "scholarship_percentage",
                ),
            },
        ),
        (
            _("Discovery Information"),
            {
                "fields": ("discovered_from_receipt", "discovery_notes"),
            },
        ),
        (
            _("Processing Status"),
            {
                "fields": ("requires_reprocessing", "applied_to_reconstruction"),
            },
        ),
        (
            _("Audit Information"),
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at", "created_by", "updated_by"]

    @admin.display(description=_("Student"))
    def student_display(self, obj) -> str:
        """Display student information."""
        student_id = getattr(obj.student, "student_id", None)
        if student_id is not None:
            formatted_id = format_student_id(student_id)
            return f"{obj.student} ({formatted_id})"
        return f"{obj.student} (N/A)"

    def save_model(self, request, obj, form, change):
        """Set user tracking on save."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset to prevent N+1 queries."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "student__person",
                "term",
                "created_by",
                "updated_by",
            )
        )


@admin.register(ClerkIdentification)
class ClerkIdentificationAdmin(ComprehensiveAuditMixin, ModelAdmin):
    """Admin interface for clerk identification tracking."""

    list_display = [
        "clerk_name",
        "computer_identifier",
        "extraction_confidence",
        "receipt_count",
        "first_seen_date",
        "last_seen_date",
        "verified_by_user",
    ]
    list_filter = [
        "extraction_confidence",
        "verified_by_user",
        "first_seen_date",
        "last_seen_date",
    ]
    search_fields = [
        "clerk_name",
        "computer_identifier",
        "receipt_id_pattern",
        "verification_notes",
    ]
    ordering = ["-receipt_count", "clerk_name"]
    list_per_page = 50

    fieldsets = (
        (
            _("Clerk Information"),
            {
                "fields": ("clerk_name", "computer_identifier"),
            },
        ),
        (
            _("Pattern Matching"),
            {
                "fields": ("receipt_id_pattern", "extraction_confidence"),
            },
        ),
        (
            _("Usage Statistics"),
            {
                "fields": ("first_seen_date", "last_seen_date", "receipt_count"),
            },
        ),
        (
            _("Verification"),
            {
                "fields": ("verified_by_user", "verification_notes"),
            },
        ),
        (
            _("Audit Information"),
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = [
        "first_seen_date",
        "last_seen_date",
        "receipt_count",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
    ]

    def save_model(self, request, obj, form, change):
        """Set user tracking on save."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset to prevent N+1 queries."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "verified_by_user",
                "created_by",
                "updated_by",
            )
        )


@admin.register(AdministrativeFeeConfig)
class AdministrativeFeeConfigAdmin(ComprehensiveAuditMixin, ModelAdmin):
    """Admin interface for administrative fee configurations."""

    list_display = [
        "cycle_type",
        "cycle_type_display",
        "fee_amount",
        "included_document_units",
        "is_active",
        "description_preview",
        "created_at",
    ]
    list_filter = [
        "cycle_type",
        "is_active",
        "created_at",
    ]
    search_fields = ["description"]
    ordering = ["cycle_type"]
    list_per_page = 50

    fieldsets = (
        (_("Fee Configuration"), {"fields": ("cycle_type", "fee_amount", "included_document_units", "description")}),
        (_("Status"), {"fields": ("is_active",)}),
        (
            _("Audit Information"),
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at", "created_by", "updated_by"]

    @admin.display(description=_("Cycle Type"))
    def cycle_type_display(self, obj):
        """Display cycle type with human-readable name."""
        return obj.get_cycle_type_display()

    @admin.display(description=_("Description"))
    def description_preview(self, obj):
        """Display truncated description."""
        return obj.description[:50] + "..." if len(obj.description) > 50 else obj.description

    def save_model(self, request, obj, form, change):
        """Set user tracking on save."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Optimize queryset to prevent N+1 queries."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "created_by",
                "updated_by",
            )
        )


@admin.register(DocumentExcessFee)
class DocumentExcessFeeAdmin(ComprehensiveAuditMixin, ModelAdmin):
    """Admin interface for document excess fee charges."""

    list_display = [
        "document_request_display",
        "invoice_line_item_display",
        "units_charged",
        "unit_price",
        "total_amount",
        "created_at",
    ]
    list_filter = [
        "created_at",
        "unit_price",
    ]
    search_fields = [
        "document_request__request_id",
        "document_request__student__student_id",
        "invoice_line_item__invoice__invoice_number",
    ]
    ordering = ["-created_at"]
    list_per_page = 50

    fieldsets = (
        (_("Fee Details"), {"fields": ("invoice_line_item", "document_request", "units_charged", "unit_price")}),
        (
            _("Audit Information"),
            {
                "fields": ("created_at", "updated_at", "created_by", "updated_by"),
                "classes": ("collapse",),
            },
        ),
    )

    readonly_fields = ["created_at", "updated_at", "created_by", "updated_by", "total_amount"]

    def get_queryset(self, request):
        """Optimize queries to prevent N+1 issues."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "invoice_line_item__invoice",
                "document_request__student__person",
                "document_request__document_type",
            )
        )

    @admin.display(description=_("Document Request"))
    def document_request_display(self, obj):
        """Display document request information."""
        return format_html(
            "<strong>{}</strong><br><small>{} - {}</small>",
            obj.document_request.document_type.name,
            obj.document_request.student.person.full_name,
            obj.document_request.request_id[:8],
        )

    @admin.display(description=_("Invoice"))
    def invoice_line_item_display(self, obj):
        """Display invoice information."""
        return format_html(
            "<strong>{}</strong><br><small>{}</small>",
            obj.invoice_line_item.invoice.invoice_number,
            obj.invoice_line_item.description,
        )

    @admin.display(description=_("Total Amount"))
    def total_amount(self, obj):
        """Display total amount."""
        return f"${obj.total_amount}"

    def save_model(self, request, obj, form, change):
        """Set user tracking on save."""
        if not change:
            obj.created_by = request.user
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)


# Import the optimized Invoice admin for performance with 90,000+ records
