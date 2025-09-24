# Migration to add new line item types for administrative fees

from django.db import migrations, models


class Migration(migrations.Migration):
    """Update InvoiceLineItem choices to include administrative fee types."""

    dependencies = [
        ("finance", "0027_add_administrative_fee_models"),
    ]

    operations = [
        migrations.AlterField(
            model_name="invoicelineitem",
            name="line_item_type",
            field=models.CharField(
                choices=[
                    ("COURSE", "Course Enrollment"),
                    ("FEE", "Fee"),
                    ("ADJUSTMENT", "Adjustment"),
                    ("REFUND", "Refund"),
                    ("ADMIN_FEE", "Administrative Fee"),
                    ("DOC_EXCESS", "Document Excess Fee"),
                ],
                help_text="Type of charge",
                max_length=20,
                verbose_name="Line Item Type",
            ),
        ),
    ]
