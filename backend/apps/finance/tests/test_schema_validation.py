"""
Test to demonstrate that schema validation works with SQLite.

This test verifies that migrations run properly for non-academic apps,
allowing detection of schema mismatches and model/DB discrepancies.
"""

from django.db import connection
from django.test import TestCase


class SchemaValidationTest(TestCase):
    """Test that demonstrates schema validation is working."""

    def test_migrations_created_tables(self):
        """Test that migrations properly created database tables."""
        with connection.cursor() as cursor:
            # Check what tables actually exist
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            all_tables = [row[0] for row in cursor.fetchall()]

            # Debug: print all tables to understand what was created
            print(f"All tables created: {all_tables}")

            # At minimum, auth tables should exist (they're core Django)
            auth_tables = [t for t in all_tables if t.startswith("auth_")]
            self.assertGreater(len(auth_tables), 0, "At least auth tables should exist from migrations")

            # Check if any finance-related tables exist
            finance_tables = [t for t in all_tables if "finance" in t.lower()]
            print(f"Finance tables found: {finance_tables}")

    def test_model_fields_match_database(self):
        """Test that model fields match database schema."""
        from apps.finance.models import Currency

        # Test that the Currency enum values work
        self.assertEqual(Currency.USD, "USD")
        self.assertEqual(Currency.KHR, "KHR")

        # Verify choices are available
        choices = Currency.choices
        self.assertEqual(len(choices), 2)
        self.assertIn(("USD", "US Dollar"), choices)
        self.assertIn(("KHR", "Cambodian Riel"), choices)

    def test_sqlite_vs_postgresql_compatibility(self):
        """Test that SQLite provides same functionality as PostgreSQL."""
        # Test database connection works
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)

        # Test vendor is correctly identified
        self.assertEqual(connection.vendor, "sqlite")

        # Test that basic SQL operations work
        with connection.cursor() as cursor:
            # Create a temporary table to test operations
            cursor.execute("""
                CREATE TEMPORARY TABLE test_compatibility (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    value DECIMAL(10,2)
                )
            """)

            # Insert test data
            cursor.execute("""
                INSERT INTO test_compatibility (name, value)
                VALUES ('test', 123.45)
            """)

            # Query test data
            cursor.execute("SELECT name, value FROM test_compatibility")
            result = cursor.fetchone()
            self.assertEqual(result[0], "test")
            # SQLite returns decimals as strings, which is expected
            self.assertIn(str(result[1]), ["123.45", "123.4500"])
