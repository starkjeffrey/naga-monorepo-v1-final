"""
Test infrastructure verification.

Simple tests to verify the test framework is working correctly.
"""

from decimal import Decimal

import pytest


@pytest.mark.unit
class TestInfrastructure:
    """Test that the test infrastructure is working."""

    def test_pytest_working(self):
        """Test that pytest is working."""
        assert True

    def test_decimal_precision(self):
        """Test decimal precision handling."""
        amount = Decimal("100.50")
        assert amount == Decimal("100.50")
        assert str(amount) == "100.50"

    def test_string_operations(self):
        """Test string operations."""
        test_string = "Naga SIS"
        assert test_string.lower() == "naga sis"
        assert len(test_string) == 8

    @pytest.mark.parametrize(
        "value,expected",
        [
            (1, 2),
            (2, 4),
            (3, 6),
        ],
    )
    def test_parametrized(self, value, expected):
        """Test parametrized tests work."""
        assert value * 2 == expected
