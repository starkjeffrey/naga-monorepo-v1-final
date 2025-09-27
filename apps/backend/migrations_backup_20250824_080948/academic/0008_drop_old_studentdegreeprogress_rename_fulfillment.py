# Migration to fix table naming conflict
# 1. Drop the old empty StudentDegreeProgress table
# 2. Rename CanonicalRequirementFulfillment table to StudentDegreeProgress

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("academic", "0007_add_consolidation_fields"),
    ]

    operations = [
        # First, drop the old empty StudentDegreeProgress table
        migrations.RunSQL(
            "DROP TABLE IF EXISTS academic_studentdegreeprogress CASCADE;", reverse_sql="-- Cannot reverse table drop"
        ),
        # Then rename CanonicalRequirementFulfillment to StudentDegreeProgress
        migrations.RenameModel(
            old_name="CanonicalRequirementFulfillment",
            new_name="StudentDegreeProgress",
        ),
    ]
