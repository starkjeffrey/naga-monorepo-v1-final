"""Name decomposition service for breaking down compound Khmer names."""

import re
from typing import List
from dataclasses import dataclass


@dataclass
class NameComponent:
    """Represents a component of a decomposed name."""
    text: str
    position: int
    confidence: float
    is_prefix: bool = False
    is_suffix: bool = False


class NameDecomposer:
    """Decomposes compound Khmer names into their constituent components.

    This service analyzes English transliterations of Khmer names and breaks
    them down into individual components that can be looked up in the pattern
    dictionary for approximation.
    """

    # Common Khmer name prefixes and suffixes
    COMMON_PREFIXES = [
        'so', 'sam', 'chan', 'sok', 'phal', 'vi', 'sor', 'sim',
        'sun', 'sin', 'sus', 'sur', 'suy', 'som', 'sot', 'seng'
    ]

    COMMON_SUFFIXES = [
        'ny', 'ra', 'tha', 'thy', 'phy', 'vith', 'rith', 'roth',
        'nith', 'na', 'da', 'det', 'deth', 'neth', 'pich', 'vich'
    ]

    # Common compound patterns (first part, second part)
    KNOWN_COMPOUNDS = {
        'sovann': ['sov', 'ann'],
        'sovath': ['sov', 'ath'],
        'sovatth': ['sov', 'atth'],
        'chantha': ['chan', 'tha'],
        'chanthou': ['chan', 'thou'],
        'veasna': ['veas', 'na'],
        'pisach': ['pi', 'sach'],
        'piseth': ['pi', 'seth'],
        'bunroeun': ['bun', 'roeun'],
        'bunthoeun': ['bun', 'thoeun'],
        'rithy': ['ri', 'thy'],
        'rithea': ['ri', 'thea'],
        'makara': ['ma', 'kara'],
        'sopheak': ['so', 'pheak'],
        'sopheap': ['so', 'pheap'],
        'seanghai': ['seang', 'hai'],
        'sovannak': ['sovann', 'ak'],
        'sovannara': ['sovann', 'ara'],
        'somphors': ['som', 'phors'],
        'somphos': ['som', 'phos'],
    }

    # Syllable patterns in Cambodian names
    SYLLABLE_PATTERNS = [
        r'[aeiou]+[ng]',  # ang, ing, ong, etc.
        r'[aeiou]+[nh]',  # ah, ih, oh, etc.
        r'[bcdfghjklmnpqrstvwxyz][aeiou]+[bcdfghjklmnpqrstvwxyz]',  # CVC
        r'[bcdfghjklmnpqrstvwxyz][aeiou]+',  # CV
        r'[aeiou]+',  # V
    ]

    def __init__(self):
        """Initialize the name decomposer."""
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        self.syllable_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self.SYLLABLE_PATTERNS]

    def decompose(self, name: str) -> List[NameComponent]:
        """Decompose a name into its constituent components.

        Args:
            name: The name to decompose

        Returns:
            List of NameComponent objects representing the breakdown
        """
        if not name or not name.strip():
            return []

        # Normalize the name
        normalized_name = self._normalize_name(name)

        # Try known compound patterns first
        components = self._try_known_compounds(normalized_name)
        if components:
            return components

        # Try prefix/suffix decomposition
        components = self._try_prefix_suffix_decomposition(normalized_name)
        if len(components) > 1:
            return components

        # Use syllable-based decomposition as fallback
        components = self._syllable_decompose(normalized_name)

        # Validate and adjust components
        components = self._validate_components(components, normalized_name)

        return components

    def _normalize_name(self, name: str) -> str:
        """Normalize a name for processing."""
        # Convert to lowercase and remove extra spaces
        normalized = re.sub(r'\s+', '', name.lower().strip())

        # Remove common punctuation that might interfere
        normalized = re.sub(r'[^\w]', '', normalized)

        return normalized

    def _try_known_compounds(self, name: str) -> List[NameComponent]:
        """Try to match against known compound name patterns."""
        name_lower = name.lower()

        # Check exact matches first
        if name_lower in self.KNOWN_COMPOUNDS:
            parts = self.KNOWN_COMPOUNDS[name_lower]
            return [
                NameComponent(
                    text=part,
                    position=i,
                    confidence=0.95  # High confidence for known patterns
                )
                for i, part in enumerate(parts)
            ]

        # Check if name starts with any known compound
        for compound, parts in self.KNOWN_COMPOUNDS.items():
            if name_lower.startswith(compound):
                components = [
                    NameComponent(
                        text=compound,
                        position=0,
                        confidence=0.90
                    )
                ]

                # Handle remainder
                remainder = name_lower[len(compound):]
                if remainder:
                    components.append(
                        NameComponent(
                            text=remainder,
                            position=1,
                            confidence=0.70
                        )
                    )

                return components

        return []

    def _try_prefix_suffix_decomposition(self, name: str) -> List[NameComponent]:
        """Try to decompose using common prefixes and suffixes."""
        components = []
        remaining = name.lower()
        position = 0

        # Check for prefixes
        for prefix in sorted(self.COMMON_PREFIXES, key=len, reverse=True):
            if remaining.startswith(prefix) and len(remaining) > len(prefix):
                components.append(
                    NameComponent(
                        text=prefix,
                        position=position,
                        confidence=0.80,
                        is_prefix=True
                    )
                )
                remaining = remaining[len(prefix):]
                position += 1
                break

        # Check for suffixes
        for suffix in sorted(self.COMMON_SUFFIXES, key=len, reverse=True):
            if remaining.endswith(suffix) and len(remaining) > len(suffix):
                # Add the middle part first
                middle = remaining[:-len(suffix)]
                if middle:
                    components.append(
                        NameComponent(
                            text=middle,
                            position=position,
                            confidence=0.75
                        )
                    )
                    position += 1

                # Add the suffix
                components.append(
                    NameComponent(
                        text=suffix,
                        position=position,
                        confidence=0.80,
                        is_suffix=True
                    )
                )
                remaining = ''
                break

        # If there's still remaining text, add it as a component
        if remaining:
            components.append(
                NameComponent(
                    text=remaining,
                    position=position,
                    confidence=0.60
                )
            )

        return components

    def _syllable_decompose(self, name: str) -> List[NameComponent]:
        """Decompose name using syllable patterns."""
        components = []
        position = 0
        remaining = name.lower()

        # Simple heuristic: split on common vowel-consonant boundaries
        # This is a basic implementation that can be improved

        # Look for natural break points
        breaks = self._find_syllable_breaks(remaining)

        if not breaks:
            # Fallback: split roughly in half for long names
            if len(remaining) > 6:
                mid = len(remaining) // 2
                # Adjust to find a good break point near the middle
                for i in range(max(0, mid-2), min(len(remaining), mid+3)):
                    if i < len(remaining) - 1:
                        # Prefer breaks after vowels or before consonant clusters
                        if remaining[i] in 'aeiou' and remaining[i+1] not in 'aeiou':
                            mid = i + 1
                            break

                return [
                    NameComponent(text=remaining[:mid], position=0, confidence=0.50),
                    NameComponent(text=remaining[mid:], position=1, confidence=0.50)
                ]
            else:
                # Short name, treat as single component
                return [NameComponent(text=remaining, position=0, confidence=0.60)]

        # Use found breaks to create components
        last_pos = 0
        for i, break_pos in enumerate(breaks + [len(remaining)]):
            if break_pos > last_pos:
                component_text = remaining[last_pos:break_pos]
                if component_text:  # Don't add empty components
                    components.append(
                        NameComponent(
                            text=component_text,
                            position=i,
                            confidence=0.65
                        )
                    )
                last_pos = break_pos

        return components

    def _find_syllable_breaks(self, text: str) -> List[int]:
        """Find potential syllable break points in the text."""
        breaks = []

        # Look for vowel-consonant and consonant-vowel boundaries
        for i in range(1, len(text)):
            prev_char = text[i-1]
            curr_char = text[i]

            # Vowel followed by consonant
            if prev_char in 'aeiou' and curr_char not in 'aeiou':
                # Don't break if it would create very short segments
                if i > 2 and len(text) - i > 2:
                    breaks.append(i)

            # Double consonants
            elif prev_char == curr_char and prev_char not in 'aeiou':
                if i > 2 and len(text) - i > 2:
                    breaks.append(i)

        return breaks

    def _validate_components(self, components: List[NameComponent], original_name: str) -> List[NameComponent]:
        """Validate and adjust components for quality."""
        if not components:
            # Fallback: return the original name as a single component
            return [NameComponent(text=original_name.lower(), position=0, confidence=0.30)]

        # Filter out very short components (unless they're known prefixes/suffixes)
        validated = []
        for comp in components:
            if (len(comp.text) >= 2 or
                comp.is_prefix or
                comp.is_suffix or
                len(components) == 1):
                validated.append(comp)
            else:
                # Merge short component with adjacent one
                if validated:
                    last_comp = validated[-1]
                    validated[-1] = NameComponent(
                        text=last_comp.text + comp.text,
                        position=last_comp.position,
                        confidence=min(last_comp.confidence, comp.confidence)
                    )
                else:
                    validated.append(comp)

        # Ensure we have at least one component
        if not validated:
            validated = [NameComponent(text=original_name.lower(), position=0, confidence=0.30)]

        return validated

    def get_decomposition_confidence(self, components: List[NameComponent]) -> float:
        """Calculate overall confidence in the decomposition."""
        if not components:
            return 0.0

        # Average confidence weighted by component length
        total_weight = sum(len(comp.text) for comp in components)
        if total_weight == 0:
            return 0.0

        weighted_confidence = sum(
            comp.confidence * len(comp.text)
            for comp in components
        )

        return weighted_confidence / total_weight

    def analyze_name_structure(self, name: str) -> dict:
        """Analyze the structure of a name for debugging/reporting."""
        components = self.decompose(name)

        return {
            'original_name': name,
            'normalized_name': self._normalize_name(name),
            'component_count': len(components),
            'components': [
                {
                    'text': comp.text,
                    'position': comp.position,
                    'confidence': comp.confidence,
                    'is_prefix': comp.is_prefix,
                    'is_suffix': comp.is_suffix,
                    'length': len(comp.text)
                }
                for comp in components
            ],
            'overall_confidence': self.get_decomposition_confidence(components),
            'total_length': len(name),
            'contains_known_patterns': any(
                name.lower().find(compound) >= 0
                for compound in self.KNOWN_COMPOUNDS.keys()
            )
        }