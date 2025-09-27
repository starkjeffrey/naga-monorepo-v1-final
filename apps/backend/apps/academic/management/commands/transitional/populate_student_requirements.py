"""[DEPRECATED] Populate StudentRequirementFulfillment records based on student major declarations.

⚠️ DEPRECATED: This command uses the legacy requirement system (StudentRequirementFulfillment).
The new system uses CanonicalRequirement and StudentDegreeProgress models.
This command should not be used and will be removed in a future version.

This script creates StudentRequirementFulfillment records for all students with
MajorDeclaration records by:
1. Finding their declared major
2. Getting all CanonicalRequirements for that major
3. Checking their ClassEnrollments for courses that fulfill requirements
4. Creating fulfillment records for passed courses

Business Logic:
- Only processes students with active major declarations
- Only counts courses with passing grades (D or better, 1.0 GPA)
- Uses term start date as fulfillment date
- Tracks credits applied toward each requirement
- Generates comprehensive audit reports
"""

import time
from datetime import datetime
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from apps.academic.canonical_models import CanonicalRequirement
from apps.academic.models import StudentRequirementFulfillment
from apps.common.management.base_migration import BaseMigrationCommand
from apps.enrollment.models import ClassEnrollment, MajorDeclaration
from apps.people.models import StudentProfile


