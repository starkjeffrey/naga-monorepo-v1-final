"""Curriculum API endpoints for managing academic structure and courses.

This module provides RESTful API endpoints for React queries to access and
manage curriculum data including divisions, cycles, majors, terms, courses,
and academic structure information.
"""


from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from ninja import Query, Router

from apps.curriculum.models import (
    Course,
    Cycle,
    Division,
    Major,
    Term,
)

from .auth import jwt_auth
from .curriculum_schemas import (
    AcademicStructureSchema,
    CourseDetailSchema,
    CurriculumStatsSchema,
    CycleSchema,
    DivisionSchema,
    MajorSchema,
    PaginatedCoursesSchema,
    PaginatedMajorsSchema,
    PaginatedTermsSchema,
    TermSchema,
)

router = Router(auth=jwt_auth, tags=["curriculum"])


# Helper serialization functions
def serialize_division(division) -> dict:
    """Serialize division."""
    return {
        "id": division.id,
        "name": division.name,
        "short_name": division.short_name,
        "description": division.description,
        "is_active": division.is_active,
        "display_order": division.display_order,
    }


def serialize_cycle(cycle) -> dict:
    """Serialize cycle."""
    return {
        "id": cycle.id,
        "name": cycle.name,
        "short_name": cycle.short_name,
        "description": cycle.description,
        "division": serialize_division(cycle.division),
        "level_order": cycle.level_order,
        "is_active": cycle.is_active,
    }


def serialize_major(major) -> dict:
    """Serialize major."""
    return {
        "id": major.id,
        "name": major.name,
        "short_name": major.short_name,
        "description": major.description,
        "program_type": major.program_type,
        "degree_type": major.degree_type,
        "division": serialize_division(major.division),
        "cycle": serialize_cycle(major.cycle),
        "required_credits": major.required_credits,
        "max_terms": major.max_terms,
        "is_active": major.is_active,
        "is_accepting_students": major.is_accepting_students,
        "display_order": major.display_order,
    }


def serialize_term(term) -> dict:
    """Serialize term."""
    return {
        "id": term.id,
        "name": term.name,
        "short_name": term.short_name,
        "start_date": term.start_date,
        "end_date": term.end_date,
        "term_type": term.term_type,
        "academic_year": term.academic_year,
        "is_current": term.is_current,
        "is_registration_open": term.is_registration_open,
        "cohort_year": term.cohort_year,
    }


def serialize_course(course) -> dict:
    """Serialize course."""
    return {
        "id": course.id,
        "code": course.code,
        "name": course.name,
        "description": course.description,
        "credit_hours": course.credit_hours,
        "level": course.level,
        "course_type": course.course_type,
        "division": serialize_division(course.division),
        "is_active": course.is_active,
        "can_repeat": course.can_repeat,
    }


# Division endpoints
@router.get("/divisions/", response=list[DivisionSchema])
def list_divisions(request, active_only: bool = Query(True, description="Show only active divisions")):
    """List all divisions."""
    queryset = Division.objects.all()

    if active_only:
        queryset = queryset.filter(is_active=True)

    queryset = queryset.order_by("display_order", "name")

    return [serialize_division(division) for division in queryset]


@router.get("/divisions/{division_id}/", response=DivisionSchema)
def get_division(request, division_id: int):
    """Get specific division."""
    division = get_object_or_404(Division, id=division_id)
    return serialize_division(division)


# Cycle endpoints
@router.get("/cycles/", response=list[CycleSchema])
def list_cycles(
    request,
    division_id: int | None = Query(None, description="Filter by division"),
    active_only: bool = Query(True, description="Show only active cycles"),
):
    """List cycles with optional division filtering."""
    queryset = Cycle.objects.select_related("division")

    if division_id:
        queryset = queryset.filter(division_id=division_id)

    if active_only:
        queryset = queryset.filter(is_active=True)

    queryset = queryset.order_by("division__display_order", "level_order", "name")

    return [serialize_cycle(cycle) for cycle in queryset]


@router.get("/cycles/{cycle_id}/", response=CycleSchema)
def get_cycle(request, cycle_id: int):
    """Get specific cycle."""
    cycle = get_object_or_404(Cycle.objects.select_related("division"), id=cycle_id)
    return serialize_cycle(cycle)


