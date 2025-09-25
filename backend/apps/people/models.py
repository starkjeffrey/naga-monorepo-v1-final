"""People app models following clean architecture principles.

This module contains models for managing people and their profiles in the Naga SIS system.
All models are designed to avoid circular dependencies with other apps.

Key architectural decisions:
- Person is the base model for all humans in the system
- Profile models (Student, Teacher, Staff) extend Person functionality
- Foreign key references to other apps are minimal and well-defined
- Each model has a single, clear responsibility
- Historical tracking is provided via base model mixins

Models:
- Gender: Enumeration for gender choices
- Province: Geographic locations for birth places
- Person: Base model for all people in the system
- StudentProfile: Student-specific data and status
- TeacherProfile: Teacher profiles and qualifications
- StaffProfile: Staff member profiles
- PersonEventLog: Audit log for person-related events
- StudentAuditLog: Student-specific audit trail
- PhoneNumber: Multiple phone numbers per person
- EmergencyContact: Emergency contact information
- TeacherLeaveRequest: Teacher leave requests with substitute tracking
- StudentPhoto: Versioned photo storage with history tracking
"""

from datetime import date
from typing import TYPE_CHECKING, ClassVar

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.db.models import (
    BooleanField,
    CharField,
    DateField,
    DateTimeField,
    EmailField,
    ForeignKey,
    ImageField,
    IntegerField,
    OneToOneField,
    PositiveIntegerField,
    TextField,
    UUIDField,
)
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django_countries.fields import CountryField
from django_countries.fields import CountryField as CountryFieldType

from apps.common.constants import BIRTH_PLACE_CHOICES, is_cambodian_province
from apps.common.models import AuditModel
from apps.common.utils.uuid_utils import generate_uuid

if TYPE_CHECKING:
    from users.models import User


# Phone number validator for international format
phone_number_validator = RegexValidator(
    regex=r"^\+?[1-9]\d{7,14}$",
    message=_(
        "Phone number must be 8-15 digits in international format. "
        "Use + followed by country code and number (e.g., +85512345678), "
        "or local format starting with a non-zero digit.",
    ),
    code="invalid_phone_format",
)


class Gender(models.TextChoices):
    """Gender choices for Person model."""

    MALE = "M", _("Male")
    FEMALE = "F", _("Female")
    NONBINARY_OTHER = "N", _("Non-Binary/Other")
    PREFER_NOT_TO_SAY = "X", _("Prefer not to say")


