"""Khmer name approximation engine with confidence scoring."""

import logging
from typing import Tuple, List, Optional, Dict
from dataclasses import dataclass
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from apps.people.models import Person, KhmerNamePattern
from apps.people.services.name_decomposer import NameDecomposer, NameComponent
from apps.common.utils.limon_to_unicode import limon_to_unicode_conversion


logger = logging.getLogger(__name__)


@dataclass
class ApproximationResult:
    """Result of a name approximation operation."""
    original_english: str
    approximated_khmer: str
    confidence_score: float
    components_used: List[Dict]
    method_used: str
    is_approximation: bool
    warnings: List[str]

    @property
    def display_name(self) -> str:
        """Get the display version of the approximated name."""
        if self.is_approximation and not self.approximated_khmer.startswith('* '):
            return f"* {self.approximated_khmer}"
        return self.approximated_khmer


class KhmerNameApproximator:
    """Approximates Khmer names based on frequency patterns.

    This service uses the pattern dictionary built from existing data
    to intelligently guess Khmer names for students who don't have them.
    """

    def __init__(self):
        """Initialize the approximator."""
        self.decomposer = NameDecomposer()
        self.pattern_cache = {}
        self._cache_timestamp = None
        self._cache_ttl = 3600  # 1 hour cache TTL

    def approximate_name(self, english_name: str) -> ApproximationResult:
        """Approximate a Khmer name from an English name.

        Args:
            english_name: The English name to approximate

        Returns:
            ApproximationResult with the approximation and metadata
        """
        if not english_name or not english_name.strip():
            return ApproximationResult(
                original_english="",
                approximated_khmer="",
                confidence_score=0.0,
                components_used=[],
                method_used="empty_input",
                is_approximation=False,
                warnings=["Empty or blank name provided"]
            )

        logger.debug(f"Approximating Khmer name for: {english_name}")

        # Normalize and decompose the name
        normalized_name = self._normalize_english_name(english_name)
        components = self.decomposer.decompose(normalized_name)

        if not components:
            return self._create_fallback_result(english_name, "decomposition_failed")

        # Try different approximation methods in order of preference
        methods = [
            self._try_exact_pattern_match,
            self._try_component_based_approximation,
            self._try_fuzzy_matching,
            self._try_transliteration_fallback
        ]

        for method in methods:
            try:
                result = method(english_name, normalized_name, components)
                if result and result.confidence_score > 0.3:  # Minimum acceptable confidence
                    return result
            except Exception as e:
                logger.warning(f"Error in approximation method {method.__name__}: {e}")
                continue

        # If all methods fail, return a fallback result
        return self._create_fallback_result(english_name, "all_methods_failed")

    def _normalize_english_name(self, name: str) -> str:
        """Normalize English name for processing."""
        import re
        # Remove extra spaces and convert to lowercase
        normalized = re.sub(r'\s+', ' ', name.strip().lower())
        # Remove common prefixes/suffixes that don't affect Khmer
        normalized = re.sub(r'\b(mr|mrs|ms|dr|prof)\.?\s*', '', normalized)
        return normalized

    def _try_exact_pattern_match(self, original: str, normalized: str, components: List[NameComponent]) -> Optional[ApproximationResult]:
        """Try to find an exact pattern match for the full name."""
        # Check if we have a pattern for the full normalized name
        pattern = self._get_best_pattern(normalized)

        if pattern and pattern.confidence_score >= 0.8:
            return ApproximationResult(
                original_english=original,
                approximated_khmer=pattern.unicode_pattern,
                confidence_score=float(pattern.confidence_score),
                components_used=[{
                    'text': normalized,
                    'pattern': pattern.unicode_pattern,
                    'confidence': float(pattern.confidence_score),
                    'method': 'exact_match'
                }],
                method_used="exact_pattern_match",
                is_approximation=True,
                warnings=[]
            )

        return None

    def _try_component_based_approximation(self, original: str, normalized: str, components: List[NameComponent]) -> Optional[ApproximationResult]:
        """Try to approximate by combining component patterns."""
        if len(components) == 1:
            # Single component - try direct lookup
            component = components[0]
            pattern = self._get_best_pattern(component.text)

            if pattern:
                return ApproximationResult(
                    original_english=original,
                    approximated_khmer=pattern.unicode_pattern,
                    confidence_score=float(pattern.confidence_score) * component.confidence,
                    components_used=[{
                        'text': component.text,
                        'pattern': pattern.unicode_pattern,
                        'confidence': float(pattern.confidence_score),
                        'method': 'single_component'
                    }],
                    method_used="single_component",
                    is_approximation=True,
                    warnings=[]
                )

        elif len(components) > 1:
            # Multiple components - combine patterns
            return self._combine_component_patterns(original, components)

        return None

    def _combine_component_patterns(self, original: str, components: List[NameComponent]) -> Optional[ApproximationResult]:
        """Combine patterns from multiple components."""
        combined_khmer = ""
        total_confidence = 1.0
        components_used = []
        warnings = []
        found_patterns = 0

        for component in components:
            pattern = self._get_best_pattern(component.text)

            if pattern:
                # Use the pattern
                combined_khmer += pattern.unicode_pattern
                total_confidence *= float(pattern.confidence_score) * component.confidence
                components_used.append({
                    'text': component.text,
                    'pattern': pattern.unicode_pattern,
                    'confidence': float(pattern.confidence_score),
                    'method': 'pattern_lookup'
                })
                found_patterns += 1
            else:
                # No pattern found - use transliteration
                transliterated = self._transliterate_component(component.text)
                combined_khmer += transliterated
                total_confidence *= 0.3  # Low confidence for transliteration
                components_used.append({
                    'text': component.text,
                    'pattern': transliterated,
                    'confidence': 0.3,
                    'method': 'transliteration'
                })
                warnings.append(f"No pattern found for component '{component.text}', used transliteration")

        if not combined_khmer:
            return None

        # Adjust confidence based on how many patterns we found
        pattern_ratio = found_patterns / len(components) if components else 0
        final_confidence = total_confidence * pattern_ratio

        return ApproximationResult(
            original_english=original,
            approximated_khmer=combined_khmer,
            confidence_score=final_confidence,
            components_used=components_used,
            method_used="component_combination",
            is_approximation=True,
            warnings=warnings
        )

    def _try_fuzzy_matching(self, original: str, normalized: str, components: List[NameComponent]) -> Optional[ApproximationResult]:
        """Try fuzzy matching against known patterns."""
        from difflib import SequenceMatcher

        best_pattern = None
        best_similarity = 0.0
        search_terms = [normalized] + [comp.text for comp in components]

        for search_term in search_terms:
            if len(search_term) < 3:  # Skip very short terms
                continue

            # Get patterns with similar components
            similar_patterns = KhmerNamePattern.objects.filter(
                Q(english_component__icontains=search_term[:3]) |
                Q(english_component__startswith=search_term[:2])
            ).filter(
                confidence_score__gte=0.6
            ).order_by('-confidence_score')[:10]

            for pattern in similar_patterns:
                similarity = SequenceMatcher(None, search_term, pattern.english_component).ratio()

                if similarity > best_similarity and similarity >= 0.7:
                    best_pattern = pattern
                    best_similarity = similarity

        if best_pattern and best_similarity >= 0.7:
            confidence = float(best_pattern.confidence_score) * best_similarity * 0.8  # Penalty for fuzzy match

            return ApproximationResult(
                original_english=original,
                approximated_khmer=best_pattern.unicode_pattern,
                confidence_score=confidence,
                components_used=[{
                    'text': normalized,
                    'pattern': best_pattern.unicode_pattern,
                    'confidence': confidence,
                    'method': 'fuzzy_match',
                    'similarity': best_similarity
                }],
                method_used="fuzzy_matching",
                is_approximation=True,
                warnings=[f"Used fuzzy matching with {best_similarity:.2f} similarity"]
            )

        return None

    def _try_transliteration_fallback(self, original: str, normalized: str, components: List[NameComponent]) -> Optional[ApproximationResult]:
        """Fallback to basic transliteration."""
        transliterated = self._transliterate_component(normalized)

        if transliterated:
            return ApproximationResult(
                original_english=original,
                approximated_khmer=transliterated,
                confidence_score=0.3,  # Low confidence for pure transliteration
                components_used=[{
                    'text': normalized,
                    'pattern': transliterated,
                    'confidence': 0.3,
                    'method': 'transliteration'
                }],
                method_used="transliteration_fallback",
                is_approximation=True,
                warnings=["No patterns found, used basic transliteration"]
            )

        return None

    def _get_best_pattern(self, component: str) -> Optional[KhmerNamePattern]:
        """Get the best pattern for a component."""
        # Check cache first
        if self._should_refresh_cache():
            self._refresh_pattern_cache()

        cache_key = component.lower().strip()
        if cache_key in self.pattern_cache:
            return self.pattern_cache[cache_key]

        # Not in cache - query database
        patterns = KhmerNamePattern.objects.filter(
            Q(english_component__iexact=component) |
            Q(normalized_component__iexact=component.lower())
        ).order_by('-frequency', '-confidence_score')

        best_pattern = patterns.first()
        if best_pattern:
            self.pattern_cache[cache_key] = best_pattern

        return best_pattern

    def _should_refresh_cache(self) -> bool:
        """Check if pattern cache needs refresh."""
        if not self._cache_timestamp:
            return True

        age = (timezone.now() - self._cache_timestamp).seconds
        return age > self._cache_ttl

    def _refresh_pattern_cache(self) -> None:
        """Refresh the pattern cache from database."""
        logger.debug("Refreshing pattern cache")

        # Load high-confidence patterns into cache
        patterns = KhmerNamePattern.objects.filter(
            confidence_score__gte=0.5
        ).order_by('-frequency', '-confidence_score')[:1000]  # Limit cache size

        self.pattern_cache = {}
        for pattern in patterns:
            self.pattern_cache[pattern.normalized_component] = pattern

        self._cache_timestamp = timezone.now()
        logger.debug(f"Loaded {len(self.pattern_cache)} patterns into cache")

    def _transliterate_component(self, component: str) -> str:
        """Basic transliteration fallback for unknown components."""
        # This is a very basic transliteration
        # In practice, you'd want a more sophisticated system
        transliteration_map = {
            'a': 'អ', 'b': 'ប', 'c': 'ច', 'd': 'ដ', 'e': 'ឯ',
            'f': 'ផ', 'g': 'គ', 'h': 'ហ', 'i': 'ឥ', 'j': 'ជ',
            'k': 'ក', 'l': 'ល', 'm': 'ម', 'n': 'ន', 'o': 'ឱ',
            'p': 'ព', 'q': 'គ', 'r': 'រ', 's': 'ស', 't': 'ត',
            'u': 'ឧ', 'v': 'វ', 'w': 'វ', 'x': 'ខ', 'y': 'យ', 'z': 'ស'
        }

        result = ""
        for char in component.lower():
            if char in transliteration_map:
                result += transliteration_map[char]
            elif char.isalpha():
                result += 'អ'  # Default for unknown letters

        return result

    def _create_fallback_result(self, original: str, reason: str) -> ApproximationResult:
        """Create a fallback result when approximation fails."""
        return ApproximationResult(
            original_english=original,
            approximated_khmer="",
            confidence_score=0.0,
            components_used=[],
            method_used="fallback",
            is_approximation=False,
            warnings=[f"Approximation failed: {reason}"]
        )

    def approximate_for_person(self, person: Person) -> ApproximationResult:
        """Approximate Khmer name for a specific person."""
        english_name = f"{person.family_name} {person.personal_name}".strip()
        return self.approximate_name(english_name)

    def batch_approximate(self, person_ids: List[int], confidence_threshold: float = 0.5) -> List[Dict]:
        """Batch approximate Khmer names for multiple people.

        Args:
            person_ids: List of person IDs to process
            confidence_threshold: Minimum confidence to apply approximation

        Returns:
            List of results with person ID and approximation data
        """
        results = []

        people = Person.objects.filter(
            id__in=person_ids,
            khmer_name_source__in=['legacy', '']
        ).filter(
            Q(khmer_name__isnull=True) | Q(khmer_name__exact='')
        )

        for person in people:
            try:
                result = self.approximate_for_person(person)

                if result.confidence_score >= confidence_threshold:
                    # Apply the approximation
                    person.khmer_name = result.display_name
                    person.khmer_name_source = 'approximated'
                    person.khmer_name_confidence = Decimal(str(result.confidence_score))
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

                    results.append({
                        'person_id': person.id,
                        'status': 'approximated',
                        'english_name': result.original_english,
                        'khmer_name': result.display_name,
                        'confidence': result.confidence_score,
                        'method': result.method_used
                    })
                else:
                    results.append({
                        'person_id': person.id,
                        'status': 'skipped_low_confidence',
                        'english_name': result.original_english,
                        'confidence': result.confidence_score,
                        'method': result.method_used
                    })

            except Exception as e:
                logger.error(f"Error approximating name for person {person.id}: {e}")
                results.append({
                    'person_id': person.id,
                    'status': 'error',
                    'error': str(e)
                })

        return results

    def get_approximation_stats(self) -> Dict:
        """Get statistics about approximated names."""
        from django.db.models import Count, Avg

        stats = Person.objects.aggregate(
            total_people=Count('id'),
            with_khmer_names=Count('id', filter=Q(khmer_name__isnull=False) & ~Q(khmer_name__exact='')),
            approximated=Count('id', filter=Q(khmer_name_source='approximated')),
            user_provided=Count('id', filter=Q(khmer_name_source='user')),
            verified=Count('id', filter=Q(khmer_name_source='verified')),
            avg_confidence=Avg('khmer_name_confidence', filter=Q(khmer_name_source='approximated'))
        )

        # Calculate coverage percentage
        total = stats['total_people'] or 1
        stats['coverage_percentage'] = (stats['with_khmer_names'] / total) * 100
        stats['approximation_percentage'] = (stats['approximated'] / total) * 100

        return stats

    def validate_approximation_quality(self, sample_size: int = 100) -> Dict:
        """Validate the quality of existing approximations."""
        # Get a sample of approximated names
        approximated_people = Person.objects.filter(
            khmer_name_source='approximated'
        ).order_by('?')[:sample_size]

        quality_metrics = {
            'sample_size': len(approximated_people),
            'high_confidence_count': 0,
            'medium_confidence_count': 0,
            'low_confidence_count': 0,
            'avg_confidence': 0.0,
            'method_distribution': {},
            'component_coverage': 0.0
        }

        total_confidence = 0.0
        method_counts = {}

        for person in approximated_people:
            confidence = float(person.khmer_name_confidence)
            total_confidence += confidence

            if confidence >= 0.8:
                quality_metrics['high_confidence_count'] += 1
            elif confidence >= 0.5:
                quality_metrics['medium_confidence_count'] += 1
            else:
                quality_metrics['low_confidence_count'] += 1

            # Track method distribution
            if person.khmer_name_components:
                method = person.khmer_name_components.get('method_used', 'unknown')
                method_counts[method] = method_counts.get(method, 0) + 1

        if len(approximated_people) > 0:
            quality_metrics['avg_confidence'] = total_confidence / len(approximated_people)

        quality_metrics['method_distribution'] = method_counts

        return quality_metrics