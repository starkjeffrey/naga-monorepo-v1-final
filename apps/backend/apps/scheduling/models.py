"""Scheduling app models following clean architecture principles.

This module contains models for operational class scheduling, room management,
and actual class instances. All models are designed to avoid circular dependencies
while providing comprehensive scheduling functionality.

Key architectural decisions:
- Clean dependencies: scheduling → curriculum + people + facilities (no circular dependencies)
- Operational instances (not planning templates - those stay in curriculum)
- ClassHeader/ClassPart created from curriculum templates via services
- Comprehensive room and teacher scheduling support
- Multi-part language class structure support
- Reading class tier management for specialized offerings

Models:
- ClassHeader: Scheduled class instances (e.g., GESL-01 Section A, Fall 2025)
- ClassSession: Session grouping within classes (for IEAP support)
- ClassPart: Scheduled class components (e.g., Grammar part, MWF 9-10am)
- CombinedClassGroup: Administrative class grouping
- ReadingClass: Specialized tiered class offerings
"""

from decimal import Decimal
from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models, transaction
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from uuid_extensions import uuid7

from apps.common.models import AuditModel
from apps.scheduling.class_part_types import ClassPartType

if TYPE_CHECKING:
    from django.contrib.auth.models import User

    from apps.common.models import Room
    from apps.people.models import TeacherProfile

from .constants import (
    DEFAULT_MAX_ENROLLMENT,
    MAX_SESSION_NUMBER,
    MIN_SESSION_NUMBER,
    READING_CLASS_CONVERSION_THRESHOLD,
    READING_CLASS_MAX_TARGET_ENROLLMENT,
    READING_CLASS_TIER_THRESHOLDS,
    SECTION_ID_PATTERN,
    VALID_MEETING_DAYS,
)


class CombinedCourseTemplate(AuditModel):
    """Term-independent templates for course combinations.

    Defines which courses should always be scheduled together across all terms.
    When any member course is scheduled, a CombinedClassInstance is automatically
    created to manage the shared scheduling resources.

    Key features:
    - Persistent across terms (template-based design)
    - Automatic scheduling when member courses are scheduled
    - Supports course combination management (e.g., SOC-429, ENGL-302A, THM-421)
    - Clean separation between configuration and instances
    """

    class StatusChoices(models.TextChoices):
        """Status options for course combination templates."""

        ACTIVE = "ACTIVE", _("Active")
        INACTIVE = "INACTIVE", _("Inactive")
        DEPRECATED = "DEPRECATED", _("Deprecated")

    name: models.CharField = models.CharField(
        _("Template Name"),
        max_length=100,
        help_text=_("Descriptive name for this course combination"),
    )
    courses: models.ManyToManyField = models.ManyToManyField(
        "curriculum.Course",
        related_name="combined_course_templates",
        verbose_name=_("Courses"),
        help_text=_("Courses that should always be scheduled together"),
    )
    description: models.TextField = models.TextField(
        _("Description"),
        blank=True,
        help_text=_("Additional details about this combination and its purpose"),
    )
    status: models.CharField = models.CharField(
        _("Status"),
        max_length=15,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE,
        db_index=True,
        help_text=_("Current status of this template"),
    )

    # Administrative tracking
    created_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_combined_course_templates",
        verbose_name=_("Created By"),
        help_text=_("User who created this template"),
    )
    notes: models.TextField = models.TextField(
        _("Administrative Notes"),
        blank=True,
        help_text=_("Internal notes for administrative purposes"),
    )

    class Meta:
        verbose_name = _("Combined Course Template")
        verbose_name_plural = _("Combined Course Templates")
        unique_together = [["name"]]
        ordering = ["name"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["status", "is_deleted"]),
            models.Index(fields=["created_by"]),
        ]
        permissions = [
            (
                "can_manage_course_combinations",
                "Can manage course combination templates",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def course_count(self) -> int:
        """Get count of courses in this template."""
        return self.courses.count()

    @property
    def course_codes(self) -> str:
        """Get comma-separated list of course codes."""
        return ", ".join(self.courses.values_list("code", flat=True))

    @property
    def active_instances_count(self) -> int:
        """Get count of active instances across all terms."""
        return self.combined_class_instances.filter(
            status=CombinedClassInstance.StatusChoices.ACTIVE,
            is_deleted=False,
        ).count()

    def get_member_courses(self):
        """Get all courses that belong to this template."""
        return self.courses.filter(is_deleted=False)

    def clean(self) -> None:
        """Validate combined course template data."""
        super().clean()

        # Note: Course count validation is handled in the admin form
        # because M2M relationships aren't saved when model.clean() runs

        if self.status == self.StatusChoices.ACTIVE and self.pk:
            overlapping_templates = (
                CombinedCourseTemplate.objects.filter(
                    status=self.StatusChoices.ACTIVE,
                    is_deleted=False,
                    courses__in=self.courses.all(),
                )
                .exclude(pk=self.pk)
                .distinct()
            )

            if overlapping_templates.exists():
                overlapping_names = list(overlapping_templates.values_list("name", flat=True))
                raise ValidationError(
                    {
                        "courses": _(
                            f"Some courses are already in active templates: {', '.join(overlapping_names)}",
                        ),
                    },
                )


class CombinedClassInstance(AuditModel):
    """Term-specific instances of course combinations.

    Created automatically when any member course from a CombinedCourseTemplate
    is scheduled in a term. Manages shared scheduling resources (teacher, room)
    while maintaining individual course enrollments.

    Key features:
    - Automatically created when member courses are scheduled
    - Manages shared teacher and room assignments
    - Links individual ClassHeaders for combined instruction
    - Supports individual course credit while sharing resources
    """

    class StatusChoices(models.TextChoices):
        """Status options for combined class instances."""

        DRAFT = "DRAFT", _("Draft")
        ACTIVE = "ACTIVE", _("Active")
        COMPLETED = "COMPLETED", _("Completed")
        CANCELLED = "CANCELLED", _("Cancelled")

    template: models.ForeignKey = models.ForeignKey(
        CombinedCourseTemplate,
        on_delete=models.CASCADE,
        related_name="combined_class_instances",
        verbose_name=_("Template"),
        help_text=_("Course combination template this instance implements"),
    )
    term: models.ForeignKey = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.CASCADE,
        related_name="combined_class_instances",
        verbose_name=_("Term"),
        help_text=_("Academic term for this combination instance"),
    )

    # Shared scheduling resources
    primary_teacher: models.ForeignKey = models.ForeignKey(
        "people.TeacherProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="combined_class_instances",
        verbose_name=_("Primary Teacher"),
        help_text=_("Teacher assigned to teach this combined class"),
    )
    primary_room: models.ForeignKey = models.ForeignKey(
        "common.Room",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="combined_class_instances",
        verbose_name=_("Primary Room"),
        help_text=_("Room where this combined class meets"),
    )

    # Instance management
    status: models.CharField = models.CharField(
        _("Status"),
        max_length=15,
        choices=StatusChoices.choices,
        default=StatusChoices.DRAFT,
        db_index=True,
        help_text=_("Current status of this combination instance"),
    )
    section_id: models.CharField = models.CharField(
        _("Combined Section ID"),
        max_length=5,
        validators=[
            RegexValidator(SECTION_ID_PATTERN, _("Section ID must be a single letter A-Z")),
        ],
        help_text=_("Section identifier for the combined class (A, B, C, etc.)"),
    )
    max_enrollment: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Maximum Combined Enrollment"),
        default=DEFAULT_MAX_ENROLLMENT,
        validators=[MinValueValidator(1), MaxValueValidator(200)],
        help_text=_("Maximum total students across all member courses"),
    )

    # Administrative details
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this combination instance"),
    )
    auto_created: models.BooleanField = models.BooleanField(
        _("Auto Created"),
        default=True,
        help_text=_("Whether this instance was automatically created"),
    )

    class Meta:
        verbose_name = _("Combined Class Instance")
        verbose_name_plural = _("Combined Class Instances")
        unique_together = [["template", "term", "section_id"]]
        ordering = ["term", "template", "section_id"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["template", "term"]),
            models.Index(fields=["term", "status"]),
            models.Index(fields=["primary_teacher"]),
            models.Index(fields=["primary_room"]),
        ]
        permissions = [
            ("can_manage_combined_instances", "Can manage combined class instances"),
        ]

    def __str__(self) -> str:
        return f"{self.template.name} - {self.term} (Section {self.section_id})"

    @property
    def member_class_headers(self):
        """Get all ClassHeaders that belong to this combination."""
        return self.class_headers.filter(is_deleted=False)

    @property
    def member_count(self) -> int:
        """Get count of member class headers."""
        return self.member_class_headers.count()

    @property
    def total_enrollment(self) -> int:
        """Get total enrollment across all member courses."""
        return sum(ch.enrollment_count for ch in self.member_class_headers)

    @property
    def course_codes(self) -> str:
        """Get comma-separated list of member course codes."""
        return ", ".join(self.member_class_headers.values_list("course__code", flat=True).order_by("course__code"))

    @property
    def is_fully_scheduled(self) -> bool:
        """Check if all template courses are scheduled in this instance."""
        template_course_count = self.template.course_count
        scheduled_course_count = self.member_class_headers.count()
        return scheduled_course_count == template_course_count

    def get_missing_courses(self):
        """Get courses from template that haven't been scheduled yet."""
        scheduled_courses = self.member_class_headers.values_list("course", flat=True)
        return self.template.courses.exclude(id__in=scheduled_courses)

    def apply_shared_resources_to_parts(self) -> int:
        """Apply shared teacher/room to all member ClassParts. Returns count updated."""
        if not (self.primary_teacher or self.primary_room):
            return 0

        updated_count = 0
        for class_header in self.member_class_headers:
            for session in class_header.class_sessions.all():
                for part in session.class_parts.all():
                    updates: dict[str, object] = {}
                    if self.primary_teacher and part.teacher != self.primary_teacher:
                        updates["teacher"] = self.primary_teacher
                    if self.primary_room and part.room != self.primary_room:
                        updates["room"] = self.primary_room

                    if updates:
                        for field, value in updates.items():
                            setattr(part, field, value)
                        part.save(update_fields=list(updates.keys()))
                        updated_count += 1

        return updated_count

    def clean(self) -> None:
        """Validate combined class instance data."""
        super().clean()

        if self.template and self.template.status != CombinedCourseTemplate.StatusChoices.ACTIVE:
            raise ValidationError(
                {"template": _("Cannot create instances from inactive templates.")},
            )

        if self.template and self.term and self.section_id:
            duplicate_instances = CombinedClassInstance.objects.filter(
                template=self.template,
                term=self.term,
                section_id=self.section_id,
                is_deleted=False,
            ).exclude(pk=self.pk)

            if duplicate_instances.exists():
                raise ValidationError(
                    {
                        "section_id": _(
                            f"Instance already exists for {self.template.name} "
                            f"in {self.term} Section {self.section_id}"
                        ),
                    },
                )

    def save(self, *args, **kwargs):
        """Apply shared resources after saving."""
        super().save(*args, **kwargs)

        # Apply shared resources to class parts if they're assigned
        if self.primary_teacher or self.primary_room:
            self.apply_shared_resources_to_parts()