class Command(BaseMigrationCommand):
    """Populate student requirement fulfillments based on major declarations."""

    help = "Create StudentRequirementFulfillment records for students with declared majors"

    # Grade point values for determining passing grades
    PASSING_GRADE_POINTS = Decimal("1.0")  # D or better

    def get_rejection_categories(self) -> list[str]:
        """Return list of possible rejection categories for this migration."""
        return [
            "no_major_declaration",
            "no_canonical_requirements",
            "no_enrollments",
            "duplicate_fulfillment",
            "validation_error",
            "database_error",
        ]

    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            "--student-id",
            type=str,
            help="Process only a specific student ID (for testing)",
        )
        parser.add_argument(
            "--major-code",
            type=str,
            help="Process only students with this major code",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Perform a dry run without saving data",
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Clear existing fulfillment records before populating",
        )

    def execute_migration(self, *args, **options):
        """Execute the migration with comprehensive tracking."""
        student_id = options.get("student_id")
        major_code = options.get("major_code")
        dry_run = options.get("dry_run", False)
        clear_existing = options.get("clear_existing", False)

        # Update audit tracking with migration-specific info
        self.audit_data["migration_info"].update(
            {
                "student_id": student_id,
                "major_code": major_code,
                "dry_run": dry_run,
                "clear_existing": clear_existing,
            },
        )

        # Clear existing records if requested
        if clear_existing and not dry_run:
            self._clear_existing_fulfillments()

        # Get students to process
        students = self._get_students_to_process(student_id, major_code)

        total_students = students.count()
        total_processed = 0
        successful_students = 0
        total_fulfillments_created = 0

        self.stdout.write(f"Found {total_students} students to process")

        with transaction.atomic():
            for student in students:
                total_processed += 1

                result = self._process_student(student, dry_run)
                if result["success"]:
                    successful_students += 1
                    total_fulfillments_created += result["fulfillments_created"]

                # Progress reporting
                if total_processed % 50 == 0:
                    self.stdout.write(
                        f"Processed {total_processed}/{total_students} students, "
                        f"{successful_students} successful, "
                        f"{total_fulfillments_created} fulfillments created",
                    )

            if dry_run:
                # Rollback transaction for dry run
                transaction.set_rollback(True)

        # Update audit summary
        self.audit_data["summary"]["input"]["total_students"] = total_students
        self.audit_data["summary"]["output"]["successful_students"] = successful_students
        self.audit_data["summary"]["output"]["fulfillments_created"] = total_fulfillments_created
        self.audit_data["summary"]["rejected"]["total_rejected"] = total_processed - successful_students

        # Calculate performance metrics
        self._calculate_performance_metrics(total_processed, successful_students)

        # Generate samples
        self._generate_samples()

        # Output summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\nMigration completed!\n"
                f"Total students processed: {total_processed}\n"
                f"Successful students: {successful_students}\n"
                f"Total fulfillments created: {total_fulfillments_created}\n"
                f"Rejected: {total_processed - successful_students}\n"
                f"Dry run: {dry_run}",
            ),
        )

    def _clear_existing_fulfillments(self):
        """Clear existing StudentRequirementFulfillment records."""
        count = StudentRequirementFulfillment.objects.all().count()
        StudentRequirementFulfillment.objects.all().delete()
        self.stdout.write(f"Cleared {count} existing fulfillment records")

    def _get_students_to_process(self, student_id: str | None = None, major_code: str | None = None):
        """Get queryset of students to process."""
        # Start with students who have active major declarations
        students = StudentProfile.objects.filter(
            major_declarations__is_active=True,
            major_declarations__is_effective=True,
        ).distinct()

        # Filter by specific student if provided
        if student_id:
            students = students.filter(student_id=student_id)

        # Filter by major code if provided
        if major_code:
            students = students.filter(major_declarations__major__code=major_code)

        # Prefetch related data for efficiency
        students = students.prefetch_related(
            Prefetch(
                "major_declarations",
                queryset=MajorDeclaration.objects.filter(is_active=True).select_related("major"),
                to_attr="active_declarations",
            ),
            Prefetch(
                "class_enrollments",
                queryset=ClassEnrollment.objects.select_related("class_section__course", "grade").filter(
                    enrollment_status=ClassEnrollment.EnrollmentStatus.ENROLLED,
                ),
                to_attr="all_enrollments",
            ),
        )

        return students.order_by("student_id")

    def _process_student(self, student: StudentProfile, dry_run: bool) -> dict[str, Any]:
        """Process a single student."""
        result = {
            "success": False,
            "fulfillments_created": 0,
            "rejection_reason": None,
        }

        try:
            # Get current major declaration
            current_declaration = student.active_declarations[0] if student.active_declarations else None

            if not current_declaration:
                self._record_rejection(
                    "no_major_declaration",
                    student.student_id,
                    "No active major declaration found",
                    {"student_id": student.student_id},
                )
                result["rejection_reason"] = "no_major_declaration"
                return result

            major = current_declaration.major

            # Get canonical requirements for the major
            requirements = CanonicalRequirement.objects.filter(major=major, is_active=True).select_related("course")

            if not requirements.exists():
                self._record_rejection(
                    "no_canonical_requirements",
                    student.student_id,
                    f"No canonical requirements found for major {major.code}",
                    {"student_id": student.student_id, "major": major.code},
                )
                result["rejection_reason"] = "no_canonical_requirements"
                return result

            # Get student's enrollments with passing grades
            passing_enrollments = self._get_passing_enrollments(student)

            if not passing_enrollments:
                self._record_rejection(
                    "no_enrollments",
                    student.student_id,
                    "No passing enrollments found",
                    {"student_id": student.student_id},
                )
                result["rejection_reason"] = "no_enrollments"
                return result

            # Create fulfillment records
            fulfillments_created = 0

            for requirement in requirements:
                # Check if student has completed this course
                matching_enrollment = next(
                    (e for e in passing_enrollments if e.class_section.course == requirement.course),
                    None,
                )

                if matching_enrollment:
                    # Create fulfillment record
                    if not dry_run:
                        # Use term start date for fulfillment date
                        term = matching_enrollment.class_section.term
                        fulfillment_date = (
                            timezone.make_aware(datetime.combine(term.start_date, datetime.min.time()))
                            if term.start_date
                            else timezone.now()
                        )

                        fulfillment, created = StudentRequirementFulfillment.objects.get_or_create(
                            student=student,
                            requirement=requirement,
                            defaults={
                                "fulfillment_source": (
                                    StudentRequirementFulfillment.FulfillmentSource.COURSE_COMPLETION
                                ),
                                "credits_applied": requirement.course.credit_hours,
                                "courses_applied": 1,
                                "fulfilling_course": requirement.course,
                                "is_fulfilled": True,
                                "fulfillment_date": fulfillment_date,
                                "notes": (
                                    f"Auto-populated from class enrollment. "
                                    f"Grade: {matching_enrollment.grade.letter_grade if matching_enrollment.grade else 'N/A'}. "  # noqa: E501
                                    f"Term: {matching_enrollment.class_section.term.code}"
                                ),
                            },
                        )

                        if created:
                            fulfillments_created += 1
                        else:
                            # Update existing record if needed
                            if not fulfillment.is_fulfilled:
                                fulfillment.is_fulfilled = True
                                fulfillment.fulfillment_date = timezone.now()
                                fulfillment.save()

            result["success"] = True
            result["fulfillments_created"] = fulfillments_created

        except Exception as e:
            self._record_rejection(
                "database_error",
                student.student_id,
                f"Unexpected error: {e!s}",
                {"student_id": student.student_id},
            )
            result["rejection_reason"] = "database_error"

        return result

    def _get_passing_enrollments(self, student: StudentProfile) -> list[ClassEnrollment]:
        """Get student's enrollments with passing grades."""
        passing_enrollments = []

        for enrollment in student.all_enrollments:
            # Check if student has a passing grade
            if enrollment.grade:
                # Consider grades with 1.0 (D) or better as passing
                if enrollment.grade.grade_points >= self.PASSING_GRADE_POINTS:
                    passing_enrollments.append(enrollment)
            # If no grade yet, check if course is in progress
            elif enrollment.enrollment_status == ClassEnrollment.EnrollmentStatus.ENROLLED:
                # Don't count in-progress courses
                continue

        return passing_enrollments

    def _record_rejection(self, category: str, student_id: str, reason: str, data: dict):
        """Record a rejected student with categorization."""
        if category not in self.detailed_rejections:
            self.detailed_rejections[category] = []

        self.detailed_rejections[category].append(
            {
                "student_id": student_id,
                "reason": reason,
                "data": data,
            },
        )

        # Update summary counts
        if category not in self.audit_data["summary"]["rejected"]["rejection_breakdown"]:
            self.audit_data["summary"]["rejected"]["rejection_breakdown"][category] = 0
        self.audit_data["summary"]["rejected"]["rejection_breakdown"][category] += 1

    def _calculate_performance_metrics(self, total_processed: int, successful_students: int):
        """Calculate performance metrics for audit report."""
        duration = time.time() - self.migration_start_time

        self.audit_data["performance_metrics"] = {
            "total_duration_seconds": round(duration, 2),
            "students_per_second": (round(total_processed / duration, 2) if duration > 0 else 0),
            "success_rate_percentage": (
                round((successful_students / total_processed * 100), 2) if total_processed > 0 else 0
            ),
        }

    def _generate_samples(self):
        """Generate sample data for audit report."""
        # Sample successful fulfillments
        sample_fulfillments = (
            StudentRequirementFulfillment.objects.filter(notes__contains="Auto-populated from class enrollment")
            .select_related("student", "requirement__course", "requirement__major")
            .order_by("-created_at")[:10]
        )

        self.audit_data["samples"]["successful_fulfillments"] = [
            {
                "student_id": f.student.student_id,
                "major": f.requirement.major.code,
                "course": f.requirement.course.code,
                "credits": str(f.credits_applied),
                "fulfilled": f.is_fulfilled,
                "notes": f.notes,
            }
            for f in sample_fulfillments
        ]

        # Sample rejections
        sample_rejections = {}
        for category, rejections in self.detailed_rejections.items():
            sample_rejections[category] = rejections[:3]

        self.audit_data["samples"]["rejected_samples"] = sample_rejections

        # Store detailed rejections for full audit
        self.audit_data["detailed_rejections"] = self.detailed_rejections

    def get_migration_description(self) -> str:
        """Return description of this migration."""
        return (
            "Populate StudentRequirementFulfillment records based on student major "
            "declarations and completed courses. Maps CanonicalRequirements to "
            "student enrollments and tracks fulfillment status."
        )
