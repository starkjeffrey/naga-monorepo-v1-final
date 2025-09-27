"""# Common base models and utilities for the Naga SIS project.

This module provides abstract base models and common utilities that can be
used across all apps in the system while maintaining clean architecture.

USAGE PATTERNS:

1. Basic Timestamp Tracking:
   class MyModel(TimestampedModel):
       name: models.CharField = models.CharField(max_length=100)

2. Soft Delete Functionality:
   class MyModel(SoftDeleteModel):
       name: models.CharField = models.CharField(max_length=100)

   # Usage:
   instance.soft_delete()  # Mark as deleted
   instance.restore()      # Restore from soft delete
   MyModel.objects.all()   # Only non-deleted records
   MyModel.all_objects.all()  # All records including deleted

3. User Tracking:
   class MyModel(UserTrackingModel):
       name: models.CharField = models.CharField(max_length=100)
   # Remember to set created_by/updated_by in your views/serializers

4. Status Management:
   class MyModel(StatusModel):
       STATUS_CHOICES = [
           ('draft', 'Draft'),
           ('published', 'Published'),
           ('archived', 'Archived'),
       ]
       name: models.CharField = models.CharField(max_length=100)

5. UUID Primary Keys:
   class MyModel(UUIDModel):
       name: models.CharField = models.CharField(max_length=100)

6. Auto-Slug Generation:
   class MyModel(SlugModel):
       SLUG_SOURCE_FIELD = 'name'
       name: models.CharField = models.CharField(max_length=100)

7. Comprehensive Audit Trail (NEW models):
   class MyModel(ComprehensiveAuditModel):
       name: models.CharField = models.CharField(max_length=100)
   # Includes: UUID primary key, timestamps, user tracking, soft delete

8. User Audit Trail (EXISTING models):
   class MyModel(UserAuditModel):
       name: models.CharField = models.CharField(max_length=100)
   # Includes: timestamps, user tracking, soft delete (preserves existing primary key)

9. Simple Audit Trail (legacy):
   class MyModel(AuditModel):
       name: models.CharField = models.CharField(max_length=100)
   # Includes: timestamps and soft delete only

CLEAN ARCHITECTURE BENEFITS:
- No circular dependencies between apps
- Consistent audit patterns across the system
- Reusable components that reduce code duplication
- Standard interfaces for common operations
- Proper separation of concerns
"""

import uuid
from typing import TYPE_CHECKING, Any, ClassVar

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import BooleanField, CharField, DateTimeField, ForeignKey, Manager, UUIDField
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .constants import Buildings, get_building_display_name


class SoftDeleteManager(models.Manager):
    """Manager that excludes soft-deleted records by default.

    Provides methods to access all records including deleted ones.
    """

    def get_queryset(self):
        """Return only non-deleted records by default."""
        return super().get_queryset().filter(is_deleted=False)

    def with_deleted(self):
        """Return all records including soft-deleted ones."""
        return super().get_queryset()

    def only_deleted(self):
        """Return only soft-deleted records."""
        return super().get_queryset().filter(is_deleted=True)


class ActiveManager(models.Manager):
    """Manager that returns only active records by default.

    Useful for models with status fields.
    """

    def get_queryset(self):
        """Return only active records by default."""
        return super().get_queryset().filter(status="active")


