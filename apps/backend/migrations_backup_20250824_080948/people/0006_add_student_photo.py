# Generated migration for StudentPhoto model

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


def student_photo_path(instance, filename):
    """Generate organized path for student photos."""
    timestamp = django.utils.timezone.now()
    student_id = (
        instance.person.student_profile.student_id if hasattr(instance.person, "student_profile") else "unknown"
    )
    ext = filename.split(".")[-1].lower()
    new_filename = f"{student_id}_{timestamp.strftime('%Y%m%d%H%M%S')}.{ext}"
    return f"student-photos/{timestamp.year}/{timestamp.month:02d}/{new_filename}"


def student_thumbnail_path(instance, filename):
    """Generate path for photo thumbnails."""
    timestamp = django.utils.timezone.now()
    student_id = (
        instance.person.student_profile.student_id if hasattr(instance.person, "student_profile") else "unknown"
    )
    ext = filename.split(".")[-1].lower()
    new_filename = f"{student_id}_{timestamp.strftime('%Y%m%d%H%M%S')}_thumb.{ext}"
    return f"student-photos/thumbnails/{timestamp.year}/{timestamp.month:02d}/{new_filename}"


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("people", "0005_add_combined_course_system"),
    ]

    operations = [
        migrations.CreateModel(
            name="StudentPhoto",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "created_at",
                    models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Created At"),
                ),
                (
                    "updated_at",
                    models.DateTimeField(auto_now=True, verbose_name="Updated At"),
                ),
                (
                    "is_deleted",
                    models.BooleanField(default=False, verbose_name="Is Deleted"),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Deleted At"),
                ),
                (
                    "photo_file",
                    models.ImageField(
                        help_text="Student photo file (JPEG/PNG, max 5MB)",
                        upload_to=student_photo_path,
                        verbose_name="Photo File",
                    ),
                ),
                (
                    "thumbnail",
                    models.ImageField(
                        blank=True,
                        help_text="Auto-generated 80x90 thumbnail",
                        null=True,
                        upload_to=student_thumbnail_path,
                        verbose_name="Thumbnail",
                    ),
                ),
                (
                    "upload_timestamp",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="When the photo was uploaded",
                        verbose_name="Upload Timestamp",
                    ),
                ),
                (
                    "upload_source",
                    models.CharField(
                        choices=[
                            ("ADMIN", "Admin Upload"),
                            ("MOBILE", "Mobile App"),
                            ("LEGACY_IMPORT", "Legacy System Import"),
                            ("API", "API Upload"),
                            ("OTHER", "Other"),
                        ],
                        default="ADMIN",
                        help_text="Where the photo was uploaded from",
                        max_length=20,
                        verbose_name="Upload Source",
                    ),
                ),
                (
                    "is_current",
                    models.BooleanField(
                        default=True,
                        help_text="Whether this is the current active photo",
                        verbose_name="Is Current",
                    ),
                ),
                (
                    "verified_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When the photo was verified",
                        null=True,
                        verbose_name="Verified At",
                    ),
                ),
                (
                    "file_hash",
                    models.CharField(
                        help_text="SHA-256 hash of the photo file for deduplication",
                        max_length=64,
                        unique=True,
                        verbose_name="File Hash",
                    ),
                ),
                (
                    "file_size",
                    models.PositiveIntegerField(help_text="File size in bytes", verbose_name="File Size"),
                ),
                (
                    "width",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Image width in pixels",
                        null=True,
                        verbose_name="Width",
                    ),
                ),
                (
                    "height",
                    models.PositiveIntegerField(
                        blank=True,
                        help_text="Image height in pixels",
                        null=True,
                        verbose_name="Height",
                    ),
                ),
                (
                    "reminder_sent_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Last time a reminder was sent for photo update",
                        null=True,
                        verbose_name="Reminder Sent At",
                    ),
                ),
                (
                    "reminder_count",
                    models.IntegerField(
                        default=0,
                        help_text="Number of reminders sent for this photo",
                        verbose_name="Reminder Count",
                    ),
                ),
                (
                    "skip_reminder",
                    models.BooleanField(
                        default=False,
                        help_text="Skip reminder for special cases (graduated, exchange students)",
                        verbose_name="Skip Reminder",
                    ),
                ),
                (
                    "original_filename",
                    models.CharField(
                        blank=True,
                        help_text="Original filename when uploaded",
                        max_length=255,
                        verbose_name="Original Filename",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        help_text="Administrative notes about this photo",
                        verbose_name="Notes",
                    ),
                ),
                (
                    "person",
                    models.ForeignKey(
                        help_text="Person this photo belongs to",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="photos",
                        to="people.person",
                        verbose_name="Person",
                    ),
                ),
                (
                    "verified_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="Staff member who verified this photo",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="verified_photos",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Verified By",
                    ),
                ),
            ],
            options={
                "verbose_name": "Student Photo",
                "verbose_name_plural": "Student Photos",
                "ordering": ["-upload_timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="studentphoto",
            index=models.Index(
                fields=["person", "-upload_timestamp"],
                name="people_stud_person__f35c19_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="studentphoto",
            index=models.Index(fields=["is_current", "person"], name="people_stud_is_curr_a9e7c8_idx"),
        ),
        migrations.AddIndex(
            model_name="studentphoto",
            index=models.Index(fields=["upload_timestamp"], name="people_stud_upload__8e7e5d_idx"),
        ),
        migrations.AddIndex(
            model_name="studentphoto",
            index=models.Index(fields=["reminder_sent_at"], name="people_stud_reminde_7b9c2a_idx"),
        ),
        migrations.AddIndex(
            model_name="studentphoto",
            index=models.Index(fields=["file_hash"], name="people_stud_file_ha_8f1d5f_idx"),
        ),
        migrations.AddConstraint(
            model_name="studentphoto",
            constraint=models.UniqueConstraint(
                condition=models.Q(("is_current", True)),
                fields=("person", "is_current"),
                name="unique_current_photo",
            ),
        ),
    ]