class CombinedClassGroup(AuditModel):
    """Administrative grouping of multiple ClassHeaders.

    Groups multiple class offerings for administrative purposes such as
    combined scheduling, shared resources, or coordinated instruction.
    Used to manage classes that should be scheduled together.

    Key features:
    - Term-specific grouping
    - Administrative convenience for bulk operations
    - Clean dependency on curriculum for terms
    """

    name: models.CharField = models.CharField(
        _("Group Name"),
        max_length=100,
        help_text=_("Descriptive name for this class group"),
    )
    term: models.ForeignKey = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.CASCADE,
        related_name="combined_class_groups",
        verbose_name=_("Term"),
        help_text=_("Academic term for this group"),
    )
    description: models.TextField = models.TextField(
        _("Description"),
        blank=True,
        help_text=_("Additional details about this group"),
    )

    class Meta:
        verbose_name = _("Combined Class Group")
        verbose_name_plural = _("Combined Class Groups")
        unique_together = [["term", "name"]]
        ordering = ["term", "name"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["term", "is_deleted"]),
        ]

    def __str__(self) -> str:
        return f"{self.term} - {self.name}"

    @property
    def member_count(self) -> int:
        """Get count of active member class headers."""
        return self.member_class_headers.filter(is_deleted=False).count()


class ClassHeader(AuditModel):
    """Scheduled class instances created from curriculum templates.

    Represents a specific offering of a course during a particular term
    (e.g., GESL Level 1, Section A, Fall 2025). These are operational
    instances created from ClassHeaderTemplate in curriculum app.

    Key features:
    - Specific course offering with section and time designation
    - Status management for scheduling workflow
    - Paired class support for language programs
    - Template derivation tracking
    - Integration with room and teacher scheduling
    - Support for different class types (standard, combined, reading)
    """

    class TimeOfDay(models.TextChoices):
        """Time periods for class scheduling."""

        MORNING = "MORN", _("Morning")
        AFTERNOON = "AFT", _("Afternoon")
        EVENING = "EVE", _("Evening")
        NIGHT = "NIGHT", _("Night")
        ALL_DAY = "ALL", _("All Day")

    class ClassType(models.TextChoices):
        """Types of class offerings."""

        STANDARD = "STANDARD", _("Standard Class")
        COMBINED = "COMBINED", _("Combined Class")
        READING = "READING", _("Reading Class")
        INTENSIVE = "INTENSIVE", _("Intensive Class")
        WORKSHOP = "WORKSHOP", _("Workshop")

    class ClassStatus(models.TextChoices):
        """Class scheduling statuses."""

        DRAFT = "DRAFT", _("Draft")
        SCHEDULED = "SCHEDULED", _("Scheduled")
        ACTIVE = "ACTIVE", _("Active")
        COMPLETED = "COMPLETED", _("Completed")
        CANCELLED = "CANCELLED", _("Cancelled")
        SUSPENDED = "SUSPENDED", _("Suspended")

    # Core scheduling information
    course: models.ForeignKey = models.ForeignKey(
        "curriculum.Course",
        on_delete=models.PROTECT,
        related_name="class_headers",
        verbose_name=_("Course"),
        help_text=_("Course being offered"),
    )
    term: models.ForeignKey = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.PROTECT,
        related_name="class_headers",
        verbose_name=_("Term"),
        help_text=_("Academic term when class is offered"),
    )
    section_id: models.CharField = models.CharField(
        _("Section ID"),
        max_length=5,
        validators=[
            RegexValidator(SECTION_ID_PATTERN, _("Section ID must be a single letter A-Z")),
        ],
        help_text=_("Section identifier (A, B, C, etc.)"),
    )
    time_of_day: models.CharField = models.CharField(
        _("Time of Day"),
        max_length=10,
        choices=TimeOfDay.choices,
        default=TimeOfDay.MORNING,
        help_text=_("General time period for this class"),
    )

    class_type: models.CharField = models.CharField(
        _("Class Type"),
        max_length=15,
        choices=ClassType.choices,
        default=ClassType.STANDARD,
        db_index=True,
        help_text=_("Type of class offering"),
    )
    status: models.CharField = models.CharField(
        _("Status"),
        max_length=15,
        choices=ClassStatus.choices,
        default=ClassStatus.DRAFT,
        db_index=True,
        help_text=_("Current scheduling status"),
    )

    # Grouping and pairing
    combined_class_instance: models.ForeignKey = models.ForeignKey(
        CombinedClassInstance,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="class_headers",
        verbose_name=_("Combined Class Instance"),
        help_text=_("Combined class instance this class belongs to (if any)"),
    )
    combined_class_group: models.ForeignKey = models.ForeignKey(
        CombinedClassGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="member_class_headers",
        verbose_name=_("Combined Class Group"),
        help_text=_("Group this class belongs to (if any)"),
    )
    is_paired: models.BooleanField = models.BooleanField(
        _("Is Paired"),
        default=False,
        help_text=_("Whether this class is paired with another"),
    )
    paired_with: models.ForeignKey["ClassHeader"] = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="paired_classes",
        verbose_name=_("Paired With"),
        help_text=_("Class this is paired with (for language programs)"),
    )

    # Capacity and enrollment
    max_enrollment: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Maximum Enrollment"),
        default=DEFAULT_MAX_ENROLLMENT,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text=_("Maximum number of students allowed"),
    )

    # Administrative details
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this class offering"),
    )
    legacy_class_id: models.CharField = models.CharField(
        _("Legacy Class ID"),
        max_length=50,
        blank=True,
        help_text=_("Legacy system identifier for migration tracking"),
    )

    class Meta:
        verbose_name = _("Class Header")
        verbose_name_plural = _("Class Headers")
        unique_together = [["course", "term", "section_id", "time_of_day"]]
        ordering = ["term", "course", "section_id"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["course", "term"]),
            models.Index(fields=["term", "status"]),
            models.Index(fields=["class_type", "status"]),
            models.Index(fields=["is_paired"]),
        ]
        permissions = [
            (
                "can_manage_class_scheduling",
                "Can manage bulk class scheduling operations",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.course.code} {self.section_id} ({self.term})"

    @property
    def full_name(self) -> str:
        """Get full descriptive name."""
        return f"{self.course.title} - Section {self.section_id}"

    @property
    def enrollment_count(self) -> int:
        """Get current enrollment count."""
        # This will work once enrollment models are properly connected
        return (
            getattr(self, "class_header_enrollments", models.Manager())
            .filter(status__in=["ENROLLED", "WAITLISTED"])
            .count()
        )

    @property
    def is_full(self) -> bool:
        """Check if class is at capacity."""
        return self.enrollment_count >= self.max_enrollment

    @property
    def available_spots(self) -> int:
        """Get number of available enrollment spots."""
        return max(0, self.max_enrollment - self.enrollment_count)

    @property
    def is_combined(self) -> bool:
        """Check if this class is part of a combined class instance."""
        return self.combined_class_instance is not None

    @property
    def combined_course_codes(self) -> str:
        """Get comma-separated list of all courses in the combination."""
        if self.combined_class_instance:
            return self.combined_class_instance.course_codes
        return self.course.code

    @property
    def shared_teacher(self):
        """Get the shared teacher from the combined instance, if any."""
        if self.combined_class_instance:
            return self.combined_class_instance.primary_teacher
        return None

    @property
    def shared_room(self):
        """Get the shared room from the combined instance, if any."""
        if self.combined_class_instance:
            return self.combined_class_instance.primary_room
        return None

    # ========== INTEGRITY METHODS ==========

    def clean(self) -> None:
        """Validate the ClassHeader model."""
        super().clean()

        # Import validator here to avoid circular imports
        from apps.scheduling.validators import validate_language_class_creation

        # Validate language classes have templates (only for new classes)
        if not self.pk and self.course:  # Only check on creation
            try:
                validate_language_class_creation(self.course)
            except ValidationError as e:
                raise ValidationError({"course": e.message}) from e

        # Validate pairing logic
        if self.is_paired and not self.paired_with:
            raise ValidationError(
                {
                    "paired_with": _(
                        "Paired classes must specify what they are paired with.",
                    ),
                },
            )

        if self.paired_with:
            # Ensure pairing is symmetric and consistent
            if not self.is_paired:
                raise ValidationError(
                    {
                        "is_paired": _(
                            "Classes must be marked as paired if they have a paired_with value.",
                        ),
                    },
                )
            if (
                self.paired_with.term_id != self.term_id
                or self.paired_with.section_id != self.section_id
                or self.paired_with.time_of_day != self.time_of_day
            ):
                raise ValidationError(
                    {
                        "paired_with": _(
                            "Paired classes must have same term, section, and time of day.",
                        ),
                    },
                )

    def ensure_sessions_exist(self):
        """Ensure appropriate sessions exist for this class type.

        Returns:
            tuple: (created_count, session_list)
        """
        created_count = 0

        if self.is_ieap_class():
            # IEAP needs exactly 2 sessions
            session1, created1 = ClassSession.objects.get_or_create(
                class_header=self,
                session_number=1,
                defaults={"session_name": "First Session", "grade_weight": Decimal("0.5")},
            )
            if created1:
                created_count += 1

            session2, created2 = ClassSession.objects.get_or_create(
                class_header=self,
                session_number=2,
                defaults={"session_name": "Second Session", "grade_weight": Decimal("0.5")},
            )
            if created2:
                created_count += 1

            sessions = [session1, session2]
        else:
            # Regular classes need exactly 1 session
            session, created = ClassSession.objects.get_or_create(
                class_header=self,
                session_number=1,
                defaults={
                    "session_name": "",  # No name for regular classes
                    "grade_weight": Decimal("1.0"),
                },
            )
            if created:
                created_count += 1
            sessions = [session]

        return created_count, sessions

    def is_ieap_class(self):
        """Determine if this is an IEAP class based on course code or type."""
        # Adjust this logic based on how you identify IEAP classes
        return (
            self.course.code.startswith("IEAP")
            or getattr(self.course, "course_type", None) == "IEAP"
            or
            # Add other IEAP identification logic here
            False
        )

    def validate_session_structure(self) -> dict[str, Any]:
        """Validate that session structure matches class type.

        Returns:
            dict: {'valid': bool, 'errors': list, 'warnings': list}
        """
        from typing import Any

        result: dict[str, Any] = {"valid": True, "errors": [], "warnings": []}
        session_count = self.class_sessions.count()

        if self.is_ieap_class():
            if session_count != 2:
                result["valid"] = False
                result["errors"].append(f"IEAP class should have exactly 2 sessions, found {session_count}")

            # Check session weights
            total_weight = sum(s.grade_weight for s in self.class_sessions.all())
            if abs(total_weight - Decimal("1.0")) > Decimal("0.001"):
                result["warnings"].append(f"Session weights sum to {total_weight}, expected 1.0")
        else:
            if session_count != 1:
                result["valid"] = False
                result["errors"].append(f"Regular class should have exactly 1 session, found {session_count}")

            session = self.class_sessions.first()
            if session and session.grade_weight != Decimal("1.0"):
                result["warnings"].append(f"Regular class session weight is {session.grade_weight}, expected 1.0")

        return result

    def get_all_parts(self):
        """Get all ClassParts across all sessions."""
        parts = []
        for session in self.class_sessions.all().order_by("session_number"):
            parts.extend(list(session.class_parts.all()))
        return parts

    def get_primary_teacher(self):
        """Get the primary teacher (from first part of first session)."""
        first_session = self.class_sessions.order_by("session_number").first()
        if first_session:
            first_part = first_session.class_parts.order_by("class_part_code").first()
            if first_part:
                return first_part.teacher
        return None

    def get_primary_room(self):
        """Get the primary room (from first part of first session)."""
        first_session = self.class_sessions.order_by("session_number").first()
        if first_session:
            first_part = first_session.class_parts.order_by("class_part_code").first()
            if first_part:
                return first_part.room
        return None

    def get_all_teachers(self):
        """Get all unique teachers across all parts."""
        teachers = set()
        for session in self.class_sessions.all():
            for part in session.class_parts.all():
                if part.teacher:
                    teachers.add(part.teacher)
        return list(teachers)

    def get_all_meeting_days(self):
        """Get all unique meeting days across all parts."""
        days = set()
        for session in self.class_sessions.all():
            for part in session.class_parts.all():
                if part.meeting_days:
                    part_days = [d.strip().upper() for d in part.meeting_days.split(",")]
                    days.update(part_days)
        return sorted(days)

    def save(self, *args, **kwargs):
        """Ensure pairing symmetry on save."""
        # Use transaction to ensure consistency
        with transaction.atomic():
            super().save(*args, **kwargs)

            # Handle symmetric pairing logic
            if self.is_paired and self.paired_with:
                self._ensure_symmetric_pairing()
            elif not self.is_paired and self.paired_with:
                # If is_paired is False but paired_with is set, clear the pairing
                self.paired_with = None
                super().save(update_fields=["paired_with"])

    def _ensure_symmetric_pairing(self):
        """Ensure symmetric pairing relationship."""
        if not self.paired_with:
            return

        # Avoid infinite recursion by checking if update is needed
        needs_update = self.paired_with.paired_with != self or not self.paired_with.is_paired

        if needs_update:
            # Use update_fields to avoid triggering save() on the paired object
            self.paired_with.paired_with = self
            self.paired_with.is_paired = True
            self.paired_with.save(update_fields=["paired_with", "is_paired"])


class ClassSession(AuditModel):
    """Session grouping for classes, primarily for IEAP program support.

    Regular classes: 1 ClassSession per ClassHeader (automatically created)
    IEAP classes: 2 ClassSessions per ClassHeader (Session 1 & Session 2)

    Key features:
    - Session-level grade weighting for IEAP averaging
    - Independent teacher/part assignments per session
    - Supports session exemptions for repeat students
    - Transparent for regular single-session classes
    """

    class_header: models.ForeignKey = models.ForeignKey(
        ClassHeader,
        on_delete=models.CASCADE,
        related_name="class_sessions",
        verbose_name=_("Class Header"),
        help_text=_("Class this session belongs to"),
    )
    internal_session_id: models.UUIDField = models.UUIDField(
        default=uuid7,
        editable=False,
        unique=True,
        help_text=_("Immutable internal identifier for this session"),
    )
    session_number: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Session Number"),
        default=1,
        validators=[
            MinValueValidator(MIN_SESSION_NUMBER),
            MaxValueValidator(MAX_SESSION_NUMBER),
        ],
        help_text=_("Session number within the class (1 for regular, 1&2 for IEAP)"),
    )
    session_name: models.CharField = models.CharField(
        _("Session Name"),
        max_length=50,
        blank=True,
        help_text=_(
            "Optional name for this session (e.g., 'Session 1', 'Morning Session')",
        ),
    )
    grade_weight: models.DecimalField = models.DecimalField(
        _("Grade Weight"),
        max_digits=4,
        decimal_places=3,
        default=Decimal("1.000"),
        validators=[
            MinValueValidator(Decimal("0.000")),
            MaxValueValidator(Decimal("1.000")),
        ],
        help_text=_(
            "Weight of this session in final grade (1.0 for regular, 0.5 for IEAP)",
        ),
    )
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this session"),
    )

    class Meta:
        verbose_name = _("Class Session")
        verbose_name_plural = _("Class Sessions")
        unique_together = [["class_header", "session_number"]]
        ordering = ["class_header", "session_number"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["class_header", "session_number"]),
        ]

    def __str__(self) -> str:
        if self.session_name:
            return f"{self.class_header} - {self.session_name}"
        if self.class_header.class_type == ClassHeader.ClassType.STANDARD and self.session_number == 1:
            return str(self.class_header)  # Don't show session for regular classes
        return f"{self.class_header} - Session {self.session_number}"

    @property
    def is_ieap_session(self) -> bool:
        """Check if this is an IEAP session (has multiple sessions in same class)."""
        return self.class_header.class_sessions.count() > 1

    @property
    def part_count(self) -> int:
        """Get number of class parts in this session."""
        return self.class_parts.count()

    # ========== INTEGRITY METHODS ==========

    def ensure_parts_exist(self, min_parts=1):
        """Ensure at least min_parts exist for this session.

        Args:
            min_parts: Minimum number of parts required

        Returns:
            int: Number of parts created
        """
        existing_parts = self.class_parts.count()
        created_count = 0

        if existing_parts < min_parts:
            for i in range(existing_parts, min_parts):
                part_code = chr(65 + i)  # A, B, C, etc.
                ClassPart.objects.create(
                    class_session=self,
                    class_part_code=part_code,
                    class_part_type=ClassPartType.MAIN,
                    grade_weight=Decimal("1.0") / min_parts,
                )
                created_count += 1

        return created_count

    def validate_parts_structure(self) -> dict[str, Any]:
        """Validate parts structure for this session.

        Returns:
            dict: {'valid': bool, 'errors': list, 'warnings': list}
        """
        from typing import Any

        result: dict[str, Any] = {"valid": True, "errors": [], "warnings": []}

        parts = self.class_parts.all()
        if not parts.exists():
            result["valid"] = False
            result["errors"].append("Session has no parts")
            return result

        # Check total grade weight
        total_weight = sum(p.grade_weight for p in parts)
        if abs(total_weight - Decimal("1.0")) > Decimal("0.001"):
            result["warnings"].append(f"Parts weights sum to {total_weight}, expected 1.0")

        # Check for duplicate part codes
        part_codes = [p.class_part_code for p in parts]
        if len(part_codes) != len(set(part_codes)):
            result["errors"].append("Duplicate part codes found")
            result["valid"] = False

        return result


