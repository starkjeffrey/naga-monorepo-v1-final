"""Basic tests for canonical requirement models to verify functionality.

This test module validates that the new canonical requirement system
works correctly and integrates properly with existing models.
"""

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from apps.academic.services.canonical import (
    CanonicalRequirementService,
)
from apps.academic.services.degree_audit import DegreeAuditService
from apps.curriculum.models import Course, Cycle, Division, Major, Term
from apps.people.models import Gender, Person, StudentProfile

User = get_user_model()

# Get models dynamically to avoid import issues
CanonicalRequirement = apps.get_model("academic", "CanonicalRequirement")
StudentRequirementException = apps.get_model("academic", "StudentRequirementException")
StudentDegreeProgress = apps.get_model("academic", "StudentDegreeProgress")


class CanonicalRequirementModelTest(TestCase):
    """Test CanonicalRequirement model functionality."""

    def setUp(self):
        """Set up test data."""
        self.division = Division.objects.create(
            name="Academic Division",
            short_name="ACAD",
        )
        self.cycle = Cycle.objects.create(
            division=self.division,
            name="Bachelor's Program",
            degree_awarded=Cycle.DegreeType.BA,
        )
        self.major = Major.objects.create(
            cycle=self.cycle,
            name="Computer Science",
            code="CS",
            total_credits_required=120,
        )
        self.course = Course.objects.create(
            code="CS101",
            title="Programming Fundamentals",
            division=self.division,
            cycle=Course.CourseLevel.BACHELORS,
            credits=3,
        )
        self.term = Term.objects.create(
            name="Fall 2024",
            term_type=Term.TermType.BACHELORS,
            start_date="2024-09-01",
            end_date="2024-12-15",
        )

    def test_canonical_requirement_creation(self):
        """Test basic canonical requirement creation."""
        requirement = CanonicalRequirement.objects.create(
            major=self.major,
            sequence_number=1,
            required_course=self.course,
            name="Programming Foundation",
            description="Core programming course",
            effective_term=self.term,
        )

        assert requirement.major == self.major
        assert requirement.sequence_number == 1
        assert requirement.required_course == self.course
        assert requirement.canonical_credits == 3  # From course.credits
        assert requirement.is_active is True

    def test_canonical_requirement_str_representation(self):
        """Test string representation."""
        requirement = CanonicalRequirement.objects.create(
            major=self.major,
            sequence_number=1,
            required_course=self.course,
            name="Programming Foundation",
            effective_term=self.term,
        )
        expected = f"{self.major.code} #1: {self.course.code}"
        assert str(requirement) == expected

    def test_canonical_credits_property(self):
        """Test canonical_credits property returns course credits."""
        requirement = CanonicalRequirement.objects.create(
            major=self.major,
            sequence_number=1,
            required_course=self.course,
            name="Programming Foundation",
            effective_term=self.term,
        )
        assert requirement.canonical_credits == self.course.credits

    def test_unique_sequence_per_major_term(self):
        """Test sequence numbers must be unique per major and term."""
        CanonicalRequirement.objects.create(
            major=self.major,
            sequence_number=1,
            required_course=self.course,
            name="First Requirement",
            effective_term=self.term,
        )

        course2 = Course.objects.create(
            code="CS102",
            title="Programming II",
            division=self.division,
            cycle=Course.CourseLevel.BACHELORS,
            credits=3,
        )

        with pytest.raises(IntegrityError):
            CanonicalRequirement.objects.create(
                major=self.major,
                sequence_number=1,  # Same sequence number
                required_course=course2,
                name="Duplicate Sequence",
                effective_term=self.term,
            )


