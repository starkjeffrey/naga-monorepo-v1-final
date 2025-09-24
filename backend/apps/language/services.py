"""Language program services for auto-promotion and level management.

This module provides business logic for language program specific operations:
- Automatic student promotion between levels with mandatory template support
- Template-based class creation (no fallback cloning)
- Language level progression validation
- Term preparation workflows

All services follow clean architecture principles and enforce curriculum integrity.
"""

import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from users.models import User as UserType

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.common.models import StudentActivityLog, SystemAuditLog
from apps.curriculum.models import Course, Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.language.enums import LanguageLevel
from apps.people.models import StudentProfile
from apps.scheduling.models import ClassHeader, ClassSession
from apps.scheduling.models_templates import ClassPartTemplateSet

from .models import (
    LanguageLevelSkipRequest,
    LanguageProgramPromotion,
    LanguageStudentPromotion,
)

User = get_user_model()

# Constants
MAX_LEVEL_SKIP = 3  # Business rule: maximum levels that can be skipped

# Initialize logger
logger = logging.getLogger(__name__)


class LanguagePromotionError(Exception):
    """Custom exception for language promotion errors."""


class LanguageLevelSkipError(Exception):
    """Custom exception for language level skip errors."""


class LanguageTemplateError(Exception):
    """Raised when language class templates are missing or invalid."""


@contextmanager
def safe_operation(operation_name: str):
    """Context manager for safe database operations with logging."""
    try:
        logger.info("Starting operation: %s", operation_name)
        yield
        logger.info("Completed operation: %s", operation_name)
    except Exception as e:
        logger.error("Failed operation: %s - %s", operation_name, str(e))
        raise


@dataclass
class PromotionPlan:
    """Plan for promoting students in a language program."""

    source_term: Term
    target_term: Term
    program: str
    eligible_students: list[tuple[StudentProfile, str, str]]  # (student, from_level, to_level)
    classes_to_create: list[dict]  # Classes that need to be created
    estimated_student_count: int
    estimated_class_count: int


@dataclass
class PromotionResult:
    """Result of a promotion operation."""

    success: bool
    promotion_batch: LanguageProgramPromotion | None = None
    students_promoted: int = 0
    classes_created: int = 0
    errors: list[str] = field(default_factory=list)
    message: str = ""
    created_classes: list[ClassHeader] = field(default_factory=list)


