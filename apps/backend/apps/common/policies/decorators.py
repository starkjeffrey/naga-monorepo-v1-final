"""Decorators for policy-driven view and method protection."""

from collections.abc import Callable
from functools import wraps
from typing import Any

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden

from .base import PolicyContext, PolicyResult, get_policy_engine


def requires_policy(policy_code: str, **context_kwargs) -> Callable:
    """Decorator that requires a policy to evaluate to ALLOW.

    Usage:
        @requires_policy('TEACH_QUAL_001', department_param='dept_id')
        def assign_teacher(request, teacher_id, course_id, dept_id):
            # View implementation

    Args:
        policy_code: Policy identifier to evaluate
        **context_kwargs: Mapping of context parameters to view parameters
    """

    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        @login_required
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            # Build policy context
            context = PolicyContext(user=request.user)

            # Map view parameters to policy context
            if "department_param" in context_kwargs:
                dept_param = context_kwargs["department_param"]
                if dept_param in kwargs:
                    # Would need to fetch department model
                    pass

            # Extract policy parameters from view kwargs
            policy_params: dict[str, Any] = {}
            for key in kwargs:
                if key.endswith("_id"):
                    # Would need model lookup logic here
                    pass

            # Evaluate policy
            engine = get_policy_engine()
            result = engine.evaluate_policy(policy_code, context, **policy_params)

            if result == PolicyResult.DENY:
                return HttpResponseForbidden("Policy violation: Access denied")

            if result == PolicyResult.REQUIRE_OVERRIDE:
                # Check if user has override authority
                engine.get_policy_violations(policy_code, context, **policy_params)
                # Would integrate with AuthorityService here

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def policy_check(policy_codes: list[str]):
    """Method decorator for policy checking in services.

    Usage:
        class TeachingService:
            @policy_check(['TEACH_QUAL_001'])
            def assign_teacher(self, teacher, course, department, user):
                # Method implementation
    """

    def decorator(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            # Extract user context
            user = kwargs.get("user") or (args[0] if args else None)
            context = PolicyContext(user=user)

            # Evaluate all policies
            engine = get_policy_engine()
            results = engine.evaluate_multiple(policy_codes, context, **kwargs)

            # Check if any policy denies
            for policy_code, result in results.items():
                if result == PolicyResult.DENY:
                    violations = engine.get_policy_violations(policy_code, context, **kwargs)
                    violation_messages = [v.message for v in violations]
                    msg = f"Policy {policy_code} violation: {'; '.join(violation_messages)}"
                    raise ValueError(msg)

            return method(self, *args, **kwargs)

        return wrapper

    return decorator