class Person(AuditModel):
    """Base model for all people in the system.

    This model serves as the foundation for students, teachers, and staff.
    It contains core demographic information and personal details that are
    common across all person types.

    Design principles:
    - Single source of truth for person data
    - Supports both preferred and legal names for official documents
    - Comprehensive validation for data integrity
    - Historical tracking via AuditModel base

    Key features:
    - UUID for secure identification
    - Dual name system (preferred vs legal)
    - Comprehensive demographic data
    - Photo and contact information
    - Birth location tracking via Province
    - Age calculation property
    - Display name logic for documents
    """

    unique_id: UUIDField = models.UUIDField(default=generate_uuid, editable=False, unique=True)

    # Core name fields
    family_name: CharField = models.CharField(_("Family Name"), max_length=255)
    personal_name: CharField = models.CharField(_("Personal Name"), max_length=255)
    full_name: CharField = models.CharField(_("Full Name"), max_length=255, blank=True)
    khmer_name: CharField = models.CharField(_("Khmer Name"), max_length=255, blank=True)

    # Gender information
    preferred_gender: CharField = models.CharField(
        _("Preferred Gender"),
        max_length=1,
        choices=Gender,
        default=Gender.PREFER_NOT_TO_SAY,
    )

    # Legal name system for official documents
    use_legal_name_for_documents: BooleanField = models.BooleanField(
        _("Use Legal Name for Documents"),
        default=False,
        help_text=_(
            "Use alternate (legal) name instead of preferred name on official documents",
        ),
    )
    alternate_family_name: CharField = models.CharField(
        _("Legal Family Name"),
        max_length=255,
        blank=True,
        help_text=_("Family name to be used for official documents"),
    )
    alternate_personal_name: CharField = models.CharField(
        _("Legal Personal Name"),
        max_length=255,
        blank=True,
        help_text=_("Personal name to be used for official documents"),
    )
    alternate_khmer_name: CharField = models.CharField(
        _("Legal Khmer Name"),
        max_length=255,
        blank=True,
        help_text=_("Khmer name to be used for official documents"),
    )
    alternate_gender: CharField = models.CharField(
        _("Legal Gender"),
        max_length=1,
        choices=Gender,
        default=Gender.PREFER_NOT_TO_SAY,
        help_text=_("Gender to be used on official documents"),
    )

    # Contact and personal information
    photo: ImageField = models.ImageField(_("Photo"), null=True, blank=True, upload_to="photos/")
    school_email: EmailField = models.EmailField(
        _("School Email"),
        blank=True,
        unique=True,
        null=True,
    )
    personal_email: EmailField = models.EmailField(_("Personal Email"), blank=True, null=True)

    # Birth and citizenship information
    date_of_birth: DateField = models.DateField(_("Date of Birth"), blank=True, null=True)
    birth_province: CharField = models.CharField(
        _("Birth Province"),
        max_length=50,
        choices=BIRTH_PLACE_CHOICES,
        blank=True,
        null=True,
        help_text=_(
            "Province of birth (for Cambodian citizens) or International for non-Cambodian citizens",
        ),
    )
    citizenship: CountryFieldType = CountryField(default="KH", verbose_name=_("Citizenship"))

    class Meta:
        verbose_name = _("Person")
        verbose_name_plural = _("People")
        ordering: ClassVar[list[str]] = ["family_name", "personal_name"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["family_name", "personal_name"]),
            models.Index(fields=["date_of_birth"]),
            models.Index(fields=["unique_id"]),
        ]

    def __str__(self) -> str:
        return self.full_name or f"{self.family_name} {self.personal_name}".strip()

    def __init__(self, *args, **kwargs):
        """Initialize field tracking for name changes."""
        super().__init__(*args, **kwargs)
        # Track original name values for change detection without database queries
        self._original_family_name = self.family_name if self.pk else None
        self._original_personal_name = self.personal_name if self.pk else None

    def save(self, *args, **kwargs):
        """Custom save method to handle name processing and validation.

        Automatically updates full_name when family_name or personal_name changes.
        Converts names to uppercase for consistency.
        Uses field tracking to avoid N+1 queries.
        """
        is_new = self.pk is None

        new_family_name = self.family_name.upper() if self.family_name else ""
        new_personal_name = self.personal_name.upper() if self.personal_name else ""

        # Check if names changed using tracked original values (no database query)
        name_changed = (
            self._original_family_name != new_family_name or self._original_personal_name != new_personal_name
        )

        self.family_name = new_family_name
        self.personal_name = new_personal_name

        if is_new or name_changed or not self.full_name:
            self.full_name = f"{new_family_name} {new_personal_name}".strip()

        super().save(*args, **kwargs)

        # Update tracked original values after successful save
        self._original_family_name = self.family_name
        self._original_personal_name = self.personal_name

    @classmethod
    def from_db(cls, db, field_names, values):
        """Initialize field tracking when loading from database."""
        instance = super().from_db(db, field_names, values)
        # Track original name values from database
        instance._original_family_name = instance.family_name
        instance._original_personal_name = instance.personal_name
        return instance

    def refresh_from_db(self, using=None, fields=None, from_queryset=None):
        """Update field tracking when refreshing from database."""
        super().refresh_from_db(using=using, fields=fields, from_queryset=from_queryset)
        # Update tracked original values after refresh
        self._original_family_name = self.family_name
        self._original_personal_name = self.personal_name

    def clean(self) -> None:
        """Comprehensive validation for Person model.

        Validates:
        - Birth province consistency with citizenship
        - Legal name requirements when use_legal_name_for_documents is True
        """
        super().clean()

        if self.citizenship != "KH" and self.birth_province and is_cambodian_province(self.birth_province):
            raise ValidationError(
                {
                    "birth_province": _(
                        "Cambodian birth province not valid for non-Cambodian citizens. Use 'International' instead.",
                    ),
                },
            )

        if self.use_legal_name_for_documents:
            if not self.alternate_family_name or not self.alternate_personal_name:
                msg = _(
                    "Alternate (Legal) name must be provided if 'use_legal_name_for_documents' is selected.",
                )
                error_dict = {}
                if not self.alternate_family_name:
                    error_dict["alternate_family_name"] = msg
                if not self.alternate_personal_name:
                    error_dict["alternate_personal_name"] = msg
                raise ValidationError(error_dict)

    @property
    def age(self) -> int | None:
        """Calculate current age based on date of birth."""
        if self.date_of_birth:
            today = timezone.now().date()
            return (
                today.year
                - self.date_of_birth.year
                - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
            )
        return None

    @property
    def display_name(self) -> str:
        """Return the appropriate name for display based on document preferences."""
        if self.use_legal_name_for_documents and self.alternate_family_name and self.alternate_personal_name:
            return f"{self.alternate_family_name} {self.alternate_personal_name}".strip()
        return self.full_name

    def get_student_profile(self):
        """Get the student profile if it exists."""
        return getattr(self, "student_profile", None)

    def get_teacher_profile(self):
        """Get the teacher profile if it exists."""
        return getattr(self, "teacher_profile", None)

    def get_staff_profile(self):
        """Get the staff profile if it exists."""
        return getattr(self, "staff_profile", None)

    @property
    def has_student_role(self) -> bool:
        """Check if this person has a student profile."""
        return hasattr(self, "student_profile")

    @property
    def has_teacher_role(self) -> bool:
        """Check if this person has a teacher profile."""
        return hasattr(self, "teacher_profile")

    @property
    def has_staff_role(self) -> bool:
        """Check if this person has a staff profile."""
        return hasattr(self, "staff_profile")

    def get_primary_emergency_contact(self):
        """Get the primary emergency contact for this person."""
        return self.emergency_contacts.filter(is_primary=True).first()

    def get_current_photo(self):
        """Get the current photo from StudentPhoto model."""
        from apps.people.models import StudentPhoto

        return StudentPhoto.get_current_photo(self)

    @property
    def current_photo_url(self) -> str | None:
        """Get URL of current photo if available."""
        current_photo = self.get_current_photo()
        if current_photo and current_photo.photo_file:
            return current_photo.photo_file.url
        # Fallback to legacy photo field
        if self.photo:
            return self.photo.url
        return None

    @property
    def current_thumbnail_url(self) -> str | None:
        """Get URL of current photo thumbnail if available."""
        current_photo = self.get_current_photo()
        if current_photo and current_photo.thumbnail:
            return current_photo.thumbnail.url
        # No thumbnail for legacy photos
        return None


