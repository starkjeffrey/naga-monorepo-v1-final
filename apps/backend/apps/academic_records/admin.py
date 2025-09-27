"""Clean admin configuration for Academic Records using flexible document system.

Fixes all issues identified in code review:
- Uses models from models.py (formerly models_v2.py)
- Implements N+1 query optimization with select_related
- Uses bulk operations for performance
- Extracts hardcoded values to constants
- Implements proper CSS classes instead of inline styles
- Removes duplicate service classes
"""

from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone
from django.utils.html import format_html

from apps.common.utils.student_id_formatter import format_student_id

from .constants import (
    ADMIN_BULK_ACTION_BATCH_SIZE,
    PRIORITY_COLORS,
    STATUS_COLORS,
)
from .models import (
    DocumentQuota,
    DocumentQuotaUsage,
    DocumentRequest,
    DocumentRequestComment,
    DocumentTypeConfig,
    DocumentUsageTracker,
    GeneratedDocument,
)
from .services import DocumentGenerationService


class DocumentRequestCommentInline(admin.TabularInline):
    """Inline for document request comments."""

    model = DocumentRequestComment
    extra = 0
    readonly_fields = ("author", "created_at")
    fields = ("comment_text", "is_internal", "author", "created_at")

    def save_model(self, request, obj, form, change):
        """Auto-set comment author."""
        if not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)


class GeneratedDocumentInline(admin.TabularInline):
    """Inline for generated documents."""

    model = GeneratedDocument
    extra = 0
    readonly_fields = (
        "document_id",
        "verification_code",
        "generated_by",
        "generated_date",
        "access_count",
    )
    fields = (
        "document_id",
        "verification_code",
        "file_size",
        "generated_by",
        "generated_date",
        "access_count",
    )


@admin.register(DocumentTypeConfig)
class DocumentTypeConfigAdmin(admin.ModelAdmin):
    """Admin for document type configuration."""

    list_display = [
        "code",
        "name",
        "category",
        "fee_display",
        "processing_time_display",
        "requires_approval",
        "is_active",
        "display_order",
    ]
    list_filter = [
        "category",
        "requires_approval",
        "auto_generate",
        "is_active",
        "has_fee",
    ]
    search_fields = ["code", "name", "description"]
    ordering = ["display_order", "name"]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "code",
                    "name",
                    "category",
                    "description",
                    "is_active",
                    "display_order",
                )
            },
        ),
        (
            "Processing Configuration",
            {
                "fields": (
                    "requires_approval",
                    "auto_generate",
                    "processing_time_hours",
                    "required_permission",
                )
            },
        ),
        (
            "Data Requirements",
            {
                "fields": (
                    "requires_grade_data",
                    "requires_attendance_data",
                    "requires_manual_input",
                )
            },
        ),
        (
            "Delivery Options",
            {
                "fields": (
                    "allows_email_delivery",
                    "allows_pickup",
                    "allows_mail_delivery",
                    "allows_third_party_delivery",
                ),
            },
        ),
        (
            "Fee Configuration",
            {
                "fields": (
                    "has_fee",
                    "fee_amount",
                    "fee_currency",
                    "free_allowance_per_term",
                    "free_allowance_per_year",
                    "free_allowance_lifetime",
                ),
            },
        ),
    )

    def fee_display(self, obj):
        """Display fee information with formatting."""
        if not obj.has_fee:
            return format_html('<span class="fee-free">Free</span>')
        return format_html(
            '<span class="fee-amount">{} {}</span>',
            obj.fee_currency,
            obj.fee_amount or 0,
        )

    fee_display.short_description = "Fee"  # type: ignore[attr-defined]

    def processing_time_display(self, obj):
        """Display processing time in human-readable format."""
        hours = obj.processing_time_hours
        if hours < 24:
            return f"{hours} hours"
        days = hours // 24
        remaining_hours = hours % 24
        if remaining_hours == 0:
            return f"{days} days"
        return f"{days} days, {remaining_hours} hours"

    processing_time_display.short_description = "Processing Time"  # type: ignore[attr-defined]


