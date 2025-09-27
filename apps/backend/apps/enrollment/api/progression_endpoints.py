"""API endpoints for academic progression tracking.

Provides high-performance queries for student progression analytics,
completion statistics, and certificate tracking using the AcademicProgression
denormalized view for optimal performance.
"""

from datetime import date
from decimal import Decimal

from django.db.models import Avg, Count, Max, Min, Q
from ninja import Query, Router
from ninja.errors import HttpError
from ninja.pagination import paginate
from pydantic import BaseModel

from apps.common.api import CursorPagination
from apps.enrollment.models_progression import (
    AcademicProgression,
    CertificateIssuance,
)

router = Router(tags=["Academic Progression"])


# Schemas
class ProgressionSummarySchema(BaseModel):
    """Summary statistics for academic progression."""

    total_students: int
    active_students: int
    graduated_students: int
    dropped_students: int

    # Time metrics
    avg_time_to_ba_days: float | None = None
    avg_time_to_ma_days: float | None = None
    avg_terms_to_complete: float | None = None

    # Completion rates
    ba_completion_rate: float
    ma_completion_rate: float
    language_completion_rate: float

    # Dropout analysis
    language_dropout_rate: float
    ba_dropout_rate: float
    dropout_by_level: dict[str, int]


class StudentProgressionSchema(BaseModel):
    """Student academic progression summary."""

    student_id: int
    student_name: str
    student_id_number: str
    current_status: str

    # Entry information
    entry_program: str
    entry_date: date
    entry_term: str

    # Language program
    language_start_date: date | None = None
    language_end_date: date | None = None
    language_terms: int
    language_final_level: str
    language_completion_status: str

    # BA program
    ba_start_date: date | None = None
    ba_major: str
    ba_terms: int
    ba_credits: Decimal
    ba_gpa: Decimal | None = None
    ba_completion_date: date | None = None
    ba_completion_status: str

    # MA program
    ma_start_date: date | None = None
    ma_program: str
    ma_terms: int
    ma_credits: Decimal
    ma_gpa: Decimal | None = None
    ma_completion_date: date | None = None
    ma_completion_status: str

    # Overall metrics
    total_terms: int
    total_gap_terms: int
    time_to_ba_days: int | None = None
    time_to_ma_days: int | None = None
    last_enrollment_term: str


class DroppedStudentSchema(BaseModel):
    """Dropped student information."""

    student_id: int
    student_name: str
    program_type: str
    program_name: str | None = None
    last_level: str | None = None
    last_enrollment_date: date | None = None
    terms_before_drop: int


class CertificateSchema(BaseModel):
    """Certificate issuance information."""

    certificate_number: str
    student_id: int
    student_name: str
    certificate_type: str
    program: str | None = None
    issue_date: date
    collected: bool
    gpa: Decimal | None = None


class ProgramCompletionTimeSchema(BaseModel):
    """Average completion times by program."""

    program: str
    program_type: str
    student_count: int
    avg_days_to_complete: float
    avg_terms_to_complete: float
    min_days: int
    max_days: int


