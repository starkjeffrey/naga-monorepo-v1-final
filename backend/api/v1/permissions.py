"""Unified API permissions for django-ninja endpoints.

This module provides a consolidated permission checking system for the v1 API,
integrating with the accounts app services and providing backwards compatibility
with existing permission patterns.

Permission Functions:
- has_permission: General permission checking
- has_student_permission: Student-specific access control
- has_role: Role-based access control
"""

from apps.accounts.services import PermissionService
from apps.web_interface.permissions import has_permission as web_has_permission


def has_permission(user, permission_codename: str, department=None) -> bool:
    """Check if user has specific permission.

    This function provides a unified permission checking interface for API endpoints.
    It first tries the advanced PermissionService, then falls back to web interface permissions.

    Args:
        user: Django User instance
        permission_codename: Permission codename (e.g., "finance.view_invoice")
        department: Optional department for scoped permissions

    Returns:
        bool: True if user has permission
    """
    if not user or not user.is_authenticated:
        return False

    try:
        # Try advanced permission service first
        return PermissionService.has_permission(user, permission_codename, None, department)
    except Exception:
        # Fall back to web interface permission checking
        # Convert Django permission format to web interface format
        if "." in permission_codename:
            # Convert "app.action_model" to more general permissions
            app, action_model = permission_codename.split(".", 1)
            if action_model.startswith("view_"):
                return web_has_permission(user, app)
            elif action_model.startswith("add_"):
                return web_has_permission(user, app)
            elif action_model.startswith("change_"):
                return web_has_permission(user, app)
            elif action_model.startswith("delete_"):
                return web_has_permission(user, app)

        # Default to web interface permission check
        return web_has_permission(user, permission_codename)


def check_teacher_access(user) -> bool:
    """Check if user has teacher-level access."""
    if not user or not user.is_authenticated:
        return False

    # Check if user is staff or has teacher profile
    if user.is_staff:
        return True

    # Check for teacher profile
    if hasattr(user, "person") and hasattr(user.person, "teacher_profile"):
        return True

    return False


def check_admin_access(user) -> bool:
    """Check if user has admin-level access."""
    if not user or not user.is_authenticated:
        return False

    # Superuser always has admin access
    if user.is_superuser:
        return True

    # Staff users with appropriate permissions
    if user.is_staff:
        return True

    return False


def has_student_permission(user, student) -> bool:
    """Check if user has permission to access student data.

    Args:
        user: Django User instance
        student: StudentProfile instance

    Returns:
        bool: True if user can access student data
    """
    if not user or not user.is_authenticated:
        return False

    # Admin access
    if check_admin_access(user):
        return True

    # Student accessing their own data
    if hasattr(user, "person") and hasattr(user.person, "student_profile"):
        if user.person.student_profile == student:
            return True

    # Teacher access (simplified - could be refined with class enrollment checks)
    if check_teacher_access(user):
        return True

    return False
