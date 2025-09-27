"""Degree audit services optimized for mobile app integration.

This module provides services for generating comprehensive degree audits
and progress reports suitable for consumption by the student mobile app.
"""

from dataclasses import asdict
from typing import Any

from django.db import transaction

from apps.academic.constants import AcademicConstants
from apps.academic.models import StudentDegreeProgress, StudentRequirementException
from apps.academic.services.canonical import (
    CanonicalRequirementService,
    DegreeAuditSummary,
)
from apps.academic.services.exceptions import StudentRequirementExceptionService
from apps.common.models import StudentActivityLog


class DegreeAuditService:
    """Service for generating degree audits and progress reports."""

    @classmethod
    def generate_mobile_audit(cls, student: Any, major: Any | None = None) -> dict[str, Any]:
        """Generate a comprehensive degree audit optimized for mobile app.

        Args:
            student: StudentProfile instance
            major: Optional major (defaults to student's primary major)

        Returns:
            Dictionary with degree audit data suitable for JSON serialization
        """
        # Get major if not provided
        if major is None:
            # Assuming student has a primary_major field
            major = getattr(student, "primary_major", None)
            if not major:
                return {
                    "error": "No major specified",
                    "student_id": student.id,
                }

        # Get or create degree progress
        progress = cls._get_or_create_progress(student, major)

        # Get detailed requirement progress
        requirement_progress = CanonicalRequirementService.get_student_progress(student, major)

        # Separate completed and remaining requirements
        completed_requirements = []
        remaining_requirements = []

        for prog in requirement_progress:
            requirement_data = {
                "sequence_number": prog.requirement.sequence_number,
                "course_code": prog.requirement.required_course.code,
                "course_name": prog.requirement.required_course.title,
                "credits": float(prog.requirement.canonical_credits),
                "requirement_name": prog.requirement.name,
                "is_completed": prog.is_completed,
                "completion_method": prog.completion_method,
                "status_message": prog.status_message,
            }

            if prog.is_completed:
                requirement_data["fulfillment_details"] = prog.fulfillment_details
                requirement_data["credits_earned"] = float(prog.credits_earned)
                completed_requirements.append(requirement_data)
            else:
                requirement_data["next_action"] = prog.next_action
                remaining_requirements.append(requirement_data)

        # Get exceptions
        exceptions = StudentRequirementExceptionService.get_student_exceptions(student, major=major)

        approved_exceptions = []
        pending_exceptions = []

        for exc in exceptions:
            exception_data = {
                "id": exc.id,
                "requirement_sequence": exc.canonical_requirement.sequence_number,
                "exception_type": exc.get_exception_type_display(),
                "reason": exc.reason,
                "credits": float(exc.exception_credits),
                "status": exc.approval_status,
                "created_date": exc.created_at.isoformat(),
            }

            if exc.approval_status == StudentRequirementException.ApprovalStatus.APPROVED:
                exception_data["approval_date"] = exc.approval_date.isoformat() if exc.approval_date else None
                approved_exceptions.append(exception_data)
            elif exc.approval_status == StudentRequirementException.ApprovalStatus.PENDING:
                pending_exceptions.append(exception_data)

        # Create audit summary
        audit_summary = DegreeAuditSummary(
            student_id=student.id,
            major_code=major.code,
            major_name=major.name,
            total_requirements=progress["total_requirements"],
            completed_requirements=progress["completed_requirements"],
            completion_percentage=progress["completion_percentage"],
            total_credits_required=progress["total_credits_required"],
            credits_completed=progress["credits_completed"],
            remaining_requirements=remaining_requirements,
            completed_requirements_list=completed_requirements,
            approved_exceptions=approved_exceptions,
            pending_exceptions=pending_exceptions,
            is_graduation_eligible=progress["is_graduation_eligible"],
            estimated_graduation_term=None,
            last_updated=None,
        )

        # Convert to dictionary for JSON serialization
        audit_dict = asdict(audit_summary)

        # Add additional mobile-specific fields
        audit_dict["summary"] = {
            "total_requirements": progress["total_requirements"],
            "completed": progress["completed_requirements"],
            "remaining": progress["remaining_requirements"],
            "percentage": progress["completion_percentage"],
            "credits_completed": float(progress["credits_completed"]),
            "credits_remaining": float(progress["remaining_credits"]),
            "status": progress["completion_status"],
            "status_display": progress["completion_status"],  # Remove method call
        }

        # Add quick stats for mobile dashboard
        audit_dict["quick_stats"] = {
            "courses_this_term": cls._get_current_term_courses(student),
            "gpa": cls._get_student_gpa(student),
            "academic_standing": cls._get_academic_standing(student),
            "next_registration": cls._get_next_registration_info(student),
        }

        return audit_dict

    @classmethod
    def _get_or_create_progress(cls, student: Any, major: Any) -> dict[str, Any]:
        """Get calculated student degree progress.

        Returns a dictionary with progress data calculated from individual fulfillments.
        This replaces the old cached StudentDegreeProgress model.
        """
        # Use the new dynamic calculation method
        progress_data = StudentDegreeProgress.get_student_progress(student, major)
        return progress_data

    @classmethod
    def _get_current_term_courses(cls, student: Any) -> int:
        """Get number of courses student is taking in current term."""
        from apps.curriculum.models import Term
        from apps.enrollment.models import ClassHeaderEnrollment

        current_term = Term.get_current_term()
        if not current_term:
            return 0

        return ClassHeaderEnrollment.objects.filter(
            student=student,
            class_header__term=current_term,
            enrollment_status__in=["ENROLLED", "WAITLISTED"],
        ).count()

    @classmethod
    def _get_student_gpa(cls, student) -> float | None:
        """Get student's current GPA."""
        # Assuming there's a GPA model or calculation
        # This is a placeholder implementation
        from apps.grading.models import StudentGPA

        try:
            gpa = StudentGPA.objects.filter(student=student, is_current=True).latest("calculated_date")
            return float(gpa.cumulative_gpa)
        except StudentGPA.DoesNotExist:
            return None

    @classmethod
    def _get_academic_standing(cls, student) -> str:
        """Get student's academic standing."""
        # Placeholder implementation
        gpa = cls._get_student_gpa(student)
        if gpa is None:
            return "Unknown"
        elif gpa >= 3.5:  # Dean's List threshold
            return "Dean's List"
        elif gpa >= float(AcademicConstants.MINIMUM_CUMULATIVE_GPA):
            return "Good Standing"
        else:
            return "Academic Probation"

    @classmethod
    def _get_next_registration_info(cls, student) -> dict | None:
        """Get information about next registration period for academic students.

        Note: This is for BA/MA academic students only. Gets the next term
        of the same type (BA -> BA, MA -> MA) for continued enrollment.
        """

        from apps.curriculum.models import Term

        # Find student's current academic term (most recent enrollment)
        current_enrollment = (
            student.class_header_enrollments.filter(
                class_header__term__term_type__in=[Term.TermType.BACHELORS, Term.TermType.MASTERS],
                class_header__term__is_active=True,
            )
            .select_related("class_header__term")
            .order_by("-class_header__term__start_date")
            .first()
        )

        if not current_enrollment:
            return None

        current_term = current_enrollment.class_header.term

        # Find next term of same type (BA -> BA, MA -> MA)
        next_term = Term.suggest_target_term(current_term)
        if not next_term:
            return None

        return {
            "term": next_term.code,
            "registration_opens": (
                next_term.registration_start.isoformat() if hasattr(next_term, "registration_start") else None
            ),
            "registration_closes": (
                next_term.registration_end.isoformat() if hasattr(next_term, "registration_end") else None
            ),
        }

    @classmethod
    @transaction.atomic
    def refresh_degree_audit(cls, student, major=None):
        """Force refresh of degree audit data.

        Args:
            student: StudentProfile instance
            major: Optional major (defaults to student's primary major)

        Returns:
            Updated degree audit dictionary
        """
        # Get major if not provided
        if major is None:
            major = getattr(student, "primary_major", None)
            if not major:
                raise ValueError("No major specified")

        # Update degree progress
        progress = CanonicalRequirementService.update_degree_progress(student, major)

        # Log the refresh
        StudentActivityLog.objects.create(
            student=student,
            activity_type="DEGREE_AUDIT_REFRESH",
            description=f"Degree audit refreshed for {major.name}",
            related_object=progress,
        )

        # Generate and return updated audit
        return cls.generate_mobile_audit(student, major)

    @classmethod
    def get_graduation_checklist(cls, student, major=None) -> dict:
        """Generate a graduation checklist for the student.

        Args:
            student: StudentProfile instance
            major: Optional major (defaults to student's primary major)

        Returns:
            Dictionary with graduation requirements checklist
        """
        # Get major if not provided
        if major is None:
            major = getattr(student, "primary_major", None)
            if not major:
                return {"error": "No major specified"}

        # Get degree progress
        progress = cls._get_or_create_progress(student, major)

        checklist = {
            "student_id": student.id,
            "major": major.name,
            "requirements": {
                "degree_requirements": {
                    "status": ("complete" if progress["completion_percentage"] == 100 else "incomplete"),
                    "completed": progress["completed_requirements"],
                    "total": progress["total_requirements"],
                    "percentage": progress["completion_percentage"],
                },
                "credit_requirements": {
                    "status": (
                        "complete"
                        if progress["credits_completed"] >= progress["total_credits_required"]
                        else "incomplete"
                    ),
                    "completed": float(progress["credits_completed"]),
                    "required": float(progress["total_credits_required"]),
                    "remaining": float(progress["remaining_credits"]),
                },
                "gpa_requirement": {
                    "status": "unknown",  # Placeholder
                    "current_gpa": cls._get_student_gpa(student),
                    "required_gpa": float(AcademicConstants.MINIMUM_CUMULATIVE_GPA),
                },
                "residency_requirement": {
                    "status": "unknown",  # Placeholder
                    "description": "Complete at least 50% of credits at PUCSR",
                },
                "senior_project": {
                    "status": "unknown",  # Placeholder
                    "description": "Complete senior project/thesis",
                },
            },
            "can_graduate": progress["is_graduation_eligible"],
            "next_steps": cls._get_graduation_next_steps(student, progress),
        }

        return checklist

    @classmethod
    def _get_graduation_next_steps(cls, student, progress: dict) -> list[str]:
        """Get next steps for graduation."""
        steps = []

        if progress["remaining_requirements"] > 0:
            steps.append(f"Complete {progress['remaining_requirements']} remaining course requirements")

        if progress["remaining_credits"] > 0:
            steps.append(f"Earn {progress['remaining_credits']} more credits")

        if not progress["is_graduation_eligible"]:
            steps.append("Meet with academic advisor to review graduation requirements")

        if progress["completion_percentage"] >= 90:
            steps.append("Apply for graduation through the registrar's office")

        return steps
