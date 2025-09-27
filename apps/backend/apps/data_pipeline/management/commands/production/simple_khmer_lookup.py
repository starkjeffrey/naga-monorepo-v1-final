"""
Simple Khmer name lookup command based on existing data patterns.

This command analyzes existing Khmer names to create a lookup table for family names,
then applies it to people missing Khmer names.
"""

from django.db import transaction
from django.db.models import Q

from apps.common.management.base_migration import BaseMigrationCommand
from apps.people.models import Person


class Command(BaseMigrationCommand):
    """Simple Khmer name lookup based on existing patterns."""

    help = "Apply simple Khmer family name lookup to people missing Khmer names"

    def get_rejection_categories(self):
        return [
            "no_family_name",
            "family_name_not_found",
            "already_has_khmer_name",
            "invalid_data",
        ]

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without making changes",
        )

    def execute_migration(self, *args, **options):
        dry_run = options.get("dry_run", False)

        if dry_run:
            self.stdout.write("DRY RUN MODE - No changes will be made")

        # Step 1: Build lookup table from existing data
        self.stdout.write("Building family name lookup table from existing Khmer names...")

        family_name_lookup = self._build_family_name_lookup()

        self.stdout.write(f"Built lookup table with {len(family_name_lookup)} family name patterns:")
        for english_name, khmer_name in family_name_lookup.items():
            self.stdout.write(f"  {english_name} → {khmer_name}")

        # Step 2: Find people missing Khmer names
        people_missing_khmer = Person.objects.filter(
            Q(khmer_name__isnull=True) | Q(khmer_name="")
        ).exclude(
            Q(family_name__isnull=True) | Q(family_name="")
        )

        self.record_input_stats(
            total_records=people_missing_khmer.count(),
            source_description="People missing Khmer names with valid family names"
        )

        self.stdout.write(f"Found {people_missing_khmer.count()} people missing Khmer names")

        # Step 3: Apply lookup
        successful_updates = 0

        with transaction.atomic():
            for person in people_missing_khmer:
                try:
                    family_name_upper = person.family_name.upper()

                    if family_name_upper in family_name_lookup:
                        khmer_name = self._clean_khmer_name(family_name_lookup[family_name_upper])

                        if not dry_run:
                            person.khmer_name = khmer_name
                            person.khmer_name_source = "lookup"
                            person.khmer_name_confidence = 0.8  # High confidence for direct lookup
                            person.save(update_fields=['khmer_name', 'khmer_name_source', 'khmer_name_confidence'])

                        self.record_success("khmer_name_applied", 1)
                        successful_updates += 1

                        self.stdout.write(
                            f"{'[DRY RUN] ' if dry_run else ''}Applied {person.family_name} → {khmer_name} for {person.full_name}"
                        )
                    else:
                        self.record_rejection(
                            category="family_name_not_found",
                            record_id=person.id,
                            reason=f"No Khmer pattern found for family name: {person.family_name}"
                        )

                except Exception as e:
                    self.record_rejection(
                        category="invalid_data",
                        record_id=person.id,
                        reason=f"Error processing {person.full_name}: {str(e)}"
                    )

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully applied Khmer names to {successful_updates} people")
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"DRY RUN: Would apply Khmer names to {successful_updates} people")
            )

    def _build_family_name_lookup(self):
        """Build lookup table from existing Khmer names."""
        # Get all people with both English family name and Khmer name
        people_with_khmer = Person.objects.filter(
            family_name__isnull=False,
            khmer_name__isnull=False
        ).exclude(
            family_name="",
            khmer_name=""
        ).values('family_name', 'khmer_name')

        # Build frequency mapping
        family_name_mapping = {}
        for person in people_with_khmer:
            family_name = person['family_name'].upper()
            khmer_name = self._clean_khmer_name(person['khmer_name'])

            # Skip empty names after cleaning
            if not khmer_name.strip():
                continue

            if family_name not in family_name_mapping:
                family_name_mapping[family_name] = {}

            if khmer_name not in family_name_mapping[family_name]:
                family_name_mapping[family_name][khmer_name] = 0

            family_name_mapping[family_name][khmer_name] += 1

        # Create final lookup with most frequent Khmer name for each family name
        final_lookup = {}
        for family_name, khmer_variants in family_name_mapping.items():
            # Get the most frequent Khmer name for this family name
            most_frequent_khmer = max(khmer_variants.items(), key=lambda x: x[1])[0]
            final_lookup[family_name] = most_frequent_khmer

        return final_lookup

    def _clean_khmer_name(self, khmer_name):
        """Clean Khmer name by removing suffixes like {AF}, (ST), <PLF>, etc."""
        if not khmer_name:
            return khmer_name

        import re

        # Remove common suffixes and tags
        patterns_to_remove = [
            r'\{[^}]*\}',  # {AF}, {FRIENDS}, etc.
            r'\([^)]*\)',  # (ST), (PLF), etc.
            r'<[^>]*>',    # <PLF>, <CRST>, <PEPY>, etc.
            r'\$\$.*',     # $$ and everything after
        ]

        cleaned_name = khmer_name.strip()
        for pattern in patterns_to_remove:
            cleaned_name = re.sub(pattern, '', cleaned_name).strip()

        return cleaned_name