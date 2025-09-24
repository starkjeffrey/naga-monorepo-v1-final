"""Services for managing canonical requirement fulfillments.

This module provides business logic for tracking how students fulfill
degree requirements through various means.
"""

from django.db import transaction
from django.utils import timezone

from apps.academic.models import (
    CanonicalRequirement,
    StudentDegreeProgress,
    StudentRequirementException,
    TransferCredit,
)
from apps.common.models import StudentActivityLog
from apps.enrollment.models import ClassHeaderEnrollment


class CanonicalFulfillmentService:
    """Service for managing canonical requirement fulfillments."""

    @classmethod
    @transaction.atomic
    def create_course_fulfillment(
        cls,
        student,
        enrollment: ClassHeaderEnrollment,
        grade: str,
        canonical_requirement: CanonicalRequirement,
    ) -> StudentDegreeProgress:
        """Create a fulfillment record for a course completion.

        Args:
            student: StudentProfile instance
            enrollment: ClassHeaderEnrollment that fulfilled the requirement
            grade: Final grade earned
            canonical_requirement: The requirement being fulfilled

        Returns:
            Created StudentDegreeProgress instance
        """
        # Check if fulfillment already exists
        existing = StudentDegreeProgress.objects.filter(
            student=student,
            canonical_requirement=canonical_requirement,
        ).first()

        if existing:
            # Update existing if needed
            if not existing.is_active:
                existing.is_active = True
                existing.fulfillment_method = StudentDegreeProgress.FulfillmentMethod.COURSE_COMPLETION
                existing.fulfilling_enrollment = enrollment
                existing.grade = grade
                existing.credits_earned = enrollment.class_header.course.credits
                existing.fulfillment_date = enrollment.class_header.term.end_date or timezone.now().date()
                existing.save()
                return existing
            return existing

        # Create new fulfillment
        fulfillment = StudentDegreeProgress.objects.create(
            student=student,
            canonical_requirement=canonical_requirement,
            fulfillment_method=StudentDegreeProgress.FulfillmentMethod.COURSE_COMPLETION,
            fulfilling_enrollment=enrollment,
            credits_earned=enrollment.class_header.course.credits,
            grade=grade,
            fulfillment_date=enrollment.class_header.term.end_date or timezone.now().date(),
        )

        # Log activity
        StudentActivityLog.objects.create(
            student_number=student.student_id if hasattr(student, "student_id") else str(student.id),
            student_name=str(student),
            activity_type=StudentActivityLog.ActivityType.GRADE_ASSIGNMENT,
            description=f"Fulfilled {canonical_requirement} with grade {grade}",
            activity_details={"fulfillment_id": fulfillment.id},
            performed_by_id=1,  # System user
        )

        return fulfillment

    @classmethod
    @transaction.atomic
    def create_transfer_fulfillment(
        cls,
        student,
        transfer_credit: TransferCredit,
        canonical_requirement: CanonicalRequirement,
    ) -> StudentDegreeProgress:
        """Create a fulfillment record for a transfer credit.

        Args:
            student: StudentProfile instance
            transfer_credit: Approved TransferCredit
            canonical_requirement: The requirement being fulfilled

        Returns:
            Created StudentDegreeProgress instance
        """
        fulfillment = StudentDegreeProgress.objects.create(
            student=student,
            canonical_requirement=canonical_requirement,
            fulfillment_method=StudentDegreeProgress.FulfillmentMethod.TRANSFER_CREDIT,
            fulfilling_transfer=transfer_credit,
            credits_earned=transfer_credit.awarded_credits,
            grade=transfer_credit.external_grade or "TRANSFER",
            fulfillment_date=transfer_credit.review_date or timezone.now().date(),
        )

        # Log activity
        StudentActivityLog.objects.create(
            student_number=student.student_id if hasattr(student, "student_id") else str(student.id),
            student_name=str(student),
            activity_type=StudentActivityLog.ActivityType.GRADE_ASSIGNMENT,
            description=f"Fulfilled {canonical_requirement} with transfer credit",
            activity_details={"fulfillment_id": fulfillment.id},
            performed_by_id=1,  # System user
        )

        return fulfillment

    @classmethod
    @transaction.atomic
    def create_exception_fulfillment(
        cls,
        student,
        exception: StudentRequirementException,
    ) -> StudentDegreeProgress | None:
        """Create a fulfillment record for an approved exception.

        Args:
            student: StudentProfile instance
            exception: Approved StudentRequirementException

        Returns:
            Created StudentDegreeProgress instance or None if waived
        """
        if exception.is_waived:
            # Create waiver fulfillment
            method = StudentDegreeProgress.FulfillmentMethod.WAIVER
        else:
            # Create substitution fulfillment
            method = StudentDegreeProgress.FulfillmentMethod.EXCEPTION_SUBSTITUTION

        fulfillment = StudentDegreeProgress.objects.create(
            student=student,
            canonical_requirement=exception.canonical_requirement,
            fulfillment_method=method,
            fulfilling_exception=exception,
            credits_earned=exception.exception_credits,
            fulfillment_date=exception.approval_date or timezone.now().date(),
        )

        # Log activity
        StudentActivityLog.objects.create(
            student_number=student.student_id if hasattr(student, "student_id") else str(student.id),
            student_name=str(student),
            activity_type=StudentActivityLog.ActivityType.GRADE_ASSIGNMENT,
            description=f"Fulfilled {exception.canonical_requirement} via exception",
            activity_details={"fulfillment_id": fulfillment.id},
            performed_by_id=1,  # System user
        )

        return fulfillment

    @classmethod
    def check_course_completion_fulfillments(
        cls,
        enrollment: ClassHeaderEnrollment,
    ) -> list[StudentDegreeProgress]:
        """Check if a completed enrollment fulfills any canonical requirements.

        This method should be called when a student completes a course to
        automatically create fulfillment records. Enhanced to check both
        direct course matches and course equivalencies.

        Args:
            enrollment: Completed ClassHeaderEnrollment

        Returns:
            List of created StudentDegreeProgress instances
        """
        # Get the student's active major(s)
        from apps.enrollment.models import ProgramEnrollment

        active_programs = ProgramEnrollment.objects.filter(
            student=enrollment.student,
            status="ACTIVE",
        ).select_related("program")

        fulfillments = []

        for program in active_programs:
            # Find all requirements this course could fulfill (direct + equivalencies)
            fulfillable_requirements = cls.find_fulfillable_requirements(
                course=enrollment.class_header.course,
                major=program.program,
                term=enrollment.class_header.term,
            )

            # Get the grade from ClassSessionGrade (lazy import to avoid circular dependency)
            from apps.grading.models import ClassSessionGrade

            # Get the most recent session grade for this enrollment
            session_grade = (
                ClassSessionGrade.objects.filter(
                    enrollment=enrollment,
                )
                .order_by("-calculated_at")
                .first()
            )

            if not session_grade or session_grade.letter_grade not in [
                "A+",
                "A",
                "A-",
                "B+",
                "B",
                "B-",
                "C+",
                "C",
                "C-",
                "D+",
                "D",
                "D-",
                "P",
            ]:
                continue  # Not a passing grade

            for requirement in fulfillable_requirements:
                # Check if already fulfilled (prevent double fulfillments)
                existing = StudentDegreeProgress.objects.filter(
                    student=enrollment.student,
                    canonical_requirement=requirement,
                    is_active=True,
                ).exists()

                if not existing:
                    fulfillment = cls.create_course_fulfillment(
                        student=enrollment.student,
                        enrollment=enrollment,
                        grade=session_grade.letter_grade,
                        canonical_requirement=requirement,
                    )
                    fulfillments.append(fulfillment)

        return fulfillments

    @classmethod
    def find_fulfillable_requirements(
        cls,
        course,
        major,
        term,
    ) -> list[CanonicalRequirement]:
        """Find all canonical requirements that a course can fulfill.

        Checks both direct course matches and course equivalencies to find
        all requirements that the given course can satisfy.

        Args:
            course: Course instance
            major: Major instance
            term: Term instance (used for equivalency term validation)

        Returns:
            List of CanonicalRequirement instances that can be fulfilled
        """
        # Import here to avoid circular imports
        from apps.academic.services.transfer import CourseEquivalencyService

        fulfillable_requirements: list[CanonicalRequirement] = []

        # 1. Find direct matches (existing behavior)
        direct_requirements = CanonicalRequirement.objects.filter(
            major=major,
            required_course=course,
            is_active=True,
        ).select_related("required_course", "major")

        fulfillable_requirements.extend(direct_requirements)

        # 2. Find equivalency matches (new behavior)
        equivalencies = CourseEquivalencyService.find_equivalencies(
            course=course,
            term=term,
            bidirectional=True,
        )

        for equivalency in equivalencies:
            # For each equivalent course, find requirements it could fulfill
            equivalent_requirements = CanonicalRequirement.objects.filter(
                major=major,
                required_course=equivalency.original_course,
                is_active=True,
            ).select_related("required_course", "major")

            fulfillable_requirements.extend(equivalent_requirements)

            # If bidirectional, also check the reverse direction
            if equivalency.bidirectional:
                reverse_requirements = CanonicalRequirement.objects.filter(
                    major=major,
                    required_course=equivalency.equivalent_course,
                    is_active=True,
                ).select_related("required_course", "major")

                fulfillable_requirements.extend(reverse_requirements)

        # Remove duplicates while preserving order
        seen = set()
        unique_requirements = []
        for req in fulfillable_requirements:
            if req.id not in seen:
                seen.add(req.id)
                unique_requirements.append(req)

        return unique_requirements

    @classmethod
    def get_unfulfilled_requirements(cls, student, major) -> list[CanonicalRequirement]:
        """Get list of canonical requirements not yet fulfilled by student.

        Args:
            student: StudentProfile instance
            major: Major instance

        Returns:
            List of unfulfilled CanonicalRequirement instances
        """
        # Get all requirements for the major
        all_requirements = CanonicalRequirement.objects.filter(
            major=major,
            is_active=True,
        ).order_by("sequence_number")

        # Get fulfilled requirement IDs
        fulfilled_ids = StudentDegreeProgress.objects.filter(
            student=student,
            canonical_requirement__major=major,
            is_active=True,
        ).values_list("canonical_requirement_id", flat=True)

        # Return unfulfilled requirements
        return [req for req in all_requirements if req.id not in fulfilled_ids]

    @classmethod
    def calculate_remaining_courses(cls, student, major) -> int:
        """Calculate number of courses student still needs to complete.

        Args:
            student: StudentProfile instance
            major: Major instance

        Returns:
            Number of remaining courses
        """
        unfulfilled = cls.get_unfulfilled_requirements(student, major)
        return len(unfulfilled)
