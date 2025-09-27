"""Analytics-related GraphQL types."""

from typing import List, Optional, Dict, Any
import strawberry
from datetime import datetime

from .common import MetricValue, TimeSeriesPoint
from .student import StudentMetrics
from .academic import AcademicMetrics
from .finance import FinancialMetrics


@strawberry.type
class SystemMetrics:
    """System performance metrics."""
    active_users: MetricValue
    system_health: MetricValue
    performance_score: MetricValue
    response_time: MetricValue
    error_rate: MetricValue


@strawberry.type
class DashboardMetrics:
    """Comprehensive dashboard metrics."""
    student_metrics: StudentMetrics
    academic_metrics: AcademicMetrics
    financial_metrics: FinancialMetrics
    system_metrics: SystemMetrics
    last_updated: datetime


@strawberry.type
class ChartData:
    """Chart data for visualizations."""
    title: str
    chart_type: str  # "line", "bar", "pie", "area"
    data: List[TimeSeriesPoint]
    options: Optional[str] = None  # JSON string for chart options


@strawberry.type
class CustomReportResult:
    """Result of custom report generation."""
    report_type: str
    generated_at: datetime
    data: str  # JSON string of report data
    download_url: Optional[str] = None
    filters_applied: Optional[str] = None  # JSON string


@strawberry.input
class ReportFiltersInput:
    """Filters for custom reports."""
    date_range_days: int = 30
    program_ids: List[strawberry.ID] = strawberry.field(default_factory=list)
    student_statuses: List[str] = strawberry.field(default_factory=list)
    include_financial_data: bool = True
    include_academic_data: bool = True


@strawberry.type
class PredictiveInsight:
    """Predictive analytics insight."""
    model_type: str
    prediction: str  # JSON string of prediction data
    confidence: float
    model_version: str
    features_used: List[str]
    explanation: Optional[str] = None
    recommendations: List[str]


@strawberry.type
class FeatureAnalysis:
    """Feature importance analysis."""
    model_id: str
    feature_correlations: str  # JSON string
    feature_distributions: str  # JSON string
    segment_insights: str  # JSON string
    generated_at: datetime


@strawberry.type
class EnrollmentTrend:
    """Enrollment trend data."""
    period: str
    total_enrollment: int
    new_enrollments: int
    program_breakdown: List["ProgramEnrollment"]
    trend_direction: str


@strawberry.type
class ProgramEnrollment:
    """Program-specific enrollment data."""
    program_name: str
    program_id: strawberry.ID
    enrollment_count: int
    change_from_previous: int
    percentage_of_total: float


@strawberry.type
class GradeDistribution:
    """Grade distribution analysis."""
    class_id: strawberry.ID
    course_code: str
    grade_ranges: List["GradeRange"]
    average_score: float
    median_score: float
    total_students: int


@strawberry.type
class GradeRange:
    """Grade range bucket."""
    label: str  # "A (90-100)", "B (80-89)", etc.
    count: int
    percentage: float


@strawberry.type
class CommunicationStats:
    """Communication analytics."""
    total_messages: int
    active_threads: int
    response_rate: float
    average_response_time_hours: float
    message_types: str  # JSON string of type breakdown
    channels: str  # JSON string of channel breakdown
    peak_hours: List["PeakHour"]


@strawberry.type
class PeakHour:
    """Peak communication hour."""
    hour: int
    message_count: int


@strawberry.type
class WorkflowPerformance:
    """Workflow automation performance."""
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    average_execution_time: float
    most_active_workflows: List["WorkflowStats"]
    failure_reasons: str  # JSON string


@strawberry.type
class WorkflowStats:
    """Individual workflow statistics."""
    name: str
    executions: int
    success_rate: float
    average_duration: float


@strawberry.input
class AnalyticsFiltersInput:
    """Filters for analytics queries."""
    date_range_days: int = 30
    include_predictions: bool = False
    confidence_threshold: float = 0.7
    segment: Optional[str] = None  # "all", "high_risk", "high_performing"


@strawberry.type
class DataQualityMetrics:
    """Data quality and completeness metrics."""
    completeness_score: float
    accuracy_score: float
    consistency_score: float
    timeliness_score: float
    missing_data_fields: List[str]
    data_freshness: datetime
    quality_issues: List[str]