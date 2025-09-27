# Khmer Name Approximation System Design

## Executive Summary

This document outlines a comprehensive solution for improving Khmer name handling in the Naga SIS system. The current LIMON-to-Unicode conversion process produces unreliable results, leaving many students without proper Khmer names. This design proposes a frequency-based approximation system that will intelligently guess Khmer names based on common patterns until users can provide their correct names through the mobile app.

## Problem Statement

1. **Faulty Conversion**: The LIMON-to-Unicode converter doesn't always produce reliable output
2. **Missing Data**: Many students have no Khmer name in the database
3. **No Authoritative Source**: Unable to locate an authoritative LIMON conversion table
4. **User Impact**: Students cannot see their names properly displayed in Khmer

## Solution Overview

### Core Approach

Create an intelligent approximation system that:
1. Analyzes existing Khmer names to find common patterns
2. Builds a frequency dictionary of English name components to LIMON representations
3. Decomposes compound names into components (e.g., "Sovansomphors" → "Sovann" + "Somphors")
4. Approximates Khmer names using the most frequent LIMON patterns
5. Marks approximated names with an asterisk (e.g., "* សុវណ្ណសម្ផស្ស")
6. Allows users to provide correct names via mobile app

## System Architecture

### 1. Name Pattern Analyzer

Extracts and analyzes patterns from existing data:

```python
class NamePatternAnalyzer:
    """Analyzes existing Khmer names to extract common patterns."""

    def analyze_existing_names(self):
        """Extract patterns from database."""
        # Query all non-empty Khmer names
        # Decompose into components
        # Build frequency maps

    def identify_compound_patterns(self):
        """Identify how names are composed."""
        # Detect common prefixes/suffixes
        # Find recurring combinations
        # Map English variations to Khmer
```

### 2. Pattern Dictionary Structure

```python
KHMER_NAME_PATTERNS = {
    "sovann": {
        "limon": "suvaNÑ",           # Most frequent LIMON representation
        "unicode": "សុវណ្ណ",          # Correct Unicode
        "frequency": 0.85,            # 85% of "Sovann" uses this pattern
        "occurrence_count": 342,      # Number of times seen
        "variants": ["suvan", "sovan"],  # Alternative English spellings
        "confidence": 0.92            # Confidence score
    },
    "somphors": {
        "limon": "sMPaRs",
        "unicode": "សម្ផស្ស",
        "frequency": 0.72,
        "occurrence_count": 128,
        "variants": ["somphos", "somphoss"],
        "confidence": 0.88
    },
    "dara": {
        "limon": "dara",
        "unicode": "ដារា",
        "frequency": 0.91,
        "occurrence_count": 256,
        "variants": ["darra", "daara"],
        "confidence": 0.95
    }
    # ... hundreds more patterns
}
```

### 3. Approximation Engine

```python
class KhmerNameApproximator:
    """Approximates Khmer names based on frequency patterns."""

    def approximate(self, english_name: str) -> tuple[str, float]:
        """
        Approximate Khmer name from English name.

        Returns:
            Tuple of (approximated_name, confidence_score)
        """
        # 1. Normalize and clean input
        cleaned_name = self.normalize_name(english_name)

        # 2. Decompose into components
        components = self.decompose_name(cleaned_name)

        # 3. Look up each component
        limon_parts = []
        total_confidence = 1.0

        for component in components:
            pattern = self.find_best_pattern(component)
            if pattern:
                limon_parts.append(pattern['limon'])
                total_confidence *= pattern['confidence']
            else:
                # Unknown component - use transliteration
                limon_parts.append(self.transliterate(component))
                total_confidence *= 0.3

        # 4. Combine and convert
        limon_name = ''.join(limon_parts)
        unicode_name = limon_to_unicode(limon_name)

        # 5. Mark as approximation
        if total_confidence < 1.0:
            unicode_name = f"* {unicode_name}"

        return unicode_name, total_confidence

    def decompose_name(self, name: str) -> list[str]:
        """Decompose compound name into components."""
        # Use syllable detection
        # Check against known patterns
        # Return list of components

    def find_best_pattern(self, component: str) -> dict:
        """Find best matching pattern for component."""
        # Exact match first
        # Then fuzzy matching
        # Return best pattern or None
```

