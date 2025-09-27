"""
Build permanent family name lookup table from existing Khmer names.

This command analyzes all existing Khmer names in the database to create
a permanent lookup table that maps English family names to their most
common Khmer equivalents. This lookup table is saved in the KhmerNamePattern
model for future use.
"""

from django.db import transaction
from django.db.models import Count

from apps.common.management.base_migration import BaseMigrationCommand
from apps.people.models import KhmerNamePattern, Person


class Command(BaseMigrationCommand):
    """Build permanent family name lookup table from existing data."""

    help = "Build permanent family name lookup table from existing Khmer names"

    def get_rejection_categories(self):
        return [
            "no_khmer_name",
            "no_family_name",
            "invalid_data",
            "pattern_creation_failed",
        ]

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without creating patterns",
        )
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="Overwrite existing patterns",
        )

    def execute_migration(self, *args, **options):
        dry_run = options.get("dry_run", False)
        overwrite = options.get("overwrite", False)

        if dry_run:
            self.stdout.write("DRY RUN MODE - No patterns will be created")

        # Step 1: Analyze existing data to build frequency mapping
        self.stdout.write("Analyzing existing Khmer names in the database...")

        family_name_mapping = self._build_family_name_frequency_mapping()

        self.record_input_stats(
            total_records=len(family_name_mapping),
            source_description="Unique family names with Khmer equivalents"
        )

        self.stdout.write(f"Found {len(family_name_mapping)} family name patterns:")

        # Step 2: Create/update KhmerNamePattern records
        patterns_created = 0
        patterns_updated = 0

        with transaction.atomic():
            for english_family_name, khmer_data in family_name_mapping.items():
                try:
                    most_frequent_khmer = khmer_data['most_frequent']
                    frequency_count = khmer_data['frequency_count']
                    total_count = khmer_data['total_count']
                    confidence = frequency_count / total_count if total_count > 0 else 0.0

                    self.stdout.write(
                        f"  {english_family_name} → {most_frequent_khmer} "
                        f"(×{frequency_count}/{total_count}, confidence: {confidence:.2f})"
                    )

                    if not dry_run:
                        # Check if pattern already exists
                        pattern, created = KhmerNamePattern.objects.get_or_create(
                            english_component=english_family_name,
                            normalized_component=english_family_name.lower(),
                            defaults={
                                'limon_pattern': most_frequent_khmer,  # Using Khmer as LIMON for now
                                'unicode_pattern': most_frequent_khmer,
                                'frequency': confidence,
                                'occurrence_count': frequency_count,
                                'confidence_score': confidence,
                                'is_verified': True,  # High confidence since derived from real data
                            }
                        )

                        if created:
                            patterns_created += 1
                            self.record_success("pattern_created", 1)
                        elif overwrite:
                            # Update existing pattern with new data
                            pattern.limon_pattern = most_frequent_khmer
                            pattern.unicode_pattern = most_frequent_khmer
                            pattern.frequency = confidence
                            pattern.occurrence_count = frequency_count
                            pattern.confidence_score = confidence
                            pattern.is_verified = True
                            pattern.save()
                            patterns_updated += 1
                            self.record_success("pattern_updated", 1)
                        else:
                            self.record_rejection(
                                category="pattern_creation_failed",
                                record_id=english_family_name,
                                reason="Pattern already exists (use --overwrite to update)"
                            )

                except Exception as e:
                    self.record_rejection(
                        category="pattern_creation_failed",
                        record_id=english_family_name,
                        reason=f"Error creating pattern: {str(e)}"
                    )

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully created {patterns_created} new patterns and updated {patterns_updated} existing patterns"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would create/update {len(family_name_mapping)} family name patterns"
                )
            )

        # Step 3: Display statistics
        self._display_lookup_statistics()

    def _build_family_name_frequency_mapping(self):
        """Build frequency mapping from existing data."""
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
            khmer_name = person['khmer_name']

            if family_name not in family_name_mapping:
                family_name_mapping[family_name] = {}

            if khmer_name not in family_name_mapping[family_name]:
                family_name_mapping[family_name][khmer_name] = 0

            family_name_mapping[family_name][khmer_name] += 1

        # Create final lookup with most frequent Khmer name for each family name
        final_mapping = {}
        for family_name, khmer_variants in family_name_mapping.items():
            if not khmer_variants:  # Skip empty variants
                continue

            # Get the most frequent Khmer name for this family name
            most_frequent_khmer = max(khmer_variants.items(), key=lambda x: x[1])
            khmer_name = most_frequent_khmer[0]
            frequency_count = most_frequent_khmer[1]
            total_count = sum(khmer_variants.values())

            final_mapping[family_name] = {
                'most_frequent': khmer_name,
                'frequency_count': frequency_count,
                'total_count': total_count,
                'all_variants': khmer_variants
            }

        return final_mapping

    def _display_lookup_statistics(self):
        """Display statistics about the lookup table."""
        total_patterns = KhmerNamePattern.objects.count()
        verified_patterns = KhmerNamePattern.objects.filter(is_verified=True).count()

        high_confidence = KhmerNamePattern.objects.filter(confidence_score__gte=0.8).count()
        medium_confidence = KhmerNamePattern.objects.filter(
            confidence_score__gte=0.5,
            confidence_score__lt=0.8
        ).count()
        low_confidence = KhmerNamePattern.objects.filter(confidence_score__lt=0.5).count()

        self.stdout.write("\n" + "="*50)
        self.stdout.write("FAMILY NAME LOOKUP TABLE STATISTICS")
        self.stdout.write("="*50)
        self.stdout.write(f"Total patterns: {total_patterns}")
        self.stdout.write(f"Verified patterns: {verified_patterns}")
        self.stdout.write(f"High confidence (≥0.8): {high_confidence}")
        self.stdout.write(f"Medium confidence (0.5-0.8): {medium_confidence}")
        self.stdout.write(f"Low confidence (<0.5): {low_confidence}")
        self.stdout.write("="*50)

        # Show top 10 most frequent patterns
        top_patterns = KhmerNamePattern.objects.order_by('-occurrence_count')[:10]
        if top_patterns:
            self.stdout.write("\nTop 10 Most Frequent Family Name Patterns:")
            for i, pattern in enumerate(top_patterns, 1):
                self.stdout.write(
                    f"{i:2d}. {pattern.english_component} → {pattern.unicode_pattern} "
                    f"(×{pattern.occurrence_count}, conf: {pattern.confidence_score:.2f})"
                )