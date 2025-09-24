# Generated manually to remove incorrect direct column for Django's built-in M2M

from django.db import migrations


class Migration(migrations.Migration):
    """Remove incorrect permissions TEXT column from auth_group table.

    Django's auth_group.permissions is a ManyToMany that uses auth_group_permissions
    junction table, not a direct column.
    """

    dependencies = [
        ("accounts", "0002_initial"),
    ]

    operations = [
        migrations.RunSQL(
            # Remove incorrect direct column if it exists
            sql="ALTER TABLE auth_group DROP COLUMN IF EXISTS permissions CASCADE;",
            reverse_sql="ALTER TABLE auth_group ADD COLUMN permissions TEXT;",
            state_operations=[],  # No state operations needed as Django built-in
        ),
    ]
