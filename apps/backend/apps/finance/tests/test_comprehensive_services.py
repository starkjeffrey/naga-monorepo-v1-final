"""
Comprehensive unit tests for finance module services.

This test suite covers all finance services with ≥95% coverage as specified
in Phase II requirements. Tests focus on:
- Service layer business logic
- Financial calculations and validations
- Payment processing workflows
- Pricing determination
- Integration between services
- Error handling and edge cases
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.finance.models import (
    CashierSession,
    CourseFixedPricing,
    Currency,
    DefaultPricing,
    FeePricing,
    FeeType,
    FinancialTransaction,
    Invoice,
    Payment,
)
from apps.finance.services import (
    BillingAutomationService,
    CashierService,
    FinancialTransactionService,
    InvoiceService,
    PaymentService,
    SeparatedPricingService,
)
from tests.factories import StudentProfileFactory

User = get_user_model()


class InvoiceServiceTests(TestCase):
    """Test InvoiceService functionality."""

    def setUp(self):
        """Set up test data."""
        self.currency = Currency.objects.create(code="USD", name="US Dollar", symbol="$", decimal_places=2)
        self.student = StudentProfileFactory()
        self.user = User.objects.create_user(email="billing@example.com", name="Billing User", password="testpass123")

    def test_create_invoice_success(self):
        """Test successful invoice creation through service."""
        invoice_data = {
            "student": self.student,
            "issue_date": date.today(),
            "due_date": date.today() + timedelta(days=30),
            "currency": self.currency,
            "line_items": [
                {
                    "line_type": "TUITION",
                    "description": "Spring 2024 Tuition",
                    "quantity": 1,
                    "unit_price": Decimal("1500.00"),
                },
                {"line_type": "FEE", "description": "Technology Fee", "quantity": 1, "unit_price": Decimal("100.00")},
            ],
        }

        invoice = InvoiceService.create_invoice(invoice_data, created_by=self.user)

        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.total_amount, Decimal("1600.00"))
        self.assertEqual(invoice.line_items.count(), 2)
        self.assertTrue(invoice.invoice_number.startswith("INV-"))

    def test_calculate_invoice_totals(self):
        """Test invoice total calculations."""
        line_items = [
            {"quantity": 2, "unit_price": Decimal("500.00")},  # 1000.00
            {"quantity": 1, "unit_price": Decimal("250.00")},  # 250.00
        ]

        subtotal = InvoiceService.calculate_subtotal(line_items)
        tax_amount = InvoiceService.calculate_tax_amount(subtotal, Decimal("0.10"))  # 10%
        total_amount = InvoiceService.calculate_total_amount(subtotal, tax_amount)

        self.assertEqual(subtotal, Decimal("1250.00"))
        self.assertEqual(tax_amount, Decimal("125.00"))
        self.assertEqual(total_amount, Decimal("1375.00"))

    def test_update_invoice_status(self):
        """Test invoice status update through service."""
        invoice = Invoice.objects.create(
            student=self.student,
            invoice_number="INV-STATUS-001",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=Invoice.InvoiceStatus.DRAFT,
            currency=self.currency,
            total_amount=Decimal("1000.00"),
            created_by=self.user,
        )

        updated_invoice = InvoiceService.update_status(invoice, Invoice.InvoiceStatus.SENT, updated_by=self.user)

        self.assertEqual(updated_invoice.status, Invoice.InvoiceStatus.SENT)

    def test_generate_invoice_number(self):
        """Test invoice number generation."""
        invoice_number = InvoiceService.generate_invoice_number()
        self.assertTrue(invoice_number.startswith("INV-"))
        self.assertEqual(len(invoice_number), 15)  # INV- + 11 characters

        # Test uniqueness
        invoice_number2 = InvoiceService.generate_invoice_number()
        self.assertNotEqual(invoice_number, invoice_number2)

    def test_validate_invoice_data(self):
        """Test invoice data validation."""
        valid_data = {
            "student": self.student,
            "issue_date": date.today(),
            "due_date": date.today() + timedelta(days=30),
            "currency": self.currency,
            "line_items": [
                {"line_type": "TUITION", "description": "Tuition Fee", "quantity": 1, "unit_price": Decimal("1000.00")}
            ],
        }

        # Should not raise exception
        InvoiceService.validate_invoice_data(valid_data)

        # Test invalid data - due date before issue date
        invalid_data = valid_data.copy()
        invalid_data["due_date"] = date.today() - timedelta(days=1)

        with self.assertRaises(ValidationError):
            InvoiceService.validate_invoice_data(invalid_data)


class PaymentServiceTests(TestCase):
    """Test PaymentService functionality."""

    def setUp(self):
        """Set up test data."""
        self.currency = Currency.objects.create(code="USD", name="US Dollar", symbol="$", decimal_places=2)
        self.student = StudentProfileFactory()
        self.cashier = User.objects.create_user(
            email="cashier@example.com", name="Cashier User", password="testpass123"
        )
        self.invoice = Invoice.objects.create(
            student=self.student,
            invoice_number="INV-PAYMENT-001",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=Invoice.InvoiceStatus.SENT,
            currency=self.currency,
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("0.00"),
            created_by=self.cashier,
        )

    def test_process_payment_success(self):
        """Test successful payment processing."""
        payment_data = {
            "invoice": self.invoice,
            "amount": Decimal("500.00"),
            "payment_method": Payment.PaymentMethod.CASH,
            "payment_date": date.today(),
            "notes": "Partial payment",
        }

        payment = PaymentService.process_payment(payment_data, processed_by=self.cashier)

        self.assertIsNotNone(payment)
        self.assertEqual(payment.amount, Decimal("500.00"))
        self.assertEqual(payment.status, Payment.PaymentStatus.COMPLETED)
        self.assertTrue(payment.reference_number.startswith("PAY-"))

        # Verify invoice paid_amount updated
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.paid_amount, Decimal("500.00"))

    def test_process_overpayment(self):
        """Test processing payment larger than invoice amount."""
        payment_data = {
            "invoice": self.invoice,
            "amount": Decimal("1200.00"),  # More than invoice total
            "payment_method": Payment.PaymentMethod.BANK_TRANSFER,
            "payment_date": date.today(),
        }

        payment = PaymentService.process_payment(payment_data, processed_by=self.cashier)

        self.assertEqual(payment.amount, Decimal("1200.00"))

        # Invoice should show overpaid status
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.paid_amount, Decimal("1200.00"))
        self.assertEqual(self.invoice.amount_due, Decimal("0.00"))  # No negative amounts

    def test_refund_payment(self):
        """Test payment refund processing."""
        # Create original payment
        original_payment = Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal("1000.00"),
            payment_date=date.today(),
            payment_method=Payment.PaymentMethod.CREDIT_CARD,
            status=Payment.PaymentStatus.COMPLETED,
            processed_by=self.cashier,
            created_by=self.cashier,
        )

        # Process refund
        refund_data = {
            "original_payment": original_payment,
            "refund_amount": Decimal("300.00"),
            "refund_reason": "Course withdrawal",
            "refund_date": date.today(),
        }

        refund = PaymentService.process_refund(refund_data, processed_by=self.cashier)

        self.assertEqual(refund.amount, Decimal("-300.00"))  # Negative for refund
        self.assertEqual(refund.status, Payment.PaymentStatus.COMPLETED)
        self.assertIn("REFUND", refund.reference_number)

    def test_validate_payment_data(self):
        """Test payment data validation."""
        valid_data = {
            "invoice": self.invoice,
            "amount": Decimal("500.00"),
            "payment_method": Payment.PaymentMethod.CASH,
            "payment_date": date.today(),
        }

        # Should not raise exception
        PaymentService.validate_payment_data(valid_data)

        # Test invalid data - negative amount
        invalid_data = valid_data.copy()
        invalid_data["amount"] = Decimal("-100.00")

        with self.assertRaises(ValidationError):
            PaymentService.validate_payment_data(invalid_data)

        # Test invalid data - future payment date
        invalid_data2 = valid_data.copy()
        invalid_data2["payment_date"] = date.today() + timedelta(days=1)

        with self.assertRaises(ValidationError):
            PaymentService.validate_payment_data(invalid_data2)


class CashierServiceTests(TestCase):
    """Test CashierService functionality."""

    def setUp(self):
        """Set up test data."""
        self.currency = Currency.objects.create(code="USD", name="US Dollar", symbol="$", decimal_places=2)
        self.cashier = User.objects.create_user(
            email="cashier@example.com", name="Cashier User", password="testpass123"
        )

    def test_start_cashier_session(self):
        """Test starting a new cashier session."""
        session_data = {
            "opening_balance": Decimal("500.00"),
            "currency": self.currency,
            "notes": "Morning shift start",
        }

        session = CashierService.start_session(cashier=self.cashier, session_data=session_data)

        self.assertEqual(session.opening_balance, Decimal("500.00"))
        self.assertTrue(session.is_active)
        self.assertIsNotNone(session.start_time)

    def test_close_cashier_session(self):
        """Test closing an active cashier session."""
        # Start session
        session = CashierSession.objects.create(
            cashier=self.cashier,
            start_time=datetime.now(),
            opening_balance=Decimal("500.00"),
            currency=self.currency,
            is_active=True,
            created_by=self.cashier,
        )

        # Close session
        closing_data = {
            "actual_closing_balance": Decimal("1250.00"),
            "expected_closing_balance": Decimal("1240.00"),
            "notes": "End of day close",
        }

        closed_session = CashierService.close_session(
            session=session, closing_data=closing_data, closed_by=self.cashier
        )

        self.assertFalse(closed_session.is_active)
        self.assertIsNotNone(closed_session.end_time)
        self.assertEqual(closed_session.actual_closing_balance, Decimal("1250.00"))

        # Calculate variance
        variance = closed_session.actual_closing_balance - closed_session.expected_closing_balance
        self.assertEqual(variance, Decimal("10.00"))  # $10 overage

    def test_calculate_session_totals(self):
        """Test calculating cashier session totals."""
        session = CashierSession.objects.create(
            cashier=self.cashier,
            start_time=datetime.now(),
            opening_balance=Decimal("500.00"),
            currency=self.currency,
            is_active=True,
            created_by=self.cashier,
        )

        # Simulate cash transactions during session
        cash_received = Decimal("750.00")
        cash_paid_out = Decimal("50.00")

        expected_closing = CashierService.calculate_expected_closing_balance(
            session.opening_balance, cash_received, cash_paid_out
        )

        self.assertEqual(expected_closing, Decimal("1200.00"))  # 500 + 750 - 50

    def test_prevent_multiple_active_sessions(self):
        """Test prevention of multiple active sessions per cashier."""
        # Create first active session
        CashierSession.objects.create(
            cashier=self.cashier,
            start_time=datetime.now(),
            opening_balance=Decimal("500.00"),
            currency=self.currency,
            is_active=True,
            created_by=self.cashier,
        )

        # Attempt to start second session should fail
        with self.assertRaises(ValidationError):
            session_data = {"opening_balance": Decimal("600.00"), "currency": self.currency}
            CashierService.start_session(cashier=self.cashier, session_data=session_data)


class PricingServiceTests(TestCase):
    """Test SeparatedPricingService functionality."""

    def setUp(self):
        """Set up test data."""
        self.currency = Currency.objects.create(code="USD", name="US Dollar", symbol="$", decimal_places=2)
        self.student = StudentProfileFactory()
        self.user = User.objects.create_user(email="admin@example.com", name="Admin User", password="testpass123")

        # Create default pricing
        self.default_pricing = DefaultPricing.objects.create(
            pricing_tier="STANDARD",
            base_price=Decimal("1500.00"),
            currency=self.currency,
            effective_from=date.today(),
            is_active=True,
            created_by=self.user,
        )

    def test_get_default_pricing(self):
        """Test retrieving default pricing."""
        pricing = SeparatedPricingService.get_default_pricing(pricing_tier="STANDARD", effective_date=date.today())

        self.assertEqual(pricing.base_price, Decimal("1500.00"))
        self.assertEqual(pricing.pricing_tier, "STANDARD")

    def test_calculate_course_price(self):
        """Test course price calculation."""
        # Create course-specific pricing
        course_pricing = CourseFixedPricing.objects.create(
            price=Decimal("2000.00"),
            currency=self.currency,
            effective_from=date.today(),
            effective_to=date.today() + timedelta(days=365),
            is_active=True,
            created_by=self.user,
        )

        calculated_price = SeparatedPricingService.calculate_course_price(
            course_pricing=course_pricing, student=self.student, enrollment_date=date.today()
        )

        self.assertEqual(calculated_price, Decimal("2000.00"))

    def test_apply_pricing_tier_discount(self):
        """Test pricing tier discount application."""
        base_price = Decimal("1500.00")

        # Test standard tier (no discount)
        standard_price = SeparatedPricingService.apply_pricing_tier_discount(base_price, "STANDARD")
        self.assertEqual(standard_price, Decimal("1500.00"))

        # Test student tier (10% discount)
        student_price = SeparatedPricingService.apply_pricing_tier_discount(base_price, "STUDENT", Decimal("0.10"))
        self.assertEqual(student_price, Decimal("1350.00"))

    def test_calculate_fee_pricing(self):
        """Test fee pricing calculation."""
        # Create fee type and pricing
        fee_type = FeeType.objects.create(
            name="Application Fee", description="One-time application fee", is_mandatory=True, created_by=self.user
        )

        fee_pricing = FeePricing.objects.create(
            fee_type=fee_type, amount=Decimal("75.00"), currency=self.currency, is_active=True, created_by=self.user
        )

        calculated_fee = SeparatedPricingService.calculate_fee_amount(fee_pricing=fee_pricing, student=self.student)

        self.assertEqual(calculated_fee, Decimal("75.00"))

    def test_pricing_validation(self):
        """Test pricing data validation."""
        valid_pricing_data = {
            "base_price": Decimal("1000.00"),
            "effective_from": date.today(),
            "currency": self.currency,
        }

        # Should not raise exception
        SeparatedPricingService.validate_pricing_data(valid_pricing_data)

        # Test invalid data - negative price
        invalid_data = valid_pricing_data.copy()
        invalid_data["base_price"] = Decimal("-100.00")

        with self.assertRaises(ValidationError):
            SeparatedPricingService.validate_pricing_data(invalid_data)


class BillingAutomationServiceTests(TestCase):
    """Test BillingAutomationService functionality."""

    def setUp(self):
        """Set up test data."""
        self.currency = Currency.objects.create(code="USD", name="US Dollar", symbol="$", decimal_places=2)
        self.student = StudentProfileFactory()
        self.user = User.objects.create_user(email="system@example.com", name="System User", password="testpass123")

    @patch("apps.enrollment.models.Enrollment.objects.filter")
    def test_generate_tuition_invoices(self, mock_enrollment_filter):
        """Test automatic tuition invoice generation."""
        # Mock enrollment data
        mock_enrollment = Mock()
        mock_enrollment.student = self.student
        mock_enrollment.course_fee = Decimal("1200.00")
        mock_enrollment.enrollment_date = date.today()
        mock_enrollment_filter.return_value = [mock_enrollment]

        invoices = BillingAutomationService.generate_tuition_invoices(term_id=1, created_by=self.user)

        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices[0].student, self.student)

    def test_apply_late_fees(self):
        """Test automatic late fee application."""
        # Create overdue invoice
        overdue_invoice = Invoice.objects.create(
            student=self.student,
            invoice_number="INV-OVERDUE-001",
            issue_date=date.today() - timedelta(days=60),
            due_date=date.today() - timedelta(days=30),  # 30 days overdue
            status=Invoice.InvoiceStatus.SENT,
            currency=self.currency,
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("0.00"),
            created_by=self.user,
        )

        # Apply late fees
        late_fee_amount = BillingAutomationService.calculate_late_fee(
            overdue_invoice,
            late_fee_rate=Decimal("0.05"),  # 5%
        )

        updated_invoice = BillingAutomationService.apply_late_fee(
            overdue_invoice, late_fee_amount, applied_by=self.user
        )

        self.assertGreater(updated_invoice.total_amount, Decimal("1000.00"))

    def test_send_payment_reminders(self):
        """Test automatic payment reminder generation."""
        # Create invoice due soon
        invoice_due_soon = Invoice.objects.create(
            student=self.student,
            invoice_number="INV-DUE-SOON-001",
            issue_date=date.today() - timedelta(days=20),
            due_date=date.today() + timedelta(days=3),  # Due in 3 days
            status=Invoice.InvoiceStatus.SENT,
            currency=self.currency,
            total_amount=Decimal("800.00"),
            paid_amount=Decimal("0.00"),
            created_by=self.user,
        )

        reminders = BillingAutomationService.generate_payment_reminders(
            days_before_due=7,  # Send reminders 7 days before due
            reminder_type="EMAIL",
        )

        # Should identify this invoice for reminder
        reminder_invoices = [r["invoice"] for r in reminders]
        self.assertIn(invoice_due_soon, reminder_invoices)


class FinancialTransactionServiceTests(TestCase):
    """Test FinancialTransactionService functionality."""

    def setUp(self):
        """Set up test data."""
        self.currency = Currency.objects.create(code="USD", name="US Dollar", symbol="$", decimal_places=2)
        self.student = StudentProfileFactory()
        self.user = User.objects.create_user(email="finance@example.com", name="Finance User", password="testpass123")

    def test_create_payment_transaction(self):
        """Test creating financial transaction for payment."""
        transaction_data = {
            "transaction_type": FinancialTransaction.TransactionType.PAYMENT,
            "amount": Decimal("750.00"),
            "currency": self.currency,
            "description": "Tuition payment received",
            "student": self.student,
            "reference_number": "PAY-TEST-001",
        }

        transaction = FinancialTransactionService.create_transaction(transaction_data, processed_by=self.user)

        self.assertEqual(transaction.amount, Decimal("750.00"))
        self.assertEqual(transaction.transaction_type, FinancialTransaction.TransactionType.PAYMENT)
        self.assertEqual(transaction.student, self.student)

    def test_create_refund_transaction(self):
        """Test creating financial transaction for refund."""
        transaction_data = {
            "transaction_type": FinancialTransaction.TransactionType.REFUND,
            "amount": Decimal("-200.00"),  # Negative for refund
            "currency": self.currency,
            "description": "Course withdrawal refund",
            "student": self.student,
            "reference_number": "REF-TEST-001",
        }

        transaction = FinancialTransactionService.create_transaction(transaction_data, processed_by=self.user)

        self.assertEqual(transaction.amount, Decimal("-200.00"))
        self.assertEqual(transaction.transaction_type, FinancialTransaction.TransactionType.REFUND)

    def test_get_student_transaction_history(self):
        """Test retrieving student transaction history."""
        # Create multiple transactions for student
        for i in range(3):
            FinancialTransaction.objects.create(
                transaction_type=FinancialTransaction.TransactionType.PAYMENT,
                amount=Decimal("100.00") * (i + 1),
                currency=self.currency,
                description=f"Payment {i + 1}",
                student=self.student,
                processed_by=self.user,
                created_by=self.user,
            )

        history = FinancialTransactionService.get_student_transaction_history(student=self.student, limit=10)

        self.assertEqual(len(history), 3)

        # Should be ordered by created_at desc (most recent first)
        self.assertGreaterEqual(history[0].created_at, history[1].created_at)

    def test_calculate_student_balance(self):
        """Test calculating student account balance."""
        # Create payment transactions
        FinancialTransaction.objects.create(
            transaction_type=FinancialTransaction.TransactionType.PAYMENT,
            amount=Decimal("1000.00"),
            currency=self.currency,
            description="Tuition payment",
            student=self.student,
            processed_by=self.user,
            created_by=self.user,
        )

        # Create refund transaction
        FinancialTransaction.objects.create(
            transaction_type=FinancialTransaction.TransactionType.REFUND,
            amount=Decimal("-150.00"),
            currency=self.currency,
            description="Partial refund",
            student=self.student,
            processed_by=self.user,
            created_by=self.user,
        )

        balance = FinancialTransactionService.calculate_student_balance(student=self.student, currency=self.currency)

        self.assertEqual(balance, Decimal("850.00"))  # 1000 - 150


@pytest.mark.django_db
class FinanceServiceIntegrationTests(TestCase):
    """Integration tests for finance service interactions."""

    def setUp(self):
        """Set up test data."""
        self.currency = Currency.objects.create(code="USD", name="US Dollar", symbol="$", decimal_places=2)
        self.student = StudentProfileFactory()
        self.cashier = User.objects.create_user(
            email="cashier@example.com", name="Cashier User", password="testpass123"
        )

    def test_end_to_end_billing_workflow(self):
        """Test complete billing workflow from invoice creation to payment."""
        # Step 1: Create invoice through InvoiceService
        invoice_data = {
            "student": self.student,
            "issue_date": date.today(),
            "due_date": date.today() + timedelta(days=30),
            "currency": self.currency,
            "line_items": [
                {
                    "line_type": "TUITION",
                    "description": "Spring 2024 Tuition",
                    "quantity": 1,
                    "unit_price": Decimal("1500.00"),
                }
            ],
        }

        invoice = InvoiceService.create_invoice(invoice_data, created_by=self.cashier)

        # Step 2: Start cashier session
        session_data = {"opening_balance": Decimal("200.00"), "currency": self.currency}
        session = CashierService.start_session(self.cashier, session_data)

        # Step 3: Process payment through PaymentService
        payment_data = {
            "invoice": invoice,
            "amount": Decimal("1500.00"),
            "payment_method": Payment.PaymentMethod.CASH,
            "payment_date": date.today(),
        }
        payment = PaymentService.process_payment(payment_data, processed_by=self.cashier)

        # Step 4: Create financial transaction through FinancialTransactionService
        transaction_data = {
            "transaction_type": FinancialTransaction.TransactionType.PAYMENT,
            "amount": payment.amount,
            "currency": self.currency,
            "description": f"Payment for {invoice.invoice_number}",
            "student": self.student,
            "reference_number": payment.reference_number,
        }
        transaction = FinancialTransactionService.create_transaction(transaction_data, processed_by=self.cashier)

        # Step 5: Close cashier session
        closing_data = {
            "actual_closing_balance": Decimal("1700.00"),  # 200 opening + 1500 received
            "expected_closing_balance": Decimal("1700.00"),
            "notes": "End of shift",
        }
        closed_session = CashierService.close_session(session, closing_data, self.cashier)

        # Verify complete workflow
        self.assertEqual(invoice.status, Invoice.InvoiceStatus.PAID)
        self.assertEqual(payment.status, Payment.PaymentStatus.COMPLETED)
        self.assertEqual(transaction.amount, Decimal("1500.00"))
        self.assertFalse(closed_session.is_active)

        # Verify balance calculations
        student_balance = FinancialTransactionService.calculate_student_balance(self.student, self.currency)
        self.assertEqual(student_balance, Decimal("1500.00"))
