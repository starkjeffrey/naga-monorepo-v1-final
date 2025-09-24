"""
Add schedule criteria field to DiscountRule for time-of-day based discounts.

This migration adds the applies_to_schedule JSON field to support
time-of-day and cycle-based discount rules as requested for the
AR reconstruction enhancement.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("finance", "0029_alter_administrativefeeconfig_managers_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="discountrule",
            name="applies_to_schedule",
            field=models.JSONField(
                verbose_name="Schedule Criteria",
                default=dict,
                blank=True,
                help_text="Time-of-day and cycle-based discount criteria (JSON format)",
            ),
        ),
    ]
