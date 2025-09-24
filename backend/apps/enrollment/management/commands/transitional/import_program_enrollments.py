"""Comprehensive Program Enrollment Import Command

This command uses the comprehensive program detection service to create
ProgramEnrollment records that represent individual program periods,
enabling accurate major switching and language progression tracking.

Each ProgramEnrollment record represents ONE continuous period in ONE specific program.
"""

import logging

from django.db import transaction

from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Major, Term
from apps.enrollment.models import ClassHeaderEnrollment, ProgramEnrollment
from apps.enrollment.services.comprehensive_program_detector import (
    ComprehensiveProgramDetectionService,
)
from apps.people.models import StudentProfile

logger = logging.getLogger(__name__)


class Command(BaseMigrationCommand):
    """Import ProgramEnrollment records using comprehensive program detection."""

    help = "Create ProgramEnrollment records with comprehensive program detection"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {
            "total_students_processed": 0,
            "language_enrollments_created": 0,
            "academic_enrollments_created": 0,
            "students_with_academic_majors": 0,
            "students_with_language_programs": 0,
            "major_switches_detected": 0,
            "language_switches_detected": 0,
            "errors": 0,
        }

        # Initialize comprehensive program detection service
        self.program_detector = ComprehensiveProgramDetectionService()

        # Major mapping for database storage
        self.major_code_mapping = {
            "TESOL": "BA_TES",
            "BA_BUSINESS": "BA_BAD",
            "BA_FINANCE": "BA_FIN",
            "BA_TOURISM": "BA_TOU",
            "BA_INTERNATIONAL_RELATIONS": "BA_INT",
        }

    def get_rejection_categories(self):
        return [
            "no_enrollments_found",
            "no_program_detected",
            "invalid_major_code",
            "missing_term_data",
            "database_error",
        ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Clear existing ProgramEnrollment records before import",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of students to process (for testing)",
        )

    def execute_migration(self, *args, **options):
        """Execute the comprehensive program enrollment creation."""
        self.record_input_stats(total_students=StudentProfile.objects.count())

        if options["clear_existing"]:
            deleted_count = ProgramEnrollment.objects.count()
            ProgramEnrollment.objects.all().delete()
            self.stdout.write(f"🗑️  Cleared {deleted_count} existing ProgramEnrollment records")

        # Get all students with enrollments
        students_with_enrollments = StudentProfile.objects.filter(classheaderenrollment__isnull=False).distinct()

        if options["limit"]:
            students_with_enrollments = students_with_enrollments[: options["limit"]]
            self.stdout.write(f"📊 Processing limited to {options['limit']} students")

        total_students = students_with_enrollments.count()
        self.stdout.write(f"🎓 Processing {total_students} students with enrollments")

        # Process students in batches
        batch_size = 100
        for i in range(0, total_students, batch_size):
            batch = students_with_enrollments[i : i + batch_size]
            self._process_student_batch(batch)

            if (i + batch_size) % 500 == 0:
                self.stdout.write(f"   Processed {i + batch_size} students...")

        # Generate final statistics
        detection_stats = self.program_detector.get_comprehensive_stats()
        self.stats.update(
            {
                "students_with_academic_majors": detection_stats["students_with_academic_majors"],
                "students_with_language_programs": detection_stats["students_with_language_programs"],
                "major_switches_detected": detection_stats["students_with_academic_switches"],
                "language_switches_detected": detection_stats["students_with_language_switches"],
            },
        )

        self.record_success(
            "program_enrollments_created",
            self.stats["academic_enrollments_created"] + self.stats["language_enrollments_created"],
        )

        # Display summary
        self._display_summary(detection_stats)

    def _process_student_batch(self, students):
        """Process a batch of students for program enrollment creation."""
        for student in students:
            try:
                with transaction.atomic():
                    self._process_single_student(student)
                    self.stats["total_students_processed"] += 1
            except Exception as e:
                self.record_rejection("database_error", student.id, str(e))
                self.stats["errors"] += 1
                logger.exception("Error processing student %s: %s", student.id, e)

    def _process_single_student(self, student):
        """Process a single student for comprehensive program detection."""
        # Get all enrollments for this student
        enrollments = ClassHeaderEnrollment.objects.filter(student=student).select_related(
            "class_header__course",
            "class_header__term",
        )

        if not enrollments.exists():
            self.record_rejection("no_enrollments_found", student.id, "No enrollments found")
            return

        # Run comprehensive program detection
        history = self.program_detector.analyze_student_programs(str(student.id), enrollments)

        if not history.academic_periods and not history.language_periods:
            self.record_rejection("no_program_detected", student.id, "No programs detected")
            return

        # Create ProgramEnrollment records for academic periods
        for period in history.academic_periods:
            self._create_academic_enrollment(student, period)
            self.stats["academic_enrollments_created"] += 1

        # Create ProgramEnrollment records for language periods
        for period in history.language_periods:
            self._create_language_enrollment(student, period)
            self.stats["language_enrollments_created"] += 1

    def _create_academic_enrollment(self, student, period):
        """Create ProgramEnrollment record for academic period."""
        try:
            # Map program name to database major code
            major_code = self.major_code_mapping.get(period.program_name)
            if not major_code:
                self.record_rejection(
                    "invalid_major_code",
                    student.id,
                    f"Invalid major code: {period.program_name}",
                )
                return

            major = Major.objects.get(code=major_code)
            start_term = Term.objects.get(code=period.start_term)
            end_term = Term.objects.get(code=period.end_term)

            ProgramEnrollment.objects.create(
                student=student,
                program_type="academic",
                major=major,
                start_term=start_term,
                end_term=end_term,
                is_current=False,  # Will be updated by separate process
            )

        except (Major.DoesNotExist, Term.DoesNotExist) as e:
            self.record_rejection("missing_term_data", student.id, str(e))

    def _create_language_enrollment(self, student, period):
        """Create ProgramEnrollment record for language period."""
        try:
            start_term = Term.objects.get(code=period.start_term)
            end_term = Term.objects.get(code=period.end_term)

            ProgramEnrollment.objects.create(
                student=student,
                program_type="language",
                language_program=period.program_name,
                entry_level=period.entry_level,
                finishing_level=period.finishing_level,
                start_term=start_term,
                end_term=end_term,
                is_current=False,  # Will be updated by separate process
            )

        except Term.DoesNotExist as e:
            self.record_rejection("missing_term_data", student.id, str(e))

    def _display_summary(self, detection_stats):
        """Display comprehensive import summary."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("🎓 COMPREHENSIVE PROGRAM ENROLLMENT SUMMARY")
        self.stdout.write("=" * 60)

        self.stdout.write(f"📊 Students Processed: {self.stats['total_students_processed']}")
        self.stdout.write(f"🎯 Academic Enrollments Created: {self.stats['academic_enrollments_created']}")
        self.stdout.write(f"🗣️  Language Enrollments Created: {self.stats['language_enrollments_created']}")
        self.stdout.write(f"📈 Students with Academic Majors: {self.stats['students_with_academic_majors']}")
        self.stdout.write(f"🌐 Students with Language Programs: {self.stats['students_with_language_programs']}")
        self.stdout.write(f"🔄 Academic Major Switches: {self.stats['major_switches_detected']}")
        self.stdout.write(f"🔄 Language Program Switches: {self.stats['language_switches_detected']}")
        self.stdout.write(f"❌ Errors: {self.stats['errors']}")

        total_created = self.stats["academic_enrollments_created"] + self.stats["language_enrollments_created"]
        self.stdout.write(f"\n✅ Total ProgramEnrollment Records Created: {total_created}")

        if detection_stats["academic_switch_patterns"]:
            self.stdout.write("\n🔄 Academic Switch Patterns:")
            for pattern, count in detection_stats["academic_switch_patterns"].items():
                self.stdout.write(f"   • {pattern}: {count} students")

        if detection_stats["language_switch_patterns"]:
            self.stdout.write("\n🗣️  Language Switch Patterns:")
            for pattern, count in detection_stats["language_switch_patterns"].items():
                self.stdout.write(f"   • {pattern}: {count} students")
