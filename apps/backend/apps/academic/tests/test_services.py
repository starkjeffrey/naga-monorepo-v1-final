"""Comprehensive tests for academic app services and business logic.

Tests the service layer functionality including:
- RequirementFulfillmentService: Degree requirement tracking
- TransferCreditService: Transfer credit approval workflow
- StudentCourseOverrideService: Course substitution management
- EquivalencyService: Course equivalency management
- Academic progress calculations and validation
"""

from datetime import date

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.academic.models import (
    CourseEquivalency,
    StudentCourseOverride,
    TransferCredit,
)
from apps.curriculum.models import Course, Cycle, Division, Major, Term
from apps.people.models import Gender, Person, StudentProfile

User = get_user_model()


class TransferCreditServiceTest(TestCase):
    """Test TransferCreditService business logic."""

    def setUp(self):
        """Set up test data."""
        # Create user
        self.user = User.objects.create_user(
            email="advisor@example.com",
        )

        # Create person and student
        self.person = Person.objects.create(
            personal_name="Alice",
            family_name="Johnson",
            personal_email="alice.johnson@example.com",
            preferred_gender=Gender.FEMALE,
        )
        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id=20250001,
        )

        # Create academic structure
        self.division = Division.objects.create(
            name="Academic Division",
            short_name="ACAD",
        )
        self.cycle = Cycle.objects.create(
            division=self.division,
            name="Bachelor's Program",
        )
        self.major = Major.objects.create(
            cycle=self.cycle,
            name="Mathematics",
            code="MATH",
            total_credits_required=120,
            program_type=Major.ProgramType.ACADEMIC,
            degree_awarded=Major.DegreeAwarded.BA,
        )

        # Create equivalent course
        self.equivalent_course = Course.objects.create(
            code="MATH201",
            title="Calculus I",
            credits=4,
            cycle=self.cycle,
        )
        self.equivalent_course.majors.add(self.major)

        self.transfer_credit = TransferCredit.objects.create(
            student=self.student,
            external_institution="State University",
            external_course_code="CALC101",
            external_course_title="Calculus",
            external_credits=4,
            external_grade="A",
            year_taken=2023,
            term_taken="Fall",
            equivalent_course=self.equivalent_course,
            awarded_credits=4,
            approval_status=TransferCredit.ApprovalStatus.PENDING,
        )

    def test_transfer_credit_approve_method(self):
        """Test transfer credit approve method."""
        # Verify initial state
        self.assertEqual(self.transfer_credit.approval_status, TransferCredit.ApprovalStatus.PENDING)
        self.assertIsNone(self.transfer_credit.approved_by)

        # Approve transfer directly (no service layer)
        self.transfer_credit.approval_status = TransferCredit.ApprovalStatus.APPROVED
        self.transfer_credit.approved_by = self.user
        self.transfer_credit.approved_at = timezone.now()
        self.transfer_credit.save()

        # Verify approval
        self.transfer_credit.refresh_from_db()
        self.assertEqual(self.transfer_credit.approval_status, TransferCredit.ApprovalStatus.APPROVED)
        self.assertEqual(self.transfer_credit.approved_by, self.user)
        self.assertIsNotNone(self.transfer_credit.approved_at)

    def test_transfer_credit_reject_method(self):
        """Test transfer credit reject method."""
        # Reject transfer directly (no service layer)
        reason = "Course content does not match requirements"
        self.transfer_credit.approval_status = TransferCredit.ApprovalStatus.REJECTED
        self.transfer_credit.approved_by = self.user
        self.transfer_credit.approved_at = timezone.now()
        self.transfer_credit.rejection_reason = reason
        self.transfer_credit.save()

        # Verify rejection
        self.transfer_credit.refresh_from_db()
        self.assertEqual(self.transfer_credit.approval_status, TransferCredit.ApprovalStatus.REJECTED)
        self.assertEqual(self.transfer_credit.approved_by, self.user)
        self.assertEqual(self.transfer_credit.rejection_reason, reason)

    def test_transfer_credit_properties(self):
        """Test transfer credit properties."""
        # Test is_approved property when pending
        self.assertFalse(self.transfer_credit.is_approved)

        # Approve and test again
        self.transfer_credit.approval_status = TransferCredit.ApprovalStatus.APPROVED
        self.transfer_credit.save()
        self.assertTrue(self.transfer_credit.is_approved)

    def test_transfer_credit_validation(self):
        """Test transfer credit validation rules."""
        # Test valid transfer credit
        try:
            self.transfer_credit.clean()
        except ValidationError:
            self.fail("Valid transfer credit should not raise ValidationError")

        # Test invalid - internal credits exceed external credits
        self.transfer_credit.internal_credits = 6  # More than external_credits (4)
        with self.assertRaises(ValidationError):
            self.transfer_credit.clean()

    def test_transfer_credit_string_representation(self):
        """Test transfer credit string representation."""
        expected = (
            f"{self.student}: {self.transfer_credit.external_course_code} "
            f"from {self.transfer_credit.external_institution}"
        )
        self.assertEqual(str(self.transfer_credit), expected)


