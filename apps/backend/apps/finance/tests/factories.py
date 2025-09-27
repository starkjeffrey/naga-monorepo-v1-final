"""Factory-boy factories for finance models.

This module provides factory classes for generating realistic test data
for all finance-related models including:
- Separated pricing models (DefaultPricing, CourseFixedPricing, SeniorProjectPricing, ReadingClassPricing)
- Fee structures and pricing with direct local/foreign amounts
- Student invoices and line items
- Payment records and transactions
- Financial audit trails

Following clean architecture principles with realistic data generation
that supports comprehensive testing of financial workflows using the new
separated pricing architecture.
"""

from datetime import timedelta
from decimal import Decimal

import factory
from django.contrib.auth import get_user_model
from django.utils import timezone
from factory import SubFactory
from factory.django import DjangoModelFactory

from apps.common.utils import get_current_date
from apps.finance.models import (
    CourseFixedPricing,
    DefaultPricing,
    FeePricing,
    FinancialTransaction,
    Invoice,
    InvoiceLineItem,
    Payment,
    ReadingClassPricing,
    SeniorProjectCourse,
    SeniorProjectPricing,
)

User = get_user_model()


class DefaultPricingFactory(DjangoModelFactory):
    """Factory for creating default pricing."""

    class Meta:
        model = DefaultPricing
        django_get_or_create = ("cycle", "effective_date")

    # Will be set by external factories
    cycle = None

    domestic_price = factory.LazyAttribute(
        lambda obj: Decimal(str(factory.factory.Faker("random_int", min=200, max=800))),
    )

    foreign_price = factory.LazyAttribute(
        lambda obj: Decimal(str(factory.factory.Faker("random_int", min=300, max=1200))),
    )

    effective_date = factory.LazyFunction(
        lambda: get_current_date() - timedelta(days=factory.factory.Faker("random_int", min=1, max=365)),
    )

    end_date = factory.LazyAttribute(
        lambda obj: (
            None
            if factory.factory.Faker("boolean", chance_of_getting_true=80)
            else obj.effective_date + timedelta(days=factory.factory.Faker("random_int", min=90, max=730))
        ),
    )

    notes = factory.LazyAttribute(lambda obj: f"Default pricing for {obj.cycle} cycle")


class CourseFixedPricingFactory(DjangoModelFactory):
    """Factory for creating course-specific fixed pricing."""

    class Meta:
        model = CourseFixedPricing
        django_get_or_create = ("course", "effective_date")

    # Will be set by external factories
    course = None

    domestic_price = factory.LazyAttribute(
        lambda obj: Decimal(str(factory.factory.Faker("random_int", min=250, max=900))),
    )

    foreign_price = factory.LazyAttribute(
        lambda obj: Decimal(str(factory.factory.Faker("random_int", min=350, max=1300))),
    )

    effective_date = factory.LazyFunction(
        lambda: get_current_date() - timedelta(days=factory.factory.Faker("random_int", min=1, max=365)),
    )

    end_date = factory.LazyAttribute(
        lambda obj: (
            None
            if factory.factory.Faker("boolean", chance_of_getting_true=85)
            else obj.effective_date + timedelta(days=factory.factory.Faker("random_int", min=90, max=730))
        ),
    )

    notes = factory.LazyAttribute(
        lambda obj: (f"Fixed pricing for course {obj.course.code}" if obj.course else "Course fixed pricing"),
    )