class StudentProfile(AuditModel):
    """Student-specific profile information and status tracking.

    This model extends Person with student-specific data including enrollment
    status, academic information, and study preferences. It maintains a clean
    separation from academic program details to avoid circular dependencies.

    Key features:
    - Comprehensive status tracking with audit trail
    - Study time preferences
    - Transfer student identification
    - Monk status for special considerations
    - Student ID management
    - Historical tracking via AuditModel

    Status Management:
    - Tracks current enrollment status
    - Provides status change methods with logging
    - Supports various student states (active, graduated, dropped, etc.)
    """

    class Status(models.TextChoices):
        """Valid status values for student profiles."""

        ACTIVE = "ACTIVE", _("Active")
        INACTIVE = "INACTIVE", _("Inactive")
        GRADUATED = "GRADUATED", _("Graduated")
        DROPPED = "DROPPED", _("Dropped")
        SUSPENDED = "SUSPENDED", _("Suspended")
        TRANSFERRED = "TRANSFERRED", _("Transferred")
        FROZEN = "FROZEN", _("Frozen")
        UNKNOWN = "UNKNOWN", _("Unknown")

    STUDY_TIME_CHOICES = [
        ("morning", _("Morning")),
        ("afternoon", _("Afternoon")),
        ("evening", _("Evening")),
    ]

    person: OneToOneField = models.OneToOneField(
        Person,
        on_delete=models.PROTECT,
        related_name="student_profile",
    )
    student_id: PositiveIntegerField = models.PositiveIntegerField(_("Student ID"), unique=True)
    legacy_ipk: PositiveIntegerField = models.PositiveIntegerField(
        _("Legacy System IPK"),
        null=True,
        blank=True,
        help_text=_("Identity Primary Key from legacy system for change tracking"),
        db_index=True,
    )

    # Student characteristics
    is_monk: BooleanField = models.BooleanField(_("Is a Monk"), default=False)
    is_transfer_student: BooleanField = models.BooleanField(
        _("Is Transfer Student"),
        default=False,
        help_text=_("Indicates student transferred from another institution"),
    )

    # Status tracking
    current_status: CharField = models.CharField(
        _("Current Status"),
        max_length=11,
        choices=Status.choices,
        default=Status.UNKNOWN,
        db_index=True,
    )

    # Study preferences
    study_time_preference: CharField = models.CharField(
        _("Study Time Preference"),
        max_length=20,
        choices=STUDY_TIME_CHOICES,
        default="evening",
        help_text=_("Preferred time of day for classes"),
    )

    # Enrollment tracking
    last_enrollment_date: DateField = models.DateField(
        _("Last Enrollment Date"),
        null=True,
        blank=True,
    )

    class Meta:
        indexes = [
            models.Index(fields=["student_id"]),
            models.Index(fields=["current_status"]),
        ]
        ordering = ["student_id"]
        verbose_name = _("Student Profile")
        verbose_name_plural = _("Student Profiles")
        permissions = [
            ("can_activate_student", "Can activate student accounts"),
            ("can_deactivate_student", "Can deactivate student accounts"),
            ("can_change_student_status", "Can change student status"),
            (
                "can_manage_student_records",
                "Can perform administrative actions on student records",
            ),
        ]

    def __str__(self) -> str:
        person_name = self.person.full_name if self.person else f"ID: {self.student_id}"
        return f"{self.student_id}: {person_name}"

    @property
    def formatted_student_id(self) -> str:
        """Return formatted student ID with leading zeros."""
        return f"{self.student_id:05d}" if isinstance(self.student_id, int) else str(self.student_id)

    @property
    def full_name(self) -> str:
        """Return the person's full name."""
        return self.person.full_name if self.person else ""

    @property
    def is_student_active(self) -> bool:
        """Check if student is currently active."""
        return self.current_status == self.Status.ACTIVE

    @property
    def declared_major(self):
        """Get the student's currently declared major (from MajorDeclaration).

        This returns only explicitly declared majors, not majors inferred from
        enrollment history. Use effective_major for a comprehensive view.

        Returns:
            Major instance or None if no active declaration exists
        """
        from apps.enrollment.models import MajorDeclaration

        declaration = MajorDeclaration.get_current_declaration(self)
        return declaration.major if declaration else None

    @property
    def enrollment_history_major(self):
        """Get the student's major based on enrollment history (from ProgramEnrollment).

        This returns the major from the student's most recent program enrollment,
        representing their historical/retrospective major based on course taking.

        Returns:
            Major instance or None if no program enrollment exists

        Architecture note: This property violates clean architecture by
        calling service from model. Future refactor: Move this logic to
        service layer and access via
        MajorDeclarationService.get_enrollment_history_major(student)
        """
        from apps.enrollment.services import MajorDeclarationService

        return MajorDeclarationService._get_enrollment_history_major(self)

    @property
    def has_major_conflict(self) -> bool:
        """Check if student has a conflict between declared major and enrollment history.

        Returns True if the student's declared major differs from their enrollment
        history major, indicating a potential inconsistency that may need review.

        Note: Language programs (IEAP, etc.) do not conflict with academic majors
        since students can be enrolled in both simultaneously.

        Returns:
            Boolean indicating if there's a major conflict
        """
        declared = self.declared_major
        enrollment_history = self.enrollment_history_major

        # No conflict if either is missing
        if declared is None or enrollment_history is None:
            return False

        # Import here to avoid circular dependency
        from apps.curriculum.models import Major

        # No conflict if enrollment history is a language program
        if enrollment_history.program_type == Major.ProgramType.LANGUAGE:
            return False

        # No conflict if declared major is a language program (shouldn't happen, but be safe)
        if declared.program_type == Major.ProgramType.LANGUAGE:
            return False

        # Both are academic programs - check if they differ
        return declared != enrollment_history

    def change_status(
        self,
        new_status: str,
        user: "User",
        notes: str = "",
    ) -> None:
        """Change student status with audit logging.

        Args:
            new_status: New status value (must be valid Status choice)
            user: User making the change
            notes: Optional notes about the status change

        Raises:
            ValueError: If new_status is not a valid choice
        """
        if new_status not in [choice[0] for choice in self.Status.choices]:
            msg = f"Invalid status: {new_status}"
            raise ValueError(msg)

        old_status = self.current_status
        if new_status != old_status:
            self.current_status = new_status
            self.save(update_fields=["current_status"])

            StudentAuditLog.log_status_change(
                student=self,
                old_status=old_status,
                new_status=new_status,
                user=user,
                notes=notes,
            )

    def left_the_monkhood(self, user=None, notes=""):
        """Mark that the student has left the monkhood.

        This method properly logs the monk status change since it affects
        scholarship eligibility and financial aid programs.

        Args:
            user: User recording the change (required for audit trail)
            notes: Optional notes about why the student left monkhood
        """
        if not self.is_monk:
            return  # Already not a monk

        # Log the change before updating
        StudentAuditLog.log_monk_status_change(
            student=self,
            old_status=True,
            new_status=False,
            user=user,
            notes=notes or "Student has left the monkhood",
        )

        self.is_monk = False
        self.save(update_fields=["is_monk"])

    def became_monk(self, user=None, notes=""):
        """Mark that the student has become a monk.

        This method properly logs the monk status change since it affects
        scholarship eligibility and financial aid programs.

        Args:
            user: User recording the change (required for audit trail)
            notes: Optional notes about the student becoming a monk
        """
        if self.is_monk:
            return  # Already a monk

        # Log the change before updating
        StudentAuditLog.log_monk_status_change(
            student=self,
            old_status=False,
            new_status=True,
            user=user,
            notes=notes or "Student has become a monk",
        )

        self.is_monk = True
        self.save(update_fields=["is_monk"])

    def set_monk_status(self, is_monk, user=None, notes=""):
        """Set the monk status with proper logging.

        This is the preferred method for changing monk status as it ensures
        all changes are properly logged for audit trail and scholarship tracking.

        Args:
            is_monk: Boolean - True if student is a monk, False if not
            user: User recording the change (required for audit trail)
            notes: Optional notes about the status change
        """
        if self.is_monk == is_monk:
            return  # No change needed

        # Log the change before updating
        StudentAuditLog.log_monk_status_change(
            student=self,
            old_status=self.is_monk,
            new_status=is_monk,
            user=user,
            notes=notes or f"Monk status changed to {'Monk' if is_monk else 'Not a Monk'}",
        )

        self.is_monk = is_monk
        self.save(update_fields=["is_monk"])


