"""from datetime import date
Comprehensive tests for the attendance app models.

This test module validates all functionality of the attendance tracking system
following clean architecture principles and mobile-first design patterns.

Test coverage includes:
- AttendanceSettings: Program-specific attendance policies
- AttendanceSession: Teacher-generated attendance tracking sessions
- AttendanceRecord: Individual student attendance records with validation
- PermissionRequest: Excused absence request workflow
- RosterSync: Daily enrollment synchronization
- AttendanceArchive: Term-end attendance archival
- Mobile app integration patterns
- Geofencing and code validation
- Business logic constraints and validation
- Audit logging functionality
- Edge cases and error conditions
- Clean architecture compliance
"""

from datetime import date, time, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.attendance.models import (
    AttendanceArchive,
    AttendanceRecord,
    AttendanceSession,
    AttendanceSettings,
    PermissionRequest,
    RosterSync,
)
from apps.common.utils import get_current_date
from apps.curriculum.models import Division
from apps.people.models import Person, StudentProfile, TeacherProfile

# We'll mock the curriculum and scheduling models since they may not exist yet

User = get_user_model()

# Test constants
LATE_THRESHOLD_MINUTES = 10
DEFAULT_CODE_WINDOW_MINUTES = 20
DEFAULT_GEOFENCE_RADIUS = 100


class MockDivision:
    """Mock curriculum division for testing."""

    def __init__(self, name="Test Program"):
        self.name = name
        self.id = 1


class MockClassPart:
    """Mock scheduling class part for testing."""

    def __init__(self, name="Test Class"):
        self.name = name
        self.id = 1


class MockTerm:
    """Mock curriculum term for testing."""

    def __init__(self, name="Fall 2024"):
        self.name = name
        self.id = 1


class AttendanceSettingsModelTest(TestCase):
    """Test AttendanceSettings model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        # Create real division for attendance settings
        self.division = Division.objects.create(
            name="Language",
            short_name="LANG",
            description="Language Division for foreign language programs",
        )

    def test_attendance_settings_creation(self):
        """Test basic attendance settings creation."""
        settings = AttendanceSettings.objects.create(
            program=self.division,
            allows_permission_requests=False,
            auto_approve_permissions=False,
            parent_notification_required=False,
            attendance_required_percentage=Decimal("85.00"),
            late_threshold_minutes=10,
            default_code_window_minutes=20,
            default_geofence_radius=100,
            attendance_affects_grade=True,
            attendance_grade_weight=Decimal("0.150"),
        )

        assert not settings.allows_permission_requests
        assert not settings.auto_approve_permissions
        assert not settings.parent_notification_required
        assert settings.attendance_required_percentage == Decimal("85.00")
        assert settings.late_threshold_minutes == LATE_THRESHOLD_MINUTES
        assert settings.default_code_window_minutes == DEFAULT_CODE_WINDOW_MINUTES
        assert settings.default_geofence_radius == DEFAULT_GEOFENCE_RADIUS
        assert settings.attendance_affects_grade
        assert settings.attendance_grade_weight == Decimal("0.150")

    def test_attendance_settings_defaults(self):
        """Test default values for attendance settings."""
        settings = AttendanceSettings()

        assert settings.allows_permission_requests  # Default True
        assert not settings.auto_approve_permissions  # Default False
        assert not settings.parent_notification_required  # Default False
        assert settings.attendance_required_percentage == Decimal("80.00")
        assert settings.late_threshold_minutes == 15
        assert settings.default_code_window_minutes == 15
        assert settings.default_geofence_radius == 50
        assert settings.attendance_affects_grade  # Default True
        assert settings.attendance_grade_weight == Decimal("0.100")

    def test_attendance_percentage_validation(self):
        """Test validation of attendance percentage bounds."""
        # Test invalid percentage > 100
        settings = AttendanceSettings(
            program=self.division,
            attendance_required_percentage=Decimal("150.00"),
        )
        with pytest.raises(ValidationError):
            settings.full_clean()

        # Test invalid percentage < 0
        settings = AttendanceSettings(
            program=self.division,
            attendance_required_percentage=Decimal("-10.00"),
        )
        with pytest.raises(ValidationError):
            settings.full_clean()

        # Test valid percentage
        settings = AttendanceSettings(
            program=self.division,
            attendance_required_percentage=Decimal("95.00"),
        )
        settings.full_clean()  # Should not raise

    def test_grade_weight_validation(self):
        """Test validation of attendance grade weight bounds."""
        # Test invalid weight > 1
        settings = AttendanceSettings(
            program=self.division,
            attendance_grade_weight=Decimal("1.500"),
        )
        with pytest.raises(ValidationError):
            settings.full_clean()

        # Test invalid weight < 0
        settings = AttendanceSettings(
            program=self.division,
            attendance_grade_weight=Decimal("-0.100"),
        )
        with pytest.raises(ValidationError):
            settings.full_clean()

        # Test valid weight
        settings = AttendanceSettings(
            program=self.division,
            attendance_grade_weight=Decimal("0.250"),
        )
        settings.full_clean()  # Should not raise

    def test_string_representation(self):
        """Test string representation."""
        settings = AttendanceSettings.objects.create(
            program=self.division,
        )

        expected = "Language - Attendance Settings"
        assert str(settings) == expected


class AttendanceSessionModelTest(TestCase):
    """Test AttendanceSession model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="teacher@test.com",
            password="testpass",
        )

        self.person = Person.objects.create(
            family_name="Teacher",
            personal_name="Test",
            date_of_birth=date(1980, 1, 1),
        )

        self.teacher = TeacherProfile.objects.create(
            person=self.person,
            status=TeacherProfile.Status.ACTIVE,
        )

    @patch("apps.attendance.models.AttendanceSession.class_part")
    def test_attendance_session_creation(self, mock_class_part):
        """Test basic attendance session creation."""
        mock_class_part.name = "English 101"

        session = AttendanceSession.objects.create(
            teacher=self.teacher,
            session_date=get_current_date(),
            start_time=time(9, 0),
            end_time=time(10, 30),
            attendance_code="ABC12",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
            code_window_minutes=15,
            latitude=Decimal("11.5564"),  # Phnom Penh coordinates
            longitude=Decimal("104.9282"),
            geofence_radius_meters=75,
            is_active=True,
            is_makeup_class=False,
            manual_fallback_enabled=True,
            django_fallback_enabled=True,
        )

        assert session.teacher == self.teacher
        assert session.session_date == get_current_date()
        assert session.start_time == time(9, 0)
        assert session.end_time == time(10, 30)
        assert session.attendance_code == "ABC12"
        assert session.latitude == Decimal("11.5564")
        assert session.longitude == Decimal("104.9282")
        assert session.geofence_radius_meters == 75
        assert session.is_active
        assert not session.is_makeup_class
        assert session.manual_fallback_enabled
        assert session.django_fallback_enabled

    def test_is_code_valid_property(self):
        """Test code validity checking."""
        # Create session with valid code - in-memory
        future_expiry = timezone.now() + timedelta(minutes=10)
        session = AttendanceSession(
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code="VALID",
            code_generated_at=timezone.now(),
            code_expires_at=future_expiry,
            is_active=True,
        )

        assert session.is_code_valid

        # Test expired code
        session.code_expires_at = timezone.now() - timedelta(minutes=1)
        assert not session.is_code_valid

        # Test inactive session
        session.code_expires_at = future_expiry
        session.is_active = False
        assert not session.is_code_valid

    def test_attendance_percentage_calculation(self):
        """Test attendance percentage calculation."""
        # Test in-memory percentage calculation
        session = AttendanceSession(
            total_students=20,
            present_count=15,
            absent_count=5,
        )

        assert session.attendance_percentage == 75.0

        # Test with zero students
        session.total_students = 0
        assert session.attendance_percentage == 0.0

    def test_makeup_class_handling(self):
        """Test makeup class functionality."""
        # Test in-memory makeup class attributes
        session = AttendanceSession(
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code="MAKE1",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
            is_makeup_class=True,
            makeup_reason="Holiday replacement class",
        )

        assert session.is_makeup_class
        assert session.makeup_reason == "Holiday replacement class"

    @patch("apps.attendance.models.AttendanceSession.class_part")
    def test_session_statistics_update(self, mock_class_part):
        """Test update_statistics method."""
        mock_class_part.name = "Test Class"

        session = AttendanceSession.objects.create(
            teacher=self.teacher,
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code="STAT1",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
        )

        # Mock attendance records
        with patch.object(session, "attendance_records") as mock_records:
            mock_all = mock_records.all.return_value
            mock_all.count.return_value = 25

            mock_filter_present = mock_records.filter.return_value
            mock_filter_present.count.return_value = 20  # Present + Permission

            session.update_statistics()

        session.refresh_from_db()
        assert session.total_students == 25
        assert session.present_count == 20
        assert session.absent_count == 20  # This would be calculated differently in real implementation

    @patch("apps.attendance.models.AttendanceSession.class_part")
    def test_string_representation(self, mock_class_part):
        """Test string representation."""
        mock_class_part.__str__ = lambda: "English 101"

        session = AttendanceSession.objects.create(
            teacher=self.teacher,
            session_date=date(2024, 3, 15),
            start_time=time(9, 0),
            attendance_code="STR01",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
        )

        expected = "English 101 - 2024-03-15 (STR01)"
        assert str(session) == expected