class SeniorProjectPricingFactory(DjangoModelFactory):
    """Factory for creating senior project pricing."""

    class Meta:
        model = SeniorProjectPricing
        django_get_or_create = ("tier", "effective_date")

    tier = factory.Iterator(["1", "2", "3-4", "5+"])

    individual_price = factory.LazyAttribute(
        lambda obj: {
            "1": Decimal("800.00"),
            "2": Decimal("600.00"),
            "3-4": Decimal("400.00"),
            "5+": Decimal("300.00"),
        }.get(obj.tier, Decimal("500.00")),
    )

    foreign_individual_price = factory.LazyAttribute(
        lambda obj: obj.individual_price * Decimal("1.5"),
    )

    advisor_payment = factory.LazyAttribute(
        lambda obj: Decimal(str(factory.factory.Faker("random_int", min=50, max=150))),
    )

    committee_payment = factory.LazyAttribute(
        lambda obj: Decimal(str(factory.factory.Faker("random_int", min=25, max=75))),
    )

    effective_date = factory.LazyFunction(
        lambda: get_current_date() - timedelta(days=factory.factory.Faker("random_int", min=1, max=365)),
    )

    end_date = factory.LazyAttribute(
        lambda obj: (
            None
            if factory.factory.Faker("boolean", chance_of_getting_true=90)
            else obj.effective_date + timedelta(days=factory.factory.Faker("random_int", min=180, max=730))
        ),
    )

    notes = factory.LazyAttribute(lambda obj: f"Senior project pricing for {obj.tier} students")


class SeniorProjectCourseFactory(DjangoModelFactory):
    """Factory for creating senior project course configuration."""

    class Meta:
        model = SeniorProjectCourse
        django_get_or_create = ("course",)

    # Will be set by external factories
    course = None

    project_code = factory.LazyAttribute(
        lambda obj: (
            f"PROJ-{factory.factory.Faker('random_element', elements=['IR', 'FIN', 'BUS', 'THM'])}-"
            f"{factory.factory.Faker('random_int', min=400, max=499)}"
        )
    )

    major_name = factory.LazyAttribute(
        lambda obj: factory.factory.Faker(
            "random_element",
            elements=[
                "International Relations",
                "Finance",
                "Business Administration",
                "Tourism & Hospitality Management",
            ],
        ),
    )

    allows_groups = factory.LazyAttribute(
        lambda obj: obj.major_name != "TESOL" if obj.major_name else True,
    )

    is_active = True


class ReadingClassPricingFactory(DjangoModelFactory):
    """Factory for creating reading class pricing."""

    class Meta:
        model = ReadingClassPricing
        django_get_or_create = ("cycle", "tier", "effective_date")

    # Will be set by external factories
    cycle = None

    tier = factory.Iterator(["1-2", "3-5", "6-15", "16+"])

    price_per_student = factory.LazyAttribute(
        lambda obj: {
            "1-2": Decimal("500.00"),
            "3-5": Decimal("400.00"),
            "6-15": Decimal("300.00"),
            "16+": Decimal("250.00"),
        }.get(obj.tier, Decimal("300.00")),
    )

    minimum_revenue = factory.LazyAttribute(
        lambda obj: (
            obj.price_per_student * Decimal("2") if obj.tier == "1-2" else obj.price_per_student * Decimal("3")
        ),
    )

    effective_date = factory.LazyFunction(
        lambda: get_current_date() - timedelta(days=factory.factory.Faker("random_int", min=1, max=365)),
    )

    end_date = factory.LazyAttribute(
        lambda obj: (
            None
            if factory.factory.Faker("boolean", chance_of_getting_true=85)
            else obj.effective_date + timedelta(days=factory.factory.Faker("random_int", min=180, max=730))
        ),
    )

    notes = factory.LazyAttribute(lambda obj: f"Reading class pricing for {obj.tier} students")