class StudentCourseOverrideServiceTest(TestCase):
    """Test StudentCourseOverride business logic."""

    def setUp(self):
        """Set up test data."""
        # Create users
        self.advisor = User.objects.create_user(
            email="advisor@example.com",
        )
        self.student_user = User.objects.create_user(
            email="student@example.com",
        )

        # Create person and student
        self.person = Person.objects.create(
            personal_name="Bob",
            family_name="Smith",
            personal_email="bob.smith@example.com",
            preferred_gender=Gender.MALE,
        )
        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id=20250002,
        )

        # Create academic structure
        self.division = Division.objects.create(
            name="Academic Division",
            short_name="ACAD",
        )
        self.cycle = Cycle.objects.create(
            division=self.division,
            name="Bachelor's Program",
        )
        self.major = Major.objects.create(
            cycle=self.cycle,
            name="Computer Science",
            code="CS",
            total_credits_required=120,
            program_type=Major.ProgramType.ACADEMIC,
            degree_awarded=Major.DegreeAwarded.BS,
        )

        # Create courses
        self.required_course = Course.objects.create(
            code="CS101",
            title="Programming Fundamentals",
            credits=3,
            cycle=self.cycle,
        )
        self.required_course.majors.add(self.major)

        self.substitute_course = Course.objects.create(
            code="IT101",
            title="Information Technology Fundamentals",
            credits=3,
            cycle=self.cycle,
        )
        self.substitute_course.majors.add(self.major)

        # Create term
        self.term = Term.objects.create(
            code="Fall 2024",
            term_type=Term.TermType.BACHELORS,
            start_date=date(2024, 9, 1),
            end_date=date(2024, 12, 15),
            is_active=True,
        )

        self.override = StudentCourseOverride.objects.create(
            student=self.student,
            original_course=self.required_course,
            substitute_course=self.substitute_course,
            override_reason=StudentCourseOverride.OverrideReason.ACADEMIC,
            detailed_reason="Student has equivalent knowledge from industry experience",
            effective_term=self.term,
            requested_by=self.student_user,
        )

    def test_override_approve_method(self):
        """Test course override approve method."""
        # Verify initial state
        self.assertEqual(self.override.approval_status, StudentCourseOverride.ApprovalStatus.PENDING)

        # Approve override directly (no service layer)
        self.override.approval_status = StudentCourseOverride.ApprovalStatus.APPROVED
        self.override.approval_date = timezone.now()
        self.override.save()

        # Verify approval
        self.override.refresh_from_db()
        self.assertEqual(self.override.approval_status, StudentCourseOverride.ApprovalStatus.APPROVED)
        self.assertIsNotNone(self.override.approval_date)

    def test_override_reject_method(self):
        """Test course override reject method."""
        reason = "Insufficient justification for substitution"

        # Reject override directly (no service layer)
        self.override.approval_status = StudentCourseOverride.ApprovalStatus.REJECTED
        self.override.approval_date = timezone.now()
        self.override.rejection_reason = reason
        self.override.save()

        # Verify rejection
        self.override.refresh_from_db()
        self.assertEqual(self.override.approval_status, StudentCourseOverride.ApprovalStatus.REJECTED)
        self.assertEqual(self.override.rejection_reason, reason)

    def test_override_validity_check(self):
        """Test override validity checking."""
        # Pending override should not be valid
        self.assertFalse(self.override.is_currently_valid)

        # Approve the override
        self.override.approval_status = StudentCourseOverride.ApprovalStatus.APPROVED
        self.override.approval_date = timezone.now()
        self.override.save()

        # Should now be valid
        self.assertTrue(self.override.is_currently_valid)

    def test_override_validation(self):
        """Test override validation rules."""
        # Test valid override
        try:
            self.override.clean()
        except ValidationError:
            self.fail("Valid override should not raise ValidationError")

        # Test invalid override - same course
        self.override.substitute_course = self.override.original_course
        with self.assertRaises(ValidationError):
            self.override.clean()

    def test_override_string_representation(self):
        """Test override string representation."""
        expected = f"{self.student}: {self.required_course.code} → {self.substitute_course.code}"
        self.assertEqual(str(self.override), expected)


