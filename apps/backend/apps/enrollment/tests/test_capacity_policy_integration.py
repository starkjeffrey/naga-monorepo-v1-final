"""Integration tests for enrollment capacity policy with services and authority checking.

These tests verify that the EnrollmentCapacityPolicy correctly integrates with:
- CapacityService for capacity checking
- EnrollmentService for student enrollment
- AuthorityService for override authority validation
- Real database models and relationships

This test suite ensures end-to-end policy enforcement and audit compliance.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase

from apps.common.policies.base import PolicyResult, PolicySeverity
from apps.curriculum.models import Course, Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.enrollment.services import (
    CapacityService,
    EnrollmentService,
    EnrollmentStatus,
)
from apps.people.models import StudentProfile
from apps.scheduling.models import ClassHeader

User = get_user_model()


class CapacityPolicyIntegrationTest(TransactionTestCase):
    """Integration tests for capacity policy with real services and models."""

    def setUp(self):
        """Set up test data with real model instances."""
        # Create users with different authority levels
        self.regular_user = User.objects.create_user(email="regular@test.com", name="Regular User", is_staff=False)

        self.department_chair = User.objects.create_user(
            email="chair@test.com",
            name="Department Chair",
            is_staff=True,
        )

        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            name="System Admin",
            is_staff=True,
            is_superuser=True,
        )

        # Create academic entities
        self.term = Term.objects.create(
            name="Fall 2025",
            start_date=date(2025, 8, 15),
            end_date=date(2025, 12, 15),
            is_active=True,
        )

        self.course = Course.objects.create(
            code="CS101",
            title="Introduction to Programming",
            credits=Decimal("3.0"),
            is_active=True,
        )

        # Create class with limited capacity
        self.limited_class = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section="A",
            max_enrollment=20,
            status="ACTIVE",
        )

        # Create unlimited class (no capacity limit)
        self.unlimited_class = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section="B",
            max_enrollment=None,
            status="ACTIVE",
        )

        # Create test students
        self.student1 = StudentProfile.objects.create(
            user=User.objects.create_user(email="student1@test.com", name="Test Student 1"),
            student_id="S2025001",
            current_status=StudentProfile.Status.ACTIVE,
        )

        self.student2 = StudentProfile.objects.create(
            user=User.objects.create_user(email="student2@test.com", name="Test Student 2"),
            student_id="S2025002",
            current_status=StudentProfile.Status.ACTIVE,
        )

    def _create_enrollments(self, class_header, count, status="ENROLLED"):
        """Helper to create multiple enrollments for capacity testing."""
        enrollments = []
        for i in range(count):
            student = StudentProfile.objects.create(
                user=User.objects.create_user(email=f"enrolled{i}@test.com", name=f"Enrolled Student {i}"),
                student_id=f"S2025{i:03d}",
                current_status=StudentProfile.Status.ACTIVE,
            )
            enrollment = ClassHeaderEnrollment.objects.create(
                student=student,
                class_header=class_header,
                enrollment_date=date.today(),
                status=status,
                enrolled_by=self.regular_user,
            )
            enrollments.append(enrollment)
        return enrollments

    def test_capacity_service_policy_integration_with_available_space(self):
        """Test CapacityService with policy integration when space is available."""
        # Create 15 enrolled students in class with max 20
        self._create_enrollments(self.limited_class, 15, "ENROLLED")

        # Test with user context (policy-aware)
        capacity_info = CapacityService.check_enrollment_capacity(
            class_header=self.limited_class,
            user=self.regular_user,
            student=self.student1,
        )

        # Verify legacy capacity info is present
        self.assertEqual(capacity_info["enrolled_count"], 15)
        self.assertEqual(capacity_info["max_enrollment"], 20)
        self.assertEqual(capacity_info["available_spots"], 5)
        self.assertTrue(capacity_info["can_enroll"])
        self.assertFalse(capacity_info["is_full"])

        # Verify policy results are present
        self.assertEqual(capacity_info["policy_result"], PolicyResult.ALLOW)
        self.assertTrue(capacity_info["policy_allows_enrollment"])
        self.assertFalse(capacity_info["policy_requires_override"])
        self.assertEqual(len(capacity_info["policy_violations"]), 0)

    def test_capacity_service_policy_integration_at_capacity(self):
        """Test CapacityService with policy integration when at capacity."""
        # Create 20 enrolled students in class with max 20 (full capacity)
        self._create_enrollments(self.limited_class, 20, "ENROLLED")

        # Test with regular user (no override authority)
        capacity_info = CapacityService.check_enrollment_capacity(
            class_header=self.limited_class,
            user=self.regular_user,
            student=self.student1,
        )

        # Verify capacity is full
        self.assertEqual(capacity_info["enrolled_count"], 20)
        self.assertEqual(capacity_info["available_spots"], 0)
        self.assertTrue(capacity_info["is_full"])
        self.assertFalse(capacity_info["can_enroll"])  # Policy should deny

        # Verify policy results
        self.assertEqual(capacity_info["policy_result"], PolicyResult.DENY)
        self.assertFalse(capacity_info["policy_allows_enrollment"])
        self.assertFalse(capacity_info["policy_requires_override"])
        self.assertEqual(len(capacity_info["policy_violations"]), 1)

        # Check violation details
        violation = capacity_info["policy_violations"][0]
        self.assertEqual(violation.code, "CAPACITY_EXCEEDED")
        self.assertEqual(violation.severity, PolicySeverity.WARNING)
        self.assertEqual(violation.override_authority_required, 2)

    @patch("apps.accounts.services.AuthorityService")
    def test_capacity_service_with_override_authority(self, mock_authority_service_class):
        """Test CapacityService when user has override authority."""
        # Mock AuthorityService to return True for department chair
        mock_authority_service = Mock()
        mock_authority_service.has_authority_level.return_value = True
        mock_authority_service_class.return_value = mock_authority_service

        # Create full class
        self._create_enrollments(self.limited_class, 20, "ENROLLED")

        # Test with department chair (has override authority)
        capacity_info = CapacityService.check_enrollment_capacity(
            class_header=self.limited_class,
            user=self.department_chair,
            student=self.student1,
        )

        # Verify policy allows override
        self.assertEqual(capacity_info["policy_result"], PolicyResult.REQUIRE_OVERRIDE)
        self.assertTrue(capacity_info["can_enroll"])  # Should allow with override
        self.assertTrue(capacity_info["policy_requires_override"])
        self.assertTrue(capacity_info["can_override"])
        self.assertTrue(capacity_info.get("override_required", False))

        # Verify AuthorityService was called correctly
        mock_authority_service.has_authority_level.assert_called_once_with(
            required_level=2,
            department=None,  # No department in our test class
        )

    def test_capacity_service_backward_compatibility(self):
        """Test CapacityService maintains backward compatibility without user context."""
        # Create 15 enrolled students
        self._create_enrollments(self.limited_class, 15, "ENROLLED")

        # Test without user context (legacy mode)
        capacity_info = CapacityService.check_enrollment_capacity(self.limited_class)

        # Should have legacy format only
        expected_keys = {
            "can_enroll",
            "enrolled_count",
            "waitlisted_count",
            "max_enrollment",
            "available_spots",
            "is_full",
        }
        self.assertEqual(set(capacity_info.keys()), expected_keys)

        # Should not have policy-specific keys
        policy_keys = {"policy_result", "policy_allows_enrollment", "policy_violations"}
        self.assertTrue(policy_keys.isdisjoint(capacity_info.keys()))

        # Verify legacy calculation
        self.assertTrue(capacity_info["can_enroll"])
        self.assertEqual(capacity_info["enrolled_count"], 15)
        self.assertEqual(capacity_info["available_spots"], 5)

    @patch("apps.accounts.services.AuthorityService")
    def test_enrollment_service_integration_with_capacity_override(self, mock_authority_service_class):
        """Test EnrollmentService integration with capacity policy override."""
        # Mock AuthorityService for department chair
        mock_authority_service = Mock()
        mock_authority_service.has_authority_level.return_value = True
        mock_authority_service_class.return_value = mock_authority_service

        # Create full class (20/20 enrolled)
        self._create_enrollments(self.limited_class, 20, "ENROLLED")

        # Attempt enrollment with department chair (has override authority)
        result = EnrollmentService.enroll_student(
            student=self.student1,
            class_header=self.limited_class,
            enrolled_by=self.department_chair,
            override_capacity=False,  # Not using manual override
        )

        # Should succeed with policy override
        self.assertEqual(result.status, EnrollmentStatus.SUCCESS)
        self.assertIsNotNone(result.enrollment)
        self.assertEqual(result.enrollment.status, "ENROLLED")

        # Verify override is documented in notes
        self.assertIn("Capacity override authorized", result.enrollment.notes)
        self.assertIn(str(self.department_chair), result.enrollment.notes)
        self.assertIn("Policy violations:", result.enrollment.notes)

        # Verify capacity info in result details
        capacity_info = result.details["capacity_info"]
        self.assertEqual(capacity_info["policy_result"], PolicyResult.REQUIRE_OVERRIDE)
        self.assertTrue(capacity_info["can_override"])

    def test_enrollment_service_integration_without_override_authority(self):
        """Test EnrollmentService integration when user lacks override authority."""
        # Create full class (20/20 enrolled)
        self._create_enrollments(self.limited_class, 20, "ENROLLED")

        # Attempt enrollment with regular user (no override authority)
        result = EnrollmentService.enroll_student(
            student=self.student1,
            class_header=self.limited_class,
            enrolled_by=self.regular_user,
            override_capacity=False,
        )

        # Should be waitlisted due to capacity
        self.assertEqual(result.status, EnrollmentStatus.WAITLISTED)
        self.assertIsNotNone(result.enrollment)
        self.assertEqual(result.enrollment.status, "WAITLISTED")
        self.assertIsNotNone(result.enrollment.waitlist_position)

        # Verify policy was evaluated
        capacity_info = result.details["capacity_info"]
        self.assertEqual(capacity_info["policy_result"], PolicyResult.DENY)
        self.assertFalse(capacity_info["policy_allows_enrollment"])

    def test_enrollment_service_integration_with_manual_override(self):
        """Test EnrollmentService with manual capacity override parameter."""
        # Create full class (20/20 enrolled)
        self._create_enrollments(self.limited_class, 20, "ENROLLED")

        # Use manual override parameter (bypasses policy)
        result = EnrollmentService.enroll_student(
            student=self.student1,
            class_header=self.limited_class,
            enrolled_by=self.regular_user,
            override_capacity=True,  # Manual override
        )

        # Should succeed even without policy override authority
        self.assertEqual(result.status, EnrollmentStatus.SUCCESS)
        self.assertEqual(result.enrollment.status, "ENROLLED")
        self.assertIsNone(result.enrollment.waitlist_position)

    @patch("apps.accounts.services.AuthorityService")
    def test_repeat_enrollment_integration(self, mock_authority_service_class):
        """Test repeat enrollment method with capacity policy integration."""
        # Mock AuthorityService
        mock_authority_service = Mock()
        mock_authority_service.has_authority_level.return_value = True
        mock_authority_service_class.return_value = mock_authority_service

        # Create full class
        self._create_enrollments(self.limited_class, 20, "ENROLLED")

        # Test repeat enrollment with capacity override
        result = EnrollmentService.enroll_student_with_repeat_override(
            student=self.student1,
            class_header=self.limited_class,
            enrolled_by=self.department_chair,
            override_reason="Student needs to retake for grade improvement",
            override_capacity=False,
        )

        # Should succeed with both overrides documented
        self.assertEqual(result.status, EnrollmentStatus.SUCCESS)
        self.assertEqual(result.enrollment.status, "ENROLLED")

        # Verify both overrides are documented
        notes = result.enrollment.notes
        self.assertIn("REPEAT OVERRIDE: Student needs to retake for grade improvement", notes)
        self.assertIn("CAPACITY OVERRIDE:", notes)
        self.assertIn("Capacity override authorized", notes)

    def test_unlimited_capacity_class_policy_integration(self):
        """Test policy integration with unlimited capacity class."""
        # Test with unlimited capacity class (max_enrollment = None)
        capacity_info = CapacityService.check_enrollment_capacity(
            class_header=self.unlimited_class,
            user=self.regular_user,
            student=self.student1,
        )

        # Unlimited classes should deny enrollment (policy treats None as 0)
        self.assertFalse(capacity_info["can_enroll"])
        self.assertEqual(capacity_info["max_enrollment"], 0)  # None converted to 0
        self.assertEqual(capacity_info["policy_result"], PolicyResult.DENY)

    def test_policy_integration_error_handling(self):
        """Test error handling when policy classes are not available."""
        # Test graceful fallback when policy import fails
        with patch("apps.enrollment.services.EnrollmentCapacityPolicy", side_effect=ImportError):
            capacity_info = CapacityService.check_enrollment_capacity(
                class_header=self.limited_class,
                user=self.regular_user,
                student=self.student1,
            )

            # Should fall back to legacy behavior
            policy_keys = {
                "policy_result",
                "policy_allows_enrollment",
                "policy_violations",
            }
            self.assertTrue(policy_keys.isdisjoint(capacity_info.keys()))

    def test_end_to_end_enrollment_workflow(self):
        """Test complete enrollment workflow with policy integration."""
        # Start with empty class
        self.assertEqual(
            CapacityService.check_enrollment_capacity(self.limited_class)["enrolled_count"],
            0,
        )

        # Enroll students up to capacity
        for i in range(20):
            student = StudentProfile.objects.create(
                user=User.objects.create_user(email=f"workflow{i}@test.com", name=f"Workflow Student {i}"),
                student_id=f"W2025{i:03d}",
                current_status=StudentProfile.Status.ACTIVE,
            )

            result = EnrollmentService.enroll_student(
                student=student,
                class_header=self.limited_class,
                enrolled_by=self.regular_user,
            )

            self.assertEqual(result.status, EnrollmentStatus.SUCCESS)
            self.assertEqual(result.enrollment.status, "ENROLLED")

        # Verify class is now full
        capacity_info = CapacityService.check_enrollment_capacity(
            self.limited_class,
            user=self.regular_user,
            student=self.student1,
        )
        self.assertTrue(capacity_info["is_full"])
        self.assertEqual(capacity_info["enrolled_count"], 20)
        self.assertEqual(capacity_info["policy_result"], PolicyResult.DENY)

        # Next enrollment should be waitlisted
        result = EnrollmentService.enroll_student(
            student=self.student1,
            class_header=self.limited_class,
            enrolled_by=self.regular_user,
        )

        self.assertEqual(result.status, EnrollmentStatus.WAITLISTED)
        self.assertEqual(result.enrollment.status, "WAITLISTED")
        self.assertEqual(result.enrollment.waitlist_position, 1)
