"""Enhanced API v2 Schemas with advanced features.

This module provides comprehensive schema definitions for the enhanced API
with support for:
- Advanced filtering and search
- Real-time updates and analytics
- Bulk operations and batch processing
- AI predictions and insights
- Performance optimization
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from ninja import Field, Schema
from pydantic import ConfigDict, validator


# Base schemas
class BaseSchema(Schema):
    """Base schema with common configuration."""
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        arbitrary_types_allowed=True
    )


# System schemas
class HealthResponse(BaseSchema):
    status: str
    version: str
    services: Dict[str, str]


class ApiInfoResponse(BaseSchema):
    title: str
    version: str
    description: str
    docs_url: str
    contact: Dict[str, str]
    features: List[str] = []


# Pagination schemas
class PaginationMeta(BaseSchema):
    """Enhanced pagination metadata."""
    page: int
    page_size: int
    total_count: int
    total_pages: int
    has_next: bool
    has_previous: bool
    next_page: Optional[int] = None
    previous_page: Optional[int] = None


class PaginatedResponse(BaseSchema):
    """Generic paginated response wrapper."""
    data: List[Any]
    meta: PaginationMeta


# Search and filter schemas
class DateRangeFilter(BaseSchema):
    """Date range filtering."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class SearchFilters(BaseSchema):
    """Advanced search filters."""
    query: Optional[str] = None
    fuzzy_search: bool = False
    fields: List[str] = []
    date_range: Optional[DateRangeFilter] = None
    tags: List[str] = []
    status: Optional[str] = None
    program_id: Optional[UUID] = None
    enrollment_year: Optional[int] = None
    risk_level: Optional[str] = None


class SortOption(BaseSchema):
    """Sorting configuration."""
    field: str
    descending: bool = False


# Analytics schemas
class MetricValue(BaseSchema):
    """Single metric value with metadata."""
    value: Union[int, float, Decimal]
    label: str
    trend: Optional[str] = None  # "up", "down", "stable"
    change_percent: Optional[float] = None
    previous_value: Optional[Union[int, float, Decimal]] = None


class DashboardMetrics(BaseSchema):
    """Dashboard metrics container."""
    student_metrics: Dict[str, MetricValue]
    academic_metrics: Dict[str, MetricValue]
    financial_metrics: Dict[str, MetricValue]
    system_metrics: Dict[str, MetricValue]
    last_updated: datetime


class TimeSeriesPoint(BaseSchema):
    """Time series data point."""
    timestamp: datetime
    value: Union[int, float, Decimal]
    label: Optional[str] = None


class ChartData(BaseSchema):
    """Chart data container."""
    title: str
    type: str  # "line", "bar", "pie", "area"
    data: List[TimeSeriesPoint]
    options: Dict[str, Any] = {}


# Student schemas
class StudentBasicInfo(BaseSchema):
    """Basic student information for lists."""
    unique_id: UUID
    student_id: str
    full_name: str
    email: str
    program: Optional[str] = None
    level: Optional[str] = None
    status: str
    photo_url: Optional[str] = None


class StudentSearchResult(BaseSchema):
    """Enhanced student search result with analytics."""
    id: UUID
    student_id: str
    name: str
    email: str
    status: str
    gpa: Optional[float] = None
    risk_score: Optional[float] = None
    enrollment_date: Optional[date] = None
    program_name: Optional[str] = None


class StudentAnalytics(BaseSchema):
    """Student analytics and predictions."""
    success_prediction: float
    risk_factors: List[str]
    performance_trend: str  # "improving", "declining", "stable"
    attendance_rate: float
    grade_average: Optional[float] = None
    payment_status: str
    engagement_score: float


class StudentDetailedInfo(StudentBasicInfo):
    """Detailed student information."""
    personal_email: Optional[str] = None
    phone_numbers: List[str] = []
    date_of_birth: Optional[date] = None
    address: Optional[str] = None
    emergency_contacts: List[Dict[str, str]] = []
    analytics: Optional[StudentAnalytics] = None
    enrollments: List[Dict[str, Any]] = []
    payments: List[Dict[str, Any]] = []
    timeline: List[Dict[str, Any]] = []


class PhotoUploadResponse(BaseSchema):
    """Photo upload response."""
    success: bool
    message: str
    photo_url: Optional[str] = None


class TimelineEvent(BaseSchema):
    """Student timeline event."""
    id: str
    type: str  # "enrollment", "grade", "payment", "attendance"
    title: str
    description: str
    timestamp: datetime
    metadata: Dict[str, Any] = {}


class RiskScoreResponse(BaseSchema):
    """Student risk assessment response."""
    risk_score: float  # 0-100
    risk_level: str  # "low", "medium", "high"
    risk_factors: List[str]
    recommendations: List[str] = []
    last_calculated: datetime


class SuccessPredictionResponse(BaseSchema):
    """Student success prediction response."""
    success_probability: float  # 0-1
    confidence: float  # 0-1
    key_factors: List[str]
    improvement_areas: List[str] = []
    model_version: str = "1.0"


# Bulk operation schemas
class BulkActionRequest(BaseSchema):
    """Bulk action request."""
    action: str
    student_ids: List[UUID]
    data: Dict[str, Any] = {}
    dry_run: bool = False


