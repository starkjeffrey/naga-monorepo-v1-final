"""Scheduling services for business logic and workflows.

This module provides business logic services for scheduling operations including:
- Class creation and management
- Room conflict resolution
- Reading class tier management
- Test period reset automation
- Bulk scheduling operations

All services follow clean architecture principles and avoid circular dependencies.
"""

import logging
from typing import cast

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from .models import (
    ClassHeader,
    ClassPart,
    CombinedClassInstance,
    CombinedCourseTemplate,
    ReadingClass,
    TestPeriodReset,
)

User = get_user_model()
logger = logging.getLogger(__name__)


class CombinedClassAutomationService:
    """Service for automated course combination management."""

    @classmethod
    @transaction.atomic
    def handle_class_header_creation(cls, class_header: ClassHeader) -> CombinedClassInstance | None:
        """Handle automatic combination creation when a ClassHeader is created.

        Args:
            class_header: Newly created ClassHeader instance

        Returns:
            CombinedClassInstance if a combination was created/joined, None otherwise
        """

        try:
            logger.info(f"Processing class header {class_header} for course combination")

            active_templates = CombinedCourseTemplate.objects.filter(
                status=CombinedCourseTemplate.StatusChoices.ACTIVE,
                courses=class_header.course,
                is_deleted=False,
            )

            if not active_templates.exists():
                logger.debug(f"No active combination templates found for course {class_header.course}")
                return None

            template = active_templates.first()
            if not template:
                return None

            existing_instance = CombinedClassInstance.objects.filter(
                template=template,
                term=class_header.term,
                is_deleted=False,
            ).first()

            if existing_instance:
                # Join existing instance
                logger.info(f"Joining existing combined instance {existing_instance} for class {class_header}")
                class_header.combined_class_instance = existing_instance
                class_header.save(update_fields=["combined_class_instance"])
                return existing_instance

            # Create new instance
            logger.info(f"Creating new combined instance for template {template} and class {class_header}")
            instance = cls._create_combined_instance(template, class_header.term, class_header.section_id)
            class_header.combined_class_instance = instance
            class_header.save(update_fields=["combined_class_instance"])

            return instance

        except Exception as e:
            logger.error(f"Error processing class header {class_header} for combination: {e}")
            return None

    @classmethod
    def _create_combined_instance(
        cls,
        template: CombinedCourseTemplate,
        term,
        section_id: str,
    ) -> CombinedClassInstance:
        """Create a new CombinedClassInstance."""
        instance = CombinedClassInstance.objects.create(
            template=template,
            term=term,
            section_id=section_id,
            status=CombinedClassInstance.StatusChoices.DRAFT,
            auto_created=True,
        )
        return instance

    @classmethod
    @transaction.atomic
    def apply_shared_resources(cls, instance: CombinedClassInstance) -> dict:
        """Apply shared teacher and room from instance to all member ClassParts.

        Args:
            instance: CombinedClassInstance with shared resources

        Returns:
            Dict with update statistics
        """
        if not (instance.primary_teacher or instance.primary_room):
            return {"updated_parts": 0, "message": "No shared resources to apply"}

        updated_count = instance.apply_shared_resources_to_parts()

        return {
            "updated_parts": updated_count,
            "message": f"Applied shared resources to {updated_count} class parts",
        }

    @classmethod
    def get_combination_opportunities(cls, term) -> list[dict]:
        """Find courses that could be combined based on active templates.

        Args:
            term: Term to analyze

        Returns:
            List of combination opportunities with details
        """
        opportunities = []

        for template in CombinedCourseTemplate.objects.filter(
            status=CombinedCourseTemplate.StatusChoices.ACTIVE,
            is_deleted=False,
        ):
            scheduled_courses = ClassHeader.objects.filter(
                term=term,
                course__in=template.courses.all(),
                is_deleted=False,
            ).select_related("course")

            scheduled_course_codes = list(scheduled_courses.values_list("course__code", flat=True))
            missing_courses = template.courses.exclude(id__in=scheduled_courses.values_list("course", flat=True))
            missing_course_codes = list(missing_courses.values_list("code", flat=True))

            existing_instance = CombinedClassInstance.objects.filter(
                template=template,
                term=term,
                is_deleted=False,
            ).first()

            opportunities.append(
                {
                    "template": template,
                    "template_name": template.name,
                    "total_courses": template.course_count,
                    "scheduled_courses": scheduled_course_codes,
                    "scheduled_count": len(scheduled_course_codes),
                    "missing_courses": missing_course_codes,
                    "missing_count": len(missing_course_codes),
                    "existing_instance": existing_instance,
                    "can_combine": len(scheduled_course_codes) >= 2,
                    "is_complete": len(missing_course_codes) == 0,
                },
            )

        return opportunities

    @classmethod
    @transaction.atomic
    def create_combination_for_existing_classes(
        cls,
        template: CombinedCourseTemplate,
        term,
        section_id: str = "A",
    ) -> CombinedClassInstance:
        """Create a combination instance for existing ClassHeaders.

        Args:
            template: CombinedCourseTemplate to implement
            term: Academic term
            section_id: Section identifier

        Returns:
            Created CombinedClassInstance
        """
        # Check if instance already exists
        existing_instance = CombinedClassInstance.objects.filter(
            template=template,
            term=term,
            section_id=section_id,
            is_deleted=False,
        ).first()

        if existing_instance:
            return existing_instance

        # Create new instance
        instance = CombinedClassInstance.objects.create(
            template=template,
            term=term,
            section_id=section_id,
            status=CombinedClassInstance.StatusChoices.DRAFT,
            auto_created=False,  # Manually created
        )

        existing_headers = ClassHeader.objects.filter(
            term=term,
            course__in=template.courses.all(),
            combined_class_instance__isnull=True,  # Not already combined
            is_deleted=False,
        )

        # Link them to the instance
        for header in existing_headers:
            header.combined_class_instance = instance
            header.save(update_fields=["combined_class_instance"])

        return instance

    @classmethod
    def get_instance_status_report(cls, instance: CombinedClassInstance) -> dict:
        """Generate a comprehensive status report for a combined class instance.

        Args:
            instance: CombinedClassInstance to analyze

        Returns:
            Dict with status information
        """
        member_headers = instance.member_class_headers
        template_courses = instance.template.courses.all()  # type: ignore[attr-defined]

        # Calculate completeness
        scheduled_courses = set(member_headers.values_list("course_id", flat=True))
        template_course_ids = set(template_courses.values_list("id", flat=True))
        missing_course_ids = template_course_ids - scheduled_courses

        # Get missing course details
        missing_courses = template_courses.filter(id__in=missing_course_ids)

        # Calculate enrollment statistics
        enrollments = [header.enrollment_count for header in member_headers]
        total_enrollment = sum(enrollments)
        avg_enrollment = total_enrollment / len(enrollments) if enrollments else 0

        # Check resource assignments
        has_shared_teacher = instance.primary_teacher is not None
        has_shared_room = instance.primary_room is not None

        # Check if all parts have consistent resources
        all_parts_have_teacher = True
        all_parts_have_room = True
        inconsistent_teachers = False
        inconsistent_rooms = False

        for header in member_headers:
            for session in header.class_sessions.all():
                for part in session.class_parts.all():
                    if not part.teacher:
                        all_parts_have_teacher = False
                    elif has_shared_teacher and part.teacher != instance.primary_teacher:
                        inconsistent_teachers = True

                    if not part.room:
                        all_parts_have_room = False
                    elif has_shared_room and part.room != instance.primary_room:
                        inconsistent_rooms = True

        return {
            "instance": instance,
            "template_name": instance.template.name,  # type: ignore[attr-defined]
            "is_complete": len(missing_course_ids) == 0,
            "member_count": member_headers.count(),
            "total_courses_needed": template_courses.count(),
            "missing_courses": list(missing_courses.values_list("code", flat=True)),
            "total_enrollment": total_enrollment,
            "average_enrollment": round(avg_enrollment, 1),
            "has_shared_teacher": has_shared_teacher,
            "has_shared_room": has_shared_room,
            "all_parts_have_teacher": all_parts_have_teacher,
            "all_parts_have_room": all_parts_have_room,
            "needs_resource_sync": inconsistent_teachers or inconsistent_rooms,
            "inconsistent_teachers": inconsistent_teachers,
            "inconsistent_rooms": inconsistent_rooms,
        }


