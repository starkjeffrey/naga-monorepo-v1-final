"""Leave Management app models for teacher absence and substitute management.

This module contains models for:
- Teacher leave requests (sick leave, personal leave, etc.)
- Leave policies and balances per contract type
- Substitute teacher assignments
- Temporary attendance permission transfers
- Leave approval workflows
- Management reporting on teacher absences

Key architectural decisions:
- Clean separation from student attendance (different bounded context)
- Integration points via service layer for permission transfers
- Support for different leave policies by contract type
- Comprehensive audit trail for HR compliance
- Mobile-first design for teacher leave submissions
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, ClassVar, Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.common.models import AuditModel

if TYPE_CHECKING:
    from apps.people.models import TeacherProfile
    from apps.scheduling.models import ClassPart


class LeaveType(AuditModel):
    """Types of leave available to teachers."""

    class Category(models.TextChoices):
        """Categories of leave."""
        SICK = "SICK", _("Sick Leave")
        PERSONAL = "PERSONAL", _("Personal Leave")
        VACATION = "VACATION", _("Vacation/Holiday")
        MATERNITY = "MATERNITY", _("Maternity Leave")
        PATERNITY = "PATERNITY", _("Paternity Leave")
        BEREAVEMENT = "BEREAVEMENT", _("Bereavement Leave")
        PROFESSIONAL = "PROFESSIONAL", _("Professional Development")
        UNPAID = "UNPAID", _("Unpaid Leave")
        OTHER = "OTHER", _("Other")

    name = models.CharField(
        _("Leave Type Name"),
        max_length=100,
        unique=True,
        help_text=_("Display name for this leave type"),
    )
    code = models.CharField(
        _("Leave Code"),
        max_length=20,
        unique=True,
        help_text=_("Short code for reports (e.g., 'SICK', 'VAC')"),
    )
    category = models.CharField(
        _("Category"),
        max_length=20,
        choices=Category.choices,
        help_text=_("Category of leave for policy application"),
    )
    requires_documentation = models.BooleanField(
        _("Requires Documentation"),
        default=False,
        help_text=_("Whether supporting documents are required"),
    )
    max_consecutive_days = models.PositiveIntegerField(
        _("Max Consecutive Days"),
        null=True,
        blank=True,
        help_text=_("Maximum consecutive days allowed (null = unlimited)"),
    )
    advance_notice_days = models.PositiveIntegerField(
        _("Advance Notice Required (Days)"),
        default=0,
        help_text=_("Days of advance notice required (0 for emergency leave)"),
    )
    is_active = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this leave type is currently available"),
    )

    class Meta:
        verbose_name = _("Leave Type")
        verbose_name_plural = _("Leave Types")
        ordering = ["category", "name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.code})"


class LeavePolicy(AuditModel):
    """Leave policies by contract type and employment terms."""

    contract_type = models.CharField(
        _("Contract Type"),
        max_length=50,
        help_text=_("Type of teacher contract (e.g., 'FULL_TIME', 'PART_TIME', 'CONTRACT')"),
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="policies",
        verbose_name=_("Leave Type"),
    )
    annual_days = models.DecimalField(
        _("Annual Days Allowed"),
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Number of days allowed per year"),
    )
    accrual_rate = models.DecimalField(
        _("Monthly Accrual Rate"),
        max_digits=5,
        decimal_places=3,
        default=Decimal("0"),
        validators=[MinValueValidator(0)],
        help_text=_("Days accrued per month (0 if granted annually)"),
    )
    carries_forward = models.BooleanField(
        _("Carries Forward"),
        default=False,
        help_text=_("Whether unused leave carries to next year"),
    )
    max_carryover = models.DecimalField(
        _("Max Carryover Days"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Maximum days that can carry forward"),
    )
    effective_date = models.DateField(
        _("Effective Date"),
        help_text=_("When this policy becomes effective"),
    )
    end_date = models.DateField(
        _("End Date"),
        null=True,
        blank=True,
        help_text=_("When this policy ends (null = current)"),
    )

    class Meta:
        verbose_name = _("Leave Policy")
        verbose_name_plural = _("Leave Policies")
        unique_together = [["contract_type", "leave_type", "effective_date"]]
        ordering = ["contract_type", "leave_type", "-effective_date"]

    def __str__(self) -> str:
        return f"{self.contract_type} - {self.leave_type.name}: {self.annual_days} days/year"

    def clean(self) -> None:
        """Validate policy dates don't overlap."""
        super().clean()
        if self.end_date and self.end_date <= self.effective_date:
            raise ValidationError(
                {"end_date": _("End date must be after effective date.")}
            )


