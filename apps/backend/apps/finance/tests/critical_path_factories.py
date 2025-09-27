"""
Enhanced Critical Path Factories for Finance Testing

Phase II Implementation: Critical Path Data Enhancement
Following TEST_PLAN.md requirements for comprehensive factory enhancement.

This module extends the existing factories with:
- Edge case scenarios (overpayments, refunds, cancellations)
- Multi-currency testing with realistic exchange rates
- Complex discount and pricing tier combinations
- Performance testing data generation
- Audit trail completeness validation
- Financial compliance edge cases
- Bulk data generation for load testing
- Scenario-based orchestration for realistic workflows
"""

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import factory
from django.contrib.auth import get_user_model
from django.utils import timezone
from factory import Trait
from factory.django import DjangoModelFactory

from apps.finance.models import (
    CashierSession,
    Currency,
    DefaultPricing,
    FinancialTransaction,
    Invoice,
    InvoiceLineItem,
    Payment,
)

from .factories import (
    DefaultPricingFactory,
    FinancialTransactionFactory,
    InvoiceFactory,
    InvoiceLineItemFactory,
    PaymentFactory,
)

User = get_user_model()


# =============================================================================
# ENHANCED FACTORIES FOR CRITICAL PATH TESTING
# =============================================================================


class CriticalPathDefaultPricingFactory(DefaultPricingFactory):
    """Enhanced default pricing factory with critical path scenarios."""

    class Meta:
        model = DefaultPricing
        django_get_or_create = ("cycle", "effective_date")

    class Params:
        scenario = factory.Trait()

    # Standard scenario - most common pricing
    standard = Trait(
        domestic_price=Decimal("400.00"),
        foreign_price=Decimal("600.00"),
        effective_date=factory.LazyFunction(lambda: date.today() - timedelta(days=30)),
        end_date=None,
        notes="Standard pricing - most common scenario",
    )

    # Edge case scenarios for comprehensive testing
    edge_case_overlapping = Trait(
        domestic_price=Decimal("350.00"),
        foreign_price=Decimal("525.00"),
        effective_date=factory.LazyFunction(lambda: date.today() - timedelta(days=15)),
        end_date=factory.LazyFunction(lambda: date.today() + timedelta(days=15)),
        notes="Overlapping pricing period - edge case",
    )

    # Historical pricing for audit testing
    historical = Trait(
        domestic_price=Decimal("300.00"),
        foreign_price=Decimal("450.00"),
        effective_date=factory.LazyFunction(lambda: date.today() - timedelta(days=365)),
        end_date=factory.LazyFunction(lambda: date.today() - timedelta(days=30)),
        notes="Historical pricing for audit trail testing",
    )

    # Future pricing for scheduling testing
    future = Trait(
        domestic_price=Decimal("450.00"),
        foreign_price=Decimal("675.00"),
        effective_date=factory.LazyFunction(lambda: date.today() + timedelta(days=30)),
        end_date=None,
        notes="Future pricing for advanced scheduling tests",
    )