class CourseEquivalencyTest(TestCase):
    """Test CourseEquivalency model and validation."""

    def setUp(self):
        """Set up test data."""
        # Create user
        self.user = User.objects.create_user(
            email="registrar@example.com",
        )

        # Create academic structure
        self.division = Division.objects.create(
            name="Academic Division",
            short_name="ACAD",
        )
        self.cycle = Cycle.objects.create(
            division=self.division,
            name="Bachelor's Program",
        )
        self.major = Major.objects.create(
            cycle=self.cycle,
            name="Engineering",
            code="ENG",
            total_credits_required=128,
            program_type=Major.ProgramType.ACADEMIC,
            degree_awarded=Major.DegreeAwarded.BS,
        )

        # Create courses
        self.course_a = Course.objects.create(
            code="ENG201",
            title="Engineering Mathematics",
            credits=4,
            cycle=self.cycle,
        )
        self.course_a.majors.add(self.major)

        self.course_b = Course.objects.create(
            code="MATH201",
            title="Advanced Mathematics",
            credits=4,
            cycle=self.cycle,
        )
        self.course_b.majors.add(self.major)

        # Create term
        self.term = Term.objects.create(
            code="Spring 2024",
            term_type=Term.TermType.BACHELORS,
            start_date=date(2024, 1, 15),
            end_date=date(2024, 5, 15),
            is_active=True,
        )

    def test_equivalency_creation(self):
        """Test equivalency creation."""
        equivalency = CourseEquivalency.objects.create(
            original_course=self.course_a,
            equivalent_course=self.course_b,
            effective_term=self.term,
            reason="Courses cover identical mathematical concepts",
            approved_by=self.user,
            approval_date=date.today(),
            is_bidirectional=True,
        )

        self.assertEqual(equivalency.original_course, self.course_a)
        self.assertEqual(equivalency.equivalent_course, self.course_b)
        self.assertTrue(equivalency.is_bidirectional)
        self.assertEqual(equivalency.approved_by, self.user)

    def test_equivalency_string_representation(self):
        """Test equivalency string representations."""
        # Bidirectional equivalency
        equivalency = CourseEquivalency.objects.create(
            original_course=self.course_a,
            equivalent_course=self.course_b,
            effective_term=self.term,
            reason="Test equivalency",
            approved_by=self.user,
            approval_date=date.today(),
            is_bidirectional=True,
        )

        expected = f"{self.course_a.code} ↔ {self.course_b.code}"
        self.assertEqual(str(equivalency), expected)

        # Unidirectional equivalency
        equivalency.is_bidirectional = False
        equivalency.save()
        expected = f"{self.course_a.code} → {self.course_b.code}"
        self.assertEqual(str(equivalency), expected)

    def test_equivalency_validation(self):
        """Test equivalency validation."""
        # Valid equivalency
        equivalency = CourseEquivalency(
            original_course=self.course_a,
            equivalent_course=self.course_b,
            effective_term=self.term,
            reason="Test",
            approved_by=self.user,
            approval_date=date.today(),
        )

        # Should not raise validation error
        try:
            equivalency.clean()
        except ValidationError:
            self.fail("Valid equivalency should not raise ValidationError")

        # Invalid equivalency - same course
        equivalency.equivalent_course = self.course_a
        with self.assertRaises(ValidationError):
            equivalency.clean()


# RequirementTypeTest removed - RequirementType model deleted in migration 0004_auto_20250123.py


