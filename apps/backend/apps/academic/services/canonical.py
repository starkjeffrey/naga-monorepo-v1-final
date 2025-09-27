"""Canonical requirement services implementing "Canonical as default, exception as override" pattern.

This module provides simplified business logic services for the new canonical academic
requirement system. The services follow clean architecture principles and implement
the architectural decision to use Course.credits as the single source of truth.

DESIGN PRINCIPLES:
1. Single Source of Truth: Course.credits is the ONLY source for course credit values
2. Canonical First: Always check canonical requirements before exceptions
3. Exception Override: Approved exceptions override canonical requirements
4. Clean Logic: Simpler algorithms than the flexible requirement system
"""

from collections import Counter
from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.db.models import Q

from apps.academic.constants import AcademicConstants
from apps.academic.models import (
    CanonicalRequirement,
    StudentDegreeProgress,
    StudentRequirementException,
)
from apps.common.models import StudentActivityLog


@dataclass
class CanonicalProgress:
    """Data structure for canonical requirement progress with student notification details."""

    requirement: CanonicalRequirement
    is_completed: bool
    completion_method: str  # 'canonical', 'exception', 'pending'
    credits_earned: Decimal
    exception: StudentRequirementException | None = None
    notes: str = ""

    # Student notification fields
    status_message: str = ""  # Human-readable status for students
    next_action: str = ""  # What student should do next
    fulfillment_details: str = ""  # How requirement was/can be fulfilled


@dataclass
class DegreeAuditSummary:
    """Comprehensive degree audit summary for mobile app."""

    student_id: int
    major_code: str
    major_name: str
    total_requirements: int
    completed_requirements: int
    completion_percentage: int
    total_credits_required: int
    credits_completed: Decimal
    remaining_requirements: list[dict]  # Simplified for mobile
    completed_requirements_list: list[dict]  # Simplified for mobile
    approved_exceptions: list[dict]  # Simplified for mobile
    pending_exceptions: list[dict]  # Simplified for mobile
    is_graduation_eligible: bool
    estimated_graduation_term: str | None = None
    last_updated: str | None = None


