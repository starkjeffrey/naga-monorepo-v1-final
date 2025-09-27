"""Fix Khmer names that contain 'NULL' written in Khmer script."""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.people.models import Person


class Command(BaseCommand):
    """Fix Khmer names containing NULL written in Khmer."""

    help = "Replace 'NULL' written in Khmer with empty string"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be changed without making changes",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of records to process",
        )

    def handle(self, *args, **options):
        """Execute the fix."""
        dry_run = options["dry_run"]
        limit = options.get("limit")

        self.stdout.write("=" * 80)
        self.stdout.write("FIX KHMER NULL NAMES")
        self.stdout.write("=" * 80)

        # Common ways "NULL" might be written in Khmer
        # These are various phonetic spellings of "NULL" in Khmer script
        null_patterns = [
            "ណុល",  # nul
            "ណូល",  # noul
            "នុល",  # nul (different first letter)
            "នូល",  # noul (different first letter)
            "ណល់",  # nal
            "នល់",  # nal (different first letter)
            "ណុលល៍",  # null with final consonant
            "ណូលល៍",  # noull with final consonant
            "NULL",  # English NULL
            "Null",  # English Null
            "null",  # English null
        ]

        # Find all records with these patterns
        total_found = 0
        records_to_fix = []

        for pattern in null_patterns:
            queryset = Person.objects.filter(khmer_name=pattern)
            if limit and total_found >= limit:
                break

            count = queryset.count()
            if count > 0:
                self.stdout.write(f"\nFound {count} records with '{pattern}'")

                # Show examples
                examples = queryset[:5]
                for person in examples:
                    self.stdout.write(
                        f"  ID {person.id}: {person.personal_name} {person.family_name} (Khmer: '{person.khmer_name}')"
                    )

                if limit:
                    remaining = limit - total_found
                    records_to_fix.extend(list(queryset[:remaining]))
                else:
                    records_to_fix.extend(list(queryset))

                total_found += count

        # Also check for patterns that contain NULL as substring
        self.stdout.write("\n" + "-" * 40)
        self.stdout.write("Checking for NULL as substring...")

        for pattern in ["ណុល", "ណូល", "នុល", "នូល"]:
            queryset = Person.objects.filter(khmer_name__icontains=pattern).exclude(khmer_name__in=null_patterns)
            count = queryset.count()
            if count > 0:
                self.stdout.write(f"\nFound {count} records containing '{pattern}' as substring")
                examples = queryset[:3]
                for person in examples:
                    self.stdout.write(
                        f"  ID {person.id}: {person.personal_name} {person.family_name} (Khmer: '{person.khmer_name}')"
                    )

        # Summary
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(f"TOTAL RECORDS TO FIX: {len(records_to_fix)}")
        self.stdout.write("=" * 80)

        if not records_to_fix:
            self.stdout.write("\nNo records found with NULL in Khmer.")
            return

        if dry_run:
            self.stdout.write("\nDRY RUN - No changes will be made")
            self.stdout.write("\nWould update the following records:")
            for i, person in enumerate(records_to_fix[:20], 1):
                self.stdout.write(
                    f"{i}. ID {person.id}: {person.personal_name} {person.family_name} "
                    f"- Would clear '{person.khmer_name}'"
                )
            if len(records_to_fix) > 20:
                self.stdout.write(f"... and {len(records_to_fix) - 20} more records")
        else:
            # Perform the update
            confirm = input(f"\nReady to update {len(records_to_fix)} records? (yes/no): ")
            if confirm.lower() != "yes":
                self.stdout.write("Aborted.")
                return

            with transaction.atomic():
                updated = 0
                for person in records_to_fix:
                    person.khmer_name = ""  # Set to empty string
                    person.save(update_fields=["khmer_name"])
                    updated += 1

                    if updated % 100 == 0:
                        self.stdout.write(f"Updated {updated} records...")

                self.stdout.write(f"\n✅ Successfully updated {updated} records")

        # Additional check for alternate Khmer name field
        self.stdout.write("\n" + "-" * 40)
        self.stdout.write("Checking alternate_khmer_name field...")

        for pattern in null_patterns[:4]:  # Check main patterns
            count = Person.objects.filter(alternate_khmer_name=pattern).count()
            if count > 0:
                self.stdout.write(f"Found {count} records with '{pattern}' in alternate_khmer_name")
                if not dry_run:
                    self.stdout.write("Run with --fix-alternate to also fix these")

        self.stdout.write("\n✅ Process complete!")
