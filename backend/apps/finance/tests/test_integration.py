"""Integration tests for finance workflows.

These tests verify end-to-end financial workflows including:
- Automatic invoice generation on enrollment
- Payment processing and invoice updates
- Financial transaction audit trails
- Signal-driven billing automation

Following clean architecture testing principles with proper test isolation
and comprehensive coverage of business processes.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from django.utils import timezone

from apps.common.utils import get_current_date
from apps.curriculum.models import Course, Division, Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.finance.models import (
    DefaultPricing,
    FeePricing,
    FinancialTransaction,
    Invoice,
    InvoiceLineItem,
    Payment,
)
from apps.finance.services import (
    FinancialError,
    FinancialTransactionService,
    InvoiceService,
    PaymentService,
    SeparatedPricingService,
)
from apps.people.models import Person, StudentProfile
from apps.scheduling.models import ClassHeader

User = get_user_model()


class FinanceIntegrationTestCase(TransactionTestCase):
    """Base test case for finance integration tests.

    Uses TransactionTestCase to properly test signals and transactions.
    """

    def setUp(self):
        """Set up test data for finance integration tests."""
        # Create test user
        self.user = User.objects.create_user(email="test@example.com", password="testpass123")

        # Create system user for automated operations
        self.system_user = User.objects.create_user(
            email="system@naga-sis.local",
            password="systempass",
            is_active=False,
        )

        # Create test person and student
        self.person = Person.objects.create(
            personal_name="John",
            family_name="Doe",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="M",
            citizenship="KH",
            personal_email="john.doe@example.com",
        )

        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id=20241001,
            last_enrollment_date=get_current_date(),
            current_status="ACTIVE",
        )

        # Create division and course
        self.division = Division.objects.create(
            name="Computer Science",
            short_name="CS",
            description="Computer Science Division",
        )

        self.course = Course.objects.create(
            code="CS101",
            title="Introduction to Programming",
            short_title="Intro Programming",
            credits=3,
            division=self.division,
            cycle="BA",
            description="Basic programming concepts",
        )

        # Create default pricing for the division
        self.default_pricing = DefaultPricing.objects.create(
            cycle=self.division,
            domestic_price=Decimal("500.00"),
            foreign_price=Decimal("750.00"),
            effective_date=get_current_date() - timedelta(days=30),
        )

        # Create term
        self.term = Term.objects.create(
            name="Fall 2024",
            start_date=get_current_date(),
            end_date=get_current_date() + timedelta(days=120),
            term_type="BA",
        )

        # Create class header
        self.class_header = ClassHeader.objects.create(
            course=self.course,
            term=self.term,
            section_id="A",
            max_enrollment=30,
            notes="Introduction section",
        )

        # Create fee pricing
        self.fee_pricing = FeePricing.objects.create(
            name="Registration Fee",
            fee_type="REGISTRATION",
            local_amount=Decimal("50.00"),
            foreign_amount=Decimal("75.00"),
            currency="USD",
            is_per_term=True,
            is_mandatory=True,
            effective_date=get_current_date() - timedelta(days=30),
        )


class EnrollmentBillingIntegrationTest(FinanceIntegrationTestCase):
    """Test automatic billing on enrollment."""

    def test_automatic_invoice_creation_on_enrollment(self):
        """Test that invoice is automatically created when student enrolls."""
        # Verify no invoice exists initially
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertEqual(InvoiceLineItem.objects.count(), 0)
        self.assertEqual(FinancialTransaction.objects.count(), 0)

        # Create enrollment (should trigger invoice creation via signal)
        enrollment = ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            enrollment_date=timezone.now(),
            status="ENROLLED",
            enrolled_by=self.user,
        )

        # Verify invoice was created
        self.assertEqual(Invoice.objects.count(), 1)

        invoice = Invoice.objects.first()
        self.assertEqual(invoice.student, self.student)
        self.assertEqual(invoice.term, self.term)
        self.assertEqual(invoice.status, "DRAFT")
        self.assertEqual(invoice.currency, "USD")

        # Verify line items were created (course + mandatory fee)
        line_items = invoice.line_items.all()
        self.assertEqual(line_items.count(), 2)

        # Find course line item
        course_line = line_items.filter(line_item_type="COURSE").first()
        self.assertIsNotNone(course_line)
        self.assertEqual(course_line.unit_price, Decimal("500.00"))
        self.assertEqual(course_line.quantity, Decimal("1.00"))
        self.assertEqual(course_line.line_total, Decimal("500.00"))
        self.assertEqual(course_line.enrollment, enrollment)

        # Find fee line item
        fee_line = line_items.filter(line_item_type="FEE").first()
        self.assertIsNotNone(fee_line)
        self.assertEqual(fee_line.unit_price, Decimal("50.00"))

        # Verify invoice totals (course + fee)
        self.assertEqual(invoice.subtotal, Decimal("550.00"))
        self.assertEqual(invoice.total_amount, Decimal("550.00"))

        # Verify financial transaction was created
        transactions = FinancialTransaction.objects.all()
        self.assertTrue(transactions.count() >= 1)

        # Find the invoice creation transaction
        invoice_txn = transactions.filter(transaction_type="INVOICE_CREATED").first()
        self.assertIsNotNone(invoice_txn)
        self.assertEqual(invoice_txn.student, self.student)
        self.assertEqual(invoice_txn.invoice, invoice)

    def test_multiple_enrollments_single_invoice(self):
        """Test that multiple enrollments in same term are added to same invoice."""
        # Create first enrollment
        ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            enrollment_date=timezone.now(),
            status="ENROLLED",
            enrolled_by=self.user,
        )

        # Create second course and class
        course2 = Course.objects.create(
            code="CS102",
            title="Data Structures",
            credits=3,
            division=self.division,
            description="Data structures and algorithms",
        )

        from apps.finance.models import CourseFixedPricing

        CourseFixedPricing.objects.create(
            course=course2,
            domestic_price=Decimal("600.00"),
            foreign_price=Decimal("900.00"),
            effective_date=get_current_date() - timedelta(days=30),
        )

        class_header2 = ClassHeader.objects.create(
            course=course2,
            term=self.term,
            section_id="A",
            max_enrollment=25,
            notes="Data structures section",
        )

        # Create second enrollment
        ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=class_header2,
            enrollment_date=timezone.now(),
            status="ENROLLED",
            enrolled_by=self.user,
        )

        # Should still have only one invoice
        self.assertEqual(Invoice.objects.count(), 1)

        invoice = Invoice.objects.first()
        line_items = invoice.line_items.all()

        # Should have three line items: course 1, course 2, registration fee
        self.assertEqual(line_items.count(), 3)

        # Verify total is sum of both courses plus registration fee
        # Course 1: 500, Course 2: 600, Registration fee: 50 (per term)
        self.assertEqual(invoice.subtotal, Decimal("1150.00"))  # 500 + 600 + 50
        self.assertEqual(invoice.total_amount, Decimal("1150.00"))

    def test_enrollment_status_change_no_duplicate_billing(self):
        """Test that only ENROLLED status on creation triggers billing."""
        # Create a pending enrollment - no invoice should be created
        enrollment = ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            enrollment_date=timezone.now(),
            status="PENDING",  # Start with pending
            enrolled_by=self.user,
        )

        # No invoice should be created for pending enrollment
        self.assertEqual(Invoice.objects.count(), 0)

        # Change to enrolled status - signal only fires on creation, not updates
        enrollment.status = "ENROLLED"
        enrollment.save()

        # Invoice still should not be created (signal only triggers on creation)
        self.assertEqual(Invoice.objects.count(), 0)

        # Test that ENROLLED status on creation does create invoice
        # Delete the pending enrollment first
        enrollment.delete()

        # Create new enrollment with ENROLLED status
        enrolled_enrollment = ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            enrollment_date=timezone.now(),
            status="ENROLLED",  # ENROLLED on creation
            enrolled_by=self.user,
        )

        # Now invoice should be created
        self.assertEqual(Invoice.objects.count(), 1)

        # Change status - should not create duplicate invoice
        enrolled_enrollment.status = "COMPLETED"
        enrolled_enrollment.save()

        # Should still be only one invoice
        self.assertEqual(Invoice.objects.count(), 1)


class PaymentProcessingIntegrationTest(FinanceIntegrationTestCase):
    """Test payment processing workflows."""

    def setUp(self):
        super().setUp()

        # Create an invoice with line items
        self.invoice = InvoiceService.create_invoice(
            student=self.student,
            term=self.term,
            enrollments=[],
            created_by=self.user,
        )

        # Add course line item manually
        InvoiceLineItem.objects.create(
            invoice=self.invoice,
            line_item_type="COURSE",
            description=f"Course: {self.course.code} - {self.course.title}",
            unit_price=Decimal("500.00"),
            quantity=Decimal("1.00"),
            line_total=Decimal("500.00"),
        )

        # Add fee line item
        InvoiceLineItem.objects.create(
            invoice=self.invoice,
            line_item_type="FEE",
            description="Registration Fee",
            unit_price=Decimal("50.00"),
            quantity=Decimal("1.00"),
            line_total=Decimal("50.00"),
            fee_pricing=self.fee_pricing,
        )

        # Update invoice totals
        self.invoice.subtotal = Decimal("550.00")
        self.invoice.total_amount = Decimal("550.00")
        self.invoice.save()

    def test_full_payment_processing(self):
        """Test complete payment processing workflow."""
        FinancialTransaction.objects.count()

        # Record full payment
        payment = PaymentService.record_payment(
            invoice=self.invoice,
            amount=Decimal("550.00"),
            payment_method="CASH",
            payment_date=get_current_date(),
            processed_by=self.user,
            payer_name="John Doe",
            external_reference="CASH-001",
            notes="Full payment in cash",
        )

        # Verify payment was created
        self.assertEqual(payment.amount, Decimal("550.00"))
        self.assertEqual(payment.status, "COMPLETED")
        self.assertEqual(payment.currency, "USD")
        self.assertTrue(payment.payment_reference.startswith("PAY-"))

        # Verify invoice was updated
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.paid_amount, Decimal("550.00"))
        self.assertEqual(self.invoice.status, "PAID")
        self.assertEqual(self.invoice.amount_due, Decimal("0.00"))

        # Verify financial transaction was created
        new_transactions = FinancialTransaction.objects.filter(transaction_type="PAYMENT_RECEIVED")
        self.assertEqual(new_transactions.count(), 1)

        txn = new_transactions.first()
        self.assertEqual(txn.student, self.student)
        self.assertEqual(txn.amount, Decimal("550.00"))
        self.assertEqual(txn.invoice, self.invoice)
        self.assertEqual(txn.payment, payment)
        self.assertEqual(txn.processed_by, self.user)

    def test_partial_payment_processing(self):
        """Test partial payment processing."""
        # Record partial payment
        payment = PaymentService.record_payment(
            invoice=self.invoice,
            amount=Decimal("300.00"),
            payment_method="BANK_TRANSFER",
            payment_date=get_current_date(),
            processed_by=self.user,
            payer_name="John Doe",
        )

        # Verify payment
        self.assertEqual(payment.amount, Decimal("300.00"))
        self.assertEqual(payment.status, "COMPLETED")

        # Verify invoice status
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.paid_amount, Decimal("300.00"))
        self.assertEqual(self.invoice.status, "PARTIALLY_PAID")
        self.assertEqual(self.invoice.amount_due, Decimal("250.00"))

        # Record second payment to complete
        PaymentService.record_payment(
            invoice=self.invoice,
            amount=Decimal("250.00"),
            payment_method="CREDIT_CARD",
            payment_date=get_current_date(),
            processed_by=self.user,
            payer_name="John Doe",
        )

        # Verify final state
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.paid_amount, Decimal("550.00"))
        self.assertEqual(self.invoice.status, "PAID")
        self.assertEqual(self.invoice.amount_due, Decimal("0.00"))

        # Verify both payments exist
        payments = Payment.objects.filter(invoice=self.invoice)
        self.assertEqual(payments.count(), 2)

    def test_payment_refund_processing(self):
        """Test payment refund workflow."""
        # Make initial payment
        payment = PaymentService.record_payment(
            invoice=self.invoice,
            amount=Decimal("550.00"),
            payment_method="CREDIT_CARD",
            payment_date=get_current_date(),
            processed_by=self.user,
            payer_name="John Doe",
        )

        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, "PAID")

        # Process refund
        refund = PaymentService.refund_payment(
            payment=payment,
            refund_amount=Decimal("100.00"),
            reason="Course cancellation",
            processed_by=self.user,
        )

        # Verify refund
        self.assertEqual(refund.amount, Decimal("-100.00"))
        self.assertEqual(refund.status, "REFUNDED")
        self.assertTrue(refund.external_reference.startswith("REFUND-"))

        # Verify invoice updated
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.paid_amount, Decimal("450.00"))
        self.assertEqual(self.invoice.status, "PARTIALLY_PAID")
        self.assertEqual(self.invoice.amount_due, Decimal("100.00"))

        # Verify refund transaction
        refund_txns = FinancialTransaction.objects.filter(transaction_type="PAYMENT_REFUNDED")
        self.assertEqual(refund_txns.count(), 1)

        refund_txn = refund_txns.first()
        self.assertEqual(refund_txn.amount, Decimal("-100.00"))
        self.assertEqual(refund_txn.payment, refund)


class PricingCalculationIntegrationTest(FinanceIntegrationTestCase):
    """Test pricing calculation workflows."""

    def test_course_fixed_pricing_override(self):
        """Test course-specific pricing override using CourseFixedPricing."""
        from apps.finance.models import CourseFixedPricing

        # Create course-specific pricing to override default
        CourseFixedPricing.objects.create(
            course=self.course,
            domestic_price=Decimal("450.00"),  # Different from default 500.00
            foreign_price=Decimal("675.00"),
            effective_date=get_current_date() - timedelta(days=10),  # More recent than default
        )

        # Get course price - should use course-specific pricing
        price, currency, details = SeparatedPricingService.get_course_price(
            course=self.course,
            student=self.student,
            term=self.term,
        )

        # Should be course-specific price
        self.assertEqual(price, Decimal("450.00"))
        self.assertEqual(currency, "USD")
        self.assertEqual(details["pricing_type"], "fixed")

    def test_fee_pricing_calculation(self):
        """Test fee pricing calculation for different fee types."""
        # Create additional fees
        FeePricing.objects.create(
            name="Technology Fee",
            fee_type="TECHNOLOGY",
            local_amount=Decimal("25.00"),
            foreign_amount=Decimal("37.50"),
            currency="USD",
            is_per_course=True,
            is_mandatory=True,
            effective_date=get_current_date() - timedelta(days=30),
        )

        FeePricing.objects.create(
            name="Library Fee",
            fee_type="LIBRARY",
            local_amount=Decimal("15.00"),
            foreign_amount=Decimal("22.50"),
            currency="USD",
            is_per_term=True,
            is_mandatory=False,
            effective_date=get_current_date() - timedelta(days=30),
        )

        # Get applicable fees - pass empty list for 2 courses
        # Since this is a unit test, we can simulate having 2 courses
        mock_enrollments = [
            None,
            None,
        ]  # Two enrollments for per-course fee calculation
        cost_breakdown = SeparatedPricingService.calculate_total_cost(
            student=self.student, term=self.term, enrollments=mock_enrollments
        )
        fees = cost_breakdown["applicable_fees"]

        # Should include registration (per-term) and technology (per-course * 2)
        mandatory_fees = [f for f in fees if f["is_mandatory"]]
        self.assertEqual(len(mandatory_fees), 2)

        # Find fees by type
        reg_fee = next(f for f in fees if f["fee_type"] == "REGISTRATION")
        tech_fee = next(f for f in fees if f["fee_type"] == "TECHNOLOGY")

        self.assertEqual(reg_fee["total_amount"], 50.00)  # Per term
        self.assertEqual(tech_fee["total_amount"], 50.00)  # Per course * 2


class FinancialAuditTrailIntegrationTest(FinanceIntegrationTestCase):
    """Test financial audit trail and transaction logging."""

    def test_complete_student_financial_history(self):
        """Test complete financial history tracking for a student."""
        # Create enrollment (triggers invoice creation)
        ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=self.class_header,
            enrollment_date=timezone.now(),
            status="ENROLLED",
            enrolled_by=self.user,
        )

        invoice = Invoice.objects.get(student=self.student)

        InvoiceService.send_invoice(invoice, sent_by=self.user)

        # Make payment
        PaymentService.record_payment(
            invoice=invoice,
            amount=Decimal("300.00"),
            payment_method="BANK_TRANSFER",
            payment_date=get_current_date(),
            processed_by=self.user,
            payer_name="John Doe",
        )

        # Make second payment
        PaymentService.record_payment(
            invoice=invoice,
            amount=Decimal("200.00"),
            payment_method="CASH",
            payment_date=get_current_date(),
            processed_by=self.user,
            payer_name="John Doe",
        )

        # Get student financial history
        history = FinancialTransactionService.get_student_financial_history(student=self.student, term=self.term)

        # Should have multiple transactions
        self.assertTrue(len(history) >= 4)  # Creation, sent, payment1, payment2

        # Verify transaction types
        transaction_types = [txn.transaction_type for txn in history]
        self.assertIn("INVOICE_CREATED", transaction_types)
        self.assertIn("INVOICE_SENT", transaction_types)
        self.assertIn("PAYMENT_RECEIVED", transaction_types)

        # Verify all transactions are for this student
        for txn in history:
            self.assertEqual(txn.student, self.student)

        # Verify chronological order (most recent first)
        for i in range(len(history) - 1):
            self.assertGreaterEqual(history[i].transaction_date, history[i + 1].transaction_date)

    def test_invoice_status_change_auditing(self):
        """Test that invoice status changes are properly audited."""
        invoice = InvoiceService.create_invoice(
            student=self.student,
            term=self.term,
            enrollments=[],
            created_by=self.user,
        )

        FinancialTransaction.objects.count()

        # Change status to sent
        invoice.status = "SENT"
        invoice.save()

        # Should create audit transaction
        new_txns = FinancialTransaction.objects.filter(invoice=invoice, transaction_type="INVOICE_SENT")
        self.assertEqual(new_txns.count(), 1)

        # Change to cancelled
        invoice.status = "CANCELLED"
        invoice.save()

        # Should create another audit transaction
        cancel_txns = FinancialTransaction.objects.filter(invoice=invoice, transaction_type="INVOICE_CANCELLED")
        self.assertEqual(cancel_txns.count(), 1)

        # Verify reference data includes status changes
        cancel_txn = cancel_txns.first()
        self.assertIn("old_status", cancel_txn.reference_data)
        self.assertIn("new_status", cancel_txn.reference_data)
        self.assertEqual(cancel_txn.reference_data["old_status"], "SENT")
        self.assertEqual(cancel_txn.reference_data["new_status"], "CANCELLED")


class FinancialErrorHandlingTest(FinanceIntegrationTestCase):
    """Test error handling in financial workflows."""

    def test_invoice_creation_with_invalid_pricing(self):
        """Test invoice creation handles missing pricing gracefully."""
        # Create course without pricing
        course_no_pricing = Course.objects.create(
            code="CS999",
            title="No Pricing Course",
            credits=3,
            division=self.division,
            description="Course without pricing",
        )

        class_header_no_pricing = ClassHeader.objects.create(
            course=course_no_pricing,
            term=self.term,
            section_id="A",
            max_enrollment=20,
        )

        # Enrollment should not crash, but no invoice should be created
        ClassHeaderEnrollment.objects.create(
            student=self.student,
            class_header=class_header_no_pricing,
            enrollment_date=timezone.now(),
            status="ENROLLED",
            enrolled_by=self.user,
        )

        # Should handle gracefully - no invoice created
        self.assertEqual(Invoice.objects.count(), 0)

    def test_payment_validation_errors(self):
        """Test payment validation and error handling."""
        invoice = InvoiceService.create_invoice(
            student=self.student,
            term=self.term,
            enrollments=[],
            created_by=self.user,
        )

        # Add line item
        InvoiceLineItem.objects.create(
            invoice=invoice,
            line_item_type="COURSE",
            description="Test Course",
            unit_price=Decimal("100.00"),
            quantity=Decimal("1.00"),
            line_total=Decimal("100.00"),
        )
        invoice.subtotal = Decimal("100.00")
        invoice.total_amount = Decimal("100.00")
        invoice.save()

        # Test negative payment amount
        with self.assertRaises(FinancialError):
            PaymentService.record_payment(
                invoice=invoice,
                amount=Decimal("-50.00"),
                payment_method="CASH",
                payment_date=get_current_date(),
                processed_by=self.user,
            )

        # Test overpayment
        with self.assertRaises(FinancialError):
            PaymentService.record_payment(
                invoice=invoice,
                amount=Decimal("150.00"),  # More than invoice total
                payment_method="CASH",
                payment_date=get_current_date(),
                processed_by=self.user,
            )

        # Test zero payment
        with self.assertRaises(FinancialError):
            PaymentService.record_payment(
                invoice=invoice,
                amount=Decimal("0.00"),
                payment_method="CASH",
                payment_date=get_current_date(),
                processed_by=self.user,
            )
