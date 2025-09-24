# Generated manually for notes processing integration

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0017_fix_reconciliation_schema_mismatches"),
    ]

    operations = [
        migrations.AddField(
            model_name="legacyreceiptmapping",
            name="legacy_notes",
            field=models.TextField(
                blank=True,
                help_text="Original Notes field from receipt_headers",
                verbose_name="Legacy Notes",
            ),
        ),
        migrations.AddField(
            model_name="legacyreceiptmapping",
            name="parsed_note_type",
            field=models.CharField(
                blank=True,
                help_text="Parsed note type from notes processor",
                max_length=50,
                verbose_name="Parsed Note Type",
            ),
        ),
        migrations.AddField(
            model_name="legacyreceiptmapping",
            name="parsed_amount_adjustment",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Amount adjustment extracted from notes",
                max_digits=10,
                null=True,
                verbose_name="Parsed Amount Adjustment",
            ),
        ),
        migrations.AddField(
            model_name="legacyreceiptmapping",
            name="parsed_percentage_adjustment",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Percentage adjustment extracted from notes",
                max_digits=5,
                null=True,
                verbose_name="Parsed Percentage Adjustment",
            ),
        ),
        migrations.AddField(
            model_name="legacyreceiptmapping",
            name="parsed_authority",
            field=models.CharField(
                blank=True,
                help_text="Authority/approver extracted from notes",
                max_length=100,
                verbose_name="Parsed Authority",
            ),
        ),
        migrations.AddField(
            model_name="legacyreceiptmapping",
            name="parsed_reason",
            field=models.CharField(
                blank=True,
                help_text="Reason/explanation extracted from notes",
                max_length=200,
                verbose_name="Parsed Reason",
            ),
        ),
        migrations.AddField(
            model_name="legacyreceiptmapping",
            name="notes_processing_confidence",
            field=models.DecimalField(
                decimal_places=2,
                default=0.0,
                help_text="Confidence score from notes processing (0.0-1.0)",
                max_digits=3,
                verbose_name="Notes Processing Confidence",
            ),
        ),
        migrations.AddField(
            model_name="legacyreceiptmapping",
            name="ar_transaction_mapping",
            field=models.CharField(
                blank=True,
                help_text="Where this note element should be recorded in A/R transaction",
                max_length=50,
                verbose_name="A/R Transaction Mapping",
            ),
        ),
        migrations.AddField(
            model_name="legacyreceiptmapping",
            name="normalized_note",
            field=models.TextField(
                blank=True,
                help_text="Normalized note string for automated processing",
                verbose_name="Normalized Note",
            ),
        ),
    ]