class LeaveBalance(AuditModel):
    """Track leave balances for each teacher."""

    teacher = models.ForeignKey(
        "people.TeacherProfile",
        on_delete=models.CASCADE,
        related_name="leave_mgmt_balances",
        verbose_name=_("Teacher"),
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="balances",
        verbose_name=_("Leave Type"),
    )
    year = models.PositiveIntegerField(
        _("Year"),
        help_text=_("Calendar year for this balance"),
    )

    # Balance tracking
    entitled_days = models.DecimalField(
        _("Entitled Days"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Total days entitled for the year"),
    )
    used_days = models.DecimalField(
        _("Used Days"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Days used so far"),
    )
    pending_days = models.DecimalField(
        _("Pending Days"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Days in pending requests"),
    )
    carried_forward = models.DecimalField(
        _("Carried Forward"),
        max_digits=5,
        decimal_places=2,
        default=Decimal("0"),
        help_text=_("Days carried from previous year"),
    )

    class Meta:
        verbose_name = _("Leave Balance")
        verbose_name_plural = _("Leave Balances")
        unique_together = [["teacher", "leave_type", "year"]]
        ordering = ["teacher", "year", "leave_type"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["teacher", "year"]),
            models.Index(fields=["leave_type", "year"]),
        ]

    def __str__(self) -> str:
        return f"{self.teacher} - {self.leave_type.name} ({self.year}): {self.available_days} days available"

    @property
    def available_days(self) -> Decimal:
        """Calculate available days."""
        return self.entitled_days + self.carried_forward - self.used_days - self.pending_days

    def can_request_days(self, days: Decimal) -> bool:
        """Check if teacher has enough balance for requested days."""
        return self.available_days >= days


class LeaveRequest(AuditModel):
    """Teacher leave requests with approval workflow."""

    class Status(models.TextChoices):
        """Leave request statuses."""
        DRAFT = "DRAFT", _("Draft")
        PENDING = "PENDING", _("Pending Approval")
        APPROVED = "APPROVED", _("Approved")
        REJECTED = "REJECTED", _("Rejected")
        CANCELLED = "CANCELLED", _("Cancelled")
        SUBSTITUTE_PENDING = "SUB_PENDING", _("Awaiting Substitute")
        SUBSTITUTE_ASSIGNED = "SUB_ASSIGNED", _("Substitute Assigned")
        COMPLETED = "COMPLETED", _("Completed")

    class Priority(models.TextChoices):
        """Request priority levels."""
        LOW = "LOW", _("Low")
        NORMAL = "NORMAL", _("Normal")
        HIGH = "HIGH", _("High")
        EMERGENCY = "EMERGENCY", _("Emergency")

    # Request details
    teacher = models.ForeignKey(
        "people.TeacherProfile",
        on_delete=models.PROTECT,
        related_name="leave_mgmt_requests",
        verbose_name=_("Teacher"),
    )
    leave_type = models.ForeignKey(
        LeaveType,
        on_delete=models.PROTECT,
        related_name="requests",
        verbose_name=_("Leave Type"),
    )
    start_date = models.DateField(
        _("Start Date"),
        help_text=_("First day of leave"),
    )
    end_date = models.DateField(
        _("End Date"),
        help_text=_("Last day of leave"),
    )

    # Leave details
    reason = models.TextField(
        _("Reason"),
        help_text=_("Detailed reason for leave request"),
    )
    priority = models.CharField(
        _("Priority"),
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    status = models.CharField(
        _("Status"),
        max_length=15,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    # Documentation
    supporting_documents = models.TextField(
        _("Supporting Documents"),
        blank=True,
        help_text=_("JSON array of document URLs/paths"),
    )

    # Approval workflow
    submitted_date = models.DateTimeField(
        _("Submitted Date"),
        null=True,
        blank=True,
        help_text=_("When request was submitted for approval"),
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_leave_requests",
        verbose_name=_("Reviewed By"),
    )
    review_date = models.DateTimeField(
        _("Review Date"),
        null=True,
        blank=True,
    )
    review_notes = models.TextField(
        _("Review Notes"),
        blank=True,
        help_text=_("Notes from reviewer/approver"),
    )

    # Substitute management
    requires_substitute = models.BooleanField(
        _("Requires Substitute"),
        default=True,
        help_text=_("Whether a substitute teacher is needed"),
    )
    substitute_notes = models.TextField(
        _("Substitute Notes"),
        blank=True,
        help_text=_("Special instructions for substitute"),
    )

    class Meta:
        verbose_name = _("Leave Request")
        verbose_name_plural = _("Leave Requests")
        ordering = ["-start_date", "-created_at"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["teacher", "-start_date"]),
            models.Index(fields=["status", "start_date"]),
            models.Index(fields=["priority", "status"]),
            models.Index(fields=["requires_substitute", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.teacher} - {self.leave_type.name} ({self.start_date} to {self.end_date})"

    @property
    def total_days(self) -> int:
        """Calculate total leave days requested."""
        return (self.end_date - self.start_date).days + 1

    @property
    def is_emergency(self) -> bool:
        """Check if this is an emergency request (submitted late)."""
        if not self.submitted_date:
            return False
        days_notice = (self.start_date - self.submitted_date.date()).days
        return days_notice < self.leave_type.advance_notice_days

    def clean(self) -> None:
        """Validate leave request."""
        super().clean()

        # Validate dates
        if self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": _("End date must be after or equal to start date.")}
            )

        # Check for past dates when creating new request
        if not self.pk and self.start_date < date.today():
            raise ValidationError(
                {"start_date": _("Cannot request leave for past dates.")}
            )

        # Validate against max consecutive days
        if self.leave_type.max_consecutive_days:
            if self.total_days > self.leave_type.max_consecutive_days:
                raise ValidationError(
                    {"end_date": _(
                        f"Leave type {self.leave_type.name} allows maximum "
                        f"{self.leave_type.max_consecutive_days} consecutive days."
                    )}
                )

    def approve(self, user, notes: str = "") -> None:
        """Approve the leave request."""
        with transaction.atomic():
            self.status = self.Status.APPROVED
            self.reviewed_by = user
            self.review_date = timezone.now()
            self.review_notes = notes

            if self.requires_substitute:
                self.status = self.Status.SUBSTITUTE_PENDING

            # Update leave balance
            balance = LeaveBalance.objects.get_or_create(
                teacher=self.teacher,
                leave_type=self.leave_type,
                year=self.start_date.year,
                defaults={"entitled_days": Decimal("0")}
            )[0]
            balance.pending_days -= Decimal(str(self.total_days))
            balance.used_days += Decimal(str(self.total_days))
            balance.save()

            self.save()

    def reject(self, user, notes: str) -> None:
        """Reject the leave request."""
        with transaction.atomic():
            self.status = self.Status.REJECTED
            self.reviewed_by = user
            self.review_date = timezone.now()
            self.review_notes = notes

            # Release pending balance
            balance = LeaveBalance.objects.filter(
                teacher=self.teacher,
                leave_type=self.leave_type,
                year=self.start_date.year
            ).first()
            if balance:
                balance.pending_days -= Decimal(str(self.total_days))
                balance.save()

            self.save()


class SubstituteAssignment(AuditModel):
    """Assignment of substitute teachers to cover leave."""

    class Status(models.TextChoices):
        """Assignment statuses."""
        PENDING = "PENDING", _("Pending Confirmation")
        CONFIRMED = "CONFIRMED", _("Confirmed")
        DECLINED = "DECLINED", _("Declined by Substitute")
        COMPLETED = "COMPLETED", _("Completed")
        CANCELLED = "CANCELLED", _("Cancelled")

    leave_request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name="substitute_assignments",
        verbose_name=_("Leave Request"),
    )
    substitute_teacher = models.ForeignKey(
        "people.TeacherProfile",
        on_delete=models.PROTECT,
        related_name="leave_mgmt_substitute_assignments",
        verbose_name=_("Substitute Teacher"),
    )
    status = models.CharField(
        _("Status"),
        max_length=15,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # Assignment details
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="assigned_substitutes",
        verbose_name=_("Assigned By"),
    )
    assignment_date = models.DateTimeField(
        _("Assignment Date"),
        default=timezone.now,
    )

    # Classes to cover
    classes_to_cover = models.ManyToManyField(
        "scheduling.ClassPart",
        related_name="substitute_assignments",
        verbose_name=_("Classes to Cover"),
        blank=True,
    )

    # Communication
    notification_sent = models.BooleanField(
        _("Notification Sent"),
        default=False,
        help_text=_("Whether substitute has been notified"),
    )
    notification_date = models.DateTimeField(
        _("Notification Date"),
        null=True,
        blank=True,
    )
    substitute_notes = models.TextField(
        _("Notes for Substitute"),
        blank=True,
        help_text=_("Instructions and information for substitute"),
    )

    # Confirmation
    confirmed_date = models.DateTimeField(
        _("Confirmed Date"),
        null=True,
        blank=True,
        help_text=_("When substitute confirmed assignment"),
    )
    declined_date = models.DateTimeField(
        _("Declined Date"),
        null=True,
        blank=True,
    )
    decline_reason = models.TextField(
        _("Decline Reason"),
        blank=True,
    )

    # Attendance permissions
    permissions_granted = models.BooleanField(
        _("Permissions Granted"),
        default=False,
        help_text=_("Whether attendance permissions have been granted"),
    )
    permissions_granted_date = models.DateTimeField(
        _("Permissions Granted Date"),
        null=True,
        blank=True,
    )
    permissions_revoked_date = models.DateTimeField(
        _("Permissions Revoked Date"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Substitute Assignment")
        verbose_name_plural = _("Substitute Assignments")
        ordering = ["-assignment_date"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["leave_request", "status"]),
            models.Index(fields=["substitute_teacher", "status"]),
            models.Index(fields=["status", "assignment_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.substitute_teacher} covering for {self.leave_request.teacher} ({self.leave_request.start_date})"

    def confirm(self) -> None:
        """Confirm the substitute assignment."""
        self.status = self.Status.CONFIRMED
        self.confirmed_date = timezone.now()

        # Update leave request status
        self.leave_request.status = LeaveRequest.Status.SUBSTITUTE_ASSIGNED
        self.leave_request.save()

        self.save()

        # This would trigger permission grant via service layer
        from apps.leave_management.services import grant_substitute_permissions
        grant_substitute_permissions(self)

    def decline(self, reason: str) -> None:
        """Decline the substitute assignment."""
        self.status = self.Status.DECLINED
        self.declined_date = timezone.now()
        self.decline_reason = reason

        # Revert leave request to needing substitute
        self.leave_request.status = LeaveRequest.Status.SUBSTITUTE_PENDING
        self.leave_request.save()

        self.save()


class LeaveReport(AuditModel):
    """Monthly/periodic reports on teacher absences."""

    class ReportType(models.TextChoices):
        """Types of reports."""
        MONTHLY = "MONTHLY", _("Monthly Report")
        QUARTERLY = "QUARTERLY", _("Quarterly Report")
        ANNUAL = "ANNUAL", _("Annual Report")
        CUSTOM = "CUSTOM", _("Custom Period")

    report_type = models.CharField(
        _("Report Type"),
        max_length=15,
        choices=ReportType.choices,
    )
    period_start = models.DateField(
        _("Period Start"),
        help_text=_("Start date of reporting period"),
    )
    period_end = models.DateField(
        _("Period End"),
        help_text=_("End date of reporting period"),
    )

    # Report data (JSON)
    summary_data = models.JSONField(
        _("Summary Data"),
        default=dict,
        help_text=_("Summary statistics for the period"),
    )
    detail_data = models.JSONField(
        _("Detail Data"),
        default=dict,
        help_text=_("Detailed leave records"),
    )

    # Report metadata
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="generated_leave_reports",
        verbose_name=_("Generated By"),
    )
    generated_date = models.DateTimeField(
        _("Generated Date"),
        default=timezone.now,
    )
    report_file = models.FileField(
        _("Report File"),
        upload_to="leave_reports/%Y/%m/",
        null=True,
        blank=True,
        help_text=_("Generated PDF/Excel report file"),
    )

    class Meta:
        verbose_name = _("Leave Report")
        verbose_name_plural = _("Leave Reports")
        ordering = ["-period_end", "-generated_date"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["report_type", "-period_end"]),
            models.Index(fields=["-generated_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.get_report_type_display()} - {self.period_start} to {self.period_end}"
