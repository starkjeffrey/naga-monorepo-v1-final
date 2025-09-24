"""
Data migration to handle model moves to proper domains.

This migration documents the refactoring but doesn't perform any data operations
since the models are being moved to different apps rather than renamed within the same app.

The actual migrations will be:
1. Create new models in destination apps
2. Migrate data from old to new tables
3. Remove old models from settings app
"""

from django.db import migrations


class Migration(migrations.Migration):
    """
    This migration removes models that have been moved to their proper domain apps:
    - GradeScale, GradeLevel → apps.grading.models_configurable
    - PaymentMethod → apps.finance.models.payment_configuration.PaymentConfiguration
    - NotificationTemplate → apps.common.models

    Before running this migration:
    1. Run migrations in grading, finance, and common apps to create new tables
    2. Run data migration to copy existing data to new tables
    3. Update all code references to use new model locations
    """

    dependencies = [
        ("settings", "0001_initial"),  # Replace with actual last migration
    ]

    operations = [
        migrations.RemoveField(
            model_name="gradelevel",
            name="grade_scale",
        ),
        migrations.DeleteModel(
            name="GradeLevel",
        ),
        migrations.DeleteModel(
            name="GradeScale",
        ),
        migrations.DeleteModel(
            name="PaymentMethod",
        ),
        migrations.DeleteModel(
            name="NotificationTemplate",
        ),
    ]