class StudentRequirementExceptionModelTest(TestCase):
    """Test StudentRequirementException model functionality."""

    def setUp(self):
        """Set up test data."""
        # Create organizational structure
        self.division = Division.objects.create(name="Academic Division")
        self.cycle = Cycle.objects.create(
            division=self.division,
            name="Bachelor's Program",
            degree_awarded=Cycle.DegreeType.BA,
        )
        self.major = Major.objects.create(
            cycle=self.cycle,
            name="Computer Science",
            code="CS",
        )
        self.course = Course.objects.create(
            code="CS101",
            title="Programming Fundamentals",
            division=self.division,
            cycle=Course.CourseLevel.BACHELORS,
            credits=3,
        )
        self.term = Term.objects.create(
            name="Fall 2024",
            term_type=Term.TermType.BACHELORS,
            start_date="2024-09-01",
            end_date="2024-12-15",
        )

        # Create canonical requirement
        self.canonical_requirement = CanonicalRequirement.objects.create(
            major=self.major,
            sequence_number=1,
            required_course=self.course,
            name="Programming Foundation",
            effective_term=self.term,
        )

        # Create student
        self.person = Person.objects.create(
            personal_name="John",
            family_name="Doe",
            preferred_gender=Gender.MALE,
        )
        self.student = StudentProfile.objects.create(
            person=self.person,
        )

        # Create user for approval workflow
        self.user = User.objects.create_user(
            email="admin@example.com",
        )

    def test_exception_creation_with_course(self):
        """Test exception creation with fulfilling course."""
        substitute_course = Course.objects.create(
            code="MATH101",
            title="Mathematics for CS",
            division=self.division,
            cycle=Course.CourseLevel.BACHELORS,
            credits=3,
        )

        exception = StudentRequirementException.objects.create(
            student=self.student,
            canonical_requirement=self.canonical_requirement,
            exception_type=StudentRequirementException.ExceptionType.COURSE_SUBSTITUTION,
            fulfilling_course=substitute_course,
            reason="Math course provides equivalent programming logic foundation",
            effective_term=self.term,
            requested_by=self.user,
        )

        assert exception.student == self.student
        assert exception.canonical_requirement == self.canonical_requirement
        assert exception.fulfilling_course == substitute_course
        assert exception.exception_credits == substitute_course.credits

    def test_exception_creation_with_waiver(self):
        """Test exception creation with requirement waiver."""
        exception = StudentRequirementException.objects.create(
            student=self.student,
            canonical_requirement=self.canonical_requirement,
            exception_type=StudentRequirementException.ExceptionType.WAIVER,
            is_waived=True,
            reason="Student has extensive industry programming experience",
            effective_term=self.term,
            requested_by=self.user,
        )

        assert exception.is_waived is True
        assert exception.exception_credits == self.canonical_requirement.canonical_credits

    def test_exception_credits_calculation(self):
        """Test exception_credits property calculation."""
        # Test with waiver
        waiver_exception = StudentRequirementException.objects.create(
            student=self.student,
            canonical_requirement=self.canonical_requirement,
            exception_type=StudentRequirementException.ExceptionType.WAIVER,
            is_waived=True,
            reason="Waived requirement",
            effective_term=self.term,
            requested_by=self.user,
        )
        assert waiver_exception.exception_credits == self.canonical_requirement.canonical_credits

        # Test with fulfilling course
        substitute_course = Course.objects.create(
            code="MATH101",
            title="Mathematics",
            division=self.division,
            cycle=Course.CourseLevel.BACHELORS,
            credits=4,
        )
        course_exception = StudentRequirementException.objects.create(
            student=self.student,
            canonical_requirement=self.canonical_requirement,
            exception_type=StudentRequirementException.ExceptionType.COURSE_SUBSTITUTION,
            fulfilling_course=substitute_course,
            reason="Course substitution",
            effective_term=self.term,
            requested_by=self.user,
        )
        assert course_exception.exception_credits == substitute_course.credits

    def test_approval_workflow(self):
        """Test exception approval and rejection workflow."""
        exception = StudentRequirementException.objects.create(
            student=self.student,
            canonical_requirement=self.canonical_requirement,
            exception_type=StudentRequirementException.ExceptionType.WAIVER,
            is_waived=True,
            reason="Test waiver",
            effective_term=self.term,
            requested_by=self.user,
        )

        # Test approval
        assert exception.approval_status == StudentRequirementException.ApprovalStatus.PENDING
        exception.approve(self.user, "Approved for testing")
        exception.refresh_from_db()

        assert exception.approval_status == StudentRequirementException.ApprovalStatus.APPROVED
        assert exception.approved_by == self.user
        assert exception.approval_date is not None

        # Test rejection on new exception
        exception2 = StudentRequirementException.objects.create(
            student=self.student,
            canonical_requirement=self.canonical_requirement,
            exception_type=StudentRequirementException.ExceptionType.ADMINISTRATIVE_OVERRIDE,
            is_waived=True,
            reason="Test rejection",
            effective_term=self.term,
            requested_by=self.user,
        )

        exception2.reject(self.user, "Rejected for testing")
        exception2.refresh_from_db()

        assert exception2.approval_status == StudentRequirementException.ApprovalStatus.REJECTED
        assert exception2.rejection_reason == "Rejected for testing"