class ClassPart(AuditModel):
    """Scheduled components of ClassSession instances.

    Represents specific scheduled components of a class session (e.g., Grammar part
    meeting MWF 9-10am, Computer lab part meeting TTh 2-3pm). Each part belongs
    to a ClassSession, which allows IEAP programs to have separate sessions.

    Key features:
    - Specific meeting times and days
    - Room and teacher assignments
    - Grade weight contributions within session
    - Textbook assignments
    - Session-based organization for IEAP support
    - Multi-part language class support
    """

    # ClassPartType now imported from class_part_types.py

    class_session: models.ForeignKey["ClassSession"] = models.ForeignKey(
        ClassSession,
        on_delete=models.CASCADE,
        related_name="class_parts",
        verbose_name=_("Class Session"),
        help_text=_("Session this part belongs to"),
    )
    internal_part_id: models.UUIDField = models.UUIDField(
        default=uuid7,
        editable=False,
        unique=True,
        help_text=_("Immutable internal identifier for this part"),
    )

    # Part identification
    class_part_type: models.CharField = models.CharField(
        _("Class Part Type"),
        max_length=15,
        choices=ClassPartType.choices,
        default=ClassPartType.MAIN,
        db_index=True,
        help_text=_("Type of class component"),
    )
    class_part_code: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Class Part Code"),
        default=1,
        help_text=_("Numeric identifier for this part (1, 2, 3, etc.)"),
    )
    name: models.CharField = models.CharField(
        _("Part Name"),
        max_length=100,
        blank=True,
        help_text=_("Optional specific name for this part"),
    )

    # Scheduling details
    teacher: models.ForeignKey["TeacherProfile"] = models.ForeignKey(
        "people.TeacherProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="class_parts",
        verbose_name=_("Teacher"),
        help_text=_("Assigned teacher for this part"),
    )
    room: models.ForeignKey["Room"] = models.ForeignKey(
        "common.Room",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="class_parts",
        verbose_name=_("Room"),
        help_text=_("Assigned room for this part"),
    )

    # Meeting times
    # Note: Using CharField for days until we implement MultiSelectField
    meeting_days: models.CharField = models.CharField(
        _("Meeting Days"),
        max_length=20,
        help_text=_("Days of week this part meets (comma-separated: MON,WED,FRI)"),
    )
    start_time: models.TimeField = models.TimeField(
        _("Start Time"),
        null=True,
        blank=True,
        help_text=_("When this part starts (filled by scheduler)"),
    )
    end_time: models.TimeField = models.TimeField(
        _("End Time"),
        null=True,
        blank=True,
        help_text=_("When this part ends (filled by scheduler)"),
    )

    # Academic configuration
    grade_weight: models.DecimalField = models.DecimalField(
        _("Grade Weight"),
        max_digits=4,
        decimal_places=3,
        default=Decimal("1.000"),
        validators=[
            MinValueValidator(Decimal("0.000")),
            MaxValueValidator(Decimal("1.000")),
        ],
        help_text=_("Weight of this part in final grade (0.000-1.000)"),
    )

    # Resources
    textbooks: models.ManyToManyField = models.ManyToManyField(
        "curriculum.Textbook",
        blank=True,
        related_name="class_parts",
        verbose_name=_("Textbooks"),
        help_text=_("Textbooks used in this part"),
    )

    # Template derivation support
    template_derived: models.BooleanField = models.BooleanField(
        _("Template Derived"),
        default=False,
        help_text=_("Whether this class part was derived from a ClassPartTemplate"),
    )

    # Administrative details
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this class part"),
    )
    legacy_class_id: models.CharField = models.CharField(
        _("Legacy Class ID"),
        max_length=50,
        blank=True,
        help_text=_("Legacy system identifier for migration tracking"),
    )

    class Meta:
        verbose_name = _("Class Part")
        verbose_name_plural = _("Class Parts")
        unique_together = [["class_session", "class_part_code"]]
        ordering = ["class_session", "class_part_code"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["class_session", "class_part_type"]),
            models.Index(fields=["teacher"]),
            models.Index(fields=["room"]),
            models.Index(fields=["start_time", "end_time"]),
        ]

    def __str__(self) -> str:
        part_name = self.name or self.get_class_part_type_display()
        return f"{self.class_session} - {part_name}"

    @property
    def full_name(self) -> str:
        """Get full descriptive name."""
        part_name = self.name or self.get_class_part_type_display()
        return f"{self.class_session.class_header.full_name} - {part_name}"

    @property
    def class_header(self) -> ClassHeader:
        """Get the class header through the session."""
        return self.class_session.class_header

    @property
    def duration_minutes(self) -> int:
        """Calculate duration in minutes."""
        if self.start_time and self.end_time:
            start_seconds = self.start_time.hour * 3600 + self.start_time.minute * 60
            end_seconds = self.end_time.hour * 3600 + self.end_time.minute * 60
            return (end_seconds - start_seconds) // 60
        return 0

    @property
    def meeting_days_list(self) -> list[str]:
        """Get meeting days as a list."""
        if self.meeting_days:
            return [day.strip() for day in self.meeting_days.split(",") if day.strip()]
        return []

    @property
    def enrollment_count(self) -> int:
        """Get current enrollment count for this part."""
        # This will work once enrollment models are properly connected
        return getattr(self, "class_part_enrollments", models.Manager()).filter(is_active=True).count()

    def clean(self) -> None:
        """Validate class part data."""
        super().clean()

        # Validate time ordering
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError({"end_time": _("End time must be after start time.")})

        # Validate grade weight
        if self.grade_weight < 0 or self.grade_weight > 1:
            raise ValidationError(
                {"grade_weight": _("Grade weight must be between 0.000 and 1.000.")},
            )

        # Validate meeting days format
        if self.meeting_days:
            days = [day.strip().upper() for day in self.meeting_days.split(",")]
            invalid_days = [day for day in days if day not in VALID_MEETING_DAYS]
            if invalid_days:
                raise ValidationError(
                    {
                        "meeting_days": _(
                            f"Invalid days: {', '.join(invalid_days)}. Use: {', '.join(VALID_MEETING_DAYS)}",
                        ),
                    },
                )

        # Validate room conflicts (simple double-booking prevention)
        if self.room and self.start_time and self.end_time and self.meeting_days:
            self._validate_room_conflicts()

    def _validate_room_conflicts(self) -> None:
        """Check for room conflicts with other class parts."""
        my_days = {day.strip().upper() for day in self.meeting_days.split(",")}

        # More efficient approach: build database query to find day overlaps
        from django.db.models import Q

        # Build Q objects for each day overlap check
        day_queries = Q()
        for day in my_days:
            # Use contains to match days in comma-separated format
            day_queries |= Q(meeting_days__icontains=day)

        # Find conflicting parts with database-level filtering
        conflicting_parts = (
            ClassPart.objects.filter(
                room=self.room,
                start_time__lt=self.end_time,
                end_time__gt=self.start_time,
            )
            .filter(day_queries)
            .exclude(pk=self.pk)
        )

        # Verify actual conflicts (since __icontains can have false positives)
        for part in conflicting_parts:
            if part.meeting_days:
                other_days = {day.strip().upper() for day in part.meeting_days.split(",")}
                overlapping_days = my_days & other_days
                if overlapping_days:  # If days actually overlap
                    raise ValidationError(
                        {
                            "room": _(
                                f"Room conflict with {part.class_session} on {', '.join(overlapping_days)}",
                            ),
                        },
                    )


