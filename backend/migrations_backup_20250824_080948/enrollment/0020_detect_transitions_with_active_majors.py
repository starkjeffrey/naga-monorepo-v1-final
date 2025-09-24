# Generated manually to detect program transitions using active major declarations

from django.db import migrations


def detect_program_transitions_active(apps, schema_editor):
    """Detect when students transition from language to BA/MA programs using active declarations."""

    with schema_editor.connection.cursor() as cursor:
        print("Detecting program transitions for students using active major declarations...")

        # Let's first understand what we have
        cursor.execute(
            """
            SELECT
                COUNT(*) as total_students,
                COUNT(DISTINCT md.student_id) as students_with_declarations
            FROM people_studentprofile sp
            LEFT JOIN enrollment_majordeclaration md ON sp.id = md.student_id AND md.is_active = true
        """
        )

        total_students, students_with_declarations = cursor.fetchone()
        print(f"Total students: {total_students}, Students with active declarations: {students_with_declarations}")

        # Now let's see what types of majors students have declared
        cursor.execute(
            """
            SELECT
                m.program_type,
                m.degree_awarded,
                COUNT(*) as count
            FROM enrollment_majordeclaration md
            JOIN curriculum_major m ON md.major_id = m.id
            WHERE md.is_active = true
            GROUP BY m.program_type, m.degree_awarded
            ORDER BY count DESC
        """
        )

        print("\nActive major declaration types:")
        print("=" * 50)
        for program_type, degree_awarded, count in cursor.fetchall():
            print(f"  {program_type:<15} {degree_awarded or 'NULL':<10} {count:>8}")

        # Now let's create AcademicJourney records for students who have declared non-language majors
        cursor.execute(
            """
            WITH student_major_analysis AS (
                SELECT
                    md.student_id,
                    md.major_id,
                    m.name as major_name,
                    m.program_type,
                    m.degree_awarded,
                    md.effective_date,
                    md.declared_date,
                    -- Determine program type from major
                    CASE
                        WHEN m.degree_awarded IN ('MA', 'MBA', 'MEd') THEN 'MA'
                        WHEN m.degree_awarded IN ('BA', 'AA') THEN 'BA'
                        WHEN m.program_type = 'LANGUAGE' THEN 'LANGUAGE'
                        WHEN m.program_type = 'ACADEMIC' THEN 'BA'  -- Default academic to BA
                        ELSE 'BA'
                    END as major_program_type
                FROM enrollment_majordeclaration md
                JOIN curriculum_major m ON md.major_id = m.id
                WHERE md.is_active = true
            ),
            students_needing_degree_journeys AS (
                -- Find students with BA/MA declarations who only have LANGUAGE journey records
                SELECT
                    sma.student_id,
                    sma.major_id,
                    sma.major_program_type,
                    sma.effective_date,
                    sma.declared_date,
                    -- Check if they have any existing journey records for this program type
                    NOT EXISTS (
                        SELECT 1 FROM enrollment_academicjourney aj
                        WHERE aj.student_id = sma.student_id
                        AND aj.program_type = sma.major_program_type
                    ) as needs_new_journey
                FROM student_major_analysis sma
                WHERE sma.major_program_type IN ('BA', 'MA')
            )
            INSERT INTO enrollment_academicjourney (
                student_id,
                program_type,
                program_id,
                start_date,
                stop_date,
                start_term_id,
                term_code,
                duration_in_terms,
                transition_status,
                accumulated_credits,
                courses_completed,
                language_level,
                current_level,
                confidence_score,
                data_issues,
                data_source,
                notes,
                requires_review,
                is_deleted,
                created_at,
                updated_at
            )
            SELECT
                sn.student_id,
                sn.major_program_type,
                sn.major_id,
                COALESCE(sn.effective_date, DATE(sn.declared_date), CURRENT_DATE),
                NULL,  -- stop_date
                NULL,  -- start_term_id (will be populated later)
                'DECLARED',  -- term_code indicating this was created from declaration
                0,  -- duration_in_terms (will be calculated later)
                'CHANGED_PROGRAM',  -- transition_status
                0,  -- accumulated_credits
                0,  -- courses_completed
                '',  -- language_level (empty string, not null)
                '',  -- current_level (empty string, not null)
                0.0,  -- confidence_score
                '{}',  -- data_issues (empty JSON object)
                'MAJOR_DECLARATION',  -- data_source
                'Created from active major declaration',  -- notes
                FALSE,  -- requires_review
                FALSE,  -- is_deleted
                NOW(),
                NOW()
            FROM students_needing_degree_journeys sn
            WHERE sn.needs_new_journey = true
        """
        )

        new_records = cursor.rowcount
        print(f"\nCreated {new_records} new academic journey records for degree program declarations")

        # Now update the stop_date for language journeys when students transition to degree programs
        cursor.execute(
            """
            WITH degree_transitions AS (
                SELECT
                    aj_degree.student_id,
                    aj_degree.start_date as degree_start_date,
                    aj_lang.id as language_journey_id
                FROM enrollment_academicjourney aj_degree
                JOIN enrollment_academicjourney aj_lang
                    ON aj_degree.student_id = aj_lang.student_id
                WHERE aj_degree.program_type IN ('BA', 'MA')
                AND aj_lang.program_type = 'LANGUAGE'
                AND aj_lang.stop_date IS NULL  -- Only update open language journeys
                AND aj_degree.start_date > aj_lang.start_date  -- Degree started after language
            )
            UPDATE enrollment_academicjourney aj
            SET
                stop_date = dt.degree_start_date,
                transition_status = 'CHANGED_PROGRAM'
            FROM degree_transitions dt
            WHERE aj.id = dt.language_journey_id
        """
        )

        updated_language_records = cursor.rowcount
        print(f"Updated {updated_language_records} language journey records with stop dates")

        # Now let's see the final results
        cursor.execute(
            """
            SELECT
                program_type,
                transition_status,
                COUNT(*) as count
            FROM enrollment_academicjourney
            GROUP BY program_type, transition_status
            ORDER BY program_type, transition_status
        """
        )

        print("\nFinal program type and transition status distribution:")
        print("=" * 80)
        for ptype, status, count in cursor.fetchall():
            print(f"  {ptype:<10} {status:<20} {count:>8}")

        # Show some example student progressions
        cursor.execute(
            """
            WITH student_progressions AS (
                SELECT
                    student_id,
                    STRING_AGG(
                        program_type || '(' || transition_status || ')',
                        ' → '
                        ORDER BY start_date, created_at
                    ) as journey,
                    COUNT(*) as journey_count
                FROM enrollment_academicjourney
                GROUP BY student_id
                HAVING COUNT(*) > 1
            )
            SELECT
                journey,
                COUNT(*) as student_count
            FROM student_progressions
            GROUP BY journey
            ORDER BY student_count DESC
            LIMIT 10
        """
        )

        print("\nTop 10 student progression patterns:")
        print("=" * 80)
        for journey, count in cursor.fetchall():
            print(f"  {journey:<60} {count:>8} students")


def reverse_transitions_active(apps, schema_editor):
    """Remove the additional transition records."""
    with schema_editor.connection.cursor() as cursor:
        # Remove records created from declarations
        cursor.execute(
            """
            DELETE FROM enrollment_academicjourney
            WHERE term_code = 'DECLARED'
        """
        )
        print(f"Removed {cursor.rowcount} declaration-based journey records")


class Migration(migrations.Migration):
    dependencies = [
        ("enrollment", "0019_detect_program_transitions"),
    ]

    operations = [
        migrations.RunPython(detect_program_transitions_active, reverse_transitions_active),
    ]