class TeacherProfile(AuditModel):
    """Teacher-specific profile information and qualifications.

    This model extends Person with teacher-specific data including qualifications,
    employment status, and areas of expertise. It maintains clean boundaries
    to avoid circular dependencies with course/scheduling systems.

    Key features:
    - Educational qualification tracking
    - Employment status management
    - Date range tracking for employment periods
    - Areas of expertise (will be linked to courses in academic app)
    - Active status calculation based on dates and status
    """

    class Qualification(models.TextChoices):
        """Educational qualification levels."""

        BACHELOR = "BA/BSc", "Bachelor's Degree"
        MASTER = "MA/MSc/JD", "Master's Degree"
        DOCTORATE = "PHD", "Doctorate"
        OTHER = "OTH", "Other"

    class Status(models.TextChoices):
        """Employment status choices."""

        ACTIVE = "ACTIVE", _("Active")
        INACTIVE = "INACTIVE", _("Inactive")
        SUSPENDED = "SUSPENDED", _("Suspended")
        ON_LEAVE = "ON_LEAVE", _("On Leave")

    person: OneToOneField = models.OneToOneField(
        Person,
        on_delete=models.PROTECT,
        related_name="teacher_profile",
    )

    # Qualifications
    terminal_degree: CharField = models.CharField(
        max_length=50,
        choices=Qualification.choices,
        default=Qualification.OTHER,
        blank=True,
    )

    # Employment status
    status: CharField = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        blank=True,
        db_index=True,
    )

    # Employment period tracking
    start_date: DateField = models.DateField(
        _("Start Date"),
        default=date.today,
        help_text=_("Date when employment started"),
    )
    end_date: DateField = models.DateField(
        _("End Date"),
        null=True,
        blank=True,
        help_text=_("Date when employment ended (if applicable)"),
    )

    class Meta:
        verbose_name = _("Teacher Profile")
        verbose_name_plural = _("Teacher Profiles")

    def __str__(self) -> str:
        return self.person.full_name if self.person else "Unknown Teacher"

    @property
    def is_teacher_active(self) -> bool:
        """Check if teacher is currently active.

        A teacher is considered active if:
        - Status is ACTIVE
        - Start date is in the past
        - End date is either null or in the future
        """
        today = timezone.now().date()
        return (
            self.status == self.Status.ACTIVE
            and self.start_date <= today
            and (self.end_date is None or self.end_date >= today)
        )