class SchedulingService:
    """Service for core scheduling operations and class management."""

    @classmethod
    @transaction.atomic
    def create_paired_classes(
        cls,
        course1,
        course2,
        term,
        section_id: str,
        time_of_day: str,
        **kwargs,
    ) -> tuple[ClassHeader, ClassHeader]:
        """Create a pair of classes with symmetric pairing.

        Args:
            course1: First course to schedule
            course2: Second course to schedule
            term: Academic term
            section_id: Section identifier
            time_of_day: Time of day for both classes
            **kwargs: Additional class header fields

        Returns:
            Tuple of (class1, class2) ClassHeader instances
        """
        # Create both classes
        class1 = ClassHeader.objects.create(
            course=course1,
            term=term,
            section_id=section_id,
            time_of_day=time_of_day,
            is_paired=True,
            **kwargs,
        )

        class2 = ClassHeader.objects.create(
            course=course2,
            term=term,
            section_id=section_id,
            time_of_day=time_of_day,
            is_paired=True,
            paired_with=class1,
            **kwargs,
        )

        # Set up symmetric pairing
        class1.paired_with = class2
        class1.save(update_fields=["paired_with"])

        return class1, class2

    @classmethod
    def get_room_availability(cls, room, start_time, end_time, meeting_days: str, exclude_part=None):
        """Check room availability for given time slots.

        Args:
            room: Room instance
            start_time: Start time
            end_time: End time
            meeting_days: Comma-separated meeting days
            exclude_part: ClassPart to exclude from conflict check

        Returns:
            Boolean indicating if room is available
        """
        from django.db.models import Q

        from .models import ClassPart

        if not meeting_days:
            return True

        my_days = {day.strip().upper() for day in meeting_days.split(",")}

        # Build query for day overlaps
        day_queries = Q()
        for day in my_days:
            day_queries |= Q(meeting_days__icontains=day)

        # Check for conflicts
        conflicts = ClassPart.objects.filter(
            room=room,
            start_time__lt=end_time,
            end_time__gt=start_time,
        ).filter(day_queries)

        if exclude_part:
            conflicts = conflicts.exclude(pk=exclude_part.pk)

        # Verify actual day overlaps
        for part in conflicts:
            if part.meeting_days:
                other_days = {day.strip().upper() for day in part.meeting_days.split(",")}
                if my_days & other_days:
                    return False

        return True


