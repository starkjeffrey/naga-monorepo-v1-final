"""Tests for Khmer name approximation system."""

import pytest
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model

from apps.people.models import Person, KhmerNamePattern, KhmerNameCorrection
from apps.people.services.name_decomposer import NameDecomposer
from apps.people.services.khmer_approximator import KhmerNameApproximator
from apps.people.services.pattern_analyzer import PatternAnalyzer
from apps.people.services.pattern_learner import PatternLearner


User = get_user_model()


class TestNameDecomposer(TestCase):
    """Test name decomposition functionality."""

    def setUp(self):
        """Set up test data."""
        self.decomposer = NameDecomposer()

    def test_simple_name_decomposition(self):
        """Test decomposition of simple single-component names."""
        result = self.decomposer.decompose("Sovann")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].text.lower(), "sovann")
        self.assertGreater(result[0].confidence, 0)

    def test_compound_name_decomposition(self):
        """Test decomposition of known compound names."""
        result = self.decomposer.decompose("Sovansomphors")
        self.assertGreaterEqual(len(result), 2)

        # Check that decomposition contains expected components
        components_text = [comp.text.lower() for comp in result]
        self.assertTrue(any("sov" in comp for comp in components_text))

    def test_empty_name_handling(self):
        """Test handling of empty or invalid names."""
        self.assertEqual(self.decomposer.decompose(""), [])
        self.assertEqual(self.decomposer.decompose("   "), [])
        self.assertEqual(self.decomposer.decompose(None), [])

    def test_name_with_prefixes_suffixes(self):
        """Test decomposition of names with common prefixes/suffixes."""
        result = self.decomposer.decompose("Sokha")
        self.assertGreater(len(result), 0)

        # Should identify "so" as prefix
        first_component = result[0]
        self.assertTrue(first_component.text.lower().startswith("so") or
                       any(comp.is_prefix for comp in result))

    def test_confidence_scores(self):
        """Test that confidence scores are reasonable."""
        result = self.decomposer.decompose("Dara")
        for component in result:
            self.assertGreaterEqual(component.confidence, 0.0)
            self.assertLessEqual(component.confidence, 1.0)


class TestKhmerNamePattern(TestCase):
    """Test KhmerNamePattern model functionality."""

    def test_pattern_creation(self):
        """Test creating a new pattern."""
        pattern = KhmerNamePattern.objects.create(
            english_component="sovann",
            normalized_component="sovann",
            limon_pattern="suvaNÑ",
            unicode_pattern="សុវណ្ណ",
            frequency=Decimal("0.85"),
            occurrence_count=10,
            confidence_score=Decimal("0.90")
        )

        self.assertEqual(pattern.english_component, "sovann")
        self.assertEqual(pattern.unicode_pattern, "សុវណ្ណ")
        self.assertEqual(pattern.frequency, Decimal("0.85"))
        self.assertTrue(pattern.is_verified is False)  # Default

    def test_pattern_validation(self):
        """Test pattern field validation."""
        with self.assertRaises(Exception):
            # Invalid frequency > 1.0
            KhmerNamePattern.objects.create(
                english_component="test",
                frequency=Decimal("1.5"),
                confidence_score=Decimal("0.5")
            )

    def test_update_frequency(self):
        """Test frequency recalculation."""
        # Create multiple patterns for same component
        KhmerNamePattern.objects.create(
            english_component="test",
            normalized_component="test",
            limon_pattern="pattern1",
            unicode_pattern="test1",
            frequency=Decimal("0.0"),
            occurrence_count=30,
            confidence_score=Decimal("0.5")
        )

        pattern2 = KhmerNamePattern.objects.create(
            english_component="test",
            normalized_component="test",
            limon_pattern="pattern2",
            unicode_pattern="test2",
            frequency=Decimal("0.0"),
            occurrence_count=70,
            confidence_score=Decimal("0.7")
        )

        pattern2.update_frequency()
        pattern2.refresh_from_db()

        # Should be 70/100 = 0.7
        self.assertEqual(pattern2.frequency, Decimal("0.70"))


