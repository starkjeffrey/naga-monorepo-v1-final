"""Curriculum services for academic planning and validation.

This module provides business logic services for:
- Academic structure validation and management
- Course progression and prerequisite checking
- Curriculum template validation and completeness
- Academic planning and degree requirement tracking
- Transfer credit evaluation

Following clean architecture principles with separation of concerns
and comprehensive business rule enforcement.
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Any

from django.contrib.auth.models import AbstractUser
from django.db import transaction
from django.db.models import Q, Sum

from apps.common.utils import get_current_date

from .models import (
    Course,
    CoursePartTemplate,
    Cycle,
    Division,
    Major,
    SeniorProjectGroup,
    Term,
)

# Setup logging
logger = logging.getLogger(__name__)


class CurriculumError(Exception):
    """Custom exception for curriculum operations."""


class AcademicStructureService:
    """Service for managing academic structure (divisions, cycles, majors)."""

    @staticmethod
    def validate_academic_hierarchy(division_id: int, cycle_id: int, major_id: int) -> bool:
        """Validate that division → cycle → major hierarchy is correct.

        Args:
            division_id: Division ID
            cycle_id: Cycle ID
            major_id: Major ID

        Returns:
            bool: True if hierarchy is valid

        Raises:
            CurriculumError: If hierarchy is invalid
        """
        logger.info(f"Validating academic hierarchy: division={division_id}, cycle={cycle_id}, major={major_id}")

        try:
            division = Division.objects.get(id=division_id, is_active=True)
            cycle = Cycle.objects.get(id=cycle_id, division=division, is_active=True)
            Major.objects.get(id=major_id, cycle=cycle, is_active=True)

            logger.info(f"Academic hierarchy validation successful for major {major_id}")
            return True
        except Division.DoesNotExist as e:
            logger.error(f"Division {division_id} not found or inactive")
            msg = f"Division {division_id} not found or inactive"
            raise CurriculumError(msg) from e
        except Cycle.DoesNotExist as e:
            logger.error(f"Cycle {cycle_id} not found, inactive, or not in division {division_id}")
            msg = f"Cycle {cycle_id} not found, inactive, or not in division {division_id}"
            raise CurriculumError(msg) from e
        except Major.DoesNotExist as e:
            logger.error(f"Major {major_id} not found, inactive, or not in cycle {cycle_id}")
            msg = f"Major {major_id} not found, inactive, or not in cycle {cycle_id}"
            raise CurriculumError(msg) from e
        except Exception as e:
            logger.error(f"Unexpected error validating academic hierarchy: {e}")
            msg = "Unexpected error validating academic hierarchy"
            raise CurriculumError(msg) from e

    @staticmethod
    def get_division_structure(division_id: int) -> dict[str, Any]:
        """Get complete structure for a division including cycles and majors.

        Args:
            division_id: Division ID

        Returns:
            Dictionary with complete division structure
        """
        try:
            division = Division.objects.prefetch_related("cycles__majors").get(id=division_id, is_active=True)
        except Division.DoesNotExist as e:
            msg = f"Division {division_id} not found or inactive"
            raise CurriculumError(msg) from e

        structure: dict[str, Any] = {
            "division": {
                "id": division.id,
                "name": division.name,
                "short_name": division.short_name,
                "description": division.description,
            },
            "cycles": [],
        }

        for cycle in division.cycles.filter(is_active=True):
            cycle_data: dict[str, Any] = {
                "id": cycle.id,
                "name": cycle.name,
                "short_name": cycle.short_name,
                "typical_duration_terms": cycle.typical_duration_terms,
                "majors": [],
            }

            for major in cycle.majors.filter(is_active=True):
                major_data = {
                    "id": major.id,
                    "name": major.name,
                    "code": major.code,
                    "program_type": major.program_type,
                    "total_credits_required": major.total_credits_required,
                }
                cycle_data["majors"].append(major_data)

            structure["cycles"].append(cycle_data)

        return structure

    @staticmethod
    def create_academic_structure(
        division_name: str,
        cycle_name: str,
        major_name: str,
        major_code: str,
        major_type: str = "ACADEMIC",
        created_by: AbstractUser | None = None,
    ) -> dict[str, Any]:
        """Create complete academic structure with proper validation.

        Args:
            division_name: Name of division
            cycle_name: Name of cycle
            major_name: Name of major
            major_code: Major code
            major_type: Type of major
            created_by: User creating the structure

        Returns:
            Dictionary with created structure IDs
        """
        with transaction.atomic():
            # Create or get division
            division, _created = Division.objects.get_or_create(
                name=division_name,
                defaults={
                    "short_name": division_name[:10].upper(),
                    "description": f"{division_name} Division",
                    "is_active": True,
                },
            )

            # Create or get cycle
            cycle, _created = Cycle.objects.get_or_create(
                name=cycle_name,
                division=division,
                defaults={
                    "short_name": cycle_name[:10].upper(),
                    "description": f"{cycle_name} within {division.name}",
                    "typical_duration_terms": 8 if "bachelor" in cycle_name.lower() else 4,
                    "is_active": True,
                },
            )

            # Create major
            major = Major.objects.create(
                name=major_name,
                code=major_code.upper(),
                cycle=cycle,
                program_type=major_type,
                is_active=True,
            )

            return {
                "division_id": division.id,
                "cycle_id": cycle.id,
                "major_id": major.id,
                "created": True,
            }


class CourseService:
    """Service for course management and validation."""

    @staticmethod
    def validate_course_creation(
        code: str,
        title: str,
        credits: int,
        cycle_id: int,
    ) -> bool:
        """Validate course creation parameters.

        Args:
            code: Course code
            title: Course title
            credits: Credit hours
            cycle_id: Cycle ID

        Returns:
            bool: True if valid

        Raises:
            CurriculumError: If validation fails
        """
        # Check for duplicate course code
        if Course.objects.filter(code=code.upper()).exists():
            msg = f"Course code {code} already exists"
            raise CurriculumError(msg)

        # Validate cycle exists
        if not Cycle.objects.filter(id=cycle_id, is_active=True).exists():
            msg = f"Cycle {cycle_id} not found or inactive"
            raise CurriculumError(msg)

        # Validate credits
        if credits < 1 or credits > 12:
            msg = "Credits must be between 1 and 12"
            raise CurriculumError(msg)

        return True

    @staticmethod
    @transaction.atomic
    def create_course_with_templates(
        code: str,
        title: str,
        credits: int,
        cycle_id: int,
        description: str = "",
        part_templates: list[dict[str, Any]] | None = None,
        created_by: AbstractUser | None = None,
    ) -> Course:
        """Create a course with part templates and validation.

        Args:
            code: Course code
            title: Course title
            credits: Credit hours
            cycle_id: Cycle ID
            description: Course description
            part_templates: List of part template definitions
            created_by: User creating the course

        Returns:
            Created Course instance
        """
        # Validate course creation
        CourseService.validate_course_creation(code, title, credits, cycle_id)

        cycle = Cycle.objects.get(id=cycle_id)

        # Create course
        course = Course.objects.create(
            code=code.upper(),
            title=title,
            short_title=title[:50],
            credits=credits,
            cycle=cycle,
            description=description,
            is_active=True,
        )

        if part_templates:
            CourseTemplateService.create_part_templates(course, part_templates)

        return course

    @staticmethod
    def get_course_progression_options(student_major_id: int) -> list[dict[str, Any]]:
        """Get available courses for a student based on their major and completed prerequisites.

        Args:
            student_major_id: Student's major ID

        Returns:
            List of available courses with prerequisite status
        """
        try:
            major = Major.objects.get(id=student_major_id, is_active=True)
        except Major.DoesNotExist as e:
            msg = f"Major {student_major_id} not found"
            raise CurriculumError(msg) from e

        available_courses = []

        for course in major.courses.filter(is_active=True):
            # Check prerequisites (simplified - would need student completion data)
            prerequisites = list(course.required_prerequisites.select_related("prerequisite"))

            course_info = {
                "course_id": course.id,
                "code": course.code,
                "title": course.title,
                "credits": course.credits,
                "prerequisites": [
                    {
                        "code": prereq.prerequisite.code,
                        "title": prereq.prerequisite.title,
                        "is_required": prereq.is_required,
                        "completed": False,  # Would check student records
                    }
                    for prereq in prerequisites
                ],
                "is_available": len(prerequisites) == 0,  # Simplified logic
            }

            available_courses.append(course_info)

        return available_courses

    @staticmethod
    def check_prerequisites(course_id: int, completed_course_codes: list[str]) -> dict[str, Any]:
        """Check if prerequisites are met for a course.

        Args:
            course_id: Course ID to check
            completed_course_codes: List of completed course codes

        Returns:
            Dictionary with prerequisite status
        """
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist as e:
            msg = f"Course {course_id} not found"
            raise CurriculumError(msg) from e

        prerequisites = course.required_prerequisites.select_related("prerequisite")
        completed_codes = {code.upper() for code in completed_course_codes}

        missing_required = []
        missing_optional = []

        for prereq in prerequisites:
            prereq_code = prereq.prerequisite.code

            if prereq_code not in completed_codes:
                if prereq.is_required:
                    missing_required.append(
                        {
                            "code": prereq_code,
                            "title": prereq.prerequisite.title,
                            "relationship": prereq.relationship_type,
                        },
                    )
                else:
                    missing_optional.append(
                        {
                            "code": prereq_code,
                            "title": prereq.prerequisite.title,
                            "relationship": prereq.relationship_type,
                        },
                    )

        return {
            "course_code": course.code,
            "prerequisites_met": len(missing_required) == 0,
            "missing_required": missing_required,
            "missing_optional": missing_optional,
            "can_enroll": len(missing_required) == 0,
        }


class CourseTemplateService:
    """Service for course part template management."""

    @staticmethod
    def validate_template_weights(course_id: int, session_number: int) -> dict[str, Any]:
        """Validate that grade weights for a session sum to 1.000.

        Args:
            course_id: Course ID
            session_number: Session number

        Returns:
            Validation result dictionary
        """
        templates = CoursePartTemplate.objects.filter(
            course_id=course_id,
            session_number=session_number,
            is_active=True,
        )

        total_weight = templates.aggregate(total=Sum("grade_weight"))["total"] or Decimal("0.000")

        is_valid = abs(total_weight - Decimal("1.000")) <= Decimal("0.001")

        return {
            "is_valid": is_valid,
            "total_weight": float(total_weight),
            "expected_weight": 1.000,
            "difference": float(abs(total_weight - Decimal("1.000"))),
            "template_count": templates.count(),
        }

    @staticmethod
    @transaction.atomic
    def create_part_templates(course: Course, templates: list[dict[str, Any]]) -> list[CoursePartTemplate]:
        """Create part templates for a course with validation.

        Args:
            course: Course instance
            templates: List of template definitions

        Returns:
            List of created CoursePartTemplate instances
        """
        created_templates = []

        sessions: dict[int, list] = {}
        for template_data in templates:
            session = template_data["session_number"]
            if session not in sessions:
                sessions[session] = []
            sessions[session].append(template_data)

        # Validate each session's weights sum to 1.000
        for session_num, session_templates in sessions.items():
            total_weight = sum(Decimal(str(t["grade_weight"])) for t in session_templates)

            if abs(total_weight - Decimal("1.000")) > Decimal("0.001"):
                msg = f"Session {session_num} template weights must sum to 1.000, got {total_weight}"
                raise CurriculumError(msg)

        for template_data in templates:
            template = CoursePartTemplate.objects.create(
                course=course,
                name=template_data["part_name"],
                session_number=template_data["session_number"],
                grade_weight=Decimal(str(template_data["grade_weight"])),
                # is_required field doesn't exist on this model, removing it
                is_active=True,
            )
            created_templates.append(template)

        return created_templates

    @staticmethod
    def validate_course_template_completeness(course_id: int) -> dict[str, Any]:
        """Validate that a course has complete and valid templates.

        This is the optimized version from CoursePartTemplate.validate_course_template_completeness.

        Args:
            course_id: Course ID to validate

        Returns:
            Validation result with errors and warnings
        """
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return {
                "valid": False,
                "errors": [f"Course {course_id} not found"],
                "warnings": [],
            }

        templates = CoursePartTemplate.objects.filter(course=course, is_active=True)
        errors = []
        warnings: list[str] = []

        if not templates.exists():
            errors.append(f"Course {course.code} has no part templates defined")
            return {"valid": False, "errors": errors, "warnings": warnings}

        # Check session weight totals using optimized aggregation
        sessions = templates.values_list("session_number", flat=True).distinct()
        for session_num in sessions:
            session_templates = templates.filter(session_number=session_num)
            total_weight = session_templates.aggregate(total_sum=Sum("grade_weight"))["total_sum"] or Decimal("0.000")

            if abs(total_weight - Decimal("1.000")) > Decimal("0.001"):
                errors.append(f"Session {session_num} weights sum to {total_weight:.3f}, should be 1.000")

        # Check IEAP requirements
        if course.code.startswith("IEAP"):
            if len(sessions) != 2:
                errors.append(f"IEAP course {course.code} must have exactly 2 sessions, found {len(sessions)}")

        if templates.exists() and not course.textbooks.exists():
            warnings.append(f"Course {course.code} has templates but no assigned textbooks")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "session_count": len(sessions),
            "template_count": templates.count(),
        }


class TransferCreditService:
    """Service for transfer credit evaluation."""

    @staticmethod
    def evaluate_transfer_credits(
        source_major_id: int,
        target_major_id: int,
        completed_course_codes: list[str],
    ) -> dict[str, Any]:
        """Evaluate which credits can transfer between majors.

        Args:
            source_major_id: Original major ID
            target_major_id: Target major ID
            completed_course_codes: List of completed course codes

        Returns:
            Transfer credit evaluation results
        """
        try:
            source_major = Major.objects.get(id=source_major_id)
            target_major = Major.objects.get(id=target_major_id)
        except Major.DoesNotExist as e:
            msg = "One or both majors not found"
            raise CurriculumError(msg) from e

        transferable_credits = []
        non_transferable_credits = []

        for course_code in completed_course_codes:
            course_code_upper = course_code.upper()

            # Use the fixed transfer credit logic
            can_transfer = target_major.can_transfer_credit_from(source_major, course_code_upper)

            try:
                course = Course.objects.get(code=course_code_upper)
                credit_info = {
                    "course_code": course_code_upper,
                    "course_title": course.title,
                    "credits": course.credits,
                    "transferable": can_transfer,
                }

                if can_transfer:
                    transferable_credits.append(credit_info)
                else:
                    non_transferable_credits.append(credit_info)

            except Course.DoesNotExist:
                non_transferable_credits.append(
                    {
                        "course_code": course_code_upper,
                        "course_title": "Course not found",
                        "credits": 0,
                        "transferable": False,
                        "error": "Course not found in system",
                    },
                )

        total_transferable_credits = sum(c["credits"] for c in transferable_credits)

        return {
            "source_major": source_major.name,
            "target_major": target_major.name,
            "transferable_credits": transferable_credits,
            "non_transferable_credits": non_transferable_credits,
            "total_transferable_credits": total_transferable_credits,
            "transfer_summary": {
                "total_courses_evaluated": len(completed_course_codes),
                "transferable_course_count": len(transferable_credits),
                "non_transferable_course_count": len(non_transferable_credits),
                "transfer_success_rate": (
                    len(transferable_credits) / len(completed_course_codes) if completed_course_codes else 0
                ),
            },
        }


class SeniorProjectService:
    """Service for senior project management."""

    @staticmethod
    def validate_senior_project_group(
        course_id: int,
        student_ids: list[int],
        advisor_id: int | None = None,
    ) -> dict[str, Any]:
        """Validate senior project group formation.

        Args:
            course_id: Senior project course ID
            student_ids: List of student IDs
            advisor_id: Faculty advisor ID

        Returns:
            Validation result
        """
        try:
            course = Course.objects.get(id=course_id, is_senior_project=True)
        except Course.DoesNotExist as e:
            msg = "Course not found or not a senior project course"
            raise CurriculumError(msg) from e

        errors = []
        warnings: list[str] = []

        # Validate group size (1-5 students)
        if len(student_ids) < 1:
            errors.append("Senior project groups must have at least 1 student")
        elif len(student_ids) > 5:
            errors.append("Senior project groups cannot have more than 5 students")

        # Check for duplicate students
        if len(set(student_ids)) != len(student_ids):
            errors.append("Duplicate students in group")

        # Check if students are already in other groups for this course
        existing_groups = SeniorProjectGroup.objects.filter(
            course=course,
            students__id__in=student_ids,
            status__in=[
                SeniorProjectGroup.ProjectStatus.PROPOSED,
                SeniorProjectGroup.ProjectStatus.IN_PROGRESS,
            ],
        ).distinct()

        if existing_groups.exists():
            conflicts = []
            for group in existing_groups:
                conflicts.append(f"Group: {group.project_title}")
            errors.append(f"Some students are already in active groups: {', '.join(conflicts)}")

        # Validate advisor if provided
        if advisor_id:
            # Would check if advisor exists and is eligible
            pass

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "group_size": len(student_ids),
            "pricing_tier": SeniorProjectService.get_pricing_tier_for_group_size(len(student_ids)),
        }

    @staticmethod
    def get_pricing_tier_for_group_size(group_size: int) -> str | None:
        """Get pricing tier code for senior project group size.

        Args:
            group_size: Number of students in group

        Returns:
            Pricing tier code or None if invalid size
        """
        if group_size <= 0 or group_size > 5:
            return None
        if group_size <= 2:
            return "SENIOR_1_2"
        # 3-5
        return "SENIOR_3_5"

    @staticmethod
    @transaction.atomic
    def create_senior_project_group(
        course_id: int,
        project_title: str,
        description: str,
        student_ids: list[int],
        advisor_id: int,
        created_by: AbstractUser | None = None,
    ) -> SeniorProjectGroup:
        """Create a senior project group with validation.

        Args:
            course_id: Senior project course ID
            project_title: Project title
            description: Project description
            student_ids: List of student IDs
            advisor_id: Faculty advisor ID
            created_by: User creating the group

        Returns:
            Created SeniorProjectGroup instance
        """
        # Validate group formation
        validation = SeniorProjectService.validate_senior_project_group(course_id, student_ids, advisor_id)

        if not validation["valid"]:
            msg = f"Group validation failed: {', '.join(validation['errors'])}"
            raise CurriculumError(msg)

        # Get required objects
        course = Course.objects.get(id=course_id)
        # advisor = TeacherProfile.objects.get(id=advisor_id)  # Would need people app integration

        # Create group
        return SeniorProjectGroup.objects.create(
            course=course,
            project_title=project_title,
            project_description=description,
            status=SeniorProjectGroup.ProjectStatus.PROPOSED,
            # advisor=advisor,  # Would set when people app integrated
        )

        # Add students
        # group.students.set(student_ids)  # Would set when people app integrated


class TermService:
    """Service for academic term management."""

    @staticmethod
    def get_current_term() -> Term | None:
        """Get the current active term with caching for performance.

        Note: This returns the first active term. For multiple active terms,
        use get_all_active_terms() instead.
        """
        today = get_current_date()
        # Add ordering to ensure consistent results
        return (
            Term.objects.filter(
                start_date__lte=today,
                end_date__gte=today,
                is_active=True,  # Only consider active terms
            )
            .order_by("start_date")
            .first()
        )

    @staticmethod
    def get_all_active_terms() -> list[Term]:
        """Get all currently active terms (ENG_A, ENG_B, BA, MA).

        Returns all terms that are currently active, typically 4 terms:
        - 2 English terms (ENG_A and ENG_B) that overlap
        - 1 BA term
        - 1 MA term
        """
        today = get_current_date()
        return list(
            Term.objects.filter(
                start_date__lte=today,
                end_date__gte=today,
                is_active=True,
            ).order_by("term_type", "start_date")
        )

    @staticmethod
    def get_active_terms_by_type() -> dict[str, Term | None]:
        """Get active terms organized by type.

        Returns a dictionary with keys for each term type and the active term
        for that type (or None if no active term).
        """
        today = get_current_date()
        active_terms = Term.objects.filter(
            start_date__lte=today,
            end_date__gte=today,
            is_active=True,
        )

        result: dict[str, Term | None] = {
            "ENG_A": None,
            "ENG_B": None,
            "BA": None,
            "MA": None,
            "SPECIAL": None,
        }

        for term in active_terms:
            if term.term_type == Term.TermType.ENGLISH_A:
                result["ENG_A"] = term
            elif term.term_type == Term.TermType.ENGLISH_B:
                result["ENG_B"] = term
            elif term.term_type == Term.TermType.BACHELORS:
                result["BA"] = term
            elif term.term_type == Term.TermType.MASTERS:
                result["MA"] = term
            elif term.term_type == Term.TermType.SPECIAL:
                result["SPECIAL"] = term

        return result

    @staticmethod
    def get_upcoming_terms(limit: int = 5) -> list[Term]:
        """Get upcoming terms with performance optimization."""
        today = get_current_date()
        return list(
            Term.objects.filter(
                start_date__gt=today,
                is_active=True,  # Only consider active terms
            ).order_by("start_date")[:limit]
        )

    @staticmethod
    def validate_term_dates(start_date: date, end_date: date) -> bool:
        """Validate term date range.

        Args:
            start_date: Term start date
            end_date: Term end date

        Returns:
            True if valid

        Raises:
            CurriculumError: If dates are invalid
        """
        if start_date >= end_date:
            msg = "Term start date must be before end date"
            raise CurriculumError(msg)

        # Check for overlapping terms
        overlapping = Term.objects.filter(
            Q(start_date__lte=start_date, end_date__gte=start_date)
            | Q(start_date__lte=end_date, end_date__gte=end_date)
            | Q(start_date__gte=start_date, end_date__lte=end_date),
        )

        if overlapping.exists():
            overlapping_terms = ", ".join(term.code for term in overlapping)
            msg = f"Term dates overlap with existing terms: {overlapping_terms}"
            raise CurriculumError(msg)

        return True
