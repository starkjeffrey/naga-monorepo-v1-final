"""Simple Program Enrollment Generation for Demo

Creates basic ProgramEnrollment records from legacy course data for demo purposes.
"""

from datetime import date

from django.db import connection, transaction

from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Major
from apps.enrollment.models import ProgramEnrollment
from apps.people.models import StudentProfile


class Command(BaseMigrationCommand):
    """Generate basic ProgramEnrollment records for demo."""

    help = "Generate basic ProgramEnrollment records from legacy course data"

    def get_rejection_categories(self):
        return ["missing_student", "missing_major", "no_courses", "database_error"]

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Clear existing ProgramEnrollment records",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of students to process",
        )

    def execute_migration(self, *args, **options):
        """Execute demo enrollment generation."""
        if options["clear_existing"]:
            deleted_count = ProgramEnrollment.objects.count()
            ProgramEnrollment.objects.all().delete()
            self.stdout.write(f"🗑️  Cleared {deleted_count} existing records")

        # Cache majors
        majors = {major.code: major for major in Major.objects.all()}

        # Language program mapping
        lang_programs = {
            "IEAP": majors.get("IEAP"),
            "EHSS": majors.get("EHSS"),
            "GESL": majors.get("GESL"),
        }

        # Academic major course prefixes
        academic_majors = {
            "POL": majors.get("IR"),  # International Relations
            "BUS": majors.get("BUSADMIN"),  # Business Admin
            "FIN": majors.get("FIN-BANK"),  # Finance
            "THM": majors.get("TOUR-HOSP"),  # Tourism
            "TESOL": majors.get("TESOL"),  # TESOL
            "ENGL": majors.get("TESOL"),  # English courses → TESOL
            "EDUC": majors.get("TESOL"),  # Education courses → TESOL
        }

        # Get students with course data
        with connection.cursor() as cursor:
            limit_clause = f"LIMIT {options['limit']}" if options.get("limit") else ""

            cursor.execute(
                f"""
                SELECT DISTINCT student_id
                FROM legacy_academiccoursetakers
                WHERE student_id IS NOT NULL
                AND CAST(student_id AS INTEGER) >= 10000
                ORDER BY student_id
                {limit_clause}
            """
            )

            student_ids = [row[0] for row in cursor.fetchall()]

        self.stdout.write(f"📊 Processing {len(student_ids)} students")

        created_count = 0

        for student_id in student_ids:
            try:
                with transaction.atomic():
                    # Get student profile
                    try:
                        student = StudentProfile.objects.get(student_id=student_id)
                    except StudentProfile.DoesNotExist:
                        self.record_rejection("missing_student", student_id, "Student profile not found")
                        continue

                    # Get student's course history
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT
                                parsed_termid,
                                parsed_coursecode,
                                normalizedlangcourse,
                                grade,
                                academic_year
                            FROM legacy_academiccoursetakers
                            WHERE student_id = %s
                            AND (parsed_coursecode IS NOT NULL OR normalizedlangcourse IS NOT NULL)
                            ORDER BY parsed_termid, parsed_coursecode
                        """,
                            [student_id],
                        )

                        courses = cursor.fetchall()

                    if not courses:
                        self.record_rejection("no_courses", student_id, "No course data found")
                        continue

                    # Detect programs
                    programs_detected = {}

                    for term, course_code, lang_course, _grade, year in courses:
                        if not term or not year:
                            continue

                        # Language program detection
                        if lang_course:
                            if "IEAP" in lang_course and "IEAP" not in programs_detected:
                                programs_detected["IEAP"] = {
                                    "major": lang_programs["IEAP"],
                                    "start_year": year,
                                    "type": "LANGUAGE",
                                }
                            elif "EHSS" in lang_course and "EHSS" not in programs_detected:
                                programs_detected["EHSS"] = {
                                    "major": lang_programs["EHSS"],
                                    "start_year": year,
                                    "type": "LANGUAGE",
                                }
                            elif "GESL" in lang_course and "GESL" not in programs_detected:
                                programs_detected["GESL"] = {
                                    "major": lang_programs["GESL"],
                                    "start_year": year,
                                    "type": "LANGUAGE",
                                }

                        # Academic major detection
                        if course_code:
                            prefix = course_code.split("-")[0] if "-" in course_code else course_code[:3]
                            if prefix in academic_majors and prefix not in programs_detected:
                                major = academic_majors[prefix]
                                if major:
                                    programs_detected[prefix] = {
                                        "major": major,
                                        "start_year": year,
                                        "type": "ACADEMIC",
                                    }

                    # Create ProgramEnrollment records
                    for program_key, program_info in programs_detected.items():
                        major = program_info["major"]
                        if not major:
                            continue

                        start_date = date(int(program_info["start_year"]), 1, 1)

                        # Check if enrollment already exists
                        existing = ProgramEnrollment.objects.filter(
                            student=student,
                            program=major,
                            start_date=start_date,
                        ).first()

                        if not existing:
                            ProgramEnrollment.objects.create(
                                student=student,
                                program=major,
                                enrollment_type=program_info["type"],
                                status="ACTIVE",
                                start_date=start_date,
                                is_system_generated=True,
                                notes=f"Demo generation from {program_key} courses",
                            )
                            created_count += 1

            except Exception as e:
                self.record_rejection("database_error", student_id, str(e))

        self.record_success("program_enrollments_created", created_count)
        self.stdout.write(f"✅ Created {created_count} program enrollments")
