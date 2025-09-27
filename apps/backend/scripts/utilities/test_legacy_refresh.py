#!/usr/bin/env python
"""Test script to verify the legacy table refresh functionality.

This script checks the current IPK values and simulates what would happen
with a refresh operation.
"""

import os
import sys

import django

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.db import connection


def check_legacy_tables():
    """Check the current state of legacy tables."""

    print("=== LEGACY TABLE STATUS CHECK ===\n")

    # Check legacy_students
    with connection.cursor() as cursor:
        # Get max IPK
        cursor.execute("SELECT MAX(ipk) FROM legacy_students")
        max_student_ipk = cursor.fetchone()[0] or 0

        # Get record count
        cursor.execute("SELECT COUNT(*) FROM legacy_students")
        student_count = cursor.fetchone()[0]

        # Get date range
        cursor.execute(
            """
            SELECT MIN(created_date), MAX(created_date)
            FROM legacy_students
            WHERE created_date IS NOT NULL
        """
        )
        student_dates = cursor.fetchone()

        print("Legacy Students Table:")
        print(f"  - Total records: {student_count:,}")
        print(f"  - Highest IPK: {max_student_ipk:,}")
        print(f"  - Date range: {student_dates[0]} to {student_dates[1]}")

        # Sample of latest records
        cursor.execute(
            """
            SELECT ipk, id, name, created_date
            FROM legacy_students
            ORDER BY ipk DESC
            LIMIT 5
        """
        )
        print("\n  Latest 5 records by IPK:")
        for row in cursor.fetchall():
            print(f"    IPK {row[0]}: ID {row[1]} - {row[2]} (created: {row[3]})")

    print("\n" + "-" * 50 + "\n")

    # Check legacy_receipt_headers
    with connection.cursor() as cursor:
        # Get max IPK
        cursor.execute("SELECT MAX(ipk) FROM legacy_receipt_headers")
        max_receipt_ipk = cursor.fetchone()[0] or 0

        # Get record count
        cursor.execute("SELECT COUNT(*) FROM legacy_receipt_headers")
        receipt_count = cursor.fetchone()[0]

        # Get date range
        cursor.execute(
            """
            SELECT MIN(pmtdate), MAX(pmtdate)
            FROM legacy_receipt_headers
            WHERE pmtdate IS NOT NULL
        """
        )
        receipt_dates = cursor.fetchone()

        print("Legacy Receipt Headers Table:")
        print(f"  - Total records: {receipt_count:,}")
        print(f"  - Highest IPK: {max_receipt_ipk:,}")
        print(f"  - Payment date range: {receipt_dates[0]} to {receipt_dates[1]}")

        # Sample of latest records
        cursor.execute(
            """
            SELECT ipk, id, receiptno, amount, pmtdate
            FROM legacy_receipt_headers
            ORDER BY ipk DESC
            LIMIT 5
        """
        )
        print("\n  Latest 5 records by IPK:")
        for row in cursor.fetchall():
            print(f"    IPK {row[0]}: Student {row[1]}, Receipt {row[2]}, ${row[3]:.2f} (paid: {row[4]})")

    print("\n" + "=" * 50 + "\n")

    # Simulate refresh
    print("REFRESH SIMULATION:")
    print(f"  - New student records would need IPK > {max_student_ipk:,}")
    print(f"  - New receipt records would need IPK > {max_receipt_ipk:,}")
    print("\nTo run actual refresh:")
    print("  python manage.py refresh_legacy_tables --students-file data/legacy/new_students.csv")
    print("  python manage.py refresh_legacy_tables --receipts-file data/legacy/new_receipts.csv")
    print("  python manage.py refresh_legacy_tables --table both  # Refresh both tables")


if __name__ == "__main__":
    check_legacy_tables()
