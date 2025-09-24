"""
Update ClassHeaderEnrollment status to DROPPED based on legacy attendance data.

This script looks up students and classes in the legacy_course_takers table where
attendance='Drop' and updates the corresponding ClassHeaderEnrollment records
to have status='DROPPED'.
"""

from django.db import connection

from apps.common.management.base_migration import BaseMigrationCommand


class Command(BaseMigrationCommand):
    help = "Update enrollment status to DROPPED based on legacy attendance data"

    def get_rejection_categories(self):
        return [
            "student_not_found",
            "enrollment_not_found",
            "multiple_enrollments_found",
            "update_failed",
            "legacy_data_missing",
        ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of records to process",
        )

    def execute_migration(self, *args, **options):
        dry_run = options.get("dry_run", False)
        limit = options.get("limit")

        # Record input stats
        with connection.cursor() as cursor:
            # Count total legacy records with Drop attendance
            cursor.execute(
                """
                SELECT COUNT(*)
                FROM legacy_course_takers
                WHERE TRIM(attendance) = 'Drop'
            """
            )
            total_dropped_records = cursor.fetchone()[0]

        self.record_input_stats(total_records=total_dropped_records, source_table="legacy_course_takers")

        self.stdout.write(self.style.SUCCESS(f"Found {total_dropped_records} legacy records with Drop attendance"))

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        # Process the updates
        updated_count = 0
        processed_count = 0

        with connection.cursor() as cursor:
            # Get all legacy records with Drop attendance
            query = """
                SELECT DISTINCT lct.id, lct.classid
                FROM legacy_course_takers lct
                WHERE TRIM(lct.attendance) = 'Drop'
            """

            if limit:
                query += f" LIMIT {limit}"

            cursor.execute(query)
            dropped_records = cursor.fetchall()

        for student_id, class_id in dropped_records:
            processed_count += 1

            try:
                # Find matching ClassHeaderEnrollment records
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT e.id, e.status, s.student_id, e.notes
                        FROM enrollment_classheaderenrollment e
                        JOIN people_studentprofile s ON e.student_id = s.id
                        WHERE s.student_id = %s
                        AND e.notes LIKE %s
                    """,
                        [int(student_id), f"%{class_id}%"],
                    )

                    matching_enrollments = cursor.fetchall()

                if not matching_enrollments:
                    self.record_rejection(
                        category="enrollment_not_found",
                        record_id=f"{student_id}-{class_id}",
                        reason=f"No enrollment found for student {student_id} with class {class_id}",
                        error_details=f"Student: {student_id}, Class: {class_id}",
                    )
                    continue

                if len(matching_enrollments) > 1:
                    # Multiple matches - this is possible, just update all of them
                    self.stdout.write(
                        self.style.WARNING(
                            f"Found {len(matching_enrollments)} enrollments for student {student_id}, "
                            f"class {class_id} - updating all"
                        )
                    )

                # Update each matching enrollment
                for enrollment_id, current_status, student_num, _notes in matching_enrollments:
                    if current_status == "DROPPED":
                        # Already dropped, skip
                        continue

                    if not dry_run:
                        with connection.cursor() as cursor:
                            cursor.execute(
                                """
                                UPDATE enrollment_classheaderenrollment
                                SET status = 'DROPPED',
                                    updated_at = NOW()
                                WHERE id = %s
                            """,
                                [enrollment_id],
                            )

                    updated_count += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"{'[DRY RUN] Would update' if dry_run else 'Updated'} student {student_num} "
                            f"enrollment {enrollment_id}: {current_status} → DROPPED"
                        )
                    )

                self.record_success("enrollments_updated", 1)

            except Exception as e:
                self.record_rejection(
                    category="update_failed",
                    record_id=f"{student_id}-{class_id}",
                    reason=f"Failed to update enrollment: {e!s}",
                    error_details=f"Student: {student_id}, Class: {class_id}, Error: {e!s}",
                )
                continue

            # Progress indicator
            if processed_count % 100 == 0:
                self.stdout.write(f"Processed {processed_count}/{len(dropped_records)} records...")

        # Final summary
        self.stdout.write(self.style.SUCCESS(f"\nCompleted processing {processed_count} legacy records"))
        self.stdout.write(
            self.style.SUCCESS(
                f"{'Would update' if dry_run else 'Updated'} {updated_count} enrollment records to DROPPED status"
            )
        )

        # Record final stats
        self.record_success("total_processed", processed_count)
        self.record_success("total_updated", updated_count)

        if not dry_run:
            # Verify the changes
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM enrollment_classheaderenrollment
                    WHERE status = 'DROPPED'
                """
                )
                final_dropped_count = cursor.fetchone()[0]

            self.stdout.write(
                self.style.SUCCESS(f"Verification: {final_dropped_count} total enrollments now have DROPPED status")
            )
