# Migration to add DiscountApplication model

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Add DiscountApplication model to track when and how discounts are applied.

    This provides an audit trail for discount applications and links AR reconstruction
    to the main discount system.
    """

    dependencies = [
        ("curriculum", "0007_add_senior_project_group"),
        ("people", "0009_alter_studentphoto_managers_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("finance", "0025_move_discount_rule_to_discounts"),
    ]

    operations = [
        migrations.CreateModel(
            name="DiscountApplication",
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
                    "original_amount",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Amount before discount",
                        max_digits=10,
                        verbose_name="Original Amount",
                    ),
                ),
                (
                    "discount_amount",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Amount of discount applied",
                        max_digits=10,
                        verbose_name="Discount Amount",
                    ),
                ),
                (
                    "final_amount",
                    models.DecimalField(
                        decimal_places=2, help_text="Amount after discount", max_digits=10, verbose_name="Final Amount"
                    ),
                ),
                (
                    "applied_date",
                    models.DateTimeField(
                        auto_now_add=True, help_text="When the discount was applied", verbose_name="Applied Date"
                    ),
                ),
                (
                    "payment_date",
                    models.DateField(
                        help_text="Date of payment (for early bird eligibility)", verbose_name="Payment Date"
                    ),
                ),
                (
                    "authority",
                    models.CharField(
                        default="SYSTEM",
                        help_text="Who authorized the discount (SYSTEM, MANUAL, etc.)",
                        max_length=50,
                        verbose_name="Authority",
                    ),
                ),
                (
                    "approval_status",
                    models.CharField(
                        choices=[
                            ("APPROVED", "Approved"),
                            ("PENDING_APPROVAL", "Pending Approval"),
                            ("REJECTED", "Rejected"),
                        ],
                        default="APPROVED",
                        max_length=20,
                        verbose_name="Approval Status",
                    ),
                ),
                (
                    "notes",
                    models.TextField(
                        blank=True, help_text="Additional notes about this discount application", verbose_name="Notes"
                    ),
                ),
                (
                    "legacy_receipt_ipk",
                    models.IntegerField(
                        blank=True,
                        help_text="Link to legacy receipt if applied during reconstruction",
                        null=True,
                        verbose_name="Legacy Receipt IPK",
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
                    "discount_rule",
                    models.ForeignKey(
                        help_text="The rule that triggered this discount",
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="applications",
                        to="finance.discountrule",
                    ),
                ),
                (
                    "invoice",
                    models.ForeignKey(
                        blank=True,
                        help_text="Invoice this discount was applied to",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="discount_applications",
                        to="finance.invoice",
                    ),
                ),
                (
                    "payment",
                    models.ForeignKey(
                        blank=True,
                        help_text="Payment associated with this discount",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="discount_applications",
                        to="finance.payment",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="discount_applications",
                        to="people.studentprofile",
                    ),
                ),
                (
                    "term",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="discount_applications",
                        to="curriculum.term",
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
                "verbose_name": "Discount Application",
                "verbose_name_plural": "Discount Applications",
                "db_table": "finance_discount_application",
            },
        ),
        migrations.AddIndex(
            model_name="discountapplication",
            index=models.Index(fields=["student", "term"], name="finance_dis_student_2bd163_idx"),
        ),
        migrations.AddIndex(
            model_name="discountapplication",
            index=models.Index(fields=["discount_rule", "applied_date"], name="finance_dis_discoun_699413_idx"),
        ),
        migrations.AddIndex(
            model_name="discountapplication",
            index=models.Index(fields=["approval_status"], name="finance_dis_approva_569852_idx"),
        ),
        migrations.AddIndex(
            model_name="discountapplication",
            index=models.Index(fields=["legacy_receipt_ipk"], name="finance_dis_legacy__4e08c4_idx"),
        ),
    ]
