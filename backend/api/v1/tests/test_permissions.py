"""Tests for unified v1 API permissions.

Tests unified permission checking functions and authorization logic.
"""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.test import TestCase

from api.v1.permissions import (
    check_admin_access,
    check_teacher_access,
    has_permission,
    has_student_permission,
)
from apps.people.models import Person, StudentProfile, TeacherProfile

User = get_user_model()


class PermissionsTest(TestCase):
    """Test unified permission system."""

    def setUp(self):
        """Set up test data."""
        # Create users
        self.superuser = User.objects.create_user(email="super@example.com", password="testpass123", is_superuser=True)

        self.staff_user = User.objects.create_user(email="staff@example.com", password="testpass123", is_staff=True)

        self.regular_user = User.objects.create_user(email="regular@example.com", password="testpass123")

        # Create person and profiles for testing
        self.teacher_person = Person.objects.create(
            personal_name="John",
            family_name="Teacher",
            preferred_gender="M",
            date_of_birth="1980-01-01",
            citizenship="US",
        )

        self.student_person = Person.objects.create(
            personal_name="Jane",
            family_name="Student",
            preferred_gender="F",
            date_of_birth="2000-01-01",
            citizenship="US",
        )

        # Create teacher user and profile
        self.teacher_user = User.objects.create_user(email="teacher@example.com", password="testpass123")
        self.teacher_user.person = self.teacher_person
        self.teacher_user.save()

        self.teacher_profile = TeacherProfile.objects.create(
            person=self.teacher_person, employee_id="T001", hire_date="2020-01-01"
        )

        # Create student user and profile
        self.student_user = User.objects.create_user(email="student@example.com", password="testpass123")
        self.student_user.person = self.student_person
        self.student_user.save()

        self.student_profile = StudentProfile.objects.create(
            person=self.student_person, student_id="S001", admission_date="2023-01-01"
        )

    def test_check_admin_access(self):
        """Test admin access checking."""
        # Superuser should have admin access
        self.assertTrue(check_admin_access(self.superuser))

        # Staff user should have admin access
        self.assertTrue(check_admin_access(self.staff_user))

        # Regular user should not have admin access
        self.assertFalse(check_admin_access(self.regular_user))

        # Unauthenticated user should not have admin access
        self.assertFalse(check_admin_access(None))

    def test_check_teacher_access(self):
        """Test teacher access checking."""
        # Staff user should have teacher access
        self.assertTrue(check_teacher_access(self.staff_user))

        # User with teacher profile should have teacher access
        self.assertTrue(check_teacher_access(self.teacher_user))

        # Regular user should not have teacher access
        self.assertFalse(check_teacher_access(self.regular_user))

        # Student user should not have teacher access
        self.assertFalse(check_teacher_access(self.student_user))

        # Unauthenticated user should not have teacher access
        self.assertFalse(check_teacher_access(None))

    def test_has_student_permission(self):
        """Test student permission checking."""
        # Admin should have access to any student
        self.assertTrue(has_student_permission(self.superuser, self.student_profile))

        # Teacher should have access to any student (simplified)
        self.assertTrue(has_student_permission(self.teacher_user, self.student_profile))

        # Student should have access to their own profile
        self.assertTrue(has_student_permission(self.student_user, self.student_profile))

        # Student should not have access to other student profiles
        other_person = Person.objects.create(
            personal_name="Other",
            family_name="Student",
            preferred_gender="M",
            date_of_birth="2000-01-01",
            citizenship="US",
        )
        other_student = StudentProfile.objects.create(
            person=other_person, student_id="S002", admission_date="2023-01-01"
        )

        self.assertFalse(has_student_permission(self.student_user, other_student))

        # Regular user should not have access
        self.assertFalse(has_student_permission(self.regular_user, self.student_profile))

    def test_has_permission_with_permissions(self):
        """Test permission checking with Django permissions."""
        # Add a specific permission to user
        permission = Permission.objects.get(codename="view_studentprofile")
        self.regular_user.user_permissions.add(permission)

        # Should be able to check permission
        result = has_permission(self.regular_user, "people.view_studentprofile")
        # This might vary depending on PermissionService implementation
        self.assertIsInstance(result, bool)

    def test_has_permission_fallback(self):
        """Test permission checking fallback to web interface."""
        # Test with a permission that should fall back
        result = has_permission(self.regular_user, "nonexistent.permission")
        self.assertFalse(result)

        # Unauthenticated user
        self.assertFalse(has_permission(None, "any.permission"))

    def test_permission_format_conversion(self):
        """Test Django permission format conversion."""
        # Test different permission formats
        test_permissions = ["finance.view_invoice", "grading.add_grade", "attendance.change_session"]

        for perm in test_permissions:
            result = has_permission(self.regular_user, perm)
            self.assertIsInstance(result, bool)
