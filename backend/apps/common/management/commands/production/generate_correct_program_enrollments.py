"""Generate correct ProgramEnrollment records based on academic course taker data.

Business Rules:
1. One record for every change in program/major
2. Correct start and end dates with start and finishing levels
3. Active status only if enrolled in currently active term
4. Finishing level filled for all records except the last
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.curriculum.models import Major, Term
from apps.enrollment.models import ClassHeaderEnrollment, ProgramEnrollment
from apps.people.models import StudentProfile


class Command(BaseCommand):
    help = "Generate correct ProgramEnrollment records from academiccoursetakers data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without making changes",
        )
        parser.add_argument(
            "--student-ids",
            type=str,
            help="Comma-separated student IDs to process (e.g., '10700,10750,10800' or '10700-10800')",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        student_ids = options.get("student_ids")

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No data will be modified"))

        # Parse student ID filter
        student_filter = self._parse_student_ids(student_ids)

        # Get students to process
        students_qs = StudentProfile.objects.select_related("person")
        if student_filter:
            students_qs = students_qs.filter(student_id__in=student_filter)
            self.stdout.write(f"📊 Processing {len(student_filter)} specific students")
        else:
            self.stdout.write("📊 Processing ALL students")

        students = list(students_qs)
        self.stdout.write(f"📋 Found {len(students)} students to process")

        # Process students (individual transactions for better error handling)
        self._process_students(students, dry_run)

        self.stdout.write(self.style.SUCCESS("✅ Program enrollment generation completed"))

    def _parse_student_ids(self, student_ids_str):
        """Parse student ID string into list of integers."""
        if not student_ids_str:
            return None

        student_ids = []
        for part in student_ids_str.split(","):
            part = part.strip()
            if "-" in part:
                # Range like "10700-10800"
                start, end = map(int, part.split("-"))
                student_ids.extend(range(start, end + 1))
            else:
                # Single ID
                student_ids.append(int(part))

        return student_ids

    def _process_students(self, students, dry_run):
        """Process each student to generate correct program enrollments."""
        created_count = 0

        for student in students:
            try:
                enrollments_created = self._process_student(student, dry_run)
                created_count += enrollments_created

                if enrollments_created > 0:
                    self.stdout.write(f"✅ Student {student.student_id}: {enrollments_created} program enrollments")

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Error processing student {student.student_id}: {e}"))

        self.stdout.write(f"📊 Total program enrollments created: {created_count}")

    def _process_student(self, student, dry_run):
        """Generate program enrollments for a single student."""
        # Get all class enrollments for this student, ordered by date
        enrollments = (
            ClassHeaderEnrollment.objects.filter(student=student)
            .select_related("class_header__course", "class_header__term")
            .order_by("enrollment_date", "class_header__term__start_date")
        )

        if not enrollments.exists():
            return 0

        # Group enrollments by program transitions
        program_periods = self._identify_program_periods(enrollments)

        # Create ProgramEnrollment records with individual transactions
        created_count = 0
        for period in program_periods:
            if not dry_run:
                try:
                    with transaction.atomic():
                        self._create_program_enrollment(student, period)
                        created_count += 1
                except Exception as e:
                    self.stdout.write(f"    ⚠️  Failed to create {period['major']}: {e}")
            else:
                self._preview_program_enrollment(student, period)
                created_count += 1

        return created_count

    def _identify_program_periods(self, enrollments):
        """Identify distinct program periods from class enrollments."""
        periods = []
        current_period = None

        for enrollment in enrollments:
            course = enrollment.class_header.course
            term = enrollment.class_header.term

            # Determine program and major from course
            program_info = self._get_program_from_course(course)

            # Check if this is a new program period
            if (
                current_period is None
                or current_period["major"] != program_info["major"]
                or current_period["program"] != program_info["program"]
            ):
                # Finalize previous period
                if current_period:
                    current_period["end_date"] = self._get_previous_term_end(term)
                    current_period["finishing_level"] = self._determine_finishing_level(current_period["enrollments"])
                    periods.append(current_period)

                # Start new period
                current_period = {
                    "program": program_info["program"],
                    "major": program_info["major"],
                    "start_date": term.start_date,
                    "start_level": self._determine_starting_level(course),
                    "enrollments": [],
                    "terms": set(),
                }

            # Add enrollment to current period
            current_period["enrollments"].append(enrollment)
            current_period["terms"].add(term)
            current_period["last_term"] = term

        # Finalize last period (no finishing level - still active)
        if current_period:
            current_period["end_date"] = None
            current_period["finishing_level"] = None
            periods.append(current_period)

        return periods

    def _get_program_from_course(self, course):
        """Determine program and major from course using ONLY existing majors."""
        course_code = course.code.upper()

        # Language courses - use actual existing language major names
        if any(lang in course_code for lang in ["IEAP"]):
            return {
                "program": "Language Program",
                "major": "Intensive English for Academic Purposes",  # ID: 7
            }
        elif any(lang in course_code for lang in ["EHSS"]):
            return {
                "program": "Language Program",
                "major": "English for HIgh School Students",  # ID: 8
            }
        elif any(lang in course_code for lang in ["GESL", "ESL"]):
            return {
                "program": "Language Program",
                "major": "General English as a Second Language",  # ID: 9
            }
        elif any(lang in course_code for lang in ["EXPRESS"]):
            return {
                "program": "Language Program",
                "major": "Express (Weekend)",  # ID: 10
            }
        elif any(lang in course_code for lang in ["IELTS"]):
            return {
                "program": "Language Program",
                "major": "IELTS",  # ID: 11
            }

        # Academic courses - use actual existing academic major names
        elif any(biz in course_code for biz in ["BUS", "MGT", "ACC", "MBA"]):
            return {
                "program": "Bachelor Program",
                "major": "Business Administration",  # ID: 1
            }
        elif any(fin in course_code for fin in ["FIN"]):
            return {
                "program": "Bachelor Program",
                "major": "Finance and Banking",  # ID: 4
            }
        elif any(tesol in course_code for tesol in ["TESOL", "ELT"]):
            return {
                "program": "Bachelor Program",
                "major": "Teaching of English as a Second Language",  # ID: 5
            }
        elif any(tour in course_code for tour in ["TOUR", "HOSP"]):
            return {
                "program": "Bachelor Program",
                "major": "Tourism & Hospitality",  # ID: 3
            }

        # International Relations/Political Science courses
        elif any(ir in course_code for ir in ["IR", "POL", "ECON", "LAW", "HIST", "PHIL"]):
            return {
                "program": "Bachelor Program",
                "major": "International Relations",  # ID: 6 - This is correct for student 10774!
            }

        # Default to Business Administration for unrecognized courses
        else:
            return {
                "program": "Bachelor Program",
                "major": "Business Administration",  # ID: 1 - Most common
            }

    def _determine_starting_level(self, first_course):
        """Determine starting level from first course in program."""
        course_code = first_course.code.upper()

        # Extract level from course code (e.g., IEAP-01, BUS-101)
        if "-" in course_code:
            level_part = course_code.split("-")[-1]
            if level_part.isdigit():
                level_num = int(level_part)
                if level_num <= 6:
                    return f"Level {level_num}"
                elif level_num >= 100:
                    return f"Year {(level_num // 100)}"

        return "Level 1"  # Default

    def _determine_finishing_level(self, enrollments):
        """Determine finishing level from last courses in program."""
        if not enrollments:
            return None

        # Get the highest level course completed
        highest_level = 0
        for enrollment in enrollments:
            course_code = enrollment.class_header.course.code.upper()
            if "-" in course_code:
                level_part = course_code.split("-")[-1]
                if level_part.isdigit():
                    level_num = int(level_part)
                    highest_level = max(highest_level, level_num)

        if highest_level <= 6:
            return f"Level {highest_level}"
        elif highest_level >= 100:
            return f"Year {(highest_level // 100)}"

        return "Completed"

    def _get_previous_term_end(self, current_term):
        """Get end date of term before current term."""
        try:
            prev_term = Term.objects.filter(start_date__lt=current_term.start_date).order_by("-start_date").first()

            return prev_term.end_date if prev_term else current_term.start_date
        except Exception:
            return current_term.start_date

    def _is_currently_active(self, last_term):
        """Determine if student should be marked active based on last term."""
        if not last_term:
            return False

        today = timezone.now().date()

        # Active if last term is currently running
        return last_term.start_date <= today <= last_term.end_date

    def _create_program_enrollment(self, student, period):
        """Create actual ProgramEnrollment record."""
        # Determine status
        is_active = self._is_currently_active(period["last_term"])
        status = (
            ProgramEnrollment.EnrollmentStatus.ACTIVE if is_active else ProgramEnrollment.EnrollmentStatus.INACTIVE
        )

        # Determine enrollment type based on program
        if period["program"] == "Language Program":
            enrollment_type = ProgramEnrollment.EnrollmentType.LANGUAGE
        else:
            enrollment_type = ProgramEnrollment.EnrollmentType.ACADEMIC

        # Get existing Major (should never create new ones!)
        try:
            major = Major.objects.get(name=period["major"])
        except Major.DoesNotExist:
            self.stdout.write(f"    ❌ ERROR: Major '{period['major']}' does not exist in database!")
            self.stdout.write(f"    Available majors: {list(Major.objects.values_list('name', flat=True))}")
            return  # Skip this enrollment

        # Check for existing record to avoid duplicates
        existing = ProgramEnrollment.objects.filter(
            student=student,
            program=major,
            start_date=period["start_date"],
        ).first()

        if not existing:
            ProgramEnrollment.objects.create(
                student=student,
                program=major,  # Using Major as program for now
                enrollment_type=enrollment_type,
                status=status,
                start_date=period["start_date"],
                end_date=period["end_date"],
                start_term=period["last_term"],  # Will fix this logic
                notes=(
                    f"Generated from academiccoursetakers data. "
                    f"Start: {period['start_level']}, Finish: {period['finishing_level'] or 'Ongoing'}"
                ),
            )
        else:
            self.stdout.write(f"    Skipping duplicate: {major.name} starting {period['start_date']}")

    def _preview_program_enrollment(self, student, period):
        """Preview what would be created in dry-run mode."""
        is_active = self._is_currently_active(period["last_term"])
        status = "ACTIVE" if is_active else "INACTIVE"

        self.stdout.write(
            (
                f"  📋 Would create: {student.student_id} | {period['program']} - {period['major']} | "
                f"{period['start_date']} to {period['end_date'] or 'ongoing'} | "
                f"{period['start_level']} → {period['finishing_level'] or 'ongoing'} | {status}"
            ),
        )
