"""Analytics-related GraphQL queries."""

import strawberry
from typing import List, Optional
from datetime import datetime

from ..types.analytics import (
    ChartData,
    CustomReportResult,
    PredictiveInsight,
    EnrollmentTrend,
    GradeDistribution,
    ReportFiltersInput,
    AnalyticsFiltersInput
)
from ..types.common import TimeSeriesPoint


@strawberry.type
class AnalyticsQueries:
    """Analytics-related GraphQL queries."""

    @strawberry.field
    def enrollment_trends(
        self,
        info,
        months: int = 12,
        program_id: Optional[strawberry.ID] = None
    ) -> ChartData:
        """Get enrollment trends chart data."""

        # Generate sample trend data
        data_points = []
        base_date = datetime.now().replace(day=1)

        for i in range(months):
            month_date = base_date.replace(month=((base_date.month - i - 1) % 12) + 1)
            # Simulate seasonal enrollment patterns
            base_enrollment = 100
            if month_date.month in [1, 9]:  # January and September peaks
                enrollment = base_enrollment + 20
            elif month_date.month in [6, 7]:  # Summer low
                enrollment = base_enrollment - 15
            else:
                enrollment = base_enrollment + (i % 3 - 1) * 5

            data_points.append(TimeSeriesPoint(
                timestamp=month_date,
                value=float(enrollment),
                label=month_date.strftime('%Y-%m')
            ))

        return ChartData(
            title="Enrollment Trends",
            chart_type="line",
            data=data_points,
            options='{"months": ' + str(months) + ', "program_filter": "' + (str(program_id) if program_id else "all") + '"}'
        )

    @strawberry.field
    def custom_report(
        self,
        info,
        report_type: str,
        filters: Optional[ReportFiltersInput] = None
    ) -> CustomReportResult:
        """Generate custom analytical reports."""

        if not filters:
            filters = ReportFiltersInput()

        if report_type == "student_performance":
            report_data = {
                "summary": {
                    "total_students": 1247,
                    "average_gpa": 3.42,
                    "attendance_rate": 0.92,
                    "completion_rate": 0.87
                },
                "by_program": [
                    {
                        "program": "Business Administration",
                        "student_count": 345,
                        "average_gpa": 3.45,
                        "completion_rate": 0.89
                    },
                    {
                        "program": "Computer Science",
                        "student_count": 289,
                        "average_gpa": 3.38,
                        "completion_rate": 0.85
                    }
                ]
            }

        elif report_type == "financial_analysis":
            report_data = {
                "revenue_summary": {
                    "total_revenue": 125670.50,
                    "tuition_revenue": 98450.25,
                    "fees_revenue": 23220.25
                },
                "payment_analysis": {
                    "on_time_payments": 0.78,
                    "late_payments": 0.18,
                    "defaulted_payments": 0.04
                }
            }

        else:
            report_data = {"error": f"Unknown report type: {report_type}"}

        import json
        return CustomReportResult(
            report_type=report_type,
            generated_at=datetime.now(),
            data=json.dumps(report_data),
            download_url=f"/api/v2/analytics/reports/download/?type={report_type}",
            filters_applied=json.dumps({
                "date_range_days": filters.date_range_days,
                "include_financial_data": filters.include_financial_data,
                "include_academic_data": filters.include_academic_data
            })
        )

    @strawberry.field
    def predictive_insights(
        self,
        info,
        model_type: str = "student_success",
        filters: Optional[AnalyticsFiltersInput] = None
    ) -> PredictiveInsight:
        """Get predictive analytics and insights."""

        if not filters:
            filters = AnalyticsFiltersInput()

        if model_type == "student_success":
            insight_data = {
                "high_risk_students": {
                    "count": 45,
                    "factors": ["low_attendance", "failing_grades", "financial_stress"]
                },
                "likely_to_excel": {
                    "count": 123,
                    "factors": ["high_engagement", "strong_attendance"]
                }
            }

        elif model_type == "enrollment_forecast":
            insight_data = {
                "predicted_enrollment": 1320,
                "confidence_interval": [1250, 1390],
                "by_program": [
                    {"program": "Business", "predicted": 380},
                    {"program": "Computer Science", "predicted": 310}
                ]
            }

        else:
            insight_data = {"error": f"Unknown model type: {model_type}"}

        import json
        return PredictiveInsight(
            model_type=model_type,
            prediction=json.dumps(insight_data),
            confidence=filters.confidence_threshold,
            model_version="v2.1",
            features_used=["gpa", "attendance", "engagement"],
            explanation=f"Predictive analysis for {model_type} with {filters.confidence_threshold} confidence",
            recommendations=[
                "Monitor high-risk students closely",
                "Provide additional support for at-risk categories"
            ]
        )

    @strawberry.field
    def grade_distribution(
        self,
        info,
        class_id: strawberry.ID
    ) -> Optional[GradeDistribution]:
        """Get grade distribution for a class."""

        from ..types.analytics import GradeRange

        # Mock grade distribution
        return GradeDistribution(
            class_id=class_id,
            course_code="MATH101",
            grade_ranges=[
                GradeRange(label="A (90-100)", count=15, percentage=25.0),
                GradeRange(label="B (80-89)", count=20, percentage=33.3),
                GradeRange(label="C (70-79)", count=15, percentage=25.0),
                GradeRange(label="D (60-69)", count=7, percentage=11.7),
                GradeRange(label="F (0-59)", count=3, percentage=5.0)
            ],
            average_score=78.5,
            median_score=82.0,
            total_students=60
        )