"""
Management command to run Khmer name approximation pipeline stage.

This command executes the KhmerNameApproximationStage to approximate
Khmer names for people who don't have them.
"""

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q
from django.utils import timezone

from apps.common.management.base_migration import BaseMigrationCommand
from apps.data_pipeline.core.khmer_name_stage import KhmerNameApproximationStage
from apps.data_pipeline.configs.base import PipelineLogger
from apps.people.models import Person


class Command(BaseMigrationCommand):
    """Run Khmer name approximation for people without Khmer names."""

    help = "Run Khmer name approximation pipeline stage"

    def get_rejection_categories(self):
        """Define rejection categories for audit reporting."""
        return [
            "low_confidence",
            "decomposition_failed",
            "pattern_not_found",
            "processing_error"
        ]

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--target-ids',
            type=str,
            help='Comma-separated list of specific person IDs to process'
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
            help='Run without saving changes to database'
        )
        parser.add_argument(
            '--limit',
            type=int,
            help='Maximum number of records to process'
        )
        parser.add_argument(
            '--latest',
            action='store_true',
            help='Process latest records first (highest IDs)'
        )

    def execute_migration(self, *args, **options):
        """Execute the Khmer name approximation pipeline stage."""
        # Initialize pipeline logger
        logger = PipelineLogger()
        stage = KhmerNameApproximationStage(logger)

        # Parse target IDs if provided
        target_ids = None
        if options['target_ids']:
            try:
                target_ids = [int(id.strip()) for id in options['target_ids'].split(',')]
                self.stdout.write(f"🎯 Processing specific IDs: {target_ids}")
            except ValueError:
                raise CommandError("Invalid target IDs format. Use comma-separated integers.")

        # If no specific IDs, find candidates
        if not target_ids:
            # Find people without Khmer names
            candidates = Person.objects.filter(
                Q(khmer_name__isnull=True) | Q(khmer_name__exact='')
            ).exclude(
                khmer_name_source='approximated'  # Don't re-approximate
            )

            if options['latest']:
                candidates = candidates.order_by('-id')
            else:
                candidates = candidates.order_by('id')

            if options['limit']:
                candidates = candidates[:options['limit']]

            target_ids = list(candidates.values_list('id', dtype=int))

            if not target_ids:
                self.stdout.write("ℹ️  No candidates found for approximation")
                return

            self.stdout.write(f"🎯 Found {len(target_ids)} candidates for approximation")
            if options['latest']:
                self.stdout.write(f"📋 Latest IDs: {target_ids[:10]}{'...' if len(target_ids) > 10 else ''}")
            else:
                self.stdout.write(f"📋 ID range: {min(target_ids)} - {max(target_ids)}")

        # Record input statistics
        self.record_input_stats(
            total_records=len(target_ids),
            source_description="People without Khmer names",
            processing_mode="khmer_approximation"
        )

        # Execute the pipeline stage
        try:
            self.stdout.write("🚀 Starting Khmer name approximation pipeline...")

            start_time = timezone.now()
            results = stage.execute(
                target_ids=target_ids,
                confidence_threshold=options['confidence_threshold'],
                dry_run=options['dry_run']
            )

            # Record results in audit system
            stats = results['statistics']

            # Record successful approximations
            self.record_success("approximated", stats['approximated'])

            # Record rejections by category
            self.record_rejection(
                category="low_confidence",
                count=stats['skipped'],
                reason=f"Confidence below {options['confidence_threshold']}"
            )

            self.record_rejection(
                category="processing_error",
                count=stats['errors'],
                reason="Failed during approximation processing"
            )

            # Generate and display report
            report = stage.generate_report(results)
            self.stdout.write("\n" + "="*60)
            self.stdout.write("📊 KHMER NAME APPROXIMATION REPORT")
            self.stdout.write("="*60)
            self.stdout.write(report)

            # Show examples if available
            if results.get('examples'):
                self.stdout.write("\n🌟 EXAMPLE APPROXIMATIONS:")
                for example in results['examples'][:5]:  # Show first 5
                    self.stdout.write(
                        f"  ID {example['id']}: {example['english_name']} → {example['khmer_name']} "
                        f"(confidence: {example['confidence']:.2f})"
                    )

            if options['dry_run']:
                self.stdout.write("\n⚠️  DRY RUN MODE - No changes were saved to database")
            else:
                self.stdout.write(f"\n✅ Processing completed in {stats['elapsed_time']:.2f} seconds")

        except Exception as e:
            # Record processing error
            self.record_rejection(
                category="processing_error",
                count=len(target_ids),
                reason=f"Pipeline stage failed: {str(e)}"
            )
            raise CommandError(f"Pipeline stage execution failed: {e}")

        # Final summary
        self.stdout.write("\n" + "="*40)
        self.stdout.write("📈 PROCESSING SUMMARY")
        self.stdout.write("="*40)
        self.stdout.write(f"Total Records: {len(target_ids)}")
        self.stdout.write(f"Successfully Approximated: {stats['approximated']}")
        self.stdout.write(f"Skipped (Low Confidence): {stats['skipped']}")
        self.stdout.write(f"Errors: {stats['errors']}")
        self.stdout.write(f"Success Rate: {stats['success_rate']:.1f}%")

        if not options['dry_run'] and stats['approximated'] > 0:
            self.stdout.write(f"\n✨ {stats['approximated']} people now have approximated Khmer names!")