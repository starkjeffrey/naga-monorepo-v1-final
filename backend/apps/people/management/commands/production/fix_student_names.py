"""Management command to fix student names that were imported without proper parsing.

This command will:
1. Find all Person records with $$ or other indicators in their names
2. Re-parse the names using the proper name parser
3. Update the records with clean names
4. Log any status indicators found (sponsored, frozen, admin fees)
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import models, transaction

from apps.people.models import Person
from apps.people.utils.name_parser import parse_student_name

User = get_user_model()


class Command(BaseCommand):
    """Fix student names that were imported without proper parsing."""

    help = "Fix student names by re-parsing with proper name parser"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {
            "total_checked": 0,
            "names_fixed": 0,
            "sponsored_found": 0,
            "frozen_found": 0,
            "admin_fee_found": 0,
            "parsing_warnings": 0,
            "errors": 0,
        }

    def add_arguments(self, parser):
        """Add command-specific arguments."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be fixed without making changes",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of records to process (for testing)",
        )

    def handle(self, *args, **options):
        """Execute the name fixing process."""
        dry_run = options["dry_run"]
        limit = options.get("limit")

        self.stdout.write("🔧 Starting student name fixing process...")

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN - No changes will be made"))

        # Find all Person records that likely need name parsing
        # Look for records with $$ (dollar-dollar-space) or other indicators in the name fields
        problematic_persons = Person.objects.filter(
            models.Q(family_name__contains="$$ ")
            | models.Q(personal_name__contains="$$ ")
            | models.Q(full_name__contains="$$ ")
            | models.Q(family_name__contains="$$")  # Also catch any remaining $$
            | models.Q(personal_name__contains="$$")
            | models.Q(full_name__contains="$$")
            | models.Q(family_name__contains="<")
            | models.Q(personal_name__contains="<")
            | models.Q(full_name__contains="<")
            | models.Q(family_name__contains="{")
            | models.Q(personal_name__contains="{")
            | models.Q(full_name__contains="{"),
        )

        if limit:
            problematic_persons = problematic_persons[:limit]

        total_found = problematic_persons.count()
        self.stdout.write(f"📋 Found {total_found} persons with problematic names")

        if total_found == 0:
            self.stdout.write(self.style.SUCCESS("✅ No problematic names found!"))
            return

        # Get system user for logging
        system_user = User.objects.filter(is_staff=True).first()

        # Process each problematic person
        with transaction.atomic():
            for person in problematic_persons:
                self._fix_person_name(person, system_user, dry_run)

        # Print final statistics
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Name fixing complete!\n"
                    f"   Persons checked: {self.stats['total_checked']}\n"
                    f"   Names fixed: {self.stats['names_fixed']}\n"
                    f"   Sponsored students found: {self.stats['sponsored_found']}\n"
                    f"   Frozen students found: {self.stats['frozen_found']}\n"
                    f"   Admin fee students found: {self.stats['admin_fee_found']}\n"
                    f"   Parsing warnings: {self.stats['parsing_warnings']}\n"
                    f"   Errors: {self.stats['errors']}",
                ),
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"🔍 Dry run complete! Would fix {self.stats['names_fixed']} names"))

    def _fix_person_name(self, person, system_user, dry_run):
        """Fix a single person's name using the name parser."""
        self.stats["total_checked"] += 1

        try:
            # Determine the raw name to parse
            # Use full_name if available, otherwise construct from family + personal
            raw_name = person.full_name
            if not raw_name:
                raw_name = f"{person.family_name} {person.personal_name}".strip()

            if not raw_name:
                return  # Skip if no name data

            # Parse the name
            parsed_result = parse_student_name(raw_name)

            # Check if this name needs fixing
            if not parsed_result.clean_name:
                self.stdout.write(f"⚠️  Warning: No clean name found for {raw_name}")
                self.stats["parsing_warnings"] += 1
                return

            # Check if the name is already clean (no fixing needed)
            current_full_name = f"{person.family_name} {person.personal_name}".strip()
            if current_full_name == parsed_result.clean_name and not parsed_result.has_special_status:
                return  # No changes needed

            # Show what will be changed
            self.stdout.write(f"🔧 Fixing: '{raw_name}' → '{parsed_result.clean_name}'")

            if parsed_result.has_special_status:
                self.stdout.write(f"   Status: {parsed_result.status_summary}")

            # Track statistics
            if parsed_result.parsing_warnings:
                self.stats["parsing_warnings"] += 1
            if parsed_result.is_sponsored:
                self.stats["sponsored_found"] += 1
            if parsed_result.is_frozen:
                self.stats["frozen_found"] += 1
            if parsed_result.has_admin_fees:
                self.stats["admin_fee_found"] += 1

            if dry_run:
                self.stats["names_fixed"] += 1
                return

            # Parse the clean name into components
            clean_name = parsed_result.clean_name.strip()
            name_parts = clean_name.split()

            if len(name_parts) >= 2:
                family_name = name_parts[0]
                personal_name = " ".join(name_parts[1:])
            else:
                family_name = ""
                personal_name = clean_name

            # Update the person record
            person.family_name = family_name
            person.personal_name = personal_name
            person.full_name = clean_name
            person.save(update_fields=["family_name", "personal_name", "full_name"])

            # Handle special status indicators
            if parsed_result.has_special_status:
                self._handle_special_status(person, parsed_result, system_user)

            self.stats["names_fixed"] += 1

        except Exception as e:
            self.stats["errors"] += 1
            self.stdout.write(self.style.ERROR(f"❌ Error fixing name for {person.id}: {e}"))

    def _handle_special_status(self, person, parsed_result, system_user):
        """Handle special status indicators found in the name."""
        try:
            # Check if this person has a student profile
            if hasattr(person, "student_profile"):
                student = person.student_profile

                # Handle frozen status
                if parsed_result.is_frozen:
                    self.stdout.write(f"   📝 Note: Student {student.student_id} is marked as FROZEN")
                    # Could add logic here to mark student as frozen in the system

                # Handle sponsored status
                if parsed_result.is_sponsored:
                    sponsor_name = parsed_result.sponsor_name or "Unknown"
                    self.stdout.write(f"   📝 Note: Student {student.student_id} is SPONSORED by {sponsor_name}")
                    # Could add logic here to link to sponsor record

                # Handle admin fees
                if parsed_result.has_admin_fees:
                    self.stdout.write(f"   📝 Note: Student {student.student_id} is subject to ADMIN FEES")
                    # Could add logic here to flag for admin fees

        except Exception as e:
            self.stdout.write(f"   ⚠️  Warning: Could not handle special status: {e}")
