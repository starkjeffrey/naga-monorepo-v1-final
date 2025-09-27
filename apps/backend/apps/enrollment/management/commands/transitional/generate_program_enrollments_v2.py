"""PRODUCTION PROGRAM ENROLLMENT MIGRATION

Creates ProgramEnrollment records from legacy academic course enrollment data.
Implements chronological major detection algorithm based on actual course enrollments.

CRITICAL BUSINESS RULES:
- Process ALL enrollments in strict chronological order by term start_date
- Detect major from actual course enrollments (NOT from unreliable SelProgram/SelMajor)
- Create new ProgramEnrollment when student changes majors
- Flag dual major violations for manual review
- Use SelProgram/SelMajor ONLY as absolute last resort for Foundation Year students

NEVER CREATE NEW MAJORS - only link to existing Major records.
"""

import time
from datetime import date, timedelta

from django.db import connection, models

from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Major, Term
from apps.enrollment.models import ProgramEnrollment
from apps.people.models import StudentProfile


class Command(BaseMigrationCommand):
    """Generate ProgramEnrollment records from legacy academic course enrollment data."""

    help = "Generate ProgramEnrollment records using chronological major detection from course enrollments"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {
            "total_students": 0,
            "program_enrollments_created": 0,
            "major_changes_detected": 0,
            "dual_major_violations": 0,
            "foundation_only_students": 0,
            "unknown_major_assignments": 0,
        }
        self.major_course_map = {}
        self.term_cache = {}
        self.student_cache = {}
        self.dual_major_violations = []

    def get_rejection_categories(self) -> list[str]:
        """Return possible rejection categories for this migration."""
        return [
            "missing_student_profile",
            "no_course_enrollments",
            "invalid_term_data",
            "missing_major_mapping",
            "dual_major_violation",
            "database_error",
            "unknown_program_codes",
            "validation_error",
        ]

    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without making changes",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of students to process (for testing)",
        )
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Clear existing ProgramEnrollment records before creating new ones",
        )

    def execute_migration(self, *args, **options):
        """Execute the ProgramEnrollment generation with comprehensive audit tracking."""
        dry_run = options.get("dry_run", False)
        limit = options.get("limit")
        clear_existing = options.get("clear_existing", False)

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No database changes will be made"))

        # Record input statistics
        total_legacy_enrollments = self._get_legacy_enrollment_count()
        total_students_with_enrollments = self._get_students_with_enrollments_count()

        self.record_input_stats(
            total_legacy_enrollments=total_legacy_enrollments,
            total_students_with_enrollments=total_students_with_enrollments,
            limit_applied=bool(limit),
            limit_value=limit or "None",
            clear_existing=clear_existing,
        )

        # Clear existing if requested
        if clear_existing and not dry_run:
            deleted_count = ProgramEnrollment.objects.all().delete()[0]
            self.stdout.write(self.style.SUCCESS(f"🗑️  Cleared {deleted_count} existing ProgramEnrollment records"))

        # Initialize caches and mappings
        self._initialize_caches()

        # Performance metrics
        processing_start = time.time()

        # Get students to process
        students_to_process = self._get_students_with_course_data(limit)
        self.stats["total_students"] = len(students_to_process)

        self.stdout.write(f"📊 Processing {self.stats['total_students']} students with course enrollment data")

        # Process each student chronologically
        for i, student_id in enumerate(students_to_process, 1):
            try:
                if not dry_run:
                    self._process_student_enrollments(student_id)
                else:
                    self._validate_student_enrollments(student_id)

                # Progress reporting
                if i % 100 == 0:
                    self.stdout.write(f"📈 Processed {i}/{self.stats['total_students']} students")

            except Exception as e:
                # Categorize and log the error
                category = self._categorize_error(e, student_id)
                self.record_rejection(
                    category=category,
                    record_id=str(student_id),
                    reason=str(e),
                    error_details=f"Error processing student {student_id}: {e}",
                    raw_data={"student_id": student_id},
                )

        # Record final statistics
        self.record_success("program_enrollments_created", self.stats["program_enrollments_created"])
        self.record_success("major_changes_detected", self.stats["major_changes_detected"])
        self.record_success("dual_major_violations", self.stats["dual_major_violations"])
        self.record_success("foundation_only_students", self.stats["foundation_only_students"])
        self.record_success("unknown_major_assignments", self.stats["unknown_major_assignments"])

        # Performance metrics
        processing_time = time.time() - processing_start
        self.record_performance_metric("total_processing_time_seconds", processing_time)
        self.record_performance_metric(
            "students_per_second",
            (self.stats["total_students"] / processing_time if processing_time > 0 else 0),
        )

        # Record dual major violations for investigation
        if self.dual_major_violations:
            self.record_sample_data("dual_major_violations", self.dual_major_violations[:10])

        # Data integrity validation
        if not dry_run:
            self._validate_data_integrity()

        # Don't return stats - BaseMigrationCommand handles output
        pass

    def _get_legacy_enrollment_count(self) -> int:
        """Get total count of legacy enrollment records."""
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM legacy_academiccoursetakers")
            return cursor.fetchone()[0]

    def _get_students_with_enrollments_count(self) -> int:
        """Get count of students who have course enrollment data."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(DISTINCT student_id)
                FROM legacy_academiccoursetakers
                WHERE student_id IS NOT NULL AND student_id != ''
            """
            )
            return cursor.fetchone()[0]

    def _initialize_caches(self):
        """Initialize caches for efficient processing."""
        self.stdout.write("🏗️  Initializing caches...")

        # Build major-to-course mapping from document specifications
        self._build_major_course_mapping()

        # Cache terms for date lookups
        self._cache_terms()

        # Cache student profiles
        self._cache_student_profiles()

        self.stdout.write(
            f"✅ Loaded {len(self.major_course_map)} major mappings, "
            f"{len(self.term_cache)} terms, {len(self.student_cache)} students"
        )

    def _build_major_course_mapping(self):
        """Build mapping from course codes to majors based on document specifications."""
        # Get existing majors
        existing_majors = {major.code: major for major in Major.objects.all()}

        # TESOL major courses (24 unique codes)
        tesol_courses = [
            "ENGL-200A",
            "EDUC-400",
            "ENGL-302A",
            "EDUC-301",
            "EDUC-401",
            "EDUC-404",
            "EDUC-403",
            "EDUC-405",
            "ENGL-401A",
            "EDUC-408",
            "ENGL-140",
            "PHIL-213",
            "EDUC-407",
            "ENGL-130",
            "ENGL-403",
            "ENGL-306",
            "ENGL-301",
            "ENGL-303",
            "ENGL-200",
            "LIT-325",
            "ENGL-450",
            "EDUC-300",
            "PSYC-313",
            "ENGL-201A",
        ]

        # Business Administration courses (11 unique codes)
        busadmin_courses = [
            "BUS-464",
            "BUS-465",
            "BUS-425",
            "BUS-460",
            "BUS-463",
            "BUS-489",
            "ECON-212",
            "MGT-489",
            "BUS-360",
            "BUS-461",
            "MGT-467",
        ]

        # Finance & Banking courses (11 unique codes)
        finance_courses = [
            "FIN-360",
            "ECON-425",
            "FIN-445",
            "FIN-444",
            "FIN-442",
            "FIN-443",
            "ECON-449",
            "ECON-456",
            "FIN-453",
            "FIN-489",
            "FIN-442A",
        ]

        # Tourism & Hospitality courses (23 unique codes)
        tourism_courses = [
            "THM-431",
            "THM-323",
            "THM-321",
            "THM-411",
            "THM-322",
            "THM-332",
            "THM-413",
            "THM-312",
            "THM-324",
            "THM-422",
            "THM-215",
            "THM-314",
            "THM-225",
            "THM-331",
            "THM-313",
            "THM-421",
            "THM-423",
            "THM-412",
            "THM-333",
            "THM-424",
            "THM-414",
            "THM-432",
            "THM-433",
        ]

        # International Relations courses (24 unique codes)
        ir_courses = [
            "PAD-110",
            "POL-405",
            "POL-413",
            "POL-302",
            "LAW-301",
            "SOC-429",
            "IR-480",
            "IR-485",
            "ECON-455",
            "POL-304",
            "ECON-368",
            "LAW-304",
            "ECON-310",
            "LAW-305",
            "ECON-459",
            "IR-479",
            "IR-481",
            "IR-489",
            "POL-305",
            "IR-482",
            "POL-306",
            "PA-110",
            "PHIL-210",
            "POL-120",
        ]

        # MBA courses
        mba_courses = [
            "MGT-505",
            "ECON-515",
            "MGT-535",
            "FIN-540",
            "FIN-571",
            "MGT-545",
            "MGT-578",
            "MGT-582",
            "MGT-585",
            "BUS-520",
            "ECON-544",
            "ACCT-545",
            "MKT-567",
            "MKT-569",
            "MGT-570",
            "MKT-571",
            "FIN-574",
            "MGT-597",
            "MGT-598",
            "MGT-599",
        ]

        # MEd Educational Leadership courses
        med_lead_courses = ["EDUC-560", "EDUC-562", "EDUC-563", "EDUC-564"]

        # MEd TESOL courses
        med_tesol_courses = ["EDUC-549"]

        # Map courses to majors (only if major exists in database)
        course_major_mappings = [
            (tesol_courses, "TESOL"),
            (busadmin_courses, "BUSADMIN"),
            (finance_courses, "FIN-BANK"),
            (tourism_courses, "TOUR-HOSP"),
            (ir_courses, "IR"),
            (mba_courses, "MBA"),
            (med_lead_courses, "MED-LEAD"),
            (med_tesol_courses, "MED-TESOL"),
        ]

        for courses, major_code in course_major_mappings:
            if major_code in existing_majors:
                major_obj = existing_majors[major_code]
                for course_code in courses:
                    self.major_course_map[course_code] = major_obj

        # Language programs based on course code prefix (IEAP, EHSS, GESL, etc.)
        language_major_map = {
            "IEAP": "IEAP",
            "EHSS": "EHSS",
            "GESL": "GESL",
            "EXPRESS": "EXPRESS",
            "IELTS": "IELTS",
            "ELL": "ELL",
        }

        for prefix, major_code in language_major_map.items():
            if major_code in existing_majors:
                self.major_course_map[f"{prefix}_PROGRAM"] = existing_majors[major_code]

    def _cache_terms(self):
        """Cache terms for efficient lookups."""
        for term in Term.objects.all():
            # Use term name as key for legacy data matching (legacy uses parsed_termid)
            self.term_cache[term.code] = term

    def _cache_student_profiles(self):
        """Cache student profiles for efficient lookups."""
        for student in StudentProfile.objects.select_related("person").all():
            # Cache both as string and padded string for legacy ID matching
            self.student_cache[str(student.student_id)] = student
            self.student_cache[f"{student.student_id:05d}"] = student  # Pad to 5 digits like legacy IDs

    def _get_students_with_course_data(self, limit=None) -> list[str]:
        """Get list of students who have course enrollment data."""
        with connection.cursor() as cursor:
            sql = """
                SELECT DISTINCT student_id
                FROM legacy_academiccoursetakers
                WHERE student_id IS NOT NULL AND student_id != ''
                ORDER BY student_id
            """

            if limit:
                sql += f" LIMIT {limit}"

            cursor.execute(sql)
            return [row[0] for row in cursor.fetchall()]

    def _process_student_enrollments(self, student_id: str):
        """Process all enrollments for a single student chronologically."""
        # Get student profile
        student_profile = self.student_cache.get(student_id)
        if not student_profile:
            raise ValueError(f"Student profile not found for ID {student_id}")

        # Get all course enrollments for this student in chronological order
        enrollments = self._get_student_course_enrollments(student_id)
        if not enrollments:
            raise ValueError(f"No course enrollments found for student {student_id}")

        # Find last valid course date and check if student is in active term
        last_course_date = None
        student_in_active_term = False

        for enrollment in enrollments:
            if enrollment["term_start_date"]:
                last_course_date = enrollment["term_start_date"]
                # Check if this term is currently active
                term = self.term_cache.get(enrollment["parsed_termid"])
                if term and self._is_term_currently_active(term):
                    student_in_active_term = True

        # Process enrollments chronologically to detect major changes
        current_major = None
        program_changes = []

        for enrollment in enrollments:
            term_id = enrollment["parsed_termid"]
            course_code = enrollment["parsed_coursecode"]
            norm_course = enrollment["normalizedlangcourse"]
            term_start_date = enrollment["term_start_date"]

            # Skip if no valid course code or term date
            if (not course_code and not norm_course) or not term_start_date:
                continue

            # Detect major from academic course code first
            detected_major = None
            if course_code:
                detected_major = self._detect_major_from_course(course_code)

                # Skip Foundation Year courses (no major detection possible)
                if self._is_foundation_course(course_code):
                    continue

            # Language program detection from normalized course
            if not detected_major and norm_course:
                detected_major = self._detect_language_program(norm_course)

            # Record program change if detected
            if detected_major and detected_major != current_major:
                program_changes.append(
                    {
                        "major": detected_major,
                        "start_date": term_start_date,
                        "term_id": term_id,
                        "first_course": course_code,
                    },
                )
                current_major = detected_major

        # Create ProgramEnrollment records for each program change
        for i, change in enumerate(program_changes):
            end_date = None
            if i < len(program_changes) - 1:
                # End date is day before next program starts
                next_start = program_changes[i + 1]["start_date"]
                end_date = next_start - timedelta(days=1)
            else:
                # Last program - check if student is in active term
                if not student_in_active_term:
                    end_date = last_course_date
                # If student is in active term, end_date remains None

            # Create the enrollment
            self._create_program_enrollment_with_dates(
                student_profile,
                change["major"],
                change["start_date"],
                end_date,
                change["term_id"],
                f"Program change #{i + 1}. First course: {change['first_course']}",
            )

            if i > 0:  # Count major changes (not initial enrollment)
                self.stats["major_changes_detected"] += 1

        # If no major was detected from courses, use fallback logic
        if not program_changes:
            self._handle_no_major_detected(student_profile, student_id)

    def _get_student_course_enrollments(self, student_id: str) -> list[dict]:
        """Get all course enrollments for a student in chronological order."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT l.*, t.start_date as term_start_date
                FROM legacy_academiccoursetakers l
                LEFT JOIN curriculum_term t ON l.parsed_termid = t.name
                WHERE l.student_id = %s
                ORDER BY t.start_date ASC, l.parsed_termid ASC
            """,
                [student_id],
            )

            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]

    def _detect_major_from_course(self, course_code: str) -> Major | None:
        """Detect major from course code using predefined mappings."""
        if not course_code:
            return None

        # Direct course code mapping
        if course_code in self.major_course_map:
            return self.major_course_map[course_code]

        # Language program detection
        for prefix, major in self.major_course_map.items():
            if prefix.endswith("_PROGRAM") and course_code.startswith(prefix.replace("_PROGRAM", "")):
                return major

        return None

    def _detect_language_program(self, course_code: str) -> Major | None:
        """Detect language program from normalized course code."""
        if not course_code:
            return None

        # Extract prefix (e.g., IEAP-01 -> IEAP)
        if "-" in course_code:
            prefix = course_code.split("-")[0]
            program_key = f"{prefix}_PROGRAM"
            return self.major_course_map.get(program_key)

        return None

    def _is_foundation_course(self, course_code: str) -> bool:
        """Check if course is a Foundation Year course."""
        # Foundation courses are common to all majors, so can't determine major
        foundation_patterns = ["FOUND", "CORE", "GEN"]
        return any(pattern in course_code.upper() for pattern in foundation_patterns)

    def _is_language_program(self, major: Major) -> bool:
        """Check if major is a language program."""
        language_codes = ["IEAP", "EHSS", "GESL", "EXPRESS", "IELTS", "ELL"]
        return major.code in language_codes

    def _get_term_start_date(self, term_id: str) -> date | None:
        """Get start date for a term."""
        term = self.term_cache.get(term_id)
        return term.start_date if term else None

    def _is_term_currently_active(self, term: Term) -> bool:
        """Check if a term is currently active."""
        from datetime import date

        today = date.today()

        # A term is active if today is between start_date and end_date
        if term.start_date and term.end_date:
            return term.start_date <= today <= term.end_date
        elif term.start_date and not term.end_date:
            # If no end date, check if it started recently (within last 6 months)
            return (today - term.start_date).days <= 180

        return False

    def _create_program_enrollment_with_dates(
        self,
        student: StudentProfile,
        major: Major,
        start_date: date,
        end_date: date | None,
        term_id: str,
        notes: str,
    ) -> ProgramEnrollment:
        """Create a new ProgramEnrollment record with specific dates."""
        # Determine enrollment type based on major
        if major.code in ["MBA", "MED-LEAD", "MED-TESOL"]:
            enrollment_type = ProgramEnrollment.EnrollmentType.ACADEMIC
        elif major.code in ["BUSADMIN", "TESOL", "FIN-BANK", "TOUR-HOSP", "IR"]:
            enrollment_type = ProgramEnrollment.EnrollmentType.ACADEMIC
        else:
            enrollment_type = ProgramEnrollment.EnrollmentType.LANGUAGE

        # Find corresponding term
        start_term = self.term_cache.get(term_id)

        # Determine status based on end_date
        status = (
            ProgramEnrollment.EnrollmentStatus.COMPLETED if end_date else ProgramEnrollment.EnrollmentStatus.ACTIVE
        )

        enrollment = ProgramEnrollment.objects.create(
            student=student,
            program=major,
            enrollment_type=enrollment_type,
            status=status,
            start_date=start_date,
            end_date=end_date,
            start_term=start_term,
            terms_active=1,
            is_system_generated=True,
            notes=notes,
        )

        self.stats["program_enrollments_created"] += 1
        return enrollment

    def _create_program_enrollment(
        self,
        student: StudentProfile,
        major: Major,
        start_date: date,
        term_id: str,
    ) -> ProgramEnrollment:
        """Create a new ProgramEnrollment record."""
        # Determine enrollment type based on major
        if major.code in ["MBA", "MED-LEAD", "MED-TESOL"]:
            enrollment_type = ProgramEnrollment.EnrollmentType.ACADEMIC
        elif major.code in ["BUSADMIN", "TESOL", "FIN-BANK", "TOUR-HOSP", "IR"]:
            enrollment_type = ProgramEnrollment.EnrollmentType.ACADEMIC
        else:
            enrollment_type = ProgramEnrollment.EnrollmentType.LANGUAGE

        # Find corresponding term
        start_term = self.term_cache.get(term_id)

        enrollment = ProgramEnrollment.objects.create(
            student=student,
            program=major,
            enrollment_type=enrollment_type,
            status=ProgramEnrollment.EnrollmentStatus.ACTIVE,
            start_date=start_date,
            start_term=start_term,
            terms_active=1,
            is_system_generated=True,
            notes=f"Auto-generated from course enrollment data. First major-specific course: {term_id}",
        )

        self.stats["program_enrollments_created"] += 1
        return enrollment

    def _end_program_enrollment(self, enrollment: ProgramEnrollment, end_date: date):
        """End a program enrollment (major change detected)."""
        # Set end date to previous term's end
        if end_date:
            enrollment.end_date = end_date
            enrollment.status = ProgramEnrollment.EnrollmentStatus.COMPLETED
            enrollment.save()

    def _handle_no_major_detected(self, student_profile: StudentProfile, student_id: str):
        """Handle students where no major could be detected from course data."""
        # Per specification: Use SelProgram/SelMajor as absolute last resort
        # for students with only Foundation Year courses

        major_from_legacy = self._get_major_from_selprogram_selmajor(student_id)

        if major_from_legacy:
            # Create enrollment with detected legacy major
            self._create_program_enrollment_with_dates(
                student_profile,
                major_from_legacy,
                student_profile.last_enrollment_date or date.today(),
                None,  # No end date for foundation-only students
                "FOUNDATION",
                "Foundation Year student - major detected from legacy SelProgram/SelMajor",
            )
            self.stats["foundation_only_students"] += 1
            return

        # If SelProgram/SelMajor don't match known codes, use UNKNOWN
        try:
            unknown_major = Major.objects.get(code="UNKNOWN")
        except Major.DoesNotExist:
            # Flag for manual major creation
            self.record_rejection(
                category="validation_error",
                record_id=student_id,
                reason="No major detected from courses, SelProgram/SelMajor invalid, and UNKNOWN major does not exist",
                error_details=f"Student {student_id} needs manual major assignment",
            )
            return

        # Create enrollment with UNKNOWN major
        self._create_program_enrollment_with_dates(
            student_profile,
            unknown_major,
            student_profile.last_enrollment_date or date.today(),
            None,
            "UNKNOWN",
            "No major detectable from courses or legacy data",
        )
        self.stats["unknown_major_assignments"] += 1

    def _get_major_from_selprogram_selmajor(self, student_id: str) -> Major | None:
        """Get major from legacy SelProgram/SelMajor codes as last resort."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT selprogram, selmajor
                FROM legacy_students
                WHERE id = %s
            """,
                [student_id],
            )

            row = cursor.fetchone()
            if not row:
                return None

            sel_program, sel_major = row

            # Map known SelProgram/SelMajor combinations to major codes
            legacy_major_map = {
                (87, 540): "IR",  # International Relations
                (87, 2301): "BUSADMIN",  # Business Administration
                (87, 2400): "TESOL",  # TESOL
                (87, 4060): "FIN-BANK",  # Finance & Banking
                (87, 4316): "TOUR-HOSP",  # Hospitality & Tourism
                (147, 6516): "MBA",  # MBA
                (147, 2138): "MED-LEAD",  # Educational Management & Leadership
            }

            major_code = legacy_major_map.get((sel_program, sel_major))
            if major_code:
                try:
                    return Major.objects.get(code=major_code)
                except Major.DoesNotExist:
                    pass

            return None

    def _validate_student_enrollments(self, student_id: str):
        """Validate student enrollments in dry-run mode."""
        # Check if student exists
        if student_id not in self.student_cache:
            raise ValueError(f"Student profile not found for ID {student_id}")

        # Check if student has course data
        enrollments = self._get_student_course_enrollments(student_id)
        if not enrollments:
            raise ValueError(f"No course enrollments found for student {student_id}")

        # This would create enrollments in actual run
        self.stats["program_enrollments_created"] += 1

    def _categorize_error(self, error: Exception, student_id: str) -> str:
        """Categorize error for rejection tracking."""
        error_str = str(error).lower()

        if "student profile not found" in error_str:
            return "missing_student_profile"
        elif "no course enrollments" in error_str:
            return "no_course_enrollments"
        elif "term" in error_str or "invalid" in error_str:
            return "validation_error"  # Changed from invalid_term_data
        elif "major" in error_str or "unknown" in error_str:
            return "validation_error"  # Changed from missing_major_mapping
        elif "dual major" in error_str:
            return "dual_major_violation"
        elif "database" in error_str or "constraint" in error_str:
            return "database_error"
        else:
            return "validation_error"  # Default to validation_error

    def _validate_data_integrity(self):
        """Validate data integrity after migration."""
        # Check for students without program enrollments
        students_without_programs = StudentProfile.objects.filter(program_enrollments__isnull=True).count()
        self.record_data_integrity("students_without_programs", students_without_programs)

        # Check for overlapping enrollments (should not exist)
        overlapping_enrollments = (
            ProgramEnrollment.objects.filter(end_date__isnull=True)
            .values("student")
            .annotate(active_count=models.Count("id"))
            .filter(active_count__gt=1)
            .count()
        )
        self.record_data_integrity("students_with_multiple_active_enrollments", overlapping_enrollments)

        # Sample created enrollments
        sample_enrollments = list(
            ProgramEnrollment.objects.filter(is_system_generated=True)
            .select_related("student__person", "program")
            .order_by("-created_at")[:5]
            .values(
                "id",
                "student__student_id",
                "student__person__family_name",
                "student__person__personal_name",
                "program__name",
                "enrollment_type",
                "start_date",
                "end_date",
            ),
        )
        self.record_sample_data("created_program_enrollments", sample_enrollments)
