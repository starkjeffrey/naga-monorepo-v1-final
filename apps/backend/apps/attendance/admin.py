"""from datetime import date
Django admin interface for attendance management.

Provides comprehensive admin interfaces for:
- Attendance session management and monitoring
- Student attendance record review and correction
- Permission request approval workflows
- Roster sync monitoring and troubleshooting
- Attendance statistics and reporting
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    AttendanceArchive,
    AttendanceRecord,
    AttendanceSession,
    AttendanceSettings,
    PermissionRequest,
    RosterSync,
)

# Attendance constants
EXCELLENT_ATTENDANCE_THRESHOLD = 80
GOOD_ATTENDANCE_THRESHOLD = 60
LATE_THRESHOLD_MINUTES = 15
MIN_STUDENTS_FOR_STATS = 5


@admin.register(AttendanceSettings)
class AttendanceSettingsAdmin(admin.ModelAdmin):
    """Admin interface for attendance settings and policies."""

    list_display = [
        "program",
        "allows_permission_requests",
        "auto_approve_permissions",
        "attendance_required_percentage",
        "late_threshold_minutes",
        "attendance_affects_grade",
    ]
    list_filter = [
        "allows_permission_requests",
        "auto_approve_permissions",
        "parent_notification_required",
        "attendance_affects_grade",
    ]
    search_fields = ["program__name"]

    fieldsets = (
        ("Program", {"fields": ("program",)}),
        (
            "Permission Policies",
            {
                "fields": (
                    "allows_permission_requests",
                    "auto_approve_permissions",
                    "parent_notification_required",
                ),
            },
        ),
        (
            "Attendance Thresholds",
            {
                "fields": (
                    "attendance_required_percentage",
                    "late_threshold_minutes",
                ),
            },
        ),
        (
            "Code & Geofence Settings",
            {
                "fields": (
                    "default_code_window_minutes",
                    "default_geofence_radius",
                ),
            },
        ),
        (
            "Grade Impact",
            {
                "fields": (
                    "attendance_affects_grade",
                    "attendance_grade_weight",
                ),
            },
        ),
    )


class AttendanceRecordInline(admin.TabularInline):
    """Inline for viewing attendance records within a session."""

    model = AttendanceRecord
    extra = 0
    readonly_fields = [
        "student",
        "status",
        "submitted_at",
        "code_correct",
        "within_geofence",
        "data_source",
    ]
    fields = [
        "student",
        "status",
        "submitted_at",
        "code_correct",
        "within_geofence",
        "data_source",
        "notes",
    ]

    def has_add_permission(self, request, obj):
        return False


@admin.register(AttendanceSession)
class AttendanceSessionAdmin(admin.ModelAdmin):
    """Admin interface for attendance sessions."""

    list_display = [
        "class_part",
        "teacher",
        "session_date",
        "start_time",
        "attendance_code",
        "is_active",
        "attendance_summary",
        "code_status",
    ]
    list_filter = [
        "session_date",
        "is_active",
        "is_makeup_class",
        "teacher",
    ]
    search_fields = [
        "class_part__class_session__class_header__course__code",
        "teacher__person__family_name",
        "attendance_code",
    ]
    readonly_fields = [
        "attendance_code",
        "code_generated_at",
        "total_students",
        "present_count",
        "absent_count",
        "attendance_percentage",
    ]

    fieldsets = (
        (
            "Session Details",
            {
                "fields": (
                    "class_part",
                    "teacher",
                    "session_date",
                    "start_time",
                    "end_time",
                ),
            },
        ),
        (
            "Attendance Code",
            {
                "fields": (
                    "attendance_code",
                    "code_generated_at",
                    "code_expires_at",
                    "code_window_minutes",
                ),
            },
        ),
        (
            "Location & Geofencing",
            {
                "fields": (
                    "latitude",
                    "longitude",
                    "geofence_radius_meters",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Session Configuration",
            {
                "fields": (
                    "is_active",
                    "is_makeup_class",
                    "makeup_reason",
                    "manual_fallback_enabled",
                    "django_fallback_enabled",
                ),
            },
        ),
        (
            "Statistics",
            {
                "fields": (
                    "total_students",
                    "present_count",
                    "absent_count",
                    "attendance_percentage",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    inlines = [AttendanceRecordInline]

    @admin.display(description="Attendance")
    def attendance_summary(self, obj):
        """Display attendance summary for the session."""
        if obj.total_students > 0:
            percentage = obj.attendance_percentage
            color = (
                "green"
                if percentage >= EXCELLENT_ATTENDANCE_THRESHOLD
                else "orange"
                if percentage >= GOOD_ATTENDANCE_THRESHOLD
                else "red"
            )
            return format_html(
                '<span style="color: {};">{}/{} ({:.1f}%)</span>',
                color,
                obj.present_count,
                obj.total_students,
                percentage,
            )
        return "No data"

    @admin.display(description="Code Status")
    def code_status(self, obj):
        """Display code validity status."""
        if obj.is_code_valid:
            return format_html('<span style="color: green;">Active</span>')
        return format_html('<span style="color: red;">Expired</span>')

    actions = ["update_statistics", "deactivate_sessions"]

    @admin.action(description="Update attendance statistics")
    def update_statistics(self, request, queryset):
        """Update attendance statistics for selected sessions."""
        for session in queryset:
            session.update_statistics()
        self.message_user(
            request,
            f"Updated statistics for {queryset.count()} sessions.",
        )

    @admin.action(description="Deactivate sessions")
    def deactivate_sessions(self, request, queryset):
        """Deactivate selected sessions."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"Deactivated {updated} sessions.")


