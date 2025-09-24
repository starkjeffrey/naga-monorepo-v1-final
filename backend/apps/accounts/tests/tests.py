"""Tests for accounts app authorization system.

This module contains comprehensive tests for the role-based access control
system including models, services, permissions, and admin functionality.
Tests verify the core functionality works correctly and maintains clean
architecture principles.
"""

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.models import Department, Permission, Role, RolePermission, UserRole
from apps.accounts.services import PermissionService, RoleService, UserAccountService

User = get_user_model()

# Test constants
DEFAULT_DEPARTMENT_DISPLAY_ORDER = 100
EXPECTED_ROLE_COUNT = 2
EXPECTED_HIERARCHY_SIZE = 2


class DepartmentModelTest(TestCase):
    """Test Department model functionality."""

    def setUp(self):
        self.department = Department.objects.create(
            name="Computer Science",
            code="CS",
            description="Computer Science Department",
        )

    def test_department_creation(self):
        """Test department creation and string representation."""
        assert str(self.department) == "Computer Science (CS)"
        assert self.department.is_active
        assert self.department.display_order == DEFAULT_DEPARTMENT_DISPLAY_ORDER

    def test_department_code_uppercase(self):
        """Test that department codes are automatically uppercase."""
        dept = Department.objects.create(name="Math", code="math")
        dept.full_clean()
        assert dept.code == "MATH"


class RoleModelTest(TestCase):
    """Test Role model functionality."""

    def setUp(self):
        self.department = Department.objects.create(name="CS", code="CS")
        self.parent_role = Role.objects.create(
            name="Senior Teacher",
            role_type="TEACHER",
            department=self.department,
        )
        self.child_role = Role.objects.create(
            name="Junior Teacher",
            role_type="TEACHER",
            department=self.department,
            parent_role=self.parent_role,
        )

    def test_role_creation(self):
        """Test role creation and properties."""
        assert str(self.parent_role) == "Senior Teacher (CS)"
        assert not self.parent_role.is_global_role
        assert self.parent_role.can_view
        assert not self.parent_role.can_edit

    def test_global_role(self):
        """Test global role creation."""
        global_role = Role.objects.create(
            name="System Admin",
            role_type="DIRECTOR",
        )
        assert global_role.is_global_role
        assert str(global_role) == "System Admin (Global)"

    def test_circular_parent_validation(self):
        """Test that circular parent relationships are prevented."""
        self.parent_role.parent_role = self.child_role

        with pytest.raises(ValidationError):
            self.parent_role.full_clean()

    def test_permission_inheritance(self):
        """Test that child roles inherit parent permissions."""
        # Create a permission for the parent role
        permission = Permission.objects.create(
            name="View Grades",
            codename="view_grades",
        )
        RolePermission.objects.create(
            role=self.parent_role,
            permission=permission,
        )

        # Child role should inherit parent permissions
        parent_perms = self.parent_role.get_all_permissions()
        child_perms = self.child_role.get_all_permissions()

        assert "view_grades" in parent_perms
        assert "view_grades" in child_perms


class UserRoleModelTest(TestCase):
    """Test UserRole model functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )
        self.department = Department.objects.create(name="CS", code="CS")
        self.dept_role = Role.objects.create(
            name="Teacher",
            role_type="TEACHER",
            department=self.department,
        )
        self.global_role = Role.objects.create(
            name="Admin",
            role_type="DIRECTOR",
        )

    def test_user_role_creation(self):
        """Test user role assignment."""
        user_role = UserRole.objects.create(
            user=self.user,
            role=self.dept_role,
            department=self.department,
        )

        assert str(user_role) == f"{self.user.email} - Teacher in CS"
        assert user_role.is_active

    def test_department_required_validation(self):
        """Test that department-specific roles require department."""
        user_role = UserRole(
            user=self.user,
            role=self.dept_role,
            # No department specified
        )

        with pytest.raises(ValidationError):
            user_role.full_clean()

    def test_global_role_no_department(self):
        """Test that global roles should not have department."""
        user_role = UserRole(
            user=self.user,
            role=self.global_role,
            department=self.department,  # Should not be specified
        )

        with pytest.raises(ValidationError):
            user_role.full_clean()


class UserAccountServiceTest(TestCase):
    """Test UserAccountService functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="teacher@example.com",
            password="testpass123",
        )
        self.department = Department.objects.create(name="CS", code="CS")
        self.teacher_role = Role.objects.create(
            name="Teacher",
            role_type="TEACHER",
            department=self.department,
        )
        self.admin_role = Role.objects.create(
            name="Director",
            role_type="DIRECTOR",
        )

    def test_assign_role(self):
        """Test role assignment functionality."""
        user_role = UserAccountService.assign_role(
            user=self.user,
            role=self.teacher_role,
            department=self.department,
            notes="Initial assignment",
        )

        assert user_role.user == self.user
        assert user_role.role == self.teacher_role
        assert user_role.department == self.department
        assert user_role.is_active

    def test_has_role(self):
        """Test role checking functionality."""
        # Initially user has no roles
        assert not UserAccountService.has_role(self.user, "TEACHER", self.department)

        # Assign role
        UserAccountService.assign_role(
            user=self.user,
            role=self.teacher_role,
            department=self.department,
        )

        # Now user should have the role
        assert UserAccountService.has_role(self.user, "TEACHER", self.department)

    def test_remove_role(self):
        """Test role removal functionality."""
        # Assign role first
        UserAccountService.assign_role(
            user=self.user,
            role=self.teacher_role,
            department=self.department,
        )

        # Remove role
        result = UserAccountService.remove_role(
            user=self.user,
            role=self.teacher_role,
            department=self.department,
        )

        assert result
        assert not UserAccountService.has_role(self.user, "TEACHER", self.department)

    def test_get_user_roles(self):
        """Test getting user roles."""
        # Assign multiple roles
        UserAccountService.assign_role(
            user=self.user,
            role=self.teacher_role,
            department=self.department,
        )
        UserAccountService.assign_role(
            user=self.user,
            role=self.admin_role,
        )

        # Get all roles
        all_roles = UserAccountService.get_user_roles(self.user)
        assert all_roles.count() == EXPECTED_ROLE_COUNT

        # Get department-specific roles
        dept_roles = UserAccountService.get_user_roles(self.user, self.department)
        assert dept_roles.count() == 1
        assert dept_roles.first().role == self.teacher_role