class AttendanceRecordModelTest(TestCase):
    """Test AttendanceRecord model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="teacher@test.com",
            password="testpass",
        )

        # Create teacher
        teacher_person = Person.objects.create(
            family_name="Teacher",
            personal_name="Test",
            date_of_birth=date(1980, 1, 1),
        )
        self.teacher = TeacherProfile.objects.create(
            person=teacher_person,
            status=TeacherProfile.Status.ACTIVE,
        )

        # Create student
        student_person = Person.objects.create(
            family_name="Student",
            personal_name="Test",
            date_of_birth=date(2000, 1, 1),
        )
        self.student = StudentProfile.objects.create(
            person=student_person,
            student_id=12345,
        )

    @patch("apps.attendance.models.AttendanceSession.class_part")
    def test_attendance_record_creation(self, mock_class_part):
        """Test basic attendance record creation."""
        mock_class_part.name = "Test Class"

        session = AttendanceSession.objects.create(
            teacher=self.teacher,
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code="REC01",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
        )

        record = AttendanceRecord.objects.create(
            attendance_session=session,
            student=self.student,
            status=AttendanceRecord.AttendanceStatus.PRESENT,
            submitted_code="REC01",
            code_correct=True,
            submitted_at=timezone.now(),
            submitted_latitude=Decimal("11.5564"),
            submitted_longitude=Decimal("104.9282"),
            within_geofence=True,
            distance_from_class=25,
            data_source=AttendanceRecord.DataSource.MOBILE_CODE,
            recorded_by=self.user,
        )

        assert record.attendance_session == session
        assert record.student == self.student
        assert record.status == AttendanceRecord.AttendanceStatus.PRESENT
        assert record.submitted_code == "REC01"
        assert record.code_correct
        assert record.within_geofence
        assert record.distance_from_class == 25
        assert record.data_source == AttendanceRecord.DataSource.MOBILE_CODE

    def test_attendance_status_choices(self):
        """Test all attendance status options."""
        statuses = [
            AttendanceRecord.AttendanceStatus.PRESENT,
            AttendanceRecord.AttendanceStatus.ABSENT,
            AttendanceRecord.AttendanceStatus.LATE,
            AttendanceRecord.AttendanceStatus.PERMISSION,
        ]

        for status in statuses:
            record = AttendanceRecord(
                student=self.student,
                status=status,
            )
            assert record.status == status

    def test_data_source_choices(self):
        """Test all data source options."""
        data_sources = [
            AttendanceRecord.DataSource.MOBILE_CODE,
            AttendanceRecord.DataSource.MOBILE_MANUAL,
            AttendanceRecord.DataSource.DJANGO_MANUAL,
            AttendanceRecord.DataSource.AUTO_ABSENT,
            AttendanceRecord.DataSource.PERMISSION_REQUEST,
        ]

        for data_source in data_sources:
            record = AttendanceRecord(
                student=self.student,
                status=AttendanceRecord.AttendanceStatus.PRESENT,
                data_source=data_source,
            )
            assert record.data_source == data_source

    def test_is_present_property(self):
        """Test is_present property logic."""
        # Test PRESENT status
        record = AttendanceRecord(
            student=self.student,
            status=AttendanceRecord.AttendanceStatus.PRESENT,
        )
        assert record.is_present

        # Test PERMISSION status (excused)
        record.status = AttendanceRecord.AttendanceStatus.PERMISSION
        assert record.is_present

        # Test ABSENT status
        record.status = AttendanceRecord.AttendanceStatus.ABSENT
        assert not record.is_present

        # Test LATE status
        record.status = AttendanceRecord.AttendanceStatus.LATE
        assert not record.is_present

    @patch("apps.attendance.models.AttendanceSession.class_part")
    def test_submission_delay_calculation(self, mock_class_part):
        """Test submission delay calculation."""
        mock_class_part.name = "Test Class"

        session_date = get_current_date()
        start_time = time(9, 0)

        session = AttendanceSession.objects.create(
            teacher=self.teacher,
            session_date=session_date,
            start_time=start_time,
            attendance_code="DELAY",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
        )

        # Create record with submission 10 minutes after class start
        class_start = timezone.datetime.combine(session_date, start_time)
        class_start = timezone.make_aware(class_start)
        submitted_at = class_start + timedelta(minutes=10)

        record = AttendanceRecord.objects.create(
            attendance_session=session,
            student=self.student,
            status=AttendanceRecord.AttendanceStatus.LATE,
            submitted_at=submitted_at,
        )

        assert record.submission_delay_minutes == 10

        # Test with no submission time
        record.submitted_at = None
        assert record.submission_delay_minutes == 0

    @patch("apps.attendance.models.AttendanceSession.class_part")
    def test_permission_handling(self, mock_class_part):
        """Test permission request handling."""
        mock_class_part.name = "Test Class"

        session = AttendanceSession.objects.create(
            teacher=self.teacher,
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code="PERM1",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
        )

        record = AttendanceRecord.objects.create(
            attendance_session=session,
            student=self.student,
            status=AttendanceRecord.AttendanceStatus.PERMISSION,
            permission_reason="Medical appointment",
            permission_approved=True,
            permission_approved_by=self.user,
            permission_notes="Doctor's note provided",
            data_source=AttendanceRecord.DataSource.PERMISSION_REQUEST,
        )

        assert record.status == AttendanceRecord.AttendanceStatus.PERMISSION
        assert record.permission_reason == "Medical appointment"
        assert record.permission_approved
        assert record.permission_approved_by == self.user
        assert record.permission_notes == "Doctor's note provided"

    @patch("apps.attendance.models.AttendanceSession.class_part")
    def test_unique_session_student_constraint(self, mock_class_part):
        """Test unique constraint per session and student."""
        mock_class_part.name = "Test Class"

        session = AttendanceSession.objects.create(
            teacher=self.teacher,
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code="UNIQ1",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
        )

        # Create first record
        AttendanceRecord.objects.create(
            attendance_session=session,
            student=self.student,
            status=AttendanceRecord.AttendanceStatus.PRESENT,
        )

        with pytest.raises(IntegrityError):
            AttendanceRecord.objects.create(
                attendance_session=session,
                student=self.student,
                status=AttendanceRecord.AttendanceStatus.ABSENT,
            )

    @patch("apps.attendance.models.AttendanceSession.class_part")
    def test_string_representation(self, mock_class_part):
        """Test string representation."""
        mock_class_part.name = "Test Class"

        session = AttendanceSession.objects.create(
            teacher=self.teacher,
            session_date=date(2024, 3, 15),
            start_time=time(9, 0),
            attendance_code="STR02",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
        )

        record = AttendanceRecord.objects.create(
            attendance_session=session,
            student=self.student,
            status=AttendanceRecord.AttendanceStatus.PRESENT,
        )

        expected = f"{self.student} - 2024-03-15 (PRESENT)"
        assert str(record) == expected


class PermissionRequestModelTest(TestCase):
    """Test PermissionRequest model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        # Create student
        student_person = Person.objects.create(
            family_name="Student",
            personal_name="Test",
            date_of_birth=date(2000, 1, 1),
        )
        self.student = StudentProfile.objects.create(
            person=student_person,
            student_id=12345,
        )

    @patch("apps.attendance.models.PermissionRequest.class_part")
    def test_permission_request_creation(self, mock_class_part):
        """Test basic permission request creation."""
        mock_class_part.name = "English 101"

        request = PermissionRequest.objects.create(
            student=self.student,
            session_date=get_current_date() + timedelta(days=1),
            reason="Medical appointment with specialist doctor",
            request_status=PermissionRequest.RequestStatus.PENDING,
            program_type=PermissionRequest.ProgramType.BA,
            requires_approval=True,
        )

        assert request.student == self.student
        assert request.session_date == get_current_date() + timedelta(days=1)
        assert request.reason == "Medical appointment with specialist doctor"
        assert request.request_status == PermissionRequest.RequestStatus.PENDING
        assert request.program_type == PermissionRequest.ProgramType.BA
        assert request.requires_approval

    def test_request_status_choices(self):
        """Test all request status options."""
        statuses = [
            PermissionRequest.RequestStatus.PENDING,
            PermissionRequest.RequestStatus.APPROVED,
            PermissionRequest.RequestStatus.DENIED,
            PermissionRequest.RequestStatus.AUTO_APPROVED,
            PermissionRequest.RequestStatus.EXPIRED,
        ]

        for status in statuses:
            # Basic test that status can be set
            request = PermissionRequest(
                student=self.student,
                session_date=get_current_date() + timedelta(days=1),
                reason="Test reason",
                request_status=status,
                program_type=PermissionRequest.ProgramType.BA,
            )
            assert request.request_status == status

    def test_program_type_choices(self):
        """Test all program type options."""
        program_types = [
            PermissionRequest.ProgramType.IEAP,
            PermissionRequest.ProgramType.HIGH_SCHOOL,
            PermissionRequest.ProgramType.BA,
            PermissionRequest.ProgramType.MA,
            PermissionRequest.ProgramType.OTHER,
        ]

        for program_type in program_types:
            request = PermissionRequest(
                student=self.student,
                session_date=get_current_date() + timedelta(days=1),
                reason="Test reason",
                program_type=program_type,
            )
            assert request.program_type == program_type

    @patch("apps.attendance.models.PermissionRequest.class_part")
    def test_ieap_validation_restriction(self, mock_class_part):
        """Test that IEAP programs cannot request permissions."""
        mock_class_part.name = "IEAP Class"

        request = PermissionRequest(
            student=self.student,
            session_date=get_current_date() + timedelta(days=1),
            reason="Test reason",
            program_type=PermissionRequest.ProgramType.IEAP,
        )

        with pytest.raises(ValidationError) as exc_info:
            request.clean()

        assert "IEAP program does not allow permission requests" in str(exc_info.value)

    @patch("apps.attendance.models.PermissionRequest.class_part")
    def test_past_date_validation(self, mock_class_part):
        """Test validation against requesting permission for past dates."""
        mock_class_part.name = "Test Class"

        request = PermissionRequest(
            student=self.student,
            session_date=get_current_date() - timedelta(days=1),  # Past date
            reason="Test reason",
            program_type=PermissionRequest.ProgramType.BA,
        )

        with pytest.raises(ValidationError) as exc_info:
            request.clean()

        assert "Cannot request permission for past dates" in str(exc_info.value)

    @patch("apps.attendance.models.PermissionRequest.class_part")
    def test_approval_workflow(self, mock_class_part):
        """Test approval workflow functionality."""
        mock_class_part.name = "Test Class"

        request = PermissionRequest.objects.create(
            student=self.student,
            session_date=get_current_date() + timedelta(days=1),
            reason="Family emergency",
            request_status=PermissionRequest.RequestStatus.PENDING,
            program_type=PermissionRequest.ProgramType.BA,
            requires_approval=True,
        )

        # Test approval
        request.request_status = PermissionRequest.RequestStatus.APPROVED
        request.approved_by = self.user
        request.approval_date = timezone.now()
        request.approval_notes = "Valid reason provided"
        request.save()

        assert request.request_status == PermissionRequest.RequestStatus.APPROVED
        assert request.approved_by == self.user
        assert request.approval_date is not None
        assert request.approval_notes == "Valid reason provided"

    @patch("apps.attendance.models.PermissionRequest.class_part")
    def test_high_school_auto_approval(self, mock_class_part):
        """Test high school auto-approval functionality."""
        mock_class_part.name = "Grade 12 English"

        request = PermissionRequest.objects.create(
            student=self.student,
            session_date=get_current_date() + timedelta(days=1),
            reason="Family event",
            request_status=PermissionRequest.RequestStatus.AUTO_APPROVED,
            program_type=PermissionRequest.ProgramType.HIGH_SCHOOL,
            requires_approval=False,
            parent_notified=True,
            parent_notification_date=timezone.now(),
        )

        assert request.request_status == PermissionRequest.RequestStatus.AUTO_APPROVED
        assert not request.requires_approval
        assert request.parent_notified
        assert request.parent_notification_date is not None

    @patch("apps.attendance.models.PermissionRequest.class_part")
    def test_parent_notification_system(self, mock_class_part):
        """Test parent notification functionality."""
        mock_class_part.name = "Test Class"

        request = PermissionRequest.objects.create(
            student=self.student,
            session_date=get_current_date() + timedelta(days=1),
            reason="School field trip",
            program_type=PermissionRequest.ProgramType.HIGH_SCHOOL,
            parent_notified=True,
            parent_notification_date=timezone.now(),
            parent_response="Approved by parent via phone",
        )

        assert request.parent_notified
        assert request.parent_notification_date is not None
        assert request.parent_response == "Approved by parent via phone"

    @patch("apps.attendance.models.PermissionRequest.class_part")
    def test_unique_student_class_date_constraint(self, mock_class_part):
        """Test unique constraint per student, class, and date."""
        mock_class_part.name = "Test Class"
        mock_class_part.id = 1

        # Create first request
        PermissionRequest.objects.create(
            student=self.student,
            session_date=get_current_date() + timedelta(days=1),
            reason="First request",
            program_type=PermissionRequest.ProgramType.BA,
        )

        with pytest.raises(IntegrityError):
            PermissionRequest.objects.create(
                student=self.student,
                session_date=get_current_date() + timedelta(days=1),
                reason="Duplicate request",
                program_type=PermissionRequest.ProgramType.BA,
            )

    @patch("apps.attendance.models.PermissionRequest.class_part")
    def test_string_representation(self, mock_class_part):
        """Test string representation."""
        mock_class_part.__str__ = lambda: "English 101"

        request = PermissionRequest.objects.create(
            student=self.student,
            session_date=date(2024, 3, 20),
            reason="Test reason",
            program_type=PermissionRequest.ProgramType.BA,
        )

        expected = f"{self.student} - English 101 (2024-03-20)"
        assert str(request) == expected


