"""Tests for enrollment policies including capacity management and business rule enforcement.

This test suite ensures that enrollment policies correctly implement business rules
with proper authority checking and violation reporting for audit compliance.
"""

from datetime import date
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.common.policies.base import PolicyContext, PolicyResult, PolicySeverity
from apps.enrollment.policies.enrollment_policies import EnrollmentCapacityPolicy

User = get_user_model()


class TestEnrollmentCapacityPolicy(TestCase):
    """Test suite for ENRL_CAPACITY_001 - Enrollment Capacity Management Policy."""

    def setUp(self):
        """Set up test data for capacity policy testing."""
        self.policy = EnrollmentCapacityPolicy()

        # Create mock user with various authority levels
        self.regular_user = Mock(spec=User)
        self.regular_user.id = 1
        self.regular_user.email = "user@test.com"

        self.department_chair = Mock(spec=User)
        self.department_chair.id = 2
        self.department_chair.email = "chair@test.com"

        self.admin_user = Mock(spec=User)
        self.admin_user.id = 3
        self.admin_user.email = "admin@test.com"

        # Create mock department
        self.department = Mock()
        self.department.id = 1
        self.department.name = "Computer Science"

        # Create mock course
        self.course = Mock()
        self.course.id = 1
        self.course.code = "CS101"
        self.course.title = "Introduction to Programming"

        # Create mock class headers with different capacity scenarios
        self.class_with_capacity = Mock()
        self.class_with_capacity.id = 1
        self.class_with_capacity.max_enrollment = 25
        self.class_with_capacity.course = self.course

        self.class_at_capacity = Mock()
        self.class_at_capacity.id = 2
        self.class_at_capacity.max_enrollment = 20
        self.class_at_capacity.course = self.course

        self.unlimited_class = Mock()
        self.unlimited_class.id = 3
        self.unlimited_class.max_enrollment = None  # No limit
        self.unlimited_class.course = self.course

        # Create mock student
        self.student = Mock()
        self.student.id = 1
        self.student.student_id = "S2025001"

    def test_policy_metadata(self):
        """Test that policy has correct metadata for discovery."""
        self.assertEqual(self.policy.code, "ENRL_CAPACITY_001")
        self.assertEqual(self.policy.name, "Enrollment Capacity Management")
        self.assertIn("capacity limits", self.policy.description)

        metadata = self.policy.get_policy_metadata()
        self.assertIn("regulatory_reference", metadata)
        self.assertIn("University Enrollment Standards 3.1.2", metadata["regulatory_reference"])
        self.assertEqual(metadata["authority_levels"]["override"], 2)

    @patch("apps.enrollment.models.ClassHeaderEnrollment.objects")
    def test_evaluate_class_with_available_capacity(self, mock_enrollments):
        """Test policy allows enrollment when class has available spots."""
        # Mock 15 enrolled students in class with max 25
        mock_enrollments.filter.return_value.count.side_effect = [
            15,
            5,
        ]  # enrolled, waitlisted

        context = PolicyContext(
            user=self.regular_user,
            department=self.department,
            effective_date=date.today(),
        )

        result = self.policy.evaluate(context, class_header=self.class_with_capacity, student=self.student)

        self.assertEqual(result, PolicyResult.ALLOW)

    @patch("apps.enrollment.models.ClassHeaderEnrollment.objects")
    def test_evaluate_class_at_full_capacity_no_override(self, mock_enrollments):
        """Test policy denies enrollment when class is full and user has no override authority."""
        # Mock 20 enrolled students in class with max 20 (full capacity)
        mock_enrollments.filter.return_value.count.side_effect = [
            20,
            3,
        ]  # enrolled, waitlisted

        context = PolicyContext(
            user=self.regular_user,
            department=self.department,
            effective_date=date.today(),
        )

        with patch.object(self.policy, "_has_override_authority", return_value=False):
            result = self.policy.evaluate(context, class_header=self.class_at_capacity, student=self.student)

        self.assertEqual(result, PolicyResult.DENY)

    @patch("apps.enrollment.models.ClassHeaderEnrollment.objects")
    def test_evaluate_class_at_full_capacity_with_override(self, mock_enrollments):
        """Test policy requires override when class is full but user has override authority."""
        # Mock 20 enrolled students in class with max 20 (full capacity)
        mock_enrollments.filter.return_value.count.side_effect = [
            20,
            3,
        ]  # enrolled, waitlisted

        context = PolicyContext(
            user=self.department_chair,
            department=self.department,
            effective_date=date.today(),
        )

        with patch.object(self.policy, "_has_override_authority", return_value=True):
            result = self.policy.evaluate(context, class_header=self.class_at_capacity, student=self.student)

        self.assertEqual(result, PolicyResult.REQUIRE_OVERRIDE)

    def test_evaluate_missing_class_header(self):
        """Test policy denies when class_header is missing."""
        context = PolicyContext(
            user=self.regular_user,
            department=self.department,
            effective_date=date.today(),
        )

        result = self.policy.evaluate(context, student=self.student)
        self.assertEqual(result, PolicyResult.DENY)

    @patch("apps.enrollment.models.ClassHeaderEnrollment.objects")
    def test_get_violations_capacity_exceeded(self, mock_enrollments):
        """Test violation details when capacity is exceeded."""
        # Mock 20 enrolled students in class with max 20
        mock_enrollments.filter.return_value.count.side_effect = [
            20,
            3,
        ]  # enrolled, waitlisted

        context = PolicyContext(
            user=self.regular_user,
            department=self.department,
            effective_date=date.today(),
        )

        violations = self.policy.get_violations(context, class_header=self.class_at_capacity, student=self.student)

        self.assertEqual(len(violations), 1)
        violation = violations[0]

        self.assertEqual(violation.code, "CAPACITY_EXCEEDED")
        self.assertEqual(violation.severity, PolicySeverity.WARNING)
        self.assertEqual(violation.override_authority_required, 2)  # Department Chair
        self.assertIn("maximum capacity", violation.message)
        self.assertIn("20/20", violation.message)  # enrolled/max format

        # Check metadata
        self.assertEqual(violation.metadata["enrolled_count"], 20)
        self.assertEqual(violation.metadata["max_enrollment"], 20)
        self.assertEqual(violation.metadata["waitlisted_count"], 3)
        self.assertEqual(violation.metadata["available_spots"], 0)
        self.assertEqual(violation.metadata["course_code"], "CS101")

    def test_get_violations_missing_class_header(self):
        """Test violation when class_header is missing."""
        context = PolicyContext(
            user=self.regular_user,
            department=self.department,
            effective_date=date.today(),
        )

        violations = self.policy.get_violations(context, student=self.student)

        self.assertEqual(len(violations), 1)
        violation = violations[0]

        self.assertEqual(violation.code, "MISSING_CLASS_HEADER")
        self.assertEqual(violation.severity, PolicySeverity.ERROR)
        self.assertIn("Class header is required", violation.message)

    @patch("apps.enrollment.models.ClassHeaderEnrollment.objects")
    def test_calculate_capacity_info_with_available_spots(self, mock_enrollments):
        """Test capacity calculation when spots are available."""
        # Mock 15 enrolled, 3 waitlisted in class with max 25
        mock_enrollments.filter.return_value.count.side_effect = [15, 3]

        capacity_info = self.policy._calculate_capacity_info(self.class_with_capacity)

        expected = {
            "can_enroll": True,
            "enrolled_count": 15,
            "waitlisted_count": 3,
            "max_enrollment": 25,
            "available_spots": 10,
            "is_full": False,
        }

        self.assertEqual(capacity_info, expected)

    @patch("apps.enrollment.models.ClassHeaderEnrollment.objects")
    def test_calculate_capacity_info_at_capacity(self, mock_enrollments):
        """Test capacity calculation when class is at maximum."""
        # Mock 20 enrolled, 5 waitlisted in class with max 20
        mock_enrollments.filter.return_value.count.side_effect = [20, 5]

        capacity_info = self.policy._calculate_capacity_info(self.class_at_capacity)

        expected = {
            "can_enroll": False,
            "enrolled_count": 20,
            "waitlisted_count": 5,
            "max_enrollment": 20,
            "available_spots": 0,
            "is_full": True,
        }

        self.assertEqual(capacity_info, expected)

    @patch("apps.enrollment.models.ClassHeaderEnrollment.objects")
    def test_calculate_capacity_info_unlimited_class(self, mock_enrollments):
        """Test capacity calculation for class with no enrollment limit."""
        # Mock 50 enrolled in unlimited class (max_enrollment = None)
        mock_enrollments.filter.return_value.count.side_effect = [50, 2]

        capacity_info = self.policy._calculate_capacity_info(self.unlimited_class)

        expected = {
            "can_enroll": False,  # 0 max means no enrollment allowed
            "enrolled_count": 50,
            "waitlisted_count": 2,
            "max_enrollment": 0,  # None becomes 0
            "available_spots": 0,  # max(0, 0-50) = 0
            "is_full": True,  # 50 >= 0
        }

        self.assertEqual(capacity_info, expected)

    @patch("apps.accounts.services.AuthorityService")
    def test_has_override_authority_department_chair(self, mock_authority_service_class):
        """Test override authority check for department chair (level 2)."""
        mock_authority_service = Mock()
        mock_authority_service.has_authority_level.return_value = True
        mock_authority_service_class.return_value = mock_authority_service

        context = PolicyContext(
            user=self.department_chair,
            department=self.department,
            effective_date=date.today(),
        )

        has_authority = self.policy._has_override_authority(context, {})

        self.assertTrue(has_authority)
        mock_authority_service.has_authority_level.assert_called_once_with(
            required_level=2,
            department=self.department,
        )

    @patch("apps.accounts.services.AuthorityService")
    def test_has_override_authority_regular_user(self, mock_authority_service_class):
        """Test override authority check for regular user (no authority)."""
        mock_authority_service = Mock()
        mock_authority_service.has_authority_level.return_value = False
        mock_authority_service_class.return_value = mock_authority_service

        context = PolicyContext(
            user=self.regular_user,
            department=self.department,
            effective_date=date.today(),
        )

        has_authority = self.policy._has_override_authority(context, {})

        self.assertFalse(has_authority)

    def test_has_override_authority_no_user(self):
        """Test override authority check when no user in context."""
        context = PolicyContext(user=None, department=self.department, effective_date=date.today())

        has_authority = self.policy._has_override_authority(context, {})

        self.assertFalse(has_authority)

    @patch("apps.enrollment.models.ClassHeaderEnrollment.objects")
    def test_enrollment_status_filters(self, mock_enrollments):
        """Test that capacity calculation uses correct enrollment status filters."""
        # Call _calculate_capacity_info to trigger the ORM calls
        self.policy._calculate_capacity_info(self.class_with_capacity)

        # Verify the filter calls used correct status values
        filter_calls = mock_enrollments.filter.call_args_list

        # First call should filter for enrolled students (ENROLLED, ACTIVE)
        enrolled_filter = filter_calls[0][1]
        self.assertEqual(enrolled_filter["class_header"], self.class_with_capacity)
        self.assertEqual(enrolled_filter["status__in"], ["ENROLLED", "ACTIVE"])

        # Second call should filter for waitlisted students
        waitlist_filter = filter_calls[1][1]
        self.assertEqual(waitlist_filter["class_header"], self.class_with_capacity)
        self.assertEqual(waitlist_filter["status"], "WAITLISTED")

    def test_policy_integration_with_common_framework(self):
        """Test that policy correctly inherits from base Policy class."""
        # Verify it's a proper Policy subclass
        from apps.common.policies.base import Policy

        self.assertIsInstance(self.policy, Policy)

        # Verify required attributes exist
        self.assertTrue(hasattr(self.policy, "code"))
        self.assertTrue(hasattr(self.policy, "name"))
        self.assertTrue(hasattr(self.policy, "description"))
        self.assertTrue(hasattr(self.policy, "evaluate"))
        self.assertTrue(hasattr(self.policy, "get_violations"))

        # Verify code format follows convention
        self.assertRegex(self.policy.code, r"^[A-Z]+_[A-Z]+_\d{3}$")  # DOMAIN_CONCERN_VERSION
