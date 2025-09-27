"""
Simple test to verify SQLite compatibility for finance module.

This test uses minimal model dependencies to verify basic functionality.
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.finance.models import Currency

User = get_user_model()


class SimpleSQLiteTests(TestCase):
    """Simple tests to verify SQLite functionality."""

    def test_currency_enum(self):
        """Test Currency enum functionality."""
        self.assertEqual(Currency.USD, "USD")
        self.assertEqual(Currency.KHR, "KHR")

        # Test choices structure
        choices = Currency.choices
        self.assertEqual(len(choices), 2)
        self.assertIn(("USD", "US Dollar"), choices)
        self.assertIn(("KHR", "Cambodian Riel"), choices)

    def test_database_operations(self):
        """Test basic database operations work with SQLite."""
        # Test that we can perform basic database queries
        from django.db import connection

        with connection.cursor() as cursor:
            # Test a simple query that should work
            cursor.execute("SELECT 1 as test_value")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)

        # Test SQLite-specific features
        self.assertEqual(connection.vendor, "sqlite")

    def test_decimal_precision(self):
        """Test decimal precision handling."""
        amount = Decimal("1234.56")
        self.assertEqual(amount.as_tuple().exponent, -2)

        # Test financial calculations
        price = Decimal("999.99")
        tax = price * Decimal("0.10")
        total = price + tax

        self.assertEqual(tax, Decimal("99.999"))  # Before rounding
        self.assertEqual(total, Decimal("1099.989"))  # Before rounding

        # Test proper rounding for financial amounts
        tax_rounded = tax.quantize(Decimal("0.01"))
        total_rounded = price + tax_rounded

        self.assertEqual(tax_rounded, Decimal("100.00"))
        self.assertEqual(total_rounded, Decimal("1099.99"))

    def test_currency_consistency(self):
        """Test currency handling consistency."""
        usd_amount = Decimal("1500.00")
        khr_amount = Decimal("4000000.00")

        # Test that both currencies maintain precision
        self.assertEqual(usd_amount.as_tuple().exponent, -2)
        self.assertEqual(khr_amount.as_tuple().exponent, -2)

        # Test currency enum usage
        invoice_currency_usd = Currency.USD
        invoice_currency_khr = Currency.KHR

        self.assertEqual(invoice_currency_usd, "USD")
        self.assertEqual(invoice_currency_khr, "KHR")
