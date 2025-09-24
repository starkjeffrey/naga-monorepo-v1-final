"""Optimized Invoice Admin for handling 90,000+ records efficiently.

This module provides performance-optimized admin interfaces for the finance app,
specifically designed to handle large datasets with minimal database queries.
"""

from typing import Any

from django.contrib import admin
from django.db.models import F, Prefetch, QuerySet
from django.http import HttpRequest
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from apps.common.utils import format_student_id
from apps.finance.models import Invoice, InvoiceLineItem


class OptimizedInvoiceLineItemInline(admin.TabularInline):
    """Optimized inline for invoice line items."""

    model = InvoiceLineItem
    extra = 0
    fields = [
        "description",
        "line_item_type",
        "unit_price",
        "quantity",
        "line_total",
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


@admin.register(Invoice)
class OptimizedInvoiceAdmin(admin.ModelAdmin):
    """Highly optimized Invoice admin for 90,000+ records."""

    # List display configuration - minimize property access
    list_display = [
        "invoice_number",
        "formatted_student",  # Optimized method
        "term_display",  # Optimized method
        "status_display",
        "issue_date",
        "due_date",
        "total_amount",
        "paid_amount",
        "calculated_amount_due",  # Pre-calculated in queryset
    ]

    # List filters - use database indexes
    list_filter = [
        "status",
        "term",
        "issue_date",
        "currency",
        "is_historical",
    ]

    # Search configuration - limit to indexed fields
    search_fields = [
        "invoice_number",  # Unique index
        "=student__student_id",  # Exact match for performance
        "student__person__last_name",  # Most selective name field
    ]

    # Date navigation
    date_hierarchy = "issue_date"

    # Ordering - use indexed fields
    ordering = ["-issue_date", "-id"]

    # Pagination - limit records per page
    list_per_page = 50
    list_max_show_all = 200

    # Disable sorting on expensive columns
    sortable_by = [
        "invoice_number",
        "issue_date",
        "due_date",
        "total_amount",
        "status",
    ]

    # Read-only fields to prevent accidental updates
    readonly_fields = [
        "created_at",
        "updated_at",
        "sent_date",
        "calculated_totals_display",
    ]

    # Inline configuration
    inlines = []  # Remove inlines from list view for performance

    def get_queryset(self, request: HttpRequest) -> QuerySet:
        """Heavily optimized queryset with pre-calculated fields."""
        qs = super().get_queryset(request)

        # Annotate with calculated amount due to avoid property access
        qs = qs.annotate(calculated_amount_due=F("total_amount") - F("paid_amount"))

        # Essential select_related for display fields only
        qs = qs.select_related(
            "student__person",  # For student display
            "term",  # For term display
        )

        # Prefetch line items with a limited queryset
        # Only prefetch if viewing change form, not list
        if request.resolver_match and request.resolver_match.url_name == "finance_invoice_change":
            line_items_qs = InvoiceLineItem.objects.select_related(
                "enrollment__class_header__course",
                "fee_pricing__fee",
            )
            qs = qs.prefetch_related(Prefetch("line_items", queryset=line_items_qs))

        # Aggregate payment count for list display (optional)
        # Removed to improve performance - only calculate on demand

        return qs

    def get_list_display(self, request: HttpRequest) -> list:
        """Adjust list display based on request parameters."""
        # Remove expensive columns when searching or filtering
        if request.GET:
            # Simplified display when filtering
            return [
                "invoice_number",
                "formatted_student",
                "term_display",
                "status",
                "total_amount",
                "calculated_amount_due",
            ]
        return self.list_display

    def changelist_view(self, request: HttpRequest, extra_context: dict | None = None) -> Any:
        """Optimize changelist view."""
        # Add performance hints
        if extra_context is None:
            extra_context = {}

        # Get total count efficiently
        total_count = self.model.objects.count()
        if total_count > 10000:
            extra_context["performance_warning"] = (
                f"Large dataset ({total_count:,} records). Use filters to narrow results for better performance."
            )

        return super().changelist_view(request, extra_context)

    def change_view(
        self, request: HttpRequest, object_id: str, form_url: str = "", extra_context: dict | None = None
    ) -> Any:
        """Re-enable inlines for detail view."""
        original_inlines = self.inlines
        self.inlines = [OptimizedInvoiceLineItemInline]  # type: ignore[misc]

        try:
            return super().change_view(request, object_id, form_url, extra_context)
        finally:
            self.inlines = original_inlines  # type: ignore[misc]

    # Optimized display methods
    @admin.display(description=_("Student"), ordering="student__person__family_name")
    def formatted_student(self, obj) -> str:
        """Optimized student display using select_related data."""
        # Access pre-fetched data only
        student_id = obj.student.student_id
        if student_id:
            return format_html("{} ({})", obj.student.person.full_name, format_student_id(student_id))
        return f"{obj.student.person.full_name} (N/A)"

    @admin.display(description=_("Term"), ordering="term__start_date")
    def term_display(self, obj) -> str:
        """Optimized term display using select_related data."""
        return obj.term.code if obj.term else "—"

    @admin.display(description=_("Status"))
    def status_display(self, obj) -> str:
        """Display status with simple formatting."""
        # Simplified color coding for performance
        if obj.status == "OVERDUE":
            return format_html('<b style="color:red">{}</b>', obj.get_status_display())
        elif obj.status == "PAID":
            return format_html('<span style="color:green">{}</span>', obj.get_status_display())
        return obj.get_status_display()

    @admin.display(description=_("Amount Due"), ordering="calculated_amount_due")
    def calculated_amount_due(self, obj) -> str:
        """Display pre-calculated amount due."""
        # Use annotated field instead of property
        amount = obj.calculated_amount_due
        if amount and amount > 0:
            return format_html('<b style="color:red">{} {}</b>', f"{amount:.2f}", obj.currency)
        return format_html('<span style="color:green">0.00 {}</span>', obj.currency)

    @admin.display(description=_("Totals"))
    def calculated_totals_display(self, obj) -> str:
        """Display invoice totals for detail view."""
        return format_html(
            "Subtotal: {}<br>Tax: {}<br>Total: {}<br>Paid: {}<br>Due: {}",
            f"{obj.subtotal:.2f}",
            f"{obj.tax_amount:.2f}",
            f"{obj.total_amount:.2f}",
            f"{obj.paid_amount:.2f}",
            f"{obj.total_amount - obj.paid_amount:.2f}",
        )

    # Performance optimization settings
    def get_search_results(self, request, queryset, search_term):
        """Optimize search to use specific fields."""
        # If searching for a number, assume it's a student ID
        if search_term.isdigit():
            # Direct student ID search
            queryset = queryset.filter(student__student_id=search_term)
            return queryset, False

        # Otherwise use default search
        return super().get_search_results(request, queryset, search_term)

    # Bulk actions optimization
    actions = ["mark_as_sent", "mark_as_paid"]

    @admin.action(description=_("Mark selected invoices as sent"))
    def mark_as_sent(self, request, queryset):
        """Bulk update status to sent."""
        from django.utils import timezone

        count = queryset.update(status=Invoice.InvoiceStatus.SENT, sent_date=timezone.now())
        self.message_user(request, f"{count} invoices marked as sent.")

    @admin.action(description=_("Mark selected invoices as paid"))
    def mark_as_paid(self, request, queryset):
        """Bulk update status to paid."""
        # Only update invoices where paid_amount equals total_amount
        count = queryset.filter(paid_amount=F("total_amount")).update(status=Invoice.InvoiceStatus.PAID)
        self.message_user(request, f"{count} invoices marked as paid.")

    class Media:
        css = {"all": ("admin/css/finance_optimized.css",)}
        js = ("admin/js/finance_optimized.js",)
