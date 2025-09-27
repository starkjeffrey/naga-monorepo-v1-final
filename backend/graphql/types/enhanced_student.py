"""Enhanced Student GraphQL types with advanced features."""

from typing import List, Optional
import strawberry
from datetime import datetime, date
from decimal import Decimal

from .common import MetricValue, TimeSeriesPoint


@strawberry.type
class RiskAssessment:
    """Student risk assessment details."""
    risk_score: float
    risk_level: str  # "low", "medium", "high"
    risk_factors: List[str]
    recommendations: List[str]
    last_calculated: datetime
    confidence: float


@strawberry.type
class SuccessPrediction:
    """Student success prediction details."""
    success_probability: float
    confidence: float
    key_factors: List[str]
    improvement_areas: List[str]
    model_version: str
    prediction_date: datetime


@strawberry.type
class StudentPhoto:
    """Student photo information."""
    photo_url: str
    thumbnail_url: Optional[str] = None
    uploaded_at: datetime
    file_size: int
    width: int
    height: int


@strawberry.type
class EmergencyContact:
    """Emergency contact information."""
    name: str
    relationship: str
    phone_primary: str
    phone_secondary: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    is_primary: bool


@strawberry.type
class AttendanceRecord:
    """Attendance record details."""
    date: date
    status: str  # "present", "absent", "late", "excused"
    check_in_time: Optional[str] = None  # Time as string
    check_out_time: Optional[str] = None
    location: Optional[str] = None
    method: Optional[str] = None  # "manual", "qr_scan", "biometric"
    notes: Optional[str] = None


@strawberry.type
class GradeDetail:
    """Detailed grade information."""
    assignment_name: str
    assignment_type: str
    score: Optional[float] = None
    max_score: float
    percentage: Optional[float] = None
    letter_grade: Optional[str] = None
    grade_points: Optional[float] = None
    date_recorded: datetime
    instructor_notes: Optional[str] = None


@strawberry.type
class EnhancedEnrollmentInfo:
    """Enhanced student enrollment with detailed information."""
    unique_id: strawberry.ID
    course_code: str
    course_name: str
    course_description: Optional[str] = None
    credit_hours: int
    term: Optional[str] = None
    instructor: Optional[str] = None
    status: str
    enrolled_date: datetime
    completion_date: Optional[datetime] = None

    # Grades
    current_grade: Optional[str] = None
    grade_percentage: Optional[float] = None
    grades: List[GradeDetail]

    # Attendance
    attendance_rate: float
    total_sessions: int
    attended_sessions: int
    attendance_records: List[AttendanceRecord]

    # Financial
    total_fees: str  # Decimal as string
    paid_amount: str
    outstanding_amount: str


@strawberry.type
class FinancialSummary:
    """Student financial summary."""
    total_charges: str  # Decimal as string
    total_payments: str
    current_balance: str
    overdue_amount: str
    credit_balance: str

    # Payment history
    last_payment_date: Optional[datetime] = None
    last_payment_amount: Optional[str] = None
    payment_plan_active: bool

    # Scholarship information
    scholarship_total: str
    scholarship_percentage: float
    financial_aid_eligibility: bool


@strawberry.type
class AcademicProgress:
    """Academic progress tracking."""
    current_term_gpa: Optional[float] = None
    cumulative_gpa: Optional[float] = None
    total_credit_hours: int
    completed_credit_hours: int
    in_progress_credit_hours: int

    # Degree progress
    degree_completion_percentage: float
    required_courses_remaining: int
    elective_credits_needed: int
    expected_graduation_date: Optional[date] = None

    # Academic standing
    academic_standing: str  # "good", "probation", "suspension"
    honors_recognition: List[str]


