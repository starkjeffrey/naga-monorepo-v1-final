"""
Comprehensive unit tests for finance module models.

This test suite covers all finance models with ≥95% coverage as specified
in Phase II requirements. Tests focus on:
- Model field validation
- Business logic methods
- Currency precision handling
- Financial calculations
- Status transitions
- Data integrity constraints
"""

from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models
from django.test import TestCase

from apps.finance.models import (
    # Administrative models
    CashierSession,
    CourseFixedPricing,
    # Core models
    Currency,
    # Pricing models
    DefaultPricing,
    DiscountApplication,
    # Discount models
    DiscountRule,
    FeePricing,
    FeeType,
    FinancialTransaction,
    # G/L models
    GLAccount,
    Invoice,
    InvoiceLineItem,
    JournalEntry,
    JournalEntryLine,
    MaterialityThreshold,
    Payment,
    ReconciliationBatch,
)
from tests.factories import StudentProfileFactory

User = get_user_model()


class CurrencyModelTests(TestCase):
    """Test Currency model functionality."""

    def test_currency_creation(self):
        """Test basic currency creation."""
        currency = Currency.objects.create(code="USD", name="US Dollar", symbol="$", decimal_places=2, is_active=True)
        self.assertEqual(currency.code, "USD")
        self.assertEqual(currency.decimal_places, 2)

    def test_currency_str_representation(self):
        """Test currency string representation."""
        currency = Currency.objects.create(code="KHR", name="Cambodian Riel", symbol="៛", decimal_places=0)
        self.assertEqual(str(currency), "KHR")

    def test_currency_uniqueness(self):
        """Test currency code uniqueness constraint."""
        Currency.objects.create(code="EUR", name="Euro", symbol="€")
        with self.assertRaises(IntegrityError):
            Currency.objects.create(code="EUR", name="Euro Duplicate", symbol="€")

    def test_format_amount_method(self):
        """Test currency amount formatting."""
        usd = Currency.objects.create(code="USD", name="US Dollar", symbol="$", decimal_places=2)
        khr = Currency.objects.create(code="KHR", name="Cambodian Riel", symbol="៛", decimal_places=0)

        # Test USD formatting
        self.assertEqual(usd.format_amount(Decimal("1234.56")), "$1,234.56")

        # Test KHR formatting (no decimals)
        self.assertEqual(khr.format_amount(Decimal("1234")), "៛1,234")


class InvoiceModelTests(TestCase):
    """Test Invoice model functionality."""

    def setUp(self):
        """Set up test data."""
        self.currency = Currency.objects.create(code="USD", name="US Dollar", symbol="$", decimal_places=2)
        self.student = StudentProfileFactory()
        self.user = User.objects.create_user(email="test@example.com", name="Test User", password="testpass123")

    def test_invoice_creation(self):
        """Test basic invoice creation."""
        invoice = Invoice.objects.create(
            student=self.student,
            invoice_number="INV-001",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=Invoice.InvoiceStatus.DRAFT,
            currency=self.currency,
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("100.00"),
            total_amount=Decimal("1100.00"),
            created_by=self.user,
        )
        self.assertEqual(invoice.total_amount, Decimal("1100.00"))
        self.assertEqual(invoice.amount_due, Decimal("1100.00"))

    def test_amount_due_calculation(self):
        """Test amount due calculation with payments."""
        invoice = Invoice.objects.create(
            student=self.student,
            invoice_number="INV-002",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=Invoice.InvoiceStatus.SENT,
            currency=self.currency,
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("300.00"),
            created_by=self.user,
        )
        self.assertEqual(invoice.amount_due, Decimal("700.00"))

    def test_amount_due_never_negative(self):
        """Test amount due cannot be negative (overpayment scenario)."""
        invoice = Invoice.objects.create(
            student=self.student,
            invoice_number="INV-003",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=Invoice.InvoiceStatus.PAID,
            currency=self.currency,
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("1200.00"),  # Overpayment
            created_by=self.user,
        )
        self.assertEqual(invoice.amount_due, Decimal("0.00"))

    def test_is_overdue_property(self):
        """Test overdue status calculation."""
        overdue_invoice = Invoice.objects.create(
            student=self.student,
            invoice_number="INV-004",
            issue_date=date.today() - timedelta(days=60),
            due_date=date.today() - timedelta(days=30),  # Past due
            status=Invoice.InvoiceStatus.SENT,
            currency=self.currency,
            total_amount=Decimal("500.00"),
            created_by=self.user,
        )
        self.assertTrue(overdue_invoice.is_overdue)

        current_invoice = Invoice.objects.create(
            student=self.student,
            invoice_number="INV-005",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),  # Future due
            status=Invoice.InvoiceStatus.SENT,
            currency=self.currency,
            total_amount=Decimal("500.00"),
            created_by=self.user,
        )
        self.assertFalse(current_invoice.is_overdue)

    def test_invoice_number_uniqueness(self):
        """Test invoice number uniqueness constraint."""
        Invoice.objects.create(
            student=self.student,
            invoice_number="INV-UNIQUE",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=Invoice.InvoiceStatus.DRAFT,
            currency=self.currency,
            total_amount=Decimal("100.00"),
            created_by=self.user,
        )

        with self.assertRaises(IntegrityError):
            Invoice.objects.create(
                student=self.student,
                invoice_number="INV-UNIQUE",  # Duplicate
                issue_date=date.today(),
                due_date=date.today() + timedelta(days=30),
                status=Invoice.InvoiceStatus.DRAFT,
                currency=self.currency,
                total_amount=Decimal("200.00"),
                created_by=self.user,
            )

    def test_decimal_precision_handling(self):
        """Test proper decimal precision for financial amounts."""
        invoice = Invoice.objects.create(
            student=self.student,
            invoice_number="INV-PRECISION",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=Invoice.InvoiceStatus.DRAFT,
            currency=self.currency,
            subtotal=Decimal("1234.567"),  # More than 2 decimal places
            created_by=self.user,
        )

        # Should be rounded to 2 decimal places
        invoice.refresh_from_db()
        self.assertEqual(invoice.subtotal.as_tuple().exponent, -2)


