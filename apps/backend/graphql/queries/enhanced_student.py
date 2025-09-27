"""Enhanced Student GraphQL queries with advanced features."""

import logging
from typing import List, Optional
import strawberry
from datetime import datetime
from django.core.cache import cache
from django.db.models import Q, Prefetch, Count, Avg
from django.shortcuts import get_object_or_404

from apps.people.models import StudentProfile, Person
from apps.enrollment.models import ClassHeaderEnrollment
from apps.grading.models import Grade
from apps.attendance.models import AttendanceRecord
from apps.finance.models import Payment, Invoice

from ..types.enhanced_student import (
    EnhancedStudentType,
    StudentSearchResult,
    AdvancedStudentSearchFilters,
    StudentSortInput,
    TimelineFilterInput,
    RiskAssessment,
    SuccessPrediction,
    AcademicProgress,
    FinancialSummary,
)
from ..types.common import TimeSeriesPoint

logger = logging.getLogger(__name__)


@strawberry.type
class EnhancedStudentQueries:
    """Enhanced student queries with analytics and predictions."""

    @strawberry.field
    def student(self, student_id: strawberry.ID) -> Optional[EnhancedStudentType]:
        """Get a single student with full details."""
        try:
            student = StudentProfile.objects.select_related('person').get(
                unique_id=student_id
            )
            return self._build_enhanced_student(student)
        except StudentProfile.DoesNotExist:
            return None

    @strawberry.field
    def students(
        self,
        filters: Optional[AdvancedStudentSearchFilters] = None,
        sort: Optional[StudentSortInput] = None,
        limit: int = 25,
        offset: int = 0
    ) -> StudentSearchResult:
        """Advanced student search with facets and analytics."""

        start_time = datetime.now()

        # Build base queryset with optimizations
        queryset = StudentProfile.objects.select_related('person').prefetch_related(
            Prefetch(
                'class_header_enrollments',
                queryset=ClassHeaderEnrollment.objects.select_related(
                    'class_header__course',
                    'class_header__term'
                )
            ),
            'program_enrollments__program',
            'emergency_contacts',
        )

        # Apply filters
        if filters:
            queryset = self._apply_filters(queryset, filters)

        # Apply sorting
        if sort:
            order_field = f"{'-' if sort.direction == 'DESC' else ''}{self._get_sort_field(sort.field)}"
            queryset = queryset.order_by(order_field)
        else:
            queryset = queryset.order_by('person__family_name', 'person__personal_name')

        # Get total count before pagination
        total_count = queryset.count()

        # Apply pagination
        paginated_queryset = queryset[offset:offset + limit]

        # Convert to enhanced student types
        students = [
            self._build_enhanced_student(student)
            for student in paginated_queryset
        ]

        # Calculate search time
        search_time = (datetime.now() - start_time).total_seconds() * 1000

        return StudentSearchResult(
            students=students,
            total_count=total_count,
            facets=None,  # TODO: Implement faceting
            aggregations=None,  # TODO: Implement aggregations
            search_time_ms=int(search_time),
            suggestions=[]  # TODO: Implement search suggestions
        )

    @strawberry.field
    def student_risk_assessment(self, student_id: strawberry.ID) -> Optional[RiskAssessment]:
        """Get detailed risk assessment for a student."""
        try:
            student = get_object_or_404(StudentProfile, unique_id=student_id)
            return self._calculate_risk_assessment(student)
        except Exception as e:
            logger.error("Failed to calculate risk assessment for %s: %s", student_id, e)
            return None

    @strawberry.field
    def student_success_prediction(self, student_id: strawberry.ID) -> Optional[SuccessPrediction]:
        """Get success prediction for a student."""
        try:
            student = get_object_or_404(StudentProfile, unique_id=student_id)
            return self._calculate_success_prediction(student)
        except Exception as e:
            logger.error("Failed to calculate success prediction for %s: %s", student_id, e)
            return None

    @strawberry.field
    def student_academic_progress(self, student_id: strawberry.ID) -> Optional[AcademicProgress]:
        """Get detailed academic progress for a student."""
        try:
            student = get_object_or_404(StudentProfile, unique_id=student_id)
            return self._calculate_academic_progress(student)
        except Exception as e:
            logger.error("Failed to calculate academic progress for %s: %s", student_id, e)
            return None

    @strawberry.field
    def student_financial_summary(self, student_id: strawberry.ID) -> Optional[FinancialSummary]:
        """Get financial summary for a student."""
        try:
            student = get_object_or_404(StudentProfile, unique_id=student_id)
            return self._calculate_financial_summary(student)
        except Exception as e:
            logger.error("Failed to calculate financial summary for %s: %s", student_id, e)
            return None

    @strawberry.field
    def student_timeline(
        self,
        student_id: strawberry.ID,
        filters: Optional[TimelineFilterInput] = None
    ) -> List[strawberry.type("TimelineEvent")]:
        """Get student activity timeline with advanced filtering."""
        try:
            student = get_object_or_404(StudentProfile, unique_id=student_id)
            return self._get_student_timeline(student, filters)
        except Exception as e:
            logger.error("Failed to get timeline for %s: %s", student_id, e)
            return []

    @strawberry.field
    def students_at_risk(
        self,
        risk_threshold: float = 0.7,
        limit: int = 50
    ) -> List[EnhancedStudentType]:
        """Get students identified as at-risk."""
        # This would typically use a cached risk calculation
        # For now, we'll use simplified logic

        students = StudentProfile.objects.select_related('person').annotate(
            avg_grade=Avg('class_header_enrollments__grades__grade_points'),
            attendance_count=Count('attendance_records')
        ).filter(
            Q(avg_grade__lt=2.0) |  # Low GPA
            Q(attendance_count__lt=10)  # Poor attendance
        )[:limit]

        return [self._build_enhanced_student(student) for student in students]

    @strawberry.field
    def student_cohort_analysis(
        self,
        cohort_year: int,
        program_id: Optional[strawberry.ID] = None
    ) -> List[TimeSeriesPoint]:
        """Analyze student cohort performance over time."""
        # TODO: Implement cohort analysis
        return []

    def _apply_filters(self, queryset, filters: AdvancedStudentSearchFilters):
        """Apply advanced filters to student queryset."""

        # Text search
        if filters.query:
            search_terms = filters.query.split()
            search_q = Q()
            for term in search_terms:
                search_q |= (
                    Q(person__personal_name__icontains=term) |
                    Q(person__family_name__icontains=term) |
                    Q(student_id__icontains=term) |
                    Q(person__school_email__icontains=term)
                )
            queryset = queryset.filter(search_q)

        # Categorical filters
        if filters.program_ids:
            queryset = queryset.filter(
                program_enrollments__program__unique_id__in=filters.program_ids
            )

        if filters.statuses:
            queryset = queryset.filter(status__in=filters.statuses)

        # Academic filters
        if filters.min_gpa is not None or filters.max_gpa is not None:
            queryset = queryset.annotate(
                avg_grade=Avg('class_header_enrollments__grades__grade_points')
            )
            if filters.min_gpa is not None:
                queryset = queryset.filter(avg_grade__gte=filters.min_gpa)
            if filters.max_gpa is not None:
                queryset = queryset.filter(avg_grade__lte=filters.max_gpa)

        # Financial filters
        if filters.has_overdue_payments is not None:
            if filters.has_overdue_payments:
                queryset = queryset.filter(
                    invoices__due_date__lt=datetime.now(),
                    invoices__status='pending'
                )
            else:
                queryset = queryset.exclude(
                    invoices__due_date__lt=datetime.now(),
                    invoices__status='pending'
                )

        # Date filters
        if filters.enrolled_after:
            queryset = queryset.filter(enrollment_start_date__gte=filters.enrolled_after)

        if filters.enrolled_before:
            queryset = queryset.filter(enrollment_start_date__lte=filters.enrolled_before)

        return queryset.distinct()

    def _get_sort_field(self, field: str) -> str:
        """Map GraphQL sort fields to model fields."""
        field_mapping = {
            'name': 'person__family_name',
            'gpa': 'avg_grade',  # Requires annotation
            'risk_score': 'risk_score',  # Would require annotation
            'last_activity': 'last_activity',
            'enrollment_date': 'enrollment_start_date'
        }
        return field_mapping.get(field, 'person__family_name')

    def _build_enhanced_student(self, student: StudentProfile) -> EnhancedStudentType:
        """Build enhanced student type with all related data."""

        # Use caching for expensive calculations
        cache_key = f"enhanced_student_{student.unique_id}"
        cached_data = cache.get(cache_key)

        if cached_data:
            return EnhancedStudentType(**cached_data)

        # Calculate all the enhanced data
        risk_assessment = self._calculate_risk_assessment(student)
        success_prediction = self._calculate_success_prediction(student)
        academic_progress = self._calculate_academic_progress(student)
        financial_summary = self._calculate_financial_summary(student)

        # Build the enhanced student object
        enhanced_student_data = {
            'unique_id': str(student.unique_id),
            'student_id': student.student_id,
            'person': student.person,
            'status': student.status,
            'enrollment_start_date': student.enrollment_start_date,
            'risk_assessment': risk_assessment,
            'success_prediction': success_prediction,
            'academic_progress': academic_progress,
            'financial_summary': financial_summary,
            'engagement_score': 0.8,  # Placeholder
            'emergency_contacts': [],  # TODO: Implement
            'enrollments': [],  # TODO: Implement
            'timeline': [],  # TODO: Implement
        }

        # Cache for 15 minutes
        cache.set(cache_key, enhanced_student_data, 900)

        return EnhancedStudentType(**enhanced_student_data)

    def _calculate_risk_assessment(self, student: StudentProfile) -> RiskAssessment:
        """Calculate detailed risk assessment."""

        risk_factors = []
        risk_score = 0.0

        # Academic risk factors
        recent_grades = Grade.objects.filter(
            class_header_enrollment__student_profile=student
        ).order_by('-created_at')[:10]

        if recent_grades:
            avg_grade = sum(g.grade_points for g in recent_grades if g.grade_points) / len(recent_grades)
            if avg_grade < 2.0:
                risk_factors.append("low_academic_performance")
                risk_score += 0.3

        # Attendance risk factors
        recent_attendance = AttendanceRecord.objects.filter(
            student_profile=student
        ).order_by('-date')[:20]

        if recent_attendance:
            attendance_rate = len([a for a in recent_attendance if a.status == 'present']) / len(recent_attendance)
            if attendance_rate < 0.7:
                risk_factors.append("poor_attendance")
                risk_score += 0.2

        # Financial risk factors
        overdue_invoices = Invoice.objects.filter(
            student_profile=student,
            due_date__lt=datetime.now(),
            status='pending'
        ).count()

        if overdue_invoices > 0:
            risk_factors.append("financial_difficulties")
            risk_score += 0.2

        # Determine risk level
        if risk_score >= 0.7:
            risk_level = "high"
        elif risk_score >= 0.4:
            risk_level = "medium"
        else:
            risk_level = "low"

        recommendations = []
        if "low_academic_performance" in risk_factors:
            recommendations.append("Schedule academic counseling session")
        if "poor_attendance" in risk_factors:
            recommendations.append("Contact student about attendance concerns")
        if "financial_difficulties" in risk_factors:
            recommendations.append("Refer to financial aid office")

        return RiskAssessment(
            risk_score=min(risk_score, 1.0),
            risk_level=risk_level,
            risk_factors=risk_factors,
            recommendations=recommendations,
            last_calculated=datetime.now(),
            confidence=0.8
        )

    def _calculate_success_prediction(self, student: StudentProfile) -> SuccessPrediction:
        """Calculate success prediction using simplified model."""

        # Simplified success prediction algorithm
        success_factors = []
        base_score = 0.5

        # Academic performance
        grades = Grade.objects.filter(
            class_header_enrollment__student_profile=student
        ).values_list('grade_points', flat=True)

        if grades:
            avg_grade = sum(grades) / len(grades)
            if avg_grade > 3.0:
                success_factors.append("strong_academic_performance")
                base_score += 0.2
            elif avg_grade < 2.0:
                base_score -= 0.2

        # Attendance pattern
        attendance_records = AttendanceRecord.objects.filter(
            student_profile=student
        )
        if attendance_records.exists():
            attendance_rate = attendance_records.filter(
                status='present'
            ).count() / attendance_records.count()

            if attendance_rate > 0.9:
                success_factors.append("excellent_attendance")
                base_score += 0.15
            elif attendance_rate < 0.7:
                base_score -= 0.15

        # Financial stability
        overdue_count = Invoice.objects.filter(
            student_profile=student,
            due_date__lt=datetime.now(),
            status='pending'
        ).count()

        if overdue_count == 0:
            success_factors.append("financial_stability")
            base_score += 0.1

        success_probability = max(0.0, min(1.0, base_score))

        improvement_areas = []
        if success_probability < 0.7:
            improvement_areas.extend([
                "improve_study_habits",
                "increase_class_participation",
                "seek_academic_support"
            ])

        return SuccessPrediction(
            success_probability=success_probability,
            confidence=0.75,
            key_factors=success_factors,
            improvement_areas=improvement_areas,
            model_version="1.0.0",
            prediction_date=datetime.now()
        )

    def _calculate_academic_progress(self, student: StudentProfile) -> AcademicProgress:
        """Calculate detailed academic progress."""

        # Get all enrollments
        enrollments = ClassHeaderEnrollment.objects.filter(
            student_profile=student
        ).select_related('class_header__course')

        total_credit_hours = sum(
            enrollment.class_header.course.credit_hours
            for enrollment in enrollments
        )

        completed_enrollments = enrollments.filter(status='completed')
        completed_credit_hours = sum(
            enrollment.class_header.course.credit_hours
            for enrollment in completed_enrollments
        )

        in_progress_enrollments = enrollments.filter(status='enrolled')
        in_progress_credit_hours = sum(
            enrollment.class_header.course.credit_hours
            for enrollment in in_progress_enrollments
        )

        # Calculate GPA
        grades = Grade.objects.filter(
            class_header_enrollment__student_profile=student,
            assignment__assignment_type='final'
        )

        if grades.exists():
            total_points = sum(
                grade.grade_points * grade.class_header_enrollment.class_header.course.credit_hours
                for grade in grades if grade.grade_points
            )
            total_hours = sum(
                grade.class_header_enrollment.class_header.course.credit_hours
                for grade in grades if grade.grade_points
            )
            cumulative_gpa = total_points / total_hours if total_hours > 0 else None
        else:
            cumulative_gpa = None

        # Academic standing
        if cumulative_gpa is None:
            academic_standing = "new_student"
        elif cumulative_gpa >= 3.5:
            academic_standing = "dean_list"
        elif cumulative_gpa >= 2.0:
            academic_standing = "good_standing"
        else:
            academic_standing = "academic_probation"

        return AcademicProgress(
            cumulative_gpa=cumulative_gpa,
            total_credit_hours=total_credit_hours,
            completed_credit_hours=completed_credit_hours,
            in_progress_credit_hours=in_progress_credit_hours,
            degree_completion_percentage=0.0,  # TODO: Calculate based on program requirements
            required_courses_remaining=0,  # TODO: Calculate
            elective_credits_needed=0,  # TODO: Calculate
            academic_standing=academic_standing,
            honors_recognition=[]  # TODO: Implement
        )

    def _calculate_financial_summary(self, student: StudentProfile) -> FinancialSummary:
        """Calculate comprehensive financial summary."""

        invoices = Invoice.objects.filter(student_profile=student)
        payments = Payment.objects.filter(invoice__student_profile=student)

        total_charges = sum(invoice.amount for invoice in invoices)
        total_payments = sum(payment.amount for payment in payments)
        current_balance = total_charges - total_payments

        overdue_invoices = invoices.filter(
            due_date__lt=datetime.now(),
            status='pending'
        )
        overdue_amount = sum(invoice.amount for invoice in overdue_invoices)

        last_payment = payments.order_by('-created_at').first()

        return FinancialSummary(
            total_charges=str(total_charges),
            total_payments=str(total_payments),
            current_balance=str(current_balance),
            overdue_amount=str(overdue_amount),
            credit_balance="0.00",  # TODO: Implement credit tracking
            last_payment_date=last_payment.created_at if last_payment else None,
            last_payment_amount=str(last_payment.amount) if last_payment else None,
            payment_plan_active=False,  # TODO: Implement payment plans
            scholarship_total="0.00",  # TODO: Implement scholarship tracking
            scholarship_percentage=0.0,
            financial_aid_eligibility=current_balance > 0
        )

    def _get_student_timeline(self, student: StudentProfile, filters) -> List:
        """Get filtered timeline events for student."""
        # TODO: Implement comprehensive timeline
        return []