"""Unit tests for Finance app models.

This module tests the critical business logic of financial models including:
- Invoice calculations and status management
- Payment processing and validation
- Decimal precision for money operations
- Financial transaction audit trail
- Cashier session cash handling

Focus on testing the "why" - the actual business rules and calculations.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.finance.models import (
    CashierSession,
    Currency,
    FinancialTransaction,
    Invoice,
    InvoiceLineItem,
    Payment,
)

# Get user model for testing
User = get_user_model()


@pytest.fixture
def admin_user():
    """Create admin user for tests."""
    return User.objects.create_user(
        username="admin",
        email="admin@example.com",
        password="testpass123",
    )


@pytest.fixture
def student(db):
    """Create student profile for testing."""
    from apps.people.models import Person, StudentProfile

    person = Person.objects.create(first_name="John", last_name="Doe", email="john.doe@example.com")

    return StudentProfile.objects.create(person=person, student_id="STU001")


@pytest.fixture
def term(db):
    """Create term for testing."""
    from apps.curriculum.models import Term

    return Term.objects.create(
        code="2024-1",
        name="Spring 2024",
        start_date=date(2024, 1, 15),
        end_date=date(2024, 5, 15),
    )


@pytest.fixture
def invoice(db, admin_user, student, term):
    """Create basic invoice for testing."""
    return Invoice.objects.create(
        invoice_number="INV-2024-001",
        student=student,
        term=term,
        due_date=date.today() + timedelta(days=30),
        subtotal=Decimal("1000.00"),
        tax_amount=Decimal("0.00"),
        total_amount=Decimal("1000.00"),
        created_by=admin_user,
        updated_by=admin_user,
    )


@pytest.mark.django_db
class TestInvoice:
    """Test Invoice model business logic."""

    def test_invoice_creation_with_defaults(self, admin_user, student, term):
        """Test invoice creation with default values."""
        invoice = Invoice.objects.create(
            invoice_number="INV-2024-002",
            student=student,
            term=term,
            due_date=date.today() + timedelta(days=30),
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert invoice.status == Invoice.InvoiceStatus.DRAFT
        assert invoice.subtotal == Decimal("0.00")
        assert invoice.tax_amount == Decimal("0.00")
        assert invoice.total_amount == Decimal("0.00")
        assert invoice.paid_amount == Decimal("0.00")
        assert invoice.currency == Currency.USD
        assert invoice.version == 1
        assert invoice.issue_date == date.today()

    @pytest.mark.parametrize(
        "total_amount, paid_amount, expected_amount_due",
        [
            (Decimal("1000.00"), Decimal("0.00"), Decimal("1000.00")),
            (Decimal("1000.00"), Decimal("500.00"), Decimal("500.00")),
            (Decimal("1000.00"), Decimal("1000.00"), Decimal("0.00")),
            (Decimal("1000.00"), Decimal("1200.00"), Decimal("0.00")),  # Overpayment
        ],
    )
    def test_amount_due_calculation(self, invoice, total_amount, paid_amount, expected_amount_due):
        """Test amount due calculation with various scenarios."""
        invoice.total_amount = total_amount
        invoice.paid_amount = paid_amount
        invoice.save()

        assert invoice.amount_due == expected_amount_due

    def test_is_overdue_logic(self, invoice):
        """Test overdue detection logic."""
        # Not overdue - future due date
        invoice.due_date = date.today() + timedelta(days=1)
        invoice.total_amount = Decimal("1000.00")
        invoice.paid_amount = Decimal("0.00")
        invoice.save()
        assert not invoice.is_overdue

        # Not overdue - past due date but fully paid
        invoice.due_date = date.today() - timedelta(days=1)
        invoice.paid_amount = Decimal("1000.00")
        invoice.save()
        assert not invoice.is_overdue

        # Overdue - past due date with outstanding balance
        invoice.paid_amount = Decimal("500.00")
        invoice.save()
        assert invoice.is_overdue

    def test_calculate_totals_from_line_items(self, invoice, admin_user):
        """Test total calculation from line items."""
        # Add line items
        InvoiceLineItem.objects.create(
            invoice=invoice,
            line_item_type=InvoiceLineItem.LineItemType.COURSE,
            description="Course Enrollment",
            unit_price=Decimal("500.00"),
            quantity=Decimal("1.00"),
            line_total=Decimal("500.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

        InvoiceLineItem.objects.create(
            invoice=invoice,
            line_item_type=InvoiceLineItem.LineItemType.FEE,
            description="Registration Fee",
            unit_price=Decimal("100.00"),
            quantity=Decimal("2.00"),
            line_total=Decimal("200.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Recalculate totals
        invoice.calculate_totals()

        assert invoice.subtotal == Decimal("700.00")
        assert invoice.total_amount == Decimal("700.00")  # No tax in this test

    def test_legacy_data_preservation_fields(self, admin_user, student, term):
        """Test legacy data preservation fields."""
        invoice = Invoice.objects.create(
            invoice_number="INV-LEGACY-001",
            student=student,
            term=term,
            due_date=date.today() + timedelta(days=30),
            is_historical=True,
            legacy_ipk=12345,
            legacy_receipt_number="RCP-001",
            legacy_receipt_id="CLERK123-RCP-001",
            legacy_notes="Original notes from legacy system",
            legacy_processing_clerk="John Smith",
            original_amount=Decimal("1200.00"),
            discount_applied=Decimal("200.00"),
            reconstruction_status="COMPLETED",
            needs_reprocessing=False,
            total_amount=Decimal("1000.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert invoice.is_historical is True
        assert invoice.legacy_ipk == 12345
        assert invoice.original_amount == Decimal("1200.00")
        assert invoice.discount_applied == Decimal("200.00")
        assert invoice.reconstruction_status == "COMPLETED"

    def test_unique_invoice_number_constraint(self, admin_user, student, term):
        """Test unique constraint on invoice number."""
        # Create first invoice
        Invoice.objects.create(
            invoice_number="INV-DUPLICATE",
            student=student,
            term=term,
            due_date=date.today() + timedelta(days=30),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Try to create duplicate
        with pytest.raises(Exception):  # IntegrityError wrapped by Django
            Invoice.objects.create(
                invoice_number="INV-DUPLICATE",
                student=student,
                term=term,
                due_date=date.today() + timedelta(days=30),
                created_by=admin_user,
                updated_by=admin_user,
            )

    def test_decimal_precision_money_operations(self, invoice):
        """Test decimal precision for money calculations."""
        # Test precise decimal calculations
        invoice.subtotal = Decimal("999.99")
        invoice.tax_amount = Decimal("0.01")
        invoice.save()

        # Manual calculation should be precise
        calculated_total = invoice.subtotal + invoice.tax_amount
        assert calculated_total == Decimal("1000.00")

        # Test rounding edge cases
        invoice.subtotal = Decimal("333.333")  # More than 2 decimal places
        with pytest.raises(Exception):  # Should fail validation
            invoice.full_clean()


@pytest.mark.django_db
class TestInvoiceLineItem:
    """Test InvoiceLineItem model business logic."""

    def test_line_total_auto_calculation(self, invoice, admin_user):
        """Test automatic line total calculation on save."""
        line_item = InvoiceLineItem(
            invoice=invoice,
            line_item_type=InvoiceLineItem.LineItemType.COURSE,
            description="Course Fee",
            unit_price=Decimal("150.50"),
            quantity=Decimal("3.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Line total should be calculated on save
        line_item.save()
        assert line_item.line_total == Decimal("451.50")

    @pytest.mark.parametrize(
        "unit_price, quantity, expected_total",
        [
            (Decimal("100.00"), Decimal("1.00"), Decimal("100.00")),
            (Decimal("99.99"), Decimal("2.00"), Decimal("199.98")),
            (Decimal("33.33"), Decimal("3.00"), Decimal("99.99")),
            (Decimal("0.01"), Decimal("1000.00"), Decimal("10.00")),
        ],
    )
    def test_line_total_calculation_precision(self, invoice, admin_user, unit_price, quantity, expected_total):
        """Test line total calculation with various decimal scenarios."""
        line_item = InvoiceLineItem.objects.create(
            invoice=invoice,
            line_item_type=InvoiceLineItem.LineItemType.FEE,
            description="Test Fee",
            unit_price=unit_price,
            quantity=quantity,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert line_item.line_total == expected_total

    def test_line_item_types_coverage(self, invoice, admin_user):
        """Test all line item types can be created."""
        line_item_types = [
            InvoiceLineItem.LineItemType.COURSE,
            InvoiceLineItem.LineItemType.FEE,
            InvoiceLineItem.LineItemType.ADJUSTMENT,
            InvoiceLineItem.LineItemType.REFUND,
            InvoiceLineItem.LineItemType.ADMIN_FEE,
            InvoiceLineItem.LineItemType.DOC_EXCESS,
        ]

        for item_type in line_item_types:
            line_item = InvoiceLineItem.objects.create(
                invoice=invoice,
                line_item_type=item_type,
                description=f"Test {item_type}",
                unit_price=Decimal("100.00"),
                quantity=Decimal("1.00"),
                created_by=admin_user,
                updated_by=admin_user,
            )
            assert line_item.line_item_type == item_type

    def test_minimum_value_validators(self, invoice, admin_user):
        """Test minimum value validators for price and quantity."""
        # Test negative unit price
        with pytest.raises(ValidationError):
            line_item = InvoiceLineItem(
                invoice=invoice,
                line_item_type=InvoiceLineItem.LineItemType.COURSE,
                description="Negative Price",
                unit_price=Decimal("-100.00"),
                quantity=Decimal("1.00"),
                created_by=admin_user,
                updated_by=admin_user,
            )
            line_item.full_clean()

        # Test zero quantity
        with pytest.raises(ValidationError):
            line_item = InvoiceLineItem(
                invoice=invoice,
                line_item_type=InvoiceLineItem.LineItemType.COURSE,
                description="Zero Quantity",
                unit_price=Decimal("100.00"),
                quantity=Decimal("0.00"),
                created_by=admin_user,
                updated_by=admin_user,
            )
            line_item.full_clean()

    def test_legacy_fields_for_reconstruction(self, invoice, admin_user):
        """Test legacy data fields for A/R reconstruction."""
        line_item = InvoiceLineItem.objects.create(
            invoice=invoice,
            line_item_type=InvoiceLineItem.LineItemType.COURSE,
            description="Legacy Course",
            unit_price=Decimal("500.00"),
            quantity=Decimal("1.00"),
            legacy_program_code="BUSADMIN",
            legacy_course_level="300",
            pricing_method_used="DEFAULT_PRICING",
            pricing_confidence="HIGH",
            base_amount=Decimal("600.00"),
            discount_amount=Decimal("100.00"),
            discount_reason="Early bird discount applied",
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert line_item.legacy_program_code == "BUSADMIN"
        assert line_item.base_amount == Decimal("600.00")
        assert line_item.discount_amount == Decimal("100.00")
        assert line_item.pricing_confidence == "HIGH"


@pytest.mark.django_db
class TestPayment:
    """Test Payment model business logic."""

    def test_payment_creation_with_required_fields(self, invoice, admin_user):
        """Test payment creation with all required fields."""
        payment = Payment.objects.create(
            payment_reference="PAY-2024-001",
            invoice=invoice,
            amount=Decimal("500.00"),
            payment_method=Payment.PaymentMethod.CASH,
            payment_date=timezone.now(),
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert payment.status == Payment.PaymentStatus.PENDING
        assert payment.currency == Currency.USD
        assert payment.amount == Decimal("500.00")

    @pytest.mark.parametrize(
        "payment_method",
        [
            Payment.PaymentMethod.CASH,
            Payment.PaymentMethod.CREDIT_CARD,
            Payment.PaymentMethod.BANK_TRANSFER,
            Payment.PaymentMethod.CHECK,
            Payment.PaymentMethod.ONLINE,
            Payment.PaymentMethod.SCHOLARSHIP,
            Payment.PaymentMethod.OTHER,
        ],
    )
    def test_payment_methods_coverage(self, invoice, admin_user, payment_method):
        """Test all payment methods can be used."""
        payment = Payment.objects.create(
            payment_reference=f"PAY-{payment_method}-001",
            invoice=invoice,
            amount=Decimal("100.00"),
            payment_method=payment_method,
            payment_date=timezone.now(),
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert payment.payment_method == payment_method

    def test_negative_payment_for_refunds(self, invoice, admin_user):
        """Test negative payments for refunds."""
        refund = Payment.objects.create(
            payment_reference="REF-2024-001",
            invoice=invoice,
            amount=Decimal("-200.00"),  # Negative for refund
            payment_method=Payment.PaymentMethod.CASH,
            status=Payment.PaymentStatus.COMPLETED,
            payment_date=timezone.now(),
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert refund.amount == Decimal("-200.00")
        assert "REF-2024-001 - -200.00 USD" in str(refund)

    def test_unique_payment_reference_constraint(self, invoice, admin_user):
        """Test unique constraint on payment reference."""
        # Create first payment
        Payment.objects.create(
            payment_reference="PAY-UNIQUE-001",
            invoice=invoice,
            amount=Decimal("100.00"),
            payment_method=Payment.PaymentMethod.CASH,
            payment_date=timezone.now(),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Try to create duplicate
        with pytest.raises(Exception):  # IntegrityError
            Payment.objects.create(
                payment_reference="PAY-UNIQUE-001",
                invoice=invoice,
                amount=Decimal("100.00"),
                payment_method=Payment.PaymentMethod.CASH,
                payment_date=timezone.now(),
                created_by=admin_user,
                updated_by=admin_user,
            )

    def test_payment_processing_workflow(self, invoice, admin_user):
        """Test payment processing workflow."""
        payment = Payment.objects.create(
            payment_reference="PAY-WORKFLOW-001",
            invoice=invoice,
            amount=Decimal("500.00"),
            payment_method=Payment.PaymentMethod.CREDIT_CARD,
            payment_date=timezone.now(),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Initially pending
        assert payment.status == Payment.PaymentStatus.PENDING
        assert payment.processed_by is None
        assert payment.processed_date is None

        # Process payment
        payment.status = Payment.PaymentStatus.COMPLETED
        payment.processed_by = admin_user
        payment.processed_date = timezone.now()
        payment.save()

        assert payment.status == Payment.PaymentStatus.COMPLETED
        assert payment.processed_by == admin_user
        assert payment.processed_date is not None

    def test_payment_legacy_fields(self, invoice, admin_user):
        """Test legacy data preservation fields."""
        payment = Payment.objects.create(
            payment_reference="PAY-LEGACY-001",
            invoice=invoice,
            amount=Decimal("300.00"),
            payment_method=Payment.PaymentMethod.CASH,
            payment_date=timezone.now(),
            is_historical_payment=True,
            legacy_ipk=67890,
            legacy_receipt_reference="LEGACY-001",
            legacy_processing_clerk="Jane Smith",
            legacy_business_notes="Payment from old system",
            legacy_receipt_full_id="CLERK456-LEGACY-001",
            legacy_program_code="TESOL",
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert payment.is_historical_payment is True
        assert payment.legacy_ipk == 67890
        assert payment.legacy_processing_clerk == "Jane Smith"


@pytest.mark.django_db
class TestFinancialTransaction:
    """Test FinancialTransaction model audit trail logic."""

    def test_transaction_creation_for_invoice(self, student, admin_user):
        """Test financial transaction creation for invoice events."""
        transaction_obj = FinancialTransaction.objects.create(
            transaction_id="TXN-INV-001",
            transaction_type=FinancialTransaction.TransactionType.INVOICE_CREATED,
            student=student,
            amount=Decimal("1000.00"),
            description="Invoice created for Spring 2024",
            processed_by=admin_user,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert transaction_obj.transaction_type == FinancialTransaction.TransactionType.INVOICE_CREATED
        assert transaction_obj.amount == Decimal("1000.00")
        assert transaction_obj.currency == Currency.USD
        assert transaction_obj.processed_by == admin_user

    @pytest.mark.parametrize(
        "transaction_type, amount_sign",
        [
            (FinancialTransaction.TransactionType.INVOICE_CREATED, 1),  # Positive
            (FinancialTransaction.TransactionType.PAYMENT_RECEIVED, -1),  # Negative (credit)
            (FinancialTransaction.TransactionType.PAYMENT_REFUNDED, 1),  # Positive (debit)
            (FinancialTransaction.TransactionType.ADJUSTMENT, 0),  # Can be either
            (FinancialTransaction.TransactionType.WRITEOFF, -1),  # Negative (credit)
        ],
    )
    def test_transaction_types_and_amounts(self, student, admin_user, transaction_type, amount_sign):
        """Test different transaction types with appropriate amount signs."""
        base_amount = Decimal("500.00")
        if amount_sign == -1:
            amount = -base_amount
        elif amount_sign == 1:
            amount = base_amount
        else:
            amount = base_amount  # For adjustments, can be either

        transaction_obj = FinancialTransaction.objects.create(
            transaction_id=f"TXN-{transaction_type}-001",
            transaction_type=transaction_type,
            student=student,
            amount=amount,
            description=f"Test {transaction_type}",
            processed_by=admin_user,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert transaction_obj.transaction_type == transaction_type
        assert transaction_obj.amount == amount

    def test_transaction_with_reference_data(self, student, admin_user):
        """Test transaction with JSON reference data."""
        reference_data = {
            "invoice_id": 123,
            "payment_method": "CREDIT_CARD",
            "external_ref": "CC-TXN-456789",
            "metadata": {"processor": "Stripe", "fee": "2.9%"},
        }

        transaction_obj = FinancialTransaction.objects.create(
            transaction_id="TXN-REF-001",
            transaction_type=FinancialTransaction.TransactionType.PAYMENT_RECEIVED,
            student=student,
            amount=Decimal("-500.00"),
            description="Credit card payment",
            processed_by=admin_user,
            reference_data=reference_data,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert transaction_obj.reference_data == reference_data
        assert transaction_obj.reference_data["metadata"]["processor"] == "Stripe"

    def test_transaction_audit_trail_integrity(self, student, admin_user, invoice):
        """Test transaction audit trail maintains referential integrity."""
        # Create transaction linked to invoice
        transaction_obj = FinancialTransaction.objects.create(
            transaction_id="TXN-AUDIT-001",
            transaction_type=FinancialTransaction.TransactionType.INVOICE_CREATED,
            student=student,
            amount=Decimal("1000.00"),
            description="Invoice audit test",
            invoice=invoice,
            processed_by=admin_user,
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert transaction_obj.invoice == invoice
        assert transaction_obj.student == invoice.student

        # Verify transaction is accessible from invoice
        assert transaction_obj in invoice.transactions.all()


@pytest.mark.django_db
class TestCashierSession:
    """Test CashierSession model cash handling logic."""

    def test_cashier_session_creation(self, admin_user):
        """Test cashier session creation with defaults."""
        session = CashierSession.objects.create(
            session_number="CASH-2024-001",
            cashier=admin_user,
            opening_balance=Decimal("100.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

        assert session.is_active is True
        assert session.closed_at is None
        assert session.closing_balance is None
        assert session.expected_balance is None
        assert session.opened_at is not None

    def test_cash_payments_calculation(self, admin_user, invoice):
        """Test cash payments total calculation for session."""
        session = CashierSession.objects.create(
            session_number="CASH-2024-002",
            cashier=admin_user,
            opening_balance=Decimal("100.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

        session_start = session.opened_at

        # Create cash payments within session timeframe
        Payment.objects.create(
            payment_reference="CASH-PAY-001",
            invoice=invoice,
            amount=Decimal("200.00"),
            payment_method=Payment.PaymentMethod.CASH,
            status=Payment.PaymentStatus.COMPLETED,
            payment_date=session_start + timedelta(minutes=30),
            created_by=admin_user,
            updated_by=admin_user,
        )

        Payment.objects.create(
            payment_reference="CASH-PAY-002",
            invoice=invoice,
            amount=Decimal("150.00"),
            payment_method=Payment.PaymentMethod.CASH,
            status=Payment.PaymentStatus.COMPLETED,
            payment_date=session_start + timedelta(minutes=60),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Create non-cash payment (should not be included)
        Payment.objects.create(
            payment_reference="CC-PAY-001",
            invoice=invoice,
            amount=Decimal("300.00"),
            payment_method=Payment.PaymentMethod.CREDIT_CARD,
            status=Payment.PaymentStatus.COMPLETED,
            payment_date=session_start + timedelta(minutes=45),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Calculate cash payments total
        cash_total = session.cash_payments_total
        assert cash_total == Decimal("350.00")  # Only cash payments

    def test_session_close_workflow(self, admin_user):
        """Test complete session close workflow."""
        session = CashierSession.objects.create(
            session_number="CASH-2024-003",
            cashier=admin_user,
            opening_balance=Decimal("100.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Initially active
        assert session.is_active is True
        assert session.variance == Decimal("0.00")  # No closing balance yet

        # Close session
        closing_balance = Decimal("450.00")
        session.close_session(closing_balance, admin_user)

        # Verify session is closed
        assert session.is_active is False
        assert session.closed_at is not None
        assert session.closing_balance == closing_balance
        assert session.expected_balance == Decimal("100.00")  # opening + 0 cash payments
        assert session.variance == Decimal("350.00")  # Over by 350

    def test_session_variance_calculation_scenarios(self, admin_user, invoice):
        """Test variance calculation in different scenarios."""
        session = CashierSession.objects.create(
            session_number="CASH-VARIANCE-001",
            cashier=admin_user,
            opening_balance=Decimal("200.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Add cash payment
        Payment.objects.create(
            payment_reference="VAR-CASH-001",
            invoice=invoice,
            amount=Decimal("300.00"),
            payment_method=Payment.PaymentMethod.CASH,
            status=Payment.PaymentStatus.COMPLETED,
            payment_date=session.opened_at + timedelta(minutes=15),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Test exact match (no variance)
        session.close_session(Decimal("500.00"), admin_user)  # 200 + 300 = 500
        assert session.variance == Decimal("0.00")

        # Test shortage
        session.closing_balance = Decimal("480.00")
        session.save()
        assert session.variance == Decimal("-20.00")

        # Test overage
        session.closing_balance = Decimal("520.00")
        session.save()
        assert session.variance == Decimal("20.00")

    def test_unique_session_number_constraint(self, admin_user):
        """Test unique constraint on session number."""
        # Create first session
        CashierSession.objects.create(
            session_number="UNIQUE-SESSION-001",
            cashier=admin_user,
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Try to create duplicate
        with pytest.raises(Exception):  # IntegrityError
            CashierSession.objects.create(
                session_number="UNIQUE-SESSION-001",
                cashier=admin_user,
                created_by=admin_user,
                updated_by=admin_user,
            )

    def test_inactive_session_cash_calculation(self, admin_user):
        """Test cash payments calculation for inactive sessions without closed_at."""
        session = CashierSession.objects.create(
            session_number="INACTIVE-SESSION-001",
            cashier=admin_user,
            is_active=False,  # Inactive but no closed_at
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Should return 0 for inactive sessions without closed_at
        assert session.cash_payments_total == Decimal("0.00")


# Edge case and integration tests
@pytest.mark.django_db
class TestFinanceModelIntegration:
    """Test integration between finance models."""

    def test_invoice_payment_financial_transaction_flow(self, admin_user, student, term):
        """Test complete flow from invoice creation to payment to transaction logging."""
        # Create invoice
        invoice = Invoice.objects.create(
            invoice_number="INT-2024-001",
            student=student,
            term=term,
            due_date=date.today() + timedelta(days=30),
            total_amount=Decimal("1000.00"),
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Log invoice creation
        FinancialTransaction.objects.create(
            transaction_id="TXN-INT-CREATE-001",
            transaction_type=FinancialTransaction.TransactionType.INVOICE_CREATED,
            student=student,
            amount=Decimal("1000.00"),
            description="Invoice created for integration test",
            invoice=invoice,
            processed_by=admin_user,
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Create partial payment
        payment = Payment.objects.create(
            payment_reference="PAY-INT-001",
            invoice=invoice,
            amount=Decimal("600.00"),
            payment_method=Payment.PaymentMethod.CASH,
            status=Payment.PaymentStatus.COMPLETED,
            payment_date=timezone.now(),
            processed_by=admin_user,
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Update invoice paid amount
        invoice.paid_amount = Decimal("600.00")
        invoice.status = Invoice.InvoiceStatus.PARTIALLY_PAID
        invoice.save()

        # Log payment transaction
        FinancialTransaction.objects.create(
            transaction_id="TXN-INT-PAY-001",
            transaction_type=FinancialTransaction.TransactionType.PAYMENT_RECEIVED,
            student=student,
            amount=Decimal("-600.00"),  # Credit to student account
            description="Partial payment received",
            invoice=invoice,
            payment=payment,
            processed_by=admin_user,
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Verify relationships and calculations
        assert invoice.amount_due == Decimal("400.00")
        assert invoice.status == Invoice.InvoiceStatus.PARTIALLY_PAID
        assert payment.invoice == invoice

        # Verify audit trail
        invoice_transactions = invoice.transactions.all()
        assert invoice_transactions.count() == 2

        transaction_types = [t.transaction_type for t in invoice_transactions]
        assert FinancialTransaction.TransactionType.INVOICE_CREATED in transaction_types
        assert FinancialTransaction.TransactionType.PAYMENT_RECEIVED in transaction_types

    def test_decimal_precision_across_models(self, admin_user, student, term):
        """Test decimal precision consistency across all finance models."""
        # Test high precision calculations
        invoice = Invoice.objects.create(
            invoice_number="PREC-2024-001",
            student=student,
            term=term,
            due_date=date.today() + timedelta(days=30),
            subtotal=Decimal("999.999"),  # Should be truncated/rounded
            created_by=admin_user,
            updated_by=admin_user,
        )

        # Django should handle decimal precision validation
        with pytest.raises(Exception):  # ValidationError or similar
            invoice.full_clean()

    def test_concurrent_payment_processing(self, admin_user, invoice):
        """Test concurrent payment processing scenarios."""
        with transaction.atomic():
            # Simulate concurrent payment processing
            Payment.objects.create(
                payment_reference="CONC-PAY-001",
                invoice=invoice,
                amount=Decimal("500.00"),
                payment_method=Payment.PaymentMethod.CASH,
                payment_date=timezone.now(),
                created_by=admin_user,
                updated_by=admin_user,
            )

            Payment.objects.create(
                payment_reference="CONC-PAY-002",
                invoice=invoice,
                amount=Decimal("600.00"),
                payment_method=Payment.PaymentMethod.CREDIT_CARD,
                payment_date=timezone.now(),
                created_by=admin_user,
                updated_by=admin_user,
            )

            # Both payments should be created successfully
            assert Payment.objects.filter(invoice=invoice).count() == 2

            # Total payment amount
            total_payments = sum(p.amount for p in invoice.payments.all())
            assert total_payments == Decimal("1100.00")
