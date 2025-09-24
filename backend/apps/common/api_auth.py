"""API authentication decorators for Django Ninja.

This module provides role-based authentication decorators for the API using
the accounts app's comprehensive authorization system. These decorators now
use role-based access control with hierarchical permissions.

Updated decorators:
- teacher_required: For teacher role endpoints
- student_required: For student role endpoints
- admin_required: For admin/staff role endpoints
- role_required: Generic role-based decorator
- permission_required: Permission-based decorator

Legacy profile-based checking is maintained for backward compatibility.
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from django.http import HttpRequest
from ninja.responses import Response

from apps.accounts.services import PermissionService, UserAccountService


def teacher_required(view_func: Callable) -> Callable:
    """Decorator to require teacher authentication for API endpoints.

    Now uses accounts app role system with fallback to profile checking.
    Checks for TEACHER role first, then falls back to teacher profile.
    """

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)

        # Check role-based access first (new system)
        if UserAccountService.has_role(request.user, "TEACHER"):
            return view_func(request, *args, **kwargs)

        # Fallback to profile-based checking (legacy compatibility)
        if hasattr(request.user, "person") and hasattr(
            request.user.person,
            "teacher_profile",
        ):
            return view_func(request, *args, **kwargs)

        return Response({"error": "Teacher access required"}, status=403)

    return wrapper


def student_required(view_func: Callable) -> Callable:
    """Decorator to require student authentication for API endpoints.

    Now uses accounts app role system with fallback to profile checking.
    Checks for STUDENT role first, then falls back to student profile.
    """

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)

        # Check role-based access first (new system)
        if UserAccountService.has_role(request.user, "STUDENT"):
            return view_func(request, *args, **kwargs)

        # Fallback to profile-based checking (legacy compatibility)
        if hasattr(request.user, "person") and hasattr(
            request.user.person,
            "student_profile",
        ):
            return view_func(request, *args, **kwargs)

        return Response({"error": "Student access required"}, status=403)

    return wrapper


def admin_required(view_func: Callable) -> Callable:
    """Decorator to require admin authentication for API endpoints.

    Now uses accounts app role system with fallback to Django's built-in system.
    Checks for DIRECTOR/HEAD/SUPERVISOR roles first, then falls back to is_staff.
    """

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)

        # Check role-based access first (new system)
        admin_roles = ["DIRECTOR", "HEAD", "SUPERVISOR"]
        for role in admin_roles:
            if UserAccountService.has_role(request.user, role):
                return view_func(request, *args, **kwargs)

        # Fallback to Django's built-in system (legacy compatibility)
        if request.user.is_staff or request.user.is_superuser:
            return view_func(request, *args, **kwargs)

        return Response({"error": "Admin access required"}, status=403)

    return wrapper


def authenticated_required(view_func: Callable) -> Callable:
    """Decorator to require basic authentication for API endpoints.

    Checks that the user is authenticated.
    """

    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        if not request.user.is_authenticated:
            return Response({"error": "Authentication required"}, status=401)

        return view_func(request, *args, **kwargs)

    return wrapper


def role_required(role_type: str, department_id: int | None = None):
    """Generic decorator to require specific role type for API endpoints.

    Args:
        role_type: Required role type from Role.RoleType choices
        department_id: Optional department ID for department-scoped roles

    Usage:
        @role_required("TEACHER")
        def teacher_endpoint(request):
            return {"message": "Teacher access granted"}

        @role_required("HEAD", department_id=1)
        def department_head_endpoint(request):
            return {"message": "Department head access granted"}
    """

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            if not request.user.is_authenticated:
                return Response({"error": "Authentication required"}, status=401)

            # Get department if specified
            department = None
            if department_id:
                from apps.accounts.models import Department

                try:
                    department = Department.objects.get(
                        id=department_id,
                        is_active=True,
                    )
                except Department.DoesNotExist:
                    return Response({"error": "Invalid department"}, status=400)

            # Check role access
            if not UserAccountService.has_role(request.user, role_type, department):
                return Response({"error": f"{role_type} role required"}, status=403)

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def permission_required(permission_codename: str, department_id: int | None = None):
    """Decorator to require specific permission for API endpoints.

    Args:
        permission_codename: Required permission codename
        department_id: Optional department ID for department-scoped permissions

    Usage:
        @permission_required("grading.change_grade")
        def edit_grade_endpoint(request):
            return {"message": "Grade editing access granted"}

        @permission_required("academic.view_course", department_id=1)
        def view_department_courses(request):
            return {"courses": [...]}
    """

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            if not request.user.is_authenticated:
                return Response({"error": "Authentication required"}, status=401)

            # Get department if specified
            department = None
            if department_id:
                from apps.accounts.models import Department

                try:
                    department = Department.objects.get(
                        id=department_id,
                        is_active=True,
                    )
                except Department.DoesNotExist:
                    return Response({"error": "Invalid department"}, status=400)

            # Check permission
            if not PermissionService.has_permission(
                request.user,
                permission_codename,
                None,
                department,
            ):
                return Response(
                    {"error": f"Permission {permission_codename} required"},
                    status=403,
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def department_role_required(role_type: str):
    """Decorator that extracts department from URL parameters and checks role.

    Args:
        role_type: Required role type from Role.RoleType choices

    Usage:
        @department_role_required("HEAD")
        def department_admin_endpoint(request, department_id: int):
            # department_id is automatically used for role checking
            return {"message": "Department head access granted"}
    """

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
            if not request.user.is_authenticated:
                return Response({"error": "Authentication required"}, status=401)

            # Extract department_id from URL parameters
            department_id = kwargs.get("department_id")
            if not department_id:
                return Response({"error": "Department ID required"}, status=400)

            # Get department
            from apps.accounts.models import Department

            try:
                department = Department.objects.get(id=department_id, is_active=True)
            except Department.DoesNotExist:
                return Response({"error": "Invalid department"}, status=400)

            # Check role access
            if not UserAccountService.has_role(request.user, role_type, department):
                return Response(
                    {"error": f"{role_type} role required for this department"},
                    status=403,
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