class BulkActionResult(BaseSchema):
    """Bulk action result."""
    success: bool
    processed_count: int
    failed_count: int
    failed_ids: List[UUID] = []
    message: str


# Academic schemas
class GradeEntry(BaseSchema):
    """Grade entry for spreadsheet interface."""
    student_id: UUID
    assignment_id: UUID
    score: Optional[float] = None
    max_score: float
    notes: Optional[str] = None
    last_modified: datetime
    modified_by: str


class GradeSpreadsheetData(BaseSchema):
    """Grade spreadsheet data structure."""
    class_id: UUID
    assignments: List[Dict[str, Any]]
    students: List[Dict[str, Any]]
    grades: List[List[Optional[float]]]  # 2D array of grades
    metadata: Dict[str, Any]


class ScheduleConflict(BaseSchema):
    """Schedule conflict detection."""
    type: str  # "time_overlap", "resource_conflict", "capacity_exceeded"
    severity: str  # "critical", "warning", "info"
    message: str
    affected_items: List[Dict[str, Any]]
    suggestions: List[str] = []


# Financial schemas
class POSTransaction(BaseSchema):
    """Point-of-sale transaction."""
    amount: Decimal
    payment_method: str
    student_id: Optional[UUID] = None
    description: str
    line_items: List[Dict[str, Any]] = []
    metadata: Dict[str, Any] = {}


class FinancialAnalytics(BaseSchema):
    """Financial analytics and forecasting."""
    total_revenue: Decimal
    pending_payments: Decimal
    overdue_amount: Decimal
    scholarship_total: Decimal
    payment_trends: List[TimeSeriesPoint]
    forecasts: Dict[str, Decimal]
    payment_method_breakdown: Dict[str, Decimal]


# Communication schemas
class MessageThread(BaseSchema):
    """Message thread for communications."""
    thread_id: UUID
    subject: str
    participants: List[Dict[str, str]]
    message_count: int
    last_message: datetime
    last_message_preview: str
    unread_count: int
    tags: List[str] = []


class Message(BaseSchema):
    """Individual message."""
    message_id: UUID
    thread_id: UUID
    sender: Dict[str, str]
    content: str
    timestamp: datetime
    message_type: str = "text"  # "text", "file", "system"
    attachments: List[Dict[str, str]] = []
    read_by: List[Dict[str, datetime]] = []


# Document schemas
class DocumentOCRResult(BaseSchema):
    """OCR document processing result."""
    document_id: UUID
    confidence_score: float
    extracted_text: str
    entities: List[Dict[str, Any]] = []
    processed_data: Dict[str, Any] = {}
    processing_time: float


class DocumentIntelligence(BaseSchema):
    """Document intelligence analysis."""
    document_type: str
    key_fields: Dict[str, str]
    validation_status: str
    confidence_scores: Dict[str, float]
    suggestions: List[str] = []


# Automation schemas
class WorkflowDefinition(BaseSchema):
    """Workflow automation definition."""
    workflow_id: UUID
    name: str
    description: str
    trigger_type: str  # "schedule", "event", "manual"
    steps: List[Dict[str, Any]]
    is_active: bool
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None


class WorkflowExecution(BaseSchema):
    """Workflow execution result."""
    execution_id: UUID
    workflow_id: UUID
    status: str  # "running", "completed", "failed", "cancelled"
    started_at: datetime
    completed_at: Optional[datetime] = None
    steps_completed: int
    total_steps: int
    logs: List[Dict[str, Any]] = []


# AI prediction schemas
class PredictionRequest(BaseSchema):
    """AI prediction request."""
    model_type: str  # "success_prediction", "risk_assessment", "grade_prediction"
    input_data: Dict[str, Any]
    confidence_threshold: float = 0.5


class PredictionResult(BaseSchema):
    """AI prediction result."""
    prediction: Union[float, str, Dict[str, Any]]
    confidence: float
    model_version: str
    features_used: List[str]
    explanation: Optional[str] = None
    recommendations: List[str] = []


# Export all schemas
__all__ = [
    # Base
    "BaseSchema",
    # System
    "HealthResponse",
    "ApiInfoResponse",
    # Pagination
    "PaginationMeta",
    "PaginatedResponse",
    # Search
    "DateRangeFilter",
    "SearchFilters",
    "SortOption",
    # Analytics
    "MetricValue",
    "DashboardMetrics",
    "TimeSeriesPoint",
    "ChartData",
    # Students
    "StudentBasicInfo",
    "StudentSearchResult",
    "StudentAnalytics",
    "StudentDetailedInfo",
    "PhotoUploadResponse",
    "TimelineEvent",
    "RiskScoreResponse",
    "SuccessPredictionResponse",
    # Bulk operations
    "BulkActionRequest",
    "BulkActionResult",
    # Academic
    "GradeEntry",
    "GradeSpreadsheetData",
    "ScheduleConflict",
    # Financial
    "POSTransaction",
    "FinancialAnalytics",
    # Communication
    "MessageThread",
    "Message",
    # Documents
    "DocumentOCRResult",
    "DocumentIntelligence",
    # Automation
    "WorkflowDefinition",
    "WorkflowExecution",
    # AI
    "PredictionRequest",
    "PredictionResult",
]