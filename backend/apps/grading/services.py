"""Grading services for calculation and management following clean architecture.

This module provides services for:
- Grade calculations with proper rounding and validation
- GPA calculations limited to current major requirements
- Grade conversions between numeric and letter grades
- Automated grade processing and notifications
- Grade change auditing and history management

Key architectural decisions:
- Business logic separated from models and views
- Type-safe operations with comprehensive error handling
- Atomic operations for grade changes with full audit trails
- Configurable calculation rules for different grading scales
- Support for bulk operations with performance optimization
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from decimal import ROUND_HALF_UP, Decimal
from functools import lru_cache
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Avg
from django.utils import timezone

from .models import (
    ClassPartGrade,
    ClassSessionGrade,
    GPARecord,
    GradeChangeHistory,
    GradeConversion,
    GradingScale,
)

# Initialize logger
logger = logging.getLogger(__name__)


class GradeCalculationError(Exception):
    """Custom exception for grade calculation errors."""


class GPACalculationError(Exception):
    """Custom exception for GPA calculation errors."""


@contextmanager
def safe_grade_operation(operation_name: str) -> Iterator[None]:
    """Context manager for safe grade operations with logging."""
    try:
        logger.info("Starting grade operation: %s", operation_name)
        yield
        logger.info("Completed grade operation: %s", operation_name)
    except Exception as e:
        logger.error("Failed grade operation: %s - %s", operation_name, str(e))
        raise


class GradeConversionService:
    """Service for converting between numeric scores and letter grades.

    Handles conversions across different grading scales with proper
    validation and error handling.
    """

    @staticmethod
    def get_letter_grade(
        numeric_score: Decimal,
        grading_scale: GradingScale,
    ) -> tuple[str, Decimal]:
        """Convert numeric score to letter grade and GPA points.

        Args:
            numeric_score: The numeric score to convert (0-100)
            grading_scale: The grading scale to use for conversion

        Returns:
            Tuple of (letter_grade, gpa_points)

        Raises:
            GradeCalculationError: If no matching grade conversion found
        """
        if not (0 <= numeric_score <= 100):
            msg = f"Numeric score {numeric_score} must be between 0 and 100"
            raise GradeCalculationError(
                msg,
            )

        conversion = GradeConversion.objects.filter(
            grading_scale=grading_scale,
            min_percentage__lte=numeric_score,
            max_percentage__gte=numeric_score,
        ).first()

        if not conversion:
            msg = f"No grade conversion found for score {numeric_score} in grading scale {grading_scale.name}"
            raise GradeCalculationError(
                msg,
            )

        return conversion.letter_grade, conversion.gpa_points

    @staticmethod
    def get_numeric_range(
        letter_grade: str,
        grading_scale: GradingScale,
    ) -> tuple[Decimal, Decimal]:
        """Get numeric range for a letter grade.

        Args:
            letter_grade: The letter grade to look up
            grading_scale: The grading scale to use

        Returns:
            Tuple of (min_percentage, max_percentage)

        Raises:
            GradeCalculationError: If letter grade not found
        """
        conversion = GradeConversion.objects.filter(
            grading_scale=grading_scale,
            letter_grade=letter_grade,
        ).first()

        if not conversion:
            msg = f"Letter grade {letter_grade} not found in grading scale {grading_scale.name}"
            raise GradeCalculationError(
                msg,
            )

        return conversion.min_percentage, conversion.max_percentage

    @staticmethod
    def validate_grade_data(
        numeric_score: Decimal | None,
        letter_grade: str | None,
        grading_scale: GradingScale,
    ) -> dict[str, Any]:
        """Validate and normalize grade data.

        Args:
            numeric_score: Optional numeric score
            letter_grade: Optional letter grade
            grading_scale: Grading scale for validation

        Returns:
            Dict with normalized grade data

        Raises:
            ValidationError: If grade data is invalid
        """
        if not numeric_score and not letter_grade:
            msg = "Either numeric score or letter grade must be provided"
            raise ValidationError(
                msg,
            )

        result = {}

        if numeric_score is not None:
            try:
                letter, gpa_points = GradeConversionService.get_letter_grade(
                    numeric_score,
                    grading_scale,
                )
                result.update(
                    {
                        "numeric_score": numeric_score,
                        "letter_grade": letter,
                        "gpa_points": gpa_points,
                    },
                )
            except GradeCalculationError as e:
                msg = f"Invalid numeric score: {e}"
                raise ValidationError(msg) from e

        elif letter_grade:
            try:
                min_pct, max_pct = GradeConversionService.get_numeric_range(
                    letter_grade,
                    grading_scale,
                )
                conversion = GradeConversion.objects.get(
                    grading_scale=grading_scale,
                    letter_grade=letter_grade,
                )
                result.update(
                    {
                        "letter_grade": letter_grade,
                        "gpa_points": conversion.gpa_points,
                        # Store midpoint as numeric equivalent
                        "numeric_score": (min_pct + max_pct) / 2,
                    },
                )
            except GradeConversion.DoesNotExist as e:
                msg = f"Invalid letter grade: {letter_grade}"
                raise ValidationError(msg) from e

        return result


class ClassPartGradeService:
    """Service for managing individual class part grades.

    Handles grade entry, updates, and validation with proper
    audit trails and business rule enforcement.
    """

    @staticmethod
    @transaction.atomic
    def create_or_update_grade(
        enrollment,
        class_part,
        numeric_score: Decimal | None = None,
        letter_grade: str | None = None,
        entered_by=None,
        grade_source: str = ClassPartGrade.GradeSource.MANUAL_TEACHER,
        notes: str = "",
        reason: str = "",
    ) -> ClassPartGrade:
        """Create or update a class part grade with full audit trail.

        Args:
            enrollment: ClassHeaderEnrollment instance
            class_part: ClassPart instance
            numeric_score: Optional numeric score (0-100)
            letter_grade: Optional letter grade
            entered_by: User who entered the grade
            grade_source: Source of the grade entry
            notes: Additional notes
            reason: Reason for change (for updates)

        Returns:
            Created or updated ClassPartGrade instance

        Raises:
            ValidationError: If grade data is invalid
        """
        # Get the appropriate grading scale
        grading_scale = ClassPartGradeService._get_grading_scale_for_class(
            enrollment.class_header,
        )

        # Validate and normalize grade data
        grade_data = GradeConversionService.validate_grade_data(
            numeric_score,
            letter_grade,
            grading_scale,
        )

        # Check if grade already exists
        existing_grade = ClassPartGrade.objects.filter(
            enrollment=enrollment,
            class_part=class_part,
        ).first()

        if existing_grade:
            # Update existing grade
            return ClassPartGradeService._update_existing_grade(
                existing_grade,
                grade_data,
                entered_by,
                grade_source,
                notes,
                reason,
            )
        # Create new grade
        return ClassPartGradeService._create_new_grade(
            enrollment,
            class_part,
            grade_data,
            entered_by,
            grade_source,
            notes,
        )

    @staticmethod
    @lru_cache(maxsize=128)
    def _get_grading_scale_for_class_cached(
        course_cycle: str, course_division_name: str, is_language: bool, is_foundation_year: bool
    ) -> GradingScale:
        """Cached version of grading scale determination."""
        # Determine scale type based on course characteristics
        scale_type = None

        # Academic programs (BA/MA) use academic grading scale
        if course_cycle in ["BA", "MA"]:
            scale_type = GradingScale.ScaleType.ACADEMIC

        # Language courses use different scales based on division
        elif course_cycle == "LANGUAGE" or is_language:
            # Check division short name for IEAP programs
            if "IEAP" in course_division_name.upper():
                scale_type = GradingScale.ScaleType.LANGUAGE_IEAP
            else:
                # EHSS, GESL, WKEND use standard language scale
                scale_type = GradingScale.ScaleType.LANGUAGE_STANDARD

        # Foundation year courses typically use language standard scale
        elif is_foundation_year:
            scale_type = GradingScale.ScaleType.LANGUAGE_STANDARD

        # Default to language standard for unclassified courses
        else:
            scale_type = GradingScale.ScaleType.LANGUAGE_STANDARD

        # Get the grading scale
        try:
            return GradingScale.objects.get(scale_type=scale_type, is_active=True)
        except GradingScale.DoesNotExist:
            # Fallback to any active scale
            scale = GradingScale.objects.filter(is_active=True).first()
            if not scale:
                raise GradeCalculationError("No active grading scale found") from None
            return scale

    @staticmethod
    def _get_grading_scale_for_class(class_header) -> GradingScale:
        """Determine the appropriate grading scale for a class based on course characteristics.

        Args:
            class_header: ClassHeader instance

        Returns:
            Appropriate GradingScale instance

        Raises:
            GradeCalculationError: If no appropriate scale found
        """
        course = class_header.course
        division_name = course.division.short_name or course.division.name

        return ClassPartGradeService._get_grading_scale_for_class_cached(
            course.cycle, division_name, course.is_language, course.is_foundation_year
        )

    @staticmethod
    def _create_new_grade(
        enrollment,
        class_part,
        grade_data: dict[str, Any],
        entered_by,
        grade_source: str,
        notes: str,
    ) -> ClassPartGrade:
        """Create a new class part grade."""
        letter_grade = grade_data.get("letter_grade")
        grade = ClassPartGrade.objects.create(
            enrollment=enrollment,
            class_part=class_part,
            numeric_score=grade_data.get("numeric_score"),
            letter_grade=letter_grade if letter_grade is not None else "",
            gpa_points=grade_data.get("gpa_points"),
            grade_source=grade_source,
            entered_by=entered_by,
            notes=notes,
        )

        # Create initial entry history record
        GradeChangeHistory.objects.create(
            class_part_grade=grade,
            change_type=GradeChangeHistory.ChangeType.INITIAL_ENTRY,
            changed_by=entered_by,
            new_numeric_score=grade.numeric_score,
            new_letter_grade=grade.letter_grade,
            new_status=grade.grade_status,
            reason="Initial grade entry",
        )

        return grade

    @staticmethod
    @transaction.atomic
    def _update_existing_grade(
        grade: ClassPartGrade,
        grade_data: dict[str, Any],
        entered_by,
        grade_source: str,
        notes: str,
        reason: str,
    ) -> ClassPartGrade:
        """Update an existing class part grade with audit trail and race condition protection."""
        # Lock the grade record to prevent concurrent modifications
        locked_grade = ClassPartGrade.objects.select_for_update().get(id=grade.id)  # type: ignore[attr-defined]

        # Store previous values for audit trail
        previous_numeric = locked_grade.numeric_score
        previous_letter = locked_grade.letter_grade
        previous_status = locked_grade.grade_status

        # Update grade data
        locked_grade.numeric_score = grade_data.get("numeric_score")
        letter_grade = grade_data.get("letter_grade")
        locked_grade.letter_grade = letter_grade if letter_grade is not None else ""
        locked_grade.gpa_points = grade_data.get("gpa_points")
        locked_grade.grade_source = grade_source
        locked_grade.entered_by = entered_by
        locked_grade.entered_at = timezone.now()
        locked_grade.notes = notes
        locked_grade.save()

        # Create change history record
        GradeChangeHistory.objects.create(
            class_part_grade=locked_grade,
            change_type=GradeChangeHistory.ChangeType.CORRECTION,
            changed_by=entered_by,
            previous_numeric_score=previous_numeric,
            previous_letter_grade=previous_letter,
            previous_status=previous_status,
            new_numeric_score=locked_grade.numeric_score,
            new_letter_grade=locked_grade.letter_grade,
            new_status=locked_grade.grade_status,
            reason=reason or "Grade correction",
        )

        return locked_grade

    @staticmethod
    def change_grade_status(
        grade: ClassPartGrade,
        new_status: str,
        changed_by,
        reason: str = "",
    ) -> ClassPartGrade:
        """Change the status of a grade with audit trail.

        Args:
            grade: ClassPartGrade to update
            new_status: New status value
            changed_by: User making the change
            reason: Reason for status change

        Returns:
            Updated ClassPartGrade instance
        """
        if grade.grade_status == new_status:
            return grade

        previous_status = grade.grade_status
        grade.grade_status = new_status

        # Handle approval fields
        if new_status == ClassPartGrade.GradeStatus.APPROVED:
            grade.approved_by = changed_by
            grade.approved_at = timezone.now()

        grade.save()

        # Create audit record
        GradeChangeHistory.objects.create(
            class_part_grade=grade,
            change_type=GradeChangeHistory.ChangeType.STATUS_CHANGE,
            changed_by=changed_by,
            previous_status=previous_status,
            new_status=new_status,
            reason=reason or f"Status changed to {new_status}",
        )

        return grade


class ClassSessionGradeService:
    """Service for calculating and managing class session grades.

    Calculates weighted averages from class part grades and manages
    session-level grade records.
    """

    @staticmethod
    @transaction.atomic
    def calculate_session_grade(
        enrollment,
        class_session,
        force_recalculate: bool = False,
    ) -> ClassSessionGrade | None:
        """Calculate grade for a class session from component grades.

        Args:
            enrollment: ClassHeaderEnrollment instance
            class_session: ClassSession instance
            force_recalculate: Whether to recalculate existing grades

        Returns:
            ClassSessionGrade instance or None if no grades available
        """
        # Check if session grade already exists
        existing_grade = ClassSessionGrade.objects.filter(
            enrollment=enrollment,
            class_session=class_session,
        ).first()

        if existing_grade and not force_recalculate:
            return existing_grade

        # Get all class part grades for this session
        part_grades = (
            ClassPartGrade.objects.filter(
                enrollment=enrollment,
                class_part__class_session=class_session,
                grade_status__in=[
                    ClassPartGrade.GradeStatus.SUBMITTED,
                    ClassPartGrade.GradeStatus.APPROVED,
                    ClassPartGrade.GradeStatus.FINALIZED,
                ],
            )
            .select_related("class_part", "class_part__class_session", "enrollment", "enrollment__student")
            .order_by("class_part__display_order")
        )

        if not part_grades.exists():
            return None

        # Calculate weighted average
        total_weighted_score = Decimal("0")
        total_weight = Decimal("0")
        calculation_details = []

        for part_grade in part_grades:
            weight = part_grade.class_part.grade_weight or Decimal("100")
            score = part_grade.numeric_score or Decimal("0")

            weighted_score = score * weight / 100
            total_weighted_score += weighted_score
            total_weight += weight

            calculation_details.append(
                {
                    "class_part": part_grade.class_part.name,
                    "score": float(score),
                    "weight": float(weight),
                    "weighted_score": float(weighted_score),
                },
            )

        if total_weight == 0:
            return None

        # Calculate final score
        calculated_score = (total_weighted_score / total_weight * 100).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )

        # Get grading scale and convert to letter grade
        grading_scale = ClassPartGradeService._get_grading_scale_for_class(
            enrollment.class_header,
        )

        try:
            letter_grade, gpa_points = GradeConversionService.get_letter_grade(
                calculated_score,
                grading_scale,
            )
        except GradeCalculationError:
            # Handle edge cases - use lowest grade
            letter_grade = "F"
            gpa_points = Decimal("0.00")

        # Create or update session grade
        session_grade, _created = ClassSessionGrade.objects.update_or_create(
            enrollment=enrollment,
            class_session=class_session,
            defaults={
                "calculated_score": calculated_score,
                "letter_grade": letter_grade,
                "gpa_points": gpa_points,
                "calculated_at": timezone.now(),
                "calculation_details": {
                    "components": calculation_details,
                    "total_weight": float(total_weight),
                    "final_score": float(calculated_score),
                    "grading_scale": grading_scale.name,
                },
            },
        )

        return session_grade


class GPACalculationService:
    """Service for calculating student GPA records.

    Handles both term and cumulative GPA calculations limited to
    courses in the student's current major requirements.
    """

    @staticmethod
    @transaction.atomic
    def calculate_term_gpa(
        student,
        term,
        major,
        force_recalculate: bool = False,
    ) -> GPARecord | None:
        """Calculate term GPA for a student's major.

        Args:
            student: StudentProfile instance
            term: Term instance
            major: Major instance
            force_recalculate: Whether to recalculate existing GPA

        Returns:
            GPARecord instance or None if no qualifying grades
        """
        # Check if GPA already exists
        existing_gpa = GPARecord.objects.filter(
            student=student,
            term=term,
            major=major,
            gpa_type=GPARecord.GPAType.TERM,
        ).first()

        if existing_gpa and not force_recalculate:
            return existing_gpa

        # Get qualifying grades for the term
        # Future enhancement: Implement logic to filter by major requirements

        enrollments = student.class_header_enrollments.filter(
            class_header__term=term,
            status="ENROLLED",  # Note: Use proper enrollment status from constants
        ).select_related("class_header", "class_header__course", "class_header__term")

        if not enrollments.exists():
            return None

        total_quality_points = Decimal("0")
        total_credit_hours_attempted = Decimal("0")
        total_credit_hours_earned = Decimal("0")
        course_details = []

        for enrollment in enrollments:
            # Get final grade for this enrollment
            # This would typically be the class header grade

            session_grades = ClassSessionGrade.objects.filter(enrollment=enrollment).select_related(
                "class_session", "enrollment"
            )

            if not session_grades.exists():
                continue

            # Calculate overall grade from session grades
            # Future enhancement: Implement proper weighting based on session structure
            avg_gpa_points = session_grades.aggregate(avg_gpa=Avg("gpa_points"))["avg_gpa"] or Decimal("0")

            # Get credit hours for the course
            credit_hours = Decimal(str(enrollment.class_header.course.credits))

            quality_points = avg_gpa_points * credit_hours
            total_quality_points += quality_points
            total_credit_hours_attempted += credit_hours

            # Count as earned if passing grade
            if avg_gpa_points >= Decimal("1.0"):  # Note: Use proper passing threshold from configuration
                total_credit_hours_earned += credit_hours

            course_details.append(
                {
                    "course": str(enrollment.class_header),
                    "credit_hours": float(credit_hours),
                    "gpa_points": float(avg_gpa_points),
                    "quality_points": float(quality_points),
                },
            )

        if total_credit_hours_attempted == 0:
            return None

        # Calculate GPA
        gpa_value = (total_quality_points / total_credit_hours_attempted).quantize(
            Decimal("0.001"),
            rounding=ROUND_HALF_UP,
        )

        # Create or update GPA record
        gpa_record, _created = GPARecord.objects.update_or_create(
            student=student,
            term=term,
            major=major,
            gpa_type=GPARecord.GPAType.TERM,
            defaults={
                "gpa_value": gpa_value,
                "quality_points": total_quality_points,
                "credit_hours_attempted": total_credit_hours_attempted,
                "credit_hours_earned": total_credit_hours_earned,
                "calculated_at": timezone.now(),
                "calculation_details": {
                    "courses": course_details,
                    "calculation_method": "weighted_average",
                },
            },
        )

        return gpa_record

    @staticmethod
    @transaction.atomic
    def calculate_cumulative_gpa(
        student,
        current_term,
        major,
        force_recalculate: bool = False,
    ) -> GPARecord | None:
        """Calculate cumulative GPA for a student's major.

        Args:
            student: StudentProfile instance
            current_term: Current term for the calculation
            major: Major instance
            force_recalculate: Whether to recalculate existing GPA

        Returns:
            GPARecord instance or None if no qualifying grades
        """
        # Check if cumulative GPA already exists
        existing_gpa = GPARecord.objects.filter(
            student=student,
            term=current_term,
            major=major,
            gpa_type=GPARecord.GPAType.CUMULATIVE,
        ).first()

        if existing_gpa and not force_recalculate:
            return existing_gpa

        # Get all term GPAs for this major up to current term
        term_gpas = (
            GPARecord.objects.filter(
                student=student,
                major=major,
                gpa_type=GPARecord.GPAType.TERM,
                term__end_date__lte=current_term.end_date,
            )
            .select_related("term", "student", "major")
            .order_by("term__start_date")
        )

        if not term_gpas.exists():
            return None

        total_quality_points = Decimal("0")
        total_credit_hours_attempted = Decimal("0")
        total_credit_hours_earned = Decimal("0")
        term_details = []

        for term_gpa in term_gpas:
            total_quality_points += term_gpa.quality_points
            total_credit_hours_attempted += term_gpa.credit_hours_attempted
            total_credit_hours_earned += term_gpa.credit_hours_earned

            term_details.append(
                {
                    "term": str(term_gpa.term),
                    "term_gpa": float(term_gpa.gpa_value),
                    "quality_points": float(term_gpa.quality_points),
                    "credit_hours_attempted": float(term_gpa.credit_hours_attempted),
                    "credit_hours_earned": float(term_gpa.credit_hours_earned),
                },
            )

        if total_credit_hours_attempted == 0:
            return None

        # Calculate cumulative GPA
        cumulative_gpa = (total_quality_points / total_credit_hours_attempted).quantize(
            Decimal("0.001"),
            rounding=ROUND_HALF_UP,
        )

        # Create or update cumulative GPA record
        gpa_record, _created = GPARecord.objects.update_or_create(
            student=student,
            term=current_term,
            major=major,
            gpa_type=GPARecord.GPAType.CUMULATIVE,
            defaults={
                "gpa_value": cumulative_gpa,
                "quality_points": total_quality_points,
                "credit_hours_attempted": total_credit_hours_attempted,
                "credit_hours_earned": total_credit_hours_earned,
                "calculated_at": timezone.now(),
                "calculation_details": {
                    "terms": term_details,
                    "calculation_method": "cumulative_weighted",
                },
            },
        )

        return gpa_record


class BulkGradeService:
    """Service for bulk grade operations.

    Handles batch processing of grades with performance optimization
    and comprehensive error handling.
    """

    @staticmethod
    @transaction.atomic
    def bulk_import_grades(
        grade_data: list[dict[str, Any]],
        imported_by,
        grade_source: str = ClassPartGrade.GradeSource.MOODLE_IMPORT,
    ) -> dict[str, Any]:
        """Import grades in bulk with validation and error handling.

        Args:
            grade_data: List of grade dictionaries with enrollment/part info
            imported_by: User performing the import
            grade_source: Source of the imported grades

        Returns:
            Dict with import results and any errors
        """
        results: dict[str, Any] = {
            "success_count": 0,
            "error_count": 0,
            "errors": [],
            "created_grades": [],
        }

        for i, data in enumerate(grade_data):
            try:
                # Extract required fields
                enrollment_id = data.get("enrollment_id")
                class_part_id = data.get("class_part_id")
                numeric_score = data.get("numeric_score")
                letter_grade = data.get("letter_grade")
                notes = data.get("notes", "")

                # Validate required fields
                if not enrollment_id or not class_part_id:
                    msg = "Missing enrollment_id or class_part_id"
                    raise ValidationError(msg)

                # Get objects
                from apps.enrollment.models import ClassHeaderEnrollment
                from apps.scheduling.models import ClassPart

                enrollment = ClassHeaderEnrollment.objects.get(id=enrollment_id)
                class_part = ClassPart.objects.get(id=class_part_id)

                # Create or update grade
                grade = ClassPartGradeService.create_or_update_grade(
                    enrollment=enrollment,
                    class_part=class_part,
                    numeric_score=(Decimal(str(numeric_score)) if numeric_score else None),
                    letter_grade=letter_grade,
                    entered_by=imported_by,
                    grade_source=grade_source,
                    notes=notes,
                    reason="Bulk import",
                )

                results["created_grades"].append(grade.id)  # type: ignore[attr-defined]
                results["success_count"] += 1

            except Exception as e:
                results["error_count"] += 1
                results["errors"].append(
                    {
                        "row": i + 1,
                        "data": data,
                        "error": str(e),
                    },
                )

        return results

    @staticmethod
    @transaction.atomic
    def bulk_create_grades(
        grade_entries: list[dict[str, Any]],
        batch_size: int = 100,
    ) -> dict[str, Any]:
        """Create multiple grades efficiently using bulk operations.

        Args:
            grade_entries: List of grade data dictionaries
            batch_size: Number of grades to process in each batch

        Returns:
            Results dictionary with success/error counts
        """
        results: dict[str, Any] = {
            "success_count": 0,
            "error_count": 0,
            "errors": [],
            "created_grades": [],
        }

        grades_to_create = []
        history_records = []

        with safe_grade_operation("bulk_create_grades"):
            for i in range(0, len(grade_entries), batch_size):
                batch = grade_entries[i : i + batch_size]

                for entry_data in batch:
                    try:
                        # Validate grade data first
                        enrollment = entry_data["enrollment"]
                        class_part = entry_data["class_part"]
                        grading_scale = ClassPartGradeService._get_grading_scale_for_class(enrollment.class_header)

                        grade_data = GradeConversionService.validate_grade_data(
                            entry_data.get("numeric_score"),
                            entry_data.get("letter_grade"),
                            grading_scale,
                        )

                        # Create grade instance
                        letter_grade = grade_data.get("letter_grade")
                        grade = ClassPartGrade(
                            enrollment=enrollment,
                            class_part=class_part,
                            numeric_score=grade_data.get("numeric_score"),
                            letter_grade=letter_grade if letter_grade is not None else "",
                            gpa_points=grade_data.get("gpa_points"),
                            grade_source=entry_data.get("grade_source", ClassPartGrade.GradeSource.MANUAL_TEACHER),
                            entered_by=entry_data["entered_by"],
                            notes=entry_data.get("notes", ""),
                        )

                        grades_to_create.append(grade)

                    except Exception as e:
                        results["error_count"] += 1
                        results["errors"].append(
                            {
                                "index": i,
                                "error": str(e),
                                "data": entry_data,
                            }
                        )

                # Bulk create grades
                if grades_to_create:
                    created_grades = ClassPartGrade.objects.bulk_create(grades_to_create)
                    results["created_grades"].extend([g.id for g in created_grades])
                    results["success_count"] += len(created_grades)

                    # Create history records for bulk created grades
                    for grade in created_grades:
                        history_records.append(
                            GradeChangeHistory(
                                class_part_grade=grade,
                                change_type=GradeChangeHistory.ChangeType.INITIAL_ENTRY,
                                changed_by=grade.entered_by,
                                new_numeric_score=grade.numeric_score,
                                new_letter_grade=grade.letter_grade,
                                new_status=grade.grade_status,
                                reason="Bulk initial entry",
                            )
                        )

                    grades_to_create.clear()

            # Bulk create history records
            if history_records:
                GradeChangeHistory.objects.bulk_create(history_records)

        return results
