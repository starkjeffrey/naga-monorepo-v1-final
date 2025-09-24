"""Django management command to create StaffProfile records for imported staff.

This command creates StaffProfile records for all imported staff users, linking them
to their Person records and setting appropriate positions based on the CSV data.
"""

import csv
from pathlib import Path
from typing import Any

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.people.models import Person, StaffProfile

User = get_user_model()


class Command(BaseCommand):
    """Create StaffProfile records for imported staff."""

    help = "Create StaffProfile records for all imported staff users"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--csv-file",
            type=str,
            default="data/migrate/staff.csv",
            help="Path to CSV file containing staff data (for position info)",
        )
        parser.add_argument("--dry-run", action="store_true", help="Show what would be created without making changes")

    def handle(self, *args, **options) -> None:
        """Execute the command."""
        csv_file = options["csv_file"]
        dry_run = options["dry_run"]

        # Resolve file path
        if not Path(csv_file).is_absolute():
            csv_file = Path(__file__).parent.parent.parent.parent / csv_file

        if not Path(csv_file).exists():
            raise CommandError(f"CSV file not found: {csv_file}")

        self.stdout.write(f"Creating StaffProfile records from: {csv_file}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        try:
            with transaction.atomic():
                # First, read the CSV to get position information
                position_map = self._read_position_data(csv_file)

                # Create StaffProfile records for all staff users
                results = self._create_staff_profiles(position_map, dry_run)

                if dry_run:
                    # Rollback the transaction in dry run mode
                    transaction.set_rollback(True)

                self._print_summary(results)

        except Exception as e:
            raise CommandError(f"Staff profile creation failed: {e}") from e

    def _read_position_data(self, csv_file: Path) -> dict[str, str]:
        """Read position data from CSV file."""
        position_map = {}

        with open(csv_file, encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)

            for row in reader:
                # Skip empty rows
                if not any(row.values()) or not row.get("family_name"):
                    continue

                email = row["schoolemail"].strip().lower() if row["schoolemail"] else ""
                position = row["Position"].strip() if row["Position"] else "Staff"

                if email:
                    position_map[email] = position

        self.stdout.write(f"Found position data for {len(position_map)} staff members")
        return position_map

    def _create_staff_profiles(self, position_map: dict[str, str], dry_run: bool) -> dict[str, Any]:
        """Create StaffProfile records for staff users."""
        results = {"created_profiles": 0, "existing_profiles": 0, "missing_persons": 0, "errors": []}

        # Get all staff users (is_staff=True)
        staff_users = User.objects.filter(is_staff=True).select_related()

        self.stdout.write(f"Found {staff_users.count()} staff users")

        for user in staff_users:
            try:
                self._process_single_user(user, position_map, dry_run, results)
            except Exception as e:
                error_msg = f"User {user.email}: {e}"
                results["errors"].append(error_msg)
                self.stdout.write(self.style.ERROR(error_msg))

        return results

    def _process_single_user(
        self, user: User, position_map: dict[str, str], dry_run: bool, results: dict[str, Any]
    ) -> None:
        """Process a single staff user."""
        email = user.email.lower()
        position = position_map.get(email, "Staff")  # Default to 'Staff' if not found

        # Find corresponding Person record by name matching
        person = self._find_person_for_user(user)

        if not person:
            results["missing_persons"] += 1
            self.stdout.write(self.style.WARNING(f"No Person record found for user: {user.email} ({user.name})"))
            return

        if dry_run:
            # Check if StaffProfile exists
            profile_exists = StaffProfile.objects.filter(person=person).exists()
            if not profile_exists:
                results["created_profiles"] += 1
                self.stdout.write(f"WOULD CREATE: StaffProfile for {person.full_name} - {position}")
            else:
                results["existing_profiles"] += 1
                self.stdout.write(f"EXISTS: StaffProfile for {person.full_name}")
        else:
            # Create actual StaffProfile
            staff_profile, created = StaffProfile.objects.get_or_create(
                person=person,
                defaults={
                    "position": position,
                    "status": StaffProfile.Status.ACTIVE,
                },
            )

            if created:
                results["created_profiles"] += 1
                self.stdout.write(f"CREATED: StaffProfile for {person.full_name} - {position}")
            else:
                results["existing_profiles"] += 1
                self.stdout.write(f"EXISTS: StaffProfile for {person.full_name} - {staff_profile.position}")

    def _find_person_for_user(self, user: User) -> Person:
        """Find Person record for a User by name matching."""
        if not user.name:
            return None

        # Split user name (format: "Personal Family")
        name_parts = user.name.strip().split()
        if len(name_parts) < 2:
            return None

        personal_name = name_parts[0].upper()
        family_name = name_parts[1].upper()

        # Try to find Person by family_name and personal_name
        try:
            person = Person.objects.get(family_name=family_name, personal_name=personal_name)
            return person
        except Person.DoesNotExist:
            # Try alternative matching strategies
            try:
                # Maybe the names are in full_name field
                full_name = f"{personal_name} {family_name}"
                person = Person.objects.get(full_name=full_name)
                return person
            except Person.DoesNotExist:
                return None
        except Person.MultipleObjectsReturned:
            # If multiple matches, get the first one
            person = Person.objects.filter(family_name=family_name, personal_name=personal_name).first()
            return person

    def _print_summary(self, results: dict[str, Any]) -> None:
        """Print creation summary."""
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("STAFF PROFILE CREATION SUMMARY")
        self.stdout.write("=" * 50)

        self.stdout.write(f"StaffProfiles created: {results['created_profiles']}")
        self.stdout.write(f"StaffProfiles already existed: {results['existing_profiles']}")
        self.stdout.write(f"Users without Person records: {results['missing_persons']}")

        if results["errors"]:
            self.stdout.write(f"\nErrors encountered: {len(results['errors'])}")
            for error in results["errors"]:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
        else:
            self.stdout.write(self.style.SUCCESS("\nNo errors encountered!"))

        total_processed = results["created_profiles"] + results["existing_profiles"] + results["missing_persons"]
        self.stdout.write(f"\nTotal staff users processed: {total_processed}")
