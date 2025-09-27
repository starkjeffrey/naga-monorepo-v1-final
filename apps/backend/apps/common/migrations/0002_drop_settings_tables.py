# Migration to drop tables from removed settings app
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('common', '0001_initial'),
    ]

    operations = [
        # Drop the settings_systemsetting table
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS settings_systemsetting CASCADE;",
            reverse_sql="-- Cannot reverse table drop",
        ),
        # Drop the django_migrations entry for settings app
        migrations.RunSQL(
            sql="DELETE FROM django_migrations WHERE app = 'settings';",
            reverse_sql="-- Cannot reverse migration record deletion",
        ),
    ]