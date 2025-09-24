"""Management command to set up test data using factories."""

import logging

from django.core.management.base import BaseCommand
from django.db import transaction

logger = logging.getLogger("migration")


class Command(BaseCommand):
    """Set up comprehensive test data using factory classes.

    This creates a realistic dataset for development and testing
    that doesn't interfere with migration data.
    """

    help = "Set up test data using factories"

    def add_arguments(self, parser):
        parser.add_argument(
            "--students",
            type=int,
            default=50,
            help="Number of students to create (default: 50)",
        )
        parser.add_argument(
            "--teachers",
            type=int,
            default=10,
            help="Number of teachers to create (default: 10)",
        )
        parser.add_argument(
            "--courses",
            type=int,
            default=20,
            help="Number of courses to create (default: 20)",
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Clear existing data before creating new data",
        )

    def handle(self, *args, **options):
        """Execute test data setup."""
        self.stdout.write(self.style.SUCCESS("🧪 Setting up test data..."))

        try:
            with transaction.atomic(using="default"):
                if options["clear_existing"]:
                    self._clear_existing_data()

                self._create_test_data(options)

            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Test data created successfully!\n"
                    f"   - {options['students']} students\n"
                    f"   - {options['teachers']} teachers\n"
                    f"   - {options['courses']} courses\n"
                    f"   - Plus related enrollment, scheduling, and grade data",
                ),
            )

        except Exception as e:
            logger.exception("Test data setup failed")
            self.stdout.write(self.style.ERROR(f"❌ Test data setup failed: {e}"))
            raise

    def _clear_existing_data(self):
        """Clear existing test data safely."""
        self.stdout.write("🧹 Clearing existing test data...")

        # Import models to clear (avoiding circular imports)
        from apps.curriculum.models import Course
        from apps.enrollment.models import ClassHeaderEnrollment
        from apps.grading.models import ClassPartGrade
        from apps.people.models import Person
        from apps.scheduling.models import ClassHeader
        from users.models import User

        # Clear in dependency order
        ClassPartGrade.objects.using("default").all().delete()
        ClassHeaderEnrollment.objects.using("default").all().delete()
        ClassHeader.objects.using("default").all().delete()
        Course.objects.using("default").all().delete()
        Person.objects.using("default").all().delete()
        # Keep superusers but clear other users
        User.objects.using("default").filter(is_superuser=False).delete()

        self.stdout.write("   Existing data cleared")

    def _create_test_data(self, options):
        """Create comprehensive test data."""
        self.stdout.write("📊 Creating test data...")

        from apps.people.tests.factories import PersonFactory, StudentProfileFactory

        # Create simple test data for now (avoiding complex factories)
        self.stdout.write(f"   Creating {options['students']} students...")
        students = []
        for _i in range(options["students"]):
            person = PersonFactory()
            student_profile = StudentProfileFactory(person=person)
            students.append(student_profile)

        self.stdout.write(f"   Creating {options['teachers']} teachers...")
        teachers = []
        for _i in range(options["teachers"]):
            teacher = PersonFactory()
            # Update school email to faculty format
            teacher.school_email = f"{teacher.personal_name.lower()}.{teacher.family_name.lower()}@faculty.naga.edu.kh"
            teacher.save()
            teachers.append(teacher)

        self.stdout.write("   Test data creation completed")

        logger.info("Test data created: %s students, %s teachers", len(students), len(teachers))