@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    """Admin interface for individual attendance records."""

    list_display = [
        "student",
        "attendance_session",
        "status",
        "data_source",
        "submission_info",
        "location_validation",
    ]
    list_filter = [
        "status",
        "data_source",
        "code_correct",
        "within_geofence",
        "attendance_session__session_date",
    ]
    search_fields = [
        "student__student_id",
        "student__person__family_name",
        "attendance_session__class_part__class_session__class_header__course__code",
    ]
    readonly_fields = [
        "attendance_session",
        "student",
        "submitted_code",
        "code_correct",
        "submitted_at",
        "submitted_latitude",
        "submitted_longitude",
        "within_geofence",
        "distance_from_class",
        "data_source",
        "submission_delay_minutes",
    ]

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "attendance_session",
                    "student",
                    "status",
                ),
            },
        ),
        (
            "Code Submission",
            {
                "fields": (
                    "submitted_code",
                    "code_correct",
                    "submitted_at",
                    "submission_delay_minutes",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Location Validation",
            {
                "fields": (
                    "submitted_latitude",
                    "submitted_longitude",
                    "within_geofence",
                    "distance_from_class",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Data Source & Audit",
            {
                "fields": (
                    "data_source",
                    "recorded_by",
                ),
            },
        ),
        (
            "Permission Details",
            {
                "fields": (
                    "permission_reason",
                    "permission_approved",
                    "permission_approved_by",
                    "permission_notes",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Additional Notes", {"fields": ("notes",)}),
    )

    @admin.display(description="Submitted")
    def submission_info(self, obj):
        """Display code submission information."""
        if obj.submitted_at:
            delay = obj.submission_delay_minutes
            color = (
                "green" if delay <= MIN_STUDENTS_FOR_STATS else "orange" if delay <= LATE_THRESHOLD_MINUTES else "red"
            )
            return format_html(
                '{} <span style="color: {};">(+{} min)</span>',
                obj.submitted_at.strftime("%H:%M"),
                color,
                delay,
            )
        return "No submission"

    @admin.display(description="Location")
    def location_validation(self, obj):
        """Display location validation status."""
        if obj.within_geofence is not None:
            if obj.within_geofence:
                return format_html('<span style="color: green;">✓ Valid</span>')
            distance = obj.distance_from_class or 0
            return format_html(
                '<span style="color: red;">✗ Invalid ({} m)</span>',
                distance,
            )
        return "No location"

    actions = ["mark_as_present", "mark_as_absent", "approve_permissions"]

    @admin.action(description="Mark as Present")
    def mark_as_present(self, request, queryset):
        """Mark selected records as present."""
        updated = queryset.update(
            status=AttendanceRecord.AttendanceStatus.PRESENT,
            data_source=AttendanceRecord.DataSource.DJANGO_MANUAL,
            recorded_by=request.user,
        )
        self.message_user(request, f"Marked {updated} records as present.")

    @admin.action(description="Mark as Absent")
    def mark_as_absent(self, request, queryset):
        """Mark selected records as absent."""
        updated = queryset.update(
            status=AttendanceRecord.AttendanceStatus.ABSENT,
            data_source=AttendanceRecord.DataSource.DJANGO_MANUAL,
            recorded_by=request.user,
        )
        self.message_user(request, f"Marked {updated} records as absent.")

    @admin.action(description="Approve Permissions")
    def approve_permissions(self, request, queryset):
        """Approve permission records."""
        updated = queryset.filter(
            status=AttendanceRecord.AttendanceStatus.PERMISSION,
        ).update(permission_approved=True, permission_approved_by=request.user)
        self.message_user(request, f"Approved {updated} permission records.")


@admin.register(PermissionRequest)
class PermissionRequestAdmin(admin.ModelAdmin):
    """Admin interface for permission requests."""

    list_display = [
        "student",
        "class_part",
        "session_date",
        "program_type",
        "request_status",
        "requires_approval",
        "parent_notified",
    ]
    list_filter = [
        "request_status",
        "program_type",
        "requires_approval",
        "parent_notified",
        "session_date",
    ]
    search_fields = [
        "student__student_id",
        "student__person__family_name",
        "class_part__class_session__class_header__course__code",
    ]
    readonly_fields = [
        "student",
        "class_part",
        "session_date",
        "program_type",
        "requires_approval",
        "created_at",
        "parent_notification_date",
    ]

    fieldsets = (
        (
            "Request Details",
            {
                "fields": (
                    "student",
                    "class_part",
                    "session_date",
                    "reason",
                ),
            },
        ),
        (
            "Program Configuration",
            {
                "fields": (
                    "program_type",
                    "requires_approval",
                ),
            },
        ),
        (
            "Approval Workflow",
            {
                "fields": (
                    "request_status",
                    "approved_by",
                    "approval_date",
                    "approval_notes",
                ),
            },
        ),
        (
            "Parent Notification",
            {
                "fields": (
                    "parent_notified",
                    "parent_notification_date",
                    "parent_response",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    actions = ["approve_requests", "deny_requests", "notify_parents"]

    @admin.action(description="Approve requests")
    def approve_requests(self, request, queryset):
        """Approve selected permission requests."""
        updated = queryset.filter(
            request_status=PermissionRequest.RequestStatus.PENDING,
        ).update(
            request_status=PermissionRequest.RequestStatus.APPROVED,
            approved_by=request.user,
            approval_date=timezone.now(),
        )
        self.message_user(request, f"Approved {updated} permission requests.")

    @admin.action(description="Deny requests")
    def deny_requests(self, request, queryset):
        """Deny selected permission requests."""
        updated = queryset.filter(
            request_status=PermissionRequest.RequestStatus.PENDING,
        ).update(
            request_status=PermissionRequest.RequestStatus.DENIED,
            approved_by=request.user,
            approval_date=timezone.now(),
        )
        self.message_user(request, f"Denied {updated} permission requests.")

    @admin.action(description="Mark parents notified")
    def notify_parents(self, request, queryset):
        """Mark parents as notified for high school requests."""
        updated = queryset.filter(
            program_type=PermissionRequest.ProgramType.HIGH_SCHOOL,
            parent_notified=False,
        ).update(parent_notified=True, parent_notification_date=timezone.now())
        self.message_user(request, f"Marked {updated} parents as notified.")


@admin.register(RosterSync)
class RosterSyncAdmin(admin.ModelAdmin):
    """Admin interface for roster synchronization monitoring."""

    list_display = [
        "class_part",
        "sync_date",
        "sync_type",
        "sync_timestamp",
        "student_count",
        "is_successful",
        "roster_changed",
    ]
    list_filter = [
        "sync_date",
        "sync_type",
        "is_successful",
        "roster_changed",
    ]
    search_fields = [
        "class_part__class_session__class_header__course__code",
    ]
    readonly_fields = [
        "class_part",
        "sync_date",
        "sync_timestamp",
        "student_count",
        "enrollment_snapshot",
        "roster_changed",
        "changes_summary",
    ]

    fieldsets = (
        (
            "Sync Details",
            {
                "fields": (
                    "class_part",
                    "sync_date",
                    "sync_timestamp",
                    "sync_type",
                ),
            },
        ),
        (
            "Sync Results",
            {
                "fields": (
                    "is_successful",
                    "error_message",
                    "student_count",
                ),
            },
        ),
        (
            "Change Tracking",
            {
                "fields": (
                    "roster_changed",
                    "changes_summary",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Enrollment Data",
            {"fields": ("enrollment_snapshot",), "classes": ("collapse",)},
        ),
    )

    def has_add_permission(self, request):
        return False


@admin.register(AttendanceArchive)
class AttendanceArchiveAdmin(admin.ModelAdmin):
    """Admin interface for attendance archives."""

    list_display = [
        "student",
        "class_part",
        "term",
        "attendance_percentage",
        "punctuality_percentage",
        "attendance_grade",
        "archived_on",
    ]
    list_filter = [
        "term",
        "archived_on",
    ]
    search_fields = [
        "student__student_id",
        "student__person__family_name",
        "class_part__class_session__class_header__course__code",
    ]
    readonly_fields = [
        "student",
        "class_part",
        "term",
        "total_sessions",
        "present_sessions",
        "absent_sessions",
        "late_sessions",
        "excused_sessions",
        "attendance_percentage",
        "punctuality_percentage",
        "attendance_grade",
        "archived_on",
        "archived_by",
        "session_details",
    ]

    fieldsets = (
        (
            "Archive Information",
            {
                "fields": (
                    "student",
                    "class_part",
                    "term",
                    "archived_on",
                    "archived_by",
                ),
            },
        ),
        (
            "Attendance Summary",
            {
                "fields": (
                    "total_sessions",
                    "present_sessions",
                    "absent_sessions",
                    "late_sessions",
                    "excused_sessions",
                ),
            },
        ),
        (
            "Calculated Metrics",
            {
                "fields": (
                    "attendance_percentage",
                    "punctuality_percentage",
                    "attendance_grade",
                ),
            },
        ),
        ("Detailed Data", {"fields": ("session_details",), "classes": ("collapse",)}),
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
