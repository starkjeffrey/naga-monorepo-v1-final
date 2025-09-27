# Generated manually by Claude Code on 2025-01-18

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("enrollment", "0003_classheaderenrollment_created_by_and_more"),
    ]

    operations = [
        # Add division field
        migrations.AddField(
            model_name="programenrollment",
            name="division",
            field=models.CharField(
                choices=[
                    ("LANG", "Language Programs"),
                    ("ACAD", "Academic Programs"),
                    ("PREP", "Preparatory Programs"),
                    ("PROF", "Professional Development"),
                ],
                db_index=True,
                default="ACAD",
                help_text="Academic division (Language/Academic/etc)",
                max_length=10,
                verbose_name="Division",
            ),
            preserve_default=False,
        ),
        # Add cycle field
        migrations.AddField(
            model_name="programenrollment",
            name="cycle",
            field=models.CharField(
                choices=[
                    ("HS", "High School (EHSS)"),
                    ("CERT", "Certificate Program"),
                    ("PREP", "Preparatory (IEAP/Foundation)"),
                    ("BA", "Bachelor's Degree"),
                    ("MA", "Master's Degree"),
                    ("PHD", "Doctoral Degree"),
                ],
                db_index=True,
                default="BA",
                help_text="Academic cycle or degree level",
                max_length=10,
                verbose_name="Cycle",
            ),
            preserve_default=False,
        ),
        # Add credit tracking fields
        migrations.AddField(
            model_name="programenrollment",
            name="credits_earned",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Total credits earned in this program",
                max_digits=6,
                verbose_name="Credits Earned",
            ),
        ),
        migrations.AddField(
            model_name="programenrollment",
            name="credits_required",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Total credits required for program completion",
                max_digits=6,
                null=True,
                verbose_name="Credits Required",
            ),
        ),
        migrations.AddField(
            model_name="programenrollment",
            name="gpa_at_exit",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Cumulative GPA when leaving the program",
                max_digits=3,
                null=True,
                verbose_name="GPA at Exit",
            ),
        ),
        # Add exit tracking
        migrations.AddField(
            model_name="programenrollment",
            name="exit_reason",
            field=models.CharField(
                blank=True,
                choices=[
                    ("GRAD", "Graduated"),
                    ("COMP", "Completed without Graduation"),
                    ("TRAN_INT", "Transferred to Another Program"),
                    ("TRAN_EXT", "Transferred to Another Institution"),
                    ("DISM", "Academic Dismissal"),
                    ("FIN", "Financial Reasons"),
                    ("PERS", "Personal Reasons"),
                    ("MED", "Medical Leave"),
                    ("VISA", "Visa/Immigration Issues"),
                    ("NS", "Never Attended"),
                    ("UNK", "Unknown/Not Specified"),
                ],
                db_index=True,
                help_text="Reason for leaving the program",
                max_length=15,
                verbose_name="Exit Reason",
            ),
        ),
        # Add deduction tracking
        migrations.AddField(
            model_name="programenrollment",
            name="is_deduced",
            field=models.BooleanField(
                default=False,
                help_text="Whether major was deduced from course enrollment patterns",
                verbose_name="Major Deduced",
            ),
        ),
        migrations.AddField(
            model_name="programenrollment",
            name="deduction_confidence",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Confidence score (0-1) for deduced major",
                max_digits=3,
                null=True,
                verbose_name="Deduction Confidence",
            ),
        ),
        # Add completion tracking
        migrations.AddField(
            model_name="programenrollment",
            name="completion_percentage",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Percentage of program requirements completed",
                max_digits=5,
                verbose_name="Completion Percentage",
            ),
        ),
        migrations.AddField(
            model_name="programenrollment",
            name="expected_completion_date",
            field=models.DateField(
                blank=True,
                help_text="Originally expected completion date",
                null=True,
                verbose_name="Expected Completion",
            ),
        ),
        # Add analytics fields
        migrations.AddField(
            model_name="programenrollment",
            name="time_to_completion",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Days from start to completion/exit",
                null=True,
                verbose_name="Time to Completion",
            ),
        ),
        migrations.AddField(
            model_name="programenrollment",
            name="enrollment_gaps",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text="List of terms with no enrollment",
                verbose_name="Enrollment Gaps",
            ),
        ),
        migrations.AddField(
            model_name="programenrollment",
            name="legacy_section_code",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="Section code from legacy system (87=BA, 147=MA, etc)",
                max_length=10,
                verbose_name="Legacy Section Code",
            ),
        ),
        # Add indexes for performance
        migrations.AddIndex(
            model_name="programenrollment",
            index=models.Index(fields=["division", "cycle"], name="enrollment_division_cycle_idx"),
        ),
        migrations.AddIndex(
            model_name="programenrollment",
            index=models.Index(fields=["exit_reason", "status"], name="enrollment_exit_status_idx"),
        ),
        migrations.AddIndex(
            model_name="programenrollment",
            index=models.Index(
                fields=["is_deduced", "deduction_confidence"],
                name="enrollment_deduction_idx",
            ),
        ),
        # Create ProgramTransition model
        migrations.CreateModel(
            name="ProgramTransition",
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
                    "transition_date",
                    models.DateField(
                        db_index=True,
                        verbose_name="Transition Date",
                    ),
                ),
                (
                    "transition_type",
                    models.CharField(
                        choices=[
                            ("PROG", "Natural Progression (e.g., IEAP to BA)"),
                            ("MAJOR", "Change of Major"),
                            ("LEVEL", "Level Change (e.g., BA to MA)"),
                            ("LAT", "Lateral Move (e.g., between language programs)"),
                            ("RESTART", "Program Restart"),
                        ],
                        max_length=10,
                        verbose_name="Transition Type",
                    ),
                ),
                (
                    "transition_reason",
                    models.TextField(
                        blank=True,
                        verbose_name="Transition Reason",
                    ),
                ),
                (
                    "credits_transferred",
                    models.DecimalField(
                        decimal_places=2,
                        default=0,
                        max_digits=6,
                        verbose_name="Credits Transferred",
                    ),
                ),
                (
                    "gap_days",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Days between programs",
                        verbose_name="Gap Days",
                    ),
                ),
                (
                    "from_enrollment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transitions_from",
                        to="enrollment.programenrollment",
                        verbose_name="From Program",
                    ),
                ),
                (
                    "to_enrollment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="transitions_to",
                        to="enrollment.programenrollment",
                        verbose_name="To Program",
                    ),
                ),
                (
                    "transition_term",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        to="curriculum.term",
                        verbose_name="Transition Term",
                    ),
                ),
            ],
            options={
                "verbose_name": "Program Transition",
                "verbose_name_plural": "Program Transitions",
                "ordering": ["from_enrollment__student", "transition_date"],
                "indexes": [
                    models.Index(
                        fields=["transition_date"],
                        name="transition_date_idx",
                    ),
                    models.Index(
                        fields=["transition_type"],
                        name="transition_type_idx",
                    ),
                ],
            },
        ),
    ]
