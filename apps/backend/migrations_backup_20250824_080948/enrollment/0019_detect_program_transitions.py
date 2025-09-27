# Generated manually to properly detect program transitions from language to degree programs

from django.db import migrations


def detect_program_transitions(apps, schema_editor):
    """Detect when students transition from language to BA/MA programs."""

    with schema_editor.connection.cursor() as cursor:
        print("Detecting program transitions for students...")

        # First, let's analyze the actual enrollment patterns
        cursor.execute(
            """
            WITH student_major_declarations AS (
                -- Get approved major declarations for each student
                SELECT DISTINCT
                    md.student_id,
                    md.major_id,
                    m.name as major_name,
                    m.program_type,
                    m.degree_awarded,
                    md.declared_date,
                    md.approved_date,
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
                WHERE md.approved_date IS NOT NULL  -- Only approved declarations
            ),
            student_progression AS (
                -- Get chronological course enrollments for each student
                SELECT
                    che.student_id,
                    t.start_date,
                    t.id as term_id,
                    t.code as term_code,
                    c.code as course_code,
                    c.title as course_title,
                    c.is_language,
                    smd.major_id,
                    smd.major_program_type,
                    smd.approved_date as major_approval_date,
                    -- Detect program type based on course patterns and major declarations
                    CASE
                        -- If student has approved major and course date is after approval, use major type
                        WHEN smd.major_id IS NOT NULL AND smd.approved_date IS NOT NULL AND t.start_date >= DATE(smd.approved_date) THEN smd.major_program_type
                        -- Language courses
                        WHEN c.is_language = true THEN 'LANGUAGE'
                        WHEN c.code LIKE 'IEAP%' OR c.code LIKE 'GESL%' OR c.code LIKE 'EHSS%' THEN 'LANGUAGE'
                        WHEN c.code LIKE 'ELL%' OR c.code LIKE 'EXPRESS%' OR c.code LIKE 'IELTS%' THEN 'LANGUAGE'
                        -- Graduate level courses (500+)
                        WHEN c.code ~ '^[0-9]{3}' AND CAST(SUBSTRING(c.code FROM '^[0-9]{3}') AS INTEGER) >= 500 THEN 'MA'
                        -- Undergraduate level courses (100-499)
                        WHEN c.code ~ '^[0-9]{3}' AND CAST(SUBSTRING(c.code FROM '^[0-9]{3}') AS INTEGER) < 500 THEN 'BA'
                        -- Default to language for unclear cases
                        ELSE 'LANGUAGE'
                    END as detected_program_type,
                    ROW_NUMBER() OVER (PARTITION BY che.student_id ORDER BY t.start_date) as enrollment_order
                FROM enrollment_classheaderenrollment che
                JOIN scheduling_classheader ch ON che.class_header_id = ch.id
                JOIN curriculum_course c ON ch.course_id = c.id
                JOIN curriculum_term t ON ch.term_id = t.id
                LEFT JOIN student_major_declarations smd ON che.student_id = smd.student_id
                WHERE che.status IN ('ENROLLED', 'COMPLETED', 'PASSED', 'FAILED')
            ),
            program_periods AS (
                -- Identify program transition periods
                SELECT
                    student_id,
                    detected_program_type,
                    MIN(start_date) as period_start,
                    MAX(start_date) as period_end,
                    MIN(term_id) as start_term_id,
                    MAX(term_id) as end_term_id,
                    MIN(term_code) as start_term_code,
                    COUNT(DISTINCT term_id) as duration_terms,
                    MAX(major_id) as representative_major_id,
                    -- Detect when program type changes
                    LAG(detected_program_type) OVER (PARTITION BY student_id ORDER BY MIN(start_date)) as prev_program_type
                FROM student_progression
                WHERE detected_program_type IS NOT NULL
                GROUP BY student_id, detected_program_type
            ),
            transition_detection AS (
                -- Mark transitions and create proper periods
                SELECT
                    student_id,
                    detected_program_type,
                    period_start,
                    period_end,
                    start_term_id,
                    start_term_code,
                    duration_terms,
                    representative_major_id,
                    -- Determine transition status
                    CASE
                        WHEN prev_program_type IS NULL THEN 'ACTIVE'  -- First program
                        WHEN prev_program_type != detected_program_type THEN 'CHANGED_PROGRAM'
                        ELSE 'ACTIVE'
                    END as transition_status,
                    ROW_NUMBER() OVER (PARTITION BY student_id ORDER BY period_start) as period_number
                FROM program_periods
            )
            -- Now update existing records or create new ones as needed
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
                created_at,
                updated_at
            )
            SELECT
                td.student_id,
                td.detected_program_type,
                td.representative_major_id,
                td.period_start,
                CASE
                    WHEN td.transition_status = 'CHANGED_PROGRAM' THEN td.period_end
                    ELSE NULL
                END,
                td.start_term_id,
                COALESCE(td.start_term_code, 'UNKNOWN'),
                td.duration_terms,
                td.transition_status,
                NOW(),
                NOW()
            FROM transition_detection td
            WHERE NOT EXISTS (
                -- Don't create duplicates
                SELECT 1
                FROM enrollment_academicjourney aj
                WHERE aj.student_id = td.student_id
                AND aj.program_type = td.detected_program_type
                AND aj.start_date = td.period_start
            )
            AND td.period_number > 1  -- Skip first period as it likely already exists
        """
        )

        new_records = cursor.rowcount
        print(f"Created {new_records} new program transition records")

        # Update existing LANGUAGE records that should be marked as transitions
        cursor.execute(
            """
            WITH transitions AS (
                SELECT
                    aj1.id,
                    aj1.student_id,
                    aj1.program_type as current_type,
                    aj2.program_type as next_type,
                    aj2.start_date as next_start_date
                FROM enrollment_academicjourney aj1
                JOIN enrollment_academicjourney aj2
                    ON aj1.student_id = aj2.student_id
                    AND aj2.start_date > aj1.start_date
                WHERE aj1.transition_status = 'ACTIVE'
                AND aj1.stop_date IS NULL
            )
            UPDATE enrollment_academicjourney aj
            SET
                transition_status = 'CHANGED_PROGRAM',
                stop_date = t.next_start_date
            FROM transitions t
            WHERE aj.id = t.id
            AND t.next_type != t.current_type
        """
        )

        transitions_updated = cursor.rowcount
        print(f"Updated {transitions_updated} records with transition status")

        # Now let's see the results
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

        print("\nProgram type and transition status distribution:")
        print("=" * 60)
        for ptype, status, count in cursor.fetchall():
            print(f"  {ptype:<10} {status:<20} {count:>8}")

        # Check student progression patterns
        cursor.execute(
            """
            WITH progression_summary AS (
                SELECT
                    student_id,
                    STRING_AGG(program_type || '(' || COALESCE(transition_status, 'ACTIVE') || ')', ' → '
                               ORDER BY start_date) as journey,
                    COUNT(*) as program_count
                FROM enrollment_academicjourney
                GROUP BY student_id
            )
            SELECT
                journey,
                COUNT(*) as student_count
            FROM progression_summary
            WHERE program_count > 1
            GROUP BY journey
            ORDER BY student_count DESC
            LIMIT 20
        """
        )

        print("\nTop 20 student progression patterns:")
        print("=" * 80)
        for journey, count in cursor.fetchall():
            print(f"  {journey:<60} {count:>8} students")


def reverse_transitions(apps, schema_editor):
    """Remove the additional transition records."""
    # This is destructive, so we'll just pass
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("enrollment", "0018_populate_journey_dates_and_levels"),
    ]

    operations = [
        migrations.RunPython(detect_program_transitions, reverse_transitions),
    ]