## Database Schema Updates

### New Fields on Person Model

```sql
ALTER TABLE people_person ADD COLUMN khmer_name_source VARCHAR(20) DEFAULT 'legacy';
ALTER TABLE people_person ADD COLUMN khmer_name_confidence DECIMAL(3,2) DEFAULT 0.00;
ALTER TABLE people_person ADD COLUMN khmer_name_approximated_at TIMESTAMP NULL;
ALTER TABLE people_person ADD COLUMN khmer_name_verified_at TIMESTAMP NULL;
ALTER TABLE people_person ADD COLUMN khmer_name_components JSONB NULL;
```

### Pattern Storage Table

```sql
CREATE TABLE people_khmernampattern (
    id SERIAL PRIMARY KEY,
    english_component VARCHAR(100) NOT NULL,
    normalized_component VARCHAR(100) NOT NULL,
    limon_pattern VARCHAR(255) NOT NULL,
    unicode_pattern VARCHAR(255) NOT NULL,
    frequency DECIMAL(3,2) NOT NULL,
    occurrence_count INTEGER DEFAULT 0,
    confidence_score DECIMAL(3,2) DEFAULT 0.50,
    variants TEXT[], -- Array of alternative spellings
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_verified BOOLEAN DEFAULT FALSE,
    UNIQUE(english_component, limon_pattern)
);

CREATE INDEX idx_pattern_english ON people_khmernampattern(english_component);
CREATE INDEX idx_pattern_normalized ON people_khmernampattern(normalized_component);
CREATE INDEX idx_pattern_frequency ON people_khmernampattern(frequency DESC);
```

### Correction Tracking Table

```sql
CREATE TABLE people_khmernamecorrection (
    id SERIAL PRIMARY KEY,
    person_id INTEGER REFERENCES people_person(id),
    original_khmer_name VARCHAR(255),
    corrected_khmer_name VARCHAR(255) NOT NULL,
    original_english_name VARCHAR(255),
    correction_source VARCHAR(50) NOT NULL,
    confidence_impact DECIMAL(3,2),
    patterns_learned JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_by_id INTEGER REFERENCES auth_user(id),
    verified_at TIMESTAMP NULL,
    verified_by_id INTEGER REFERENCES auth_user(id)
);
```

## Django Model Updates

```python
from django.db import models
from django.contrib.postgres.fields import ArrayField

class KhmerNameSource(models.TextChoices):
    USER = 'user', 'User Provided'
    APPROXIMATED = 'approximated', 'System Approximated'
    LEGACY = 'legacy', 'Legacy Data'
    VERIFIED = 'verified', 'Verified by User'
    IMPORT = 'import', 'Imported from External Source'

class Person(AuditModel):
    # Existing fields
    khmer_name = models.CharField(max_length=255, blank=True)

    # New tracking fields
    khmer_name_source = models.CharField(
        max_length=20,
        choices=KhmerNameSource.choices,
        default=KhmerNameSource.LEGACY,
        help_text="Source of the Khmer name data"
    )
    khmer_name_confidence = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        help_text="Confidence score (0.00-1.00) for approximated names"
    )
    khmer_name_approximated_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When the name was approximated"
    )
    khmer_name_verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When user verified the name"
    )
    khmer_name_components = models.JSONField(
        null=True,
        blank=True,
        help_text="Decomposed name components for debugging"
    )

class KhmerNamePattern(models.Model):
    """Stores patterns for Khmer name approximation."""

    english_component = models.CharField(max_length=100, db_index=True)
    normalized_component = models.CharField(max_length=100, db_index=True)
    limon_pattern = models.CharField(max_length=255)
    unicode_pattern = models.CharField(max_length=255)
    frequency = models.DecimalField(max_digits=3, decimal_places=2)
    occurrence_count = models.IntegerField(default=0)
    confidence_score = models.DecimalField(max_digits=3, decimal_places=2, default=0.50)
    variants = ArrayField(models.CharField(max_length=100), default=list)
    is_verified = models.BooleanField(default=False)

    class Meta:
        unique_together = [['english_component', 'limon_pattern']]
        ordering = ['-frequency', '-occurrence_count']

    def update_frequency(self):
        """Recalculate frequency based on occurrences."""
        total = KhmerNamePattern.objects.filter(
            english_component=self.english_component
        ).aggregate(total=models.Sum('occurrence_count'))['total']

        if total:
            self.frequency = self.occurrence_count / total

class KhmerNameCorrection(models.Model):
    """Tracks user corrections to improve approximation."""

    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    original_khmer_name = models.CharField(max_length=255, blank=True)
    corrected_khmer_name = models.CharField(max_length=255)
    original_english_name = models.CharField(max_length=255, blank=True)
    correction_source = models.CharField(max_length=50)
    confidence_impact = models.DecimalField(max_digits=3, decimal_places=2, null=True)
    patterns_learned = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        related_name='verified_corrections'
    )

    def apply_correction(self):
        """Apply correction and update patterns."""
        # Update person's Khmer name
        self.person.khmer_name = self.corrected_khmer_name
        self.person.khmer_name_source = KhmerNameSource.VERIFIED
        self.person.khmer_name_verified_at = timezone.now()
        self.person.save()

        # Learn from correction
        self.learn_patterns()

    def learn_patterns(self):
        """Extract patterns from correction to improve future approximations."""
        # Analyze the correction
        # Update pattern dictionary
        # Adjust confidence scores
```

