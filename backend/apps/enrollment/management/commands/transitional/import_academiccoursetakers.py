"""Production-quality import script for academic course takers enrollment data.

This script imports student enrollment and grade data from the legacy
all_academiccoursetakers_*.csv files, creating comprehensive enrollment
records in our V1 system.

Key Features:
- Idempotent operation (safe to run multiple times)
- Batch processing for large files
- Course validation and missing course detection
- ClassSession creation with alphabetical assignment logic
- Comprehensive error handling and reporting
- Grade and credit tracking with legacy ClassID preservation

Based on user requirements:
- Use NormalizedLangCourse for ClassHeader names (EHSS-01, IEAP-01, etc.)
- Use parsed_coursecode for academic courses (section 87/147)
- Use parsed_termid for Term lookup
- Keep CLASSID as comment for legacy linkage
- Grammar/Communications → Session 1, Writing → Session 2 (alphabetical)
"""

import csv
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.db import transaction

from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Course, Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.people.models import StudentProfile
from apps.scheduling.class_part_types import ClassPartType
from apps.scheduling.models import ClassHeader, ClassPart, ClassSession


class Command(BaseMigrationCommand):
    """Import legacy academic course takers enrollment data."""

    help = "Import enrollment data from all_academiccoursetakers_*.csv with comprehensive validation"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.stats = {
            "total_rows": 0,
            "class_headers_created": 0,
            "class_sessions_created": 0,
            "class_parts_created": 0,
            "enrollments_created": 0,
            "enrollments_updated": 0,
            "errors": 0,
            "skipped": 0,
            "missing_students": 0,
            "missing_courses": 0,
            "missing_terms": 0,
        }

        # Caches for efficient lookup
        self.student_cache: dict[str, StudentProfile] = {}
        self.course_cache: dict[str, Course] = {}
        self.term_cache: dict[str, Term] = {}
        self.class_header_cache: dict[tuple[str, str, str], ClassHeader] = {}

        # Track missing data for validation
        self.missing_students: set[str] = set()
        self.missing_courses: set[str] = set()
        self.missing_terms: set[str] = set()

        self.error_log: list[str] = []

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
            help="Validate data without making database changes",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=2000,
            help="Number of records to process in each batch (default: 2000)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of records to process (for testing)",
        )
        parser.add_argument(
            "--start-row",
            type=int,
            default=0,
            help="Start from row number (zero-indexed, default: 0)",
        )
        parser.add_argument(
            "--validate-only",
            action="store_true",
            help="Only validate courses, students, and terms - don't process enrollments",
        )
        parser.add_argument(
            "--progress-frequency",
            type=int,
            default=5000,
            help="Report progress every N records (default: 5000)",
        )
        parser.add_argument(
            "--skip-existing",
            action="store_true",
            help="Skip enrollments that already exist (faster re-runs)",
        )
        parser.add_argument(
            "--memory-efficient",
            action="store_true",
            help="Use smaller batch sizes and clear caches periodically for large datasets",
        )

    def get_rejection_categories(self):
        """Return list of possible rejection categories."""
        return [
            "missing_student",
            "missing_course",
            "missing_term",
            "duplicate_constraint",
            "data_validation_error",
            "database_error",
            "unexpected_error",
        ]

    def execute_migration(self, *args, **options):
        """Main command handler."""
        file_path = options["file"]
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        limit = options.get("limit")
        start_row = options["start_row"]
        validate_only = options["validate_only"]
        progress_frequency = options["progress_frequency"]
        skip_existing = options["skip_existing"]
        memory_efficient = options["memory_efficient"]

        # Adjust batch size for memory efficiency
        if memory_efficient:
            batch_size = min(batch_size, 500)
            self.stdout.write(self.style.WARNING("🧠 MEMORY EFFICIENT MODE - Using smaller batches"))

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No database changes will be made"))

        if validate_only:
            self.stdout.write(self.style.WARNING("✅ VALIDATION ONLY - Only checking data integrity"))

        if skip_existing:
            self.stdout.write(self.style.WARNING("⏭️  SKIP EXISTING MODE - Existing enrollments will be skipped"))

        self.stdout.write(f"📊 Processing enrollment file: {file_path}")
        self.stdout.write(f"📋 Batch size: {batch_size:,}, Start row: {start_row:,}")
        self.stdout.write(f"📋 Progress frequency: {progress_frequency:,} records")

        if limit:
            self.stdout.write(f"📋 Processing limit: {limit:,} records")

        try:
            # Load caches
            self._load_caches()

            # Validate CSV file
            csv_path = Path(file_path)
            if not csv_path.exists():
                msg = f"CSV file not found: {file_path}"
                raise CommandError(msg)

            # Count total CSV rows for audit
            with csv_path.open(encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                total_csv_rows = sum(1 for _ in reader)

            # Record initial stats for audit
            self.record_input_stats(
                csv_file=str(csv_path),
                total_csv_rows=total_csv_rows,
                start_row=start_row,
                limit_applied=limit if limit else "none",
                students_available=len(self.student_cache),
                courses_available=len(self.course_cache),
                terms_available=len(self.term_cache),
            )

            # Process CSV file
            self._process_csv_file(
                csv_path,
                dry_run,
                batch_size,
                limit,
                start_row,
                validate_only,
                progress_frequency,
                skip_existing,
                memory_efficient,
            )

            # Record final statistics for audit
            self.record_success("class_headers_created", self.stats["class_headers_created"])
            self.record_success("class_sessions_created", self.stats["class_sessions_created"])
            self.record_success("class_parts_created", self.stats["class_parts_created"])
            self.record_success("enrollments_created", self.stats["enrollments_created"])
            self.record_success("enrollments_updated", self.stats["enrollments_updated"])

            # Record performance metrics
            self.record_performance_metric("total_rows_processed", self.stats["total_rows"])
            self.record_performance_metric("batch_size", batch_size)
            if limit:
                self.record_performance_metric("limit_applied", limit)

            # Report validation results
            self._report_validation_results()

            # Report final results
            self._report_results(dry_run, validate_only)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Import failed: {e}"))
            msg = f"Import failed: {e}"
            raise CommandError(msg) from e

    def _load_caches(self):
        """Load all reference data into memory for efficient processing."""
        self.stdout.write("🏗️  Loading caches...")

        # Load students by student_id (zero-padded to 5 digits) with optimized query
        students_qs = StudentProfile.objects.select_related("person").only(
            "student_id",
            "person__family_name",
            "person__personal_name",
            "person",
        )
        for student in students_qs:
            student_key = str(student.student_id).zfill(5)
            self.student_cache[student_key] = student

        # Load courses by code with optimized query
        courses_qs = Course.objects.only("code", "credits", "title")
        for course in courses_qs:
            self.course_cache[course.code] = course

        # Load terms by code with optimized query
        terms_qs = Term.objects.only("code", "start_date", "end_date")
        for term in terms_qs:
            self.term_cache[term.code] = term

        # Pre-warm ClassHeader cache to avoid expensive lookups during processing
        self._prewarm_class_header_cache()

        # Get system user for enrollment creation
        User = get_user_model()
        self.system_user = User.objects.only("id", "email").first()
        if not self.system_user:
            msg = "No users found - create a user first"
            raise CommandError(msg)

        self.stdout.write(
            f"   📋 Loaded {len(self.student_cache):,} students, "
            f"{len(self.course_cache):,} courses, "
            f"{len(self.term_cache):,} terms, "
            f"{len(self.class_header_cache):,} class headers",
        )

    def _prewarm_class_header_cache(self):
        """Pre-warm ClassHeader cache from existing enrollments to avoid expensive lookups."""
        # Get all existing ClassHeaders that have enrollments with Legacy ClassID notes
        existing_class_headers = (
            ClassHeader.objects.filter(class_header_enrollments__notes__contains="Legacy ClassID:")
            .select_related("course", "term")
            .prefetch_related("class_header_enrollments")
            .distinct()
        )

        # Build cache by extracting ClassID from enrollment notes
        for class_header in existing_class_headers:
            for enrollment in class_header.class_header_enrollments.all():
                if enrollment.notes and "Legacy ClassID:" in enrollment.notes:
                    # Extract ClassID from notes like "Legacy ClassID: 2009T3T3E!$582!$M!$M1A!$INTER-1"
                    try:
                        class_id_start = enrollment.notes.find("Legacy ClassID:") + len("Legacy ClassID:")
                        class_id_end = enrollment.notes.find(".", class_id_start)
                        if class_id_end == -1:
                            class_id_end = enrollment.notes.find("\n", class_id_start)
                        if class_id_end == -1:
                            class_id_end = len(enrollment.notes)

                        class_id = enrollment.notes[class_id_start:class_id_end].strip()
                        if class_id:
                            self.class_header_cache[class_id] = class_header
                            break  # Only need one ClassID per ClassHeader
                    except Exception:
                        continue  # Skip malformed notes

    def _process_csv_file(
        self,
        csv_path: Path,
        dry_run: bool,
        batch_size: int,
        limit: int | None,
        start_row: int,
        validate_only: bool,
        progress_frequency: int,
        skip_existing: bool,
        memory_efficient: bool,
    ):
        """Process the CSV file in optimized batches."""
        # Build existing enrollment cache for skip_existing optimization
        existing_enrollments_cache = set()
        if skip_existing and not dry_run and not validate_only:
            self.stdout.write("🔍 Building existing enrollments cache...")
            existing_enrollments = ClassHeaderEnrollment.objects.values_list(
                "student__student_id",
                "class_header__course__code",
                "class_header__term__code",
            )
            for student_id, course_code, term_code in existing_enrollments:
                key = f"{str(student_id).zfill(5)}-{course_code}-{term_code}"
                existing_enrollments_cache.add(key)
            self.stdout.write(f"   📋 Cached {len(existing_enrollments_cache):,} existing enrollments")

        with csv_path.open(encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)

            # Skip to start position efficiently
            for _ in range(start_row):
                try:
                    next(reader)
                except StopIteration:
                    self.stdout.write(self.style.WARNING(f"⚠️  Reached end of file at row {start_row}"))
                    return

            # Process records in batches
            batch = []
            total_processed = 0

            for row_num, row in enumerate(reader, start=start_row + 1):
                if limit and total_processed >= limit:
                    break

                batch.append((row_num, row))
                total_processed += 1

                if len(batch) >= batch_size:
                    self._process_batch(
                        batch,
                        dry_run,
                        validate_only,
                        existing_enrollments_cache,
                        skip_existing,
                    )
                    batch = []

                    # Progress reporting at configurable frequency
                    if total_processed % progress_frequency == 0:
                        self.stdout.write(f"📋 Processed {total_processed:,} rows...")

                        # Memory management for large datasets
                        if memory_efficient and total_processed % (progress_frequency * 4) == 0:
                            self._periodic_cache_cleanup()

            # Process remaining batch
            if batch:
                self._process_batch(
                    batch,
                    dry_run,
                    validate_only,
                    existing_enrollments_cache,
                    skip_existing,
                )

        self.stats["total_rows"] = total_processed

    def _process_batch(
        self,
        batch: list[tuple[int, dict]],
        dry_run: bool,
        validate_only: bool,
        existing_enrollments_cache: set,
        skip_existing: bool,
    ):
        """Process a batch of enrollment records with transaction safety."""
        if not dry_run and not validate_only:
            with transaction.atomic():
                for row_num, row in batch:
                    self._process_enrollment_record(
                        row_num,
                        row,
                        dry_run,
                        validate_only,
                        existing_enrollments_cache,
                        skip_existing,
                    )
        else:
            for row_num, row in batch:
                self._process_enrollment_record(
                    row_num,
                    row,
                    dry_run,
                    validate_only,
                    existing_enrollments_cache,
                    skip_existing,
                )

    def _periodic_cache_cleanup(self):
        """Periodic cache cleanup for memory efficiency in large datasets."""
        # Keep only frequently accessed items in class_header_cache
        if len(self.class_header_cache) > 10000:
            # Keep the most recently accessed items (this is a simple approximation)
            # In a more sophisticated implementation, we could track access frequency
            cache_items = list(self.class_header_cache.items())
            # Keep only the first 5000 items (most recently added)
            self.class_header_cache = dict(cache_items[:5000])
            self.stdout.write("🧠 Performed cache cleanup - reduced ClassHeader cache size")

    def _process_enrollment_record(
        self,
        row_num: int,
        row: dict,
        dry_run: bool,
        validate_only: bool,
        existing_enrollments_cache: set,
        skip_existing: bool,
    ):
        """Process a single enrollment record with comprehensive validation."""
        try:
            # Extract and validate core fields
            student_id = str(row.get("ID", "")).strip().zfill(5)
            class_id = row.get("ClassID", "").strip()
            term_id = row.get("parsed_termid", "").strip()
            grade = str(row.get("Grade", "")).strip().strip('"').strip()
            credit = self._parse_decimal(row.get("Credit"))
            attendance = str(row.get("Attendance", "")).strip()

            # Extract course identification fields (use Normalized fields for all courses)
            normalized_course = str(row.get("NormalizedCourse", "")).strip()
            normalized_part = str(row.get("NormalizedPart", "")).strip()
            normalized_section = str(row.get("NormalizedSection", "")).strip()

            # Skip records with insufficient data
            if not student_id or not class_id or not term_id:
                self.stats["skipped"] += 1
                return

            # Use NormalizedCourse for all course types (replaces deprecated parsed_coursecode)
            course_code = normalized_course if normalized_course != "NULL" else None
            class_header_name = normalized_course if normalized_course != "NULL" else None

            # Validate required data
            if not course_code or course_code == "NULL":
                self.stats["skipped"] += 1
                return

            if not class_header_name or class_header_name == "NULL":
                self.stats["skipped"] += 1
                return

            # Skip existing enrollments optimization
            if skip_existing and not dry_run and not validate_only:
                enrollment_key = f"{student_id}-{course_code}-{term_id}"
                if enrollment_key in existing_enrollments_cache:
                    self.stats["skipped"] += 1
                    return

            # Track missing entities for validation and audit
            missing_entities = []
            if student_id not in self.student_cache:
                self.missing_students.add(student_id)
                self.stats["missing_students"] += 1
                missing_entities.append("student")

            if course_code not in self.course_cache:
                self.missing_courses.add(course_code)
                self.stats["missing_courses"] += 1
                missing_entities.append("course")

            if term_id not in self.term_cache:
                self.missing_terms.add(term_id)
                self.stats["missing_terms"] += 1
                missing_entities.append("term")

            # Record rejections for audit if any entities are missing
            if missing_entities:
                for entity_type in missing_entities:
                    category = f"missing_{entity_type}"
                    entity_value = (
                        student_id if entity_type == "student" else course_code if entity_type == "course" else term_id
                    )
                    self.record_rejection(
                        category=category,
                        record_id=f"{student_id}-{class_id}",
                        reason=f"Missing {entity_type}: {entity_value}",
                        raw_data={
                            "row_num": row_num,
                            "student_id": student_id,
                            "class_id": class_id,
                            "course_code": course_code,
                            "term_id": term_id,
                            "grade": grade,
                        },
                    )

            # Skip processing if validation-only mode or missing required entities
            if validate_only or missing_entities:
                return

            # Get entities from cache
            student = self.student_cache[student_id]
            course = self.course_cache[course_code]
            term = self.term_cache[term_id]

            # Create or get ClassHeader
            class_header = self._get_or_create_class_header(
                course,
                term,
                class_header_name,
                class_id,
                normalized_section,
                dry_run,
                row,
            )

            if not class_header:
                self.stats["skipped"] += 1
                return

            # Create ClassSession if needed (for IEAP courses with multiple parts)
            class_session = self._get_or_create_class_session(class_header, normalized_part, dry_run)

            # Create or get ClassPart
            self._get_or_create_class_part(class_header, class_session, normalized_part, credit, dry_run)

            # Create or update enrollment
            if not dry_run:
                self._create_or_update_enrollment(student, class_header, grade, credit, class_id, row_num, attendance)

        except Exception as e:
            self.stats["errors"] += 1

            # Categorize the error for audit
            error_str = str(e).lower()
            if "duplicate key" in error_str or "unique constraint" in error_str:
                category = "duplicate_constraint"
            elif "null value" in error_str or "not-null constraint" in error_str:
                category = "data_validation_error"
            elif "foreign key" in error_str:
                category = "database_error"
            else:
                category = "unexpected_error"

            # Record detailed error for audit
            self.record_rejection(
                category=category,
                record_id=f"{student_id}-{class_id}",
                reason=f"Processing error: {e}",
                error_details=str(e),
                raw_data={
                    "row_num": row_num,
                    "student_id": student_id,
                    "class_id": class_id,
                    "grade": grade,
                    "full_row": dict(row),
                },
            )

            # Log first 20 errors for debugging
            if self.stats["errors"] <= 20:
                self.stdout.write(
                    self.style.ERROR(f"   ❌ Row {row_num}: {e} - Student: {student_id}, Class: {class_id}"),
                )

    def _get_or_create_class_header(
        self,
        course: Course,
        term: Term,
        class_header_name: str,
        class_id: str,
        normalized_section: str,
        dry_run: bool,
        row: dict | None = None,
    ) -> ClassHeader | None:
        """Get or create ClassHeader using the full ClassID as the unique identifier."""
        # The FULL ClassID is the unique identifier for a class
        # Use it directly as the cache key for perfect deduplication
        cache_key = class_id

        if cache_key in self.class_header_cache:
            return self.class_header_cache[cache_key]

        if dry_run:
            # For dry run, just validate the logic
            return None

        # Cache miss - ClassHeader doesn't exist yet, create it
        # (Pre-warming eliminated the expensive query lookup)

        # Use NormalizedSection as primary source for section_id (preserves original section information)
        section_id = self._create_section_id_from_normalized_section(normalized_section, class_id)

        # Extract time of day from the normalized fields for database storage
        normalized_tod = str(row.get("NormalizedTOD", "")).strip() if row else ""
        time_of_day = self._map_normalized_tod_to_time_of_day(normalized_tod)

        # Create new ClassHeader for this unique ClassID with section_id from NormalizedSection
        class_header = ClassHeader.objects.create(
            course=course,
            term=term,
            section_id=section_id,
            time_of_day=time_of_day,
            status=ClassHeader.ClassStatus.ACTIVE,
            class_type=ClassHeader.ClassType.STANDARD,
        )

        self.stats["class_headers_created"] += 1

        # Cache for future use
        self.class_header_cache[cache_key] = class_header
        return class_header

    def _create_section_id_from_normalized_section(self, normalized_section: str, class_id: str) -> str:
        """Create section_id using NormalizedSection as primary source, with fallback to ClassID hash.

        This preserves original section information for class size analysis and administrative tracking.
        """
        # Use NormalizedSection if available and meaningful
        if normalized_section and normalized_section not in ["NULL", "", "null"]:
            # Clean and format for database constraints (5 char max, alphanumeric)
            section_id = "".join(c for c in normalized_section if c.isalnum())[:5].upper()
            if section_id:
                return section_id

        # Fallback to ClassID-based hash for unique identification
        import hashlib

        compound_key = f"{class_id}"
        class_id_hash = hashlib.sha256(compound_key.encode()).hexdigest()[:5].upper()
        return class_id_hash

    def _get_or_create_class_session(
        self,
        class_header: ClassHeader,
        course_part: str,
        dry_run: bool,
    ) -> ClassSession | None:
        """Create ClassSession with alphabetical assignment logic."""
        if dry_run:
            return None

        # Determine session number based on alphabetical order
        # Grammar/Communications → Session 1, Writing → Session 2
        session_number = 1
        if course_part and any(
            writing_keyword in course_part.upper() for writing_keyword in ["WR", "WRIT", "WRITING"]
        ):
            session_number = 2

        # Create or get ClassSession
        class_session, created = ClassSession.objects.get_or_create(
            class_header=class_header,
            session_number=session_number,
            defaults={
                "session_name": f"Session {session_number}",
                "notes": f"Auto-created session for {course_part or 'course part'}",
            },
        )

        if created:
            self.stats["class_sessions_created"] += 1

        return class_session

    def _get_or_create_class_part(
        self,
        class_header: ClassHeader,
        class_session: ClassSession | None,
        part_name: str,
        credit: Decimal,
        dry_run: bool,
    ) -> ClassPart | None:
        """Get or create ClassPart for the enrollment."""
        if dry_run:
            return None

        # Use course part name or default
        effective_part_name = part_name if part_name and part_name != "NULL" else "Main"

        # Create or get ClassPart using the actual unique constraint fields
        class_part, created = ClassPart.objects.get_or_create(
            class_session=class_session,
            class_part_code="A",  # Use the unique constraint field
            defaults={
                "name": effective_part_name,
                "class_part_type": ClassPartType.MAIN,
                "meeting_days": "",  # Will be filled by scheduler
                "notes": f"Auto-created part for {effective_part_name}",
            },
        )

        if created:
            self.stats["class_parts_created"] += 1

        return class_part

    def _create_or_update_enrollment(
        self,
        student: StudentProfile,
        class_header: ClassHeader,
        grade: str,
        credit: Decimal,
        class_id: str,
        row_num: int,
        attendance: str = "",
    ):
        """Create or update enrollment record with idempotent operation."""
        # Clean grade value - use empty string for null grades since field doesn't allow null
        clean_grade = grade if grade and grade not in ["NULL", ""] else ""

        # The 'credit' from CSV is already the student's earned credits
        # Grade A-D = earned credits, Grade F/W = 0 credits (already reflected in CSV)
        earned_credits = credit  # CSV already has correct earned credits

        course_credits = class_header.course.credits or 1
        attempted_credits = Decimal(str(course_credits))

        # Determine enrollment status based on attendance, grade and term completion
        enrollment_status = self._determine_enrollment_status(clean_grade, class_header.term, attendance)

        # Convert term start_date to timezone-aware datetime
        from django.utils.timezone import make_aware

        if isinstance(class_header.term.start_date, date):
            enrollment_datetime = make_aware(datetime.combine(class_header.term.start_date, datetime.min.time()))
        else:
            enrollment_datetime = class_header.term.start_date

        # Create or update enrollment
        enrollment, created = ClassHeaderEnrollment.objects.get_or_create(
            student=student,
            class_header=class_header,
            defaults={
                "status": enrollment_status,
                "enrollment_date": enrollment_datetime,
                "final_grade": clean_grade,
                "enrolled_by": self.system_user,
                "notes": (
                    f"Legacy ClassID: {class_id}. Credits attempted: {attempted_credits}, earned: {earned_credits}"
                ),
            },
        )

        if created:
            self.stats["enrollments_created"] += 1
        else:
            # Update existing enrollment (idempotent)
            updated = False

            if enrollment.final_grade != clean_grade:
                enrollment.final_grade = clean_grade
                updated = True

            # Update status based on current grade and term completion
            new_status = self._determine_enrollment_status(clean_grade, class_header.term, attendance)
            if enrollment.status != new_status:
                enrollment.status = new_status
                updated = True

            # Update notes with credit information
            credit_info = f"Credits attempted: {attempted_credits}, earned: {earned_credits}"
            legacy_info = f"Legacy ClassID: {class_id}"

            if legacy_info not in (enrollment.notes or "") or credit_info not in (enrollment.notes or ""):
                existing_notes = enrollment.notes or ""
                new_notes = f"{existing_notes}\n{legacy_info}. {credit_info}".strip()
                enrollment.notes = new_notes
                updated = True

            if updated:
                enrollment.save()
                self.stats["enrollments_updated"] += 1

    def _determine_enrollment_status(self, grade: str, term, attendance: str = "") -> str:
        """Determine enrollment status based on attendance, grade and term completion status."""
        from django.utils import timezone

        # Check attendance first - if dropped, always return DROPPED regardless of other factors
        if attendance and attendance.strip().lower() == "drop":
            return ClassHeaderEnrollment.EnrollmentStatus.DROPPED

        current_date = timezone.now().date()
        grade_upper = grade.upper().strip()

        # For active terms (currently in session)
        if current_date >= term.start_date and current_date <= term.end_date:
            # If attendance is Normal and grade is IP, return ACTIVE (student is still enrolled)
            if attendance.strip().lower() == "normal" and grade_upper == "IP":
                return ClassHeaderEnrollment.EnrollmentStatus.ACTIVE
            return ClassHeaderEnrollment.EnrollmentStatus.ACTIVE

        # For completed terms, determine status based on grade
        if current_date > term.end_date:
            grade_upper = grade.upper().strip()

            # For completed terms, attendance has dominance over grade
            # If attendance is Normal and grade is IP, return INCOMPLETE (term ended but student didn't complete)
            if attendance.strip().lower() == "normal" and grade_upper == "IP":
                return ClassHeaderEnrollment.EnrollmentStatus.INCOMPLETE

            # Handle specific non-passing grades
            if grade_upper == "F":
                return ClassHeaderEnrollment.EnrollmentStatus.FAILED
            if grade_upper == "W":
                return ClassHeaderEnrollment.EnrollmentStatus.WITHDRAWN
            if grade_upper == "I":
                return ClassHeaderEnrollment.EnrollmentStatus.INCOMPLETE
            if grade_upper == "IP":
                # If term has ended but grade is still "In Progress", student didn't complete
                return ClassHeaderEnrollment.EnrollmentStatus.INCOMPLETE

            # Check if grade is D or above (passing grade)
            if grade_upper and grade_upper not in ["", "NULL"]:
                # Extract base grade letter (remove +/- modifiers)
                base_grade = grade_upper.replace("+", "").replace("-", "").strip()

                # Grades A, B, C, D are passing (completed)
                if base_grade in ["A", "B", "C", "D"]:
                    return ClassHeaderEnrollment.EnrollmentStatus.COMPLETED

            # Grade is empty/null or unrecognized for completed term - mark as incomplete
            return ClassHeaderEnrollment.EnrollmentStatus.INCOMPLETE

        # For future terms (not yet started)
        return ClassHeaderEnrollment.EnrollmentStatus.ACTIVE  # ACTIVE = ENROLLED

    def _extract_section_from_class_id(self, class_id: str) -> str:
        """Extract section identifier from ClassID with intelligent parsing."""
        # Parse format: termid!$program_code!$tod!$part4!$part5
        parts = class_id.split("!$")

        if len(parts) >= 5:
            # Use combination of part4 and part5 for section differentiation
            # Examples: GESL-1A!$MAINST-1A vs GESL-1A!$SPECT-1A
            part4 = parts[3]
            part5 = parts[4]

            # Create unique section ID from both parts
            combined = f"{part4}-{part5}"
            # Clean and truncate to 5 characters max for database constraint
            section_id = "".join(c for c in combined if c.isalnum())[:5]
            return section_id if section_id else "A"
        elif len(parts) >= 2:
            # Use program code as section ID
            program_code = parts[1]
            section_id = "".join(c for c in program_code if c.isalnum())[:5]
            return section_id if section_id else "A"

        return "A"

    def _map_normalized_tod_to_time_of_day(self, normalized_tod: str) -> str:
        """Map NormalizedTOD field to ClassHeader.TimeOfDay choices."""
        tod_mapping = {
            "M": ClassHeader.TimeOfDay.MORNING,
            "A": ClassHeader.TimeOfDay.AFTERNOON,
            "E": ClassHeader.TimeOfDay.EVENING,
            "N": ClassHeader.TimeOfDay.NIGHT,
            # Handle common variations
            "MORNING": ClassHeader.TimeOfDay.MORNING,
            "AFTERNOON": ClassHeader.TimeOfDay.AFTERNOON,
            "EVENING": ClassHeader.TimeOfDay.EVENING,
            "NIGHT": ClassHeader.TimeOfDay.NIGHT,
        }

        # Clean and normalize the input
        tod_key = normalized_tod.upper().strip()

        # Return mapped value or default to MORNING
        return tod_mapping.get(tod_key, ClassHeader.TimeOfDay.MORNING)

    def _map_normalized_part_to_section_id(self, normalized_part: str) -> str:
        """Map NormalizedPart to section_id for proper class differentiation."""
        if not normalized_part or normalized_part in ["NULL", ""]:
            return "A"  # Default section

        # Clean the part and create a valid section ID
        # Remove special characters and limit to 5 chars for database constraint
        clean_part = "".join(c for c in normalized_part if c.isalnum())[:5]

        return clean_part if clean_part else "A"

    def _extract_time_of_day_from_class_id(self, class_id: str) -> str:
        """Extract time of day from ClassID format."""
        # Parse format: termid!$program_code!$tod!$part4!$part5
        parts = class_id.split("!$")
        if len(parts) >= 3:
            tod_code = parts[2]

            time_mapping = {
                "M": ClassHeader.TimeOfDay.MORNING,
                "A": ClassHeader.TimeOfDay.AFTERNOON,
                "E": ClassHeader.TimeOfDay.EVENING,
                "N": ClassHeader.TimeOfDay.NIGHT,
            }

            return time_mapping.get(tod_code, ClassHeader.TimeOfDay.MORNING)

        return ClassHeader.TimeOfDay.MORNING

    def _parse_decimal(self, value: str) -> Decimal:
        """Parse decimal value from CSV field."""
        if not value or str(value).upper() in ("NULL", ""):
            return Decimal("0")
        try:
            return Decimal(str(value))
        except Exception:
            return Decimal("0")

    def _report_validation_results(self):
        """Report validation issues found during processing."""
        if self.missing_students or self.missing_courses or self.missing_terms:
            self.stdout.write("\n⚠️  VALIDATION ISSUES FOUND:")

            if self.missing_students:
                self.stdout.write(f"   Missing students: {len(self.missing_students):,}")
                if len(self.missing_students) <= 10:
                    for student_id in sorted(self.missing_students):
                        self.stdout.write(f"      - {student_id}")
                else:
                    sample_students = sorted(self.missing_students)[:5]
                    self.stdout.write(f"      Sample: {', '.join(sample_students)} ...")

            if self.missing_courses:
                self.stdout.write(f"   Missing courses: {len(self.missing_courses):,}")
                if len(self.missing_courses) <= 10:
                    for course_code in sorted(self.missing_courses):
                        self.stdout.write(f"      - {course_code}")
                else:
                    sample_courses = sorted(self.missing_courses)[:5]
                    self.stdout.write(f"      Sample: {', '.join(sample_courses)} ...")

            if self.missing_terms:
                self.stdout.write(f"   Missing terms: {len(self.missing_terms):,}")
                if len(self.missing_terms) <= 10:
                    for term_code in sorted(self.missing_terms):
                        self.stdout.write(f"      - {term_code}")
                else:
                    sample_terms = sorted(self.missing_terms)[:5]
                    self.stdout.write(f"      Sample: {', '.join(sample_terms)} ...")

    def _report_results(self, dry_run: bool, validate_only: bool):
        """Report comprehensive import results."""
        mode = "VALIDATION" if validate_only else ("DRY RUN" if dry_run else "IMPORT")

        self.stdout.write(f"\n📊 {mode} RESULTS:")
        self.stdout.write(f"   Total records processed: {self.stats['total_rows']:,}")

        if not validate_only:
            self.stdout.write(f"   Class headers created: {self.stats['class_headers_created']:,}")
            self.stdout.write(f"   Class sessions created: {self.stats['class_sessions_created']:,}")
            self.stdout.write(f"   Class parts created: {self.stats['class_parts_created']:,}")
            self.stdout.write(f"   Enrollments created: {self.stats['enrollments_created']:,}")
            self.stdout.write(f"   Enrollments updated: {self.stats['enrollments_updated']:,}")

        self.stdout.write(f"   Records skipped: {self.stats['skipped']:,}")
        self.stdout.write(f"   Errors encountered: {self.stats['errors']:,}")

        # Validation summary
        total_missing = self.stats["missing_students"] + self.stats["missing_courses"] + self.stats["missing_terms"]

        if total_missing > 0:
            self.stdout.write(f"\n⚠️  MISSING ENTITIES: {total_missing:,}")
            self.stdout.write(f"   Missing students: {self.stats['missing_students']:,}")
            self.stdout.write(f"   Missing courses: {self.stats['missing_courses']:,}")
            self.stdout.write(f"   Missing terms: {self.stats['missing_terms']:,}")

        # Error summary
        if self.error_log:
            self.stdout.write("\n❌ FIRST 10 ERRORS:")
            for error in self.error_log[:10]:
                self.stdout.write(f"   {error}")
            if len(self.error_log) > 10:
                self.stdout.write(f"   ... and {len(self.error_log) - 10} more errors")

        # Success message
        if not dry_run and not validate_only and self.stats["errors"] == 0:
            self.stdout.write(self.style.SUCCESS("\n✅ Import completed successfully!"))
        elif validate_only:
            self.stdout.write(self.style.SUCCESS("\n✅ Validation completed!"))
        elif dry_run:
            self.stdout.write(self.style.SUCCESS("\n✅ Dry run completed - ready for import!"))
        else:
            self.stdout.write(self.style.WARNING("\n⚠️  Import completed with issues"))