class CanonicalServicesTest(TestCase):
    """Test canonical requirement services."""

    def setUp(self):
        """Set up test data."""
        # Create organizational structure
        self.division = Division.objects.create(name="Academic Division")
        self.cycle = Cycle.objects.create(
            division=self.division,
            name="Bachelor's Program",
            degree_awarded=Cycle.DegreeType.BA,
        )
        self.major = Major.objects.create(
            cycle=self.cycle,
            name="Computer Science",
            code="CS",
        )
        self.term = Term.objects.create(
            name="Fall 2024",
            term_type=Term.TermType.BACHELORS,
            start_date="2024-09-01",
            end_date="2024-12-15",
        )

        # Create courses
        self.course1 = Course.objects.create(
            code="CS101",
            title="Programming I",
            division=self.division,
            cycle=Course.CourseLevel.BACHELORS,
            credits=3,
        )
        self.course2 = Course.objects.create(
            code="CS102",
            title="Programming II",
            division=self.division,
            cycle=Course.CourseLevel.BACHELORS,
            credits=3,
        )

        # Create canonical requirements
        self.req1 = CanonicalRequirement.objects.create(
            major=self.major,
            sequence_number=1,
            required_course=self.course1,
            name="Programming Foundation",
            effective_term=self.term,
        )
        self.req2 = CanonicalRequirement.objects.create(
            major=self.major,
            sequence_number=2,
            required_course=self.course2,
            name="Advanced Programming",
            effective_term=self.term,
        )

        # Create student
        self.person = Person.objects.create(
            personal_name="Jane",
            family_name="Smith",
            preferred_gender=Gender.FEMALE,
        )
        self.student = StudentProfile.objects.create(
            person=self.person,
        )

        # Create user
        self.user = User.objects.create_user(
            email="advisor@example.com",
        )

    def test_get_major_requirements(self):
        """Test getting canonical requirements for a major."""
        requirements = CanonicalRequirementService.get_major_requirements(self.major)

        assert len(requirements) == 2
        assert requirements[0].sequence_number == 1
        assert requirements[1].sequence_number == 2
        assert requirements[0].required_course == self.course1
        assert requirements[1].required_course == self.course2

    def test_student_progress_calculation(self):
        """Test student progress calculation."""
        # Initially no progress
        progress_list = CanonicalRequirementService.get_student_progress(self.student, self.major)

        assert len(progress_list) == 2
        assert not progress_list[0].is_completed
        assert not progress_list[1].is_completed

        # Add exception for first requirement
        exception = StudentRequirementException.objects.create(
            student=self.student,
            canonical_requirement=self.req1,
            exception_type=StudentRequirementException.ExceptionType.WAIVER,
            is_waived=True,
            reason="Prior experience",
            effective_term=self.term,
            requested_by=self.user,
        )
        exception.approve(self.user, "Approved")

        # Check progress with exception
        progress_list = CanonicalRequirementService.get_student_progress(self.student, self.major)

        assert progress_list[0].is_completed
        assert not progress_list[1].is_completed
        assert progress_list[0].completion_method == "exception"
        assert progress_list[1].completion_method == "pending"

    def test_student_notification_service(self):
        """Test student notification service using degree audit."""
        # Get initial progress summary using degree audit
        audit = DegreeAuditService.generate_mobile_audit(self.student, self.major)

        # Audit returns comprehensive data including progress
        assert audit["progress_metrics"]["completion_percentage"] == 0
        assert audit["progress_metrics"]["completed_requirements"] == 0
        assert audit["progress_metrics"]["total_requirements"] == 2
        assert not audit["is_graduation_eligible"]
        assert len(audit["remaining_requirements"]) == 2

        # Add progress
        exception = StudentRequirementException.objects.create(
            student=self.student,
            canonical_requirement=self.req1,
            exception_type=StudentRequirementException.ExceptionType.WAIVER,
            is_waived=True,
            reason="Prior experience",
            effective_term=self.term,
            requested_by=self.user,
        )
        exception.approve(self.user, "Approved")

        # Check updated summary
        audit = DegreeAuditService.generate_mobile_audit(self.student, self.major)

        assert audit["progress_metrics"]["completion_percentage"] == 50
        assert audit["progress_metrics"]["completed_requirements"] == 1
        assert len(audit["remaining_requirements"]) == 1  # Only one remaining
        assert len(audit["completed_requirements"]) == 1  # One completed
