# Generated migration for ProgramPeriod model

from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("enrollment", "0009_merge_20250731_2004"),
        ("curriculum", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ProgramPeriod",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Created at")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Updated at")),
                ("is_deleted", models.BooleanField(default=False, verbose_name="Is deleted")),
                ("deleted_at", models.DateTimeField(blank=True, null=True, verbose_name="Deleted at")),
                (
                    "transition_type",
                    models.CharField(
                        choices=[
                            ("INITIAL", "Initial Enrollment"),
                            ("PROGRESSION", "Natural Progression"),
                            ("CHANGE", "Program Change"),
                            ("RETURN", "Return to Previous Program"),
                            ("CONTINUATION", "Continuation in Same Program"),
                            ("GAP", "Gap Period"),
                        ],
                        help_text="Type of transition",
                        max_length=20,
                        verbose_name="Transition Type",
                    ),
                ),
                (
                    "transition_date",
                    models.DateField(
                        db_index=True,
                        help_text="Date when this program period started",
                        verbose_name="Transition Date",
                    ),
                ),
                (
                    "from_program_type",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("IEAP", "Intensive English for Academic Purposes"),
                            ("GESL", "General English as a Second Language"),
                            ("EHSS", "English for High School Students"),
                            ("LANG_OTHER", "Other Language Program"),
                            ("BA", "Bachelor of Arts"),
                            ("MA", "Master of Arts"),
                            ("PHD", "Doctoral Program"),
                            ("CERT", "Certificate Program"),
                        ],
                        help_text="Previous program type",
                        max_length=20,
                        null=True,
                        verbose_name="From Program Type",
                    ),
                ),
                (
                    "to_program_type",
                    models.CharField(
                        choices=[
                            ("IEAP", "Intensive English for Academic Purposes"),
                            ("GESL", "General English as a Second Language"),
                            ("EHSS", "English for High School Students"),
                            ("LANG_OTHER", "Other Language Program"),
                            ("BA", "Bachelor of Arts"),
                            ("MA", "Master of Arts"),
                            ("PHD", "Doctoral Program"),
                            ("CERT", "Certificate Program"),
                        ],
                        help_text="New program type",
                        max_length=20,
                        verbose_name="To Program Type",
                    ),
                ),
                (
                    "program_name",
                    models.CharField(
                        help_text="Full program name for display", max_length=200, verbose_name="Program Name"
                    ),
                ),
                (
                    "duration_days",
                    models.PositiveIntegerField(
                        help_text="Days spent in this program period", verbose_name="Duration (Days)"
                    ),
                ),
                (
                    "duration_months",
                    models.DecimalField(
                        decimal_places=1,
                        help_text="Months spent in this program period",
                        max_digits=5,
                        verbose_name="Duration (Months)",
                    ),
                ),
                (
                    "term_count",
                    models.PositiveIntegerField(
                        default=0, help_text="Number of terms enrolled in this period", verbose_name="Term Count"
                    ),
                ),
                (
                    "total_credits",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Total credits attempted in this period",
                        max_digits=6,
                        verbose_name="Total Credits",
                    ),
                ),
                (
                    "completed_credits",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        help_text="Credits successfully completed",
                        max_digits=6,
                        verbose_name="Completed Credits",
                    ),
                ),
                (
                    "gpa",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="GPA for this period",
                        max_digits=3,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.00")),
                            django.core.validators.MaxValueValidator(Decimal("4.00")),
                        ],
                        verbose_name="GPA",
                    ),
                ),
                (
                    "completion_status",
                    models.CharField(
                        choices=[
                            ("ACTIVE", "Currently Active"),
                            ("COMPLETED", "Completed Successfully"),
                            ("GRADUATED", "Graduated with Degree"),
                            ("DROPPED", "Dropped Out"),
                            ("INACTIVE", "Inactive"),
                            ("TRANSFERRED", "Transferred"),
                        ],
                        help_text="Status at end of this period",
                        max_length=20,
                        verbose_name="Completion Status",
                    ),
                ),
                (
                    "language_level",
                    models.CharField(
                        blank=True,
                        help_text="Final level achieved (for language programs)",
                        max_length=10,
                        verbose_name="Language Level",
                    ),
                ),
                (
                    "sequence_number",
                    models.PositiveIntegerField(
                        help_text="Order in student's journey (1-based)", verbose_name="Sequence Number"
                    ),
                ),
                (
                    "confidence_score",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("1.00"),
                        help_text="Confidence in transition data (0.0-1.0)",
                        max_digits=3,
                        validators=[
                            django.core.validators.MinValueValidator(Decimal("0.00")),
                            django.core.validators.MaxValueValidator(Decimal("1.00")),
                        ],
                        verbose_name="Confidence Score",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True, help_text="Additional notes about this transition", verbose_name="Notes"
                    ),
                ),
                (
                    "journey",
                    models.ForeignKey(
                        help_text="Parent journey record",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="program_periods",
                        to="enrollment.academicjourney",
                        verbose_name="Academic Journey",
                    ),
                ),
                (
                    "to_program",
                    models.ForeignKey(
                        blank=True,
                        help_text="Specific program or major (for BA/MA)",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="program_periods",
                        to="curriculum.major",
                        verbose_name="Program/Major",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created by",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Updated by",
                    ),
                ),
            ],
            options={
                "verbose_name": "Program Period",
                "verbose_name_plural": "Program Periods",
                "ordering": ["journey", "sequence_number"],
            },
        ),
        migrations.AddIndex(
            model_name="programperiod",
            index=models.Index(fields=["journey", "sequence_number"], name="enrollment__journey_9f8b14_idx"),
        ),
        migrations.AddIndex(
            model_name="programperiod",
            index=models.Index(fields=["transition_date", "to_program_type"], name="enrollment__transit_5c6f9f_idx"),
        ),
        migrations.AddIndex(
            model_name="programperiod",
            index=models.Index(fields=["completion_status", "to_program_type"], name="enrollment__complet_d6c3e9_idx"),
        ),
        migrations.AlterUniqueTogether(
            name="programperiod",
            unique_together={("journey", "sequence_number")},
        ),
    ]
