"""Moodle integration models."""

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.db.models import (
    BooleanField,
    CharField,
    DateTimeField,
    DecimalField,
    EmailField,
    ForeignKey,
    IntegerField,
    JSONField,
    OneToOneField,
    PositiveIntegerField,
    TextField,
)

from apps.common.models import TimestampedModel


class SyncStatusChoices(models.TextChoices):
    """Sync status options."""

    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In Progress"
    SUCCESS = "success", "Success"
    FAILED = "failed", "Failed"
    RETRY = "retry", "Retry"


class MoodleSyncStatus(TimestampedModel):
    """Track synchronization status for any SIS entity to Moodle.

    This model uses generic foreign keys to track sync status for any
    SIS model (Person, Course, Enrollment, etc.) with Moodle.
    """

    content_type: ForeignKey = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id: PositiveIntegerField = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    moodle_id: IntegerField = models.IntegerField(help_text="Moodle entity ID")
    sync_status: CharField = models.CharField(
        max_length=20,
        choices=SyncStatusChoices.choices,
        default=SyncStatusChoices.PENDING,
    )
    last_synced: DateTimeField = models.DateTimeField(auto_now=True)
    error_message: TextField = models.TextField(blank=True)
    retry_count: PositiveIntegerField = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Moodle Sync Status"
        verbose_name_plural = "Moodle Sync Statuses"
        unique_together = [["content_type", "object_id"]]
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
            models.Index(fields=["sync_status"]),
            models.Index(fields=["last_synced"]),
        ]

    def __str__(self):
        return f"{self.content_object} -> Moodle ID {self.moodle_id} ({self.sync_status})"


class MoodleUserMapping(TimestampedModel):
    """Map SIS Person to Moodle user."""

    sis_person: OneToOneField = models.OneToOneField(
        "people.Person",
        on_delete=models.CASCADE,
        related_name="moodle_mapping",
    )
    moodle_user_id: IntegerField = models.IntegerField(unique=True)
    moodle_username: CharField = models.CharField(max_length=100, unique=True)
    moodle_email: EmailField = models.EmailField()
    is_active: BooleanField = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Moodle User Mapping"
        verbose_name_plural = "Moodle User Mappings"
        indexes = [
            models.Index(fields=["moodle_user_id"]),
            models.Index(fields=["moodle_username"]),
        ]

    def __str__(self):
        return f"{self.sis_person} -> Moodle User {self.moodle_user_id}"


class MoodleCourseMapping(TimestampedModel):
    """Map SIS Course to Moodle course."""

    sis_course: OneToOneField = models.OneToOneField(
        "curriculum.Course",
        on_delete=models.CASCADE,
        related_name="moodle_mapping",
    )
    moodle_course_id: IntegerField = models.IntegerField(unique=True)
    moodle_shortname: CharField = models.CharField(max_length=100, unique=True)
    moodle_category_id: IntegerField = models.IntegerField()
    is_active: BooleanField = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Moodle Course Mapping"
        verbose_name_plural = "Moodle Course Mappings"
        indexes = [
            models.Index(fields=["moodle_course_id"]),
            models.Index(fields=["moodle_shortname"]),
        ]

    def __str__(self):
        return f"{self.sis_course} -> Moodle Course {self.moodle_course_id}"


class MoodleEnrollmentMapping(TimestampedModel):
    """Map SIS Enrollment to Moodle enrollment."""

    sis_enrollment: OneToOneField = models.OneToOneField(
        "enrollment.Enrollment",
        on_delete=models.CASCADE,
        related_name="moodle_mapping",
    )
    moodle_enrolment_id: IntegerField = models.IntegerField(unique=True)
    moodle_role_id: IntegerField = models.IntegerField(help_text="Moodle role (student=5, teacher=3)")
    is_active: BooleanField = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Moodle Enrollment Mapping"
        verbose_name_plural = "Moodle Enrollment Mappings"
        indexes = [
            models.Index(fields=["moodle_enrolment_id"]),
            models.Index(fields=["moodle_role_id"]),
        ]

    def __str__(self):
        return f"{self.sis_enrollment} -> Moodle Enrolment {self.moodle_enrolment_id}"


class MoodleGradeMapping(TimestampedModel):
    """Map SIS Grade to Moodle grade (future implementation)."""

    # TODO: Implement when grading app is created
    # sis_grade = models.OneToOneField('grading.Grade', on_delete=models.CASCADE)
    moodle_grade_id: IntegerField = models.IntegerField(unique=True)
    moodle_grade_item_id: IntegerField = models.IntegerField()
    last_synced_value: DecimalField = models.DecimalField(max_digits=5, decimal_places=2)
    is_active: BooleanField = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Moodle Grade Mapping"
        verbose_name_plural = "Moodle Grade Mappings"
        indexes = [
            models.Index(fields=["moodle_grade_id"]),
            models.Index(fields=["moodle_grade_item_id"]),
        ]

    def __str__(self):
        return f"Moodle Grade {self.moodle_grade_id}"


class MoodleAPILog(TimestampedModel):
    """Log all Moodle API interactions for debugging and auditing."""

    endpoint: CharField = models.CharField(max_length=200)
    method: CharField = models.CharField(max_length=10)  # GET, POST, etc.
    request_data: JSONField = models.JSONField(blank=True, null=True)
    response_data: JSONField = models.JSONField(blank=True, null=True)
    status_code: IntegerField = models.IntegerField()
    execution_time_ms: IntegerField = models.IntegerField(help_text="API call duration in milliseconds")
    error_message: TextField = models.TextField(blank=True)

    class Meta:
        verbose_name = "Moodle API Log"
        verbose_name_plural = "Moodle API Logs"
        indexes = [
            models.Index(fields=["endpoint"]),
            models.Index(fields=["status_code"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"{self.method} {self.endpoint} - {self.status_code}"
