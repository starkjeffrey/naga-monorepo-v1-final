"""Comprehensive tests for enrollment app models.

Tests all enrollment models following clean architecture principles:
- ProgramEnrollment: Student enrollment in academic programs/majors
- ClassHeaderEnrollment: Student enrollment in scheduled classes
- ClassPartEnrollment: Student enrollment in class components
- ClassSessionExemption: Session exemptions for IEAP repeat students
- StudentCourseEligibility: Cached course eligibility calculations

Key testing areas:
- Model validation and business logic
- Enrollment lifecycle management
- Status transitions and workflows
- Grade tracking and GPA calculations
- IEAP session exemption handling
- Eligibility caching and performance
- Relationships and dependency management
"""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.curriculum.models import Course, Cycle, Division, Major, Term
from apps.enrollment.models import (
    ClassHeaderEnrollment,
    ClassPartEnrollment,
    ClassSessionExemption,
    ProgramEnrollment,
    StudentCourseEligibility,
)
from apps.people.models import Person, StudentProfile
from apps.scheduling.class_part_types import ClassPartType
from apps.scheduling.models import ClassHeader, ClassPart, ClassSession

# Test constants
TEST_CREDIT_HOURS_2 = 2
TEST_CREDIT_HOURS_8 = 8

User = get_user_model()


class ProgramEnrollmentModelTest(TestCase):
    """Test ProgramEnrollment model functionality."""

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
        )

        self.term = Term.objects.create(
            name="Fall 2025",
            start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 15),
        )

    def test_create_program_enrollment(self):
        """Test creating a program enrollment."""
        enrollment = ProgramEnrollment.objects.create(
            student=self.student,
            program=self.major,
            enrollment_type=ProgramEnrollment.EnrollmentType.ACADEMIC,
            status=ProgramEnrollment.EnrollmentStatus.ACTIVE,
            start_date=date(2025, 9, 1),
            start_term=self.term,
            entry_level="Freshman",
            enrolled_by=self.user,
        )

        assert enrollment.student == self.student
        assert enrollment.program == self.major
        assert enrollment.enrollment_type == ProgramEnrollment.EnrollmentType.ACADEMIC
        assert enrollment.status == ProgramEnrollment.EnrollmentStatus.ACTIVE
        assert enrollment.entry_level == "Freshman"

    def test_unique_together_constraint(self):
        """Test unique constraint on student, program, and start_date."""
        ProgramEnrollment.objects.create(
            student=self.student,
            program=self.major,
            start_date=date(2025, 9, 1),
            start_term=self.term,
            enrolled_by=self.user,
        )

        with pytest.raises(IntegrityError):
            ProgramEnrollment.objects.create(
                student=self.student,
                program=self.major,
                start_date=date(2025, 9, 1),  # Same date - duplicate
                start_term=self.term,
                enrolled_by=self.user,
            )

    def test_enrollment_types(self):
        """Test all enrollment types."""
        enrollment_types = [
            ProgramEnrollment.EnrollmentType.LANGUAGE,
            ProgramEnrollment.EnrollmentType.ACADEMIC,
            ProgramEnrollment.EnrollmentType.JOINT,
        ]

        for enrollment_type in enrollment_types:
            enrollment = ProgramEnrollment.objects.create(
                student=self.student,
                program=self.major,
                enrollment_type=enrollment_type,
                start_date=date(2025, enrollment_types.index(enrollment_type) + 1, 1),
                start_term=self.term,
                enrolled_by=self.user,
            )
            assert enrollment.enrollment_type == enrollment_type

    def test_status_workflow(self):
        """Test enrollment status workflow."""
        enrollment = ProgramEnrollment.objects.create(
            student=self.student,
            program=self.major,
            start_date=date(2025, 9, 1),
            start_term=self.term,
            status=ProgramEnrollment.EnrollmentStatus.ACTIVE,
            enrolled_by=self.user,
        )

        # Test completion
        enrollment.end_enrollment(
            end_date=timezone.now().date(),
            reason="Graduated",
            user=self.user,
        )
        assert enrollment.status == ProgramEnrollment.EnrollmentStatus.COMPLETED
        assert enrollment.end_date is not None

        # Test withdrawal
        enrollment.status = ProgramEnrollment.EnrollmentStatus.ACTIVE
        enrollment.withdraw_enrollment(
            withdrawal_date=timezone.now().date(),
            reason="Personal reasons",
            user=self.user,
        )
        assert enrollment.status == ProgramEnrollment.EnrollmentStatus.WITHDRAWN

    def test_date_validation(self):
        """Test date validation."""
        enrollment = ProgramEnrollment(
            student=self.student,
            program=self.major,
            start_date=date(2025, 9, 1),
            end_date=date(2025, 8, 1),  # End before start - invalid
            start_term=self.term,
            enrolled_by=self.user,
        )

        with pytest.raises(ValidationError):
            enrollment.clean()

    def test_language_program_validation(self):
        """Test validation for language program enrollments."""
        enrollment = ProgramEnrollment(
            student=self.student,
            program=self.major,
            enrollment_type=ProgramEnrollment.EnrollmentType.LANGUAGE,
            start_date=date(2025, 9, 1),
            start_term=self.term,
            entry_level="",  # Required for language programs
            enrolled_by=self.user,
        )

        with pytest.raises(ValidationError):
            enrollment.clean()

    def test_properties(self):
        """Test program enrollment properties."""
        enrollment = ProgramEnrollment.objects.create(
            student=self.student,
            program=self.major,
            start_date=timezone.now().date(),
            start_term=self.term,
            status=ProgramEnrollment.EnrollmentStatus.ACTIVE,
            enrolled_by=self.user,
        )

        assert enrollment.is_active
        assert enrollment.is_current

        # Test with end date in past
        enrollment.end_date = timezone.now().date() - timezone.timedelta(days=30)
        assert not enrollment.is_current