class TimestampedModel(models.Model):
    """Abstract base model that provides self-updating timestamp fields.

    This model should be used as a base for most models in the system
    to provide consistent audit trail capabilities.
    """

    created_at: DateTimeField = models.DateTimeField(
        _("Created at"),
        auto_now_add=True,
        help_text=_("Date and time when the record was created"),
    )
    updated_at: DateTimeField = models.DateTimeField(
        _("Updated at"),
        auto_now=True,
        help_text=_("Date and time when the record was last updated"),
    )

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """Abstract base model that provides soft delete functionality.

    Instead of permanently deleting records, this model marks them
    as deleted and hides them from normal queries.
    """

    is_deleted: BooleanField = models.BooleanField(
        _("Is deleted"),
        default=False,
        help_text=_("Indicates if this record has been soft deleted"),
    )
    deleted_at: DateTimeField = models.DateTimeField(
        _("Deleted at"),
        null=True,
        blank=True,
        help_text=_("Date and time when the record was marked as deleted"),
    )

    # Managers (should come after fields per Django style guide)
    all_objects: Manager = models.Manager()  # Access to all records including deleted
    objects = SoftDeleteManager()

    class Meta:
        abstract = True

    def soft_delete(self):
        """Mark this record as deleted."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])


class UUIDModel(models.Model):
    """Abstract base model that uses UUID as primary key.

    Provides a universally unique identifier that's not sequential,
    improving security and enabling distributed systems.
    """

    id: UUIDField = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        help_text=_("Unique identifier for this record"),
    )

    class Meta:
        abstract = True


class UserTrackingModel(models.Model):
    """Abstract base model that tracks which user created/modified records.

    This mixin provides user audit trail capabilities without creating
    circular dependencies by using get_user_model().
    """

    created_by: ForeignKey = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_created",
        verbose_name=_("Created by"),
        help_text=_("User who created this record"),
    )
    updated_by: ForeignKey = models.ForeignKey(
        get_user_model(),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(app_label)s_%(class)s_updated",
        verbose_name=_("Updated by"),
        help_text=_("User who last updated this record"),
    )

    class Meta:
        abstract = True


class StatusModel(models.Model):
    """Abstract base model for entities that have status tracking.

    Provides a flexible status field with change tracking using proper
    field tracking without database queries for better performance and reliability.
    Override STATUS_CHOICES in your model to define valid statuses.
    """

    # Default status choices - override in child models
    STATUS_CHOICES = [
        ("active", _("Active")),
        ("inactive", _("Inactive")),
        ("draft", _("Draft")),
        ("archived", _("Archived")),
    ]

    status: CharField = models.CharField(
        _("Status"),
        max_length=20,
        choices=STATUS_CHOICES,
        default="active",
        help_text=_("Current status of this record"),
    )
    status_changed_at: DateTimeField = models.DateTimeField(
        _("Status changed at"),
        auto_now_add=True,
        help_text=_("Date and time when status was last changed"),
    )

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        """Initialize field tracking for status changes."""
        super().__init__(*args, **kwargs)
        # Track the original status value for change detection
        self._original_status = self.status if self.pk else None

    def save(self, *args, **kwargs):
        """Update status_changed_at when status changes without database query."""
        # For new instances, always set status_changed_at
        if self.pk is None:
            self.status_changed_at = timezone.now()
        elif self._original_status != self.status:
            # Check if status actually changed using tracked original value
            self.status_changed_at = timezone.now()

        super().save(*args, **kwargs)

        # Update the tracked original value after successful save
        self._original_status = self.status

    @classmethod
    def from_db(cls, db, field_names, values):
        """Initialize field tracking when loading from database."""
        instance = super().from_db(db, field_names, values)
        # Track the original status value from database
        instance._original_status = instance.status
        return instance

    def refresh_from_db(self, using=None, fields=None, from_queryset=None):
        """Update field tracking when refreshing from database."""
        super().refresh_from_db(using=using, fields=fields, from_queryset=from_queryset)
        # Update tracked original value after refresh
        self._original_status = self.status


class SlugModel(models.Model):
    """Abstract base model that provides slug functionality.

    Automatically generates and maintains a slug field based on a title/name field.
    Child models should define SLUG_SOURCE_FIELD to specify the source field.
    """

    slug: models.SlugField = models.SlugField(
        _("Slug"),
        max_length=150,
        unique=True,
        help_text=_("URL-friendly version of the name"),
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """Auto-generate slug if not provided."""
        if not self.slug:
            if not hasattr(self, "SLUG_SOURCE_FIELD"):
                from django.core.exceptions import ImproperlyConfigured

                raise ImproperlyConfigured(f"{self.__class__.__name__} must define SLUG_SOURCE_FIELD.")

            source_field = getattr(self, self.SLUG_SOURCE_FIELD)
            if source_field:
                self.slug = slugify(source_field)
        super().save(*args, **kwargs)


class OrderedModel(models.Model):
    """Abstract base model that provides ordering functionality.

    Maintains an order field that can be used for sorting records.
    """

    order: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Order"),
        default=0,
        help_text=_("Order for sorting records"),
    )

    class Meta:
        abstract = True
        ordering = ["order"]


class ComprehensiveAuditModel(
    UUIDModel,
    TimestampedModel,
    UserTrackingModel,
    SoftDeleteModel,
):
    """Most comprehensive audit model combining all tracking capabilities.

    This model is designed for NEW models that need maximum audit trail capabilities
    from the start. It combines all audit mixins including UUID primary keys.

    FEATURES:
    - UUID primary key for security and distribution
    - Timestamp tracking (created_at, updated_at)
    - User tracking (created_by, updated_by)
    - Soft delete functionality (is_deleted, deleted_at)

    WHEN TO USE:
    - New models that need comprehensive audit trails
    - Models that will be distributed across systems
    - Models requiring non-sequential primary keys for security
    - Models that need all audit capabilities from day one

    ADMIN INTEGRATION:
    Use with ComprehensiveAuditMixin for automatic admin audit displays:

        from apps.common.admin_mixins import ComprehensiveAuditMixin

        class MyModelAdmin(ComprehensiveAuditMixin, admin.ModelAdmin):
            list_display = ['name', 'created_by_display', 'updated_by_display']

    FIELDS PROVIDED:
    - id: UUIDField (primary key)
    - created_at: DateTimeField (auto-set on creation)
    - updated_at: DateTimeField (auto-updated on save)
    - created_by: ForeignKey to User (set in admin/views)
    - updated_by: ForeignKey to User (set in admin/views)
    - is_deleted: BooleanField (for soft delete)
    - deleted_at: DateTimeField (timestamp of soft deletion)

    MANAGERS:
    - objects: SoftDeleteManager (excludes soft-deleted records)
    - all_objects: Manager (includes all records)

    EXAMPLE USAGE:
        class NewDocument(ComprehensiveAuditModel):
            title: models.CharField = models.CharField(max_length=200)
            content: models.TextField = models.TextField()

            class Meta:
                verbose_name = "Document"
                verbose_name_plural = "Documents"
    """

    class Meta:
        abstract = True


class UserAuditModel(
    TimestampedModel,
    UserTrackingModel,
    SoftDeleteModel,
):
    """Audit model that adds user tracking without changing primary key.

    This model is designed for EXISTING models that already have BigAutoField
    primary keys but need comprehensive audit capabilities added to them.
    It provides all audit features except UUID primary keys.

    FEATURES:
    - Timestamp tracking (created_at, updated_at)
    - User tracking (created_by, updated_by)
    - Soft delete functionality (is_deleted, deleted_at)
    - Preserves existing BigAutoField primary keys

    WHEN TO USE:
    - Existing models that need audit capabilities added
    - Models that must maintain existing primary key structure
    - Models with existing foreign key relationships
    - Migration scenarios where changing primary keys would be problematic

    ADMIN INTEGRATION:
    Use with ComprehensiveAuditMixin for automatic admin audit displays:

        from apps.common.admin_mixins import ComprehensiveAuditMixin

        class MyModelAdmin(ComprehensiveAuditMixin, admin.ModelAdmin):
            list_display = ['name', 'created_by_display', 'updated_by_display']

    FIELDS PROVIDED:
    - id: BigAutoField (preserved existing primary key)
    - created_at: DateTimeField (auto-set on creation)
    - updated_at: DateTimeField (auto-updated on save)
    - created_by: ForeignKey to User (set in admin/views)
    - updated_by: ForeignKey to User (set in admin/views)
    - is_deleted: BooleanField (for soft delete)
    - deleted_at: DateTimeField (timestamp of soft deletion)

    MANAGERS:
    - objects: SoftDeleteManager (excludes soft-deleted records)
    - all_objects: Manager (includes all records)

    MIGRATION EXAMPLE:
        # Before migration:
        class Invoice(models.Model):
            amount: models.DecimalField = models.DecimalField(max_digits=10, decimal_places=2)

        # After migration:
        class Invoice(UserAuditModel):
            amount: models.DecimalField = models.DecimalField(max_digits=10, decimal_places=2)

        # Django migration will add: created_by, updated_by, created_at,
        # updated_at, is_deleted, deleted_at fields

    CURRENT IMPLEMENTATIONS:
    - Finance models: PricingTier, Invoice, Payment, etc.
    - Grading models: GradingScale, ClassPartGrade, GPARecord, etc.
    - Enrollment models: ProgramEnrollment, ClassHeaderEnrollment, etc.
    - Academic records: DocumentRequest, GeneratedDocument, etc.
    - Scholarships: Sponsor, SponsoredStudent, Scholarship
    """

    class Meta:
        abstract = True


class OverlapCheckMixin:
    """Mixin that provides overlap validation for date range models.

    This mixin validates that date ranges don't overlap with existing records.
    Useful for scheduling (classes, room bookings), academic terms, etc.

    USAGE:

    1. Basic date range overlap check:
       class ClassSchedule(OverlapCheckMixin, models.Model):
           start_date: models.DateTimeField = models.DateTimeField()
           end_date: models.DateTimeField = models.DateTimeField()

           def clean(self):
               super().clean()
               self.validate_no_overlaps()

    2. Custom field names:
       class Term(OverlapCheckMixin, models.Model):
           _start_field_name = "term_start"
           _end_field_name = "term_end"
           term_start: models.DateField = models.DateField()
           term_end: models.DateField = models.DateField()

           def clean(self):
               super().clean()
               self.validate_no_overlaps("term_start", "term_end")

    CLEAN ARCHITECTURE BENEFITS:
    - No external dependencies or circular imports
    - Self-contained validation logic
    - Configurable field names for flexibility
    - Proper Django validation pattern
    """

    if TYPE_CHECKING:
        from django.db.models import Manager

        objects: Manager[Any]

    pk: Any
    _meta: Any
    _start_field_name: str = "start_date"
    _end_field_name: str = "end_date"

    def validate_no_overlaps(self, start_field=None, end_field=None, additional_filters=None):
        """Validate that this record's date range doesn't overlap with existing records.

        Performance optimized to use database indexes effectively.
        For best performance, ensure your model has a composite index on:
        (start_field, end_field) or use additional_filters to limit scope.

        Args:
            start_field: Name of the start date field (defaults to _start_field_name)
            end_field: Name of the end date field (defaults to _end_field_name)
            additional_filters: Additional filters to limit the scope (e.g., {'room': self.room})

        Raises:
            ValidationError: If an overlapping record is found
        """
        start_field_name = start_field or self._start_field_name
        end_field_name = end_field or self._end_field_name

        start_date = getattr(self, start_field_name)
        end_date = getattr(self, end_field_name)

        if not start_date or not end_date:
            return

        # Build optimized overlap query
        overlap_filter = {
            f"{start_field_name}__lte": end_date,
            f"{end_field_name}__gte": start_date,
        }

        # Add additional filters to reduce query scope (important for performance)
        if additional_filters:
            overlap_filter.update(additional_filters)

        # Use exists() for better performance - stops at first match
        queryset = self.__class__.objects.filter(**overlap_filter)

        if self.pk:
            queryset = queryset.exclude(pk=self.pk)

        if queryset.exists():
            msg = f"Date range overlaps with existing {self._meta.verbose_name}"
            raise ValidationError(msg)


class AuditModel(TimestampedModel, SoftDeleteModel):
    """Complete audit trail model combining timestamps and soft delete.

    This provides a comprehensive base for models that need full
    audit capabilities without creating circular dependencies.
    """

    class Meta:
        abstract = True


class SystemAuditLog(TimestampedModel):
    """Centralized audit log for all management override actions across the system.

    This model provides a single place to track all override actions for compliance
    and administrative purposes while maintaining clean architecture principles.
    """

    class ActionType(models.TextChoices):
        """Types of override actions that can be logged."""

        ENROLLMENT_OVERRIDE = "ENROLLMENT_OVERRIDE", _("Enrollment Override")
        REPEAT_PREVENTION_OVERRIDE = "REPEAT_PREVENTION_OVERRIDE", _("Repeat Prevention Override")
        PREREQUISITE_OVERRIDE = "PREREQUISITE_OVERRIDE", _("Prerequisite Override")
        CAPACITY_OVERRIDE = "CAPACITY_OVERRIDE", _("Capacity Override")
        ACADEMIC_POLICY_OVERRIDE = "ACADEMIC_POLICY_OVERRIDE", _("Academic Policy Override")
        REGISTRATION_POLICY_OVERRIDE = "REGISTRATION_POLICY_OVERRIDE", _("Registration Policy Override")
        LANGUAGE_LEVEL_SKIP = "LANGUAGE_LEVEL_SKIP", _("Language Level Skip")
        LANGUAGE_PROMOTION_OVERRIDE = "LANGUAGE_PROMOTION_OVERRIDE", _("Language Promotion Override")

    # Core audit information
    action_type: models.CharField = models.CharField(
        _("Action Type"),
        max_length=50,
        choices=ActionType.choices,
        help_text=_("Type of override action performed"),
    )
    performed_by: models.ForeignKey = models.ForeignKey(
        get_user_model(),
        on_delete=models.PROTECT,
        related_name="performed_overrides",
        verbose_name=_("Performed By"),
        help_text=_("User who performed the override action"),
    )

    # Target information using ContentType framework
    content_type: models.ForeignKey = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name=_("Content Type"),
        help_text=_("Type of the target object"),
    )
    object_id: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Object ID"),
        help_text=_("ID of the specific object that was affected"),
    )
    content_object = GenericForeignKey("content_type", "object_id")

    target_app: models.CharField = models.CharField(
        _("Target App"),
        max_length=50,
        blank=True,
        null=True,
        help_text=_("DEPRECATED: Use content_type instead"),
    )
    target_model: models.CharField = models.CharField(
        _("Target Model"),
        max_length=50,
        blank=True,
        null=True,
        help_text=_("DEPRECATED: Use content_type instead"),
    )
    target_object_id: models.CharField = models.CharField(
        _("Target Object ID"),
        max_length=100,
        blank=True,
        null=True,
        help_text=_("DEPRECATED: Use object_id instead"),
    )

    # Override details
    override_reason: models.TextField = models.TextField(
        _("Override Reason"),
        help_text=_("Detailed reason for the override action"),
    )
    original_restriction: models.TextField = models.TextField(
        _("Original Restriction"),
        help_text=_("Description of the rule/restriction that was overridden"),
    )
    override_details: models.JSONField = models.JSONField(
        _("Override Details"),
        default=dict,
        blank=True,
        help_text=_("Additional details about the override in JSON format"),
    )

    # Context information
    ip_address: models.GenericIPAddressField = models.GenericIPAddressField(
        _("IP Address"),
        null=True,
        blank=True,
        help_text=_("IP address of the user who performed the override"),
    )
    user_agent: models.TextField = models.TextField(
        _("User Agent"),
        blank=True,
        help_text=_("Browser/client information for the override action"),
    )

    class Meta:
        verbose_name = _("System Audit Log")
        verbose_name_plural = _("System Audit Logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["action_type", "created_at"]),
            models.Index(fields=["performed_by", "created_at"]),
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.action_type} by {self.performed_by} on {self.created_at}"

    @classmethod
    def log_override(
        cls,
        action_type: str,
        performed_by,
        target_app: str | None = None,
        target_model: str | None = None,
        target_object_id: str | None = None,
        target_object=None,
        override_reason: str = "",
        original_restriction: str = "",
        override_details: dict | None = None,
        request=None,
    ) -> "SystemAuditLog":
        """Create an audit log entry for an override action.

        Args:
            action_type: Type of override action
            performed_by: User performing the override
            target_app: Django app name (DEPRECATED - use target_object instead)
            target_model: Model name (DEPRECATED - use target_object instead)
            target_object_id: ID of affected object (DEPRECATED - use target_object instead)
            target_object: The actual object being audited (PREFERRED)
            override_reason: Reason for override
            original_restriction: Description of overridden rule
            override_details: Additional details (optional)
            request: HTTP request object for IP/user agent (optional)

        Returns:
            Created SystemAuditLog instance
        """
        log_data = {
            "action_type": action_type,
            "performed_by": performed_by,
            "override_reason": override_reason,
            "original_restriction": original_restriction,
            "override_details": override_details or {},
        }

        # Use ContentType framework if target_object is provided (preferred)
        if target_object is not None:
            log_data["content_type"] = ContentType.objects.get_for_model(target_object)
            log_data["object_id"] = target_object.pk
            # Still populate legacy fields for compatibility
            log_data["target_app"] = target_object._meta.app_label
            log_data["target_model"] = target_object._meta.model_name
            log_data["target_object_id"] = str(target_object.pk)
        else:
            # Fallback to legacy string-based approach
            log_data["target_app"] = target_app
            log_data["target_model"] = target_model
            log_data["target_object_id"] = str(target_object_id) if target_object_id else ""

            # Try to populate ContentType fields if we can resolve the model
            if target_app and target_model:
                try:
                    content_type = ContentType.objects.get(app_label=target_app, model=target_model)
                    log_data["content_type"] = content_type
                    if target_object_id:
                        try:
                            log_data["object_id"] = int(target_object_id)
                        except (ValueError, TypeError):
                            # If target_object_id isn't a valid integer, skip object_id
                            pass
                except ContentType.DoesNotExist:
                    # ContentType not found, skip ContentType fields
                    pass

        if request:
            # Extract IP address securely
            # REMOTE_ADDR is more reliable as it's set by the server's connection to the client
            log_data["ip_address"] = request.META.get("REMOTE_ADDR")

            # If behind a trusted proxy, we can consider x-forwarded-for as additional info
            # but we still primarily trust REMOTE_ADDR for security purposes
            x_forwarded_for = request.headers.get("x-forwarded-for")
            if x_forwarded_for:
                # Store forwarded info in override_details for reference but don't trust it
                if "forwarded_ips" not in log_data["override_details"]:
                    log_data["override_details"]["forwarded_ips"] = x_forwarded_for.split(",")

            # Extract user agent
            log_data["user_agent"] = request.headers.get("user-agent", "")

        return cls.objects.create(**log_data)


class StudentActivityLogManager(models.Manager):
    """Manager for StudentActivityLog with filtering methods."""

    def get_student_visible_activities(self):
        """Get activities that students are allowed to see."""
        return self.filter(
            visibility__in=[
                "STUDENT_VISIBLE",
                "PUBLIC",
            ]
        )


class StudentActivityLog(TimestampedModel):
    """Comprehensive audit log for all student activities and actions.

    This model provides a searchable, permanent record of all student-related
    activities including enrollment changes, level progressions, overrides,
    and administrative actions. Designed for easy searching by student, term,
    class, and date range.

    """

    class ActivityType(models.TextChoices):
        """Types of student activities that can be logged."""

        # Enrollment activities
        CLASS_ENROLLMENT = "CLASS_ENROLLMENT", _("Class Enrollment")
        CLASS_WITHDRAWAL = "CLASS_WITHDRAWAL", _("Class Withdrawal")
        CLASS_COMPLETION = "CLASS_COMPLETION", _("Class Completion")

        # Language program activities
        LANGUAGE_PROMOTION = "LANGUAGE_PROMOTION", _("Language Level Promotion")
        LANGUAGE_LEVEL_SKIP = "LANGUAGE_LEVEL_SKIP", _("Language Level Skip")
        LANGUAGE_PROGRAM_TRANSFER = "LANGUAGE_PROGRAM_TRANSFER", _("Language Program Transfer")

        # Academic activities
        GRADE_ASSIGNMENT = "GRADE_ASSIGNMENT", _("Grade Assignment")
        GRADE_CHANGE = "GRADE_CHANGE", _("Grade Change")
        GRADUATION = "GRADUATION", _("Graduation Recorded")

        # Administrative actions
        PROGRAM_ENROLLMENT = "PROGRAM_ENROLLMENT", _("Program Enrollment")
        PROGRAM_WITHDRAWAL = "PROGRAM_WITHDRAWAL", _("Program Withdrawal")
        STUDENT_STATUS_CHANGE = "STUDENT_STATUS_CHANGE", _("Student Status Change")
        MONK_STATUS_CHANGE = "MONK_STATUS_CHANGE", _("Monk Status Change")

        # Override activities
        MANAGEMENT_OVERRIDE = "MANAGEMENT_OVERRIDE", _("Management Override Applied")
        REPEAT_PREVENTION_OVERRIDE = "REPEAT_PREVENTION_OVERRIDE", _("Repeat Prevention Override")
        PREREQUISITE_OVERRIDE = "PREREQUISITE_OVERRIDE", _("Prerequisite Override")
        CAPACITY_OVERRIDE = "CAPACITY_OVERRIDE", _("Capacity Override")

        # Other activities
        ATTENDANCE_RECORD = "ATTENDANCE_RECORD", _("Attendance Record")
        DOCUMENT_REQUEST = "DOCUMENT_REQUEST", _("Document Request")
        SCHOLARSHIP_ASSIGNED = "SCHOLARSHIP_ASSIGNED", _("Scholarship Assigned")
        SCHOLARSHIP_REVOKED = "SCHOLARSHIP_REVOKED", _("Scholarship Revoked")

        # Profile management
        PROFILE_CREATE = "PROFILE_CREATE", _("Student Profile Created")
        PROFILE_UPDATE = "PROFILE_UPDATE", _("Student Profile Updated")
        PROFILE_MERGE = "PROFILE_MERGE", _("Student Profiles Merged")

    # Core student information
    student_number: models.CharField = models.CharField(
        _("Student Number"),
        max_length=20,
        db_index=True,
        help_text=_("Student number for easy searching"),
    )
    student_name: models.CharField = models.CharField(
        _("Student Name"),
        max_length=200,
        help_text=_("Student name at time of action (for historical reference)"),
    )

    # Activity details
    activity_type: models.CharField = models.CharField(
        _("Activity Type"),
        max_length=40,
        choices=ActivityType.choices,
        db_index=True,
        help_text=_("Type of activity performed"),
    )
    description: models.TextField = models.TextField(
        _("Description"),
        help_text=_("Detailed description of the activity"),
    )

    # Context information (nullable for flexibility)
    term_name: models.CharField = models.CharField(
        _("Term Name"),
        max_length=100,
        blank=True,
        db_index=True,
        help_text=_("Term when activity occurred (if applicable)"),
    )
    class_code: models.CharField = models.CharField(
        _("Class Code"),
        max_length=20,
        blank=True,
        db_index=True,
        help_text=_("Course/class code (if applicable)"),
    )
    class_section: models.CharField = models.CharField(
        _("Class Section"),
        max_length=10,
        blank=True,
        help_text=_("Class section (if applicable)"),
    )
    program_name: models.CharField = models.CharField(
        _("Program Name"),
        max_length=100,
        blank=True,
        help_text=_("Academic or language program (if applicable)"),
    )

    # Additional details in JSON format for flexibility
    activity_details: models.JSONField = models.JSONField(
        _("Activity Details"),
        default=dict,
        blank=True,
        help_text=_("Additional structured details about the activity"),
    )

    # Administrative information
    performed_by: models.ForeignKey = models.ForeignKey(
        get_user_model(),
        on_delete=models.PROTECT,
        related_name="student_activities_performed",
        verbose_name=_("Performed By"),
        help_text=_("Staff member who performed or initiated the action"),
    )
    is_system_generated: models.BooleanField = models.BooleanField(
        _("System Generated"),
        default=False,
        help_text=_("Whether this log entry was automatically generated"),
    )

    # Visibility control
    class VisibilityLevel(models.TextChoices):
        """Control who can see this log entry."""

        STAFF_ONLY = "STAFF_ONLY", _("Staff Only")
        STUDENT_VISIBLE = "STUDENT_VISIBLE", _("Student Can View")
        PUBLIC = "PUBLIC", _("Public Record")

    visibility: models.CharField = models.CharField(
        _("Visibility"),
        max_length=20,
        choices=VisibilityLevel.choices,
        default=VisibilityLevel.STAFF_ONLY,
        help_text=_("Who can view this audit log entry"),
    )

    # Manager
    objects = StudentActivityLogManager()

    # Clean architecture: Use string-based references instead of foreign keys
    # to prevent circular dependencies between apps. The string fields above
    # (student_number, term_name, class_code) provide sufficient querying capability.
    #
    # ARCHITECTURAL DECISION: Removed foreign key references to maintain clean
    # architecture and prevent circular dependencies. All querying can be done
    # through the indexed string fields which are more stable anyway since they
    # don't break when records are deleted.

    class Meta:
        verbose_name = _("Student Audit Log")
        verbose_name_plural = _("Student Audit Logs")
        ordering = ["-created_at"]
        indexes = [
            # Primary search indexes
            models.Index(fields=["student_number", "-created_at"]),
            models.Index(fields=["activity_type", "-created_at"]),
            models.Index(fields=["term_name", "-created_at"]),
            models.Index(fields=["class_code", "-created_at"]),
            # Compound search indexes
            models.Index(fields=["student_number", "term_name", "-created_at"]),
            models.Index(fields=["student_number", "class_code", "-created_at"]),
            models.Index(fields=["student_number", "activity_type", "-created_at"]),
            # Date range searches
            models.Index(fields=["created_at"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.student_number}: {self.activity_type} on {self.created_at.strftime('%Y-%m-%d')}"

    @classmethod
    def log_student_activity(
        cls,  # Remove problematic type hint that causes inheritance issues
        student,  # Can be StudentProfile instance or None
        activity_type: str,
        description: str,
        performed_by,
        student_number: str | None = None,
        student_name: str | None = None,
        term=None,
        class_header=None,
        program_name: str = "",
        activity_details: dict | None = None,
        *,
        is_system_generated: bool = False,
    ):  # Return type varies based on inheritance, removing specific type
        """Create a student audit log entry.

        Args:
            student: StudentProfile instance (can be None for historical records)
            activity_type: Type of activity from ActivityType choices
            description: Human-readable description of what happened
            performed_by: User who performed the action
            student_number: Student number (required if student is None)
            student_name: Student name (optional, auto-filled from student if available)
            term: Term instance (optional)
            class_header: ClassHeader instance (optional)
            program_name: Program name (optional)
            activity_details: Additional structured details (optional)
            is_system_generated: Whether this is an automated log entry

        Returns:
            Created StudentAuditLog instance
        """
        # Extract student information
        if student:
            student_number = str(student.student_id)  # Use student_id as student_number
            student_name = student_name or student.person.full_name
        elif not student_number:
            msg = "Either student instance or student_number must be provided"
            raise ValueError(msg)

        # Extract context information
        term_name = term.code if term else ""
        class_code = class_header.course.code if class_header else ""
        class_section = class_header.section_id if class_header else ""

        return cls.objects.create(
            student_number=student_number,
            student_name=student_name or "",
            activity_type=activity_type,
            description=description,
            term_name=term_name,
            class_code=class_code,
            class_section=class_section,
            program_name=program_name,
            activity_details=activity_details or {},
            performed_by=performed_by,
            is_system_generated=is_system_generated,
        )

    @classmethod
    def search_student_activities(
        cls,
        student_number: str | None = None,
        activity_type: str | None = None,
        term_name: str | None = None,
        class_code: str | None = None,
        date_from=None,
        date_to=None,
        limit: int = 100,
    ):
        """Search student activities with various filters.

        Args:
            student_number: Filter by student number
            activity_type: Filter by activity type
            term_name: Filter by term name
            class_code: Filter by class code
            date_from: Filter by date range start
            date_to: Filter by date range end
            limit: Maximum number of results

        Returns:
            QuerySet of matching StudentAuditLog entries
        """
        filters = {}
        if student_number:
            filters["student_number"] = student_number
        if activity_type:
            filters["activity_type"] = activity_type
        if term_name:
            filters["term_name"] = term_name
        if class_code:
            filters["class_code"] = class_code
        if date_from:
            filters["created_at__gte"] = date_from
        if date_to:
            filters["created_at__lte"] = date_to

        # Unpack the dictionary of active filters directly into the filter method
        queryset = cls.objects.filter(**filters)
        return queryset.order_by("-created_at")[:limit]

    @classmethod
    def log_status_change(cls, student, old_status: str, new_status: str, user, notes: str = ""):
        """Helper method to log student status changes."""
        student_number = str(student.student_id) if hasattr(student, "student_id") else str(student)
        student_name = student.person.full_name if hasattr(student, "person") else ""

        return cls.objects.create(
            student_number=student_number,
            student_name=student_name,
            activity_type=cls.ActivityType.STUDENT_STATUS_CHANGE,
            description=f"Status changed from {old_status} to {new_status}",
            activity_details={
                "old_status": old_status,
                "new_status": new_status,
                "notes": notes,
            },
            performed_by=user,
            visibility=cls.VisibilityLevel.STUDENT_VISIBLE,
        )

    @classmethod
    def log_enrollment(cls, student, class_header, term, user, action: str = "enrolled"):
        """Helper method to log class enrollment actions."""
        activity_type = {
            "enrolled": cls.ActivityType.CLASS_ENROLLMENT,
            "withdrawn": cls.ActivityType.CLASS_WITHDRAWAL,
            "completed": cls.ActivityType.CLASS_COMPLETION,
        }.get(action, cls.ActivityType.CLASS_ENROLLMENT)

        student_number = str(student.student_id) if hasattr(student, "student_id") else str(student)
        student_name = student.person.full_name if hasattr(student, "person") else ""

        return cls.objects.create(
            student_number=student_number,
            student_name=student_name,
            activity_type=activity_type,
            description=f"Student {action} in {class_header.course.code} Section {class_header.section_id}",
            term_name=term.code if term else "",
            class_code=class_header.course.code if class_header else "",
            class_section=class_header.section_id if class_header else "",
            performed_by=user,
            visibility=cls.VisibilityLevel.STUDENT_VISIBLE,
        )

    @classmethod
    def log_grade_change(
        cls,
        student,
        class_code: str,
        old_grade: str,
        new_grade: str,
        user,
        reason: str = "",
    ):
        """Helper method to log grade changes."""
        student_number = str(student.student_id) if hasattr(student, "student_id") else str(student)
        student_name = student.person.full_name if hasattr(student, "person") else ""

        return cls.objects.create(
            student_number=student_number,
            student_name=student_name,
            activity_type=cls.ActivityType.GRADE_CHANGE,
            description=f"Grade changed from {old_grade} to {new_grade} in {class_code}",
            class_code=class_code,
            activity_details={
                "old_grade": old_grade,
                "new_grade": new_grade,
                "reason": reason,
            },
            performed_by=user,
            visibility=cls.VisibilityLevel.STUDENT_VISIBLE,
        )

    @classmethod
    def log_override(cls, student, override_type: str, reason: str, user, **context):
        """Helper method to log management overrides."""
        student_number = str(student.student_id) if hasattr(student, "student_id") else str(student)
        student_name = student.person.full_name if hasattr(student, "person") else ""

        # Map override types to activity types
        activity_type_map = {
            "repeat_prevention": cls.ActivityType.REPEAT_PREVENTION_OVERRIDE,
            "prerequisite": cls.ActivityType.PREREQUISITE_OVERRIDE,
            "capacity": cls.ActivityType.CAPACITY_OVERRIDE,
            "management": cls.ActivityType.MANAGEMENT_OVERRIDE,
        }

        activity_type = activity_type_map.get(override_type, cls.ActivityType.MANAGEMENT_OVERRIDE)

        return cls.objects.create(
            student_number=student_number,
            student_name=student_name,
            activity_type=activity_type,
            description=f"{override_type.replace('_', ' ').title()} override applied: {reason}",
            activity_details={
                "override_type": override_type,
                "reason": reason,
                **context,
            },
            performed_by=user,
            visibility=cls.VisibilityLevel.STAFF_ONLY,
        )


class RoomManager(SoftDeleteManager["Room"]):
    """Custom manager for Room model with atomic code generation."""

    def create_with_code(self, **kwargs) -> "Room":
        """Create a new room with an atomically generated code.

        This method ensures thread-safe code generation by using database-level
        locking to prevent race conditions during concurrent room creation.
        """
        from django.db import transaction

        # Extract code if provided (allow manual override)
        code = kwargs.pop("code", None)

        # Create the room instance
        room = self.model(**kwargs)

        # Use atomic transaction with select_for_update to ensure thread safety
        with transaction.atomic():
            room.save()

            # Generate code if not provided
            if not code:
                # Lock the room record to prevent concurrent modifications
                room = self.select_for_update().get(pk=room.pk)
                room.code = f"{room.building}{room.id:02d}"  # type: ignore[attr-defined]
                room.save(update_fields=["code"])
            else:
                room.code = code
                room.save(update_fields=["code"])

        return room


class Room(AuditModel):
    """Physical classroom/meeting rooms across campus buildings.

    This model represents the physical spaces where classes and activities
    take place. Includes capacity and equipment information for scheduling
    and room management purposes.
    """

    ROOM_TYPE_CHOICES = [
        ("CLASS", _("Classroom")),
        ("COMP", _("Computer Lab")),
        ("LANG", _("Language Lab")),
        ("CONFERENCE", _("Conference Room")),
        ("MEETING", _("Meeting Room")),
        ("OFFICE", _("Office")),
        ("OTHER", _("Other")),
    ]

    building: models.CharField = models.CharField(
        _("Building"),
        max_length=10,
        choices=[
            (Buildings.MAIN, _("Main Building")),
            (Buildings.WEST, _("West Building")),
            (Buildings.BACK, _("Back Building")),
        ],
        help_text=_("Building where this room is located"),
    )
    name: models.CharField = models.CharField(
        _("Room Name"),
        max_length=100,
        help_text=_("Name or identifier for the room"),
    )
    code: models.CharField = models.CharField(
        _("Room Code"),
        max_length=20,
        unique=True,
        editable=False,
        help_text=_("Auto-generated internal identifier for the room"),
    )
    capacity: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Capacity"),
        help_text=_("Maximum number of people this room can accommodate"),
    )
    room_type: models.CharField = models.CharField(
        _("Room Type"),
        max_length=20,
        choices=ROOM_TYPE_CHOICES,
        default="CLASS",
        help_text=_("Type of room for scheduling purposes"),
    )

    # Equipment and features
    has_projector: models.BooleanField = models.BooleanField(
        _("Has Projector"),
        default=False,
        help_text=_("Whether this room has an overhead projector"),
    )
    has_whiteboard: models.BooleanField = models.BooleanField(
        _("Has Whiteboard"),
        default=True,
        help_text=_("Whether this room has a whiteboard"),
    )
    has_computers: models.BooleanField = models.BooleanField(
        _("Has Computers"),
        default=False,
        help_text=_("Whether this room has computers available"),
    )

    # Status and availability
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this room is currently available for use"),
    )
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional notes about this room"),
    )

    objects = RoomManager()

    class Meta:
        verbose_name = _("Room")
        verbose_name_plural = _("Rooms")
        ordering = ["building", "name"]
        unique_together = [["building", "code"]]

    def __str__(self) -> str:
        """Return a string representation of the room."""
        building_name = get_building_display_name(self.building)
        return f"{building_name} - {self.name}"

    def save(self, *args, **kwargs):
        """Save the room instance.

        Note: For new rooms, prefer using Room.objects.create_with_code()
        which handles atomic code generation safely.
        """
        super().save(*args, **kwargs)

    def get_full_name(self) -> str:
        """Get the full display name including building."""
        building_name = get_building_display_name(self.building)
        return f"{building_name} - {self.name}"

    def clean(self):
        """Validate room data."""
        super().clean()


class Holiday(AuditModel):
    """Cambodian national holidays and institutional holidays.

    This model stores official holidays that affect academic scheduling
    and administrative operations. Used for calendar display and scheduling
    conflict prevention.
    """

    eng_name: models.CharField = models.CharField(
        _("English Name"),
        max_length=200,
        help_text=_("Holiday name in English"),
    )
    khmer_name: models.CharField = models.CharField(
        _("Khmer Name"),
        max_length=200,
        blank=True,
        help_text=_("Holiday name in Khmer"),
    )
    start_date: models.DateField = models.DateField(
        _("Start Date"),
        help_text=_("Date when the holiday begins"),
    )
    end_date: models.DateField = models.DateField(
        _("End Date"),
        help_text=_("Date when the holiday ends"),
    )
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this holiday is currently observed"),
    )
    notes: models.TextField = models.TextField(
        _("Notes"),
        blank=True,
        help_text=_("Additional information about this holiday"),
    )

    class Meta:
        verbose_name = _("Holiday")
        verbose_name_plural = _("Holidays")
        ordering = ["start_date"]
        unique_together = [["eng_name", "start_date"]]

    def __str__(self) -> str:
        """Return string representation of the holiday."""
        if self.start_date == self.end_date:
            return f"{self.eng_name} ({self.start_date})"
        return f"{self.eng_name} ({self.start_date} - {self.end_date})"

    def clean(self):
        """Validate holiday data."""
        super().clean()

        if self.end_date < self.start_date:
            raise ValidationError(
                {"end_date": _("End date cannot be before start date")},
            )

    @property
    def duration_days(self) -> int:
        """Calculate the number of days this holiday spans."""
        return (self.end_date - self.start_date).days + 1

    @property
    def is_multi_day(self) -> bool:
        """Check if this holiday spans multiple days."""
        return self.start_date != self.end_date


class Notification(UserAuditModel):
    """User notifications for system events and activities."""

    class NotificationType(models.TextChoices):
        """Types of notifications."""

        INFO = "INFO", _("Information")
        SUCCESS = "SUCCESS", _("Success")
        WARNING = "WARNING", _("Warning")
        ERROR = "ERROR", _("Error")
        FINANCE = "FINANCE", _("Finance")
        ACADEMIC = "ACADEMIC", _("Academic")
        ENROLLMENT = "ENROLLMENT", _("Enrollment")
        GRADING = "GRADING", _("Grading")
        SYSTEM = "SYSTEM", _("System")

    class Priority(models.TextChoices):
        """Notification priority levels."""

        LOW = "LOW", _("Low")
        NORMAL = "NORMAL", _("Normal")
        HIGH = "HIGH", _("High")
        URGENT = "URGENT", _("Urgent")

    user: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("User"),
    )
    title: models.CharField = models.CharField(
        _("Title"),
        max_length=255,
        help_text=_("Brief notification title"),
    )
    message: models.TextField = models.TextField(
        _("Message"),
        help_text=_("Detailed notification message"),
    )
    notification_type: models.CharField = models.CharField(
        _("Type"),
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO,
    )
    priority: models.CharField = models.CharField(
        _("Priority"),
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
    )
    is_read: models.BooleanField = models.BooleanField(
        _("Is Read"),
        default=False,
        help_text=_("Whether the user has read this notification"),
    )
    read_at: models.DateTimeField = models.DateTimeField(
        _("Read At"),
        null=True,
        blank=True,
        help_text=_("When the notification was read"),
    )
    action_url: models.URLField = models.URLField(
        _("Action URL"),
        max_length=500,
        blank=True,
        help_text=_("Optional URL for notification action"),
    )
    action_text: models.CharField = models.CharField(
        _("Action Text"),
        max_length=100,
        blank=True,
        help_text=_("Text for action button"),
    )
    expires_at: models.DateTimeField = models.DateTimeField(
        _("Expires At"),
        null=True,
        blank=True,
        help_text=_("When this notification expires"),
    )
    metadata = models.JSONField(
        _("Metadata"),
        default=dict,
        blank=True,
        help_text=_("Additional notification data"),
    )

    # Related object
    content_type: models.ForeignKey = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Content Type"),
    )
    object_id: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Object ID"),
        null=True,
        blank=True,
    )
    content_object = GenericForeignKey("content_type", "object_id")

    class Meta:
        verbose_name = _("Notification")
        verbose_name_plural = _("Notifications")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["notification_type", "-created_at"]),
            models.Index(fields=["priority", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.email}: {self.title}"

    def mark_as_read(self) -> None:
        """Mark this notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=["is_read", "read_at"])

    @property
    def is_expired(self) -> bool:
        """Check if this notification has expired."""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    @classmethod
    def create_notification(
        cls,
        user,
        title: str,
        message: str,
        notification_type: str = NotificationType.INFO,
        priority: str = Priority.NORMAL,
        action_url: str = "",
        action_text: str = "",
        expires_at=None,
        related_object=None,
        **metadata,
    ) -> "Notification":
        """Create a new notification for a user."""
        notification_data = {
            "user": user,
            "title": title,
            "message": message,
            "notification_type": notification_type,
            "priority": priority,
            "action_url": action_url,
            "action_text": action_text,
            "expires_at": expires_at,
            "metadata": metadata,
        }

        if related_object:
            notification_data["content_object"] = related_object

        return cls.objects.create(**notification_data)


