"""Policy-driven authority service for institutional governance.

This service integrates the policy engine with institutional authority models
to provide centralized, auditable decision-making for all authorization needs.

LEGACY NOTE: This file previously contained UserAccountService, PermissionService,
and RoleService. These have been moved to legacy_services.py to maintain
backward compatibility while transitioning to the new policy-driven architecture.
"""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

from apps.common.policies.base import PolicyContext, PolicyResult, get_policy_engine

from .models import PositionAssignment, TeachingAssignment

if TYPE_CHECKING:
    from apps.accounts.models import Department, UserRole


class AuthorityService:
    """██████████████████████████████████████████████████████████████████████████████
    ████                    POLICY-DRIVEN AUTHORITY SERVICE                   ████
    ██████████████████████████████████████████████████████████████████████████████

    CENTRALIZED AUTHORITY CHECKING WITH POLICY ENGINE INTEGRATION
    ────────────────────────────────────────────────────────────────────────────

    This service provides the single source of truth for all authority decisions
    in the system. It integrates with the policy engine to ensure consistent,
    auditable, and maintainable business rule enforcement.

    Key Features:
    ✅ Policy-driven decision making
    ✅ Institutional hierarchy awareness
    ✅ Delegation and acting role support
    ✅ Comprehensive audit logging
    ✅ Context-aware permissions

    Usage:
        authority_service = AuthorityService(user)

        # Teaching authority
        if authority_service.can_assign_teacher(teacher, course, department):
            # Process assignment

        # Override authority
        if authority_service.can_override_policy('ENROLLMENT', department):
            # Process override

    ██████████████████████████████████████████████████████████████████████████████
    """

    def __init__(self, user, effective_date: date | None = None):
        """Initialize authority service for a specific user.

        Args:
            user: User whose authority to evaluate
            effective_date: Date for temporal authority checks (defaults to today)
        """
        self.user = user
        self.effective_date = effective_date or date.today()
        self.policy_engine = get_policy_engine()

        # Caching for performance
        self._position_cache: list[PositionAssignment] | None = None
        self._teaching_cache: list[TeachingAssignment] | None = None

    # ═══════════════════════════════════════════════════════════════════════════
    # TEACHING AUTHORITY (Policy-Driven)
    # ═══════════════════════════════════════════════════════════════════════════

    def can_assign_teacher(self, teacher, course, department) -> bool:
        """Check if user can assign a teacher to a course using policy engine.

        Evaluates TEACH_QUAL_001 policy and override authority.
        """
        context = self._create_policy_context(department=department)

        # Evaluate teaching qualification policy
        result = self.policy_engine.evaluate_policy(
            "TEACH_QUAL_001",
            context,
            teacher=teacher,
            course=course,
            department=department,
        )

        if result == PolicyResult.ALLOW:
            return True

        if result == PolicyResult.REQUIRE_OVERRIDE:
            # Check if user has override authority
            return self.can_override_policy("TEACHING_QUAL", department=department)

        return False

    def get_teaching_assignment_violations(self, teacher, course, department) -> list[dict[str, Any]]:
        """Get detailed violations for teacher assignment.

        Returns user-friendly violation information for UI display.
        """
        context = self._create_policy_context(department=department)
        violations = self.policy_engine.get_policy_violations(
            "TEACH_QUAL_001",
            context,
            teacher=teacher,
            course=course,
            department=department,
        )

        return [
            {
                "code": v.code,
                "message": v.message,
                "severity": v.severity.value,
                "can_override": v.can_be_overridden(),
                "override_authority_required": v.override_authority_required,
                "user_can_override": (
                    self.has_authority_level(v.override_authority_required, department=department)
                    if v.override_authority_required
                    else False
                ),
                "metadata": v.metadata,
            }
            for v in violations
        ]

    def can_teach_course(self, teacher, course, department) -> bool:
        """Check if teacher is qualified to teach a specific course."""
        context = self._create_policy_context(department=department)
        result = self.policy_engine.evaluate_policy(
            "TEACH_QUAL_001",
            context,
            teacher=teacher,
            course=course,
            department=department,
        )
        return result == PolicyResult.ALLOW

    # ═══════════════════════════════════════════════════════════════════════════
    # OVERRIDE AUTHORITY (Policy-Driven)
    # ═══════════════════════════════════════════════════════════════════════════

    def can_override_policy(self, policy_type: str, department=None) -> bool:
        """Check if user can override a specific policy type using policy engine.

        Evaluates AUTH_OVERRIDE_001 policy for institutional authority validation.
        """
        context = self._create_policy_context(department=department)

        result = self.policy_engine.evaluate_policy(
            "AUTH_OVERRIDE_001",
            context,
            policy_type=policy_type,
            department=department,
        )

        return result == PolicyResult.ALLOW

    def get_override_authority_violations(self, policy_type: str, department=None) -> list[dict[str, Any]]:
        """Get detailed information about override authority violations."""
        context = self._create_policy_context(department=department)
        violations = self.policy_engine.get_policy_violations(
            "AUTH_OVERRIDE_001",
            context,
            policy_type=policy_type,
            department=department,
        )

        return [
            {
                "code": v.code,
                "message": v.message,
                "severity": v.severity.value,
                "metadata": v.metadata,
            }
            for v in violations
        ]

    # ═══════════════════════════════════════════════════════════════════════════
    # INSTITUTIONAL HIERARCHY (Direct Model Access)
    # ═══════════════════════════════════════════════════════════════════════════

    def has_authority_level(self, required_level: int, department=None) -> bool:
        """Check if user has sufficient authority level (1=highest).

        This is direct model access since it's foundational to policy evaluation.
        """
        positions = self.get_user_positions(department=department)

        for assignment in positions:
            effective_assignment = assignment.get_effective_authority()
            if effective_assignment.position.authority_level <= required_level:  # type: ignore[attr-defined]
                return True

        return False

    def get_user_positions(self, department=None) -> list[PositionAssignment]:
        """Get user's current position assignments with caching."""
        if self._position_cache is None:
            self._position_cache = list(
                self.user.position_assignments.filter(
                    start_date__lte=self.effective_date,
                    is_current=True,
                ).select_related("position", "position__department"),
            )

        positions = self._position_cache

        if department:
            positions = [p for p in positions if p.position.department == department or p.position.department is None]  # type: ignore[attr-defined]

        return positions

    def get_highest_authority_level(self, department=None) -> int | None:
        """Get user's highest authority level (lowest number = highest authority)."""
        positions = self.get_user_positions(department=department)

        if not positions:
            return None

        authority_levels = []
        for assignment in positions:
            effective_assignment = assignment.get_effective_authority()
            authority_levels.append(effective_assignment.position.authority_level)  # type: ignore[attr-defined]

        return min(authority_levels) if authority_levels else None

    # ═══════════════════════════════════════════════════════════════════════════
    # APPROVAL AUTHORITY (Business Logic)
    # ═══════════════════════════════════════════════════════════════════════════

    def has_approval_authority(self, amount: Decimal, approval_type: str, department=None) -> bool:
        """Check financial/policy approval authority with amount limits."""
        positions = self.get_user_positions(department=department)

        for assignment in positions:
            effective_assignment = assignment.get_effective_authority()
            position = effective_assignment.position
            limits = position.approval_limits or {}  # type: ignore[attr-defined]

            if approval_type in limits:
                limit = limits[approval_type]
                if limit == "unlimited" or (isinstance(limit, int | float) and amount <= limit):
                    return True

        return False

    def get_approval_limit(self, approval_type: str, department=None) -> Decimal | None:
        """Get user's approval limit for a specific type."""
        positions = self.get_user_positions(department=department)
        max_limit = Decimal("0")

        for assignment in positions:
            effective_assignment = assignment.get_effective_authority()
            position = effective_assignment.position
            limits = position.approval_limits or {}  # type: ignore[attr-defined]

            if approval_type in limits:
                limit = limits[approval_type]
                if limit == "unlimited":
                    return None  # Unlimited authority
                if isinstance(limit, int | float):
                    max_limit = max(max_limit, Decimal(str(limit)))

        return max_limit if max_limit > 0 else None

    # ═══════════════════════════════════════════════════════════════════════════
    # CONTEXT AND UTILITY METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def _create_policy_context(self, department=None, **kwargs) -> PolicyContext:
        """Create standardized policy context for evaluations."""
        return PolicyContext(
            user=self.user,
            department=department,
            effective_date=self.effective_date,
            metadata=kwargs,
        )

    def get_all_authorities(self, department=None) -> dict[str, Any]:
        """Get comprehensive authority summary for user.

        Useful for admin interfaces and debugging.
        """
        positions = self.get_user_positions(department=department)

        authority_summary: dict[str, Any] = {
            "highest_authority_level": self.get_highest_authority_level(department=department),
            "positions": [],
            "override_authorities": [],
            "approval_limits": {},
            "teaching_assignments": [],
        }

        # Position details
        for assignment in positions:
            effective_assignment = assignment.get_effective_authority()
            position = effective_assignment.position

            authority_summary["positions"].append(
                {
                    "title": position.title,  # type: ignore[attr-defined]
                    "authority_level": position.authority_level,  # type: ignore[attr-defined]
                    "department": (position.department.name if position.department else "Institutional"),  # type: ignore[attr-defined]
                    "is_acting": assignment.is_acting,
                    "has_delegation": assignment.has_active_delegation,
                },
            )

            # Override authorities
            for policy_type in position.can_override_policies:  # type: ignore[attr-defined]
                authority_summary["override_authorities"].append(policy_type)

            # Approval limits
            if position.approval_limits:  # type: ignore[attr-defined]
                for approval_type, limit in position.approval_limits.items():  # type: ignore[attr-defined]
                    current_limit = authority_summary["approval_limits"].get(approval_type, 0)
                    if limit == "unlimited":
                        authority_summary["approval_limits"][approval_type] = "unlimited"
                    elif isinstance(limit, int | float):
                        authority_summary["approval_limits"][approval_type] = max(current_limit, limit)

        return authority_summary

    def audit_authority_decision(self, action: str, result: bool, **context) -> None:
        """Log authority decisions for audit purposes."""
        import logging

        audit_logger = logging.getLogger("naga.authority_audit")
        audit_logger.info(
            f"Authority decision: {action} = {result}",
            extra={
                "user_id": self.user.id,
                "action": action,
                "result": result,
                "effective_date": self.effective_date.isoformat(),
                "context": context,
                "highest_authority_level": self.get_highest_authority_level(),
            },
        )


