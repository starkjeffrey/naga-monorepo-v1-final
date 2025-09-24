"""GPA calculation and management system following clean architecture.

This module provides specialized GPA calculation services including:
- Term and cumulative GPA calculations
- Major-specific GPA tracking
- Academic standing determination
- GPA forecasting and planning tools
- Transcript generation support

Key business rules:
- GPA calculations limited to courses in current major requirements
- Only finalized grades included in GPA calculations
- Academic standing based on both term and cumulative GPA
- Support for different credit systems (semester hours vs. other)
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.utils import timezone

from .models import GPARecord
from .services import GPACalculationService

# GPA calculation constants
MIN_DECIMAL_PLACES = 2
GPA_TOLERANCE = Decimal("0.1")


@dataclass
class GPASnapshot:
    """Data class for GPA calculation snapshots."""

    term_gpa: Decimal | None
    cumulative_gpa: Decimal | None
    quality_points: Decimal
    credit_hours_attempted: Decimal
    credit_hours_earned: Decimal
    courses_count: int
    calculation_date: datetime


@dataclass
class AcademicStanding:
    """Data class for academic standing determination."""

    status: str  # GOOD_STANDING, PROBATION, SUSPENSION, DISMISSAL
    term_gpa: Decimal | None
    cumulative_gpa: Decimal | None
    requirements_met: bool
    warnings: list[str]
    recommendations: list[str]


class GPAManager:
    """Advanced GPA management and calculation system.

    Provides comprehensive GPA tracking with academic standing
    determination and forecasting capabilities.
    """

    # Academic standing thresholds
    GOOD_STANDING_THRESHOLD = Decimal("2.0")
    PROBATION_THRESHOLD = Decimal("1.5")
    SUSPENSION_THRESHOLD = Decimal("1.0")

    # Credit hour requirements for standing
    MIN_CREDITS_FOR_STANDING = Decimal("12.0")

    @classmethod
    def calculate_comprehensive_gpa(
        cls,
        student,
        term,
        major,
        include_forecasting: bool = False,
    ) -> dict[str, Any]:
        """Calculate comprehensive GPA data for a student.

        Args:
            student: StudentProfile instance
            term: Current term for calculations
            major: Major for GPA calculations
            include_forecasting: Whether to include GPA forecasting

        Returns:
            Comprehensive GPA data including standing and projections
        """
        # Calculate current GPAs
        term_gpa = GPACalculationService.calculate_term_gpa(
            student=student,
            term=term,
            major=major,
            force_recalculate=True,
        )

        cumulative_gpa = GPACalculationService.calculate_cumulative_gpa(
            student=student,
            current_term=term,
            major=major,
            force_recalculate=True,
        )

        # Create GPA snapshot
        snapshot = cls._create_gpa_snapshot(term_gpa, cumulative_gpa)

        # Determine academic standing
        standing = cls.determine_academic_standing(
            student=student,
            term_gpa_record=term_gpa,
            cumulative_gpa_record=cumulative_gpa,
        )

        # Get GPA history
        history = cls.get_gpa_history(student, major, limit=8)

        # Calculate progress metrics
        progress = cls.calculate_progress_metrics(student, major, term)

        result = {
            "snapshot": snapshot,
            "standing": standing,
            "history": history,
            "progress": progress,
            "term_gpa_record": term_gpa,
            "cumulative_gpa_record": cumulative_gpa,
        }

        # Add forecasting if requested
        if include_forecasting:
            result["forecasting"] = cls.calculate_gpa_forecasting(
                student,
                major,
                cumulative_gpa,
            )

        return result

    @classmethod
    def _create_gpa_snapshot(
        cls,
        term_gpa: GPARecord | None,
        cumulative_gpa: GPARecord | None,
    ) -> GPASnapshot:
        """Create a GPA snapshot from GPA records."""
        return GPASnapshot(
            term_gpa=term_gpa.gpa_value if term_gpa else None,
            cumulative_gpa=cumulative_gpa.gpa_value if cumulative_gpa else None,
            quality_points=(cumulative_gpa.quality_points if cumulative_gpa else Decimal("0")),
            credit_hours_attempted=(cumulative_gpa.credit_hours_attempted if cumulative_gpa else Decimal("0")),
            credit_hours_earned=(cumulative_gpa.credit_hours_earned if cumulative_gpa else Decimal("0")),
            courses_count=(len(cumulative_gpa.calculation_details.get("terms", [])) if cumulative_gpa else 0),
            calculation_date=timezone.now(),
        )

    @classmethod
    def determine_academic_standing(
        cls,
        student,
        term_gpa_record: GPARecord | None,
        cumulative_gpa_record: GPARecord | None,
    ) -> AcademicStanding:
        """Determine academic standing based on GPA thresholds.

        Args:
            student: StudentProfile instance
            term_gpa_record: Term GPA record
            cumulative_gpa_record: Cumulative GPA record

        Returns:
            AcademicStanding with status and recommendations
        """
        warnings = []
        recommendations = []
        requirements_met = True

        term_gpa = term_gpa_record.gpa_value if term_gpa_record else None
        cumulative_gpa = cumulative_gpa_record.gpa_value if cumulative_gpa_record else None

        # Default to good standing for new students
        if not cumulative_gpa or not term_gpa:
            return AcademicStanding(
                status="GOOD_STANDING",
                term_gpa=term_gpa,
                cumulative_gpa=cumulative_gpa,
                requirements_met=True,
                warnings=["Insufficient grade data for standing determination"],
                recommendations=[
                    "Complete more coursework for accurate standing assessment",
                ],
            )

        # Check minimum credit hours
        # cumulative_gpa_record should not be None due to the check above
        assert cumulative_gpa_record is not None, "cumulative_gpa_record should not be None after validation"
        credits_attempted = cumulative_gpa_record.credit_hours_attempted
        if credits_attempted < cls.MIN_CREDITS_FOR_STANDING:
            warnings.append(
                f"Minimum {cls.MIN_CREDITS_FOR_STANDING} credit hours required for standing determination",
            )

        # Determine standing based on cumulative GPA
        if cumulative_gpa >= cls.GOOD_STANDING_THRESHOLD:
            status = "GOOD_STANDING"

            # Check for term GPA warnings
            if term_gpa and term_gpa < cls.GOOD_STANDING_THRESHOLD:
                warnings.append("Term GPA below good standing threshold")
                recommendations.append("Focus on improving current term performance")

        elif cumulative_gpa >= cls.PROBATION_THRESHOLD:
            status = "PROBATION"
            requirements_met = False

            warnings.extend(
                [
                    "Cumulative GPA below good standing threshold",
                    "Academic probation status requires improvement plan",
                ],
            )

            recommendations.extend(
                [
                    "Meet with academic advisor to create improvement plan",
                    "Consider reducing course load to focus on grades",
                    "Utilize tutoring and academic support services",
                ],
            )

        elif cumulative_gpa >= cls.SUSPENSION_THRESHOLD:
            status = "SUSPENSION"
            requirements_met = False

            warnings.extend(
                ["Cumulative GPA critically low", "Academic suspension may be imposed"],
            )

            recommendations.extend(
                [
                    "Immediate intervention required",
                    "Meet with dean for academic planning",
                    "Consider academic leave or program change",
                ],
            )

        else:
            status = "DISMISSAL"
            requirements_met = False

            warnings.extend(
                [
                    "Cumulative GPA below minimum threshold",
                    "Academic dismissal proceedings may be initiated",
                ],
            )

            recommendations.extend(
                [
                    "Contact academic affairs immediately",
                    "Explore appeal process if applicable",
                    "Consider alternative academic pathways",
                ],
            )

        return AcademicStanding(
            status=status,
            term_gpa=term_gpa,
            cumulative_gpa=cumulative_gpa,
            requirements_met=requirements_met,
            warnings=warnings,
            recommendations=recommendations,
        )

    @classmethod
    def get_gpa_history(
        cls,
        student,
        major,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Get GPA history for trend analysis.

        Args:
            student: StudentProfile instance
            major: Major instance
            limit: Maximum number of records to return

        Returns:
            List of GPA history records
        """
        gpa_records = (
            GPARecord.objects.filter(
                student=student,
                major=major,
                gpa_type=GPARecord.GPAType.TERM,
            )
            .select_related("term")
            .order_by("-term__start_date")[:limit]
        )

        history = []
        for record in gpa_records:
            # Get corresponding cumulative GPA
            cumulative = GPARecord.objects.filter(
                student=student,
                major=major,
                term=record.term,
                gpa_type=GPARecord.GPAType.CUMULATIVE,
            ).first()

            history.append(
                {
                    "term": str(record.term),
                    "term_start": record.term.start_date,
                    "term_gpa": float(record.gpa_value),
                    "cumulative_gpa": (float(cumulative.gpa_value) if cumulative else None),
                    "credit_hours": float(record.credit_hours_attempted),
                    "courses_count": len(record.calculation_details.get("courses", [])),
                },
            )

        return history

    @classmethod
    def calculate_progress_metrics(
        cls,
        student,
        major,
        current_term,
    ) -> dict[str, Any]:
        """Calculate academic progress metrics.

        Args:
            student: StudentProfile instance
            major: Major instance
            current_term: Current term

        Returns:
            Progress metrics and trends
        """
        recent_records = GPARecord.objects.filter(
            student=student,
            major=major,
            gpa_type=GPARecord.GPAType.TERM,
        ).order_by("-term__start_date")[:4]

        if len(recent_records) < MIN_DECIMAL_PLACES:
            return {
                "trend": "INSUFFICIENT_DATA",
                "trend_direction": None,
                "improvement_rate": None,
                "completion_rate": None,
            }

        # Calculate GPA trend
        gpa_values = [float(record.gpa_value) for record in recent_records]
        gpa_trend = cls._calculate_trend(gpa_values)

        # Calculate completion rate
        total_attempted = sum(float(record.credit_hours_attempted) for record in recent_records)
        total_earned = sum(float(record.credit_hours_earned) for record in recent_records)
        completion_rate = (total_earned / total_attempted * 100) if total_attempted > 0 else 0

        # Calculate improvement rate (change per term)
        if len(gpa_values) >= MIN_DECIMAL_PLACES:
            recent_change = gpa_values[0] - gpa_values[1]
            improvement_rate = recent_change
        else:
            improvement_rate = 0

        return {
            "trend": gpa_trend["trend"],
            "trend_direction": gpa_trend["direction"],
            "improvement_rate": improvement_rate,
            "completion_rate": completion_rate,
            "recent_gpa_values": gpa_values,
            "terms_analyzed": len(recent_records),
        }

    @classmethod
    def _calculate_trend(cls, values: list[float]) -> dict[str, Any]:
        """Calculate trend from a series of values."""
        if len(values) < MIN_DECIMAL_PLACES:
            return {"trend": "INSUFFICIENT_DATA", "direction": None}

        recent_avg = sum(values[:MIN_DECIMAL_PLACES]) / MIN_DECIMAL_PLACES
        older_avg = sum(values[-MIN_DECIMAL_PLACES:]) / MIN_DECIMAL_PLACES

        change = recent_avg - older_avg

        if abs(change) < float(GPA_TOLERANCE):  # Minimal change threshold
            return {"trend": "STABLE", "direction": 0}
        if change > 0:
            return {"trend": "IMPROVING", "direction": 1}
        return {"trend": "DECLINING", "direction": -1}

    @classmethod
    def calculate_gpa_forecasting(
        cls,
        student,
        major,
        cumulative_gpa_record: GPARecord | None,
    ) -> dict[str, Any]:
        """Calculate GPA forecasting scenarios.

        Args:
            student: StudentProfile instance
            major: Major instance
            cumulative_gpa_record: Current cumulative GPA record

        Returns:
            GPA forecasting scenarios
        """
        if not cumulative_gpa_record:
            return {
                "scenarios": [],
                "recommendations": ["Complete more coursework for forecasting"],
            }

        current_gpa = cumulative_gpa_record.gpa_value
        current_credits = cumulative_gpa_record.credit_hours_attempted
        current_quality_points = cumulative_gpa_record.quality_points

        # Define scenario credit loads
        scenario_credits = [3, 6, 9, 12, 15]  # Common credit loads
        target_gpas = [Decimal("2.0"), Decimal("2.5"), Decimal("3.0"), Decimal("3.5")]

        scenarios = []

        for credits in scenario_credits:
            for target_gpa in target_gpas:
                if target_gpa <= current_gpa:
                    continue  # Only show improvement scenarios

                # Calculate required grade average
                required_quality_points = (target_gpa * (current_credits + credits)) - current_quality_points
                required_avg_grade = required_quality_points / credits

                if required_avg_grade <= 4.0:  # Achievable scenario
                    scenarios.append(
                        {
                            "credits": credits,
                            "target_gpa": float(target_gpa),
                            "required_avg_grade": float(required_avg_grade),
                            "achievable": required_avg_grade <= Decimal("4.0"),
                            "difficulty": cls._assess_difficulty(required_avg_grade),
                        },
                    )

        # Generate recommendations
        recommendations = cls._generate_forecasting_recommendations(
            current_gpa,
            scenarios,
        )

        return {
            "current_gpa": float(current_gpa),
            "current_credits": float(current_credits),
            "scenarios": scenarios[:10],  # Limit to 10 most relevant
            "recommendations": recommendations,
        }

    @classmethod
    def _assess_difficulty(cls, required_avg_grade: Decimal) -> str:
        """Assess difficulty of achieving required grade average."""
        if required_avg_grade >= Decimal("3.7"):
            return "VERY_DIFFICULT"
        if required_avg_grade >= Decimal("3.0"):
            return "MODERATE"
        if required_avg_grade >= Decimal("2.0"):
            return "ACHIEVABLE"
        return "EASY"

    @classmethod
    def _generate_forecasting_recommendations(
        cls,
        current_gpa: Decimal,
        scenarios: list[dict[str, Any]],
    ) -> list[str]:
        """Generate recommendations based on forecasting scenarios."""
        recommendations = []

        if current_gpa < cls.GOOD_STANDING_THRESHOLD:
            recommendations.append("Focus on achieving good standing (2.0 GPA) first")
            recommendations.append(
                "Consider lighter course load to ensure grade quality",
            )

        achievable_scenarios = [s for s in scenarios if s["achievable"] and s["difficulty"] in ["EASY", "ACHIEVABLE"]]

        if achievable_scenarios:
            best_scenario = min(achievable_scenarios, key=lambda x: x["credits"])
            recommendations.append(
                (
                    f"Consider taking {best_scenario['credits']} credits with "
                    f"{best_scenario['required_avg_grade']:.1f} average grade to reach "
                    f"{best_scenario['target_gpa']} GPA"
                ),
            )

        if current_gpa >= Decimal("3.0"):
            recommendations.append(
                "Maintain current performance for continued academic success",
            )

        return recommendations