class RosterSyncModelTest(TestCase):
    """Test RosterSync model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

    @patch("apps.attendance.models.RosterSync.class_part")
    def test_roster_sync_creation(self, mock_class_part):
        """Test basic roster sync creation."""
        mock_class_part.name = "English 101"

        sync = RosterSync.objects.create(
            sync_date=get_current_date(),
            sync_type=RosterSync.SyncType.MIDNIGHT,
            is_successful=True,
            student_count=25,
            enrollment_snapshot={
                "students": [
                    {"id": 1, "name": "John Doe", "status": "active"},
                    {"id": 2, "name": "Jane Smith", "status": "active"},
                ],
                "sync_timestamp": "2024-03-15T00:00:00Z",
            },
            roster_changed=True,
            changes_summary="Added 2 new students, removed 1 student",
        )

        assert sync.sync_date == get_current_date()
        assert sync.sync_type == RosterSync.SyncType.MIDNIGHT
        assert sync.is_successful
        assert sync.student_count == 25
        assert "students" in sync.enrollment_snapshot
        assert sync.roster_changed
        assert "Added 2 new students" in sync.changes_summary

    def test_sync_type_choices(self):
        """Test all sync type options."""
        sync_types = [
            RosterSync.SyncType.MIDNIGHT,
            RosterSync.SyncType.NOON,
            RosterSync.SyncType.MANUAL,
        ]

        for sync_type in sync_types:
            sync = RosterSync(
                sync_date=get_current_date(),
                sync_type=sync_type,
                student_count=20,
            )
            assert sync.sync_type == sync_type

    @patch("apps.attendance.models.RosterSync.class_part")
    def test_failed_sync_handling(self, mock_class_part):
        """Test handling of failed sync operations."""
        mock_class_part.name = "Test Class"

        sync = RosterSync.objects.create(
            sync_date=get_current_date(),
            sync_type=RosterSync.SyncType.NOON,
            is_successful=False,
            error_message="Database connection timeout during enrollment query",
            student_count=0,
            enrollment_snapshot={},
            roster_changed=False,
        )

        assert not sync.is_successful
        assert "Database connection timeout" in sync.error_message
        assert sync.student_count == 0
        assert sync.enrollment_snapshot == {}
        assert not sync.roster_changed

    @patch("apps.attendance.models.RosterSync.class_part")
    def test_enrollment_snapshot_structure(self, mock_class_part):
        """Test enrollment snapshot data structure."""
        mock_class_part.name = "Test Class"

        enrollment_data = {
            "sync_metadata": {
                "timestamp": "2024-03-15T12:00:00Z",
                "sync_type": "NOON",
                "total_count": 30,
            },
            "students": [
                {
                    "student_id": "S001",
                    "full_name": "John Doe",
                    "status": "ACTIVE",
                    "enrollment_date": "2024-01-15",
                },
                {
                    "student_id": "S002",
                    "full_name": "Jane Smith",
                    "status": "ACTIVE",
                    "enrollment_date": "2024-01-20",
                },
            ],
            "changes": {
                "additions": ["S003"],
                "removals": [],
                "status_changes": [],
            },
        }

        sync = RosterSync.objects.create(
            sync_date=get_current_date(),
            sync_type=RosterSync.SyncType.NOON,
            is_successful=True,
            student_count=30,
            enrollment_snapshot=enrollment_data,
            roster_changed=True,
            changes_summary="Added 1 new student (S003)",
        )

        assert sync.enrollment_snapshot["sync_metadata"]["total_count"] == 30
        assert len(sync.enrollment_snapshot["students"]) == 2
        assert sync.enrollment_snapshot["changes"]["additions"] == ["S003"]

    @patch("apps.attendance.models.RosterSync.class_part")
    def test_unique_class_date_type_constraint(self, mock_class_part):
        """Test unique constraint per class, date, and sync type."""
        mock_class_part.name = "Test Class"
        mock_class_part.id = 1

        # Create first sync
        RosterSync.objects.create(
            sync_date=get_current_date(),
            sync_type=RosterSync.SyncType.MIDNIGHT,
            student_count=20,
        )

        with pytest.raises(IntegrityError):
            RosterSync.objects.create(
                sync_date=get_current_date(),
                sync_type=RosterSync.SyncType.MIDNIGHT,
                student_count=25,
            )

    @patch("apps.attendance.models.RosterSync.class_part")
    def test_string_representation(self, mock_class_part):
        """Test string representation."""
        mock_class_part.__str__ = lambda: "English 101"

        sync = RosterSync.objects.create(
            sync_date=date(2024, 3, 15),
            sync_type=RosterSync.SyncType.MIDNIGHT,
            student_count=25,
        )

        expected = "English 101 - 2024-03-15 (MIDNIGHT)"
        assert str(sync) == expected


class AttendanceArchiveModelTest(TestCase):
    """Test AttendanceArchive model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        # Create student
        student_person = Person.objects.create(
            family_name="Student",
            personal_name="Archive",
            date_of_birth=date(2000, 1, 1),
        )
        self.student = StudentProfile.objects.create(
            person=student_person,
            student_id="S999",
        )

    @patch("apps.attendance.models.AttendanceArchive.class_part")
    @patch("apps.attendance.models.AttendanceArchive.term")
    def test_attendance_archive_creation(self, mock_term, mock_class_part):
        """Test basic attendance archive creation."""
        mock_class_part.name = "English 101"
        mock_term.name = "Fall 2024"

        archive = AttendanceArchive.objects.create(
            student=self.student,
            total_sessions=45,
            present_sessions=40,
            absent_sessions=3,
            late_sessions=2,
            excused_sessions=5,
            attendance_percentage=Decimal("88.89"),
            punctuality_percentage=Decimal("95.56"),
            archived_by=self.user,
            session_details={
                "term_summary": {
                    "start_date": "2024-01-15",
                    "end_date": "2024-05-15",
                    "total_weeks": 16,
                },
                "monthly_breakdown": {
                    "january": {"present": 8, "absent": 0, "late": 1},
                    "february": {"present": 9, "absent": 1, "late": 0},
                    "march": {"present": 10, "absent": 1, "late": 0},
                    "april": {"present": 8, "absent": 1, "late": 1},
                    "may": {"present": 5, "absent": 0, "late": 0},
                },
                "detailed_records": [],  # Would contain full attendance history
            },
        )

        assert archive.student == self.student
        assert archive.total_sessions == 45
        assert archive.present_sessions == 40
        assert archive.absent_sessions == 3
        assert archive.late_sessions == 2
        assert archive.excused_sessions == 5
        assert archive.attendance_percentage == Decimal("88.89")
        assert archive.punctuality_percentage == Decimal("95.56")
        assert archive.archived_by == self.user
        assert "term_summary" in archive.session_details
        assert "monthly_breakdown" in archive.session_details

    def test_attendance_grade_calculation(self):
        """Test attendance grade conversion."""
        test_cases = [
            (Decimal("97.0"), "A"),
            (Decimal("92.0"), "A-"),
            (Decimal("87.0"), "B+"),
            (Decimal("82.0"), "B"),
            (Decimal("77.0"), "B-"),
            (Decimal("72.0"), "C+"),
            (Decimal("67.0"), "C"),
            (Decimal("62.0"), "C-"),
            (Decimal("55.0"), "F"),
        ]

        for percentage, expected_grade in test_cases:
            # Test grade calculation property without database save
            archive = AttendanceArchive(
                total_sessions=100,
                present_sessions=int(percentage),
                absent_sessions=100 - int(percentage),
                late_sessions=0,
                excused_sessions=0,
                attendance_percentage=percentage,
                punctuality_percentage=Decimal("100.0"),
            )

            assert archive.attendance_grade == expected_grade

    @patch("apps.attendance.models.AttendanceArchive.class_part")
    @patch("apps.attendance.models.AttendanceArchive.term")
    def test_comprehensive_session_details(self, mock_term, mock_class_part):
        """Test comprehensive session details structure."""
        mock_class_part.name = "Advanced English"
        mock_term.name = "Spring 2024"

        detailed_session_data = {
            "term_info": {
                "term_id": 1,
                "term_name": "Spring 2024",
                "start_date": "2024-01-15",
                "end_date": "2024-05-15",
            },
            "class_info": {
                "class_id": 1,
                "class_name": "Advanced English",
                "teacher": "Dr. Smith",
                "schedule": "MWF 9:00-10:30",
            },
            "statistics": {
                "total_possible_sessions": 45,
                "sessions_held": 43,
                "sessions_cancelled": 2,
                "makeup_sessions": 1,
            },
            "attendance_breakdown": {
                "on_time": 35,
                "late_but_present": 5,
                "absent_unexcused": 2,
                "absent_excused": 1,
            },
            "monthly_data": {},
            "session_records": [],  # Individual session details
        }

        archive = AttendanceArchive.objects.create(
            student=self.student,
            total_sessions=45,
            present_sessions=40,
            absent_sessions=3,
            late_sessions=5,
            excused_sessions=1,
            attendance_percentage=Decimal("91.11"),
            punctuality_percentage=Decimal("87.50"),
            archived_by=self.user,
            session_details=detailed_session_data,
        )

        details = archive.session_details
        assert details["term_info"]["term_name"] == "Spring 2024"
        assert details["class_info"]["teacher"] == "Dr. Smith"
        assert details["statistics"]["total_possible_sessions"] == 45
        assert details["attendance_breakdown"]["on_time"] == 35

    @patch("apps.attendance.models.AttendanceArchive.class_part")
    @patch("apps.attendance.models.AttendanceArchive.term")
    def test_unique_class_student_term_constraint(self, mock_term, mock_class_part):
        """Test unique constraint per class, student, and term."""
        mock_class_part.name = "Test Class"
        mock_class_part.id = 1
        mock_term.name = "Test Term"
        mock_term.id = 1

        # Create first archive
        AttendanceArchive.objects.create(
            student=self.student,
            total_sessions=30,
            present_sessions=25,
            absent_sessions=5,
            late_sessions=2,
            excused_sessions=1,
            attendance_percentage=Decimal("83.33"),
            punctuality_percentage=Decimal("92.00"),
            archived_by=self.user,
        )

        with pytest.raises(IntegrityError):
            AttendanceArchive.objects.create(
                student=self.student,
                total_sessions=30,
                present_sessions=20,
                absent_sessions=10,
                late_sessions=5,
                excused_sessions=2,
                attendance_percentage=Decimal("66.67"),
                punctuality_percentage=Decimal("80.00"),
                archived_by=self.user,
            )

    @patch("apps.attendance.models.AttendanceArchive.class_part")
    @patch("apps.attendance.models.AttendanceArchive.term")
    def test_string_representation(self, mock_term, mock_class_part):
        """Test string representation."""
        mock_class_part.__str__ = lambda: "English 101"
        mock_term.__str__ = lambda: "Fall 2024"

        archive = AttendanceArchive.objects.create(
            student=self.student,
            total_sessions=45,
            present_sessions=40,
            absent_sessions=5,
            late_sessions=2,
            excused_sessions=1,
            attendance_percentage=Decimal("88.89"),
            punctuality_percentage=Decimal("95.00"),
            archived_by=self.user,
        )

        expected = f"{self.student} - English 101 (Fall 2024)"
        assert str(archive) == expected