## Implementation Plan

### Phase 1: Analysis & Pattern Extraction (Week 1)

#### 1.1 Create Analysis Management Command

```python
# backend/apps/people/management/commands/analyze_khmer_names.py

class Command(BaseMigrationCommand):
    """Analyze existing Khmer names to extract patterns."""

    def handle(self, *args, **options):
        # Query all people with Khmer names
        people_with_khmer = Person.objects.exclude(
            khmer_name__isnull=True
        ).exclude(
            khmer_name__exact=''
        ).select_related()

        # Build pattern dictionary
        pattern_map = defaultdict(lambda: defaultdict(int))

        for person in people_with_khmer:
            english_name = f"{person.family_name} {person.personal_name}"
            components = self.decompose_name(english_name)

            for component in components:
                # Extract LIMON pattern
                limon_pattern = self.extract_limon_pattern(
                    component,
                    person.khmer_name
                )
                pattern_map[component][limon_pattern] += 1

        # Calculate frequencies and save patterns
        self.save_patterns(pattern_map)

        # Generate report
        self.generate_analysis_report(pattern_map)
```

#### 1.2 Initial Pattern Database Population

- Analyze top 500 most common Khmer name components
- Build initial pattern dictionary
- Validate against known good translations

### Phase 2: Approximation Service (Week 1-2)

#### 2.1 Core Approximation Service

```python
# backend/apps/people/services/khmer_name_approximator.py

class KhmerNameApproximationService:
    """Service for approximating Khmer names."""

    def __init__(self):
        self.pattern_cache = {}
        self.load_patterns()

    def load_patterns(self):
        """Load patterns from database into memory."""
        patterns = KhmerNamePattern.objects.filter(
            is_verified=True
        ).order_by('-frequency')

        for pattern in patterns:
            if pattern.english_component not in self.pattern_cache:
                self.pattern_cache[pattern.english_component] = []
            self.pattern_cache[pattern.english_component].append(pattern)

    def approximate_name(self, english_name: str) -> ApproximationResult:
        """Main approximation method."""
        # Implementation as designed above

    def batch_approximate(self, person_ids: list[int]):
        """Batch process multiple people."""
        people = Person.objects.filter(
            id__in=person_ids,
            khmer_name__exact=''
        )

        results = []
        for person in people:
            result = self.approximate_for_person(person)
            results.append(result)

        return results
```

#### 2.2 Name Decomposition Algorithm

