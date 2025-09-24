# Generated manually to remove deprecated majors column

from django.db import migrations


class Migration(migrations.Migration):
    """Remove deprecated majors column from curriculum_course table.

    This column was replaced by CanonicalRequirement for versioned major requirements.
    The column exists in the database but not in the model, causing backup/restore issues.
    """

    dependencies = [
        ("curriculum", "0011_fix_academic_journey_start_term_nullable"),
    ]

    operations = [
        migrations.RunSQL(
            # Remove the deprecated column if it exists
            sql="ALTER TABLE curriculum_course DROP COLUMN IF EXISTS majors CASCADE;",
            reverse_sql="ALTER TABLE curriculum_course ADD COLUMN majors TEXT;",
            state_operations=[],  # No state operations needed as field not in model
        ),
    ]
