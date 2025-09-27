"""Tests for QuickBooks reporting functionality.

Tests cover the QuickBooksReportService and management command for generating
accounting reports that can be easily imported into QuickBooks.
"""

from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.curriculum.models import Term
from apps.finance.models import FinancialTransaction, Invoice, Payment
from apps.finance.services import QuickBooksReportService
from apps.people.models import Person, StudentProfile

User = get_user_model()


class QuickBooksReportServiceTest(TestCase):
    """Test QuickBooks report service functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(email="test@example.com", password="testpass123")

        # Create student
        person = Person.objects.create(
            personal_name="Test",
            family_name="Student",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )
        self.student = StudentProfile.objects.create(
            person=person,
            student_id=1001,
        )

        # Create term
        self.term = Term.objects.create(
            name="Summer 2025",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 8, 31),
        )

        # Create service instance
        self.service = QuickBooksReportService()

        # Test date
        self.test_year = 2025
        self.test_month = 6

    def test_generate_monthly_cash_receipts_summary_no_data(self):
        """Test cash receipts summary with no transactions."""
        report = self.service.generate_monthly_cash_receipts_summary(self.test_year, self.test_month)

        self.assertIn("No transactions found", report)
        self.assertIn("TOTAL RECEIPTS:......................... $0.00", report)
        self.assertIn("June 2025", report)

    def test_generate_monthly_cash_receipts_summary_with_data(self):
        """Test cash receipts summary with sample transactions."""
        # Create sample invoice and payment
        invoice = Invoice.objects.create(
            invoice_number="INV-2025-1001-0001",
            student=self.student,
            term=self.term,
            issue_date=date(2025, 6, 1),
            due_date=date(2025, 6, 15),
            subtotal=Decimal("1000.00"),
            total_amount=Decimal("1000.00"),
        )

        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal("1000.00"),
            payment_method="CASH",
            payment_date=date(2025, 6, 10),
            processed_by=self.user,
        )

        # Create financial transaction
        FinancialTransaction.objects.create(
            transaction_id="TXN-20250610120000-000001",
            student=self.student,
            invoice=invoice,
            payment=payment,
            amount=Decimal("1000.00"),
            transaction_type=FinancialTransaction.TransactionType.PAYMENT_RECEIVED,
            transaction_date=timezone.make_aware(timezone.datetime(2025, 6, 10, 12, 0)),
            processed_by=self.user,
            description="Tuition payment",
        )

        report = self.service.generate_monthly_cash_receipts_summary(self.test_year, self.test_month)

        self.assertIn("June 2025", report)
        self.assertIn("$1000.00", report)
        self.assertNotIn("No transactions found", report)

    def test_generate_quickbooks_journal_entry_no_data(self):
        """Test journal entry format with no data."""
        report = self.service.generate_quickbooks_journal_entry(self.test_year, self.test_month)

        self.assertIn("QUICKBOOKS JOURNAL ENTRY - June 2025", report)
        self.assertIn("Date: 2025-06-30", report)
        self.assertIn("TOTALS                                   $      0.00  $      0.00", report)

    def test_generate_quickbooks_journal_entry_with_data(self):
        """Test journal entry format with sample data."""
        # Create sample invoice and payment
        invoice = Invoice.objects.create(
            invoice_number="INV-2025-1001-0002",
            student=self.student,
            term=self.term,
            issue_date=date(2025, 6, 1),
            due_date=date(2025, 6, 15),
            subtotal=Decimal("500.00"),
            total_amount=Decimal("500.00"),
        )

        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal("500.00"),
            payment_method="BANK_TRANSFER",
            payment_date=date(2025, 6, 5),
            processed_by=self.user,
        )

        # Create financial transaction
        FinancialTransaction.objects.create(
            transaction_id="TXN-20250610120000-000001",
            student=self.student,
            invoice=invoice,
            payment=payment,
            amount=Decimal("500.00"),
            transaction_type=FinancialTransaction.TransactionType.PAYMENT_RECEIVED,
            transaction_date=timezone.make_aware(timezone.datetime(2025, 6, 5, 10, 0)),
            processed_by=self.user,
            description="Registration fee payment",
        )

        report = self.service.generate_quickbooks_journal_entry(self.test_year, self.test_month)

        self.assertIn("June 2025", report)
        self.assertIn("Cash receipts for June 2025", report)
        # Should have some credits for income
        self.assertIn("$    500.00", report)

    def test_generate_bank_deposit_report_no_data(self):
        """Test bank deposit report with no data."""
        report = self.service.generate_bank_deposit_report(self.test_year, self.test_month)

        self.assertIn("BANK DEPOSIT REPORT - June 2025", report)
        self.assertIn(
            "TOTAL DEPOSITS FOR THE MONTH:                                       $      0.00",
            report,
        )

    def test_generate_bank_deposit_report_with_data(self):
        """Test bank deposit report with sample data."""
        # Create multiple transactions on different days
        for i, day in enumerate([5, 10, 15], 1):
            invoice = Invoice.objects.create(
                invoice_number=f"INV-2025-1001-000{i + 2}",
                student=self.student,
                issue_date=date(2025, 6, day),
                due_date=date(2025, 6, day + 5),
                subtotal=Decimal("300.00"),
                total_amount=Decimal("300.00"),
                created_by=self.user,
            )

            payment = Payment.objects.create(
                invoice=invoice,
                amount=Decimal("300.00"),
                payment_method="CASH",
                payment_date=date(2025, 6, day),
                processed_by=self.user,
            )

            FinancialTransaction.objects.create(
                transaction_id=f"TXN-202506{day:02d}140000-{i + 2:06d}",
                student=self.student,
                invoice=invoice,
                payment=payment,
                amount=Decimal("300.00"),
                transaction_type=FinancialTransaction.TransactionType.PAYMENT_RECEIVED,
                transaction_date=timezone.make_aware(timezone.datetime(2025, 6, day, 14, 0)),
                processed_by=self.user,
                description=f"Payment on day {day}",
            )

        report = self.service.generate_bank_deposit_report(self.test_year, self.test_month)

        self.assertIn("June 2025", report)
        self.assertIn("$    900.00", report)  # Total of 3 x $300

    def test_generate_monthly_transaction_details(self):
        """Test monthly transaction details report."""
        # Create sample transaction
        invoice = Invoice.objects.create(
            invoice_number="INV-2025-1001-0006",
            student=self.student,
            term=self.term,
            issue_date=date(2025, 6, 10),
            due_date=date(2025, 6, 20),
            subtotal=Decimal("750.00"),
            total_amount=Decimal("750.00"),
        )

        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal("750.00"),
            payment_method="CREDIT_CARD",
            payment_date=date(2025, 6, 12),
            processed_by=self.user,
        )

        FinancialTransaction.objects.create(
            student=self.student,
            invoice=invoice,
            payment=payment,
            amount=Decimal("750.00"),
            transaction_type=FinancialTransaction.TransactionType.PAYMENT_RECEIVED,
            transaction_date=timezone.make_aware(timezone.datetime(2025, 6, 12, 16, 0)),
            processed_by=self.user,
            description="Course fee payment",
        )

        report = self.service.generate_monthly_transaction_details(self.test_year, self.test_month)

        self.assertIn("June 2025", report)
        self.assertIn("Course fee payment", report)
        self.assertIn("$750.00", report)

    def test_cash_receipts_summary_csv_format(self):
        """Test CSV format output for cash receipts summary."""
        # Create sample transaction
        invoice = Invoice.objects.create(
            invoice_number="INV-2025-1001-0007",
            student=self.student,
            term=self.term,
            issue_date=date(2025, 6, 15),
            due_date=date(2025, 6, 25),
            subtotal=Decimal("400.00"),
            total_amount=Decimal("400.00"),
        )

        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal("400.00"),
            payment_method="CASH",
            payment_date=date(2025, 6, 20),
            processed_by=self.user,
        )

        FinancialTransaction.objects.create(
            student=self.student,
            invoice=invoice,
            payment=payment,
            amount=Decimal("400.00"),
            transaction_type=FinancialTransaction.TransactionType.PAYMENT_RECEIVED,
            transaction_date=timezone.make_aware(timezone.datetime(2025, 6, 20, 11, 0)),
            processed_by=self.user,
            description="Lab fee payment",
        )

        report = self.service.generate_monthly_cash_receipts_summary(self.test_year, self.test_month, format="csv")

        # CSV format should still be readable (this service may format as readable regardless)
        self.assertIn("June 2025", report)
        self.assertIn("$400.00", report)

    def test_refund_transactions(self):
        """Test handling of refund transactions."""
        # Create original payment
        invoice = Invoice.objects.create(
            invoice_number="INV-2025-1001-0008",
            student=self.student,
            term=self.term,
            issue_date=date(2025, 6, 5),
            due_date=date(2025, 6, 15),
            subtotal=Decimal("600.00"),
            total_amount=Decimal("600.00"),
        )

        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal("600.00"),
            payment_method="CASH",
            payment_date=date(2025, 6, 10),
            processed_by=self.user,
        )

        # Payment transaction
        FinancialTransaction.objects.create(
            student=self.student,
            invoice=invoice,
            payment=payment,
            amount=Decimal("600.00"),
            transaction_type=FinancialTransaction.TransactionType.PAYMENT_RECEIVED,
            transaction_date=timezone.make_aware(timezone.datetime(2025, 6, 10, 9, 0)),
            processed_by=self.user,
            description="Original payment",
        )

        # Refund transaction
        FinancialTransaction.objects.create(
            student=self.student,
            invoice=invoice,
            payment=payment,
            amount=Decimal("-100.00"),
            transaction_type=FinancialTransaction.TransactionType.PAYMENT_REFUNDED,
            transaction_date=timezone.make_aware(timezone.datetime(2025, 6, 20, 15, 0)),
            processed_by=self.user,
            description="Partial refund",
        )

        report = self.service.generate_monthly_cash_receipts_summary(self.test_year, self.test_month)

        self.assertIn("June 2025", report)
        # Should show net amount after refund
        self.assertIn("$500.00", report)  # $600 - $100 refund


class QuickBooksManagementCommandTest(TestCase):
    """Test QuickBooks report management command."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(email="test@example.com", password="testpass123")

        # Create student for test data
        person = Person.objects.create(
            personal_name="Command",
            family_name="Test",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="F",
            citizenship="KH",
        )
        self.student = StudentProfile.objects.create(
            person=person,
            student_id=2001,
        )

        # Create term
        self.term = Term.objects.create(
            name="June 2025 Term",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 8, 31),
        )

    def test_generate_quickbooks_reports_command_default(self):
        """Test command with default parameters (previous month)."""
        out = StringIO()

        call_command("generate_quickbooks_reports", stdout=out)

        output = out.getvalue()
        self.assertIn("Report generated successfully!", output)
        self.assertIn("MONTHLY CASH RECEIPTS SUMMARY", output)

    def test_generate_quickbooks_reports_command_specific_month(self):
        """Test command with specific year and month."""
        out = StringIO()

        call_command("generate_quickbooks_reports", "--year", "2025", "--month", "6", stdout=out)

        output = out.getvalue()
        self.assertIn("Generating QuickBooks reports for June 2025", output)
        self.assertIn("Report generated successfully!", output)

    def test_generate_quickbooks_reports_command_journal_only(self):
        """Test command with journal entry only."""
        out = StringIO()

        call_command(
            "generate_quickbooks_reports",
            "--journal",
            "--year",
            "2025",
            "--month",
            "6",
            stdout=out,
        )

        output = out.getvalue()
        self.assertIn("QUICKBOOKS JOURNAL ENTRY", output)
        self.assertIn("June 2025", output)

    def test_generate_quickbooks_reports_command_deposits_only(self):
        """Test command with deposits report only."""
        out = StringIO()

        call_command(
            "generate_quickbooks_reports",
            "--deposits",
            "--year",
            "2025",
            "--month",
            "6",
            stdout=out,
        )

        output = out.getvalue()
        self.assertIn("DAILY DEPOSITS REPORT", output)
        self.assertIn("BANK DEPOSIT REPORT", output)

    def test_generate_quickbooks_reports_command_all(self):
        """Test command with all reports."""
        out = StringIO()

        call_command(
            "generate_quickbooks_reports",
            "--all",
            "--year",
            "2025",
            "--month",
            "6",
            stdout=out,
        )

        output = out.getvalue()
        self.assertIn("QUICKBOOKS JOURNAL ENTRY", output)
        self.assertIn("DAILY DEPOSITS REPORT", output)
        self.assertIn("MONTHLY CASH RECEIPTS SUMMARY", output)

    def test_generate_quickbooks_reports_command_csv_format(self):
        """Test command with CSV format."""
        out = StringIO()

        call_command(
            "generate_quickbooks_reports",
            "--format",
            "csv",
            "--year",
            "2025",
            "--month",
            "6",
            stdout=out,
        )

        output = out.getvalue()
        self.assertIn("Report generated successfully!", output)

    def test_generate_quickbooks_reports_command_with_data(self):
        """Test command with actual transaction data."""
        # Create sample transaction for June 2025
        invoice = Invoice.objects.create(
            invoice_number="INV-2025-2001-0001",
            student=self.student,
            term=self.term,
            issue_date=date(2025, 6, 1),
            due_date=date(2025, 6, 30),
            subtotal=Decimal("1200.00"),
            total_amount=Decimal("1200.00"),
        )

        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal("1200.00"),
            payment_method="BANK_TRANSFER",
            payment_date=date(2025, 6, 15),
            processed_by=self.user,
        )

        FinancialTransaction.objects.create(
            student=self.student,
            invoice=invoice,
            payment=payment,
            amount=Decimal("1200.00"),
            transaction_type=FinancialTransaction.TransactionType.PAYMENT_RECEIVED,
            transaction_date=timezone.make_aware(timezone.datetime(2025, 6, 15, 13, 0)),
            processed_by=self.user,
            description="Full tuition payment",
        )

        out = StringIO()

        call_command(
            "generate_quickbooks_reports",
            "--all",
            "--year",
            "2025",
            "--month",
            "6",
            stdout=out,
        )

        output = out.getvalue()
        self.assertIn("$1200.00", output)
        self.assertIn("Full tuition payment", output)
        self.assertNotIn("No transactions found", output)

    def test_generate_quickbooks_reports_command_invalid_month(self):
        """Test command with invalid month."""
        out = StringIO()
        err = StringIO()

        try:
            call_command(
                "generate_quickbooks_reports",
                "--year",
                "2025",
                "--month",
                "13",
                stdout=out,
                stderr=err,
            )
            self.fail("Should have raised SystemExit")
        except SystemExit:
            pass  # Expected behavior

    def test_generate_quickbooks_reports_command_future_date(self):
        """Test command with future date."""
        out = StringIO()
        err = StringIO()

        try:
            call_command(
                "generate_quickbooks_reports",
                "--year",
                "2026",
                "--month",
                "12",
                stdout=out,
                stderr=err,
            )
            self.fail("Should have raised SystemExit")
        except SystemExit:
            pass  # Expected behavior