class FeePricingFactory(DjangoModelFactory):
    """Factory for creating fee pricing."""

    class Meta:
        model = FeePricing
        django_get_or_create = ("name", "fee_type", "effective_date")

    fee_type = factory.Iterator(
        [
            "REGISTRATION",
            "APPLICATION",
            "LATE_PAYMENT",
            "MATERIAL",
            "TECHNOLOGY",
            "LIBRARY",
            "STUDENT_SERVICES",
            "GRADUATION",
            "TRANSCRIPT",
            "ID_CARD",
            "PARKING",
            "OTHER",
        ],
    )

    name = factory.LazyAttribute(
        lambda obj: {
            "REGISTRATION": "Registration Fee",
            "APPLICATION": "Application Fee",
            "LATE_PAYMENT": "Late Payment Fee",
            "MATERIAL": factory.factory.Faker(
                "random_element",
                elements=[
                    "Course Materials",
                    "Lab Materials",
                    "Textbook Fee",
                    "Equipment Fee",
                ],
            ),
            "TECHNOLOGY": "Technology Fee",
            "LIBRARY": "Library Fee",
            "STUDENT_SERVICES": "Student Services Fee",
            "GRADUATION": "Graduation Fee",
            "TRANSCRIPT": "Official Transcript Fee",
            "ID_CARD": "Student ID Card Fee",
            "PARKING": "Parking Permit Fee",
            "OTHER": factory.factory.Faker(
                "random_element",
                elements=[
                    "Activity Fee",
                    "Health Services Fee",
                    "Recreation Fee",
                    "Security Fee",
                ],
            ),
        }.get(obj.fee_type, f"{obj.fee_type.title()} Fee"),
    )

    local_amount = factory.LazyAttribute(
        lambda obj: Decimal(
            str(
                {
                    "REGISTRATION": factory.factory.Faker("random_int", min=25, max=100),
                    "APPLICATION": factory.factory.Faker("random_int", min=50, max=150),
                    "LATE_PAYMENT": factory.factory.Faker("random_int", min=15, max=50),
                    "MATERIAL": factory.factory.Faker("random_int", min=30, max=200),
                    "TECHNOLOGY": factory.factory.Faker("random_int", min=20, max=75),
                    "LIBRARY": factory.factory.Faker("random_int", min=10, max=40),
                    "STUDENT_SERVICES": factory.factory.Faker("random_int", min=15, max=60),
                    "GRADUATION": factory.factory.Faker("random_int", min=100, max=300),
                    "TRANSCRIPT": factory.factory.Faker("random_int", min=10, max=25),
                    "ID_CARD": factory.factory.Faker("random_int", min=5, max=20),
                    "PARKING": factory.factory.Faker("random_int", min=50, max=200),
                    "OTHER": factory.factory.Faker("random_int", min=10, max=100),
                }.get(obj.fee_type, 50),
            ),
        ),
    )

    foreign_amount = factory.LazyAttribute(
        lambda obj: obj.local_amount * Decimal("1.5") if obj.local_amount else None,
    )

    currency = factory.Iterator(["USD", "EUR", "KHR"])

    is_per_course = factory.LazyAttribute(
        lambda obj: obj.fee_type in ["MATERIAL", "LATE_PAYMENT"] and factory.factory.Faker("boolean"),
    )

    is_per_term = factory.LazyAttribute(
        lambda obj: not obj.is_per_course
        and obj.fee_type not in ["APPLICATION", "GRADUATION", "TRANSCRIPT", "ID_CARD"],
    )

    is_mandatory = factory.LazyAttribute(
        lambda obj: obj.fee_type in ["REGISTRATION", "TECHNOLOGY", "STUDENT_SERVICES"]
        or factory.factory.Faker("boolean", chance_of_getting_true=70),
    )

    effective_date = factory.LazyFunction(
        lambda: get_current_date() - timedelta(days=factory.factory.Faker("random_int", min=1, max=365)),
    )

    end_date = factory.LazyAttribute(
        lambda obj: (
            None
            if factory.factory.Faker("boolean", chance_of_getting_true=85)
            else obj.effective_date + timedelta(days=factory.factory.Faker("random_int", min=180, max=730))
        ),
    )

    description = factory.LazyAttribute(
        lambda obj: (
            f"{obj.name} charged "
            f"{'per course' if obj.is_per_course else 'per term' if obj.is_per_term else 'one-time'}"
        )
    )


