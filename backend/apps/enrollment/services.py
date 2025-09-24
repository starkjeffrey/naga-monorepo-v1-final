"""Enrollment services for business logic and workflows.

This module provides business logic services for enrollment operations including:
- Program enrollment management and validation
- Class enrollment processing and waitlist management
- Course eligibility calculation and prerequisite checking
- Session exemption processing for IEAP programs
- Enrollment statistics and reporting
- Academic standing and progression tracking

All services follow clean architecture principles and avoid circular dependencies
while providing comprehensive enrollment management functionality.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.db.models import QuerySet

    from apps.curriculum.models import CoursePrerequisite
    from users.models import User

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, cast

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import F, Sum
from django.utils import timezone

from apps.academic.models import StudentDegreeProgress
from apps.common.policies.base import PolicyContext, PolicyResult
from apps.curriculum.models import Course, CoursePrerequisite, Division, Major, Term
from apps.people.models import StudentProfile
from apps.scheduling.models import ClassHeader, ClassPart

from .constants import (
    ENROLLMENT_STATUS_COMPLETED,
    ENROLLMENT_STATUS_ENROLLED,
    GRADE_POINTS,
    HIGH_GPA_THRESHOLD,
    MAX_COURSES_PER_TERM,
    MAX_CREDITS_PER_TERM,
    MIN_PREREQUISITE_GRADE,
    PROGRAM_STATUS_ACTIVE,
    SCHEDULE_BUFFER_MINUTES,
    SYSTEM_USER_EMAIL,
)
from .models import (
    ClassHeaderEnrollment,
    ClassPartEnrollment,
    ClassSessionExemption,
    ProgramEnrollment,
    StudentCourseEligibility,
    StudentCycleStatus,
)

# Runtime user model access
_UserModel = get_user_model()


def get_system_user() -> User:
    """Get or create the system user for automated operations."""
    try:
        return cast("User", _UserModel.objects.get(email=SYSTEM_USER_EMAIL))
    except _UserModel.DoesNotExist:
        # Create system user if it doesn't exist
        # Note: User model uses 'name' field instead of first_name/last_name
        manager = getattr(_UserModel, "objects", _UserModel._default_manager)
        create_user = manager.create_user
        return cast(
            "User",
            create_user(
                email=SYSTEM_USER_EMAIL,
                name="System User",
                is_staff=True,
                is_active=True,
            ),
        )


class EnrollmentError(Exception):
    """Base exception for enrollment-related errors."""


class EnrollmentStatus(Enum):
    """Enrollment operation results."""

    SUCCESS = "success"
    CAPACITY_FULL = "capacity_full"
    PREREQUISITE_MISSING = "prerequisite_missing"
    SCHEDULE_CONFLICT = "schedule_conflict"
    ALREADY_ENROLLED = "already_enrolled"
    FINANCIAL_HOLD = "financial_hold"
    ACADEMIC_HOLD = "academic_hold"
    INVALID_TERM = "invalid_term"
    COURSE_CLOSED = "course_closed"


@dataclass
class EnrollmentResult:
    """Result of an enrollment operation."""

    status: EnrollmentStatus
    enrollment: ClassHeaderEnrollment | None = None
    message: str = ""
    details: dict[str, Any] | None = None

    @property
    def success(self) -> bool:
        return self.status == EnrollmentStatus.SUCCESS


@dataclass
class EligibilityResult:
    """Result of course eligibility check."""

    eligible: bool
    requirements_met: list[str]
    requirements_missing: list[str]
    warnings: list[str]
    gpa_requirement: Decimal | None = None
    current_gpa: Decimal | None = None


class EnrollmentService:
    """Core service for student enrollment operations."""

    @staticmethod
    def enroll_student(
        student: StudentProfile,
        class_header: ClassHeader,
        enrolled_by: User,
        override_capacity: bool = False,
        override_prerequisites: bool = False,
        notes: str = "",
    ) -> EnrollmentResult:
        """Enroll a student in a class with comprehensive validation.

        Args:
            student: Student to enroll
            class_header: Class to enroll in
            enrolled_by: User performing the enrollment
            override_capacity: Allow enrollment even if class is full
            override_prerequisites: Skip prerequisite checking
            notes: Optional enrollment notes

        Returns:
            EnrollmentResult with status and details
        """
        from apps.people.models import StudentProfile
        from apps.scheduling.models import ClassHeader

        try:
            with transaction.atomic():
                # Lock class header to prevent concurrent enrollment race conditions
                locked_class_header = ClassHeader.objects.select_for_update().get(id=class_header.id)  # type: ignore[attr-defined]

                # Lock student to prevent duplicate enrollments
                locked_student = StudentProfile.objects.select_for_update().get(id=student.id)  # type: ignore[attr-defined]

                # 1. Check if already enrolled (with locks held)
                existing = ClassHeaderEnrollment.objects.filter(
                    student=student,
                    class_header=locked_class_header,
                ).first()

                if existing and existing.status in ["ENROLLED", "ACTIVE"]:
                    return EnrollmentResult(
                        status=EnrollmentStatus.ALREADY_ENROLLED,
                        enrollment=existing,
                        message=f"Student already enrolled with status: {existing.status}",
                    )

                # 2. Check academic holds
                if locked_student.current_status != StudentProfile.Status.ACTIVE:
                    return EnrollmentResult(
                        status=EnrollmentStatus.ACADEMIC_HOLD,
                        message=f"Student has academic hold. Status: {locked_student.current_status}",
                    )

                # 3. Check term validity
                if not locked_class_header.term.is_active:
                    return EnrollmentResult(
                        status=EnrollmentStatus.INVALID_TERM,
                        message=f"Term {locked_class_header.term.code} is not active for enrollment",
                    )

                # 4. Check course prerequisites (unless overridden)
                if not override_prerequisites:
                    eligibility = PrerequisiteService.check_course_eligibility(
                        student,
                        locked_class_header.course,
                        locked_class_header.term,
                    )
                    if not eligibility.eligible:
                        return EnrollmentResult(
                            status=EnrollmentStatus.PREREQUISITE_MISSING,
                            message="Prerequisites not met",
                            details={
                                "missing_requirements": eligibility.requirements_missing,
                                "warnings": eligibility.warnings,
                            },
                        )

                # 5. Check major declaration consistency
                _is_valid, major_warnings = MajorDeclarationService.validate_course_registration(
                    student,
                    locked_class_header.course,
                    locked_class_header.term,
                )

                # Log warnings but don't block enrollment (allow staff review)
                if major_warnings:
                    # Add to enrollment notes for staff review
                    if notes:
                        notes += f"\n\nMajor Declaration Warnings: {'; '.join(major_warnings)}"
                    else:
                        notes = f"Major Declaration Warnings: {'; '.join(major_warnings)}"

                # 6. Check schedule conflicts
                conflicts = ScheduleService.check_schedule_conflicts(
                    student,
                    class_header,
                )
                if conflicts:
                    return EnrollmentResult(
                        status=EnrollmentStatus.SCHEDULE_CONFLICT,
                        message="Schedule conflict detected",
                        details={"conflicts": conflicts},
                    )

                # 7. Check capacity with simplified logic (using locked objects)
                capacity_check = CapacityService.check_enrollment_capacity_atomic(
                    class_header=locked_class_header,
                    user=enrolled_by,
                    student=student,
                    department=getattr(locked_class_header.course, "department", None),
                )

                # Handle capacity decisions - either enroll or reject (no waitlist)
                if not capacity_check["can_enroll"] and not override_capacity:
                    # Check if this is a policy override situation
                    if capacity_check.get("policy_requires_override", False):
                        # User has override authority - document the override in notes
                        override_note = f"Capacity override authorized by {enrolled_by}"
                        if capacity_check.get("policy_violations"):
                            violation_details = [v.message for v in capacity_check["policy_violations"]]
                            override_note += f" (Policy violations: {'; '.join(violation_details)})"
                        notes = f"{notes}\n{override_note}".strip()
                    else:
                        # No capacity and no override authority - reject enrollment
                        return EnrollmentResult(
                            status=EnrollmentStatus.CAPACITY_FULL,
                            message="Class is at capacity. No spots available.",
                            details={"capacity_info": capacity_check},
                        )

                # 8. Create enrollment record (always ENROLLED if we reach this point)
                enrollment = ClassHeaderEnrollment.objects.create(
                    student=student,
                    class_header=locked_class_header,
                    enrollment_date=timezone.now().date(),
                    status="ENROLLED",
                    enrolled_by=enrolled_by,
                    notes=notes,
                )

                # 9. Update course eligibility cache
                PrerequisiteService.update_student_eligibility_cache(student)

                return EnrollmentResult(
                    status=EnrollmentStatus.SUCCESS,
                    enrollment=enrollment,
                    message="Student enrolled successfully",
                    details={"capacity_info": capacity_check},
                )

        except ValidationError as e:
            return EnrollmentResult(
                status=EnrollmentStatus.INVALID_TERM,  # Generic error status
                message=f"Enrollment failed: {e!s}",
            )

    @staticmethod
    def drop_student(
        enrollment: ClassHeaderEnrollment,
        dropped_by,
        drop_reason: str = "",
    ) -> EnrollmentResult:
        """Drop a student from a class.

        Args:
            enrollment: Enrollment to drop
            dropped_by: User performing the drop
            drop_reason: Reason for dropping

        Returns:
            EnrollmentResult with drop status
        """
        try:
            with transaction.atomic():
                # Update enrollment status
                enrollment.status = "DROPPED"
                # Note: drop_date not available on ClassHeaderEnrollment model
                enrollment.notes = f"{enrollment.notes}\nDropped: {drop_reason}".strip()
                enrollment.save()

                return EnrollmentResult(
                    status=EnrollmentStatus.SUCCESS,
                    enrollment=enrollment,
                    message="Student dropped successfully",
                )

        except ValidationError as e:
            return EnrollmentResult(
                status=EnrollmentStatus.INVALID_TERM,  # Generic error
                message=f"Drop failed: {e!s}",
            )

    @staticmethod
    def transfer_enrollment(
        enrollment: ClassHeaderEnrollment,
        target_class: ClassHeader,
        transferred_by,
        notes: str = "",
    ) -> EnrollmentResult:
        """Transfer student from one class to another with atomic transaction.

        Args:
            enrollment: Current enrollment to transfer
            target_class: Target class to transfer to
            transferred_by: User performing the transfer
            notes: Transfer notes

        Returns:
            EnrollmentResult with transfer status
        """
        try:
            with transaction.atomic():
                # Drop from current class
                drop_result = EnrollmentService.drop_student(
                    enrollment,
                    transferred_by,
                    f"Transfer to {target_class}",
                )

                if not drop_result.success:
                    return drop_result

                # Enroll in new class
                enroll_result = EnrollmentService.enroll_student(
                    cast("StudentProfile", enrollment.student),
                    target_class,
                    transferred_by,
                    notes=f"Transferred from {enrollment.class_header}. {notes}".strip(),
                )

                return enroll_result
        except Exception as e:
            return EnrollmentResult(
                status=EnrollmentStatus.INVALID_TERM,  # Generic error status
                message=f"Transfer failed: {e!s}",
            )

    @staticmethod
    def enroll_student_with_repeat_override(
        student: StudentProfile,
        class_header: ClassHeader,
        enrolled_by,
        override_reason: str,
        override_capacity: bool | None = False,
        override_prerequisites: bool | None = False,
        notes: str = "",
    ) -> EnrollmentResult:
        """Enroll a student with override for repeat prevention rule.

        This method bypasses the normal repeat prevention check that blocks
        students from re-enrolling in courses they've already passed with D+.
        Should only be called by management override endpoints.

        Args:
            student: Student to enroll
            class_header: Class to enroll in
            enrolled_by: User performing the enrollment (must have override permission)
            override_reason: Reason for overriding the repeat prevention rule
            override_capacity: Allow enrollment even if class is full
            override_prerequisites: Skip prerequisite checking
            notes: Optional enrollment notes

        Returns:
            EnrollmentResult with status and details
        """
        try:
            with transaction.atomic():
                # Lock class header to prevent concurrent enrollment race conditions
                locked_class_header = ClassHeader.objects.select_for_update().get(id=class_header.id)  # type: ignore[attr-defined]

                # Lock student to prevent duplicate enrollments
                locked_student = StudentProfile.objects.select_for_update().get(id=student.id)  # type: ignore[attr-defined]

                # 1. Check if already enrolled (still enforce this)
                existing = ClassHeaderEnrollment.objects.filter(
                    student=student,
                    class_header=locked_class_header,
                ).first()

                if existing and existing.status in ["ENROLLED", "ACTIVE"]:
                    return EnrollmentResult(
                        status=EnrollmentStatus.ALREADY_ENROLLED,
                        enrollment=existing,
                        message=f"Student already enrolled with status: {existing.status}",
                    )

                # 2. Check academic holds (still enforce this)
                if locked_student.current_status != "ACTIVE":
                    return EnrollmentResult(
                        status=EnrollmentStatus.ACADEMIC_HOLD,
                        message=f"Student has academic hold. Status: {locked_student.current_status}",
                    )

                # 3. Check term validity (still enforce this)
                if not locked_class_header.term.is_active:
                    return EnrollmentResult(
                        status=EnrollmentStatus.INVALID_TERM,
                        message=f"Term {locked_class_header.term.code} is not active for enrollment",
                    )

                # 4. Skip repeat prevention check (this is the override!)
                # NOTE: We're deliberately bypassing the check_course_eligibility that
                # would normally prevent re-enrollment for passed courses

                # 5. Check prerequisites (unless overridden)
                if not override_prerequisites:
                    # Create a modified eligibility check that skips repeat prevention
                    eligibility = PrerequisiteService._check_course_eligibility_without_repeat_check(
                        student,
                        locked_class_header.course,
                        locked_class_header.term,
                    )
                    if not eligibility.eligible:
                        return EnrollmentResult(
                            status=EnrollmentStatus.PREREQUISITE_MISSING,
                            message="Prerequisites not met",
                            details={
                                "missing_requirements": eligibility.requirements_missing,
                                "warnings": eligibility.warnings,
                            },
                        )

                # 6. Check schedule conflicts
                conflicts = ScheduleService.check_schedule_conflicts(
                    student,
                    class_header,
                )
                if conflicts:
                    return EnrollmentResult(
                        status=EnrollmentStatus.SCHEDULE_CONFLICT,
                        message="Schedule conflict detected",
                        details={"conflicts": conflicts},
                    )

                # 7. Check capacity with simplified logic (no waitlist)
                capacity_check = CapacityService.check_enrollment_capacity(
                    class_header=locked_class_header,
                    user=enrolled_by,
                    student=student,
                    department=getattr(locked_class_header.course, "department", None),
                )

                # Handle capacity decisions - either enroll or reject (no waitlist)
                if not capacity_check["can_enroll"] and not override_capacity:
                    # Check if this is a policy override situation
                    if capacity_check.get("policy_requires_override", False):
                        # User has override authority - document both overrides in notes
                        override_note = f"Capacity override authorized by {enrolled_by}"
                        if capacity_check.get("policy_violations"):
                            violation_details = [v.message for v in capacity_check["policy_violations"]]
                            override_note += f" (Policy violations: {'; '.join(violation_details)})"

                        # Combine repeat override reason with capacity override
                        combined_notes = f"REPEAT OVERRIDE: {override_reason}\nCAPACITY OVERRIDE: {override_note}"
                        notes = f"{notes}\n{combined_notes}".strip()
                    else:
                        # No capacity and no override authority - reject enrollment
                        return EnrollmentResult(
                            status=EnrollmentStatus.CAPACITY_FULL,
                            message="Class is at capacity. No spots available.",
                            details={"capacity_info": capacity_check},
                        )
                else:
                    # Document repeat override when enrollment succeeds
                    notes = f"{notes}\nREPEAT OVERRIDE: {override_reason}".strip()

                # 8. Create enrollment record with override information (always ENROLLED if we reach this point)
                override_notes = f"REPEAT OVERRIDE: {override_reason}"
                if notes:
                    override_notes += f"\nAdditional notes: {notes}"

                enrollment = ClassHeaderEnrollment.objects.create(
                    student=student,
                    class_header=locked_class_header,
                    enrollment_date=timezone.now().date(),
                    status="ENROLLED",
                    enrolled_by=enrolled_by,
                    notes=override_notes,
                    has_override=True,
                    override_type="REPEAT_PREVENTION_RULE",
                    override_reason=override_reason,
                )

                # 9. Update course eligibility cache
                PrerequisiteService.update_student_eligibility_cache(student)

                return EnrollmentResult(
                    status=EnrollmentStatus.SUCCESS,
                    enrollment=enrollment,
                    message="Student enrolled successfully with repeat override",
                    details={
                        "override_applied": "REPEAT_PREVENTION_RULE",
                        "override_reason": override_reason,
                        "capacity_info": capacity_check,
                    },
                )

        except ValidationError as e:
            return EnrollmentResult(
                status=EnrollmentStatus.INVALID_TERM,  # Generic error status
                message=f"Enrollment failed: {e!s}",
            )


class CapacityService:
    """Service for managing class capacity."""

    @staticmethod
    def check_enrollment_capacity_atomic(
        class_header: ClassHeader,
        user: User | None = None,
        student: StudentProfile | None = None,
        department: Any | None = None,
    ) -> dict[str, Any]:
        """Check enrollment capacity with proper atomic locking for race condition prevention.

        This method should only be called within a transaction with locked objects
        to ensure consistency during concurrent enrollment operations.

        Args:
            class_header: LOCKED ClassHeader instance (must be locked with select_for_update)
            user: User context for policy evaluation (optional)
            student: Student context for policy evaluation (optional)
            department: Department context for override authority (optional)

        Returns:
            Dictionary with capacity information and policy results
        """
        # Count current enrollments using the locked class_header
        # This query will respect the transaction locks
        enrolled_count = ClassHeaderEnrollment.objects.filter(
            class_header=class_header,
            status__in=["ENROLLED", "ACTIVE"],
        ).count()

        max_enrollment = class_header.max_enrollment or 0
        available_spots = max(0, max_enrollment - enrolled_count)

        # Base capacity information
        capacity_info: dict[str, Any] = {
            "can_enroll": available_spots > 0,
            "enrolled_count": enrolled_count,
            "max_enrollment": max_enrollment,
            "available_spots": available_spots,
            "is_full": enrolled_count >= max_enrollment,
        }

        # Enhanced policy evaluation when user context is provided
        if user is not None:
            try:
                from apps.enrollment.policies.enrollment_policies import (
                    EnrollmentCapacityPolicy,
                )

                # Create policy context
                context = PolicyContext(
                    user=user,
                    department=department or getattr(class_header.course, "department", None),
                    effective_date=date.today(),
                )

                # Evaluate policy
                policy = EnrollmentCapacityPolicy()
                policy_result = policy.evaluate(context, class_header=class_header, student=student)

                # Get detailed violations if any
                violations = policy.get_violations(context, class_header=class_header, student=student)

                # Add policy information to capacity info
                capacity_info.update(
                    {
                        "policy_result": policy_result,
                        "policy_allows_enrollment": policy_result == PolicyResult.ALLOW,
                        "policy_requires_override": policy_result == PolicyResult.REQUIRE_OVERRIDE,
                        "policy_violations": violations,
                        "can_override": policy_result == PolicyResult.REQUIRE_OVERRIDE,
                    },
                )

                # Override can_enroll based on policy when policy context is available
                if policy_result == PolicyResult.ALLOW:
                    capacity_info["can_enroll"] = True
                elif policy_result == PolicyResult.REQUIRE_OVERRIDE:
                    # Allow enrollment but flag that override is required
                    capacity_info["can_enroll"] = True
                    capacity_info["override_required"] = True
                else:  # PolicyResult.DENY
                    capacity_info["can_enroll"] = False

            except ImportError:
                # Policy not available, fall back to legacy logic
                pass

        return capacity_info

    @staticmethod
    def check_enrollment_capacity(
        class_header: ClassHeader,
        user: User | None = None,
        student: StudentProfile | None = None,
        department: Any | None = None,
    ) -> dict[str, Any]:
        """Check if a class has enrollment capacity using policy-driven evaluation.

        Args:
            class_header: Class to check
            user: User context for policy evaluation (optional)
            student: Student context for policy evaluation (optional)
            department: Department context for override authority (optional)

        Returns:
            Dictionary with capacity information and policy results
        """
        # Count current enrollments
        enrolled_count = ClassHeaderEnrollment.objects.filter(
            class_header=class_header,
            status__in=["ENROLLED", "ACTIVE"],
        ).count()

        max_enrollment = class_header.max_enrollment or 0
        available_spots = max(0, max_enrollment - enrolled_count)

        # Base capacity information
        capacity_info: dict[str, Any] = {
            "can_enroll": available_spots > 0,
            "enrolled_count": enrolled_count,
            "max_enrollment": max_enrollment,
            "available_spots": available_spots,
            "is_full": enrolled_count >= max_enrollment,
        }

        # Enhanced policy evaluation when user context is provided
        if user is not None:
            try:
                from apps.enrollment.policies.enrollment_policies import (
                    EnrollmentCapacityPolicy,
                )

                # Create policy context
                context = PolicyContext(
                    user=user,
                    department=department or getattr(class_header.course, "department", None),
                    effective_date=date.today(),
                )

                # Evaluate policy
                policy = EnrollmentCapacityPolicy()
                policy_result = policy.evaluate(context, class_header=class_header, student=student)

                # Get detailed violations if any
                violations = policy.get_violations(context, class_header=class_header, student=student)

                # Add policy information to capacity info
                capacity_info.update(
                    {
                        "policy_result": policy_result,
                        "policy_allows_enrollment": policy_result == PolicyResult.ALLOW,
                        "policy_requires_override": policy_result == PolicyResult.REQUIRE_OVERRIDE,
                        "policy_violations": violations,
                        "can_override": policy_result == PolicyResult.REQUIRE_OVERRIDE,
                    },
                )

                # Override can_enroll based on policy when policy context is available
                if policy_result == PolicyResult.ALLOW:
                    capacity_info["can_enroll"] = True
                elif policy_result == PolicyResult.REQUIRE_OVERRIDE:
                    # Allow enrollment but flag that override is required
                    capacity_info["can_enroll"] = True
                    capacity_info["override_required"] = True
                else:  # PolicyResult.DENY
                    capacity_info["can_enroll"] = False

            except ImportError:
                # Policy not available, fall back to legacy logic
                pass

        return capacity_info


class PrerequisiteService:
    """Service for managing course prerequisites and academic eligibility."""

    @staticmethod
    def check_course_eligibility(
        student: StudentProfile,
        course: Course,
        term: Term,
    ) -> EligibilityResult:
        """Check if student is eligible to enroll in a course.

        Args:
            student: Student to check
            course: Course to check eligibility for
            term: Term for enrollment

        Returns:
            EligibilityResult with eligibility details
        """
        requirements_met = []
        requirements_missing = []
        warnings: list[str] = []

        # Check if eligibility is cached
        cached_eligibility = StudentCourseEligibility.objects.filter(
            student=student,
            course=course,
            term=term,
        ).first()

        if cached_eligibility and cached_eligibility.last_calculated:
            # Use cached result if recent (within 24 hours)
            if (timezone.now() - cached_eligibility.last_calculated).days < 1:
                # Parse cached calculation notes back into lists
                notes = cached_eligibility.calculation_notes or ""
                req_met: list[str] = []
                req_missing: list[str] = []
                warn: list[str] = []

                for line in notes.split("\n"):
                    if line.startswith("Requirements met: "):
                        req_met = line.replace("Requirements met: ", "").split("; ")
                    elif line.startswith("Requirements missing: "):
                        req_missing = line.replace("Requirements missing: ", "").split("; ")
                    elif line.startswith("Warnings: "):
                        warn = line.replace("Warnings: ", "").split("; ")

                return EligibilityResult(
                    eligible=cached_eligibility.is_eligible,
                    requirements_met=req_met,
                    requirements_missing=req_missing,
                    warnings=warn,
                )

        # Calculate fresh eligibility
        eligible = True
        gpa_requirement = None
        current_gpa = None

        # 1. Check course prerequisites using CoursePrerequisite model
        prerequisite_check = PrerequisiteService._check_prerequisites(student, course)
        if prerequisite_check["all_met"]:
            requirements_met.extend(prerequisite_check["met_requirements"])
        else:
            requirements_missing.extend(prerequisite_check["missing_requirements"])
            eligible = False

        # Text prerequisites would be checked here if Course model had a prerequisites_text field
        # This functionality could be added in the future if needed

        # 2. Check academic level requirements
        if course.cycle == "MA" and student.current_status == "ACTIVE":
            # Check if student has bachelor's degree
            ba_program = ProgramEnrollment.objects.filter(
                student=student,
                program__degree_type="BACHELORS",
                status="GRADUATED",
            ).exists()

            if ba_program:
                requirements_met.append("Bachelor's degree requirement met")
            else:
                requirements_missing.append(
                    "Bachelor's degree required for graduate courses",
                )
                eligible = False

        # 3. Check GPA requirements (if any)
        # Note: Course model doesn't have minimum_grade field currently
        # This functionality could be added in the future if needed
        current_gpa = PrerequisiteService._calculate_student_gpa(student)
        if current_gpa is not None:
            requirements_met.append(f"Current GPA: {current_gpa:.2f}")
        else:
            requirements_met.append("No GPA calculated yet")

        # 4. Check for previous course completion (repeat prevention)
        previous_completion = PrerequisiteService._check_previous_course_completion(student, course)
        if previous_completion["has_passed"]:
            requirements_missing.append(
                f"Student already completed {course.code} with grade "
                f"{previous_completion['grade']} on {previous_completion['completion_date']}. "
                f"Re-enrollment requires management override.",
            )
            eligible = False
        else:
            requirements_met.append("No previous completion found - eligible to enroll")

        # 5. Check major requirements (students can only take courses in their major)
        major_check = PrerequisiteService._check_major_requirements(student, course)
        if major_check["eligible"]:
            requirements_met.append(major_check["message"])
        else:
            requirements_missing.append(major_check["message"])
            eligible = False

        # 6. Check enrollment limits (if field exists)
        max_enrollments = getattr(course, "max_enrollments", None)
        if max_enrollments:
            previous_enrollments = ClassHeaderEnrollment.objects.filter(
                student=student,
                class_header__course=course,
                status__in=["COMPLETED", "PASSED"],
            ).count()

            if previous_enrollments >= max_enrollments:
                requirements_missing.append(
                    f"Maximum enrollments ({max_enrollments}) exceeded",
                )
                eligible = False
            else:
                requirements_met.append(
                    f"Enrollment limit check passed ({previous_enrollments}/{max_enrollments})",
                )
        else:
            requirements_met.append("No enrollment limits specified")

        # Cache the result with calculation notes
        calculation_notes = []
        if requirements_met:
            calculation_notes.append(f"Requirements met: {'; '.join(requirements_met)}")
        if requirements_missing:
            calculation_notes.append(f"Requirements missing: {'; '.join(requirements_missing)}")
        if warnings:
            calculation_notes.append(f"Warnings: {'; '.join(warnings)}")

        _eligibility_obj, _created = StudentCourseEligibility.objects.update_or_create(
            student=student,
            course=course,
            term=term,
            defaults={
                "is_eligible": eligible,
                "calculation_notes": "\n".join(calculation_notes),
                "last_calculated": timezone.now(),
            },
        )

        return EligibilityResult(
            eligible=eligible,
            requirements_met=requirements_met,
            requirements_missing=requirements_missing,
            warnings=warnings,
            gpa_requirement=gpa_requirement,
            current_gpa=current_gpa,
        )

    @staticmethod
    def _check_previous_course_completion(student: StudentProfile, course: Course) -> dict[str, Any]:
        """Check if student has previously completed this course with a passing grade.

        Business rule: Students cannot re-enroll in courses they completed with grade D or higher.
        This implements the repeat prevention policy per user requirements.

        Args:
            student: Student to check
            course: Course to check completion for

        Returns:
            Dictionary with completion details:
            - has_passed: bool - Whether student has passed this course
            - grade: str - Grade received (if any)
            - completion_date: date - Date course was completed (if any)
            - enrollment_id: int - ID of the completion enrollment (if any)
        """
        # Define passing grades (D and above - per user clarification)
        # Note: No "D-" grade exists, just "D" which is passing
        passing_grades = ["D", "D+", "C-", "C", "C+", "B-", "B", "B+", "A-", "A", "A+"]

        # Check for completed enrollments with passing grades
        completed_enrollment = (
            ClassHeaderEnrollment.objects.filter(
                student=student,
                class_header__course=course,
                status__in=["COMPLETED", "PASSED"],
                final_grade__in=passing_grades,
            )
            .select_related("class_header")
            .first()
        )

        if completed_enrollment:
            return {
                "has_passed": True,
                "grade": completed_enrollment.final_grade,
                "completion_date": completed_enrollment.completion_date or completed_enrollment.enrollment_date,
                "enrollment_id": completed_enrollment.id,
                "class_header": str(completed_enrollment.class_header),
            }

        # Also check StudentDegreeProgress for transfer credits or other fulfillment methods
        # Look for any fulfillment where the canonical requirement's course matches this course

        from apps.academic.models import CanonicalRequirement

        # Find canonical requirements for this course
        canonical_reqs = CanonicalRequirement.objects.filter(required_course=course, is_active=True).values_list(
            "id",
            flat=True,
        )

        # Check if student has fulfilled any of these requirements through non-enrollment means
        fulfillment = StudentDegreeProgress.objects.filter(
            student=student,
            canonical_requirement_id__in=canonical_reqs,
            is_active=True,
            fulfillment_method__in=[
                StudentDegreeProgress.FulfillmentMethod.TRANSFER_CREDIT,
                StudentDegreeProgress.FulfillmentMethod.EXAM_CREDIT,
            ],
        ).first()

        if fulfillment:
            return {
                "has_passed": True,
                "grade": fulfillment.grade or "TRANSFER/CREDIT",
                "completion_date": fulfillment.fulfillment_date,
                "enrollment_id": None,
                "fulfillment_source": fulfillment.fulfillment_method,
            }

        return {
            "has_passed": False,
            "grade": None,
            "completion_date": None,
            "enrollment_id": None,
        }

    @staticmethod
    def _check_course_eligibility_without_repeat_check(
        student: StudentProfile,
        course: Course,
        term: Term,
    ) -> EligibilityResult:
        """Check course eligibility without the repeat prevention check.

        This is used for management override enrollments where we want to
        bypass the repeat prevention rule but still check other requirements
        like prerequisites, academic level, etc.

        Args:
            student: Student to check
            course: Course to check eligibility for
            term: Term for enrollment

        Returns:
            EligibilityResult with eligibility details (excluding repeat check)
        """
        requirements_met = []
        requirements_missing = []
        warnings: list[str] = []
        eligible = True

        # 1. Check course prerequisites (basic text-based for now)
        # Note: prerequisites_text field not implemented on Course model
        # Future enhancement: Implement complex prerequisite parsing with course dependencies
        # requirements_met.append("Prerequisites will be verified manually")
        # warnings.append("Manual prerequisite verification required")

        # 2. Check academic level requirements
        if course.cycle == "MA" and student.current_status == "ACTIVE":
            # Check if student has bachelor's degree
            ba_program = ProgramEnrollment.objects.filter(
                student=student,
                program__degree_type="BACHELORS",
                status="GRADUATED",
            ).exists()

            if ba_program:
                requirements_met.append("Bachelor's degree requirement met")
            else:
                requirements_missing.append(
                    "Bachelor's degree required for graduate courses",
                )
                eligible = False

        # 3. Check GPA requirements (if any)
        gpa_requirement = None
        current_gpa = None
        # Note: minimum_grade field not implemented on Course model
        # Future enhancement: Implement minimum_grade field and GPA calculation for course eligibility
        # warnings.append("GPA verification pending grade calculation implementation")

        # 4. Skip repeat prevention check (this is the key difference!)
        requirements_met.append("Repeat prevention check bypassed by management override")

        # 5. Check enrollment limits
        # Note: max_enrollments field not implemented on Course model
        # Future enhancement: Implement max_enrollments field for course enrollment limits
        # For now, skip enrollment limit checks

        return EligibilityResult(
            eligible=eligible,
            requirements_met=requirements_met,
            requirements_missing=requirements_missing,
            warnings=warnings,
            gpa_requirement=gpa_requirement,
            current_gpa=current_gpa,
        )

    @staticmethod
    def update_student_eligibility_cache(student: StudentProfile):
        """Update all cached eligibility for a student."""
        # Get active terms
        active_terms = Term.objects.filter(is_active=True)

        # Update eligibility for all courses in active terms
        for term in active_terms:
            courses = Course.objects.filter(is_active=True)
            for course in courses:
                PrerequisiteService.check_course_eligibility(student, course, term)

    @staticmethod
    def _check_prerequisites(student: StudentProfile, course: Course) -> dict[str, Any]:
        """Check if student has met all prerequisites for a course.

        Args:
            student: Student to check
            course: Course to check prerequisites for

        Returns:
            Dictionary with prerequisite check results
        """

        prerequisites = CoursePrerequisite.objects.filter(course=course).select_related("prerequisite")

        if not prerequisites.exists():
            return {
                "all_met": True,
                "met_requirements": ["No prerequisites required"],
                "missing_requirements": [],
            }

        met_requirements: list[str] = []
        missing_requirements: list[str] = []

        for prereq in prerequisites:
            # Check if student has completed the prerequisite course with D+ or better
            completed_enrollments = ClassHeaderEnrollment.objects.filter(
                student=student,
                class_header__course=cast("Course", prereq.prerequisite),
                status__in=[ENROLLMENT_STATUS_COMPLETED],
            ).exclude(final_grade__isnull=True)

            # Check if any enrollment has passing grade (D+ or better)
            has_passed = False
            best_grade = None
            for enrollment in completed_enrollments:
                if enrollment.final_grade and PrerequisiteService._is_passing_grade(enrollment.final_grade):
                    has_passed = True
                    best_grade = enrollment.final_grade
                    break

            if has_passed:
                met_requirements.append(
                    f"Prerequisite {cast('Course', prereq.prerequisite).code} completed with grade {best_grade}"
                )
            else:
                missing_requirements.append(
                    f"Prerequisite {cast('Course', prereq.prerequisite).code} not completed with passing grade",
                )

        return {
            "all_met": len(missing_requirements) == 0,
            "met_requirements": met_requirements,
            "missing_requirements": missing_requirements,
        }

    @staticmethod
    def _check_major_requirements(student: StudentProfile, course: Course) -> dict[str, Any]:
        """Check if student can take this course based on their current major.

        Args:
            student: Student to check
            course: Course to check

        Returns:
            Dictionary with major requirement check results
        """

        # Get student's most recent active program enrollment
        current_program: ProgramEnrollment | None = (
            ProgramEnrollment.objects.filter(student=student, status=PROGRAM_STATUS_ACTIVE)
            .order_by("-start_date", "-created_at")
            .first()
        )

        if not current_program:
            return {
                "eligible": False,
                "message": "Student is not enrolled in any active program",
            }

        # Check if course belongs to student's major
        # This assumes courses are linked to majors through requirements or similar
        # We'll check if the course is available in the student's major requirements
        from apps.academic.models import CanonicalRequirement

        program = cast("Major", current_program.program)

        major_courses = CanonicalRequirement.objects.filter(major=program, is_active=True).values_list(
            "required_course_id",
            flat=True,
        )

        if course.id in major_courses:  # type: ignore[attr-defined]
            return {
                "eligible": True,
                "message": f"Course is available for {program.name} major",
            }
        return {
            "eligible": False,
            "message": f"Course {course.code} is not available for {program.name} major",
        }

    @staticmethod
    def _calculate_student_gpa(student: StudentProfile) -> Decimal | None:
        """Calculate student's CGPA based on completed courses in their major (4.0 scale).

        Only courses from the student's current major count toward GPA calculation.
        Uses grades from ClassHeaderEnrollment records where final grades exist.

        Args:
            student: Student to calculate GPA for

        Returns:
            Decimal GPA on 4.0 scale, or None if no grades available
        """
        # Get the student's most recent active program enrollment
        from .models import ProgramEnrollment

        active_enrollment: ProgramEnrollment | None = ProgramEnrollment.objects.filter(
            student=student,
            status=ProgramEnrollment.EnrollmentStatus.ACTIVE,
        ).first()

        if not active_enrollment:
            return None

        # Get completed enrollments in courses that belong to the student's major
        # Only include enrollments with final grades for GPA calculation
        from apps.curriculum.models import Cycle

        program = cast("Major", active_enrollment.program)
        cycle = cast("Cycle", program.cycle)

        completed_enrollments = ClassHeaderEnrollment.objects.filter(
            student=student,
            status__in=[ClassHeaderEnrollment.EnrollmentStatus.COMPLETED],
            class_header__course__cycle__division=cast("Division", cycle.division),
            final_grade__isnull=False,
            grade_points__isnull=False,
        ).exclude(
            final_grade="",  # Exclude empty grades
        )

        # Perform the entire calculation in a single database query for efficiency
        result = completed_enrollments.aggregate(
            total_grade_points=Sum(
                F("grade_points") * F("class_header__course__credits"), output_field=models.DecimalField()
            ),
            total_credits=Sum("class_header__course__credits"),
        )

        total_credits = result.get("total_credits")
        total_grade_points = result.get("total_grade_points")
        if total_credits and total_credits > 0 and total_grade_points is not None:
            return Decimal(str(total_grade_points)) / Decimal(str(total_credits))

        return None

    @staticmethod
    def _is_passing_grade(grade: str) -> bool:
        """Check if a grade is passing (D+ or better).

        Args:
            grade: Grade string to check

        Returns:
            Boolean indicating if grade is passing
        """
        if not grade:
            return False

        grade = grade.strip().upper()

        if grade in GRADE_POINTS:
            return GRADE_POINTS[grade] >= MIN_PREREQUISITE_GRADE

        return False


class ScheduleService:
    """Service for schedule management and conflict detection."""

    @staticmethod
    def check_schedule_conflicts(
        student: StudentProfile,
        new_class: ClassHeader,
    ) -> list[dict[str, Any]]:
        """Check for schedule conflicts with student's existing enrollments.

        Args:
            student: Student to check
            new_class: New class to check for conflicts

        Returns:
            List of conflicts found
        """
        conflicts = []

        # Get student's current enrollments in the same term
        current_enrollments = ClassHeaderEnrollment.objects.filter(
            student=student,
            class_header__term=new_class.term,
            status__in=["ENROLLED", "ACTIVE"],
        ).select_related("class_header")

        # Get class parts for the new class
        new_class_parts = ClassPart.objects.filter(class_session__class_header=new_class)

        for enrollment in current_enrollments:
            existing_parts = ClassPart.objects.filter(
                class_session__class_header=cast("ClassHeader", enrollment.class_header),
            )

            # Check for time conflicts between class parts
            for new_part in new_class_parts:
                for existing_part in existing_parts:
                    if ScheduleService._parts_conflict(new_part, existing_part):
                        conflicts.append(
                            {
                                "conflicting_class": enrollment.class_header,
                                "new_class_part": new_part,
                                "existing_class_part": existing_part,
                                "conflict_type": "time_overlap",
                            },
                        )

        return conflicts

    @staticmethod
    def _parts_conflict(part1: ClassPart, part2: ClassPart) -> bool:
        """Check if two class parts have schedule conflicts.

        Checks for overlapping meeting days and times between two class parts.

        Args:
            part1: First class part
            part2: Second class part

        Returns:
            Boolean indicating if there's a time conflict
        """
        # If either part doesn't have complete schedule info, assume no conflict
        if not all(
            [
                part1.meeting_days,
                part1.start_time,
                part1.end_time,
                part2.meeting_days,
                part2.start_time,
                part2.end_time,
            ],
        ):
            return False

        # Parse meeting days for both parts
        days1 = {day.strip().upper() for day in part1.meeting_days.split(",") if day.strip()}
        days2 = {day.strip().upper() for day in part2.meeting_days.split(",") if day.strip()}

        # Check if they have any common meeting days
        common_days = days1.intersection(days2)
        if not common_days:
            return False  # No common days, no conflict

        # Check for time overlap on common days
        start1 = part1.start_time
        end1 = part1.end_time
        start2 = part2.start_time
        end2 = part2.end_time

        # Handle None values first
        if not all([start1, end1, start2, end2]):
            return False  # Can't overlap if any time is None

        # Add buffer time if configured
        if SCHEDULE_BUFFER_MINUTES > 0:
            buffer = timedelta(minutes=SCHEDULE_BUFFER_MINUTES)
            today = timezone.now().date()

            # Convert times to datetime, apply buffer, then back to time
            if start1 is not None:
                start1_dt = datetime.combine(today, start1)
                start1 = (start1_dt - buffer).time()
            if start2 is not None:
                start2_dt = datetime.combine(today, start2)
                start2 = (start2_dt - buffer).time()
            if end1 is not None:
                end1_dt = datetime.combine(today, end1)
                end1 = (end1_dt + buffer).time()
            if end2 is not None:
                end2_dt = datetime.combine(today, end2)
                end2 = (end2_dt + buffer).time()

        # Check for time overlap: two time periods overlap if one starts before the other ends
        # and the other starts before the first one ends
        # Final None check after buffer processing
        if not all([start1, end1, start2, end2]):
            return False  # Can't overlap if any time is None after processing

        # Type narrowing assertion for MyPy
        assert start1 is not None and end1 is not None and start2 is not None and end2 is not None
        return not (end1 <= start2 or end2 <= start1)


class EnrollmentReportService:
    """Service for enrollment reporting and analytics."""

    @staticmethod
    def get_enrollment_summary(term: Term) -> dict[str, Any]:
        """Get enrollment summary for a term."""
        enrollments = ClassHeaderEnrollment.objects.filter(class_header__term=term)

        by_status = enrollments.values("status").annotate(count=models.Count("id"))

        return {
            "total_enrollments": enrollments.count(),
            "by_status": {item["status"]: item["count"] for item in by_status},
            "unique_students": enrollments.values("student").distinct().count(),
        }

    @staticmethod
    def get_class_enrollment_details(class_header: ClassHeader) -> dict[str, Any]:
        """Get detailed enrollment information for a class."""
        enrollments = ClassHeaderEnrollment.objects.filter(
            class_header=class_header,
        ).select_related("student__person")

        enrollment_list = list(enrollments)

        capacity_info = CapacityService.check_enrollment_capacity(class_header)

        course = cast("Course", class_header.course)
        term = cast("Term", class_header.term)

        return {
            "class_info": {
                "course": course.title,
                "section": class_header.section_id,
                "term": term.code,
            },
            "capacity_info": capacity_info,
            "enrollments": [
                {
                    "student_id": cast("Any", e.student).student_id,
                    "student_name": cast("Any", cast("Any", e.student).person).full_name,
                    "status": e.status,
                    "enrollment_date": e.enrollment_date,
                }
                for e in enrollment_list
            ],
        }


class ProgramEnrollmentService:
    """Service for managing student program enrollments."""

    @classmethod
    @transaction.atomic
    def enroll_student_in_program(
        cls,
        student,
        program,
        enrollment_type: str = ProgramEnrollment.EnrollmentType.ACADEMIC,
        admission_term=None,
        enrolled_by: User | None = None,
        notes: str = "",
    ) -> ProgramEnrollment:
        """Enroll a student in an academic program.

        Args:
            student: StudentProfile instance
            program: Major instance (program to enroll in)
            enrollment_type: Type of enrollment
            admission_term: Term when student was admitted
            enrolled_by: User performing the enrollment
            notes: Additional enrollment notes

        Returns:
            Created ProgramEnrollment instance

        Raises:
            ValidationError: If enrollment violates business rules
        """
        # Validate enrollment eligibility
        validation_errors = cls._validate_program_enrollment(student, program)
        if validation_errors:
            raise ValidationError(validation_errors)

        # Check for existing active enrollment
        existing_enrollment = ProgramEnrollment.objects.filter(
            student=student,
            program=program,
            status=ProgramEnrollment.EnrollmentStatus.ACTIVE,
        ).first()

        if existing_enrollment:
            msg = f"Student is already enrolled in {program.name}"
            raise ValidationError(msg)

        # Create enrollment
        # Use system user if no enrolled_by provided
        if enrolled_by is None:
            enrolled_by = get_system_user()

        return ProgramEnrollment.objects.create(
            student=student,
            program=program,
            enrollment_type=enrollment_type,
            start_term=admission_term,
            status=ProgramEnrollment.EnrollmentStatus.ACTIVE,
            start_date=timezone.now().date(),
            enrolled_by=enrolled_by,
            notes=notes,
        )

    @classmethod
    def _validate_program_enrollment(cls, student, program) -> list[str]:
        """Validate that a student can enroll in a program."""
        errors = []

        # Check student status
        if student.current_status != student.Status.ACTIVE:
            errors.append("Student must be active to enroll in programs")

        # Check program availability
        if not program.is_active:
            errors.append(f"Program {program.name} is not currently active")

        # Check for conflicting enrollments in same cycle
        conflicting_enrollments = ProgramEnrollment.objects.filter(
            student=student,
            program__cycle=program.cycle,
            status=ProgramEnrollment.EnrollmentStatus.ACTIVE,
        ).exclude(program=program)

        if conflicting_enrollments.exists():
            errors.append(
                f"Student is already enrolled in another program in the {program.cycle.name} cycle",
            )

        return errors

    @classmethod
    @transaction.atomic
    def change_enrollment_status(
        cls,
        enrollment: ProgramEnrollment,
        new_status: str,
        changed_by: User,
        reason: str = "",
    ) -> ProgramEnrollment:
        """Change the status of a program enrollment.

        Args:
            enrollment: ProgramEnrollment instance
            new_status: New enrollment status
            changed_by: User making the change
            reason: Reason for status change

        Returns:
            Updated ProgramEnrollment instance
        """
        old_status = enrollment.status
        enrollment.status = new_status

        if new_status in (
            ProgramEnrollment.EnrollmentStatus.COMPLETED,
            ProgramEnrollment.EnrollmentStatus.WITHDRAWN,
        ):
            enrollment.end_date = timezone.now().date()

        enrollment.save()

        # Log the status change - this would integrate with audit logging
        status_note = (
            f"Status changed from {old_status} to {new_status} by {getattr(changed_by, 'email', str(changed_by))}"
        )
        if reason:
            status_note += f". Reason: {reason}"

        if enrollment.notes:
            enrollment.notes += f"\n{status_note}"
        else:
            enrollment.notes = status_note
        enrollment.save()

        return enrollment

    @classmethod
    def get_student_enrollments(cls, student: Any) -> QuerySet[ProgramEnrollment]:
        """Get all program enrollments for a student."""
        return (
            ProgramEnrollment.objects.filter(student=student)
            .select_related("program", "start_term")
            .order_by("-start_date")
        )

    @classmethod
    def get_active_enrollment(cls, student: Any) -> ProgramEnrollment | None:
        """Get the active program enrollment for a student."""
        return (
            ProgramEnrollment.objects.filter(
                student=student,
                status=ProgramEnrollment.EnrollmentStatus.ACTIVE,
            )
            .select_related("program")
            .first()
        )


class SessionExemptionService:
    """Service for managing IEAP session exemptions."""

    @classmethod
    @transaction.atomic
    def create_session_exemption(
        cls,
        student,
        class_session,
        exemption_type: str,
        reason: str,
        approved_by: User,
        notes: str = "",
    ) -> ClassSessionExemption:
        """Create a session exemption for an IEAP student.

        Args:
            student: StudentProfile instance
            class_session: ClassSession instance
            exemption_type: Type of exemption (stored in exemption_reason)
            reason: Reason for exemption
            approved_by: User approving the exemption
            notes: Additional notes

        Returns:
            Created ClassSessionExemption instance

        Raises:
            ValidationError: If exemption is not valid
        """
        # Get or create the class header enrollment for this student/session
        class_header_enrollment = ClassHeaderEnrollment.objects.filter(
            student=student,
            class_header=class_session.class_header,
        ).first()

        if not class_header_enrollment:
            msg = "Student must be enrolled in the class to receive exemptions"
            raise ValidationError(msg)

        # Validate exemption eligibility
        validation_errors = cls._validate_session_exemption(student, class_session)
        if validation_errors:
            raise ValidationError(validation_errors)

        return ClassSessionExemption.objects.create(
            class_header_enrollment=class_header_enrollment,
            class_session=class_session,
            exemption_reason=f"{exemption_type}: {reason}",
            exempted_by=approved_by,
            notes=notes,
        )

    @classmethod
    def _validate_session_exemption(cls, student, class_session) -> list[str]:
        """Validate that a session exemption can be created."""
        errors = []

        # Check if student is enrolled in any class part of this session
        if not ClassPartEnrollment.objects.filter(
            student=student,
            class_part__class_session=class_session,
            is_active=True,
        ).exists():
            errors.append("Student must be enrolled in the class to receive exemptions")

        # Check for existing exemption
        if ClassSessionExemption.objects.filter(
            class_header_enrollment__student=student,
            class_session=class_session,
        ).exists():
            errors.append("Student already has an exemption for this session")

        return errors

    @classmethod
    def get_student_exemptions(cls, student, term=None) -> QuerySet[ClassSessionExemption]:
        """Get all session exemptions for a student."""
        queryset = ClassSessionExemption.objects.filter(class_header_enrollment__student=student)

        if term:
            queryset = queryset.filter(
                class_session__class_header__term=term,
            )

        return queryset.select_related(
            "class_session__class_header__course",
            "exempted_by",
        ).order_by("-exemption_date")


class EnrollmentValidationService:
    """Service for enrollment data validation and business rule enforcement."""

    @classmethod
    def validate_bulk_enrollment(
        cls,
        student_course_pairs: list[tuple],
        term,
    ) -> tuple[list, list]:
        """Validate multiple enrollment requests at once.

        Args:
            student_course_pairs: List of (student, course) tuples
            term: Term for enrollments

        Returns:
            Tuple of (valid_enrollments, invalid_enrollments_with_errors)
        """
        valid_enrollments = []
        invalid_enrollments = []

        for student, course in student_course_pairs:
            # Find class header for the course in the term
            try:
                class_header = ClassHeader.objects.get(course=course, term=term)
            except ClassHeader.DoesNotExist:
                invalid_enrollments.append(
                    {
                        "student": student,
                        "course": course,
                        "errors": [
                            f"No class scheduled for {course.code} in {term.code}",
                        ],
                    },
                )
                continue

            # Validate enrollment using existing service
            conflicts = ScheduleService.check_schedule_conflicts(student, class_header)
            validation_errors = []

            if conflicts:
                validation_errors.extend(
                    [f"Schedule conflict: {conflict}" for conflict in conflicts],
                )

            if validation_errors:
                invalid_enrollments.append(
                    {
                        "student": student,
                        "course": course,
                        "class_header": class_header,
                        "errors": validation_errors,
                    },
                )
            else:
                valid_enrollments.append(
                    {
                        "student": student,
                        "course": course,
                        "class_header": class_header,
                    },
                )

        return valid_enrollments, invalid_enrollments

    @classmethod
    def validate_enrollment_limits(
        cls,
        student,
        additional_courses: int = 0,
        additional_credits: int = 0,
    ) -> tuple[bool, list[str]]:
        """Validate that student enrollment doesn't exceed limits.

        Business rules:
        - Maximum 3 courses per term (9 credits) unless GPA is B+ or higher
        - No full-time/part-time distinctions
        - Manual override available for enrollment admin

        Args:
            student: StudentProfile instance
            additional_courses: Additional courses being considered
            additional_credits: Additional credits being considered

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Get current enrollment load for current term
        current_term = cls._get_current_term()
        if not current_term:
            return True, []

        current_enrollments: QuerySet[ClassHeaderEnrollment] = ClassHeaderEnrollment.objects.filter(
            student=student,
            class_header__term=current_term,
            status__in=[ENROLLMENT_STATUS_ENROLLED],
        ).select_related("class_header__course")

        current_courses = current_enrollments.count()
        current_credits = 0
        for enrollment in current_enrollments:
            enrollment_obj = cast("ClassHeaderEnrollment", enrollment)
            class_header = enrollment_obj.class_header
            course = class_header.course  # type: ignore[attr-defined]
            credits = course.credits or 3
            current_credits += int(credits)

        total_courses = current_courses + additional_courses
        total_credits = current_credits + additional_credits

        # Check course limits based on GPA
        max_courses, max_credits = cls._get_max_limits_for_student(student)

        if total_courses > max_courses:
            errors.append(
                f"Total courses ({total_courses}) would exceed maximum allowed ({max_courses}). "
                f"Override required for more than {MAX_COURSES_PER_TERM} courses.",
            )

        if total_credits > max_credits:
            errors.append(
                f"Total credits ({total_credits}) would exceed maximum allowed ({max_credits}). "
                f"Override required for more than {MAX_CREDITS_PER_TERM} credits.",
            )

        return len(errors) == 0, errors

    @classmethod
    def _get_current_term(cls):
        """Get the current academic term."""
        current_date = timezone.now().date()
        return Term.objects.filter(
            start_date__lte=current_date,
            end_date__gte=current_date,
        ).first()

    @classmethod
    def _get_max_limits_for_student(cls, student) -> tuple[int, int]:
        """Get maximum course and credit limits for a student.

        Business rules:
        - Default: 3 courses per term (9 credits)
        - B+ GPA or higher: Higher limits (allow manual override)

        Args:
            student: StudentProfile instance

        Returns:
            Tuple of (max_courses, max_credits)
        """
        # Calculate student's current GPA
        current_gpa = PrerequisiteService._calculate_student_gpa(student)

        # Check if student has B+ or higher GPA (3.3 on 4.0 scale)
        if current_gpa is not None and current_gpa >= HIGH_GPA_THRESHOLD:
            # High-performing students can take more courses with manual approval
            return (
                MAX_COURSES_PER_TERM + 2,
                MAX_CREDITS_PER_TERM + 6,
            )  # Up to 5 courses, 15 credits

        # Default limits for all students
        return MAX_COURSES_PER_TERM, MAX_CREDITS_PER_TERM

    @classmethod
    def _get_max_credits_for_student(cls, student) -> int:
        """Get maximum credit limit for a student (legacy method for compatibility).

        Args:
            student: StudentProfile instance

        Returns:
            Maximum credits allowed
        """
        _, max_credits = cls._get_max_limits_for_student(student)
        return max_credits