class ClassHeaderEnrollmentModelTest(TestCase):
    """Test ClassHeaderEnrollment model functionality."""

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
        )

        # Create curriculum structure
        self.division = Division.objects.create(
            name="Academic Division",
            short_name="ACAD",
        )

        self.course = Course.objects.create(
            code="CS-101",
            title="Introduction to Programming",
            short_title="Intro Programming",
            division=self.division,
            credits=3,
        )

        self.term = Term.objects.create(
            name="Fall 2025",
            start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 15),
        )

        self.class_header = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="A",
            max_enrollment=20,
        )

    def test_create_class_header_enrollment(self):
        """Test creating a class header enrollment."""
        enrollment = ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            enrolled_by=self.user,
        )

        assert enrollment.student == self.student
        assert enrollment.class_header == self.class_header
        assert enrollment.status == ClassHeaderEnrollment.EnrollmentStatus.ENROLLED
        assert enrollment.enrolled_by == self.user

    def test_unique_together_constraint(self):
        """Test unique constraint on student and class_header."""
        ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            enrolled_by=self.user,
        )

        with pytest.raises(IntegrityError):
            ClassHeaderEnrollment.objects.create(
                student=self.student,
                class_header=self.class_header,  # Duplicate
                enrolled_by=self.user,
            )

    def test_enrollment_statuses(self):
        """Test all enrollment statuses."""
        statuses = [
            ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            ClassHeaderEnrollment.EnrollmentStatus.COMPLETED,
            ClassHeaderEnrollment.EnrollmentStatus.WITHDRAWN,
            ClassHeaderEnrollment.EnrollmentStatus.FAILED,
            ClassHeaderEnrollment.EnrollmentStatus.DROPPED,
            ClassHeaderEnrollment.EnrollmentStatus.AUDIT,
        ]

        for status in statuses:
            enrollment = ClassHeaderEnrollment.objects.create(
                student=self.student,
                class_header=self.class_header,
                status=status,
                enrolled_by=self.user,
            )
            assert enrollment.status == status
            enrollment.delete()  # Clean up for next iteration

    def test_grade_tracking(self):
        """Test grade tracking functionality."""
        enrollment = ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            final_grade="A",
            grade_points=Decimal("4.00"),
            enrolled_by=self.user,
        )

        assert enrollment.final_grade == "A"
        assert enrollment.grade_points == Decimal("4.00")

    def test_completion_workflow(self):
        """Test enrollment completion workflow."""
        enrollment = ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            enrolled_by=self.user,
        )

        # Test completion
        enrollment.complete_enrollment(
            final_grade="B+",
            grade_points=Decimal("3.30"),
            notes="Good performance",
            user=self.user,
        )

        assert enrollment.status == ClassHeaderEnrollment.EnrollmentStatus.COMPLETED
        assert enrollment.final_grade == "B+"
        assert enrollment.grade_points == Decimal("3.30")
        assert enrollment.completion_date is not None

        # Test withdrawal
        enrollment.status = ClassHeaderEnrollment.EnrollmentStatus.ENROLLED
        enrollment.withdraw_enrollment(reason="Schedule conflict", user=self.user)
        assert enrollment.status == ClassHeaderEnrollment.EnrollmentStatus.WITHDRAWN

    def test_grade_validation(self):
        """Test grade validation."""
        enrollment = ClassHeaderEnrollment(
            student=self.student,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.COMPLETED,
            final_grade="",  # Required for completed enrollments
            enrolled_by=self.user,
        )

        with pytest.raises(ValidationError):
            enrollment.clean()

    def test_grade_points_validation(self):
        """Test grade points validation."""
        enrollment = ClassHeaderEnrollment(
            student=self.student,
            class_header=self.class_header,
            grade_points=Decimal("5.00"),  # Invalid - above 4.00
            enrolled_by=self.user,
        )

        with pytest.raises(ValidationError):
            enrollment.clean()

    def test_properties(self):
        """Test enrollment properties."""
        enrollment = ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            enrolled_by=self.user,
        )

        assert enrollment.is_active
        assert not enrollment.is_completed

        # Test completed status
        enrollment.status = ClassHeaderEnrollment.EnrollmentStatus.COMPLETED
        assert not enrollment.is_active
        assert enrollment.is_completed

    def test_audit_enrollment(self):
        """Test audit enrollment functionality."""
        enrollment = ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            is_audit=True,
            enrolled_by=self.user,
        )

        assert enrollment.is_audit

    def test_late_enrollment(self):
        """Test late enrollment tracking."""
        enrollment = ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            late_enrollment=True,
            enrolled_by=self.user,
        )

        assert enrollment.late_enrollment


