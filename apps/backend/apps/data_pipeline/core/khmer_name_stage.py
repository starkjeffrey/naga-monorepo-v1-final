"""
Khmer Name Approximation Stage for Data Pipeline

This stage analyzes existing data to build patterns and approximates
Khmer names for students who don't have them.
"""

import time
from typing import Any, Dict, List
from pathlib import Path

from django.db.models import Q
from django.db import transaction
from django.utils import timezone

from apps.people.models import Person, KhmerNamePattern
from apps.people.services.pattern_analyzer import PatternAnalyzer
from apps.people.services.khmer_approximator import KhmerNameApproximator
from ..configs.base import PipelineLogger


class KhmerNameApproximationStage:
    """Pipeline stage for Khmer name approximation."""

    def __init__(self, logger: PipelineLogger):
        self.logger = logger
        self.analyzer = PatternAnalyzer()
        self.approximator = KhmerNameApproximator()

    def execute(self,
                target_ids: List[int] = None,
                confidence_threshold: float = 0.5,
                dry_run: bool = False) -> Dict[str, Any]:
        """Execute Khmer name approximation pipeline stage.

        Args:
            target_ids: Specific person IDs to process (if None, processes all without Khmer names)
            confidence_threshold: Minimum confidence to apply approximation
            dry_run: If True, doesn't save changes

        Returns:
            Dictionary with processing results and statistics
        """
        start_time = time.time()

        self.logger.info("🇰🇭 Starting Khmer Name Approximation Stage")

        try:
            # Step 1: Analyze existing patterns if needed
            pattern_count = KhmerNamePattern.objects.count()
            if pattern_count < 5:  # Build patterns if we don't have enough
                self.logger.info("📚 Building pattern dictionary from existing data...")
                self._build_patterns()
            else:
                self.logger.info(f"📚 Using existing {pattern_count} patterns")

            # Step 2: Find target people
            target_people = self._find_target_people(target_ids)
            if not target_people:
                self.logger.info("ℹ️  No target people found for approximation")
                return self._create_result(0, 0, 0, 0, time.time() - start_time)

            self.logger.info(f"🎯 Found {len(target_people)} people for approximation")

            # Step 3: Process approximations
            results = self._process_approximations(
                target_people,
                confidence_threshold,
                dry_run
            )

            # Step 4: Generate report
            elapsed_time = time.time() - start_time
            self.logger.info(f"✅ Khmer name approximation completed in {elapsed_time:.2f}s")

            return self._create_result(
                total_processed=len(target_people),
                approximated=results['approximated'],
                skipped=results['skipped'],
                errors=results['errors'],
                elapsed_time=elapsed_time,
                examples=results['examples']
            )

        except Exception as e:
            self.logger.error(f"❌ Khmer name approximation stage failed: {e}")
            raise

    def _build_patterns(self) -> None:
        """Build pattern dictionary from existing Khmer names."""
        # Analyze existing names
        results = self.analyzer.analyze_existing_names(batch_size=500)

        if results['statistics']['total_patterns'] > 0:
            # Save patterns to database
            patterns_saved = self.analyzer.save_patterns_to_database(
                min_confidence=0.3,  # Lower threshold for initial patterns
                min_count=1
            )
            self.logger.info(f"📚 Created {patterns_saved} patterns from analysis")

            # Add some common Khmer name patterns for bootstrapping
            self._add_bootstrap_patterns()
        else:
            self.logger.warning("⚠️  No patterns found in existing data, using bootstrap patterns only")
            self._add_bootstrap_patterns()

    def _add_bootstrap_patterns(self) -> None:
        """Add common Khmer name patterns for bootstrapping."""
        bootstrap_patterns = [
            ("sovann", "សុវណ្ណ", 0.85, 15),
            ("dara", "ដារា", 0.92, 20),
            ("chan", "ចន្ទ", 0.78, 12),
            ("reach", "រាជ", 0.81, 14),
            ("sokha", "សុខា", 0.90, 18),
            ("phalla", "ផល្លា", 0.76, 10),
            ("veasna", "វាសនា", 0.88, 16),
            ("chantha", "ច័ន្ទថា", 0.82, 13),
            ("sopheak", "សុភ័ក្ត", 0.79, 11),
            ("ratha", "រថា", 0.83, 12),
            ("kunthea", "គន្ធា", 0.77, 9),
            ("makara", "មករា", 0.84, 14),
            ("pisach", "ពិសាច", 0.75, 8),
            ("rithy", "រិទ្ធី", 0.86, 15),
            ("seanghai", "សៀងហៃ", 0.74, 7),
        ]

        created_count = 0
        for english, khmer, confidence, count in bootstrap_patterns:
            pattern, created = KhmerNamePattern.objects.get_or_create(
                english_component=english,
                defaults={
                    'normalized_component': english,
                    'limon_pattern': khmer,
                    'unicode_pattern': khmer,
                    'frequency': confidence,
                    'occurrence_count': count,
                    'confidence_score': confidence,
                    'is_verified': False  # Bootstrap patterns are not user-verified
                }
            )
            if created:
                created_count += 1

        self.logger.info(f"🌱 Added {created_count} bootstrap patterns")

    def _find_target_people(self, target_ids: List[int] = None) -> List[Person]:
        """Find people who need Khmer name approximation."""
        # Base query: people without Khmer names
        query = Person.objects.filter(
            Q(khmer_name__isnull=True) | Q(khmer_name__exact='')
        ).exclude(
            khmer_name_source='approximated'  # Don't re-approximate
        )

        # Filter by specific IDs if provided
        if target_ids:
            query = query.filter(id__in=target_ids)

        # Order by ID descending to get latest first
        return list(query.order_by('-id'))

    def _process_approximations(self,
                               people: List[Person],
                               confidence_threshold: float,
                               dry_run: bool) -> Dict[str, Any]:
        """Process approximations for a list of people."""
        results = {
            'approximated': 0,
            'skipped': 0,
            'errors': 0,
            'examples': []
        }

        for person in people:
            try:
                # Get approximation
                result = self.approximator.approximate_for_person(person)

                if result.confidence_score >= confidence_threshold:
                    if not dry_run:
                        # Apply approximation
                        with transaction.atomic():
                            person.khmer_name = result.display_name
                            person.khmer_name_source = 'approximated'
                            person.khmer_name_confidence = result.confidence_score
                            person.khmer_name_approximated_at = timezone.now()
                            person.khmer_name_components = {
                                'original_english': result.original_english,
                                'components_used': result.components_used,
                                'method_used': result.method_used,
                                'warnings': result.warnings
                            }
                            person.save(update_fields=[
                                'khmer_name',
                                'khmer_name_source',
                                'khmer_name_confidence',
                                'khmer_name_approximated_at',
                                'khmer_name_components'
                            ])

                    results['approximated'] += 1

                    # Store example for report
                    if len(results['examples']) < 10:
                        results['examples'].append({
                            'id': person.id,
                            'english_name': result.original_english,
                            'khmer_name': result.display_name,
                            'confidence': result.confidence_score,
                            'method': result.method_used
                        })

                    self.logger.info(
                        f"✅ ID {person.id}: {result.original_english} → {result.display_name} "
                        f"(confidence: {result.confidence_score:.2f})"
                    )

                else:
                    results['skipped'] += 1
                    self.logger.debug(
                        f"⏭️  ID {person.id}: {result.original_english} "
                        f"skipped (confidence: {result.confidence_score:.2f} < {confidence_threshold})"
                    )

            except Exception as e:
                results['errors'] += 1
                self.logger.error(f"❌ ID {person.id}: Error approximating - {e}")

        return results

    def _create_result(self,
                      total_processed: int,
                      approximated: int,
                      skipped: int,
                      errors: int,
                      elapsed_time: float,
                      examples: List[Dict] = None) -> Dict[str, Any]:
        """Create standardized result dictionary."""
        return {
            'stage': 'khmer_name_approximation',
            'status': 'completed',
            'statistics': {
                'total_processed': total_processed,
                'approximated': approximated,
                'skipped': skipped,
                'errors': errors,
                'success_rate': (approximated / total_processed * 100) if total_processed > 0 else 0,
                'elapsed_time': elapsed_time
            },
            'examples': examples or [],
            'timestamp': timezone.now().isoformat()
        }

    def generate_report(self, results: Dict[str, Any]) -> str:
        """Generate human-readable report."""
        stats = results['statistics']
        examples = results.get('examples', [])

        report_lines = [
            "# Khmer Name Approximation Report",
            "",
            f"**Execution Time:** {stats['elapsed_time']:.2f} seconds",
            f"**Total Processed:** {stats['total_processed']} people",
            f"**Successfully Approximated:** {stats['approximated']} names",
            f"**Skipped (Low Confidence):** {stats['skipped']} names",
            f"**Errors:** {stats['errors']} records",
            f"**Success Rate:** {stats['success_rate']:.1f}%",
            "",
            "## Example Approximations",
            ""
        ]

        if examples:
            for example in examples:
                report_lines.append(
                    f"- **ID {example['id']}**: {example['english_name']} → {example['khmer_name']} "
                    f"(confidence: {example['confidence']:.2f}, method: {example['method']})"
                )
        else:
            report_lines.append("No examples available.")

        return "\n".join(report_lines)