```python
class NameDecomposer:
    """Decomposes compound Khmer names into components."""

    COMMON_PREFIXES = ['so', 'sam', 'chan', 'sok', 'phal']
    COMMON_SUFFIXES = ['ny', 'ra', 'tha', 'thy', 'phy']

    def decompose(self, name: str) -> list[str]:
        """Decompose name into components."""
        name = name.lower().strip()

        # Try known compound patterns first
        components = self.try_known_compounds(name)
        if components:
            return components

        # Use syllable-based decomposition
        components = self.syllable_decompose(name)

        # Validate against pattern dictionary
        components = self.validate_components(components)

        return components
```

### Phase 3: Migration Process (Week 2)

#### 3.1 Batch Approximation Command

```python
# backend/apps/people/management/commands/approximate_khmer_names.py

class Command(BaseMigrationCommand):
    """Approximate Khmer names for students without them."""

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            type=int,
            default=100,
            help='Number of records to process at once'
        )
        parser.add_argument(
            '--confidence-threshold',
            type=float,
            default=0.5,
            help='Minimum confidence to apply approximation'
        )

    def handle(self, *args, **options):
        # Query students without Khmer names
        students_without_khmer = Person.objects.filter(
            Q(khmer_name__isnull=True) | Q(khmer_name__exact='')
        ).exclude(
            khmer_name_source=KhmerNameSource.USER
        )

        self.stdout.write(f"Found {students_without_khmer.count()} students without Khmer names")

        # Process in batches
        service = KhmerNameApproximationService()

        for batch in self.batch_queryset(students_without_khmer, options['batch_size']):
            results = service.batch_approximate([p.id for p in batch])
            self.process_results(results, options['confidence_threshold'])

        # Generate migration report
        self.generate_migration_report()
```

### Phase 4: Mobile App Integration (Week 3)

#### 4.1 API Endpoints

```python
# backend/api/v1/khmer_names.py

@router.post("/khmer-name/submit")
def submit_khmer_name(request, data: KhmerNameSubmission):
    """Allow users to submit their correct Khmer name."""
    person = request.user.person

    # Create correction record
    correction = KhmerNameCorrection.objects.create(
        person=person,
        original_khmer_name=person.khmer_name,
        corrected_khmer_name=data.khmer_name,
        original_english_name=f"{person.family_name} {person.personal_name}",
        correction_source='mobile_app',
        created_by=request.user
    )

    # Apply correction
    correction.apply_correction()

    # Learn from correction for future improvements
    learn_from_correction(correction)

    return {"status": "success", "message": "Khmer name updated successfully"}

@router.get("/khmer-name/verify")
def get_name_for_verification(request):
    """Get current Khmer name for user verification."""
    person = request.user.person

    return {
        "english_name": f"{person.family_name} {person.personal_name}",
        "khmer_name": person.khmer_name,
        "is_approximated": person.khmer_name_source == KhmerNameSource.APPROXIMATED,
        "confidence": float(person.khmer_name_confidence),
        "can_edit": True
    }
```

### Phase 5: Continuous Improvement (Ongoing)

#### 5.1 Pattern Learning System

```python
class PatternLearner:
    """Learns from user corrections to improve patterns."""

    def learn_from_correction(self, correction: KhmerNameCorrection):
        """Extract patterns from a correction."""
        # Decompose both names
        english_components = self.decompose(correction.original_english_name)
        khmer_components = self.extract_khmer_components(correction.corrected_khmer_name)

        # Align components
        alignments = self.align_components(english_components, khmer_components)

        # Update patterns
        for eng, khmer in alignments:
            self.update_pattern(eng, khmer)

    def update_pattern(self, english: str, khmer: str):
        """Update or create pattern based on new learning."""
        limon = unicode_to_limon(khmer)

        pattern, created = KhmerNamePattern.objects.get_or_create(
            english_component=english.lower(),
            limon_pattern=limon,
            defaults={
                'unicode_pattern': khmer,
                'occurrence_count': 0,
                'confidence_score': 0.5
            }
        )

        # Increment occurrence
        pattern.occurrence_count += 1

        # Adjust confidence based on consistency
        pattern.confidence_score = self.calculate_confidence(pattern)

        # Recalculate frequency
        pattern.update_frequency()
        pattern.save()
```

#### 5.2 Quality Monitoring

