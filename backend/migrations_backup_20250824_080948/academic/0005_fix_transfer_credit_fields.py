# Fix TransferCredit field names to match model

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("academic", "0004_auto_20250123"),
    ]

    operations = [
        # Remove the index that references the old field name first
        migrations.RemoveIndex(
            model_name="transfercredit",
            name="academic_tr_interna_c2be59_idx",
        ),
        # Rename internal_equivalent_course to equivalent_course
        migrations.RenameField(
            model_name="transfercredit",
            old_name="internal_equivalent_course",
            new_name="equivalent_course",
        ),
        # Rename external_course_title to external_course_name
        migrations.RenameField(
            model_name="transfercredit",
            old_name="external_course_title",
            new_name="external_course_name",
        ),
        migrations.RemoveField(
            model_name="transfercredit",
            name="approved_at",
        ),
        migrations.RemoveField(
            model_name="transfercredit",
            name="approved_by",
        ),
        migrations.RemoveField(
            model_name="transfercredit",
            name="documentation_provided",
        ),
        migrations.RemoveField(
            model_name="transfercredit",
            name="internal_credits",
        ),
        migrations.RemoveField(
            model_name="transfercredit",
            name="notes",
        ),
        migrations.RemoveField(
            model_name="transfercredit",
            name="rejection_reason",
        ),
        migrations.RemoveField(
            model_name="transfercredit",
            name="syllabus_reviewed",
        ),
        # Add new fields that are in the model but not in DB
        migrations.AddField(
            model_name="transfercredit",
            name="documentation",
            field=models.TextField(
                blank=True,
                help_text="Documentation provided for evaluation",
                verbose_name="Documentation",
            ),
        ),
        migrations.AddField(
            model_name="transfercredit",
            name="review_date",
            field=models.DateField(
                blank=True,
                help_text="Date when the transfer was reviewed",
                null=True,
                verbose_name="Review Date",
            ),
        ),
        migrations.AddField(
            model_name="transfercredit",
            name="review_notes",
            field=models.TextField(
                blank=True,
                help_text="Administrative notes about the review",
                verbose_name="Review Notes",
            ),
        ),
        migrations.AddField(
            model_name="transfercredit",
            name="reviewed_by",
            field=models.ForeignKey(
                blank=True,
                help_text="User who reviewed this transfer",
                null=True,
                on_delete=models.deletion.SET_NULL,
                related_name="reviewed_transfers",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Reviewed By",
            ),
        ),
        migrations.AddField(
            model_name="transfercredit",
            name="term_taken",
            field=models.CharField(
                blank=True,
                help_text="Term/semester when course was taken",
                max_length=50,
                verbose_name="Term Taken",
            ),
        ),
        migrations.AddField(
            model_name="transfercredit",
            name="year_taken",
            field=models.PositiveIntegerField(
                blank=True,
                help_text="Year when course was taken",
                null=True,
                verbose_name="Year Taken",
            ),
        ),
        # Add the index back with the correct field name
        migrations.AddIndex(
            model_name="transfercredit",
            index=models.Index(
                fields=["equivalent_course"],
                name="academic_tr_equival_c2be59_idx",
            ),
        ),
    ]
