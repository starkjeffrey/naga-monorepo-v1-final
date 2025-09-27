"""Management command to approximate Khmer names for students without them."""

import logging
from django.core.management.base import CommandError
from django.db.models import Q

from apps.common.management.base_migration import BaseMigrationCommand
from apps.people.models import Person, KhmerNamePattern
from apps.people.services.khmer_approximator import KhmerNameApproximator


logger = logging.getLogger(__name__)


class Command(BaseMigrationCommand):
    """Approximate Khmer names for students who don't have them."""

    help = "Approximate Khmer names for students without them using frequency-based patterns"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of records to process at once (default: 100)'
        )
        parser.add_argument(
            '--confidence-threshold',
            type=float,
            default=0.5,
            help='Minimum confidence score to apply approximation (default: 0.5)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform dry run without saving changes'
        )
        parser.add_argument(
            '--student-ids',
            nargs='*',
            type=int,
            help='Specific student IDs to process (optional)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force re-approximation of already approximated names'
        )
        parser.add_argument(
            '--max-records',
            type=int,
            help='Maximum number of records to process (for testing)'
        )

    def get_rejection_categories(self):
        """Define rejection categories for audit reporting."""
        return [
            'already_has_khmer_name',
            'already_approximated',
            'confidence_too_low',
            'decomposition_failed',
            'approximation_error',
            'no_patterns_available'
        ]

    def execute_migration(self, *args, **options):
        """Execute the approximation migration."""
        self.stdout.write("🤖 Starting Khmer name approximation...")

        # Check if we have patterns to work with
        pattern_count = KhmerNamePattern.objects.filter(
            confidence_score__gte=options['confidence_threshold']
        ).count()

        if pattern_count == 0:
            raise CommandError(
                f"No patterns found with confidence >= {options['confidence_threshold']}. "
                "Run 'analyze_khmer_names --save-patterns' first."
            )

        self.stdout.write(f"📊 Found {pattern_count} patterns available for approximation")

        # Get target people
        people_query = self._build_target_query(options)
        total_candidates = people_query.count()

        if total_candidates == 0:
            self.stdout.write(
                self.style.WARNING("⚠️  No people found matching criteria")
            )
            return

        # Apply max records limit if specified
        if options['max_records']:
            people_query = people_query[:options['max_records']]
            actual_count = min(total_candidates, options['max_records'])
            self.stdout.write(f"🎯 Processing {actual_count} of {total_candidates} candidates (limited)")
        else:
            actual_count = total_candidates
            self.stdout.write(f"🎯 Processing {actual_count} candidates")

        # Record input statistics
        self.record_input_stats(
            total_records=actual_count,
            source_description="People without Khmer names for approximation"
        )

        # Initialize approximator
        approximator = KhmerNameApproximator()

        # Process in batches
        processed_count = 0
        approximated_count = 0
        skipped_count = 0
        error_count = 0

        self.stdout.write("🔄 Processing batches...")

        for batch_start in range(0, actual_count, options['batch_size']):
            batch_end = min(batch_start + options['batch_size'], actual_count)
            batch_people = list(people_query[batch_start:batch_end])

            self.stdout.write(f"  📦 Batch {batch_start//options['batch_size'] + 1}: "
                             f"Processing people {batch_start + 1}-{batch_end}")

            # Process batch
            batch_results = self._process_batch(
                approximator,
                batch_people,
                options
            )

            # Update counters
            processed_count += len(batch_people)
            approximated_count += batch_results['approximated']
            skipped_count += batch_results['skipped']
            error_count += batch_results['errors']

            # Show progress
            self.stdout.write(f"    ✅ Approximated: {batch_results['approximated']}")
            self.stdout.write(f"    ⏭️  Skipped: {batch_results['skipped']}")
            if batch_results['errors'] > 0:
                self.stdout.write(f"    ❌ Errors: {batch_results['errors']}")

        # Display final results
        self.stdout.write("\n📈 Final Results:")
        self.stdout.write(f"  Total processed: {processed_count}")
        self.stdout.write(f"  Successfully approximated: {approximated_count}")
        self.stdout.write(f"  Skipped (low confidence): {skipped_count}")
        self.stdout.write(f"  Errors: {error_count}")

        if approximated_count > 0:
            success_rate = (approximated_count / processed_count) * 100
            self.stdout.write(f"  Success rate: {success_rate:.1f}%")

        # Record final statistics
        self.record_success('names_approximated', approximated_count)
        self.record_success('processing_success_rate', int((approximated_count / processed_count) * 100))

        if options['dry_run']:
            self.stdout.write(
                self.style.WARNING("🔍 DRY RUN - No changes were saved to database")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("🎉 Khmer name approximation completed successfully!")
            )

        # Show some approximation examples
        if approximated_count > 0 and not options['dry_run']:
            self._show_approximation_examples()

    def _build_target_query(self, options):
        """Build query for target people to process."""
        query = Person.objects.all()

        # Base filter: people without Khmer names or with empty Khmer names
        base_filter = Q(khmer_name__isnull=True) | Q(khmer_name__exact='')

        # If not forcing, exclude already approximated names
        if not options['force']:
            base_filter |= ~Q(khmer_name_source='approximated')

        query = query.filter(base_filter)

        # Filter by specific IDs if provided
        if options['student_ids']:
            query = query.filter(id__in=options['student_ids'])

        # Order by ID for consistent processing
        query = query.order_by('id')

        return query

    def _process_batch(self, approximator, people, options):
        """Process a batch of people."""
        results = {
            'approximated': 0,
            'skipped': 0,
            'errors': 0
        }

        person_ids = [person.id for person in people]

        try:
            if options['dry_run']:
                # For dry run, just test approximation without saving
                for person in people:
                    try:
                        result = approximator.approximate_for_person(person)
                        if result.confidence_score >= options['confidence_threshold']:
                            results['approximated'] += 1
                            self.stdout.write(
                                f"    🔍 {person.full_name} → {result.display_name} "
                                f"(confidence: {result.confidence_score:.2f})"
                            )
                        else:
                            results['skipped'] += 1
                            self.record_rejection(
                                'confidence_too_low',
                                person.id,
                                f"Confidence {result.confidence_score:.2f} below threshold"
                            )
                    except Exception as e:
                        results['errors'] += 1
                        self.record_rejection('approximation_error', person.id, str(e))
            else:
                # Real processing with database saves
                batch_results = approximator.batch_approximate(
                    person_ids,
                    confidence_threshold=options['confidence_threshold']
                )

                for result_data in batch_results:
                    if result_data['status'] == 'approximated':
                        results['approximated'] += 1
                        self.record_success('person_approximated', 1)
                    elif result_data['status'] == 'skipped_low_confidence':
                        results['skipped'] += 1
                        self.record_rejection(
                            'confidence_too_low',
                            result_data['person_id'],
                            f"Confidence {result_data.get('confidence', 0):.2f} below threshold"
                        )
                    else:
                        results['errors'] += 1
                        self.record_rejection(
                            'approximation_error',
                            result_data['person_id'],
                            result_data.get('error', 'Unknown error')
                        )

        except Exception as e:
            logger.exception(f"Error processing batch: {e}")
            results['errors'] += len(people)
            for person in people:
                self.record_rejection('approximation_error', person.id, str(e))

        return results

    def _show_approximation_examples(self):
        """Show some examples of approximated names."""
        self.stdout.write("\n🌟 Recent Approximation Examples:")
        self.stdout.write("-" * 70)

        # Get recently approximated names
        recent_approximations = Person.objects.filter(
            khmer_name_source='approximated'
        ).exclude(
            khmer_name__exact=''
        ).order_by('-khmer_name_approximated_at')[:5]

        for person in recent_approximations:
            confidence = person.khmer_name_confidence or 0
            method = "Unknown"
            if person.khmer_name_components:
                method = person.khmer_name_components.get('method_used', 'Unknown')

            self.stdout.write(
                f"  {person.full_name:<25} → {person.khmer_name:<20} "
                f"(confidence: {confidence:.2f}, method: {method})"
            )

        self.stdout.write("-" * 70)

    def _get_migration_description(self):
        """Get description for this migration."""
        return "Approximate Khmer names for students without them using frequency-based pattern matching"

    def _get_data_sources(self):
        """Get data sources for this migration."""
        return [
            "people_person (without khmer_name)",
            "people_khmernamepattern (for approximation)"
        ]

    def _get_target_tables(self):
        """Get target tables for this migration."""
        return ["people_person.khmer_name*"]