```python
class ApproximationQualityMonitor:
    """Monitors and reports on approximation quality."""

    def generate_quality_report(self):
        """Generate quality metrics report."""
        metrics = {
            'total_approximations': Person.objects.filter(
                khmer_name_source=KhmerNameSource.APPROXIMATED
            ).count(),
            'user_corrections': KhmerNameCorrection.objects.count(),
            'correction_rate': self.calculate_correction_rate(),
            'average_confidence': self.calculate_average_confidence(),
            'pattern_coverage': self.calculate_pattern_coverage(),
            'top_corrected_patterns': self.get_top_corrected_patterns()
        }

        return metrics
```

## Testing Strategy

### Unit Tests

```python
class TestKhmerNameApproximation(TestCase):
    """Test Khmer name approximation system."""

    def test_simple_name_approximation(self):
        """Test approximation of simple single-component name."""
        result = approximate_khmer_name("Sovann")
        self.assertEqual(result[0], "* សុវណ្ណ")
        self.assertGreater(result[1], 0.8)

    def test_compound_name_approximation(self):
        """Test approximation of compound name."""
        result = approximate_khmer_name("Sovansomphors")
        self.assertIn("សុវណ្ណ", result[0])
        self.assertIn("សម្ផស្ស", result[0])

    def test_unknown_component_handling(self):
        """Test handling of unknown name components."""
        result = approximate_khmer_name("UnknownName")
        self.assertTrue(result[0].startswith("*"))
        self.assertLess(result[1], 0.5)
```

### Integration Tests

```python
class TestKhmerNameIntegration(IntegrationTestCase):
    """Integration tests for Khmer name system."""

    def test_batch_approximation_command(self):
        """Test batch approximation management command."""
        # Create test people without Khmer names
        people = [
            Person.objects.create(
                family_name="SOVANN",
                personal_name="DARA",
                khmer_name=""
            )
            for _ in range(10)
        ]

        # Run command
        call_command('approximate_khmer_names', batch_size=5)

        # Verify results
        for person in Person.objects.filter(id__in=[p.id for p in people]):
            self.assertNotEqual(person.khmer_name, "")
            self.assertEqual(person.khmer_name_source, KhmerNameSource.APPROXIMATED)
```

## Performance Considerations

### Caching Strategy

```python
class PatternCache:
    """In-memory cache for pattern lookups."""

    def __init__(self):
        self._cache = {}
        self._last_refresh = None
        self._ttl = 3600  # 1 hour

    def get_pattern(self, component: str) -> Optional[dict]:
        """Get pattern from cache."""
        if self._should_refresh():
            self._refresh_cache()

        return self._cache.get(component.lower())

    def _should_refresh(self) -> bool:
        """Check if cache needs refresh."""
        if not self._last_refresh:
            return True

        age = (timezone.now() - self._last_refresh).seconds
        return age > self._ttl
```

### Database Optimization

```sql
-- Indexes for performance
CREATE INDEX idx_person_khmer_name_null ON people_person(id)
WHERE khmer_name IS NULL OR khmer_name = '';

CREATE INDEX idx_person_khmer_source ON people_person(khmer_name_source);

CREATE INDEX idx_pattern_lookup ON people_khmernampattern(
    normalized_component,
    frequency DESC,
    confidence_score DESC
);

-- Materialized view for common patterns
CREATE MATERIALIZED VIEW mv_common_patterns AS
SELECT
    english_component,
    limon_pattern,
    unicode_pattern,
    frequency,
    confidence_score
FROM people_khmernampattern
WHERE occurrence_count > 10
    AND confidence_score > 0.7
ORDER BY frequency DESC;

CREATE INDEX idx_mv_common_english ON mv_common_patterns(english_component);
```

## Success Metrics

### Key Performance Indicators

1. **Coverage Metrics**
   - % of students with Khmer names (Target: >95%)
   - % of names approximated vs user-provided
   - Pattern dictionary size (Target: >500 components)

2. **Quality Metrics**
   - Approximation accuracy rate (Target: >80%)
   - User correction rate (Lower is better)
   - Average confidence score (Target: >0.75)

3. **User Engagement**
   - Mobile app name submission rate
   - Time to first correction
   - User satisfaction scores

