"""Core policy architecture for centralized business rule management.

This module provides the foundation for implementing institutional policies
as code, ensuring all business rules are discoverable, testable, and auditable.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from functools import lru_cache
from typing import Any

# Configure policy decision logging
policy_logger = logging.getLogger("naga.policies")


class PolicyResult(Enum):
    """Standardized policy evaluation results."""

    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_OVERRIDE = "REQUIRE_OVERRIDE"


class PolicySeverity(Enum):
    """Policy violation severity levels."""

    CRITICAL = "CRITICAL"  # Cannot be overridden
    ERROR = "ERROR"  # Requires high authority to override
    WARNING = "WARNING"  # Can be overridden with moderate authority
    INFO = "INFO"  # Advisory only


@dataclass
class PolicyViolation:
    """Detailed information about a policy violation."""

    code: str  # Unique violation code (e.g., 'INSUFFICIENT_DEGREE_BA')
    message: str  # Human-readable violation description
    severity: PolicySeverity  # Violation severity level
    override_authority_required: int | None = None  # Authority level needed to override (1=highest)
    metadata: dict[str, Any] = field(default_factory=dict)  # Additional context data

    def can_be_overridden(self) -> bool:
        """Check if this violation can be overridden."""
        return self.severity != PolicySeverity.CRITICAL and self.override_authority_required is not None


@dataclass
class PolicyContext:
    """Standardized context for all policy evaluations."""

    # Core context
    user: Any = None  # User requesting the action
    department: Any = None  # Department context
    academic_term: Any = None  # Academic term context
    effective_date: date | None = None

    # Request context
    ip_address: str | None = None  # For audit trails
    user_agent: str | None = None  # For security policies

    # Additional metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Set default effective date if not provided."""
        if self.effective_date is None:
            self.effective_date = date.today()


class Policy(ABC):
    """Base class for all institutional policies.

    Policies encapsulate business rules in a standardized, testable format.
    Each policy should represent a single business concern and provide
    clear, auditable decision logic.

    Example:
        class TeachingQualificationPolicy(Policy):
            policy_code = "TEACH_QUAL_001"
            policy_name = "Teaching Qualification Requirements"
            policy_description = "Validates teacher qualifications for course assignments"

            def evaluate(self, context, teacher, course, department):
                # Implementation here
                pass
    """

    @property
    @abstractmethod
    def policy_code(self) -> str:
        """Unique identifier for this policy.

        Format: {DOMAIN}_{CONCERN}_{VERSION}
        Examples: TEACH_QUAL_001, ENROLL_ELIG_001, FINANCE_LATE_001
        """

    @property
    @abstractmethod
    def policy_name(self) -> str:
        """Human-readable policy name for audit reports."""

    @property
    @abstractmethod
    def policy_description(self) -> str:
        """Detailed description of what this policy governs."""

    @property
    def policy_version(self) -> str:
        """Policy version for change tracking (defaults to 1.0)."""
        return "1.0"

    @property
    def regulatory_references(self) -> list[str]:
        """List of regulatory/institutional references this policy implements."""
        return []

    @abstractmethod
    def evaluate(self, context: PolicyContext, **kwargs) -> PolicyResult:
        """Evaluate if the policy allows the proposed action.

        Args:
            context: Standardized policy context
            **kwargs: Action-specific parameters

        Returns:
            PolicyResult indicating allow/deny/require_override
        """

    @abstractmethod
    def get_violations(self, context: PolicyContext, **kwargs) -> list[PolicyViolation]:
        """Get detailed violations if policy evaluation fails.

        Args:
            context: Standardized policy context
            **kwargs: Action-specific parameters

        Returns:
            List of PolicyViolation objects describing rule failures
        """

    def get_required_parameters(self) -> list[str]:
        """Get list of required parameters for this policy.

        Used for validation and documentation purposes.
        Override if policy requires specific parameters.
        """
        return []

    def is_applicable(self, context: PolicyContext, **kwargs) -> bool:
        """Check if this policy applies to the given context.

        Allows for conditional policy application based on context.
        Override if policy has specific applicability rules.
        """
        return True

    def log_evaluation(self, context: PolicyContext, result: PolicyResult, **kwargs) -> None:
        """Log policy evaluation for audit purposes."""
        policy_logger.info(
            f"Policy {self.policy_code} evaluated: {result.value}",
            extra={
                "policy_code": self.policy_code,
                "policy_name": self.policy_name,
                "result": result.value,
                "user_id": context.user.id if context.user else None,
                "department_id": context.department.id if context.department else None,
                "effective_date": (context.effective_date.isoformat() if context.effective_date else None),
                "parameters": {k: str(v) for k, v in kwargs.items()},
            },
        )


