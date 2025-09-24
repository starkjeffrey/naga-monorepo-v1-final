"""Enrollment business policies for centralized rule management.

This module implements enrollment-specific policies including capacity management,
prerequisite validation, and course repeat prevention following the university's
policy-driven architecture for audit compliance and governance transparency.
"""

from typing import Any

from apps.common.policies.base import (
    Policy,
    PolicyContext,
    PolicyResult,
    PolicySeverity,
    PolicyViolation,
)
from apps.enrollment.models import ClassHeaderEnrollment


class EnrollmentCapacityPolicy(Policy):
    """████████████████████████████████████████████████████████████████████████████████
    ████                    ENROLLMENT CAPACITY POLICY                         ████
    ████████████████████████████████████████████████████████████████████████████████

    🎓 CLASS CAPACITY: Students cannot enroll in classes at maximum capacity
    🚫 REJECTION: Students are rejected when class is full (no waitlist)
    🔧 OVERRIDE: Department Chair (level 2) can override capacity limits
    📋 REGULATORY: University Enrollment Standards 3.1.2

    Business Rules:
    ✓ Enrolled + Active students count toward capacity
    ✓ Available spots = max_enrollment - enrolled_count
    ✓ Override authority level 2 (Department Chair) can bypass capacity

    ████████████████████████████████████████████████████████████████████████████████
    """

    @property
    def policy_code(self) -> str:
        """Unique identifier for this policy."""
        return "ENRL_CAPACITY_001"

    @property
    def policy_name(self) -> str:
        """Human-readable policy name for audit reports."""
        return "Enrollment Capacity Management"

    @property
    def policy_description(self) -> str:
        """Detailed description of what this policy governs."""
        return "Controls class enrollment based on capacity limits with department chair override authority"

    def evaluate(self, context: PolicyContext, **kwargs) -> PolicyResult:
        """Evaluate enrollment capacity policy for a specific class and student.

        Args:
            context: Policy context with user, department, and metadata
            **kwargs: Must include:
                - class_header: ClassHeader instance to check capacity for
                - student: StudentProfile instance (for context/logging)

        Returns:
            PolicyResult indicating whether enrollment is allowed
        """
        class_header = kwargs.get("class_header")
        kwargs.get("student")

        if not class_header:
            return PolicyResult.DENY

        # Get current enrollment counts
        capacity_info = self._calculate_capacity_info(class_header)

        # Check if class has available capacity
        if capacity_info["can_enroll"]:
            return PolicyResult.ALLOW

        # Class is full - check for override authority
        # Department Chair (level 2) can override capacity limits
        if self._has_override_authority(context, capacity_info):
            return PolicyResult.REQUIRE_OVERRIDE

        # No capacity and no override authority
        return PolicyResult.DENY

    def get_violations(self, context: PolicyContext, **kwargs) -> list[PolicyViolation]:
        """Get detailed violations when policy evaluation fails."""
        class_header = kwargs.get("class_header")
        kwargs.get("student")

        if not class_header:
            return [
                PolicyViolation(
                    code="MISSING_CLASS_HEADER",
                    message="Class header is required for capacity evaluation",
                    severity=PolicySeverity.ERROR,
                ),
            ]

        violations = []
        capacity_info = self._calculate_capacity_info(class_header)

        if not capacity_info["can_enroll"]:
            violation = PolicyViolation(
                code="CAPACITY_EXCEEDED",
                message=f"Class {class_header} is at maximum capacity "
                f"({capacity_info['enrolled_count']}/{capacity_info['max_enrollment']}). "
                f"Enrollment will be rejected unless capacity override is approved.",
                severity=PolicySeverity.WARNING,
                override_authority_required=2,  # Department Chair level
                metadata={
                    "enrolled_count": capacity_info["enrolled_count"],
                    "max_enrollment": capacity_info["max_enrollment"],
                    "available_spots": capacity_info["available_spots"],
                    "class_header_id": class_header.id,
                    "course_code": (class_header.course.code if class_header.course else None),
                },
            )
            violations.append(violation)

        return violations

    def _calculate_capacity_info(self, class_header) -> dict[str, Any]:
        """Calculate current capacity information for a class.

        This replicates the logic from CapacityService.check_enrollment_capacity()
        but as a policy-aware method that can be easily tested and audited.
        """
        enrolled_count = ClassHeaderEnrollment.objects.filter(
            class_header=class_header,
            status__in=["ENROLLED", "ACTIVE"],
        ).count()

        max_enrollment = class_header.max_enrollment or 0
        available_spots = max(0, max_enrollment - enrolled_count)

        return {
            "can_enroll": available_spots > 0,
            "enrolled_count": enrolled_count,
            "max_enrollment": max_enrollment,
            "available_spots": available_spots,
            "is_full": enrolled_count >= max_enrollment,
        }

    def _has_override_authority(self, context: PolicyContext, capacity_info: dict[str, Any]) -> bool:
        """Check if the user in context has authority to override capacity limits.

        Authority Level 2 (Department Chair) can override capacity restrictions.
        This integrates with the AuthorityService to check institutional hierarchy.
        """
        # Import here to avoid circular imports
        from apps.accounts.services import AuthorityService

        if not context.user:
            return False

        authority_service = AuthorityService(context.user, context.effective_date)

        # Check if user has authority level 2 or higher (lower numbers = higher authority)
        # Department Chair is level 2, can override capacity
        return authority_service.has_authority_level(required_level=2, department=context.department)

    def get_policy_metadata(self) -> dict[str, Any]:
        """Return metadata for policy discovery and audit purposes."""
        return {
            "regulatory_reference": "University Enrollment Standards 3.1.2",
            "authority_levels": {
                "override": 2,  # Department Chair
                "description": "Department Chair can override capacity limits with documented reason",
            },
            "business_rules": [
                "Students cannot enroll in classes at maximum capacity",
                "Enrolled and Active students count toward capacity limits",
                "Available spots calculated as max_enrollment - enrolled_count",
                "Department Chair (level 2) authority can override capacity",
                "Students are rejected when class is full (no waitlist system)",
            ],
            "related_services": [
                "apps.enrollment.services.CapacityService",
                "apps.enrollment.services.EnrollmentService",
                "apps.accounts.services.AuthorityService",
            ],
        }
