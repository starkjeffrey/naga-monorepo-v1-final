# Generated manually to add document quota models

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Add document quota models and unit_cost field to DocumentTypeConfig."""

    dependencies = [
        ("academic_records", "0003_documentrequest_created_by_and_more"),
        ("people", "0009_alter_studentphoto_managers_and_more"),
        ("curriculum", "0008_move_discount_rule_to_discounts"),
        ("enrollment", "0022_add_student_cycle_status"),
        ("finance", "0026_add_discount_application"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add unit_cost field to DocumentTypeConfig
        migrations.AddField(
            model_name="documenttypeconfig",
            name="unit_cost",
            field=models.PositiveIntegerField(
                default=1, help_text="Number of quota units required for this document type", verbose_name="Unit Cost"
            ),
        ),
        # Create DocumentQuota model
        migrations.CreateModel(
            name="DocumentQuota",
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
                    "total_units",
                    models.PositiveIntegerField(
                        default=10,
                        help_text="Total document units allocated for this term",
                        verbose_name="Total Units",
                    ),
                ),
                (
                    "used_units",
                    models.PositiveIntegerField(
                        default=0, help_text="Document units already used", verbose_name="Used Units"
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True, help_text="Whether this quota is currently usable", verbose_name="Is Active"
                    ),
                ),
                (
                    "expires_date",
                    models.DateField(help_text="Date when this quota expires", verbose_name="Expires Date"),
                ),
                (
                    "admin_fee_line_item",
                    models.ForeignKey(
                        blank=True,
                        help_text="Administrative fee invoice line item that included this quota",
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="document_quotas",
                        to="finance.invoicelineitem",
                        verbose_name="Administrative Fee Line Item",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who created this record",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created by",
                    ),
                ),
                (
                    "cycle_status",
                    models.ForeignKey(
                        help_text="Associated cycle status that triggered this quota",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="document_quotas",
                        to="enrollment.studentcyclestatus",
                        verbose_name="Cycle Status",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        help_text="Student who owns this document quota",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="document_quotas",
                        to="people.studentprofile",
                        verbose_name="Student",
                    ),
                ),
                (
                    "term",
                    models.ForeignKey(
                        help_text="Term this quota applies to",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="document_quotas",
                        to="curriculum.term",
                        verbose_name="Term",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who last updated this record",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="%(app_label)s_%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Updated by",
                    ),
                ),
            ],
            options={
                "verbose_name": "Document Quota",
                "verbose_name_plural": "Document Quotas",
                "db_table": "academic_records_document_quota",
            },
        ),
        # Create DocumentQuotaUsage model
        migrations.CreateModel(
            name="DocumentQuotaUsage",
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
                    "units_consumed",
                    models.PositiveIntegerField(
                        help_text="Number of units consumed for this document", verbose_name="Units Consumed"
                    ),
                ),
                (
                    "usage_date",
                    models.DateTimeField(
                        auto_now_add=True, help_text="When the units were consumed", verbose_name="Usage Date"
                    ),
                ),
                (
                    "document_request",
                    models.ForeignKey(
                        help_text="Document request that consumed these units",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="quota_usage",
                        to="academic_records.documentrequest",
                        verbose_name="Document Request",
                    ),
                ),
                (
                    "quota",
                    models.ForeignKey(
                        help_text="Quota from which units were consumed",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="usage_records",
                        to="academic_records.documentquota",
                        verbose_name="Document Quota",
                    ),
                ),
            ],
            options={
                "verbose_name": "Document Quota Usage",
                "verbose_name_plural": "Document Quota Usage Records",
                "db_table": "academic_records_document_quota_usage",
                "ordering": ["-usage_date"],
            },
        ),
        # Add indexes and constraints
        migrations.AlterUniqueTogether(
            name="documentquota",
            unique_together={("student", "term")},
        ),
        migrations.AddIndex(
            model_name="documentquota",
            index=models.Index(fields=["student", "term", "is_active"], name="academic_re_student_0f5c4d_idx"),
        ),
        migrations.AddIndex(
            model_name="documentquota",
            index=models.Index(fields=["expires_date"], name="academic_re_expires_89e3f6_idx"),
        ),
        migrations.AddIndex(
            model_name="documentquota",
            index=models.Index(fields=["cycle_status"], name="academic_re_cycle_s_7b5d23_idx"),
        ),
        migrations.AddIndex(
            model_name="documentquotausage",
            index=models.Index(fields=["quota", "usage_date"], name="academic_re_quota_i_a2c4e1_idx"),
        ),
        migrations.AddIndex(
            model_name="documentquotausage",
            index=models.Index(fields=["document_request"], name="academic_re_documen_8f3b2a_idx"),
        ),
    ]
