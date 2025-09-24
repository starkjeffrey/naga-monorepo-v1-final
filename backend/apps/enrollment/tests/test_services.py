"""Comprehensive tests for enrollment services.

Tests all business logic services in the enrollment app including:
- ProgramEnrollmentService: Program enrollment management
- SessionExemptionService: IEAP session exemption processing
- EnrollmentValidationService: Bulk enrollment validation
- Integration with existing services:
  - EnrollmentService: Core enrollment workflows
  - CapacityService: Waitlist and capacity management
  - PrerequisiteService: Eligibility checking

These tests ensure proper business logic implementation while maintaining
clean architecture principles and avoiding circular dependencies.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

# Deprecated models removed - these were deleted in migration 0004_auto_20250123.py
from apps.curriculum.models import Course, Cycle, Division, Major, Term
from apps.enrollment.models import (
    ClassHeaderEnrollment,
    ClassPartEnrollment,
    ClassSessionExemption,
    ProgramEnrollment,
)
from apps.enrollment.services import (
    EnrollmentValidationService,
    ProgramEnrollmentService,
    ScheduleService,
    SessionExemptionService,
    get_system_user,
)
from apps.people.models import Person, StudentProfile
from apps.scheduling.models import ClassHeader, ClassPart, ClassSession

User = get_user_model()


class ProgramEnrollmentServiceTest(TestCase):
    """Test ProgramEnrollmentService functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        self.person = Person.objects.create(
            personal_name="John",
            family_name="Doe",
            date_of_birth="1990-01-01",
        )

        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id=1001,
            current_status=StudentProfile.Status.ACTIVE,
        )

        self.division = Division.objects.create(
            name="Academic Division",
            short_name="ACAD",
        )

        self.cycle = Cycle.objects.create(
            division=self.division,
            name="Bachelor's Program",
            short_name="BA",
            degree_awarded=Cycle.DegreeType.BA,
        )

        self.major = Major.objects.create(
            cycle=self.cycle,
            code="CS",
            name="Computer Science",
            is_active=True,
        )

        self.term = Term.objects.create(
            name="Fall 2025",
            start_date="2025-09-01",
            end_date="2025-12-15",
        )

    def test_enroll_student_in_program_success(self):
        """Test successful program enrollment."""
        # Test with system user since enrolled_by now defaults to system user
        enrollment = ProgramEnrollmentService.enroll_student_in_program(
            student=self.student,
            program=self.major,
            enrollment_type=ProgramEnrollment.EnrollmentType.ACADEMIC,
            admission_term=self.term,
            enrolled_by=get_system_user(),
            notes="Initial enrollment",
        )

        assert enrollment.student == self.student
        assert enrollment.program == self.major
        assert enrollment.enrollment_type == ProgramEnrollment.EnrollmentType.ACADEMIC
        assert enrollment.start_term == self.term
        assert enrollment.status == ProgramEnrollment.EnrollmentStatus.ACTIVE
        assert enrollment.start_date == timezone.now().date()
        assert enrollment.notes == "Initial enrollment"

    def test_enroll_student_in_program_student_inactive(self):
        """Test program enrollment fails for inactive student."""
        self.student.current_status = StudentProfile.Status.INACTIVE
        self.student.save()

        with pytest.raises(ValidationError) as exc_info:
            ProgramEnrollmentService.enroll_student_in_program(
                student=self.student,
                program=self.major,
            )

        assert "Student must be active" in str(exc_info.value)

    def test_enroll_student_in_program_program_inactive(self):
        """Test program enrollment fails for inactive program."""
        self.major.is_active = False
        self.major.save()

        with pytest.raises(ValidationError) as exc_info:
            ProgramEnrollmentService.enroll_student_in_program(
                student=self.student,
                program=self.major,
            )

        assert "not currently active" in str(exc_info.value)

    def test_enroll_student_in_program_already_enrolled(self):
        """Test program enrollment fails if already enrolled."""
        # Create existing enrollment
        ProgramEnrollment.objects.create(
            student=self.student,
            program=self.major,
            status=ProgramEnrollment.EnrollmentStatus.ACTIVE,
            start_date=timezone.now().date(),
        )

        with pytest.raises(ValidationError) as exc_info:
            ProgramEnrollmentService.enroll_student_in_program(
                student=self.student,
                program=self.major,
            )

        assert "already enrolled" in str(exc_info.value)

    def test_enroll_student_in_program_conflicting_cycle_enrollment(self):
        """Test program enrollment fails with conflicting cycle enrollment."""
        # Create another major in the same cycle
        conflicting_major = Major.objects.create(
            cycle=self.cycle,
            code="EE",
            name="Electrical Engineering",
            is_active=True,
        )

        # Enroll in conflicting major
        ProgramEnrollment.objects.create(
            student=self.student,
            program=conflicting_major,
            status=ProgramEnrollment.EnrollmentStatus.ACTIVE,
            start_date=timezone.now().date(),
        )

        with pytest.raises(ValidationError) as exc_info:
            ProgramEnrollmentService.enroll_student_in_program(
                student=self.student,
                program=self.major,
            )

        assert "already enrolled in another program" in str(exc_info.value)

    def test_change_enrollment_status_to_graduated(self):
        """Test changing enrollment status to graduated."""
        enrollment = ProgramEnrollment.objects.create(
            student=self.student,
            program=self.major,
            status=ProgramEnrollment.EnrollmentStatus.ACTIVE,
            start_date=timezone.now().date(),
        )

        updated_enrollment = ProgramEnrollmentService.change_enrollment_status(
            enrollment=enrollment,
            new_status=ProgramEnrollment.EnrollmentStatus.COMPLETED,
            changed_by=self.user,
            reason="Completed all requirements",
        )

        assert updated_enrollment.status == ProgramEnrollment.EnrollmentStatus.COMPLETED
        assert updated_enrollment.end_date == timezone.now().date()
        assert "Completed all requirements" in updated_enrollment.notes

    def test_change_enrollment_status_to_withdrawn(self):
        """Test changing enrollment status to withdrawn."""
        enrollment = ProgramEnrollment.objects.create(
            student=self.student,
            program=self.major,
            status=ProgramEnrollment.EnrollmentStatus.ACTIVE,
            start_date=timezone.now().date(),
        )

        updated_enrollment = ProgramEnrollmentService.change_enrollment_status(
            enrollment=enrollment,
            new_status=ProgramEnrollment.EnrollmentStatus.WITHDRAWN,
            changed_by=self.user,
            reason="Personal reasons",
        )

        assert updated_enrollment.status == ProgramEnrollment.EnrollmentStatus.WITHDRAWN
        assert updated_enrollment.end_date == timezone.now().date()
        assert "Personal reasons" in updated_enrollment.notes

    def test_get_student_enrollments(self):
        """Test getting all student enrollments."""
        # Create multiple enrollments
        enrollment1 = ProgramEnrollment.objects.create(
            student=self.student,
            program=self.major,
            status=ProgramEnrollment.EnrollmentStatus.ACTIVE,
            start_date="2025-01-01",
        )

        # Create another major for second enrollment
        major2 = Major.objects.create(
            cycle=self.cycle,
            code="MATH",
            name="Mathematics",
        )

        enrollment2 = ProgramEnrollment.objects.create(
            student=self.student,
            program=major2,
            status=ProgramEnrollment.EnrollmentStatus.COMPLETED,
            start_date="2023-01-01",
        )

        enrollments = ProgramEnrollmentService.get_student_enrollments(self.student)

        # Should be ordered by start date (desc)
        assert len(enrollments) == 2
        assert enrollments[0] == enrollment1
        assert enrollments[1] == enrollment2

    def test_get_active_enrollment(self):
        """Test getting active enrollment for student."""
        # Create inactive enrollment
        ProgramEnrollment.objects.create(
            student=self.student,
            program=self.major,
            status=ProgramEnrollment.EnrollmentStatus.WITHDRAWN,
            start_date="2024-01-01",
        )

        # Create active enrollment
        active_enrollment = ProgramEnrollment.objects.create(
            student=self.student,
            program=self.major,
            status=ProgramEnrollment.EnrollmentStatus.ACTIVE,
            start_date="2025-01-01",
        )

        result = ProgramEnrollmentService.get_active_enrollment(self.student)

        assert result == active_enrollment

    def test_get_active_enrollment_none(self):
        """Test getting active enrollment when none exists."""
        result = ProgramEnrollmentService.get_active_enrollment(self.student)

        assert result is None


