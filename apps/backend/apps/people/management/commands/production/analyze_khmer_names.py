"""Management command to analyze existing Khmer names and build pattern dictionary."""

import logging
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.common.management.base_migration import BaseMigrationCommand
from apps.people.services.pattern_analyzer import PatternAnalyzer


logger = logging.getLogger(__name__)


class Command(BaseMigrationCommand):
    """Analyze existing Khmer names to extract patterns for approximation."""

    help = "Analyze existing Khmer names and build frequency-based pattern dictionary"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            '--batch-size',
            type=int,
            default=1000,
            help='Number of records to process at once (default: 1000)'
        )
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.5,
            help='Minimum confidence score to save patterns (default: 0.5)'
        )
        parser.add_argument(
            '--min-count',
            type=int,
            default=2,
            help='Minimum occurrence count to save patterns (default: 2)'
        )
        parser.add_argument(
            '--save-patterns',
            action='store_true',
            help='Save patterns to database (default: False - analysis only)'
        )
        parser.add_argument(
            '--generate-report',
            action='store_true',
            help='Generate detailed analysis report'
        )

    def get_rejection_categories(self):
        """Define rejection categories for audit reporting."""
        return [
            'no_khmer_name',
            'invalid_khmer_name',
            'decomposition_failed',
            'pattern_extraction_failed',
            'confidence_too_low',
            'count_too_low'
        ]

    def execute_migration(self, *args, **options):
        """Execute the analysis migration."""
        self.stdout.write("🔍 Starting Khmer name pattern analysis...")

        # Initialize analyzer
        analyzer = PatternAnalyzer()

        # Record input statistics
        from apps.people.models import Person
        total_people = Person.objects.count()
        people_with_khmer = Person.objects.exclude(
            khmer_name__isnull=True
        ).exclude(
            khmer_name__exact=''
        ).exclude(
            khmer_name__startswith='*'
        ).count()

        self.record_input_stats(
            total_records=total_people,
            source_description="People with Khmer names for pattern analysis"
        )

        self.stdout.write(f"📊 Found {people_with_khmer} people with Khmer names out of {total_people} total")

        if people_with_khmer == 0:
            self.record_rejection('no_khmer_name', None, "No people with Khmer names found")
            raise CommandError("No people with Khmer names found. Cannot perform analysis.")

        # Run analysis
        try:
            self.stdout.write("🔍 Analyzing existing names...")
            results = analyzer.analyze_existing_names(batch_size=options['batch_size'])

            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Analysis complete! Found {results['statistics']['total_components']} "
                    f"components with {results['statistics']['total_patterns']} patterns"
                )
            )

            # Record success statistics
            self.record_success('patterns_extracted', results['statistics']['total_patterns'])
            self.record_success('components_analyzed', results['statistics']['total_components'])

            # Save patterns to database if requested
            if options['save_patterns']:
                self.stdout.write("💾 Saving patterns to database...")
                patterns_saved = analyzer.save_patterns_to_database(
                    min_confidence=options['min_confidence'],
                    min_count=options['min_count']
                )

                self.stdout.write(
                    self.style.SUCCESS(f"✅ Saved {patterns_saved} patterns to database")
                )
                self.record_success('patterns_saved', patterns_saved)

                # Record rejections for patterns not meeting criteria
                total_patterns = results['statistics']['total_patterns']
                rejected_patterns = total_patterns - patterns_saved
                if rejected_patterns > 0:
                    self.record_rejection(
                        'confidence_too_low',
                        None,
                        f"{rejected_patterns} patterns rejected for low confidence/count"
                    )

            # Generate analysis report if requested
            if options['generate_report']:
                self.stdout.write("📄 Generating analysis report...")
                report = analyzer.generate_analysis_report()

                # Save report to file
                report_path = self.get_report_path('khmer_name_analysis_report.md')
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(report)

                self.stdout.write(f"📄 Report saved to: {report_path}")

                # Also display top patterns
                self._display_top_patterns(analyzer.analysis_results)

            # Validate pattern quality
            quality_report = analyzer.validate_pattern_quality()
            self.stdout.write("\n📈 Pattern Quality Assessment:")
            self.stdout.write(f"  High confidence patterns: {quality_report['high_confidence']}")
            self.stdout.write(f"  Medium confidence patterns: {quality_report['medium_confidence']}")
            self.stdout.write(f"  Low confidence patterns: {quality_report['low_confidence']}")
            self.stdout.write(f"  Overall quality score: {quality_report['quality_score']:.2f}")

            # Record quality metrics
            self.record_success('high_confidence_patterns', quality_report['high_confidence'])
            self.record_success('quality_score', int(quality_report['quality_score'] * 100))

        except Exception as e:
            logger.exception("Error during pattern analysis")
            self.record_rejection('pattern_extraction_failed', None, str(e))
            raise CommandError(f"Analysis failed: {e}")

        self.stdout.write(
            self.style.SUCCESS("🎉 Khmer name pattern analysis completed successfully!")
        )

    def _display_top_patterns(self, analysis_results):
        """Display top patterns in the console."""
        if not analysis_results or 'patterns' not in analysis_results:
            return

        self.stdout.write("\n🔝 Top 10 Most Common Name Components:")
        self.stdout.write("-" * 60)

        # Sort components by total occurrences
        sorted_components = sorted(
            analysis_results['patterns'].items(),
            key=lambda x: x[1]['total_occurrences'],
            reverse=True
        )

        for i, (english_comp, comp_data) in enumerate(sorted_components[:10], 1):
            most_common_pattern = comp_data['patterns'].get(comp_data['most_common'], {})

            self.stdout.write(
                f"{i:2d}. {english_comp:<15} → {most_common_pattern.get('unicode', 'N/A'):<20} "
                f"(freq: {most_common_pattern.get('frequency', 0):.2f}, "
                f"count: {comp_data['total_occurrences']})"
            )

        self.stdout.write("-" * 60)

    def _get_migration_description(self):
        """Get description for this migration."""
        return "Analyze existing Khmer names to extract frequency-based patterns for approximation system"

    def _get_data_sources(self):
        """Get data sources for this migration."""
        return ["people_person.khmer_name", "people_person.family_name", "people_person.personal_name"]

    def _get_target_tables(self):
        """Get target tables for this migration."""
        return ["people_khmernamepattern"]