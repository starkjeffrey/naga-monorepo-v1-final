# Generated manually to remove deprecated direct columns for ManyToMany fields

from django.db import migrations


class Migration(migrations.Migration):
    """Remove deprecated direct TEXT column that was replaced by proper junction table.

    The affected_class_parts field is a ManyToMany that should use a junction table,
    not a direct TEXT column.
    """

    dependencies = [
        ("people", "0011_sync_with_database"),
    ]

    operations = [
        migrations.RunSQL(
            # Remove deprecated direct column if it exists
            sql="ALTER TABLE people_teacherleaverequest DROP COLUMN IF EXISTS affected_class_parts CASCADE;",
            reverse_sql="ALTER TABLE people_teacherleaverequest ADD COLUMN affected_class_parts TEXT;",
            state_operations=[],  # No state operations needed as field not in model
        ),
    ]