# Endpoints
@router.get("/summary", response=ProgressionSummarySchema)
def get_progression_summary(
    request,
    program: str | None = Query(None, description="Filter by program name"),
    status: str | None = Query(None, description="Filter by journey status"),
    start_date: date | None = Query(None, description="Filter by start date after"),
    end_date: date | None = Query(None, description="Filter by start date before"),
) -> ProgressionSummarySchema:
    """Get summary statistics for academic progression.

    This endpoint provides high-level analytics about student progression
    through programs, including completion rates and time metrics.
    """
    # Base queryset
    queryset = AcademicProgression.objects.all()

    # Apply filters
    if program:
        queryset = queryset.filter(Q(ba_major__icontains=program) | Q(ma_program__icontains=program))
    if status:
        queryset = queryset.filter(current_status=status)
    if start_date:
        queryset = queryset.filter(entry_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(entry_date__lte=end_date)

    # Calculate statistics
    total = queryset.count()
    active = queryset.filter(current_status="ACTIVE").count()
    graduated = queryset.filter(Q(ba_completion_status="GRADUATED") | Q(ma_completion_status="GRADUATED")).count()
    dropped = queryset.filter(current_status="DROPPED").count()

    # Time metrics
    ba_times = queryset.filter(ba_completion_status="GRADUATED", time_to_ba_days__isnull=False).aggregate(
        avg=Avg("time_to_ba_days")
    )

    ma_times = queryset.filter(ma_completion_status="GRADUATED", time_to_ma_days__isnull=False).aggregate(
        avg=Avg("time_to_ma_days")
    )

    avg_terms = queryset.filter(Q(ba_completion_status="GRADUATED") | Q(ma_completion_status="GRADUATED")).aggregate(
        avg=Avg("total_terms")
    )

    # Completion rates
    ba_students = queryset.filter(ba_start_date__isnull=False).count()
    ba_completed = queryset.filter(ba_completion_status="GRADUATED").count()
    ba_completion_rate = (ba_completed / ba_students * 100) if ba_students > 0 else 0

    ma_students = queryset.filter(ma_start_date__isnull=False).count()
    ma_completed = queryset.filter(ma_completion_status="GRADUATED").count()
    ma_completion_rate = (ma_completed / ma_students * 100) if ma_students > 0 else 0

    lang_students = queryset.filter(language_start_date__isnull=False).count()
    lang_completed = queryset.filter(language_completion_status="COMPLETED").count()
    language_completion_rate = (lang_completed / lang_students * 100) if lang_students > 0 else 0

    # Dropout analysis
    lang_dropped = queryset.filter(language_completion_status="DROPPED").count()
    language_dropout_rate = (lang_dropped / lang_students * 100) if lang_students > 0 else 0

    ba_dropped = queryset.filter(ba_completion_status="DROPPED").count()
    ba_dropout_rate = (ba_dropped / ba_students * 100) if ba_students > 0 else 0

    # Dropout by level
    dropout_by_level = {}
    for level in range(1, 13):  # Language levels 1-12
        count = queryset.filter(language_completion_status="DROPPED", language_final_level=str(level)).count()
        if count > 0:
            dropout_by_level[f"Level {level}"] = count

    return ProgressionSummarySchema(
        total_students=total,
        active_students=active,
        graduated_students=graduated,
        dropped_students=dropped,
        avg_time_to_ba_days=ba_times["avg"],
        avg_time_to_ma_days=ma_times["avg"],
        avg_terms_to_complete=avg_terms["avg"],
        ba_completion_rate=round(ba_completion_rate, 2),
        ma_completion_rate=round(ma_completion_rate, 2),
        language_completion_rate=round(language_completion_rate, 2),
        language_dropout_rate=round(language_dropout_rate, 2),
        ba_dropout_rate=round(ba_dropout_rate, 2),
        dropout_by_level=dropout_by_level,
    )


@router.get("/students", response=list[StudentProgressionSchema])
@paginate(CursorPagination)
def list_student_progressions(
    request,
    status: str | None = Query(None, description="Filter by current status"),
    ba_major: str | None = Query(None, description="Filter by BA major"),
    ma_program: str | None = Query(None, description="Filter by MA program"),
    entry_program: str | None = Query(None, description="Filter by entry program"),
) -> list[StudentProgressionSchema]:
    """List student academic progressions with filtering.

    Returns paginated list of student progressions with their complete
    academic history and current status.
    """
    queryset = AcademicProgression.objects.select_related("student__person").order_by("-last_updated")

    # Apply filters
    if status:
        queryset = queryset.filter(current_status__icontains=status)
    if ba_major:
        queryset = queryset.filter(ba_major__icontains=ba_major)
    if ma_program:
        queryset = queryset.filter(ma_program__icontains=ma_program)
    if entry_program:
        queryset = queryset.filter(entry_program__icontains=entry_program)

    results = []
    for progression in queryset:
        results.append(
            StudentProgressionSchema(
                student_id=progression.student.id,
                student_name=progression.student_name,
                student_id_number=progression.student_id_number,
                current_status=progression.current_status,
                entry_program=progression.entry_program,
                entry_date=progression.entry_date,
                entry_term=progression.entry_term,
                language_start_date=progression.language_start_date,
                language_end_date=progression.language_end_date,
                language_terms=progression.language_terms,
                language_final_level=progression.language_final_level,
                language_completion_status=progression.language_completion_status,
                ba_start_date=progression.ba_start_date,
                ba_major=progression.ba_major,
                ba_terms=progression.ba_terms,
                ba_credits=progression.ba_credits,
                ba_gpa=progression.ba_gpa,
                ba_completion_date=progression.ba_completion_date,
                ba_completion_status=progression.ba_completion_status,
                ma_start_date=progression.ma_start_date,
                ma_program=progression.ma_program,
                ma_terms=progression.ma_terms,
                ma_credits=progression.ma_credits,
                ma_gpa=progression.ma_gpa,
                ma_completion_date=progression.ma_completion_date,
                ma_completion_status=progression.ma_completion_status,
                total_terms=progression.total_terms,
                total_gap_terms=progression.total_gap_terms,
                time_to_ba_days=progression.time_to_ba_days,
                time_to_ma_days=progression.time_to_ma_days,
                last_enrollment_term=progression.last_enrollment_term,
            )
        )

    return results


@router.get("/dropouts", response=list[DroppedStudentSchema])
def get_dropout_analysis(
    request,
    program: str | None = Query(None, description="Filter by program"),
    level: str | None = Query(None, description="Filter by dropout level"),
    min_terms: int | None = Query(None, description="Minimum terms before dropout"),
) -> list[DroppedStudentSchema]:
    """Analyze student dropouts by program and level.

    Returns detailed information about students who dropped out,
    including where in their journey they left.
    """
    # Query dropped students
    queryset = AcademicProgression.objects.filter(
        Q(language_completion_status="DROPPED") | Q(ba_completion_status="DROPPED") | Q(ma_completion_status="DROPPED")
    ).select_related("student__person")

    # Apply filters
    if program:
        queryset = queryset.filter(Q(ba_major__icontains=program) | Q(ma_program__icontains=program))
    if level:
        queryset = queryset.filter(language_final_level=level)

    results = []
    for prog in queryset[:100]:  # Limit to 100 for performance
        # Determine dropout details
        if prog.language_completion_status == "DROPPED":
            program_type = "Language"
            program_name = "Language Program"
            last_level = prog.language_final_level
            last_date = prog.language_end_date or prog.language_start_date
            terms = prog.language_terms
        elif prog.ba_completion_status == "DROPPED":
            program_type = "BA"
            program_name = prog.ba_major
            last_level = None
            last_date = prog.ba_start_date
            terms = prog.ba_terms
        else:  # MA dropout
            program_type = "MA"
            program_name = prog.ma_program
            last_level = None
            last_date = prog.ma_start_date
            terms = prog.ma_terms

        if min_terms and terms < min_terms:
            continue

        results.append(
            DroppedStudentSchema(
                student_id=prog.student.id,
                student_name=prog.student_name,
                program_type=program_type,
                program_name=program_name,
                last_level=last_level,
                last_enrollment_date=last_date,
                terms_before_drop=terms,
            )
        )

    return results


@router.get("/completion-times", response=list[ProgramCompletionTimeSchema])
def get_completion_times_by_program(request) -> list[ProgramCompletionTimeSchema]:
    """Get average completion times for each program.

    Returns statistics on how long it takes students to complete
    different programs.
    """
    results = []

    # BA Programs
    ba_stats = (
        AcademicProgression.objects.filter(ba_completion_status="GRADUATED", time_to_ba_days__isnull=False)
        .values("ba_major")
        .annotate(
            count=Count("student"),
            avg_days=Avg("time_to_ba_days"),
            avg_terms=Avg("ba_terms"),
            min_days=Min("time_to_ba_days"),
            max_days=Max("time_to_ba_days"),
        )
    )

    for stat in ba_stats:
        if stat["ba_major"]:
            results.append(
                ProgramCompletionTimeSchema(
                    program=stat["ba_major"],
                    program_type="BA",
                    student_count=stat["count"],
                    avg_days_to_complete=round(stat["avg_days"], 1),
                    avg_terms_to_complete=round(stat["avg_terms"], 1),
                    min_days=stat["min_days"],
                    max_days=stat["max_days"],
                )
            )

    # MA Programs
    ma_stats = (
        AcademicProgression.objects.filter(ma_completion_status="GRADUATED", time_to_ma_days__isnull=False)
        .values("ma_program")
        .annotate(
            count=Count("student"),
            avg_days=Avg("time_to_ma_days"),
            avg_terms=Avg("ma_terms"),
            min_days=Min("time_to_ma_days"),
            max_days=Max("time_to_ma_days"),
        )
    )

    for stat in ma_stats:
        if stat["ma_program"]:
            results.append(
                ProgramCompletionTimeSchema(
                    program=stat["ma_program"],
                    program_type="MA",
                    student_count=stat["count"],
                    avg_days_to_complete=round(stat["avg_days"], 1),
                    avg_terms_to_complete=round(stat["avg_terms"], 1),
                    min_days=stat["min_days"],
                    max_days=stat["max_days"],
                )
            )

    # Sort by program type and name
    results.sort(key=lambda x: (x.program_type, x.program))

    return results


@router.get("/certificates", response=list[CertificateSchema])
@paginate(CursorPagination)
def list_certificates(
    request,
    certificate_type: str | None = Query(None, description="Filter by certificate type"),
    collected: bool | None = Query(None, description="Filter by collection status"),
    start_date: date | None = Query(None, description="Issue date after"),
    end_date: date | None = Query(None, description="Issue date before"),
) -> list[CertificateSchema]:
    """List issued certificates with filtering.

    Returns paginated list of certificates issued to students.
    """
    queryset = CertificateIssuance.objects.select_related("student__person", "program").order_by("-issue_date")

    # Apply filters
    if certificate_type:
        queryset = queryset.filter(certificate_type=certificate_type)
    if collected is not None:
        if collected:
            queryset = queryset.filter(collected_date__isnull=False)
        else:
            queryset = queryset.filter(collected_date__isnull=True)
    if start_date:
        queryset = queryset.filter(issue_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(issue_date__lte=end_date)

    results = []
    for cert in queryset:
        results.append(
            CertificateSchema(
                certificate_number=cert.certificate_number,
                student_id=cert.student.id,
                student_name=cert.student.person.full_name,
                certificate_type=cert.get_certificate_type_display(),
                program=cert.program.name if cert.program else None,
                issue_date=cert.issue_date,
                collected=cert.is_collected,
                gpa=cert.gpa,
            )
        )

    return results


@router.get("/student/{student_id}/progression", response=StudentProgressionSchema)
def get_student_progression(request, student_id: int) -> StudentProgressionSchema:
    """Get detailed progression information for a specific student.

    Returns comprehensive progression data including all programs
    and completion status.
    """
    try:
        progression = AcademicProgression.objects.select_related("student__person").get(student_id=student_id)
    except AcademicProgression.DoesNotExist as err:
        raise HttpError(404, "Student progression not found") from err

    return StudentProgressionSchema(
        student_id=progression.student.id,
        student_name=progression.student_name,
        student_id_number=progression.student_id_number,
        current_status=progression.current_status,
        entry_program=progression.entry_program,
        entry_date=progression.entry_date,
        entry_term=progression.entry_term,
        language_start_date=progression.language_start_date,
        language_end_date=progression.language_end_date,
        language_terms=progression.language_terms,
        language_final_level=progression.language_final_level,
        language_completion_status=progression.language_completion_status,
        ba_start_date=progression.ba_start_date,
        ba_major=progression.ba_major,
        ba_terms=progression.ba_terms,
        ba_credits=progression.ba_credits,
        ba_gpa=progression.ba_gpa,
        ba_completion_date=progression.ba_completion_date,
        ba_completion_status=progression.ba_completion_status,
        ma_start_date=progression.ma_start_date,
        ma_program=progression.ma_program,
        ma_terms=progression.ma_terms,
        ma_credits=progression.ma_credits,
        ma_gpa=progression.ma_gpa,
        ma_completion_date=progression.ma_completion_date,
        ma_completion_status=progression.ma_completion_status,
        total_terms=progression.total_terms,
        total_gap_terms=progression.total_gap_terms,
        time_to_ba_days=progression.time_to_ba_days,
        time_to_ma_days=progression.time_to_ma_days,
        last_enrollment_term=progression.last_enrollment_term,
    )
