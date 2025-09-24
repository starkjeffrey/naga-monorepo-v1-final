"""[DEPRECATED] Course Fulfillment Population for Business Administration and TESOL Students

⚠️ DEPRECATED: This command uses the legacy requirement system (StudentRequirementFulfillment).
The new system uses CanonicalRequirement and StudentDegreeProgress models.
This command should not be used and will be removed in a future version.

Creates StudentRequirementFulfillment records based on completed courses
for students enrolled in Business Administration and TESOL programs.
"""

from decimal import Decimal

from django.db import connection, transaction
from django.utils import timezone

from apps.academic.models import StudentRequirementFulfillment
from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Course, Major
from apps.enrollment.models import ProgramEnrollment


class Command(BaseMigrationCommand):
    """Populate course fulfillments for Business Admin and TESOL students."""

    help = "Populate course fulfillments for Business Admin and TESOL students (IDs > 10000)"

    def get_rejection_categories(self):
        return [
            "missing_student",
            "missing_enrollment",
            "missing_course",
            "invalid_program",
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
        """Execute course fulfillment population."""
        limit = options["limit"]
        major_codes = [code.strip() for code in options["majors"].split(",")]
        min_student_id = options["min_student_id"]

        self.stdout.write(
            f"📊 Populating fulfillments for {major_codes} majors, student IDs >= {min_student_id}, limit: {limit}",
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
        created_fulfillments = 0

        for student_data in target_students:
            try:
                with transaction.atomic():
                    fulfillments_created = self._process_student_fulfillments(student_data)
                    created_fulfillments += fulfillments_created

            except Exception as e:
                self.record_rejection("database_error", student_data["student_id"], str(e))

        self.record_success("fulfillments_created", created_fulfillments)
        self.stdout.write(f"✅ Created {created_fulfillments} fulfillment records")

    def _load_caches(self):
        """Load data caches for efficient lookup."""
        # Cache courses
        self.course_cache = {course.code: course for course in Course.objects.all()}

        # Cache majors
        self.major_cache = {major.code: major for major in Major.objects.all()}

        self.stdout.write(f"📚 Cached {len(self.course_cache)} courses, {len(self.major_cache)} majors")

    def _get_target_students(self, major_codes, min_student_id, limit):
        """Get target students with their program information - BA level only."""
        # Get BA-level majors
        target_majors = []
        for code in major_codes:
            major = self.major_cache.get(code)
            if major:
                target_majors.append(major)

        if not target_majors:
            raise ValueError(f"No majors found for codes: {major_codes}")

        # Get students enrolled in target BA programs with ACADEMIC enrollment type
        enrollments = (
            ProgramEnrollment.objects.filter(program__in=target_majors, enrollment_type="ACADEMIC")
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

    def _process_student_fulfillments(self, student_data):
        """Process course fulfillments for a single student."""
        student_id = student_data["student_id"]
        student_profile = student_data["student_profile"]
        major_code = student_data["major_code"]

        # Get signature courses for this major
        signature_courses = self._get_signature_courses(major_code)

        # Get student's completed courses from legacy data (using actual completed courses)
        with connection.cursor() as cursor:
            # Create proper SQL placeholder for IN clause
            placeholder = ",".join(["%s"] * len(signature_courses))

            # Construct SQL query safely with proper parameterization
            sql_query = f"""
                SELECT
                    parsed_coursecode,
                    TRIM(grade) as grade,
                    credit,
                    academic_year,
                    parsed_termid
                FROM legacy_academiccoursetakers
                WHERE student_id = %s
                AND parsed_coursecode IN ({placeholder})
                AND TRIM(grade) NOT IN ('F', 'W', 'IP', 'I', 'AU')
                AND grade IS NOT NULL
                ORDER BY parsed_termid, parsed_coursecode
            """

            cursor.execute(
                sql_query,
                [str(student_id).zfill(5), *list(signature_courses)],
            )

            course_records = cursor.fetchall()

        if not course_records:
            self.record_rejection("missing_course", student_id, "No signature courses completed")
            return 0

        fulfillments_created = 0

        for record in course_records:
            course_code, grade, credit, _year, term_id = record

            # Get course
            course = self.course_cache.get(course_code)
            if not course:
                continue

            # Find the term when this requirement was actually fulfilled
            from apps.curriculum.models import Term

            fulfillment_term = Term.objects.filter(code=term_id).first()

            # Determine fulfillment date - prefer term end date for academic accuracy
            if fulfillment_term and fulfillment_term.end_date:
                fulfillment_date = fulfillment_term.end_date
                term_info = f"completed in {fulfillment_term.description}"
            else:
                # Fallback to processing date if no term found
                fulfillment_date = timezone.now()
                term_info = f"completed in term {term_id} (term not found in system)"

            # Create requirement fulfillment
            self._get_requirement_category(major_code, course_code)

            # Find the canonical requirement that this specific course fulfills
            major = self.major_cache.get(major_code)
            if not major:
                continue

            # Look for canonical requirement for this exact course
            from apps.academic.canonical_models import CanonicalRequirement

            canonical_requirement = CanonicalRequirement.objects.filter(
                major=major,
                required_course=course,
                is_active=True,
            ).first()

            if not canonical_requirement:
                # This course doesn't have a canonical requirement defined yet
                # Skip it for now - canonical requirements should be pre-defined
                continue

            # For now, we need to create/find a legacy requirement that maps to this canonical requirement
            # This is a bridge until the system fully transitions to canonical-only
            from apps.academic.models import Requirement, RequirementType

            # Find or create a legacy requirement for this canonical requirement
            general_type = RequirementType.objects.filter(code="CANONICAL").first()
            if not general_type:
                general_type = RequirementType.objects.create(
                    name="Canonical Requirements",
                    code="CANONICAL",
                    description="Legacy bridge to canonical requirements",
                )

            # Create bridge requirement that matches the canonical requirement
            legacy_requirement, _created = Requirement.objects.get_or_create(
                major=major,
                requirement_type=general_type,
                name=canonical_requirement.name,
                defaults={
                    "description": f"Bridge to canonical requirement: {canonical_requirement.name}",
                    "required_courses_count": 1,
                    "effective_term_id": 1,  # Default term
                    "is_active": True,
                },
            )

            # Check for existing fulfillment
            existing = StudentRequirementFulfillment.objects.filter(
                student=student_profile,
                fulfilling_course=course,
                requirement=legacy_requirement,
            ).first()

            if existing:
                continue  # Skip duplicates

            # CRITICAL: Handle Course Retake Logic
            # Issue: Need to implement course retake functionality
            # When admin approves student to retake a course they already fulfilled:
            # 1. Student completed BUS-464 with grade "D" (fulfilled requirement)
            # 2. Admin approves retake for grade improvement
            # 3. Student completes BUS-464 again with grade "B"
            # 4. System must:
            #    a) Update fulfillment_date to newer term completion date
            #    b) Update grade reference in notes to show improved grade
            #    c) Coordinate with GPA calculation to use higher grade only
            #    d) Mark original grade as "replaced" in transcript/GPA logic
            # 5. Business rules needed:
            #    - Which grade policies apply? (higher grade wins, most recent wins, etc.)
            #    - How to handle credits (avoid double-counting in degree progress)
            #    - Integration with transcript and GPA calculation services
            # 6. Implementation needs:
            #    - Service to detect and handle retaken courses
            #    - Update existing fulfillment vs create new fulfillment logic
            #    - Academic policy configuration for retake rules
            #    - Coordination with grade/transcript management system

            # Create fulfillment record using legacy requirement (bridge to canonical)
            # Since we only process completed courses with passing grades, mark as fulfilled
            StudentRequirementFulfillment.objects.create(
                student=student_profile,
                requirement=legacy_requirement,
                fulfilling_course=course,
                credits_applied=self._parse_credit_value(credit),  # Parse credit value safely
                courses_applied=1,
                fulfillment_source="COURSE_COMPLETION",
                is_fulfilled=True,  # Requirement is fulfilled by course completion
                fulfillment_date=fulfillment_date,  # Use actual term completion date
                notes=(
                    f"Course {course_code} (Grade: {grade}) fulfills canonical requirement: "
                    f"{canonical_requirement.name}, {term_info}"
                ),
            )

            fulfillments_created += 1

        return fulfillments_created

    def _get_requirement_category(self, major_code, course_code):
        """Map course to requirement category."""
        # Business Administration categories
        if major_code == "BUSADMIN":
            if course_code in ["BUS-464", "BUS-465", "BUS-425", "BUS-460", "BUS-463"]:
                return "CORE_BUSINESS"
            elif course_code in ["BUS-489"]:
                return "CAPSTONE"
            elif course_code in ["ECON-212"]:
                return "ECONOMICS"
            elif course_code in ["MGT-489", "MGT-467"]:
                return "MANAGEMENT"
            elif course_code in ["BUS-360", "BUS-461"]:
                return "FINANCE"
            else:
                return "BUSINESS_ELECTIVE"

        # TESOL categories
        elif major_code == "TESOL":
            if course_code.startswith("ENGL-"):
                return "ENGLISH_CORE"
            elif course_code.startswith("EDUC-"):
                return "EDUCATION_CORE"
            elif course_code in ["PHIL-213", "LIT-325", "PSYC-313"]:
                return "SUPPORT_COURSES"
            else:
                return "TESOL_ELECTIVE"

        return "GENERAL_REQUIREMENT"

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

    def _parse_credit_value(self, credit):
        """Parse credit value safely to Decimal."""
        if not credit:
            return Decimal("3.00")

        try:
            # Convert to string first, handle various formats
            credit_str = str(credit).strip()
            if not credit_str or credit_str.lower() == "null":
                return Decimal("3.00")
            return Decimal(credit_str)
        except (ValueError, TypeError, Exception):
            return Decimal("3.00")  # Default fallback
