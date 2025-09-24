"""Management command to reconcile course equivalency fulfillments.

This command processes historical data to create fulfillment records for students
who completed equivalent courses before the enhanced fulfillment system was active.

Key features:
- Batch processing with progress tracking
- Dry-run mode for validation
- Comprehensive audit reporting
- Error handling and validation
"""

from typing import Any, cast

from django.core.management.base import CommandError, CommandParser
from django.db import models, transaction
from django.utils import timezone

from apps.academic.models import CourseEquivalency, StudentDegreeProgress
from apps.academic.services.fulfillment import CanonicalFulfillmentService
from apps.common.management.base_migration import BaseMigrationCommand
from apps.enrollment.models import ClassHeaderEnrollment, ProgramEnrollment


class Command(BaseMigrationCommand):
    """Reconcile course equivalency fulfillments for historical data."""

    help = "Create fulfillment records for students who completed equivalent courses"

    def add_arguments(self, parser: CommandParser) -> None:
        """Add command-line arguments."""
        super().add_arguments(parser)

        parser.add_argument(
            "--equivalency-course",
            type=str,
            help="Course code of the equivalent course (e.g., COMEX-488)",
        )

        parser.add_argument(
            "--target-course",
            type=str,
            help="Course code of the target requirement course (e.g., IR-489)",
        )

        parser.add_argument(
            "--term-from",
            type=str,
            help="Process enrollments from this term onwards (e.g., 2021T3)",
        )

        parser.add_argument(
            "--term-to",
            type=str,
            help="Process enrollments up to this term (e.g., 2024T2)",
        )

        parser.add_argument(
            "--student-id",
            type=int,
            help="Process specific student only (for testing)",
        )

        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of enrollments to process per batch (default: 100)",
        )

    def get_migration_name(self) -> str:
        """Return migration name for audit purposes."""
        equivalency_course = self.options.get("equivalency_course", "UNKNOWN")
        target_course = self.options.get("target_course", "UNKNOWN")
        return f"reconcile_equivalency_{equivalency_course}_to_{target_course}"

    def get_rejection_categories(self) -> list[str]:
        """Return list of possible rejection categories."""
        return [
            "NO_PASSING_GRADE",
            "NO_ACTIVE_PROGRAMS",
            "NO_EQUIVALENCY_REQUIREMENTS",
            "ALREADY_FULFILLED",
            "PROCESSING_ERROR",
        ]

    def execute_migration(self, *args, **options) -> dict[str, Any]:
        """Execute the migration and return results."""
        return self.handle_migration(*args, **options)

    def handle_migration(self, *args, **options) -> dict[str, Any]:
        """Main migration logic."""
        self.options = options

        # Validate inputs
        self.validate_inputs()

        # Find relevant equivalencies
        equivalencies = self.find_equivalencies()
        if not equivalencies:
            raise CommandError("No active equivalencies found matching criteria")

        self.stdout.write(f"Found {len(equivalencies)} active equivalencies")

        # Find eligible enrollments
        enrollments = self.find_eligible_enrollments(equivalencies)
        self.stdout.write(f"Found {len(enrollments)} eligible enrollments to process")

        if not enrollments:
            self.stdout.write(self.style.WARNING("No enrollments found to process"))
            return {"processed": 0, "created": 0, "skipped": 0, "errors": 0}

        # Process enrollments in batches
        return self.process_enrollments(enrollments, equivalencies)

    def validate_inputs(self) -> None:
        """Validate command inputs."""
        equivalency_course = self.options.get("equivalency_course")
        target_course = self.options.get("target_course")

        if equivalency_course:
            from apps.curriculum.models import Course

            try:
                Course.objects.get(code=equivalency_course)
            except Course.DoesNotExist as e:
                raise CommandError(f"Course {equivalency_course} not found") from e

        if target_course:
            from apps.curriculum.models import Course

            try:
                Course.objects.get(code=target_course)
            except Course.DoesNotExist as e:
                raise CommandError(f"Course {target_course} not found") from e

    def find_equivalencies(self) -> list[CourseEquivalency]:
        """Find relevant course equivalencies."""
        from apps.curriculum.models import Course

        equivalencies = CourseEquivalency.objects.filter(is_active=True)

        # Filter by equivalency course if specified
        if self.options.get("equivalency_course"):
            course = Course.objects.get(code=self.options["equivalency_course"])
            equivalencies = equivalencies.filter(
                models.Q(original_course=course) | models.Q(equivalent_course=course, bidirectional=True)
            )

        # Filter by target course if specified
        if self.options.get("target_course"):
            course = Course.objects.get(code=self.options["target_course"])
            equivalencies = equivalencies.filter(
                models.Q(original_course=course) | models.Q(equivalent_course=course, bidirectional=True)
            )

        return list(equivalencies.select_related("original_course", "equivalent_course", "effective_term", "end_term"))

    def find_eligible_enrollments(self, equivalencies: list[CourseEquivalency]) -> list[ClassHeaderEnrollment]:
        """Find enrollments that completed equivalent courses."""

        from apps.curriculum.models import Term

        # Get all courses that appear in equivalencies
        equivalent_courses = set()
        for equiv in equivalencies:
            equivalent_courses.add(equiv.original_course)
            equivalent_courses.add(equiv.equivalent_course)

        # Base enrollment query
        enrollments = ClassHeaderEnrollment.objects.filter(
            class_header__course__in=equivalent_courses,
            status="COMPLETED",
        ).select_related("student", "class_header__course", "class_header__term")

        # Filter by term range if specified
        if self.options.get("term_from"):
            from_term = Term.objects.get(term_id=self.options["term_from"])
            enrollments = enrollments.filter(class_header__term__start_date__gte=from_term.start_date)

        if self.options.get("term_to"):
            to_term = Term.objects.get(term_id=self.options["term_to"])
            enrollments = enrollments.filter(class_header__term__start_date__lte=to_term.start_date)

        # Filter by student if specified
        if self.options.get("student_id"):
            enrollments = enrollments.filter(student_id=self.options["student_id"])

        return list(enrollments)

    @transaction.atomic
    def process_enrollments(
        self, enrollments: list[ClassHeaderEnrollment], equivalencies: list[CourseEquivalency]
    ) -> dict[str, Any]:
        """Process enrollments and create fulfillments."""
        results: dict[str, Any] = {"processed": 0, "created": 0, "skipped": 0, "errors": 0, "details": []}

        batch_size = self.options.get("batch_size", 100)

        for i in range(0, len(enrollments), batch_size):
            batch = enrollments[i : i + batch_size]
            batch_results = self.process_batch(batch, equivalencies)

            # Aggregate results
            for key in ["processed", "created", "skipped", "errors"]:
                results[key] += batch_results[key]
            results["details"].extend(batch_results["details"])

            self.stdout.write(
                f"Processed batch {i // batch_size + 1}: "
                f"{batch_results['created']} created, {batch_results['skipped']} skipped, "
                f"{batch_results['errors']} errors"
            )

        return results

    def process_batch(
        self, enrollments: list[ClassHeaderEnrollment], equivalencies: list[CourseEquivalency]
    ) -> dict[str, Any]:
        """Process a batch of enrollments."""
        results: dict[str, Any] = {"processed": 0, "created": 0, "skipped": 0, "errors": 0, "details": []}

        for enrollment in enrollments:
            try:
                result = self.process_enrollment(enrollment, equivalencies)
                results["processed"] += 1

                if result["created"]:
                    results["created"] += len(result["fulfillments"])
                    # Safely access related attributes for typing
                    student_pk = getattr(enrollment.student, "pk", None)
                    ch: Any = enrollment.class_header
                    course_code = getattr(getattr(ch, "course", None), "code", "")
                    term_code = getattr(getattr(ch, "term", None), "code", "")
                    results["details"].append(
                        {
                            "student_id": student_pk,
                            "course": course_code,
                            "term": term_code,
                            "fulfillments_created": len(result["fulfillments"]),
                            "requirements": [f.canonical_requirement.id for f in result["fulfillments"]],
                        }
                    )
                else:
                    results["skipped"] += 1

            except Exception as e:
                results["errors"] += 1
                student_pk = getattr(enrollment.student, "pk", None)
                ch_err: Any = enrollment.class_header
                course_code = getattr(getattr(ch_err, "course", None), "code", "")
                results["details"].append(
                    {
                        "student_id": student_pk,
                        "course": course_code,
                        "error": str(e),
                    }
                )

                if not self.options.get("dry_run"):
                    enrollment_id = getattr(enrollment, "pk", None) or getattr(enrollment, "id", None)
                    self.stderr.write(f"Error processing enrollment {enrollment_id}: {e}")

        return results

    def process_enrollment(
        self, enrollment: ClassHeaderEnrollment, equivalencies: list[CourseEquivalency]
    ) -> dict[str, Any]:
        """Process a single enrollment for equivalency fulfillments."""
        # Check if enrollment has passing grade
        session_grade = cast(Any, enrollment).class_session_grades.filter(enrollment=enrollment).order_by(
            "-calculated_at"
        ).first()

        if not session_grade or not self.is_passing_grade(session_grade.letter_grade):
            return {"created": False, "reason": "No passing grade", "fulfillments": []}

        # Get student's active programs during enrollment term
        active_programs = ProgramEnrollment.objects.filter(
            student=enrollment.student,
            enrollment_status="ACTIVE",
        ).select_related("program")

        fulfillments_created: list[Any] = []

        for program in active_programs:
            # Find requirements this course could fulfill via equivalency
            ch: Any = enrollment.class_header
            fulfillable_requirements = CanonicalFulfillmentService.find_fulfillable_requirements(
                course=getattr(ch, "course", None),
                major=program.program,
                term=getattr(ch, "term", None),
            )

            # Filter to only requirements fulfilled via equivalency (not direct matches)
            equivalency_requirements = []
            for req in fulfillable_requirements:
                if req.required_course != getattr(ch, "course", None):
                    equivalency_requirements.append(req)

            # Create fulfillments for unmet requirements
            for requirement in equivalency_requirements:
                existing = StudentDegreeProgress.objects.filter(
                    student=enrollment.student,
                    canonical_requirement=requirement,
                    is_active=True,
                ).exists()

                if not existing and not self.options.get("dry_run"):
                    fulfillment = CanonicalFulfillmentService.create_course_fulfillment(
                        student=enrollment.student,
                        enrollment=enrollment,
                        grade=session_grade.letter_grade,
                        canonical_requirement=requirement,
                    )
                    fulfillments_created.append(fulfillment)
                elif not existing:
                    # Dry run - create mock fulfillment object
                    mock_fulfillment = type(
                        "MockFulfillment",
                        (),
                        {
                            "canonical_requirement": requirement,
                            "student": enrollment.student,
                            "grade": session_grade.letter_grade,
                        },
                    )()
                    fulfillments_created.append(mock_fulfillment)

        return {"created": len(fulfillments_created) > 0, "fulfillments": fulfillments_created}

    def is_passing_grade(self, grade: str) -> bool:
        """Check if grade is passing."""
        passing_grades = ["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "P"]
        return grade in passing_grades

    def generate_summary_report(self, results: dict[str, Any]) -> dict[str, Any]:
        """Generate summary report."""
        return {
            "migration_name": self.get_migration_name(),
            "timestamp": timezone.now().isoformat(),
            "dry_run": self.options.get("dry_run", False),
            "statistics": {
                "enrollments_processed": results["processed"],
                "fulfillments_created": results["created"],
                "enrollments_skipped": results["skipped"],
                "errors_encountered": results["errors"],
            },
            "filters_applied": {
                "equivalency_course": self.options.get("equivalency_course"),
                "target_course": self.options.get("target_course"),
                "term_from": self.options.get("term_from"),
                "term_to": self.options.get("term_to"),
                "student_id": self.options.get("student_id"),
            },
            "sample_results": results["details"][:10],  # First 10 for brevity
        }