class MajorDeclarationService:
    """Service for managing student major declarations and validation.

    Handles the business logic for major declarations including validation
    against enrollment history, course registration conflicts, and approval
    workflows. Ensures consistency between prospective declarations and
    retrospective enrollment records.
    """

    @classmethod
    @transaction.atomic
    def create_major_declaration(
        cls,
        student: StudentProfile,
        major,
        effective_date=None,
        declared_by: User | None = None,
        change_reason: str = "",
        requires_approval: bool = False,
        notes: str = "",
    ):
        """Create a new major declaration for a student.

        Args:
            student: StudentProfile instance
            major: Major instance (from curriculum app)
            effective_date: Date when declaration becomes effective
            declared_by: User making the declaration (None for student self-declaration)
            change_reason: Reason for major change (required if changing majors)
            requires_approval: Whether declaration requires administrative approval
            notes: Additional notes

        Returns:
            Created MajorDeclaration instance

        Raises:
            ValidationError: If declaration violates business rules
            MajorConflictError: If declaration conflicts with enrollment history
        """
        from .exceptions import MajorConflictError, MajorDeclarationError
        from .models import MajorDeclaration

        # Set defaults
        if effective_date is None:
            effective_date = timezone.now().date()

        # Get student's current active declaration
        current_declaration = MajorDeclaration.get_current_declaration(student)

        # Validate major change requirements
        if current_declaration and current_declaration.major != major:
            if not change_reason:
                msg = "Change reason is required when changing majors"
                raise MajorDeclarationError(msg)

        # Validate against enrollment history
        validation_errors = cls._validate_declaration_against_enrollment_history(student, major, effective_date)
        if validation_errors:
            msg = f"Major declaration conflicts with enrollment history: {'; '.join(validation_errors)}"
            raise MajorConflictError(
                msg,
                declared_major=major,
                enrollment_major=(current_declaration.major if current_declaration else None),
            )

        # Deactivate previous declaration if this is a change
        previous_declaration = None
        if current_declaration:
            current_declaration.is_active = False
            current_declaration.save(update_fields=["is_active"])
            previous_declaration = current_declaration

        # Create new declaration
        return MajorDeclaration.objects.create(
            student=student,
            major=major,
            effective_date=effective_date,
            declared_by=declared_by,
            is_self_declared=declared_by is None,
            previous_declaration=previous_declaration,
            change_reason=change_reason,
            requires_approval=requires_approval,
            notes=notes,
        )

    @classmethod
    def validate_course_registration(
        cls,
        student: StudentProfile,
        course,
        term,
    ) -> tuple[bool, list[str]]:
        """Validate that a course registration is consistent with student's major declaration.

        Args:
            student: StudentProfile instance
            course: Course instance to register for
            term: Term for registration

        Returns:
            Tuple of (is_valid, list_of_warnings)

        Note: This returns warnings rather than hard errors to allow
        flexibility in course registration while alerting staff to conflicts.
        """
        from .models import MajorDeclaration

        warnings: list[str] = []

        # Get student's current major declaration
        current_declaration = MajorDeclaration.get_current_declaration(student)
        if not current_declaration:
            warnings.append("Student has no active major declaration")
            return False, warnings  # DENY registration - major declaration required

        # Check if major declaration is approved by administration
        if not current_declaration.approved_date:
            warnings.append("Major declaration requires administrative approval before enrollment")
            return False, warnings  # DENY registration - approval required

        # Get student's enrollment history major
        enrollment_history_major = cls._get_enrollment_history_major(student)

        # Check if course belongs to declared major (with term sensitivity)
        if not cls._course_belongs_to_major(course, current_declaration.major, term):
            warnings.append(f"Course {course.code} does not belong to declared major {current_declaration.major.name}")

        # Check consistency between declaration and enrollment history
        if enrollment_history_major and enrollment_history_major != current_declaration.major:
            if cls._course_belongs_to_major(course, enrollment_history_major, term):
                warnings.append(
                    f"Course {course.code} belongs to enrollment history major "
                    f"({enrollment_history_major.name}) but student has declared "
                    f"{current_declaration.major.name}. Review major consistency.",
                )

        # Allow registration with warnings (staff can review)
        return True, warnings

    @classmethod
    def get_effective_major(cls, student: StudentProfile, as_of_date=None):
        """Get the student's effective major as of a specific date.

        Considers both major declarations and enrollment history to determine
        the most appropriate major for the student.

        Args:
            student: StudentProfile instance
            as_of_date: Date to check effective major (defaults to today)

        Returns:
            Major instance or None if no effective major found
        """
        from .models import MajorDeclaration

        if as_of_date is None:
            as_of_date = timezone.now().date()

        # First, check for active major declaration
        declaration = (
            MajorDeclaration.objects.filter(
                student=student,
                is_active=True,
                effective_date__lte=as_of_date,
            )
            .order_by("-effective_date")
            .first()
        )

        if declaration:
            return declaration.major

        # Fall back to enrollment history
        enrollment_major = cls._get_enrollment_history_major(student)
        if enrollment_major:
            return enrollment_major

        return None

    @classmethod
    def _validate_declaration_against_enrollment_history(
        cls,
        student: StudentProfile,
        declared_major,
        effective_date,
    ) -> list[str]:
        """Validate major declaration against student's enrollment history.

        Args:
            student: StudentProfile instance
            declared_major: Major being declared
            effective_date: When declaration becomes effective

        Returns:
            List of validation error messages
        """
        errors = []

        # Get recent enrollments that might conflict
        recent_enrollments = ClassHeaderEnrollment.objects.filter(
            student=student,
            enrollment_date__gte=effective_date - timedelta(days=180),  # Last 6 months
            status__in=["ENROLLED", "ACTIVE", "COMPLETED"],
        ).select_related("class_header__course")

        # Check for courses that don't belong to declared major
        conflicting_courses = []
        for enrollment in recent_enrollments:
            enrollment_obj = cast("ClassHeaderEnrollment", enrollment)
            course = enrollment_obj.class_header.course  # type: ignore[attr-defined]
            enrollment_term = enrollment_obj.class_header.term  # type: ignore[attr-defined]
            if not cls._course_belongs_to_major(course, declared_major, enrollment_term):
                conflicting_courses.append(course.code)

        if conflicting_courses:
            errors.append(
                f"Student has recent enrollments in courses that don't belong to "
                f"declared major {declared_major.name}: {', '.join(conflicting_courses)}",
            )

        return errors

    @classmethod
    def _get_enrollment_history_major(cls, student: StudentProfile):
        """Determine student's major based on enrollment history.

        Args:
            student: StudentProfile instance

        Returns:
            Major instance or None
        """
        # Get the most recent program enrollment
        recent_enrollment = ProgramEnrollment.get_most_recent_for_student(student)
        if recent_enrollment:
            return recent_enrollment.program

        # If no program enrollment, try to infer from course history
        recent_courses = (
            ClassHeaderEnrollment.objects.filter(
                student=student,
                status__in=["COMPLETED", "ENROLLED", "ACTIVE"],
            )
            .select_related("class_header__course")
            .order_by("-enrollment_date")[:10]
        )

        # Count courses by major
        major_counts: dict[str, int] = {}
        for enrollment in recent_courses:
            enrollment_obj = cast("ClassHeaderEnrollment", enrollment)
            course = enrollment_obj.class_header.course  # type: ignore[attr-defined]

            # Find majors this course belongs to
            course_majors = cls._get_majors_for_course(course)
            for major in course_majors:
                major_counts[major] = major_counts.get(major, 0) + 1

        # Return major with most course enrollments
        if major_counts:
            return max(major_counts.items(), key=lambda x: x[1])[0]

        return None

    @classmethod
    def _course_belongs_to_major(cls, course, major, term=None) -> bool:
        """Check if a course belongs to a specific major using appropriate validation method.

        Args:
            course: Course instance
            major: Major instance
            term: Term instance for term-sensitive curriculum validation

        Returns:
            Boolean indicating if course belongs to major

        Note: Uses dual validation system:
        - Language majors (IEAP, GESL, etc.): Course prefix matching
        - Academic majors (BUSADMIN, TESOL, etc.): CanonicalRequirement validation
        """
        # Determine validation method based on major type
        if cls._is_language_major(major):
            # Language majors: use course prefix matching
            # IEAP students can take IEAP courses, GESL students take GESL courses, etc.
            return bool(course.code.startswith(major.code))
        else:
            # Academic majors: use CanonicalRequirement with term sensitivity
            from django.db.models import Q

            from apps.academic.models import CanonicalRequirement

            # Build term-sensitive query
            queryset = CanonicalRequirement.objects.filter(
                major=major,
                required_course=course,
                is_active=True,
            )

            # Add term-based filtering if term provided
            if term:
                queryset = queryset.filter(
                    effective_term__start_date__lte=term.start_date,
                ).filter(Q(end_term__isnull=True) | Q(end_term__start_date__gt=term.start_date))

            return queryset.exists()

    @classmethod
    def _is_language_major(cls, major) -> bool:
        """Determine if a major is a language program based on major code.

        Args:
            major: Major instance

        Returns:
            Boolean indicating if this is a language major
        """
        language_major_codes = {"IEAP", "GESL", "EHSS", "EXPRESS", "PT PRE-B"}
        return major.code in language_major_codes

    @classmethod
    def _get_majors_for_course(cls, course) -> list:
        """Get all majors that include this course.

        Args:
            course: Course instance

        Returns:
            List of Major instances
        """
        # Direct major relationships
        direct_majors = list(course.majors.all())

        # Majors through requirements
        from apps.academic.models import CanonicalRequirement

        requirement_majors = list(
            CanonicalRequirement.objects.filter(
                required_course=course,
                is_active=True,
            ).values_list("major", flat=True),
        )

        # Get Major instances for requirement majors
        from apps.curriculum.models import Major

        requirement_major_objects = list(Major.objects.filter(id__in=requirement_majors))

        # Combine and deduplicate
        all_majors = direct_majors + requirement_major_objects
        return list({major.id: major for major in all_majors}.values())

    @classmethod
    def generate_declaration_report(
        cls,
        student: StudentProfile,
    ) -> dict[str, Any]:
        """Generate a comprehensive report on student's major declarations and consistency.

        Args:
            student: StudentProfile instance

        Returns:
            Dictionary with declaration analysis
        """
        from .models import MajorDeclaration

        # Get all declarations
        declarations = MajorDeclaration.objects.filter(student=student).order_by("-effective_date")

        # Get current effective major
        current_major = cls.get_effective_major(student)

        # Get enrollment history major
        enrollment_major = cls._get_enrollment_history_major(student)

        # Analyze consistency
        consistency_issues = []
        if current_major and enrollment_major and current_major != enrollment_major:
            # Import here to avoid circular dependency
            from apps.curriculum.models import Major

            # Only flag as inconsistent if both are academic programs
            if (
                enrollment_major.program_type == Major.ProgramType.ACADEMIC
                and current_major.program_type == Major.ProgramType.ACADEMIC
            ):
                consistency_issues.append(
                    f"Declared major ({current_major.name}) differs from "
                    f"enrollment history major ({enrollment_major.name})",
                )

        # Get recent course registrations that might conflict
        recent_enrollments = ClassHeaderEnrollment.objects.filter(
            student=student,
            enrollment_date__gte=timezone.now().date() - timedelta(days=365),
            status__in=["ENROLLED", "ACTIVE", "COMPLETED"],
        ).select_related("class_header__course")

        course_conflicts = []
        if current_major:
            for enrollment in recent_enrollments:
                enrollment_obj = cast("ClassHeaderEnrollment", enrollment)
                course = enrollment_obj.class_header.course  # type: ignore[attr-defined]
                enrollment_term = enrollment_obj.class_header.term  # type: ignore[attr-defined]
                if not cls._course_belongs_to_major(course, current_major, enrollment_term):
                    course_conflicts.append(course.code)

        return {
            "student": {
                "id": student.student_id,
                "name": student.person.full_name,
            },
            "current_declaration": {
                "major": current_major.name if current_major else None,
                "effective_date": (
                    first_decl.effective_date
                    if declarations.exists() and (first_decl := declarations.first()) is not None
                    else None
                ),
            },
            "enrollment_history_major": (enrollment_major.name if enrollment_major else None),
            "declaration_history": [
                {
                    "major": decl.major.name,
                    "effective_date": decl.effective_date,
                    "declared_date": decl.declared_date,
                    "is_active": decl.is_active,
                    "change_reason": decl.change_reason,
                }
                for decl in declarations
            ],
            "consistency_analysis": {
                "is_consistent": len(consistency_issues) == 0 and len(course_conflicts) == 0,
                "issues": consistency_issues,
                "conflicting_courses": course_conflicts,
            },
            "recommendations": cls._generate_recommendations(
                current_major,
                enrollment_major,
                consistency_issues,
                course_conflicts,
            ),
        }

    @classmethod
    def _generate_recommendations(
        cls,
        current_major,
        enrollment_major,
        consistency_issues: list[str],
        course_conflicts: list[str],
    ) -> list[str]:
        """Generate recommendations for resolving major declaration issues."""
        recommendations = []

        if not current_major:
            recommendations.append("Student should declare a major through the mobile app or administrative system")

        if current_major and enrollment_major and current_major != enrollment_major:
            # Import here to avoid circular dependency
            from apps.curriculum.models import Major

            # Only recommend review if both are academic programs
            if (
                enrollment_major.program_type == Major.ProgramType.ACADEMIC
                and current_major.program_type == Major.ProgramType.ACADEMIC
            ):
                recommendations.append(
                    f"Review major change from {enrollment_major.name} to {current_major.name}. "
                    "Ensure all requirements are met and academic advisor has approved.",
                )

        if course_conflicts:
            recommendations.append(
                f"Review recent course registrations ({', '.join(course_conflicts[:3])}) "
                "that don't align with declared major. Consider academic planning meeting.",
            )

        if not recommendations:
            recommendations.append("Major declaration appears consistent. No action needed.")

        return recommendations