class InvoiceFactory(DjangoModelFactory):
    """Factory for creating invoices."""

    class Meta:
        model = Invoice

    invoice_number = factory.Sequence(lambda n: f"INV-{get_current_date().strftime('%Y%m%d')}-{n + 1:04d}")

    # Will be set by external factories
    student = None
    term = None

    issue_date = factory.LazyFunction(
        lambda: get_current_date() - timedelta(days=factory.factory.Faker("random_int", min=0, max=30)),
    )

    due_date = factory.LazyAttribute(lambda obj: obj.issue_date + timedelta(days=30))

    status = factory.Iterator(
        ["DRAFT", "SENT", "PAID", "PARTIALLY_PAID", "OVERDUE", "CANCELLED"],
        getter=lambda choices: factory.factory.Faker("random_element", elements=choices),
    )

    subtotal = factory.LazyAttribute(lambda obj: Decimal(str(factory.factory.Faker("random_int", min=200, max=2000))))

    tax_amount = factory.LazyAttribute(
        lambda obj: obj.subtotal * Decimal("0.00"),  # No tax for now
    )

    total_amount = factory.LazyAttribute(lambda obj: obj.subtotal + obj.tax_amount)

    paid_amount = factory.LazyAttribute(
        lambda obj: {
            "DRAFT": Decimal("0.00"),
            "SENT": Decimal("0.00"),
            "PAID": obj.total_amount,
            "PARTIALLY_PAID": obj.total_amount
            * Decimal(str(factory.factory.Faker("random_int", min=10, max=90) / 100)),
            "OVERDUE": Decimal("0.00"),
            "CANCELLED": Decimal("0.00"),
        }.get(obj.status, Decimal("0.00")),
    )

    currency = factory.Iterator(["USD", "EUR", "KHR"])

    notes = factory.LazyAttribute(
        lambda obj: (f"Invoice for {obj.term} - Generated on {obj.issue_date}" if obj.term else "Student invoice"),
    )

    sent_date = factory.LazyAttribute(
        lambda obj: (
            obj.issue_date + timedelta(days=1) if obj.status in ["SENT", "PAID", "PARTIALLY_PAID", "OVERDUE"] else None
        ),
    )


class InvoiceLineItemFactory(DjangoModelFactory):
    """Factory for creating invoice line items."""

    class Meta:
        model = InvoiceLineItem

    invoice = SubFactory(InvoiceFactory)

    line_item_type = factory.Iterator(["COURSE", "FEE", "ADJUSTMENT", "DISCOUNT"])

    description = factory.LazyAttribute(
        lambda obj: {
            "COURSE": factory.factory.Faker(
                "random_element",
                elements=[
                    "Course: Introduction to Programming",
                    "Course: Advanced Mathematics",
                    "Course: Business Ethics",
                    "Course: Data Structures",
                    "Course: Digital Marketing",
                ],
            ),
            "FEE": factory.factory.Faker(
                "random_element",
                elements=[
                    "Registration Fee",
                    "Technology Fee",
                    "Library Fee",
                    "Student Services Fee",
                    "Materials Fee",
                ],
            ),
            "ADJUSTMENT": factory.factory.Faker(
                "random_element",
                elements=[
                    "Administrative Adjustment",
                    "Policy Exception",
                    "Special Circumstances",
                ],
            ),
            "DISCOUNT": factory.factory.Faker(
                "random_element",
                elements=[
                    "Early Bird Discount",
                    "Loyalty Discount",
                    "Student Hardship Discount",
                ],
            ),
        }.get(obj.line_item_type, f"{obj.line_item_type} Item"),
    )

    unit_price = factory.LazyAttribute(
        lambda obj: Decimal(
            str(
                {
                    "COURSE": factory.factory.Faker("random_int", min=300, max=800),
                    "FEE": factory.factory.Faker("random_int", min=15, max=100),
                    "ADJUSTMENT": factory.factory.Faker("random_int", min=-100, max=100),
                    "DISCOUNT": -Decimal(str(factory.factory.Faker("random_int", min=25, max=150))),
                }.get(obj.line_item_type, 50),
            ),
        ),
    )

    quantity = factory.LazyAttribute(
        lambda obj: (
            Decimal("1.00")
            if obj.line_item_type in ["COURSE", "ADJUSTMENT", "DISCOUNT"]
            else Decimal(str(factory.factory.Faker("random_int", min=1, max=3)))
        ),
    )

    line_total = factory.LazyAttribute(lambda obj: obj.unit_price * obj.quantity)

    # Optional relationships - will be set by external factories when needed
    enrollment = None
    fee_pricing = None


