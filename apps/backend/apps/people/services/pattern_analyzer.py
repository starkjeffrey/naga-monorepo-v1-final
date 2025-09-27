"""Pattern analysis service for extracting Khmer name patterns from existing data."""

import logging
from collections import defaultdict
from typing import Dict, List, Tuple, Optional
from decimal import Decimal

from django.db.models import QuerySet
from django.db import transaction

from apps.people.models import Person, KhmerNamePattern
from apps.people.services.name_decomposer import NameDecomposer
from apps.common.utils.limon_to_unicode import limon_to_unicode_conversion


logger = logging.getLogger(__name__)


class PatternAnalyzer:
    """Analyzes existing Khmer names to extract common patterns.

    This service examines the relationship between English names and their
    Khmer counterparts to build a frequency-based pattern dictionary.
    """

    def __init__(self):
        """Initialize the pattern analyzer."""
        self.decomposer = NameDecomposer()
        self.pattern_stats = defaultdict(lambda: defaultdict(int))
        self.analysis_results = {}

    def analyze_existing_names(self, batch_size: int = 1000) -> Dict:
        """Analyze all existing Khmer names to extract patterns.

        Args:
            batch_size: Number of records to process at once

        Returns:
            Dictionary with analysis results and statistics
        """
        logger.info("Starting analysis of existing Khmer names")

        # Get all people with both English and Khmer names
        people_with_khmer = Person.objects.exclude(
            khmer_name__isnull=True
        ).exclude(
            khmer_name__exact=''
        ).exclude(
            khmer_name__startswith='*'  # Skip already approximated names
        ).select_related()

        total_count = people_with_khmer.count()
        logger.info(f"Found {total_count} people with Khmer names to analyze")

        if total_count == 0:
            return self._create_empty_results()

        # Process in batches to avoid memory issues
        processed_count = 0
        pattern_map = defaultdict(lambda: defaultdict(int))
        unicode_map = defaultdict(str)  # Store unicode representations

        for batch_start in range(0, total_count, batch_size):
            batch_end = min(batch_start + batch_size, total_count)
            batch = people_with_khmer[batch_start:batch_end]

            logger.info(f"Processing batch {batch_start}-{batch_end}")

            for person in batch:
                try:
                    patterns = self._extract_patterns_from_person(person)
                    for english_comp, limon_pattern, unicode_pattern in patterns:
                        pattern_map[english_comp][limon_pattern] += 1
                        unicode_map[f"{english_comp}|{limon_pattern}"] = unicode_pattern

                    processed_count += 1

                except Exception as e:
                    logger.warning(f"Error processing person {person.id}: {e}")
                    continue

        logger.info(f"Processed {processed_count} people, found patterns for {len(pattern_map)} components")

        # Calculate frequencies and create results
        results = self._calculate_frequencies(pattern_map, unicode_map)
        results['processed_count'] = processed_count
        results['total_people'] = total_count

        self.analysis_results = results
        return results

    def _extract_patterns_from_person(self, person: Person) -> List[Tuple[str, str, str]]:
        """Extract patterns from a single person's name data.

        Args:
            person: Person object to analyze

        Returns:
            List of (english_component, limon_pattern, unicode_pattern) tuples
        """
        english_name = f"{person.family_name} {person.personal_name}".strip()
        khmer_name = person.khmer_name.strip()

        if not english_name or not khmer_name:
            return []

        # Decompose the English name
        components = self.decomposer.decompose(english_name)

        if not components:
            return []

        patterns = []

        # For now, use a simple approach: if there's one component, map it to the full Khmer name
        # For multiple components, we'll need more sophisticated alignment
        if len(components) == 1:
            # Single component maps to full Khmer name
            english_comp = components[0].text.lower()
            unicode_pattern = khmer_name
            limon_pattern = self._extract_limon_from_unicode(unicode_pattern)

            if limon_pattern:
                patterns.append((english_comp, limon_pattern, unicode_pattern))

        else:
            # Multiple components - try to extract patterns using heuristics
            patterns.extend(self._extract_multi_component_patterns(components, khmer_name))

        return patterns

    def _extract_limon_from_unicode(self, unicode_khmer: str) -> Optional[str]:
        """Attempt to reverse-engineer LIMON from Unicode Khmer.

        This is a heuristic approach since we don't have the original LIMON.
        """
        # For now, we'll use the unicode as a "pattern" identifier
        # In a real implementation, you might try to reverse the conversion
        # or use the unicode directly as the pattern
        return unicode_khmer  # Simplified approach

    def _extract_multi_component_patterns(self, components: List, khmer_name: str) -> List[Tuple[str, str, str]]:
        """Extract patterns when English name has multiple components.

        This is a complex alignment problem. For now, we use simple heuristics.
        """
        patterns = []

        # Simple approach: if we have 2 components, try to split the Khmer name
        if len(components) == 2:
            # Look for natural break points in the Khmer name
            mid_point = len(khmer_name) // 2

            # Try to find a good split point near the middle
            for i in range(max(1, mid_point - 2), min(len(khmer_name), mid_point + 3)):
                # This is very simplified - in practice you'd need more sophisticated
                # Khmer script analysis
                first_part = khmer_name[:i]
                second_part = khmer_name[i:]

                if first_part and second_part:
                    patterns.append((
                        components[0].text.lower(),
                        first_part,
                        first_part
                    ))
                    patterns.append((
                        components[1].text.lower(),
                        second_part,
                        second_part
                    ))
                    break

        # For 3+ components, it gets more complex - skip for now
        # In a production system, you'd want more sophisticated alignment

        return patterns

    def _calculate_frequencies(self, pattern_map: Dict, unicode_map: Dict) -> Dict:
        """Calculate frequency statistics for patterns."""
        results = {
            'patterns': {},
            'statistics': {
                'total_components': len(pattern_map),
                'total_patterns': 0,
                'avg_patterns_per_component': 0
            }
        }

        total_patterns = 0

        for english_comp, limon_patterns in pattern_map.items():
            total_occurrences = sum(limon_patterns.values())
            component_patterns = {}

            for limon_pattern, count in limon_patterns.items():
                frequency = count / total_occurrences
                unicode_key = f"{english_comp}|{limon_pattern}"
                unicode_pattern = unicode_map.get(unicode_key, limon_pattern)

                component_patterns[limon_pattern] = {
                    'count': count,
                    'frequency': float(frequency),
                    'unicode': unicode_pattern,
                    'confidence': self._calculate_confidence(frequency, count)
                }
                total_patterns += 1

            # Sort by frequency (highest first)
            sorted_patterns = dict(
                sorted(component_patterns.items(), key=lambda x: x[1]['frequency'], reverse=True)
            )

            results['patterns'][english_comp] = {
                'total_occurrences': total_occurrences,
                'pattern_count': len(sorted_patterns),
                'patterns': sorted_patterns,
                'most_common': list(sorted_patterns.keys())[0] if sorted_patterns else None
            }

        results['statistics']['total_patterns'] = total_patterns
        if len(pattern_map) > 0:
            results['statistics']['avg_patterns_per_component'] = total_patterns / len(pattern_map)

        return results

    def _calculate_confidence(self, frequency: float, count: int) -> float:
        """Calculate confidence score for a pattern."""
        # Base confidence on frequency and absolute count
        frequency_score = frequency  # 0.0 to 1.0
        count_score = min(count / 20.0, 1.0)  # Max confidence at 20+ occurrences

        # Weighted average (frequency is more important)
        confidence = (0.7 * frequency_score) + (0.3 * count_score)
        return min(confidence, 1.0)

    def save_patterns_to_database(self, min_confidence: float = 0.5, min_count: int = 2) -> int:
        """Save analyzed patterns to the database.

        Args:
            min_confidence: Minimum confidence score to save
            min_count: Minimum occurrence count to save

        Returns:
            Number of patterns saved
        """
        if not self.analysis_results:
            logger.warning("No analysis results available. Run analyze_existing_names() first.")
            return 0

        patterns_saved = 0

        with transaction.atomic():
            for english_comp, comp_data in self.analysis_results['patterns'].items():
                for limon_pattern, pattern_data in comp_data['patterns'].items():
                    if (pattern_data['confidence'] >= min_confidence and
                        pattern_data['count'] >= min_count):

                        # Create or update pattern
                        pattern, created = KhmerNamePattern.objects.update_or_create(
                            english_component=english_comp,
                            limon_pattern=limon_pattern,
                            defaults={
                                'normalized_component': english_comp.lower(),
                                'unicode_pattern': pattern_data['unicode'],
                                'frequency': Decimal(str(pattern_data['frequency'])),
                                'occurrence_count': pattern_data['count'],
                                'confidence_score': Decimal(str(pattern_data['confidence'])),
                                'is_verified': False  # Will be verified manually or through corrections
                            }
                        )

                        if created:
                            patterns_saved += 1
                            logger.debug(f"Created pattern: {english_comp} → {pattern_data['unicode']}")
                        else:
                            logger.debug(f"Updated pattern: {english_comp} → {pattern_data['unicode']}")

        logger.info(f"Saved {patterns_saved} new patterns to database")
        return patterns_saved

    def generate_analysis_report(self) -> str:
        """Generate a human-readable analysis report."""
        if not self.analysis_results:
            return "No analysis results available. Run analyze_existing_names() first."

        report_lines = [
            "# Khmer Name Pattern Analysis Report",
            "",
            f"## Summary",
            f"- Total people processed: {self.analysis_results.get('processed_count', 0)}",
            f"- Total components found: {self.analysis_results['statistics']['total_components']}",
            f"- Total patterns extracted: {self.analysis_results['statistics']['total_patterns']}",
            f"- Average patterns per component: {self.analysis_results['statistics']['avg_patterns_per_component']:.2f}",
            "",
            "## Top Components by Frequency",
            ""
        ]

        # Sort components by total occurrences
        sorted_components = sorted(
            self.analysis_results['patterns'].items(),
            key=lambda x: x[1]['total_occurrences'],
            reverse=True
        )

        for english_comp, comp_data in sorted_components[:20]:  # Top 20
            most_common_pattern = comp_data['patterns'].get(comp_data['most_common'], {})
            report_lines.extend([
                f"### {english_comp}",
                f"- Total occurrences: {comp_data['total_occurrences']}",
                f"- Pattern variations: {comp_data['pattern_count']}",
                f"- Most common: {comp_data['most_common']} (freq: {most_common_pattern.get('frequency', 0):.2f})",
                f"- Unicode: {most_common_pattern.get('unicode', 'N/A')}",
                ""
            ])

        return "\n".join(report_lines)

    def _create_empty_results(self) -> Dict:
        """Create empty results structure when no data is available."""
        return {
            'patterns': {},
            'statistics': {
                'total_components': 0,
                'total_patterns': 0,
                'avg_patterns_per_component': 0
            },
            'processed_count': 0,
            'total_people': 0
        }

    def get_pattern_recommendations(self, english_component: str) -> List[Dict]:
        """Get pattern recommendations for a specific English component."""
        if not self.analysis_results:
            return []

        component_data = self.analysis_results['patterns'].get(english_component.lower())
        if not component_data:
            return []

        recommendations = []
        for limon_pattern, pattern_data in component_data['patterns'].items():
            recommendations.append({
                'limon_pattern': limon_pattern,
                'unicode_pattern': pattern_data['unicode'],
                'frequency': pattern_data['frequency'],
                'confidence': pattern_data['confidence'],
                'count': pattern_data['count']
            })

        return recommendations

    def validate_pattern_quality(self) -> Dict:
        """Validate the quality of extracted patterns."""
        if not self.analysis_results:
            return {'error': 'No analysis results available'}

        total_patterns = self.analysis_results['statistics']['total_patterns']
        high_confidence_count = 0
        medium_confidence_count = 0
        low_confidence_count = 0

        for comp_data in self.analysis_results['patterns'].values():
            for pattern_data in comp_data['patterns'].values():
                confidence = pattern_data['confidence']
                if confidence >= 0.8:
                    high_confidence_count += 1
                elif confidence >= 0.5:
                    medium_confidence_count += 1
                else:
                    low_confidence_count += 1

        return {
            'total_patterns': total_patterns,
            'high_confidence': high_confidence_count,
            'medium_confidence': medium_confidence_count,
            'low_confidence': low_confidence_count,
            'quality_score': (high_confidence_count + 0.5 * medium_confidence_count) / total_patterns if total_patterns > 0 else 0
        }