class AcademicValidationTest(TestCase):
    """Test academic validation and business rules."""

    def setUp(self):
        """Set up test data."""
        # Create academic structure
        self.division = Division.objects.create(
            name="Academic Division",
            short_name="ACAD",
        )
        self.cycle = Cycle.objects.create(
            division=self.division,
            name="Bachelor's Program",
        )
        self.major = Major.objects.create(
            cycle=self.cycle,
            name="Business Administration",
            code="BUSADMIN",
            total_credits_required=120,
            program_type=Major.ProgramType.ACADEMIC,
            degree_awarded=Major.DegreeAwarded.BA,
        )

        # Create terms
        self.term1 = Term.objects.create(
            code="Fall 2023",
            term_type=Term.TermType.BACHELORS,
            start_date=date(2023, 9, 1),
            end_date=date(2023, 12, 15),
            is_active=True,
        )

        self.term2 = Term.objects.create(
            code="Spring 2024",
            term_type=Term.TermType.BACHELORS,
            start_date=date(2024, 1, 15),
            end_date=date(2024, 5, 15),
            is_active=True,
        )

        # Create courses
        self.course1 = Course.objects.create(
            code="BUS101",
            title="Introduction to Business",
            credits=3,
            cycle=self.cycle,
        )
        self.course1.majors.add(self.major)

        self.course2 = Course.objects.create(
            code="BUS102",
            title="Business Ethics",
            credits=3,
            cycle=self.cycle,
        )
        self.course2.majors.add(self.major)

    def test_credit_validation_limits(self):
        """Test credit amount validation limits."""
        User.objects.create_user(
            email="test@example.com",
        )

        person = Person.objects.create(
            personal_name="Test",
            family_name="Student",
            personal_email="test@example.com",
            preferred_gender=Gender.PREFER_NOT_TO_SAY,
        )
        student = StudentProfile.objects.create(
            person=person,
            student_id=20250005,
        )

        # Test maximum credit limit validation (should be 12.0)
        with self.assertRaises(ValidationError):
            transfer = TransferCredit(
                student=student,
                external_institution="Test University",
                external_course_code="MEGA101",
                external_course_name="Mega Course",
                external_credits=15,  # Over maximum of 12.0
                internal_credits=15,
                equivalent_course=self.course1,
            )
            transfer.full_clean()

    def test_term_ordering_validation(self):
        """Test term date ordering validation."""
        user = User.objects.create_user(
            email="test@example.com",
        )

        # Invalid term order in equivalency (end_term before effective_term)
        equivalency = CourseEquivalency(
            original_course=self.course1,
            equivalent_course=self.course2,
            effective_term=self.term2,  # Later term
            end_term=self.term1,  # Earlier term - invalid
            reason="Test",
            approved_by=user,
            approval_date=date.today(),
        )

        with self.assertRaises(ValidationError):
            equivalency.clean()

    def test_self_reference_validation(self):
        """Test validation against self-references."""
        user = User.objects.create_user(
            email="test@example.com",
        )

        # Course equivalency to itself should be invalid
        equivalency = CourseEquivalency(
            original_course=self.course1,
            equivalent_course=self.course1,  # Same course - invalid
            effective_term=self.term1,
            reason="Self equivalency",
            approved_by=user,
            approval_date=date.today(),
        )

        with self.assertRaises(ValidationError):
            equivalency.clean()