class PaymentFactory(DjangoModelFactory):
    """Factory for creating payments."""

    class Meta:
        model = Payment

    payment_reference = factory.Sequence(lambda n: f"PAY-{timezone.now().strftime('%Y%m%d%H%M%S')}-{n + 1:04d}")

    invoice = SubFactory(InvoiceFactory)

    amount = factory.LazyAttribute(
        lambda obj: (
            obj.invoice.total_amount
            if factory.factory.Faker("boolean", chance_of_getting_true=60)
            else obj.invoice.total_amount * Decimal(str(factory.factory.Faker("random_int", min=25, max=99) / 100))
        ),
    )

    currency = factory.LazyAttribute(lambda obj: obj.invoice.currency)

    payment_method = factory.Iterator(
        [
            "CASH",
            "BANK_TRANSFER",
            "CREDIT_CARD",
            "DEBIT_CARD",
            "CHECK",
            "MONEY_ORDER",
            "ONLINE",
            "MOBILE_PAYMENT",
        ],
    )

    payment_date = factory.LazyAttribute(
        lambda obj: obj.invoice.issue_date + timedelta(days=factory.factory.Faker("random_int", min=1, max=45)),
    )

    processed_date = factory.LazyAttribute(
        lambda obj: timezone.make_aware(timezone.datetime.combine(obj.payment_date, timezone.datetime.now().time())),
    )

    status = factory.Faker(
        "random_element",
        elements=[
            "COMPLETED",
            "COMPLETED",
            "COMPLETED",  # Weight 70%
            "PENDING",
            "FAILED",
            "CANCELLED",
            "REFUNDED",
        ],
    )

    payer_name = factory.LazyAttribute(
        lambda obj: (
            f"{obj.invoice.student.person.first_name} {obj.invoice.student.person.last_name}"
            if obj.invoice and obj.invoice.student
            else factory.factory.Faker("name")
        ),
    )

    external_reference = factory.LazyAttribute(
        lambda obj: {
            "BANK_TRANSFER": f"TXN-{factory.factory.Faker('random_number', digits=10)}",
            "CREDIT_CARD": f"CC-{factory.factory.Faker('random_number', digits=8)}",
            "DEBIT_CARD": f"DC-{factory.factory.Faker('random_number', digits=8)}",
            "CHECK": f"CHK-{factory.factory.Faker('random_number', digits=6)}",
            "ONLINE": f"ON-{factory.factory.Faker('random_number', digits=12)}",
            "MOBILE_PAYMENT": f"MP-{factory.factory.Faker('random_number', digits=10)}",
        }.get(obj.payment_method, ""),
    )

    notes = factory.LazyAttribute(lambda obj: f"Payment via {obj.payment_method.replace('_', ' ').title()}")

    # Will be set by external factories
    processed_by = None