# Major endpoints
@router.get("/majors/", response=PaginatedMajorsSchema)
def list_majors(
    request,
    division_id: int | None = Query(None, description="Filter by division"),
    cycle_id: int | None = Query(None, description="Filter by cycle"),
    program_type: str | None = Query(None, description="Filter by program type"),
    active_only: bool = Query(True, description="Show only active majors"),
    accepting_students: bool = Query(False, description="Show only majors accepting students"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """List majors with filtering and pagination."""
    queryset = Major.objects.select_related("division", "cycle").annotate(
        student_count=Count("programenrollment", filter=Q(programenrollment__is_active=True))
    )

    if division_id:
        queryset = queryset.filter(division_id=division_id)

    if cycle_id:
        queryset = queryset.filter(cycle_id=cycle_id)

    if program_type:
        queryset = queryset.filter(program_type=program_type)

    if active_only:
        queryset = queryset.filter(is_active=True)

    if accepting_students:
        queryset = queryset.filter(is_accepting_students=True)

    queryset = queryset.order_by("division__display_order", "cycle__level_order", "display_order", "name")

    # Paginate
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    results = []
    for major in page_obj:
        results.append(
            {
                "id": major.id,
                "name": major.name,
                "short_name": major.short_name,
                "program_type": major.program_type,
                "degree_type": major.degree_type,
                "division_name": major.division.name,
                "cycle_name": major.cycle.name,
                "is_active": major.is_active,
                "is_accepting_students": major.is_accepting_students,
                "student_count": major.student_count,
            }
        )

    return {"count": paginator.count, "next": None, "previous": None, "results": results}


@router.get("/majors/{major_id}/", response=MajorSchema)
def get_major(request, major_id: int):
    """Get specific major."""
    major = get_object_or_404(Major.objects.select_related("division", "cycle"), id=major_id)
    return serialize_major(major)


# Term endpoints
@router.get("/terms/", response=PaginatedTermsSchema)
def list_terms(
    request,
    academic_year: int | None = Query(None, description="Filter by academic year"),
    term_type: str | None = Query(None, description="Filter by term type"),
    current_only: bool = Query(False, description="Show only current term"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List terms with filtering and pagination."""
    queryset = Term.objects.annotate(
        enrollment_count=Count("classheader__enrollments", filter=Q(classheader__enrollments__status="ENROLLED"))
    )

    if academic_year:
        queryset = queryset.filter(academic_year=academic_year)

    if term_type:
        queryset = queryset.filter(term_type=term_type)

    if current_only:
        queryset = queryset.filter(is_current=True)

    queryset = queryset.order_by("-start_date")

    # Paginate
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    results = []
    for term in page_obj:
        results.append(
            {
                "id": term.id,
                "name": term.name,
                "short_name": term.short_name,
                "start_date": term.start_date,
                "end_date": term.end_date,
                "term_type": term.term_type,
                "academic_year": term.academic_year,
                "is_current": term.is_current,
                "is_registration_open": term.is_registration_open,
                "enrollment_count": term.enrollment_count,
            }
        )

    return {"count": paginator.count, "next": None, "previous": None, "results": results}


@router.get("/terms/{term_id}/", response=TermSchema)
def get_term(request, term_id: int):
    """Get specific term."""
    term = get_object_or_404(Term, id=term_id)
    return serialize_term(term)


@router.get("/terms/current/", response=TermSchema)
def get_current_term(request):
    """Get the current active term."""
    current_term = Term.objects.filter(is_current=True).first()
    if not current_term:
        return {"error": "No current term is set"}, 404
    return serialize_term(current_term)


# Course endpoints
@router.get("/courses/", response=PaginatedCoursesSchema)
def list_courses(
    request,
    division_id: int | None = Query(None, description="Filter by division"),
    course_type: str | None = Query(None, description="Filter by course type"),
    level: int | None = Query(None, description="Filter by level"),
    active_only: bool = Query(True, description="Show only active courses"),
    search: str | None = Query(None, description="Search in code and name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """List courses with filtering and pagination."""
    queryset = Course.objects.select_related("division").annotate(class_count=Count("classheader"))

    if division_id:
        queryset = queryset.filter(division_id=division_id)

    if course_type:
        queryset = queryset.filter(course_type=course_type)

    if level:
        queryset = queryset.filter(level=level)

    if active_only:
        queryset = queryset.filter(is_active=True)

    if search:
        queryset = queryset.filter(Q(code__icontains=search) | Q(name__icontains=search))

    queryset = queryset.order_by("division__display_order", "level", "code")

    # Paginate
    paginator = Paginator(queryset, page_size)
    page_obj = paginator.get_page(page)

    results = []
    for course in page_obj:
        results.append(
            {
                "id": course.id,
                "code": course.code,
                "name": course.name,
                "credit_hours": course.credit_hours,
                "level": course.level,
                "course_type": course.course_type,
                "division_name": course.division.name,
                "is_active": course.is_active,
                "class_count": course.class_count,
            }
        )

    return {"count": paginator.count, "next": None, "previous": None, "results": results}


@router.get("/courses/{course_id}/", response=CourseDetailSchema)
def get_course_detail(request, course_id: int):
    """Get detailed course information including prerequisites."""
    course = get_object_or_404(
        Course.objects.select_related("division").prefetch_related(
            "prerequisites__prerequisite_course", "textbooks", "courseparttemplate_set"
        ),
        id=course_id,
    )

    data = serialize_course(course)

    # Add prerequisites
    data["prerequisites"] = [serialize_course(prereq.prerequisite_course) for prereq in course.prerequisites.all()]

    # Add textbooks
    data["textbooks"] = [
        {
            "id": textbook.id,
            "title": textbook.title,
            "author": textbook.author,
            "publisher": textbook.publisher,
            "isbn": textbook.isbn,
            "edition": textbook.edition,
            "publication_year": textbook.publication_year,
            "is_required": True,  # Assuming all course textbooks are required
        }
        for textbook in course.textbooks.all()
    ]

    # Add part templates (for language courses)
    data["part_templates"] = [
        {
            "id": template.id,
            "part_type": template.part_type,
            "curriculum_weight": float(template.curriculum_weight),
            "is_required": template.is_required,
        }
        for template in course.courseparttemplate_set.all()
    ]

    return data


# Academic structure overview
@router.get("/structure/", response=AcademicStructureSchema)
def get_academic_structure(request):
    """Get complete academic structure overview."""
    divisions = Division.objects.filter(is_active=True).order_by("display_order", "name")

    cycles = (
        Cycle.objects.filter(is_active=True)
        .select_related("division")
        .order_by("division__display_order", "level_order", "name")
    )

    majors = (
        Major.objects.filter(is_active=True)
        .select_related("division", "cycle")
        .order_by("division__display_order", "cycle__level_order", "display_order", "name")
    )

    current_term = Term.objects.filter(is_current=True).first()

    return {
        "divisions": [serialize_division(division) for division in divisions],
        "cycles": [serialize_cycle(cycle) for cycle in cycles],
        "majors": [serialize_major(major) for major in majors],
        "current_term": serialize_term(current_term) if current_term else None,
    }


# Statistics
@router.get("/statistics/", response=CurriculumStatsSchema)
def get_curriculum_statistics(request):
    """Get curriculum statistics overview."""
    total_majors = Major.objects.count()
    active_majors = Major.objects.filter(is_active=True).count()

    total_courses = Course.objects.count()
    active_courses = Course.objects.filter(is_active=True).count()

    total_terms = Term.objects.count()

    current_term = Term.objects.filter(is_current=True).first()
    current_term_id = current_term.id if current_term else None

    # Division breakdown
    division_breakdown = {}
    for division, count in (
        Major.objects.filter(is_active=True).values_list("division__name").annotate(count=Count("id"))
    ):
        division_breakdown[division] = count

    # Program type breakdown
    program_type_breakdown = {}
    for program_type, count in (
        Major.objects.filter(is_active=True).values_list("program_type").annotate(count=Count("id"))
    ):
        program_type_breakdown[program_type] = count

    # Course type breakdown
    course_type_breakdown = {}
    for course_type, count in (
        Course.objects.filter(is_active=True).values_list("course_type").annotate(count=Count("id"))
    ):
        course_type_breakdown[course_type] = count

    return {
        "total_majors": total_majors,
        "active_majors": active_majors,
        "total_courses": total_courses,
        "active_courses": active_courses,
        "total_terms": total_terms,
        "current_term_id": current_term_id,
        "division_breakdown": division_breakdown,
        "program_type_breakdown": program_type_breakdown,
        "course_type_breakdown": course_type_breakdown,
    }


# Utility endpoints for React dropdowns
@router.get("/program-types/", response=list[dict])
def get_program_types(request):
    """Get program type choices."""
    from apps.curriculum.models import Major

    return [{"value": choice[0], "label": choice[1]} for choice in Major.ProgramType.choices]


@router.get("/degree-types/", response=list[dict])
def get_degree_types(request):
    """Get degree type choices."""
    from apps.curriculum.models import Major

    return [{"value": choice[0], "label": choice[1]} for choice in Major.DegreeType.choices]


@router.get("/course-types/", response=list[dict])
def get_course_types(request):
    """Get course type choices."""
    from apps.curriculum.models import Course

    return [{"value": choice[0], "label": choice[1]} for choice in Course.CourseType.choices]


@router.get("/term-types/", response=list[dict])
def get_term_types(request):
    """Get term type choices."""
    from apps.curriculum.models import Term

    return [{"value": choice[0], "label": choice[1]} for choice in Term.TermType.choices]
