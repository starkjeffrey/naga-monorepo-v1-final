"""Django management command to generate ProgramEnrollment records from existing student data.

This creates initial ProgramEnrollment records for all students with a simplified
ACTIVE status approach. Once legacy_academiccoursetakers data is available, the
Dramatiq job will handle complex ACTIVE/INACTIVE determination.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.common.utils import get_current_date
from apps.curriculum.models import Major, Term
from apps.enrollment.models import ProgramEnrollment
from apps.people.models import StudentProfile

# Constants
MAX_ERROR_LOG_ENTRIES = 20
MAX_DISPLAYED_ERRORS = 10


class Command(BaseCommand):
    """Generate initial ProgramEnrollment records from existing student data."""

    help = "Generate ProgramEnrollment records from existing student data"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {
            "total_students": 0,
            "enrollments_created": 0,
            "errors": 0,
            "skipped": 0,
        }
        self.error_log = []

    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without making changes",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of students to process (for testing)",
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Clear existing ProgramEnrollment records before creating new ones",
        )

    def handle(self, *args, **options):
        """Main command handler."""
        dry_run = options["dry_run"]
        limit = options.get("limit")
        clear_existing = options["clear_existing"]

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No database changes will be made"))

        try:
            # Clear existing if requested
            if clear_existing and not dry_run:
                deleted_count = ProgramEnrollment.objects.all().delete()[0]
                self.stdout.write(self.style.SUCCESS(f"🗑️  Cleared {deleted_count} existing ProgramEnrollment records"))

            # Get students to process
            students = StudentProfile.objects.select_related("person").all()
            if limit:
                students = students[:limit]

            self.stats["total_students"] = students.count()
            self.stdout.write(f"📊 Processing {self.stats['total_students']} students")

            # Cache open terms for status determination
            open_term_ids = self._get_open_term_ids()
            self.stdout.write(f"🕒 Found {len(open_term_ids)} currently open terms")

            # Process each student
            for student in students:
                try:
                    if not dry_run:
                        self._create_program_enrollment(student, open_term_ids)
                    else:
                        self._validate_student(student)

                except (ValueError, TypeError, AttributeError) as e:
                    self.stats["errors"] += 1
                    error_msg = f"Error processing student {student.student_id}: {e}"
                    self.error_log.append(error_msg)

                    if len(self.error_log) > MAX_ERROR_LOG_ENTRIES:
                        break

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Migration failed: {e}"))
            raise

        # Report results
        self._report_results(dry_run=dry_run)

    def _get_open_term_ids(self) -> set:
        """Get IDs of currently open terms (max 4)."""
        today = timezone.now().date()
        return set(Term.objects.filter(start_date__lte=today, end_date__gte=today).values_list("id", flat=True))

    def _determine_program_and_type(self, student) -> tuple[Major | None, str]:
        """Determine program and enrollment type for a student."""
        # For now, assign a default program - this will be enhanced when we have
        # more detailed program assignment logic from legacy data

        # Try to find a default English language program
        default_program = Major.objects.filter(name__icontains="English").first()

        if not default_program:
            # Fallback to any available major
            default_program = Major.objects.first()

        if default_program:
            # Determine type based on program name
            if any(keyword in default_program.name.upper() for keyword in ["BA", "BACHELOR", "ACADEMIC"]):
                enrollment_type = ProgramEnrollment.EnrollmentType.ACADEMIC
            elif any(keyword in default_program.name.upper() for keyword in ["JOINT", "DUAL"]):
                enrollment_type = ProgramEnrollment.EnrollmentType.JOINT
            else:
                enrollment_type = ProgramEnrollment.EnrollmentType.LANGUAGE

            return default_program, enrollment_type

        return None, ProgramEnrollment.EnrollmentType.LANGUAGE

    def _determine_status(self, student, open_term_ids: set) -> str:
        """Determine enrollment status for a student."""
        # For now, default everyone to ACTIVE - will be corrected by Dramatiq job
        return ProgramEnrollment.EnrollmentStatus.ACTIVE

    def _create_program_enrollment(self, student, open_term_ids: set):
        """Create ProgramEnrollment record for a student."""
        # Check if student already has a program enrollment
        existing = ProgramEnrollment.objects.filter(student=student).first()
        if existing:
            self.stats["skipped"] += 1
            return

        # Determine program and type
        program, enrollment_type = self._determine_program_and_type(student)
        if not program:
            self.stats["skipped"] += 1
            return

        # Determine status
        status = self._determine_status(student, open_term_ids)

        # Use enrollment date from student profile or default to today
        start_date = student.last_enrollment_date or get_current_date()

        # Find the closest term for start_term
        start_term = Term.objects.filter(start_date__lte=start_date).order_by("-start_date").first()

        with transaction.atomic():
            # Create enrollment with or without start_term depending on availability
            enrollment_data = {
                "student": student,
                "program": program,
                "enrollment_type": enrollment_type,
                "status": status,
                "start_date": start_date,
                "terms_active": 1,  # Default to 1 term
                "is_system_generated": True,  # Mark as system-generated
                "enrolled_by": None,  # No human user for initial generation
                "notes": "Auto-generated from existing student data during initial migration",
            }

            # Only add start_term if we found one
            if start_term:
                enrollment_data["start_term"] = start_term

            ProgramEnrollment.objects.create(**enrollment_data)

            self.stats["enrollments_created"] += 1

    def _validate_student(self, student):
        """Validate a student record in dry-run mode."""
        if not student.student_id:
            msg = "Missing student ID"
            raise ValueError(msg)
        if not student.person:
            msg = "Missing person record"
            raise ValueError(msg)

    def _report_results(self, *, dry_run: bool):
        """Report migration results."""
        mode = "DRY RUN" if dry_run else "MIGRATION"

        self.stdout.write(f"\\n📊 {mode} RESULTS:")
        self.stdout.write(f"   Total students processed: {self.stats['total_students']:,}")
        self.stdout.write(f"   Program enrollments created: {self.stats['enrollments_created']:,}")
        self.stdout.write(f"   Students skipped: {self.stats['skipped']:,}")
        self.stdout.write(f"   Errors encountered: {self.stats['errors']:,}")

        if self.error_log:
            self.stdout.write(f"\\n❌ ERRORS ({len(self.error_log)}):")
            for error in self.error_log[:10]:  # Show first 10 errors
                self.stdout.write(f"   {error}")
            if len(self.error_log) > MAX_DISPLAYED_ERRORS:
                self.stdout.write(f"   ... and {len(self.error_log) - MAX_DISPLAYED_ERRORS} more errors")

        if not dry_run:
            self.stdout.write(self.style.SUCCESS("\\n✅ Program enrollment generation completed!"))
            self.stdout.write("\\n🔄 Next steps:")
            self.stdout.write("   1. Load legacy_academiccoursetakers data")
            self.stdout.write("   2. Run Dramatiq job to update ACTIVE/INACTIVE statuses based on term enrollment")
            self.stdout.write("   3. Implement payment-based status updates")
        else:
            self.stdout.write(self.style.SUCCESS("\\n✅ Dry run completed - ready for migration!"))
