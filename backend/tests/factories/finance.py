"""
Test factories for finance-related models.
"""

from decimal import Decimal

import factory
from factory import fuzzy

from apps.finance.models.core import Invoice, InvoiceLineItem, Payment
from apps.finance.models.pricing import PricingRule


class InvoiceFactory(factory.django.DjangoModelFactory):
    """Factory for Invoice model."""

    class Meta:
        model = Invoice

    student = factory.SubFactory("tests.factories.people.StudentProfileFactory")
    term = factory.SubFactory("tests.factories.curriculum.TermFactory")
    invoice_number = factory.Sequence(lambda n: f"INV-{n:06d}")
    issue_date = factory.Faker("date_this_year")
    due_date = factory.LazyAttribute(lambda obj: obj.issue_date)
    status = fuzzy.FuzzyChoice(["DRAFT", "SENT", "PAID", "OVERDUE", "CANCELLED"])
    subtotal = fuzzy.FuzzyDecimal(Decimal("100.00"), Decimal("5000.00"), precision=2)
    tax_amount = factory.LazyAttribute(lambda obj: obj.subtotal * Decimal("0.10"))
    total_amount = factory.LazyAttribute(lambda obj: obj.subtotal + obj.tax_amount)
    notes = factory.Faker("sentence")


class InvoiceLineItemFactory(factory.django.DjangoModelFactory):
    """Factory for InvoiceLineItem model."""

    class Meta:
        model = InvoiceLineItem

    invoice = factory.SubFactory(InvoiceFactory)
    description = factory.Faker("sentence", nb_words=4)
    quantity = fuzzy.FuzzyInteger(1, 10)
    unit_price = fuzzy.FuzzyDecimal(Decimal("50.00"), Decimal("500.00"), precision=2)
    total_price = factory.LazyAttribute(lambda obj: obj.quantity * obj.unit_price)


class PaymentFactory(factory.django.DjangoModelFactory):
    """Factory for Payment model."""

    class Meta:
        model = Payment

    invoice = factory.SubFactory(InvoiceFactory)
    amount = fuzzy.FuzzyDecimal(Decimal("50.00"), Decimal("5000.00"), precision=2)
    payment_date = factory.Faker("date_this_year")
    payment_method = fuzzy.FuzzyChoice(["CASH", "BANK_TRANSFER", "CREDIT_CARD", "CHECK"])
    reference_number = factory.Sequence(lambda n: f"REF-{n:08d}")
    status = fuzzy.FuzzyChoice(["PENDING", "COMPLETED", "FAILED", "REFUNDED"])
    notes = factory.Faker("sentence")


class PricingRuleFactory(factory.django.DjangoModelFactory):
    """Factory for PricingRule model."""

    class Meta:
        model = PricingRule

    name = factory.Faker("word")
    rule_type = fuzzy.FuzzyChoice(["FIXED", "PERCENTAGE", "TIERED"])
    priority = fuzzy.FuzzyInteger(1, 100)
    is_active = True
    amount = fuzzy.FuzzyDecimal(Decimal("10.00"), Decimal("1000.00"), precision=2)
    effective_date = factory.Faker("date_this_year")
    expiry_date = factory.LazyAttribute(lambda obj: obj.effective_date.replace(year=obj.effective_date.year + 1))
