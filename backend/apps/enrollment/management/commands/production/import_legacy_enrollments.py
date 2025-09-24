"""Import legacy academic course takers data from V0 all_academiccoursetakers_*.csv files.

This script imports student enrollment and grade data from the legacy system,
creating ClassHeader, ClassPart, and ClassHeaderEnrollment records in our V1 system.

Based on V0 scripts:
- load_acadcoursetakers_csv.py
- import_legacy_academiccoursetakers.py
"""

import csv
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.curriculum.models import Course, Major, Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.people.models import StudentProfile
from apps.scheduling.models import ClassHeader, ClassPart


class Command(BaseCommand):
    """Import legacy enrollment data from academiccoursetakers CSV files."""

    help = "Import legacy enrollment and grade data from all_academiccoursetakers_*.csv"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {
            "total_rows": 0,
            "class_headers_created": 0,
            "class_parts_created": 0,
            "enrollments_created": 0,
            "enrollments_updated": 0,
            "errors": 0,
            "skipped": 0,
        }
        self.student_cache = {}
        self.course_cache = {}
        self.term_cache = {}
        self.program_cache = {}
        self.error_log = []

    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            "--file",
            required=True,
            help="Path to the CSV file containing academic course takers data",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without making changes",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Number of records to process in each batch",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of records to process (for testing)",
        )
        parser.add_argument(
            "--start",
            type=int,
            default=0,
            help="Start from row number (zero-indexed)",
        )

    def handle(self, *args, **options):
        """Main command handler."""
        file_path = options["file"]
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        limit = options.get("limit")
        start = options["start"]

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No database changes will be made"))

        self.stdout.write(f"📊 Processing enrollment file: {file_path}")

        try:
            # Load caches
            self._load_caches()

            # Process CSV file
            self._process_csv_file(file_path, dry_run, batch_size, limit, start)

            # Report results
            self._report_results(dry_run)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Import failed: {e}"))
            msg = f"Import failed: {e}"
            raise CommandError(msg) from e

    def _load_caches(self):
        """Load data into caches for efficient lookup."""
        self.stdout.write("🏗️  Loading caches...")

        # Load students by student_id
        for student in StudentProfile.objects.select_related("person").all():
            self.student_cache[str(student.student_id).zfill(5)] = student

        # Load courses by code
        for course in Course.objects.all():
            self.course_cache[course.code] = course

        # Load terms by code
        for term in Term.objects.all():
            self.term_cache[term.code] = term

        # Load programs/majors by code
        for major in Major.objects.all():
            if major.code:
                self.program_cache[major.code] = major

        self.stdout.write(
            f"   📋 Loaded {len(self.student_cache)} students, "
            f"{len(self.course_cache)} courses, "
            f"{len(self.term_cache)} terms, "
            f"{len(self.program_cache)} programs",
        )

    def _process_csv_file(
        self,
        file_path: str,
        dry_run: bool,
        batch_size: int,
        limit: int | None,
        start: int,
    ):
        """Process the CSV file in batches."""
        csv_path = Path(file_path)
        if not csv_path.exists():
            msg = f"CSV file not found: {file_path}"
            raise CommandError(msg)

        with csv_path.open(encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            # Skip to start position
            for _ in range(start):
                try:
                    next(reader)
                except StopIteration:
                    break

            # Process records in batches
            batch = []
            for row_num, row in enumerate(reader, start=start + 1):
                if limit and row_num > start + limit:
                    break

                batch.append((row_num, row))

                if len(batch) >= batch_size:
                    self._process_batch(batch, dry_run)
                    batch = []

                    if row_num % 5000 == 0:
                        self.stdout.write(f"📋 Processed {row_num - start} rows...")

            # Process remaining batch
            if batch:
                self._process_batch(batch, dry_run)

        self.stats["total_rows"] = row_num - start

    def _process_batch(self, batch: list, dry_run: bool):
        """Process a batch of records."""
        if not dry_run:
            with transaction.atomic():
                for row_num, row in batch:
                    self._process_enrollment_record(row_num, row, dry_run)
        else:
            for row_num, row in batch:
                self._process_enrollment_record(row_num, row, dry_run)

    def _process_enrollment_record(self, row_num: int, row: dict, dry_run: bool):
        """Process a single enrollment record."""
        try:
            # Parse basic fields
            student_id = str(row.get("ID", "")).strip().zfill(5)
            class_id = row.get("ClassID", "").strip()
            grade = row.get("Grade", "").strip()
            credit = self._parse_decimal(row.get("Credit", "0"))

            if not student_id or not class_id:
                self.stats["skipped"] += 1
                return

            # Parse ClassID: termid!$program_code!$tod!$part4!$part5
            parsed_class = self._parse_class_id(class_id)
            if not parsed_class:
                self.stats["skipped"] += 1
                return

            term_id, program_code, time_of_day, header_name, part_name = parsed_class

            # Get or create records
            if not dry_run:
                student = self._get_student(student_id)
                if not student:
                    self.stats["skipped"] += 1
                    return

                class_header = self._get_or_create_class_header(term_id, header_name, program_code, time_of_day)
                if not class_header:
                    self.stats["skipped"] += 1
                    return

                self._get_or_create_class_part(class_header, part_name, credit)

                self._get_or_create_enrollment(student, class_header, grade, credit)

            else:
                # Dry run validation
                self._validate_enrollment_record(student_id, parsed_class, grade, credit)

        except Exception as e:
            self.stats["errors"] += 1
            error_msg = f"Row {row_num}: {e} - Student: {student_id}, Class: {class_id}"
            self.error_log.append(error_msg)

            if len(self.error_log) <= 20:  # Limit error logging
                self.stdout.write(self.style.ERROR(f"   ❌ {error_msg}"))

    def _parse_class_id(self, class_id: str) -> tuple[str, str, str, str, str] | None:
        """Parse ClassID format: termid!$program_code!$tod!$part4!$part5

        Examples:
        - 2009T3T3E!$582!$M!$M1A!$INTER-1 (IEAP class)
        - 2009T3T3E!$87!$M!$INT-101!$A (Academic class)
        """
        parts = class_id.split("!$")
        if len(parts) < 5:
            return None

        term_id, program_code, time_of_day, part4, part5 = parts

        # Determine header and part names based on program type
        is_language = program_code not in {"87", "147"}  # BA and MA are academic

        if is_language:
            header_name = part4  # M1A, E1A, etc.
            part_name = part5  # INTER-1, COM-1, etc.
        else:
            header_name = part5  # Course name for academic
            part_name = part4  # Section for academic

        return term_id, program_code, time_of_day, header_name, part_name

    def _get_student(self, student_id: str) -> StudentProfile | None:
        """Get student from cache."""
        return self.student_cache.get(student_id)

    def _get_or_create_class_header(
        self,
        term_id: str,
        header_name: str,
        program_code: str,
        time_of_day: str,
    ) -> ClassHeader | None:
        """Get or create ClassHeader record."""
        # Map time of day codes
        time_mapping = {
            "M": ClassHeader.TimeOfDay.MORNING,
            "A": ClassHeader.TimeOfDay.AFTERNOON,
            "E": ClassHeader.TimeOfDay.EVENING,
            "N": ClassHeader.TimeOfDay.NIGHT,
        }

        mapped_time = time_mapping.get(time_of_day, ClassHeader.TimeOfDay.MORNING)

        # Try to find term
        term = self.term_cache.get(term_id)
        if not term:
            # Could create a basic term here if needed
            return None

        # For now, create a placeholder course if not found
        course_code = f"LEGACY-{program_code}"
        course = self.course_cache.get(course_code)
        if not course:
            return None

        # Create or get ClassHeader
        class_header, created = ClassHeader.objects.get_or_create(
            course=course,
            term=term,
            section_id="A",  # Default section
            time_of_day=mapped_time,
            defaults={
                "status": ClassHeader.ClassStatus.ACTIVE,
                "class_type": ClassHeader.ClassType.STANDARD,
            },
        )

        if created:
            self.stats["class_headers_created"] += 1

        return class_header

    def _get_or_create_class_part(self, class_header: ClassHeader, part_name: str, credit: Decimal) -> ClassPart:
        """Get or create ClassPart record."""
        class_part, created = ClassPart.objects.get_or_create(
            class_header=class_header,
            name=part_name,
            defaults={
                "credit_hours": credit,
                "is_required": True,
            },
        )

        if created:
            self.stats["class_parts_created"] += 1

        return class_part

    def _get_or_create_enrollment(
        self,
        student: StudentProfile,
        class_header: ClassHeader,
        grade: str,
        credit: Decimal,
    ) -> ClassHeaderEnrollment:
        """Get or create enrollment record."""
        enrollment, created = ClassHeaderEnrollment.objects.get_or_create(
            student=student,
            class_header=class_header,
            defaults={
                "status": ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
                "enrollment_date": class_header.term.start_date,
                "final_grade": grade if grade else None,
                "credit_hours_attempted": credit,
                "credit_hours_earned": (credit if grade and grade not in ["F", "I", "W"] else Decimal("0")),
            },
        )

        if created:
            self.stats["enrollments_created"] += 1
        else:
            # Update existing enrollment
            if grade:
                enrollment.final_grade = grade
            enrollment.credit_hours_attempted = credit
            enrollment.credit_hours_earned = credit if grade and grade not in ["F", "I", "W"] else Decimal("0")
            enrollment.save()
            self.stats["enrollments_updated"] += 1

        return enrollment

    def _parse_decimal(self, value: str) -> Decimal:
        """Parse decimal value from string."""
        if not value or value.upper() in ("NULL", ""):
            return Decimal("0")
        try:
            return Decimal(str(value))
        except (ValueError, TypeError, InvalidOperation):
            return Decimal("0")

    def _validate_enrollment_record(self, student_id: str, parsed_class: tuple, grade: str, credit: Decimal):
        """Validate enrollment record in dry run mode."""
        if student_id not in self.student_cache:
            msg = f"Student not found: {student_id}"
            raise ValueError(msg)

        term_id, program_code, time_of_day, header_name, part_name = parsed_class

        if term_id not in self.term_cache:
            msg = f"Term not found: {term_id}"
            raise ValueError(msg)

    def _report_results(self, dry_run: bool):
        """Report import results."""
        mode = "DRY RUN" if dry_run else "IMPORT"

        self.stdout.write(f"\n📊 {mode} RESULTS:")
        self.stdout.write(f"   Total records processed: {self.stats['total_rows']:,}")
        self.stdout.write(f"   Class headers created: {self.stats['class_headers_created']:,}")
        self.stdout.write(f"   Class parts created: {self.stats['class_parts_created']:,}")
        self.stdout.write(f"   Enrollments created: {self.stats['enrollments_created']:,}")
        self.stdout.write(f"   Enrollments updated: {self.stats['enrollments_updated']:,}")
        self.stdout.write(f"   Records skipped: {self.stats['skipped']:,}")
        self.stdout.write(f"   Errors encountered: {self.stats['errors']:,}")

        if self.error_log:
            self.stdout.write(f"\n❌ ERRORS ({len(self.error_log)}):")
            for error in self.error_log[:10]:  # Show first 10 errors
                self.stdout.write(f"   {error}")
            if len(self.error_log) > 10:
                self.stdout.write(f"   ... and {len(self.error_log) - 10} more errors")

        if not dry_run:
            self.stdout.write(self.style.SUCCESS("\n✅ Import completed successfully!"))
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ Dry run completed - ready for import!"))