class LanguagePromotionService:
    """Service for managing language program promotions."""

    @staticmethod
    def validate_templates_exist(program: str, start_level: int, end_level: int) -> tuple[bool, list[str]]:
        """Validate that all required templates exist for a range of levels.

        Args:
            program: Language program code (EHSS, GESL, IEAP, EXPRESS)
            start_level: Starting level number
            end_level: Ending level number (inclusive)

        Returns:
            Tuple of (all_exist, list_of_missing)
        """
        missing = []

        for level in range(start_level, end_level + 1):
            template_set = ClassPartTemplateSet.get_current_for_level(program_code=program, level_number=level)

            if not template_set:
                missing.append(f"{program}-{level:02d}")

        return len(missing) == 0, missing

    @staticmethod
    def analyze_promotion_eligibility(source_term: Term, target_term: Term, program: str) -> PromotionPlan:
        """Analyze which students are eligible for promotion.

        Args:
            source_term: Term students are completing
            target_term: Term students will be promoted to
            program: Language program (EHSS, GESL, etc.)

        Returns:
            PromotionPlan with eligible students and classes to clone

        Raises:
            LanguagePromotionError: If validation fails or required data is missing
        """
        # Validate inputs
        if not source_term or not target_term or not program:
            raise LanguagePromotionError("Source term, target term, and program are required")

        if source_term.end_date >= target_term.start_date:
            raise LanguagePromotionError("Source term must end before target term starts")

        with safe_operation(f"analyze_promotion_eligibility_{program}_{source_term.code}_{target_term.code}"):
            # Find all classes in the source term for this program
            program_classes = ClassHeader.objects.filter(
                term=source_term,
                course__code__startswith=program,
                course__is_language=True,
            ).select_related("course", "term", "course__division")

            eligible_students = []
            classes_to_create = []

            for class_header in program_classes:
                # Find students who completed this class successfully
                completed_enrollments = ClassHeaderEnrollment.objects.filter(
                    class_header=class_header,
                    status__in=[
                        ClassHeaderEnrollment.EnrollmentStatus.COMPLETED,
                        ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,  # Still enrolled at term end
                    ],
                ).select_related("student", "student__person", "class_header")

                # Parse current level from course code (e.g., EHSS-05 -> level 5)
                current_level = LanguagePromotionService._extract_level_from_course_code(class_header.course.code)

                if current_level is None:
                    continue

                # Find next level for this program
                language_level = LanguageLevel.get_level_by_program_and_num(program, current_level)
                if language_level:
                    next_language_level = LanguageLevel.get_next_level(language_level)
                    if next_language_level:
                        next_level = next_language_level.level_num

                        # Add eligible students
                        for enrollment in completed_enrollments:
                            if LanguagePromotionService._is_student_eligible_for_promotion(enrollment):
                                # Type cast to help mypy understand the concrete type
                                student: StudentProfile = cast("StudentProfile", enrollment.student)
                                eligible_students.append(
                                    (
                                        student,
                                        f"{program}-{current_level:02d}",
                                        f"{program}-{next_level:02d}",
                                    ),
                                )

                # Mark class for creation if it has eligible students
                if any(LanguagePromotionService._is_student_eligible_for_promotion(e) for e in completed_enrollments):
                    next_level_code = f"{program}-{(current_level + 1):02d}"
                    classes_to_create.append(
                        {
                            "course_code": next_level_code,
                            "section_id": class_header.section_id,
                            "time_of_day": class_header.time_of_day,
                            "max_enrollment": class_header.max_enrollment,
                        }
                    )

            return PromotionPlan(
                source_term=source_term,
                target_term=target_term,
                program=program,
                eligible_students=eligible_students,
                classes_to_create=classes_to_create,
                estimated_student_count=len(eligible_students),
                estimated_class_count=len(classes_to_create),
            )

    @staticmethod
    def _extract_level_from_course_code(course_code: str) -> int | None:
        """Extract level number from course code (e.g., EHSS-05 -> 5)."""
        try:
            if "-" in course_code:
                level_part = course_code.split("-")[1]
                return int(level_part)
        except (IndexError, ValueError):
            pass
        return None

    @staticmethod
    def _is_student_eligible_for_promotion(enrollment: ClassHeaderEnrollment) -> bool:
        """Check if student is eligible for promotion based on their performance."""
        # Check if student has passing grade or is still enrolled
        if enrollment.status == ClassHeaderEnrollment.EnrollmentStatus.COMPLETED:
            # For completed courses, check if they have a passing grade
            passing_grades = [
                "D",
                "D+",
                "C-",
                "C",
                "C+",
                "B-",
                "B",
                "B+",
                "A-",
                "A",
                "A+",
            ]
            return enrollment.final_grade in passing_grades
        if enrollment.status == ClassHeaderEnrollment.EnrollmentStatus.ENROLLED:
            # Still enrolled students are eligible (assumed to be passing)
            return True

        return False

    @staticmethod
    @transaction.atomic
    def execute_promotion(promotion_plan: PromotionPlan, initiated_by: "UserType", notes: str = "") -> PromotionResult:
        """Execute the promotion plan.

        Args:
            promotion_plan: Plan created by analyze_promotion_eligibility
            initiated_by: "UserType" performing the promotion
            notes: Optional notes about the promotion

        Returns:
            PromotionResult with success status and details
        """
        errors = []

        try:
            # Create promotion batch record
            promotion_batch = LanguageProgramPromotion.objects.create(
                source_term=promotion_plan.source_term,
                target_term=promotion_plan.target_term,
                program=promotion_plan.program,
                initiated_by=initiated_by,
                notes=notes,
                status=LanguageProgramPromotion.PromotionStatus.IN_PROGRESS,
            )

            classes_created = 0
            students_promoted = 0

            # Create classes first using templates
            created_class_mapping = {}
            for class_info in promotion_plan.classes_to_create:
                try:
                    # Find the course for this level
                    next_course = Course.objects.get(code=class_info["course_code"])

                    # Create class with template
                    created_class = LanguagePromotionService.create_class_with_template(
                        course=next_course,
                        term=promotion_plan.target_term,
                        section_id=class_info["section_id"],
                        time_of_day=class_info["time_of_day"],
                        max_enrollment=class_info["max_enrollment"],
                    )

                    created_class_mapping[class_info["course_code"]] = created_class
                    classes_created += 1

                except Course.DoesNotExist:
                    errors.append(f"Course {class_info['course_code']} not found")
                except LanguageTemplateError as e:
                    errors.append(f"Template error for {class_info['course_code']}: {e!s}")
                except Exception as e:
                    errors.append(f"Failed to create class {class_info['course_code']}: {e!s}")

            # Promote students
            for student, from_level, to_level in promotion_plan.eligible_students:
                try:
                    # Find source class enrollment
                    source_enrollment = (
                        ClassHeaderEnrollment.objects.filter(
                            student=student,
                            class_header__term=promotion_plan.source_term,
                            class_header__course__code__startswith=promotion_plan.program,
                        )
                        .select_related("class_header", "class_header__course", "student", "student__person")
                        .first()
                    )

                    if not source_enrollment:
                        errors.append(f"No source enrollment found for {student}")
                        continue

                    # Find target class based on next level
                    source_level = LanguagePromotionService._extract_level_from_course_code(
                        source_enrollment.class_header.course.code
                    )
                    if source_level is None:
                        errors.append(f"Cannot determine source level for {student}")
                        continue

                    next_level_code = f"{promotion_plan.program}-{(source_level + 1):02d}"
                    target_class = created_class_mapping.get(next_level_code)
                    if not target_class:
                        errors.append(f"No target class found for {student.student_id}: {student.person.full_name}")
                        continue

                    # Create promotion record
                    LanguageStudentPromotion.objects.create(
                        promotion_batch=promotion_batch,
                        student=student,
                        from_level=from_level,
                        to_level=to_level,
                        source_class=source_enrollment.class_header,
                        target_class=target_class,
                        result=LanguageStudentPromotion.PromotionResult.PROMOTED,
                        final_grade=source_enrollment.final_grade or "",
                    )

                    # Create enrollment in target class
                    ClassHeaderEnrollment.objects.create(
                        student=student,
                        class_header=target_class,
                        enrolled_by=initiated_by,
                        status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
                        notes=f"Auto-promoted from {from_level} via promotion batch {promotion_batch.id}",
                    )

                    # Log the promotion activity
                    StudentActivityLog.log_student_activity(
                        student=student,
                        activity_type=StudentActivityLog.ActivityType.LANGUAGE_PROMOTION,
                        description=f"Student promoted from {from_level} to {to_level} via automatic promotion batch",
                        performed_by=initiated_by,
                        term=promotion_plan.target_term,
                        class_header=target_class,
                        program_name=promotion_plan.program,
                        activity_details={
                            "promotion_batch_id": promotion_batch.id,
                            "from_level": from_level,
                            "to_level": to_level,
                            "source_term": promotion_plan.source_term.code,
                            "promotion_type": "automatic",
                        },
                        is_system_generated=True,
                    )

                    students_promoted += 1

                except Exception as e:
                    errors.append(f"Failed to promote student {student}: {e!s}")

            # Mark promotion as completed
            promotion_batch.mark_completed(students_promoted, classes_created)

            return PromotionResult(
                success=len(errors) == 0,
                promotion_batch=promotion_batch,
                students_promoted=students_promoted,
                classes_created=classes_created,
                errors=errors,
                message=f"Promoted {students_promoted} students and created {classes_created} classes",
                created_classes=list(created_class_mapping.values()),
            )

        except Exception as e:
            errors.append(f"Critical error during promotion: {e!s}")
            return PromotionResult(
                success=False,
                errors=errors,
                message="Promotion failed due to critical error",
            )

    @staticmethod
    def create_class_with_template(
        course: Course,
        term: Term,
        section_id: str,
        time_of_day: str | None = None,
        max_enrollment: int = 20,
    ) -> ClassHeader:
        """Create a language class with mandatory template application.

        Args:
            course: Course to create class for
            term: Term for the class
            section_id: Section identifier
            time_of_day: Optional time of day (MORNING, AFTERNOON, EVENING)
            max_enrollment: Maximum enrollment capacity

        Returns:
            Created ClassHeader with all parts from template

        Raises:
            LanguageTemplateError: If template is missing or invalid
        """
        # Extract program and level from course code
        if not course.code or len(course.code) < 3:
            raise LanguageTemplateError(f"Invalid course code: {course.code}")

        # Parse program and level (e.g., "EHSS-07" or "IEAP-03")
        parts = course.code.split("-")
        if len(parts) != 2:
            raise LanguageTemplateError(f"Course code must be in format PROGRAM-LEVEL: {course.code}")

        program_code = parts[0]
        try:
            level_number = int(parts[1])
        except ValueError as err:
            raise LanguageTemplateError(f"Invalid level number in course code: {course.code}") from err

        # Get current template for this level
        template_set = ClassPartTemplateSet.get_current_for_level(program_code=program_code, level_number=level_number)

        if not template_set:
            raise LanguageTemplateError(
                f"No active template found for {program_code} Level {level_number}. "
                f"Language classes CANNOT be created without templates. "
                f"Please create a ClassPartTemplateSet for {program_code}-{level_number:02d} first."
            )

        # Validate template has parts
        if not template_set.templates.filter(is_active=True).exists():
            raise LanguageTemplateError(
                f"Template set for {program_code}-{level_number:02d} has no active parts defined."
            )

        # Create the class header
        with transaction.atomic():
            class_header = ClassHeader.objects.create(
                course=course,
                term=term,
                section_id=section_id,
                time_of_day=time_of_day or ClassHeader.TimeOfDay.MORNING,
                max_enrollment=max_enrollment,
                status=ClassHeader.ClassStatus.DRAFT,
                notes=f"Created from template: {template_set}",
            )

            # Create session based on program type
            # IEAP has 2 sessions, others have 1
            is_ieap = program_code == "IEAP"
            session_count = 2 if is_ieap else 1

            for session_num in range(1, session_count + 1):
                session = ClassSession.objects.create(
                    class_header=class_header,
                    session_number=session_num,
                    session_name=f"Session {chr(64 + session_num)}" if is_ieap else "",
                    grade_weight=Decimal("0.500") if is_ieap else Decimal("1.000"),
                )

                # Apply template to create parts
                if session_num == 1:  # Apply template only to first/main session
                    created_parts = template_set.apply_to_session(session)

                    logger.info(
                        "Created %d parts for class %s from template %s",
                        len(created_parts),
                        class_header,
                        template_set,
                    )

        return class_header

    @staticmethod
    def get_promotion_history(program: str, limit: int = 10) -> list[LanguageProgramPromotion]:
        """Get recent promotion history for a program."""
        return list(
            LanguageProgramPromotion.objects.filter(program=program)
            .select_related("source_term", "target_term", "initiated_by")
            .prefetch_related("student_promotions__student__person")
            .order_by("-initiated_at")[:limit]
        )

    @staticmethod
    def get_failed_students_for_workflow(
        promotion_batch: LanguageProgramPromotion,
    ) -> list[LanguageStudentPromotion]:
        """Get students who failed promotion and need workflow follow-up."""
        return list(
            LanguageStudentPromotion.objects.filter(
                promotion_batch=promotion_batch,
                result__in=[
                    LanguageStudentPromotion.PromotionResult.FAILED_COURSE,
                    LanguageStudentPromotion.PromotionResult.NO_SHOW,
                ],
            ).select_related("student", "student__person", "source_class", "target_class")
        )

    @staticmethod
    def suggest_target_term_for_promotion(source_term: Term) -> Term | None:
        """Suggest appropriate target term for language program promotion.

        Uses the Term model's suggest_target_term method to find the next
        available term of the same type (ENG_A -> ENG_A, BA -> BA, etc.).

        Args:
            source_term: The term students are completing

        Returns:
            Next available term of same type, or None if no suitable term found

        Example:
            source_term = Term.objects.get(code="ENG_A_2024_1")
            target_term = LanguagePromotionService.suggest_target_term_for_promotion(source_term)
            if target_term:
                plan = LanguagePromotionService.analyze_promotion_eligibility(
                    source_term=source_term,
                    target_term=target_term,
                    program="EHSS"
                )
        """
        return Term.suggest_target_term(source_term)

    @staticmethod
    def promote_class_section(
        source_class: ClassHeader,
        target_term: Term,
        initiated_by: "UserType",
        preserve_time_of_day: bool = True,
    ) -> tuple[ClassHeader | None, list[StudentProfile]]:
        """Promote an entire class section to the next level.

        Args:
            source_class: Current class to promote from
            target_term: Term to promote to
            initiated_by: User initiating the promotion
            preserve_time_of_day: Whether to keep same time of day

        Returns:
            Tuple of (new_class, promoted_students)

        Raises:
            LanguageTemplateError: If target level template is missing
        """

        # Parse current level
        course_code = source_class.course.code
        parts = course_code.split("-")
        if len(parts) != 2:
            raise ValueError(f"Invalid course code format: {course_code}")

        program_code = parts[0]
        current_level = int(parts[1])

        # Determine next level
        next_level = current_level + 1

        # Special handling for IEAP-04 → BA transition
        if program_code == "IEAP" and current_level == 4:
            logger.info("IEAP-04 students ready for BA program, no language class to create")
            return None, []

        # Check if next level exists in program
        next_level_course_code = f"{program_code}-{next_level:02d}"

        try:
            next_course = Course.objects.get(code=next_level_course_code)
        except Course.DoesNotExist:
            logger.warning("No course found for %s, students completed language program", next_level_course_code)
            return None, []

        # Create the new class with template (will raise if template missing)
        new_class = LanguagePromotionService.create_class_with_template(
            course=next_course,
            term=target_term,
            section_id=source_class.section_id,  # Keep same section
            time_of_day=source_class.time_of_day if preserve_time_of_day else None,
            max_enrollment=source_class.max_enrollment,
        )

        # Get active students from source class
        active_enrollments = ClassHeaderEnrollment.objects.filter(
            class_header=source_class,
            status__in=["ENROLLED", "COMPLETED"],
        ).select_related("student")

        promoted_students = []

        # Enroll students in new class
        with transaction.atomic():
            for enrollment in active_enrollments:
                # Check if student passed (you may want to add grade checking logic here)
                # For now, we'll promote all active students

                # Create enrollment in new class
                ClassHeaderEnrollment.objects.create(
                    student=enrollment.student,
                    class_header=new_class,
                    enrolled_by=initiated_by,
                    status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
                    notes=f"Promoted from {course_code} in {source_class.term.code}",
                )

                # Deactivate old enrollment
                enrollment.status = ClassHeaderEnrollment.EnrollmentStatus.COMPLETED
                enrollment.save()

                promoted_students.append(cast("StudentProfile", enrollment.student))

                logger.info(
                    "Promoted student %s from %s to %s",
                    enrollment.student,
                    course_code,
                    next_level_course_code,
                )

        logger.info(
            "Successfully promoted %d students from %s to %s",
            len(promoted_students),
            source_class,
            new_class,
        )

        return new_class, promoted_students

    @staticmethod
    def bulk_promote_level(
        program: str,
        source_level: int,
        source_term: Term,
        target_term: Term,
        initiated_by: "UserType",
    ) -> PromotionResult:
        """Promote all classes of a specific level to the next level.

        Args:
            program: Language program code
            source_level: Current level number
            source_term: Current term
            target_term: Target term for promotion
            initiated_by: User initiating the promotion

        Returns:
            PromotionResult with details of the promotion
        """
        # First validate that target level template exists
        target_level = source_level + 1
        template_exists, missing = LanguagePromotionService.validate_templates_exist(
            program=program,
            start_level=target_level,
            end_level=target_level,
        )

        if not template_exists:
            return PromotionResult(
                success=False,
                errors=[f"Missing required templates: {', '.join(missing)}"],
                message=f"Cannot promote to {program}-{target_level:02d} without templates",
            )

        # Find all source classes
        source_course_code = f"{program}-{source_level:02d}"
        source_classes = ClassHeader.objects.filter(
            course__code=source_course_code,
            term=source_term,
            status__in=["ACTIVE", "SCHEDULED"],
        )

        if not source_classes.exists():
            return PromotionResult(
                success=False,
                message=f"No active classes found for {source_course_code} in {source_term.code}",
            )

        result = PromotionResult(success=True)

        # Promote each class
        for source_class in source_classes:
            try:
                new_class, promoted_students = LanguagePromotionService.promote_class_section(
                    source_class=source_class,
                    target_term=target_term,
                    initiated_by=initiated_by,
                    preserve_time_of_day=True,
                )

                if new_class:
                    result.classes_created += 1
                    result.students_promoted += len(promoted_students)
                    result.created_classes.append(new_class)

            except Exception as e:
                result.errors.append(f"Failed to promote {source_class}: {e!s}")
                result.success = False

        result.message = f"Promoted {result.students_promoted} students, created {result.classes_created} classes"

        if result.errors:
            result.message += f" with {len(result.errors)} errors"

        return result


