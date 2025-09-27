"""Enhanced attendance tracking with location and method support."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0001_initial'),
    ]

    operations = [
        # Add new fields to existing AttendanceRecord model
        migrations.AddField(
            model_name='attendancerecord',
            name='check_in_time',
            field=models.TimeField(
                null=True,
                blank=True,
                help_text='Time when student checked in'
            ),
        ),

        migrations.AddField(
            model_name='attendancerecord',
            name='check_out_time',
            field=models.TimeField(
                null=True,
                blank=True,
                help_text='Time when student checked out'
            ),
        ),

        migrations.AddField(
            model_name='attendancerecord',
            name='location',
            field=models.CharField(
                max_length=200,
                blank=True,
                help_text='Location where attendance was recorded (e.g., classroom, building)'
            ),
        ),

        migrations.AddField(
            model_name='attendancerecord',
            name='method',
            field=models.CharField(
                max_length=50,
                default='manual',
                choices=[
                    ('manual', 'Manual Entry'),
                    ('qr_scan', 'QR Code Scan'),
                    ('biometric', 'Biometric'),
                    ('card_swipe', 'Card Swipe'),
                    ('mobile_app', 'Mobile App'),
                ],
                help_text='Method used to record attendance'
            ),
        ),

        migrations.AddField(
            model_name='attendancerecord',
            name='device_info',
            field=models.JSONField(
                null=True,
                blank=True,
                help_text='Information about the device used to record attendance'
            ),
        ),

        migrations.AddField(
            model_name='attendancerecord',
            name='verification_code',
            field=models.CharField(
                max_length=100,
                blank=True,
                help_text='Verification code for QR or other digital attendance methods'
            ),
        ),

        migrations.AddField(
            model_name='attendancerecord',
            name='late_minutes',
            field=models.PositiveIntegerField(
                null=True,
                blank=True,
                help_text='Number of minutes late (calculated automatically)'
            ),
        ),

        migrations.AddField(
            model_name='attendancerecord',
            name='excused_reason',
            field=models.TextField(
                blank=True,
                help_text='Reason for excused absence or tardiness'
            ),
        ),

        # Add performance indexes
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS attendance_record_date_idx ON attendance_attendancerecord(date);",
            reverse_sql="DROP INDEX IF EXISTS attendance_record_date_idx;"
        ),

        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS attendance_record_status_idx ON attendance_attendancerecord(status);",
            reverse_sql="DROP INDEX IF EXISTS attendance_record_status_idx;"
        ),

        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS attendance_record_method_idx ON attendance_attendancerecord(method);",
            reverse_sql="DROP INDEX IF EXISTS attendance_record_method_idx;"
        ),

        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS attendance_record_student_date_idx ON attendance_attendancerecord(student_profile_id, date);",
            reverse_sql="DROP INDEX IF EXISTS attendance_record_student_date_idx;"
        ),
    ]