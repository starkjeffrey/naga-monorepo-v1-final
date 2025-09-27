"""Academic-related GraphQL types."""

from typing import List, Optional
import strawberry
from datetime import datetime, date

from .common import TimeSeriesPoint


@strawberry.type
class CourseType:
    """Course information."""
    unique_id: strawberry.ID
    code: str
    name: str
    description: Optional[str] = None
    credit_hours: Optional[int] = None
    department: Optional[str] = None
    level: Optional[str] = None


@strawberry.type
class AssignmentType:
    """Assignment information."""
    unique_id: strawberry.ID
    name: str
    assignment_type: str
    max_score: float
    weight: float
    due_date: Optional[datetime] = None
    is_published: bool
    course: CourseType


@strawberry.type
class GradeType:
    """Grade information."""
    unique_id: strawberry.ID
    score: Optional[float] = None
    letter_grade: Optional[str] = None
    assignment: AssignmentType
    student_id: strawberry.ID
    entered_by: Optional[str] = None
    entered_at: datetime
    notes: Optional[str] = None


@strawberry.type
class ClassHeaderType:
    """Class header information."""
    unique_id: strawberry.ID
    course: CourseType
    instructor: Optional[str] = None
    term: Optional[str] = None
    capacity: Optional[int] = None
    enrolled_count: int
    status: str


@strawberry.type
class GradeSpreadsheetRow:
    """Grade spreadsheet row for a student."""
    student_id: strawberry.ID
    student_name: str
    grades: List[Optional[float]]  # Corresponds to assignments


@strawberry.type
class GradeSpreadsheetData:
    """Grade spreadsheet data for a class."""
    class_header: ClassHeaderType
    assignments: List[AssignmentType]
    rows: List[GradeSpreadsheetRow]
    completion_rate: float
    last_modified: datetime


@strawberry.type
class ScheduleConflict:
    """Schedule conflict information."""
    conflict_type: str  # "time_overlap", "resource_conflict", "capacity_exceeded"
    severity: str  # "critical", "warning", "info"
    message: str
    affected_classes: List[ClassHeaderType]
    suggestions: List[str]


@strawberry.type
class PrerequisiteChain:
    """Course prerequisite chain."""
    course: CourseType
    prerequisites: List["PrerequisiteChain"]
    is_circular: bool = False


@strawberry.type
class TranscriptCourse:
    """Course entry in transcript."""
    course_code: str
    course_name: str
    credits: int
    grade: str
    grade_points: float
    term: str


@strawberry.type
class TranscriptData:
    """Student transcript data."""
    student_id: strawberry.ID
    student_name: str
    program: str
    courses: List[TranscriptCourse]
    total_credits: int
    gpa: float
    academic_standing: str
    generated_date: datetime


@strawberry.type
class AttendanceRecord:
    """Attendance record."""
    unique_id: strawberry.ID
    student_id: strawberry.ID
    class_header: ClassHeaderType
    date: date
    status: str  # "present", "absent", "late", "excused"
    scan_location: Optional[str] = None
    scan_timestamp: Optional[datetime] = None


@strawberry.type
class AcademicMetrics:
    """Academic-related metrics."""
    grades_entered: int
    transcripts_pending: int
    attendance_rate: float
    average_class_size: float
    course_completion_rate: float


@strawberry.input
class GradeUpdateInput:
    """Input for updating grades."""
    student_id: strawberry.ID
    assignment_id: strawberry.ID
    score: Optional[float] = None
    notes: Optional[str] = None


@strawberry.input
class BulkGradeUpdateInput:
    """Input for bulk grade updates."""
    class_id: strawberry.ID
    grade_updates: List[GradeUpdateInput]


@strawberry.type
class GradeUpdateResult:
    """Result of grade update operation."""
    success: bool
    message: str
    grade: Optional[GradeType] = None