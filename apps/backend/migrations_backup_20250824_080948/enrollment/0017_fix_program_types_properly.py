# Generated manually to properly fix AcademicJourney program types

from django.db import migrations


def fix_program_types_properly(apps, schema_editor):
    """Fix program_type values based on actual program relationships."""

    with schema_editor.connection.cursor() as cursor:
        # First, for records with a program_id, use the Major's degree_awarded to set program_type
        cursor.execute(
            """
            UPDATE enrollment_academicjourney aj
            SET program_type = CASE
                -- Language programs
                WHEN m.program_type = 'LANGUAGE' THEN 'LANGUAGE'
                -- Degree programs based on degree_awarded
                WHEN m.degree_awarded IN ('BA', 'AA') THEN 'BA'
                WHEN m.degree_awarded IN ('MA', 'MBA', 'MEd') THEN 'MA'
                WHEN m.degree_awarded = 'PHD' THEN 'PHD'
                WHEN m.degree_awarded = 'CERT' THEN 'CERT'
                -- Default based on program_type
                WHEN m.program_type = 'ACADEMIC' THEN 'BA'
                ELSE 'BA'
            END
            FROM curriculum_major m
            WHERE aj.program_id = m.id
            AND aj.program_id IS NOT NULL
        """
        )

        # For records without a program_id, analyze enrollment history
        cursor.execute(
            """
            WITH student_programs AS (
                SELECT DISTINCT
                    che.student_id,
                    CASE
                        -- Check if course is a language course
                        WHEN c.is_language = true THEN 'LANGUAGE'
                        -- Check course code patterns for language programs
                        WHEN c.code LIKE 'IEAP%' OR c.code LIKE 'GESL%' OR c.code LIKE 'EHSS%' THEN 'LANGUAGE'
                        WHEN c.code LIKE 'ELL%' OR c.code LIKE 'EXPRESS%' OR c.code LIKE 'IELTS%' THEN 'LANGUAGE'
                        -- Check cycle names for degree levels
                        WHEN cy.name LIKE '%Bachelor%' OR cy.name LIKE '%BA%' THEN 'BA'
                        WHEN cy.name LIKE '%Master%' OR cy.name LIKE '%MA%' OR cy.name LIKE '%MBA%' THEN 'MA'
                        WHEN cy.name LIKE '%Language%' OR cy.name LIKE '%Foundation%' THEN 'LANGUAGE'
                        -- Default based on course code patterns
                        WHEN c.code ~ '^[0-9]{3}' AND CAST(SUBSTRING(c.code FROM '^[0-9]{3}') AS INTEGER) < 500 THEN 'BA'
                        WHEN c.code ~ '^[0-9]{3}' AND CAST(SUBSTRING(c.code FROM '^[0-9]{3}') AS INTEGER) >= 500 THEN 'MA'
                        ELSE NULL
                    END as detected_type,
                    MIN(t.start_date) as earliest_date
                FROM enrollment_classheaderenrollment che
                JOIN scheduling_classheader ch ON che.class_header_id = ch.id
                JOIN curriculum_course c ON ch.course_id = c.id
                JOIN curriculum_term t ON ch.term_id = t.id
                LEFT JOIN curriculum_cycle cy ON c.cycle_id = cy.id
                GROUP BY che.student_id, detected_type
            )
            UPDATE enrollment_academicjourney aj
            SET program_type = COALESCE(
                (SELECT sp.detected_type
                 FROM student_programs sp
                 WHERE sp.student_id = aj.student_id
                 AND sp.detected_type IS NOT NULL
                 ORDER BY
                    CASE sp.detected_type
                        WHEN 'LANGUAGE' THEN 1  -- Language programs first
                        WHEN 'BA' THEN 2
                        WHEN 'MA' THEN 3
                        ELSE 4
                    END,
                    sp.earliest_date
                 LIMIT 1),
                'BA'  -- Default to BA if no enrollments found
            )
            WHERE aj.program_id IS NULL
        """
        )

        # Log the results
        cursor.execute(
            """
            SELECT program_type, COUNT(*) as count
            FROM enrollment_academicjourney
            GROUP BY program_type
            ORDER BY count DESC
        """
        )

        results = cursor.fetchall()
        print("Program type distribution after fix:")
        for ptype, count in results:
            print(f"  {ptype}: {count}")


def reverse_fix(apps, schema_editor):
    """Reverse the fix."""
    # Not really reversible, but we could set everything back to BA
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE enrollment_academicjourney
            SET program_type = 'BA'
        """
        )


class Migration(migrations.Migration):
    dependencies = [
        ("enrollment", "0016_fix_academic_journey_data"),
    ]

    operations = [
        migrations.RunPython(fix_program_types_properly, reverse_fix),
    ]