class ActivityLog(UserAuditModel):
    """System activity log for tracking user actions and system events."""

    class ActivityType(models.TextChoices):
        """Types of activities."""

        LOGIN = "LOGIN", _("User Login")
        LOGOUT = "LOGOUT", _("User Logout")
        CREATE = "CREATE", _("Create Record")
        UPDATE = "UPDATE", _("Update Record")
        DELETE = "DELETE", _("Delete Record")
        VIEW = "VIEW", _("View Record")
        EXPORT = "EXPORT", _("Export Data")
        IMPORT = "IMPORT", _("Import Data")
        PAYMENT = "PAYMENT", _("Payment Processed")
        ENROLLMENT = "ENROLLMENT", _("Student Enrollment")
        GRADE_ENTRY = "GRADE_ENTRY", _("Grade Entry")
        SYSTEM = "SYSTEM", _("System Event")
        ERROR = "ERROR", _("System Error")

    user: models.ForeignKey = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="activity_logs",
        verbose_name=_("User"),
    )
    activity_type: models.CharField = models.CharField(
        _("Activity Type"),
        max_length=20,
        choices=ActivityType.choices,
    )
    description: models.TextField = models.TextField(
        _("Description"),
        help_text=_("Human-readable description of the activity"),
    )
    ip_address: models.GenericIPAddressField = models.GenericIPAddressField(
        _("IP Address"),
        null=True,
        blank=True,
        help_text=_("User's IP address when action was performed"),
    )
    user_agent: models.TextField = models.TextField(
        _("User Agent"),
        blank=True,
        help_text=_("User's browser/client information"),
    )
    session_key: models.CharField = models.CharField(
        _("Session Key"),
        max_length=40,
        blank=True,
        help_text=_("User's session identifier"),
    )

    # Related object
    content_type: models.ForeignKey = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("Content Type"),
    )
    object_id: models.PositiveIntegerField = models.PositiveIntegerField(
        _("Object ID"),
        null=True,
        blank=True,
    )
    content_object = GenericForeignKey("content_type", "object_id")

    # Additional context
    changes = models.JSONField(
        _("Changes"),
        default=dict,
        blank=True,
        help_text=_("Details of what changed (for updates)"),
    )
    metadata = models.JSONField(
        _("Metadata"),
        default=dict,
        blank=True,
        help_text=_("Additional activity context"),
    )
    success: models.BooleanField = models.BooleanField(
        _("Success"),
        default=True,
        help_text=_("Whether the activity completed successfully"),
    )
    error_message: models.TextField = models.TextField(
        _("Error Message"),
        blank=True,
        help_text=_("Error details if activity failed"),
    )

    class Meta:
        verbose_name = _("Activity Log")
        verbose_name_plural = _("Activity Logs")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["activity_type", "-created_at"]),
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self) -> str:
        user_info = self.user.email if self.user else "System"
        return f"{user_info}: {self.get_activity_type_display()} - {self.description}"  # type: ignore[attr-defined]

    @classmethod
    def log_activity(
        cls,
        activity_type: str,
        description: str,
        user=None,
        related_object=None,
        request=None,
        success: bool = True,
        error_message: str = "",
        changes=None,
        **metadata,
    ) -> "ActivityLog":
        """Log a new activity."""
        activity_data = {
            "activity_type": activity_type,
            "description": description,
            "user": user,
            "success": success,
            "error_message": error_message,
            "changes": changes or {},
            "metadata": metadata,
        }

        if related_object:
            activity_data["content_object"] = related_object

        if request:
            # Extract request information
            x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
            if x_forwarded_for:
                ip = x_forwarded_for.split(",")[0]
            else:
                ip = request.META.get("REMOTE_ADDR")

            activity_data.update(
                {
                    "ip_address": ip,
                    "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                    "session_key": request.session.session_key,
                }
            )

        return cls.objects.create(**activity_data)


