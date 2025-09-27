# Generated manually to remove orphaned junction table

from django.db import migrations


class Migration(migrations.Migration):
    """Remove orphaned curriculum_course_majors junction table.

    This table was from the old ManyToMany relationship between Course and Major
    which has been replaced by CanonicalRequirement.
    """

    dependencies = [
        ("curriculum", "0013_remove_deprecated_m2m_columns"),
    ]

    operations = [
        migrations.RunSQL(
            # Drop the orphaned junction table
            sql="DROP TABLE IF EXISTS curriculum_course_majors CASCADE;",
            reverse_sql="""
                CREATE TABLE curriculum_course_majors (
                    id SERIAL PRIMARY KEY,
                    course_id INTEGER,
                    major_id INTEGER
                );
            """,
            state_operations=[],  # No state operations needed as table not in model
        ),
    ]