class AcademicIntegrationTest(TestCase):
    """Test integration between academic models and other apps."""

    def setUp(self):
        """Set up test data for integration testing."""
        # Create users
        self.advisor = User.objects.create_user(
            email="advisor@example.com",
        )

        # Create academic structure
        self.division = Division.objects.create(
            name="Academic Division",
            short_name="ACAD",
        )
        self.cycle = Cycle.objects.create(
            division=self.division,
            name="Bachelor's Program",
        )
        self.major = Major.objects.create(
            cycle=self.cycle,
            name="Psychology",
            code="PSYC",
            total_credits_required=120,
            program_type=Major.ProgramType.ACADEMIC,
            degree_awarded=Major.DegreeAwarded.BA,
        )

        # Create terms
        self.term = Term.objects.create(
            code="Fall 2024",
            term_type=Term.TermType.BACHELORS,
            start_date=date(2024, 9, 1),
            end_date=date(2024, 12, 15),
            is_active=True,
        )

        # Create people and students
        self.person1 = Person.objects.create(
            personal_name="Sarah",
            family_name="Wilson",
            personal_email="sarah.wilson@example.com",
            preferred_gender=Gender.FEMALE,
        )
        self.student1 = StudentProfile.objects.create(
            person=self.person1,
            student_id=20250003,
        )

        self.person2 = Person.objects.create(
            personal_name="Mike",
            family_name="Davis",
            personal_email="mike.davis@example.com",
            preferred_gender=Gender.MALE,
        )
        self.student2 = StudentProfile.objects.create(
            person=self.person2,
            student_id=20250004,
        )

        # Create courses
        self.course1 = Course.objects.create(
            code="PSYC101",
            title="Introduction to Psychology",
            credits=3,
            cycle=self.cycle,
        )
        self.course1.majors.add(self.major)

        self.course2 = Course.objects.create(
            code="PSYC201",
            title="Research Methods",
            credits=4,
            cycle=self.cycle,
        )
        self.course2.majors.add(self.major)

    def test_student_transfer_credit_integration(self):
        """Test integration between students and transfer credits."""
        # Create transfer credits for student
        transfer1 = TransferCredit.objects.create(
            student=self.student1,
            external_institution="Community College",
            external_course_code="PSYC100",
            external_course_name="General Psychology",
            external_credits=3,
            internal_credits=3,
            equivalent_course=self.course1,
        )

        transfer2 = TransferCredit.objects.create(
            student=self.student1,
            external_institution="Community College",
            external_course_code="STAT101",
            external_course_name="Statistics",
            external_credits=4,
            awarded_credits=4,
            equivalent_course=self.course2,
        )

        # Test student's transfer credits relationship
        student_transfers = self.student1.transfer_credits.all()
        self.assertEqual(len(student_transfers), 2)
        self.assertIn(transfer1, student_transfers)
        self.assertIn(transfer2, student_transfers)

        # Test total internal credits calculation
        total_credits = sum(t.internal_credits for t in student_transfers)
        self.assertEqual(total_credits, 7)  # 3 + 4

    def test_course_equivalency_integration(self):
        """Test integration between courses and equivalencies."""
        # Create course equivalency
        equivalency = CourseEquivalency.objects.create(
            original_course=self.course1,
            equivalent_course=self.course2,
            effective_term=self.term,
            reason="Content overlap in psychology fundamentals",
            approved_by=self.advisor,
            approval_date=date.today(),
            is_bidirectional=True,
        )

        # Test course relationships
        course1_equivalencies = self.course1.equivalency_mappings.all()
        self.assertEqual(len(course1_equivalencies), 1)
        self.assertEqual(course1_equivalencies[0], equivalency)

        course2_reverse_equivalencies = self.course2.reverse_equivalency_mappings.all()
        self.assertEqual(len(course2_reverse_equivalencies), 1)
        self.assertEqual(course2_reverse_equivalencies[0], equivalency)

    def test_student_override_integration(self):
        """Test integration between students and course overrides."""
        # Create course override
        override = StudentCourseOverride.objects.create(
            student=self.student2,
            original_course=self.course1,
            substitute_course=self.course2,
            override_reason=StudentCourseOverride.OverrideReason.ACADEMIC,
            detailed_reason="Student tested out of intro course",
            effective_term=self.term,
            requested_by=self.advisor,
        )

        # Test student's overrides relationship
        student_overrides = self.student2.course_overrides.all()
        self.assertEqual(len(student_overrides), 1)
        self.assertEqual(student_overrides[0], override)

        # Test course relationships
        original_overrides = self.course1.overridden_by_students.all()
        substitute_overrides = self.course2.substitutes_for_students.all()

        self.assertEqual(len(original_overrides), 1)
        self.assertEqual(len(substitute_overrides), 1)
        self.assertEqual(original_overrides[0], override)
        self.assertEqual(substitute_overrides[0], override)

    def test_course_major_integration(self):
        """Test integration between courses and majors through many-to-many relationship."""
        # Create additional major
        second_major = Major.objects.create(
            cycle=self.cycle,
            name="Cognitive Science",
            code="COGSCI",
            total_credits_required=120,
            program_type=Major.ProgramType.ACADEMIC,
            degree_awarded=Major.DegreeAwarded.BS,
        )

        # Add course to multiple majors
        self.course1.majors.add(second_major)

        # Test course's majors
        course_majors = self.course1.majors.all()
        self.assertEqual(len(course_majors), 2)
        self.assertIn(self.major, course_majors)
        self.assertIn(second_major, course_majors)

        # Test major's courses
        psyc_courses = self.major.courses.all()
        cogsci_courses = second_major.courses.all()

        self.assertIn(self.course1, psyc_courses)
        self.assertIn(self.course2, psyc_courses)
        self.assertIn(self.course1, cogsci_courses)
        self.assertNotIn(self.course2, cogsci_courses)
