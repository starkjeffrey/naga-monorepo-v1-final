"""Student-related GraphQL queries."""

import strawberry
from typing import List, Optional
from django.core.cache import cache
from django.db.models import Q, Prefetch

from apps.people.models import StudentProfile, Person
from apps.enrollment.models import ClassHeaderEnrollment

from ..types.student import (
    StudentType,
    StudentConnection,
    StudentSearchFilters,
    PersonType,
    StudentAnalytics,
    EnrollmentInfo,
    PaymentInfo,
    TimelineEvent
)
from ..types.common import PaginationInput


def convert_student_to_graphql(student: StudentProfile) -> StudentType:
    """Convert Django model to GraphQL type."""

    # Convert person
    person = PersonType(
        unique_id=str(student.person.unique_id),
        full_name=student.person.full_name,
        family_name=student.person.family_name,
        personal_name=student.person.personal_name,
        khmer_name=student.person.khmer_name,
        school_email=student.person.school_email,
        personal_email=student.person.personal_email,
        date_of_birth=student.person.date_of_birth,
        preferred_gender=student.person.preferred_gender
    )

    # Get enrollments
    enrollments = []
    for enrollment in student.enrollments.all()[:10]:  # Limit to recent 10
        enrollments.append(EnrollmentInfo(
            unique_id=str(enrollment.unique_id),
            course_code=enrollment.class_header.course.code,
            course_name=enrollment.class_header.course.name,
            term=enrollment.class_header.term.name if enrollment.class_header.term else None,
            status=enrollment.status,
            enrolled_date=enrollment.created_at
        ))

    # Get payments (mock for now)
    payments = []

    # Get timeline (mock for now)
    timeline = []

    # Get analytics (simplified)
    analytics = StudentAnalytics(
        success_prediction=0.85,
        risk_factors=["low_attendance"] if student.status == "at_risk" else [],
        performance_trend="stable",
        attendance_rate=0.87,
        grade_average=3.2,
        payment_status="current",
        engagement_score=0.75
    )

    return StudentType(
        unique_id=str(student.unique_id),
        student_id=student.student_id,
        person=person,
        program=student.current_program.name if student.current_program else None,
        level=student.current_level,
        status=student.status,
        photo_url=None,  # TODO: Get from photos
        analytics=analytics,
        enrollments=enrollments,
        payments=payments,
        timeline=timeline,
        enrollment_count=len(enrollments),
        last_activity=student.last_modified
    )


@strawberry.type
class StudentQueries:
    """Student-related GraphQL queries."""

    @strawberry.field
    def student(self, info, student_id: strawberry.ID) -> Optional[StudentType]:
        """Get a single student by ID."""
        try:
            student = StudentProfile.objects.select_related(
                'person', 'current_program'
            ).prefetch_related(
                Prefetch(
                    'enrollments',
                    queryset=ClassHeaderEnrollment.objects.select_related(
                        'class_header__course', 'class_header__term'
                    )
                )
            ).get(unique_id=student_id)

            return convert_student_to_graphql(student)
        except StudentProfile.DoesNotExist:
            return None

    @strawberry.field
    def students(
        self,
        info,
        filters: Optional[StudentSearchFilters] = None,
        pagination: Optional[PaginationInput] = None
    ) -> StudentConnection:
        """Search and list students with advanced filtering."""

        # Base query
        queryset = StudentProfile.objects.select_related(
            'person', 'current_program'
        ).prefetch_related(
            Prefetch(
                'enrollments',
                queryset=ClassHeaderEnrollment.objects.select_related(
                    'class_header__course'
                )
            )
        )

        # Apply filters
        if filters:
            if filters.query:
                search_query = filters.query.strip()
                if filters.fuzzy_search:
                    # Fuzzy search
                    q_objects = Q()
                    for term in search_query.split():
                        q_objects |= (
                            Q(person__family_name__icontains=term) |
                            Q(person__personal_name__icontains=term) |
                            Q(student_id__icontains=term) |
                            Q(person__school_email__icontains=term)
                        )
                    queryset = queryset.filter(q_objects)
                else:
                    # Exact search
                    queryset = queryset.filter(
                        Q(person__family_name__icontains=search_query) |
                        Q(person__personal_name__icontains=search_query) |
                        Q(student_id__icontains=search_query) |
                        Q(person__school_email__icontains=search_query)
                    )

            if filters.statuses:
                queryset = queryset.filter(status__in=filters.statuses)

            if filters.program_ids:
                queryset = queryset.filter(current_program__unique_id__in=filters.program_ids)

            if filters.levels:
                queryset = queryset.filter(current_level__in=filters.levels)

        # Apply pagination
        page_size = 25
        if pagination and pagination.first:
            page_size = min(pagination.first, 100)

        # For simplicity, using basic pagination here
        # In production, implement proper cursor-based pagination
        total_count = queryset.count()
        students = list(queryset[:page_size])

        # Convert to GraphQL types
        from ..types.student import StudentEdge, StudentPageInfo

        edges = []
        for i, student in enumerate(students):
            edges.append(StudentEdge(
                node=convert_student_to_graphql(student),
                cursor=str(i)  # Simple cursor implementation
            ))

        page_info = StudentPageInfo(
            has_next_page=len(students) >= page_size,
            has_previous_page=False,  # Simplified
            start_cursor="0" if edges else None,
            end_cursor=str(len(edges) - 1) if edges else None
        )

        return StudentConnection(
            edges=edges,
            page_info=page_info,
            total_count=total_count
        )

    @strawberry.field
    def student_analytics(self, info, student_id: strawberry.ID) -> Optional[StudentAnalytics]:
        """Get detailed analytics for a specific student."""
        cache_key = f"student_analytics_{student_id}"
        cached = cache.get(cache_key)

        if cached:
            return StudentAnalytics(**cached)

        try:
            student = StudentProfile.objects.get(unique_id=student_id)

            # Calculate analytics (simplified version)
            analytics = StudentAnalytics(
                success_prediction=0.85,
                risk_factors=["low_attendance"] if student.status == "at_risk" else [],
                performance_trend="stable",
                attendance_rate=0.87,
                grade_average=3.2,
                payment_status="current",
                engagement_score=0.75
            )

            # Cache for 15 minutes
            cache.set(cache_key, {
                "success_prediction": analytics.success_prediction,
                "risk_factors": analytics.risk_factors,
                "performance_trend": analytics.performance_trend,
                "attendance_rate": analytics.attendance_rate,
                "grade_average": analytics.grade_average,
                "payment_status": analytics.payment_status,
                "engagement_score": analytics.engagement_score
            }, 900)

            return analytics

        except StudentProfile.DoesNotExist:
            return None

    @strawberry.field
    def student_timeline(
        self,
        info,
        student_id: strawberry.ID,
        event_types: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[TimelineEvent]:
        """Get student activity timeline."""

        try:
            student = StudentProfile.objects.get(unique_id=student_id)

            # Mock timeline events
            timeline = [
                TimelineEvent(
                    event_type="enrollment",
                    description=f"Enrolled in MATH101 - Calculus I",
                    timestamp=student.created_at
                ),
                TimelineEvent(
                    event_type="payment",
                    description="Payment of $1,500 received",
                    timestamp=student.created_at
                )
            ]

            # Filter by event types if specified
            if event_types:
                timeline = [event for event in timeline if event.event_type in event_types]

            return timeline[:limit]

        except StudentProfile.DoesNotExist:
            return []