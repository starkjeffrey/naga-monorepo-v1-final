# Generated manually to populate missing dates and add level tracking

from django.db import migrations, models


def populate_dates_and_levels(apps, schema_editor):
    """Populate missing dates and add level tracking to AcademicJourney records."""

    with schema_editor.connection.cursor() as cursor:
        # First, populate start_date, stop_date, and start_term from enrollment history
        print("Populating dates from enrollment history...")

        cursor.execute(
            """
            WITH journey_dates AS (
                -- Get first and last enrollment dates for each journey
                SELECT
                    aj.id as journey_id,
                    aj.student_id,
                    aj.program_id,
                    aj.program_type,
                    MIN(t.start_date) as first_enrollment_date,
                    MAX(t.end_date) as last_enrollment_date,
                    MIN(t.id) as first_term_id,
                    MAX(t.id) as last_term_id,
                    COUNT(DISTINCT t.id) as term_count
                FROM enrollment_academicjourney aj
                LEFT JOIN enrollment_classheaderenrollment che ON che.student_id = aj.student_id
                LEFT JOIN scheduling_classheader ch ON che.class_header_id = ch.id
                LEFT JOIN curriculum_term t ON ch.term_id = t.id
                WHERE che.status IN ('ENROLLED', 'COMPLETED', 'INCOMPLETE', 'PASSED', 'FAILED')
                GROUP BY aj.id, aj.student_id, aj.program_id, aj.program_type
            )
            UPDATE enrollment_academicjourney aj
            SET
                start_date = COALESCE(jd.first_enrollment_date, CURRENT_DATE),
                stop_date = CASE
                    WHEN aj.transition_status IN ('GRADUATED', 'DROPPED_OUT', 'CHANGED_PROGRAM')
                    THEN jd.last_enrollment_date
                    ELSE NULL
                END,
                start_term_id = jd.first_term_id,
                duration_in_terms = COALESCE(jd.term_count, 0)
            FROM journey_dates jd
            WHERE aj.id = jd.journey_id
            AND aj.start_date IS NULL
        """
        )

        rows_updated = cursor.rowcount
        print(f"Updated {rows_updated} records with dates from enrollment history")

        # For records still without dates, use created_at as fallback
        cursor.execute(
            """
            UPDATE enrollment_academicjourney
            SET start_date = DATE(created_at)
            WHERE start_date IS NULL
        """
        )

        fallback_rows = cursor.rowcount
        print(f"Updated {fallback_rows} records using created_at as fallback")

        # Now detect language levels for LANGUAGE program records
        print("\nDetecting language levels for language program students...")

        cursor.execute(
            """
            WITH language_levels AS (
                SELECT DISTINCT ON (aj.id)
                    aj.id as journey_id,
                    aj.student_id,
                    -- Extract language level from course codes
                    CASE
                        -- EHSS levels (EHSS-01 through EHSS-12)
                        WHEN c.code ~ '^EHSS-[0-9]{2}$' THEN
                            'EHSS_' || CAST(SUBSTRING(c.code FROM 6 FOR 2) AS INTEGER)
                        -- GESL levels (GESL-01 through GESL-12)
                        WHEN c.code ~ '^GESL-[0-9]{2}$' THEN
                            'GESL_' || CAST(SUBSTRING(c.code FROM 6 FOR 2) AS INTEGER)
                        -- IEAP levels
                        WHEN c.code = 'IEAP-PRE' THEN 'IEAP_-2'
                        WHEN c.code = 'IEAP-BEG' THEN 'IEAP_-1'
                        WHEN c.code ~ '^IEAP-[0-9]$' THEN
                            'IEAP_' || SUBSTRING(c.code FROM 6 FOR 1)
                        -- Weekend Express
                        WHEN c.code = 'EXPRESS-BEG' THEN 'W_EXPR_-1'
                        WHEN c.code ~ '^EXPRESS-[0-9]{2}$' THEN
                            'W_EXPR_' || CAST(SUBSTRING(c.code FROM 9 FOR 2) AS INTEGER)
                        -- ELL codes
                        WHEN c.code ~ '^ELL[0-9]{3}$' THEN
                            'GESL_' || CASE
                                WHEN SUBSTRING(c.code FROM 4 FOR 3) BETWEEN '101' AND '199' THEN '1'
                                WHEN SUBSTRING(c.code FROM 4 FOR 3) BETWEEN '201' AND '299' THEN '2'
                                WHEN SUBSTRING(c.code FROM 4 FOR 3) BETWEEN '301' AND '399' THEN '3'
                                WHEN SUBSTRING(c.code FROM 4 FOR 3) BETWEEN '401' AND '499' THEN '4'
                                WHEN SUBSTRING(c.code FROM 4 FOR 3) BETWEEN '501' AND '599' THEN '5'
                                WHEN SUBSTRING(c.code FROM 4 FOR 3) BETWEEN '601' AND '699' THEN '6'
                                ELSE NULL
                            END
                        ELSE NULL
                    END as detected_level,
                    t.start_date as level_date
                FROM enrollment_academicjourney aj
                JOIN enrollment_classheaderenrollment che ON che.student_id = aj.student_id
                JOIN scheduling_classheader ch ON che.class_header_id = ch.id
                JOIN curriculum_course c ON ch.course_id = c.id
                JOIN curriculum_term t ON ch.term_id = t.id
                WHERE aj.program_type = 'LANGUAGE'
                AND che.status IN ('ENROLLED', 'COMPLETED', 'PASSED')
                ORDER BY aj.id, t.start_date DESC  -- Get most recent level
            )
            UPDATE enrollment_academicjourney aj
            SET language_level = ll.detected_level
            FROM language_levels ll
            WHERE aj.id = ll.journey_id
            AND ll.detected_level IS NOT NULL
        """
        )

        language_rows = cursor.rowcount
        print(f"Updated {language_rows} language program records with detected levels")

        # Calculate accumulated credits for BA/MA programs
        print("\nCalculating accumulated credits for BA/MA programs...")

        cursor.execute(
            """
            WITH credit_accumulation AS (
                SELECT
                    aj.id as journey_id,
                    aj.student_id,
                    SUM(
                        CASE
                            WHEN che.status IN ('COMPLETED', 'PASSED') AND c.credits > 0
                            THEN c.credits
                            ELSE 0
                        END
                    ) as total_credits_earned,
                    COUNT(DISTINCT CASE
                        WHEN che.status IN ('COMPLETED', 'PASSED')
                        THEN che.class_header_id
                    END) as courses_completed
                FROM enrollment_academicjourney aj
                JOIN enrollment_classheaderenrollment che ON che.student_id = aj.student_id
                JOIN scheduling_classheader ch ON che.class_header_id = ch.id
                JOIN curriculum_course c ON ch.course_id = c.id
                JOIN curriculum_term t ON ch.term_id = t.id
                WHERE aj.program_type IN ('BA', 'MA')
                AND t.start_date >= aj.start_date
                AND (aj.stop_date IS NULL OR t.end_date <= aj.stop_date)
                GROUP BY aj.id, aj.student_id
            )
            UPDATE enrollment_academicjourney aj
            SET
                accumulated_credits = COALESCE(ca.total_credits_earned, 0),
                courses_completed = COALESCE(ca.courses_completed, 0)
            FROM credit_accumulation ca
            WHERE aj.id = ca.journey_id
        """
        )

        credit_rows = cursor.rowcount
        print(f"Updated {credit_rows} BA/MA records with accumulated credits")

        # Log summary statistics
        cursor.execute(
            """
            SELECT
                program_type,
                COUNT(*) as total,
                COUNT(language_level) as with_level,
                AVG(accumulated_credits) as avg_credits,
                AVG(duration_in_terms) as avg_duration
            FROM enrollment_academicjourney
            GROUP BY program_type
            ORDER BY total DESC
        """
        )

        print("\nSummary after population:")
        print("=" * 80)
        print(f"{'Program Type':<15} {'Total':<10} {'With Level':<12} {'Avg Credits':<12} {'Avg Terms':<10}")
        print("-" * 80)

        for row in cursor.fetchall():
            program_type, total, with_level, avg_credits, avg_duration = row
            avg_credits = avg_credits or 0
            avg_duration = avg_duration or 0
            print(f"{program_type:<15} {total:<10} {with_level:<12} {avg_credits:<12.1f} {avg_duration:<10.1f}")


def add_fields(apps, schema_editor):
    """Add language_level and accumulated_credits fields."""
    # Note: This would normally be in a separate migration, but including here for completeness
    pass


def remove_fields(apps, schema_editor):
    """Remove the added fields."""
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("enrollment", "0017_fix_program_types_properly"),
    ]

    operations = [
        # First add the new fields
        migrations.AddField(
            model_name="academicjourney",
            name="language_level",
            field=models.CharField(
                blank=True,
                max_length=20,
                help_text="Current language level (e.g., EHSS_5, GESL_12)",
                verbose_name="Language Level",
            ),
        ),
        migrations.AddField(
            model_name="academicjourney",
            name="accumulated_credits",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                max_digits=6,
                help_text="Total credits accumulated in this program",
                verbose_name="Accumulated Credits",
            ),
        ),
        migrations.AddField(
            model_name="academicjourney",
            name="courses_completed",
            field=models.PositiveIntegerField(
                default=0, help_text="Number of courses completed in this program", verbose_name="Courses Completed"
            ),
        ),
        # Then populate the data
        migrations.RunPython(populate_dates_and_levels, remove_fields),
    ]
