"""Tests for the separated pricing model architecture.

This module tests the new separated pricing models and services
to ensure business rules are correctly implemented.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.curriculum.models import Course, Cycle
from apps.finance.models import (
    DefaultPricing,
    ReadingClassPricing,
    SeniorProjectCourse,
    SeniorProjectPricing,
)
from apps.finance.services.separated_pricing_service import (
    DefaultPricingService,
    SeparatedPricingService,
)

User = get_user_model()


class DefaultPricingModelTest(TestCase):
    """Test DefaultPricing model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user("testuser", "test@test.com", "password")
        self.cycle = Cycle.objects.create(
            name="Bachelor of Arts",
            abbreviation="BA",
            created_by=self.user,
            updated_by=self.user,
        )

    def test_default_pricing_creation(self):
        """Test creating default pricing."""
        pricing = DefaultPricing.objects.create(
            cycle=self.cycle,
            domestic_price=Decimal("250.00"),
            foreign_price=Decimal("350.00"),
            effective_date=date.today(),
            created_by=self.user,
            updated_by=self.user,
        )

        self.assertEqual(pricing.cycle, self.cycle)
        self.assertEqual(pricing.domestic_price, Decimal("250.00"))
        self.assertEqual(pricing.foreign_price, Decimal("350.00"))
        self.assertTrue(pricing.is_current)

    def test_get_price_for_student(self):
        """Test price retrieval for different student types."""
        pricing = DefaultPricing.objects.create(
            cycle=self.cycle,
            domestic_price=Decimal("250.00"),
            foreign_price=Decimal("350.00"),
            effective_date=date.today(),
            created_by=self.user,
            updated_by=self.user,
        )

        self.assertEqual(pricing.get_price_for_student(False), Decimal("250.00"))
        self.assertEqual(pricing.get_price_for_student(True), Decimal("350.00"))

    def test_unique_constraint_same_cycle_date(self):
        """Test unique constraint prevents duplicate pricing for same cycle/date."""
        DefaultPricing.objects.create(
            cycle=self.cycle,
            domestic_price=Decimal("250.00"),
            foreign_price=Decimal("350.00"),
            effective_date=date.today(),
            created_by=self.user,
            updated_by=self.user,
        )

        with self.assertRaises(IntegrityError):
            DefaultPricing.objects.create(
                cycle=self.cycle,
                domestic_price=Decimal("300.00"),
                foreign_price=Decimal("400.00"),
                effective_date=date.today(),
                created_by=self.user,
                updated_by=self.user,
            )

    def test_overlapping_periods_prevention(self):
        """Test that overlapping effective periods are prevented."""
        # Create initial pricing
        DefaultPricing.objects.create(
            cycle=self.cycle,
            domestic_price=Decimal("250.00"),
            foreign_price=Decimal("350.00"),
            effective_date=date.today(),
            end_date=None,  # Current pricing
            created_by=self.user,
            updated_by=self.user,
        )

        # This should fail due to unique constraint for current pricing
        with self.assertRaises(IntegrityError):
            DefaultPricing.objects.create(
                cycle=self.cycle,
                domestic_price=Decimal("300.00"),
                foreign_price=Decimal("400.00"),
                effective_date=date.today() + timedelta(days=30),
                end_date=None,  # Another current pricing
                created_by=self.user,
                updated_by=self.user,
            )


