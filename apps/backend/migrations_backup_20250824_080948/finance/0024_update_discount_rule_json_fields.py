"""
Update DiscountRule JSONFields to properly handle empty values.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0023_add_discount_rule_cycle_field"),
    ]

    operations = [
        migrations.AlterField(
            model_name="discountrule",
            name="applies_to_terms",
            field=models.JSONField(
                verbose_name="Applies to Terms",
                default=list,
                blank=True,
                help_text="List of terms this rule applies to (empty = all terms)",
            ),
        ),
        migrations.AlterField(
            model_name="discountrule",
            name="applies_to_programs",
            field=models.JSONField(
                verbose_name="Applies to Programs",
                default=list,
                blank=True,
                help_text="List of program codes this rule applies to (empty = all programs)",
            ),
        ),
    ]
