"""Dashboard-related GraphQL queries."""

import strawberry
from datetime import datetime, timedelta
from typing import Optional

from ..types.analytics import DashboardMetrics
from ..types.student import StudentMetrics
from ..types.academic import AcademicMetrics
from ..types.finance import FinancialMetrics
from ..types.analytics import SystemMetrics
from ..types.common import MetricValue, TimeSeriesPoint


@strawberry.type
class DashboardQueries:
    """Dashboard-related GraphQL queries."""

    @strawberry.field
    def dashboard_metrics(
        self,
        info,
        date_range_days: int = 30
    ) -> DashboardMetrics:
        """Get comprehensive dashboard metrics."""

        # Mock student metrics
        student_metrics = StudentMetrics(
            total_count=MetricValue(
                value=1247,
                label="Total Students",
                trend="up",
                change_percent=3.2,
                previous_value=1208
            ),
            new_this_week=MetricValue(
                value=23,
                label="New This Week",
                trend="stable",
                change_percent=0.0,
                previous_value=23
            ),
            at_risk_count=MetricValue(
                value=45,
                label="At Risk Students",
                trend="down",
                change_percent=-12.5,
                previous_value=52
            ),
            success_rate=MetricValue(
                value=0.87,
                label="Success Rate",
                trend="up",
                change_percent=2.1,
                previous_value=0.85
            ),
            enrollment_trends=[
                TimeSeriesPoint(
                    timestamp=datetime.now() - timedelta(days=i),
                    value=100 + i % 10,
                    label=f"Day {i}"
                )
                for i in range(7)
            ]
        )

        # Mock academic metrics
        academic_metrics = AcademicMetrics(
            grades_entered=2341,
            transcripts_pending=12,
            attendance_rate=0.92,
            average_class_size=25.5,
            course_completion_rate=0.89
        )

        # Mock financial metrics
        financial_metrics = FinancialMetrics(
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
            payment_method_breakdown=[]
        )

        # Mock system metrics
        system_metrics = SystemMetrics(
            active_users=MetricValue(
                value=156,
                label="Active Users",
                trend="up",
                change_percent=6.8,
                previous_value=146
            ),
            system_health=MetricValue(
                value=0.98,
                label="System Health",
                trend="stable",
                change_percent=0.0,
                previous_value=0.98
            ),
            performance_score=MetricValue(
                value=0.94,
                label="Performance Score",
                trend="up",
                change_percent=1.5,
                previous_value=0.926
            ),
            response_time=MetricValue(
                value=245.5,
                label="Avg Response Time (ms)",
                trend="down",
                change_percent=-8.2,
                previous_value=267.3
            ),
            error_rate=MetricValue(
                value=0.02,
                label="Error Rate",
                trend="down",
                change_percent=-25.0,
                previous_value=0.027
            )
        )

        return DashboardMetrics(
            student_metrics=student_metrics,
            academic_metrics=academic_metrics,
            financial_metrics=financial_metrics,
            system_metrics=system_metrics,
            last_updated=datetime.now()
        )