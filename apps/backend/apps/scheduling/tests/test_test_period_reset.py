"""Tests for TestPeriodReset model and functionality.

Comprehensive tests for absence penalty reset date management including:
- Model validation and constraints
- Language division validation
- Bulk application logic
- Class-specific overrides
- Helper method functionality
- Edge cases and error conditions
"""

from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.curriculum.models import Course, Cycle, Division, Term
from apps.scheduling.models import ClassHeader, TestPeriodReset


class TestPeriodResetModelTest(TestCase):
    """Test TestPeriodReset model functionality."""

    def setUp(self):
        """Set up test data."""
        # Create divisions
        self.lang_division = Division.objects.create(name="Language Division", short_name="LANG")
        self.academic_division = Division.objects.create(name="Academic Division", short_name="ACAD")

        # Create cycles
        self.lang_cycle = Cycle.objects.create(
            division=self.lang_division,
            name="Language Programs",
            degree_awarded="CERT",
        )
        self.academic_cycle = Cycle.objects.create(
            division=self.academic_division,
            name="Bachelor's",
            degree_awarded="BA",
        )

        # Create courses
        self.ieap_course = Course.objects.create(
            code="IEAP01",
            title="Intensive English for Academic Purposes",
            short_title="IEAP",
            division=self.lang_division,
            cycle="LANGUAGE",
            is_language=True,
        )
        self.gesl_course = Course.objects.create(
            code="GESL01",
            title="General English as Second Language",
            short_title="GESL",
            division=self.lang_division,
            cycle="LANGUAGE",
            is_language=True,
        )
        self.academic_course = Course.objects.create(
            code="BUS101",
            title="Introduction to Business",
            short_title="Intro Bus",
            division=self.academic_division,
            cycle="BA",
            is_language=False,
        )

        # Create term
        self.term = Term.objects.create(
            name="Fall 2024",
            term_type="ENG_A",
            start_date=date(2024, 9, 1),
            end_date=date(2024, 12, 15),
        )

        # Create class headers
        self.ieap_class = ClassHeader.objects.create(
            course=self.ieap_course,
            term=self.term,
            section_id="A",
            time_of_day="MORN",
        )
        self.gesl_class = ClassHeader.objects.create(
            course=self.gesl_course,
            term=self.term,
            section_id="A",
            time_of_day="MORN",
        )
        self.academic_class = ClassHeader.objects.create(
            course=self.academic_course,
            term=self.term,
            section_id="A",
            time_of_day="MORN",
        )

    def test_create_valid_test_period_reset(self):
        """Test creating a valid test period reset."""
        reset = TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2024, 10, 15),
            applies_to_all_language_classes=True,
        )

        self.assertEqual(reset.term, self.term)
        self.assertEqual(reset.test_type, TestPeriodReset.TestType.MIDTERM)
        self.assertEqual(reset.reset_date, date(2024, 10, 15))
        self.assertTrue(reset.applies_to_all_language_classes)

    def test_str_representation(self):
        """Test string representation of test period reset."""
        reset = TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.IEAP_TEST_1,
            reset_date=date(2024, 10, 1),
            applies_to_all_language_classes=True,
        )

        expected = f"{self.term} - IEAP Test 1 (2024-10-01) - All Language Classes"
        self.assertEqual(str(reset), expected)

    def test_str_representation_specific_classes(self):
        """Test string representation for specific classes."""
        reset = TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.FINAL,
            reset_date=date(2024, 12, 1),
            applies_to_all_language_classes=False,
        )

        expected = f"{self.term} - Final (2024-12-01) - Specific Classes"
        self.assertEqual(str(reset), expected)

    def test_unique_constraint_violation(self):
        """Test unique constraint for term, test_type, applies_to_all."""
        TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2024, 10, 15),
            applies_to_all_language_classes=True,
        )

        with self.assertRaises(IntegrityError):
            TestPeriodReset.objects.create(
                term=self.term,
                test_type=TestPeriodReset.TestType.MIDTERM,
                reset_date=date(2024, 10, 20),  # Different date
                applies_to_all_language_classes=True,  # Same combination
            )

    def test_reset_date_within_term_validation(self):
        """Test validation that reset date must be within term dates."""
        reset = TestPeriodReset(
            term=self.term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2025, 1, 15),  # After term end
            applies_to_all_language_classes=True,
        )

        with self.assertRaises(ValidationError) as cm:
            reset.clean()

        self.assertIn("Reset date must be within the term dates", str(cm.exception))

    def test_reset_date_before_term_validation(self):
        """Test validation that reset date cannot be before term start."""
        reset = TestPeriodReset(
            term=self.term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2024, 8, 15),  # Before term start
            applies_to_all_language_classes=True,
        )

        with self.assertRaises(ValidationError) as cm:
            reset.clean()

        self.assertIn("Reset date must be within the term dates", str(cm.exception))

    def test_applicable_classes_count_all_language(self):
        """Test applicable classes count for all language classes."""
        reset = TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2024, 10, 15),
            applies_to_all_language_classes=True,
        )

        # Should count both IEAP and GESL classes, but not academic
        self.assertEqual(reset.applicable_classes_count, 2)

    def test_applicable_classes_count_specific(self):
        """Test applicable classes count for specific classes."""
        reset = TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2024, 10, 15),
            applies_to_all_language_classes=False,
        )
        reset.specific_classes.add(self.ieap_class)

        self.assertEqual(reset.applicable_classes_count, 1)

    def test_get_applicable_classes_all_language(self):
        """Test getting all applicable language classes."""
        reset = TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2024, 10, 15),
            applies_to_all_language_classes=True,
        )

        applicable_classes = list(reset.get_applicable_classes())
        self.assertEqual(len(applicable_classes), 2)
        self.assertIn(self.ieap_class, applicable_classes)
        self.assertIn(self.gesl_class, applicable_classes)
        self.assertNotIn(self.academic_class, applicable_classes)

    def test_get_applicable_classes_specific(self):
        """Test getting specific applicable classes."""
        reset = TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2024, 10, 15),
            applies_to_all_language_classes=False,
        )
        reset.specific_classes.add(self.ieap_class)

        applicable_classes = list(reset.get_applicable_classes())
        self.assertEqual(len(applicable_classes), 1)
        self.assertIn(self.ieap_class, applicable_classes)

    def test_get_reset_date_for_class_specific_override(self):
        """Test getting reset date with specific class override."""
        # Create general reset
        TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2024, 10, 15),
            applies_to_all_language_classes=True,
        )

        # Create specific override
        specific_reset = TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2024, 10, 20),  # Different date
            applies_to_all_language_classes=False,
        )
        specific_reset.specific_classes.add(self.ieap_class)

        # Should get specific override for IEAP class
        reset_date = TestPeriodReset.get_reset_date_for_class(self.ieap_class, TestPeriodReset.TestType.MIDTERM)
        self.assertEqual(reset_date, date(2024, 10, 20))

        # Should get general reset for GESL class
        reset_date = TestPeriodReset.get_reset_date_for_class(self.gesl_class, TestPeriodReset.TestType.MIDTERM)
        self.assertEqual(reset_date, date(2024, 10, 15))

    def test_get_reset_date_for_class_no_reset(self):
        """Test getting reset date when no reset exists."""
        reset_date = TestPeriodReset.get_reset_date_for_class(self.ieap_class, TestPeriodReset.TestType.MIDTERM)
        self.assertIsNone(reset_date)

    def test_get_all_reset_dates_for_term(self):
        """Test getting all reset dates for a term."""
        # Create multiple resets
        TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2024, 10, 15),
            applies_to_all_language_classes=True,
        )
        TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.FINAL,
            reset_date=date(2024, 12, 1),
            applies_to_all_language_classes=True,
        )

        reset_dates = TestPeriodReset.get_all_reset_dates_for_term(self.term)

        expected = {
            TestPeriodReset.TestType.MIDTERM: date(2024, 10, 15),
            TestPeriodReset.TestType.FINAL: date(2024, 12, 1),
        }
        self.assertEqual(reset_dates, expected)

    def test_is_language_class_validation(self):
        """Test language class validation helper method."""
        reset = TestPeriodReset(
            term=self.term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2024, 10, 15),
            applies_to_all_language_classes=False,
        )

        # Test language classes
        self.assertTrue(reset._is_language_class(self.ieap_class))
        self.assertTrue(reset._is_language_class(self.gesl_class))

        # Test academic class
        self.assertFalse(reset._is_language_class(self.academic_class))

    def test_ieap_test_types(self):
        """Test IEAP-specific test types."""
        for test_type in [
            TestPeriodReset.TestType.IEAP_TEST_1,
            TestPeriodReset.TestType.IEAP_TEST_2,
            TestPeriodReset.TestType.IEAP_TEST_3,
        ]:
            reset = TestPeriodReset.objects.create(
                term=self.term,
                test_type=test_type,
                reset_date=date(2024, 10, 15),
                applies_to_all_language_classes=True,
            )
            self.assertEqual(reset.test_type, test_type)

    def test_standard_test_types(self):
        """Test standard test types for non-IEAP programs."""
        for test_type in [
            TestPeriodReset.TestType.MIDTERM,
            TestPeriodReset.TestType.FINAL,
        ]:
            reset = TestPeriodReset.objects.create(
                term=self.term,
                test_type=test_type,
                reset_date=date(2024, 10, 15),
                applies_to_all_language_classes=True,
            )
            self.assertEqual(reset.test_type, test_type)

    def test_notes_field(self):
        """Test notes field functionality."""
        notes = "Special considerations for this reset period"
        reset = TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2024, 10, 15),
            applies_to_all_language_classes=True,
            notes=notes,
        )

        self.assertEqual(reset.notes, notes)

    def test_model_ordering(self):
        """Test model ordering by term, test_type, reset_date."""
        # Create resets in different order
        reset2 = TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.FINAL,
            reset_date=date(2024, 12, 1),
            applies_to_all_language_classes=True,
        )
        reset1 = TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2024, 10, 15),
            applies_to_all_language_classes=True,
        )

        # Should be ordered by test_type (FINAL comes after MIDTERM alphabetically)
        resets = list(TestPeriodReset.objects.all())
        self.assertEqual(resets[0], reset2)  # FINAL
        self.assertEqual(resets[1], reset1)  # MIDTERM

    def test_with_deleted_classes(self):
        """Test that deleted classes are excluded from applicable classes."""
        # Mark GESL class as deleted
        self.gesl_class.is_deleted = True
        self.gesl_class.save()

        reset = TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2024, 10, 15),
            applies_to_all_language_classes=True,
        )

        # Should only count active language classes
        self.assertEqual(reset.applicable_classes_count, 1)  # Only IEAP
        applicable_classes = list(reset.get_applicable_classes())
        self.assertIn(self.ieap_class, applicable_classes)
        self.assertNotIn(self.gesl_class, applicable_classes)


