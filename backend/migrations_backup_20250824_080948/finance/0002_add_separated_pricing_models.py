# Generated migration for separated pricing models

import datetime

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("curriculum", "0001_initial"),
        ("users", "0001_initial"),
        ("finance", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="DefaultPricing",
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
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
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
                    "effective_date",
                    models.DateField(
                        default=datetime.date.today,
                        help_text="When this pricing becomes effective",
                        verbose_name="Effective Date",
                    ),
                ),
                (
                    "end_date",
                    models.DateField(
                        blank=True,
                        help_text="When this pricing expires (null = current)",
                        null=True,
                        verbose_name="End Date",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        help_text="Internal notes about this pricing",
                        verbose_name="Notes",
                    ),
                ),
                (
                    "domestic_price",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Price for domestic students",
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Domestic Price",
                    ),
                ),
                (
                    "foreign_price",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Price for international students",
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Foreign Price",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_created",
                        to="users.User",
                        verbose_name="Created By",
                    ),
                ),
                (
                    "cycle",
                    models.ForeignKey(
                        help_text="Academic cycle (BA/MA/LANG)",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="default_pricing",
                        to="curriculum.cycle",
                        verbose_name="Cycle",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_updated",
                        to="users.User",
                        verbose_name="Updated By",
                    ),
                ),
            ],
            options={
                "verbose_name": "Default Pricing",
                "verbose_name_plural": "Default Pricing",
                "ordering": ["cycle", "-effective_date"],
            },
        ),
        migrations.CreateModel(
            name="CourseFixedPricing",
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
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
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
                    "effective_date",
                    models.DateField(
                        default=datetime.date.today,
                        help_text="When this pricing becomes effective",
                        verbose_name="Effective Date",
                    ),
                ),
                (
                    "end_date",
                    models.DateField(
                        blank=True,
                        help_text="When this pricing expires (null = current)",
                        null=True,
                        verbose_name="End Date",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        help_text="Internal notes about this pricing",
                        verbose_name="Notes",
                    ),
                ),
                (
                    "domestic_price",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Price for domestic students",
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Domestic Price",
                    ),
                ),
                (
                    "foreign_price",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Price for international students",
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Foreign Price",
                    ),
                ),
                (
                    "course",
                    models.ForeignKey(
                        help_text="Course with fixed pricing",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fixed_pricing",
                        to="curriculum.course",
                        verbose_name="Course",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_created",
                        to="users.User",
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_updated",
                        to="users.User",
                        verbose_name="Updated By",
                    ),
                ),
            ],
            options={
                "verbose_name": "Course Fixed Pricing",
                "verbose_name_plural": "Course Fixed Pricing",
                "ordering": ["course", "-effective_date"],
            },
        ),
        migrations.CreateModel(
            name="SeniorProjectPricing",
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
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
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
                    "effective_date",
                    models.DateField(
                        default=datetime.date.today,
                        help_text="When this pricing becomes effective",
                        verbose_name="Effective Date",
                    ),
                ),
                (
                    "end_date",
                    models.DateField(
                        blank=True,
                        help_text="When this pricing expires (null = current)",
                        null=True,
                        verbose_name="End Date",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        help_text="Internal notes about this pricing",
                        verbose_name="Notes",
                    ),
                ),
                (
                    "tier",
                    models.CharField(
                        choices=[
                            ("1-2", "1-2 Students"),
                            ("3-4", "3-4 Students"),
                            ("5+", "5+ Students"),
                        ],
                        help_text="Student group size tier",
                        max_length=10,
                        verbose_name="Group Size Tier",
                    ),
                ),
                (
                    "total_price",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Total price for the project (split among group)",
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Total Project Price",
                    ),
                ),
                (
                    "foreign_price",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Total price for foreign students (split among group)",
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Foreign Total Price",
                    ),
                ),
                (
                    "advisor_payment",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Payment to project advisor",
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Advisor Payment",
                    ),
                ),
                (
                    "committee_payment",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Payment to each committee member",
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Committee Payment",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_created",
                        to="users.User",
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_updated",
                        to="users.User",
                        verbose_name="Updated By",
                    ),
                ),
            ],
            options={
                "verbose_name": "Senior Project Pricing",
                "verbose_name_plural": "Senior Project Pricing",
                "ordering": ["tier", "-effective_date"],
            },
        ),
        migrations.CreateModel(
            name="ReadingClassPricing",
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
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
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
                    "effective_date",
                    models.DateField(
                        default=datetime.date.today,
                        help_text="When this pricing becomes effective",
                        verbose_name="Effective Date",
                    ),
                ),
                (
                    "end_date",
                    models.DateField(
                        blank=True,
                        help_text="When this pricing expires (null = current)",
                        null=True,
                        verbose_name="End Date",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True,
                        help_text="Internal notes about this pricing",
                        verbose_name="Notes",
                    ),
                ),
                (
                    "tier",
                    models.CharField(
                        choices=[
                            ("1-2", "1-2 Students (Tutorial)"),
                            ("3-5", "3-5 Students (Small Class)"),
                            ("6-15", "6-15 Students (Medium Class)"),
                        ],
                        help_text="Class enrollment size tier",
                        max_length=10,
                        verbose_name="Class Size Tier",
                    ),
                ),
                (
                    "price_per_student",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Price charged per student",
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Price Per Student",
                    ),
                ),
                (
                    "minimum_revenue",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Minimum total revenue for the class",
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(0)],
                        verbose_name="Minimum Revenue",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_created",
                        to="users.User",
                        verbose_name="Created By",
                    ),
                ),
                (
                    "cycle",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reading_class_pricing",
                        to="curriculum.cycle",
                        verbose_name="Cycle",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_updated",
                        to="users.User",
                        verbose_name="Updated By",
                    ),
                ),
            ],
            options={
                "verbose_name": "Reading Class Pricing",
                "verbose_name_plural": "Reading Class Pricing",
                "ordering": ["cycle", "tier", "-effective_date"],
            },
        ),
        migrations.CreateModel(
            name="SeniorProjectCourse",
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
                    models.DateTimeField(auto_now_add=True, verbose_name="Created At"),
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
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Whether this course uses senior project pricing",
                        verbose_name="Is Active",
                    ),
                ),
                (
                    "course",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="senior_project_config",
                        to="curriculum.course",
                        verbose_name="Course",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_created",
                        to="users.User",
                        verbose_name="Created By",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_updated",
                        to="users.User",
                        verbose_name="Updated By",
                    ),
                ),
            ],
            options={
                "verbose_name": "Senior Project Course",
                "verbose_name_plural": "Senior Project Courses",
                "ordering": ["course__code"],
            },
        ),
        # Add constraints
        migrations.AddConstraint(
            model_name="defaultpricing",
            constraint=models.UniqueConstraint(
                fields=("cycle", "effective_date"), name="unique_default_per_cycle_date"
            ),
        ),
        migrations.AddConstraint(
            model_name="defaultpricing",
            constraint=models.UniqueConstraint(
                condition=models.Q(("end_date__isnull", True)),
                fields=("cycle",),
                name="unique_current_default_per_cycle",
            ),
        ),
        migrations.AddConstraint(
            model_name="coursefixedpricing",
            constraint=models.UniqueConstraint(
                fields=("course", "effective_date"), name="unique_fixed_per_course_date"
            ),
        ),
        migrations.AddConstraint(
            model_name="coursefixedpricing",
            constraint=models.UniqueConstraint(
                condition=models.Q(("end_date__isnull", True)),
                fields=("course",),
                name="unique_current_fixed_per_course",
            ),
        ),
        migrations.AddConstraint(
            model_name="seniorprojectpricing",
            constraint=models.UniqueConstraint(
                fields=("tier", "effective_date"),
                name="unique_senior_project_tier_date",
            ),
        ),
        migrations.AddConstraint(
            model_name="seniorprojectpricing",
            constraint=models.UniqueConstraint(
                condition=models.Q(("end_date__isnull", True)),
                fields=("tier",),
                name="unique_current_senior_project_tier",
            ),
        ),
        migrations.AddConstraint(
            model_name="readingclasspricing",
            constraint=models.UniqueConstraint(
                fields=("cycle", "tier", "effective_date"),
                name="unique_reading_per_cycle_tier_date",
            ),
        ),
        migrations.AddConstraint(
            model_name="readingclasspricing",
            constraint=models.UniqueConstraint(
                condition=models.Q(("end_date__isnull", True)),
                fields=("cycle", "tier"),
                name="unique_current_reading_per_cycle_tier",
            ),
        ),
        # Add indexes
        migrations.AddIndex(
            model_name="defaultpricing",
            index=models.Index(
                fields=["cycle", "effective_date"],
                name="finance_defaul_cycle_i_7e1b5c_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="defaultpricing",
            index=models.Index(
                fields=["effective_date", "end_date"],
                name="finance_defaul_effecti_6b0d2a_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="coursefixedpricing",
            index=models.Index(
                fields=["course", "effective_date"],
                name="finance_course_course__84e3c1_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="coursefixedpricing",
            index=models.Index(
                fields=["effective_date", "end_date"],
                name="finance_course_effecti_a6c4b7_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="seniorprojectpricing",
            index=models.Index(fields=["tier", "effective_date"], name="finance_senior_tier_7f9a1b_idx"),
        ),
        migrations.AddIndex(
            model_name="seniorprojectpricing",
            index=models.Index(
                fields=["effective_date", "end_date"],
                name="finance_senior_effecti_c5d8e2_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="readingclasspricing",
            index=models.Index(
                fields=["cycle", "tier", "effective_date"],
                name="finance_readin_cycle_i_3a9f4c_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="readingclasspricing",
            index=models.Index(
                fields=["effective_date", "end_date"],
                name="finance_readin_effecti_2b8e7d_idx",
            ),
        ),
    ]
