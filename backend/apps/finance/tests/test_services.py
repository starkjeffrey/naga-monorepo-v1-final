"""Unit tests for finance services.

Tests the business logic layer services including:
- SeparatedPricingService: Course and fee pricing calculations using separated pricing models
- InvoiceService: Invoice creation and management
- PaymentService: Payment processing and refunds
- FinancialTransactionService: Audit trail management

Following clean architecture testing with isolated unit tests
that focus on business logic without external dependencies.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.common.utils import get_current_date
from apps.curriculum.models import Course, Division, Term
from apps.finance.models import DefaultPricing, FeePricing, Invoice
from apps.finance.services import (
    FinancialError,
    FinancialTransactionService,
    InvoiceService,
    PaymentService,
    SeparatedPricingService,
)
from apps.people.models import Person, StudentProfile

User = get_user_model()


class SeparatedPricingServiceTest(TestCase):
    """Test separated pricing service business logic."""

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
            last_enrollment_date=get_current_date(),
        )

        # Create course
        division = Division.objects.create(name="Test Division", short_name="TD")
        self.course = Course.objects.create(code="TEST101", title="Test Course", credits=3, division=division)

        # Create term
        self.term = Term.objects.create(
            name="Test Term",
            start_date=get_current_date(),
            end_date=get_current_date() + timedelta(days=90),
        )

        # Create default pricing for the division/cycle
        self.default_pricing = DefaultPricing.objects.create(
            cycle=division,
            domestic_price=Decimal("500.00"),
            foreign_price=Decimal("750.00"),
            effective_date=get_current_date() - timedelta(days=30),
        )

        # Create fee pricing
        self.fee_pricing = FeePricing.objects.create(
            name="Registration Fee",
            fee_type="REGISTRATION",
            local_amount=Decimal("50.00"),
            foreign_amount=Decimal("75.00"),
            effective_date=get_current_date() - timedelta(days=30),
        )

    def test_get_course_price_default_pricing(self):
        """Test getting course price using default pricing."""
        price, currency, details = SeparatedPricingService.get_course_price(
            course=self.course,
            student=self.student,
            term=self.term,
        )
        self.assertEqual(price, Decimal("500.00"))
        self.assertEqual(currency, "USD")
        self.assertIn("pricing_type", details)
        self.assertEqual(details["pricing_type"], "default")

    def test_get_course_price_foreign_student(self):
        """Test getting course price for foreign student."""
        # Create foreign student
        foreign_person = Person.objects.create(
            personal_name="Foreign",
            family_name="Student",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="F",
            citizenship="US",
        )
        foreign_student = StudentProfile.objects.create(
            person=foreign_person,
            student_id=1002,
            last_enrollment_date=get_current_date(),
        )

        price, currency, details = SeparatedPricingService.get_course_price(
            course=self.course,
            student=foreign_student,
            term=self.term,
        )
        self.assertEqual(price, Decimal("750.00"))  # foreign price
        self.assertEqual(currency, "USD")
        self.assertEqual(details["pricing_type"], "default")

    def test_calculate_total_cost(self):
        """Test calculating total cost using separated pricing service."""
        # This test demonstrates the new pricing service can calculate costs
        cost_breakdown = SeparatedPricingService.calculate_total_cost(
            student=self.student,
            term=self.term,
            enrollments=[],  # Empty for simplicity
        )

        # Verify the structure returned
        self.assertIn("course_costs", cost_breakdown)
        self.assertIn("applicable_fees", cost_breakdown)
        self.assertIn("subtotal", cost_breakdown)
        self.assertIn("total_amount", cost_breakdown)
        self.assertIn("currency", cost_breakdown)


class InvoiceServiceTest(TestCase):
    """Test invoice service business logic."""

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
            last_enrollment_date=get_current_date(),
        )

        # Create term
        self.term = Term.objects.create(
            name="Test Term",
            start_date=get_current_date(),
            end_date=get_current_date() + timedelta(days=90),
        )

        from apps.curriculum.models import Division

        self.division = Division.objects.create(name="Test Division", short_name="TD")

        # Create default pricing
        from apps.finance.models import DefaultPricing

        self.default_pricing = DefaultPricing.objects.create(
            cycle=self.division,
            domestic_price=Decimal("500.00"),
            foreign_price=Decimal("750.00"),
            effective_date=get_current_date() - timedelta(days=30),
        )

    def test_generate_invoice_number(self):
        """Test invoice number generation."""
        invoice_number = InvoiceService.generate_invoice_number(self.term, self.student)

        self.assertTrue(invoice_number.startswith("2025-"))  # Should start with year
        self.assertIn("-1001-", invoice_number)  # Should contain student ID

    def test_create_invoice_basic(self):
        """Test basic invoice creation error with empty enrollments."""
        with self.assertRaises(FinancialError) as context:
            InvoiceService.create_invoice(
                student=self.student,
                term=self.term,
                enrollments=[],
                created_by=self.user,
            )

        self.assertIn("No valid course costs", str(context.exception))

    def test_create_invoice_with_custom_due_date(self):
        """Test invoice creation with custom due date - expects error with empty enrollments."""
        with self.assertRaises(FinancialError):
            InvoiceService.create_invoice(
                student=self.student,
                term=self.term,
                enrollments=[],
                due_days=14,
                created_by=self.user,
            )

    def test_send_invoice(self):
        """Test invoice sending."""
        invoice = Invoice.objects.create(
            invoice_number="TEST-2025-1001-0001",
            student=self.student,
            term=self.term,
            issue_date=get_current_date(),
            due_date=get_current_date() + timedelta(days=30),
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
            currency="USD",
            status=Invoice.InvoiceStatus.DRAFT,
        )

        # Initially draft
        self.assertEqual(invoice.status, "DRAFT")
        self.assertIsNone(invoice.sent_date)

        sent_invoice = InvoiceService.send_invoice(invoice, sent_by=self.user)

        self.assertEqual(sent_invoice.status, "SENT")
        self.assertIsNotNone(sent_invoice.sent_date)

    def test_update_invoice_payment_status(self):
        """Test invoice status updates based on payments."""
        # Create invoice directly
        invoice = Invoice.objects.create(
            invoice_number="TEST-2025-1001-0002",
            student=self.student,
            term=self.term,
            issue_date=get_current_date(),
            due_date=get_current_date() + timedelta(days=30),
            subtotal=Decimal("100.00"),
            total_amount=Decimal("100.00"),
            currency="USD",
            status=Invoice.InvoiceStatus.DRAFT,
        )

        # No payment - should remain as is
        InvoiceService.update_invoice_payment_status(invoice)
        self.assertEqual(invoice.status, "DRAFT")

        # Partial payment
        invoice.paid_amount = Decimal("50.00")
        invoice.save()

        InvoiceService.update_invoice_payment_status(invoice)
        self.assertEqual(invoice.status, "PARTIALLY_PAID")

        # Full payment
        invoice.paid_amount = Decimal("100.00")
        invoice.save()

        InvoiceService.update_invoice_payment_status(invoice)
        self.assertEqual(invoice.status, "PAID")


class PaymentServiceTest(TestCase):
    """Test payment service business logic."""

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

        student = StudentProfile.objects.create(
            person=person,
            student_id=1001,
            last_enrollment_date=get_current_date(),
        )

        term = Term.objects.create(
            name="Test Term",
            start_date=get_current_date(),
            end_date=get_current_date() + timedelta(days=90),
        )

        # Create invoice
        self.invoice = Invoice.objects.create(
            invoice_number="INV-TEST-001",
            student=student,
            term=term,
            subtotal=Decimal("500.00"),
            total_amount=Decimal("500.00"),
            currency="USD",
            due_date=get_current_date() + timedelta(days=30),
        )

    def test_generate_payment_reference(self):
        """Test payment reference generation."""
        ref = PaymentService.generate_payment_reference()

        self.assertTrue(ref.startswith("PAY-"))
        self.assertTrue(ref.endswith("-0001"))

    def test_record_payment_valid(self):
        """Test recording a valid payment."""
        payment = PaymentService.record_payment(
            invoice=self.invoice,
            amount=Decimal("300.00"),
            payment_method="CASH",
            payment_date=get_current_date(),
            processed_by=self.user,
            payer_name="Test Payer",
        )

        self.assertEqual(payment.amount, Decimal("300.00"))
        self.assertEqual(payment.invoice, self.invoice)
        self.assertEqual(payment.payment_method, "CASH")
        self.assertEqual(payment.status, "COMPLETED")
        self.assertTrue(payment.payment_reference.startswith("PAY-"))

        # Verify invoice updated
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.paid_amount, Decimal("300.00"))

    def test_record_payment_negative_amount(self):
        """Test that negative payment amounts are rejected."""
        with self.assertRaises(FinancialError):
            PaymentService.record_payment(
                invoice=self.invoice,
                amount=Decimal("-50.00"),
                payment_method="CASH",
                payment_date=get_current_date(),
                processed_by=self.user,
            )

    def test_record_payment_zero_amount(self):
        """Test that zero payment amounts are rejected."""
        with self.assertRaises(FinancialError):
            PaymentService.record_payment(
                invoice=self.invoice,
                amount=Decimal("0.00"),
                payment_method="CASH",
                payment_date=get_current_date(),
                processed_by=self.user,
            )

    def test_record_payment_overpayment(self):
        """Test that overpayments are rejected."""
        with self.assertRaises(FinancialError):
            PaymentService.record_payment(
                invoice=self.invoice,
                amount=Decimal("600.00"),  # More than invoice total
                payment_method="CASH",
                payment_date=get_current_date(),
                processed_by=self.user,
            )

    def test_refund_payment(self):
        """Test payment refund processing."""
        # Create original payment
        payment = PaymentService.record_payment(
            invoice=self.invoice,
            amount=Decimal("500.00"),
            payment_method="CREDIT_CARD",
            payment_date=get_current_date(),
            processed_by=self.user,
        )

        # Process refund
        refund = PaymentService.refund_payment(
            payment=payment,
            refund_amount=Decimal("100.00"),
            reason="Test refund",
            processed_by=self.user,
        )

        self.assertEqual(refund.amount, Decimal("-100.00"))
        self.assertEqual(refund.status, "REFUNDED")
        self.assertTrue(refund.external_reference.startswith("REFUND-"))

        # Verify invoice updated
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.paid_amount, Decimal("400.00"))

    def test_refund_payment_invalid_amount(self):
        """Test refund validation."""
        payment = PaymentService.record_payment(
            invoice=self.invoice,
            amount=Decimal("300.00"),
            payment_method="CASH",
            payment_date=get_current_date(),
            processed_by=self.user,
        )

        # Test refund more than payment
        with self.assertRaises(FinancialError):
            PaymentService.refund_payment(
                payment=payment,
                refund_amount=Decimal("400.00"),
                reason="Invalid refund",
                processed_by=self.user,
            )

        # Test negative refund
        with self.assertRaises(FinancialError):
            PaymentService.refund_payment(
                payment=payment,
                refund_amount=Decimal("-50.00"),
                reason="Invalid refund",
                processed_by=self.user,
            )


class FinancialTransactionServiceTest(TestCase):
    """Test financial transaction service."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(email="test@example.com", password="testpass123")

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
            last_enrollment_date=get_current_date(),
        )

    def test_generate_transaction_id(self):
        """Test transaction ID generation."""
        txn_id = FinancialTransactionService.generate_transaction_id()

        self.assertTrue(txn_id.startswith("TXN-"))
        self.assertEqual(len(txn_id), 25)  # TXN-YYYYMMDDHHMMSS-000001

    def test_record_transaction(self):
        """Test transaction recording."""
        txn = FinancialTransactionService.record_transaction(
            transaction_type="PAYMENT_RECEIVED",
            student=self.student,
            amount=Decimal("100.00"),
            currency="USD",
            description="Test transaction",
            processed_by=self.user,
            reference_data={"test": "data"},
        )

        self.assertEqual(txn.transaction_type, "PAYMENT_RECEIVED")
        self.assertEqual(txn.student, self.student)
        self.assertEqual(txn.amount, Decimal("100.00"))
        self.assertEqual(txn.currency, "USD")
        self.assertEqual(txn.processed_by, self.user)
        self.assertEqual(txn.reference_data["test"], "data")
        self.assertTrue(txn.transaction_id.startswith("TXN-"))

    def test_get_student_financial_history(self):
        """Test retrieving student financial history."""
        # Create multiple transactions
        for i in range(5):
            FinancialTransactionService.record_transaction(
                transaction_type="PAYMENT_RECEIVED",
                student=self.student,
                amount=Decimal(f"{100 + i}.00"),
                currency="USD",
                description=f"Transaction {i}",
                processed_by=self.user,
            )

        history = FinancialTransactionService.get_student_financial_history(student=self.student, limit=3)

        self.assertEqual(len(history), 3)

        # Should be in reverse chronological order
        for txn in history:
            self.assertEqual(txn.student, self.student)

        # First transaction should be most recent
        self.assertGreaterEqual(history[0].transaction_date, history[1].transaction_date)
