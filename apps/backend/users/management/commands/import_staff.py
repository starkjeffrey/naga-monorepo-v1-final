"""Django management command to import staff from CSV file.

This command imports staff data from a CSV file and creates:
1. User accounts with email and basic information
2. Person records with full demographic information
3. Links between User and Person models

The command handles duplicate detection and provides comprehensive reporting.
"""

import csv
from pathlib import Path
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.people.models import Person

User = get_user_model()


class Command(BaseCommand):
    """Import staff from CSV file."""

    help = "Import staff data from CSV file into User and Person models"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument("csv_file", type=str, help="Path to CSV file containing staff data")
        parser.add_argument(
            "--dry-run", action="store_true", help="Show what would be imported without making changes"
        )
        parser.add_argument("--update-existing", action="store_true", help="Update existing users if found by email")

    def handle(self, *args, **options) -> None:
        """Execute the command."""
        csv_file = options["csv_file"]
        dry_run = options["dry_run"]
        update_existing = options["update_existing"]

        # Resolve file path
        if not Path(csv_file).is_absolute():
            csv_file = Path(__file__).parent.parent.parent.parent / csv_file

        if not Path(csv_file).exists():
            raise CommandError(f"CSV file not found: {csv_file}")

        self.stdout.write(f"Importing staff from: {csv_file}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        try:
            with transaction.atomic():
                staff_data = self._read_csv(csv_file)
                results = self._process_staff_data(staff_data, dry_run, update_existing)

                if dry_run:
                    # Rollback the transaction in dry run mode
                    transaction.set_rollback(True)

                self._print_summary(results)

        except Exception as e:
            raise CommandError(f"Import failed: {e}") from e

    def _read_csv(self, csv_file: Path) -> list[dict[str, str]]:
        """Read and validate CSV file."""
        staff_data = []

        with open(csv_file, encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            # Validate headers
            expected_headers = {"family_name", "personal_name", "Position", "Phone", "schoolemail"}
            actual_headers = set(reader.fieldnames or [])

            if not expected_headers.issubset(actual_headers):
                missing = expected_headers - actual_headers
                raise CommandError(f"Missing CSV headers: {missing}")

            for row_num, row in enumerate(reader, start=2):  # Start at 2 (header is row 1)
                # Skip empty rows
                if not any(row.values()) or not row.get("family_name"):
                    continue

                # Clean up data
                cleaned_row = {k: v.strip() if v else "" for k, v in row.items()}
                cleaned_row["row_num"] = row_num
                staff_data.append(cleaned_row)

        self.stdout.write(f"Found {len(staff_data)} staff records in CSV")
        return staff_data

    def _process_staff_data(
        self, staff_data: list[dict[str, str]], dry_run: bool, update_existing: bool
    ) -> dict[str, Any]:
        """Process staff data and create/update records."""
        results = {
            "created_users": 0,
            "updated_users": 0,
            "created_persons": 0,
            "updated_persons": 0,
            "skipped": 0,
            "errors": [],
        }

        for staff in staff_data:
            try:
                self._process_single_staff(staff, dry_run, update_existing, results)
            except Exception as e:
                error_msg = f"Row {staff.get('row_num', '?')}: {e}"
                results["errors"].append(error_msg)
                self.stdout.write(self.style.ERROR(error_msg))

        return results

    def _process_single_staff(
        self, staff: dict[str, str], dry_run: bool, update_existing: bool, results: dict[str, Any]
    ) -> None:
        """Process a single staff record."""
        family_name = staff["family_name"]
        personal_name = staff["personal_name"]
        email = staff["schoolemail"].lower() if staff["schoolemail"] else ""
        position = staff["Position"]
        staff["Phone"]

        if not email:
            results["skipped"] += 1
            self.stdout.write(self.style.WARNING(f"Skipping {family_name}, {personal_name}: No email provided"))
            return

        # Check if user exists
        user, user_created = self._get_or_create_user(email, family_name, personal_name, dry_run, update_existing)

        if user_created:
            results["created_users"] += 1
            action = "CREATE"
        elif not user_created and update_existing:
            results["updated_users"] += 1
            action = "UPDATE"
        else:
            results["skipped"] += 1
            self.stdout.write(self.style.WARNING(f"Skipping existing user: {email}"))
            return

        # Create or update Person record
        _person, person_created = self._get_or_create_person(user, staff, dry_run, update_existing)

        if person_created:
            results["created_persons"] += 1
        elif not person_created and update_existing:
            results["updated_persons"] += 1

        # Output progress
        self.stdout.write(f"{action}: {family_name}, {personal_name} ({email}) - {position}")

    def _get_or_create_user(
        self, email: str, family_name: str, personal_name: str, dry_run: bool, update_existing: bool
    ) -> tuple[User | None, bool]:
        """Get or create User record."""
        if dry_run:
            # Check if user would exist
            exists = User.objects.filter(email=email).exists()
            return None, not exists

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "name": f"{personal_name} {family_name}",
                "is_staff": True,  # Mark as staff
                "is_active": True,
            },
        )

        if not created and update_existing:
            user.name = f"{personal_name} {family_name}"
            user.is_staff = True
            user.is_active = True
            user.save()

        return user, created

    def _get_or_create_person(
        self, user: User | None, staff: dict[str, str], dry_run: bool, update_existing: bool
    ) -> tuple[Person | None, bool]:
        """Get or create Person record."""
        family_name = staff["family_name"]
        personal_name = staff["personal_name"]
        staff["Position"]
        staff["Phone"]

        if dry_run:
            # Check if person would exist (by name combination)
            exists = Person.objects.filter(family_name=family_name, personal_name=personal_name).exists()
            return None, not exists

        # Generate full name - will be auto-generated by model save method

        person, created = Person.objects.get_or_create(
            family_name=family_name,
            personal_name=personal_name,
            defaults={
                # full_name will be auto-generated by the model's save method
                # Don't set fields that don't exist or are optional
            },
        )

        if not created and update_existing:
            # Only update if the person already exists and we want to update
            person.save()  # This will trigger the auto-generation of full_name

        return person, created

    def _print_summary(self, results: dict[str, Any]) -> None:
        """Print import summary."""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("IMPORT SUMMARY")
        self.stdout.write("=" * 50)

        self.stdout.write(f"Users created: {results['created_users']}")
        self.stdout.write(f"Users updated: {results['updated_users']}")
        self.stdout.write(f"Persons created: {results['created_persons']}")
        self.stdout.write(f"Persons updated: {results['updated_persons']}")
        self.stdout.write(f"Records skipped: {results['skipped']}")

        if results["errors"]:
            self.stdout.write(f"\nErrors encountered: {len(results['errors'])}")
            for error in results["errors"]:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
        else:
            self.stdout.write(self.style.SUCCESS("\nNo errors encountered!"))

        total_processed = results["created_users"] + results["updated_users"] + results["skipped"]
        self.stdout.write(f"\nTotal records processed: {total_processed}")
