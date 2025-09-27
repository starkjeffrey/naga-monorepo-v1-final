"""Attendance business logic and services.

This module provides services for:
- Daily roster synchronization with enrollment
- Attendance code generation and validation
- Geofence validation
- Permission request handling
- External system integration (Moodle, sponsors)
"""

import secrets
import string
from datetime import date, datetime, timedelta

from django.db.models import Prefetch
from django.utils import timezone

from apps.enrollment.models import ClassHeaderEnrollment
from apps.people.models import StudentProfile, TeacherProfile
from apps.scheduling.models import ClassPart, TeacherLeaveRequest

from .constants import AttendanceConstants
from .models import AttendanceRecord, AttendanceSession, PermissionRequest, RosterSync


class RosterSyncService:
    """Service for synchronizing class rosters with enrollment data.
    Runs twice daily (midnight and noon) to update mobile apps.
    """

    @classmethod
    def sync_daily_rosters(cls, sync_type: str = "MIDNIGHT") -> dict[str, int]:
        """Sync all active class rosters for today.

        Args:
            sync_type: 'MIDNIGHT' or 'NOON'

        Returns:
            Dict with sync statistics
        """
        today = timezone.now().date()
        success_count = 0
        error_count = 0

        # Get all active class parts for today with prefetched enrollments
        active_class_parts = ClassPart.objects.filter(
            class_session__class_header__status="ACTIVE",
            meeting_days__contains=today.strftime("%a").upper()[:3],
        ).prefetch_related(
            # Prefetch the enrollments for all class parts at once
            Prefetch(
                "class_session__class_header__enrollments",
                queryset=ClassHeaderEnrollment.objects.filter(status__in=["ENROLLED", "AUDIT"]).select_related(
                    "student__person"
                ),
                to_attr="prefetched_enrollments",
            )
        )

        for class_part in active_class_parts:
            try:
                cls._sync_class_roster(class_part, today, sync_type)
                success_count += 1
            except (ValueError, TypeError, AttributeError) as e:
                # Log error but continue with other classes
                RosterSync.objects.create(
                    class_part=class_part,
                    sync_date=today,
                    sync_type=sync_type,
                    student_count=0,
                    enrollment_snapshot={},
                    is_successful=False,
                    error_message=str(e),
                )
                error_count += 1

        return {
            "success_count": success_count,
            "error_count": error_count,
            "total_classes": success_count + error_count,
        }

    @classmethod
    def _sync_class_roster(cls, class_part: ClassPart, sync_date, sync_type: str):
        """Sync roster for a single class part."""
        # Use prefetched enrollments if available, otherwise query
        if hasattr(class_part.class_session.class_header, "prefetched_enrollments"):  # type: ignore[attr-defined]
            enrollments = class_part.class_session.class_header.prefetched_enrollments  # type: ignore[attr-defined]
        else:
            # Fallback for when called without prefetch
            enrollments = ClassHeaderEnrollment.objects.filter(
                class_header=class_part.class_session.class_header,  # type: ignore[attr-defined]
                status__in=["ENROLLED", "AUDIT"],  # Active enrollment statuses
            ).select_related("student__person")

        # Create enrollment snapshot
        roster_data = []
        for enrollment in enrollments:
            student_data = {
                "student_id": enrollment.student.student_id,
                "student_name": enrollment.student.person.display_name,
                "enrollment_status": enrollment.status,
                "is_audit": enrollment.is_audit,
                "late_enrollment": enrollment.late_enrollment,
            }
            roster_data.append(student_data)

        # Save roster sync record
        RosterSync.objects.update_or_create(
            class_part=class_part,
            sync_date=sync_date,
            sync_type=sync_type,
            defaults={
                "student_count": len(roster_data),
                "enrollment_snapshot": {"roster": roster_data},
                "is_successful": True,
                "error_message": "",
            },
        )