@strawberry.type
class EnhancedStudentType:
    """Enhanced student with comprehensive information."""
    unique_id: strawberry.ID
    student_id: str
    person: strawberry.type("PersonType")

    # Basic information
    program: Optional[str] = None
    level: Optional[str] = None
    status: str
    enrollment_start_date: Optional[date] = None
    expected_graduation_date: Optional[date] = None

    # Contact information
    emergency_contacts: List[EmergencyContact]

    # Visual
    photo: Optional[StudentPhoto] = None

    # Analytics and predictions
    analytics: Optional[strawberry.type("StudentAnalytics")] = None
    risk_assessment: Optional[RiskAssessment] = None
    success_prediction: Optional[SuccessPrediction] = None

    # Academic information
    academic_progress: AcademicProgress
    enrollments: List[EnhancedEnrollmentInfo]

    # Financial information
    financial_summary: FinancialSummary

    # Timeline and activity
    timeline: List[strawberry.type("TimelineEvent")]
    last_activity: Optional[datetime] = None

    # Metrics
    engagement_score: float
    satisfaction_score: Optional[float] = None

    # Search relevance (when used in search results)
    match_score: Optional[float] = None


@strawberry.input
class AdvancedStudentSearchFilters:
    """Advanced search filters for students."""
    # Text search
    query: Optional[str] = None
    fuzzy_search: bool = False
    search_fields: List[str] = strawberry.field(default_factory=list)

    # Categorical filters
    program_ids: List[strawberry.ID] = strawberry.field(default_factory=list)
    levels: List[str] = strawberry.field(default_factory=list)
    statuses: List[str] = strawberry.field(default_factory=list)

    # Academic filters
    min_gpa: Optional[float] = None
    max_gpa: Optional[float] = None
    academic_standing: List[str] = strawberry.field(default_factory=list)
    risk_levels: List[str] = strawberry.field(default_factory=list)

    # Financial filters
    has_overdue_payments: Optional[bool] = None
    has_scholarship: Optional[bool] = None
    payment_plan_active: Optional[bool] = None

    # Engagement filters
    min_attendance_rate: Optional[float] = None
    max_attendance_rate: Optional[float] = None
    min_engagement_score: Optional[float] = None

    # Date filters
    enrolled_after: Optional[date] = None
    enrolled_before: Optional[date] = None
    last_activity_after: Optional[datetime] = None

    # Location filters
    location: Optional[str] = None
    program_location: Optional[str] = None


@strawberry.input
class StudentSortInput:
    """Sorting options for student queries."""
    field: str  # "name", "gpa", "risk_score", "last_activity", "enrollment_date"
    direction: str = "ASC"  # "ASC", "DESC"


@strawberry.input
class BulkStudentAction:
    """Bulk action input for multiple students."""
    action: str  # "update_status", "send_notification", "export_data", "generate_reports"
    student_ids: List[strawberry.ID]
    parameters: Optional[str] = None  # JSON string for action parameters
    dry_run: bool = False


@strawberry.type
class BulkActionResult:
    """Result of bulk action on students."""
    success: bool
    processed_count: int
    failed_count: int
    failed_ids: List[strawberry.ID]
    message: str
    details: Optional[str] = None  # JSON string with detailed results


@strawberry.type
class StudentSearchResult:
    """Student search with facets and aggregations."""
    students: List[EnhancedStudentType]
    total_count: int
    facets: Optional[str] = None  # JSON string with facet counts
    aggregations: Optional[str] = None  # JSON string with numeric aggregations
    search_time_ms: int
    suggestions: List[str]  # Search suggestions for typos/improvements


@strawberry.input
class PhotoUploadInput:
    """Photo upload input."""
    student_id: strawberry.ID
    photo_data: str  # Base64 encoded image data
    filename: str
    content_type: str


@strawberry.type
class PhotoUploadResult:
    """Photo upload result."""
    success: bool
    message: str
    photo: Optional[StudentPhoto] = None


@strawberry.input
class TimelineFilterInput:
    """Timeline filtering options."""
    event_types: List[str] = strawberry.field(default_factory=list)
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = 50


# Export all types
__all__ = [
    "RiskAssessment",
    "SuccessPrediction",
    "StudentPhoto",
    "EmergencyContact",
    "AttendanceRecord",
    "GradeDetail",
    "EnhancedEnrollmentInfo",
    "FinancialSummary",
    "AcademicProgress",
    "EnhancedStudentType",
    "AdvancedStudentSearchFilters",
    "StudentSortInput",
    "BulkStudentAction",
    "BulkActionResult",
    "StudentSearchResult",
    "PhotoUploadInput",
    "PhotoUploadResult",
    "TimelineFilterInput",
]