class NotificationTemplate(UserAuditModel):
    """Email and SMS notification templates.

    This model was moved from apps.settings to maintain proper domain boundaries.
    It defines templates for various notification types and trigger events.
    """

    class TemplateType(models.TextChoices):
        EMAIL = "email", _("Email")
        SMS = "sms", _("SMS")
        PUSH = "push", _("Push Notification")

    class TriggerEvent(models.TextChoices):
        ENROLLMENT = "enrollment", _("Enrollment")
        PAYMENT_DUE = "payment_due", _("Payment Due")
        PAYMENT_RECEIVED = "payment_received", _("Payment Received")
        GRADE_POSTED = "grade_posted", _("Grade Posted")
        ATTENDANCE_ALERT = "attendance_alert", _("Attendance Alert")
        SYSTEM_MAINTENANCE = "system_maintenance", _("System Maintenance")

    name: models.CharField = models.CharField(
        _("Template Name"), max_length=200, help_text=_("Descriptive name for this template")
    )
    template_type: models.CharField = models.CharField(
        _("Template Type"), max_length=10, choices=TemplateType.choices, help_text=_("Type of notification")
    )
    trigger_event: models.CharField = models.CharField(
        _("Trigger Event"),
        max_length=20,
        choices=TriggerEvent.choices,
        help_text=_("When this notification should be sent"),
    )
    subject: models.CharField = models.CharField(
        _("Subject"), max_length=200, blank=True, help_text=_("Subject line for email notifications")
    )
    body: models.TextField = models.TextField(_("Body"), help_text=_("Notification content with template variables"))
    is_active: models.BooleanField = models.BooleanField(
        _("Is Active"), default=True, help_text=_("Whether this template is currently in use")
    )
    send_to_student: models.BooleanField = models.BooleanField(
        _("Send to Student"), default=True, help_text=_("Whether to send to students")
    )
    send_to_parent: models.BooleanField = models.BooleanField(
        _("Send to Parent"), default=False, help_text=_("Whether to send to parents/guardians")
    )
    send_to_staff: models.BooleanField = models.BooleanField(
        _("Send to Staff"), default=False, help_text=_("Whether to send to staff members")
    )

    class Meta:
        verbose_name = _("Notification Template")
        verbose_name_plural = _("Notification Templates")
        unique_together = [["template_type", "trigger_event"]]
        ordering = ["template_type", "trigger_event"]
        indexes: ClassVar[list[models.Index]] = [
            models.Index(fields=["template_type", "is_active"]),
            models.Index(fields=["trigger_event"]),
        ]

    def __str__(self):
        return f"{self.get_template_type_display()}: {self.name}"
