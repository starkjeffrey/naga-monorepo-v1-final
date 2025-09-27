"""
Update Fee Pricing to support document fees and improve clarity.

Changes:
1. Change FeeType choice from 'TRANSCRIPT' to 'DOCUMENT' (broader scope)
2. Add is_per_document field for per-document pricing
3. Improve help text for better clarity on fee types
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0030_add_schedule_criteria_to_discount_rule"),
    ]

    operations = [
        # Add the new is_per_document field
        migrations.AddField(
            model_name="feepricing",
            name="is_per_document",
            field=models.BooleanField(
                default=False,
                help_text="Whether this fee is charged per document (transcripts, certificates, etc.)",
                verbose_name="Is Per Document",
            ),
        ),
        # Data migration to update existing TRANSCRIPT fees to DOCUMENT
        migrations.RunSQL(
            sql="UPDATE finance_fee_pricing SET fee_type = 'DOCUMENT' WHERE fee_type = 'TRANSCRIPT';",
            reverse_sql="UPDATE finance_fee_pricing SET fee_type = 'TRANSCRIPT' WHERE fee_type = 'DOCUMENT';",
        ),
    ]