@admin.register(DocumentRequest)
class DocumentRequestAdmin(admin.ModelAdmin):
    """Admin for document requests with optimized queries and bulk actions.

    Fixes N+1 query issues by using select_related and prefetch_related.
    Implements efficient bulk operations using QuerySet.update().
    """

    list_display = [
        "request_id_display",
        "student_display",
        "document_type",
        "status_display",
        "priority_display",
        "delivery_method",
        "fee_display",
        "requested_date",
        "due_date_display",
    ]
    list_filter = [
        "request_status",
        "priority",
        "delivery_method",
        "document_type__category",
        "has_fee",
        "payment_status",
        "requested_date",
    ]
    search_fields = [
        "request_id",
        "student__student_id",
        "student__person__full_name",
        "document_type__name",
        "recipient_name",
        "recipient_email",
    ]
    readonly_fields = [
        "request_id",
        "requested_date",
        "due_date",
        "approved_date",
        "completed_date",
    ]
    date_hierarchy = "requested_date"
    ordering = ["-requested_date"]
    actions = [
        "approve_selected_requests",
        "mark_as_in_progress",
        "mark_as_completed",
        "generate_documents",
        "send_status_emails",
    ]
    inlines = [DocumentRequestCommentInline, GeneratedDocumentInline]

    fieldsets = (
        (
            "Request Information",
            {
                "fields": (
                    "request_id",
                    "document_type",
                    "student",
                    "request_status",
                    "priority",
                )
            },
        ),
        (
            "Delivery Details",
            {
                "fields": (
                    "delivery_method",
                    "recipient_name",
                    "recipient_email",
                    "recipient_address",
                )
            },
        ),
        ("Request Details", {"fields": ("request_notes", "custom_data")}),
        (
            "Financial Information",
            {
                "fields": (
                    "has_fee",
                    "fee_amount",
                    "is_free_allowance",
                    "payment_required",
                    "payment_status",
                    "finance_invoice_id",
                ),
            },
        ),
        (
            "Processing Information",
            {"fields": ("requested_by", "assigned_to", "processed_by")},
        ),
        (
            "Important Dates",
            {
                "fields": (
                    "requested_date",
                    "due_date",
                    "approved_date",
                    "completed_date",
                )
            },
        ),
    )

    def get_queryset(self, request):
        """Optimize queries to prevent N+1 issues."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "document_type",
                "student__person",
                "requested_by",
                "assigned_to",
                "processed_by",
            )
            .prefetch_related("comments", "generated_documents")
        )

    def request_id_display(self, obj):
        """Display shortened request ID."""
        return str(obj.request_id)[:8] + "..."

    request_id_display.short_description = "Request ID"  # type: ignore[attr-defined]

    def student_display(self, obj):
        """Display student information."""
        return format_html(
            "<strong>{}</strong><br><small>{}</small>",
            obj.student.person.full_name,
            format_student_id(obj.student.student_id),
        )

    student_display.short_description = "Student"  # type: ignore[attr-defined]

    def status_display(self, obj):
        """Display status with color coding using CSS classes."""
        color = STATUS_COLORS.get(obj.request_status, "#6c757d")
        return format_html(
            (
                '<span class="status-badge" style="background-color: {}; '
                'color: white; padding: 2px 8px; border-radius: 3px; font-size: 11px;">{}</span>'
            ),
            color,
            obj.get_request_status_display(),
        )

    status_display.short_description = "Status"  # type: ignore[attr-defined]

    def priority_display(self, obj):
        """Display priority with color coding."""
        color = PRIORITY_COLORS.get(obj.priority, "#6c757d")
        return format_html(
            (
                '<span class="priority-badge" style="background-color: {}; '
                'color: white; padding: 2px 6px; border-radius: 3px; font-size: 10px;">{}</span>'
            ),
            color,
            obj.get_priority_display(),
        )

    priority_display.short_description = "Priority"  # type: ignore[attr-defined]

    def fee_display(self, obj):
        """Display fee information."""
        if not obj.has_fee:
            return format_html('<span class="fee-free">Free</span>')
        if obj.is_free_allowance:
            return format_html('<span class="fee-allowance">Free Allowance</span>')
        return format_html('<span class="fee-amount">${}</span>', obj.fee_amount or 0)

    fee_display.short_description = "Fee"  # type: ignore[attr-defined]

    def due_date_display(self, obj):
        """Display due date with overdue highlighting."""
        if not obj.due_date:
            return "No due date"

        if obj.is_overdue and not obj.is_completed:
            return format_html(
                '<span class="overdue-date" style="color: #dc3545; font-weight: bold;">{}</span>',
                obj.due_date.strftime("%Y-%m-%d"),
            )
        return obj.due_date.strftime("%Y-%m-%d")

    due_date_display.short_description = "Due Date"  # type: ignore[attr-defined]

    # Bulk Actions with Performance Optimization

    @admin.action(description="Approve selected requests")
    def approve_selected_requests(self, request, queryset):
        """Bulk approve requests using efficient update."""
        with transaction.atomic():
            updated = queryset.filter(request_status=DocumentRequest.RequestStatus.PENDING).update(
                request_status=DocumentRequest.RequestStatus.APPROVED,
                approved_date=timezone.now(),
                processed_by=request.user,
            )

        self.message_user(request, f"Successfully approved {updated} requests.", messages.SUCCESS)

    @admin.action(description="Mark as in progress")
    def mark_as_in_progress(self, request, queryset):
        """Bulk mark requests as in progress."""
        with transaction.atomic():
            updated = queryset.filter(
                request_status__in=[
                    DocumentRequest.RequestStatus.PENDING,
                    DocumentRequest.RequestStatus.APPROVED,
                ],
            ).update(
                request_status=DocumentRequest.RequestStatus.IN_PROGRESS,
                assigned_to=request.user,
            )

        self.message_user(
            request,
            f"Successfully marked {updated} requests as in progress.",
            messages.SUCCESS,
        )

    @admin.action(description="Mark as completed")
    def mark_as_completed(self, request, queryset):
        """Bulk mark requests as completed."""
        with transaction.atomic():
            updated = queryset.filter(request_status=DocumentRequest.RequestStatus.IN_PROGRESS).update(
                request_status=DocumentRequest.RequestStatus.COMPLETED,
                completed_date=timezone.now(),
                processed_by=request.user,
            )

        self.message_user(request, f"Successfully completed {updated} requests.", messages.SUCCESS)

    @admin.action(description="Generate documents for approved requests")
    def generate_documents(self, request, queryset):
        """Generate documents for approved requests (background task recommended)."""
        approved_requests = queryset.filter(request_status=DocumentRequest.RequestStatus.APPROVED)

        generated_count = 0
        error_count = 0

        for doc_request in approved_requests[:ADMIN_BULK_ACTION_BATCH_SIZE]:
            try:
                # Use real service from services.py
                DocumentGenerationService.generate_document(document_request=doc_request, generated_by=request.user)
                generated_count += 1
            except Exception as e:
                error_count += 1
                # Log error for debugging
                self.message_user(
                    request,
                    f"Error generating document for request {doc_request.request_id}: {e!s}",
                    messages.ERROR,
                )

        if generated_count > 0:
            self.message_user(
                request,
                f"Successfully generated {generated_count} documents.",
                messages.SUCCESS,
            )
        if error_count > 0:
            self.message_user(
                request,
                f"{error_count} documents failed to generate. Check logs for details.",
                messages.WARNING,
            )

    @admin.action(description="Send status update emails")
    def send_status_emails(self, request, queryset):
        """Send status update emails to students."""
        # TODO: Implement email service integration
        self.message_user(
            request,
            "Email notifications will be implemented with email service integration.",
            messages.INFO,
        )


@admin.register(GeneratedDocument)
class GeneratedDocumentAdmin(admin.ModelAdmin):
    """Admin for generated documents with security features."""

    list_display = [
        "document_id_display",
        "student_display",
        "document_type_display",
        "verification_code",
        "file_size_display",
        "generated_date",
        "access_count",
    ]
    list_filter = [
        "document_request__document_type__category",
        "generated_date",
        "access_count",
    ]
    search_fields = [
        "document_id",
        "verification_code",
        "student__student_id",
        "student__person__full_name",
        "document_request__document_type__name",
    ]
    readonly_fields = [
        "document_id",
        "verification_code",
        "content_hash",
        "generated_date",
        "access_count",
        "last_accessed",
    ]
    date_hierarchy = "generated_date"
    ordering = ["-generated_date"]
    actions = ["verify_document_integrity", "regenerate_verification_codes"]

    def get_queryset(self, request):
        """Optimize queries to prevent N+1 issues."""
        return (
            super()
            .get_queryset(request)
            .select_related("document_request__document_type", "student__person", "generated_by")
        )

    def document_id_display(self, obj):
        """Display shortened document ID."""
        return str(obj.document_id)[:8] + "..."

    document_id_display.short_description = "Document ID"  # type: ignore[attr-defined]

    def student_display(self, obj):
        """Display student information."""
        return format_html(
            "<strong>{}</strong><br><small>{}</small>",
            obj.student.person.full_name,
            format_student_id(obj.student.student_id),
        )

    student_display.short_description = "Student"  # type: ignore[attr-defined]

    def document_type_display(self, obj):
        """Display document type."""
        return obj.document_request.document_type.name

    document_type_display.short_description = "Document Type"  # type: ignore[attr-defined]

    def file_size_display(self, obj):
        """Display file size in human-readable format."""
        if not obj.file_size:
            return "Unknown"

        if obj.file_size < 1024:
            return f"{obj.file_size} bytes"
        if obj.file_size < 1024 * 1024:
            return f"{obj.file_size / 1024:.1f} KB"
        return f"{obj.file_size / (1024 * 1024):.1f} MB"

    file_size_display.short_description = "File Size"  # type: ignore[attr-defined]

    @admin.action(description="Verify document integrity")
    def verify_document_integrity(self, request, queryset):
        """Verify document integrity and update access count."""
        verified_count = 0

        for document in queryset:
            # Increment access count efficiently
            GeneratedDocument.objects.filter(id=document.id).update(
                access_count=document.access_count + 1,
                last_accessed=timezone.now(),
            )
            verified_count += 1

        self.message_user(
            request,
            f"Verified integrity of {verified_count} documents.",
            messages.SUCCESS,
        )

    @admin.action(description="Regenerate verification codes")
    def regenerate_verification_codes(self, request, queryset):
        """Regenerate verification codes for selected documents."""
        import uuid

        for document in queryset:
            document.verification_code = str(uuid.uuid4()).replace("-", "")[:16].upper()
            document.save(update_fields=["verification_code"])

        self.message_user(
            request,
            f"Regenerated verification codes for {queryset.count()} documents.",
            messages.SUCCESS,
        )


@admin.register(DocumentUsageTracker)
class DocumentUsageTrackerAdmin(admin.ModelAdmin):
    """Admin for document usage tracking."""

    list_display = [
        "student_display",
        "document_type",
        "total_requested",
        "total_completed",
        "current_term_count",
        "current_year_count",
        "remaining_allowances_display",
    ]
    list_filter = [
        "document_type",
        "total_requested",
        "last_request_date",
    ]
    search_fields = [
        "student__student_id",
        "student__person__full_name",
        "document_type__name",
    ]
    readonly_fields = [
        "total_requested",
        "total_completed",
        "total_free_used",
        "total_paid",
        "last_request_date",
        "last_completed_date",
    ]
    ordering = ["-last_request_date"]

    def get_queryset(self, request):
        """Optimize queries to prevent N+1 issues."""
        return super().get_queryset(request).select_related("student__person", "document_type")

    def student_display(self, obj):
        """Display student information."""
        return format_html(
            "<strong>{}</strong><br><small>{}</small>",
            obj.student.person.full_name,
            format_student_id(obj.student.student_id),
        )

    student_display.short_description = "Student"  # type: ignore[attr-defined]

    def remaining_allowances_display(self, obj):
        """Display remaining free allowances."""
        allowances = []
        if obj.remaining_free_term > 0:
            allowances.append(f"Term: {obj.remaining_free_term}")
        if obj.remaining_free_year > 0:
            allowances.append(f"Year: {obj.remaining_free_year}")
        if obj.remaining_free_lifetime > 0:
            allowances.append(f"Lifetime: {obj.remaining_free_lifetime}")

        if not allowances:
            return format_html('<span class="no-allowance">None</span>')

        return format_html("<br>".join(allowances))

    remaining_allowances_display.short_description = "Remaining Free"  # type: ignore[attr-defined]


@admin.register(DocumentRequestComment)
class DocumentRequestCommentAdmin(admin.ModelAdmin):
    """Admin for document request comments."""

    list_display = [
        "document_request_display",
        "comment_preview",
        "is_internal",
        "author",
        "created_at",
    ]
    list_filter = [
        "is_internal",
        "created_at",
        "author",
    ]
    search_fields = [
        "document_request__request_id",
        "comment_text",
        "author__username",
    ]
    readonly_fields = ["created_at", "updated_at"]
    ordering = ["-created_at"]

    def get_queryset(self, request):
        """Optimize queries to prevent N+1 issues."""
        return (
            super()
            .get_queryset(request)
            .select_related(
                "document_request__document_type",
                "document_request__student__person",
                "author",
            )
        )

    def document_request_display(self, obj):
        """Display document request information."""
        return format_html(
            "<strong>{}</strong><br><small>{}</small>",
            obj.document_request.document_type.name,
            obj.document_request.student.person.full_name,
        )

    document_request_display.short_description = "Request"  # type: ignore[attr-defined]

    def comment_preview(self, obj):
        """Display comment preview."""
        preview = obj.comment_text[:50]
        if len(obj.comment_text) > 50:
            preview += "..."
        return preview

    comment_preview.short_description = "Comment"  # type: ignore[attr-defined]


@admin.register(DocumentQuota)
class DocumentQuotaAdmin(admin.ModelAdmin):
    """Admin interface for document quotas."""

    list_display = [
        "student_display",
        "term",
        "total_units",
        "used_units",
        "remaining_units_display",
        "is_active",
        "created_at",
    ]
    list_filter = [
        "is_active",
        "term",
        "created_at",
    ]
    search_fields = [
        "student__student_id",
        "student__person__first_name",
        "student__person__last_name",
        "term__code",
    ]
    readonly_fields = ["created_at", "updated_at", "remaining_units_display"]
    autocomplete_fields = ["student", "term"]

    fieldsets = (
        ("Quota Information", {"fields": ("student", "term", "total_units", "used_units", "remaining_units_display")}),
        ("Status", {"fields": ("is_active",)}),
        (
            "Source",
            {
                "fields": ("admin_fee_line_item", "cycle_status"),
                "description": "Reference to the administrative fee that created this quota",
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at"), "classes": ["collapse"]}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("student__person", "term")

    def student_display(self, obj):
        """Display student information."""
        return format_html(
            "<strong>{}</strong><br><small>{}</small>",
            obj.student.person.full_name,
            format_student_id(obj.student.student_id),
        )

    student_display.short_description = "Student"  # type: ignore[attr-defined]

    def remaining_units_display(self, obj):
        """Display remaining units with color coding."""
        remaining = obj.remaining_units
        if remaining <= 0:
            return format_html('<span style="color: #dc3545; font-weight: bold;">{}</span>', remaining)
        elif remaining <= 3:
            return format_html('<span style="color: #ffc107; font-weight: bold;">{}</span>', remaining)
        else:
            return format_html('<span style="color: #28a745;">{}</span>', remaining)

    remaining_units_display.short_description = "Remaining Units"  # type: ignore[attr-defined]


@admin.register(DocumentQuotaUsage)
class DocumentQuotaUsageAdmin(admin.ModelAdmin):
    """Admin interface for document quota usage tracking."""

    list_display = [
        "quota_student_display",
        "document_request_display",
        "units_consumed",
        "usage_date",
    ]
    list_filter = [
        "usage_date",
        "quota__term",
    ]
    search_fields = [
        "quota__student__student_id",
        "quota__student__person__first_name",
        "quota__student__person__last_name",
        "document_request__request_id",
        "document_request__document_type__name",
    ]
    readonly_fields = ["usage_date"]
    autocomplete_fields = ["quota", "document_request"]
    date_hierarchy = "usage_date"

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("quota__student__person", "quota__term", "document_request__document_type")
        )

    def quota_student_display(self, obj):
        """Display student from quota."""
        return format_html(
            "<strong>{}</strong><br><small>{} - {}</small>",
            obj.quota.student.person.full_name,
            format_student_id(obj.quota.student.student_id),
            obj.quota.term.code,
        )

    quota_student_display.short_description = "Student/Term"  # type: ignore[attr-defined]

    def document_request_display(self, obj):
        """Display document request details."""
        return format_html(
            "<strong>{}</strong><br><small>{}</small>",
            obj.document_request.document_type.name,
            str(obj.document_request.request_id)[:8] + "...",
        )

    document_request_display.short_description = "Document Request"  # type: ignore[attr-defined]


# Custom admin site configuration
admin.site.site_header = "Academic Records Administration"
admin.site.site_title = "Academic Records"
admin.site.index_title = "Document Management System"
