"""Core business logic tests for academic app.

Tests the essential business logic without complex model dependencies:
- Transfer credit grade threshold logic
- Academic permission system
- Basic service functionality
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase

from apps.academic.models import (
    StudentCourseOverride,
    TransferCredit,
)
from apps.academic.services import (
    AcademicOverrideService,
    AcademicValidationService,
    TransferCreditService,
)
from apps.curriculum.models import Course, Division, Term
from apps.people.models import Person, StudentProfile

User = get_user_model()


class TransferGradeThresholdTest(TestCase):
    """Test transfer credit grade threshold business logic."""

    def setUp(self):
        """Set up test service."""
        self.service = AcademicValidationService()

    def test_acceptable_letter_grades(self):
        """Test that C+ and above letter grades meet transfer threshold."""
        acceptable_grades = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C"]
        for grade in acceptable_grades:
            with self.subTest(grade=grade):
                result = self.service._transfer_grade_meets_threshold(grade)
                self.assertTrue(result, f"Grade {grade} should be acceptable")

    def test_unacceptable_letter_grades(self):
        """Test that below C letter grades don't meet transfer threshold."""
        unacceptable_grades = ["C-", "D+", "D", "D-", "F"]
        for grade in unacceptable_grades:
            with self.subTest(grade=grade):
                result = self.service._transfer_grade_meets_threshold(grade)
                self.assertFalse(result, f"Grade {grade} should not be acceptable")

    def test_numeric_grade_thresholds(self):
        """Test numeric grade thresholds (77+ acceptable)."""
        # Acceptable numeric grades
        acceptable_numeric = ["77", "85", "90.5", "100"]
        for grade in acceptable_numeric:
            with self.subTest(grade=grade):
                result = self.service._transfer_grade_meets_threshold(grade)
                self.assertTrue(result, f"Numeric grade {grade} should be acceptable")

        # Unacceptable numeric grades
        unacceptable_numeric = ["76", "65.5", "50", "0"]
        for grade in unacceptable_numeric:
            with self.subTest(grade=grade):
                result = self.service._transfer_grade_meets_threshold(grade)
                self.assertFalse(result, f"Numeric grade {grade} should not be acceptable")

    def test_percentage_grade_thresholds(self):
        """Test percentage grade thresholds (77%+ acceptable)."""
        # Acceptable percentage grades
        acceptable_percent = ["77%", "85%", "100%"]
        for grade in acceptable_percent:
            with self.subTest(grade=grade):
                result = self.service._transfer_grade_meets_threshold(grade)
                self.assertTrue(result, f"Percentage grade {grade} should be acceptable")

        # Unacceptable percentage grades
        unacceptable_percent = ["76%", "60%", "45%"]
        for grade in unacceptable_percent:
            with self.subTest(grade=grade):
                result = self.service._transfer_grade_meets_threshold(grade)
                self.assertFalse(result, f"Percentage grade {grade} should not be acceptable")

    def test_edge_cases(self):
        """Test edge cases for grade threshold."""
        # Empty/invalid grades
        invalid_grades = ["", None, "Invalid", "  ", "XYZ"]
        for grade in invalid_grades:
            with self.subTest(grade=grade):
                result = self.service._transfer_grade_meets_threshold(grade)
                self.assertFalse(result, f"Invalid grade {grade} should not be acceptable")

    def test_case_insensitive_grades(self):
        """Test that grade checking is case insensitive."""
        # Lowercase should work
        result = self.service._transfer_grade_meets_threshold("b+")
        self.assertTrue(result, "Lowercase b+ should be acceptable")

        result = self.service._transfer_grade_meets_threshold("f")
        self.assertFalse(result, "Lowercase f should not be acceptable")


class AcademicPermissionTest(TestCase):
    """Test academic permission system."""

    def setUp(self):
        """Set up test users and permissions."""
        # Create users
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )
        self.regular_user = User.objects.create_user(
            email="user@test.com",
            password="testpass",
        )

        # Give admin user academic affairs permission
        academic_permission = Permission.objects.get(
            codename="can_approve_academic_affairs",
            content_type__app_label="academic",
        )
        self.admin_user.user_permissions.add(academic_permission)

    def test_admin_user_has_permission(self):
        """Test that admin user has academic approval permission."""
        result = AcademicValidationService._has_academic_approval_permission(self.admin_user)
        self.assertTrue(result, "Admin user should have academic approval permission")

    def test_regular_user_lacks_permission(self):
        """Test that regular user lacks academic approval permission."""
        result = AcademicValidationService._has_academic_approval_permission(self.regular_user)
        self.assertFalse(result, "Regular user should not have academic approval permission")

    def test_specific_permissions_also_work(self):
        """Test that specific permissions also grant approval rights."""
        # Give regular user specific transfer credit permission
        transfer_permission = Permission.objects.get(
            codename="can_approve_transfer_credit",
            content_type__app_label="academic",
        )
        self.regular_user.user_permissions.add(transfer_permission)

        result = AcademicValidationService._has_academic_approval_permission(self.regular_user)
        self.assertTrue(result, "User with specific permission should have approval rights")


