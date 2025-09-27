"""
FIXED 2025 ACADEMIC COURSE TAKERS LOADER

CRITICAL BUSINESS RULES:
1. NEVER create courses - only use existing Course table entries
2. Use only existing terms from Term table
3. Use integer IDs that match existing students
4. IEAP classes: ClassHeader → ClassSession → ClassPart (2 parts matched by program/time/section)
5. EHSS/GESL/WKEND: ClassHeader → ClassPart (no session concept)

Uses processed data from academiccoursetakers_stage3_cleaned with parsed course codes.
"""

import logging

from django.db import connection

from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Course, Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.people.models import StudentProfile
from apps.scheduling.models import ClassHeader, ClassPart

logger = logging.getLogger(__name__)


class Command(BaseMigrationCommand):
    """Fixed loader for 2025 academic course takers using SIS-first approach"""

    help = "Load 2025 academiccoursetakers from pipeline stage3 data into Django models"

    def get_rejection_categories(self):
        return [
            "missing_student",
            "missing_course",
            "missing_term",
            "invalid_data",
            "duplicate_enrollment",
            "processing_error",
        ]

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Show what would be loaded without making changes")
        parser.add_argument("--limit", type=int, help="Limit number of records to process")
        parser.add_argument("--batch-size", type=int, default=100, help="Batch size for processing")

    def execute_migration(self, *args, **options):
        self.dry_run = options.get("dry_run", False)
        self.limit = options.get("limit")
        self.batch_size = options.get("batch_size", 100)

        self.stdout.write("🚀 FIXED 2025 Academic Course Takers Loader")
        self.stdout.write(f"   Dry run: {self.dry_run}")

        if self.dry_run:
            self.stdout.write("   ⚠️  DRY RUN MODE - No changes will be made")

        # Record input statistics from stage3 data
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*)
                FROM academiccoursetakers_stage3_cleaned
                WHERE parsed_term_id LIKE '25%'
            """)
            total_2025_records = cursor.fetchone()[0]

        self.record_input_stats(
            total_records=total_2025_records, source_file="academiccoursetakers_stage3_cleaned (2025 terms only)"
        )

        # Load reference data
        self.load_reference_data()

        # Process 2025 enrollment records
        self.process_2025_enrollments()

        # Generate final report
        self.generate_final_report()

    def load_reference_data(self):
        """Load existing courses, terms, and students from SIS"""
        self.course_cache = {}
        self.term_cache = {}
        self.student_cache = {}

        # Load existing courses
        course_count = Course.objects.count()
        for course in Course.objects.all():
            self.course_cache[course.code] = course

        # Load existing terms
        term_count = Term.objects.count()
        for term in Term.objects.all():
            self.term_cache[term.code] = term

        # Load existing students
        student_count = StudentProfile.objects.count()
        for student in StudentProfile.objects.select_related("person"):
            # Cache by both student_id and zero-padded formats
            self.student_cache[str(student.student_id)] = student
            self.student_cache[str(student.student_id).zfill(5)] = student

        self.stdout.write("📋 Reference Data Loaded:")
        self.stdout.write(f"   Courses: {course_count:,}")
        self.stdout.write(f"   Terms: {term_count:,}")
        self.stdout.write(f"   Students: {student_count:,}")

        # Check status
        if course_count == 0:
            self.stdout.write(self.style.ERROR("❌ No courses found in Course table!"))
            self.stdout.write("   You need to load courses into the SIS first")

        if term_count == 0:
            self.stdout.write(self.style.ERROR("❌ No terms found in Term table!"))
            self.stdout.write("   You need to load terms into the SIS first")

    def process_2025_enrollments(self):
        """Process 2025 enrollment records from stage3 data"""

        with connection.cursor() as cursor:
            # Get 2025 enrollment records with parsed data
            query = """
                SELECT
                    student_id,
                    class_id,
                    parsed_course_code,
                    parsed_term_id,
                    final_grade,
                    credit_hours,
                    grade_points,
                    attendance_status,
                    is_passed,
                    legacy_id
                FROM academiccoursetakers_stage3_cleaned
                WHERE parsed_term_id LIKE '25%'
                AND parsed_course_code IS NOT NULL
                ORDER BY parsed_term_id, parsed_course_code, student_id
            """

            if self.limit:
                query += f" LIMIT {self.limit}"

            cursor.execute(query)

            batch = []
            for row in cursor.fetchall():
                batch.append(row)

                if len(batch) >= self.batch_size:
                    self.process_enrollment_batch(batch)
                    batch = []

            # Process remaining batch
            if batch:
                self.process_enrollment_batch(batch)

    def process_enrollment_batch(self, batch):
        """Process a batch of enrollment records"""

        for record in batch:
            (
                student_id,
                class_id,
                parsed_course_code,
                parsed_term_id,
                final_grade,
                credit_hours,
                grade_points,
                attendance_status,
                is_passed,
                legacy_id,
            ) = record

            try:
                self.process_single_enrollment(
                    student_id,
                    class_id,
                    parsed_course_code,
                    parsed_term_id,
                    final_grade,
                    credit_hours,
                    grade_points,
                    attendance_status,
                    is_passed,
                    legacy_id,
                )

            except Exception as e:
                self.record_rejection(
                    category="processing_error", record_id=legacy_id, reason=f"Failed to process enrollment: {e!s}"
                )
                logger.error("Failed to process enrollment %s: %s", legacy_id, e)

    def process_single_enrollment(
        self,
        student_id,
        class_id,
        parsed_course_code,
        parsed_term_id,
        final_grade,
        credit_hours,
        grade_points,
        attendance_status,
        is_passed,
        legacy_id,
    ):
        """Process a single enrollment record"""

        # Validate required data exists in SIS

        if student_id not in self.student_cache:
            self.record_rejection(
                category="missing_student", record_id=legacy_id, reason=f"Student {student_id} not found in SIS"
            )
            return

        # Apply normalization to check if course exists
        normalized_course_code = self.normalize_course_code(parsed_course_code)
        if normalized_course_code not in self.course_cache:
            self.record_rejection(
                category="missing_course",
                record_id=legacy_id,
                reason=f"Course {parsed_course_code} -> {normalized_course_code} not found in SIS Course table",
            )
            return

        # Extract base term code (remove suffixes like 'E', 'M', 'B')
        base_term_code = parsed_term_id[:6] if len(parsed_term_id) >= 6 else parsed_term_id
        if base_term_code not in self.term_cache:
            self.record_rejection(
                category="missing_term",
                record_id=legacy_id,
                reason=f"Term {base_term_code} not found in SIS Term table",
            )
            return

        # All dependencies exist - record successful validation
        self.record_success("validated_enrollment", 1)

        if not self.dry_run:
            # Create class structure and enrollment
            self.create_class_and_enrollment(
                student_id,
                class_id,
                parsed_course_code,
                parsed_term_id,
                final_grade,
                credit_hours,
                grade_points,
                attendance_status,
                is_passed,
                legacy_id,
            )

    def create_class_and_enrollment(
        self,
        student_id,
        class_id,
        parsed_course_code,
        parsed_term_id,
        final_grade,
        credit_hours,
        grade_points,
        attendance_status,
        is_passed,
        legacy_id,
    ):
        """Create class structure and enrollment based on course type"""

        student = self.student_cache[student_id]

        # Apply normalization to get the correct course code
        normalized_course_code = self.normalize_course_code(parsed_course_code)
        course = self.course_cache[normalized_course_code]

        base_term_code = parsed_term_id[:6] if len(parsed_term_id) >= 6 else parsed_term_id
        term = self.term_cache[base_term_code]

        # Determine class structure based on course type
        if self.is_ieap_course(parsed_course_code):
            # IEAP: ClassHeader → ClassSession → ClassPart (2 parts)
            class_header, _class_session, class_part = self.create_ieap_class_structure(course, term, class_id)
        else:
            # EHSS/GESL/WKEND: ClassHeader → ClassPart (no session)
            class_header, _class_part = self.create_standard_class_structure(course, term, class_id)

        # Create enrollment
        self.create_enrollment(
            student, class_header, final_grade, credit_hours, grade_points, attendance_status, is_passed
        )

        self.record_success("enrollment_created", 1)

    def normalize_course_code(self, parsed_code):
        """Convert parsed course code to normalized course code (matches Course.code field)

        This applies the normalization logic from yesterday's 4-hour parsing work.
        Examples: EHSS-1A -> EHSS-01, GESL-2B -> GESL-02, IEAP-3C -> IEAP-03
        """
        import re

        if not parsed_code:
            return None

        # EHSS patterns: EHSS-1A -> EHSS-01
        ehss_match = re.match(r"^EHSS-(\d+)([ABCD]?)$", parsed_code, re.IGNORECASE)
        if ehss_match:
            level = ehss_match.group(1).zfill(2)
            return f"EHSS-{level}"

        # GESL patterns: GESL-1A -> GESL-01
        gesl_match = re.match(r"^GESL-(\d+)([ABCD]?)$", parsed_code, re.IGNORECASE)
        if gesl_match:
            level = gesl_match.group(1).zfill(2)
            return f"GESL-{level}"

        # IEAP patterns: IEAP-1A -> IEAP-01
        ieap_match = re.match(r"^IEAP-(\d+)([ABCD]?)$", parsed_code, re.IGNORECASE)
        if ieap_match:
            level = ieap_match.group(1).zfill(2)
            return f"IEAP-{level}"

        # For complex combinations or academic courses, return as-is
        # These should match existing course codes directly
        return parsed_code

    def is_ieap_course(self, course_code):
        """Check if this is an IEAP course that needs sessions"""
        return course_code.startswith("IEAP-")

    def create_ieap_class_structure(self, course, term, class_id):
        """Create ClassHeader → ClassSession → ClassPart for IEAP courses"""
        # TODO: Implement IEAP class structure creation
        # This requires matching pairs by program/time/section
        raise NotImplementedError("IEAP class structure creation not yet implemented")

    def create_standard_class_structure(self, course, term, class_id):
        """Create ClassHeader → ClassPart for EHSS/GESL/WKEND courses"""

        # Create or get ClassHeader
        class_header, created = ClassHeader.objects.get_or_create(
            course=course,
            term=term,
            section="A",  # Default section
            defaults={"max_enrollment": 25, "current_enrollment": 0},
        )

        if created:
            self.record_success("class_header_created", 1)

        # Create or get ClassPart
        class_part, created = ClassPart.objects.get_or_create(
            class_header=class_header, part_type="Main", defaults={"max_enrollment": 25, "current_enrollment": 0}
        )

        if created:
            self.record_success("class_part_created", 1)

        return class_header, class_part

    def create_enrollment(
        self, student, class_header, final_grade, credit_hours, grade_points, attendance_status, is_passed
    ):
        """Create enrollment record"""

        enrollment, _created = ClassHeaderEnrollment.objects.get_or_create(
            student_profile=student,
            class_header=class_header,
            defaults={
                "enrollment_status": "enrolled",
                "final_grade": final_grade,
                "grade_points": grade_points,
                "credits_earned": credit_hours if is_passed else 0,
                "attendance_status": attendance_status,
            },
        )

        return enrollment

    def generate_final_report(self):
        """Generate final migration report"""

        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("🎯 FIXED 2025 LOADER RESULTS")
        self.stdout.write("=" * 60)

        # Get current statistics
        stats = self.get_migration_stats()

        self.stdout.write("📊 Processing Statistics:")
        self.stdout.write(f"   Validated enrollments: {stats.get('validated_enrollment', 0):,}")
        self.stdout.write(f"   Enrollments created: {stats.get('enrollment_created', 0):,}")
        self.stdout.write(f"   Class headers created: {stats.get('class_header_created', 0):,}")
        self.stdout.write(f"   Class parts created: {stats.get('class_part_created', 0):,}")

        self.stdout.write("\n❌ Rejections by category:")
        rejection_stats = self.get_rejection_stats()
        for category, count in rejection_stats.items():
            self.stdout.write(f"   {category}: {count:,}")

        if not self.dry_run:
            self.stdout.write("\n✅ Data successfully loaded into Django models")
        else:
            self.stdout.write("\n⚠️  DRY RUN completed - no data was modified")
