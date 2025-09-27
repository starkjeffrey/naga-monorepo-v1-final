"""Finance services for pricing and billing calculations following clean architecture.

This module provides services for:
- Course and fee pricing calculations with historical support
- Invoice generation and management
- Payment processing and tracking
- Financial transaction audit trails
- Billing automation based on enrollment events

Key architectural decisions:
- Business logic separated from models and views
- Type-safe operations with comprehensive error handling
- No circular dependencies - only depends on people, enrollment, curriculum
- Event-driven billing through signals integration
- Comprehensive audit trails for financial compliance
- Multi-currency support with proper conversion handling

Service classes have been organized into focused modules:
- separated_pricing_service: Course and fee pricing calculations with separated models
- invoice_service: Invoice generation and management
- payment_service: Payment processing and tracking
- transaction_service: Financial transaction audit trails
- billing_automation_service: Automated billing based on events
- gl_integration_service: General ledger integration
- quickbooks_service: QuickBooks report generation
- cashier_service: Cashier operations and cash management
- receipt_service: Receipt generation in various formats
- report_service: Financial reporting and analysis

Note: pricing_service is deprecated in favor of separated_pricing_service
"""

# Import all services from their respective modules for backward compatibility
from .services.billing_automation_service import BillingAutomationService
from .services.cashier_service import CashierService
from .services.gl_integration_service import GLIntegrationService
from .services.invoice_service import InvoiceService
from .services.payment_service import PaymentService
from .services.quickbooks_service import QuickBooksReportService
from .services.receipt_service import ReceiptService
from .services.report_service import FinancialReportService
from .services.separated_pricing_service import (
    FINANCIAL_PRECISION,
    FinancialError,
    SeparatedPricingService,
    normalize_decimal,
    safe_decimal_add,
)
from .services.transaction_service import FinancialTransactionService

# Backward compatibility alias
PricingService = SeparatedPricingService

# Export all services and utilities
__all__ = [
    "FINANCIAL_PRECISION",
    # Services
    "BillingAutomationService",
    "CashierService",
    # Utilities
    "FinancialError",
    "FinancialReportService",
    "FinancialTransactionService",
    "GLIntegrationService",
    "InvoiceService",
    "PaymentService",
    "PricingService",
    "QuickBooksReportService",
    "ReceiptService",
    "normalize_decimal",
    "safe_decimal_add",
]
