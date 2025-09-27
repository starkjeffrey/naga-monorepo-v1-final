"""Finance-related GraphQL queries."""

import strawberry
from typing import List, Optional
from datetime import datetime, timedelta

from ..types.finance import (
    FinancialMetrics,
    PaymentType,
    InvoiceType,
    ScholarshipMatchType
)
from ..types.common import MetricValue, TimeSeriesPoint


@strawberry.type
class FinanceQueries:
    """Finance-related GraphQL queries."""

    @strawberry.field
    def financial_analytics(
        self,
        info,
        date_range_days: int = 30,
        include_forecasts: bool = True
    ) -> FinancialMetrics:
        """Get comprehensive financial analytics."""

        # Mock financial metrics
        return FinancialMetrics(
            total_revenue=MetricValue(
                value=125670.50,
                label="Total Revenue",
                trend="up",
                change_percent=8.7,
                previous_value=115532.25
            ),
            pending_payments=MetricValue(
                value=23450.00,
                label="Pending Payments",
                trend="down",
                change_percent=-5.2,
                previous_value=24734.50
            ),
            overdue_amount=MetricValue(
                value=8950.00,
                label="Overdue Amount",
                trend="down",
                change_percent=-15.3,
                previous_value=10567.00
            ),
            scholarship_total=MetricValue(
                value=45200.00,
                label="Scholarship Awards",
                trend="up",
                change_percent=12.3,
                previous_value=40250.00
            ),
            payment_trends=[
                TimeSeriesPoint(
                    timestamp=datetime.now() - timedelta(days=i),
                    value=5000 + i * 100,
                    label=f"Day {i}"
                )
                for i in range(7)
            ],
            payment_method_breakdown=[],
            revenue_forecast="135000.00" if include_forecasts else None,
            forecast_confidence=0.85 if include_forecasts else None
        )

    @strawberry.field
    def scholarship_matches(
        self,
        info,
        student_id: strawberry.ID,
        min_match_score: float = 0.5
    ) -> List[ScholarshipMatchType]:
        """Get scholarship matches for a student."""

        # Mock scholarship matches
        from ..types.finance import ScholarshipType

        mock_scholarships = [
            ScholarshipMatchType(
                scholarship=ScholarshipType(
                    unique_id="1",
                    name="Academic Excellence Scholarship",
                    amount="2000.00",
                    description="For students with GPA > 3.5",
                    application_deadline=datetime.now().date(),
                    is_active=True,
                    requirements=["GPA >= 3.5", "Full-time enrollment"]
                ),
                match_score=0.92,
                criteria_met=["GPA requirement", "Enrollment status"],
                criteria_missing=[],
                recommendation="Highly recommended"
            )
        ]

        return [match for match in mock_scholarships if match.match_score >= min_match_score]