4. **System Performance**
   - Approximation speed (<100ms per name)
   - Batch processing throughput (>1000 names/minute)
   - Pattern learning convergence rate

### Monitoring Dashboard

```python
class KhmerNameDashboard:
    """Dashboard for monitoring Khmer name system."""

    def get_metrics(self):
        return {
            'coverage': {
                'total_people': Person.objects.count(),
                'with_khmer_names': Person.objects.exclude(
                    khmer_name__exact=''
                ).count(),
                'user_provided': Person.objects.filter(
                    khmer_name_source=KhmerNameSource.USER
                ).count(),
                'approximated': Person.objects.filter(
                    khmer_name_source=KhmerNameSource.APPROXIMATED
                ).count(),
                'verified': Person.objects.filter(
                    khmer_name_source=KhmerNameSource.VERIFIED
                ).count()
            },
            'quality': {
                'avg_confidence': Person.objects.filter(
                    khmer_name_source=KhmerNameSource.APPROXIMATED
                ).aggregate(avg=models.Avg('khmer_name_confidence'))['avg'],
                'correction_rate': self.calculate_correction_rate(),
                'pattern_accuracy': self.calculate_pattern_accuracy()
            },
            'patterns': {
                'total_patterns': KhmerNamePattern.objects.count(),
                'verified_patterns': KhmerNamePattern.objects.filter(
                    is_verified=True
                ).count(),
                'high_confidence_patterns': KhmerNamePattern.objects.filter(
                    confidence_score__gte=0.8
                ).count()
            }
        }
```

## Risk Mitigation

### Identified Risks

1. **Pattern Accuracy Risk**
   - Mitigation: Start with high-confidence patterns only
   - Fallback: Allow easy user corrections

2. **Cultural Sensitivity**
   - Mitigation: Clear marking of approximations
   - User control: Easy opt-out and correction options

3. **Performance Impact**
   - Mitigation: Caching and batch processing
   - Monitoring: Performance metrics and alerts

4. **Data Quality Degradation**
   - Mitigation: Confidence thresholds
   - Validation: Regular quality audits

## Conclusion

This Khmer name approximation system provides a practical solution to the current LIMON conversion problems while maintaining respect for users' actual names. By combining frequency analysis, intelligent pattern matching, and continuous learning from user corrections, the system will progressively improve its accuracy while immediately providing value to users who currently have no Khmer name display.

The phased implementation approach ensures that each component is thoroughly tested before moving to the next phase, minimizing risk and maximizing the chance of success. The system's self-improving nature through user feedback means that accuracy will continually increase over time.

## Appendix: Example Patterns

### Common Khmer Name Components

| English | LIMON | Unicode | Frequency | Notes |
|---------|-------|---------|-----------|-------|
| Sovann | suvaNÑ | សុវណ្ណ | 0.85 | "Gold" |
| Dara | dara | ដារា | 0.91 | "Star" |
| Sopheak | suPak | សុភ័ក្ត | 0.78 | "Good fortune" |
| Chantha | c½nßa | ច័ន្ទថា | 0.82 | "Moon" |
| Somphors | sMPaRs | សម្ផស្ស | 0.72 | "Contact" |
| Veasna | vEasna | វាសនា | 0.88 | "Destiny" |
| Sokha | suxa | សុខា | 0.94 | "Happiness" |
| Phalla | Pløa | ផល្លា | 0.76 | "Fruit" |
| Ratha | rfaH | រថា | 0.83 | "Chariot" |
| Kunthea | KunßEa | គន្ធា | 0.79 | "Fragrance" |

### Compound Name Examples

| English | Components | Approximation |
|---------|------------|---------------|
| Sovansomphors | Sovann + Somphors | * សុវណ្ណសម្ផស្ស |
| Darasopheak | Dara + Sopheak | * ដារាសុភ័ក្ត |
| Chanthaveasna | Chantha + Veasna | * ច័ន្ទថាវាសនា |
| Sokharatha | Sokha + Ratha | * សុខារថា |

---

*Document Version: 1.0*
*Last Updated: 2025*
*Author: System Architecture Team*