class ReadingClassService:
    """Service for reading class tier management and conversions."""

    @classmethod
    def bulk_update_tiers(cls, reading_classes_queryset) -> int:
        """Efficiently update tiers for multiple reading classes.

        Args:
            reading_classes_queryset: QuerySet of ReadingClass instances

        Returns:
            Number of classes updated
        """
        updated_count = 0

        # Process in batches to avoid memory issues
        for reading_class in reading_classes_queryset.select_related("class_header"):
            if reading_class.update_tier():
                updated_count += 1

        return updated_count

    @classmethod
    def bulk_convert_to_standard(cls, reading_classes_queryset, user=None) -> int:
        """Efficiently convert eligible reading classes to standard.

        Args:
            reading_classes_queryset: QuerySet of ReadingClass instances
            user: User performing the conversion

        Returns:
            Number of classes converted
        """
        converted_count = 0
        eligible_classes = []

        # Identify eligible classes
        for reading_class in reading_classes_queryset.select_related("class_header"):
            if reading_class.can_convert_to_standard:
                eligible_classes.append(reading_class)

        # Bulk update class headers
        if eligible_classes:
            with transaction.atomic():
                class_header_ids = [rc.class_header.id for rc in eligible_classes]
                ClassHeader.objects.filter(id__in=class_header_ids).update(class_type=ClassHeader.ClassType.STANDARD)

                # Update reading class statuses
                reading_class_ids = [rc.id for rc in eligible_classes]
                ReadingClass.objects.filter(id__in=reading_class_ids).update(
                    enrollment_status=ReadingClass.EnrollmentStatus.CONVERTED,
                )

                converted_count = len(eligible_classes)

        return converted_count


