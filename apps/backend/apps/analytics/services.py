"""Analytics services for program journey analysis and major deduction.

This module provides services for analyzing student program journeys,
deducing majors from course patterns, and generating analytics.
"""

from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

from apps.curriculum.models import Course, Major, Term
from apps.enrollment.models import ClassHeaderEnrollment, ProgramEnrollment
from apps.people.models import StudentProfile


class ProgramJourneyAnalyzer:
    """Analyze student program journeys and transitions."""

    def __init__(self) -> None:
        # Note: Legacy section codes removed - new SIS uses direct program/cycle relationships
        self.section_to_program: dict[str, str] = {}

    def analyze_student_journey(self, student: StudentProfile) -> dict[str, Any]:
        """Analyze a student's complete program journey.

        Returns a comprehensive analysis including:
        - Program transitions
        - Completion status
        - Time in each program
        - Credits earned
        - Major deductions
        """
        enrollments = list(
            ClassHeaderEnrollment.objects.filter(student=student)
            .select_related("class_header__course", "class_header__term")
            .order_by("class_header__term__start_date"),
        )

        if not enrollments:
            return {"status": "NO_ENROLLMENTS"}

        term_courses = defaultdict(list)

        for enrollment in enrollments:
            term = enrollment.class_header.term
            term_courses[term].append(enrollment.class_header.course)

        # Identify program periods (using new SIS structure)
        program_periods = self._identify_program_periods(term_courses)

        # Deduce majors for academic programs
        for period in program_periods:
            if period["division"] == "ACADEMIC":
                period["deduced_major"] = self._deduce_major_from_courses(period["courses"])

        # Calculate journey metrics
        journey = {
            "student_id": student.student_id,
            "program_periods": program_periods,
            "total_programs": len(program_periods),
            "journey_type": self._classify_journey_type(program_periods),
            "total_terms": len(term_courses),
            "gaps": self._identify_gaps(list(term_courses.keys())),
        }

        return journey

    def _extract_section(self, class_header) -> str:
        """Extract section code from class header."""
        # Legacy method - new SIS uses direct program/cycle relationships
        # This method is deprecated and should not be used
        return None

    def _identify_program_periods(self, term_sections: dict[Any, Any]) -> list[dict[str, Any]]:
        """Identify distinct program enrollment periods using actual program enrollments."""
        # This method should be rewritten to use ProgramEnrollment model
        # instead of legacy section codes
        periods: list[dict[str, Any]] = []

        # Get actual program enrollments for the student
        # This is a placeholder - should be implemented based on actual ProgramEnrollment model
        # program_enrollments = ProgramEnrollment.objects.filter(student=student).order_by('start_date')

        # Implementation needed: Use ProgramEnrollment model for accurate program periods
        return periods

    def _classify_journey_type(self, periods: list[dict]) -> str:
        """Classify the type of student journey."""
        if len(periods) == 1:
            return "LINEAR"
        elif len(periods) > 1:
            # Check for program transitions within academic division
            cycles = [p.get("cycle") for p in periods if p.get("division") == "ACADEMIC"]
            if "BA" in cycles and "MA" in cycles:
                return "BA_TO_MA_PROGRESSION"
            else:
                return "MULTI_PROGRAM"
        else:
            return "UNKNOWN"

    def _identify_gaps(self, terms: list[Term]) -> list[dict]:
        """Identify enrollment gaps."""
        gaps = []
        sorted_terms = sorted(terms, key=lambda t: t.start_date)

        for i in range(1, len(sorted_terms)):
            prev_term = sorted_terms[i - 1]
            curr_term = sorted_terms[i]

            # Simple gap detection - would need more sophisticated logic
            gap_days = (curr_term.start_date - prev_term.end_date).days
            if gap_days > 30:  # More than a month gap
                gaps.append(
                    {
                        "after_term": prev_term.code,
                        "before_term": curr_term.code,
                        "gap_days": gap_days,
                    }
                )

        return gaps

    def _deduce_major_from_courses(self, courses: list[Course]) -> dict | None:
        """Deduce a student's major from their course enrollment patterns.

        Uses course prefixes and frequencies to determine likely major.
        """
        if not courses:
            return None

        # Count course prefixes
        prefix_counts: Counter[str] = Counter()
        for course in courses:
            prefix = course.code.split("-")[0]
            prefix_counts[prefix] += 1

        # Calculate percentages
        total_courses = sum(prefix_counts.values())
        prefix_percentages = {prefix: count / total_courses for prefix, count in prefix_counts.items()}

        # Find dominant prefix
        dominant_prefix = max(prefix_percentages, key=prefix_percentages.get)
        confidence = prefix_percentages[dominant_prefix]

        # Map prefix to major (simplified - would need actual mapping)
        prefix_to_major = {
            "IR": "International Relations",
            "BUS": "Business Administration",
            "COMP": "Computer Science",
            "ENGL": "English",
            "POL": "Political Science",
            # Add more mappings
        }

        major_name = prefix_to_major.get(dominant_prefix, f"{dominant_prefix} Studies")

        return {
            "major": major_name,
            "confidence": confidence,
            "primary_prefix": dominant_prefix,
            "course_distribution": dict(prefix_counts.most_common(5)),
        }