class PermissionServiceTest(TestCase):
    """Test PermissionService functionality."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="testpass123",
        )
        self.department = Department.objects.create(name="CS", code="CS")
        self.role = Role.objects.create(
            name="Teacher",
            role_type="TEACHER",
            department=self.department,
        )
        self.permission = Permission.objects.create(
            name="View Grades",
            codename="view_grades",
        )

        # Assign permission to role
        RolePermission.objects.create(
            role=self.role,
            permission=self.permission,
            department=self.department,
        )

        # Assign role to user
        UserAccountService.assign_role(
            user=self.user,
            role=self.role,
            department=self.department,
        )

    def test_has_permission(self):
        """Test permission checking functionality."""
        # User should have the permission through role
        assert PermissionService.has_permission(
            self.user,
            "view_grades",
            None,
            self.department,
        )

        # User should not have non-existent permission
        assert not PermissionService.has_permission(
            self.user,
            "edit_grades",
            None,
            self.department,
        )

    def test_superuser_permissions(self):
        """Test that superusers have all permissions."""
        superuser = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
        )

        # Superuser should have any permission
        assert PermissionService.has_permission(superuser, "any_permission")

    def test_get_user_permissions(self):
        """Test getting all user permissions."""
        permissions = PermissionService.get_user_permissions(
            self.user,
            self.department,
        )

        assert "view_grades" in permissions


class RoleServiceTest(TestCase):
    """Test RoleService functionality."""

    def setUp(self):
        self.department = Department.objects.create(name="CS", code="CS")

    def test_create_role(self):
        """Test role creation service."""
        role = RoleService.create_role(
            name="Test Teacher",
            role_type="TEACHER",
            department=self.department,
            can_edit=True,
        )

        assert role.name == "Test Teacher"
        assert role.role_type == "TEACHER"
        assert role.department == self.department
        assert role.can_edit

    def test_invalid_role_type(self):
        """Test that invalid role types are rejected."""
        with pytest.raises(ValueError):
            RoleService.create_role(
                name="Invalid Role",
                role_type="INVALID_TYPE",
            )

    def test_role_hierarchy(self):
        """Test role hierarchy functionality."""
        parent = RoleService.create_role(
            name="Senior Teacher",
            role_type="TEACHER",
            department=self.department,
        )
        child = RoleService.create_role(
            name="Junior Teacher",
            role_type="TEACHER",
            department=self.department,
            parent_role=parent,
        )

        hierarchy = RoleService.get_role_hierarchy(child)
        assert len(hierarchy) == EXPECTED_HIERARCHY_SIZE
        assert hierarchy[0] == parent
        assert hierarchy[1] == child


class AccountsIntegrationTest(TestCase):
    """Integration tests for the complete accounts system."""

    def setUp(self):
        # Create test data
        self.department = Department.objects.create(name="Computer Science", code="CS")

        self.teacher_role = Role.objects.create(
            name="Teacher",
            role_type="TEACHER",
            department=self.department,
            can_view=True,
            can_edit=True,
        )

        self.permission = Permission.objects.create(
            name="View Student Grades",
            codename="view_student_grades",
        )

        RolePermission.objects.create(
            role=self.teacher_role,
            permission=self.permission,
            department=self.department,
        )

        self.teacher_user = User.objects.create_user(
            email="teacher@school.edu",
            password="teacherpass123",
        )

        self.student_user = User.objects.create_user(
            email="student@school.edu",
            password="studentpass123",
        )

    def test_complete_authorization_flow(self):
        """Test complete authorization flow from role assignment to permission checking."""
        # 1. Assign role to teacher
        UserAccountService.assign_role(
            user=self.teacher_user,
            role=self.teacher_role,
            department=self.department,
        )

        # 2. Teacher should have the role
        assert UserAccountService.has_role(
            self.teacher_user,
            "TEACHER",
            self.department,
        )

        # 3. Teacher should have the permission
        assert PermissionService.has_permission(
            self.teacher_user,
            "view_student_grades",
            None,
            self.department,
        )

        # 4. Student should not have teacher role or permission
        assert not UserAccountService.has_role(
            self.student_user,
            "TEACHER",
            self.department,
        )
        assert not PermissionService.has_permission(
            self.student_user,
            "view_student_grades",
            None,
            self.department,
        )

    def test_role_deactivation(self):
        """Test that deactivated roles don't grant permissions."""
        # Assign role
        user_role = UserAccountService.assign_role(
            user=self.teacher_user,
            role=self.teacher_role,
            department=self.department,
        )

        # Verify permission
        assert PermissionService.has_permission(
            self.teacher_user,
            "view_student_grades",
            None,
            self.department,
        )

        # Deactivate role assignment
        user_role.is_active = False
        user_role.save()

        # Should no longer have permission
        assert not PermissionService.has_permission(
            self.teacher_user,
            "view_student_grades",
            None,
            self.department,
        )