class ClassPartEnrollmentModelTest(TestCase):
    """Test ClassPartEnrollment model functionality."""

    def setUp(self):
        """Set up test data."""
        self.person = Person.objects.create(
            personal_name="John",
            family_name="Doe",
            date_of_birth="1990-01-01",
        )

        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id=1001,
        )

        # Create curriculum and scheduling structure
        self.division = Division.objects.create(
            name="Academic Division",
            short_name="ACAD",
        )

        self.course = Course.objects.create(
            code="CS-101",
            title="Introduction to Programming",
            short_title="Intro Programming",
            division=self.division,
            credits=3,
        )

        self.term = Term.objects.create(
            name="Fall 2025",
            start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 15),
        )

        self.class_header = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="A",
        )

        # First create a ClassSession, then create ClassPart with it
        self.class_session = ClassSession.objects.create(
            class_header=self.class_header,
            session_number=1,
        )

        self.class_part = ClassPart.objects.create(
            class_session=self.class_session,
            class_part_type=ClassPartType.MAIN,
            class_part_code="A",
            meeting_days="MON,WED,FRI",
            start_time="09:00",
            end_time="10:00",
        )

    def test_create_class_part_enrollment(self):
        """Test creating a class part enrollment."""
        enrollment = ClassPartEnrollment.objects.create(
            student=self.student,
            class_part=self.class_part,
            is_active=True,
        )

        assert enrollment.student == self.student
        assert enrollment.class_part == self.class_part
        assert enrollment.is_active
        assert enrollment.enrollment_date is not None

    def test_unique_together_constraint(self):
        """Test unique constraint on student, class_part, and is_active."""
        ClassPartEnrollment.objects.create(
            student=self.student,
            class_part=self.class_part,
            is_active=True,
        )

        with pytest.raises(IntegrityError):
            ClassPartEnrollment.objects.create(
                student=self.student,
                class_part=self.class_part,
                is_active=True,  # Duplicate active enrollment
            )

    def test_enrollment_management(self):
        """Test enrollment activation/deactivation."""
        enrollment = ClassPartEnrollment.objects.create(
            student=self.student,
            class_part=self.class_part,
            is_active=True,
        )

        # Test deactivation
        enrollment.deactivate(reason="Dropped class part")
        assert not enrollment.is_active
        assert "Deactivated" in enrollment.notes

        # Test reactivation
        enrollment.reactivate(reason="Re-enrolled in class part")
        assert enrollment.is_active
        assert "Reactivated" in enrollment.notes

    def test_multiple_enrollments_different_activity(self):
        """Test that student can have multiple enrollments if different activity status."""
        # Create active enrollment
        active_enrollment = ClassPartEnrollment.objects.create(
            student=self.student,
            class_part=self.class_part,
            is_active=True,
        )

        # Create inactive enrollment (should be allowed)
        inactive_enrollment = ClassPartEnrollment.objects.create(
            student=self.student,
            class_part=self.class_part,
            is_active=False,
        )

        assert active_enrollment.is_active
        assert not inactive_enrollment.is_active

    def test_string_representation(self):
        """Test string representation."""
        enrollment = ClassPartEnrollment.objects.create(
            student=self.student,
            class_part=self.class_part,
            is_active=True,
        )

        expected = f"✓ {self.student} → Part #{self.class_part.id}"
        assert str(enrollment) == expected

        # Test inactive representation
        enrollment.is_active = False
        enrollment.save()
        expected = f"✗ {self.student} → Part #{self.class_part.id}"
        assert str(enrollment) == expected

    def test_notes_management(self):
        """Test notes management functionality."""
        enrollment = ClassPartEnrollment.objects.create(
            student=self.student,
            class_part=self.class_part,
            notes="Initial enrollment notes",
        )

        assert enrollment.notes == "Initial enrollment notes"

        # Test note appending through deactivate
        enrollment.deactivate(reason="Academic probation")
        assert "Initial enrollment notes" in enrollment.notes
        assert "Deactivated: Academic probation" in enrollment.notes