class CanonicalRequirementService:
    """Service for managing canonical degree requirements."""

    @classmethod
    def get_major_requirements(cls, major, term=None) -> list[CanonicalRequirement]:
        """Get all canonical requirements for a major with optimized queries.

        Args:
            major: Major instance
            term: Optional term to check effective requirements (defaults to current)

        Returns:
            List of CanonicalRequirement instances ordered by sequence_number
        """
        # Optimize with select_related to avoid N+1 queries
        requirements = (
            CanonicalRequirement.objects.filter(
                major=major,
                is_active=True,
            )
            .select_related(
                "required_course",
                "required_course__division",
                "major",
                "effective_term",
                "end_term",
            )
            .order_by("sequence_number")
        )

        if term:
            requirements = requirements.filter(
                effective_term__start_date__lte=term.start_date,
            ).filter(Q(end_term__isnull=True) | Q(end_term__start_date__gt=term.start_date))

        return list(requirements)

    @classmethod
    def validate_requirement_sequence(cls, major) -> tuple[bool, list[str]]:
        """Validate that canonical requirements form a complete sequence.

        Args:
            major: Major instance to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        requirements = cls.get_major_requirements(major)
        if not requirements:
            errors.append(f"No canonical requirements defined for {major.full_name}")
            return False, errors

        # Check for complete sequence based on degree type
        expected_count = (
            AcademicConstants.BA_TOTAL_REQUIREMENTS
            if major.cycle.degree_awarded == "BA"
            else AcademicConstants.MA_TOTAL_REQUIREMENTS
        )
        sequence_numbers = [req.sequence_number for req in requirements]

        missing_numbers = set(range(1, expected_count + 1)) - set(sequence_numbers)
        if missing_numbers:
            errors.append(f"Missing sequence numbers: {sorted(missing_numbers)}")

        # Use Counter for efficient duplicate detection
        sequence_counts = Counter(sequence_numbers)
        duplicate_numbers = [num for num, count in sequence_counts.items() if count > 1]
        if duplicate_numbers:
            errors.append(f"Duplicate sequence numbers: {sorted(duplicate_numbers)}")

        # Check for course duplicates
        course_codes = [req.required_course.code for req in requirements]
        course_counts = Counter(course_codes)
        duplicate_courses = [code for code, count in course_counts.items() if count > 1]
        if duplicate_courses:
            errors.append(f"Duplicate courses in requirements: {sorted(duplicate_courses)}")

        return not errors, errors

    @classmethod
    def get_student_progress(cls, student, major) -> list[CanonicalProgress]:
        """Get detailed progress for each canonical requirement.
        Optimized for mobile app usage with minimal queries.

        Args:
            student: StudentProfile instance
            major: Major instance

        Returns:
            List of CanonicalProgress instances
        """
        # Get all canonical requirements for the major
        requirements = cls.get_major_requirements(major)

        # Get all fulfillments for this student and major
        fulfillments = StudentDegreeProgress.objects.filter(
            student=student,
            canonical_requirement__major=major,
            is_active=True,
        ).select_related(
            "canonical_requirement",
            "canonical_requirement__required_course",
            "fulfilling_enrollment__class_header__course",
            "fulfilling_enrollment__class_header__term",
            "fulfilling_transfer",
            "fulfilling_exception",
        )

        # Build a map of fulfilled requirements
        fulfilled_requirements = {f.canonical_requirement_id: f for f in fulfillments}

        # Get all approved exceptions for this student
        approved_exceptions = StudentRequirementException.objects.filter(
            student=student,
            canonical_requirement__major=major,
            approval_status=StudentRequirementException.ApprovalStatus.APPROVED,
        ).select_related(
            "canonical_requirement",
            "fulfilling_course",
            "fulfilling_transfer_credit",
            "fulfilling_transfer_credit__equivalent_course",
        )

        # Build exception map by requirement
        exception_map = {exc.canonical_requirement_id: exc for exc in approved_exceptions}

        # Build progress list
        progress_list = []
        for req in requirements:
            # Check for fulfillment first
            fulfillment = fulfilled_requirements.get(req.id)

            if fulfillment:
                # Requirement has been fulfilled
                progress = CanonicalProgress(
                    requirement=req,
                    is_completed=True,
                    completion_method=fulfillment.fulfillment_method,
                    credits_earned=fulfillment.credits_earned,
                    exception=fulfillment.fulfilling_exception,
                    status_message=f"Fulfilled by {fulfillment.get_fulfillment_method_display()}",
                    fulfillment_details=cls._get_fulfillment_details(fulfillment),
                )
            else:
                # Check for exception that might create a fulfillment
                exception = exception_map.get(req.id)

                if exception and exception.approval_status == StudentRequirementException.ApprovalStatus.APPROVED:
                    # Exception exists but no fulfillment record yet - this shouldn't happen
                    # but we'll handle it gracefully
                    progress = CanonicalProgress(
                        requirement=req,
                        is_completed=True,
                        completion_method="exception",
                        credits_earned=exception.exception_credits,
                        exception=exception,
                        status_message=f"Fulfilled by exception: {exception.get_exception_type_display()}",
                        fulfillment_details=cls._get_exception_details(exception),
                    )
                else:
                    # Not completed
                    progress = CanonicalProgress(
                        requirement=req,
                        is_completed=False,
                        completion_method="pending",
                        credits_earned=Decimal("0.00"),
                        status_message="Not yet completed",
                        next_action=f"Enroll in {req.required_course.code}",
                    )

            progress_list.append(progress)

        return progress_list

    @classmethod
    def _get_fulfillment_details(cls, fulfillment: StudentDegreeProgress) -> str:
        """Get human-readable details about a fulfillment."""
        if fulfillment.fulfillment_method == StudentDegreeProgress.FulfillmentMethod.COURSE_COMPLETION:
            if fulfillment.fulfilling_enrollment:
                return f"Grade: {fulfillment.grade} in {fulfillment.fulfilling_enrollment.class_header.term.code}"
            return f"Grade: {fulfillment.grade}"
        elif fulfillment.fulfillment_method == StudentDegreeProgress.FulfillmentMethod.TRANSFER_CREDIT:
            if fulfillment.fulfilling_transfer:
                return f"Transfer from {fulfillment.fulfilling_transfer.external_institution}"
            return "Transfer credit"
        elif fulfillment.fulfillment_method == StudentDegreeProgress.FulfillmentMethod.WAIVER:
            return "Requirement waived"
        elif fulfillment.fulfillment_method == StudentDegreeProgress.FulfillmentMethod.EXCEPTION_SUBSTITUTION:
            if fulfillment.fulfilling_exception and fulfillment.fulfilling_exception.fulfilling_course:
                return f"Substituted with {fulfillment.fulfilling_exception.fulfilling_course.code}"
            return "Course substitution"
        return "Fulfilled"

    @classmethod
    def _get_exception_details(cls, exception: StudentRequirementException) -> str:
        """Get human-readable details about an exception."""
        if exception.is_waived:
            return "Requirement waived"
        elif exception.fulfilling_course:
            return f"Substituted with {exception.fulfilling_course.code}"
        elif exception.fulfilling_transfer_credit:
            return f"Transfer credit from {exception.fulfilling_transfer_credit.external_institution}"
        return "Exception approved"

    @classmethod
    @transaction.atomic
    def update_degree_progress(cls, student, major) -> dict:
        """Get student degree progress summary from individual fulfillments.

        This method now uses the consolidated StudentDegreeProgress model
        to calculate progress dynamically instead of maintaining a separate summary table.

        Args:
            student: StudentProfile instance
            major: Major instance

        Returns:
            Dictionary with progress summary (replaces StudentDegreeProgress instance)
        """
        # Use the new consolidated approach
        progress_summary = StudentDegreeProgress.get_student_progress(student, major)

        # For backward compatibility, create a dict that matches the old interface
        progress_data = {
            "student": progress_summary["student"],
            "major": progress_summary["major"],
            "total_requirements": progress_summary["total_requirements"],
            "completed_requirements": progress_summary["completed_requirements"],
            "total_credits_required": progress_summary["total_credits_required"],
            "credits_completed": progress_summary["credits_completed"],
            "completion_percentage": progress_summary["completion_percentage"],
            "completion_status": progress_summary["completion_status"],
            "remaining_requirements": progress_summary["remaining_requirements"],
            "remaining_credits": progress_summary["remaining_credits"],
            "is_graduation_eligible": progress_summary["is_graduation_eligible"],
        }

        # Log activity
        StudentActivityLog.objects.create(
            student=student,
            student_name=student.person.full_name,
            activity_type=StudentActivityLog.ActivityType.PROFILE_UPDATE,
            description=f"Degree progress calculated: {progress_data['completion_percentage']}% complete",
            activity_details={
                "completion_percentage": progress_data["completion_percentage"],
                "satisfied_requirements": len(progress_data["satisfied_requirements"]),
                "unsatisfied_requirements": len(progress_data["unsatisfied_requirements"]),
            },
        )

        return progress_data