class GPAReportGenerator:
    """Service for generating GPA reports and transcripts.

    Provides formatted GPA data for official documents and
    student academic records.
    """

    @classmethod
    def generate_transcript_data(
        cls,
        student,
        major,
        include_unofficial: bool = False,
    ) -> dict[str, Any]:
        """Generate comprehensive transcript data.

        Args:
            student: StudentProfile instance
            major: Major instance
            include_unofficial: Whether to include unofficial grades

        Returns:
            Formatted transcript data
        """
        # Get all GPA records
        gpa_records = (
            GPARecord.objects.filter(
                student=student,
                major=major,
            )
            .select_related("term")
            .order_by("term__start_date", "gpa_type")
        )

        # Organize by term
        term_data = {}
        cumulative_gpa = None

        for record in gpa_records:
            term_key = str(record.term)

            if term_key not in term_data:
                term_data[term_key] = {
                    "term": record.term,
                    "term_gpa": None,
                    "cumulative_gpa": None,
                    "courses": record.calculation_details.get("courses", []),
                }

            if record.gpa_type == GPARecord.GPAType.TERM:
                term_data[term_key]["term_gpa"] = record
            elif record.gpa_type == GPARecord.GPAType.CUMULATIVE:
                term_data[term_key]["cumulative_gpa"] = record
                cumulative_gpa = record  # Keep track of latest

        # Calculate summary statistics
        total_credits_attempted = cumulative_gpa.credit_hours_attempted if cumulative_gpa else 0
        total_credits_earned = cumulative_gpa.credit_hours_earned if cumulative_gpa else 0
        final_gpa = cumulative_gpa.gpa_value if cumulative_gpa else None

        return {
            "student": student,
            "major": major,
            "terms": list(term_data.values()),
            "summary": {
                "total_credits_attempted": float(total_credits_attempted),
                "total_credits_earned": float(total_credits_earned),
                "completion_rate": float(
                    ((total_credits_earned / total_credits_attempted * 100) if total_credits_attempted > 0 else 0),
                ),
                "final_gpa": float(final_gpa) if final_gpa else None,
                "terms_completed": len(term_data),
            },
            "generated_at": timezone.now(),
            "include_unofficial": include_unofficial,
        }

    @classmethod
    def generate_gpa_summary_report(
        cls,
        students: list,
        term,
        major,
    ) -> dict[str, Any]:
        """Generate GPA summary report for multiple students.

        Args:
            students: List of StudentProfile instances
            term: Term for the report
            major: Major for filtering

        Returns:
            Summary report with statistics
        """
        student_gpas = []
        gpa_values = []

        for student in students:
            gpa_record = GPARecord.objects.filter(
                student=student,
                term=term,
                major=major,
                gpa_type=GPARecord.GPAType.TERM,
            ).first()

            if gpa_record:
                student_gpas.append(
                    {
                        "student": student,
                        "gpa": float(gpa_record.gpa_value),
                        "credits": float(gpa_record.credit_hours_attempted),
                        "standing": GPAManager.determine_academic_standing(
                            student,
                            gpa_record,
                            None,
                        ).status,
                    },
                )
                gpa_values.append(float(gpa_record.gpa_value))

        # Calculate statistics
        if gpa_values:
            avg_gpa = sum(gpa_values) / len(gpa_values)
            min_gpa = min(gpa_values)
            max_gpa = max(gpa_values)

            # Count by standing
            standing_counts: dict[str, int] = {}
            for record in student_gpas:
                standing = record["standing"]
                standing_counts[standing] = standing_counts.get(standing, 0) + 1
        else:
            avg_gpa = min_gpa = max_gpa = 0
            standing_counts: dict[str, int] = {}

        return {
            "term": term,
            "major": major,
            "student_count": len(students),
            "records_found": len(student_gpas),
            "statistics": {
                "average_gpa": round(avg_gpa, 3),
                "minimum_gpa": min_gpa,
                "maximum_gpa": max_gpa,
                "standing_distribution": standing_counts,
            },
            "student_records": student_gpas,
            "generated_at": timezone.now(),
        }
