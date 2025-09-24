"""Management command to test thermal printer connection and print a test receipt.

Usage:
    python manage.py test_thermal_printer

This command helps verify that the thermal printer is properly configured
and can receive print jobs from the Django application.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.level_testing.models import PotentialStudent
from apps.level_testing.printing import (
    print_application_receipt,
    test_printer_connection,
)


class Command(BaseCommand):
    """Test thermal printer connectivity and functionality."""

    help = "Test thermal printer connection and print a sample receipt"

    def add_arguments(self, parser):
        parser.add_argument(
            "--test-only",
            action="store_true",
            help="Only test connection without printing full receipt",
        )

        parser.add_argument(
            "--application-id",
            type=int,
            help="Print receipt for specific application ID",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.HTTP_INFO("Testing thermal printer connection..."))

        # Test basic printer connection
        if test_printer_connection():
            self.stdout.write(self.style.SUCCESS("✓ Thermal printer connection successful!"))
        else:
            self.stdout.write(self.style.ERROR("✗ Thermal printer connection failed!"))
            self.stdout.write(
                self.style.WARNING(
                    "Check printer configuration in settings.py:\n"
                    "- THERMAL_PRINTER settings\n"
                    "- Printer IP/connection\n"
                    "- python-escpos library installation"
                )
            )
            return

        # If test-only mode, stop here
        if options["test_only"]:
            return

        # Test full receipt printing
        if options["application_id"]:
            # Print receipt for specific application
            try:
                application = PotentialStudent.objects.get(id=options["application_id"])
                self.stdout.write(f"Printing receipt for application #{application.id}...")

                if print_application_receipt(application):
                    self.stdout.write(
                        self.style.SUCCESS(f"✓ Receipt printed successfully for {application.full_name_eng}")
                    )
                else:
                    self.stdout.write(self.style.ERROR("✗ Receipt printing failed!"))

            except PotentialStudent.DoesNotExist:
                self.stdout.write(self.style.ERROR(f"Application #{options['application_id']} not found"))
        else:
            # Create a test application for printing
            self.stdout.write("Creating test application for receipt printing...")

            test_application = self._create_test_application()

            if print_application_receipt(test_application):
                self.stdout.write(self.style.SUCCESS("✓ Test receipt printed successfully!"))
                # Clean up test application
                test_application.delete()
                self.stdout.write("Test application cleaned up.")
            else:
                self.stdout.write(self.style.ERROR("✗ Test receipt printing failed!"))
                # Clean up test application
                test_application.delete()

    def _create_test_application(self):
        """Create a temporary test application for printing."""
        from apps.level_testing.models import (
            ApplicationStatus,
            ProgramChoices,
            TimeSlotChoices,
        )
        from apps.people.models import Gender

        test_app = PotentialStudent.objects.create(
            # Personal Information
            family_name_eng="Test",
            personal_name_eng="Student",
            family_name_khm="តេស្ត",
            personal_name_khm="សិស្ស",
            preferred_gender=Gender.OTHER,
            date_of_birth="2000-01-01",
            birth_province="PHNOM_PENH",
            phone_number="+855 12 345 678",
            telegram_number="+855 12 345 678",
            personal_email="test@example.com",
            # Program Preferences
            preferred_program=ProgramChoices.GENERAL_ENGLISH,
            preferred_time_slot=TimeSlotChoices.MORNING,
            preferred_start_term="Test Term",
            first_time_at_puc=True,
            how_did_you_hear="Testing thermal printer",
            # Status
            status=ApplicationStatus.CONFIRMED,
            created_at=timezone.now(),
        )

        return test_app