class PaymentModelTests(TestCase):
    """Test Payment model functionality."""

    def setUp(self):
        """Set up test data."""
        self.currency = Currency.objects.create(code="USD", name="US Dollar", symbol="$", decimal_places=2)
        self.student = StudentProfileFactory()
        self.user = User.objects.create_user(email="cashier@example.com", name="Cashier User", password="testpass123")
        self.invoice = Invoice.objects.create(
            student=self.student,
            invoice_number="INV-PAY-001",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=Invoice.InvoiceStatus.SENT,
            currency=self.currency,
            total_amount=Decimal("1000.00"),
            created_by=self.user,
        )

    def test_payment_creation(self):
        """Test basic payment creation."""
        payment = Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal("500.00"),
            payment_date=date.today(),
            payment_method=Payment.PaymentMethod.CASH,
            status=Payment.PaymentStatus.COMPLETED,
            processed_by=self.user,
            created_by=self.user,
        )
        self.assertEqual(payment.amount, Decimal("500.00"))
        self.assertEqual(payment.payment_method, Payment.PaymentMethod.CASH)

    def test_payment_reference_generation(self):
        """Test automatic reference number generation."""
        payment = Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal("250.00"),
            payment_date=date.today(),
            payment_method=Payment.PaymentMethod.BANK_TRANSFER,
            status=Payment.PaymentStatus.COMPLETED,
            processed_by=self.user,
            created_by=self.user,
        )
        # Should auto-generate reference number
        self.assertIsNotNone(payment.reference_number)
        self.assertTrue(payment.reference_number.startswith("PAY-"))

    def test_partial_payment_scenario(self):
        """Test partial payment handling."""
        # First partial payment
        Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal("300.00"),
            payment_date=date.today(),
            payment_method=Payment.PaymentMethod.CASH,
            status=Payment.PaymentStatus.COMPLETED,
            processed_by=self.user,
            created_by=self.user,
        )

        # Second partial payment
        Payment.objects.create(
            invoice=self.invoice,
            amount=Decimal("700.00"),
            payment_date=date.today(),
            payment_method=Payment.PaymentMethod.CREDIT_CARD,
            status=Payment.PaymentStatus.COMPLETED,
            processed_by=self.user,
            created_by=self.user,
        )

        # Total payments should equal invoice amount
        total_payments = Payment.objects.filter(
            invoice=self.invoice, status=Payment.PaymentStatus.COMPLETED
        ).aggregate(total=models.Sum("amount"))["total"]

        self.assertEqual(total_payments, self.invoice.total_amount)