class TestKhmerNameApproximator(TestCase):
    """Test Khmer name approximation functionality."""

    def setUp(self):
        """Set up test data."""
        self.approximator = KhmerNameApproximator()

        # Create some test patterns
        KhmerNamePattern.objects.create(
            english_component="sovann",
            normalized_component="sovann",
            limon_pattern="suvaNÑ",
            unicode_pattern="សុវណ្ណ",
            frequency=Decimal("0.85"),
            occurrence_count=17,
            confidence_score=Decimal("0.90"),
            is_verified=True
        )

        KhmerNamePattern.objects.create(
            english_component="dara",
            normalized_component="dara",
            limon_pattern="dara",
            unicode_pattern="ដារា",
            frequency=Decimal("0.92"),
            occurrence_count=23,
            confidence_score=Decimal("0.95"),
            is_verified=True
        )

    def test_simple_approximation(self):
        """Test approximation of simple names."""
        result = self.approximator.approximate_name("Sovann")

        self.assertEqual(result.original_english, "Sovann")
        self.assertIn("សុវណ្ណ", result.approximated_khmer)
        self.assertGreater(result.confidence_score, 0.5)
        self.assertTrue(result.is_approximation)

    def test_unknown_name_approximation(self):
        """Test approximation of unknown names."""
        result = self.approximator.approximate_name("UnknownName")

        self.assertEqual(result.original_english, "UnknownName")
        self.assertLess(result.confidence_score, 0.8)  # Should be lower confidence
        self.assertTrue(result.is_approximation)

    def test_empty_name_handling(self):
        """Test handling of empty names."""
        result = self.approximator.approximate_name("")

        self.assertEqual(result.confidence_score, 0.0)
        self.assertFalse(result.is_approximation)
        self.assertGreater(len(result.warnings), 0)

    def test_compound_name_approximation(self):
        """Test approximation of compound names."""
        result = self.approximator.approximate_name("Darasovann")

        self.assertEqual(result.original_english, "Darasovann")
        self.assertGreater(result.confidence_score, 0.0)
        self.assertTrue(result.is_approximation)
        self.assertGreater(len(result.components_used), 0)

    def test_person_approximation(self):
        """Test approximating for a specific person."""
        person = Person.objects.create(
            family_name="SOVANN",
            personal_name="DARA",
            khmer_name=""
        )

        result = self.approximator.approximate_for_person(person)

        self.assertIn("SOVANN DARA", result.original_english)
        self.assertGreater(result.confidence_score, 0.0)