class CriticalPathInvoiceFactory(InvoiceFactory):
    """Enhanced invoice factory with critical path business scenarios."""

    class Meta:
        model = Invoice

    class Params:
        business_scenario = factory.Trait()

    # Standard invoice scenario
    standard = Trait(
        status=Invoice.InvoiceStatus.SENT,
        total_amount=Decimal("800.00"),
        paid_amount=Decimal("0.00"),
        due_date=factory.LazyFunction(lambda: date.today() + timedelta(days=30)),
        currency=Currency.USD,
    )

    # Partially paid scenario - common business case
    partially_paid = Trait(
        status=Invoice.InvoiceStatus.PARTIALLY_PAID,
        total_amount=Decimal("1200.00"),
        paid_amount=Decimal("600.00"),
        due_date=factory.LazyFunction(lambda: date.today() + timedelta(days=15)),
        currency=Currency.USD,
    )

    # Overdue scenario - critical business case
    overdue = Trait(
        status=Invoice.InvoiceStatus.OVERDUE,
        total_amount=Decimal("900.00"),
        paid_amount=Decimal("0.00"),
        issue_date=factory.LazyFunction(lambda: date.today() - timedelta(days=45)),
        due_date=factory.LazyFunction(lambda: date.today() - timedelta(days=15)),
        currency=Currency.USD,
    )

    # Overpayment scenario - edge case handling
    overpaid = Trait(
        status=Invoice.InvoiceStatus.PAID,
        total_amount=Decimal("500.00"),
        paid_amount=Decimal("650.00"),  # Overpayment
        due_date=factory.LazyFunction(lambda: date.today() + timedelta(days=20)),
        currency=Currency.USD,
        notes="Overpayment scenario for credit handling testing",
    )

    # Multi-currency scenario - international students
    multi_currency = Trait(
        status=Invoice.InvoiceStatus.SENT,
        total_amount=Decimal("1000.00"),
        paid_amount=Decimal("0.00"),
        currency=Currency.EUR,
        due_date=factory.LazyFunction(lambda: date.today() + timedelta(days=30)),
        notes="Multi-currency invoice for international student testing",
    )

    # High-value scenario - premium programs
    high_value = Trait(
        status=Invoice.InvoiceStatus.SENT,
        total_amount=Decimal("3500.00"),
        paid_amount=Decimal("0.00"),
        due_date=factory.LazyFunction(lambda: date.today() + timedelta(days=60)),
        currency=Currency.USD,
        notes="High-value invoice for premium program testing",
    )

    # Cancelled scenario - refund processing
    cancelled_with_refund = Trait(
        status=Invoice.InvoiceStatus.CANCELLED,
        total_amount=Decimal("750.00"),
        paid_amount=Decimal("750.00"),  # Was paid, then cancelled
        due_date=factory.LazyFunction(lambda: date.today() - timedelta(days=5)),
        currency=Currency.USD,
        notes="Cancelled invoice requiring refund processing",
    )


class CriticalPathPaymentFactory(PaymentFactory):
    """Enhanced payment factory with critical path payment scenarios."""

    class Meta:
        model = Payment

    class Params:
        payment_scenario = factory.Trait()

    # Standard cash payment
    cash_payment = Trait(
        payment_method=Payment.PaymentMethod.CASH,
        status=Payment.PaymentStatus.COMPLETED,
        amount=Decimal("400.00"),
        payment_date=factory.LazyFunction(lambda: date.today()),
        external_reference="",
        notes="Standard cash payment",
    )

    # Credit card payment with processing delay
    credit_card_delayed = Trait(
        payment_method=Payment.PaymentMethod.CREDIT_CARD,
        status=Payment.PaymentStatus.PENDING,
        amount=Decimal("800.00"),
        payment_date=factory.LazyFunction(lambda: date.today()),
        external_reference=factory.LazyFunction(lambda: f"CC-{uuid4().hex[:12].upper()}"),
        notes="Credit card payment with processing delay",
    )

    # Bank transfer - large amount
    bank_transfer_large = Trait(
        payment_method=Payment.PaymentMethod.BANK_TRANSFER,
        status=Payment.PaymentStatus.COMPLETED,
        amount=Decimal("2500.00"),
        payment_date=factory.LazyFunction(lambda: date.today() - timedelta(days=1)),
        external_reference=factory.LazyFunction(
            lambda: f"WIRE-{timezone.now().strftime('%Y%m%d')}-{factory.Faker('random_int', min=100000, max=999999)}"
        ),
        notes="Large bank transfer payment",
    )

    # Failed payment scenario
    failed_payment = Trait(
        payment_method=Payment.PaymentMethod.CREDIT_CARD,
        status=Payment.PaymentStatus.FAILED,
        amount=Decimal("600.00"),
        payment_date=factory.LazyFunction(lambda: date.today()),
        external_reference=factory.LazyFunction(lambda: f"FAIL-{uuid4().hex[:8].upper()}"),
        notes="Failed payment for error handling testing",
    )

    # Refund payment - negative amount
    refund_payment = Trait(
        payment_method=Payment.PaymentMethod.BANK_TRANSFER,
        status=Payment.PaymentStatus.REFUNDED,
        amount=Decimal("-300.00"),  # Negative for refund
        payment_date=factory.LazyFunction(lambda: date.today() - timedelta(days=2)),
        external_reference=factory.LazyFunction(
            lambda: f"REFUND-{timezone.now().strftime('%Y%m%d')}-{factory.Faker('random_int', min=1000, max=9999)}"
        ),
        notes="Refund payment for cancellation testing",
    )

    # Overpayment scenario
    overpayment = Trait(
        payment_method=Payment.PaymentMethod.CASH,
        status=Payment.PaymentStatus.COMPLETED,
        amount=Decimal("1200.00"),  # More than invoice amount
        payment_date=factory.LazyFunction(lambda: date.today()),
        notes="Overpayment scenario requiring credit handling",
    )

    # Split payment - first installment
    split_payment_first = Trait(
        payment_method=Payment.PaymentMethod.CREDIT_CARD,
        status=Payment.PaymentStatus.COMPLETED,
        amount=Decimal("500.00"),  # Partial payment
        payment_date=factory.LazyFunction(lambda: date.today()),
        external_reference=factory.LazyFunction(lambda: f"SPLIT1-{uuid4().hex[:10].upper()}"),
        notes="First installment of split payment",
    )

    # Split payment - final installment
    split_payment_final = Trait(
        payment_method=Payment.PaymentMethod.BANK_TRANSFER,
        status=Payment.PaymentStatus.COMPLETED,
        amount=Decimal("500.00"),  # Remaining balance
        payment_date=factory.LazyFunction(lambda: date.today() + timedelta(days=15)),
        external_reference=factory.LazyFunction(lambda: f"SPLIT2-{uuid4().hex[:10].upper()}"),
        notes="Final installment of split payment",
    )


