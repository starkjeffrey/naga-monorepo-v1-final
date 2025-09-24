"""Management command to populate requirement fulfillments from historical enrollment data.

This command creates StudentDegreeProgress records based on completed
ClassHeaderEnrollment records with passing grades. It simulates what will happen
when the system is live by matching completed courses to canonical requirements
for students' declared majors.

Usage:
    python manage.py populate_requirement_fulfillments [--dry-run] [--student-id ID]
"""

from django.core.management.base import BaseCommand, CommandError

from apps.academic.models import CanonicalRequirement, StudentDegreeProgress
from apps.enrollment.models import ClassHeaderEnrollment, MajorDeclaration
from apps.people.models import StudentProfile


class Command(BaseCommand):
    help = "Populate requirement fulfillments from historical enrollment data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating records",
        )
        parser.add_argument(
            "--student-id",
            type=str,
            help="Process only specific student ID",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of enrollments to process in each batch",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        student_id = options["student_id"]
        batch_size = options["batch_size"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No records will be created"))

        # Get all enrollments with final grades
        enrollments_query = ClassHeaderEnrollment.objects.filter(final_grade__isnull=False).select_related(
            "student", "student__person", "class_header__course", "class_header__term"
        )

        if student_id:
            try:
                student = StudentProfile.objects.get(student_id=student_id)
                enrollments_query = enrollments_query.filter(student=student)
                self.stdout.write(f"Processing enrollments for student: {student}")
            except StudentProfile.DoesNotExist as e:
                raise CommandError(f"Student with ID {student_id} not found") from e

        total_enrollments = enrollments_query.count()
        self.stdout.write(f"Found {total_enrollments} enrollments with grades to process")

        if total_enrollments == 0:
            self.stdout.write(self.style.WARNING("No enrollments found with final grades"))
            return

        created_count = 0
        skipped_count = 0
        error_count = 0
        processed_count = 0

        # Process in batches
        for offset in range(0, total_enrollments, batch_size):
            batch_enrollments = enrollments_query[offset : offset + batch_size]

            self.stdout.write(
                f"Processing batch {offset // batch_size + 1} "
                f"({offset + 1}-{min(offset + batch_size, total_enrollments)} "
                f"of {total_enrollments})"
            )

            for enrollment in batch_enrollments:
                try:
                    result = self.process_enrollment(enrollment, dry_run)
                    if result == "created":
                        created_count += 1
                    elif result == "skipped":
                        skipped_count += 1

                    processed_count += 1

                    # Progress indicator
                    if processed_count % 50 == 0:
                        self.stdout.write(f"  Processed {processed_count}/{total_enrollments}")

                except Exception as e:
                    error_count += 1
                    self.stderr.write(f"Error processing enrollment {enrollment.id}: {e}")

        # Summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS("SUMMARY:"))
        self.stdout.write(f"Total processed: {processed_count}")
        self.stdout.write(f"Created fulfillments: {created_count}")
        self.stdout.write(f"Skipped: {skipped_count}")
        self.stdout.write(f"Errors: {error_count}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No actual records created"))

    def process_enrollment(self, enrollment, dry_run=False):
        """Process a single enrollment and create fulfillment if applicable.

        Returns:
            'created' if fulfillment was created
            'skipped' if enrollment was skipped
        """
        student = enrollment.student
        course = enrollment.class_header.course
        grade = enrollment.final_grade
        term = enrollment.class_header.term

        # Check if grade is passing
        if not self.is_passing_grade(grade):
            return "skipped"

        # Get student's active major declarations at the time of enrollment
        major_declarations = MajorDeclaration.objects.filter(
            student=student, is_active=True, effective_date__lte=term.end_date or term.start_date
        )

        if not major_declarations.exists():
            return "skipped"

        fulfillment_created = False

        for declaration in major_declarations:
            major = declaration.major

            # Find matching canonical requirements
            # Note: For historical data population, we skip term filtering
            # since canonical requirements may have been defined after historical enrollments
            matching_requirements = CanonicalRequirement.objects.filter(
                major=major, required_course=course, is_active=True
            )

            for requirement in matching_requirements:
                # Check if fulfillment already exists
                existing = StudentDegreeProgress.objects.filter(
                    student=student, canonical_requirement=requirement
                ).first()

                if existing:
                    continue  # Skip if already fulfilled

                if not dry_run:
                    # Create the fulfillment record
                    StudentDegreeProgress.objects.create(
                        student=student,
                        canonical_requirement=requirement,
                        fulfillment_method=StudentDegreeProgress.FulfillmentMethod.COURSE_COMPLETION,
                        fulfillment_date=term.end_date or term.start_date,
                        fulfilling_enrollment=enrollment,
                        credits_earned=course.credits or 1,
                        grade=grade,
                        is_active=True,
                        completion_status="COMPLETED",
                        notes=f"Auto-populated from enrollment in {term.code}",
                    )

                fulfillment_created = True

        return "created" if fulfillment_created else "skipped"

    def is_passing_grade(self, grade):
        """Determine if a grade is passing.

        Args:
            grade: Grade string (e.g., 'A', 'B+', 'C-', 'F')

        Returns:
            bool: True if grade is passing
        """
        if not grade:
            return False

        # Clean up grade (remove + and - modifiers)
        grade_upper = grade.upper().replace("+", "").replace("-", "")

        # Basic passing grades (can be enhanced with institutional policy)
        passing_grades = ["A", "B", "C", "D", "P", "PASS", "CR", "CREDIT"]

        return grade_upper in passing_grades
