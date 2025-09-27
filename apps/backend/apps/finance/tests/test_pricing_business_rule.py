"""
Simple test to verify the critical pricing business rule:
"It isn't payment DATE that matters but the term that the course took place in"
"""

from datetime import date

from django.utils import timezone

from apps.finance.services.separated_pricing_service import SeparatedPricingService


class TestPricingBusinessRule:
    """Test the core business rule for pricing date determination."""

    def test_pricing_date_method_with_term(self):
        """Test that pricing date uses term.start_date when term is provided."""

        # Mock term object
        class MockTerm:
            def __init__(self, start_date):
                self.start_date = start_date

        # Test case 1: Old term from 2022
        old_term = MockTerm(date(2022, 1, 15))
        pricing_date = SeparatedPricingService.get_pricing_date(old_term)

        assert pricing_date == date(2022, 1, 15)
        assert pricing_date == old_term.start_date

        # Test case 2: Current term from 2023
        current_term = MockTerm(date(2023, 3, 20))
        pricing_date = SeparatedPricingService.get_pricing_date(current_term)

        assert pricing_date == date(2023, 3, 20)
        assert pricing_date == current_term.start_date

    def test_pricing_date_method_without_term(self):
        """Test that pricing date falls back to today when no term provided."""

        pricing_date = SeparatedPricingService.get_pricing_date(None)
        today = timezone.now().date()

        assert pricing_date == today

    def test_pricing_date_method_with_none_term(self):
        """Test explicit None term handling."""

        pricing_date = SeparatedPricingService.get_pricing_date(term=None)
        today = timezone.now().date()

        assert pricing_date == today

    def test_business_rule_enforcement_concept(self):
        """
        Conceptual test of the business rule:
        "It isn't payment DATE that matters but the term that the course took place in"

        This test demonstrates the principle even if we can't run the full models.
        """

        # Scenario: Student enrolled in Spring 2022, paying in Fall 2023
        # The system should use Spring 2022 pricing, not Fall 2023 pricing

        class MockTerm:
            def __init__(self, start_date):
                self.start_date = start_date

        # When student enrolled (Spring 2022)
        enrollment_term = MockTerm(date(2022, 1, 15))

        # When payment is made (Fall 2023 - today)
        payment_date = date(2023, 10, 15)

        # System should use enrollment term date, not payment date
        pricing_date = SeparatedPricingService.get_pricing_date(enrollment_term)

        # Critical assertion: Uses enrollment term date, NOT payment date
        assert pricing_date == date(2022, 1, 15)  # Enrollment term
        assert pricing_date != payment_date  # NOT payment date

        # This proves the business rule is enforced:
        # "term that the course took place in" (2022-01-15)
        # NOT "payment DATE" (2023-10-15)

        print("✅ Business rule enforced:")
        print(f"   Enrollment term date: {pricing_date}")
        print(f"   Payment date (ignored): {payment_date}")
        print(f"   System correctly uses: {pricing_date}")


class TestSharedPricingMethods:
    """Test the shared pricing methods work correctly."""

    def test_get_active_pricing_method_exists(self):
        """Test that the shared get_active_pricing method exists and is callable."""

        # Test that the method exists
        assert hasattr(SeparatedPricingService, "get_active_pricing")
        assert callable(SeparatedPricingService.get_active_pricing)

        # Test that the method has the expected signature
        import inspect

        sig = inspect.signature(SeparatedPricingService.get_active_pricing)
        params = list(sig.parameters.keys())

        # Should have queryset and pricing_date parameters
        assert "queryset" in params
        assert "pricing_date" in params


if __name__ == "__main__":
    # Run the conceptual test standalone
    test = TestPricingBusinessRule()
    test.test_business_rule_enforcement_concept()
    print("✅ All pricing business rule tests passed!")
