"""
Test configuration for finance app.

Provides fixtures and configuration specific to financial testing.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

# Note: Factory imports moved to fixtures to avoid Django setup issues


@pytest.fixture
def finance_admin(db):
    """Create finance admin user with permissions."""
    User = get_user_model()
    user = User.objects.create_user(
        username="finance_admin", email="finance@test.com", password="testpass123", is_staff=True
    )
    # Add finance-specific permissions here when implemented
    return user


@pytest.fixture
def test_student_with_invoice(db):
    """Create student with an invoice for testing."""
    from tests.factories import InvoiceFactory, StudentProfileFactory, TermFactory

    student = StudentProfileFactory()
    term = TermFactory(is_active=True)
    invoice = InvoiceFactory(student=student, term=term, status="SENT", total_amount=Decimal("1000.00"))
    return student, invoice


@pytest.fixture
def pricing_rules(db):
    """Create basic pricing rules for testing."""
    from tests.factories import PricingRuleFactory

    return [
        PricingRuleFactory(name="Standard Tuition", rule_type="FIXED", amount=Decimal("500.00"), priority=1),
        PricingRuleFactory(name="Early Bird Discount", rule_type="PERCENTAGE", amount=Decimal("10.00"), priority=10),
    ]


@pytest.fixture
def complete_payment_flow(db):
    """Create complete payment flow data for testing."""
    from tests.factories import InvoiceFactory, PaymentFactory, StudentProfileFactory, TermFactory

    student = StudentProfileFactory()
    term = TermFactory(is_active=True)
    invoice = InvoiceFactory(student=student, term=term, total_amount=Decimal("1500.00"), status="SENT")
    payment = PaymentFactory(invoice=invoice, amount=Decimal("500.00"), status="COMPLETED")
    return {"student": student, "term": term, "invoice": invoice, "payment": payment}


@pytest.fixture
def mock_quickbooks():
    """Mock QuickBooks integration for testing."""
    from unittest.mock import Mock, patch

    with patch("apps.finance.services.quickbooks_service.QuickBooksAPI") as mock_qb:
        mock_instance = Mock()
        mock_qb.return_value = mock_instance

        # Setup common mock responses
        mock_instance.create_customer.return_value = {"id": "QB123"}
        mock_instance.create_invoice.return_value = {"id": "INV123"}
        mock_instance.record_payment.return_value = {"id": "PAY123"}

        yield mock_instance
