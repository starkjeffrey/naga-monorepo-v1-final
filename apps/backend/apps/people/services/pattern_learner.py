"""Pattern learning service for improving approximations based on user corrections."""

import logging
from typing import Dict, List, Tuple, Optional
from decimal import Decimal

from django.db import transaction

from apps.people.models import KhmerNamePattern, KhmerNameCorrection
from apps.people.services.name_decomposer import NameDecomposer


logger = logging.getLogger(__name__)


class PatternLearner:
    """Learns from user corrections to improve pattern accuracy.

    This service analyzes corrections submitted by users to extract new
    patterns and adjust confidence scores of existing patterns.
    """

    def __init__(self):
        """Initialize the pattern learner."""
        self.decomposer = NameDecomposer()

    def learn_from_correction(self, correction: KhmerNameCorrection) -> Dict:
        """Learn patterns from a user correction.

        Args:
            correction: The correction record to learn from

        Returns:
            Dictionary with learning results and new patterns
        """
        logger.info(f"Learning from correction for person {correction.person.id}")

        # Extract components from English and Khmer names
        english_name = correction.original_english_name or f"{correction.person.family_name} {correction.person.personal_name}"
        khmer_name = correction.corrected_khmer_name

        # Decompose English name
        english_components = self.decomposer.decompose(english_name)

        if not english_components:
            logger.warning(f"Could not decompose English name: {english_name}")
            return {'status': 'failed', 'reason': 'decomposition_failed'}

        # Extract patterns
        patterns_learned = []

        if len(english_components) == 1:
            # Simple case: one English component maps to full Khmer name
            pattern_data = self._learn_single_pattern(
                english_components[0].text,
                khmer_name,
                source='user_correction'
            )
            if pattern_data:
                patterns_learned.append(pattern_data)

        else:
            # Complex case: try to align multiple components with Khmer parts
            alignment_patterns = self._learn_aligned_patterns(
                english_components,
                khmer_name,
                correction
            )
            patterns_learned.extend(alignment_patterns)

        # Update confidence scores based on this correction
        self._adjust_confidence_scores(correction, patterns_learned)

        logger.info(f"Learned {len(patterns_learned)} patterns from correction")

        return {
            'status': 'success',
            'patterns_count': len(patterns_learned),
            'patterns': patterns_learned,
            'english_components': [comp.text for comp in english_components]
        }

    def _learn_single_pattern(self, english_component: str, khmer_name: str, source: str) -> Optional[Dict]:
        """Learn a pattern from a single English component to Khmer name mapping."""
        english_normalized = english_component.lower().strip()

        try:
            with transaction.atomic():
                # Check if pattern already exists
                existing_pattern = KhmerNamePattern.objects.filter(
                    english_component=english_normalized,
                    unicode_pattern=khmer_name
                ).first()

                if existing_pattern:
                    # Increment occurrence and update confidence
                    existing_pattern.add_occurrence()
                    existing_pattern.confidence_score = min(
                        existing_pattern.confidence_score + Decimal('0.05'),
                        Decimal('1.00')
                    )
                    existing_pattern.is_verified = True
                    existing_pattern.save()

                    return {
                        'english_component': english_normalized,
                        'khmer_pattern': khmer_name,
                        'action': 'updated_existing',
                        'new_confidence': float(existing_pattern.confidence_score),
                        'occurrence_count': existing_pattern.occurrence_count
                    }

                else:
                    # Create new pattern
                    new_pattern = KhmerNamePattern.objects.create(
                        english_component=english_normalized,
                        normalized_component=english_normalized,
                        limon_pattern=khmer_name,  # Using Khmer directly for now
                        unicode_pattern=khmer_name,
                        frequency=Decimal('1.00'),  # Will be recalculated
                        occurrence_count=1,
                        confidence_score=Decimal('0.85'),  # High confidence for user corrections
                        is_verified=True
                    )

                    # Recalculate frequencies for this component
                    self._recalculate_component_frequencies(english_normalized)

                    return {
                        'english_component': english_normalized,
                        'khmer_pattern': khmer_name,
                        'action': 'created_new',
                        'confidence': float(new_pattern.confidence_score),
                        'pattern_id': new_pattern.id
                    }

        except Exception as e:
            logger.error(f"Error learning pattern {english_normalized} -> {khmer_name}: {e}")
            return None

    def _learn_aligned_patterns(self, english_components: List, khmer_name: str, correction: KhmerNameCorrection) -> List[Dict]:
        """Learn patterns from aligned English components and Khmer name parts."""
        patterns = []

        # For now, use a simple heuristic approach
        # In a production system, you'd want more sophisticated alignment

        if len(english_components) == 2:
            # Try to split Khmer name and align with English components
            khmer_parts = self._split_khmer_name(khmer_name, len(english_components))

            if len(khmer_parts) == len(english_components):
                for i, (eng_comp, khmer_part) in enumerate(zip(english_components, khmer_parts)):
                    pattern_data = self._learn_single_pattern(
                        eng_comp.text,
                        khmer_part,
                        source='aligned_correction'
                    )
                    if pattern_data:
                        pattern_data['alignment_position'] = i
                        patterns.append(pattern_data)

        # If alignment fails, learn the whole thing as one pattern
        if not patterns and len(english_components) > 0:
            # Use the longest/most significant component
            main_component = max(english_components, key=lambda c: len(c.text))
            pattern_data = self._learn_single_pattern(
                main_component.text,
                khmer_name,
                source='fallback_whole_name'
            )
            if pattern_data:
                patterns.append(pattern_data)

        return patterns

    def _split_khmer_name(self, khmer_name: str, target_parts: int) -> List[str]:
        """Attempt to split a Khmer name into the target number of parts."""
        # This is a heuristic approach - real implementation would need
        # proper Khmer script analysis

        if target_parts <= 1:
            return [khmer_name]

        # Simple approach: split roughly equally
        name_length = len(khmer_name)
        part_length = name_length // target_parts
        parts = []

        for i in range(target_parts - 1):
            start = i * part_length
            end = start + part_length
            parts.append(khmer_name[start:end])

        # Last part gets the remainder
        parts.append(khmer_name[(target_parts - 1) * part_length:])

        # Filter out empty parts
        parts = [part for part in parts if part.strip()]

        return parts

    def _recalculate_component_frequencies(self, english_component: str) -> None:
        """Recalculate frequencies for all patterns of a component."""
        patterns = KhmerNamePattern.objects.filter(
            english_component=english_component
        )

        total_occurrences = sum(p.occurrence_count for p in patterns)

        if total_occurrences > 0:
            for pattern in patterns:
                new_frequency = Decimal(pattern.occurrence_count) / Decimal(total_occurrences)
                pattern.frequency = new_frequency
                pattern.save(update_fields=['frequency'])

    def _adjust_confidence_scores(self, correction: KhmerNameCorrection, patterns_learned: List[Dict]) -> None:
        """Adjust confidence scores based on the correction context."""
        # If the original name was approximated and user corrected it,
        # we might need to penalize the patterns that led to the wrong approximation

        if correction.original_khmer_name and correction.original_khmer_name.startswith('* '):
            # This was an approximated name that was corrected
            # We can try to identify and penalize the patterns that were used

            original_components = correction.person.khmer_name_components
            if original_components and 'components_used' in original_components:
                self._penalize_incorrect_patterns(original_components['components_used'])

    def _penalize_incorrect_patterns(self, components_used: List[Dict]) -> None:
        """Penalize patterns that led to incorrect approximations."""
        for component_data in components_used:
            if component_data.get('method') == 'pattern_lookup':
                english_text = component_data.get('text')
                pattern_text = component_data.get('pattern')

                if english_text and pattern_text:
                    # Find and penalize the pattern
                    patterns = KhmerNamePattern.objects.filter(
                        english_component=english_text,
                        unicode_pattern=pattern_text
                    )

                    for pattern in patterns:
                        # Reduce confidence slightly
                        new_confidence = max(
                            pattern.confidence_score - Decimal('0.02'),
                            Decimal('0.10')  # Don't go below minimum
                        )
                        pattern.confidence_score = new_confidence
                        pattern.save(update_fields=['confidence_score'])

                        logger.debug(f"Penalized pattern {english_text} -> {pattern_text}")

    def bulk_learn_from_corrections(self, correction_ids: List[int]) -> Dict:
        """Learn from multiple corrections in batch."""
        corrections = KhmerNameCorrection.objects.filter(
            id__in=correction_ids,
            patterns_learned__isnull=True  # Only process corrections we haven't learned from
        )

        total_patterns = 0
        successful_corrections = 0
        failed_corrections = 0

        for correction in corrections:
            try:
                result = self.learn_from_correction(correction)
                if result['status'] == 'success':
                    total_patterns += result['patterns_count']
                    successful_corrections += 1
                else:
                    failed_corrections += 1

            except Exception as e:
                logger.error(f"Error learning from correction {correction.id}: {e}")
                failed_corrections += 1

        return {
            'total_corrections_processed': len(corrections),
            'successful_corrections': successful_corrections,
            'failed_corrections': failed_corrections,
            'total_patterns_learned': total_patterns
        }

    def analyze_correction_patterns(self) -> Dict:
        """Analyze patterns in user corrections to identify trends."""
        from django.db.models import Count

        corrections = KhmerNameCorrection.objects.filter(
            patterns_learned__isnull=False
        )

        # Analyze correction frequency by source
        source_stats = corrections.values('correction_source').annotate(
            count=Count('id')
        ).order_by('-count')

        # Analyze most commonly corrected components
        component_corrections = {}
        for correction in corrections:
            if correction.patterns_learned and 'english_components' in correction.patterns_learned:
                for component in correction.patterns_learned['english_components']:
                    component_corrections[component] = component_corrections.get(component, 0) + 1

        top_corrected_components = sorted(
            component_corrections.items(),
            key=lambda x: x[1],
            reverse=True
        )[:20]

        return {
            'total_corrections_analyzed': corrections.count(),
            'correction_sources': list(source_stats),
            'top_corrected_components': top_corrected_components,
            'avg_patterns_per_correction': sum(
                len(c.patterns_learned.get('patterns', []))
                for c in corrections
                if c.patterns_learned
            ) / max(corrections.count(), 1)
        }

    def suggest_pattern_improvements(self) -> List[Dict]:
        """Suggest improvements to existing patterns based on learning."""
        suggestions = []

        # Find patterns with low confidence that might need review
        low_confidence_patterns = KhmerNamePattern.objects.filter(
            confidence_score__lt=0.5,
            occurrence_count__gte=3  # But have some usage
        ).order_by('confidence_score')[:20]

        for pattern in low_confidence_patterns:
            suggestions.append({
                'type': 'low_confidence_review',
                'pattern_id': pattern.id,
                'english_component': pattern.english_component,
                'unicode_pattern': pattern.unicode_pattern,
                'confidence': float(pattern.confidence_score),
                'occurrence_count': pattern.occurrence_count,
                'suggestion': 'Review this pattern - low confidence but multiple uses'
            })

        # Find components with multiple competing patterns
        competing_patterns = self._find_competing_patterns()
        for comp_data in competing_patterns:
            suggestions.append({
                'type': 'competing_patterns',
                'english_component': comp_data['component'],
                'pattern_count': comp_data['pattern_count'],
                'top_patterns': comp_data['top_patterns'],
                'suggestion': 'Multiple patterns exist - consider consolidation'
            })

        return suggestions

    def _find_competing_patterns(self) -> List[Dict]:
        """Find components that have multiple competing patterns."""
        from django.db.models import Count

        # Find components with multiple high-confidence patterns
        components_with_multiple = KhmerNamePattern.objects.values(
            'english_component'
        ).annotate(
            pattern_count=Count('id')
        ).filter(
            pattern_count__gte=2
        ).order_by('-pattern_count')

        competing = []
        for comp_data in components_with_multiple[:10]:  # Top 10
            component = comp_data['english_component']
            patterns = KhmerNamePattern.objects.filter(
                english_component=component,
                confidence_score__gte=0.5
            ).order_by('-confidence_score')[:3]

            if len(patterns) >= 2:
                competing.append({
                    'component': component,
                    'pattern_count': comp_data['pattern_count'],
                    'top_patterns': [
                        {
                            'unicode': p.unicode_pattern,
                            'confidence': float(p.confidence_score),
                            'frequency': float(p.frequency)
                        }
                        for p in patterns
                    ]
                })

        return competing