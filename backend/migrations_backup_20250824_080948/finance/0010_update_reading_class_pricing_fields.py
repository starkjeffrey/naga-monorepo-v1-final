# Manual migration to update ReadingClassPricing fields
# Generated manually on 2025-07-25

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0009_update_feepricing_remove_pricing_tier"),
    ]

    operations = [
        # Remove old fields from ReadingClassPricing
        migrations.RemoveField(
            model_name="readingclasspricing",
            name="minimum_revenue",
        ),
        migrations.RemoveField(
            model_name="readingclasspricing",
            name="price_per_student",
        ),
        # Add new fields to ReadingClassPricing
        migrations.AddField(
            model_name="readingclasspricing",
            name="domestic_price",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Price per student for domestic students",
                max_digits=10,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Domestic Price",
            ),
        ),
        migrations.AddField(
            model_name="readingclasspricing",
            name="foreign_price",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text="Price per student for international students",
                max_digits=10,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Foreign Price",
            ),
        ),
    ]