class PolicyRegistry:
    """Registry for discovering and managing policies."""

    def __init__(self) -> None:
        self._policies: dict[str, Policy] = {}
        self._auto_discover()

    def register(self, policy: Policy) -> None:
        """Register a policy instance."""
        self._policies[policy.policy_code] = policy

    def get(self, policy_code: str) -> Policy | None:
        """Get a policy by code."""
        return self._policies.get(policy_code)

    def list_all(self) -> list[Policy]:
        """Get all registered policies."""
        return list(self._policies.values())

    def get_by_domain(self, domain: str) -> list[Policy]:
        """Get all policies for a specific domain (e.g., 'TEACH', 'ENROLL')."""
        return [policy for policy in self._policies.values() if policy.policy_code.startswith(domain)]

    def _auto_discover(self) -> None:
        """Auto-discover policies from registered apps."""
        # Import policies from each app's policies module
        from django.apps import apps

        for app_config in apps.get_app_configs():
            try:
                policies_module = __import__(f"{app_config.name}.policies", fromlist=[""])
                # Look for Policy subclasses and register them
                for attr_name in dir(policies_module):
                    attr = getattr(policies_module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, Policy) and attr != Policy:
                        try:
                            policy_instance = attr()
                            self.register(policy_instance)
                        except Exception as e:
                            policy_logger.warning(f"Could not register policy {attr_name}: {e}")
            except ImportError:
                # App doesn't have policies module - that's fine
                continue


class PolicyEngine:
    """Orchestrates policy evaluation across the system.

    The PolicyEngine provides a centralized interface for evaluating
    institutional policies, managing context, and providing audit trails.
    """

    def __init__(self):
        self.registry = PolicyRegistry()

    def evaluate_policy(self, policy_code: str, context: PolicyContext, **kwargs) -> PolicyResult:
        """Evaluate a specific policy.

        Args:
            policy_code: Unique policy identifier
            context: Policy evaluation context
            **kwargs: Policy-specific parameters

        Returns:
            PolicyResult indicating the evaluation outcome

        Raises:
            PolicyNotFoundError: If policy_code is not registered
        """
        from .exceptions import PolicyNotFoundError

        policy = self.registry.get(policy_code)
        if not policy:
            msg = f"Policy not found: {policy_code}"
            raise PolicyNotFoundError(msg)

        # Check if policy is applicable
        if not policy.is_applicable(context, **kwargs):
            return PolicyResult.ALLOW

        # Validate required parameters
        required_params = policy.get_required_parameters()
        missing_params = [param for param in required_params if param not in kwargs]
        if missing_params:
            msg = f"Missing required parameters for {policy_code}: {missing_params}"
            raise ValueError(msg)

        # Evaluate policy
        result = policy.evaluate(context, **kwargs)

        # Log evaluation
        policy.log_evaluation(context, result, **kwargs)

        return result

    def get_policy_violations(self, policy_code: str, context: PolicyContext, **kwargs) -> list[PolicyViolation]:
        """Get detailed violations for a policy.

        Args:
            policy_code: Unique policy identifier
            context: Policy evaluation context
            **kwargs: Policy-specific parameters

        Returns:
            List of PolicyViolation objects

        Raises:
            PolicyNotFoundError: If policy_code is not registered
        """
        from .exceptions import PolicyNotFoundError

        policy = self.registry.get(policy_code)
        if not policy:
            msg = f"Policy not found: {policy_code}"
            raise PolicyNotFoundError(msg)

        return policy.get_violations(context, **kwargs)

    def evaluate_multiple(self, policy_codes: list[str], context: PolicyContext, **kwargs) -> dict[str, PolicyResult]:
        """Evaluate multiple policies and return results.

        Args:
            policy_codes: List of policy identifiers
            context: Policy evaluation context
            **kwargs: Policy-specific parameters

        Returns:
            Dictionary mapping policy codes to results
        """
        results = {}
        for code in policy_codes:
            try:
                results[code] = self.evaluate_policy(code, context, **kwargs)
            except Exception as e:
                policy_logger.exception(f"Error evaluating policy {code}: {e}")
                results[code] = PolicyResult.DENY

        return results

    def get_all_violations(
        self,
        policy_codes: list[str],
        context: PolicyContext,
        **kwargs,
    ) -> dict[str, list[PolicyViolation]]:
        """Get violations for multiple policies."""
        violations = {}
        for code in policy_codes:
            try:
                violations[code] = self.get_policy_violations(code, context, **kwargs)
            except Exception as e:
                policy_logger.exception(f"Error getting violations for policy {code}: {e}")
                violations[code] = []

        return violations

    def audit_all_policies(self) -> list[dict[str, Any]]:
        """Return comprehensive metadata about all registered policies.

        Used for compliance auditing and policy discovery.
        """
        policies = []
        for policy in self.registry.list_all():
            policies.append(
                {
                    "code": policy.policy_code,
                    "name": policy.policy_name,
                    "description": policy.policy_description,
                    "version": policy.policy_version,
                    "class": policy.__class__.__name__,
                    "module": policy.__class__.__module__,
                    "regulatory_references": policy.regulatory_references,
                    "required_parameters": policy.get_required_parameters(),
                },
            )

        # Sort by policy code for consistent auditing
        return sorted(policies, key=lambda p: p["code"])

    def get_policies_by_domain(self, domain: str) -> list[dict[str, Any]]:
        """Get policy metadata for a specific domain."""
        domain_policies = self.registry.get_by_domain(domain.upper())
        return [
            {
                "code": policy.policy_code,
                "name": policy.policy_name,
                "description": policy.policy_description,
            }
            for policy in domain_policies
        ]


@lru_cache(maxsize=1)
def get_policy_engine() -> PolicyEngine:
    """Get a cached singleton PolicyEngine instance without using globals."""
    return PolicyEngine()