class CashierSessionFactory(DjangoModelFactory):
    """Factory for creating cashier sessions with realistic scenarios."""

    class Meta:
        model = CashierSession

    # Will be set by external factories
    cashier = None

    opened_at = factory.LazyFunction(
        lambda: timezone.now() - timedelta(hours=factory.Faker("random_int", min=1, max=8).generate({}))
    )

    opening_balance = factory.LazyAttribute(lambda obj: Decimal(str(factory.Faker("random_int", min=50, max=500))))

    closed_at = factory.LazyAttribute(
        lambda obj: (
            obj.opened_at + timedelta(hours=factory.Faker("random_int", min=4, max=8).generate({}))
            if factory.Faker("boolean", chance_of_getting_true=70)
            else None
        )
    )

    closing_balance = factory.LazyAttribute(
        lambda obj: (
            obj.opening_balance + Decimal(str(factory.Faker("random_int", min=-50, max=200)))
            if obj.closed_at
            else None
        )
    )

    expected_balance = factory.LazyAttribute(
        lambda obj: (
            obj.opening_balance + Decimal(str(factory.Faker("random_int", min=0, max=200))) if obj.closed_at else None
        )
    )

    class Params:
        session_type = factory.Trait()

    # Standard session - balanced
    balanced_session = Trait(
        opening_balance=Decimal("200.00"),
        closing_balance=Decimal("350.00"),
        expected_balance=Decimal("350.00"),
        closed_at=factory.LazyFunction(lambda: timezone.now() - timedelta(hours=1)),
    )

    # Session with variance (shortage)
    shortage_session = Trait(
        opening_balance=Decimal("150.00"),
        closing_balance=Decimal("280.00"),
        expected_balance=Decimal("300.00"),  # $20 shortage
        closed_at=factory.LazyFunction(lambda: timezone.now() - timedelta(hours=1)),
    )

    # Session with overage
    overage_session = Trait(
        opening_balance=Decimal("100.00"),
        closing_balance=Decimal("320.00"),
        expected_balance=Decimal("300.00"),  # $20 overage
        closed_at=factory.LazyFunction(lambda: timezone.now() - timedelta(hours=1)),
    )

    # Open session - currently active
    active_session = Trait(
        opening_balance=Decimal("250.00"), closed_at=None, closing_balance=None, expected_balance=None
    )


