"""Management override decorators for system policy enforcement.

This module provides decorators that allow specific management roles to override
business rules while maintaining a complete audit trail. The decorators are
designed to be reusable across different apps and policies.

Key features:
- Role-based override permissions
- Centralized audit logging
- Granular policy control
- Clean architecture compliance
"""

from collections.abc import Callable
from functools import wraps
from typing import Any

from django.http import HttpRequest
from ninja.responses import Response

from apps.accounts.services import UserAccountService
from apps.common.models import SystemAuditLog


def management_override_required(allowed_roles: list[str], override_policy: str):
    """Decorator that allows specific management roles to override system policies.

    This decorator provides granular control over which management roles can
    override specific business rules while maintaining a complete audit trail.

    Args:
        allowed_roles: List of role names that can perform this override
                      e.g., ['HEAD_APD', 'HEAD_REGISTRATION']
        override_policy: Name of the policy being overridden
                        e.g., 'REPEAT_PREVENTION_RULE', 'PREREQUISITE_RULE'

    Usage:
        @management_override_required(['HEAD_APD'], 'REPEAT_PREVENTION_RULE')
        def enroll_student_override_repeat(request, student_id, class_id, override_reason):
            # Override enrollment logic here
            pass

    The decorator will:
    1. Check if the user has the required management role
    2. Execute the wrapped function if authorized
    3. Log the successful override action to SystemAuditLog
    4. Return 403 if user lacks authorization
    """

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs) -> Any:
            # 1. Authentication check
            if not request.user.is_authenticated:
                return Response({"error": "Authentication required"}, status=401)

            # 2. Role authorization check
            user_has_override_permission = False
            user_role_found = None

            # Check if user has any of the allowed management roles
            for role in allowed_roles:
                if UserAccountService.has_role(request.user, role):
                    user_has_override_permission = True
                    user_role_found = role
                    break

            if not user_has_override_permission:
                return Response(
                    {
                        "error": f"Management override permission required. Allowed roles: {', '.join(allowed_roles)}",
                        "required_roles": allowed_roles,
                        "override_policy": override_policy,
                    },
                    status=403,
                )

            # 3. Execute the protected function
            try:
                result = view_func(request, *args, **kwargs)

                # 4. Log successful override action
                # Extract override details from kwargs/request
                override_reason = (
                    kwargs.get("override_reason")
                    or getattr(request, "data", {}).get("override_reason")
                    or request.POST.get("override_reason")
                    or "No reason provided"
                )

                # Try to get target object ID from various sources
                target_object_id = (
                    kwargs.get("student_id") or kwargs.get("enrollment_id") or kwargs.get("class_id") or "unknown"
                )

                SystemAuditLog.log_override(
                    action_type=f"{override_policy}_OVERRIDE",
                    performed_by=request.user,
                    target_app="enrollment",  # This could be made dynamic
                    target_model="ClassHeaderEnrollment",  # This could be made dynamic
                    target_object_id=target_object_id,
                    override_reason=override_reason,
                    original_restriction=f"System policy: {override_policy}",
                    override_details={
                        "allowed_roles": allowed_roles,
                        "user_role": user_role_found,
                        "endpoint": request.path,
                        "method": request.method,
                        "function_name": view_func.__name__,
                    },
                    request=request,
                )

            except Exception:
                # Re-raise the exception to maintain normal error handling
                raise
            else:
                return result

        return wrapper

    return decorator


def override_policy_required(policy_name: str):
    """Simplified override decorator for specific policies.

    This is a convenience decorator for common override patterns.
    It maps policies to their appropriate management roles automatically.

    Usage:
        @override_policy_required('REPEAT_PREVENTION')
        def enroll_with_repeat_override(request, ...):
            pass
    """
    # Define policy to role mappings
    policy_role_mapping = {
        "REPEAT_PREVENTION": ["HEAD_APD", "HEAD_REGISTRATION"],
        "PREREQUISITE_OVERRIDE": ["HEAD_APD"],
        "CAPACITY_OVERRIDE": ["HEAD_REGISTRATION"],
        "ACADEMIC_POLICY": ["HEAD_APD"],
        "REGISTRATION_POLICY": ["HEAD_REGISTRATION"],
    }

    allowed_roles = policy_role_mapping.get(policy_name, ["HEAD_APD", "HEAD_REGISTRATION"])
    return management_override_required(allowed_roles, policy_name)