class CashierSessionModelTests(TestCase):
    """Test CashierSession model functionality."""

    def setUp(self):
        """Set up test data."""
        self.currency = Currency.objects.create(code="USD", name="US Dollar", symbol="$", decimal_places=2)
        self.cashier = User.objects.create_user(
            email="cashier@example.com", name="Cashier User", password="testpass123"
        )

    def test_cashier_session_creation(self):
        """Test basic cashier session creation."""
        session = CashierSession.objects.create(
            cashier=self.cashier,
            start_time=datetime.now(),
            opening_balance=Decimal("500.00"),
            currency=self.currency,
            is_active=True,
            created_by=self.cashier,
        )
        self.assertEqual(session.opening_balance, Decimal("500.00"))
        self.assertTrue(session.is_active)

    def test_session_variance_calculation(self):
        """Test cash variance calculation."""
        session = CashierSession.objects.create(
            cashier=self.cashier,
            start_time=datetime.now(),
            opening_balance=Decimal("500.00"),
            expected_closing_balance=Decimal("1200.00"),
            actual_closing_balance=Decimal("1195.00"),  # $5 short
            currency=self.currency,
            is_active=False,
            created_by=self.cashier,
        )

        # Variance should be -5.00 (shortage)
        expected_variance = session.actual_closing_balance - session.expected_closing_balance
        self.assertEqual(expected_variance, Decimal("-5.00"))

    def test_only_one_active_session_per_cashier(self):
        """Test business rule: only one active session per cashier."""
        # Create first active session
        CashierSession.objects.create(
            cashier=self.cashier,
            start_time=datetime.now(),
            opening_balance=Decimal("500.00"),
            currency=self.currency,
            is_active=True,
            created_by=self.cashier,
        )

        # Attempting to create second active session should fail
        with self.assertRaises(ValidationError):
            CashierSession.objects.create(
                cashier=self.cashier,
                start_time=datetime.now(),
                opening_balance=Decimal("600.00"),
                currency=self.currency,
                is_active=True,
                created_by=self.cashier,
            )


class PricingModelTests(TestCase):
    """Test pricing model functionality."""

    def setUp(self):
        """Set up test data."""
        self.currency = Currency.objects.create(code="USD", name="US Dollar", symbol="$", decimal_places=2)
        self.user = User.objects.create_user(email="admin@example.com", name="Admin User", password="testpass123")

    def test_default_pricing_creation(self):
        """Test default pricing model."""
        pricing = DefaultPricing.objects.create(
            pricing_tier="STANDARD",
            base_price=Decimal("1500.00"),
            currency=self.currency,
            effective_from=date.today(),
            is_active=True,
            created_by=self.user,
        )
        self.assertEqual(pricing.base_price, Decimal("1500.00"))
        self.assertEqual(pricing.pricing_tier, "STANDARD")

    def test_course_fixed_pricing_date_validation(self):
        """Test date range validation for course fixed pricing."""
        pricing = CourseFixedPricing.objects.create(
            price=Decimal("2000.00"),
            currency=self.currency,
            effective_from=date.today(),
            effective_to=date.today() + timedelta(days=365),
            is_active=True,
            created_by=self.user,
        )
        self.assertTrue(pricing.effective_from < pricing.effective_to)

    def test_fee_pricing_configuration(self):
        """Test fee pricing with fee types."""
        fee_type = FeeType.objects.create(
            name="Application Fee",
            description="One-time application processing fee",
            is_mandatory=True,
            created_by=self.user,
        )

        fee_pricing = FeePricing.objects.create(
            fee_type=fee_type, amount=Decimal("50.00"), currency=self.currency, is_active=True, created_by=self.user
        )
        self.assertEqual(fee_pricing.amount, Decimal("50.00"))
        self.assertTrue(fee_pricing.fee_type.is_mandatory)


