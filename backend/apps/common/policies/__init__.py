"""Policy-driven architecture for centralized business rule management.

This module provides a standardized framework for implementing, evaluating,
and auditing institutional policies across the Naga SIS. All business rules
should be implemented as Policy classes to ensure consistency, auditability,
and regulatory compliance.

Key components:
- Policy: Base class for all business rules
- PolicyEngine: Orchestrates policy evaluation
- PolicyContext: Standardized context for policy decisions
- PolicyResult/PolicyViolation: Structured policy outcomes

Usage:
    from apps.common.policies import PolicyEngine, PolicyContext

    engine = PolicyEngine()
    context = PolicyContext(user=request.user, department=dept)
    result = engine.evaluate_policy('TEACH_QUAL_001', context, teacher=teacher, course=course)
"""

from .base import Policy, PolicyContext, PolicyEngine, PolicyResult, PolicyViolation
from .decorators import policy_check, requires_policy
from .exceptions import PolicyError, PolicyNotFoundError

__all__ = [
    "Policy",
    "PolicyContext",
    "PolicyEngine",
    "PolicyError",
    "PolicyNotFoundError",
    "PolicyResult",
    "PolicyViolation",
    "policy_check",
    "requires_policy",
]