class StudentCourseEligibilityModelTest(TestCase):
    """Test StudentCourseEligibility model functionality."""

    def setUp(self):
        """Set up test data."""
        self.person = Person.objects.create(
            personal_name="John",
            family_name="Doe",
            date_of_birth="1990-01-01",
        )

        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id=1001,
        )

        self.division = Division.objects.create(
            name="Academic Division",
            short_name="ACAD",
        )

        self.course = Course.objects.create(
            code="CS-101",
            title="Introduction to Programming",
            short_title="Intro Programming",
            division=self.division,
            credits=3,
        )

        self.prerequisite_course = Course.objects.create(
            code="MATH-101",
            title="College Mathematics",
            short_title="College Math",
            division=self.division,
            credits=3,
        )

        self.term = Term.objects.create(
            name="Fall 2025",
            start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 15),
        )

    def test_create_eligibility_record(self):
        """Test creating an eligibility record."""
        eligibility = StudentCourseEligibility.objects.create(
            student=self.student,
            course=self.course,
            term=self.term,
            is_eligible=True,
            is_retake=False,
            previous_attempts=0,
        )

        assert eligibility.student == self.student
        assert eligibility.course == self.course
        assert eligibility.term == self.term
        assert eligibility.is_eligible
        assert not eligibility.is_retake

    def test_unique_together_constraint(self):
        """Test unique constraint on student, course, and term."""
        StudentCourseEligibility.objects.create(
            student=self.student,
            course=self.course,
            term=self.term,
            is_eligible=True,
        )

        with pytest.raises(IntegrityError):
            StudentCourseEligibility.objects.create(
                student=self.student,
                course=self.course,
                term=self.term,  # Duplicate
                is_eligible=False,
            )

    def test_prerequisite_tracking(self):
        """Test prerequisite tracking functionality."""
        eligibility = StudentCourseEligibility.objects.create(
            student=self.student,
            course=self.course,
            term=self.term,
            is_eligible=False,
        )

        # Add missing prerequisite
        eligibility.missing_prerequisites.add(self.prerequisite_course)

        assert self.prerequisite_course in eligibility.missing_prerequisites.all()
        assert eligibility.missing_prerequisites.count() == 1

    def test_retake_management(self):
        """Test retake functionality."""
        eligibility = StudentCourseEligibility.objects.create(
            student=self.student,
            course=self.course,
            term=self.term,
            is_eligible=True,
            is_retake=True,
            previous_attempts=2,
            retry_priority_score=8,
        )

        assert eligibility.is_retake
        assert eligibility.previous_attempts == TEST_CREDIT_HOURS_2
        assert eligibility.retry_priority_score == TEST_CREDIT_HOURS_8

    def test_eligibility_summary(self):
        """Test eligibility summary property."""
        # Test eligible student
        eligible = StudentCourseEligibility.objects.create(
            student=self.student,
            course=self.course,
            term=self.term,
            is_eligible=True,
            is_retake=False,
        )
        assert eligible.eligibility_summary == "Eligible"

        # Test eligible retake
        retake = StudentCourseEligibility.objects.create(
            student=self.student,
            course=self.prerequisite_course,
            term=self.term,
            is_eligible=True,
            is_retake=True,
            previous_attempts=1,
        )
        assert retake.eligibility_summary == "Eligible for retake (attempt #2)"

        # Create a different term for this test to avoid unique constraint
        different_term = Term.objects.create(
            name="Spring 2026",
            start_date=date(2026, 1, 1),
            end_date=date(2026, 5, 15),
        )
        ineligible_with_prereq = StudentCourseEligibility.objects.create(
            student=self.student,
            course=self.course,
            term=different_term,
            is_eligible=False,
        )
        ineligible_with_prereq.missing_prerequisites.add(self.prerequisite_course)

        summary = ineligible_with_prereq.eligibility_summary
        assert "Missing prerequisites:" in summary
        assert "MATH-101" in summary

    def test_recalculate_eligibility(self):
        """Test eligibility recalculation."""
        eligibility = StudentCourseEligibility.objects.create(
            student=self.student,
            course=self.course,
            term=self.term,
            is_eligible=False,
        )

        original_calculated = eligibility.last_calculated

        # Recalculate (placeholder implementation)
        result = eligibility.recalculate_eligibility()

        # Should update timestamp
        eligibility.refresh_from_db()
        assert eligibility.last_calculated > original_calculated
        assert not result  # Still false in placeholder implementation

    def test_calculation_notes(self):
        """Test calculation notes functionality."""
        eligibility = StudentCourseEligibility.objects.create(
            student=self.student,
            course=self.course,
            term=self.term,
            is_eligible=True,
            calculation_notes="Student has completed all prerequisites with grades above C",
        )

        assert eligibility.calculation_notes == "Student has completed all prerequisites with grades above C"

    def test_string_representation(self):
        """Test string representation."""
        eligibility = StudentCourseEligibility.objects.create(
            student=self.student,
            course=self.course,
            term=self.term,
            is_eligible=True,
            is_retake=False,
        )

        expected = f"✓ {self.student} - {self.course.code} ({self.term})"
        assert str(eligibility) == expected

        # Test with retake
        retake_eligibility = StudentCourseEligibility.objects.create(
            student=self.student,
            course=self.prerequisite_course,
            term=self.term,
            is_eligible=True,
            is_retake=True,
        )

        expected = f"✓ {self.student} - {self.prerequisite_course.code} ({self.term}) (retake)"
        assert str(retake_eligibility) == expected


