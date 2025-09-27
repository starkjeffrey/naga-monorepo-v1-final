"""Enhanced grading with collaboration support."""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('grading', '0001_initial'),
        ('users', '0001_initial'),
    ]

    operations = [
        # Add collaboration tracking to grades
        migrations.AddField(
            model_name='grade',
            name='last_modified_by',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.SET_NULL,
                to='users.user',
                null=True,
                blank=True,
                related_name='modified_grades',
                help_text='User who last modified this grade'
            ),
        ),

        migrations.AddField(
            model_name='grade',
            name='modification_history',
            field=models.JSONField(
                null=True,
                blank=True,
                help_text='History of grade modifications with timestamps and users'
            ),
        ),

        migrations.AddField(
            model_name='grade',
            name='is_locked',
            field=models.BooleanField(
                default=False,
                help_text='Whether this grade is locked for editing'
            ),
        ),

        migrations.AddField(
            model_name='grade',
            name='locked_by',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.SET_NULL,
                to='users.user',
                null=True,
                blank=True,
                related_name='locked_grades',
                help_text='User who currently has this grade locked'
            ),
        ),

        migrations.AddField(
            model_name='grade',
            name='locked_at',
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text='When this grade was locked'
            ),
        ),

        # Add letter grade support
        migrations.AddField(
            model_name='grade',
            name='letter_grade',
            field=models.CharField(
                max_length=5,
                blank=True,
                help_text='Letter grade (A, B, C, D, F, etc.)'
            ),
        ),

        migrations.AddField(
            model_name='grade',
            name='grade_points',
            field=models.DecimalField(
                max_digits=4,
                decimal_places=2,
                null=True,
                blank=True,
                help_text='Grade points for GPA calculation (4.0 scale)'
            ),
        ),

        # Add assignment enhancements
        migrations.AddField(
            model_name='assignment',
            name='assignment_type',
            field=models.CharField(
                max_length=50,
                default='assignment',
                choices=[
                    ('homework', 'Homework'),
                    ('quiz', 'Quiz'),
                    ('exam', 'Exam'),
                    ('project', 'Project'),
                    ('participation', 'Participation'),
                    ('final', 'Final Grade'),
                    ('midterm', 'Midterm'),
                    ('lab', 'Lab Work'),
                    ('essay', 'Essay'),
                    ('presentation', 'Presentation'),
                ],
                help_text='Type of assignment'
            ),
        ),

        migrations.AddField(
            model_name='assignment',
            name='weight',
            field=models.DecimalField(
                max_digits=5,
                decimal_places=2,
                default=1.0,
                help_text='Weight of this assignment in final grade calculation'
            ),
        ),

        migrations.AddField(
            model_name='assignment',
            name='is_published',
            field=models.BooleanField(
                default=False,
                help_text='Whether grades for this assignment are published to students'
            ),
        ),

        migrations.AddField(
            model_name='assignment',
            name='rubric',
            field=models.JSONField(
                null=True,
                blank=True,
                help_text='Grading rubric as JSON structure'
            ),
        ),

        # Add performance indexes
        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS grade_last_modified_by_idx ON grading_grade(last_modified_by_id);",
            reverse_sql="DROP INDEX IF EXISTS grade_last_modified_by_idx;"
        ),

        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS grade_locked_by_idx ON grading_grade(locked_by_id);",
            reverse_sql="DROP INDEX IF EXISTS grade_locked_by_idx;"
        ),

        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS grade_is_locked_idx ON grading_grade(is_locked);",
            reverse_sql="DROP INDEX IF EXISTS grade_is_locked_idx;"
        ),

        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS assignment_type_idx ON grading_assignment(assignment_type);",
            reverse_sql="DROP INDEX IF EXISTS assignment_type_idx;"
        ),

        migrations.RunSQL(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS assignment_published_idx ON grading_assignment(is_published);",
            reverse_sql="DROP INDEX IF EXISTS assignment_published_idx;"
        ),
    ]