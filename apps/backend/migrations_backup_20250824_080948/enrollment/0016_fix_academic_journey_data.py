# Generated manually to fix AcademicJourney data

from django.db import migrations


def fix_program_types(apps, schema_editor):
    """Fix invalid program_type values and populate missing fields."""
    # Use raw SQL for data updates in migrations
    with schema_editor.connection.cursor() as cursor:
        # Fix invalid program_type values
        # "DEGREE" should be either "BA" or "MA"
        # Since we don't have enough info, default to "BA"
        cursor.execute(
            """
            UPDATE enrollment_academicjourney
            SET program_type = 'BA'
            WHERE program_type = 'DEGREE'
        """
        )

        # Any other invalid values, default to "BA"
        cursor.execute(
            """
            UPDATE enrollment_academicjourney
            SET program_type = 'BA'
            WHERE program_type NOT IN ('LANGUAGE', 'BA', 'MA', 'PHD', 'CERT')
        """
        )

        # Update empty term_code to a placeholder
        cursor.execute(
            """
            UPDATE enrollment_academicjourney
            SET term_code = 'UNKNOWN'
            WHERE term_code = ''
        """
        )


def reverse_fix(apps, schema_editor):
    """Reverse the fix - not really reversible but required."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("enrollment", "0015_academicjourney_multiple_records"),
    ]

    operations = [
        migrations.RunPython(fix_program_types, reverse_fix),
    ]
