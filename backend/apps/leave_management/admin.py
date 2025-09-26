"""Admin configuration for leave management app."""

from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse
from django.db.models import Count, Sum

from apps.leave_management.models import (
    LeaveType,
    LeavePolicy,
    LeaveBalance,
    LeaveRequest,
    SubstituteAssignment,
    LeaveReport,
)


@admin.register(LeaveType)
class LeaveTypeAdmin(admin.ModelAdmin):
    """Admin for leave types."""

    list_display = [
        "name",
        "code",
        "category",
        "requires_documentation",
        "max_consecutive_days",
        "advance_notice_days",
        "is_active",
    ]
    list_filter = [
        "category",
        "requires_documentation",
        "is_active",
    ]
    search_fields = ["name", "code"]
    ordering = ["category", "name"]

    fieldsets = (
        (None, {
            "fields": ("name", "code", "category", "is_active"),
        }),
        ("Requirements", {
            "fields": (
                "requires_documentation",
                "advance_notice_days",
                "max_consecutive_days",
            ),
        }),
    )


@admin.register(LeavePolicy)
class LeavePolicyAdmin(admin.ModelAdmin):
    """Admin for leave policies."""

    list_display = [
        "contract_type",
        "leave_type",
        "annual_days",
        "accrual_rate",
        "carries_forward",
        "max_carryover",
        "effective_date",
        "end_date",
        "is_current",
    ]
    list_filter = [
        "contract_type",
        "leave_type",
        "carries_forward",
        "effective_date",
    ]
    search_fields = [
        "contract_type",
        "leave_type__name",
    ]
    date_hierarchy = "effective_date"
    ordering = ["contract_type", "leave_type", "-effective_date"]

    def is_current(self, obj):
        """Check if policy is currently active."""
        today = timezone.now().date()
        is_active = obj.effective_date <= today
        if obj.end_date:
            is_active = is_active and obj.end_date >= today
        return is_active
    is_current.boolean = True
    is_current.short_description = "Currently Active"


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    """Admin for leave balances."""

    list_display = [
        "teacher",
        "leave_type",
        "year",
        "entitled_days",
        "used_days",
        "pending_days",
        "carried_forward",
        "available_days_display",
    ]
    list_filter = [
        "year",
        "leave_type",
        ("teacher", admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = [
        "teacher__person__name",
        "leave_type__name",
    ]
    ordering = ["-year", "teacher"]
    readonly_fields = ["available_days_display"]

    def available_days_display(self, obj):
        """Display available days with color coding."""
        available = obj.available_days
        if available < 0:
            color = "red"
        elif available < 3:
            color = "orange"
        else:
            color = "green"
        return format_html(
            '<span style="color: {};">{}</span>',
            color,
            available
        )
    available_days_display.short_description = "Available Days"

    fieldsets = (
        (None, {
            "fields": ("teacher", "leave_type", "year"),
        }),
        ("Balance", {
            "fields": (
                "entitled_days",
                "carried_forward",
                "used_days",
                "pending_days",
                "available_days_display",
            ),
        }),
    )


@admin.register(LeaveRequest)
class LeaveRequestAdmin(admin.ModelAdmin):
    """Admin for leave requests."""

    list_display = [
        "request_number",
        "teacher",
        "leave_type",
        "start_date",
        "end_date",
        "total_days",
        "status_badge",
        "priority_badge",
        "requires_substitute",
        "submitted_date",
        "reviewed_by",
    ]
    list_filter = [
        "status",
        "priority",
        "leave_type",
        "requires_substitute",
        "start_date",
        ("teacher", admin.RelatedOnlyFieldListFilter),
        ("reviewed_by", admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = [
        "teacher__person__name",
        "reason",
        "review_notes",
    ]
    date_hierarchy = "start_date"
    ordering = ["-start_date", "-created_at"]
    readonly_fields = [
        "total_days",
        "is_emergency",
        "submitted_date",
        "reviewed_by",
        "review_date",
    ]

    def request_number(self, obj):
        """Display formatted request number."""
        return f"LR-{obj.id:04d}"
    request_number.short_description = "Request #"

    def status_badge(self, obj):
        """Display status with color badge."""
        colors = {
            LeaveRequest.Status.DRAFT: "gray",
            LeaveRequest.Status.PENDING: "yellow",
            LeaveRequest.Status.APPROVED: "green",
            LeaveRequest.Status.REJECTED: "red",
            LeaveRequest.Status.CANCELLED: "gray",
            LeaveRequest.Status.SUBSTITUTE_PENDING: "orange",
            LeaveRequest.Status.SUBSTITUTE_ASSIGNED: "blue",
            LeaveRequest.Status.COMPLETED: "green",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"

    def priority_badge(self, obj):
        """Display priority with color badge."""
        colors = {
            LeaveRequest.Priority.LOW: "lightgray",
            LeaveRequest.Priority.NORMAL: "blue",
            LeaveRequest.Priority.HIGH: "orange",
            LeaveRequest.Priority.EMERGENCY: "red",
        }
        color = colors.get(obj.priority, "gray")
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_priority_display()
        )
    priority_badge.short_description = "Priority"

    fieldsets = (
        (None, {
            "fields": (
                "teacher",
                "leave_type",
                "start_date",
                "end_date",
                "total_days",
            ),
        }),
        ("Request Details", {
            "fields": (
                "reason",
                "priority",
                "status",
                "supporting_documents",
            ),
        }),
        ("Substitute", {
            "fields": (
                "requires_substitute",
                "substitute_notes",
            ),
        }),
        ("Approval", {
            "fields": (
                "submitted_date",
                "reviewed_by",
                "review_date",
                "review_notes",
            ),
        }),
    )

    actions = [
        "approve_requests",
        "reject_requests",
        "mark_as_needs_substitute",
    ]

    def approve_requests(self, request, queryset):
        """Bulk approve leave requests."""
        pending = queryset.filter(status=LeaveRequest.Status.PENDING)
        for leave_request in pending:
            leave_request.approve(request.user, "Bulk approved via admin")
        self.message_user(
            request,
            f"Approved {pending.count()} leave requests."
        )
    approve_requests.short_description = "Approve selected requests"

    def reject_requests(self, request, queryset):
        """Bulk reject leave requests."""
        pending = queryset.filter(status=LeaveRequest.Status.PENDING)
        for leave_request in pending:
            leave_request.reject(request.user, "Bulk rejected via admin")
        self.message_user(
            request,
            f"Rejected {pending.count()} leave requests."
        )
    reject_requests.short_description = "Reject selected requests"

    def mark_as_needs_substitute(self, request, queryset):
        """Mark requests as needing substitute."""
        approved = queryset.filter(status=LeaveRequest.Status.APPROVED)
        approved.update(
            status=LeaveRequest.Status.SUBSTITUTE_PENDING,
            requires_substitute=True
        )
        self.message_user(
            request,
            f"Marked {approved.count()} requests as needing substitute."
        )
    mark_as_needs_substitute.short_description = "Mark as needs substitute"


@admin.register(SubstituteAssignment)
class SubstituteAssignmentAdmin(admin.ModelAdmin):
    """Admin for substitute assignments."""

    list_display = [
        "assignment_number",
        "leave_request_link",
        "substitute_teacher",
        "status_badge",
        "assignment_date",
        "confirmed_date",
        "permissions_granted",
        "classes_count",
    ]
    list_filter = [
        "status",
        "permissions_granted",
        "assignment_date",
        ("substitute_teacher", admin.RelatedOnlyFieldListFilter),
        ("assigned_by", admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = [
        "substitute_teacher__person__name",
        "leave_request__teacher__person__name",
        "substitute_notes",
    ]
    date_hierarchy = "assignment_date"
    ordering = ["-assignment_date"]
    readonly_fields = [
        "assignment_date",
        "confirmed_date",
        "declined_date",
        "permissions_granted_date",
        "permissions_revoked_date",
    ]
    filter_horizontal = ["classes_to_cover"]

    def assignment_number(self, obj):
        """Display formatted assignment number."""
        return f"SA-{obj.id:04d}"
    assignment_number.short_description = "Assignment #"

    def leave_request_link(self, obj):
        """Link to leave request."""
        url = reverse(
            "admin:leave_management_leaverequest_change",
            args=[obj.leave_request.id]
        )
        return format_html(
            '<a href="{}">{} - {}</a>',
            url,
            obj.leave_request.teacher,
            obj.leave_request.start_date
        )
    leave_request_link.short_description = "Leave Request"

    def status_badge(self, obj):
        """Display status with color badge."""
        colors = {
            SubstituteAssignment.Status.PENDING: "yellow",
            SubstituteAssignment.Status.CONFIRMED: "green",
            SubstituteAssignment.Status.DECLINED: "red",
            SubstituteAssignment.Status.COMPLETED: "blue",
            SubstituteAssignment.Status.CANCELLED: "gray",
        }
        color = colors.get(obj.status, "gray")
        return format_html(
            '<span style="background-color: {}; color: white; '
            'padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"

    def classes_count(self, obj):
        """Count of classes to cover."""
        return obj.classes_to_cover.count()
    classes_count.short_description = "Classes"

    fieldsets = (
        (None, {
            "fields": (
                "leave_request",
                "substitute_teacher",
                "status",
            ),
        }),
        ("Assignment Details", {
            "fields": (
                "assigned_by",
                "assignment_date",
                "classes_to_cover",
                "substitute_notes",
            ),
        }),
        ("Communication", {
            "fields": (
                "notification_sent",
                "notification_date",
            ),
        }),
        ("Confirmation", {
            "fields": (
                "confirmed_date",
                "declined_date",
                "decline_reason",
            ),
        }),
        ("Permissions", {
            "fields": (
                "permissions_granted",
                "permissions_granted_date",
                "permissions_revoked_date",
            ),
        }),
    )

    actions = ["confirm_assignments", "send_notifications"]

    def confirm_assignments(self, request, queryset):
        """Bulk confirm assignments."""
        pending = queryset.filter(status=SubstituteAssignment.Status.PENDING)
        for assignment in pending:
            assignment.confirm()
        self.message_user(
            request,
            f"Confirmed {pending.count()} substitute assignments."
        )
    confirm_assignments.short_description = "Confirm selected assignments"

    def send_notifications(self, request, queryset):
        """Send notifications to substitutes."""
        not_notified = queryset.filter(notification_sent=False)
        for assignment in not_notified:
            # TODO: Implement actual notification
            assignment.notification_sent = True
            assignment.notification_date = timezone.now()
            assignment.save()
        self.message_user(
            request,
            f"Sent notifications for {not_notified.count()} assignments."
        )
    send_notifications.short_description = "Send notifications"


@admin.register(LeaveReport)
class LeaveReportAdmin(admin.ModelAdmin):
    """Admin for leave reports."""

    list_display = [
        "report_number",
        "report_type",
        "period_start",
        "period_end",
        "generated_by",
        "generated_date",
        "has_file",
    ]
    list_filter = [
        "report_type",
        "generated_date",
        ("generated_by", admin.RelatedOnlyFieldListFilter),
    ]
    search_fields = ["generated_by__username"]
    date_hierarchy = "period_end"
    ordering = ["-period_end", "-generated_date"]
    readonly_fields = ["generated_date", "summary_data", "detail_data"]

    def report_number(self, obj):
        """Display formatted report number."""
        return f"LR-{obj.id:04d}"
    report_number.short_description = "Report #"

    def has_file(self, obj):
        """Check if report file exists."""
        return bool(obj.report_file)
    has_file.boolean = True
    has_file.short_description = "Has File"

    fieldsets = (
        (None, {
            "fields": (
                "report_type",
                "period_start",
                "period_end",
            ),
        }),
        ("Report Data", {
            "fields": (
                "summary_data",
                "detail_data",
            ),
            "classes": ("collapse",),
        }),
        ("Metadata", {
            "fields": (
                "generated_by",
                "generated_date",
                "report_file",
            ),
        }),
    )
