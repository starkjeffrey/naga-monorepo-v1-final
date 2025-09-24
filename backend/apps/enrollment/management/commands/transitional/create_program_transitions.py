"""Create ProgramPeriod records to track each program change with duration.

This command analyzes enrollment data to create a record for each distinct
program period, including language programs (IEAP, GESL, EHSS), BA programs,
and MA programs.
"""

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Count

from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Major
from apps.enrollment.models import ClassHeaderEnrollment
from apps.enrollment.models_progression import ProgramPeriod
from apps.people.models import StudentProfile


class Command(BaseMigrationCommand):
    """Create detailed program period records."""

    help = "Generate ProgramPeriod records tracking each program change"

    def get_rejection_categories(self) -> list[str]:
        """Return possible rejection categories."""
        return [
            "no_enrollments",
            "data_conflict",
            "database_error",
            "validation_error",
        ]

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument("--student-id", type=str, help="Process specific student ID (e.g., 10774)")
        parser.add_argument("--dry-run", action="store_true", help="Run without creating database records")
        parser.add_argument(
            "--clear-existing", action="store_true", help="Clear existing transition records before creating"
        )

    def execute_migration(self, *args, **options):
        """Execute the program transition creation."""
        student_id = options.get("student_id")
        dry_run = options.get("dry_run", False)
        clear_existing = options.get("clear_existing", False)

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No changes will be made"))

        # Clear existing if requested
        if clear_existing and not dry_run:
            count = ProgramPeriod.objects.all().delete()[0]
            self.stdout.write(f"Cleared {count} existing program periods")

        # Get students to process
        if student_id:
            students = StudentProfile.objects.filter(student_id=student_id)
        else:
            students = StudentProfile.objects.annotate(enrollment_count=Count("class_header_enrollments")).filter(
                enrollment_count__gt=0
            )

        total = students.count()
        self.stdout.write(f"Processing {total} students...")

        for idx, student in enumerate(students):
            try:
                self.process_student(student, dry_run)
                if idx % 100 == 0:
                    self.stdout.write(f"Progress: {idx}/{total}")
            except Exception as e:
                self.record_rejection(
                    category="database_error",
                    record_id=str(student.id),
                    reason=str(e),
                    raw_data={"student_id": student.student_id},
                )

    def process_student(self, student: StudentProfile, dry_run: bool):
        """Process a single student's program transitions."""
        # Get all enrollments ordered by term
        enrollments = list(
            ClassHeaderEnrollment.objects.filter(student=student)
            .select_related("class_header__course", "class_header__term")
            .order_by("class_header__term__start_date")
        )

        if not enrollments:
            return

        # Group enrollments into program periods
        program_periods = self.detect_program_periods(enrollments)

        if dry_run:
            self.stdout.write(f"\nStudent {student.student_id}:")
            for period in program_periods:
                self.stdout.write(
                    f"  {period['program_type']}: {period['start_date']} to "
                    f"{period['end_date']} ({period['duration_days']} days)"
                )
        else:
            # Create transition records
            with transaction.atomic():
                for i, period in enumerate(program_periods):
                    self.create_transition_record(
                        student=student,
                        period=period,
                        sequence_number=i + 1,
                        previous_period=program_periods[i - 1] if i > 0 else None,
                        next_period=program_periods[i + 1] if i < len(program_periods) - 1 else None,
                    )

    def detect_program_periods(self, enrollments: list) -> list[dict]:
        """Detect distinct program periods from enrollments."""
        periods = []
        current_period = None

        for enrollment in enrollments:
            program_type = self.determine_program_type(enrollment)
            term_start = enrollment.class_header.term.start_date
            term_end = enrollment.class_header.term.end_date

            if current_period is None:
                # Start first period
                current_period = {
                    "program_type": program_type,
                    "program_name": self.get_program_name(program_type, enrollment),
                    "start_date": term_start,
                    "end_date": term_end,
                    "enrollments": [enrollment],
                    "terms": {enrollment.class_header.term.id},
                    "courses": [],
                }
            elif program_type != current_period["program_type"]:
                # Program changed - close current and start new
                periods.append(self.finalize_period(current_period))
                current_period = {
                    "program_type": program_type,
                    "program_name": self.get_program_name(program_type, enrollment),
                    "start_date": term_start,
                    "end_date": term_end,
                    "enrollments": [enrollment],
                    "terms": {enrollment.class_header.term.id},
                    "courses": [],
                }
            else:
                current_period["end_date"] = max(current_period["end_date"], term_end)
                current_period["enrollments"].append(enrollment)
                current_period["terms"].add(enrollment.class_header.term.id)

        # Add final period
        if current_period:
            periods.append(self.finalize_period(current_period))

        return periods

    def determine_program_type(self, enrollment: ClassHeaderEnrollment) -> str:
        """Determine the program type from enrollment."""
        course_code = enrollment.class_header.course.code

        # Check for specific language programs
        if "IEAP" in course_code:
            return "IEAP"
        elif "GESL" in course_code:
            return "GESL"
        elif "EHSS" in course_code:
            return "EHSS"
        elif "ELL" in course_code:
            return "LANGUAGE_OTHER"
        # Check for graduate level (500+)
        elif "-" in course_code:
            try:
                level = int(course_code.split("-")[1][:3])
                if level >= 500:
                    return "MA"
            except (ValueError, IndexError):
                pass

        # Default to BA
        return "BA"

    def get_program_name(self, program_type: str, enrollment: ClassHeaderEnrollment) -> str:
        """Get the full program name."""
        program_names = {
            "IEAP": "Intensive English for Academic Purposes",
            "GESL": "General English as a Second Language",
            "EHSS": "English for High School Students",
            "LANGUAGE_OTHER": "English Language Learning",
            "BA": "Bachelor of Arts",
            "MA": "Master of Arts",
        }
        return program_names.get(program_type, program_type)

    def finalize_period(self, period: dict) -> dict:
        """Finalize a program period with calculated metrics."""
        # Calculate duration
        period["duration_days"] = (period["end_date"] - period["start_date"]).days + 1
        period["duration_months"] = period["duration_days"] / 30.4
        period["term_count"] = len(period["terms"])

        # Calculate credits and grades
        total_credits = Decimal("0")
        completed_credits = Decimal("0")
        grade_points = Decimal("0")
        graded_credits = Decimal("0")

        grade_values = {
            "A+": 4.0,
            "A": 4.0,
            "A-": 3.7,
            "B+": 3.3,
            "B": 3.0,
            "B-": 2.7,
            "C+": 2.3,
            "C": 2.0,
            "C-": 1.7,
            "D+": 1.3,
            "D": 1.0,
            "D-": 0.7,
            "F": 0.0,
        }

        for enrollment in period["enrollments"]:
            credits = enrollment.class_header.course.credits or Decimal("0")
            total_credits += credits

            # Count all passing grades including plus/minus grades
            if enrollment.final_grade in ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "CR"]:
                completed_credits += credits

            if enrollment.final_grade in grade_values:
                grade_points += Decimal(str(grade_values[enrollment.final_grade])) * credits
                graded_credits += credits

            period["courses"].append(
                {
                    "code": enrollment.class_header.course.code,
                    "name": enrollment.class_header.course.title,
                    "credits": float(credits),
                    "grade": enrollment.final_grade,
                    "term": enrollment.class_header.term.code,
                }
            )

        period["total_credits"] = float(total_credits)
        period["completed_credits"] = float(completed_credits)
        period["gpa"] = float(grade_points / graded_credits) if graded_credits > 0 else None

        # Detect completion status
        period["status"] = self.detect_period_status(period)

        # For language programs, detect level progression
        if period["program_type"] in ["IEAP", "GESL", "EHSS"]:
            period["levels"] = self.detect_language_levels(period["enrollments"])
            period["final_level"] = max(period["levels"]) if period["levels"] else None

        return period

    def detect_period_status(self, period: dict) -> str:
        """Detect the completion status of a period."""
        program_type = period["program_type"]

        # Language program completion
        if program_type == "IEAP" and period.get("final_level") == 4:
            return "COMPLETED"
        elif program_type in ["GESL", "EHSS"] and period.get("final_level") == 12:
            return "COMPLETED"

        # BA/MA graduation detection
        elif program_type == "BA":
            # Check for graduation indicators
            has_exit_exam = any(
                "EXIT" in course["code"].upper() or "COMEX" in course["code"] for course in period.get("courses", [])
            )

            # Standard BA requires 120 credits, but check for exit exam as indicator
            if period["completed_credits"] >= 120 or (has_exit_exam and period["completed_credits"] >= 100):
                return "GRADUATED"

            # Special case: High GPA with substantial credits may indicate graduation
            if period.get("gpa") and period["gpa"] >= 3.5 and period["completed_credits"] >= 110:
                return "GRADUATED"

        elif program_type == "MA" and period["completed_credits"] >= 30:
            return "GRADUATED"

        # Check if still active (recent enrollment)
        months_since = (date.today() - period["end_date"]).days / 30
        if months_since < 6:
            return "ACTIVE"
        elif months_since < 24:
            return "INACTIVE"
        else:
            # Don't mark as dropped if they likely graduated
            if program_type == "BA" and period["completed_credits"] >= 100 and period.get("gpa", 0) >= 3.0:
                return "GRADUATED"
            return "DROPPED"

    def detect_language_levels(self, enrollments: list) -> list[int]:
        """Extract language program levels from enrollments."""
        levels = []
        for enrollment in enrollments:
            code = enrollment.class_header.course.code
            if "-" in code:
                try:
                    # Extract first digit of course number as level
                    level = int(code.split("-")[1][0])
                    levels.append(level)
                except (ValueError, IndexError):
                    pass
        return sorted(set(levels))

    def create_transition_record(
        self,
        student: StudentProfile,
        period: dict,
        sequence_number: int,
        previous_period: dict | None = None,
        next_period: dict | None = None,
    ):
        """Create a ProgramTransition record."""
        # Determine transition type
        if sequence_number == 1:
            transition_type = "INITIAL"
        elif previous_period and previous_period["program_type"] != period["program_type"]:
            transition_type = "CHANGE"
        elif previous_period and previous_period["status"] == "COMPLETED":
            transition_type = "PROGRESSION"
        else:
            transition_type = "CONTINUATION"

        # Try to find the Major object
        major = None
        if period["program_type"] == "BA":
            # Use major detection logic here
            major = self.detect_ba_major(period["enrollments"])

        ProgramPeriod.objects.create(
            journey=student.academic_journey,
            transition_type=transition_type,
            transition_date=period["start_date"],
            from_program_type=previous_period["program_type"] if previous_period else None,
            to_program_type=period["program_type"],
            to_program=major,
            program_name=period["program_name"],
            duration_days=period["duration_days"],
            duration_months=period["duration_months"],
            term_count=period["term_count"],
            total_credits=period["total_credits"],
            completed_credits=period["completed_credits"],
            gpa=period.get("gpa"),
            completion_status=period["status"],
            language_level=str(period.get("final_level", "")) if period.get("final_level") else "",
            sequence_number=sequence_number,
            confidence_score=Decimal("0.9"),  # High confidence for direct data
            notes=f"{len(period['courses'])} courses taken",
        )

    def detect_ba_major(self, enrollments: list) -> Major:
        """Detect BA major from enrollments (simplified)."""
        # This would use the same logic as progression_builder.py
        # For now, return None
        return None