# RoomSchedule model removed - using simple conflict validation in ClassPart instead


class ReadingClass(AuditModel):
    """Specialized tiered class offerings with enrollment-based pricing.

    Special class type with tiered enrollment/pricing structure and
    automatic conversion logic. Used for small, specialized offerings
    that have different pricing based on enrollment size.

    Key features:
    - Automatic tier calculation based on enrollment
    - Conversion to standard classes when enrollment exceeds threshold
    - Eligibility restrictions (BA program courses only)
    - Integration with billing systems for tiered pricing
    - Specialized enrollment management
    """

    class Tier(models.TextChoices):
        """Reading class enrollment tiers."""

        TIER_1 = "TIER_1", _("Tier 1 (1-2 students)")
        TIER_2 = "TIER_2", _("Tier 2 (3-5 students)")
        TIER_3 = "TIER_3", _("Tier 3 (6-15 students)")

    class EnrollmentStatus(models.TextChoices):
        """Reading class enrollment statuses."""

        PLANNING = "PLANNING", _("Planning")
        OPEN = "OPEN", _("Open for Enrollment")
        CLOSED = "CLOSED", _("Closed")
        CONVERTED = "CONVERTED", _("Converted to Standard")

    class_header: models.OneToOneField = models.OneToOneField(
        ClassHeader,
        on_delete=models.CASCADE,
        related_name="reading_class",
        verbose_name=_("Class Header"),
        help_text=_("Class header this reading class is associated with"),
    )
    tier: models.CharField = models.CharField(
        _("Tier"),
        max_length=10,
        choices=Tier.choices,
        default=Tier.TIER_1,
        db_index=True,
        help_text=_("Current enrollment tier"),
    )
    target_enrollment: models.PositiveSmallIntegerField = models.PositiveSmallIntegerField(
        _("Target Enrollment"),
        default=3,
        validators=[MinValueValidator(1), MaxValueValidator(15)],
        help_text=_("Target number of students for this reading class"),
    )
    enrollment_status: models.CharField = models.CharField(
        _("Enrollment Status"),
        max_length=15,
        choices=EnrollmentStatus.choices,
        default=EnrollmentStatus.PLANNING,
        db_index=True,
        help_text=_("Current enrollment status"),
    )
    description: models.TextField = models.TextField(
        _("Description"),
        blank=True,
        help_text=_("Additional description or notes about this reading class"),
    )

    class Meta:
        verbose_name = _("Reading Class")
        verbose_name_plural = _("Reading Classes")
        ordering = ["class_header"]
        permissions = [
            ("can_manage_reading_classes", "Can manage reading class operations"),
        ]

    def __str__(self) -> str:
        return f"Reading: {self.class_header} ({self.get_tier_display()})"

    @property
    def enrollment_count(self) -> int:
        """Get current enrollment count."""
        return self.class_header.enrollment_count

    @property
    def can_convert_to_standard(self) -> bool:
        """Check if reading class can be converted to standard class."""
        return self.enrollment_count > READING_CLASS_CONVERSION_THRESHOLD

    def calculate_tier(self) -> str:
        """Calculate appropriate tier based on enrollment."""
        # Use tier thresholds from constants
        tier_thresholds = {
            self.Tier.TIER_1: READING_CLASS_TIER_THRESHOLDS["TIER_1"],
            self.Tier.TIER_2: READING_CLASS_TIER_THRESHOLDS["TIER_2"],
            self.Tier.TIER_3: READING_CLASS_TIER_THRESHOLDS["TIER_3"],
        }

        count = self.enrollment_count
        for tier, max_count in tier_thresholds.items():
            if count <= max_count:
                return tier
        # Should convert to standard class
        return self.Tier.TIER_3

    def update_tier(self) -> bool:
        """Update tier based on current enrollment. Returns True if changed."""
        new_tier = self.calculate_tier()
        if new_tier != self.tier:
            self.tier = new_tier
            self.save(update_fields=["tier"])
            return True
        return False

    def convert_to_standard(self, user=None) -> None:
        """Convert reading class to standard class when enrollment exceeds 15."""
        if self.can_convert_to_standard:
            self.class_header.class_type = ClassHeader.ClassType.STANDARD
            self.class_header.save(update_fields=["class_type"])

            self.enrollment_status = self.EnrollmentStatus.CONVERTED
            self.save(update_fields=["enrollment_status"])

    def clean(self) -> None:
        """Validate reading class data."""
        super().clean()

        # Validate that associated class is reading type
        if self.class_header and self.class_header.class_type != ClassHeader.ClassType.READING:
            raise ValidationError(
                {
                    "class_header": _(
                        "Reading class must be associated with a READING type class header.",
                    ),
                },
            )

        # Validate target enrollment is within tier limits
        if self.target_enrollment > READING_CLASS_MAX_TARGET_ENROLLMENT:
            raise ValidationError(
                {
                    "target_enrollment": _(
                        f"Reading classes cannot have target enrollment above "
                        f"{READING_CLASS_MAX_TARGET_ENROLLMENT} students."
                    ),
                },
            )