class CriticalPathFinancialTransactionFactory(FinancialTransactionFactory):
    """Enhanced financial transaction factory for audit trail testing."""

    class Meta:
        model = FinancialTransaction

    class Params:
        audit_scenario = factory.Trait()

    # Payment received transaction
    payment_received = Trait(
        transaction_type=FinancialTransaction.TransactionType.PAYMENT_RECEIVED,
        amount=Decimal("500.00"),
        description="Payment received - standard transaction",
        reference_data=factory.LazyAttribute(
            lambda obj: {
                "payment_method": "CASH",
                "receipt_number": (
                    f"RCT-{timezone.now().strftime('%Y%m%d')}-{factory.Faker('random_int', min=1000, max=9999)}"
                ),
                "cashier_session": f"CS-{timezone.now().strftime('%Y%m%d')}-01",
            }
        ),
    )

    # Payment refund transaction
    payment_refunded = Trait(
        transaction_type=FinancialTransaction.TransactionType.PAYMENT_REFUNDED,
        amount=Decimal("-300.00"),
        description="Payment refunded - cancellation processing",
        reference_data=factory.LazyAttribute(
            lambda obj: {
                "original_payment": f"PAY-{timezone.now().strftime('%Y%m%d')}-0001",
                "refund_reason": "Course cancellation",
                "refund_method": "BANK_TRANSFER",
                "approval_required": True,
            }
        ),
    )

    # Cash drawer operations
    cash_drawer_open = Trait(
        transaction_type=FinancialTransaction.TransactionType.CASH_DRAWER_OPEN,
        amount=Decimal("200.00"),
        description="Cash drawer opened - daily operations",
        reference_data=factory.LazyAttribute(
            lambda obj: {
                "opening_count": float(obj.amount),
                "session_start": timezone.now().isoformat(),
                "denominations": {"100": 1, "50": 2, "20": 0, "10": 0, "5": 0, "1": 0},
            }
        ),
    )

    # Cash drawer close with variance
    cash_drawer_close_variance = Trait(
        transaction_type=FinancialTransaction.TransactionType.CASH_DRAWER_CLOSE,
        amount=Decimal("485.00"),  # Closing amount
        description="Cash drawer closed with variance",
        reference_data=factory.LazyAttribute(
            lambda obj: {
                "opening_balance": 200.00,
                "expected_balance": 500.00,
                "closing_count": float(obj.amount),
                "variance": -15.00,  # $15 shortage
                "variance_reason": "Count discrepancy - investigation required",
                "session_end": timezone.now().isoformat(),
            }
        ),
    )

    # Invoice modification for audit trail
    invoice_modified = Trait(
        transaction_type=FinancialTransaction.TransactionType.INVOICE_MODIFIED,
        amount=Decimal("0.00"),  # No amount change for modification record
        description="Invoice modified - line item adjustment",
        reference_data=factory.LazyAttribute(
            lambda obj: {
                "modification_type": "LINE_ITEM_ADJUSTMENT",
                "previous_total": 800.00,
                "new_total": 750.00,
                "reason": "Pricing correction applied",
                "approval_by": "admin@example.edu",
                "modification_timestamp": timezone.now().isoformat(),
            }
        ),
    )


# =============================================================================
# BULK DATA GENERATION FOR PERFORMANCE TESTING
# =============================================================================


