"""Attendance app models following clean architecture principles.

This module contains models for mobile-based attendance tracking with:
- Teacher-generated attendance codes with geofencing
- Student code submissions and validation
- Permission requests with program-specific policies
- Daily roster synchronization with enrollment
- Multiple fallback options for reliability

Key architectural decisions:
- Clean dependencies: attendance → scheduling → curriculum + people
- Mobile-first design with Django as data warehouse
- Flexible geofencing and code validation
- Program-specific attendance policies
- Comprehensive audit trail for all attendance data
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import (
    BooleanField,
    CharField,
    Count,
    DateField,
    DateTimeField,
    DecimalField,
    ForeignKey,
    PositiveIntegerField,
    Q,
    TimeField,
)
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import AuditModel

if TYPE_CHECKING:
    from users.models import User

if TYPE_CHECKING:
    from apps.people.models import TeacherProfile


class AttendanceSettings(AuditModel):
    """Program-specific attendance policies and settings.

    Defines attendance rules, thresholds, and policies that vary
    by academic program (IEAP, BA, High School, etc.).
    """

    program: ForeignKey = models.ForeignKey(
        "curriculum.Division",
        on_delete=models.PROTECT,
        related_name="attendance_settings",
        verbose_name=_("Program Division"),
        help_text=_("Academic program this setting applies to"),
    )

    # Permission request policies
    allows_permission_requests: BooleanField = models.BooleanField(
        _("Allows Permission Requests"),
        default=True,
        help_text=_("Whether students can request excused absences (IEAP=False)"),
    )
    auto_approve_permissions: BooleanField = models.BooleanField(
        _("Auto-Approve Permissions"),
        default=False,
        help_text=_("Automatically approve permission requests (High School=True)"),
    )
    parent_notification_required: BooleanField = models.BooleanField(
        _("Parent Notification Required"),
        default=False,
        help_text=_("Send permission requests to parents (High School=True)"),
    )

    # Attendance thresholds and policies
    attendance_required_percentage: DecimalField = models.DecimalField(
        _("Required Attendance Percentage"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("80.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Minimum attendance percentage required"),
    )
    late_threshold_minutes: PositiveIntegerField = models.PositiveIntegerField(
        _("Late Threshold (Minutes)"),
        default=15,
        help_text=_("Minutes after start time when LATE becomes ABSENT"),
    )

    # Code and geofence settings
    default_code_window_minutes: PositiveIntegerField = models.PositiveIntegerField(
        _("Code Window (Minutes)"),
        default=15,
        help_text=_("How long attendance codes remain valid"),
    )
    default_geofence_radius: PositiveIntegerField = models.PositiveIntegerField(
        _("Geofence Radius (Meters)"),
        default=50,
        help_text=_("Default geofence radius for attendance validation"),
    )

    # Grade impact settings
    attendance_affects_grade: BooleanField = models.BooleanField(
        _("Attendance Affects Grade"),
        default=True,
        help_text=_("Whether attendance impacts final grades"),
    )
    attendance_grade_weight: DecimalField = models.DecimalField(
        _("Attendance Grade Weight"),
        max_digits=4,
        decimal_places=3,
        default=Decimal("0.100"),
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text=_("Weight of attendance in final grade calculation"),
    )

    class Meta:
        verbose_name = _("Attendance Settings")
        verbose_name_plural = _("Attendance Settings")
        ordering = ["program__name"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["program"]),
        ]

    def __str__(self) -> str:
        return f"{self.program.name} - Attendance Settings"


class AttendanceSession(AuditModel):
    """Individual class session for attendance tracking.

    Created when teacher starts attendance collection using their mobile app.
    Records the teacher-generated code and session details for validation.
    """

    class_part: ForeignKey = models.ForeignKey(
        "scheduling.ClassPart",
        on_delete=models.CASCADE,
        related_name="attendance_sessions",
        verbose_name=_("Class Part"),
        help_text=_("Which class component this attendance is for"),
    )
    teacher: ForeignKey = models.ForeignKey(
        "people.TeacherProfile",
        on_delete=models.PROTECT,
        related_name="attendance_sessions",
        verbose_name=_("Scheduled Teacher"),
        help_text=_("Originally scheduled teacher for this session"),
    )
    substitute_teacher: ForeignKey = models.ForeignKey(
        "people.TeacherProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="substitute_sessions",
        verbose_name=_("Substitute Teacher"),
        help_text=_(
            "Teacher actually conducting this session (if different from scheduled)",
        ),
    )

    # Session timing
    session_date: DateField = models.DateField(
        _("Session Date"),
        help_text=_("Date when class session occurred"),
    )
    start_time: TimeField = models.TimeField(
        _("Actual Start Time"),
        help_text=_("When teacher actually started class"),
    )
    end_time: TimeField = models.TimeField(
        _("Actual End Time"),
        null=True,
        blank=True,
        help_text=_("When teacher ended class (optional)"),
    )

    # Teacher-generated attendance code
    attendance_code: CharField = models.CharField(
        _("Attendance Code"),
        max_length=5,
        help_text=_("5-digit code generated by teacher's mobile app"),
    )
    code_generated_at: DateTimeField = models.DateTimeField(
        _("Code Generated At"),
        help_text=_("When teacher generated the attendance code"),
    )
    code_expires_at: DateTimeField = models.DateTimeField(
        _("Code Expires At"),
        help_text=_("When attendance code window closes"),
    )
    code_window_minutes: PositiveIntegerField = models.PositiveIntegerField(
        _("Code Window (Minutes)"),
        default=15,
        help_text=_("How long code remains valid for submissions"),
    )

    # Geofencing (teacher's location when starting session)
    latitude: models.DecimalField = models.DecimalField(
        _("Latitude"),
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text=_("Teacher's latitude when starting session"),
    )
    longitude: models.DecimalField = models.DecimalField(
        _("Longitude"),
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text=_("Teacher's longitude when starting session"),
    )
    geofence_radius_meters: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Geofence Radius (Meters)"),
        default=50,
        help_text=_("Radius for location validation"),
    )

    # Session configuration
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether attendance collection is currently active"),
    )
    is_makeup_class: models.BooleanField = models.BooleanField(
        _("Is Makeup Class"),
        default=False,
        help_text=_("Whether this is a makeup session"),
    )
    makeup_reason: models.TextField = models.TextField(
        _("Makeup Reason"),
        blank=True,
        help_text=_("Reason for makeup class (if applicable)"),
    )

    # Substitute teacher tracking
    is_substitute_session: models.BooleanField = models.BooleanField(
        _("Is Substitute Session"),
        default=False,
        db_index=True,
        help_text=_("Whether this session is being taught by a substitute teacher"),
    )
    substitute_reason: models.TextField = models.TextField(
        _("Substitute Reason"),
        blank=True,
        help_text=_("Reason for substitute teacher (sick leave, emergency, etc.)"),
    )
    substitute_assigned_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_substitute_sessions",
        verbose_name=_("Substitute Assigned By"),
        help_text=_("User who assigned the substitute teacher"),
    )
    substitute_assigned_at: models.DateTimeField = models.DateTimeField(
        _("Substitute Assigned At"),
        null=True,
        blank=True,
        help_text=_("When the substitute teacher was assigned"),
    )

    # Backup and failsafe options
    manual_fallback_enabled: models.BooleanField = models.BooleanField(
        _("Manual Fallback Enabled"),
        default=True,
        help_text=_("Allow teacher manual entry if mobile fails"),
    )
    django_fallback_enabled: models.BooleanField = models.BooleanField(
        _("Django Fallback Enabled"),
        default=True,
        help_text=_("Allow Django admin entry if all else fails"),
    )

    # Session statistics
    total_students: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Total Students"),
        default=0,
        help_text=_("Total students enrolled in this class"),
    )
    present_count: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Present Count"),
        default=0,
        help_text=_("Number of students marked present"),
    )
    absent_count: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Absent Count"),
        default=0,
        help_text=_("Number of students marked absent"),
    )

    class Meta:
        verbose_name = _("Attendance Session")
        verbose_name_plural = _("Attendance Sessions")
        ordering = ["-session_date", "-start_time"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["class_part", "session_date"]),
            models.Index(fields=["teacher", "session_date"]),
            models.Index(fields=["substitute_teacher", "session_date"]),
            models.Index(fields=["session_date", "is_active"]),
            models.Index(fields=["attendance_code", "is_active"]),
            models.Index(fields=["is_substitute_session", "session_date"]),
        ]

    def __str__(self) -> str:
        teacher_name = self.actual_teacher.person.full_name if self.actual_teacher else "No Teacher"
        substitute_indicator = " (SUB)" if self.is_substitute_session else ""
        return f"{self.class_part} - {self.session_date} - {teacher_name}{substitute_indicator}"

    @property
    def actual_teacher(self) -> "TeacherProfile":
        """Return the teacher actually conducting this session.

        Returns substitute teacher if assigned, otherwise returns scheduled teacher.
        This is the teacher who should have mobile app permissions for this session.
        """
        return self.substitute_teacher if self.substitute_teacher else self.teacher

    @property
    def is_code_valid(self) -> bool:
        """Check if attendance code is still within valid time window."""
        return timezone.now() <= self.code_expires_at and self.is_active

    @property
    def attendance_percentage(self) -> float:
        """Calculate attendance percentage for this session."""
        if self.total_students == 0:
            return 0.0
        return (self.present_count / self.total_students) * 100

    def update_statistics(self) -> None:
        """Update session statistics using an efficient, single database query."""
        stats = self.attendance_records.aggregate(
            total_students=Count("id"),
            present_count=Count(
                "id",
                filter=Q(
                    status__in=[
                        AttendanceRecord.AttendanceStatus.PRESENT,
                        AttendanceRecord.AttendanceStatus.PERMISSION,
                    ]
                ),
            ),
            absent_count=Count(
                "id",
                filter=Q(
                    status__in=[
                        AttendanceRecord.AttendanceStatus.ABSENT,
                        AttendanceRecord.AttendanceStatus.LATE,
                    ]
                ),
            ),
        )

        self.total_students = stats.get("total_students", 0)
        self.present_count = stats.get("present_count", 0)
        self.absent_count = stats.get("absent_count", 0)

        self.save(update_fields=["total_students", "present_count", "absent_count"])

    def assign_substitute(
        self,
        substitute_teacher: "TeacherProfile",
        reason: str,
        assigned_by: "User",
    ) -> None:
        """Assign a substitute teacher to this session.

        Args:
            substitute_teacher: The teacher who will substitute
            reason: Reason for the substitution
            assigned_by: User assigning the substitute
        """
        self.substitute_teacher = substitute_teacher
        self.substitute_reason = reason
        self.substitute_assigned_by = assigned_by
        self.substitute_assigned_at = timezone.now()
        self.is_substitute_session = True

        self.save(
            update_fields=[
                "substitute_teacher",
                "substitute_reason",
                "substitute_assigned_by",
                "substitute_assigned_at",
                "is_substitute_session",
            ],
        )

    def remove_substitute(self) -> None:
        """Remove substitute teacher assignment (return to regular teacher)."""
        self.substitute_teacher = None
        self.substitute_reason = ""
        self.substitute_assigned_by = None
        self.substitute_assigned_at = None
        self.is_substitute_session = False

        self.save(
            update_fields=[
                "substitute_teacher",
                "substitute_reason",
                "substitute_assigned_by",
                "substitute_assigned_at",
                "is_substitute_session",
            ],
        )

    def clean(self) -> None:
        """Validate attendance session data."""
        super().clean()

        if self.substitute_teacher:
            if not self.substitute_reason:
                raise ValidationError(
                    {
                        "substitute_reason": _(
                            "Substitute reason is required when substitute teacher is assigned.",
                        ),
                    },
                )
            self.is_substitute_session = True

        if self.is_substitute_session and not self.substitute_teacher:
            raise ValidationError(
                {
                    "substitute_teacher": _(
                        "Substitute teacher is required when marked as substitute session.",
                    ),
                },
            )

        # Substitute teacher cannot be the same as regular teacher
        if self.substitute_teacher and self.substitute_teacher == self.teacher:
            raise ValidationError(
                {
                    "substitute_teacher": _(
                        "Substitute teacher cannot be the same as the regular teacher.",
                    ),
                },
            )


class AttendanceRecord(AuditModel):
    """Individual student attendance record for a session.

    Tracks each student's attendance status with detailed validation
    information about code submission and geolocation.
    """

    class AttendanceStatus(models.TextChoices):
        """Valid attendance statuses."""

        PRESENT = "PRESENT", _("Present")
        ABSENT = "ABSENT", _("Absent")
        LATE = "LATE", _("Late")
        PERMISSION = "PERMISSION", _("Permission (Excused)")

    class DataSource(models.TextChoices):
        """How attendance was recorded."""

        MOBILE_CODE = "MOBILE_CODE", _("Mobile App Code Entry")
        MOBILE_MANUAL = "MOBILE_MANUAL", _("Teacher Manual Entry")
        DJANGO_MANUAL = "DJANGO_MANUAL", _("Django Admin Entry")
        AUTO_ABSENT = "AUTO_ABSENT", _("Automatically Marked Absent")
        PERMISSION_REQUEST = "PERMISSION_REQUEST", _("Permission Request System")

    attendance_session: models.ForeignKey = models.ForeignKey(
        AttendanceSession,
        on_delete=models.CASCADE,
        related_name="attendance_records",
        verbose_name=_("Attendance Session"),
    )
    student: models.ForeignKey = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.PROTECT,
        related_name="attendance_records",
        verbose_name=_("Student"),
    )
    status: models.CharField = models.CharField(
        _("Attendance Status"),
        max_length=15,
        choices=AttendanceStatus.choices,
        default=AttendanceStatus.ABSENT,
    )

    # Code submission tracking
    submitted_code: models.CharField = models.CharField(
        _("Submitted Code"),
        max_length=5,
        blank=True,
        help_text=_("Code entered by student"),
    )
    code_correct: models.BooleanField = models.BooleanField(
        _("Code Correct"),
        null=True,
        help_text=_("Whether submitted code matched session code"),
    )
    submitted_at: models.DateTimeField = models.DateTimeField(
        _("Submitted At"),
        null=True,
        blank=True,
        help_text=_("When student submitted attendance code"),
    )

    # Geolocation validation
    submitted_latitude: models.DecimalField = models.DecimalField(
        _("Submitted Latitude"),
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text=_("Student's latitude when submitting code"),
    )
    submitted_longitude: models.DecimalField = models.DecimalField(
        _("Submitted Longitude"),
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
        help_text=_("Student's longitude when submitting code"),
    )
    within_geofence: models.BooleanField = models.BooleanField(
        _("Within Geofence"),
        null=True,
        help_text=_("Whether student was within valid location"),
    )
    distance_from_class: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Distance from Class (Meters)"),
        null=True,
        blank=True,
        help_text=_("Student's distance from class location"),
    )

    # Data source and audit trail
    data_source: models.CharField = models.CharField(
        _("Data Source"),
        max_length=20,
        choices=DataSource.choices,
        default=DataSource.AUTO_ABSENT,
    )
    recorded_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="recorded_attendance",
        verbose_name=_("Recorded By"),
        help_text=_("User who recorded this attendance"),
    )

    # Permission/excuse handling
    permission_reason: models.TextField = models.TextField(
        _("Permission Reason"),
        blank=True,
        help_text=_("Reason for excused absence"),
    )
    permission_approved: models.BooleanField = models.BooleanField(
        _("Permission Approved"),
        null=True,
        help_text=_("Whether permission request was approved"),
    )
    permission_approved_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_permissions",
        verbose_name=_("Permission Approved By"),
    )
    permission_notes: models.TextField = models.TextField(
        _("Permission Notes"),
        blank=True,
        help_text=_("Admin notes about permission request"),
    )

    # Additional tracking
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this attendance record"),
    )

    class Meta:
        verbose_name = _("Attendance Record")
        verbose_name_plural = _("Attendance Records")
        unique_together = [["attendance_session", "student"]]
        ordering = ["attendance_session", "student__student_id"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["attendance_session", "status"]),
            models.Index(fields=["student", "attendance_session"]),
            models.Index(fields=["status", "attendance_session"]),
            models.Index(fields=["data_source"]),
        ]

    def __str__(self) -> str:
        return f"{self.student} - {self.attendance_session.session_date} ({self.status})"

    @property
    def is_present(self) -> bool:
        """Check if student was present (including excused)."""
        return self.status in [
            self.AttendanceStatus.PRESENT,
            self.AttendanceStatus.PERMISSION,
        ]

    @property
    def submission_delay_minutes(self) -> int:
        """Calculate how many minutes after class start the code was submitted."""
        if not self.submitted_at:
            return 0

        session = self.attendance_session
        class_start = datetime.combine(
            session.session_date,
            session.start_time,
        )
        class_start = timezone.make_aware(class_start)

        delay = (self.submitted_at - class_start).total_seconds() / 60
        return max(0, int(delay))


class PermissionRequest(AuditModel):
    """Student requests for excused absences (PERMISSION status).

    Handles permission requests with program-specific policies:
    - IEAP: No permission requests allowed
    - High School: Auto-approved, parents notified
    - BA: Teacher/admin approval required
    """

    class RequestStatus(models.TextChoices):
        """Permission request statuses."""

        PENDING = "PENDING", _("Pending Approval")
        APPROVED = "APPROVED", _("Approved")
        DENIED = "DENIED", _("Denied")
        AUTO_APPROVED = "AUTO_APPROVED", _("Auto-Approved (High School)")
        EXPIRED = "EXPIRED", _("Expired (Not Processed)")

    class ProgramType(models.TextChoices):
        """Program types with different permission policies."""

        IEAP = "IEAP", _("IEAP (No Permissions)")
        HIGH_SCHOOL = "HIGH_SCHOOL", _("High School (Auto-Approve)")
        BA = "BA", _("Bachelor's (Requires Approval)")
        MA = "MA", _("Master's (Requires Approval)")
        OTHER = "OTHER", _("Other Program")

    student: models.ForeignKey = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.PROTECT,
        related_name="permission_requests",
        verbose_name=_("Student"),
    )
    class_part: models.ForeignKey = models.ForeignKey(
        "scheduling.ClassPart",
        on_delete=models.CASCADE,
        related_name="permission_requests",
        verbose_name=_("Class Part"),
    )
    session_date: models.DateField = models.DateField(
        _("Session Date"),
        help_text=_("Date of class student wants to miss"),
    )

    # Request details
    reason: models.TextField = models.TextField(
        _("Reason"),
        help_text=_("Student's reason for requesting excused absence"),
    )
    request_status: models.CharField = models.CharField(
        _("Request Status"),
        max_length=15,
        choices=RequestStatus.choices,
        default=RequestStatus.PENDING,
    )

    # Program-specific handling
    program_type: models.CharField = models.CharField(
        _("Program Type"),
        max_length=15,
        choices=ProgramType.choices,
        help_text=_("Program type determines approval workflow"),
    )
    requires_approval: models.BooleanField = models.BooleanField(
        _("Requires Approval"),
        default=True,
        help_text=_("Whether request needs manual approval"),
    )

    # Approval workflow
    approved_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_permission_requests",
        verbose_name=_("Approved By"),
    )
    approval_date: models.DateTimeField = models.DateTimeField(
        _("Approval Date"),
        null=True,
        blank=True,
    )
    approval_notes: models.TextField = models.TextField(
        _("Approval Notes"),
        blank=True,
        help_text=_("Admin notes about approval decision"),
    )

    # Parent notification (High School)
    parent_notified: models.BooleanField = models.BooleanField(
        _("Parent Notified"),
        default=False,
        help_text=_("Whether parents have been notified"),
    )
    parent_notification_date: models.DateTimeField = models.DateTimeField(
        _("Parent Notification Date"),
        null=True,
        blank=True,
    )
    parent_response: models.TextField = models.TextField(
        _("Parent Response"),
        blank=True,
        help_text=_("Parent's response to notification"),
    )

    class Meta:
        verbose_name = _("Permission Request")
        verbose_name_plural = _("Permission Requests")
        unique_together = [["student", "class_part", "session_date"]]
        ordering = ["-session_date", "request_status"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "session_date"]),
            models.Index(fields=["class_part", "session_date"]),
            models.Index(fields=["request_status", "session_date"]),
            models.Index(fields=["program_type", "request_status"]),
        ]

    def __str__(self) -> str:
        return f"{self.student} - {self.class_part} ({self.session_date})"

    def clean(self) -> None:
        """Validate permission request rules."""
        super().clean()

        # IEAP programs don't allow permission requests
        if self.program_type == self.ProgramType.IEAP:
            raise ValidationError(
                {"program_type": _("IEAP program does not allow permission requests.")},
            )

        # Can't request permission for past dates
        if self.session_date < timezone.now().date():
            raise ValidationError(
                {"session_date": _("Cannot request permission for past dates.")},
            )


class RosterSync(AuditModel):
    """Daily roster synchronization with enrollment data.

    Syncs class rosters twice daily (midnight and noon) to ensure
    teacher mobile apps have current enrollment information.
    """

    class SyncType(models.TextChoices):
        """Times when roster sync occurs."""

        MIDNIGHT = "MIDNIGHT", _("Midnight Sync")
        NOON = "NOON", _("Noon Sync")
        MANUAL = "MANUAL", _("Manual Sync")

    class_part: models.ForeignKey = models.ForeignKey(
        "scheduling.ClassPart",
        on_delete=models.CASCADE,
        related_name="roster_syncs",
        verbose_name=_("Class Part"),
    )
    sync_date: models.DateField = models.DateField(
        _("Sync Date"),
        help_text=_("Date this roster sync applies to"),
    )
    sync_timestamp: models.DateTimeField = models.DateTimeField(
        _("Sync Timestamp"),
        auto_now_add=True,
        help_text=_("When sync was performed"),
    )

    # Sync configuration
    sync_type: models.CharField = models.CharField(
        _("Sync Type"),
        max_length=10,
        choices=SyncType.choices,
        default=SyncType.MIDNIGHT,
    )
    is_successful: models.BooleanField = models.BooleanField(
        _("Is Successful"),
        default=True,
        help_text=_("Whether sync completed successfully"),
    )
    error_message: models.TextField = models.TextField(
        _("Error Message"),
        blank=True,
        help_text=_("Error details if sync failed"),
    )

    # Roster data
    student_count: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Student Count"),
        help_text=_("Number of students in roster"),
    )
    enrollment_snapshot: models.JSONField = models.JSONField(
        _("Enrollment Snapshot"),
        default=dict,
        help_text=_("Frozen enrollment data for this date"),
    )

    # Change tracking
    roster_changed: models.BooleanField = models.BooleanField(
        _("Roster Changed"),
        default=False,
        help_text=_("Whether roster changed since last sync"),
    )
    changes_summary: models.TextField = models.TextField(
        _("Changes Summary"),
        blank=True,
        help_text=_("Summary of enrollment changes"),
    )

    class Meta:
        verbose_name = _("Roster Sync")
        verbose_name_plural = _("Roster Syncs")
        unique_together = [["class_part", "sync_date", "sync_type"]]
        ordering = ["-sync_date", "-sync_timestamp"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["class_part", "sync_date"]),
            models.Index(fields=["sync_date", "sync_type"]),
            models.Index(fields=["is_successful", "sync_timestamp"]),
        ]

    def __str__(self) -> str:
        return f"{self.class_part} - {self.sync_date} ({self.sync_type})"


class AttendanceArchive(AuditModel):
    """Archived attendance data for completed terms.

    Stores compressed attendance statistics and summaries
    for historical reporting and transcript generation.
    """

    class_part: models.ForeignKey = models.ForeignKey(
        "scheduling.ClassPart",
        on_delete=models.CASCADE,
        related_name="attendance_archives",
        verbose_name=_("Class Part"),
    )
    student: models.ForeignKey = models.ForeignKey(
        "people.StudentProfile",
        on_delete=models.PROTECT,
        related_name="attendance_archives",
        verbose_name=_("Student"),
    )
    term: models.ForeignKey = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.CASCADE,
        related_name="attendance_archives",
        verbose_name=_("Term"),
    )

    # Attendance summary statistics
    total_sessions: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Total Sessions"),
        help_text=_("Total number of class sessions"),
    )
    present_sessions: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Present Sessions"),
        help_text=_("Number of sessions student was present"),
    )
    absent_sessions: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Absent Sessions"),
        help_text=_("Number of sessions student was absent"),
    )
    late_sessions: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Late Sessions"),
        help_text=_("Number of sessions student was late"),
    )
    excused_sessions: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Excused Sessions"),
        help_text=_("Number of sessions with approved permissions"),
    )

    # Calculated percentages
    attendance_percentage: models.DecimalField = models.DecimalField(
        _("Attendance Percentage"),
        max_digits=5,
        decimal_places=2,
        help_text=_("Overall attendance percentage"),
    )
    punctuality_percentage: models.DecimalField = models.DecimalField(
        _("Punctuality Percentage"),
        max_digits=5,
        decimal_places=2,
        help_text=_("Percentage of on-time arrivals"),
    )

    # Archive metadata
    archived_on: models.DateTimeField = models.DateTimeField(
        _("Archived On"),
        auto_now_add=True,
    )
    archived_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="archived_attendance",
        verbose_name=_("Archived By"),
    )

    # Detailed data (compressed)
    session_details: models.JSONField = models.JSONField(
        _("Session Details"),
        default=dict,
        help_text=_("Compressed attendance details for all sessions"),
    )

    class Meta:
        verbose_name = _("Attendance Archive")
        verbose_name_plural = _("Attendance Archives")
        unique_together = [["class_part", "student", "term"]]
        ordering = ["-archived_on"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["student", "term"]),
            models.Index(fields=["class_part", "term"]),
            models.Index(fields=["attendance_percentage"]),
        ]

    def __str__(self) -> str:
        return f"{self.student} - {self.class_part} ({self.term})"

    @property
    def attendance_grade(self) -> str:
        """Convert attendance percentage to letter grade."""
        # Grade scale mapping (threshold: grade)
        grade_scale = [
            (95, "A"),
            (90, "A-"),
            (85, "B+"),
            (80, "B"),
            (75, "B-"),
            (70, "C+"),
            (65, "C"),
            (60, "C-"),
        ]

        percentage = float(self.attendance_percentage)
        for threshold, grade in grade_scale:
            if percentage >= threshold:
                return grade
        return "F"
