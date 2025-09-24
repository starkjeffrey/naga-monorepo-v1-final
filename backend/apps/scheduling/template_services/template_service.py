"""Service for managing class part templates and promotions.

Handles template application, student promotion, and cohort management
for language program classes.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

from django.db import transaction
from django.utils import timezone

from apps.scheduling.models_templates import (
    ClassPartTemplate,
    ClassPartTemplateSet,
    ClassPromotionRule,
)

if TYPE_CHECKING:
    from apps.people.models import StudentProfile
    from apps.scheduling.models import ClassHeader, ClassPart

logger = logging.getLogger(__name__)


def parse_course_code(course_code: str) -> tuple[str, int] | None:
    """Parse course code to extract program and level.

    Args:
        course_code: Course code like "EHSS-07" or "GESL-03"

    Returns:
        Tuple of (program_code, level_number) or None if invalid
    """
    if not course_code or "-" not in course_code:
        return None

    try:
        program_code, level_str = course_code.split("-", 1)
        level_number = int(level_str)
        return program_code, level_number
    except (ValueError, IndexError):
        return None


class ClassTemplateService:
    """Service for managing class templates and structure generation."""

    @staticmethod
    def apply_template_to_class(
        class_header: ClassHeader,
        template_set: ClassPartTemplateSet | None = None,
        term: str | None = None,
    ) -> list[ClassPart]:
        """Apply templates to create class parts for a class.

        Args:
            class_header: The class to apply templates to
            template_set: Optional specific template set to use
            term: Optional term for session creation

        Returns:
            List of created ClassPart instances
        """
        from apps.scheduling.models import ClassSession

        # Get template set if not provided
        if not template_set:
            # Extract program and level from course code (e.g., "EHSS-07")
            course_code = class_header.course.code
            parsed = parse_course_code(course_code)
            if not parsed:
                logger.error("Could not parse course code: %s", course_code)
                return []

            program_code, level_number = parsed
            template_set = ClassPartTemplateSet.get_current_for_level(
                program_code=program_code,
                level_number=level_number,
            )

            if not template_set:
                logger.warning(
                    "No template found for %s level %s",
                    program_code,
                    level_number,
                )
                return []

        # Get or create session for the term
        if term:
            session, created = ClassSession.objects.get_or_create(
                class_header=class_header,
                session_number=1,
                defaults={
                    "session_name": "",
                    "grade_weight": Decimal("1.000"),
                },
            )
        else:
            # Use the first session (session_number=1)
            session_or_none = class_header.class_sessions.filter(session_number=1).first()
            if session_or_none is None:
                # Create a session if none exists
                session = ClassSession.objects.create(
                    class_header=class_header,
                    session_number=1,
                    grade_weight=Decimal("1.000"),
                )
            else:
                session = session_or_none

        # Apply the template
        created_parts = template_set.apply_to_session(session)

        logger.info(
            "Applied template %s to class %s, created %d parts",
            template_set,
            class_header,
            len(created_parts),
        )

        return created_parts

    @staticmethod
    def create_template_set(
        program_code: str,
        level_number: int,
        parts_config: list[dict],
        effective_date: str | None = None,
        name: str | None = None,
    ) -> ClassPartTemplateSet:
        """Create a new template set with parts.

        Args:
            program_code: Program code (EHSS, GESL, etc.)
            level_number: Level number
            parts_config: List of part configurations
            effective_date: Optional effective date (defaults to today)
            name: Optional template set name

        Returns:
            Created ClassPartTemplateSet

        Example parts_config:
            [
                {
                    "name": "Ventures Ventures",
                    "class_part_type": "MAIN",
                    "class_part_code": "A",
                    "meeting_days_pattern": "MON,WED",
                    "grade_weight": 0.4,
                    "sequence_order": 1,
                },
                {
                    "name": "Reading",
                    "class_part_type": "READING",
                    "class_part_code": "B",
                    "meeting_days_pattern": "TUE,THU",
                    "grade_weight": 0.4,
                    "sequence_order": 2,
                },
                {
                    "name": "Computer Training",
                    "class_part_type": "COMPUTER",
                    "class_part_code": "C",
                    "meeting_days_pattern": "FRI",
                    "grade_weight": 0.2,
                    "sequence_order": 3,
                },
            ]
        """
        with transaction.atomic():
            # Create template set
            template_set = ClassPartTemplateSet.objects.create(
                program_code=program_code,
                level_number=level_number,
                effective_date=effective_date or timezone.now().date(),
                name=name or f"{program_code}-{level_number:02d} Template",
                description=f"Template for {program_code} Level {level_number}",
            )

            # Create parts
            for config in parts_config:
                ClassPartTemplate.objects.create(template_set=template_set, **config)

            logger.info(
                "Created template set %s with %d parts",
                template_set,
                len(parts_config),
            )

            return template_set


class StudentPromotionService:
    """Service for promoting students between levels."""

    @staticmethod
    def promote_students(
        students: list[StudentProfile],
        source_class: ClassHeader,
        destination_program: str,
        destination_level: int,
        new_term: str,
        preserve_cohort: bool = True,
    ) -> dict[str, Any]:
        """Promote students to a new level.

        Args:
            students: Students to promote
            source_class: Current class
            destination_program: Target program code
            destination_level: Target level number
            new_term: Term for the new class
            preserve_cohort: Whether to keep students together

        Returns:
            Dictionary with promotion results
        """
        from apps.curriculum.models import Term
        from apps.enrollment.models import ClassHeaderEnrollment
        from apps.scheduling.models import ClassHeader

        results: dict[str, Any] = {
            "promoted": [],
            "new_classes": [],
            "errors": [],
        }

        with transaction.atomic():
            # Extract program and level from source class
            parsed = parse_course_code(source_class.course.code)
            if not parsed:
                logger.error("Could not parse source class course code: %s", source_class.course.code)
                return {
                    "promoted": [],
                    "new_classes": [],
                    "errors": [f"Invalid course code: {source_class.course.code}"],
                }

            source_program, source_level = parsed

            # Get promotion rule
            rule = ClassPromotionRule.objects.filter(
                source_program=source_program,
                source_level=source_level,
                destination_program=destination_program,
                destination_level=destination_level,
                is_active=True,
            ).first()

            if not rule:
                logger.warning(
                    "No promotion rule found for %s-%s to %s-%s",
                    source_program,
                    source_level,
                    destination_program,
                    destination_level,
                )

            # Group students by section if preserving cohort
            if preserve_cohort and rule and rule.preserve_cohort:
                sections: dict[str, list] = {}
                for student in students:
                    # Get student's current section
                    enrollment = ClassHeaderEnrollment.objects.filter(
                        student=student,
                        class_header=source_class,
                        status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
                    ).first()

                    if enrollment:
                        class_header = cast("ClassHeader", enrollment.class_header)
                        section = class_header.section_id or "A"
                        if section not in sections:
                            sections[section] = []
                        sections[section].append(student)
            else:
                # All students in one group
                sections = {"A": students}

            # Create new classes and enroll students
            for section, section_students in sections.items():
                # Get the destination course
                from apps.curriculum.models import Course

                destination_course_code = f"{destination_program}-{destination_level:02d}"
                try:
                    destination_course = Course.objects.get(code=destination_course_code)
                except Course.DoesNotExist:
                    logger.error("Destination course %s not found", destination_course_code)
                    results["errors"].append(f"Course {destination_course_code} not found")
                    continue

                # Get the term object
                try:
                    term_obj = Term.objects.get(code=new_term)
                except Term.DoesNotExist:
                    logger.error("Term %s not found", new_term)
                    results["errors"].append(f"Term {new_term} not found")
                    continue

                # Create new class
                new_class = ClassHeader.objects.create(
                    course=destination_course,
                    term=term_obj,
                    section_id=section,
                    max_enrollment=len(section_students) + 5,  # Some buffer
                )

                # Apply template if configured
                if rule and rule.apply_template:
                    template_service = ClassTemplateService()
                    template_service.apply_template_to_class(
                        class_header=new_class,
                        term=new_term,
                    )

                # Enroll students
                for student in section_students:
                    try:
                        # Deactivate old enrollment
                        from apps.enrollment.models import ClassHeaderEnrollment

                        old_enrollments = ClassHeaderEnrollment.objects.filter(
                            student=student,
                            class_header=source_class,
                            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
                        )
                        old_enrollments.update(
                            status=ClassHeaderEnrollment.EnrollmentStatus.COMPLETED,
                        )

                        # Create new enrollment
                        ClassHeaderEnrollment.objects.create(
                            student=student,
                            class_header=new_class,
                            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
                        )

                        results["promoted"].append(student)

                    except Exception as e:
                        logger.error(
                            "Failed to promote student %s: %s",
                            student,
                            str(e),
                        )
                        results["errors"].append(
                            {
                                "student": student,
                                "error": str(e),
                            }
                        )

                results["new_classes"].append(new_class)

                logger.info(
                    "Promoted %d students to new class %s",
                    len(section_students),
                    new_class,
                )

        return results

    @staticmethod
    def bulk_promote_level(
        source_program: str,
        source_level: int,
        destination_program: str,
        destination_level: int,
        term: str,
    ) -> dict:
        """Promote all active students from one level to another.

        Args:
            source_program: Source program code
            source_level: Source level number
            destination_program: Target program code
            destination_level: Target level number
            term: New term ID

        Returns:
            Dictionary with promotion results
        """
        from apps.scheduling.models import ClassHeader

        # Get all active students at source level by filtering course codes
        source_course_code = f"{source_program}-{source_level:02d}"
        source_classes = ClassHeader.objects.filter(
            course__code=source_course_code,
            status__in=[ClassHeader.ClassStatus.ACTIVE, ClassHeader.ClassStatus.SCHEDULED],
        ).select_related("course")

        all_results: dict[str, Any] = {
            "total_promoted": 0,
            "total_classes_created": 0,
            "class_results": [],
        }

        for source_class in source_classes:
            # Get active students
            from apps.enrollment.models import ClassHeaderEnrollment

            enrollments = ClassHeaderEnrollment.objects.filter(
                class_header=source_class,
                status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            ).select_related("student")

            students = [cast("StudentProfile", e.student) for e in enrollments]

            if students:
                service = StudentPromotionService()
                results = service.promote_students(
                    students=students,
                    source_class=source_class,
                    destination_program=destination_program,
                    destination_level=destination_level,
                    new_term=term,
                    preserve_cohort=True,
                )

                all_results["total_promoted"] += len(results.get("promoted", []))
                all_results["total_classes_created"] += len(results.get("new_classes", []))
                all_results["class_results"].append(results)

        logger.info(
            "Bulk promotion complete: %d students promoted, %d classes created",
            all_results["total_promoted"],
            all_results["total_classes_created"],
        )

        return all_results