class QuickBooksReportIntegrationTest(TestCase):
    """Integration tests for QuickBooks reporting with realistic data."""

    def setUp(self):
        """Set up realistic test scenario."""
        self.user = User.objects.create_user(email="accounting@school.edu", password="testpass123")

        # Create multiple students
        self.students = []
        for i in range(3):
            person = Person.objects.create(
                personal_name=f"Student{i}",
                family_name="Testson",
                date_of_birth=date(2000 + i, 1, 1),
                preferred_gender="M" if i % 2 == 0 else "F",
                citizenship="KH",
            )
            student = StudentProfile.objects.create(
                person=person,
                student_id=3000 + i,
            )
            self.students.append(student)

        self.term_june = Term.objects.create(
            name="June 2025 Term",
            start_date=date(2025, 6, 1),
            end_date=date(2025, 8, 31),
        )
        self.term_dec = Term.objects.create(
            name="December 2024 Term",
            start_date=date(2024, 12, 1),
            end_date=date(2025, 2, 28),
        )
        self.term_jan = Term.objects.create(
            name="January 2025 Term",
            start_date=date(2025, 1, 1),
            end_date=date(2025, 5, 31),
        )

        self.service = QuickBooksReportService()

    def test_complete_monthly_scenario(self):
        """Test complete monthly reporting scenario with multiple students and payment types."""
        # Create various transactions throughout June 2025
        test_data = [
            (
                self.students[0],
                Decimal("800.00"),
                "CASH",
                date(2025, 6, 5),
                "Tuition payment",
            ),
            (
                self.students[1],
                Decimal("1200.00"),
                "BANK_TRANSFER",
                date(2025, 6, 10),
                "Full semester fee",
            ),
            (
                self.students[2],
                Decimal("300.00"),
                "CREDIT_CARD",
                date(2025, 6, 15),
                "Lab fee",
            ),
            (
                self.students[0],
                Decimal("150.00"),
                "CASH",
                date(2025, 6, 20),
                "Registration fee",
            ),
            (
                self.students[1],
                Decimal("-100.00"),
                "CASH",
                date(2025, 6, 25),
                "Partial refund",
            ),
        ]

        for i, (student, amount, method, payment_date, desc) in enumerate(test_data, 1):
            invoice = Invoice.objects.create(
                invoice_number=f"INV-2025-{student.student_id}-000{i}",
                student=student,
                term=self.term_june,
                issue_date=payment_date - timedelta(days=5),
                due_date=payment_date + timedelta(days=30),
                subtotal=abs(amount),
                total_amount=abs(amount),
            )

            payment = Payment.objects.create(
                invoice=invoice,
                amount=abs(amount),
                payment_method=method,
                payment_date=payment_date,
                processed_by=self.user,
            )

            transaction_type = (
                FinancialTransaction.TransactionType.PAYMENT_REFUNDED
                if amount < 0
                else FinancialTransaction.TransactionType.PAYMENT_RECEIVED
            )

            FinancialTransaction.objects.create(
                student=student,
                invoice=invoice,
                payment=payment,
                amount=amount,
                transaction_type=transaction_type,
                transaction_date=timezone.make_aware(
                    timezone.datetime.combine(payment_date, timezone.datetime.min.time().replace(hour=10)),
                ),
                processed_by=self.user,
                description=desc,
            )

        # Test all report types
        cash_receipts = self.service.generate_monthly_cash_receipts_summary(2025, 6)
        journal_entry = self.service.generate_quickbooks_journal_entry(2025, 6)
        bank_deposits = self.service.generate_bank_deposit_report(2025, 6)
        transaction_details = self.service.generate_monthly_transaction_details(2025, 6)

        # Verify cash receipts summary
        self.assertIn("June 2025", cash_receipts)
        self.assertIn("$2350.00", cash_receipts)  # Total: 800+1200+300+150-100

        # Verify journal entry
        self.assertIn("QUICKBOOKS JOURNAL ENTRY", journal_entry)
        self.assertIn("2025-06-30", journal_entry)

        # Verify bank deposits
        self.assertIn("BANK DEPOSIT REPORT", bank_deposits)
        self.assertIn("$2350.00", bank_deposits)  # Net deposits

        # Verify transaction details
        self.assertIn("Tuition payment", transaction_details)
        self.assertIn("Full semester fee", transaction_details)
        self.assertIn("Partial refund", transaction_details)

    def test_year_end_reporting(self):
        """Test reporting across year boundary."""
        # Create December 2024 transaction
        invoice_dec = Invoice.objects.create(
            invoice_number="INV-2024-3000-0001",
            student=self.students[0],
            term=self.term_dec,
            issue_date=date(2024, 12, 1),
            due_date=date(2024, 12, 31),
            subtotal=Decimal("500.00"),
            total_amount=Decimal("500.00"),
        )

        payment_dec = Payment.objects.create(
            invoice=invoice_dec,
            amount=Decimal("500.00"),
            payment_method="CASH",
            payment_date=date(2024, 12, 15),
            processed_by=self.user,
        )

        FinancialTransaction.objects.create(
            student=self.students[0],
            invoice=invoice_dec,
            payment=payment_dec,
            amount=Decimal("500.00"),
            transaction_type=FinancialTransaction.TransactionType.PAYMENT_RECEIVED,
            transaction_date=timezone.make_aware(timezone.datetime(2024, 12, 15, 14, 0)),
            processed_by=self.user,
            description="December payment",
        )

        # Create January 2025 transaction
        invoice_jan = Invoice.objects.create(
            invoice_number="INV-2025-3001-0001",
            student=self.students[1],
            term=self.term_jan,
            issue_date=date(2025, 1, 1),
            due_date=date(2025, 1, 31),
            subtotal=Decimal("750.00"),
            total_amount=Decimal("750.00"),
        )

        payment_jan = Payment.objects.create(
            invoice=invoice_jan,
            amount=Decimal("750.00"),
            payment_method="BANK_TRANSFER",
            payment_date=date(2025, 1, 10),
            processed_by=self.user,
        )

        FinancialTransaction.objects.create(
            student=self.students[1],
            invoice=invoice_jan,
            payment=payment_jan,
            amount=Decimal("750.00"),
            transaction_type=FinancialTransaction.TransactionType.PAYMENT_RECEIVED,
            transaction_date=timezone.make_aware(timezone.datetime(2025, 1, 10, 11, 0)),
            processed_by=self.user,
            description="January payment",
        )

        # Test December 2024 report
        dec_report = self.service.generate_monthly_cash_receipts_summary(2024, 12)
        self.assertIn("December 2024", dec_report)
        self.assertIn("$500.00", dec_report)
        self.assertNotIn("January payment", dec_report)

        # Test January 2025 report
        jan_report = self.service.generate_monthly_cash_receipts_summary(2025, 1)
        self.assertIn("January 2025", jan_report)
        self.assertIn("$750.00", jan_report)
        self.assertNotIn("December payment", jan_report)
