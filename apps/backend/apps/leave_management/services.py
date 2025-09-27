"""Service layer for leave management business logic.

This module contains the business logic for:
- Leave request processing and validation
- Substitute teacher assignment
- Permission transfers to attendance app
- Leave balance calculations
- Report generation
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from django.db import transaction
from django.db.models import Q, Sum, Count, Avg
from django.utils import timezone
from django.core.exceptions import ValidationError

from apps.leave_management.models import (
    LeaveRequest,
    LeaveBalance,
    LeaveType,
    LeavePolicy,
    SubstituteAssignment,
    LeaveReport,
)
from apps.people.models import TeacherProfile
from apps.scheduling.models import ClassPart


class LeaveRequestService:
    """Service for managing leave requests."""

    @staticmethod
    @transaction.atomic
    def create_leave_request(
        teacher: TeacherProfile,
        leave_type: LeaveType,
        start_date: date,
        end_date: date,
        reason: str,
        priority: str = LeaveRequest.Priority.NORMAL,
        requires_substitute: bool = True,
        substitute_notes: str = "",
        supporting_documents: Optional[List[str]] = None,
    ) -> LeaveRequest:
        """Create a new leave request with validation and balance check.

        Args:
            teacher: The teacher requesting leave
            leave_type: Type of leave being requested
            start_date: First day of leave
            end_date: Last day of leave
            reason: Detailed reason for leave
            priority: Priority level of request
            requires_substitute: Whether substitute is needed
            substitute_notes: Instructions for substitute
            supporting_documents: List of document paths/URLs

        Returns:
            Created LeaveRequest instance

        Raises:
            ValidationError: If request is invalid or insufficient balance
        """
        # Calculate total days
        total_days = (end_date - start_date).days + 1

        # Check leave balance
        year = start_date.year
        balance = LeaveBalanceService.get_or_create_balance(
            teacher, leave_type, year
        )

        if not balance.can_request_days(Decimal(str(total_days))):
            raise ValidationError(
                f"Insufficient leave balance. Available: {balance.available_days} days, "
                f"Requested: {total_days} days"
            )

        # Check for overlapping requests
        overlapping = LeaveRequest.objects.filter(
            teacher=teacher,
            status__in=[
                LeaveRequest.Status.PENDING,
                LeaveRequest.Status.APPROVED,
                LeaveRequest.Status.SUBSTITUTE_PENDING,
                LeaveRequest.Status.SUBSTITUTE_ASSIGNED,
            ],
        ).filter(
            Q(start_date__lte=end_date) & Q(end_date__gte=start_date)
        )

        if overlapping.exists():
            raise ValidationError(
                "You have overlapping leave requests for these dates"
            )

        # Create the request
        leave_request = LeaveRequest.objects.create(
            teacher=teacher,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            priority=priority,
            requires_substitute=requires_substitute,
            substitute_notes=substitute_notes,
            supporting_documents=supporting_documents or [],
            status=LeaveRequest.Status.DRAFT,
        )

        return leave_request

    @staticmethod
    @transaction.atomic
    def submit_leave_request(leave_request: LeaveRequest) -> LeaveRequest:
        """Submit a draft leave request for approval.

        Args:
            leave_request: The draft leave request

        Returns:
            Updated LeaveRequest instance

        Raises:
            ValidationError: If request cannot be submitted
        """
        if leave_request.status != LeaveRequest.Status.DRAFT:
            raise ValidationError("Only draft requests can be submitted")

        # Update balance to mark days as pending
        total_days = leave_request.total_days
        balance = LeaveBalanceService.get_or_create_balance(
            leave_request.teacher,
            leave_request.leave_type,
            leave_request.start_date.year
        )

        if not balance.can_request_days(Decimal(str(total_days))):
            raise ValidationError("Insufficient leave balance")

        balance.pending_days += Decimal(str(total_days))
        balance.save()

        # Update request status
        leave_request.status = LeaveRequest.Status.PENDING
        leave_request.submitted_date = timezone.now()

        # Set priority to emergency if submitted late
        if leave_request.is_emergency:
            leave_request.priority = LeaveRequest.Priority.EMERGENCY

        leave_request.save()

        # TODO: Send notification to approvers
        NotificationService.notify_leave_request_submitted(leave_request)

        return leave_request

    @staticmethod
    def get_pending_requests_for_approval(user) -> List[LeaveRequest]:
        """Get leave requests pending approval for a user.

        Args:
            user: The user who can approve requests

        Returns:
            List of pending leave requests
        """
        # TODO: Add permission check for who can approve
        return LeaveRequest.objects.filter(
            status=LeaveRequest.Status.PENDING
        ).order_by("-priority", "start_date")

    @staticmethod
    def get_teacher_leave_history(
        teacher: TeacherProfile,
        year: Optional[int] = None
    ) -> List[LeaveRequest]:
        """Get leave history for a teacher.

        Args:
            teacher: The teacher
            year: Optional year filter

        Returns:
            List of leave requests
        """
        queryset = LeaveRequest.objects.filter(teacher=teacher)

        if year:
            queryset = queryset.filter(start_date__year=year)

        return queryset.order_by("-start_date")


class SubstituteAssignmentService:
    """Service for managing substitute teacher assignments."""

    @staticmethod
    @transaction.atomic
    def assign_substitute(
        leave_request: LeaveRequest,
        substitute_teacher: TeacherProfile,
        assigned_by,
        classes_to_cover: List[ClassPart],
        notes: str = ""
    ) -> SubstituteAssignment:
        """Assign a substitute teacher to cover a leave request.

        Args:
            leave_request: The leave request needing coverage
            substitute_teacher: The substitute teacher
            assigned_by: User making the assignment
            classes_to_cover: List of classes to be covered
            notes: Instructions for the substitute

        Returns:
            Created SubstituteAssignment instance

        Raises:
            ValidationError: If assignment is invalid
        """
        if leave_request.status not in [
            LeaveRequest.Status.APPROVED,
            LeaveRequest.Status.SUBSTITUTE_PENDING
        ]:
            raise ValidationError(
                "Leave request must be approved before assigning substitute"
            )

        # Check if substitute is available
        conflicting = SubstituteAssignment.objects.filter(
            substitute_teacher=substitute_teacher,
            status__in=[
                SubstituteAssignment.Status.PENDING,
                SubstituteAssignment.Status.CONFIRMED
            ],
            leave_request__start_date__lte=leave_request.end_date,
            leave_request__end_date__gte=leave_request.start_date,
        )

        if conflicting.exists():
            raise ValidationError(
                "Substitute teacher has conflicting assignments for these dates"
            )

        # Create assignment
        assignment = SubstituteAssignment.objects.create(
            leave_request=leave_request,
            substitute_teacher=substitute_teacher,
            assigned_by=assigned_by,
            substitute_notes=notes,
        )

        # Add classes to cover
        assignment.classes_to_cover.set(classes_to_cover)

        # Send notification to substitute
        NotificationService.notify_substitute_assignment(assignment)

        return assignment

    @staticmethod
    def get_available_substitutes(
        start_date: date,
        end_date: date,
        subject_area: Optional[str] = None
    ) -> List[TeacherProfile]:
        """Get list of available substitute teachers for given dates.

        Args:
            start_date: Start date needing coverage
            end_date: End date needing coverage
            subject_area: Optional subject area filter

        Returns:
            List of available substitute teachers
        """
        # Get all teachers who can substitute
        substitutes = TeacherProfile.objects.filter(
            can_substitute=True,
            is_active=True,
        )

        if subject_area:
            substitutes = substitutes.filter(
                subject_areas__contains=subject_area
            )

        # Exclude those with conflicts
        conflicting_ids = SubstituteAssignment.objects.filter(
            status__in=[
                SubstituteAssignment.Status.PENDING,
                SubstituteAssignment.Status.CONFIRMED
            ],
            leave_request__start_date__lte=end_date,
            leave_request__end_date__gte=start_date,
        ).values_list("substitute_teacher_id", flat=True)

        # Also exclude those on leave themselves
        on_leave_ids = LeaveRequest.objects.filter(
            status__in=[
                LeaveRequest.Status.APPROVED,
                LeaveRequest.Status.SUBSTITUTE_ASSIGNED
            ],
            start_date__lte=end_date,
            end_date__gte=start_date,
        ).values_list("teacher_id", flat=True)

        return substitutes.exclude(
            Q(id__in=conflicting_ids) | Q(id__in=on_leave_ids)
        )

    @staticmethod
    @transaction.atomic
    def grant_substitute_permissions(assignment: SubstituteAssignment) -> None:
        """Grant attendance permissions to substitute teacher.

        This is the integration point with the attendance app.

        Args:
            assignment: The confirmed substitute assignment
        """
        from apps.attendance.services import AttendancePermissionService

        # Grant permissions for each class
        for class_part in assignment.classes_to_cover.all():
            AttendancePermissionService.grant_temporary_permission(
                teacher=assignment.substitute_teacher,
                class_part=class_part,
                start_date=assignment.leave_request.start_date,
                end_date=assignment.leave_request.end_date,
                reason=f"Substitute for {assignment.leave_request.teacher}",
            )

        # Update assignment
        assignment.permissions_granted = True
        assignment.permissions_granted_date = timezone.now()
        assignment.save()

        # Send roster to substitute
        NotificationService.send_roster_to_substitute(assignment)

    @staticmethod
    @transaction.atomic
    def revoke_substitute_permissions(assignment: SubstituteAssignment) -> None:
        """Revoke attendance permissions from substitute teacher.

        Args:
            assignment: The substitute assignment to revoke
        """
        from apps.attendance.services import AttendancePermissionService

        # Revoke permissions for each class
        for class_part in assignment.classes_to_cover.all():
            AttendancePermissionService.revoke_temporary_permission(
                teacher=assignment.substitute_teacher,
                class_part=class_part,
            )

        # Update assignment
        assignment.permissions_revoked_date = timezone.now()
        assignment.save()


class LeaveBalanceService:
    """Service for managing leave balances."""

    @staticmethod
    def get_or_create_balance(
        teacher: TeacherProfile,
        leave_type: LeaveType,
        year: int
    ) -> LeaveBalance:
        """Get or create leave balance for a teacher.

        Args:
            teacher: The teacher
            leave_type: Type of leave
            year: Calendar year

        Returns:
            LeaveBalance instance
        """
        balance, created = LeaveBalance.objects.get_or_create(
            teacher=teacher,
            leave_type=leave_type,
            year=year,
            defaults={
                "entitled_days": Decimal("0"),
                "used_days": Decimal("0"),
                "pending_days": Decimal("0"),
                "carried_forward": Decimal("0"),
            }
        )

        if created:
            # Calculate entitlement based on policy
            LeaveBalanceService.calculate_entitlement(balance)

        return balance

    @staticmethod
    def calculate_entitlement(balance: LeaveBalance) -> None:
        """Calculate leave entitlement based on policy.

        Args:
            balance: The leave balance to update
        """
        # Get applicable policy
        teacher = balance.teacher
        contract_type = getattr(teacher, "contract_type", "FULL_TIME")

        policy = LeavePolicy.objects.filter(
            contract_type=contract_type,
            leave_type=balance.leave_type,
            effective_date__lte=date(balance.year, 1, 1),
        ).filter(
            Q(end_date__isnull=True) |
            Q(end_date__gte=date(balance.year, 12, 31))
        ).first()

        if policy:
            # Check if monthly accrual or annual grant
            if policy.accrual_rate > 0:
                # Calculate based on months worked
                current_month = timezone.now().month if balance.year == timezone.now().year else 12
                balance.entitled_days = policy.accrual_rate * current_month
            else:
                # Annual grant
                balance.entitled_days = policy.annual_days

            # Handle carryover from previous year
            if policy.carries_forward and balance.year > timezone.now().year - 1:
                prev_balance = LeaveBalance.objects.filter(
                    teacher=balance.teacher,
                    leave_type=balance.leave_type,
                    year=balance.year - 1
                ).first()

                if prev_balance:
                    carryover = prev_balance.available_days
                    if policy.max_carryover:
                        carryover = min(carryover, policy.max_carryover)
                    balance.carried_forward = carryover

            balance.save()

    @staticmethod
    def get_all_balances(
        teacher: TeacherProfile,
        year: Optional[int] = None
    ) -> Dict[str, LeaveBalance]:
        """Get all leave balances for a teacher.

        Args:
            teacher: The teacher
            year: Optional year (defaults to current)

        Returns:
            Dictionary of leave type to balance
        """
        if not year:
            year = timezone.now().year

        balances = {}
        active_leave_types = LeaveType.objects.filter(is_active=True)

        for leave_type in active_leave_types:
            balance = LeaveBalanceService.get_or_create_balance(
                teacher, leave_type, year
            )
            balances[leave_type.code] = balance

        return balances


class LeaveReportService:
    """Service for generating leave reports."""

    @staticmethod
    def generate_monthly_report(
        year: int,
        month: int,
        generated_by
    ) -> LeaveReport:
        """Generate monthly leave report.

        Args:
            year: Report year
            month: Report month
            generated_by: User generating the report

        Returns:
            Generated LeaveReport instance
        """
        period_start = date(year, month, 1)
        if month == 12:
            period_end = date(year, 12, 31)
        else:
            period_end = date(year, month + 1, 1) - timedelta(days=1)

        # Collect statistics
        leave_requests = LeaveRequest.objects.filter(
            start_date__lte=period_end,
            end_date__gte=period_start,
            status__in=[
                LeaveRequest.Status.APPROVED,
                LeaveRequest.Status.SUBSTITUTE_ASSIGNED,
                LeaveRequest.Status.COMPLETED
            ]
        )

        summary_data = {
            "total_requests": leave_requests.count(),
            "total_days": sum(lr.total_days for lr in leave_requests),
            "by_type": {},
            "by_teacher": {},
            "substitute_coverage": {
                "required": leave_requests.filter(requires_substitute=True).count(),
                "assigned": leave_requests.filter(
                    status=LeaveRequest.Status.SUBSTITUTE_ASSIGNED
                ).count(),
            }
        }

        # Group by leave type
        for leave_type in LeaveType.objects.all():
            type_requests = leave_requests.filter(leave_type=leave_type)
            if type_requests.exists():
                summary_data["by_type"][leave_type.code] = {
                    "count": type_requests.count(),
                    "days": sum(lr.total_days for lr in type_requests),
                }

        # Group by teacher
        for teacher in TeacherProfile.objects.filter(
            leave_requests__in=leave_requests
        ).distinct():
            teacher_requests = leave_requests.filter(teacher=teacher)
            summary_data["by_teacher"][str(teacher.id)] = {
                "name": str(teacher),
                "count": teacher_requests.count(),
                "days": sum(lr.total_days for lr in teacher_requests),
            }

        # Create report
        report = LeaveReport.objects.create(
            report_type=LeaveReport.ReportType.MONTHLY,
            period_start=period_start,
            period_end=period_end,
            summary_data=summary_data,
            detail_data={
                "requests": [
                    {
                        "teacher": str(lr.teacher),
                        "type": lr.leave_type.name,
                        "start": lr.start_date.isoformat(),
                        "end": lr.end_date.isoformat(),
                        "days": lr.total_days,
                        "status": lr.status,
                    }
                    for lr in leave_requests
                ]
            },
            generated_by=generated_by,
        )

        # TODO: Generate PDF/Excel file
        # report.report_file = generate_report_file(report)
        # report.save()

        return report

    @staticmethod
    def get_teacher_absence_summary(
        teacher: TeacherProfile,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Get absence summary for a teacher.

        Args:
            teacher: The teacher
            start_date: Period start
            end_date: Period end

        Returns:
            Summary dictionary
        """
        leave_requests = LeaveRequest.objects.filter(
            teacher=teacher,
            start_date__lte=end_date,
            end_date__gte=start_date,
            status__in=[
                LeaveRequest.Status.APPROVED,
                LeaveRequest.Status.SUBSTITUTE_ASSIGNED,
                LeaveRequest.Status.COMPLETED
            ]
        )

        summary = {
            "total_absences": leave_requests.count(),
            "total_days": sum(lr.total_days for lr in leave_requests),
            "by_type": {},
            "upcoming": [],
            "history": [],
        }

        # Group by type
        for leave_type in LeaveType.objects.all():
            type_requests = leave_requests.filter(leave_type=leave_type)
            if type_requests.exists():
                summary["by_type"][leave_type.name] = sum(
                    lr.total_days for lr in type_requests
                )

        # Split into upcoming and history
        today = timezone.now().date()
        for lr in leave_requests.order_by("start_date"):
            entry = {
                "type": lr.leave_type.name,
                "start": lr.start_date.isoformat(),
                "end": lr.end_date.isoformat(),
                "days": lr.total_days,
                "status": lr.get_status_display(),
            }

            if lr.start_date >= today:
                summary["upcoming"].append(entry)
            else:
                summary["history"].append(entry)

        return summary


class NotificationService:
    """Service for handling notifications (placeholder for future implementation)."""

    @staticmethod
    def notify_leave_request_submitted(leave_request: LeaveRequest) -> None:
        """Send notification when leave request is submitted."""
        # TODO: Implement email/SMS/push notification
        pass

    @staticmethod
    def notify_substitute_assignment(assignment: SubstituteAssignment) -> None:
        """Send notification to substitute teacher about assignment."""
        # TODO: Implement email/SMS/push notification
        pass

    @staticmethod
    def send_roster_to_substitute(assignment: SubstituteAssignment) -> None:
        """Send class roster to substitute teacher."""
        # TODO: Implement roster email with student lists
        pass