class TestPeriodReset(AuditModel):
    """Reset dates for absence penalty calculations by test period.

    Manages when absence counters reset for language program tests. Only applies
    to language division classes where absence penalties are calculated per test
    period. Academic classes manage their own grading and do not use this system.

    Key features:
    - Language division classes only (validated)
    - IEAP: 3 test periods, Others: midterm + final
    - Bulk application with individual class overrides
    - Term-scoped reset date management
    - Integration with mobile app and Moodle systems
    """

    class TestType(models.TextChoices):
        """Test periods for absence penalty resets."""

        IEAP_TEST_1 = "IEAP_T1", _("IEAP Test 1")
        IEAP_TEST_2 = "IEAP_T2", _("IEAP Test 2")
        IEAP_TEST_3 = "IEAP_T3", _("IEAP Test 3")
        MIDTERM = "MIDTERM", _("Midterm")
        FINAL = "FINAL", _("Final")

    # Core fields
    term: models.ForeignKey = models.ForeignKey(
        "curriculum.Term",
        on_delete=models.CASCADE,
        related_name="test_period_resets",
        verbose_name=_("Term"),
        help_text=_("Academic term for this reset period"),
    )
    test_type: models.CharField = models.CharField(
        _("Test Type"),
        max_length=10,
        choices=TestType.choices,
        db_index=True,
        help_text=_("Type of test period for absence reset"),
    )
    reset_date: models.DateField = models.DateField(
        _("Reset Date"),
        db_index=True,
        help_text=_("Date when absence counters reset for this test period"),
    )

    # Bulk application support
    applies_to_all_language_classes: models.BooleanField = models.BooleanField(
        _("Applies to All Language Classes"),
        default=True,
        help_text=_("Apply this reset date to all language classes in the term"),
    )
    specific_classes: models.ManyToManyField = models.ManyToManyField(
        ClassHeader,
        blank=True,
        related_name="test_period_resets",
        verbose_name=_("Specific Classes"),
        help_text=_("Specific classes if not applying to all (language division only)"),
    )

    # Additional details
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this reset period"),
    )

    class Meta:
        verbose_name = _("Test Period Reset")
        verbose_name_plural = _("Test Period Resets")
        ordering = ["term", "test_type", "reset_date"]
        unique_together = [["term", "test_type", "applies_to_all_language_classes"]]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["term", "test_type"]),
            models.Index(fields=["reset_date", "applies_to_all_language_classes"]),
            models.Index(fields=["term", "reset_date"]),
        ]
        permissions = [
            ("can_manage_test_resets", "Can manage test period reset operations"),
        ]

    def __str__(self) -> str:
        scope = "All Language Classes" if self.applies_to_all_language_classes else "Specific Classes"
        return f"{self.term} - {self.get_test_type_display()} ({self.reset_date}) - {scope}"

    @property
    def applicable_classes_count(self) -> int:
        """Get count of classes this reset applies to."""
        if self.applies_to_all_language_classes:
            return self._get_all_language_classes_in_term().count()
        return self.specific_classes.count()

    def _get_all_language_classes_in_term(self):
        """Get all language division classes in the term."""
        return ClassHeader.objects.filter(
            term=self.term,
            course__cycle__division__short_name__iexact="LANG",
            is_deleted=False,
        )

    def get_applicable_classes(self):
        """Get all classes this reset applies to."""
        if self.applies_to_all_language_classes:
            return self._get_all_language_classes_in_term()
        return self.specific_classes.filter(is_deleted=False)

    @classmethod
    def get_reset_date_for_class(cls, class_header, test_type):
        """Get the applicable reset date for a specific class and test type.

        Args:
            class_header: ClassHeader instance
            test_type: TestType choice value

        Returns:
            reset_date or None if no applicable reset found
        """
        # First check for specific class override
        specific_reset = cls.objects.filter(
            term=class_header.term,
            test_type=test_type,
            applies_to_all_language_classes=False,
            specific_classes=class_header,
        ).first()

        if specific_reset:
            return specific_reset.reset_date

        # Then check for term-wide reset
        general_reset = cls.objects.filter(
            term=class_header.term,
            test_type=test_type,
            applies_to_all_language_classes=True,
        ).first()

        return general_reset.reset_date if general_reset else None

    @classmethod
    def get_all_reset_dates_for_term(cls, term):
        """Get all reset dates for a term organized by test type.

        Returns:
            dict: {test_type: reset_date}
        """
        resets = {}
        for reset in cls.objects.filter(term=term, applies_to_all_language_classes=True):
            resets[reset.test_type] = reset.reset_date
        return resets

    def clean(self) -> None:
        """Validate test period reset data."""
        super().clean()

        # Validate reset date is within term dates
        if self.term and self.reset_date:
            if self.reset_date < self.term.start_date or self.reset_date > self.term.end_date:
                raise ValidationError({"reset_date": _("Reset date must be within the term dates.")})

        # Validate specific classes are language division only
        if not self.applies_to_all_language_classes and hasattr(self, "_specific_classes_validated"):
            for class_header in self._specific_classes_validated:
                if not self._is_language_class(class_header):
                    raise ValidationError(
                        {"specific_classes": _("Test period resets only apply to language division classes.")},
                    )

    def _is_language_class(self, class_header) -> bool:
        """Check if a class belongs to the language division."""
        return class_header.course.division.short_name and class_header.course.division.short_name.upper() == "LANG"

    def save(self, *args, **kwargs):
        """Override save to validate language division requirement."""
        # Pre-save validation for specific classes
        if not self.applies_to_all_language_classes and self.pk:
            # For existing instances, validate specific classes
            for class_header in self.specific_classes.all():
                if not self._is_language_class(class_header):
                    error_msg = "Test period resets only apply to language division classes."
                    raise ValidationError(error_msg)

        super().save(*args, **kwargs)


