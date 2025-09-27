"""Populate AcademicJourney records from historical enrollment data.

This command processes student enrollment history to create comprehensive
academic journey records with progression milestones. It handles unreliable
legacy data by using confidence scoring and flagging uncertain records for review.
"""

import csv
from decimal import Decimal
from pathlib import Path

from django.db import transaction
from django.db.models import Count, Prefetch

from apps.common.management.base_migration import BaseMigrationCommand
from apps.enrollment.models import ClassHeaderEnrollment
from apps.enrollment.models_progression import AcademicJourney
from apps.enrollment.progression_builder import ProgressionBuilder
from apps.people.models import StudentProfile


class Command(BaseMigrationCommand):
    """Populate AcademicJourney from legacy enrollment data."""

    help = "Generate AcademicJourney records from historical class enrollments"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.progression_builder = None
        self.stats = {
            "total_students": 0,
            "journeys_created": 0,
            "high_confidence": 0,
            "medium_confidence": 0,
            "low_confidence": 0,
            "errors": 0,
            "skipped_no_enrollments": 0,
        }
        self.low_confidence_records = []

    def get_rejection_categories(self) -> list[str]:
        """Return possible rejection categories for this migration."""
        return [
            "no_enrollments",
            "insufficient_data",
            "data_conflict",
            "major_detection_failed",
            "database_error",
            "validation_error",
            "duplicate_journey",
            "unknown_error",
        ]

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--batch-size", type=int, default=100, help="Number of students to process per batch (default: 100)"
        )
        parser.add_argument("--start-student", type=int, default=0, help="Student ID to start from (for resuming)")
        parser.add_argument("--dry-run", action="store_true", help="Run without creating database records")
        parser.add_argument(
            "--confidence-threshold",
            type=float,
            default=0.7,
            help="Confidence threshold for flagging reviews (default: 0.7)",
        )
        parser.add_argument("--export-low-confidence", type=str, help="Export low confidence records to CSV file")
        parser.add_argument("--student-ids", type=str, help="Comma-separated list of specific student IDs to process")
        parser.add_argument(
            "--clear-existing", action="store_true", help="Clear existing journey records before populating"
        )

    def execute_migration(self, *args, **options):
        """Execute the academic journey population."""
        dry_run = options.get("dry_run", False)
        batch_size = options.get("batch_size", 100)
        start_student = options.get("start_student", 0)
        confidence_threshold = options.get("confidence_threshold", 0.7)
        export_file = options.get("export_low_confidence")
        student_ids = options.get("student_ids")
        clear_existing = options.get("clear_existing", False)

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No database changes"))

        # Initialize progression builder
        self.progression_builder = ProgressionBuilder()

        # Clear existing if requested
        if clear_existing and not dry_run:
            self.clear_existing_records()

        # Get students to process
        students = self.get_students_to_process(start_student, student_ids)
        self.stats["total_students"] = students.count()

        # Record input statistics
        self.record_input_stats(
            total_students=self.stats["total_students"],
            batch_size=batch_size,
            confidence_threshold=confidence_threshold,
            dry_run=dry_run,
        )

        # Process students in batches
        self.stdout.write(f"📊 Processing {self.stats['total_students']} students")

        for batch_start in range(0, self.stats["total_students"], batch_size):
            batch_end = min(batch_start + batch_size, self.stats["total_students"])
            batch = students[batch_start:batch_end]

            self.process_batch(batch, dry_run, confidence_threshold)

            # Progress update
            self.stdout.write(
                f"📈 Progress: {batch_end}/{self.stats['total_students']} "
                f"({batch_end * 100 / self.stats['total_students']:.1f}%)"
            )

        # Export low confidence records if requested
        if export_file and self.low_confidence_records:
            self.export_low_confidence_records(export_file)

        # Final summary
        self.print_summary()

        # Record final statistics
        self.record_final_stats()

    def get_students_to_process(self, start_student: int, student_ids: str | None):
        """Get queryset of students to process."""
        # Base queryset with enrollments
        queryset = (
            StudentProfile.objects.annotate(enrollment_count=Count("class_header_enrollments"))
            .filter(enrollment_count__gt=0)
            .order_by("id")
        )

        # Apply filters
        if student_ids:
            # Process specific students
            id_list = [int(sid.strip()) for sid in student_ids.split(",")]
            queryset = queryset.filter(id__in=id_list)
        else:
            # Start from specific ID
            queryset = queryset.filter(id__gte=start_student)

        # Prefetch related data for performance
        queryset = queryset.prefetch_related(
            Prefetch(
                "class_header_enrollments",
                queryset=ClassHeaderEnrollment.objects.select_related(
                    "class_header__course", "class_header__term"
                ).order_by("class_header__term__start_date"),
            )
        )

        return queryset

    def clear_existing_records(self):
        """Clear existing journey records."""
        count = AcademicJourney.objects.all().delete()[0]
        self.stdout.write(self.style.SUCCESS(f"🗑️  Cleared {count} existing journey records"))

    @transaction.atomic
    def process_batch(self, students, dry_run: bool, confidence_threshold: float):
        """Process a batch of students."""
        for student in students:
            try:
                # Skip if no enrollments
                if not student.class_header_enrollments.exists():
                    self.stats["skipped_no_enrollments"] += 1
                    self.record_rejection(
                        category="no_enrollments",
                        record_id=str(student.id),
                        reason="No class enrollments found",
                        raw_data={"student_id": student.id},
                    )
                    continue

                # Skip if journeys already exist (unless cleared)
                if student.academic_journeys.exists():
                    self.record_rejection(
                        category="duplicate_journey",
                        record_id=str(student.id),
                        reason="Journey records already exist",
                        raw_data={"student_id": student.id},
                    )
                    continue

                # Build journey
                if not dry_run:
                    journeys = self.progression_builder.build_student_journey(student.id)
                    self.stats["journeys_created"] += len(journeys)

                    # Process each journey record
                    for journey in journeys:
                        # Categorize by confidence
                        if journey.confidence_score >= Decimal("0.8"):
                            self.stats["high_confidence"] += 1
                        elif journey.confidence_score >= Decimal("0.6"):
                            self.stats["medium_confidence"] += 1
                        else:
                            self.stats["low_confidence"] += 1

                        # Track low confidence for export
                        if journey.confidence_score < Decimal(str(confidence_threshold)):
                            self.low_confidence_records.append(
                                {
                                    "student_id": student.id,
                                    "student_name": student.person.full_name,
                                    "confidence_score": float(journey.confidence_score),
                                    "data_issues": ", ".join(journey.data_issues),
                                    "program_type": journey.program_type,
                                    "program": journey.program.name if journey.program else journey.program_type,
                                    "transition_status": journey.transition_status,
                                    "start_date": str(journey.start_date),
                                    "stop_date": str(journey.stop_date) if journey.stop_date else "Active",
                                }
                            )

                    # Record success for the student (once)
                    if journeys:
                        avg_confidence = sum(j.confidence_score for j in journeys) / len(journeys)
                        self.record_success(
                            "journey_created",
                            len(journeys),
                            {
                                "student_id": student.id,
                                "num_journeys": len(journeys),
                                "avg_confidence": float(avg_confidence),
                            },
                        )
                else:
                    # Dry run - just validate
                    enrollments = list(student.class_header_enrollments.all())
                    self.stdout.write(f"  Would process student {student.id} with {len(enrollments)} enrollments")

            except Exception as e:
                self.stats["errors"] += 1
                category = self._categorize_error(e, student.id)
                self.record_rejection(
                    category=category,
                    record_id=str(student.id),
                    reason=str(e),
                    error_details=f"Error processing student {student.id}: {e}",
                    raw_data={"student_id": student.id},
                )

                # Continue with next student
                continue

    def _categorize_error(self, error: Exception, student_id: int) -> str:
        """Categorize an error for rejection tracking."""
        error_str = str(error).lower()

        if "no enrollments" in error_str:
            return "no_enrollments"
        elif "insufficient" in error_str:
            return "insufficient_data"
        elif "conflict" in error_str or "multiple" in error_str:
            return "data_conflict"
        elif "major" in error_str or "detection" in error_str:
            return "major_detection_failed"
        elif "database" in error_str or "connection" in error_str:
            return "database_error"
        elif "validation" in error_str or "invalid" in error_str:
            return "validation_error"
        else:
            return "unknown_error"

    def export_low_confidence_records(self, filename: str):
        """Export low confidence records to CSV."""
        path = Path(filename)
        path.parent.mkdir(parents=True, exist_ok=True)

        with open(path, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = [
                "student_id",
                "student_name",
                "confidence_score",
                "data_issues",
                "program_type",
                "program",
                "transition_status",
                "start_date",
                "stop_date",
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.low_confidence_records)

        self.stdout.write(
            self.style.SUCCESS(f"📄 Exported {len(self.low_confidence_records)} low confidence records to {filename}")
        )

    def print_summary(self):
        """Print summary statistics."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("📊 ACADEMIC JOURNEY POPULATION SUMMARY")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Total students processed: {self.stats['total_students']:,}")
        self.stdout.write(f"Journeys created: {self.stats['journeys_created']:,}")
        self.stdout.write(f"Skipped (no enrollments): {self.stats['skipped_no_enrollments']:,}")
        self.stdout.write(f"Errors: {self.stats['errors']:,}")

        if self.stats["journeys_created"] > 0:
            self.stdout.write("\n📈 Confidence Distribution:")
            self.stdout.write(
                f"  High (≥0.8): {self.stats['high_confidence']:,} "
                f"({self.stats['high_confidence'] * 100 / self.stats['journeys_created']:.1f}%)"
            )
            self.stdout.write(
                f"  Medium (0.6-0.8): {self.stats['medium_confidence']:,} "
                f"({self.stats['medium_confidence'] * 100 / self.stats['journeys_created']:.1f}%)"
            )
            self.stdout.write(
                f"  Low (<0.6): {self.stats['low_confidence']:,} "
                f"({self.stats['low_confidence'] * 100 / self.stats['journeys_created']:.1f}%)"
            )

        self.stdout.write("=" * 60)

    def record_final_stats(self):
        """Record final statistics to audit report."""
        self.record_success("total_journeys_created", self.stats["journeys_created"])
        self.record_success("high_confidence_journeys", self.stats["high_confidence"])
        self.record_success("medium_confidence_journeys", self.stats["medium_confidence"])
        self.record_success("low_confidence_journeys", self.stats["low_confidence"])
        self.record_success("students_skipped_no_enrollments", self.stats["skipped_no_enrollments"])

        # Calculate percentages
        if self.stats["journeys_created"] > 0:
            self.record_performance_metric(
                "high_confidence_percentage", self.stats["high_confidence"] * 100 / self.stats["journeys_created"]
            )
            self.record_performance_metric(
                "review_needed_percentage", self.stats["low_confidence"] * 100 / self.stats["journeys_created"]
            )