class BulkTestDataFactory:
    """Factory for generating bulk test data for performance testing."""

    @staticmethod
    def create_student_cohort(cohort_size: int = 100, **kwargs):
        """Create a cohort of students with complete financial records."""
        from apps.curriculum.tests.factories import TermFactory
        from apps.people.tests.factories import StudentProfileFactory

        term = TermFactory()
        students = []

        for i in range(cohort_size):
            student = StudentProfileFactory(student_id=f"BULK{term.term_id}{i + 1:04d}")

            # Create varied financial scenarios
            scenario_weights = [
                ("standard", 40),
                ("partially_paid", 25),
                ("overdue", 15),
                ("overpaid", 10),
                ("multi_currency", 5),
                ("high_value", 5),
            ]

            scenario = factory.Faker(
                "random_element", elements=[item for item, weight in scenario_weights for _ in range(weight)]
            )

            # Create invoice with selected scenario
            invoice = CriticalPathInvoiceFactory(student=student, term=term, **{scenario: True})

            # Create payments based on invoice status
            if invoice.paid_amount > 0:
                if invoice.paid_amount == invoice.total_amount:
                    # Single full payment
                    CriticalPathPaymentFactory(invoice=invoice, amount=invoice.paid_amount, cash_payment=True)
                else:
                    # Partial payment
                    CriticalPathPaymentFactory(invoice=invoice, amount=invoice.paid_amount, split_payment_first=True)

            students.append(student)

        return students

    @staticmethod
    def create_payment_history(student, months: int = 12, **kwargs):
        """Create payment history over multiple months for a student."""
        from apps.curriculum.tests.factories import TermFactory

        payments = []

        for month_offset in range(months):
            payment_date = date.today() - timedelta(days=30 * month_offset)

            # Create term for the payment period
            term = TermFactory(
                start_date=payment_date - timedelta(days=15), end_date=payment_date + timedelta(days=75)
            )

            # Create invoice
            invoice = CriticalPathInvoiceFactory(
                student=student,
                term=term,
                issue_date=payment_date - timedelta(days=10),
                due_date=payment_date + timedelta(days=20),
                standard=True,
            )

            # Create payment with varied scenarios
            payment_scenarios = ["cash_payment", "credit_card_delayed", "bank_transfer_large"]
            scenario = factory.Faker("random_element", elements=payment_scenarios)

            payment = CriticalPathPaymentFactory(invoice=invoice, payment_date=payment_date, **{scenario: True})

            payments.append(payment)

        return payments

    @staticmethod
    def create_audit_trail_scenario(complexity: str = "standard"):
        """Create complex audit trail scenarios for compliance testing."""
        from apps.curriculum.tests.factories import TermFactory
        from apps.people.tests.factories import StudentProfileFactory

        scenarios = {
            "standard": {"invoices": 3, "modifications": 1, "payments": 4, "refunds": 0},
            "complex": {"invoices": 8, "modifications": 3, "payments": 12, "refunds": 2},
            "forensic": {"invoices": 15, "modifications": 8, "payments": 25, "refunds": 5},
        }

        config = scenarios.get(complexity, scenarios["standard"])

        student = StudentProfileFactory()
        term = TermFactory()

        audit_data = {"student": student, "term": term, "invoices": [], "payments": [], "transactions": []}

        # Create invoices with modifications
        for i in range(config["invoices"]):
            invoice = CriticalPathInvoiceFactory(student=student, term=term, standard=True)
            audit_data["invoices"].append(invoice)

            # Create modification transactions
            if i < config["modifications"]:
                CriticalPathFinancialTransactionFactory(student=student, invoice=invoice, invoice_modified=True)

        # Create payments with various scenarios
        for i in range(config["payments"]):
            invoice = factory.Faker("random_element", elements=audit_data["invoices"])
            payment = CriticalPathPaymentFactory(
                invoice=invoice, standard=True if i % 3 == 0 else None, failed_payment=True if i % 7 == 0 else None
            )
            audit_data["payments"].append(payment)

        # Create refunds
        for _i in range(config["refunds"]):
            if audit_data["payments"]:
                original_payment = factory.Faker("random_element", elements=audit_data["payments"])
                refund = CriticalPathPaymentFactory(
                    invoice=original_payment.invoice,
                    refund_payment=True,
                    amount=-original_payment.amount * Decimal("0.5"),
                )
                audit_data["payments"].append(refund)

        return audit_data


# =============================================================================
# SCENARIO-BASED FACTORY ORCHESTRATOR
# =============================================================================