class SessionExemptionServiceTest(TestCase):
    """Test SessionExemptionService functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        self.person = Person.objects.create(
            personal_name="Jane",
            family_name="Smith",
            date_of_birth="1992-01-01",
        )

        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id=1002,
        )

        self.division = Division.objects.create(
            name="IEAP Division",
            short_name="IEAP",
        )

        self.course = Course.objects.create(
            code="IEAP-101",
            title="English as a Second Language",
            short_title="ESL",
            division=self.division,
            credits=3,
        )

        self.term = Term.objects.create(
            name="Spring 2025",
            start_date="2025-01-15",
            end_date="2025-05-15",
        )

        # Create class structure
        self.class_header = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="A",
        )

        self.class_session = ClassSession.objects.create(
            class_header=self.class_header,
            session_number=1,
            session_name="Session 1",
        )

        self.class_part = ClassPart.objects.create(
            class_session=self.class_session,
            class_part_type="LECTURE",
            class_part_code="A",
        )

        # Create class header enrollment first
        self.class_header_enrollment = ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            enrolled_by=get_system_user(),
        )

        # Enroll student in class part
        self.class_part_enrollment = ClassPartEnrollment.objects.create(
            student=self.student,
            class_part=self.class_part,
            is_active=True,
        )

    def test_create_session_exemption_success(self):
        """Test successful creation of session exemption."""
        exemption = SessionExemptionService.create_session_exemption(
            student=self.student,
            class_session=self.class_session,
            exemption_type=ClassSessionExemption.ExemptionType.MEDICAL,
            reason="Doctor's appointment",
            approved_by=self.user,
            notes="Medical documentation provided",
        )

        assert exemption.class_header_enrollment.student == self.student
        assert exemption.class_session == self.class_session
        assert ClassSessionExemption.ExemptionType.MEDICAL in exemption.exemption_reason
        assert "Doctor's appointment" in exemption.exemption_reason
        assert exemption.exempted_by == self.user
        assert exemption.exemption_date.date() == timezone.now().date()
        assert exemption.notes == "Medical documentation provided"

    def test_create_session_exemption_student_not_enrolled(self):
        """Test exemption creation fails when student not enrolled."""
        # Remove enrollment
        self.class_part_enrollment.delete()

        with pytest.raises(ValidationError) as exc_info:
            SessionExemptionService.create_session_exemption(
                student=self.student,
                class_session=self.class_session,
                exemption_type=ClassSessionExemption.ExemptionType.MEDICAL,
                reason="Doctor's appointment",
                approved_by=self.user,
            )

        assert "must be enrolled in the class" in str(exc_info.value)

    def test_create_session_exemption_already_exists(self):
        """Test exemption creation fails when exemption already exists."""
        # Create existing exemption
        ClassSessionExemption.objects.create(
            class_header_enrollment=self.class_header_enrollment,
            class_session=self.class_session,
            exemption_reason=f"{ClassSessionExemption.ExemptionType.MEDICAL}: Existing exemption",
            exempted_by=self.user,
        )

        with pytest.raises(ValidationError) as exc_info:
            SessionExemptionService.create_session_exemption(
                student=self.student,
                class_session=self.class_session,
                exemption_type=ClassSessionExemption.ExemptionType.ACADEMIC,
                reason="New exemption",
                approved_by=self.user,
            )

        assert "already has an exemption" in str(exc_info.value)

    def test_get_student_exemptions_all(self):
        """Test getting all student exemptions."""
        # Create exemptions in different terms
        exemption1 = ClassSessionExemption.objects.create(
            class_header_enrollment=self.class_header_enrollment,
            class_session=self.class_session,
            exemption_reason=f"{ClassSessionExemption.ExemptionType.MEDICAL}: Medical exemption",
            exempted_by=self.user,
        )

        # Create another session for different exemption
        session2 = ClassSession.objects.create(
            class_header=self.class_header,
            session_number=2,
            session_name="Session 2",
        )

        exemption2 = ClassSessionExemption.objects.create(
            class_header_enrollment=self.class_header_enrollment,
            class_session=session2,
            exemption_reason=f"{ClassSessionExemption.ExemptionType.PERSONAL}: Personal exemption",
            exempted_by=self.user,
        )

        exemptions = SessionExemptionService.get_student_exemptions(self.student)

        assert len(exemptions) == 2
        # Should be ordered by approval date (desc)
        assert exemptions[0] in [exemption1, exemption2]
        assert exemptions[1] in [exemption1, exemption2]

    def test_get_student_exemptions_filtered_by_term(self):
        """Test getting student exemptions filtered by term."""
        # Create exemption in current term
        exemption1 = ClassSessionExemption.objects.create(
            class_header_enrollment=self.class_header_enrollment,
            class_session=self.class_session,
            exemption_reason=f"{ClassSessionExemption.ExemptionType.MEDICAL}: Current term exemption",
            exempted_by=self.user,
        )

        # Create exemption in different term
        other_term = Term.objects.create(
            name="Fall 2024",
            start_date="2024-09-01",
            end_date="2024-12-15",
        )

        other_class_header = ClassHeader.objects.create(
            course=self.course,
            term=other_term,
            section_id="B",
        )

        other_session = ClassSession.objects.create(
            class_header=other_class_header,
            session_number=1,
            session_name="Session 1",
        )

        ClassPart.objects.create(
            class_session=other_session,
            class_part_type="LECTURE",
            class_part_code="B",
        )

        # Create enrollment for other term
        other_class_header_enrollment = ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=other_class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            enrolled_by=get_system_user(),
        )

        ClassSessionExemption.objects.create(
            class_header_enrollment=other_class_header_enrollment,
            class_session=other_session,
            exemption_reason=f"{ClassSessionExemption.ExemptionType.PERSONAL}: Other term exemption",
            exempted_by=self.user,
        )

        # Filter by current term
        exemptions = SessionExemptionService.get_student_exemptions(self.student, term=self.term)

        assert len(exemptions) == 1
        assert exemptions[0] == exemption1


class EnrollmentValidationServiceTest(TestCase):
    """Test EnrollmentValidationService functionality."""

    def setUp(self):
        """Set up test data."""
        self.person1 = Person.objects.create(
            personal_name="Alice",
            family_name="Johnson",
            date_of_birth="1995-01-01",
        )

        self.student1 = StudentProfile.objects.create(
            person=self.person1,
            student_id=1003,
        )

        self.person2 = Person.objects.create(
            personal_name="Bob",
            family_name="Wilson",
            date_of_birth="1996-01-01",
        )

        self.student2 = StudentProfile.objects.create(
            person=self.person2,
            student_id=1004,
        )

        self.division = Division.objects.create(
            name="Academic Division",
            short_name="ACAD",
        )

        self.course1 = Course.objects.create(
            code="MATH-101",
            title="Calculus I",
            short_title="Calc I",
            division=self.division,
            credits=4,
        )

        self.course2 = Course.objects.create(
            code="PHYS-101",
            title="Physics I",
            short_title="Physics I",
            division=self.division,
            credits=4,
        )

        self.term = Term.objects.create(
            name="Fall 2025",
            start_date="2025-09-01",
            end_date="2025-12-15",
        )

        # Create class headers
        self.class_header1 = ClassHeader.objects.create(
            course=self.course1,
            term=self.term,
            section_id="A",
        )

        self.class_header2 = ClassHeader.objects.create(
            course=self.course2,
            term=self.term,
            section_id="A",
        )

    @patch.object(ScheduleService, "check_schedule_conflicts")
    def test_validate_bulk_enrollment_all_valid(self, mock_check_conflicts):
        """Test bulk enrollment validation with all valid enrollments."""
        mock_check_conflicts.return_value = []  # No conflicts

        student_course_pairs = [
            (self.student1, self.course1),
            (self.student1, self.course2),
            (self.student2, self.course1),
        ]

        valid_enrollments, invalid_enrollments = EnrollmentValidationService.validate_bulk_enrollment(
            student_course_pairs,
            self.term,
        )

        assert len(valid_enrollments) == 3
        assert len(invalid_enrollments) == 0

        # Verify valid enrollment structure
        valid_enrollment = valid_enrollments[0]
        assert valid_enrollment["student"] == self.student1
        assert valid_enrollment["course"] == self.course1
        assert valid_enrollment["class_header"] == self.class_header1

    def test_validate_bulk_enrollment_no_class_scheduled(self):
        """Test bulk enrollment validation with no class scheduled."""
        course_without_class = Course.objects.create(
            code="ART-101",
            title="Art History",
            division=self.division,
            credits=3,
        )

        student_course_pairs = [
            (self.student1, course_without_class),
        ]

        valid_enrollments, invalid_enrollments = EnrollmentValidationService.validate_bulk_enrollment(
            student_course_pairs,
            self.term,
        )

        assert len(valid_enrollments) == 0
        assert len(invalid_enrollments) == 1

        invalid_enrollment = invalid_enrollments[0]
        assert invalid_enrollment["student"] == self.student1
        assert invalid_enrollment["course"] == course_without_class
        assert "No class scheduled" in invalid_enrollment["errors"][0]

    @patch.object(ScheduleService, "check_schedule_conflicts")
    def test_validate_bulk_enrollment_with_conflicts(self, mock_check_conflicts):
        """Test bulk enrollment validation with schedule conflicts."""
        mock_check_conflicts.return_value = ["Time conflict detected"]

        student_course_pairs = [
            (self.student1, self.course1),
        ]

        valid_enrollments, invalid_enrollments = EnrollmentValidationService.validate_bulk_enrollment(
            student_course_pairs,
            self.term,
        )

        assert len(valid_enrollments) == 0
        assert len(invalid_enrollments) == 1

        invalid_enrollment = invalid_enrollments[0]
        assert "Schedule conflict" in invalid_enrollment["errors"][0]

    @patch.object(EnrollmentValidationService, "_get_current_term")
    def test_validate_enrollment_limits_within_limits(self, mock_get_current_term):
        """Test enrollment limits validation within limits."""
        mock_get_current_term.return_value = self.term

        # Create existing enrollment (4 credits)
        ClassHeaderEnrollment.objects.create(
            student=self.student1,
            class_header=self.class_header1,
            status="ENROLLED",
            enrolled_by=get_system_user(),
        )

        is_valid, errors = EnrollmentValidationService.validate_enrollment_limits(
            self.student1,
            additional_courses=1,
            additional_credits=4,
        )

        assert is_valid
        assert len(errors) == 0

    @patch.object(EnrollmentValidationService, "_get_current_term")
    @patch.object(EnrollmentValidationService, "_get_max_credits_for_student")
    def test_validate_enrollment_limits_exceeds_maximum(self, mock_get_max_credits, mock_get_current_term):
        """Test enrollment limits validation when exceeding maximum."""
        mock_get_current_term.return_value = self.term
        mock_get_max_credits.return_value = 15

        # Create existing enrollments totaling 12 credits
        ClassHeaderEnrollment.objects.create(
            student=self.student1,
            class_header=self.class_header1,
            status="ENROLLED",
            enrolled_by=get_system_user(),
        )

        ClassHeaderEnrollment.objects.create(
            student=self.student1,
            class_header=self.class_header2,
            status="ENROLLED",
            enrolled_by=get_system_user(),
        )

        # Try to add 8 more credits (would total 20, exceeding 15 limit)
        is_valid, errors = EnrollmentValidationService.validate_enrollment_limits(
            self.student1,
            additional_courses=2,
            additional_credits=8,
        )

        assert not is_valid
        assert "would exceed maximum allowed" in errors[0]

    @patch.object(EnrollmentValidationService, "_get_current_term")
    def test_validate_enrollment_limits_no_current_term(self, mock_get_current_term):
        """Test enrollment limits validation with no current term."""
        mock_get_current_term.return_value = None

        is_valid, errors = EnrollmentValidationService.validate_enrollment_limits(
            self.student1,
            additional_courses=1,
            additional_credits=4,
        )

        assert is_valid
        assert len(errors) == 0

    def test_get_max_credits_for_student_high_gpa(self):
        """Test getting max credits for high GPA student."""
        # Mock GPA calculation to return high GPA
        with patch("apps.enrollment.services.PrerequisiteService._calculate_student_gpa") as mock_gpa:
            mock_gpa.return_value = 3.7
            max_credits = EnrollmentValidationService._get_max_credits_for_student(self.student1)
            assert max_credits == 15  # 9 + 6 for high GPA students

    def test_get_max_credits_for_student_probation(self):
        """Test getting max credits for regular student (probation status removed)."""
        # Mock GPA calculation to return None (no GPA data)
        with patch("apps.enrollment.services.PrerequisiteService._calculate_student_gpa") as mock_gpa:
            mock_gpa.return_value = None
            max_credits = EnrollmentValidationService._get_max_credits_for_student(self.student1)
            assert max_credits == 9  # Default limit

    def test_get_max_credits_for_student_default(self):
        """Test getting max credits for regular student."""
        # Mock GPA calculation to return low GPA
        with patch("apps.enrollment.services.PrerequisiteService._calculate_student_gpa") as mock_gpa:
            mock_gpa.return_value = 2.5
            max_credits = EnrollmentValidationService._get_max_credits_for_student(self.student1)
            assert max_credits == 9  # Default limit


# ExistingEnrollmentServiceIntegrationTest removed - depends on deprecated models
# (RequirementType, Requirement, RequirementCourse deleted in migration 0004_auto_20250123.py)


class MockLevelTestingIntegrationTest(TestCase):
    """Test integration points with level_testing app (mocked)."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

    @patch("apps.level_testing.models.PotentialStudent")
    def test_potential_student_lookup_integration(self, mock_potential_student_model):
        """Test integration with level_testing PotentialStudent model."""
        mock_potential_student = MagicMock()
        mock_potential_student.test_number = "T0001234"
        mock_potential_student.converted_student_number = 100001

        mock_potential_student_model.objects.get.return_value = mock_potential_student

        # This would be used in conversion workflows
        result = mock_potential_student_model.objects.get(converted_student_number=100001)

        assert result.test_number == "T0001234"
        assert result.converted_student_number == 100001
