"""Populate AcademicJourney records from CSV enrollment data.

This command processes student enrollment history from CSV to create comprehensive
academic journey records with progression milestones. It handles unreliable
legacy data by using confidence scoring and flagging uncertain records for review.

This version reads from the same CSV format as the original load_program_enrollments command.
"""

import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from django.db import transaction

from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Course, Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.enrollment.models_progression import AcademicJourney
from apps.enrollment.progression_builder import ProgressionBuilder
from apps.people.models import StudentProfile
from apps.scheduling.models import ClassHeader


class Command(BaseMigrationCommand):
    """Populate AcademicJourney from CSV enrollment data."""

    help = "Generate AcademicJourney records from CSV enrollment file"

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
        self.enrollment_cache = {}  # Cache for created enrollments

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
            "student_not_found",
            "course_not_found",
            "term_not_found",
        ]

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "csv_file", type=str, help="Path to the enrollment CSV file (same format as load_program_enrollments)"
        )
        parser.add_argument(
            "--batch-size", type=int, default=100, help="Number of students to process per batch (default: 100)"
        )
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
        parser.add_argument(
            "--create-enrollments",
            action="store_true",
            help="Create ClassHeaderEnrollment records from CSV data (for testing)",
        )

    def execute_migration(self, *args, **options):
        """Execute the academic journey population from CSV."""
        csv_file = options.get("csv_file")
        dry_run = options.get("dry_run", False)
        batch_size = options.get("batch_size", 100)
        confidence_threshold = options.get("confidence_threshold", 0.7)
        export_file = options.get("export_low_confidence")
        student_ids = options.get("student_ids")
        clear_existing = options.get("clear_existing", False)
        create_enrollments = options.get("create_enrollments", False)

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No database changes"))

        # Initialize progression builder
        self.progression_builder = ProgressionBuilder()

        # Clear existing if requested
        if clear_existing and not dry_run:
            self.clear_existing_records()

        # Read CSV and group enrollments by student
        self.stdout.write(f"📖 Reading enrollments from {csv_file}")
        student_enrollments = self.read_csv_enrollments(csv_file, student_ids)
        self.stats["total_students"] = len(student_enrollments)

        # Record input statistics
        self.record_input_stats(
            total_students=self.stats["total_students"],
            csv_file=csv_file,
            batch_size=batch_size,
            confidence_threshold=confidence_threshold,
            dry_run=dry_run,
            create_enrollments=create_enrollments,
        )

        # Process students in batches
        self.stdout.write(f"📊 Processing {self.stats['total_students']} students from CSV")

        student_ids_list = list(student_enrollments.keys())
        for batch_start in range(0, self.stats["total_students"], batch_size):
            batch_end = min(batch_start + batch_size, self.stats["total_students"])
            batch_student_ids = student_ids_list[batch_start:batch_end]

            self.process_batch_from_csv(
                batch_student_ids, student_enrollments, dry_run, confidence_threshold, create_enrollments
            )

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

    def read_csv_enrollments(self, csv_file: str, student_filter: str | None = None) -> dict:
        """Read enrollments from CSV and group by student.

        Expected CSV format with normalized fields:
        - ID: Student ID
        - parsed_termid: Term code
        - NormalizedCourse: Normalized course code (e.g., ENGL-101 instead of ENGL101A)
        - NormalizedSection: Normalized section
        - NormalizedTOD: Normalized time of day
        - Grade: Final grade (A-F, W, IP, I, CR)
        - Credit: Credit hours
        - GradePoint: Grade points
        - Attendance: Should be 'Normal' for valid enrollments

        Grade handling:
        - A through D, CR = Passing grades
        - F, W = Failing (must retake)
        - IP = In Progress/In Program (no grade submitted for historical, in process for current)
        - I = Incomplete (should be finished in previous term)
        """
        student_enrollments = defaultdict(list)
        total_rows = 0
        filtered_rows = 0

        with open(csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                total_rows += 1

                # Filter for Attendance = 'Normal' as specified
                attendance = row.get("Attendance", "").strip()
                if attendance != "Normal":
                    continue

                student_id = row.get("ID", "").strip()

                if not student_id:
                    continue

                if student_filter:
                    filter_ids = [sid.strip() for sid in student_filter.split(",")]
                    if student_id not in filter_ids:
                        continue

                # Parse enrollment data using normalized fields
                enrollment = {
                    "student_id": student_id,
                    "term": row.get("parsed_termid", "").strip(),
                    "course_code": row.get("NormalizedCourse", "").strip(),  # Use normalized course
                    "section": row.get("NormalizedSection", "").strip(),  # Use normalized section
                    "tod": row.get("NormalizedTOD", "").strip(),  # Use normalized time of day
                    "grade": row.get("Grade", "").strip().upper(),  # Normalize grade to uppercase
                    "credit": row.get("Credit", "").strip(),
                    "grade_point": row.get("GradePoint", "").strip(),
                    "attendance": attendance,
                    # Keep original parsed_coursecode for reference
                    "original_course_code": row.get("parsed_coursecode", "").strip(),
                }

                # Skip if missing critical data
                if enrollment["term"] and enrollment["course_code"]:
                    student_enrollments[student_id].append(enrollment)
                    filtered_rows += 1

        self.stdout.write(f"📚 Processed {total_rows} total rows")
        self.stdout.write(f"📚 Found {filtered_rows} enrollments with Attendance='Normal'")
        self.stdout.write(f"📚 Found {len(student_enrollments)} students with valid enrollments")

        # Show sample of student IDs found
        sample_ids = list(student_enrollments.keys())[:10]
        self.stdout.write(f"📚 Sample student IDs from CSV: {sample_ids}")

        return student_enrollments

    def clear_existing_records(self):
        """Clear existing journey records."""
        count = AcademicJourney.objects.all().delete()[0]
        self.stdout.write(self.style.SUCCESS(f"🗑️  Cleared {count} existing journey records"))

    @transaction.atomic
    def process_batch_from_csv(
        self, student_ids, student_enrollments, dry_run: bool, confidence_threshold: float, create_enrollments: bool
    ):
        """Process a batch of students from CSV data."""
        for student_id in student_ids:
            try:
                # Get student profile
                # Strip leading zeros for numeric student IDs
                try:
                    # Try to convert to int and back to string to remove leading zeros
                    numeric_id = str(int(student_id))
                    student = StudentProfile.objects.get(student_id=numeric_id)
                except (ValueError, StudentProfile.DoesNotExist):
                    # If conversion fails or student not found with numeric ID,
                    # try with the original ID
                    try:
                        student = StudentProfile.objects.get(student_id=student_id)
                    except StudentProfile.DoesNotExist:
                        self.stats["errors"] += 1
                        self.record_rejection(
                            category="student_not_found",
                            record_id=str(student_id),
                            reason="Student profile not found",
                            raw_data={
                                "student_id": student_id,
                                "tried_numeric": numeric_id if "numeric_id" in locals() else None,
                            },
                        )
                        continue

                # Get enrollments for this student
                csv_enrollments = student_enrollments.get(student_id, [])

                if not csv_enrollments:
                    self.stats["skipped_no_enrollments"] += 1
                    self.record_rejection(
                        category="no_enrollments",
                        record_id=str(student_id),
                        reason="No enrollments in CSV",
                        raw_data={"student_id": student_id},
                    )
                    continue

                # Skip if journey already exists (unless cleared)
                if hasattr(student, "academic_journey"):
                    self.record_rejection(
                        category="duplicate_journey",
                        record_id=str(student_id),
                        reason="Journey already exists",
                        raw_data={"student_id": student_id},
                    )
                    continue

                if not dry_run:
                    # Create ClassHeaderEnrollment records if requested
                    if create_enrollments:
                        self.create_enrollments_from_csv(student, csv_enrollments)

                    # Build journey using the progression builder
                    # Pass the database primary key (id), not the student_id string
                    journeys = self.progression_builder.build_student_journey(student.id)
                    self.stats["journeys_created"] += len(journeys)
                    self.stdout.write(
                        f"  ✅ Created {len(journeys)} journey record(s) for student "
                        f"{student.student_id} (db id: {student.id})"
                    )

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
                    # Dry run - just report
                    self.stdout.write(
                        f"  Would process student {student.student_id} (db id: {student.id}) with "
                        f"{len(csv_enrollments)} CSV enrollments"
                    )

            except Exception as e:
                self.stats["errors"] += 1
                category = self._categorize_error(e, student_id)
                self.record_rejection(
                    category=category,
                    record_id=str(student_id),
                    reason=str(e),
                    error_details=f"Error processing student {student_id}: {e}",
                    raw_data={"student_id": student_id},
                )
                continue

    def create_enrollments_from_csv(self, student: StudentProfile, csv_enrollments: list):
        """Create ClassHeaderEnrollment records from CSV data.

        This is primarily for testing when the database doesn't have enrollment records.
        """
        # Grade mappings from legacy system
        PASSING_GRADES = ["A", "B", "C", "D", "CR"]
        FAILING_GRADES = ["F", "W"]
        IN_PROGRESS_GRADES = ["IP", "I"]

        for enrollment_data in csv_enrollments:
            try:
                # Get term
                term = Term.objects.get(code=enrollment_data["term"])

                # Get or create course
                course, _ = Course.objects.get_or_create(
                    code=enrollment_data["course_code"],
                    defaults={
                        "name": f"Course {enrollment_data['course_code']}",
                        "credits": Decimal(enrollment_data["credit"]) if enrollment_data["credit"] else Decimal("3.0"),
                    },
                )

                # Get or create class header
                # Handle NULL section
                section = enrollment_data["section"]
                if not section or section == "NULL":
                    section = "01"

                class_header, _ = ClassHeader.objects.get_or_create(
                    course=course,
                    term=term,
                    section_id=section,
                    defaults={
                        "class_type": ClassHeader.ClassType.STANDARD,
                    },
                )

                # Determine enrollment status based on grade
                grade = enrollment_data["grade"]

                # Handle missing/empty grades (common in language classes)
                if not grade or grade == "":
                    # Check if this is a language course
                    if any(
                        prefix in enrollment_data["course_code"] for prefix in ["IEAP", "GESL", "EHSS", "ELL", "IELTS"]
                    ):
                        # Language courses with no grade are likely still in progress
                        status = "ENROLLED"
                        grade = "IP"  # Treat as in progress
                    else:
                        # Non-language courses with no grade - use completed as default
                        status = "COMPLETED"
                elif grade in PASSING_GRADES:
                    status = "COMPLETED"
                elif grade in FAILING_GRADES:
                    status = "DROPPED"  # F or W means they didn't complete successfully
                elif grade in IN_PROGRESS_GRADES:
                    status = "ENROLLED"  # Still in progress
                else:
                    status = "COMPLETED"  # Default for unknown grades

                # Create enrollment if it doesn't exist
                key = f"{student.id}_{class_header.id}"
                if key not in self.enrollment_cache:
                    enrollment, created = ClassHeaderEnrollment.objects.get_or_create(
                        student=student,
                        class_header=class_header,
                        defaults={
                            "status": status,
                            "final_grade": enrollment_data["grade"],
                        },
                    )
                    self.enrollment_cache[key] = enrollment
                    if created:
                        self.stdout.write(
                            f"  ✅ Created enrollment: {course.code} in {term.code} (Grade: {grade}, Status: {status})"
                        )

            except Term.DoesNotExist:
                self.record_rejection(
                    category="term_not_found",
                    record_id=f"{student.student_id}_{enrollment_data['term']}",
                    reason=f"Term not found: {enrollment_data['term']}",
                    raw_data=enrollment_data,
                )
            except Exception as e:
                self.record_rejection(
                    category="unknown_error",
                    record_id=f"{student.student_id}_{enrollment_data['course_code']}",
                    reason=str(e),
                    raw_data=enrollment_data,
                )

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
                "current_program",
                "journey_status",
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
        self.stdout.write("📊 ACADEMIC JOURNEY POPULATION FROM CSV SUMMARY")
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
