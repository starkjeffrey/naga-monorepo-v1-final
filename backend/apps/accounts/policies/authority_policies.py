"""Authority and override policies for institutional governance.

Contains business rules for:
- Position-based override authority
- Institutional hierarchy validation
- Policy exception approval workflows
- Delegation and acting authority
"""

from apps.common.policies.base import (
    Policy,
    PolicyContext,
    PolicyResult,
    PolicySeverity,
    PolicyViolation,
)


class OverrideAuthorityPolicy(Policy):
    """██████████████████████████████████████████████████████████████████████████████
    ████                    OVERRIDE AUTHORITY POLICY                         ████
    ██████████████████████████████████████████████████████████████████████████████

    AUTHORITY HIERARCHY (Crystal Clear View):
    ────────────────────────────────────────────────────────────────────────────

    🏛️ INSTITUTIONAL AUTHORITY LEVELS:
       1️⃣ DEAN (Institutional) - Can override ALL policies
       2️⃣ DEPARTMENT CHAIR - Can override department policies
       3️⃣ ACADEMIC COORDINATOR - Can override operational policies
       4️⃣ SUPERVISOR - Can override routine decisions
       5️⃣ STAFF - No override authority

    📋 POLICY OVERRIDE MATRIX:
       ┌─────────────────────┬─────┬──────┬─────┬──────┬──────┐
       │ Policy Type         │  1  │  2   │  3  │  4   │  5   │
       ├─────────────────────┼─────┼──────┼─────┼──────┼──────┤
       │ ENROLLMENT          │  ✅  │  ✅   │  ❌  │  ❌   │  ❌  │
       │ ACADEMIC            │  ✅  │  ✅   │  ✅  │  ❌   │  ❌  │
       │ FINANCIAL           │  ✅  │  ✅   │  ❌  │  ❌   │  ❌  │
       │ TEACHING_QUAL       │  ✅  │  ✅   │  ❌  │  ❌   │  ❌  │
       │ OPERATIONAL         │  ✅  │  ✅   │  ✅  │  ✅   │  ❌  │
       └─────────────────────┴─────┴──────┴─────┴──────┴──────┘

    🔄 DELEGATION SUPPORT:
       - Acting positions inherit full authority
       - Delegation transfers override rights
       - Temporary authority with audit trail

    📋 REGULATORY REFERENCE:
       Institutional Governance Policy Section 2.1
       "Authority Levels and Override Procedures"

    ██████████████████████████████████████████████████████████████████████████████
    """

    # ═══════════════════════════════════════════════════════════════════════════
    # POLICY METADATA
    # ═══════════════════════════════════════════════════════════════════════════

    @property
    def policy_code(self) -> str:
        return "AUTH_OVERRIDE_001"

    @property
    def policy_name(self) -> str:
        return "Override Authority Validation"

    @property
    def policy_description(self) -> str:
        return (
            "Validates institutional authority for policy overrides. "
            "Ensures only appropriately positioned staff can override "
            "specific policy types within their domain of authority."
        )

    @property
    def regulatory_references(self) -> list[str]:
        return [
            "Institutional Governance Policy Section 2.1",
            "Authority Matrix Documentation 2024",
        ]

    def get_required_parameters(self) -> list[str]:
        return ["policy_type", "department"]

    # ═══════════════════════════════════════════════════════════════════════════
    # POLICY EVALUATION LOGIC
    # ═══════════════════════════════════════════════════════════════════════════

    def evaluate(self, context: PolicyContext, policy_type=None, department=None, **kwargs) -> PolicyResult:
        """Evaluate if user has authority to override a specific policy type."""
        violations = self.get_violations(context, policy_type=policy_type, department=department)

        if not violations:
            return PolicyResult.ALLOW

        # Override authority is binary - either you have it or you don't
        return PolicyResult.DENY

    def get_violations(
        self,
        context: PolicyContext,
        policy_type=None,
        department=None,
        **kwargs,
    ) -> list[PolicyViolation]:
        """═══════════════════════════════════════════════════════════════════════
        AUTHORITY VALIDATION BUSINESS RULES
        ═══════════════════════════════════════════════════════════════════════
        """
        violations = []

        if not context.user:
            violations.append(
                PolicyViolation(
                    code="NO_USER_CONTEXT",
                    message="User context required for authority validation",
                    severity=PolicySeverity.CRITICAL,
                    metadata={"rule": "User must be authenticated for override authority"},
                ),
            )
            return violations

        # ─────────────────────────────────────────────────────────────────────
        # RULE 1: Get user's effective authority positions
        # ─────────────────────────────────────────────────────────────────────
        positions = self._get_user_positions(context.user, department)
        if not positions:
            violations.append(
                PolicyViolation(
                    code="NO_AUTHORITY_POSITION",
                    message="User has no authority positions" + (f" in {department.name}" if department else ""),
                    severity=PolicySeverity.ERROR,
                    metadata={
                        "user_id": context.user.id,
                        "department_id": department.id if department else None,
                        "rule": "User must hold authority position to override policies",
                    },
                ),
            )
            return violations

        # ─────────────────────────────────────────────────────────────────────
        # RULE 2: Check if any position has override authority for policy type
        # ─────────────────────────────────────────────────────────────────────
        has_override_authority = False
        highest_authority_level = min(pos.authority_level for pos in positions)

        for position in positions:
            if self._can_override_policy_type(position, policy_type):
                has_override_authority = True
                break

        if not has_override_authority:
            violations.append(
                PolicyViolation(
                    code="INSUFFICIENT_OVERRIDE_AUTHORITY",
                    message=(
                        f"Authority level {highest_authority_level} insufficient to override {policy_type} policies. "
                        f"Required authority: {self._get_required_authority_level(policy_type)}"
                    ),
                    severity=PolicySeverity.ERROR,
                    metadata={
                        "policy_type": policy_type,
                        "user_authority_level": highest_authority_level,
                        "required_authority_level": self._get_required_authority_level(policy_type),
                        "rule": f"{policy_type} policies require specific authority level to override",
                    },
                ),
            )

        return violations

    # ═══════════════════════════════════════════════════════════════════════════
    # BUSINESS RULE HELPER METHODS
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_user_positions(self, user, department=None):
        """Get user's current authority positions with delegation support."""
        try:
            from django.db import models

            # Get position assignments (handles delegation automatically)
            assignments = user.position_assignments.filter(is_current=True)

            if department:
                # Include both department-specific and institutional positions
                assignments = assignments.filter(
                    models.Q(position__department=department)
                    | models.Q(position__department__isnull=True),  # Institutional positions
                )

            # Get effective positions (handles delegation)
            positions = []
            for assignment in assignments:
                effective_assignment = assignment.get_effective_authority()
                positions.append(effective_assignment.position)

            return positions
        except Exception:
            return []

    def _can_override_policy_type(self, position, policy_type) -> bool:
        """Business Rule: Authority matrix for policy override permissions"""
        # Check explicit override permissions first
        if policy_type in position.can_override_policies:
            return True

        # Check authority level requirements
        required_level = self._get_required_authority_level(policy_type)
        return position.authority_level <= required_level

    def _get_required_authority_level(self, policy_type) -> int:
        """═══════════════════════════════════════════════════════════════════════
        AUTHORITY MATRIX: Policy Type → Required Authority Level
        ═══════════════════════════════════════════════════════════════════════

        This is the single source of truth for override authority requirements.
        Modify this matrix to change institutional override policies.
        """
        authority_matrix = {
            "ENROLLMENT": 2,  # Department Chair or higher
            "ACADEMIC": 2,  # Department Chair or higher
            "FINANCIAL": 2,  # Department Chair or higher
            "TEACHING_QUAL": 2,  # Department Chair or higher
            "OPERATIONAL": 4,  # Supervisor or higher
            "SCHEDULING": 3,  # Academic Coordinator or higher
            "GRADING": 3,  # Academic Coordinator or higher
            "ATTENDANCE": 4,  # Supervisor or higher
        }

        return authority_matrix.get(policy_type, 1)  # Default to Dean level if unknown