class TestPeriodResetIntegrationTest(TestCase):
    """Integration tests for TestPeriodReset with real-world scenarios."""

    def setUp(self):
        """Set up integration test data."""
        # Create language division
        self.lang_division = Division.objects.create(name="Language Division", short_name="LANG")

        # Create language cycle
        self.lang_cycle = Cycle.objects.create(
            division=self.lang_division,
            name="Language Programs",
            degree_awarded="CERT",
        )

        # Create IEAP and GESL courses
        self.ieap_course = Course.objects.create(
            code="IEAP01",
            title="Intensive English for Academic Purposes",
            short_title="IEAP",
            division=self.lang_division,
            cycle="LANGUAGE",
            is_language=True,
        )
        self.gesl_course = Course.objects.create(
            code="GESL01",
            title="General English as Second Language",
            short_title="GESL",
            division=self.lang_division,
            cycle="LANGUAGE",
            is_language=True,
        )

        # Create term
        self.term = Term.objects.create(
            name="Fall 2024",
            term_type="ENG_A",
            start_date=date(2024, 9, 1),
            end_date=date(2024, 12, 15),
        )

        # Create multiple class sections
        self.ieap_classes = []
        self.gesl_classes = []

        for section in ["A", "B", "C"]:
            ieap_class = ClassHeader.objects.create(
                course=self.ieap_course,
                term=self.term,
                section_id=section,
                time_of_day="MORN",
            )
            self.ieap_classes.append(ieap_class)

            gesl_class = ClassHeader.objects.create(
                course=self.gesl_course,
                term=self.term,
                section_id=section,
                time_of_day="AFT",
            )
            self.gesl_classes.append(gesl_class)

    def test_bulk_reset_scenario(self):
        """Test bulk reset scenario for 50+ language classes."""
        # Create bulk reset for midterm and final
        midterm_reset = TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2024, 10, 15),
            applies_to_all_language_classes=True,
            notes="Bulk midterm reset for all language classes",
        )

        final_reset = TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.FINAL,
            reset_date=date(2024, 12, 1),
            applies_to_all_language_classes=True,
            notes="Bulk final reset for all language classes",
        )

        # Should apply to all 6 language classes (3 IEAP + 3 GESL)
        self.assertEqual(midterm_reset.applicable_classes_count, 6)
        self.assertEqual(final_reset.applicable_classes_count, 6)

        # Test that all classes get the correct reset dates
        for class_header in self.ieap_classes + self.gesl_classes:
            midterm_date = TestPeriodReset.get_reset_date_for_class(class_header, TestPeriodReset.TestType.MIDTERM)
            final_date = TestPeriodReset.get_reset_date_for_class(class_header, TestPeriodReset.TestType.FINAL)

            self.assertEqual(midterm_date, date(2024, 10, 15))
            self.assertEqual(final_date, date(2024, 12, 1))

    def test_ieap_three_test_scenario(self):
        """Test IEAP three-test scenario."""
        # Create IEAP-specific resets
        test_dates = [
            (TestPeriodReset.TestType.IEAP_TEST_1, date(2024, 9, 30)),
            (TestPeriodReset.TestType.IEAP_TEST_2, date(2024, 10, 30)),
            (TestPeriodReset.TestType.IEAP_TEST_3, date(2024, 11, 30)),
        ]

        ieap_resets = []
        for test_type, reset_date in test_dates:
            reset = TestPeriodReset.objects.create(
                term=self.term,
                test_type=test_type,
                reset_date=reset_date,
                applies_to_all_language_classes=False,
                notes=f"IEAP {test_type} reset",
            )
            # Apply only to IEAP classes
            reset.specific_classes.set(self.ieap_classes)
            ieap_resets.append(reset)

        # Verify IEAP classes get all three reset dates
        for ieap_class in self.ieap_classes:
            for test_type, expected_date in test_dates:
                reset_date = TestPeriodReset.get_reset_date_for_class(ieap_class, test_type)
                self.assertEqual(reset_date, expected_date)

        # Verify GESL classes don't get IEAP reset dates
        for gesl_class in self.gesl_classes:
            for test_type, _ in test_dates:
                reset_date = TestPeriodReset.get_reset_date_for_class(gesl_class, test_type)
                self.assertIsNone(reset_date)

    def test_override_scenario(self):
        """Test override scenario where one class has different dates."""
        # Create general reset for all
        TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2024, 10, 15),
            applies_to_all_language_classes=True,
        )

        # Create override for one specific class
        special_class = self.gesl_classes[0]  # GESL Section A
        override_reset = TestPeriodReset.objects.create(
            term=self.term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2024, 10, 20),  # 5 days later
            applies_to_all_language_classes=False,
            notes="Special schedule for GESL Section A",
        )
        override_reset.specific_classes.add(special_class)

        # Verify override class gets special date
        override_date = TestPeriodReset.get_reset_date_for_class(special_class, TestPeriodReset.TestType.MIDTERM)
        self.assertEqual(override_date, date(2024, 10, 20))

        # Verify other classes get general date
        for class_header in self.ieap_classes + self.gesl_classes[1:]:
            general_date = TestPeriodReset.get_reset_date_for_class(class_header, TestPeriodReset.TestType.MIDTERM)
            self.assertEqual(general_date, date(2024, 10, 15))

    def test_term_reset_summary(self):
        """Test getting complete reset summary for a term."""
        # Create comprehensive resets
        resets_data = [
            (TestPeriodReset.TestType.MIDTERM, date(2024, 10, 15)),
            (TestPeriodReset.TestType.FINAL, date(2024, 12, 1)),
            (TestPeriodReset.TestType.IEAP_TEST_1, date(2024, 9, 30)),
        ]

        for test_type, reset_date in resets_data:
            TestPeriodReset.objects.create(
                term=self.term,
                test_type=test_type,
                reset_date=reset_date,
                applies_to_all_language_classes=True,
            )

        # Get all reset dates for term
        all_resets = TestPeriodReset.get_all_reset_dates_for_term(self.term)

        expected = {
            TestPeriodReset.TestType.MIDTERM: date(2024, 10, 15),
            TestPeriodReset.TestType.FINAL: date(2024, 12, 1),
            TestPeriodReset.TestType.IEAP_TEST_1: date(2024, 9, 30),
        }
        self.assertEqual(all_resets, expected)