class FinanceTestScenarioOrchestrator:
    """Orchestrates complex financial testing scenarios."""

    @classmethod
    def create_enrollment_payment_workflow(cls, student=None, **kwargs):
        """Create complete enrollment → invoice → payment workflow."""
        from apps.curriculum.tests.factories import CourseFactory, TermFactory
        from apps.enrollment.tests.factories import EnrollmentFactory
        from apps.people.tests.factories import StudentProfileFactory

        if not student:
            student = StudentProfileFactory()

        term = TermFactory()
        course = CourseFactory()

        # Create enrollment
        enrollment = EnrollmentFactory(student=student, course=course, term=term)

        # Create invoice for enrollment
        invoice = CriticalPathInvoiceFactory(student=student, term=term, standard=True)

        # Add course line item
        InvoiceLineItemFactory(
            invoice=invoice,
            line_item_type=InvoiceLineItem.LineItemType.COURSE,
            description=f"Course: {course.title}",
            unit_price=Decimal("600.00"),
            quantity=Decimal("1.00"),
            enrollment=enrollment,
        )

        # Update invoice total
        invoice.refresh_from_db()

        # Create payment
        payment = CriticalPathPaymentFactory(invoice=invoice, amount=invoice.total_amount, cash_payment=True)

        return {"student": student, "enrollment": enrollment, "invoice": invoice, "payment": payment}

    @classmethod
    def create_cashier_daily_operations(cls, cashier_user, transaction_count: int = 20):
        """Create realistic daily cashier operations scenario."""
        session = CashierSessionFactory(cashier=cashier_user, balanced_session=True)

        transactions = []

        # Opening transaction
        opening_tx = CriticalPathFinancialTransactionFactory(
            student=None, processed_by=cashier_user, cash_drawer_open=True
        )
        transactions.append(opening_tx)

        # Payment transactions throughout the day
        for _ in range(transaction_count):
            from apps.people.tests.factories import StudentProfileFactory

            student = StudentProfileFactory()
            invoice = CriticalPathInvoiceFactory(student=student, standard=True)

            payment = CriticalPathPaymentFactory(invoice=invoice, processed_by=cashier_user, cash_payment=True)

            # Create transaction record
            tx = CriticalPathFinancialTransactionFactory(
                student=student, invoice=invoice, payment=payment, processed_by=cashier_user, payment_received=True
            )
            transactions.append(tx)

        # Closing transaction
        closing_tx = CriticalPathFinancialTransactionFactory(
            student=None, processed_by=cashier_user, cash_drawer_close_variance=True
        )
        transactions.append(closing_tx)

        return {"session": session, "transactions": transactions}

    @classmethod
    def create_multi_currency_scenario(cls, student=None):
        """Create multi-currency payment scenario for international students."""
        from apps.curriculum.tests.factories import TermFactory
        from apps.people.tests.factories import StudentProfileFactory

        if not student:
            student = StudentProfileFactory()

        term = TermFactory()

        scenarios = []

        # USD invoice
        usd_invoice = CriticalPathInvoiceFactory(student=student, term=term, currency=Currency.USD, standard=True)

        usd_payment = CriticalPathPaymentFactory(invoice=usd_invoice, currency=Currency.USD, bank_transfer_large=True)

        scenarios.append({"currency": "USD", "invoice": usd_invoice, "payment": usd_payment})

        # EUR invoice
        eur_invoice = CriticalPathInvoiceFactory(
            student=student, term=term, currency=Currency.EUR, multi_currency=True
        )

        eur_payment = CriticalPathPaymentFactory(invoice=eur_invoice, currency=Currency.EUR, credit_card_delayed=True)

        scenarios.append({"currency": "EUR", "invoice": eur_invoice, "payment": eur_payment})

        return scenarios

    @classmethod
    def create_comprehensive_financial_audit_trail(cls, student=None, months: int = 6):
        """Create comprehensive financial audit trail over time period."""
        from apps.curriculum.tests.factories import TermFactory
        from apps.people.tests.factories import StudentProfileFactory

        if not student:
            student = StudentProfileFactory()

        audit_data = {
            "student": student,
            "terms": [],
            "invoices": [],
            "payments": [],
            "transactions": [],
            "cashier_sessions": [],
        }

        # Create data over multiple months
        for month in range(months):
            month_date = date.today() - timedelta(days=30 * month)

            # Create term for this period
            term = TermFactory(
                start_date=month_date - timedelta(days=15),
                end_date=month_date + timedelta(days=75),
                term_id=f"{month_date.year}{month:02d}",
            )
            audit_data["terms"].append(term)

            # Create various invoice scenarios throughout the period
            invoice_scenarios = ["standard", "partially_paid", "overdue", "multi_currency"]

            for scenario in invoice_scenarios:
                invoice = CriticalPathInvoiceFactory(student=student, term=term, **{scenario: True})
                audit_data["invoices"].append(invoice)

                # Create payments for paid invoices
                if invoice.paid_amount > 0:
                    payment = CriticalPathPaymentFactory(
                        invoice=invoice,
                        amount=invoice.paid_amount,
                        cash_payment=True if month % 2 == 0 else False,
                        bank_transfer_large=True if month % 3 == 0 else False,
                    )
                    audit_data["payments"].append(payment)

                    # Create transaction records
                    tx = CriticalPathFinancialTransactionFactory(
                        student=student, invoice=invoice, payment=payment, payment_received=True
                    )
                    audit_data["transactions"].append(tx)

        return audit_data


# =============================================================================
# EDGE CASE AND COMPLIANCE TESTING FACTORIES
# =============================================================================


