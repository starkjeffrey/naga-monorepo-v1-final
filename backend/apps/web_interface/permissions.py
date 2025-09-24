"""
Role-based permissions for the web interface.

This module defines permission classes and mixins for controlling access
to views based on user roles in the Naga SIS system.
"""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


class RoleBasedPermissionMixin(LoginRequiredMixin):
    """
    Mixin that restricts view access based on user roles.

    Usage:
        class MyView(RoleBasedPermissionMixin, View):
            required_roles = ['admin', 'staff']

    Available roles: admin, staff, teacher, student, finance
    """

    required_roles: list[str] = []
    redirect_url: str | None = None

    def dispatch(self, request, *args, **kwargs):
        """Check role permission before dispatching to view."""
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not self.check_role_permission(request.user):
            return self.handle_permission_denied(request)

        return super().dispatch(request, *args, **kwargs)

    def check_role_permission(self, user) -> bool:
        """
        Check if user has required role permission.

        Args:
            user: Django User instance

        Returns:
            bool: True if user has permission, False otherwise
        """
        if not self.required_roles:
            return True  # No specific roles required

        user_roles = self.get_user_roles(user)

        # Admin has access to everything
        if "admin" in user_roles:
            return True

        # Check if user has any of the required roles
        return any(role in user_roles for role in self.required_roles)

    def get_user_roles(self, user) -> list[str]:
        """
        Get list of roles for the given user.

        This method can be overridden to implement custom role detection.
        By default, it uses Django groups.

        Args:
            user: Django User instance

        Returns:
            List[str]: List of role names
        """
        if user.is_superuser:
            return ["admin"]

        # Get roles from user groups
        roles = list(user.groups.values_list("name", flat=True))

        # Add default role based on profile type
        if hasattr(user, "person"):
            person = user.person
            if hasattr(person, "studentprofile"):
                roles.append("student")
            if hasattr(person, "teacherprofile"):
                roles.append("teacher")
            if hasattr(person, "staffprofile"):
                roles.append("staff")

        return roles

    def handle_permission_denied(self, request):
        """Handle permission denied scenarios."""
        if self.redirect_url:
            messages.error(request, "You don't have permission to access this page.")
            return redirect(self.redirect_url)

        raise PermissionDenied("Insufficient permissions for this action.")


# Role-specific permission mixins for convenience
class AdminRequiredMixin(RoleBasedPermissionMixin):
    """Require admin role."""

    required_roles = ["admin"]


class StaffRequiredMixin(RoleBasedPermissionMixin):
    """Require staff role."""

    required_roles = ["admin", "staff"]


class TeacherRequiredMixin(RoleBasedPermissionMixin):
    """Require teacher role."""

    required_roles = ["admin", "staff", "teacher"]


class FinanceRequiredMixin(RoleBasedPermissionMixin):
    """Require finance role."""

    required_roles = ["admin", "finance"]


class StudentRequiredMixin(RoleBasedPermissionMixin):
    """Require student role."""

    required_roles = ["admin", "staff", "student"]


# Role permission matrix
ROLE_PERMISSIONS = {
    "admin": [
        # Full access to everything
        "*"
    ],
    "staff": [
        "students",
        "student_records",
        "courses",
        "course_management",
        "enrollment",
        "class_scheduling",
        "grades",
        "grade_management",
        "transcripts",
        "academic_records",
    ],
    "teacher": [
        "my_classes",
        "my_students",
        "attendance",
        "grade_entry",
        "student_lists",
        "schedule",
        "teaching_reports",
    ],
    "finance": [
        "billing",
        "invoices",
        "payments",
        "student_accounts",
        "cashier_session",
        "financial_reports",
        "reconciliation",
        "scholarships",
    ],
    "student": [
        "my_profile",
        "my_courses",
        "my_schedule",
        "my_grades",
        "my_transcript",
        "course_registration",
        "my_payments",
        "my_balance",
    ],
}


def has_permission(user, permission: str) -> bool:
    """
    Check if user has specific permission.

    Args:
        user: Django User instance
        permission: Permission name to check

    Returns:
        bool: True if user has permission
    """
    if not user.is_authenticated:
        return False

    user_roles = RoleBasedPermissionMixin().get_user_roles(user)

    # Admin has all permissions
    if "admin" in user_roles:
        return True

    # Check role permissions
    for role in user_roles:
        role_perms = ROLE_PERMISSIONS.get(role, [])
        if "*" in role_perms or permission in role_perms:
            return True

    return False
