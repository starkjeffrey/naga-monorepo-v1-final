# Generated manually to fix missing legacy_ipk column
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprofile',
            name='legacy_ipk',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='Identity Primary Key from legacy system for change tracking',
                null=True,
                verbose_name='Legacy System IPK'
            ),
        ),
    ]