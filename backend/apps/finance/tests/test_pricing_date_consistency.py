"""
Tests for pricing date consistency across all pricing services.

Critical business rule: Pricing is determined by term.start_date, not payment date.
This test ensures all pricing services follow the same date logic.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.utils import timezone

from apps.curriculum.models import Course, Cycle, Division, Term
from apps.finance.models import (
    CourseFixedPricing,
    DefaultPricing,
    ReadingClassPricing,
    SeniorProjectCourse,
    SeniorProjectPricing,
)
from apps.finance.services.separated_pricing_service import (
    CourseFixedPricingService,
    DefaultPricingService,
    ReadingClassPricingService,
    SeniorProjectPricingService,
    SeparatedPricingService,
)
from apps.people.models import Person, StudentProfile
from apps.scheduling.models import ClassHeader


@pytest.mark.django_db
class TestPricingDateConsistency:
    """Test that all pricing services use consistent date logic."""

    @pytest.fixture
    def setup_test_data(self):
        """Set up test data for pricing consistency tests."""
        # Create division and cycle
        division = Division.objects.create(name="Test Division", short_name="TD", is_active=True, display_order=1)
        cycle = Cycle.objects.create(
            division=division,
            name="Test Cycle",
            short_name="TC",
            typical_duration_terms=8,
            is_active=True,
            display_order=1,
        )

        # Create course
        course = Course.objects.create(
            code="TEST-101",
            title="Test Course",
            short_title="Test",
            cycle=cycle,
            credits=3,
            start_date=date(2020, 1, 1),
            is_active=True,
        )

        # Create terms with different dates
        old_term = Term.objects.create(
            code="OLD-2022",
            description="Old Term 2022",
            term_type="BA",
            start_date=date(2022, 1, 15),
            end_date=date(2022, 5, 15),
            is_active=True,
        )

        current_term = Term.objects.create(
            code="CUR-2023",
            description="Current Term 2023",
            term_type="BA",
            start_date=date(2023, 1, 15),
            end_date=date(2023, 5, 15),
            is_active=True,
        )

        # Create student
        person = Person.objects.create(
            first_name="Test",
            last_name="Student",
            email="test@example.com",
            gender="M",
            date_of_birth=date(1990, 1, 1),
            primary_nationality="US",
        )
        student = StudentProfile.objects.create(person=person, student_id=12345, is_current_student=True)

        # Create pricing records with different effective dates
        self.create_pricing_records(cycle, course, old_term, current_term)

        return {
            "cycle": cycle,
            "course": course,
            "old_term": old_term,
            "current_term": current_term,
            "student": student,
            "division": division,
        }

    def create_pricing_records(self, cycle, course, old_term, current_term):
        """Create pricing records for different time periods."""

        # Old pricing (effective during old_term)
        DefaultPricing.objects.create(
            cycle=cycle,
            domestic_price=Decimal("100.00"),
            foreign_price=Decimal("150.00"),
            effective_date=date(2022, 1, 1),
            end_date=date(2022, 12, 31),
        )

        CourseFixedPricing.objects.create(
            course=course,
            domestic_price=Decimal("200.00"),
            foreign_price=Decimal("250.00"),
            effective_date=date(2022, 1, 1),
            end_date=date(2022, 12, 31),
        )

        SeniorProjectPricing.objects.create(
            tier=SeniorProjectPricing.GroupSizeTier.INDIVIDUAL,
            individual_price=Decimal("300.00"),
            foreign_individual_price=Decimal("350.00"),
            advisor_payment=Decimal("50.00"),
            committee_payment=Decimal("25.00"),
            effective_date=date(2022, 1, 1),
            end_date=date(2022, 12, 31),
        )

        ReadingClassPricing.objects.create(
            cycle=cycle,
            tier=ReadingClassPricing.ClassSizeTier.SMALL,
            domestic_price=Decimal("400.00"),
            foreign_price=Decimal("450.00"),
            effective_date=date(2022, 1, 1),
            end_date=date(2022, 12, 31),
        )

        # Current pricing (effective during current_term)
        DefaultPricing.objects.create(
            cycle=cycle,
            domestic_price=Decimal("110.00"),
            foreign_price=Decimal("160.00"),
            effective_date=date(2023, 1, 1),
            end_date=None,  # Current pricing
        )

        CourseFixedPricing.objects.create(
            course=course,
            domestic_price=Decimal("220.00"),
            foreign_price=Decimal("270.00"),
            effective_date=date(2023, 1, 1),
            end_date=None,  # Current pricing
        )

        SeniorProjectPricing.objects.create(
            tier=SeniorProjectPricing.GroupSizeTier.INDIVIDUAL,
            individual_price=Decimal("330.00"),
            foreign_individual_price=Decimal("380.00"),
            advisor_payment=Decimal("55.00"),
            committee_payment=Decimal("30.00"),
            effective_date=date(2023, 1, 1),
            end_date=None,  # Current pricing
        )

        ReadingClassPricing.objects.create(
            cycle=cycle,
            tier=ReadingClassPricing.ClassSizeTier.SMALL,
            domestic_price=Decimal("440.00"),
            foreign_price=Decimal("490.00"),
            effective_date=date(2023, 1, 1),
            end_date=None,  # Current pricing
        )

    def test_shared_pricing_date_method(self, setup_test_data):
        """Test that the shared get_pricing_date method works correctly."""
        data = setup_test_data

        # Test with term provided - should return term.start_date
        pricing_date = SeparatedPricingService.get_pricing_date(data["old_term"])
        assert pricing_date == data["old_term"].start_date

        pricing_date = SeparatedPricingService.get_pricing_date(data["current_term"])
        assert pricing_date == data["current_term"].start_date

        # Test without term - should return today
        today = timezone.now().date()
        pricing_date = SeparatedPricingService.get_pricing_date(None)
        assert pricing_date == today

    def test_shared_active_pricing_method(self, setup_test_data):
        """Test that the shared get_active_pricing method works correctly."""
        data = setup_test_data

        # Test finding pricing active during old term
        old_pricing = SeparatedPricingService.get_active_pricing(
            DefaultPricing.objects.filter(cycle=data["cycle"]),
            data["old_term"].start_date,
        )
        assert old_pricing is not None
        assert old_pricing.domestic_price == Decimal("100.00")

        # Test finding pricing active during current term
        current_pricing = SeparatedPricingService.get_active_pricing(
            DefaultPricing.objects.filter(cycle=data["cycle"]),
            data["current_term"].start_date,
        )
        assert current_pricing is not None
        assert current_pricing.domestic_price == Decimal("110.00")

    def test_default_pricing_uses_term_date(self, setup_test_data):
        """Test DefaultPricingService uses term start date, not today."""
        data = setup_test_data

        # When pricing for old term, should get old pricing
        price, description = DefaultPricingService.get_price(data["cycle"], is_foreign=False, term=data["old_term"])
        assert price == Decimal("100.00")

        # When pricing for current term, should get current pricing
        price, description = DefaultPricingService.get_price(
            data["cycle"], is_foreign=False, term=data["current_term"]
        )
        assert price == Decimal("110.00")

        # Foreign student pricing
        price, description = DefaultPricingService.get_price(data["cycle"], is_foreign=True, term=data["old_term"])
        assert price == Decimal("150.00")

    def test_course_fixed_pricing_uses_term_date(self, setup_test_data):
        """Test CourseFixedPricingService uses term start date, not today."""
        data = setup_test_data

        # When pricing for old term, should get old pricing
        price = CourseFixedPricingService.get_price(data["course"], is_foreign=False, term=data["old_term"])
        assert price == Decimal("200.00")

        # When pricing for current term, should get current pricing
        price = CourseFixedPricingService.get_price(data["course"], is_foreign=False, term=data["current_term"])
        assert price == Decimal("220.00")

        # Foreign student pricing
        price = CourseFixedPricingService.get_price(data["course"], is_foreign=True, term=data["old_term"])
        assert price == Decimal("250.00")

    def test_senior_project_pricing_uses_term_date(self, setup_test_data):
        """Test SeniorProjectPricingService uses term start date, not today."""
        data = setup_test_data

        # Create senior project course
        SeniorProjectCourse.objects.create(
            course=data["course"],
            project_code="SP-TEST",
            major_name="Test Major",
            allows_groups=True,
            is_active=True,
        )

        # When pricing for old term, should get old pricing
        price, description = SeniorProjectPricingService.calculate_price(
            data["course"], data["student"], data["old_term"], is_foreign=False
        )
        assert price == Decimal("300.00")

        # When pricing for current term, should get current pricing
        price, description = SeniorProjectPricingService.calculate_price(
            data["course"], data["student"], data["current_term"], is_foreign=False
        )
        assert price == Decimal("330.00")

        # Foreign student pricing
        price, description = SeniorProjectPricingService.calculate_price(
            data["course"], data["student"], data["old_term"], is_foreign=True
        )
        assert price == Decimal("350.00")

    def test_reading_class_pricing_uses_term_date(self, setup_test_data):
        """Test ReadingClassPricingService uses term start date, not today."""
        data = setup_test_data

        # Create class header for reading class
        class_header = ClassHeader.objects.create(
            course=data["course"],
            term=data["old_term"],
            section="A",
            class_type="READING",
            is_reading_class=True,
            max_enrollment=5,
        )

        # When pricing for old term, should get old pricing
        price, description = ReadingClassPricingService.calculate_price(
            class_header, data["student"], is_foreign=False, term=data["old_term"]
        )
        assert price == Decimal("400.00")

        # Update class_header term and test current pricing
        class_header.term = data["current_term"]
        class_header.save()

        price, description = ReadingClassPricingService.calculate_price(
            class_header, data["student"], is_foreign=False, term=data["current_term"]
        )
        assert price == Decimal("440.00")

        # Foreign student pricing
        class_header.term = data["old_term"]
        class_header.save()

        price, description = ReadingClassPricingService.calculate_price(
            class_header, data["student"], is_foreign=True, term=data["old_term"]
        )
        assert price == Decimal("450.00")

    def test_all_services_consistent_with_no_term(self, setup_test_data):
        """Test all services behave consistently when no term is provided."""
        data = setup_test_data

        # All services should fall back to current pricing when no term provided
        # (using today's date which should match current pricing)

        default_price, _ = DefaultPricingService.get_price(data["cycle"], is_foreign=False, term=None)
        assert default_price == Decimal("110.00")  # Current pricing

        fixed_price = CourseFixedPricingService.get_price(data["course"], is_foreign=False, term=None)
        assert fixed_price == Decimal("220.00")  # Current pricing

    def test_pricing_date_business_rule_enforcement(self, setup_test_data):
        """Test that the business rule is enforced: term date, not payment date."""
        data = setup_test_data

        # Student enrolled in old term but paying today
        # Should get OLD term pricing, not current pricing

        # Simulate: Student took course in old term (Jan 2022)
        # Payment made today (2023 or later)
        # Should use 2022 pricing, not 2023 pricing

        price, description = DefaultPricingService.get_price(data["cycle"], is_foreign=False, term=data["old_term"])

        # Should get OLD pricing (100.00), not current pricing (110.00)
        assert price == Decimal("100.00")
        assert "Default Test Cycle Pricing" in description

        # This test proves: "It isn't payment DATE that matters but the term
        # that the course took place in"


@pytest.mark.django_db
class TestReadingClassPricingModelChanges:
    """Test the ReadingClassPricing model changes work correctly."""

    @pytest.fixture
    def setup_reading_class_data(self):
        """Set up test data for reading class pricing."""
        division = Division.objects.create(name="Test Division", short_name="TD", is_active=True, display_order=1)
        cycle = Cycle.objects.create(
            division=division,
            name="Test Cycle",
            short_name="TC",
            typical_duration_terms=8,
            is_active=True,
            display_order=1,
        )

        return {"cycle": cycle}

    def test_reading_class_pricing_model_fields(self, setup_reading_class_data):
        """Test that ReadingClassPricing has correct fields."""
        data = setup_reading_class_data

        pricing = ReadingClassPricing.objects.create(
            cycle=data["cycle"],
            tier=ReadingClassPricing.ClassSizeTier.SMALL,
            domestic_price=Decimal("100.00"),
            foreign_price=Decimal("150.00"),
            effective_date=date(2023, 1, 1),
        )

        assert pricing.domestic_price == Decimal("100.00")
        assert pricing.foreign_price == Decimal("150.00")
        assert hasattr(pricing, "get_price_for_student")

        # Test get_price_for_student method
        assert pricing.get_price_for_student(is_foreign=False) == Decimal("100.00")
        assert pricing.get_price_for_student(is_foreign=True) == Decimal("150.00")

    def test_reading_class_pricing_string_representation(self, setup_reading_class_data):
        """Test ReadingClassPricing string representation."""
        data = setup_reading_class_data

        pricing = ReadingClassPricing.objects.create(
            cycle=data["cycle"],
            tier=ReadingClassPricing.ClassSizeTier.TUTORIAL,
            domestic_price=Decimal("200.00"),
            foreign_price=Decimal("250.00"),
            effective_date=date(2023, 1, 1),
        )

        expected = "Test Cycle Reading 1-2: $200.00/$250.00"
        assert str(pricing) == expected

    def test_reading_class_model_no_minimum_revenue(self, setup_reading_class_data):
        """Test that minimum revenue concept is completely removed."""
        data = setup_reading_class_data

        pricing = ReadingClassPricing.objects.create(
            cycle=data["cycle"],
            tier=ReadingClassPricing.ClassSizeTier.MEDIUM,
            domestic_price=Decimal("75.00"),
            foreign_price=Decimal("100.00"),
            effective_date=date(2023, 1, 1),
        )

        # Should not have minimum revenue fields or methods
        assert not hasattr(pricing, "minimum_revenue")
        assert not hasattr(pricing, "price_per_student")
        assert not hasattr(pricing, "calculate_total_charge")
        assert not hasattr(pricing, "calculate_per_student_charge")

        # Should have simple domestic/foreign pricing
        assert hasattr(pricing, "domestic_price")
        assert hasattr(pricing, "foreign_price")
        assert hasattr(pricing, "get_price_for_student")


@pytest.mark.django_db
class TestPricingServiceIntegration:
    """Integration tests for the complete pricing system."""

    @pytest.fixture
    def complete_setup(self):
        """Complete setup for integration testing."""
        # Create all necessary objects
        division = Division.objects.create(name="Business", short_name="BUS", is_active=True, display_order=1)
        cycle = Cycle.objects.create(
            division=division,
            name="Bachelor",
            short_name="BA",
            typical_duration_terms=8,
            is_active=True,
            display_order=1,
        )

        course = Course.objects.create(
            code="BUS-101",
            title="Business Fundamentals",
            short_title="Bus Fund",
            cycle=cycle,
            credits=3,
            start_date=date(2020, 1, 1),
            is_active=True,
        )

        term = Term.objects.create(
            code="SP2023",
            description="Spring 2023",
            term_type="BA",
            start_date=date(2023, 1, 15),
            end_date=date(2023, 5, 15),
            is_active=True,
        )

        person = Person.objects.create(
            first_name="Jane",
            last_name="Doe",
            email="jane@example.com",
            gender="F",
            date_of_birth=date(1995, 3, 15),
            primary_nationality="KH",
        )

        student = StudentProfile.objects.create(person=person, student_id=54321, is_current_student=True)

        # Create pricing for the term
        DefaultPricing.objects.create(
            cycle=cycle,
            domestic_price=Decimal("500.00"),
            foreign_price=Decimal("750.00"),
            effective_date=date(2023, 1, 1),
            end_date=None,
        )

        return {
            "cycle": cycle,
            "course": course,
            "term": term,
            "student": student,
            "division": division,
        }

    def test_main_pricing_service_orchestration(self, complete_setup):
        """Test that the main SeparatedPricingService orchestrates correctly."""
        data = complete_setup

        # Test default pricing (no fixed pricing set)
        price, description = SeparatedPricingService.calculate_course_price(
            data["course"], data["student"], data["term"]
        )

        # Should use default pricing for domestic student (KH = Cambodia = domestic)
        assert price == Decimal("500.00")
        assert "Default Bachelor Pricing" in description

        # Test with international student
        data["student"].person.primary_nationality = "US"
        data["student"].person.save()

        price, description = SeparatedPricingService.calculate_course_price(
            data["course"], data["student"], data["term"]
        )

        # Should use foreign pricing
        assert price == Decimal("750.00")
        assert "Default Bachelor Pricing" in description

    def test_fixed_pricing_override(self, complete_setup):
        """Test that fixed pricing overrides default pricing."""
        data = complete_setup

        # Add fixed pricing for this course
        CourseFixedPricing.objects.create(
            course=data["course"],
            domestic_price=Decimal("600.00"),
            foreign_price=Decimal("800.00"),
            effective_date=date(2023, 1, 1),
            end_date=None,
        )

        # Should now use fixed pricing instead of default
        price, description = SeparatedPricingService.calculate_course_price(
            data["course"], data["student"], data["term"]
        )

        assert price == Decimal("600.00")  # Fixed pricing, not default 500.00
        assert description == "Fixed Course Pricing"