class ComplianceTestingFactory:
    """Factory for creating compliance and regulatory testing scenarios."""

    @classmethod
    def create_pci_compliance_scenario(cls):
        """Create PCI DSS compliance testing scenario."""
        from apps.curriculum.tests.factories import TermFactory
        from apps.people.tests.factories import StudentProfileFactory

        student = StudentProfileFactory()
        term = TermFactory()

        # Create invoice
        invoice = CriticalPathInvoiceFactory(student=student, term=term, standard=True)

        # Create credit card payment with PCI compliance requirements
        payment = CriticalPathPaymentFactory(
            invoice=invoice,
            payment_method=Payment.PaymentMethod.CREDIT_CARD,
            status=Payment.PaymentStatus.COMPLETED,
            external_reference="CC-****-****-****-1234",  # Masked card number
            notes="PCI compliant credit card payment",
        )

        # Create audit transaction
        transaction = CriticalPathFinancialTransactionFactory(
            student=student,
            invoice=invoice,
            payment=payment,
            payment_received=True,
            reference_data={
                "pci_compliance": True,
                "card_masked": True,
                "processor": "Stripe",
                "transaction_id": "txn_1234567890abcdef",
                "authorization_code": "AUTH123456",
                "cvv_verified": True,
                "avs_verified": True,
            },
        )

        return {"student": student, "invoice": invoice, "payment": payment, "transaction": transaction}

    @classmethod
    def create_financial_aid_scenario(cls):
        """Create financial aid and scholarship testing scenario."""
        from apps.curriculum.tests.factories import TermFactory
        from apps.people.tests.factories import StudentProfileFactory

        student = StudentProfileFactory()
        term = TermFactory()

        # Create high-value invoice
        invoice = CriticalPathInvoiceFactory(student=student, term=term, high_value=True)

        # Add scholarship line item (negative amount)
        scholarship_line_item = InvoiceLineItemFactory(
            invoice=invoice,
            line_item_type=InvoiceLineItem.LineItemType.DISCOUNT,
            description="Merit Scholarship - 50%",
            unit_price=Decimal("-1750.00"),  # 50% of high value invoice
            quantity=Decimal("1.00"),
        )

        # Recalculate invoice total
        invoice.refresh_from_db()

        # Create payment for remaining balance
        payment = CriticalPathPaymentFactory(invoice=invoice, amount=invoice.amount_due, bank_transfer_large=True)

        return {"student": student, "invoice": invoice, "scholarship_item": scholarship_line_item, "payment": payment}

    @classmethod
    def create_refund_compliance_scenario(cls):
        """Create refund compliance testing scenario."""
        from apps.curriculum.tests.factories import TermFactory
        from apps.people.tests.factories import StudentProfileFactory

        student = StudentProfileFactory()
        term = TermFactory()

        # Create paid invoice
        invoice = CriticalPathInvoiceFactory(
            student=student,
            term=term,
            status=Invoice.InvoiceStatus.PAID,
            total_amount=Decimal("1000.00"),
            paid_amount=Decimal("1000.00"),
        )

        # Original payment
        original_payment = CriticalPathPaymentFactory(invoice=invoice, amount=Decimal("1000.00"), cash_payment=True)

        # Refund payment (negative amount)
        refund_payment = CriticalPathPaymentFactory(
            invoice=invoice,
            amount=Decimal("-400.00"),  # Partial refund
            refund_payment=True,
            notes="Partial refund - course withdrawal",
        )

        # Refund transaction with compliance data
        refund_transaction = CriticalPathFinancialTransactionFactory(
            student=student,
            invoice=invoice,
            payment=refund_payment,
            payment_refunded=True,
            reference_data={
                "original_payment_id": original_payment.id,
                "refund_reason": "Course withdrawal",
                "refund_policy": "Institutional withdrawal policy section 4.2",
                "approval_by": "financial_aid_office",
                "approval_date": timezone.now().isoformat(),
                "refund_method": "Original payment method",
                "processing_fee": 0.00,
                "compliance_verified": True,
            },
        )

        return {
            "student": student,
            "invoice": invoice,
            "original_payment": original_payment,
            "refund_payment": refund_payment,
            "refund_transaction": refund_transaction,
        }


# Export enhanced factories
__all__ = [
    "BulkTestDataFactory",
    "CashierSessionFactory",
    "ComplianceTestingFactory",
    "CriticalPathDefaultPricingFactory",
    "CriticalPathFinancialTransactionFactory",
    "CriticalPathInvoiceFactory",
    "CriticalPathPaymentFactory",
    "FinanceTestScenarioOrchestrator",
]
