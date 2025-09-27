"""Fix enrollment statuses for records incorrectly marked as ACTIVE in ended terms.

This addresses the systemic issue where the import script incorrectly marked
enrollments as ACTIVE when they should be COMPLETED, FAILED, WITHDRAWN, or INCOMPLETE
based on their final grades and term end dates.
"""

from django.utils import timezone

from apps.common.management.base_migration import BaseMigrationCommand
from apps.enrollment.models import ClassHeaderEnrollment


class Command(BaseMigrationCommand):
    """Fix enrollment statuses based on term end dates and final grades."""

    help = "Fix ACTIVE enrollments in ended terms to correct status based on grades"

    def get_rejection_categories(self):
        return ["update_failed", "data_validation_error"]

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without making updates",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Number of records to process in each batch",
        )

    def execute_migration(self, *args, **options):
        """Main command handler."""
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No changes will be made"))

        current_date = timezone.now().date()

        # Find all ACTIVE enrollments in ended terms
        problematic_enrollments = ClassHeaderEnrollment.objects.filter(
            status=ClassHeaderEnrollment.EnrollmentStatus.ACTIVE,
            class_header__term__end_date__lt=current_date,
        ).select_related("class_header__term", "class_header__course", "student")

        total_count = problematic_enrollments.count()

        self.record_input_stats(
            total_problematic_enrollments=total_count,
            current_date=str(current_date),
            batch_size=batch_size,
        )

        self.stdout.write(f"🔍 Found {total_count:,} ACTIVE enrollments in ended terms")

        if total_count == 0:
            self.stdout.write(self.style.SUCCESS("✅ No problematic enrollments found"))
            return

        # Process in batches
        processed = 0
        updated_counts = {
            "COMPLETED": 0,
            "FAILED": 0,
            "WITHDRAWN": 0,
            "INCOMPLETE": 0,
        }

        self.stdout.write(f"📊 Processing {total_count:,} enrollments in batches of {batch_size:,}...")

        for enrollment in problematic_enrollments.iterator(chunk_size=batch_size):
            try:
                new_status = self._determine_correct_status(enrollment)

                if not dry_run:
                    enrollment.status = new_status
                    enrollment.save(update_fields=["status"])

                updated_counts[new_status] += 1
                processed += 1

                # Progress reporting
                if processed % batch_size == 0:
                    self.stdout.write(f"📋 Processed {processed:,}/{total_count:,} records...")

            except Exception as e:
                self.record_rejection(
                    category="update_failed",
                    record_id=f"student-{enrollment.student.student_id}-{enrollment.class_header.id}",
                    reason=f"Failed to update enrollment status: {e}",
                    error_details=str(e),
                )

        # Record success metrics
        for status, count in updated_counts.items():
            if count > 0:
                self.record_success(f"updated_to_{status.lower()}", count)

        # Report results
        self._report_results(updated_counts, total_count, dry_run)

    def _determine_correct_status(self, enrollment) -> str:
        """Determine the correct enrollment status based on grade and term completion."""
        grade = (enrollment.final_grade or "").upper().strip()

        # Handle specific grade cases
        if grade == "F":
            return ClassHeaderEnrollment.EnrollmentStatus.FAILED
        elif grade == "W":
            return ClassHeaderEnrollment.EnrollmentStatus.WITHDRAWN
        elif grade in ["I", "IP", ""]:
            # Incomplete/In Progress grades or no grade in ended term = INCOMPLETE
            return ClassHeaderEnrollment.EnrollmentStatus.INCOMPLETE
        elif grade and grade not in ["NULL"]:
            # Extract base grade letter (remove +/- modifiers)
            base_grade = grade.replace("+", "").replace("-", "").strip()

            # Grades A, B, C, D are passing (completed)
            if base_grade in ["A", "B", "C", "D"]:
                return ClassHeaderEnrollment.EnrollmentStatus.COMPLETED

        # Default: no grade or unrecognized grade in ended term = INCOMPLETE
        return ClassHeaderEnrollment.EnrollmentStatus.INCOMPLETE

    def _report_results(self, updated_counts, total_count, dry_run):
        """Report the results of the status fixes."""
        mode = "DRY RUN" if dry_run else "UPDATE"

        self.stdout.write(f"\n📊 {mode} RESULTS:")
        self.stdout.write(f"   Total processed: {total_count:,}")

        for status, count in updated_counts.items():
            if count > 0:
                self.stdout.write(f"   Updated to {status}: {count:,}")

        if not dry_run:
            self.stdout.write(self.style.SUCCESS("\n✅ Enrollment statuses fixed successfully!"))
        else:
            self.stdout.write(self.style.WARNING("\n⚠️  This was a dry run - no changes were made"))
            self.stdout.write("   Run without --dry-run to apply these changes")