class TransferCreditServiceTest(TestCase):
    """Test TransferCreditService with permission checking."""

    def setUp(self):
        """Set up test data."""
        # Create users
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )
        self.regular_user = User.objects.create_user(
            email="user@test.com",
            password="testpass",
        )

        # Give admin user academic affairs permission
        academic_permission = Permission.objects.get(
            codename="can_approve_academic_affairs",
            content_type__app_label="academic",
        )
        self.admin_user.user_permissions.add(academic_permission)

        # Create minimal academic structure
        self.person = Person.objects.create(
            personal_name="John",
            family_name="Doe",
            date_of_birth="1990-01-01",
        )

        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id=1001,
        )

    def test_evaluate_transfer_credit_with_permission(self):
        """Test transfer credit evaluation with proper permission."""
        transfer_credit = TransferCredit.objects.create(
            student=self.student,
            external_institution="Other University",
            external_course_code="COMP-101",
            external_course_title="Computer Programming",
            external_credits=Decimal("3.00"),
            external_grade="B",
            internal_credits=Decimal("3.00"),
            approval_status=TransferCredit.ApprovalStatus.PENDING,
        )

        # Should work with admin user (has permission)
        result = TransferCreditService.evaluate_transfer_credit(
            transfer_credit=transfer_credit,
            evaluator=self.admin_user,
            decision="approve",
            reason="Meets requirements",
        )

        self.assertEqual(result.approval_status, TransferCredit.ApprovalStatus.APPROVED)
        self.assertEqual(result.approved_by, self.admin_user)

    def test_evaluate_transfer_credit_without_permission(self):
        """Test transfer credit evaluation fails without permission."""
        transfer_credit = TransferCredit.objects.create(
            student=self.student,
            external_institution="Other University",
            external_course_code="COMP-101",
            external_course_title="Computer Programming",
            external_credits=Decimal("3.00"),
            external_grade="B",
            internal_credits=Decimal("3.00"),
            approval_status=TransferCredit.ApprovalStatus.PENDING,
        )

        # Should fail with regular user (no permission)
        with self.assertRaises(PermissionError) as context:
            TransferCreditService.evaluate_transfer_credit(
                transfer_credit=transfer_credit,
                evaluator=self.regular_user,
                decision="approve",
                reason="Meets requirements",
            )

        self.assertIn("permission", str(context.exception).lower())

    def test_evaluate_transfer_credit_reject(self):
        """Test rejecting transfer credit."""
        transfer_credit = TransferCredit.objects.create(
            student=self.student,
            external_institution="Other University",
            external_course_code="COMP-101",
            external_course_title="Computer Programming",
            external_credits=Decimal("3.00"),
            external_grade="F",  # Failing grade
            internal_credits=Decimal("3.00"),
            approval_status=TransferCredit.ApprovalStatus.PENDING,
        )

        result = TransferCreditService.evaluate_transfer_credit(
            transfer_credit=transfer_credit,
            evaluator=self.admin_user,
            decision="reject",
            reason="Grade too low",
        )

        self.assertEqual(result.approval_status, TransferCredit.ApprovalStatus.REJECTED)


class AcademicOverrideServiceTest(TestCase):
    """Test AcademicOverrideService with permission checking."""

    def setUp(self):
        """Set up test data."""
        # Create users
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )
        self.regular_user = User.objects.create_user(
            email="user@test.com",
            password="testpass",
        )

        # Give admin user academic affairs permission
        academic_permission = Permission.objects.get(
            codename="can_approve_academic_affairs",
            content_type__app_label="academic",
        )
        self.admin_user.user_permissions.add(academic_permission)

        # Create minimal academic structure
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

        self.course1 = Course.objects.create(
            code="MATH-101",
            title="College Algebra",
            short_title="College Algebra",
            division=self.division,
            credits=3,
        )

        self.course2 = Course.objects.create(
            code="MATH-110",
            title="Statistics",
            short_title="Statistics",
            division=self.division,
            credits=3,
        )

        self.term = Term.objects.create(
            name="Fall 2025",
            start_date="2025-09-01",
            end_date="2025-12-15",
            term_type=Term.TermType.BACHELORS,
        )

    def test_process_override_with_permission(self):
        """Test course override processing with proper permission."""
        override = StudentCourseOverride.objects.create(
            student=self.student,
            original_course=self.course1,
            substitute_course=self.course2,
            override_reason=StudentCourseOverride.OverrideReason.ACADEMIC_PETITION,
            detailed_reason="Valid substitution",
            effective_term=self.term,
            approval_status=StudentCourseOverride.ApprovalStatus.PENDING,
            requested_by=self.admin_user,
        )

        # Should work with admin user (has permission)
        result = AcademicOverrideService.process_override_request(
            override=override,
            approver=self.admin_user,
            decision="approve",
            notes="Approved after review",
        )

        self.assertEqual(result.approval_status, StudentCourseOverride.ApprovalStatus.APPROVED)

    def test_process_override_without_permission(self):
        """Test course override processing fails without permission."""
        override = StudentCourseOverride.objects.create(
            student=self.student,
            original_course=self.course1,
            substitute_course=self.course2,
            override_reason=StudentCourseOverride.OverrideReason.ACADEMIC_PETITION,
            detailed_reason="Valid substitution",
            effective_term=self.term,
            approval_status=StudentCourseOverride.ApprovalStatus.PENDING,
            requested_by=self.admin_user,
        )

        # Should fail with regular user (no permission)
        with self.assertRaises(PermissionError) as context:
            AcademicOverrideService.process_override_request(
                override=override,
                approver=self.regular_user,
                decision="approve",
                notes="Approved after review",
            )

        self.assertIn("permission", str(context.exception).lower())

    def test_process_override_reject(self):
        """Test rejecting course override."""
        override = StudentCourseOverride.objects.create(
            student=self.student,
            original_course=self.course1,
            substitute_course=self.course2,
            override_reason=StudentCourseOverride.OverrideReason.ACADEMIC_PETITION,
            detailed_reason="Questionable substitution",
            effective_term=self.term,
            approval_status=StudentCourseOverride.ApprovalStatus.PENDING,
            requested_by=self.admin_user,
        )

        result = AcademicOverrideService.process_override_request(
            override=override,
            approver=self.admin_user,
            decision="reject",
            notes="Substitution not equivalent",
        )

        self.assertEqual(result.approval_status, StudentCourseOverride.ApprovalStatus.REJECTED)