class ProgramCompletionAnalyzer:
    """Analyze program completion rates and patterns."""

    def calculate_completion_status(self, enrollment: ProgramEnrollment) -> str:
        """Determine the completion status of a program enrollment.

        Complex logic considering:
        - Credits earned vs required
        - Last activity date
        - Subsequent enrollments
        - Graduation records
        """
        # Check if graduated
        if hasattr(enrollment.student, "graduation") and enrollment.student.graduation:
            if enrollment.program == enrollment.student.graduation.program:
                return "GRADUATED"

        # Check credits if available
        if enrollment.credits_required and enrollment.credits_earned:
            completion_pct = enrollment.credits_earned / enrollment.credits_required
            if completion_pct >= 0.95:  # 95% or more
                return "COMPLETED"
            elif completion_pct < 0.25 and not enrollment.is_active:
                return "DROPPED"

        # Check time since last activity
        if enrollment.end_date:
            days_inactive = (datetime.now().date() - enrollment.end_date).days
            if days_inactive > 365:  # More than a year
                return "INACTIVE"
            elif days_inactive > 180:  # More than 6 months
                return "INTERRUPTED"

        # Check for program transfers
        later_enrollments = ProgramEnrollment.objects.filter(
            student=enrollment.student,
            start_date__gt=enrollment.start_date,
        ).exclude(pk=enrollment.pk)

        if later_enrollments.exists():
            return "TRANSFERRED"

        return "ACTIVE" if enrollment.is_active else "UNKNOWN"

    def generate_completion_analytics(self, program: Major, start_year: int, end_year: int) -> dict:
        """Generate completion analytics for a program."""
        enrollments = ProgramEnrollment.objects.filter(
            program=program,
            start_date__year__gte=start_year,
            start_date__year__lte=end_year,
        )

        total = enrollments.count()
        if total == 0:
            return {"error": "No enrollments found"}

        # Calculate completion statuses
        status_counts: dict[str, int] = defaultdict(int)
        completion_times = []

        for enrollment in enrollments:
            status = self.calculate_completion_status(enrollment)
            status_counts[status] += 1

            if status in ["GRADUATED", "COMPLETED"] and enrollment.time_to_completion:
                completion_times.append(enrollment.time_to_completion)

        # Calculate metrics
        completion_rate = (status_counts["GRADUATED"] + status_counts["COMPLETED"]) / total * 100
        dropout_rate = status_counts["DROPPED"] / total * 100

        avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else None

        return {
            "program": program.name,
            "total_enrollments": total,
            "completion_rate": round(completion_rate, 2),
            "dropout_rate": round(dropout_rate, 2),
            "average_completion_days": avg_completion_time,
            "status_distribution": dict(status_counts),
            "years_analyzed": f"{start_year}-{end_year}",
        }
