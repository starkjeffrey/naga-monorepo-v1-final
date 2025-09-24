# Generated manually to remove deprecated direct columns for ManyToMany fields

from django.db import migrations


class Migration(migrations.Migration):
    """Remove deprecated direct TEXT column that was replaced by proper junction table.

    The matched_enrollments field is a ManyToMany that should use a junction table,
    not a direct TEXT column.
    """

    dependencies = [
        ("finance", "0036_alter_cashiersession_is_active_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            # Remove deprecated direct column if it exists
            sql="ALTER TABLE finance_reconciliation_status DROP COLUMN IF EXISTS matched_enrollments CASCADE;",
            reverse_sql="ALTER TABLE finance_reconciliation_status ADD COLUMN matched_enrollments TEXT;",
            state_operations=[],  # No state operations needed as field not in model
        ),
    ]