class StaffProfile(AuditModel):
    """Staff-specific profile information and employment details.

    This model extends Person with staff-specific data including position,
    department, and employment status. It maintains clean boundaries
    to avoid dependencies with other systems.

    Key features:
    - Position and department tracking
    - Employment status management
    - Date range tracking for employment periods
    - Leave management methods
    - Active status calculation
    """

    class Status(models.TextChoices):
        """Employment status choices."""

        ACTIVE = "ACTIVE", _("Active")
        INACTIVE = "INACTIVE", _("Inactive")
        SUSPENDED = "SUSPENDED", _("Suspended")
        ON_LEAVE = "ON_LEAVE", _("On Leave")

    person: OneToOneField = models.OneToOneField(
        Person,
        on_delete=models.PROTECT,
        related_name="staff_profile",
    )

    # Position information
    position: CharField = models.CharField(max_length=100, default="Staff")

    # Employment status
    status: CharField = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        blank=True,
        db_index=True,
    )

    # Employment period tracking
    start_date: DateField = models.DateField(
        _("Start Date"),
        default=date.today,
        help_text=_("Date when employment started"),
    )
    end_date: DateField = models.DateField(
        _("End Date"),
        null=True,
        blank=True,
        help_text=_("Date when employment ended (if applicable)"),
    )

    class Meta:
        verbose_name = "Staff Profile"
        verbose_name_plural = "Staff Profiles"

    def __str__(self) -> str:
        person_name = self.person.full_name if self.person else "Unknown Staff"
        return f"{person_name} - {self.position}"

    @property
    def is_staff_active(self) -> bool:
        """Check if staff member is currently active.

        A staff member is considered active if:
        - Status is ACTIVE
        - Start date is in the past
        - End date is either null or in the future
        """
        today = timezone.now().date()
        return (
            self.status == self.Status.ACTIVE
            and self.start_date <= today
            and (self.end_date is None or self.end_date >= today)
        )

    def take_leave(self, start_date=None, user=None, notes=""):
        """Record the start of a leave of absence.

        Args:
            start_date: Date when leave starts (defaults to today)
            user: User recording the leave
            notes: Optional notes about the leave
        """
        sd = start_date or timezone.now().date()
        old_status = self.status
        self.status = self.Status.ON_LEAVE
        self.save(update_fields=["status"])

        PersonEventLog.log_leave(
            person=self.person,
            start_date=sd,
            user=user,
            notes=notes or str(_("Leave of absence started")),
            details={"old_status": old_status},
        )

    def return_from_leave(self, end_date=None, user=None, notes=""):
        """Record the end of a leave of absence.

        Args:
            end_date: Date when leave ends (defaults to today)
            user: User recording the return
            notes: Optional notes about the return
        """
        ed = end_date or timezone.now().date()
        old_status = self.status
        self.status = self.Status.ACTIVE
        self.save(update_fields=["status"])

        PersonEventLog.log_leave(
            person=self.person,
            start_date=None,
            end_date=ed,
            user=user,
            notes=notes or str(_("Returned from leave")),
            details={"old_status": old_status},
        )


