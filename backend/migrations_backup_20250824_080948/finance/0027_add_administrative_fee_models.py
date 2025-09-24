# Generated manually to add administrative fee models

from decimal import Decimal

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """Add administrative fee configuration and document excess fee models."""

    dependencies = [
        ("finance", "0026_add_discount_application"),
        ("academic_records", "0005_add_document_quota_models"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Create AdministrativeFeeConfig model
        migrations.CreateModel(
            name="AdministrativeFeeConfig",
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
                        help_text="Type of cycle change this fee applies to",
                        max_length=3,
                        unique=True,
                        verbose_name="Cycle Type",
                    ),
                ),
                (
                    "fee_amount",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Administrative fee amount per term",
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                        verbose_name="Fee Amount",
                    ),
                ),
                (
                    "included_document_units",
                    models.PositiveIntegerField(
                        default=10,
                        help_text="Number of document units included with this fee",
                        verbose_name="Included Document Units",
                    ),
                ),
                (
                    "quota_validity_days",
                    models.PositiveIntegerField(
                        default=120,
                        help_text="Number of days the document quota is valid",
                        verbose_name="Quota Validity Days",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(
                        default=True,
                        help_text="Whether this fee configuration is currently active",
                        verbose_name="Is Active",
                    ),
                ),
                (
                    "effective_date",
                    models.DateField(
                        help_text="Date when this configuration becomes effective", verbose_name="Effective Date"
                    ),
                ),
                (
                    "end_date",
                    models.DateField(
                        blank=True,
                        help_text="Date when this configuration expires (null = current)",
                        null=True,
                        verbose_name="End Date",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True, help_text="Internal notes about this fee configuration", verbose_name="Notes"
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
                "verbose_name": "Administrative Fee Configuration",
                "verbose_name_plural": "Administrative Fee Configurations",
                "db_table": "finance_administrative_fee_config",
                "ordering": ["cycle_type", "-effective_date"],
            },
        ),
        # Create DocumentExcessFee model
        migrations.CreateModel(
            name="DocumentExcessFee",
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
                    "units_charged",
                    models.PositiveIntegerField(
                        help_text="Number of excess units charged", verbose_name="Units Charged"
                    ),
                ),
                (
                    "unit_price",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Price per excess unit",
                        max_digits=10,
                        validators=[django.core.validators.MinValueValidator(Decimal("0.00"))],
                        verbose_name="Unit Price",
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
                    "document_request",
                    models.ForeignKey(
                        help_text="Document request that triggered this excess fee",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="excess_fees",
                        to="academic_records.documentrequest",
                        verbose_name="Document Request",
                    ),
                ),
                (
                    "invoice_line_item",
                    models.ForeignKey(
                        help_text="Invoice line item for this excess fee",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="document_excess_fees",
                        to="finance.invoicelineitem",
                        verbose_name="Invoice Line Item",
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
                "verbose_name": "Document Excess Fee",
                "verbose_name_plural": "Document Excess Fees",
                "db_table": "finance_document_excess_fee",
            },
        ),
        # Add indexes
        migrations.AddIndex(
            model_name="administrativefeeconfig",
            index=models.Index(fields=["cycle_type", "is_active"], name="finance_adm_cycle_t_3f8a9c_idx"),
        ),
        migrations.AddIndex(
            model_name="administrativefeeconfig",
            index=models.Index(fields=["effective_date"], name="finance_adm_effecti_2b5c7d_idx"),
        ),
        migrations.AddIndex(
            model_name="administrativefeeconfig",
            index=models.Index(fields=["cycle_type", "effective_date"], name="finance_adm_cycle_t_9a2e4f_idx"),
        ),
        migrations.AddIndex(
            model_name="documentexcessfee",
            index=models.Index(fields=["invoice_line_item"], name="finance_doc_invoice_8d1b3e_idx"),
        ),
        migrations.AddIndex(
            model_name="documentexcessfee",
            index=models.Index(fields=["document_request"], name="finance_doc_documen_6f2a9c_idx"),
        ),
    ]
