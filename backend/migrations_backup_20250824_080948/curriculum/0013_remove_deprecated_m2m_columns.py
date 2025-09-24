# Generated manually to remove deprecated direct columns for ManyToMany fields

from django.db import migrations


class Migration(migrations.Migration):
    """Remove deprecated direct TEXT columns that were replaced by proper junction tables.

    These columns exist in the backup but shouldn't be there as they represent
    ManyToMany relationships that should use junction tables.
    """

    dependencies = [
        ("curriculum", "0012_remove_deprecated_majors_column"),
    ]

    operations = [
        migrations.RunSQL(
            # Remove deprecated direct column if it exists
            sql="ALTER TABLE curriculum_seniorprojectgroup DROP COLUMN IF EXISTS students CASCADE;",
            reverse_sql="ALTER TABLE curriculum_seniorprojectgroup ADD COLUMN students TEXT;",
            state_operations=[],  # No state operations needed as field not in model
        ),
    ]
