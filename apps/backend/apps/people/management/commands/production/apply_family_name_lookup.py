"""
Apply family name lookup to students missing Khmer names.

This command uses the permanent lookup table (KhmerNamePattern) to assign
Khmer names to students who only have English family names.
"""

from django.db import transaction
from django.db.models import Q

from apps.common.management.base_migration import BaseMigrationCommand
from apps.people.models import KhmerNamePattern, Person


class Command(BaseMigrationCommand):
    """Apply family name lookup to generate Khmer names for missing students."""

    help = "Apply family name lookup to students missing Khmer names"

    def get_rejection_categories(self):
        return [
            "no_family_name",
            "family_name_not_found_in_lookup",
            "already_has_khmer_name",
            "low_confidence_pattern",
            "invalid_data",
        ]

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be done without applying names",
        )
        parser.add_argument(
            "--min-confidence",
            type=float,
            default=0.5,
            help="Minimum confidence score to apply a pattern (default: 0.5)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of students to process (for testing)",
        )

    def execute_migration(self, *args, **options):
        dry_run = options.get("dry_run", False)
        min_confidence = options.get("min_confidence", 0.5)
        limit = options.get("limit")

        if dry_run:
            self.stdout.write("DRY RUN MODE - No Khmer names will be applied")

        self.stdout.write(f"Using minimum confidence threshold: {min_confidence}")

        # Step 1: Find people missing Khmer names
        people_missing_khmer = Person.objects.filter(
            Q(khmer_name__isnull=True) | Q(khmer_name="")
        ).exclude(
            Q(family_name__isnull=True) | Q(family_name="")
        )

        if limit:
            people_missing_khmer = people_missing_khmer[:limit]
            self.stdout.write(f"Limiting to first {limit} students for testing")

        total_people = people_missing_khmer.count()

        self.record_input_stats(
            total_records=total_people,
            source_description="People missing Khmer names with valid family names"
        )

        self.stdout.write(f"Found {total_people} people missing Khmer names")

        # Step 2: Load lookup patterns
        patterns = {
            pattern.english_component: pattern
            for pattern in KhmerNamePattern.objects.filter(
                confidence_score__gte=min_confidence
            )
        }

        self.stdout.write(f"Loaded {len(patterns)} family name patterns with confidence ≥ {min_confidence}")

        # Step 3: Apply lookup
        successful_applications = 0
        skipped_low_confidence = 0

        with transaction.atomic():
            for person in people_missing_khmer:
                try:
                    family_name_upper = person.family_name.upper()

                    if family_name_upper in patterns:
                        pattern = patterns[family_name_upper]

                        if pattern.confidence_score >= min_confidence:
                            if not dry_run:
                                person.khmer_name = pattern.unicode_pattern
                                person.khmer_name_source = "lookup"
                                person.khmer_name_confidence = float(pattern.confidence_score)
                                person.save(update_fields=[
                                    'khmer_name',
                                    'khmer_name_source',
                                    'khmer_name_confidence'
                                ])

                            self.record_success("khmer_name_applied", 1)
                            successful_applications += 1

                            self.stdout.write(
                                f"{'[DRY RUN] ' if dry_run else ''}Applied: "
                                f"{person.family_name} {person.personal_name} → {pattern.unicode_pattern} "
                                f"(conf: {pattern.confidence_score:.2f})"
                            )
                        else:
                            self.record_rejection(
                                category="low_confidence_pattern",
                                record_id=person.id,
                                reason=f"Pattern confidence {pattern.confidence_score:.2f} below threshold {min_confidence}"
                            )
                            skipped_low_confidence += 1
                    else:
                        self.record_rejection(
                            category="family_name_not_found_in_lookup",
                            record_id=person.id,
                            reason=f"No pattern found for family name: {person.family_name}"
                        )

                except Exception as e:
                    self.record_rejection(
                        category="invalid_data",
                        record_id=person.id,
                        reason=f"Error processing {person.full_name}: {str(e)}"
                    )

        # Step 4: Display results
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully applied Khmer names to {successful_applications} people"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would apply Khmer names to {successful_applications} people"
                )
            )

        if skipped_low_confidence > 0:
            self.stdout.write(
                self.style.WARNING(
                    f"Skipped {skipped_low_confidence} people due to low confidence patterns"
                )
            )

        # Step 5: Show statistics
        self._show_application_statistics(min_confidence)

    def _show_application_statistics(self, min_confidence):
        """Display statistics about the application results."""
        total_people = Person.objects.count()
        people_with_khmer = Person.objects.exclude(
            Q(khmer_name__isnull=True) | Q(khmer_name="")
        ).count()
        people_from_lookup = Person.objects.filter(
            khmer_name_source="lookup"
        ).count()

        self.stdout.write("\n" + "="*60)
        self.stdout.write("KHMER NAME APPLICATION STATISTICS")
        self.stdout.write("="*60)
        self.stdout.write(f"Total people in database: {total_people:,}")
        self.stdout.write(f"People with Khmer names: {people_with_khmer:,} ({people_with_khmer/total_people*100:.1f}%)")
        self.stdout.write(f"Applied from lookup table: {people_from_lookup:,}")
        self.stdout.write("="*60)

        # Show breakdown by confidence
        confidence_ranges = [
            (0.9, 1.0, "Very High"),
            (0.7, 0.9, "High"),
            (0.5, 0.7, "Medium"),
            (0.0, 0.5, "Low")
        ]

        self.stdout.write("\nBreakdown by Confidence Level:")
        for min_conf, max_conf, label in confidence_ranges:
            count = Person.objects.filter(
                khmer_name_source="lookup",
                khmer_name_confidence__gte=min_conf,
                khmer_name_confidence__lt=max_conf
            ).count()
            self.stdout.write(f"  {label} ({min_conf:.1f}-{max_conf:.1f}): {count:,}")

        # Show top family names applied
        from django.db.models import Count
        top_applied = Person.objects.filter(
            khmer_name_source="lookup"
        ).values('family_name', 'khmer_name').annotate(
            count=Count('id')
        ).order_by('-count')[:10]

        if top_applied:
            self.stdout.write("\nTop 10 Applied Family Name Patterns:")
            for i, item in enumerate(top_applied, 1):
                self.stdout.write(
                    f"{i:2d}. {item['family_name']} → {item['khmer_name']} "
                    f"(×{item['count']})"
                )