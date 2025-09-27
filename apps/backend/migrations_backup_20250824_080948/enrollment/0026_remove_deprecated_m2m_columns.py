# Generated manually to remove deprecated direct columns for ManyToMany fields

from django.db import migrations


class Migration(migrations.Migration):
    """Remove deprecated direct TEXT column that was replaced by proper junction table.

    The missing_prerequisites field is a ManyToMany that should use a junction table,
    not a direct TEXT column.
    """

    dependencies = [
        ("enrollment", "0025_alter_academicjourney_start_date"),
    ]

    operations = [
        migrations.RunSQL(
            # Remove deprecated direct column if it exists
            sql="ALTER TABLE enrollment_studentcourseeligibility DROP COLUMN IF EXISTS missing_prerequisites CASCADE;",
            reverse_sql="ALTER TABLE enrollment_studentcourseeligibility ADD COLUMN missing_prerequisites TEXT;",
            state_operations=[],  # No state operations needed as field not in model
        ),
    ]