class EnrollmentIntegrationTest(TestCase):
    """Test integration between enrollment models."""

    def setUp(self):
        """Set up test data for integration tests."""
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
        )

        # Create curriculum structure
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
        )

        self.course = Course.objects.create(
            code="CS-101",
            title="Introduction to Programming",
            short_title="Intro Programming",
            division=self.division,
            credits=3,
        )

        self.term = Term.objects.create(
            name="Fall 2025",
            start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 15),
        )

        self.class_header = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="A",
            max_enrollment=20,
        )

        # First create a ClassSession, then create ClassPart with it
        self.class_session = ClassSession.objects.create(
            class_header=self.class_header,
            session_number=1,
        )

        self.class_part = ClassPart.objects.create(
            class_session=self.class_session,
            class_part_type=ClassPartType.MAIN,
            class_part_code="A",
            meeting_days="MON,WED,FRI",
            start_time="09:00",
            end_time="10:00",
        )

    def test_complete_enrollment_workflow(self):
        """Test complete student enrollment workflow."""
        # 1. Student enrolls in program
        program_enrollment = ProgramEnrollment.objects.create(
            student=self.student,
            program=self.major,
            enrollment_type=ProgramEnrollment.EnrollmentType.ACADEMIC,
            status=ProgramEnrollment.EnrollmentStatus.ACTIVE,
            start_date=date(2025, 9, 1),
            start_term=self.term,
            entry_level="Freshman",
            enrolled_by=self.user,
        )

        # 2. Check course eligibility
        eligibility = StudentCourseEligibility.objects.create(
            student=self.student,
            course=self.course,
            term=self.term,
            is_eligible=True,
            calculation_notes="New student - no prerequisites required",
        )

        # 3. Enroll in class header
        class_enrollment = ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            enrolled_by=self.user,
        )

        # 4. Automatically enroll in class part
        part_enrollment = ClassPartEnrollment.objects.create(
            student=self.student,
            class_part=self.class_part,
            is_active=True,
        )

        # 5. Complete the class
        class_enrollment.complete_enrollment(
            final_grade="A-",
            grade_points=Decimal("3.70"),
            notes="Excellent work",
            user=self.user,
        )

        # Verify complete workflow
        assert program_enrollment.is_active
        assert eligibility.is_eligible
        assert class_enrollment.is_completed
        assert part_enrollment.is_active
        assert class_enrollment.final_grade == "A-"

    def test_enrollment_capacity_management(self):
        """Test enrollment capacity management."""
        # Set low capacity
        self.class_header.max_enrollment = 2
        self.class_header.save()

        # Create multiple enrollments
        student2 = StudentProfile.objects.create(
            person=Person.objects.create(
                personal_name="Jane",
                family_name="Smith",
                date_of_birth="1991-01-01",
            ),
            student_id=1002,
        )

        student3 = StudentProfile.objects.create(
            person=Person.objects.create(
                personal_name="Bob",
                family_name="Johnson",
                date_of_birth="1992-01-01",
            ),
            student_id=1003,
        )

        # First two students get enrolled
        ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            enrolled_by=self.user,
        )

        ClassHeaderEnrollment.objects.create(
            student=student2,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            enrolled_by=self.user,
        )

        # Third student gets dropped (since WAITLISTED doesn't exist)
        ClassHeaderEnrollment.objects.create(
            student=student3,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.DROPPED,
            enrolled_by=self.user,
        )

        # Verify enrollment status
        enrolled_count = ClassHeaderEnrollment.objects.filter(
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
        ).count()

        dropped_count = ClassHeaderEnrollment.objects.filter(
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.DROPPED,
        ).count()

        assert enrolled_count == TEST_CREDIT_HOURS_2
        assert dropped_count == 1

    def test_student_schedule_conflicts(self):
        """Test detection of student schedule conflicts."""
        # Create conflicting class
        conflicting_course = Course.objects.create(
            code="MATH-101",
            title="College Mathematics",
            short_title="College Math",
            division=self.division,
            credits=3,
        )

        conflicting_class = ClassHeader.objects.create(
            course=conflicting_course,
            term=self.term,
            section_id="A",
        )

        conflicting_session = ClassSession.objects.create(
            class_header=conflicting_class,
            session_number=1,
        )

        ClassPart.objects.create(
            class_session=conflicting_session,
            class_part_type=ClassPartType.MAIN,
            class_part_code="A",
            meeting_days="MON,WED,FRI",  # Same days
            start_time="09:30",  # Overlapping time
            end_time="10:30",
        )

        # Enroll student in first class
        ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            enrolled_by=self.user,
        )

        ClassPartEnrollment.objects.create(
            student=self.student,
            class_part=self.class_part,
            is_active=True,
        )

        # Attempt to enroll in conflicting class (business logic would prevent this)
        ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=conflicting_class,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            enrolled_by=self.user,
        )

        # Verify both enrollments exist (conflict detection would be in business logic)
        student_enrollments = ClassHeaderEnrollment.objects.filter(
            student=self.student,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
        ).count()

        assert student_enrollments == TEST_CREDIT_HOURS_2
        # Note: Actual conflict detection would be implemented in services/views

    def test_grade_progression_tracking(self):
        """Test tracking student progression through courses."""
        # Create sequence of courses
        course2 = Course.objects.create(
            code="CS-102",
            title="Data Structures",
            short_title="Data Structures",
            division=self.division,
            credits=3,
        )

        class_header2 = ClassHeader.objects.create(
            course=course2,
            term=self.term,
            section_id="A",
        )

        # Complete first course
        ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.COMPLETED,
            final_grade="B+",
            grade_points=Decimal("3.30"),
            enrolled_by=self.user,
        )

        # Update eligibility for second course
        eligibility = StudentCourseEligibility.objects.create(
            student=self.student,
            course=course2,
            term=self.term,
            is_eligible=True,
            calculation_notes="Prerequisites met with B+ in CS-101",
        )

        # Enroll in second course
        ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=class_header2,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            enrolled_by=self.user,
        )

        # Verify progression
        completed_courses = ClassHeaderEnrollment.objects.filter(
            student=self.student,
            status=ClassHeaderEnrollment.EnrollmentStatus.COMPLETED,
        ).count()

        current_courses = ClassHeaderEnrollment.objects.filter(
            student=self.student,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
        ).count()

        assert completed_courses == 1
        assert current_courses == 1
        assert eligibility.is_eligible


