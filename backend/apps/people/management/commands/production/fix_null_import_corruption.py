"""Fix NULL import corruption in Person records."""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.people.models import Person


class Command(BaseCommand):
    """Fix Person records corrupted by NULL import."""

    help = "Fix citizenship='NU' and khmer_name='ណូឡឡ' corruption"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without making changes",
        )
        parser.add_argument(
            "--default-citizenship",
            type=str,
            default="KH",
            help="Default citizenship to use for NU records (default: KH)",
        )

    def handle(self, *args, **options):
        """Execute the fix."""
        dry_run = options["dry_run"]
        default_citizenship = options["default_citizenship"]

        self.stdout.write("=" * 80)
        self.stdout.write("FIX NULL IMPORT CORRUPTION")
        self.stdout.write("=" * 80)

        # The exact Khmer text for NULL
        khmer_null = "ណូឡឡ"  # No-la-la (NULL phonetically)

        # Find records with citizenship='NU'
        nu_citizenship = Person.objects.filter(citizenship="NU")
        nu_count = nu_citizenship.count()

        # Find records with khmer_name='ណូឡឡ'
        khmer_null_records = Person.objects.filter(khmer_name=khmer_null)
        khmer_null_count = khmer_null_records.count()

        # Find records with BOTH issues
        both_issues = Person.objects.filter(citizenship="NU", khmer_name=khmer_null)
        both_count = both_issues.count()

        self.stdout.write("\nCorrupted Records Found:")
        self.stdout.write(f"  - Citizenship = 'NU': {nu_count:,} records")
        self.stdout.write(f"  - Khmer name = 'ណូឡឡ': {khmer_null_count:,} records")
        self.stdout.write(f"  - Both issues: {both_count:,} records")

        # Show examples
        if both_count > 0:
            self.stdout.write("\nExamples of records with both issues:")
            for p in both_issues[:5]:
                self.stdout.write(
                    f"  ID {p.id}: {p.personal_name} {p.family_name} "
                    f"(Citizenship: '{p.citizenship}', Khmer: '{p.khmer_name}')"
                )

        # Also check for variations with whitespace
        khmer_null_with_space = Person.objects.filter(
            Q(khmer_name__startswith=khmer_null)
            | Q(khmer_name__endswith=khmer_null)
            | Q(khmer_name__contains=khmer_null)
        ).exclude(khmer_name=khmer_null)
        space_count = khmer_null_with_space.count()

        if space_count > 0:
            self.stdout.write(f"\n  - Khmer name contains 'ណូឡឡ' with extra chars: {space_count:,} records")
            for p in khmer_null_with_space[:3]:
                self.stdout.write(f"    ID {p.id}: '{p.khmer_name}' (length: {len(p.khmer_name)})")

        # Summary of changes
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("PROPOSED CHANGES:")
        self.stdout.write("=" * 80)

        total_to_fix = nu_count + khmer_null_count - both_count  # Don't double count

        self.stdout.write(f"\nTotal unique records to fix: {total_to_fix:,}")
        self.stdout.write("\nChanges to be made:")
        self.stdout.write(f"  1. Change citizenship from 'NU' to '{default_citizenship}': {nu_count:,} records")
        self.stdout.write(f"  2. Clear khmer_name 'ណូឡឡ' to empty string: {khmer_null_count:,} records")

        if dry_run:
            self.stdout.write("\n🔍 DRY RUN MODE - No changes will be made")
            return

        # Confirm before proceeding
        confirm = input(f"\n⚠️  Ready to update {total_to_fix:,} records? Type 'yes' to proceed: ")
        if confirm.lower() != "yes":
            self.stdout.write("❌ Operation cancelled.")
            return

        # Perform the updates
        with transaction.atomic():
            # Fix citizenship
            citizenship_updated = nu_citizenship.update(citizenship=default_citizenship)
            self.stdout.write(f"\n✅ Updated citizenship for {citizenship_updated:,} records")

            # Fix khmer_name (both exact matches and with whitespace)
            khmer_updated = khmer_null_records.update(khmer_name="")
            self.stdout.write(f"✅ Cleared khmer_name for {khmer_updated:,} records")

            # Fix variations with whitespace
            if space_count > 0:
                for record in khmer_null_with_space:
                    # Remove the NULL text but keep any other content
                    cleaned = record.khmer_name.replace(khmer_null, "").strip()
                    if cleaned != record.khmer_name:
                        record.khmer_name = cleaned
                        record.save(update_fields=["khmer_name"])
                self.stdout.write(f"✅ Cleaned khmer_name variations for {space_count:,} records")

        # Verify the fix
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("VERIFICATION:")
        self.stdout.write("=" * 80)

        remaining_nu = Person.objects.filter(citizenship="NU").count()
        remaining_khmer = Person.objects.filter(khmer_name=khmer_null).count()

        self.stdout.write("\nRemaining corrupted records:")
        self.stdout.write(f"  - Citizenship = 'NU': {remaining_nu:,}")
        self.stdout.write(f"  - Khmer name = 'ណូឡឡ': {remaining_khmer:,}")

        if remaining_nu == 0 and remaining_khmer == 0:
            self.stdout.write("\n✅ All NULL corruption has been fixed!")
        else:
            self.stdout.write("\n⚠️  Some records may still need attention")

        # Check for other potential issues
        self.stdout.write("\n" + "-" * 40)
        self.stdout.write("Additional checks:")

        # Check for other short citizenship codes that might be truncated
        weird_citizenship = Person.objects.filter(citizenship__in=["N", "NUL", "NULL"]).count()
        if weird_citizenship > 0:
            self.stdout.write(f"  - Other NULL-like citizenship codes: {weird_citizenship:,}")

        self.stdout.write("\n✅ Process complete!")
