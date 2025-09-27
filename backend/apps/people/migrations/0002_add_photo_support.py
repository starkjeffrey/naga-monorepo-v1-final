"""Add photo support for students."""

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('people', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentPhoto',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('unique_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('photo', models.ImageField(
                    upload_to='student_photos/%Y/%m/',
                    help_text='Student photo image file'
                )),
                ('thumbnail', models.ImageField(
                    upload_to='student_photos/thumbnails/%Y/%m/',
                    blank=True,
                    null=True,
                    help_text='Auto-generated thumbnail'
                )),
                ('file_size', models.PositiveIntegerField(
                    default=0,
                    help_text='File size in bytes'
                )),
                ('width', models.PositiveIntegerField(
                    default=0,
                    help_text='Image width in pixels'
                )),
                ('height', models.PositiveIntegerField(
                    default=0,
                    help_text='Image height in pixels'
                )),
                ('content_type', models.CharField(
                    max_length=100,
                    default='image/jpeg',
                    help_text='Image MIME type'
                )),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student_profile', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='people.studentprofile',
                    related_name='photo'
                )),
                ('uploaded_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.SET_NULL,
                    to='users.user',
                    null=True,
                    blank=True,
                    help_text='User who uploaded the photo'
                )),
            ],
            options={
                'verbose_name': 'Student Photo',
                'verbose_name_plural': 'Student Photos',
                'db_table': 'people_student_photo',
            },
        ),

        # Add emergency contact support
        migrations.CreateModel(
            name='EmergencyContact',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('unique_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('name', models.CharField(
                    max_length=200,
                    help_text='Full name of emergency contact'
                )),
                ('relationship', models.CharField(
                    max_length=100,
                    help_text='Relationship to student (e.g., parent, guardian, spouse)'
                )),
                ('phone_primary', models.CharField(
                    max_length=20,
                    help_text='Primary phone number'
                )),
                ('phone_secondary', models.CharField(
                    max_length=20,
                    blank=True,
                    help_text='Secondary phone number'
                )),
                ('email', models.EmailField(
                    blank=True,
                    help_text='Email address'
                )),
                ('address', models.TextField(
                    blank=True,
                    help_text='Physical address'
                )),
                ('is_primary', models.BooleanField(
                    default=False,
                    help_text='Primary emergency contact'
                )),
                ('is_authorized_pickup', models.BooleanField(
                    default=False,
                    help_text='Authorized to pick up student'
                )),
                ('notes', models.TextField(
                    blank=True,
                    help_text='Additional notes or instructions'
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('student_profile', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='people.studentprofile',
                    related_name='emergency_contacts'
                )),
            ],
            options={
                'verbose_name': 'Emergency Contact',
                'verbose_name_plural': 'Emergency Contacts',
                'db_table': 'people_emergency_contact',
                'ordering': ['-is_primary', 'name'],
            },
        ),

        # Add indexes for performance
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS people_student_photo_student_profile_id_idx ON people_student_photo(student_profile_id);",
            reverse_sql="DROP INDEX IF EXISTS people_student_photo_student_profile_id_idx;"
        ),

        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS people_emergency_contact_student_profile_id_idx ON people_emergency_contact(student_profile_id);",
            reverse_sql="DROP INDEX IF EXISTS people_emergency_contact_student_profile_id_idx;"
        ),
    ]