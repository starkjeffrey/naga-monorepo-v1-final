# Generated manually to add support for multiple AcademicJourney records per student

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("enrollment", "0010_add_program_period_model"),
        ("people", "0001_initial"),
        ("curriculum", "0001_initial"),
    ]

    operations = [
        # First, rename the existing fields to avoid conflicts
        migrations.RenameField(
            model_name="academicjourney",
            old_name="journey_status",
            new_name="journey_status_old",
        ),
        # Change student from OneToOneField to ForeignKey
        migrations.AlterField(
            model_name="academicjourney",
            name="student",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="academic_journeys",
                to="people.studentprofile",
                verbose_name="Student",
                help_text="Student for whom this journey is created",
            ),
        ),
        # Add new fields with defaults
        migrations.AddField(
            model_name="academicjourney",
            name="program_type",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("LANGUAGE", "Language Program"),
                    ("FOUNDATION", "Foundation/Liberal Arts"),
                    ("DEGREE", "Degree Program"),
                ],
                default="DEGREE",
                db_index=True,
                verbose_name="Program Type",
                help_text="Type of program in this period",
            ),
        ),
        migrations.AddField(
            model_name="academicjourney",
            name="program",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="curriculum.major",
                null=True,
                blank=True,
                verbose_name="Program/Major",
                help_text="The specific program or major for this period",
            ),
        ),
        migrations.AddField(
            model_name="academicjourney",
            name="start_date",
            field=models.DateField(
                db_index=True,
                null=True,
                verbose_name="Start Date",
                help_text="Date when this program period started",
            ),
        ),
        migrations.AddField(
            model_name="academicjourney",
            name="stop_date",
            field=models.DateField(
                null=True,
                blank=True,
                verbose_name="Stop Date",
                help_text="Date when this program period ended",
            ),
        ),
        migrations.AddField(
            model_name="academicjourney",
            name="start_term",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="curriculum.term",
                related_name="journey_starts",
                null=True,
                verbose_name="Start Term",
                help_text="Term when this program period started",
            ),
        ),
        migrations.AddField(
            model_name="academicjourney",
            name="term_code",
            field=models.CharField(
                max_length=20,
                default="",
                verbose_name="Term Code",
                help_text="Term code when the change took place",
            ),
        ),
        migrations.AddField(
            model_name="academicjourney",
            name="duration_in_terms",
            field=models.PositiveIntegerField(
                default=0,
                verbose_name="Duration in Terms",
                help_text="Number of terms in this program period",
            ),
        ),
        migrations.AddField(
            model_name="academicjourney",
            name="transition_status",
            field=models.CharField(
                max_length=20,
                choices=[
                    ("ACTIVE", "Currently Active"),
                    ("GRADUATED", "Graduated"),
                    ("CHANGED_PROGRAM", "Changed Program/Major"),
                    ("DROPPED_OUT", "Dropped Out"),
                    ("SUSPENDED", "Suspended"),
                    ("TRANSFERRED", "Transferred Out"),
                    ("COMPLETED_LEVEL", "Completed Language Level"),
                    ("UNKNOWN", "Unknown Status"),
                ],
                default="ACTIVE",
                db_index=True,
                verbose_name="Transition Status",
                help_text="Status indicating how this program period ended",
            ),
        ),
        # Remove old fields
        migrations.RemoveField(
            model_name="academicjourney",
            name="journey_status_old",
        ),
        migrations.RemoveField(
            model_name="academicjourney",
            name="current_level",
        ),
        migrations.RemoveField(
            model_name="academicjourney",
            name="expected_completion_date",
        ),
        migrations.RemoveField(
            model_name="academicjourney",
            name="first_enrollment_date",
        ),
        migrations.RemoveField(
            model_name="academicjourney",
            name="last_activity_date",
        ),
        migrations.RemoveField(
            model_name="academicjourney",
            name="total_terms_enrolled",
        ),
        migrations.RemoveField(
            model_name="academicjourney",
            name="total_credits_earned",
        ),
        migrations.RemoveField(
            model_name="academicjourney",
            name="language_programs_completed",
        ),
        migrations.RemoveField(
            model_name="academicjourney",
            name="degrees_earned",
        ),
        migrations.RemoveField(
            model_name="academicjourney",
            name="current_program_type",
        ),
        migrations.RemoveField(
            model_name="academicjourney",
            name="current_program",
        ),
        # Update meta options
        migrations.AlterModelOptions(
            name="academicjourney",
            options={
                "verbose_name": "Academic Journey",
                "verbose_name_plural": "Academic Journeys",
                "ordering": ["student", "start_date"],
            },
        ),
        # Add unique constraint
        migrations.AddConstraint(
            model_name="academicjourney",
            constraint=models.UniqueConstraint(
                fields=["student", "program_type", "start_date"],
                name="unique_journey_period",
            ),
        ),
    ]