class TestPeriodResetService:
    """Service for test period reset automation and management."""

    @classmethod
    def get_current_term(cls):
        """Get the current academic term based on system logic.

        Returns:
            Current Term instance or None if no current term

        Note: This is a placeholder implementation that needs business logic clarification.
        """
        from apps.curriculum.models import Term

        """
        Business Logic for Current Term:
        1. Primary: Term where current date falls within start_date and end_date
        2. Fallback: Most recently started term if no active term found
        3. Emergency fallback: Latest term by start_date
        """
        today = timezone.now().date()

        # First, try to find active term (current date within term dates)
        active_term = Term.objects.filter(start_date__lte=today, end_date__gte=today).first()

        if active_term:
            return active_term

        # Fallback: Most recently started term
        return Term.objects.filter(start_date__lte=today).order_by("-start_date").first()

    @classmethod
    def get_next_term_of_same_type(cls, current_term):
        """Get the next term of the same type after the given term.

        Args:
            current_term: Current Term instance

        Returns:
            Next Term instance of same type, or None

        Business Logic:
        - Finds next term with same term_type (ENG_A -> ENG_A, BA -> BA, etc.)
        - Uses suggest_target_term which enforces business rules
        """
        from apps.curriculum.models import Term

        if not current_term:
            return None

        return Term.suggest_target_term(current_term)

    @classmethod
    @transaction.atomic
    def duplicate_resets_to_next_term(cls, reset_queryset, target_term=None) -> int:
        """Duplicate test period resets to the next term with proper date adjustment.

        Args:
            reset_queryset: QuerySet of TestPeriodReset instances
            target_term: Target term (auto-detected if None)

        Returns:
            Number of resets duplicated
        """
        from datetime import timedelta

        duplicated_count = 0

        for reset in reset_queryset.select_related("term"):
            if not target_term:
                target_term = cls.get_next_term_of_same_type(reset.term)

            if not target_term:
                continue  # Skip if no next term available

            # Calculate date adjustment
            term_length_days = (reset.term.end_date - reset.term.start_date).days
            target_term_length = (target_term.end_date - target_term.start_date).days

            # Proportional date adjustment
            days_from_start = (reset.reset_date - reset.term.start_date).days
            proportional_position = days_from_start / term_length_days if term_length_days > 0 else 0

            new_reset_date = target_term.start_date + timedelta(days=int(proportional_position * target_term_length))

            # Ensure the date is within the target term
            if new_reset_date > target_term.end_date:
                new_reset_date = target_term.end_date - timedelta(days=1)
            elif new_reset_date < target_term.start_date:
                new_reset_date = target_term.start_date

            try:
                TestPeriodReset.objects.create(
                    term=target_term,
                    test_type=reset.test_type,
                    reset_date=new_reset_date,
                    applies_to_all_language_classes=reset.applies_to_all_language_classes,
                    notes=f"Duplicated from {reset.term}: {reset.notes}",
                )
                duplicated_count += 1
            except Exception:
                # Skip duplicates or validation errors
                continue

        return duplicated_count

    @classmethod
    @transaction.atomic
    def create_standard_test_schedule(cls, terms_queryset) -> int:
        """Create standard midterm and final schedules for given terms.

        Args:
            terms_queryset: QuerySet of Term instances

        Returns:
            Number of resets created
        """
        from datetime import timedelta

        created_count = 0

        for term in terms_queryset:
            try:
                # Create standard midterm (halfway through term)
                term_duration = term.end_date - term.start_date
                midterm_date = term.start_date + (term_duration / 2)

                TestPeriodReset.objects.get_or_create(
                    term=term,
                    test_type=TestPeriodReset.TestType.MIDTERM,
                    applies_to_all_language_classes=True,
                    defaults={
                        "reset_date": midterm_date,
                        "notes": "Auto-generated standard midterm reset",
                    },
                )
                created_count += 1

                # Create standard final (2 weeks before term end)
                final_date = term.end_date - timedelta(days=14)
                TestPeriodReset.objects.get_or_create(
                    term=term,
                    test_type=TestPeriodReset.TestType.FINAL,
                    applies_to_all_language_classes=True,
                    defaults={
                        "reset_date": final_date,
                        "notes": "Auto-generated standard final reset",
                    },
                )
                created_count += 1

            except Exception:
                # Skip validation errors
                continue

        return created_count