class TestKhmerNameCorrection(TestCase):
    """Test Khmer name correction functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            name="Test User"
        )

        self.person = Person.objects.create(
            family_name="SOVANN",
            personal_name="DARA",
            khmer_name="* សុវណ្ណដារា",
            khmer_name_source="approximated",
            khmer_name_confidence=Decimal("0.75")
        )

    def test_correction_creation(self):
        """Test creating a correction record."""
        correction = KhmerNameCorrection.objects.create(
            person=self.person,
            original_khmer_name="* សុវណ្ណដារា",
            corrected_khmer_name="សុវណ្ណដារា",
            original_english_name="SOVANN DARA",
            correction_source="mobile_app",
            created_by=self.user
        )

        self.assertEqual(correction.person, self.person)
        self.assertEqual(correction.corrected_khmer_name, "សុវណ្ណដារា")
        self.assertEqual(correction.correction_source, "mobile_app")

    def test_apply_correction(self):
        """Test applying a correction to update person data."""
        correction = KhmerNameCorrection.objects.create(
            person=self.person,
            original_khmer_name="* សុវណ្ណដារា",
            corrected_khmer_name="សុវណ្ណដារា",
            original_english_name="SOVANN DARA",
            correction_source="mobile_app",
            created_by=self.user
        )

        # Apply the correction
        correction.apply_correction()

        # Refresh person from database
        self.person.refresh_from_db()

        self.assertEqual(self.person.khmer_name, "សុវណ្ណដារា")
        self.assertEqual(self.person.khmer_name_source, "verified")
        self.assertEqual(self.person.khmer_name_confidence, Decimal("1.00"))
        self.assertIsNotNone(self.person.khmer_name_verified_at)


class TestPatternLearner(TestCase):
    """Test pattern learning functionality."""

    def setUp(self):
        """Set up test data."""
        self.learner = PatternLearner()
        self.user = User.objects.create_user(
            email="test@example.com",
            name="Test User"
        )

        self.person = Person.objects.create(
            family_name="SOVANN",
            personal_name="DARA",
            khmer_name="* សុវណ្ណដារា",
            khmer_name_source="approximated"
        )

    def test_learn_from_single_correction(self):
        """Test learning from a single component correction."""
        correction = KhmerNameCorrection.objects.create(
            person=self.person,
            original_khmer_name="* សុវណ្ណដារា",
            corrected_khmer_name="សុវណ្ណដារា",
            original_english_name="SOVANN DARA",
            correction_source="mobile_app",
            created_by=self.user
        )

        result = self.learner.learn_from_correction(correction)

        self.assertEqual(result['status'], 'success')
        self.assertGreater(result['patterns_count'], 0)

    def test_pattern_confidence_adjustment(self):
        """Test that learning adjusts pattern confidence."""
        # Create initial pattern
        pattern = KhmerNamePattern.objects.create(
            english_component="sovann",
            normalized_component="sovann",
            limon_pattern="wrong_pattern",
            unicode_pattern="Wrong Pattern",
            frequency=Decimal("0.5"),
            occurrence_count=1,
            confidence_score=Decimal("0.6")
        )

        original_confidence = pattern.confidence_score

        # Create correction that should teach new pattern
        correction = KhmerNameCorrection.objects.create(
            person=self.person,
            original_khmer_name="Wrong Pattern",
            corrected_khmer_name="សុវណ្ណ",
            original_english_name="SOVANN",
            correction_source="mobile_app",
            created_by=self.user
        )

        self.learner.learn_from_correction(correction)

        # Should have created new pattern for correct mapping
        new_pattern = KhmerNamePattern.objects.filter(
            english_component="sovann",
            unicode_pattern="សុវណ្ណ"
        ).first()

        self.assertIsNotNone(new_pattern)
        self.assertTrue(new_pattern.is_verified)


class TestPatternAnalyzer(TestCase):
    """Test pattern analysis functionality."""

    def setUp(self):
        """Set up test data."""
        self.analyzer = PatternAnalyzer()

        # Create test people with Khmer names
        Person.objects.create(
            family_name="SOVANN",
            personal_name="DARA",
            khmer_name="សុវណ្ណដារា"
        )

        Person.objects.create(
            family_name="CHAN",
            personal_name="DARA",
            khmer_name="ចន្ទដារា"
        )

        Person.objects.create(
            family_name="SOVANN",
            personal_name="REACH",
            khmer_name="សុវណ្ណរាជ"
        )

    def test_analyze_existing_names(self):
        """Test analysis of existing names."""
        results = self.analyzer.analyze_existing_names()

        self.assertGreater(results['processed_count'], 0)
        self.assertGreater(results['statistics']['total_components'], 0)
        self.assertIn('patterns', results)

    def test_pattern_quality_validation(self):
        """Test pattern quality validation."""
        # First run analysis
        self.analyzer.analyze_existing_names()

        # Then validate quality
        quality_report = self.analyzer.validate_pattern_quality()

        self.assertIn('total_patterns', quality_report)
        self.assertIn('quality_score', quality_report)
        self.assertGreaterEqual(quality_report['quality_score'], 0.0)
        self.assertLessEqual(quality_report['quality_score'], 1.0)

    def test_pattern_recommendations(self):
        """Test getting pattern recommendations."""
        # Run analysis first
        self.analyzer.analyze_existing_names()

        # Get recommendations for a component that should exist
        recommendations = self.analyzer.get_pattern_recommendations("sovann")

        # Might have recommendations or might not, depending on analysis
        self.assertIsInstance(recommendations, list)


@pytest.mark.django_db
class TestIntegrationScenario:
    """Integration tests for complete workflows."""

    def test_complete_approximation_workflow(self):
        """Test complete workflow from analysis to approximation to correction."""
        # Create test data
        person_with_khmer = Person.objects.create(
            family_name="SOVANN",
            personal_name="DARA",
            khmer_name="សុវណ្ណដារា"
        )

        person_without_khmer = Person.objects.create(
            family_name="SOVANN",
            personal_name="REACH",
            khmer_name=""
        )

        user = User.objects.create_user(
            email="test@example.com",
            name="Test User"
        )

        # Step 1: Analyze existing names to build patterns
        analyzer = PatternAnalyzer()
        results = analyzer.analyze_existing_names()
        assert results['processed_count'] > 0

        # Save patterns
        patterns_saved = analyzer.save_patterns_to_database(min_confidence=0.1, min_count=1)
        assert patterns_saved > 0

        # Step 2: Approximate names for people without them
        approximator = KhmerNameApproximator()
        result = approximator.approximate_for_person(person_without_khmer)

        assert result.confidence_score > 0
        assert result.approximated_khmer != ""

        # Step 3: Simulate user correction
        correction = KhmerNameCorrection.objects.create(
            person=person_without_khmer,
            original_khmer_name=result.approximated_khmer,
            corrected_khmer_name="សុវណ្ណរាជ",
            original_english_name="SOVANN REACH",
            correction_source="mobile_app",
            created_by=user
        )

        # Apply correction and learn
        correction.apply_correction()

        # Verify correction was applied
        person_without_khmer.refresh_from_db()
        assert person_without_khmer.khmer_name == "សុវណ្ណរាជ"
        assert person_without_khmer.khmer_name_source == "verified"
        assert person_without_khmer.khmer_name_confidence == Decimal("1.00")

        # Step 4: Verify learning occurred
        learner = PatternLearner()
        learning_result = learner.learn_from_correction(correction)
        assert learning_result['status'] == 'success'