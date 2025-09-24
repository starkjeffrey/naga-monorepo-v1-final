"""Teaching qualification policies for academic integrity.

Contains business rules for:
- Teacher degree requirements for different course levels
- Native speaker exceptions for language courses
- Special qualification overrides
- Department-specific teaching authorization
"""

from apps.common.policies.base import (
    Policy,
    PolicyContext,
    PolicyResult,
    PolicySeverity,
    PolicyViolation,
)


class TeachingQualificationPolicy(Policy):
    """██████████████████████████████████████████████████████████████████████████████
    ████                    TEACHING QUALIFICATION POLICY                     ████
    ██████████████████████████████████████████████████████████████████████████████

    BUSINESS RULES (Crystal Clear View):
    ────────────────────────────────────────────────────────────────────────────

    🎓 BACHELOR'S LEVEL COURSES:
       ✅ ALLOW: Master's or Doctorate degree holders
       ✅ ALLOW: Native English speakers with Bachelor's (English courses ONLY)
       ✅ ALLOW: Special qualifications with documentation
       ❌ DENY:  Bachelor's degree holders (non-English/non-native)

    🎓 GRADUATE LEVEL COURSES:
       ✅ ALLOW: Master's or Doctorate degree holders
       ✅ ALLOW: Special qualifications with documentation
       ❌ DENY:  Bachelor's degree holders (no exceptions)

    🏛️ OVERRIDE AUTHORITY:
       - Bachelor's course violations: Department Chair (level 2) can override
       - Graduate course violations: Dean (level 1) can override
       - Missing assignment: Academic Director (level 2) can override

    📋 REGULATORY REFERENCE:
       University Academic Standards Policy Section 4.2.1
       "Teaching Qualification Requirements"

    ██████████████████████████████████████████████████████████████████████████████
    """

    # ═══════════════════════════════════════════════════════════════════════════
    # POLICY METADATA
    # ═══════════════════════════════════════════════════════════════════════════

    @property
    def policy_code(self) -> str:
        return "TEACH_QUAL_001"

    @property
    def policy_name(self) -> str:
        return "Teaching Qualification Requirements"

    @property
    def policy_description(self) -> str:
        return (
            "Validates teacher degree requirements for course assignments. "
            "Ensures Bachelor's courses are taught by Master's+ degree holders "
            "with exceptions for native English speakers in English courses. "
            "Graduate courses require Master's minimum."
        )

    @property
    def regulatory_references(self) -> list[str]:
        return [
            "University Academic Standards Policy Section 4.2.1",
            "Faculty Qualification Guidelines 2024",
        ]

    def get_required_parameters(self) -> list[str]:
        return ["teacher", "course", "department"]

    # ═══════════════════════════════════════════════════════════════════════════
    # POLICY EVALUATION LOGIC
    # ═══════════════════════════════════════════════════════════════════════════

    def evaluate(
        self,
        context: PolicyContext,
        teacher=None,
        course=None,
        department=None,
        **kwargs,
    ) -> PolicyResult:
        """Main policy evaluation - determines ALLOW/DENY/REQUIRE_OVERRIDE.

        The business logic is intentionally kept simple here - all complexity
        is pushed into get_violations() for maximum clarity.
        """
        violations = self.get_violations(context, teacher=teacher, course=course, department=department)

        # No violations = immediate approval
        if not violations:
            return PolicyResult.ALLOW

        # All violations can be overridden = require authority check
        if all(v.can_be_overridden() for v in violations):
            return PolicyResult.REQUIRE_OVERRIDE

        # Some violations cannot be overridden = hard denial
        return PolicyResult.DENY

    def get_violations(
        self,
        context: PolicyContext,
        teacher=None,
        course=None,
        department=None,
        **kwargs,
    ) -> list[PolicyViolation]:
        """═══════════════════════════════════════════════════════════════════════
        DETAILED BUSINESS RULE EVALUATION
        ═══════════════════════════════════════════════════════════════════════

        This is where ALL the business logic lives. Each rule is clearly
        documented and isolated for easy auditing and modification.
        """
        violations = []

        # ─────────────────────────────────────────────────────────────────────
        # RULE 1: Teacher must have assignment in target department
        # ─────────────────────────────────────────────────────────────────────
        teaching_assignment = self._get_teaching_assignment(teacher, department)
        if not teaching_assignment:
            violations.append(
                PolicyViolation(
                    code="NO_TEACHING_ASSIGNMENT",
                    message=f"Teacher {teacher.person.full_name} has no active assignment in {department.name}",
                    severity=PolicySeverity.ERROR,
                    override_authority_required=2,  # Department Chair can override
                    metadata={
                        "teacher_id": teacher.id,
                        "department_id": department.id,
                        "rule": "Teacher must have active teaching assignment in department",
                    },
                ),
            )
            return violations  # Can't evaluate further without assignment

        # ─────────────────────────────────────────────────────────────────────
        # RULE 2: Bachelor's level course qualification requirements
        # ─────────────────────────────────────────────────────────────────────
        if course.level == "BA":
            if not self._meets_ba_course_requirements(teaching_assignment, department):
                violations.append(
                    PolicyViolation(
                        code="INSUFFICIENT_DEGREE_BA",
                        message=(
                            f"Bachelor's courses require Master's degree. "
                            f"Teacher has {teaching_assignment.get_minimum_degree_display()} degree. "
                            f"Exception: Native English speakers may teach English courses with Bachelor's."
                        ),
                        severity=PolicySeverity.ERROR,
                        override_authority_required=2,  # Department Chair can override
                        metadata={
                            "teacher_degree": teaching_assignment.minimum_degree,
                            "course_level": course.level,
                            "is_native_english": teaching_assignment.is_native_english_speaker,
                            "department_code": department.code,
                            "rule": "BA courses require Master's degree (except native English speakers for English)",
                        },
                    ),
                )

        # ─────────────────────────────────────────────────────────────────────
        # RULE 3: Graduate level course qualification requirements
        # ─────────────────────────────────────────────────────────────────────
        elif course.level == "GRADUATE":
            if not self._meets_graduate_course_requirements(teaching_assignment):
                violations.append(
                    PolicyViolation(
                        code="INSUFFICIENT_DEGREE_GRAD",
                        message=(
                            f"Graduate courses require Master's degree minimum. "
                            f"Teacher has {teaching_assignment.get_minimum_degree_display()} degree."
                        ),
                        severity=PolicySeverity.ERROR,
                        override_authority_required=1,  # Dean can override
                        metadata={
                            "teacher_degree": teaching_assignment.minimum_degree,
                            "course_level": course.level,
                            "rule": "Graduate courses require Master's degree minimum",
                        },
                    ),
                )

        # ─────────────────────────────────────────────────────────────────────
        # RULE 4: Teaching level authorization check
        # ─────────────────────────────────────────────────────────────────────
        if not self._has_teaching_level_authorization(teaching_assignment, course):
            violations.append(
                PolicyViolation(
                    code="UNAUTHORIZED_TEACHING_LEVEL",
                    message=(
                        f"Teacher authorized for {teaching_assignment.get_authorized_levels_display()} "
                        f"but course is {course.level} level."
                    ),
                    severity=PolicySeverity.WARNING,
                    override_authority_required=3,  # Academic Coordinator can override
                    metadata={
                        "authorized_levels": teaching_assignment.authorized_levels,
                        "course_level": course.level,
                        "rule": "Teacher must be authorized for course academic level",
                    },
                ),
            )

        return violations

    # ═══════════════════════════════════════════════════════════════════════════
    # BUSINESS RULE HELPER METHODS (Private Implementation Details)
    # ═══════════════════════════════════════════════════════════════════════════

    def _get_teaching_assignment(self, teacher, department):
        """Get active teaching assignment for teacher in department."""
        try:
            return teacher.teaching_assignments.get(department=department, is_active=True, is_current=True)
        except Exception:
            return None

    def _meets_ba_course_requirements(self, assignment, department) -> bool:
        """Business Rule: BA courses require Master's degree
        Exception: Native English speakers can teach English BA courses with Bachelor's
        """
        # Master's or Doctorate always qualifies
        if assignment.minimum_degree in ["MASTERS", "DOCTORATE"]:
            return True

        # Native English speaker exception for English departments
        if (
            assignment.is_native_english_speaker
            and department.code in ["ENG", "ENGLISH"]
            and assignment.minimum_degree == "BACHELORS"
        ):
            return True

        # Special qualifications override
        return bool(assignment.has_special_qualification)

    def _meets_graduate_course_requirements(self, assignment) -> bool:
        """Business Rule: Graduate courses require Master's degree minimum"""
        # Graduate teaching requires Master's or higher
        if assignment.minimum_degree in ["MASTERS", "DOCTORATE"]:
            return True

        # Special qualifications may override (rare cases)
        return bool(assignment.has_special_qualification)

    def _has_teaching_level_authorization(self, assignment, course) -> bool:
        """Business Rule: Teacher must be authorized for the course's academic level"""
        from apps.accounts.models import TeachingAssignment

        course_level_map = {"BA": "UNDERGRADUATE", "GRADUATE": "GRADUATE"}

        required_level = course_level_map.get(course.level)
        if not required_level:
            return True  # Unknown level, allow

        return assignment.authorized_levels in (
            required_level,
            TeachingAssignment.TeachingLevel.BOTH,
        )