class PersonEventLog(models.Model):
    """Generic audit log for significant events related to any Person.

    This model provides a centralized logging mechanism for person-related
    events that don't fit into specific audit models. It supports various
    event types and maintains a complete audit trail.

    Key features:
    - Generic event logging for any person
    - Structured details storage via JSONField
    - Timestamp tracking with indexing
    - User attribution for accountability
    - Flexible notes field for context
    """

    class ActionType(models.TextChoices):
        """Types of actions that can be logged."""

        ROLE_CHANGE = "ROLE_CHANGE", _("Role Change")
        LEAVE = "LEAVE", _("Leave of Absence")
        UPDATE = "UPDATE", _("Profile Update")
        OTHER = "OTHER", _("Other")

    person: ForeignKey = models.ForeignKey(
        "Person",
        on_delete=models.CASCADE,
        related_name="event_logs",
        verbose_name=_("Person"),
    )
    action: CharField = models.CharField(_("Action"), max_length=20, choices=ActionType.choices)
    changed_by: ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("Changed By"),
    )
    timestamp: DateTimeField = models.DateTimeField(_("Timestamp"), auto_now_add=True, db_index=True)
    details: models.JSONField = models.JSONField(
        _("Details"),
        default=dict,
        blank=True,
        help_text=_("Record of event details (e.g., old/new status, role)"),
    )
    notes: TextField = models.TextField(_("Notes"), blank=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = _("Person Event Log")
        verbose_name_plural = _("Person Event Logs")
        indexes = [
            models.Index(fields=["person", "-timestamp"]),
            models.Index(fields=["action", "-timestamp"]),
        ]

    def __str__(self) -> str:
        user_str = f"by {self.changed_by}" if self.changed_by else "by System"
        timestamp = self.timestamp.strftime("%Y-%m-%d %H:%M")
        return f"{self.person} - {self.get_action_display()} {user_str} on {timestamp}"  # type: ignore[attr-defined]

    @classmethod
    def log_role_change(cls, person, role, old_status, new_status, user, notes=""):
        """Log the activation/deactivation of a person's role."""
        cls.objects.create(
            person=person,
            action=cls.ActionType.ROLE_CHANGE,
            changed_by=user,
            details={
                "role": role,
                "old_status": old_status,
                "new_status": new_status,
            },
            notes=notes or f"Role '{role}' status changed to {new_status}",
        )

    @classmethod
    def log_leave(
        cls,
        person,
        start_date,
        end_date=None,
        user=None,
        notes="",
        details=None,
    ):
        """Log the start or end of a leave of absence."""
        event_details = details or {}
        event_details.update(
            {
                "start_date": (start_date.isoformat() if hasattr(start_date, "isoformat") else str(start_date)),
                "end_date": (end_date.isoformat() if hasattr(end_date, "isoformat") else str(end_date)),
            },
        )

        cls.objects.create(
            person=person,
            action=cls.ActionType.LEAVE,
            changed_by=user,
            details=event_details,
            notes=notes or str(_("Leave of absence recorded")),
        )


class StudentAuditLog(models.Model):
    """Comprehensive audit trail specifically for student-related changes.

    This model provides detailed logging for all student-specific events
    including status changes, enrollment modifications, and academic
    progression. It uses generic foreign keys to link to related objects.

    Key features:
    - Student-specific audit trail
    - Generic foreign key support for related objects
    - Comprehensive change tracking via JSONField
    - Multiple action types for different event categories
    - Timestamp indexing for performance

    Future enhancement: Consolidate people.StudentAuditLog and common.StudentActivityLog into single audit model
    """

    class ActionType(models.TextChoices):
        """Types of student-related actions that can be logged."""

        CREATE = "CREATE", _("Create")
        UPDATE = "UPDATE", _("Update")
        MERGE = "MERGE", _("Merge")
        STATUS = "STATUS", _("Status Change")
        MONK_STATUS = "MONK_STATUS", _("Monk Status Change")
        ENROLLMENT = "ENROLLMENT", _("Enrollment Change")
        GRADUATION = "GRADUATION", _("Graduation Recorded")
        ACADEMIC = "ACADEMIC", _("Academic Progression")
        OTHER = "OTHER", _("Other Change")

    student: ForeignKey = models.ForeignKey(
        "StudentProfile",
        on_delete=models.CASCADE,
        related_name="audit_logs",
        verbose_name=_("Student"),
    )
    action: CharField = models.CharField(_("Action"), max_length=15, choices=ActionType.choices)
    changed_by: ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name=_("Changed By"),
    )
    timestamp: DateTimeField = models.DateTimeField(_("Timestamp"), auto_now_add=True, db_index=True)
    changes: models.JSONField = models.JSONField(
        _("Changes"),
        default=dict,
        blank=True,
        help_text=_("Record of what changed (e.g., old/new values, reason)"),
    )
    content_type: ForeignKey = models.ForeignKey(
        ContentType,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Related Object Type"),
    )
    object_id: PositiveIntegerField = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_("Related Object ID"),
    )
    related_object = GenericForeignKey("content_type", "object_id")
    notes: TextField = models.TextField(_("Notes"), blank=True)

    class Meta:
        ordering = ["-timestamp"]
        verbose_name = _("Student Audit Log")
        verbose_name_plural = _("Student Audit Logs")
        indexes = [
            models.Index(fields=["student", "-timestamp"]),
            models.Index(fields=["action", "-timestamp"]),
            models.Index(fields=["content_type", "object_id", "-timestamp"]),
        ]

    def __str__(self) -> str:
        user_str = f"by {self.changed_by}" if self.changed_by else "by System"
        timestamp = self.timestamp.strftime("%Y-%m-%d %H:%M")
        return f"{self.student} - {self.get_action_display()} {user_str} on {timestamp}"  # type: ignore[attr-defined]

    @classmethod
    def log_status_change(cls, student, old_status, new_status, user, notes=""):
        """Log a change in the StudentProfile.current_status field."""
        return cls.objects.create(
            student=student,
            action=cls.ActionType.STATUS,
            changed_by=user,
            changes={
                "field": "current_status",
                "old_value": old_status,
                "new_value": new_status,
            },
            notes=notes or str(_("Status changed")),
        )

    @classmethod
    def log_monk_status_change(cls, student, old_status, new_status, user, notes=""):
        """Log a change in the StudentProfile.is_monk field.

        This is critical for scholarship eligibility tracking since monk status
        affects access to certain scholarships and financial aid programs.

        Args:
            student: StudentProfile instance
            old_status: Previous monk status (boolean)
            new_status: New monk status (boolean)
            user: User making the change
            notes: Optional notes about the change
        """
        # Create human-readable status descriptions
        old_status_desc = "Monk" if old_status else "Not a Monk"
        new_status_desc = "Monk" if new_status else "Not a Monk"

        return cls.objects.create(
            student=student,
            action=cls.ActionType.MONK_STATUS,
            changed_by=user,
            changes={
                "field": "is_monk",
                "old_value": old_status,
                "new_value": new_status,
                "old_status_description": old_status_desc,
                "new_status_description": new_status_desc,
                "scholarship_impact": "Monk status change affects scholarship eligibility",
            },
            notes=notes or str(_("Monk status changed")),
        )

    def get_readable_changes(self):
        """Format the changes data in a human-readable way."""
        return str(self.changes)


class PhoneNumber(AuditModel):
    """Track multiple phone numbers per person with verification status.

    This model allows each person to have multiple phone numbers with
    different purposes and verification states. It includes support for
    messaging apps and verification tracking.

    Key features:
    - Multiple phone numbers per person
    - Verification status tracking
    - Telegram support identification
    - Primary number designation with uniqueness constraint
    - Comment field for number context
    """

    person: ForeignKey = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="phone_numbers",
    )
    number: CharField = models.CharField(
        max_length=100,
        blank=True,
        validators=[phone_number_validator],
        help_text=_("Phone number in international format (e.g., +85512345678) or local format. Must be 8-15 digits."),
    )
    comment: CharField = models.CharField(max_length=100, blank=True, default="")
    is_preferred: BooleanField = models.BooleanField(default=False)
    is_telegram: BooleanField = models.BooleanField(default=False)
    is_verified: BooleanField = models.BooleanField(default=False)
    last_verification: DateTimeField = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["person", "is_preferred"],
                name="unique_preferred_number",
                condition=models.Q(is_preferred=True),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.number} ({'Preferred' if self.is_preferred else 'Secondary'})"


