"""Tests for decimal helper functions in finance services.

These tests verify that the new decimal helper functions work correctly
and maintain proper precision in all financial calculations.
"""

from decimal import Decimal

from django.test import TestCase

from apps.finance.services import (
    FINANCIAL_PRECISION,
    normalize_decimal,
    safe_decimal_add,
    safe_decimal_multiply,
)


class DecimalHelperTest(TestCase):
    """Test the decimal helper functions."""

    def test_normalize_decimal_from_decimal(self):
        """Test normalizing Decimal values."""
        test_cases = [
            (Decimal("123.456"), Decimal("123.46")),
            (Decimal("123.454"), Decimal("123.45")),
            (Decimal("123.455"), Decimal("123.46")),  # ROUND_HALF_UP
            (Decimal("0.001"), Decimal("0.00")),
            (Decimal("999.999"), Decimal("1000.00")),
        ]

        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = normalize_decimal(input_val)
                self.assertEqual(result, expected)
                self.assertIsInstance(result, Decimal)

    def test_normalize_decimal_from_string(self):
        """Test normalizing string values."""
        test_cases = [
            ("123.456", Decimal("123.46")),
            ("123.454", Decimal("123.45")),
            ("123.455", Decimal("123.46")),  # ROUND_HALF_UP
            ("0.001", Decimal("0.00")),
            ("999.999", Decimal("1000.00")),
        ]

        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = normalize_decimal(input_val)
                self.assertEqual(result, expected)
                self.assertIsInstance(result, Decimal)

    def test_normalize_decimal_from_float(self):
        """Test normalizing float values."""
        test_cases = [
            (123.456, Decimal("123.46")),
            (123.454, Decimal("123.45")),
            (123.455, Decimal("123.46")),  # ROUND_HALF_UP
            (0.001, Decimal("0.00")),
            (999.999, Decimal("1000.00")),
        ]

        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = normalize_decimal(input_val)
                self.assertEqual(result, expected)
                self.assertIsInstance(result, Decimal)

    def test_normalize_decimal_from_int(self):
        """Test normalizing integer values."""
        test_cases = [
            (123, Decimal("123.00")),
            (0, Decimal("0.00")),
            (999, Decimal("999.00")),
        ]

        for input_val, expected in test_cases:
            with self.subTest(input_val=input_val):
                result = normalize_decimal(input_val)
                self.assertEqual(result, expected)
                self.assertIsInstance(result, Decimal)

    def test_safe_decimal_add_two_values(self):
        """Test adding two decimal values."""
        test_cases = [
            (Decimal("123.45"), Decimal("67.89"), Decimal("191.34")),
            (Decimal("0.01"), Decimal("0.01"), Decimal("0.02")),
            (Decimal("999.99"), Decimal("0.01"), Decimal("1000.00")),
            ("123.45", "67.89", Decimal("191.34")),
            (123.45, 67.89, Decimal("191.34")),
        ]

        for val1, val2, expected in test_cases:
            with self.subTest(val1=val1, val2=val2):
                result = safe_decimal_add(val1, val2)
                self.assertEqual(result, expected)
                self.assertIsInstance(result, Decimal)

    def test_safe_decimal_add_multiple_values(self):
        """Test adding multiple decimal values."""
        values = [
            Decimal("123.45"),
            Decimal("67.89"),
            Decimal("12.34"),
            Decimal("5.67"),
        ]
        expected = Decimal("209.35")

        result = safe_decimal_add(*values)
        self.assertEqual(result, expected)
        self.assertIsInstance(result, Decimal)

    def test_safe_decimal_add_mixed_types(self):
        """Test adding mixed types safely."""
        result = safe_decimal_add(Decimal("123.45"), "67.89", 12.34, 5)
        expected = Decimal("208.68")
        self.assertEqual(result, expected)
        self.assertIsInstance(result, Decimal)

    def test_safe_decimal_multiply(self):
        """Test multiplying decimal values."""
        test_cases = [
            (Decimal("123.45"), Decimal("2.00"), Decimal("246.90")),
            (Decimal("123.456"), Decimal("2.00"), Decimal("246.91")),  # Rounds up
            (Decimal("0.01"), Decimal("100.00"), Decimal("1.00")),
            ("123.45", "2.00", Decimal("246.90")),
            (123.45, 2.00, Decimal("246.90")),
        ]

        for val1, val2, expected in test_cases:
            with self.subTest(val1=val1, val2=val2):
                result = safe_decimal_multiply(val1, val2)
                self.assertEqual(result, expected)
                self.assertIsInstance(result, Decimal)

    def test_safe_decimal_multiply_percentage(self):
        """Test multiplying by percentage values."""
        # Test percentage calculations
        base_amount = Decimal("100.00")
        percentage = Decimal("15.25")  # 15.25%

        # Convert percentage to decimal
        percentage_decimal = percentage / Decimal("100")
        result = safe_decimal_multiply(base_amount, percentage_decimal)

        expected = Decimal("15.25")
        self.assertEqual(result, expected)

    def test_financial_precision_constant(self):
        """Test that FINANCIAL_PRECISION constant is correct."""
        self.assertEqual(FINANCIAL_PRECISION, Decimal("0.01"))

    def test_rounding_consistency(self):
        """Test that rounding is consistent across all functions."""
        # Test ROUND_HALF_UP behavior
        test_value = Decimal("123.455")

        # All functions should round the same way
        normalized = normalize_decimal(test_value)
        added = safe_decimal_add(test_value, Decimal("0.00"))
        multiplied = safe_decimal_multiply(test_value, Decimal("1.00"))

        expected = Decimal("123.46")
        self.assertEqual(normalized, expected)
        self.assertEqual(added, expected)
        self.assertEqual(multiplied, expected)

    def test_precision_maintenance_in_complex_calculations(self):
        """Test precision maintenance in complex multi-step calculations."""
        # Simulate complex invoice calculation
        course_price = Decimal("1234.567")
        adjustment = Decimal("-234.567")
        fee = Decimal("123.456")

        # Step 1: Apply adjustment
        adjusted_price = safe_decimal_add(course_price, adjustment)

        # Step 2: Add fee
        subtotal = safe_decimal_add(adjusted_price, fee)

        # Step 3: Calculate tax (10%)
        tax_rate = Decimal("0.10")
        tax_amount = safe_decimal_multiply(subtotal, tax_rate)

        # Step 4: Calculate total
        total = safe_decimal_add(subtotal, tax_amount)

        # Expected values with proper rounding
        expected_adjusted = Decimal("1000.00")  # 1234.567 - 234.567 = 1000.000
        expected_subtotal = Decimal("1123.46")  # 1000.00 + 123.456 = 1123.456 -> 1123.46
        expected_tax = Decimal("112.35")  # 1123.46 * 0.10 = 112.346 -> 112.35
        expected_total = Decimal("1235.81")  # 1123.46 + 112.35 = 1235.81

        self.assertEqual(adjusted_price, expected_adjusted)
        self.assertEqual(subtotal, expected_subtotal)
        self.assertEqual(tax_amount, expected_tax)
        self.assertEqual(total, expected_total)

    def test_zero_handling(self):
        """Test handling of zero values."""
        zero_vals = [0, "0", "0.00", Decimal("0.00")]

        for zero_val in zero_vals:
            with self.subTest(zero_val=zero_val):
                result = normalize_decimal(zero_val)
                self.assertEqual(result, Decimal("0.00"))

                # Test addition with zero
                add_result = safe_decimal_add(Decimal("123.45"), zero_val)
                self.assertEqual(add_result, Decimal("123.45"))

                # Test multiplication with zero
                mult_result = safe_decimal_multiply(Decimal("123.45"), zero_val)
                self.assertEqual(mult_result, Decimal("0.00"))

    def test_negative_values(self):
        """Test handling of negative values."""
        negative_cases = [
            (Decimal("-123.45"), Decimal("-123.45")),
            ("-123.456", Decimal("-123.46")),
            (-123.456, Decimal("-123.46")),
        ]

        for input_val, expected in negative_cases:
            with self.subTest(input_val=input_val):
                result = normalize_decimal(input_val)
                self.assertEqual(result, expected)

                # Test addition with negative
                add_result = safe_decimal_add(Decimal("200.00"), input_val)
                expected_add = Decimal("200.00") + expected
                self.assertEqual(add_result, expected_add)

                # Test multiplication with negative
                mult_result = safe_decimal_multiply(Decimal("2.00"), input_val)
                expected_mult = Decimal("2.00") * expected
                self.assertEqual(mult_result, expected_mult)

    def test_large_numbers(self):
        """Test handling of large numbers."""
        large_cases = [
            (Decimal("1234567.89"), Decimal("1234567.89")),
            ("9999999.999", Decimal("10000000.00")),
            (1234567.89, Decimal("1234567.89")),
        ]

        for input_val, expected in large_cases:
            with self.subTest(input_val=input_val):
                result = normalize_decimal(input_val)
                self.assertEqual(result, expected)

    def test_very_small_numbers(self):
        """Test handling of very small numbers."""
        small_cases = [
            (Decimal("0.001"), Decimal("0.00")),
            (Decimal("0.004"), Decimal("0.00")),
            (Decimal("0.005"), Decimal("0.01")),  # ROUND_HALF_UP
            (Decimal("0.006"), Decimal("0.01")),
            ("0.001", Decimal("0.00")),
            (0.001, Decimal("0.00")),
        ]

        for input_val, expected in small_cases:
            with self.subTest(input_val=input_val):
                result = normalize_decimal(input_val)
                self.assertEqual(result, expected)
