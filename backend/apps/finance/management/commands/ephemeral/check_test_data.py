"""Check test data for A/R reconstruction."""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    """Check receipt and student data for testing."""

    help = "Check receipt and student data to find valid test cases"

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            # Check what terms have receipts and their student ID ranges
            cursor.execute(
                """
                SELECT termid, COUNT(*), MIN(id::integer), MAX(id::integer)
                FROM legacy_receipt_headers
                WHERE termid IS NOT NULL AND termid != ''
                GROUP BY termid
                ORDER BY COUNT(*) DESC
                LIMIT 10
            """
            )
            terms = cursor.fetchall()
            self.stdout.write("Terms with receipts (top 10 by count):")
            for termid, count, min_id, max_id in terms:
                self.stdout.write(f"  {termid}: {count} receipts, student IDs {min_id}-{max_id}")

            # Find receipts with valid student IDs (any term)
            cursor.execute(
                """
                SELECT id, receiptno, termid
                FROM legacy_receipt_headers
                WHERE id::integer <= 18319
                AND id::integer >= 1
                AND termid IS NOT NULL
                ORDER BY id::integer
                LIMIT 10
            """
            )
            receipts = cursor.fetchall()
            self.stdout.write("\nFirst 10 receipts with valid student IDs:")
            for student_id, receipt_no, term_id in receipts:
                self.stdout.write(f"  Student {student_id}, Receipt {receipt_no}, Term {term_id}")