class SchedulingPermissionService:
    """Service for checking scheduling-related permissions."""

    @classmethod
    def can_manage_reading_classes(cls, user) -> bool:
        """Check if user can manage reading class operations."""
        if not user or not hasattr(user, "is_active") or not user.is_active:
            return False
        result = (
            user.has_perm("scheduling.change_readingclass")
            or user.has_perm("scheduling.can_manage_reading_classes")
            or user.is_superuser
        )
        return bool(result)

    @classmethod
    def can_manage_test_resets(cls, user) -> bool:
        """Check if user can manage test period resets."""
        if not user or not hasattr(user, "is_active") or not user.is_active:
            return False
        result = (
            user.has_perm("scheduling.change_testperiodreset")
            or user.has_perm("scheduling.can_manage_test_resets")
            or user.is_superuser
        )
        return bool(result)

    @classmethod
    def can_manage_class_scheduling(cls, user) -> bool:
        """Check if user can perform bulk class scheduling operations."""
        if not user or not hasattr(user, "is_active") or not user.is_active:
            return False
        result = (
            user.has_perm("scheduling.change_classheader")
            or user.has_perm("scheduling.can_manage_class_scheduling")
            or user.is_superuser
        )
        return bool(result)


class ClassSchedulingService:
    """Service for safe class creation and structure management with integrity guarantees.

    This service provides transaction-atomic operations for creating classes with proper
    ClassHeader → ClassSession → ClassPart structure, ensuring the architectural rule
    that ALL ClassParts MUST go through ClassSession is maintained.
    """

    @classmethod
    @transaction.atomic
    def create_class_with_structure(cls, course, term, section_id: str = "A", class_type=None, **kwargs) -> dict:
        """Create a class with proper ClassHeader → ClassSession → ClassPart structure.

        Args:
            course: Course instance to schedule
            term: Term instance for the class
            section_id: Section identifier (default: "A")
            class_type: ClassHeader.ClassType (optional, will be determined)
            **kwargs: Additional ClassHeader fields

        Returns:
            Dict with created objects and statistics:
            {
                'class_header': ClassHeader instance,
                'sessions': [ClassSession instances],
                'parts': [ClassPart instances],
                'is_ieap': bool,
                'session_count': int,
                'part_count': int
            }
        """
        logger.info(f"Creating class with structure: {course.code} {section_id} for {term}")

        # Create ClassHeader
        class_header = ClassHeader.objects.create(
            course=course,
            term=term,
            section_id=section_id,
            class_type=class_type or ClassHeader.ClassType.STANDARD,
            **kwargs,
        )

        # Ensure proper session structure (this will be handled by signals)
        created_sessions, sessions = class_header.ensure_sessions_exist()

        # Ensure each session has parts
        all_parts = []
        for session in sessions:
            session.ensure_parts_exist()
            all_parts.extend(session.class_parts.all())

        # Validate the complete structure
        validation = class_header.validate_session_structure()
        if not validation["valid"]:
            # Log errors but don't fail - structure was created
            for error in validation["errors"]:
                logger.warning(f"Structure validation error for {class_header}: {error}")

        result = {
            "class_header": class_header,
            "sessions": list(sessions),
            "parts": all_parts,
            "is_ieap": class_header.is_ieap_class(),
            "session_count": len(sessions),
            "part_count": len(all_parts),
            "validation": validation,
        }

        logger.info(
            f"Created class {class_header} with {result['session_count']} sessions and {result['part_count']} parts"
        )

        return result

    @classmethod
    @transaction.atomic
    def duplicate_class_structure(
        cls,
        source_class: ClassHeader,
        target_term=None,
        section_id: str | None = None,
        copy_enrollments: bool = False,
        **overrides,
    ) -> dict:
        """Duplicate a class structure to another term or section.

        Args:
            source_class: ClassHeader to duplicate
            target_term: Target term (default: same term)
            section_id: Target section ID (default: auto-generate)
            copy_enrollments: Whether to copy enrollment relationships
            **overrides: Fields to override in the new ClassHeader

        Returns:
            Dict with duplicated objects and mapping information
        """
        if target_term is None:
            target_term = source_class.term

        if section_id is None:
            # Auto-generate next available section
            existing_sections = ClassHeader.objects.filter(course=source_class.course, term=target_term).values_list(
                "section_id", flat=True
            )

            # Find next available letter
            for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                if letter not in existing_sections:
                    section_id = letter
                    break
            else:
                section_id = f"Z{len(existing_sections)}"

        logger.info(f"Duplicating {source_class} to {target_term} section {section_id}")

        # Prepare new class data
        new_class_data = {
            "course": source_class.course,
            "term": target_term,
            "section_id": section_id,
            "class_type": source_class.class_type,
            "time_of_day": source_class.time_of_day,
            "max_enrollment": source_class.max_enrollment,
            "notes": f"Duplicated from {source_class}",
        }
        new_class_data.update(overrides)

        # Create new class with structure
        result = cls.create_class_with_structure(**new_class_data)
        new_class = result["class_header"]

        # Copy session and part details
        session_mapping = {}
        part_mapping = {}

        for source_session in source_class.class_sessions.all():  # type: ignore[attr-defined]
            # Find corresponding session in new class
            target_session = new_class.class_sessions.filter(session_number=source_session.session_number).first()

            if target_session:
                # Update session details
                target_session.session_name = source_session.session_name
                target_session.grade_weight = source_session.grade_weight
                target_session.save()
                session_mapping[source_session.id] = target_session

                # Copy parts structure
                for source_part in source_session.class_parts.all():
                    target_parts = list(target_session.class_parts.all())

                    if target_parts:
                        target_part = target_parts[0]  # Use first part

                        # Copy part details
                        target_part.class_part_code = source_part.class_part_code
                        target_part.class_part_type = source_part.class_part_type
                        target_part.name = source_part.name
                        target_part.teacher = source_part.teacher
                        target_part.room = source_part.room
                        target_part.meeting_days = source_part.meeting_days
                        target_part.start_time = source_part.start_time
                        target_part.end_time = source_part.end_time
                        target_part.grade_weight = source_part.grade_weight
                        target_part.save()

                        part_mapping[source_part.id] = target_part

        # Copy enrollments if requested
        copied_enrollments = 0
        if copy_enrollments:
            from apps.enrollment.models import ClassPartEnrollment

            source_enrollments = ClassPartEnrollment.objects.filter(
                class_part__class_session__class_header=source_class
            )

            for enrollment in source_enrollments:
                enrollment_part = cast("ClassPart", enrollment.class_part)
                target_part = part_mapping.get(enrollment_part.id)  # type: ignore[attr-defined]

                if target_part:
                    ClassPartEnrollment.objects.get_or_create(
                        student=enrollment.student,
                        class_part=target_part,
                        defaults={
                            "is_active": enrollment.is_active,
                            "enrollment_date": enrollment.enrollment_date,
                        },
                    )
                    copied_enrollments += 1

        result.update(
            {
                "source_class": source_class,
                "session_mapping": session_mapping,
                "part_mapping": part_mapping,
                "copied_enrollments": copied_enrollments,
            }
        )

        logger.info(
            f"Duplicated {source_class} → {new_class} "
            f"({len(session_mapping)} sessions, {len(part_mapping)} parts, "
            f"{copied_enrollments} enrollments)"
        )

        return result

    @classmethod
    def validate_all_classes_in_term(cls, term) -> dict:
        """Validate all classes in a term for proper structure.

        Args:
            term: Term instance to validate

        Returns:
            Dict with validation results and statistics
        """
        logger.info(f"Validating all classes in term {term}")

        classes = ClassHeader.objects.filter(term=term)

        results = {
            "term": term,
            "total_classes": classes.count(),
            "valid_classes": 0,
            "invalid_classes": 0,
            "issues": {
                "no_sessions": [],
                "wrong_session_count": [],
                "no_parts": [],
                "weight_issues": [],
                "orphaned_parts": [],
            },
            "statistics": {"ieap_classes": 0, "regular_classes": 0, "total_sessions": 0, "total_parts": 0},
        }

        for class_header in classes:
            is_valid = True

            # Check basic structure
            validation = class_header.validate_session_structure()
            if not validation["valid"]:
                is_valid = False
                for error in validation["errors"]:
                    if "no sessions" in error.lower():
                        results["issues"]["no_sessions"].append(class_header)
                    elif "session count" in error.lower():
                        results["issues"]["wrong_session_count"].append(class_header)

            # Check session parts
            for session in class_header.class_sessions.all():
                session_validation = session.validate_parts_structure()
                if not session_validation["valid"]:
                    is_valid = False
                    for error in session_validation["errors"]:
                        if "no parts" in error.lower():
                            results["issues"]["no_parts"].append(session)

                # Check for weight issues
                for warning in session_validation.get("warnings", []):
                    results["issues"]["weight_issues"].append(f"{session}: {warning}")

            # Check for orphaned parts (parts not going through sessions)
            orphaned_parts = ClassPart.objects.filter(
                class_session__class_header=class_header, class_session__isnull=True
            )
            if orphaned_parts.exists():
                is_valid = False
                results["issues"]["orphaned_parts"].extend(orphaned_parts)

            # Update counters
            if is_valid:
                results["valid_classes"] += 1
            else:
                results["invalid_classes"] += 1

            # Statistics
            if class_header.is_ieap_class():
                results["statistics"]["ieap_classes"] += 1
            else:
                results["statistics"]["regular_classes"] += 1

            results["statistics"]["total_sessions"] += class_header.class_sessions.count()
            results["statistics"]["total_parts"] += sum(
                s.class_parts.count() for s in class_header.class_sessions.all()
            )

        # Summary
        total_issues = sum(
            len(issue_list) if isinstance(issue_list, list) else 1 for issue_list in results["issues"].values()
        )

        logger.info(
            f"Term {term} validation complete: "
            f"{results['valid_classes']}/{results['total_classes']} valid classes, "
            f"{total_issues} total issues found"
        )

        return results

    @classmethod
    @transaction.atomic
    def fix_class_structure_issues(cls, term, dry_run: bool = True) -> dict:
        """Attempt to fix common class structure issues in a term.

        Args:
            term: Term instance to fix
            dry_run: If True, only report what would be fixed

        Returns:
            Dict with fix results and actions taken
        """
        logger.info(f"{'Analyzing' if dry_run else 'Fixing'} class structure issues in term {term}")

        validation_results = cls.validate_all_classes_in_term(term)

        fix_results = {
            "term": term,
            "dry_run": dry_run,
            "actions_taken": [],
            "fixes_applied": {"sessions_created": 0, "parts_created": 0, "structures_corrected": 0},
            "unfixable_issues": [],
        }

        # Fix classes with no sessions
        for class_header in validation_results["issues"]["no_sessions"]:
            if not dry_run:
                created_count, sessions = class_header.ensure_sessions_exist()
                fix_results["fixes_applied"]["sessions_created"] += created_count

            fix_results["actions_taken"].append(
                f"{'Would create' if dry_run else 'Created'} sessions for {class_header}"
            )

        # Fix sessions with no parts
        for session in validation_results["issues"]["no_parts"]:
            if not dry_run:
                parts_created = session.ensure_parts_exist()
                fix_results["fixes_applied"]["parts_created"] += parts_created

            fix_results["actions_taken"].append(f"{'Would create' if dry_run else 'Created'} parts for {session}")

        # Handle wrong session counts (more complex)
        for class_header in validation_results["issues"]["wrong_session_count"]:
            session_count = class_header.class_sessions.count()
            expected_count = 2 if class_header.is_ieap_class() else 1

            if session_count > expected_count:
                fix_results["unfixable_issues"].append(
                    f"{class_header}: Has {session_count} sessions, expected {expected_count} (manual review required)"
                )
            elif session_count < expected_count:
                if not dry_run:
                    created_count, sessions = class_header.ensure_sessions_exist()
                    fix_results["fixes_applied"]["structures_corrected"] += 1

                fix_results["actions_taken"].append(
                    f"{'Would fix' if dry_run else 'Fixed'} session structure for {class_header}"
                )

        logger.info(
            f"Structure fix {'analysis' if dry_run else 'operation'} complete for {term}: "
            f"{len(fix_results['actions_taken'])} actions, "
            f"{len(fix_results['unfixable_issues'])} unfixable issues"
        )

        return fix_results