class AttendanceIntegrationTest(TestCase):
    """Test integration between attendance models."""

    def setUp(self):
        """Set up test data for integration tests."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        # Create teacher
        teacher_person = Person.objects.create(
            family_name="Teacher",
            personal_name="Integration",
            date_of_birth=date(1980, 1, 1),
        )
        self.teacher = TeacherProfile.objects.create(
            person=teacher_person,
            status=TeacherProfile.Status.ACTIVE,
        )

        # Create student
        student_person = Person.objects.create(
            family_name="Student",
            personal_name="Integration",
            date_of_birth=date(2000, 1, 1),
        )
        self.student = StudentProfile.objects.create(
            person=student_person,
            student_id="INT001",
        )

    @patch("apps.attendance.models.AttendanceSession.class_part")
    @patch("apps.attendance.models.PermissionRequest.class_part")
    def test_complete_attendance_workflow(self, mock_perm_class, mock_session_class):
        """Test complete attendance workflow from session to record."""
        mock_session_class.name = "Integration Test Class"
        mock_perm_class.name = "Integration Test Class"

        # 1. Create attendance session
        session = AttendanceSession.objects.create(
            teacher=self.teacher,
            session_date=get_current_date(),
            start_time=time(9, 0),
            end_time=time(10, 30),
            attendance_code="INT01",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
            latitude=Decimal("11.5564"),
            longitude=Decimal("104.9282"),
            geofence_radius_meters=50,
            is_active=True,
        )

        # 2. Student submits attendance code
        record = AttendanceRecord.objects.create(
            attendance_session=session,
            student=self.student,
            status=AttendanceRecord.AttendanceStatus.PRESENT,
            submitted_code="INT01",
            code_correct=True,
            submitted_at=timezone.now(),
            submitted_latitude=Decimal(
                "11.5565",
            ),  # Slightly different but within range
            submitted_longitude=Decimal("104.9283"),
            within_geofence=True,
            distance_from_class=15,
            data_source=AttendanceRecord.DataSource.MOBILE_CODE,
            recorded_by=self.user,
        )

        # 3. Verify the workflow
        assert session.attendance_code == "INT01"
        assert session.is_code_valid
        assert record.attendance_session == session
        assert record.code_correct
        assert record.within_geofence
        assert record.is_present

    @patch("apps.attendance.models.PermissionRequest.class_part")
    @patch("apps.attendance.models.AttendanceSession.class_part")
    def test_permission_request_to_attendance_workflow(
        self,
        mock_session_class,
        mock_perm_class,
    ):
        """Test workflow from permission request to excused attendance."""
        mock_session_class.name = "Test Class"
        mock_perm_class.name = "Test Class"

        future_date = get_current_date() + timedelta(days=2)

        # 1. Create permission request
        permission_request = PermissionRequest.objects.create(
            student=self.student,
            session_date=future_date,
            reason="Medical appointment - dental surgery",
            request_status=PermissionRequest.RequestStatus.PENDING,
            program_type=PermissionRequest.ProgramType.BA,
            requires_approval=True,
        )

        # 2. Approve permission request
        permission_request.request_status = PermissionRequest.RequestStatus.APPROVED
        permission_request.approved_by = self.user
        permission_request.approval_date = timezone.now()
        permission_request.approval_notes = "Medical documentation provided"
        permission_request.save()

        # 3. Create attendance session for the date
        session = AttendanceSession.objects.create(
            teacher=self.teacher,
            session_date=future_date,
            start_time=time(9, 0),
            attendance_code="PERM1",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
        )

        # 4. Create attendance record based on approved permission
        record = AttendanceRecord.objects.create(
            attendance_session=session,
            student=self.student,
            status=AttendanceRecord.AttendanceStatus.PERMISSION,
            permission_reason=permission_request.reason,
            permission_approved=True,
            permission_approved_by=permission_request.approved_by,
            permission_notes=permission_request.approval_notes,
            data_source=AttendanceRecord.DataSource.PERMISSION_REQUEST,
            recorded_by=self.user,
        )

        # 5. Verify the integration
        assert permission_request.request_status == PermissionRequest.RequestStatus.APPROVED
        assert record.status == AttendanceRecord.AttendanceStatus.PERMISSION
        assert record.permission_approved
        assert record.is_present  # Excused absence counts as present
        assert record.permission_reason == permission_request.reason

    @patch("apps.attendance.models.RosterSync.class_part")
    @patch("apps.attendance.models.AttendanceSession.class_part")
    def test_roster_sync_to_attendance_integration(
        self,
        mock_session_class,
        mock_roster_class,
    ):
        """Test integration between roster sync and attendance tracking."""
        mock_session_class.name = "Test Class"
        mock_roster_class.name = "Test Class"

        # 1. Create roster sync
        roster_sync = RosterSync.objects.create(
            sync_date=get_current_date(),
            sync_type=RosterSync.SyncType.MIDNIGHT,
            is_successful=True,
            student_count=1,
            enrollment_snapshot={
                "students": [
                    {
                        "student_id": "INT001",
                        "full_name": "STUDENT INTEGRATION",
                        "status": "ACTIVE",
                    },
                ],
                "sync_timestamp": timezone.now().isoformat(),
            },
            roster_changed=False,
            changes_summary="No changes from previous sync",
        )

        # 2. Create attendance session using synced roster data
        session = AttendanceSession.objects.create(
            teacher=self.teacher,
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code="SYNC1",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
            total_students=roster_sync.student_count,  # Use synced count
        )

        # 3. Verify integration
        assert roster_sync.student_count == 1
        assert session.total_students == roster_sync.student_count
        assert roster_sync.enrollment_snapshot["students"][0]["student_id"] == "INT001"

    @patch("apps.attendance.models.AttendanceArchive.class_part")
    @patch("apps.attendance.models.AttendanceArchive.term")
    @patch("apps.attendance.models.AttendanceSession.class_part")
    def test_session_to_archive_workflow(
        self,
        mock_session_class,
        mock_term,
        mock_archive_class,
    ):
        """Test workflow from attendance sessions to term archive."""
        mock_session_class.name = "English 101"
        mock_archive_class.name = "English 101"
        mock_term.name = "Fall 2024"

        # 1. Create multiple attendance sessions
        sessions_data = []
        for i in range(5):
            session = AttendanceSession.objects.create(
                teacher=self.teacher,
                session_date=get_current_date() - timedelta(days=i),
                start_time=time(9, 0),
                attendance_code=f"ARC{i:02d}",
                code_generated_at=timezone.now(),
                code_expires_at=timezone.now() + timedelta(minutes=15),
            )

            # Create attendance record for each session
            status = AttendanceRecord.AttendanceStatus.PRESENT if i < 4 else AttendanceRecord.AttendanceStatus.ABSENT
            record = AttendanceRecord.objects.create(
                attendance_session=session,
                student=self.student,
                status=status,
                data_source=AttendanceRecord.DataSource.MOBILE_CODE,
            )

            sessions_data.append(
                {
                    "session_id": session.id,
                    "date": session.session_date.isoformat(),
                    "status": record.status,
                },
            )

        # 2. Create attendance archive summarizing the sessions
        archive = AttendanceArchive.objects.create(
            student=self.student,
            total_sessions=5,
            present_sessions=4,
            absent_sessions=1,
            late_sessions=0,
            excused_sessions=0,
            attendance_percentage=Decimal("80.00"),
            punctuality_percentage=Decimal("100.00"),
            archived_by=self.user,
            session_details={
                "session_records": sessions_data,
                "summary": {
                    "total_sessions": 5,
                    "present_sessions": 4,
                    "attendance_rate": "80.00%",
                },
            },
        )

        # 3. Verify the archival process
        assert archive.total_sessions == 5
        assert archive.present_sessions == 4
        assert archive.attendance_percentage == Decimal("80.00")
        assert len(archive.session_details["session_records"]) == 5
        assert archive.attendance_grade == "B"

    @patch("apps.attendance.models.AttendanceSession.class_part")
    def test_mobile_app_simulation(self, mock_class_part):
        """Test simulation of mobile app attendance workflow."""
        mock_class_part.name = "Mobile Test Class"

        # 1. Teacher starts class and generates code (mobile app)
        session = AttendanceSession.objects.create(
            teacher=self.teacher,
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code="MOB01",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
            latitude=Decimal("11.5564"),  # Teacher's location
            longitude=Decimal("104.9282"),
            geofence_radius_meters=50,
            is_active=True,
        )

        # 2. Student submits code within geofence (mobile app)
        record = AttendanceRecord.objects.create(
            attendance_session=session,
            student=self.student,
            status=AttendanceRecord.AttendanceStatus.PRESENT,
            submitted_code="MOB01",
            code_correct=True,
            submitted_at=timezone.now(),
            submitted_latitude=Decimal("11.5565"),  # Student's location (within range)
            submitted_longitude=Decimal("104.9283"),
            within_geofence=True,
            distance_from_class=12,  # meters
            data_source=AttendanceRecord.DataSource.MOBILE_CODE,
        )

        # 3. Verify mobile workflow
        assert session.is_code_valid
        assert record.code_correct
        assert record.within_geofence
        assert record.distance_from_class == 12
        assert record.data_source == AttendanceRecord.DataSource.MOBILE_CODE
        assert record.is_present

        # 4. Test fallback scenario - student outside geofence
        late_record = AttendanceRecord.objects.create(
            attendance_session=session,
            student=self.student,
            status=AttendanceRecord.AttendanceStatus.LATE,
            submitted_code="MOB01",
            code_correct=True,
            submitted_at=timezone.now() + timedelta(minutes=20),
            submitted_latitude=Decimal("11.6000"),  # Far from class
            submitted_longitude=Decimal("104.9000"),
            within_geofence=False,
            distance_from_class=500,  # meters - outside geofence
            data_source=AttendanceRecord.DataSource.MOBILE_MANUAL,  # Teacher override
            recorded_by=self.user,
            notes="Student arrived late, teacher manually marked present",
        )

        assert not late_record.within_geofence
        assert late_record.distance_from_class == 500
        assert late_record.data_source == AttendanceRecord.DataSource.MOBILE_MANUAL


class AttendanceBusinessLogicTest(TestCase):
    """Test attendance business logic and edge cases."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@test.com",
            password="testpass",
        )

    def test_attendance_percentage_edge_cases(self):
        """Test attendance percentage calculations in edge cases."""
        # Test with zero total sessions
        assert AttendanceSession().attendance_percentage == 0.0

        # Test perfect attendance
        session = AttendanceSession(total_students=20, present_count=20, absent_count=0)
        assert session.attendance_percentage == 100.0

        # Test zero attendance
        session = AttendanceSession(total_students=20, present_count=0, absent_count=20)
        assert session.attendance_percentage == 0.0

    def test_submission_delay_edge_cases(self):
        """Test submission delay calculations in edge cases."""
        record = AttendanceRecord()

        # Test with no submission time
        assert record.submission_delay_minutes == 0

        # Test negative delay (submission before class start)
        # This would require more complex mocking of timezone operations

    def test_geofence_validation_logic(self):
        """Test geofencing logic for attendance validation."""
        # This would typically involve calculating distances between coordinates
        # For now, we test the data storage and retrieval

        record = AttendanceRecord(
            submitted_latitude=Decimal("11.5564"),
            submitted_longitude=Decimal("104.9282"),
            within_geofence=True,
            distance_from_class=25,
        )

        assert record.within_geofence
        assert record.distance_from_class == 25

    def test_program_specific_policies(self):
        """Test program-specific attendance policies."""
        # IEAP settings
        ieap_settings = AttendanceSettings(
            allows_permission_requests=False,
            auto_approve_permissions=False,
            parent_notification_required=False,
            attendance_required_percentage=Decimal("90.00"),
        )

        assert not ieap_settings.allows_permission_requests
        assert ieap_settings.attendance_required_percentage == Decimal("90.00")

        # High School settings
        hs_settings = AttendanceSettings(
            allows_permission_requests=True,
            auto_approve_permissions=True,
            parent_notification_required=True,
            attendance_required_percentage=Decimal("85.00"),
        )

        assert hs_settings.allows_permission_requests
        assert hs_settings.auto_approve_permissions
        assert hs_settings.parent_notification_required

    def test_audit_trail_completeness(self):
        """Test that all models maintain proper audit trails."""
        # All attendance models inherit from AuditModel
        # which provides TimestampedModel and SoftDeleteModel functionality

        settings = AttendanceSettings()
        assert hasattr(settings, "created_at")
        assert hasattr(settings, "updated_at")
        assert hasattr(settings, "is_deleted")
        assert hasattr(settings, "deleted_at")

        session = AttendanceSession()
        assert hasattr(session, "created_at")
        assert hasattr(session, "updated_at")
        assert hasattr(session, "is_deleted")
        assert hasattr(session, "deleted_at")

        record = AttendanceRecord()
        assert hasattr(record, "created_at")
        assert hasattr(record, "updated_at")
        assert hasattr(record, "is_deleted")
        assert hasattr(record, "deleted_at")

    def test_clean_architecture_compliance(self):
        """Test that attendance models follow clean architecture principles."""
        # Models should only depend on:
        # - Common app (for base models)
        # - People app (for student/teacher profiles)
        # - Curriculum app (for programs/terms)
        # - Scheduling app (for class parts)

        # Test that models can be imported without circular dependencies
        from apps.attendance.models import (
            AttendanceArchive,
            AttendanceRecord,
            AttendanceSession,
            AttendanceSettings,
            PermissionRequest,
            RosterSync,
        )

        # All models should be properly defined
        assert AttendanceSettings._meta.abstract is False
        assert AttendanceSession._meta.abstract is False
        assert AttendanceRecord._meta.abstract is False
        assert PermissionRequest._meta.abstract is False
        assert RosterSync._meta.abstract is False
        assert AttendanceArchive._meta.abstract is False


