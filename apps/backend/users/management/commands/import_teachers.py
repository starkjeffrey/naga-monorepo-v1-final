"""Import teacher data from CSV into User accounts and TeacherProfile records.

This script imports teacher data into:
1. users.User - for official school email authentication accounts
2. people.Person + people.TeacherProfile - for teacher information and profiles

The script handles existing Person records (for teachers who may also be students/staff)
and follows the clean architecture pattern with comprehensive audit reporting.
"""

import csv
from datetime import date
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.common.management.base_migration import BaseMigrationCommand
from apps.people.models import Gender, Person, TeacherProfile

User = get_user_model()


class Command(BaseMigrationCommand):
    """Import teacher data from CSV into User accounts and TeacherProfile records."""

    help = "Import teacher data from CSV into User accounts and TeacherProfile records"

    def get_rejection_categories(self):
        return [
            "missing_email",
            "invalid_email",
            "duplicate_email",
            "missing_name",
            "invalid_name",
            "user_creation_failed",
            "person_creation_failed",
            "teacher_profile_creation_failed",
            "database_error",
            "duplicate_teacher_profile",
            "validation_error",
        ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            default="data/migrate/teachers.csv",
            help="Path to teachers CSV file (default: data/migrate/teachers.csv)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview the import without making changes",
        )

    def execute_migration(self, *args, **options):
        """Import teacher data from CSV file."""
        csv_file_path = Path(options["csv_file"])

        if not csv_file_path.exists():
            self.stdout.write(self.style.ERROR(f"CSV file not found: {csv_file_path}"))
            return

        self.stdout.write(f"Reading teacher data from: {csv_file_path}")

        # Read and validate CSV data first
        teacher_records = []

        try:
            with open(csv_file_path, encoding="utf-8-sig") as csvfile:
                # Handle BOM if present
                reader = csv.DictReader(csvfile)
                for row_num, row in enumerate(reader, start=2):  # Start at 2 to account for header
                    processed_row = self._process_csv_row(row, row_num)
                    if processed_row:
                        teacher_records.append(processed_row)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error reading CSV file: {e}"))
            return

        self.stdout.write(f"Found {len(teacher_records)} valid teacher records to import")

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
            self._preview_import(teacher_records)
            return

        # Record input statistics
        self.record_input_stats(total_teachers=len(teacher_records))

        # Process each teacher record
        for record in teacher_records:
            try:
                self._import_teacher(record)
            except Exception as e:
                self.record_rejection(
                    "database_error",
                    f"row_{record['row_number']}",
                    f"Unexpected error importing teacher: {e}",
                    error_details=str(e),
                    raw_data=record["row_data"],
                )

    def _process_csv_row(self, row, row_num):
        """Process and validate a single CSV row."""
        # Clean the data
        schoolemail = (row.get("schoolemail") or "").strip()
        family_name = (row.get("family_name") or "").strip()
        personal_name = (row.get("personal_name") or "").strip()

        # Basic validation
        if not schoolemail:
            self.record_rejection(
                "missing_email",
                f"row_{row_num}",
                "School email is required",
                raw_data=row,
            )
            return None

        if not family_name or not personal_name:
            self.record_rejection(
                "missing_name",
                f"row_{row_num}",
                "Both family_name and personal_name are required",
                raw_data=row,
            )
            return None

        # Email validation
        if "@" not in schoolemail or not schoolemail.endswith("@pucsr.edu.kh"):
            self.record_rejection(
                "invalid_email",
                f"row_{row_num}",
                f"Invalid school email format: {schoolemail}",
                raw_data=row,
            )
            return None

        # Check for duplicate emails in the data
        existing_user = User.objects.filter(email=schoolemail).first()
        if existing_user:
            self.stdout.write(self.style.WARNING(f"User already exists for email: {schoolemail}"))

        return {
            "row_data": row,
            "row_number": row_num,
            "schoolemail": schoolemail,
            "family_name": family_name,
            "personal_name": personal_name,
            "full_name": f"{personal_name} {family_name}",
        }

    def _preview_import(self, teacher_records):
        """Preview what would be imported without making changes."""
        self.stdout.write("\n=== IMPORT PREVIEW ===")

        for record in teacher_records[:10]:  # Show first 10 records
            self.stdout.write(f"Row {record['row_number']}: {record['full_name']} ({record['schoolemail']})")

        if len(teacher_records) > 10:
            self.stdout.write(f"... and {len(teacher_records) - 10} more records")

        # Check for existing records
        existing_users = 0
        existing_persons = 0
        existing_teachers = 0

        for record in teacher_records:
            if User.objects.filter(email=record["schoolemail"]).exists():
                existing_users += 1

            # Check if Person exists by matching names and email
            person_query = Person.objects.filter(
                family_name__iexact=record["family_name"], personal_name__iexact=record["personal_name"]
            )
            if person_query.exists():
                existing_persons += 1
                person = person_query.first()
                if hasattr(person, "teacher_profile"):
                    existing_teachers += 1

        self.stdout.write("\nExisting records found:")
        self.stdout.write(f"- Users: {existing_users}")
        self.stdout.write(f"- Persons: {existing_persons}")
        self.stdout.write(f"- Teacher Profiles: {existing_teachers}")

    @transaction.atomic
    def _import_teacher(self, record):
        """Import a single teacher record."""
        schoolemail = record["schoolemail"]
        family_name = record["family_name"]
        personal_name = record["personal_name"]
        full_name = record["full_name"]
        row_data = record["row_data"]
        row_number = record["row_number"]

        try:
            # Step 1: Create or get User account
            user, user_created = User.objects.get_or_create(
                email=schoolemail,
                defaults={
                    "name": full_name,
                    "is_active": True,
                    "date_joined": timezone.now(),
                },
            )

            if user_created:
                # Set a temporary password - teachers will need to reset via email
                user.set_password("TempPassword123!")
                user.save()
                self.stdout.write(f"Created User account: {schoolemail}")
            else:
                self.stdout.write(f"Using existing User account: {schoolemail}")

            # Step 2: Create or get Person record
            # First try to find existing Person by names
            person_query = Person.objects.filter(family_name__iexact=family_name, personal_name__iexact=personal_name)

            person = None
            person_created = False

            if person_query.exists():
                person = person_query.first()
                self.stdout.write(f"Found existing Person: {person.full_name} (may also be student/staff)")
            else:
                # Create new Person record
                person = Person.objects.create(
                    family_name=family_name,
                    personal_name=personal_name,
                    full_name=full_name,
                    # Set reasonable defaults
                    date_of_birth=date(1980, 1, 1),  # Default birth date
                    preferred_gender=Gender.PREFER_NOT_TO_SAY,
                )
                person_created = True
                self.stdout.write(f"Created Person record: {person.full_name}")

            # Step 3: Create TeacherProfile (if it doesn't exist)
            _teacher_profile, teacher_created = TeacherProfile.objects.get_or_create(
                person=person,
                defaults={
                    "terminal_degree": TeacherProfile.Qualification.OTHER,
                    "status": TeacherProfile.Status.ACTIVE,
                    "start_date": date.today(),
                },
            )

            if teacher_created:
                self.stdout.write(f"Created TeacherProfile for: {person.full_name}")
            else:
                self.stdout.write(f"TeacherProfile already exists for: {person.full_name}")
                self.record_rejection(
                    "duplicate_teacher_profile",
                    f"row_{row_number}",
                    f"TeacherProfile already exists for {person.full_name}",
                    raw_data=row_data,
                )
                return

            # Success - record the successful import
            if user_created:
                self.record_success("users_created", 1)
            if person_created:
                self.record_success("persons_created", 1)
            if teacher_created:
                self.record_success("teacher_profiles_created", 1)

            self.stdout.write(self.style.SUCCESS(f"✅ Imported teacher: {person.full_name} ({user.email})"))

        except ValidationError as e:
            self.record_rejection(
                "validation_error",
                f"row_{row_number}",
                f"Validation error: {e}",
                error_details=str(e),
                raw_data=row_data,
            )
        except Exception as e:
            self.record_rejection(
                "database_error",
                f"row_{row_number}",
                f"Database error: {e}",
                error_details=str(e),
                raw_data=row_data,
            )