class FinancialTransactionFactory(DjangoModelFactory):
    """Factory for creating financial transactions."""

    class Meta:
        model = FinancialTransaction

    transaction_id = factory.Sequence(lambda n: f"TXN-{timezone.now().strftime('%Y%m%d%H%M%S')}-{n + 1:06d}")

    transaction_type = factory.Iterator(
        [
            "INVOICE_CREATED",
            "INVOICE_SENT",
            "INVOICE_MODIFIED",
            "INVOICE_CANCELLED",
            "PAYMENT_RECEIVED",
            "PAYMENT_REFUNDED",
            "ADJUSTMENT_APPLIED",
            "DISCOUNT_APPLIED",
            "FEE_WAIVED",
            "PRICE_CHANGED",
        ],
    )

    # Will be set by external factories
    student = None
    invoice = None
    payment = None
    processed_by = None

    amount = factory.LazyAttribute(lambda obj: Decimal(str(factory.factory.Faker("random_int", min=-500, max=1000))))

    currency = factory.Iterator(["USD", "EUR", "KHR"])

    description = factory.LazyAttribute(
        lambda obj: {
            "INVOICE_CREATED": "Invoice created",
            "INVOICE_SENT": "Invoice sent to student",
            "INVOICE_MODIFIED": "Invoice modified",
            "INVOICE_CANCELLED": "Invoice cancelled",
            "PAYMENT_RECEIVED": (
                f"Payment received via "
                f"{factory.factory.Faker('random_element', elements=['cash', 'card', 'transfer'])}"
            ),
            "PAYMENT_REFUNDED": "Payment refunded",
            "ADJUSTMENT_APPLIED": "Administrative adjustment applied",
            "DISCOUNT_APPLIED": "Discount applied",
            "FEE_WAIVED": "Fee waived",
            "PRICE_CHANGED": "Price adjustment",
        }.get(obj.transaction_type, f"{obj.transaction_type} transaction"),
    )

    transaction_date = factory.LazyFunction(
        lambda: timezone.now()
        - timedelta(
            days=factory.factory.Faker("random_int", min=0, max=90),
            hours=factory.factory.Faker("random_int", min=0, max=23),
            minutes=factory.factory.Faker("random_int", min=0, max=59),
        ),
    )

    reference_data = factory.LazyAttribute(
        lambda obj: {
            "transaction_type": obj.transaction_type,
            "generated_by": "factory",
            "test_data": True,
        },
    )


# Utility factories for creating related test data


class StudentFinancePackageFactory(DjangoModelFactory):
    """Factory that creates a complete finance package for a student.

    This includes:
    - Student with enrollments
    - Invoice with line items
    - Payment records
    - Financial transactions
    """

    class Meta:
        model = Invoice

    @classmethod
    def create_complete_package(cls, student=None, term=None, **kwargs):
        """Create a complete finance package for testing."""
        # Import here to avoid circular imports
        from apps.curriculum.tests.factories import TermFactory
        from apps.people.tests.factories import StudentProfileFactory

        if not student:
            student = StudentProfileFactory()
        if not term:
            term = TermFactory()

        # Create invoice
        invoice = InvoiceFactory(student=student, term=term, **kwargs)

        # Create line items
        InvoiceLineItemFactory.create_batch(factory.factory.Faker("random_int", min=1, max=4), invoice=invoice)

        # Recalculate invoice totals
        line_items = invoice.line_items.all()
        invoice.subtotal = sum(item.line_total for item in line_items)
        invoice.total_amount = invoice.subtotal + invoice.tax_amount

        # Adjust paid amount based on status
        if invoice.status == "PAID":
            invoice.paid_amount = invoice.total_amount
        elif invoice.status == "PARTIALLY_PAID":
            invoice.paid_amount = invoice.total_amount * Decimal("0.5")
        else:
            invoice.paid_amount = Decimal("0.00")

        invoice.save()

        # Create payments if invoice is paid
        if invoice.paid_amount > 0:
            PaymentFactory(
                invoice=invoice,
                amount=invoice.paid_amount,
                processed_by=kwargs.get("processed_by"),
            )

        # Create financial transactions
        FinancialTransactionFactory(
            transaction_type="INVOICE_CREATED",
            student=student,
            invoice=invoice,
            amount=invoice.total_amount,
            currency=invoice.currency,
            processed_by=kwargs.get("processed_by"),
        )

        return invoice
