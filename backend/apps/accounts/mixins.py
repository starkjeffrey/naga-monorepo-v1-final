"""Permission mixins for role-based access control.

This module provides mixins for views and API endpoints to enforce
role-based permissions using the accounts app's authorization system.
Replaces the simple role-checking decorators with comprehensive
permission checking that considers role hierarchies and department context.

Key features:
- Django Ninja API authentication classes
- View mixins for Django class-based views
- Department-scoped permission checking
- Role hierarchy consideration
- Object-level permission support
- Integration with existing user roles
"""

from typing import TYPE_CHECKING, Any, Optional

from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.views.generic.base import View
from django.views.generic.detail import SingleObjectMixin
from ninja.security import HttpBearer

from apps.accounts.services import PermissionService, UserAccountService

if TYPE_CHECKING:
    from apps.accounts.models import Department


class AccountsAuthMixin(AccessMixin):
    """Base mixin for account-based authorization in views.

    Provides common functionality for checking permissions through
    the accounts app's role system rather than Django's built-in
    permission system.
    """

    required_role_type: str | None = None
    required_permission: str | None = None
    department_required: bool = False
    request: HttpRequest  # Type annotation for mypy - provided by view class

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Override dispatch to check accounts-based permissions."""
        if not self.test_func():
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)  # type: ignore[misc]

    def test_func(self) -> bool:
        """Test if user has required permissions."""
        user = self.request.user

        if not user.is_authenticated:
            return False

        # Check role type if specified
        if self.required_role_type:
            department = self.get_department_context()
            if not UserAccountService.has_role(
                user,
                self.required_role_type,
                department,
            ):
                return False

        # Check specific permission if specified
        if self.required_permission:
            department = self.get_department_context()
            obj = self.get_permission_object()
            if not PermissionService.has_permission(
                user,
                self.required_permission,
                obj,
                department,
            ):
                return False

        return True

    def get_department_context(self) -> Optional["Department"]:
        """Get department context for permission checking.

        Override this method to provide department context based on
        the current view/object being accessed.
        """
        return None

    def get_permission_object(self) -> Any:
        """Get object for object-level permission checking.

        Override this method to provide the object being accessed
        for object-level permissions.
        """
        return None


class RoleRequiredMixin(AccountsAuthMixin):
    """Mixin to require specific role types for view access.

    Usage:
        class TeacherOnlyView(RoleRequiredMixin, TemplateView):
            required_role_type = "TEACHER"
            template_name = "teacher_dashboard.html"
    """


class PermissionRequiredMixin(AccountsAuthMixin):
    """Mixin to require specific permissions for view access.

    Usage:
        class EditGradesView(PermissionRequiredMixin, UpdateView):
            required_permission = "grading.change_grade"
            model = Grade
    """


class DepartmentPermissionMixin(AccountsAuthMixin, View):
    """Mixin for department-scoped permission checking.

    Automatically extracts department context from URL parameters
    or object relationships.

    Usage:
        class DepartmentReportView(DepartmentPermissionMixin, TemplateView):
            required_role_type = "HEAD"
            department_url_kwarg = "department_id"
    """

    department_url_kwarg: str = "department_id"
    department_required = True

    def get_department_context(self) -> Optional["Department"]:
        """Get department from URL parameters."""
        from apps.accounts.models import Department

        department_id = self.kwargs.get(self.department_url_kwarg)
        if department_id:
            try:
                return Department.objects.get(id=department_id, is_active=True)
            except Department.DoesNotExist:
                pass
        return None


class ObjectOwnershipMixin(AccountsAuthMixin, SingleObjectMixin):
    """Mixin for object ownership-based access control.

    Checks if the current user owns or has permission to access
    the specific object being viewed.

    Usage:
        class EditStudentProfileView(ObjectOwnershipMixin, UpdateView):
            model = StudentProfile
            ownership_field = "person__user"
    """

    ownership_field: str = "user"

    def test_func(self) -> bool:
        """Test ownership in addition to base permissions."""
        if not super().test_func():
            return False

        # Check object ownership
        obj = self.get_object()
        user = self.request.user

        # Navigate through the ownership field
        owner = obj
        for field in self.ownership_field.split("__"):
            owner = getattr(owner, field, None)
            if owner is None:
                return False

        return owner == user or self._has_override_permission(user, obj)

    def _has_override_permission(self, user: Any, obj: Any) -> bool:
        """Check if user has permission to override ownership restrictions."""
        # Superusers can access everything
        if user.is_superuser:
            return True

        # Users with admin/supervisor roles can override
        return UserAccountService.has_role(
            user,
            "DIRECTOR",
        ) or UserAccountService.has_role(user, "SUPERVISOR")


# Django Ninja API Authentication Classes


class RoleBasedAuth(HttpBearer):
    """Django Ninja authentication class for role-based API access.

    Usage:
        @api.get("/teacher-endpoint", auth=RoleBasedAuth(required_role="TEACHER"))
        def teacher_endpoint(request):
            return {"message": "Teacher access granted"}
    """

    def __init__(self, required_role: str, department_required: bool = False):
        super().__init__()
        self.required_role = required_role
        self.department_required = department_required

    def authenticate(self, request: HttpRequest, token: str) -> Any | None:
        """Authenticate user and check role permissions."""
        user = request.user

        if not user.is_authenticated:
            return None

        # This is mainly for role checking
        department = self._get_department_from_request(request)

        if not UserAccountService.has_role(user, self.required_role, department):
            return None

        return user

    def _get_department_from_request(
        self,
        request: HttpRequest,
    ) -> Optional["Department"]:
        """Extract department context from request."""
        # This could be enhanced to extract from URL params, headers, etc.
        return None


class PermissionBasedAuth(HttpBearer):
    """Django Ninja authentication class for permission-based API access.

    Usage:
        @api.get("/grades", auth=PermissionBasedAuth("grading.view_grade"))
        def view_grades(request):
            return {"grades": [...]}
    """

    def __init__(self, required_permission: str, department_required: bool = False):
        super().__init__()
        self.required_permission = required_permission
        self.department_required = department_required

    def authenticate(self, request: HttpRequest, token: str) -> Any | None:
        """Authenticate user and check permissions."""
        user = request.user

        if not user.is_authenticated:
            return None

        department = self._get_department_from_request(request)

        if not PermissionService.has_permission(
            user,
            self.required_permission,
            None,
            department,
        ):
            return None

        return user

    def _get_department_from_request(
        self,
        request: HttpRequest,
    ) -> Optional["Department"]:
        """Extract department context from request."""
        return None


# Decorator functions for backward compatibility


def role_required(role_type: str, department_required: bool = False):
    """Decorator function for role-based access control.

    Args:
        role_type: Required role type from Role.RoleType choices
        department_required: Whether department context is required

    Usage:
        @role_required("TEACHER")
        def teacher_view(request):
            return render(request, "teacher_page.html")
    """

    def decorator(view_func):
        def wrapper(request: HttpRequest, *args, **kwargs):
            user = request.user

            if not user.is_authenticated:
                msg = "Authentication required"
                raise PermissionDenied(msg)

            # Extract department from kwargs if available
            department = None
            if department_required and "department_id" in kwargs:
                from apps.accounts.models import Department

                try:
                    department = Department.objects.get(
                        id=kwargs["department_id"],
                        is_active=True,
                    )
                except Department.DoesNotExist as e:
                    msg = "Invalid department"
                    raise PermissionDenied(msg) from e

            if not UserAccountService.has_role(user, role_type, department):
                msg = f"{role_type} role required"
                raise PermissionDenied(msg)

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def permission_required(permission_codename: str, department_required: bool = False):
    """Decorator function for permission-based access control.

    Args:
        permission_codename: Required permission codename
        department_required: Whether department context is required

    Usage:
        @permission_required("grading.change_grade")
        def edit_grade(request, grade_id):
            # Edit grade logic
            pass
    """

    def decorator(view_func):
        def wrapper(request: HttpRequest, *args, **kwargs):
            user = request.user

            if not user.is_authenticated:
                msg = "Authentication required"
                raise PermissionDenied(msg)

            # Extract department from kwargs if available
            department = None
            if department_required and "department_id" in kwargs:
                from apps.accounts.models import Department

                try:
                    department = Department.objects.get(
                        id=kwargs["department_id"],
                        is_active=True,
                    )
                except Department.DoesNotExist as e:
                    msg = "Invalid department"
                    raise PermissionDenied(msg) from e

            if not PermissionService.has_permission(
                user,
                permission_codename,
                None,
                department,
            ):
                msg = f"Permission {permission_codename} required"
                raise PermissionDenied(msg)

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


# Utility functions for checking permissions in templates and other contexts


def user_has_role(
    user: Any,
    role_type: str,
    department: Optional["Department"] = None,
) -> bool:
    """Template-friendly function to check if user has a specific role.

    Usage in templates:
        {% if user|has_role:"TEACHER" %}
            <!-- Teacher content -->
        {% endif %}
    """
    if not user or not user.is_authenticated:
        return False
    return UserAccountService.has_role(user, role_type, department)


def user_has_permission(
    user: Any,
    permission: str,
    obj: Any = None,
    department: Optional["Department"] = None,
) -> bool:
    """Template-friendly function to check if user has a specific permission.

    Usage in templates:
        {% if user|has_permission:"grading.view_grade" %}
            <!-- Grade viewing content -->
        {% endif %}
    """
    if not user or not user.is_authenticated:
        return False
    return PermissionService.has_permission(user, permission, obj, department)