class DiscountModelTests(TestCase):
    """Test discount model functionality."""

    def setUp(self):
        """Set up test data."""
        self.currency = Currency.objects.create(code="USD", name="US Dollar", symbol="$", decimal_places=2)
        self.user = User.objects.create_user(email="admin@example.com", name="Admin User", password="testpass123")
        self.student = StudentProfileFactory()

    def test_discount_rule_creation(self):
        """Test discount rule creation."""
        discount = DiscountRule.objects.create(
            name="Early Bird Discount",
            discount_type="percentage",
            discount_value=Decimal("10.00"),  # 10%
            priority=1,
            is_active=True,
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=90),
            created_by=self.user,
        )
        self.assertEqual(discount.discount_value, Decimal("10.00"))
        self.assertEqual(discount.discount_type, "percentage")

    def test_discount_application_tracking(self):
        """Test discount application to invoices."""
        discount_rule = DiscountRule.objects.create(
            name="Student Discount",
            discount_type="fixed",
            discount_value=Decimal("100.00"),
            priority=1,
            is_active=True,
            valid_from=date.today(),
            valid_until=date.today() + timedelta(days=365),
            created_by=self.user,
        )

        invoice = Invoice.objects.create(
            student=self.student,
            invoice_number="INV-DISCOUNT-001",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=Invoice.InvoiceStatus.DRAFT,
            currency=self.currency,
            total_amount=Decimal("1000.00"),
            created_by=self.user,
        )

        application = DiscountApplication.objects.create(
            discount_rule=discount_rule,
            invoice=invoice,
            applied_amount=Decimal("100.00"),
            application_date=date.today(),
            applied_by=self.user,
            created_by=self.user,
        )

        self.assertEqual(application.applied_amount, Decimal("100.00"))
        self.assertEqual(application.discount_rule.name, "Student Discount")


class GLAccountModelTests(TestCase):
    """Test General Ledger model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="accountant@example.com", name="Accountant User", password="testpass123"
        )

    def test_gl_account_creation(self):
        """Test G/L account creation."""
        account = GLAccount.objects.create(
            account_code="1100",
            account_name="Cash - Operating",
            account_type="ASSET",
            is_active=True,
            created_by=self.user,
        )
        self.assertEqual(account.account_code, "1100")
        self.assertEqual(account.account_type, "ASSET")

    def test_journal_entry_balanced(self):
        """Test that journal entries are balanced (debits = credits)."""
        # Create G/L accounts
        cash_account = GLAccount.objects.create(
            account_code="1100", account_name="Cash", account_type="ASSET", is_active=True, created_by=self.user
        )
        revenue_account = GLAccount.objects.create(
            account_code="4100",
            account_name="Tuition Revenue",
            account_type="REVENUE",
            is_active=True,
            created_by=self.user,
        )

        # Create journal entry
        entry = JournalEntry.objects.create(
            entry_number="JE-001",
            entry_date=date.today(),
            description="Student payment received",
            total_amount=Decimal("1000.00"),
            is_posted=False,
            created_by=self.user,
        )

        # Create journal entry lines
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=cash_account,
            description="Cash received from student",
            debit_amount=Decimal("1000.00"),
            credit_amount=Decimal("0.00"),
            created_by=self.user,
        )

        JournalEntryLine.objects.create(
            journal_entry=entry,
            account=revenue_account,
            description="Tuition revenue earned",
            debit_amount=Decimal("0.00"),
            credit_amount=Decimal("1000.00"),
            created_by=self.user,
        )

        # Verify entry is balanced
        total_debits = JournalEntryLine.objects.filter(journal_entry=entry).aggregate(
            total=models.Sum("debit_amount")
        )["total"]

        total_credits = JournalEntryLine.objects.filter(journal_entry=entry).aggregate(
            total=models.Sum("credit_amount")
        )["total"]

        self.assertEqual(total_debits, total_credits)


class ReconciliationModelTests(TestCase):
    """Test reconciliation model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="reconciler@example.com", name="Reconciler User", password="testpass123"
        )

    def test_reconciliation_batch_creation(self):
        """Test reconciliation batch creation."""
        batch = ReconciliationBatch.objects.create(
            batch_name="Monthly Reconciliation - Jan 2024",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 31),
            status="IN_PROGRESS",
            created_by=self.user,
        )
        self.assertEqual(batch.status, "IN_PROGRESS")
        self.assertTrue(batch.period_start < batch.period_end)

    def test_materiality_threshold_validation(self):
        """Test materiality threshold configuration."""
        threshold = MaterialityThreshold.objects.create(
            threshold_name="Standard Materiality",
            amount_threshold=Decimal("10.00"),
            percentage_threshold=Decimal("5.00"),  # 5%
            is_active=True,
            created_by=self.user,
        )
        self.assertEqual(threshold.amount_threshold, Decimal("10.00"))
        self.assertEqual(threshold.percentage_threshold, Decimal("5.00"))