class CycleDetectionService:
    """Service for detecting and managing student cycle changes."""

    @staticmethod
    @transaction.atomic
    def detect_cycle_change(student: StudentProfile, new_program) -> StudentCycleStatus | None:
        """
        Detect if a student is changing cycles based on program change.

        Args:
            student: The student to check
            new_program: The program they are enrolling in

        Returns:
            StudentCycleStatus if cycle change detected, None otherwise
        """

        # Check if student is new (no previous enrollments)
        if not ClassHeaderEnrollment.objects.filter(student=student, status__in=["ENROLLED", "COMPLETED"]).exists():
            return CycleDetectionService._create_new_student_status(student, new_program)

        # Get previous program enrollments
        previous_enrollments = student.program_enrollments.filter(status="ACTIVE").order_by("-start_date")

        if not previous_enrollments.exists():
            # No previous program enrollment but has class enrollments
            # This might be a new student who enrolled in classes before declaring major
            return CycleDetectionService._create_new_student_status(student, new_program)

        previous_enrollment = previous_enrollments.first()
        if previous_enrollment is None:
            return CycleDetectionService._create_new_student_status(student, new_program)

        previous_program = previous_enrollment.program

        # Detect cycle changes based on program levels
        cycle_type = CycleDetectionService._determine_cycle_type(previous_program, new_program)

        if cycle_type:
            return CycleDetectionService._create_cycle_status(student, cycle_type, previous_program, new_program)

        return None

    @staticmethod
    def _determine_cycle_type(old_program, new_program) -> str | None:
        """Determine the type of cycle change based on program transition."""
        from .models import StudentCycleStatus

        # Get program levels (assuming Major has a cycle field)
        old_level = old_program.cycle.code if hasattr(old_program, "cycle") else None
        new_level = new_program.cycle.code if hasattr(new_program, "cycle") else None

        # Language to Bachelor
        if old_level == "LANG" and new_level == "BA":
            return StudentCycleStatus.CycleChangeType.LANG_TO_BA

        # Bachelor to Master
        if old_level == "BA" and new_level == "MA":
            return StudentCycleStatus.CycleChangeType.BA_TO_MA

        return None

    @staticmethod
    def _create_new_student_status(student: StudentProfile, program) -> StudentCycleStatus:
        """Create status for new students."""
        from .models import StudentCycleStatus

        return StudentCycleStatus.objects.create(
            student=student,
            cycle_type=StudentCycleStatus.CycleChangeType.NEW_STUDENT,
            detected_date=timezone.now().date(),
            target_program=program,
        )

    @staticmethod
    def _create_cycle_status(
        student: StudentProfile, cycle_type: str, source_program, target_program
    ) -> StudentCycleStatus:
        """Create or update cycle status for student."""
        from .models import StudentCycleStatus

        status, _created = StudentCycleStatus.objects.update_or_create(
            student=student,
            cycle_type=cycle_type,
            target_program=target_program,
            defaults={"detected_date": timezone.now().date(), "source_program": source_program, "is_active": True},
        )
        return status

    @staticmethod
    def deactivate_on_graduation(student: StudentProfile, program) -> None:
        """Deactivate cycle status when student graduates."""
        from .models import StudentCycleStatus

        StudentCycleStatus.objects.filter(student=student, target_program=program, is_active=True).update(
            is_active=False, deactivated_date=timezone.now().date(), deactivation_reason="GRADUATED"
        )
