"""Django management command for generating completion and dropout reports.

Usage:
    python manage.py completion_dropout_reports [--format csv|json] [--output-dir reports/]
"""

import csv
import json
from datetime import datetime, timedelta
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Avg, Count, Q
from django.utils import timezone

from apps.curriculum.models import Term
from apps.enrollment.models import (
    ClassHeaderEnrollment,
    ProgramEnrollment,
    ProgramTransition,
)
from apps.people.models import StudentProfile


class Command(BaseCommand):
    """Django management command for completion and dropout analysis."""

    help = "Generate comprehensive completion rates and dropout pattern reports"

    def add_arguments(self, parser):
        parser.add_argument(
            "--format",
            choices=["csv", "json"],
            default="csv",
            help="Output format for reports (default: csv)",
        )
        parser.add_argument(
            "--output-dir",
            default="reports/completion_analysis",
            help="Directory to save reports (default: reports/completion_analysis)",
        )

    def handle(self, *args, **options):
        self.output_dir = Path(options["output_dir"])
        self.output_format = options["format"]
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(self.style.SUCCESS("Generating completion and dropout analysis reports..."))
        self.stdout.write(f"Output directory: {self.output_dir}")
        self.stdout.write(f"Format: {self.output_format}")
        self.stdout.write(f"Timestamp: {self.timestamp}")
        self.stdout.write("")

        report_files = {}

        try:
            # Generate all reports
            self.stdout.write("1. Generating Program Completion Rate Summary...")
            completion_data = self._analyze_program_completion_rates()
            filename = self._save_report("program_completion_rates", completion_data)
            report_files["completion_rates"] = filename
            self.stdout.write(f"   Saved: {filename}")

            self.stdout.write("2. Generating Dropout Pattern Analysis...")
            dropout_data = self._analyze_dropout_patterns()
            filename = self._save_report("dropout_patterns", dropout_data)
            report_files["dropout_patterns"] = filename
            self.stdout.write(f"   Saved: {filename}")

            self.stdout.write("3. Generating Student Journey Timeline Analysis...")
            journey_data = self._analyze_student_journeys()
            filename = self._save_report("student_journeys", journey_data)
            report_files["student_journeys"] = filename
            self.stdout.write(f"   Saved: {filename}")

            self.stdout.write("4. Generating Risk Factor Analysis...")
            risk_data = self._analyze_risk_factors()
            filename = self._save_report("risk_factors", risk_data)
            report_files["risk_factors"] = filename
            self.stdout.write(f"   Saved: {filename}")

            self.stdout.write("5. Generating Term-by-Term Retention Analysis...")
            retention_data = self._analyze_term_retention()
            filename = self._save_report("term_retention", retention_data)
            report_files["term_retention"] = filename
            self.stdout.write(f"   Saved: {filename}")

            self.stdout.write("6. Generating Executive Summary...")
            summary_data = self._generate_executive_summary()
            filename = self._save_report("executive_summary", summary_data)
            report_files["executive_summary"] = filename
            self.stdout.write(f"   Saved: {filename}")

            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("=" * 60))
            self.stdout.write(self.style.SUCCESS("COMPLETION AND DROPOUT ANALYSIS COMPLETE"))
            self.stdout.write(self.style.SUCCESS("=" * 60))
            self.stdout.write(f"Reports generated: {len(report_files)}")
            for report_type, filepath in report_files.items():
                self.stdout.write(f"  {report_type}: {filepath}")
            self.stdout.write("")
            self.stdout.write("Key insights to review:")
            self.stdout.write("1. Program completion rates by division/cycle")
            self.stdout.write("2. Primary dropout reasons and timing patterns")
            self.stdout.write("3. Student journey transitions between programs")
            self.stdout.write("4. Risk factors for current active students")
            self.stdout.write("5. Term-by-term retention trends")
            self.stdout.write("6. Executive summary with actionable recommendations")

        except Exception as e:
            raise CommandError(f"Error generating reports: {e!s}") from e

    def _analyze_program_completion_rates(self) -> list[dict]:
        """Analyze completion rates by program, division, and cycle."""
        completion_stats = (
            ProgramEnrollment.objects.values("program__name", "program__code", "division", "cycle", "enrollment_type")
            .annotate(
                total_enrollments=Count("id"),
                completed_count=Count("id", filter=Q(status="COMPLETED")),
                graduated_count=Count("id", filter=Q(exit_reason="GRAD")),
                dropped_count=Count("id", filter=Q(status="DROPPED")),
                withdrawn_count=Count("id", filter=Q(status="WITHDRAWN")),
                failed_count=Count("id", filter=Q(status="FAILED")),
                active_count=Count("id", filter=Q(status="ACTIVE")),
                avg_completion_percentage=Avg("completion_percentage"),
                avg_time_to_completion=Avg("time_to_completion"),
                avg_credits_earned=Avg("credits_earned"),
                avg_gpa_at_exit=Avg("gpa_at_exit"),
            )
            .order_by("division", "cycle", "program__name")
        )

        completion_data = []
        for stat in completion_stats:
            total = stat["total_enrollments"]
            completed = stat["completed_count"]
            graduated = stat["graduated_count"]
            dropped = stat["dropped_count"]
            withdrawn = stat["withdrawn_count"]
            failed = stat["failed_count"]
            active = stat["active_count"]

            # Calculate rates
            completion_rate = (completed / total * 100) if total > 0 else 0
            graduation_rate = (graduated / total * 100) if total > 0 else 0
            dropout_rate = (dropped / total * 100) if total > 0 else 0
            withdrawal_rate = (withdrawn / total * 100) if total > 0 else 0
            failure_rate = (failed / total * 100) if total > 0 else 0
            retention_rate = ((active + completed) / total * 100) if total > 0 else 0

            completion_data.append(
                {
                    "program_name": stat["program__name"],
                    "program_code": stat["program__code"],
                    "division": stat["division"],
                    "cycle": stat["cycle"],
                    "enrollment_type": stat["enrollment_type"],
                    "total_enrollments": total,
                    "completed_count": completed,
                    "graduated_count": graduated,
                    "dropped_count": dropped,
                    "withdrawn_count": withdrawn,
                    "failed_count": failed,
                    "active_count": active,
                    "completion_rate_percent": round(completion_rate, 2),
                    "graduation_rate_percent": round(graduation_rate, 2),
                    "dropout_rate_percent": round(dropout_rate, 2),
                    "withdrawal_rate_percent": round(withdrawal_rate, 2),
                    "failure_rate_percent": round(failure_rate, 2),
                    "retention_rate_percent": round(retention_rate, 2),
                    "avg_completion_percentage": round(stat["avg_completion_percentage"] or 0, 2),
                    "avg_time_to_completion_days": round(stat["avg_time_to_completion"] or 0, 0),
                    "avg_credits_earned": round(stat["avg_credits_earned"] or 0, 2),
                    "avg_gpa_at_exit": round(stat["avg_gpa_at_exit"] or 0, 2),
                },
            )

        return completion_data

    def _analyze_dropout_patterns(self) -> list[dict]:
        """Analyze detailed dropout patterns and exit reasons."""
        dropout_patterns = (
            ProgramEnrollment.objects.filter(status__in=["DROPPED", "WITHDRAWN", "FAILED", "SUSPENDED"])
            .values("program__name", "division", "cycle", "exit_reason", "status")
            .annotate(
                count=Count("id"),
                avg_terms_active=Avg("terms_active"),
                avg_completion_percentage=Avg("completion_percentage"),
                avg_time_in_program=Avg("time_to_completion"),
                avg_gpa_at_exit=Avg("gpa_at_exit"),
            )
            .order_by("division", "cycle", "exit_reason")
        )

        dropout_data = []
        for pattern in dropout_patterns:
            dropout_data.append(
                {
                    "program_name": pattern["program__name"],
                    "division": pattern["division"],
                    "cycle": pattern["cycle"],
                    "exit_reason": pattern["exit_reason"],
                    "final_status": pattern["status"],
                    "dropout_count": pattern["count"],
                    "avg_terms_before_dropout": round(pattern["avg_terms_active"] or 0, 1),
                    "avg_completion_at_dropout": round(pattern["avg_completion_percentage"] or 0, 2),
                    "avg_days_in_program": round(pattern["avg_time_in_program"] or 0, 0),
                    "avg_gpa_at_exit": round(pattern["avg_gpa_at_exit"] or 0, 2),
                },
            )

        return dropout_data

    def _analyze_student_journeys(self) -> dict:
        """Analyze student journey patterns and program transitions."""
        transition_data = (
            ProgramTransition.objects.values(
                "from_enrollment__program__name",
                "to_enrollment__program__name",
                "transition_type",
                "from_enrollment__division",
                "to_enrollment__division",
            )
            .annotate(
                transition_count=Count("id"),
                avg_gap_days=Avg("gap_days"),
                avg_credits_transferred=Avg("credits_transferred"),
            )
            .order_by("-transition_count")
        )

        journey_patterns = []
        for transition in transition_data:
            journey_patterns.append(
                {
                    "from_program": transition["from_enrollment__program__name"],
                    "to_program": transition["to_enrollment__program__name"],
                    "transition_type": transition["transition_type"],
                    "from_division": transition["from_enrollment__division"],
                    "to_division": transition["to_enrollment__division"],
                    "transition_count": transition["transition_count"],
                    "avg_gap_days": round(transition["avg_gap_days"] or 0, 1),
                    "avg_credits_transferred": round(transition["avg_credits_transferred"] or 0, 2),
                },
            )

        multi_program_stats = (
            StudentProfile.objects.annotate(enrollment_count=Count("program_enrollments"))
            .filter(enrollment_count__gt=1)
            .values("enrollment_count")
            .annotate(student_count=Count("id"))
            .order_by("enrollment_count")
        )

        multi_program_data = []
        for stat in multi_program_stats:
            multi_program_data.append(
                {
                    "program_count": stat["enrollment_count"],
                    "student_count": stat["student_count"],
                },
            )

        return {
            "transition_patterns": journey_patterns,
            "multi_program_students": multi_program_data,
        }

    def _analyze_risk_factors(self) -> list[dict]:
        """Analyze risk factors for early identification of at-risk students."""
        risk_analysis = (
            ProgramEnrollment.objects.filter(status="ACTIVE")
            .values("program__name", "division", "cycle")
            .annotate(
                total_active=Count("id"),
                low_completion_count=Count("id", filter=Q(completion_percentage__lt=25)),
                long_enrollment_count=Count(
                    "id",
                    filter=Q(start_date__lt=timezone.now().date() - timedelta(days=365 * 2)),
                ),
                avg_completion=Avg("completion_percentage"),
                avg_terms_active=Avg("terms_active"),
            )
            .order_by("division", "cycle")
        )

        risk_data = []
        for analysis in risk_analysis:
            total = analysis["total_active"]
            low_completion_rate = (analysis["low_completion_count"] / total * 100) if total > 0 else 0
            long_enrollment_rate = (analysis["long_enrollment_count"] / total * 100) if total > 0 else 0

            risk_data.append(
                {
                    "program_name": analysis["program__name"],
                    "division": analysis["division"],
                    "cycle": analysis["cycle"],
                    "total_active_students": total,
                    "low_completion_count": analysis["low_completion_count"],
                    "low_completion_rate_percent": round(low_completion_rate, 2),
                    "long_enrollment_count": analysis["long_enrollment_count"],
                    "long_enrollment_rate_percent": round(long_enrollment_rate, 2),
                    "avg_completion_percentage": round(analysis["avg_completion"] or 0, 2),
                    "avg_terms_active": round(analysis["avg_terms_active"] or 0, 1),
                    "overall_risk_score": round((low_completion_rate + long_enrollment_rate) / 2, 2),
                },
            )

        return risk_data

    def _analyze_term_retention(self) -> list[dict]:
        """Analyze term-by-term retention rates and enrollment patterns."""
        recent_terms = Term.objects.filter(start_date__gte=timezone.now().date() - timedelta(days=365 * 3)).order_by(
            "-start_date",
        )[:12]

        retention_data = []
        for term in recent_terms:
            term_enrollments = ClassHeaderEnrollment.objects.filter(class_header__term=term)

            total_enrolled = term_enrollments.count()
            completed = term_enrollments.filter(status__in=["COMPLETED", "ACTIVE"]).count()
            dropped = term_enrollments.filter(status__in=["DROPPED", "WITHDRAWN", "FAILED"]).count()
            no_show = term_enrollments.filter(status__in=["NO_SHOW_ACADEMIC", "NO_SHOW_LANGUAGE"]).count()

            retention_rate = (completed / total_enrolled * 100) if total_enrolled > 0 else 0
            dropout_rate = (dropped / total_enrolled * 100) if total_enrolled > 0 else 0
            no_show_rate = (no_show / total_enrolled * 100) if total_enrolled > 0 else 0

            retention_data.append(
                {
                    "term_code": term.code,
                    "term_name": term.full_name,
                    "start_date": term.start_date.isoformat(),
                    "end_date": term.end_date.isoformat() if term.end_date else None,
                    "total_enrolled": total_enrolled,
                    "completed_count": completed,
                    "dropped_count": dropped,
                    "no_show_count": no_show,
                    "retention_rate_percent": round(retention_rate, 2),
                    "dropout_rate_percent": round(dropout_rate, 2),
                    "no_show_rate_percent": round(no_show_rate, 2),
                },
            )

        return retention_data

    def _generate_executive_summary(self) -> dict:
        """Generate executive summary with key metrics."""
        total_enrollments = ProgramEnrollment.objects.count()
        active_enrollments = ProgramEnrollment.objects.filter(status="ACTIVE").count()
        completed_enrollments = ProgramEnrollment.objects.filter(status="COMPLETED").count()
        dropped_enrollments = ProgramEnrollment.objects.filter(status__in=["DROPPED", "WITHDRAWN", "FAILED"]).count()

        overall_completion_rate = (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0
        overall_dropout_rate = (dropped_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0

        division_summary = ProgramEnrollment.objects.values("division").annotate(
            total=Count("id"),
            completed=Count("id", filter=Q(status="COMPLETED")),
            active=Count("id", filter=Q(status="ACTIVE")),
            dropped=Count("id", filter=Q(status__in=["DROPPED", "WITHDRAWN", "FAILED"])),
        )

        division_stats = {}
        for div in division_summary:
            total = div["total"]
            completion_rate = (div["completed"] / total * 100) if total > 0 else 0
            dropout_rate = (div["dropped"] / total * 100) if total > 0 else 0

            division_stats[div["division"]] = {
                "total_enrollments": total,
                "completion_rate_percent": round(completion_rate, 2),
                "dropout_rate_percent": round(dropout_rate, 2),
                "active_count": div["active"],
            }

        at_risk_students = ProgramEnrollment.objects.filter(status="ACTIVE", completion_percentage__lt=25).count()

        return {
            "report_generated": timezone.now().isoformat(),
            "overall_metrics": {
                "total_enrollments": total_enrollments,
                "active_enrollments": active_enrollments,
                "completed_enrollments": completed_enrollments,
                "dropped_enrollments": dropped_enrollments,
                "overall_completion_rate_percent": round(overall_completion_rate, 2),
                "overall_dropout_rate_percent": round(overall_dropout_rate, 2),
                "at_risk_students": at_risk_students,
            },
            "division_breakdown": division_stats,
            "recommendations": [
                "Monitor students with <25% completion for early intervention",
                "Investigate high dropout rates in programs with >30% dropout",
                "Review transition pathways for language to academic programs",
                "Implement retention strategies for identified at-risk populations",
            ],
        }

    def _save_report(self, report_name: str, data) -> str:
        """Save report data to file in specified format."""
        filename = f"{report_name}_{self.timestamp}.{self.output_format}"
        filepath = self.output_dir / filename

        if self.output_format == "csv":
            self._save_as_csv(filepath, data)
        elif self.output_format == "json":
            self._save_as_json(filepath, data)
        else:
            raise CommandError(f"Unsupported output format: {self.output_format}")

        return str(filepath)

    def _save_as_csv(self, filepath: Path, data):
        """Save data as CSV file."""
        if isinstance(data, dict):
            if "transition_patterns" in data:
                for section_name, section_data in data.items():
                    section_filepath = filepath.parent / f"{filepath.stem}_{section_name}.csv"
                    if section_data:
                        with open(section_filepath, "w", newline="", encoding="utf-8") as f:
                            if isinstance(section_data, list) and len(section_data) > 0:
                                writer = csv.DictWriter(f, fieldnames=section_data[0].keys())
                                writer.writeheader()
                                writer.writerows(section_data)
            else:
                with open(str(filepath).replace(".csv", ".json"), "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, default=str)
        elif isinstance(data, list) and len(data) > 0:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=data[0].keys())
                writer.writeheader()
                writer.writerows(data)

    def _save_as_json(self, filepath: Path, data):
        """Save data as JSON file."""
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