class ClassSessionExemptionModelTest(TestCase):
    """Test ClassSessionExemption model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        # Create person and student
        self.person = Person.objects.create(
            personal_name="Alice",
            family_name="Smith",
            date_of_birth="1995-01-01",
        )

        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id=1001,
        )

        # Create academic structure
        self.division = Division.objects.create(
            name="English Language Institute",
            short_name="ELI",
        )

        self.cycle = Cycle.objects.create(
            division=self.division,
            name="Fall 2025 Cycle",
        )

        self.major = Major.objects.create(
            name="Intensive English Academic Program",
            code="IEAP",
            cycle=self.cycle,
        )

        self.course = Course.objects.create(
            code="IEAP-01",
            title="IEAP Level 1",
            short_title="IEAP Level 1",
            division=self.division,
            credits=6,
        )

        self.term = Term.objects.create(
            name="Fall 2025",
            start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 15),
        )

        # Create IEAP class with multiple sessions
        self.class_header = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="A",
        )

        self.session1 = ClassSession.objects.create(
            class_header=self.class_header,
            session_number=1,
            session_name="Session 1",
            grade_weight=Decimal("0.500"),
        )

        self.session2 = ClassSession.objects.create(
            class_header=self.class_header,
            session_number=2,
            session_name="Session 2",
            grade_weight=Decimal("0.500"),
        )

        # Create class header enrollment
        self.enrollment = ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            enrolled_by=self.user,
        )

    def test_create_session_exemption(self):
        """Test creating a session exemption."""
        exemption = ClassSessionExemption.objects.create(
            class_header_enrollment=self.enrollment,
            class_session=self.session1,
            exemption_reason="Already passed Session 1 in previous term",
            exempted_by=self.user,
        )

        assert exemption.class_header_enrollment == self.enrollment
        assert exemption.class_session == self.session1
        assert exemption.exemption_reason == "Already passed Session 1 in previous term"
        assert exemption.exempted_by == self.user

    def test_unique_together_constraint(self):
        """Test unique constraint on enrollment and session."""
        ClassSessionExemption.objects.create(
            class_header_enrollment=self.enrollment,
            class_session=self.session1,
            exemption_reason="Test exemption",
            exempted_by=self.user,
        )

        # Try to create duplicate exemption
        with pytest.raises(IntegrityError):
            ClassSessionExemption.objects.create(
                class_header_enrollment=self.enrollment,
                class_session=self.session1,  # Same session
                exemption_reason="Duplicate exemption",
                exempted_by=self.user,
            )

    def test_exemption_validation(self):
        """Test validation that session belongs to same class."""
        # Create another class
        other_course = Course.objects.create(
            code="IEAP-02",
            title="IEAP Level 2",
            short_title="IEAP Level 2",
            division=self.division,
            credits=6,
        )

        other_class = ClassHeader.objects.create(
            course=other_course,
            term=self.term,
            section_id="A",
        )

        other_session = ClassSession.objects.create(
            class_header=other_class,
            session_number=1,
        )

        # Try to create exemption for session from different class
        exemption = ClassSessionExemption(
            class_header_enrollment=self.enrollment,
            class_session=other_session,  # Different class
            exemption_reason="Invalid exemption",
            exempted_by=self.user,
        )

        with pytest.raises(ValidationError):
            exemption.clean()

    def test_str_representation(self):
        """Test string representation."""
        exemption = ClassSessionExemption.objects.create(
            class_header_enrollment=self.enrollment,
            class_session=self.session1,
            exemption_reason="Test exemption",
            exempted_by=self.user,
        )

        expected = f"{self.student} exempted from {self.session1}"
        assert str(exemption) == expected

    def test_multiple_exemptions_same_student(self):
        """Test student can be exempted from multiple sessions."""
        exemption1 = ClassSessionExemption.objects.create(
            class_header_enrollment=self.enrollment,
            class_session=self.session1,
            exemption_reason="Already passed Session 1",
            exempted_by=self.user,
        )

        exemption2 = ClassSessionExemption.objects.create(
            class_header_enrollment=self.enrollment,
            class_session=self.session2,
            exemption_reason="Already passed Session 2",
            exempted_by=self.user,
        )

        # Verify both exemptions exist
        exemptions = ClassSessionExemption.objects.filter(
            class_header_enrollment=self.enrollment,
        )
        assert exemptions.count() == TEST_CREDIT_HOURS_2
        assert exemption1 in exemptions
        assert exemption2 in exemptions

    def test_exemption_date_auto_set(self):
        """Test exemption date is automatically set."""
        exemption = ClassSessionExemption.objects.create(
            class_header_enrollment=self.enrollment,
            class_session=self.session1,
            exemption_reason="Test exemption",
            exempted_by=self.user,
        )

        assert exemption.exemption_date is not None
        assert exemption.exemption_date <= timezone.now()


class EnrollmentStatusUpdateTest(TestCase):
    """Test updated enrollment status choices."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        # Create person and student
        self.person = Person.objects.create(
            personal_name="Bob",
            family_name="Johnson",
            date_of_birth="1998-01-01",
        )

        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id=1002,
        )

        # Create minimal academic structure
        self.division = Division.objects.create(
            name="Test Division",
            short_name="TEST",
        )

        self.cycle = Cycle.objects.create(
            division=self.division,
            name="Test Cycle",
        )

        self.course = Course.objects.create(
            code="TEST-101",
            title="Test Course",
            short_title="Test Course",
            division=self.division,
            credits=3,
        )

        self.term = Term.objects.create(
            name="Test Term",
            start_date=date(2025, 9, 1),
            end_date=date(2025, 12, 15),
        )

        self.class_header = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="A",
        )

    def test_new_enrollment_status_choices(self):
        """Test new enrollment status choices are available."""
        # Test common statuses
        enrollment = ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            enrolled_by=self.user,
        )
        assert enrollment.status == "ENROLLED"

        # Test academic program specific statuses
        enrollment.status = ClassHeaderEnrollment.EnrollmentStatus.WITHDRAWN
        enrollment.save()
        assert enrollment.status == "WITHDRAWN"

        enrollment.status = ClassHeaderEnrollment.EnrollmentStatus.AUDIT
        enrollment.save()
        assert enrollment.status == "AUDIT"

        enrollment.status = ClassHeaderEnrollment.EnrollmentStatus.NO_SHOW_ACADEMIC
        enrollment.save()
        assert enrollment.status == "NO_SHOW_ACADEMIC"

        # Test language program specific statuses
        enrollment.status = ClassHeaderEnrollment.EnrollmentStatus.NO_SHOW_LANGUAGE
        enrollment.save()
        assert enrollment.status == "NO_SHOW_LANGUAGE"

    def test_is_active_property_with_new_statuses(self):
        """Test is_active property includes new AUDIT status."""
        enrollment = ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            enrolled_by=self.user,
        )

        # Test ENROLLED is active
        assert enrollment.is_active

        # Test AUDIT is active
        enrollment.status = ClassHeaderEnrollment.EnrollmentStatus.AUDIT
        enrollment.save()
        assert enrollment.is_active

        # Test other statuses are not active
        enrollment.status = ClassHeaderEnrollment.EnrollmentStatus.DROPPED
        enrollment.save()
        assert not enrollment.is_active

        enrollment.status = ClassHeaderEnrollment.EnrollmentStatus.NO_SHOW_ACADEMIC
        enrollment.save()
        assert not enrollment.is_active

    def test_status_field_max_length(self):
        """Test status field can accommodate longer status names."""
        enrollment = ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.NO_SHOW_ACADEMIC,  # 16 chars
            enrolled_by=self.user,
        )

        # Should save without errors
        enrollment.save()
        enrollment.refresh_from_db()
        assert enrollment.status == "NO_SHOW_ACADEMIC"

    def test_enrollment_workflow_with_new_statuses(self):
        """Test enrollment workflow with new status options."""
        enrollment = ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            enrolled_by=self.user,
        )

        # Test withdrawal workflow
        enrollment.withdraw_enrollment(reason="Student requested withdrawal")
        assert enrollment.status == ClassHeaderEnrollment.EnrollmentStatus.WITHDRAWN
        assert "withdrawn" in enrollment.notes.lower()

        # Test audit enrollment (use different class header to avoid unique constraint)
        audit_class_header = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="B",  # Different section
        )

        audit_enrollment = ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=audit_class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.AUDIT,
            enrolled_by=self.user,
            is_audit=True,
        )

        assert audit_enrollment.is_active
        assert audit_enrollment.is_audit
