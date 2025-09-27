"""Finance-related GraphQL types."""

from typing import List, Optional
import strawberry
from datetime import datetime, date
from decimal import Decimal

from .common import MetricValue, TimeSeriesPoint


@strawberry.type
class CurrencyType:
    """Currency information."""
    code: str
    name: str
    symbol: str


@strawberry.type
class InvoiceLineItemType:
    """Invoice line item."""
    unique_id: strawberry.ID
    description: str
    quantity: int
    unit_price: str  # Decimal as string
    total_amount: str  # Decimal as string


@strawberry.type
class InvoiceType:
    """Invoice information."""
    unique_id: strawberry.ID
    student_id: strawberry.ID
    amount: str  # Decimal as string
    currency: CurrencyType
    description: str
    due_date: date
    status: str
    created_at: datetime
    line_items: List[InvoiceLineItemType]


@strawberry.type
class PaymentType:
    """Payment information."""
    unique_id: strawberry.ID
    invoice: Optional[InvoiceType] = None
    amount: str  # Decimal as string
    currency: CurrencyType
    payment_method: str
    status: str
    payment_date: datetime
    notes: Optional[str] = None


@strawberry.type
class FinancialTransactionType:
    """Financial transaction record."""
    unique_id: strawberry.ID
    amount: str  # Decimal as string
    currency: CurrencyType
    transaction_type: str
    payment_method: str
    description: str
    student_id: Optional[strawberry.ID] = None
    created_at: datetime


@strawberry.type
class CashierSessionType:
    """Cashier session information."""
    unique_id: strawberry.ID
    cashier_name: str
    session_date: date
    opening_balance: str  # Decimal as string
    expected_balance: str  # Decimal as string
    actual_balance: Optional[str] = None  # Decimal as string
    is_closed: bool
    total_transactions: int


@strawberry.type
class ScholarshipType:
    """Scholarship information."""
    unique_id: strawberry.ID
    name: str
    amount: str  # Decimal as string
    description: Optional[str] = None
    application_deadline: date
    is_active: bool
    requirements: List[str]


@strawberry.type
class ScholarshipMatchType:
    """Scholarship match for a student."""
    scholarship: ScholarshipType
    match_score: float
    criteria_met: List[str]
    criteria_missing: List[str]
    recommendation: str


@strawberry.type
class PaymentMethodBreakdown:
    """Payment method statistics."""
    method: str
    count: int
    total_amount: str  # Decimal as string
    percentage: float


@strawberry.type
class FinancialMetrics:
    """Financial metrics and analytics."""
    total_revenue: MetricValue
    pending_payments: MetricValue
    overdue_amount: MetricValue
    scholarship_total: MetricValue
    payment_trends: List[TimeSeriesPoint]
    payment_method_breakdown: List[PaymentMethodBreakdown]

    # Forecasting
    revenue_forecast: Optional[str] = None  # Decimal as string
    forecast_confidence: Optional[float] = None


@strawberry.type
class POSTransactionResult:
    """Result of POS transaction."""
    transaction_id: strawberry.ID
    amount: str  # Decimal as string
    status: str
    receipt_number: str
    processed_at: datetime


@strawberry.input
class POSTransactionInput:
    """Input for POS transactions."""
    amount: str  # Decimal as string
    payment_method: str
    student_id: Optional[strawberry.ID] = None
    description: str
    line_items: List["LineItemInput"] = strawberry.field(default_factory=list)


@strawberry.input
class LineItemInput:
    """Line item input for transactions."""
    description: str
    quantity: int = 1
    unit_price: str  # Decimal as string


@strawberry.type
class PaymentReminderResult:
    """Result of payment reminder setup."""
    success: bool
    reminders_created: int
    students_processed: int
    message: str


@strawberry.input
class PaymentReminderInput:
    """Input for setting up payment reminders."""
    student_ids: List[strawberry.ID] = strawberry.field(default_factory=list)
    reminder_days: List[int] = strawberry.field(default_factory=lambda: [7, 3, 1])
    template: str = "default"


@strawberry.type
class RevenueForecast:
    """Revenue forecast data."""
    period: str
    forecasted_amount: str  # Decimal as string
    confidence_level: float
    trend_direction: str
    monthly_breakdown: List[TimeSeriesPoint]


@strawberry.type
class PaymentAuditSummary:
    """Payment audit summary for compliance."""
    period_start: date
    period_end: date
    total_amount: str  # Decimal as string
    total_count: int
    average_amount: str  # Decimal as string
    payment_methods: List[PaymentMethodBreakdown]
    daily_summaries: List["DailySummary"]


@strawberry.type
class DailySummary:
    """Daily payment summary."""
    date: date
    count: int
    total: str  # Decimal as string