class AttendanceCodeService:
    """Service for generating and validating 5-digit attendance codes."""

    @classmethod
    def generate_attendance_code(cls) -> str:
        """Generate a unique 6-character attendance code.

        Returns:
            6-character alphanumeric code (uppercase letters and digits)
        """
        # Use uppercase letters and digits, excluding confusing characters
        characters = string.ascii_uppercase.replace("O", "").replace("I", "") + string.digits.replace("0", "").replace(
            "1",
            "",
        )

        # Generate codes until we find one that's not currently active
        max_attempts = 100
        for _ in range(max_attempts):
            code = "".join(secrets.choice(characters) for _ in range(6))

            # Check if code is already in use for an active session
            if not AttendanceSession.objects.filter(
                attendance_code=code,
                is_active=True,
                code_expires_at__gt=timezone.now(),
            ).exists():
                return code

        # Fallback if we somehow can't generate a unique code
        msg = "Unable to generate unique attendance code"
        raise ValueError(msg)

    @classmethod
    def create_backend_generated_session(
        cls,
        class_part: ClassPart,
        teacher_user,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> AttendanceSession:
        """Create attendance session with backend-generated code.

        Args:
            class_part: The class component
            teacher_user: User object for the teacher
            latitude: Teacher's location latitude
            longitude: Teacher's location longitude

        Returns:
            AttendanceSession with backend-generated code
        """
        # Generate unique attendance code
        attendance_code = cls.generate_attendance_code()

        # Create attendance session with backend-generated code
        now = timezone.now()
        session = AttendanceSession.objects.create(
            class_part=class_part,
            teacher=teacher_user.person.teacher_profile,
            session_date=now.date(),
            start_time=now.time(),
            attendance_code=attendance_code,  # Backend-generated code
            code_generated_at=now,
            code_expires_at=now + timedelta(minutes=15),  # 15-minute window
            latitude=latitude,
            longitude=longitude,
            is_active=True,
        )

        # Auto-create ABSENT records for all enrolled students
        cls._create_default_attendance_records(session)

        return session

    @classmethod
    def record_teacher_generated_session(
        cls,
        class_part: ClassPart,
        teacher_user,
        teacher_generated_code: str,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> AttendanceSession:
        """Record attendance session with code generated by teacher's mobile app.

        Args:
            class_part: The class component
            teacher_user: User object for the teacher
            teacher_generated_code: 5-digit code generated by teacher's mobile app
            latitude: Teacher's location latitude
            longitude: Teacher's location longitude

        Returns:
            AttendanceSession with recorded code
        """
        # Create attendance session with teacher's code
        now = timezone.now()
        session = AttendanceSession.objects.create(
            class_part=class_part,
            teacher=teacher_user.person.teacher_profile,
            session_date=now.date(),
            start_time=now.time(),
            attendance_code=teacher_generated_code,  # Code from mobile app
            code_generated_at=now,
            code_expires_at=now + timedelta(minutes=15),  # 15-minute window
            latitude=latitude,
            longitude=longitude,
            is_active=True,
        )

        # Auto-create ABSENT records for all enrolled students
        cls._create_default_attendance_records(session)

        return session

    @classmethod
    def _create_default_attendance_records(cls, session: AttendanceSession):
        """Create default ABSENT records for all enrolled students."""
        enrollments = ClassHeaderEnrollment.objects.filter(
            class_header=session.class_part.class_session.class_header,  # type: ignore[attr-defined]
            status__in=["ENROLLED", "AUDIT"],
        )

        for enrollment in enrollments:
            AttendanceRecord.objects.create(
                attendance_session=session,
                student=enrollment.student,
                status=AttendanceRecord.AttendanceStatus.ABSENT,
                data_source=AttendanceRecord.DataSource.AUTO_ABSENT,
            )

    @classmethod
    def validate_student_code_submission(
        cls,
        session: AttendanceSession,
        student_id: int,
        submitted_code: str,
        latitude: float | None = None,
        longitude: float | None = None,
    ) -> dict:
        """Validate student's code submission and update attendance.

        Args:
            session: AttendanceSession
            student_id: Student ID submitting code
            submitted_code: Code student entered
            latitude: Student's location latitude
            longitude: Student's location longitude

        Returns:
            Dict with validation results
        """
        try:
            # Get student's attendance record
            record = AttendanceRecord.objects.get(
                attendance_session=session,
                student__student_id=student_id,
            )
        except AttendanceRecord.DoesNotExist:
            return {"success": False, "error": "Student not enrolled in this class"}

        # Check if code submission window is still open
        if timezone.now() > session.code_expires_at:
            return {"success": False, "error": "Attendance code has expired"}

        # Validate code
        code_correct = submitted_code == session.attendance_code

        # Validate geofence if location provided
        within_geofence = None
        if latitude and longitude and session.latitude and session.longitude:
            within_geofence = cls._validate_geofence(
                student_lat=latitude,
                student_lon=longitude,
                class_lat=float(session.latitude),
                class_lon=float(session.longitude),
                radius=session.geofence_radius_meters,
            )

        # Determine attendance status
        if code_correct and (within_geofence is None or within_geofence):
            # Check if submission is late
            submission_time = timezone.now()
            class_start = datetime.combine(session.session_date, session.start_time)
            class_start = timezone.make_aware(class_start)

            minutes_late = (submission_time - class_start).total_seconds() / 60

            if minutes_late <= AttendanceConstants.LATE_THRESHOLD_MINUTES:
                status = AttendanceRecord.AttendanceStatus.PRESENT
            else:
                status = AttendanceRecord.AttendanceStatus.LATE
        else:
            status = AttendanceRecord.AttendanceStatus.ABSENT

        # Calculate distance if location provided
        distance_meters = None
        if latitude and longitude and session.latitude and session.longitude:
            # Geolocation distance calculation - requires geopy package
            # student_location = (latitude, longitude)
            # class_location = (float(session.latitude), float(session.longitude))
            # distance_meters = int(geodesic(student_location, class_location).meters)
            distance_meters = 0  # Placeholder

        # Update attendance record
        record.submitted_code = submitted_code
        record.code_correct = code_correct
        record.submitted_at = timezone.now()
        record.submitted_latitude = latitude
        record.submitted_longitude = longitude
        record.within_geofence = within_geofence
        record.distance_from_class = distance_meters
        record.status = status
        record.data_source = AttendanceRecord.DataSource.MOBILE_CODE
        record.save()

        return {
            "success": True,
            "status": status,
            "code_correct": code_correct,
            "within_geofence": within_geofence,
            "message": f"Attendance recorded as {status}",
        }

    @classmethod
    def _validate_geofence(
        cls,
        student_lat: float,
        student_lon: float,
        class_lat: float,
        class_lon: float,
        radius: int,
    ) -> bool:
        """Check if student is within geofence radius of classroom.

        Args:
            student_lat: Student's latitude
            student_lon: Student's longitude
            class_lat: Classroom latitude
            class_lon: Classroom longitude
            radius: Geofence radius in meters

        Returns:
            True if within geofence, False otherwise
        """
        # Geolocation validation - requires geopy package
        # student_location = (student_lat, student_lon)
        # class_location = (class_lat, class_lon)
        # distance = geodesic(student_location, class_location).meters
        return True  # Placeholder - always valid for now


class PermissionRequestService:
    """Service for handling permission requests (excused absences).
    Different policies for different programs.
    """

    @classmethod
    def create_permission_request(
        cls,
        student_id: int,
        class_part_id: int,
        session_date,
        reason: str,
    ) -> dict:
        """Create a permission request for excused absence.

        Args:
            student_id: Student requesting permission
            class_part_id: Class they want to be excused from
            session_date: Date of the class
            reason: Student's reason for absence

        Returns:
            Dict with request results
        """
        try:
            student = StudentProfile.objects.get(student_id=student_id)
            class_part = ClassPart.objects.get(id=class_part_id)
        except (StudentProfile.DoesNotExist, ClassPart.DoesNotExist):
            return {"success": False, "error": "Invalid student or class"}

        # Determine program type and policies
        program_type = cls._get_program_type(class_part)

        # IEAP doesn't allow permission requests
        if program_type == "IEAP":
            return {
                "success": False,
                "error": "IEAP program does not allow permission requests",
            }

        # Create permission request
        request = PermissionRequest.objects.create(
            student=student,
            class_part=class_part,
            session_date=session_date,
            reason=reason,
            program_type=program_type,
            requires_approval=(program_type != "HIGH_SCHOOL"),
            request_status=(
                PermissionRequest.RequestStatus.AUTO_APPROVED
                if program_type == "HIGH_SCHOOL"
                else PermissionRequest.RequestStatus.PENDING
            ),
        )

        if program_type == "HIGH_SCHOOL":
            cls._notify_parents(request)

        return {
            "success": True,
            "request_id": request.id,
            "status": request.request_status,
            "requires_approval": request.requires_approval,
        }

    @classmethod
    def _get_program_type(cls, class_part: ClassPart) -> str:
        """Determine program type from class part."""
        # This would be implemented based on your program structure
        division_name = class_part.class_session.class_header.course.division.name.upper()  # type: ignore[attr-defined]

        if "IEAP" in division_name:
            return "IEAP"
        if "HIGH SCHOOL" in division_name:
            return "HIGH_SCHOOL"
        if "BA" in division_name or "BACHELOR" in division_name:
            return "BA"
        return "OTHER"

    @classmethod
    def _notify_parents(cls, request: PermissionRequest):
        """Send permission request to parents for high school students."""
        # This would integrate with your parent notification system
        request.parent_notified = True
        request.parent_notification_date = timezone.now()
        request.save()


class SubstituteTeacherService:
    """Service for managing substitute teacher assignments and leave requests.

    Handles the complete workflow for substitute teacher management:
    - Leave request creation and approval
    - Substitute assignment and confirmation
    - Attendance session management for substitutes
    - Statistics and reporting
    """

    @classmethod
    def create_leave_request(
        cls,
        teacher_id: int,
        leave_date: date,
        leave_type: str,
        reason: str,
        is_emergency: bool = False,
        affected_class_part_ids: list | None = None,
    ) -> dict:
        """Create a new teacher leave request.

        Args:
            teacher_id: TeacherProfile ID requesting leave
            leave_date: Date of requested leave
            leave_type: Type of leave (SICK, PERSONAL, etc.)
            reason: Detailed reason for leave
            is_emergency: Whether this is an emergency request
            affected_class_part_ids: List of ClassPart IDs affected

        Returns:
            Dict with creation results and request ID
        """
        try:
            teacher = TeacherProfile.objects.get(id=teacher_id)
        except TeacherProfile.DoesNotExist:
            return {"success": False, "error": "Teacher not found"}

        # Validate leave date (can't be in past unless emergency)
        if leave_date < timezone.now().date() and not is_emergency:
            return {
                "success": False,
                "error": "Cannot request leave for past dates unless it's an emergency",
            }

        # Create leave request
        leave_request = TeacherLeaveRequest.objects.create(
            teacher=teacher,
            leave_date=leave_date,
            leave_type=leave_type,
            reason=reason,
            is_emergency=is_emergency,
        )

        # Add affected class parts if provided
        if affected_class_part_ids:
            try:
                class_parts = ClassPart.objects.filter(id__in=affected_class_part_ids)
                leave_request.affected_class_parts.set(class_parts)
            except Exception as e:
                return {"success": False, "error": f"Error adding class parts: {e!s}"}

        return {
            "success": True,
            "leave_request_id": leave_request.id,
            "status": leave_request.approval_status,
            "needs_substitute": leave_request.needs_substitute,
        }

    @classmethod
    def assign_substitute(
        cls,
        leave_request_id: int,
        substitute_teacher_id: int,
        assigned_by_user,
    ) -> dict:
        """Assign a substitute teacher to a leave request.

        Args:
            leave_request_id: TeacherLeaveRequest ID
            substitute_teacher_id: TeacherProfile ID of substitute
            assigned_by_user: User making the assignment

        Returns:
            Dict with assignment results
        """
        try:
            leave_request = TeacherLeaveRequest.objects.get(id=leave_request_id)
            substitute = TeacherProfile.objects.get(id=substitute_teacher_id)
        except (TeacherLeaveRequest.DoesNotExist, TeacherProfile.DoesNotExist):
            return {
                "success": False,
                "error": "Leave request or substitute teacher not found",
            }

        # Check if substitute is available on that date
        conflicts = cls._check_substitute_conflicts(
            substitute,
            leave_request.leave_date,
        )
        if conflicts:
            return {
                "success": False,
                "error": f"Substitute has conflicts: {', '.join(conflicts)}",
            }

        # Assign substitute using model method
        leave_request.assign_substitute(
            substitute=substitute,
            assigned_by=assigned_by_user,
        )

        # Update any existing attendance sessions for affected classes
        cls._update_attendance_sessions_for_substitute(leave_request, substitute)

        return {
            "success": True,
            "substitute_assigned": True,
            "substitute_name": substitute.person.display_name,
            "affected_sessions": leave_request.affected_sessions_count,
        }

    @classmethod
    def find_available_substitutes(
        cls,
        leave_date: date,
        required_qualifications: list | None = None,
    ) -> list:
        """Find available substitute teachers for a given date.

        Args:
            leave_date: Date when substitute is needed
            required_qualifications: List of required qualifications

        Returns:
            List of available TeacherProfile objects
        """
        # Get all active teachers
        available_teachers = TeacherProfile.objects.filter(
            status=TeacherProfile.Status.ACTIVE,
            person__is_deleted=False,
        )

        # Exclude teachers who already have leave requests on that date
        teachers_on_leave = TeacherLeaveRequest.objects.filter(
            leave_date=leave_date,
            approval_status__in=[
                TeacherLeaveRequest.ApprovalStatus.APPROVED,
                TeacherLeaveRequest.ApprovalStatus.PENDING,
            ],
        ).values_list("teacher_id", flat=True)

        available_teachers = available_teachers.exclude(id__in=teachers_on_leave)

        # Exclude teachers already assigned as substitutes on that date
        substitute_assignments = TeacherLeaveRequest.objects.filter(
            leave_date=leave_date,
            substitute_teacher__isnull=False,
        ).values_list("substitute_teacher_id", flat=True)

        available_teachers = available_teachers.exclude(id__in=substitute_assignments)

        # Filter by qualifications if provided
        if required_qualifications:
            # This would be implemented based on your qualification system
            pass

        return list(available_teachers.select_related("person"))

    @classmethod
    def _check_substitute_conflicts(
        cls,
        substitute: "TeacherProfile",
        leave_date: date,
    ) -> list:
        """Check if substitute teacher has any conflicts on the given date.

        Args:
            substitute: TeacherProfile of potential substitute
            leave_date: Date to check for conflicts

        Returns:
            List of conflict descriptions
        """
        conflicts = []

        # Check if substitute has their own leave request
        own_leave = TeacherLeaveRequest.objects.filter(
            teacher=substitute,
            leave_date=leave_date,
            approval_status__in=[
                TeacherLeaveRequest.ApprovalStatus.APPROVED,
                TeacherLeaveRequest.ApprovalStatus.PENDING,
            ],
        ).first()

        if own_leave:
            conflicts.append(f"Has own leave request ({own_leave.leave_type})")

        # Check if already assigned as substitute on that date
        existing_assignment = TeacherLeaveRequest.objects.filter(
            substitute_teacher=substitute,
            leave_date=leave_date,
        ).first()

        if existing_assignment:
            conflicts.append(
                f"Already assigned as substitute for {existing_assignment.teacher.person.display_name}",
            )

        # Future enhancement: Check for regular teaching schedule conflicts
        # This would require integration with scheduling system

        return conflicts

    @classmethod
    def _update_attendance_sessions_for_substitute(
        cls,
        leave_request: "TeacherLeaveRequest",
        substitute: "TeacherProfile",
    ):
        """Update any existing attendance sessions to reflect substitute assignment.

        Args:
            leave_request: TeacherLeaveRequest with substitute assigned
            substitute: TeacherProfile of the substitute teacher
        """
        # Find attendance sessions for affected class parts on the leave date
        affected_sessions = AttendanceSession.objects.filter(
            class_part__in=leave_request.affected_class_parts.all(),
            session_date=leave_request.leave_date,
        )

        # Update sessions to reflect substitute assignment
        for session in affected_sessions:
            session.assign_substitute(
                substitute_teacher=substitute,
                reason=f"Teacher leave: {leave_request.leave_type}",
                assigned_by=leave_request.substitute_assigned_by,
            )

    @classmethod
    def get_substitute_statistics(
        cls,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict:
        """Get statistics about substitute teacher usage.

        Args:
            start_date: Start of date range (defaults to current term)
            end_date: End of date range (defaults to current term)

        Returns:
            Dict with substitute statistics
        """
        # Default to current month if no dates provided
        if not start_date:
            start_date = timezone.now().date().replace(day=1)
        if not end_date:
            end_date = timezone.now().date()

        # Get leave requests in date range
        leave_requests = TeacherLeaveRequest.objects.filter(
            leave_date__range=[start_date, end_date],
        )

        # Calculate statistics
        total_requests = leave_requests.count()
        approved_requests = leave_requests.filter(
            approval_status=TeacherLeaveRequest.ApprovalStatus.APPROVED,
        ).count()
        emergency_requests = leave_requests.filter(is_emergency=True).count()
        substitutes_found = leave_requests.filter(substitute_found=True).count()

        # Leave type breakdown
        leave_type_stats = {}
        for leave_type, display_name in TeacherLeaveRequest.LeaveType.choices:
            count = leave_requests.filter(leave_type=leave_type).count()
            if count > 0:
                leave_type_stats[display_name] = count

        # Most used substitutes
        substitute_usage: dict[str, int] = {}
        substitute_requests = leave_requests.filter(substitute_teacher__isnull=False)
        for request in substitute_requests:
            if request.substitute_teacher is not None:
                sub_name = request.substitute_teacher.person.display_name
                substitute_usage[sub_name] = substitute_usage.get(sub_name, 0) + 1

        return {
            "total_leave_requests": total_requests,
            "approved_requests": approved_requests,
            "emergency_requests": emergency_requests,
            "substitutes_found": substitutes_found,
            "substitute_coverage_rate": (
                (substitutes_found / approved_requests * 100) if approved_requests > 0 else 0
            ),
            "leave_type_breakdown": leave_type_stats,
            "substitute_usage": dict(
                sorted(
                    substitute_usage.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )[:10],
            ),  # Top 10 substitutes
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        }
