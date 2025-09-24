# Generated manually to add User-Person relationship
# This migration adds a OneToOneField from Person to User to enable
# linking authenticated users to their person profiles.

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("people", "0003_alter_studentauditlog_action"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="person",
            name="user",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="person",
                to=settings.AUTH_USER_MODEL,
                verbose_name="User Account",
                help_text="Associated user account for authentication",
            ),
        ),
        migrations.AddIndex(
            model_name="person",
            index=models.Index(fields=["user"], name="people_person_user_idx"),
        ),
    ]
