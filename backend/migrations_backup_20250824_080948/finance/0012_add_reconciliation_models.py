# Generated manually to add reconciliation models

import datetime
from decimal import Decimal

import django.core.validators
import django.db.models.deletion
import django.db.models.manager
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("curriculum", "0004_alter_course_code"),
        ("enrollment", "0005_alter_programenrollment_cycle_and_more"),
        ("finance", "0010_update_reading_class_pricing_fields"),
        ("people", "0009_alter_studentphoto_managers_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Create reconciliation models only
        migrations.CreateModel(
            name="MaterialityThreshold",
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
                    "is_deleted",
                    models.BooleanField(
                        default=False,
                        help_text="Indicates if this record has been soft deleted",
                        verbose_name="Is deleted",
                    ),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Date and time when the record was marked as deleted",
                        null=True,
                        verbose_name="Deleted at",
                    ),
                ),
                (
                    "context",
                    models.CharField(
                        choices=[
                            ("INDIVIDUAL", "Individual Payment"),
                            ("STUDENT", "Student Account Total"),
                            ("BATCH", "Batch Total"),
                            ("PERIOD", "Period Aggregate"),
                            ("ERROR_CAT", "Error Category Total"),
                        ],
                        max_length=20,
                        unique=True,
                        verbose_name="Context",
                    ),
                ),
                (
                    "absolute_threshold",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Absolute dollar amount threshold",
                        max_digits=10,
                        verbose_name="Absolute Threshold",
                    ),
                ),
                (
                    "percentage_threshold",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Percentage threshold (if applicable)",
                        max_digits=5,
                        null=True,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(100),
                        ],
                        verbose_name="Percentage Threshold",
                    ),
                ),
                (
                    "effective_date",
                    models.DateField(default=datetime.date.today, verbose_name="Effective Date"),
                ),
                ("notes", models.TextField(blank=True, verbose_name="Notes")),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(app_label)s_%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created by",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(app_label)s_%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Updated by",
                    ),
                ),
            ],
            options={
                "verbose_name": "Materiality Threshold",
                "verbose_name_plural": "Materiality Thresholds",
                "db_table": "finance_materiality_threshold",
                "ordering": ["context", "-effective_date"],
            },
            managers=[
                ("all_objects", django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name="ReconciliationBatch",
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
                    "is_deleted",
                    models.BooleanField(
                        default=False,
                        help_text="Indicates if this record has been soft deleted",
                        verbose_name="Is deleted",
                    ),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Date and time when the record was marked as deleted",
                        null=True,
                        verbose_name="Deleted at",
                    ),
                ),
                (
                    "batch_id",
                    models.CharField(max_length=50, unique=True, verbose_name="Batch ID"),
                ),
                (
                    "batch_type",
                    models.CharField(
                        choices=[
                            ("INITIAL", "Initial Reconciliation"),
                            ("REFINEMENT", "Refinement Pass"),
                            ("MANUAL", "Manual Review"),
                            ("SCHEDULED", "Scheduled Run"),
                        ],
                        default="SCHEDULED",
                        max_length=20,
                        verbose_name="Batch Type",
                    ),
                ),
                ("start_date", models.DateField(verbose_name="Start Date")),
                ("end_date", models.DateField(verbose_name="End Date")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("PENDING", "Pending"),
                            ("PROCESSING", "Processing"),
                            ("COMPLETED", "Completed"),
                            ("FAILED", "Failed"),
                            ("PARTIAL", "Partially Completed"),
                        ],
                        default="PENDING",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                (
                    "total_payments",
                    models.PositiveIntegerField(default=0, verbose_name="Total Payments"),
                ),
                (
                    "processed_payments",
                    models.PositiveIntegerField(default=0, verbose_name="Processed Payments"),
                ),
                (
                    "successful_matches",
                    models.PositiveIntegerField(default=0, verbose_name="Successful Matches"),
                ),
                (
                    "failed_matches",
                    models.PositiveIntegerField(default=0, verbose_name="Failed Matches"),
                ),
                (
                    "started_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Started At"),
                ),
                (
                    "completed_at",
                    models.DateTimeField(blank=True, null=True, verbose_name="Completed At"),
                ),
                (
                    "parameters",
                    models.JSONField(
                        default=dict,
                        help_text="Batch processing parameters",
                        verbose_name="Parameters",
                    ),
                ),
                (
                    "results_summary",
                    models.JSONField(default=dict, verbose_name="Results Summary"),
                ),
                ("error_log", models.TextField(blank=True, verbose_name="Error Log")),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(app_label)s_%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created by",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(app_label)s_%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Updated by",
                    ),
                ),
            ],
            options={
                "verbose_name": "Reconciliation Batch",
                "verbose_name_plural": "Reconciliation Batches",
                "db_table": "finance_reconciliation_batch",
                "ordering": ["-created_at"],
            },
            managers=[
                ("all_objects", django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name="ReconciliationRule",
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
                    "is_deleted",
                    models.BooleanField(
                        default=False,
                        help_text="Indicates if this record has been soft deleted",
                        verbose_name="Is deleted",
                    ),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Date and time when the record was marked as deleted",
                        null=True,
                        verbose_name="Deleted at",
                    ),
                ),
                (
                    "rule_type",
                    models.CharField(
                        choices=[
                            ("AMOUNT_MATCH", "Exact Amount Match"),
                            ("TOLERANCE", "Amount Within Tolerance"),
                            ("PATTERN", "Historical Pattern Match"),
                            ("DATE_RANGE", "Date Range Validation"),
                            ("STUDENT_MATCH", "Student ID Matching"),
                            ("REFERENCE", "Reference Number Match"),
                            ("MULTIPLE_ENR", "Multiple Enrollment Check"),
                        ],
                        max_length=20,
                        verbose_name="Rule Type",
                    ),
                ),
                (
                    "description",
                    models.CharField(max_length=200, verbose_name="Description"),
                ),
                (
                    "priority",
                    models.PositiveIntegerField(
                        default=1,
                        help_text="Lower numbers = higher priority",
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(100),
                        ],
                        verbose_name="Priority",
                    ),
                ),
                (
                    "is_active",
                    models.BooleanField(default=True, verbose_name="Is Active"),
                ),
                (
                    "parameters",
                    models.JSONField(
                        default=dict,
                        help_text="Rule-specific parameters (tolerance amounts, date ranges, etc.)",
                        verbose_name="Parameters",
                    ),
                ),
                (
                    "success_count",
                    models.PositiveIntegerField(default=0, verbose_name="Success Count"),
                ),
                (
                    "failure_count",
                    models.PositiveIntegerField(default=0, verbose_name="Failure Count"),
                ),
                (
                    "last_used",
                    models.DateTimeField(blank=True, null=True, verbose_name="Last Used"),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(app_label)s_%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created by",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(app_label)s_%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Updated by",
                    ),
                ),
            ],
            options={
                "verbose_name": "Reconciliation Rule",
                "verbose_name_plural": "Reconciliation Rules",
                "db_table": "finance_reconciliation_rule",
                "ordering": ["priority", "rule_type"],
            },
            managers=[
                ("all_objects", django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name="ReconciliationStatus",
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
                    "is_deleted",
                    models.BooleanField(
                        default=False,
                        help_text="Indicates if this record has been soft deleted",
                        verbose_name="Is deleted",
                    ),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Date and time when the record was marked as deleted",
                        null=True,
                        verbose_name="Deleted at",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("UNMATCHED", "Unmatched"),
                            ("MATCHED", "Matched"),
                            ("RECONCILED", "Reconciled"),
                            ("VARIANCE", "Has Variance"),
                            ("ERROR", "Error"),
                            ("MANUAL_REVIEW", "Manual Review Required"),
                            ("REFINEMENT", "Refinement Required"),
                        ],
                        default="UNMATCHED",
                        max_length=20,
                        verbose_name="Status",
                    ),
                ),
                (
                    "confidence_score",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0"),
                        help_text="Confidence in the match (0-100)",
                        max_digits=5,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(100),
                        ],
                        verbose_name="Confidence Score",
                    ),
                ),
                (
                    "variance_amount",
                    models.DecimalField(
                        decimal_places=2,
                        default=Decimal("0"),
                        max_digits=10,
                        verbose_name="Variance Amount",
                    ),
                ),
                (
                    "variance_percentage",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        max_digits=5,
                        null=True,
                        verbose_name="Variance Percentage",
                    ),
                ),
                (
                    "match_reason",
                    models.TextField(
                        blank=True,
                        help_text="Reason for the match/status",
                        verbose_name="Match Reason",
                    ),
                ),
                (
                    "confidence_evolution",
                    models.JSONField(
                        default=list,
                        help_text="History of confidence score changes",
                        verbose_name="Confidence Evolution",
                    ),
                ),
                (
                    "last_attempt_date",
                    models.DateTimeField(blank=True, null=True, verbose_name="Last Attempt Date"),
                ),
                (
                    "attempt_count",
                    models.PositiveIntegerField(default=0, verbose_name="Attempt Count"),
                ),
                ("notes", models.TextField(blank=True, verbose_name="Notes")),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(app_label)s_%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created by",
                    ),
                ),
                (
                    "matched_enrollments",
                    models.ManyToManyField(
                        blank=True,
                        help_text="Enrollments matched to this payment",
                        related_name="reconciliation_statuses",
                        to="enrollment.classheaderenrollment",
                        verbose_name="Matched Enrollments",
                    ),
                ),
                (
                    "payment",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="reconciliation_status",
                        to="finance.payment",
                        verbose_name="Payment",
                    ),
                ),
                (
                    "reconciled_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reconciled_payments",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Reconciled By",
                    ),
                ),
                (
                    "reconciliation_batch",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="statuses",
                        to="finance.reconciliationbatch",
                        verbose_name="Reconciliation Batch",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(app_label)s_%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Updated by",
                    ),
                ),
            ],
            options={
                "verbose_name": "Reconciliation Status",
                "verbose_name_plural": "Reconciliation Statuses",
                "db_table": "finance_reconciliation_status",
                "ordering": ["-created_at"],
            },
            managers=[
                ("all_objects", django.db.models.manager.Manager()),
            ],
        ),
        migrations.CreateModel(
            name="ReconciliationAdjustment",
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
                    "is_deleted",
                    models.BooleanField(
                        default=False,
                        help_text="Indicates if this record has been soft deleted",
                        verbose_name="Is deleted",
                    ),
                ),
                (
                    "deleted_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="Date and time when the record was marked as deleted",
                        null=True,
                        verbose_name="Deleted at",
                    ),
                ),
                (
                    "adjustment_type",
                    models.CharField(
                        choices=[
                            ("PRICING", "Pricing Variance"),
                            ("MISSING_ENR", "Missing Enrollment"),
                            ("MISSING_PAY", "Missing Payment"),
                            ("DUPLICATE", "Duplicate Payment"),
                            ("CURRENCY", "Currency Difference"),
                            ("CLERICAL", "Clerical Error"),
                            ("DISCOUNT", "Discount Applied"),
                            ("FEE_ADJ", "Fee Adjustment"),
                            ("TIMING", "Timing Difference"),
                        ],
                        max_length=20,
                        verbose_name="Adjustment Type",
                    ),
                ),
                (
                    "description",
                    models.CharField(max_length=200, verbose_name="Description"),
                ),
                (
                    "original_amount",
                    models.DecimalField(decimal_places=2, max_digits=10, verbose_name="Original Amount"),
                ),
                (
                    "adjusted_amount",
                    models.DecimalField(decimal_places=2, max_digits=10, verbose_name="Adjusted Amount"),
                ),
                (
                    "variance",
                    models.DecimalField(decimal_places=2, max_digits=10, verbose_name="Variance"),
                ),
                (
                    "requires_approval",
                    models.BooleanField(
                        default=False,
                        help_text="True if variance exceeds materiality threshold",
                        verbose_name="Requires Approval",
                    ),
                ),
                (
                    "approved_date",
                    models.DateTimeField(blank=True, null=True, verbose_name="Approved Date"),
                ),
                (
                    "approved_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="approved_adjustments",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Approved By",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(app_label)s_%(class)s_created",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Created by",
                    ),
                ),
                (
                    "gl_account",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reconciliation_adjustments",
                        to="finance.glaccount",
                        verbose_name="GL Account",
                    ),
                ),
                (
                    "journal_entry",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reconciliation_adjustments",
                        to="finance.journalentry",
                        verbose_name="Journal Entry",
                    ),
                ),
                (
                    "payment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="adjustments",
                        to="finance.payment",
                        verbose_name="Payment",
                    ),
                ),
                (
                    "reconciliation_batch",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="adjustments",
                        to="finance.reconciliationbatch",
                        verbose_name="Reconciliation Batch",
                    ),
                ),
                (
                    "reconciliation_status",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="adjustments",
                        to="finance.reconciliationstatus",
                        verbose_name="Reconciliation Status",
                    ),
                ),
                (
                    "student",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reconciliation_adjustments",
                        to="people.studentprofile",
                        verbose_name="Student",
                    ),
                ),
                (
                    "term",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="reconciliation_adjustments",
                        to="curriculum.term",
                        verbose_name="Term",
                    ),
                ),
                (
                    "updated_by",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="%(app_label)s_%(class)s_updated",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Updated by",
                    ),
                ),
            ],
            options={
                "verbose_name": "Reconciliation Adjustment",
                "verbose_name_plural": "Reconciliation Adjustments",
                "db_table": "finance_reconciliation_adjustment",
                "ordering": ["-created_at"],
            },
            managers=[
                ("all_objects", django.db.models.manager.Manager()),
            ],
        ),
        # Add indexes
        migrations.AddIndex(
            model_name="reconciliationbatch",
            index=models.Index(fields=["status", "created_at"], name="finance_rec_status_867ff7_idx"),
        ),
        migrations.AddIndex(
            model_name="reconciliationbatch",
            index=models.Index(
                fields=["batch_type", "created_at"],
                name="finance_rec_batch_t_905868_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="reconciliationrule",
            index=models.Index(fields=["is_active", "priority"], name="finance_rec_is_acti_e5d245_idx"),
        ),
        migrations.AddIndex(
            model_name="reconciliationrule",
            index=models.Index(fields=["rule_type", "is_active"], name="finance_rec_rule_ty_8c712f_idx"),
        ),
        migrations.AddIndex(
            model_name="reconciliationstatus",
            index=models.Index(
                fields=["status", "confidence_score"],
                name="finance_rec_status_59a4fd_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="reconciliationstatus",
            index=models.Index(fields=["last_attempt_date"], name="finance_rec_last_at_862647_idx"),
        ),
        migrations.AddIndex(
            model_name="reconciliationstatus",
            index=models.Index(fields=["reconciliation_batch"], name="finance_rec_reconci_92d1ea_idx"),
        ),
        migrations.AddIndex(
            model_name="reconciliationadjustment",
            index=models.Index(
                fields=["adjustment_type", "created_at"],
                name="finance_rec_adjustm_8b3e44_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="reconciliationadjustment",
            index=models.Index(fields=["student", "term"], name="finance_rec_student_22fd26_idx"),
        ),
        migrations.AddIndex(
            model_name="reconciliationadjustment",
            index=models.Index(fields=["reconciliation_batch"], name="finance_rec_reconci_3999e3_idx"),
        ),
        migrations.AddIndex(
            model_name="reconciliationadjustment",
            index=models.Index(
                fields=["requires_approval", "approved_date"],
                name="finance_rec_require_353e26_idx",
            ),
        ),
    ]