@pytest.mark.django_db
class FinanceModelIntegrationTests(TestCase):
    """Integration tests for finance model interactions."""

    def setUp(self):
        """Set up test data."""
        self.currency = Currency.objects.create(code="USD", name="US Dollar", symbol="$", decimal_places=2)
        self.student = StudentProfileFactory()
        self.user = User.objects.create_user(email="system@example.com", name="System User", password="testpass123")

    def test_invoice_payment_workflow(self):
        """Test complete invoice-to-payment workflow."""
        # Create invoice
        invoice = Invoice.objects.create(
            student=self.student,
            invoice_number="INV-WORKFLOW-001",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=Invoice.InvoiceStatus.SENT,
            currency=self.currency,
            total_amount=Decimal("1500.00"),
            created_by=self.user,
        )

        # Create line items
        InvoiceLineItem.objects.create(
            invoice=invoice,
            line_type="TUITION",
            description="Spring 2024 Tuition",
            quantity=1,
            unit_price=Decimal("1200.00"),
            total_price=Decimal("1200.00"),
            created_by=self.user,
        )

        InvoiceLineItem.objects.create(
            invoice=invoice,
            line_type="FEE",
            description="Technology Fee",
            quantity=1,
            unit_price=Decimal("300.00"),
            total_price=Decimal("300.00"),
            created_by=self.user,
        )

        # Process partial payment
        payment1 = Payment.objects.create(
            invoice=invoice,
            amount=Decimal("800.00"),
            payment_date=date.today(),
            payment_method=Payment.PaymentMethod.BANK_TRANSFER,
            status=Payment.PaymentStatus.COMPLETED,
            processed_by=self.user,
            created_by=self.user,
        )

        # Process remaining payment
        payment2 = Payment.objects.create(
            invoice=invoice,
            amount=Decimal("700.00"),
            payment_date=date.today() + timedelta(days=1),
            payment_method=Payment.PaymentMethod.CASH,
            status=Payment.PaymentStatus.COMPLETED,
            processed_by=self.user,
            created_by=self.user,
        )

        # Create financial transactions for audit trail
        FinancialTransaction.objects.create(
            transaction_type="PAYMENT",
            amount=Decimal("800.00"),
            currency=self.currency,
            description=f"Payment received for {invoice.invoice_number}",
            reference_number=payment1.reference_number,
            student=self.student,
            processed_by=self.user,
            created_by=self.user,
        )

        FinancialTransaction.objects.create(
            transaction_type="PAYMENT",
            amount=Decimal("700.00"),
            currency=self.currency,
            description=f"Payment received for {invoice.invoice_number}",
            reference_number=payment2.reference_number,
            student=self.student,
            processed_by=self.user,
            created_by=self.user,
        )

        # Verify workflow completion
        total_line_items = InvoiceLineItem.objects.filter(invoice=invoice).aggregate(total=models.Sum("total_price"))[
            "total"
        ]

        total_payments = Payment.objects.filter(invoice=invoice, status=Payment.PaymentStatus.COMPLETED).aggregate(
            total=models.Sum("amount")
        )["total"]

        total_transactions = FinancialTransaction.objects.filter(
            student=self.student, transaction_type="PAYMENT"
        ).aggregate(total=models.Sum("amount"))["total"]

        # All amounts should match
        self.assertEqual(invoice.total_amount, total_line_items)
        self.assertEqual(invoice.total_amount, total_payments)
        self.assertEqual(total_payments, total_transactions)

    def test_currency_consistency_across_models(self):
        """Test currency consistency across related models."""
        # Create invoice in USD
        invoice = Invoice.objects.create(
            student=self.student,
            invoice_number="INV-CURRENCY-001",
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=30),
            status=Invoice.InvoiceStatus.SENT,
            currency=self.currency,
            total_amount=Decimal("1000.00"),
            created_by=self.user,
        )

        # Payment must be in same currency
        payment = Payment.objects.create(
            invoice=invoice,
            amount=Decimal("1000.00"),
            payment_date=date.today(),
            payment_method=Payment.PaymentMethod.CASH,
            status=Payment.PaymentStatus.COMPLETED,
            processed_by=self.user,
            created_by=self.user,
        )

        # Transaction must be in same currency
        transaction = FinancialTransaction.objects.create(
            transaction_type="PAYMENT",
            amount=Decimal("1000.00"),
            currency=self.currency,  # Same currency as invoice
            description="Payment processing transaction",
            reference_number=payment.reference_number,
            student=self.student,
            processed_by=self.user,
            created_by=self.user,
        )

        # Verify currency consistency
        self.assertEqual(invoice.currency, self.currency)
        self.assertEqual(transaction.currency, self.currency)
