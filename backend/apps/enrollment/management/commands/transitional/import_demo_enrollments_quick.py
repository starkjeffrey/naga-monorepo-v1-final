"""Quick Demo Enrollment Import using SelMajor from legacy_students

Creates ClassHeaderEnrollment records for students with SelMajor 2301 (Business)
or 2400 (TESOL) from legacy_students table.
"""

from django.db import connection, transaction
from django.utils import timezone

from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Course, Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.people.models import StudentProfile
from apps.scheduling.models import ClassHeader


class Command(BaseMigrationCommand):
    """Quick demo enrollment import using SelMajor field."""

    help = "Quick demo enrollment import for Business (2301) and TESOL (2400) students"

    def get_rejection_categories(self):
        return [
            "missing_student",
            "missing_course",
            "missing_term",
            "no_courses",
            "database_error",
        ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=400,
            help="Limit number of students to process (default: 400)",
        )

    def execute_migration(self, *args, **options):
        """Execute quick demo enrollment import."""
        limit = options["limit"]

        self.stdout.write(f"📊 Quick import for Business (2301) and TESOL (2400) students, limit: {limit}")

        # Cache data
        self._load_caches()

        # Get target students from legacy_students
        target_students = self._get_target_students_from_legacy(limit)

        self.record_input_stats(
            total_target_students=len(target_students),
            selection_criteria="SelMajor IN (2301, 2400)",
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
        """Load data caches."""
        self.course_cache = {course.code: course for course in Course.objects.all()}
        self.term_cache = {term.code: term for term in Term.objects.all()}

        self.stdout.write(f"📚 Cached {len(self.course_cache)} courses, {len(self.term_cache)} terms")

    def _get_target_students_from_legacy(self, limit):
        """Get target students from legacy_students with SelMajor 2301 or 2400."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    ls.student_id,
                    ls.selected_major,
                    CASE
                        WHEN ls.selected_major = 'Business Administration' THEN 'BUSADMIN'
                        WHEN ls.selected_major = 'TESOL' THEN 'TESOL'
                        ELSE 'UNKNOWN'
                    END as major_code
                FROM legacy_students ls
                WHERE ls.selected_major IN ('Business Administration', 'TESOL')
                AND CAST(ls.student_id AS INTEGER) >= 10000
                ORDER BY ls.student_id
                LIMIT %s
            """,
                [limit],
            )

            results = cursor.fetchall()

        students = []
        for student_id, sel_major, major_code in results:
            # Get student profile
            try:
                student_profile = StudentProfile.objects.get(student_id=student_id)
                students.append(
                    {
                        "student_id": student_id,
                        "student_profile": student_profile,
                        "sel_major": sel_major,
                        "major_code": major_code,
                    },
                )
            except StudentProfile.DoesNotExist:
                self.record_rejection("missing_student", student_id, "Student profile not found")

        return students

    def _process_student_enrollments(self, student_data):
        """Process enrollments for a single student."""
        student_id = student_data["student_id"]
        student_profile = student_data["student_profile"]
        major_code = student_data["major_code"]

        # Get signature courses for this major
        signature_courses = self._get_signature_courses(major_code)

        # Get student's course history for signature courses
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    parsed_termid,
                    parsed_coursecode,
                    grade,
                    credit,
                    academic_year
                FROM legacy_academiccoursetakers
                WHERE student_id = %s
                AND parsed_coursecode IN %s
                AND grade NOT IN ('F', 'W', 'IP', 'I')
                AND grade IS NOT NULL
                ORDER BY parsed_termid, parsed_coursecode
            """,
                [student_id, tuple(signature_courses)],
            )

            course_records = cursor.fetchall()

        if not course_records:
            self.record_rejection("no_courses", student_id, f"No {major_code} signature courses found")
            return 0

        enrollments_created = 0

        for record in course_records:
            term_id, course_code, grade, credit, year = record

            # Get course
            course = self.course_cache.get(course_code)
            if not course:
                self.record_rejection("missing_course", student_id, f"Course not found: {course_code}")
                continue

            # Get term
            term = self.term_cache.get(term_id) if term_id else None
            if not term:
                self.record_rejection("missing_term", student_id, f"Term not found: {term_id}")
                continue

            # Get or create ClassHeader
            class_header = self._get_or_create_class_header(course, term, course_code)

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
                notes=f"Quick demo import - {major_code} (SelMajor: {student_data['sel_major']})",
            )

            enrollments_created += 1

        return enrollments_created

    def _get_or_create_class_header(self, course, term, course_code):
        """Get or create ClassHeader."""
        class_header = ClassHeader.objects.filter(course=course, term=term).first()

        if class_header:
            return class_header

        return ClassHeader.objects.create(
            course=course,
            term=term,
            section_id="001",
            capacity=30,
            enrolled_count=0,
            is_active=True,
            notes=f"Demo class for {course_code}",
        )

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