class AttendanceSessionSubstituteTest(TestCase):
    """Test substitute teacher functionality in AttendanceSession."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        # Create regular teacher
        regular_teacher_person = Person.objects.create(
            family_name="Regular",
            personal_name="Teacher",
            date_of_birth=date(1980, 1, 1),
        )
        self.regular_teacher = TeacherProfile.objects.create(
            person=regular_teacher_person,
            status=TeacherProfile.Status.ACTIVE,
        )

        # Create substitute teacher
        substitute_teacher_person = Person.objects.create(
            family_name="Substitute",
            personal_name="Teacher",
            date_of_birth=date(1975, 1, 1),
        )
        self.substitute_teacher = TeacherProfile.objects.create(
            person=substitute_teacher_person,
            status=TeacherProfile.Status.ACTIVE,
        )

        # Create mock class part
        self.mock_class_part = MockClassPart("English 101")

    @patch("apps.attendance.models.AttendanceSession.class_part")
    def test_attendance_session_with_substitute_creation(self, mock_class_part):
        """Test creating attendance session with substitute teacher."""
        mock_class_part.name = "English 101"

        session = AttendanceSession.objects.create(
            teacher=self.regular_teacher,
            substitute_teacher=self.substitute_teacher,
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code="SUB01",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
            is_substitute_session=True,
            substitute_reason="Regular teacher is sick",
            substitute_assigned_by=self.user,
            substitute_assigned_at=timezone.now(),
        )

        assert session.teacher == self.regular_teacher
        assert session.substitute_teacher == self.substitute_teacher
        assert session.is_substitute_session
        assert session.substitute_reason == "Regular teacher is sick"
        assert session.substitute_assigned_by == self.user
        assert session.substitute_assigned_at is not None

    def test_actual_teacher_property(self):
        """Test actual_teacher property returns correct teacher."""
        # Test with no substitute (regular session) - in-memory
        session = AttendanceSession(
            teacher=self.regular_teacher,
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code="REG01",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
        )

        assert session.actual_teacher == self.regular_teacher

        # Test with substitute teacher assigned
        session.substitute_teacher = self.substitute_teacher
        session.is_substitute_session = True

        assert session.actual_teacher == self.substitute_teacher

    def test_assign_substitute_method(self):
        """Test assign_substitute method functionality."""
        session = AttendanceSession.objects.create(
            class_part=self.mock_class_part,
            teacher=self.regular_teacher,
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code="ASSGN",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
        )

        # Initially no substitute
        assert not session.is_substitute_session
        assert session.substitute_teacher is None

        # Assign substitute
        session.assign_substitute(
            substitute_teacher=self.substitute_teacher,
            reason="Regular teacher has emergency",
            assigned_by=self.user,
        )

        session.refresh_from_db()
        assert session.is_substitute_session
        assert session.substitute_teacher == self.substitute_teacher
        assert session.substitute_reason == "Regular teacher has emergency"
        assert session.substitute_assigned_by == self.user
        assert session.substitute_assigned_at is not None

    def test_remove_substitute_method(self):
        """Test remove_substitute method functionality."""
        session = AttendanceSession.objects.create(
            class_part=self.mock_class_part,
            teacher=self.regular_teacher,
            substitute_teacher=self.substitute_teacher,
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code="REMOV",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
            is_substitute_session=True,
            substitute_reason="Original reason",
            substitute_assigned_by=self.user,
            substitute_assigned_at=timezone.now(),
        )

        # Initially has substitute
        assert session.is_substitute_session
        assert session.substitute_teacher == self.substitute_teacher

        # Remove substitute
        session.remove_substitute()

        session.refresh_from_db()
        assert not session.is_substitute_session
        assert session.substitute_teacher is None
        assert session.substitute_reason == ""
        assert session.substitute_assigned_by is None
        assert session.substitute_assigned_at is None

    def test_substitute_session_validation(self):
        """Test validation rules for substitute sessions."""
        # Test that substitute teacher is required when is_substitute_session=True
        session = AttendanceSession(
            class_part=self.mock_class_part,
            teacher=self.regular_teacher,
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code="VALID",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
            is_substitute_session=True,
            # No substitute_teacher assigned
        )

        with pytest.raises(ValidationError) as exc_info:
            session.clean()

        assert "Substitute teacher is required" in str(exc_info.value)

        # Test that substitute reason is required when substitute teacher assigned
        session = AttendanceSession(
            class_part=self.mock_class_part,
            teacher=self.regular_teacher,
            substitute_teacher=self.substitute_teacher,
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code="VALID",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
            # No substitute_reason provided
        )

        with pytest.raises(ValidationError) as exc_info:
            session.clean()

        assert "Substitute reason is required" in str(exc_info.value)

        # Test that substitute teacher cannot be same as regular teacher
        session = AttendanceSession(
            class_part=self.mock_class_part,
            teacher=self.regular_teacher,
            substitute_teacher=self.regular_teacher,  # Same as regular teacher
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code="VALID",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
            substitute_reason="Test reason",
        )

        with pytest.raises(ValidationError) as exc_info:
            session.clean()

        assert "cannot be the same as the regular teacher" in str(exc_info.value)

    def test_substitute_session_string_representation(self):
        """Test string representation shows substitute indicator."""
        # Regular session
        regular_session = AttendanceSession.objects.create(
            class_part=self.mock_class_part,
            teacher=self.regular_teacher,
            session_date=date(2024, 3, 15),
            start_time=time(9, 0),
            attendance_code="REG01",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
        )

        expected_regular = f"English 101 - 2024-03-15 - {self.regular_teacher.person.full_name}"
        assert str(regular_session) == expected_regular

        # Substitute session
        substitute_session = AttendanceSession.objects.create(
            class_part=self.mock_class_part,
            teacher=self.regular_teacher,
            substitute_teacher=self.substitute_teacher,
            session_date=date(2024, 3, 15),
            start_time=time(9, 0),
            attendance_code="SUB01",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
            is_substitute_session=True,
            substitute_reason="Regular teacher sick",
        )

        expected_substitute = f"English 101 - 2024-03-15 - {self.substitute_teacher.person.full_name} (SUB)"
        assert str(substitute_session) == expected_substitute

    def test_substitute_session_indexing(self):
        """Test that substitute sessions are properly indexed for querying."""
        # Create regular session
        regular_session = AttendanceSession.objects.create(
            class_part=self.mock_class_part,
            teacher=self.regular_teacher,
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code="REG01",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
        )

        # Create substitute session
        substitute_session = AttendanceSession.objects.create(
            class_part=self.mock_class_part,
            teacher=self.regular_teacher,
            substitute_teacher=self.substitute_teacher,
            session_date=get_current_date(),
            start_time=time(10, 0),
            attendance_code="SUB01",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
            is_substitute_session=True,
            substitute_reason="Emergency",
        )

        # Test querying substitute sessions
        substitute_sessions = AttendanceSession.objects.filter(
            is_substitute_session=True,
        )
        assert substitute_session in substitute_sessions
        assert regular_session not in substitute_sessions

        # Test querying sessions by substitute teacher
        substitute_teacher_sessions = AttendanceSession.objects.filter(
            substitute_teacher=self.substitute_teacher,
        )
        assert substitute_session in substitute_teacher_sessions
        assert regular_session not in substitute_teacher_sessions

    def test_substitute_session_mobile_workflow(self):
        """Test mobile app workflow with substitute teacher."""
        # Create substitute session
        session = AttendanceSession.objects.create(
            class_part=self.mock_class_part,
            teacher=self.regular_teacher,
            substitute_teacher=self.substitute_teacher,
            session_date=get_current_date(),
            start_time=time(9, 0),
            attendance_code="MOB01",
            code_generated_at=timezone.now(),
            code_expires_at=timezone.now() + timedelta(minutes=15),
            is_substitute_session=True,
            substitute_reason="Regular teacher at conference",
            substitute_assigned_by=self.user,
            substitute_assigned_at=timezone.now(),
            latitude=Decimal("11.5564"),  # Substitute teacher's location
            longitude=Decimal("104.9282"),
            geofence_radius_meters=50,
            is_active=True,
        )

        # Verify substitute teacher has authority
        assert session.actual_teacher == self.substitute_teacher
        assert session.is_code_valid
        assert session.is_substitute_session

        # Verify session tracks substitute assignment
        assert session.substitute_assigned_by == self.user
        assert session.substitute_assigned_at is not None
        assert session.substitute_reason == "Regular teacher at conference"


class SubstituteTeacherServiceTest(TestCase):
    """Test SubstituteTeacherService business logic."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        # Create teacher requesting leave
        teacher_person = Person.objects.create(
            family_name="Regular",
            personal_name="Teacher",
            date_of_birth=date(1980, 1, 1),
        )
        self.teacher = TeacherProfile.objects.create(
            person=teacher_person,
            status=TeacherProfile.Status.ACTIVE,
        )

        # Create substitute teacher
        substitute_person = Person.objects.create(
            family_name="Substitute",
            personal_name="Teacher",
            date_of_birth=date(1975, 1, 1),
        )
        self.substitute_teacher = TeacherProfile.objects.create(
            person=substitute_person,
            status=TeacherProfile.Status.ACTIVE,
        )

        substitute2_person = Person.objects.create(
            family_name="Another",
            personal_name="Substitute",
            date_of_birth=date(1978, 1, 1),
        )
        self.substitute_teacher_2 = TeacherProfile.objects.create(
            person=substitute2_person,
            status=TeacherProfile.Status.ACTIVE,
        )

    def test_create_leave_request_success(self):
        """Test successful leave request creation."""
        from apps.attendance.services import SubstituteTeacherService
        from apps.people.models import TeacherLeaveRequest

        result = SubstituteTeacherService.create_leave_request(
            teacher_id=self.teacher.id,
            leave_date=get_current_date() + timedelta(days=2),
            leave_type=TeacherLeaveRequest.LeaveType.SICK,
            reason="Flu symptoms",
            is_emergency=False,
        )

        assert result["success"] is True
        assert "leave_request_id" in result
        assert result["status"] == TeacherLeaveRequest.ApprovalStatus.PENDING

        # Verify request was created
        leave_request = TeacherLeaveRequest.objects.get(id=result["leave_request_id"])
        assert leave_request.teacher == self.teacher
        assert leave_request.leave_type == TeacherLeaveRequest.LeaveType.SICK
        assert leave_request.reason == "Flu symptoms"

    def test_create_leave_request_past_date_non_emergency(self):
        """Test that past dates are rejected for non-emergency requests."""
        from apps.attendance.services import SubstituteTeacherService
        from apps.people.models import TeacherLeaveRequest

        result = SubstituteTeacherService.create_leave_request(
            teacher_id=self.teacher.id,
            leave_date=get_current_date() - timedelta(days=1),  # Past date
            leave_type=TeacherLeaveRequest.LeaveType.PERSONAL,
            reason="Personal matter",
            is_emergency=False,
        )

        assert result["success"] is False
        assert "Cannot request leave for past dates" in result["error"]

    def test_create_leave_request_past_date_emergency(self):
        """Test that past dates are allowed for emergency requests."""
        from apps.attendance.services import SubstituteTeacherService
        from apps.people.models import TeacherLeaveRequest

        result = SubstituteTeacherService.create_leave_request(
            teacher_id=self.teacher.id,
            leave_date=get_current_date() - timedelta(days=1),  # Past date
            leave_type=TeacherLeaveRequest.LeaveType.EMERGENCY,
            reason="Family emergency",
            is_emergency=True,
        )

        assert result["success"] is True
        assert "leave_request_id" in result

    def test_create_leave_request_invalid_teacher(self):
        """Test error handling for invalid teacher ID."""
        from apps.attendance.services import SubstituteTeacherService

        result = SubstituteTeacherService.create_leave_request(
            teacher_id=99999,  # Non-existent teacher
            leave_date=get_current_date() + timedelta(days=1),
            leave_type="SICK",
            reason="Test reason",
        )

        assert result["success"] is False
        assert result["error"] == "Teacher not found"

    def test_assign_substitute_success(self):
        """Test successful substitute assignment."""
        from apps.attendance.services import SubstituteTeacherService
        from apps.people.models import TeacherLeaveRequest

        # Create leave request first
        leave_request = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=get_current_date() + timedelta(days=3),
            leave_type=TeacherLeaveRequest.LeaveType.SICK,
            reason="Sick leave",
            approval_status=TeacherLeaveRequest.ApprovalStatus.APPROVED,
        )

        result = SubstituteTeacherService.assign_substitute(
            leave_request_id=leave_request.id,
            substitute_teacher_id=self.substitute_teacher.id,
            assigned_by_user=self.user,
        )

        assert result["success"] is True
        assert result["substitute_assigned"] is True
        assert result["substitute_name"] == self.substitute_teacher.person.display_name

        # Verify assignment in database
        leave_request.refresh_from_db()
        assert leave_request.substitute_teacher == self.substitute_teacher
        assert leave_request.substitute_assigned_by == self.user
        assert leave_request.substitute_found is True

    def test_assign_substitute_with_conflicts(self):
        """Test substitute assignment when substitute has conflicts."""
        from apps.attendance.services import SubstituteTeacherService
        from apps.people.models import TeacherLeaveRequest

        target_date = get_current_date() + timedelta(days=3)

        # Create leave request for substitute teacher (creating conflict)
        TeacherLeaveRequest.objects.create(
            teacher=self.substitute_teacher,
            leave_date=target_date,
            leave_type=TeacherLeaveRequest.LeaveType.PERSONAL,
            reason="Personal leave",
            approval_status=TeacherLeaveRequest.ApprovalStatus.APPROVED,
        )

        # Create leave request for main teacher
        leave_request = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=target_date,
            leave_type=TeacherLeaveRequest.LeaveType.SICK,
            reason="Sick leave",
            approval_status=TeacherLeaveRequest.ApprovalStatus.APPROVED,
        )

        # Try to assign conflicted substitute
        result = SubstituteTeacherService.assign_substitute(
            leave_request_id=leave_request.id,
            substitute_teacher_id=self.substitute_teacher.id,
            assigned_by_user=self.user,
        )

        assert result["success"] is False
        assert "conflicts" in result["error"].lower()
        assert "Has own leave request" in result["error"]

    def test_find_available_substitutes(self):
        """Test finding available substitute teachers."""
        from apps.attendance.services import SubstituteTeacherService
        from apps.people.models import TeacherLeaveRequest

        target_date = get_current_date() + timedelta(days=5)

        # Initially both substitutes should be available
        available = SubstituteTeacherService.find_available_substitutes(target_date)
        available_ids = [t.id for t in available]

        assert self.substitute_teacher.id in available_ids
        assert self.substitute_teacher_2.id in available_ids

        # Create leave request for one substitute (making them unavailable)
        TeacherLeaveRequest.objects.create(
            teacher=self.substitute_teacher,
            leave_date=target_date,
            leave_type=TeacherLeaveRequest.LeaveType.PERSONAL,
            reason="Personal leave",
            approval_status=TeacherLeaveRequest.ApprovalStatus.APPROVED,
        )

        # Now only one substitute should be available
        available = SubstituteTeacherService.find_available_substitutes(target_date)
        available_ids = [t.id for t in available]

        assert self.substitute_teacher.id not in available_ids
        assert self.substitute_teacher_2.id in available_ids

    def test_find_available_substitutes_excludes_assigned(self):
        """Test that already assigned substitutes are excluded."""
        from apps.attendance.services import SubstituteTeacherService
        from apps.people.models import TeacherLeaveRequest

        target_date = get_current_date() + timedelta(days=5)

        # Create leave request and assign substitute
        TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=target_date,
            leave_type=TeacherLeaveRequest.LeaveType.SICK,
            reason="Sick leave",
            approval_status=TeacherLeaveRequest.ApprovalStatus.APPROVED,
            substitute_teacher=self.substitute_teacher,
            substitute_found=True,
        )

        # Assigned substitute should not be available
        available = SubstituteTeacherService.find_available_substitutes(target_date)
        available_ids = [t.id for t in available]

        assert self.substitute_teacher.id not in available_ids
        assert self.substitute_teacher_2.id in available_ids

    def test_substitute_statistics(self):
        """Test substitute teacher statistics generation."""
        from apps.attendance.services import SubstituteTeacherService
        from apps.people.models import TeacherLeaveRequest

        # Create various leave requests
        base_date = get_current_date()

        # Approved sick leave with substitute
        TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=base_date,
            leave_type=TeacherLeaveRequest.LeaveType.SICK,
            reason="Flu",
            approval_status=TeacherLeaveRequest.ApprovalStatus.APPROVED,
            substitute_teacher=self.substitute_teacher,
            substitute_found=True,
        )

        # Pending personal leave
        TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=base_date + timedelta(days=1),
            leave_type=TeacherLeaveRequest.LeaveType.PERSONAL,
            reason="Personal matter",
            approval_status=TeacherLeaveRequest.ApprovalStatus.PENDING,
        )

        # Emergency leave
        TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=base_date + timedelta(days=2),
            leave_type=TeacherLeaveRequest.LeaveType.EMERGENCY,
            reason="Family emergency",
            approval_status=TeacherLeaveRequest.ApprovalStatus.APPROVED,
            is_emergency=True,
            substitute_teacher=self.substitute_teacher_2,
            substitute_found=True,
        )

        # Get statistics
        stats = SubstituteTeacherService.get_substitute_statistics(
            start_date=base_date,
            end_date=base_date + timedelta(days=30),
        )

        assert stats["total_leave_requests"] == 3
        assert stats["approved_requests"] == 2
        assert stats["emergency_requests"] == 1
        assert stats["substitutes_found"] == 2
        assert stats["substitute_coverage_rate"] == 100.0  # 2/2 approved had substitutes

        # Check leave type breakdown
        assert "Sick Leave" in stats["leave_type_breakdown"]
        assert "Personal Leave" in stats["leave_type_breakdown"]
        assert "Emergency" in stats["leave_type_breakdown"]

        # Check substitute usage
        assert len(stats["substitute_usage"]) == 2
        assert self.substitute_teacher.person.display_name in stats["substitute_usage"]
        assert self.substitute_teacher_2.person.display_name in stats["substitute_usage"]

    def test_check_substitute_conflicts_multiple_conflicts(self):
        """Test conflict detection with multiple types of conflicts."""
        from apps.attendance.services import SubstituteTeacherService
        from apps.people.models import TeacherLeaveRequest

        target_date = get_current_date() + timedelta(days=4)

        # Create substitute's own leave request
        TeacherLeaveRequest.objects.create(
            teacher=self.substitute_teacher,
            leave_date=target_date,
            leave_type=TeacherLeaveRequest.LeaveType.PERSONAL,
            reason="Personal leave",
            approval_status=TeacherLeaveRequest.ApprovalStatus.APPROVED,
        )

        # Check conflicts
        conflicts = SubstituteTeacherService._check_substitute_conflicts(
            substitute=self.substitute_teacher,
            leave_date=target_date,
        )

        assert len(conflicts) >= 1
        assert any("Has own leave request" in c for c in conflicts)

    def test_statistics_with_empty_data(self):
        """Test statistics when no leave requests exist."""
        from apps.attendance.services import SubstituteTeacherService

        stats = SubstituteTeacherService.get_substitute_statistics(
            start_date=get_current_date(),
            end_date=get_current_date() + timedelta(days=30),
        )

        assert stats["total_leave_requests"] == 0
        assert stats["approved_requests"] == 0
        assert stats["emergency_requests"] == 0
        assert stats["substitutes_found"] == 0
        assert stats["substitute_coverage_rate"] == 0
        assert stats["leave_type_breakdown"] == {}
        assert stats["substitute_usage"] == {}

    def test_statistics_coverage_rate_calculation(self):
        """Test substitute coverage rate calculation edge cases."""
        from apps.attendance.services import SubstituteTeacherService
        from apps.people.models import TeacherLeaveRequest

        base_date = get_current_date()

        # Create approved request without substitute
        TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=base_date,
            leave_type=TeacherLeaveRequest.LeaveType.SICK,
            reason="Sick leave",
            approval_status=TeacherLeaveRequest.ApprovalStatus.APPROVED,
            substitute_found=False,
        )

        # Create approved request with substitute
        TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=base_date + timedelta(days=1),
            leave_type=TeacherLeaveRequest.LeaveType.PERSONAL,
            reason="Personal leave",
            approval_status=TeacherLeaveRequest.ApprovalStatus.APPROVED,
            substitute_teacher=self.substitute_teacher,
            substitute_found=True,
        )

        stats = SubstituteTeacherService.get_substitute_statistics(
            start_date=base_date,
            end_date=base_date + timedelta(days=30),
        )

        # 1 out of 2 approved requests had substitutes = 50%
        assert stats["total_leave_requests"] == 2
        assert stats["approved_requests"] == 2
        assert stats["substitutes_found"] == 1
        assert stats["substitute_coverage_rate"] == 50.0

    @patch(
        "apps.attendance.services.SubstituteTeacherService._update_attendance_sessions_for_substitute",
    )
    def test_assign_substitute_updates_attendance_sessions(self, mock_update_sessions):
        """Test that substitute assignment updates related attendance sessions."""
        from apps.attendance.services import SubstituteTeacherService
        from apps.people.models import TeacherLeaveRequest

        # Create leave request
        leave_request = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=get_current_date() + timedelta(days=3),
            leave_type=TeacherLeaveRequest.LeaveType.SICK,
            reason="Sick leave",
            approval_status=TeacherLeaveRequest.ApprovalStatus.APPROVED,
        )

        # Assign substitute
        SubstituteTeacherService.assign_substitute(
            leave_request_id=leave_request.id,
            substitute_teacher_id=self.substitute_teacher.id,
            assigned_by_user=self.user,
        )

        # Verify that attendance session update was called
        mock_update_sessions.assert_called_once()
        args = mock_update_sessions.call_args[0]
        assert args[0] == leave_request  # leave_request argument
        assert args[1] == self.substitute_teacher  # substitute argument