class LanguageLevelSkipService:
    """Service for managing language level skip requests and implementations."""

    @staticmethod
    def create_skip_request(
        student: StudentProfile,
        current_level: str,
        target_level: str,
        program: str,
        reason_category: str,
        detailed_reason: str,
        supporting_evidence: str,
        requested_by: "UserType",
    ) -> LanguageLevelSkipRequest:
        """Create a new level skip request.

        Args:
            student: Student requesting the skip
            current_level: Current language level
            target_level: Desired target level
            program: Language program
            reason_category: Category of reason
            detailed_reason: Detailed explanation
            supporting_evidence: Supporting documentation
            requested_by: Staff member submitting request

        Returns:
            Created LanguageLevelSkipRequest
        """
        # Calculate levels skipped
        current_level_num = LanguageLevelSkipService._extract_level_num(current_level)
        target_level_num = LanguageLevelSkipService._extract_level_num(target_level)
        levels_skipped = target_level_num - current_level_num if current_level_num and target_level_num else 1

        return LanguageLevelSkipRequest.objects.create(
            student=student,
            current_level=current_level,
            target_level=target_level,
            program=program,
            levels_skipped=max(1, levels_skipped),
            reason_category=reason_category,
            detailed_reason=detailed_reason,
            supporting_evidence=supporting_evidence,
            requested_by=requested_by,
        )

    @staticmethod
    def _extract_level_num(level_str: str) -> int | None:
        """Extract numeric level from level string (e.g., 'EHSS-05' -> 5).

        Args:
            level_str: Level string in format 'PROGRAM-##'

        Returns:
            Numeric level or None if parsing fails
        """
        try:
            if "-" in level_str:
                level_part = level_str.split("-")[1]
                return int(level_part.lstrip("0") or "0")  # Handle leading zeros
        except (IndexError, ValueError):
            pass
        return None

    @staticmethod
    @transaction.atomic
    def approve_skip_request(
        skip_request: LanguageLevelSkipRequest,
        approved_by: "UserType",
        review_notes: str = "",
        request=None,
    ) -> bool:
        """Approve a level skip request with audit logging.

        Args:
            skip_request: The skip request to approve
            approved_by: Manager approving the request
            review_notes: Notes from the reviewer
            request: HTTP request for audit trail

        Returns:
            True if successfully approved
        """
        try:
            # Approve the request
            skip_request.approve(approved_by, review_notes)

            # Log the approval action
            SystemAuditLog.log_override(
                action_type=SystemAuditLog.ActionType.LANGUAGE_LEVEL_SKIP,
                performed_by=approved_by,
                target_app="language",
                target_model="LanguageLevelSkipRequest",
                target_object_id=str(skip_request.id),
                override_reason=f"Level skip approved: {skip_request.detailed_reason}",
                original_restriction=f"Normal progression from {skip_request.current_level} to next level",
                override_details={
                    "student_id": skip_request.student.id,
                    "student_number": skip_request.student.student_id,
                    "current_level": skip_request.current_level,
                    "target_level": skip_request.target_level,
                    "levels_skipped": skip_request.levels_skipped,
                    "reason_category": skip_request.reason_category,
                    "review_notes": review_notes,
                },
                request=request,
            )

            return True

        except Exception:
            return False

    @staticmethod
    @transaction.atomic
    def implement_level_skip(
        skip_request: LanguageLevelSkipRequest,
        target_class: ClassHeader,
        implemented_by: "UserType",
        request=None,
    ) -> ClassHeaderEnrollment | None:
        """Implement an approved level skip by enrolling student in target class.

        Args:
            skip_request: Approved skip request
            target_class: Class at the target level
            implemented_by: Staff member implementing the skip
            request: HTTP request for audit trail

        Returns:
            Created enrollment or None if failed
        """
        if skip_request.status != LanguageLevelSkipRequest.RequestStatus.APPROVED:
            return None

        try:
            # Create enrollment in target class
            enrollment = ClassHeaderEnrollment.objects.create(
                student=skip_request.student,
                class_header=target_class,
                enrolled_by=implemented_by,
                status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
                notes=f"Level skip implementation: {skip_request.current_level} → {skip_request.target_level}",
            )

            # Mark skip request as implemented
            skip_request.mark_implemented(implemented_by, enrollment)

            # Log the implementation
            SystemAuditLog.log_override(
                action_type=SystemAuditLog.ActionType.LANGUAGE_LEVEL_SKIP,
                performed_by=implemented_by,
                target_app="enrollment",
                target_model="ClassHeaderEnrollment",
                target_object_id=str(enrollment.id),
                override_reason=f"Level skip implementation: {skip_request.reason_category}",
                original_restriction="Normal enrollment progression",
                override_details={
                    "skip_request_id": skip_request.id,
                    "student_id": skip_request.student.id,
                    "student_number": skip_request.student.student_id,
                    "from_level": skip_request.current_level,
                    "to_level": skip_request.target_level,
                    "target_class_id": target_class.id,
                    "levels_skipped": skip_request.levels_skipped,
                },
                request=request,
            )

            return enrollment

        except Exception:
            return None

    @staticmethod
    def get_pending_skip_requests(
        program: str | None = None,
    ) -> list[LanguageLevelSkipRequest]:
        """Get pending level skip requests, optionally filtered by program."""
        queryset = (
            LanguageLevelSkipRequest.objects.filter(status=LanguageLevelSkipRequest.RequestStatus.PENDING)
            .select_related("student", "student__person", "requested_by")
            .order_by("created_at")
        )

        if program:
            queryset = queryset.filter(program=program)

        return list(queryset)

    @staticmethod
    def get_student_skip_history(
        student: StudentProfile,
    ) -> list[LanguageLevelSkipRequest]:
        """Get all level skip requests for a specific student."""
        return list(
            LanguageLevelSkipRequest.objects.filter(student=student)
            .select_related(
                "requested_by", "reviewed_by", "implemented_by", "new_enrollment", "new_enrollment__class_header"
            )
            .order_by("-created_at")
        )

    @staticmethod
    def validate_level_skip(current_level: str, target_level: str, program: str) -> dict[str, Any]:
        """Validate that a level skip is theoretically possible.

        Returns:
            Dict with 'valid' boolean and 'message' explaining validation result
        """
        try:
            # Parse levels
            current_level_obj = None
            target_level_obj = None

            current_num = LanguageLevelSkipService._extract_level_num(current_level)
            target_num = LanguageLevelSkipService._extract_level_num(target_level)

            if current_num is not None:
                current_level_obj = LanguageLevel.get_level_by_program_and_num(program, current_num)
            if target_num is not None:
                target_level_obj = LanguageLevel.get_level_by_program_and_num(program, target_num)

            if not current_level_obj:
                return {
                    "valid": False,
                    "message": f"Invalid current level: {current_level}",
                }

            if not target_level_obj:
                return {
                    "valid": False,
                    "message": f"Invalid target level: {target_level}",
                }

            if target_level_obj.level_num <= current_level_obj.level_num:
                return {
                    "valid": False,
                    "message": "Target level must be higher than current level",
                }

            levels_skipped = target_level_obj.level_num - current_level_obj.level_num
            if levels_skipped > MAX_LEVEL_SKIP:
                return {
                    "valid": False,
                    "message": f"Cannot skip more than {MAX_LEVEL_SKIP} levels (requested: {levels_skipped})",
                }

            return {
                "valid": True,
                "message": f"Valid skip of {levels_skipped} level(s)",
                "levels_skipped": levels_skipped,
            }

        except Exception as e:
            return {"valid": False, "message": f"Validation error: {e!s}"}