class Contact(AuditModel):
    """Contact information for any person.

    This model stores shared contact details that can serve multiple purposes.
    Each person can have multiple contacts, and each contact can be designated
    for emergency and/or general situations to avoid data duplication.

    Key features:
    - Shared contact model (no duplication if same person serves both purposes)
    - Boolean flags for emergency and general contact designation
    - Relationship type tracking
    - Up to 2 phone numbers per contact
    - Email and address information
    - Validation for phone number consistency
    """

    class Relationship(models.TextChoices):
        """Types of relationships for contacts."""

        FATHER = "FATHER", "Father"
        MOTHER = "MOTHER", "Mother"
        SPOUSE = "SPOUSE", "Spouse"
        PARTNER = "PARTNER", "Partner"
        SIBLING = "SIBLING", "Sibling"
        GRANDPARENT = "GRANDPARENT", "Grandparent"
        GUARDIAN = "GUARDIAN", "Legal Guardian"
        FRIEND = "FRIEND", "Friend"
        OTHER = "OTHER", "Other"

    person: ForeignKey = models.ForeignKey(
        Person,
        related_name="contacts",
        on_delete=models.CASCADE,
    )
    name: CharField = models.CharField(max_length=100)
    relationship: CharField = models.CharField(
        max_length=40,
        choices=Relationship.choices,
        default=Relationship.OTHER,
    )
    primary_phone: CharField = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Can include multiple numbers separated by commas or slashes"),
    )
    secondary_phone: CharField = models.CharField(max_length=100, blank=True)
    email: EmailField = models.EmailField(blank=True)
    address: TextField = models.TextField(blank=True)

    # Purpose flags - a single contact can serve multiple purposes
    is_emergency_contact: BooleanField = models.BooleanField(
        default=False,
        help_text=_("Call for medical emergencies, accidents")
    )
    is_general_contact: BooleanField = models.BooleanField(
        default=False,
        help_text=_("Call for misbehavior, absences, general issues")
    )

    class Meta:
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"
        ordering = ["name"]
        constraints = [
            # Ensure at least one purpose is selected
            models.CheckConstraint(
                check=models.Q(is_emergency_contact=True) | models.Q(is_general_contact=True),
                name="contact_must_have_purpose",
            ),
        ]

    def __str__(self) -> str:
        purposes = []
        if self.is_emergency_contact:
            purposes.append("Emergency")
        if self.is_general_contact:
            purposes.append("General")
        purpose_str = "/".join(purposes)
        return f"{self.name} - {self.get_relationship_display()} ({purpose_str})"  # type: ignore[attr-defined]

    def clean(self):
        """Validate that primary and secondary phone numbers are different."""
        if self.primary_phone and self.secondary_phone and self.primary_phone == self.secondary_phone:
            msg = "Primary and secondary phone numbers must be different."
            raise ValidationError(msg)

        # Ensure at least one purpose is selected
        if not self.is_emergency_contact and not self.is_general_contact:
            msg = "Contact must be designated for at least one purpose (emergency or general)."
            raise ValidationError(msg)


# TeacherLeaveRequest moved to scheduling.models


def student_photo_path(instance, filename):
    """Generate organized path for student photos."""
    timestamp = timezone.now()
    student_id = (
        instance.person.student_profile.student_id if hasattr(instance.person, "student_profile") else "unknown"
    )
    ext = filename.split(".")[-1].lower()
    new_filename = f"{student_id}_{timestamp.strftime('%Y%m%d%H%M%S')}.{ext}"
    return f"student-photos/{timestamp.year}/{timestamp.month:02d}/{new_filename}"


def student_thumbnail_path(instance, filename):
    """Generate path for photo thumbnails."""
    timestamp = timezone.now()
    student_id = (
        instance.person.student_profile.student_id if hasattr(instance.person, "student_profile") else "unknown"
    )
    ext = filename.split(".")[-1].lower()
    new_filename = f"{student_id}_{timestamp.strftime('%Y%m%d%H%M%S')}_thumb.{ext}"
    return f"student-photos/thumbnails/{timestamp.year}/{timestamp.month:02d}/{new_filename}"


