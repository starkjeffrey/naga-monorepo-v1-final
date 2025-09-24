"""Demo Enrollment Import for Business Administration and TESOL Students

Creates ClassHeaderEnrollment records from legacy course data for students
enrolled in Business Administration and TESOL programs (IDs > 10000) for demo purposes.
"""

from django.db import connection, transaction
from django.utils import timezone

from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Course, Major, Term
from apps.enrollment.models import ClassHeaderEnrollment, ProgramEnrollment
from apps.scheduling.models import ClassHeader


class Command(BaseMigrationCommand):
    """Import demo enrollments for Business Admin and TESOL students."""

    help = "Import demo enrollments for Business Admin and TESOL students (IDs > 10000)"

    def get_rejection_categories(self):
        return [
            "missing_student",
            "missing_course",
            "missing_term",
            "invalid_program",
            "duplicate_enrollment",
            "database_error",
        ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=400,
            help="Limit number of students to process (default: 400)",
        )
        parser.add_argument(
            "--majors",
            default="BUSADMIN,TESOL",
            help="Comma-separated major codes to include (default: BUSADMIN,TESOL)",
        )
        parser.add_argument(
            "--min-student-id",
            type=int,
            default=10000,
            help="Minimum student ID to include (default: 10000)",
        )

    def execute_migration(self, *args, **options):
        """Execute demo enrollment import."""
        limit = options["limit"]
        major_codes = [code.strip() for code in options["majors"].split(",")]
        min_student_id = options["min_student_id"]

        self.stdout.write(
            f"📊 Importing enrollments for {major_codes} majors, student IDs >= {min_student_id}, limit: {limit}",
        )

        # Cache data for efficiency
        self._load_caches()

        # Get target students
        target_students = self._get_target_students(major_codes, min_student_id, limit)

        self.record_input_stats(
            total_target_students=len(target_students),
            major_codes=major_codes,
            min_student_id=min_student_id,
            limit=limit,
        )

        self.stdout.write(f"🎯 Processing {len(target_students)} students")

        # Process each student
        created_enrollments = 0

        for student_data in target_students:
            try:
                with transaction.atomic():
                    enrollments_created = self._process_student_enrollments(student_data)
                    created_enrollments += enrollments_created

            except Exception as e:
                self.record_rejection("database_error", student_data["student_id"], str(e))

        self.record_success("enrollments_created", created_enrollments)
        self.stdout.write(f"✅ Created {created_enrollments} enrollment records")

    def _load_caches(self):
        """Load data caches for efficient lookup."""
        # Cache courses
        self.course_cache = {course.code: course for course in Course.objects.all()}

        # Cache terms
        self.term_cache = {term.code: term for term in Term.objects.all()}

        # Cache majors
        self.major_cache = {major.code: major for major in Major.objects.all()}

        self.stdout.write(
            f"📚 Cached {len(self.course_cache)} courses, {len(self.term_cache)} terms, {len(self.major_cache)} majors"
        )

    def _get_target_students(self, major_codes, min_student_id, limit):
        """Get target students with their program information - BA level only."""
        # Get majors - specifically BA level programs
        target_majors = []
        for code in major_codes:
            if code == "BUSADMIN":
                # Get BA Business Admin (code: BUSADMIN, not BUSADMIN-AA)
                major = self.major_cache.get("BUSADMIN")
                if major:
                    target_majors.append(major)
            elif code == "TESOL":
                # Get BA TESOL (code: TESOL, not MED-TESOL)
                major = self.major_cache.get("TESOL")
                if major:
                    target_majors.append(major)

        if not target_majors:
            raise ValueError(f"No BA-level majors found for codes: {major_codes}")

        # Get students enrolled in target BA programs with ACADEMIC enrollment type
        enrollments = (
            ProgramEnrollment.objects.filter(
                program__in=target_majors,
                enrollment_type="ACADEMIC",  # Only academic (BA) enrollments
            )
            .select_related("student", "program")
            .order_by("student__student_id")
        )

        students = []
        seen_students = set()

        for enrollment in enrollments:
            student_id_int = int(enrollment.student.student_id)
            student_id = enrollment.student.student_id

            if student_id_int >= min_student_id and student_id not in seen_students:
                students.append(
                    {
                        "student_id": student_id,
                        "student_profile": enrollment.student,
                        "major_code": enrollment.program.code,
                        "major": enrollment.program,
                    },
                )
                seen_students.add(student_id)

                if len(students) >= limit:
                    break

        return students

    def _process_student_enrollments(self, student_data):
        """Process all course enrollments for a single student."""
        student_id = student_data["student_id"]
        student_profile = student_data["student_profile"]
        major_code = student_data["major_code"]

        # Get signature courses for this major
        signature_courses = self._get_signature_courses(major_code)

        # Get student's course history from legacy data
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    parsed_termid,
                    parsed_coursecode,
                    normalizedlangcourse,
                    grade,
                    credit,
                    academic_year,
                    semester_offered
                FROM legacy_academiccoursetakers
                WHERE student_id = %s
                AND (
                    parsed_coursecode IN %s
                    OR normalizedlangcourse IS NOT NULL
                )
                AND grade NOT IN ('F', 'W', 'IP', 'I')
                ORDER BY parsed_termid, parsed_coursecode
            """,
                [student_id, tuple(signature_courses)],
            )

            course_records = cursor.fetchall()

        if not course_records:
            self.record_rejection("missing_course", student_id, "No relevant course data found")
            return 0

        enrollments_created = 0

        for record in course_records:
            term_id, course_code, lang_course, grade, credit, year, semester = record

            # Use course_code for academic courses, lang_course for language courses
            effective_course_code = course_code if course_code else lang_course
            if not effective_course_code:
                continue

            # Get or create course
            course = self.course_cache.get(effective_course_code)
            if not course:
                self.record_rejection(
                    "missing_course",
                    student_id,
                    f"Course not found: {effective_course_code}",
                )
                continue

            # Get term
            term = self.term_cache.get(term_id) if term_id else None
            if not term:
                self.record_rejection("missing_term", student_id, f"Term not found: {term_id}")
                continue

            # Create or get ClassHeader
            class_header = self._get_or_create_class_header(course, term, effective_course_code)

            # Check for existing enrollment
            existing_enrollment = ClassHeaderEnrollment.objects.filter(
                student=student_profile,
                class_header=class_header,
            ).first()

            if existing_enrollment:
                continue  # Skip duplicates

            # Create enrollment
            ClassHeaderEnrollment.objects.create(
                student=student_profile,
                class_header=class_header,
                status="COMPLETED",
                final_grade=grade,
                enrollment_date=timezone.now(),
                completion_date=timezone.now(),
                enrolled_by_id=1,  # System user
                notes=f"Demo import - {major_code} signature course",
            )

            enrollments_created += 1

        return enrollments_created

    def _get_or_create_class_header(self, course, term, course_code):
        """Get or create ClassHeader for course and term."""
        # Try to find existing class header
        class_header = ClassHeader.objects.filter(course=course, term=term).first()

        if class_header:
            return class_header

        # Create new class header
        class_header = ClassHeader.objects.create(
            course=course,
            term=term,
            section_id="001",  # Default section
            capacity=30,  # Default capacity
            enrolled_count=0,
            is_active=True,
            notes=f"Demo class for {course_code}",
        )

        return class_header

    def _get_signature_courses(self, major_code):
        """Get signature courses for a major."""
        signature_courses = {
            "BUSADMIN": [
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
            ],
            "TESOL": [
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
            ],
        }

        return signature_courses.get(major_code, [])