# ============================================================================
# TEACHER LEAVE MANAGEMENT
# ============================================================================


class TeacherLeaveRequest(AuditModel):
    """Teacher leave requests with substitute assignment tracking.

    Manages formal leave requests from teachers and tracks substitute teacher
    assignments. Designed primarily for the language program where substitute
    teachers are commonly needed, but also supports academic program needs
    (e.g., exam proctoring substitutes).

    Key features:
    - Links to affected class parts for specific session coverage
    - Leave type categorization for tracking patterns
    - Approval workflow with administrative oversight
    - Substitute teacher assignment and notification
    - Leave counting for administrative reporting
    - Support for both language and academic program substitutions
    """

    class LeaveType(models.TextChoices):
        """Types of teacher leave."""

        SICK = "SICK", _("Sick Leave")
        PERSONAL = "PERSONAL", _("Personal Leave")
        EMERGENCY = "EMERGENCY", _("Emergency")
        PROFESSIONAL = "PROFESSIONAL", _("Professional Development")
        FAMILY = "FAMILY", _("Family Emergency")
        MEDICAL = "MEDICAL", _("Medical Appointment")
        OTHER = "OTHER", _("Other")

    class ApprovalStatus(models.TextChoices):
        """Leave request approval statuses."""

        PENDING = "PENDING", _("Pending Approval")
        APPROVED = "APPROVED", _("Approved")
        DENIED = "DENIED", _("Denied")
        CANCELLED = "CANCELLED", _("Cancelled")

    teacher: models.ForeignKey = models.ForeignKey(
        "people.TeacherProfile",
        on_delete=models.PROTECT,
        related_name="leave_requests",
        verbose_name=_("Teacher"),
        help_text=_("Teacher requesting leave"),
    )

    # Leave details
    leave_date: models.DateField = models.DateField(
        _("Leave Date"),
        help_text=_("Date when teacher will be absent"),
    )
    leave_type: models.CharField = models.CharField(
        _("Leave Type"),
        max_length=15,
        choices=LeaveType.choices,
        default=LeaveType.SICK,
        help_text=_("Type of leave being requested"),
    )
    reason: models.TextField = models.TextField(
        _("Reason"),
        help_text=_("Detailed reason for leave request"),
    )
    is_emergency: models.BooleanField = models.BooleanField(
        _("Is Emergency"),
        default=False,
        help_text=_("Whether this is an emergency/last-minute request"),
    )

    # Classes affected - tracks which sessions need substitutes
    affected_class_parts: models.ManyToManyField = models.ManyToManyField(
        "ClassPart",
        related_name="teacher_leave_requests",
        verbose_name=_("Affected Class Parts"),
        help_text=_("Class parts that need substitute coverage"),
    )

    # Substitute assignment
    substitute_teacher: models.ForeignKey = models.ForeignKey(
        "people.TeacherProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="substitute_assignments",
        verbose_name=_("Substitute Teacher"),
        help_text=_("Teacher assigned to cover the classes"),
    )
    substitute_confirmed: models.BooleanField = models.BooleanField(
        _("Substitute Confirmed"),
        default=False,
        help_text=_("Whether substitute teacher has confirmed availability"),
    )
    substitute_assigned_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_substitute_leaves",
        verbose_name=_("Substitute Assigned By"),
        help_text=_("Staff member who assigned the substitute"),
    )
    substitute_assigned_at: models.DateTimeField = models.DateTimeField(
        _("Substitute Assigned At"),
        null=True,
        blank=True,
        help_text=_("When substitute was assigned"),
    )

    # Approval workflow
    approval_status: models.CharField = models.CharField(
        _("Approval Status"),
        max_length=15,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        db_index=True,
    )
    approved_by: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_leave_requests",
        verbose_name=_("Approved By"),
    )
    approved_at: models.DateTimeField = models.DateTimeField(
        _("Approved At"),
        null=True,
        blank=True,
    )
    denial_reason: models.TextField = models.TextField(
        _("Denial Reason"),
        blank=True,
        help_text=_("Reason for denial if status is denied"),
    )

    # Administrative tracking
    notification_sent: models.BooleanField = models.BooleanField(
        _("Notification Sent"),
        default=False,
        help_text=_("Whether department has been notified"),
    )
    substitute_found: models.BooleanField = models.BooleanField(
        _("Substitute Found"),
        default=False,
        help_text=_("Whether a substitute has been secured"),
    )
    notes: models.TextField = models.TextField(
        _("Administrative Notes"),
        blank=True,
        help_text=_("Internal notes about this leave request"),
    )

    class Meta:
        verbose_name = _("Teacher Leave Request")
        verbose_name_plural = _("Teacher Leave Requests")
        ordering = ["-leave_date", "-created_at"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["teacher", "leave_date"]),
            models.Index(fields=["leave_date", "approval_status"]),
            models.Index(fields=["substitute_teacher", "leave_date"]),
            models.Index(fields=["is_emergency", "approval_status"]),
            models.Index(fields=["substitute_found", "leave_date"]),
        ]

    def __str__(self) -> str:
        return f"{self.teacher.person.full_name} - {self.leave_date} ({self.get_leave_type_display()})"

    def approve(self, user: "User", notes: str = "") -> None:
        """Approve the leave request."""
        self.approval_status = self.ApprovalStatus.APPROVED
        self.approved_by = user
        self.approved_at = timezone.now()
        if notes:
            self.notes = f"{self.notes}\n\nApproval: {notes}".strip()
        self.save(
            update_fields=["approval_status", "approved_by", "approved_at", "notes"],
        )

    def deny(self, user: "User", reason: str) -> None:
        """Deny the leave request."""
        self.approval_status = self.ApprovalStatus.DENIED
        self.approved_by = user
        self.approved_at = timezone.now()
        self.denial_reason = reason
        self.save(
            update_fields=[
                "approval_status",
                "approved_by",
                "approved_at",
                "denial_reason",
            ],
        )

    def assign_substitute(
        self,
        substitute: "TeacherProfile",
        assigned_by: "User",
    ) -> None:
        """Assign a substitute teacher to cover the leave."""
        self.substitute_teacher = substitute
        self.substitute_assigned_by = assigned_by
        self.substitute_assigned_at = timezone.now()
        self.substitute_found = True

        self.save(
            update_fields=[
                "substitute_teacher",
                "substitute_assigned_by",
                "substitute_assigned_at",
                "substitute_found",
            ],
        )

    @property
    def is_approved(self) -> bool:
        """Check if leave request is approved."""
        return self.approval_status == self.ApprovalStatus.APPROVED

    @property
    def needs_substitute(self) -> bool:
        """Check if leave request needs substitute coverage."""
        return self.is_approved and self.affected_class_parts.exists() and not self.substitute_found

    @property
    def affected_sessions_count(self) -> int:
        """Count how many class sessions are affected."""
        return self.affected_class_parts.count()

    def clean(self) -> None:
        """Validate leave request data."""
        super().clean()

        # Cannot request leave for past dates (unless emergency)
        if self.leave_date < timezone.now().date() and not self.is_emergency:
            raise ValidationError(
                {
                    "leave_date": _(
                        "Cannot request leave for past dates unless it's an emergency.",
                    ),
                },
            )

        if self.approval_status == self.ApprovalStatus.DENIED and not self.denial_reason:
            raise ValidationError(
                {"denial_reason": _("Denial reason is required for denied requests.")},
            )

        if self.substitute_teacher and not self.substitute_found:
            self.substitute_found = True
