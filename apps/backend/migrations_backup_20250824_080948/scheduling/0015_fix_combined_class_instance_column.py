# Generated manually to fix column naming issue

from django.db import migrations


class Migration(migrations.Migration):
    """Fix column name for combined_class_instance foreign key.

    The backup has 'combined_class_instance_id' but Django expects the column
    to match the field name 'combined_class_instance' (Django adds _id suffix
    automatically for the FK constraint).
    """

    dependencies = [
        ("scheduling", "0014_sync_with_database"),
    ]

    operations = [
        migrations.RunSQL(
            # Rename column if the incorrect name exists
            sql="""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'scheduling_classheader'
                        AND column_name = 'combined_class_instance_id'
                    ) THEN
                        ALTER TABLE scheduling_classheader
                        RENAME COLUMN combined_class_instance_id TO combined_class_instance;
                    END IF;
                END $$;
            """,
            reverse_sql="""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'scheduling_classheader'
                        AND column_name = 'combined_class_instance'
                    ) THEN
                        ALTER TABLE scheduling_classheader
                        RENAME COLUMN combined_class_instance TO combined_class_instance_id;
                    END IF;
                END $$;
            """,
            state_operations=[],
        ),
    ]
