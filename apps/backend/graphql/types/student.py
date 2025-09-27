"""Student-related GraphQL types."""

from typing import List, Optional
import strawberry
from datetime import datetime, date

from .common import MetricValue, TimeSeriesPoint


@strawberry.type
class PersonType:
    """Person information."""
    unique_id: strawberry.ID
    full_name: str
    family_name: str
    personal_name: str
    khmer_name: Optional[str] = None
    school_email: Optional[str] = None
    personal_email: Optional[str] = None
    date_of_birth: Optional[date] = None
    preferred_gender: Optional[str] = None


@strawberry.type
class StudentAnalytics:
    """Student analytics and predictions."""
    success_prediction: float
    risk_factors: List[str]
    performance_trend: str  # "improving", "declining", "stable"
    attendance_rate: float
    grade_average: Optional[float] = None
    payment_status: str
    engagement_score: float


@strawberry.type
class EnrollmentInfo:
    """Student enrollment information."""
    unique_id: strawberry.ID
    course_code: str
    course_name: str
    term: Optional[str] = None
    status: str
    enrolled_date: datetime
    grade: Optional[str] = None


@strawberry.type
class PaymentInfo:
    """Student payment information."""
    unique_id: strawberry.ID
    amount: str  # Decimal as string for precision
    date: datetime
    method: str
    status: str
    description: Optional[str] = None


@strawberry.type
class TimelineEvent:
    """Student timeline event."""
    event_type: str
    description: str
    timestamp: datetime
    metadata: Optional[str] = None  # JSON string


@strawberry.type
class StudentType:
    """Student information with analytics."""
    unique_id: strawberry.ID
    student_id: str
    person: PersonType
    program: Optional[str] = None
    level: Optional[str] = None
    status: str
    photo_url: Optional[str] = None

    # Analytics
    analytics: Optional[StudentAnalytics] = None

    # Related data
    enrollments: List[EnrollmentInfo]
    payments: List[PaymentInfo]
    timeline: List[TimelineEvent]

    # Metrics
    enrollment_count: int
    last_activity: Optional[datetime] = None

    # Search relevance (when used in search results)
    match_score: Optional[float] = None


@strawberry.input
class StudentSearchFilters:
    """Search filters for students."""
    query: Optional[str] = None
    fuzzy_search: bool = False
    program_ids: List[strawberry.ID] = strawberry.field(default_factory=list)
    levels: List[str] = strawberry.field(default_factory=list)
    statuses: List[str] = strawberry.field(default_factory=list)
    risk_levels: List[str] = strawberry.field(default_factory=list)
    has_overdue_payments: Optional[bool] = None
    min_gpa: Optional[float] = None
    max_gpa: Optional[float] = None


@strawberry.type
class StudentConnection:
    """Paginated student results."""
    edges: List[strawberry.type("StudentEdge")]
    page_info: strawberry.type("StudentPageInfo")
    total_count: int


@strawberry.type
class StudentEdge:
    """Student edge for pagination."""
    node: StudentType
    cursor: str


@strawberry.type
class StudentPageInfo:
    """Student pagination info."""
    has_next_page: bool
    has_previous_page: bool
    start_cursor: Optional[str] = None
    end_cursor: Optional[str] = None


@strawberry.type
class StudentMetrics:
    """Student-related metrics."""
    total_count: MetricValue
    new_this_week: MetricValue
    at_risk_count: MetricValue
    success_rate: MetricValue
    enrollment_trends: List[TimeSeriesPoint]