@pytest.mark.django_db
class TestTestPeriodResetConstraints:
    """Test database constraints and edge cases for TestPeriodReset."""

    def test_specific_and_general_resets_allowed(self):
        """Test that specific and general resets can coexist for different test types."""
        # Setup
        lang_division = Division.objects.create(name="Language Division", short_name="LANG")
        Cycle.objects.create(division=lang_division, name="Language Programs")
        course = Course.objects.create(
            code="TEST01",
            title="Test Course",
            short_title="Test",
            division=lang_division,
            cycle="LANGUAGE",
            is_language=True,
        )
        term = Term.objects.create(
            name="Test Term",
            term_type="ENG_A",
            start_date=date(2024, 9, 1),
            end_date=date(2024, 12, 15),
        )

        class1 = ClassHeader.objects.create(course=course, term=term, section_id="A")

        # Create general reset for midterm
        general_reset = TestPeriodReset.objects.create(
            term=term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2024, 10, 15),
            applies_to_all_language_classes=True,
        )

        # Create specific reset for final (different test type)
        specific_reset = TestPeriodReset.objects.create(
            term=term,
            test_type=TestPeriodReset.TestType.FINAL,
            reset_date=date(2024, 11, 20),
            applies_to_all_language_classes=False,
        )
        specific_reset.specific_classes.add(class1)

        # Should not raise any errors due to different test types
        assert general_reset.pk != specific_reset.pk
        assert general_reset.applies_to_all_language_classes
        assert not specific_reset.applies_to_all_language_classes
        assert specific_reset.specific_classes.count() == 1

    def test_duplicate_constraint_violation(self):
        """Test that duplicate resets with same term/test_type/applies_to_all are prevented."""
        # Setup
        lang_division = Division.objects.create(name="Language Division", short_name="LANG")
        Cycle.objects.create(division=lang_division, name="Language Programs")
        Course.objects.create(
            code="TEST01",
            title="Test Course",
            short_title="Test",
            division=lang_division,
            cycle="LANGUAGE",
            is_language=True,
        )
        term = Term.objects.create(
            name="Test Term",
            term_type="ENG_A",
            start_date=date(2024, 9, 1),
            end_date=date(2024, 12, 15),
        )

        # Create first specific reset
        TestPeriodReset.objects.create(
            term=term,
            test_type=TestPeriodReset.TestType.MIDTERM,
            reset_date=date(2024, 10, 15),
            applies_to_all_language_classes=False,
        )

        with pytest.raises(IntegrityError):
            TestPeriodReset.objects.create(
                term=term,
                test_type=TestPeriodReset.TestType.MIDTERM,
                reset_date=date(2024, 10, 20),  # Different date
                applies_to_all_language_classes=False,  # Same constraint values
            )