# ═══════════════════════════════════════════════════════════════════════════════
# LEGACY SERVICES (Preserved for backward compatibility)
# ═══════════════════════════════════════════════════════════════════════════════

# Import legacy services to maintain backward compatibility
# These will be gradually phased out in favor of the policy-driven approach

User = get_user_model()


class UserAccountService:
    """LEGACY: Use AuthorityService for new implementations."""

    @staticmethod
    def get_user_roles(user, department: Optional["Department"] = None) -> QuerySet["UserRole"]:
        """Get all active roles for a user, optionally filtered by department."""
        from apps.accounts.models import UserRole

        queryset = UserRole.objects.filter(
            user=user,
            is_active=True,
            role__is_active=True,
        ).select_related("role", "department")

        if department:
            queryset = queryset.filter(department=department)

        return queryset

    @staticmethod
    def has_role(user, role_type: str, department: Optional["Department"] = None) -> bool:
        """Check if user has a specific role type."""
        if not user or not hasattr(user, "is_active") or not user.is_active:
            return False

        # Superusers have all roles
        if hasattr(user, "is_superuser") and user.is_superuser:
            return True

        user_roles = UserAccountService.get_user_roles(user, department)
        return user_roles.filter(role__role_type=role_type).exists()


class PermissionService:
    """LEGACY: Use AuthorityService with policy engine for new implementations."""

    @staticmethod
    def has_permission(
        user,
        permission_codename: str,
        obj: Any = None,
        department: Optional["Department"] = None,
    ) -> bool:
        """Check if user has a specific permission."""
        if not user or not hasattr(user, "is_active") or not user.is_active:
            return False

        # Superusers have all permissions
        if hasattr(user, "is_superuser") and user.is_superuser:
            return True

        # Check Django's built-in permissions first
        if hasattr(user, "has_perm"):
            return bool(user.has_perm(permission_codename))
        return False