class StudentPhoto(AuditModel):
    """Versioned photo storage for students with history tracking.

    This model maintains a complete photo history for each person, supporting
    compliance requirements for regular photo updates. It tracks upload sources,
    timestamps, and verification status while maintaining backwards compatibility
    with the existing Person.photo field.

    Key features:
    - Complete photo version history with timestamps
    - Multiple upload sources (admin, mobile app, import)
    - Automatic thumbnail generation
    - Reminder tracking for 6-month refresh requirement
    - File deduplication via SHA-256 hash
    - Admin verification workflow

    Design decisions:
    - Uses ForeignKey (not OneToOne) to support multiple photos per person
    - Filesystem storage with year/month organization for scalability
    - Separate thumbnail field for performance optimization
    - Soft delete via is_current flag to maintain history
    """

    class UploadSource(models.TextChoices):
        """Sources of photo uploads."""

        ADMIN = "ADMIN", _("Admin Upload")
        MOBILE = "MOBILE", _("Mobile App")
        LEGACY_IMPORT = "LEGACY_IMPORT", _("Legacy System Import")
        API = "API", _("API Upload")
        OTHER = "OTHER", _("Other")

    person: ForeignKey = models.ForeignKey(
        Person,
        on_delete=models.CASCADE,
        related_name="photos",
        verbose_name=_("Person"),
        help_text=_("Person this photo belongs to"),
    )

    photo_file: ImageField = models.ImageField(
        _("Photo File"),
        upload_to=student_photo_path,
        help_text=_("Student photo file (JPEG/PNG, max 5MB)"),
    )

    thumbnail: ImageField = models.ImageField(
        _("Thumbnail"),
        upload_to=student_thumbnail_path,
        blank=True,
        null=True,
        help_text=_("Auto-generated 80x90 thumbnail"),
    )

    upload_timestamp: DateTimeField = models.DateTimeField(
        _("Upload Timestamp"),
        auto_now_add=True,
        help_text=_("When the photo was uploaded"),
    )

    upload_source: CharField = models.CharField(
        _("Upload Source"),
        max_length=20,
        choices=UploadSource.choices,
        default=UploadSource.ADMIN,
        help_text=_("Where the photo was uploaded from"),
    )

    is_current: BooleanField = models.BooleanField(
        _("Is Current"),
        default=True,
        help_text=_("Whether this is the current active photo"),
    )

    verified_by: ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_photos",
        verbose_name=_("Verified By"),
        help_text=_("Staff member who verified this photo"),
    )

    verified_at: DateTimeField = models.DateTimeField(
        _("Verified At"),
        null=True,
        blank=True,
        help_text=_("When the photo was verified"),
    )

    file_hash: CharField = models.CharField(
        _("File Hash"),
        max_length=64,
        unique=True,
        help_text=_("SHA-256 hash of the photo file for deduplication"),
    )

    file_size: PositiveIntegerField = models.PositiveIntegerField(
        _("File Size"),
        help_text=_("File size in bytes"),
    )

    width: PositiveIntegerField = models.PositiveIntegerField(
        _("Width"),
        null=True,
        blank=True,
        help_text=_("Image width in pixels"),
    )

    height: PositiveIntegerField = models.PositiveIntegerField(
        _("Height"),
        null=True,
        blank=True,
        help_text=_("Image height in pixels"),
    )

    # Reminder tracking
    reminder_sent_at: DateTimeField = models.DateTimeField(
        _("Reminder Sent At"),
        null=True,
        blank=True,
        help_text=_("Last time a reminder was sent for photo update"),
    )

    reminder_count: IntegerField = models.IntegerField(
        _("Reminder Count"),
        default=0,
        help_text=_("Number of reminders sent for this photo"),
    )

    skip_reminder: BooleanField = models.BooleanField(
        _("Skip Reminder"),
        default=False,
        help_text=_("Skip reminder for special cases (graduated, exchange students)"),
    )

    # Additional metadata
    original_filename: CharField = models.CharField(
        _("Original Filename"),
        max_length=255,
        blank=True,
        help_text=_("Original filename when uploaded"),
    )

    notes: TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Administrative notes about this photo"),
    )

    class Meta:
        verbose_name = _("Student Photo")
        verbose_name_plural = _("Student Photos")
        ordering = ["-upload_timestamp"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["person", "-upload_timestamp"]),
            models.Index(fields=["is_current", "person"]),
            models.Index(fields=["upload_timestamp"]),
            models.Index(fields=["reminder_sent_at"]),
            models.Index(fields=["file_hash"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["person", "is_current"],
                condition=models.Q(is_current=True),
                name="unique_current_photo",
            ),
        ]

    def __str__(self) -> str:
        person_name = self.person.full_name if self.person else "Unknown"  # type: ignore[attr-defined]
        status = "Current" if self.is_current else f"Historical ({self.upload_timestamp.date()})"
        return f"{person_name} - {status}"

    def save(self, *args, **kwargs):
        """Override save to ensure only one current photo per person."""
        if self.is_current:
            # Set all other photos for this person to not current
            StudentPhoto.objects.filter(person=self.person, is_current=True).exclude(pk=self.pk).update(
                is_current=False,
            )

        super().save(*args, **kwargs)

    @property
    def age_in_days(self) -> int:
        """Calculate age of photo in days."""
        return (timezone.now() - self.upload_timestamp).days

    @property
    def age_in_months(self) -> float:
        """Calculate age of photo in months."""
        return self.age_in_days / 30.0

    @property
    def needs_update(self) -> bool:
        """Check if photo needs update based on 6-month rule."""
        if self.skip_reminder:
            return False

        # Special case for monks - 12 month period
        if hasattr(self.person, "student_profile") and self.person.student_profile.is_monk:
            return self.age_in_months >= 12

        return self.age_in_months >= 6

    @property
    def needs_reminder(self) -> bool:
        """Check if reminder should be sent (5+ months old)."""
        if self.skip_reminder:
            return False

        # Special case for monks
        if hasattr(self.person, "student_profile") and self.person.student_profile.is_monk:
            return self.age_in_months >= 11 and self.age_in_months < 12

        return self.age_in_months >= 5 and self.age_in_months < 6

    def verify(self, user: "User") -> None:
        """Mark photo as verified by staff member."""
        self.verified_by = user
        self.verified_at = timezone.now()
        self.save(update_fields=["verified_by", "verified_at"])

    def send_reminder(self) -> None:
        """Record that a reminder was sent."""
        self.reminder_sent_at = timezone.now()
        self.reminder_count += 1
        self.save(update_fields=["reminder_sent_at", "reminder_count"])

    @classmethod
    def get_current_photo(cls, person: Person) -> "StudentPhoto | None":
        """Get the current photo for a person."""
        return cls.objects.filter(person=person, is_current=True).first()

    def clean(self) -> None:
        """Validate photo data."""
        super().clean()

        # Validate file size (5MB max)
        if self.photo_file and self.photo_file.size > 5 * 1024 * 1024:
            raise ValidationError(
                {"photo_file": _("Photo file size must be less than 5MB.")},
            )