class SeniorProjectPricingModelTest(TestCase):
    """Test SeniorProjectPricing model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user("testuser", "test@test.com", "password")

    def test_senior_project_pricing_creation(self):
        """Test creating senior project pricing."""
        pricing = SeniorProjectPricing.objects.create(
            tier=SeniorProjectPricing.GroupSizeTier.INDIVIDUAL,
            total_price=Decimal("600.00"),
            foreign_price=Decimal("800.00"),
            advisor_payment=Decimal("100.00"),
            committee_payment=Decimal("50.00"),
            effective_date=date.today(),
            created_by=self.user,
            updated_by=self.user,
        )

        self.assertEqual(pricing.tier, SeniorProjectPricing.GroupSizeTier.INDIVIDUAL)
        self.assertEqual(pricing.total_price, Decimal("600.00"))
        self.assertEqual(pricing.foreign_price, Decimal("800.00"))

    def test_get_price_per_student_calculation(self):
        """Test per-student price calculation for different group sizes."""
        pricing = SeniorProjectPricing.objects.create(
            tier=SeniorProjectPricing.GroupSizeTier.INDIVIDUAL,
            total_price=Decimal("600.00"),
            foreign_price=Decimal("800.00"),
            advisor_payment=Decimal("100.00"),
            committee_payment=Decimal("50.00"),
            effective_date=date.today(),
            created_by=self.user,
            updated_by=self.user,
        )

        # Test different group sizes
        self.assertEqual(pricing.get_price_per_student(1, False), Decimal("600.00"))
        self.assertEqual(pricing.get_price_per_student(2, False), Decimal("300.00"))
        self.assertEqual(pricing.get_price_per_student(1, True), Decimal("800.00"))
        self.assertEqual(pricing.get_price_per_student(2, True), Decimal("400.00"))


class ReadingClassPricingModelTest(TestCase):
    """Test ReadingClassPricing model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user("testuser", "test@test.com", "password")
        self.cycle = Cycle.objects.create(
            name="Bachelor of Arts",
            abbreviation="BA",
            created_by=self.user,
            updated_by=self.user,
        )

    def test_reading_class_pricing_creation(self):
        """Test creating reading class pricing."""
        pricing = ReadingClassPricing.objects.create(
            cycle=self.cycle,
            tier=ReadingClassPricing.ClassSizeTier.TUTORIAL,
            price_per_student=Decimal("200.00"),
            minimum_revenue=Decimal("300.00"),
            effective_date=date.today(),
            created_by=self.user,
            updated_by=self.user,
        )

        self.assertEqual(pricing.cycle, self.cycle)
        self.assertEqual(pricing.tier, ReadingClassPricing.ClassSizeTier.TUTORIAL)
        self.assertEqual(pricing.price_per_student, Decimal("200.00"))
        self.assertEqual(pricing.minimum_revenue, Decimal("300.00"))

    def test_calculate_total_charge(self):
        """Test total charge calculation with minimum revenue."""
        pricing = ReadingClassPricing.objects.create(
            cycle=self.cycle,
            tier=ReadingClassPricing.ClassSizeTier.TUTORIAL,
            price_per_student=Decimal("200.00"),
            minimum_revenue=Decimal("300.00"),
            effective_date=date.today(),
            created_by=self.user,
            updated_by=self.user,
        )

        # Test with enrollment below minimum revenue threshold
        self.assertEqual(pricing.calculate_total_charge(1), Decimal("300.00"))  # Uses minimum

        # Test with enrollment above minimum revenue threshold
        self.assertEqual(pricing.calculate_total_charge(2), Decimal("400.00"))  # Uses per-student

    def test_calculate_per_student_charge(self):
        """Test per-student charge calculation considering minimum revenue."""
        pricing = ReadingClassPricing.objects.create(
            cycle=self.cycle,
            tier=ReadingClassPricing.ClassSizeTier.TUTORIAL,
            price_per_student=Decimal("200.00"),
            minimum_revenue=Decimal("300.00"),
            effective_date=date.today(),
            created_by=self.user,
            updated_by=self.user,
        )

        # Test with enrollment requiring minimum revenue adjustment
        self.assertEqual(pricing.calculate_per_student_charge(1), Decimal("300.00"))  # $300 ÷ 1

        # Test with enrollment where per-student rate applies
        self.assertEqual(pricing.calculate_per_student_charge(2), Decimal("200.00"))  # $400 ÷ 2


class SeniorProjectCourseModelTest(TestCase):
    """Test SeniorProjectCourse model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user("testuser", "test@test.com", "password")
        self.cycle = Cycle.objects.create(
            name="Bachelor of Arts",
            abbreviation="BA",
            created_by=self.user,
            updated_by=self.user,
        )
        self.course = Course.objects.create(
            code="IR-489",
            title="International Relations Senior Project",
            cycle=self.cycle,
            credits=Decimal("3.0"),
            created_by=self.user,
            updated_by=self.user,
        )

    def test_senior_project_course_creation(self):
        """Test creating senior project course configuration."""
        config = SeniorProjectCourse.objects.create(
            course=self.course,
            is_active=True,
            created_by=self.user,
            updated_by=self.user,
        )

        self.assertEqual(config.course, self.course)
        self.assertTrue(config.is_active)

    def test_one_to_one_constraint(self):
        """Test that each course can only have one senior project configuration."""
        SeniorProjectCourse.objects.create(
            course=self.course,
            is_active=True,
            created_by=self.user,
            updated_by=self.user,
        )

        with self.assertRaises(IntegrityError):
            SeniorProjectCourse.objects.create(
                course=self.course,
                is_active=False,
                created_by=self.user,
                updated_by=self.user,
            )


class DefaultPricingServiceTest(TestCase):
    """Test DefaultPricingService functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user("testuser", "test@test.com", "password")
        self.cycle = Cycle.objects.create(
            name="Bachelor of Arts",
            abbreviation="BA",
            created_by=self.user,
            updated_by=self.user,
        )

    def test_get_current_price(self):
        """Test retrieving current default price."""
        DefaultPricing.objects.create(
            cycle=self.cycle,
            domestic_price=Decimal("250.00"),
            foreign_price=Decimal("350.00"),
            effective_date=date.today(),
            created_by=self.user,
            updated_by=self.user,
        )

        price, description = DefaultPricingService.get_price(self.cycle, False)
        self.assertEqual(price, Decimal("250.00"))
        self.assertIn("Default", description)
        self.assertIn("BA", description)

        price, description = DefaultPricingService.get_price(self.cycle, True)
        self.assertEqual(price, Decimal("350.00"))

    def test_no_pricing_found(self):
        """Test error when no pricing is found."""
        with self.assertRaises(ValidationError):
            DefaultPricingService.get_price(self.cycle, False)


