"""Finance services package for clean service-oriented architecture.

This package organizes financial services into focused modules:
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

# Import main service classes for backwards compatibility
from .administrative import AdministrativeFeeService
from .billing_automation_service import BillingAutomationService
from .cashier_service import CashierService
from .gl_integration_service import GLIntegrationService
from .invoice_service import InvoiceService
from .payment_service import PaymentService
from .quickbooks_service import QuickBooksReportService
from .receipt_service import ReceiptService
from .report_service import FinancialReportService
from .separated_pricing_service import FinancialError, SeparatedPricingService
from .transaction_service import FinancialTransactionService

# Backward compatibility alias
PricingService = SeparatedPricingService

__all__ = [
    "AdministrativeFeeService",
    "BillingAutomationService",
    "CashierService",
    "FinancialError",
    "FinancialReportService",
    "FinancialTransactionService",
    "GLIntegrationService",
    "InvoiceService",
    "PaymentService",
    "PricingService",  # Backward compatibility alias
    "QuickBooksReportService",
    "ReceiptService",
    "SeparatedPricingService",
]
