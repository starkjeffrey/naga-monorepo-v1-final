"""Finance models package.

This package organizes finance models into logical groupings for better maintainability.
"""

# Core financial models
# A/R reconstruction models
# Administrative fee models
from .administrative import (
    AdministrativeFeeConfig,
    DocumentExcessFee,
    ExtendedLineItemType,
)
from .ar_reconstruction import (
    ARReconstructionBatch,
    ClerkIdentification,
    LegacyReceiptMapping,
    ReconstructionScholarshipEntry,
)
from .core import (
    CashierSession,
    Currency,
    FinancialTransaction,
    Invoice,
    InvoiceLineItem,
    Payment,
)

# Discount models
from .discounts import (
    DiscountApplication,
    DiscountRule,
)

# G/L and accounting models
from .gl import (
    FeeGLMapping,
    GLAccount,
    GLBatch,
    JournalEntry,
    JournalEntryLine,
)

# Payment configuration model (moved from settings app)
from .payment_configuration import PaymentConfiguration

# Pricing models
from .pricing import (
    CourseFixedPricing,
    DefaultPricing,
    FeePricing,
    FeeType,
    ReadingClassPricing,
    SeniorProjectCourse,
    SeniorProjectPricing,
)

# Migration-specific reconciliation models
from .reconciliation import (
    MaterialityThreshold,
    ReconciliationAdjustment,
    ReconciliationBatch,
    ReconciliationRule,
    ReconciliationStatus,
)

# Ensure all models are available at package level for Django
__all__ = [
    # A/R reconstruction models
    "ARReconstructionBatch",
    # Administrative fee models
    "AdministrativeFeeConfig",
    # Core models
    "CashierSession",
    "ClerkIdentification",
    "CourseFixedPricing",
    "Currency",
    # Pricing models
    "DefaultPricing",
    "DiscountApplication",
    "DiscountRule",
    # Administrative fee models
    "DocumentExcessFee",
    # Extended line item types
    "ExtendedLineItemType",
    # G/L models
    "FeeGLMapping",
    "FeePricing",
    "FeeType",
    "FinancialTransaction",
    "GLAccount",
    "GLBatch",
    # Core models
    "Invoice",
    "InvoiceLineItem",
    "JournalEntry",
    "JournalEntryLine",
    "LegacyReceiptMapping",
    # Reconciliation models
    "MaterialityThreshold",
    "Payment",
    "PaymentConfiguration",
    "ReadingClassPricing",
    "ReconciliationAdjustment",
    "ReconciliationBatch",
    "ReconciliationRule",
    "ReconciliationStatus",
    "ReconstructionScholarshipEntry",
    "SeniorProjectCourse",
    "SeniorProjectPricing",
]