class SeparatedPricingServiceTest(TestCase):
    """Test the main SeparatedPricingService functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user("testuser", "test@test.com", "password")
        self.cycle = Cycle.objects.create(
            name="Bachelor of Arts",
            abbreviation="BA",
            created_by=self.user,
            updated_by=self.user,
        )
        self.course = Course.objects.create(
            code="HIST-101",
            title="Introduction to History",
            cycle=self.cycle,
            credits=Decimal("3.0"),
            created_by=self.user,
            updated_by=self.user,
        )

        # Create default pricing
        DefaultPricing.objects.create(
            cycle=self.cycle,
            domestic_price=Decimal("250.00"),
            foreign_price=Decimal("350.00"),
            effective_date=date.today(),
            created_by=self.user,
            updated_by=self.user,
        )

    def test_is_senior_project_detection(self):
        """Test senior project course detection."""
        # Initially not a senior project
        self.assertFalse(SeparatedPricingService._is_senior_project(self.course))

        # Configure as senior project
        SeniorProjectCourse.objects.create(
            course=self.course,
            is_active=True,
            created_by=self.user,
            updated_by=self.user,
        )

        self.assertTrue(SeparatedPricingService._is_senior_project(self.course))

        # Deactivate senior project configuration
        config = SeniorProjectCourse.objects.get(course=self.course)
        config.is_active = False
        config.save()

        self.assertFalse(SeparatedPricingService._is_senior_project(self.course))


@pytest.mark.django_db
class TestPricingConstraints:
    """Test database constraints and business rules."""

    def test_end_date_after_effective_date(self):
        """Test that end_date must be after effective_date."""
        user = User.objects.create_user("testuser", "test@test.com", "password")
        cycle = Cycle.objects.create(name="Bachelor of Arts", abbreviation="BA", created_by=user, updated_by=user)

        pricing = DefaultPricing(
            cycle=cycle,
            domestic_price=Decimal("250.00"),
            foreign_price=Decimal("350.00"),
            effective_date=date.today(),
            end_date=date.today() - timedelta(days=1),  # End before start
            created_by=user,
            updated_by=user,
        )

        with pytest.raises(ValidationError):
            pricing.full_clean()

    def test_price_validation(self):
        """Test that prices must be non-negative."""
        user = User.objects.create_user("testuser", "test@test.com", "password")
        cycle = Cycle.objects.create(name="Bachelor of Arts", abbreviation="BA", created_by=user, updated_by=user)

        pricing = DefaultPricing(
            cycle=cycle,
            domestic_price=Decimal("-10.00"),  # Negative price
            foreign_price=Decimal("350.00"),
            effective_date=date.today(),
            created_by=user,
            updated_by=user,
        )

        with pytest.raises(ValidationError):
            pricing.full_clean()


class PricingBusinessRulesTest(TestCase):
    """Test business rules implementation."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user("testuser", "test@test.com", "password")
        self.cycle = Cycle.objects.create(
            name="Bachelor of Arts",
            abbreviation="BA",
            created_by=self.user,
            updated_by=self.user,
        )

    def test_overlapping_periods_prevented(self):
        """Test that overlapping effective periods are prevented by constraints."""
        # Create first pricing
        DefaultPricing.objects.create(
            cycle=self.cycle,
            domestic_price=Decimal("250.00"),
            foreign_price=Decimal("350.00"),
            effective_date=date.today(),
            end_date=None,  # Current/active pricing
            created_by=self.user,
            updated_by=self.user,
        )

        with self.assertRaises(IntegrityError):
            DefaultPricing.objects.create(
                cycle=self.cycle,
                domestic_price=Decimal("300.00"),
                foreign_price=Decimal("400.00"),
                effective_date=date.today() + timedelta(days=10),
                end_date=None,  # Another current pricing - should conflict
                created_by=self.user,
                updated_by=self.user,
            )

    def test_historical_pricing_preserved(self):
        """Test that historical pricing is preserved."""
        # Create historical pricing
        old_pricing = DefaultPricing.objects.create(
            cycle=self.cycle,
            domestic_price=Decimal("200.00"),
            foreign_price=Decimal("300.00"),
            effective_date=date.today() - timedelta(days=365),
            end_date=date.today() - timedelta(days=1),
            created_by=self.user,
            updated_by=self.user,
        )

        # Create current pricing
        current_pricing = DefaultPricing.objects.create(
            cycle=self.cycle,
            domestic_price=Decimal("250.00"),
            foreign_price=Decimal("350.00"),
            effective_date=date.today(),
            end_date=None,
            created_by=self.user,
            updated_by=self.user,
        )

        # Both should exist
        self.assertEqual(DefaultPricing.objects.filter(cycle=self.cycle).count(), 2)

        # Historical pricing should not be current
        old_pricing.refresh_from_db()
        self.assertFalse(old_pricing.is_current)

        # Current pricing should be current
        current_pricing.refresh_from_db()
        self.assertTrue(current_pricing.is_current)
