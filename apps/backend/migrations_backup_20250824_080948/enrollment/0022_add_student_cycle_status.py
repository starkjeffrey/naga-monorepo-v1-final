# Generated manually to add StudentCycleStatus model

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Add StudentCycleStatus model to track students changing academic cycles."""

    dependencies = [
        ("enrollment", "0021_fix_program_transition_fields"),
        ("people", "0009_alter_studentphoto_managers_and_more"),
        ("curriculum", "0008_move_discount_rule_to_discounts"),
    ]

    operations = [
        migrations.CreateModel(
            name="StudentCycleStatus",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "created_at",
                    models.DateTimeField(
                        auto_now_add=True,
                        help_text="Date and time when the record was created",
                        verbose_name="Created at",
                    ),
                ),
                (
                    "updated_at",
                    models.DateTimeField(
                        auto_now=True,
                        help_text="Date and time when the record was last updated",
                        verbose_name="Updated at",
                    ),
                ),
                (
                    "cycle_type",
                    models.CharField(
                        choices=[
                            ("NEW", "New Student"),
                            ("L2B", "Language to Bachelor"),
                            ("B2M", "Bachelor to Master"),
                        ],
                        help_text="Type of cycle change",
                        max_length=3,
                        verbose_name="Cycle Type",
                    ),
                ),
                (
                    "detected_date",
                    models.DateField(help_text="Date when cycle change was detected", verbose_name="Detected Date"),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Active until student graduates from target program",
                        verbose_name="Is Active",
                    ),
                ),
                (
                    "deactivated_date",
                    models.DateField(
                        blank=True,
                        help_text="Date when status was deactivated (graduation/withdrawal)",
                        null=True,
                        verbose_name="Deactivated Date",
                    ),
                ),
                (
                    "deactivation_reason",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("GRADUATED", "Graduated"),
                            ("WITHDRAWN", "Withdrawn"),
                            ("TRANSFERRED", "Transferred"),
                            ("OTHER", "Other"),
                        ],
                        help_text="Reason for deactivation",
                        max_length=50,
                        verbose_name="Deactivation Reason",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True, help_text="Additional notes about this cycle change", verbose_name="Notes"
                    ),
                ),
                (
                    "source_program",
                    models.ForeignKey(
                        blank=True,
                        help_text="Program student was in before change (null for new students)",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="cycle_departures",
                        to="curriculum.major",
                        verbose_name="Source Program",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        help_text="Student with cycle change status",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="cycle_statuses",
                        to="people.studentprofile",
                        verbose_name="Student",
                    ),
                ),
                (
                    "target_program",
                    models.ForeignKey(
                        help_text="Program student changed to",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="cycle_arrivals",
                        to="curriculum.major",
                        verbose_name="Target Program",
                    ),
                ),
            ],
            options={
                "verbose_name": "Student Cycle Status",
                "verbose_name_plural": "Student Cycle Statuses",
                "db_table": "enrollment_student_cycle_status",
            },
        ),
        migrations.AddIndex(
            model_name="studentcyclestatus",
            index=models.Index(fields=["student", "is_active"], name="enrollment__student_f66c8d_idx"),
        ),
        migrations.AddIndex(
            model_name="studentcyclestatus",
            index=models.Index(fields=["cycle_type", "is_active"], name="enrollment__cycle_t_e32185_idx"),
        ),
        migrations.AddIndex(
            model_name="studentcyclestatus",
            index=models.Index(fields=["detected_date"], name="enrollment__detecte_277cac_idx"),
        ),
        migrations.AddIndex(
            model_name="studentcyclestatus",
            index=models.Index(fields=["target_program", "is_active"], name="enrollment__target__4db3c8_idx"),
        ),
        migrations.AddConstraint(
            model_name="studentcyclestatus",
            constraint=models.UniqueConstraint(
                fields=("student", "cycle_type", "target_program"), name="unique_student_cycle_program"
            ),
        ),
    ]
