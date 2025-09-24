"""
Rebuild ClassHeader, ClassSession, ClassPart, and ClassHeaderEnrollment
from legacy_academic_classes and legacy_course_takers data.

This command:
1. Deletes existing ClassHeader, ClassSession, ClassPart data
2. Creates ClassHeader records from legacy_academic_classes
3. Creates ClassSession and ClassPart records
4. Creates ClassHeaderEnrollment records from legacy_course_takers
5. Maps Attendance=Drop to status=DROPPED
"""

import logging

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.common.management.base_migration import BaseMigrationCommand
from apps.enrollment.models import ClassHeaderEnrollment
from apps.scheduling.models import ClassHeader, ClassPart, ClassSession

logger = logging.getLogger(__name__)


class Command(BaseMigrationCommand):
    help = "Rebuild classes from legacy_academic_classes and legacy_course_takers"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--delete-existing", action="store_true", help="Delete existing class data before rebuilding"
        )
        parser.add_argument(
            "--term-filter", type=str, nargs="+", help="Only process specific terms (e.g. 2015T1E 240109E-T1AE)"
        )

    def execute_migration(self, *args, **options):
        """Execute the class rebuilding migration."""
        self.stdout.write("Starting class rebuilding migration")

        try:
            if options["delete_existing"]:
                self._delete_existing_classes()

            self._rebuild_classes_from_legacy(options.get("term_filter"))

            self.stdout.write("Successfully rebuilt classes from legacy data")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to rebuild classes: {e!s}"))
            raise

    def get_rejection_categories(self) -> list[str]:
        """Return rejection categories for this migration."""
        return [
            "missing_term_data",
            "missing_course_data",
            "student_not_found",
            "invalid_class_data",
            "enrollment_creation_error",
        ]

    def _get_system_user(self):
        """Get the system user for legacy imports."""
        User = get_user_model()
        try:
            return User.objects.get(email="no-reply@pucsr.edu.kh")
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    "System user 'no-reply@pucsr.edu.kh' not found. "
                    "Please create this superuser first for legacy imports."
                )
            )
            raise

    def _delete_existing_classes(self):
        """Delete existing class structure."""
        self.stdout.write("Deleting existing class data...")

        # Delete in dependency order
        deleted_enrollments = ClassHeaderEnrollment.objects.all().delete()[0]
        deleted_parts = ClassPart.objects.all().delete()[0]
        deleted_sessions = ClassSession.objects.all().delete()[0]
        deleted_headers = ClassHeader.objects.all().delete()[0]

        self.stdout.write(
            f"Deleted: {deleted_headers} headers, {deleted_sessions} sessions, "
            f"{deleted_parts} parts, {deleted_enrollments} enrollments"
        )

    def _rebuild_classes_from_legacy(self, term_filter=None):
        """Rebuild classes from legacy data using proper grouping."""
        from django.db import connection

        # Get system user for enrollments (cache it for efficiency)
        system_user = self._get_system_user()

        # Get grouped legacy class data
        with connection.cursor() as cursor:
            sql = """
                SELECT
                    "TermID",
                    "NormalizedCourse",
                    "NormalizedSection",
                    "NormalizedTOD",
                    ARRAY_AGG("ClassID") as class_ids,
                    ARRAY_AGG("NormalizedPart") as normalized_parts,
                    ARRAY_AGG("CourseCode") as course_codes
                FROM legacy_academic_classes
            """
            if term_filter:
                # Handle both single term and list of terms
                if isinstance(term_filter, str):
                    sql += ' WHERE "TermID" = %s'
                    params = [term_filter]
                else:
                    sql += ' WHERE "TermID" = ANY(%s)'
                    params = [term_filter]
                sql += ' GROUP BY "TermID", "NormalizedCourse", "NormalizedSection", "NormalizedTOD"'
                cursor.execute(sql, params)
            else:
                sql += ' GROUP BY "TermID", "NormalizedCourse", "NormalizedSection", "NormalizedTOD"'
                cursor.execute(sql)

            class_groups = cursor.fetchall()

        self.stdout.write(f"Found {len(class_groups)} class groups to process")
        total_class_ids = sum(len(group[4]) for group in class_groups)
        self.record_input_stats(class_groups_count=len(class_groups), total_class_ids=total_class_ids)

        created_headers = 0
        created_sessions = 0
        created_parts = 0

        for group_data in class_groups:
            term_id, norm_course, norm_section, norm_tod, class_ids, normalized_parts, course_codes = group_data

            # Validate prerequisites outside transaction
            if created_headers == 0:  # Log first example
                self.stdout.write(
                    f"Processing group - Term: '{term_id}', Course: '{norm_course}', "
                    f"Section: '{norm_section}', TOD: '{norm_tod}'"
                )
                self.stdout.write(f"  ClassIDs in group: {len(class_ids)}")

            # Look up existing term
            from apps.curriculum.models import Term

            try:
                term = Term.objects.get(code=term_id)
            except Term.DoesNotExist:
                self.record_rejection("missing_term_data", f"{term_id}-{norm_course}", f"Term {term_id} not found")
                continue

            # Look up existing course using normalized course code
            from apps.curriculum.models import Course

            try:
                course = Course.objects.get(code=norm_course)
            except Course.DoesNotExist:
                self.record_rejection(
                    "missing_course_data", f"{term_id}-{norm_course}", f"Course {norm_course} not found"
                )
                continue

            # Create section_id
            section_id = norm_section if norm_section and norm_section.upper() != "NULL" else "A"

            # Now process the group creation within atomic transaction
            try:
                with transaction.atomic():  # Individual transaction per group
                    # Create ClassHeader for this group
                    class_header = ClassHeader.objects.create(
                        course=course,
                        term=term,
                        section_id=section_id,
                        time_of_day=self._map_tod_to_time_of_day(norm_tod),
                        notes=f"Legacy import: {len(class_ids)} parts",
                    )
                    created_headers += 1

                    # Determine session structure based on course type
                    is_ieap = norm_course.startswith("IEAP")
                    sessions_created = self._create_sessions_for_class(class_header, is_ieap)
                    created_sessions += sessions_created

                    # Create ClassParts for each ClassID in this group (use CourseCode for actual part names)
                    parts_created = self._create_parts_for_group(class_header, class_ids, course_codes, is_ieap)
                    created_parts += parts_created

                # Create enrollments outside the atomic block (separate transaction handling)
                self._create_enrollments_for_group(class_header, class_ids, system_user)

            except Exception as e:
                group_id = f"{term_id}-{norm_course}-{norm_section}-{norm_tod}"
                self.record_rejection("invalid_class_data", group_id, f"Failed to create class group: {e!s}")
                continue

        self.stdout.write(f"Created: {created_headers} headers, {created_sessions} sessions, {created_parts} parts")
        self.record_success("class_headers", created_headers)
        self.record_success("class_sessions", created_sessions)
        self.record_success("class_parts", created_parts)

    def _map_legacy_attendance_to_status(self, attendance, passed):
        """Map legacy attendance values to enrollment status."""
        if attendance:
            attendance_lower = attendance.lower()
            if attendance_lower in ["drop", "dropped", "leave", "quit"]:
                return "DROPPED"

        # Default status for normal enrollment
        return "ENROLLED"

    def _map_tod_to_time_of_day(self, tod):
        """Map legacy time of day values to ClassHeader choices."""
        if not tod:
            return "MORN"

        tod_upper = tod.upper()
        mapping = {
            "M": "MORN",
            "MORN": "MORN",
            "MORNING": "MORN",
            "A": "AFT",
            "AFT": "AFT",
            "AFTERNOON": "AFT",
            "E": "EVE",
            "EVE": "EVE",
            "EVENING": "EVE",
            "N": "NIGHT",
            "NIGHT": "NIGHT",
        }

        return mapping.get(tod_upper, "MORN")

    def _create_sessions_for_class(self, class_header, is_ieap):
        """Create appropriate sessions for a class."""
        if is_ieap:
            # IEAP classes need 2 sessions
            ClassSession.objects.create(
                class_header=class_header, session_number=1, session_name="Grammar/Communications"
            )
            ClassSession.objects.create(class_header=class_header, session_number=2, session_name="Writing")
            return 2
        else:
            # Non-IEAP classes just need 1 session
            ClassSession.objects.create(class_header=class_header, session_number=1, session_name="Main Session")
            return 1

    def _create_parts_for_group(self, class_header, class_ids, normalized_parts, is_ieap):
        """Create ClassParts for all ClassIDs in a group."""

        parts_created = 0
        session_part_counters = {}  # Track part numbers per session

        for i, (class_id, norm_part) in enumerate(zip(class_ids, normalized_parts, strict=False)):
            # Determine which session this part belongs to
            session_number = self._assign_part_to_session(class_id, is_ieap)

            # Get the appropriate session
            sessions = class_header.class_sessions.all().order_by("id")
            if is_ieap and len(sessions) >= 2:
                class_session = sessions[session_number - 1]  # 1->0, 2->1
            else:
                class_session = sessions[0]  # Single session for non-IEAP

            # Track unique part codes per session to avoid duplicates
            session_id = class_session.id
            if session_id not in session_part_counters:
                session_part_counters[session_id] = 0
            session_part_counters[session_id] += 1

            # Map normalized part to proper ClassPartType
            part_type, _ = self._map_normalized_part_to_type(norm_part)

            # Truncate name if too long for database field (max 50 chars)
            part_name = norm_part or f"Part {i + 1}"
            if len(part_name) > 50:
                part_name = part_name[:47] + "..."

            # Create ClassPart with proper type mapping
            ClassPart.objects.create(
                class_session=class_session,
                name=part_name,  # Keep original NormalizedPart as name (truncated if needed)
                class_part_type=part_type,
                class_part_code=session_part_counters[session_id],  # Unique within session
                meeting_days="MON,WED,FRI",  # Default
                legacy_class_id=class_id,
            )
            parts_created += 1

        return parts_created

    def _assign_part_to_session(self, class_id, is_ieap):
        """Assign a part to session 1 or 2 based on ClassID content."""
        if not is_ieap:
            return 1  # Non-IEAP always use session 1

        if class_id:
            class_id_upper = class_id.upper()
            # Session 2 (Writing) indicators - check the ClassID suffix
            if any(w in class_id_upper for w in ["-WR", "WRIT", "WRITING"]):
                return 2
            # Session 1 (Grammar/Communications) indicators
            if any(g in class_id_upper for g in ["COM", "INTER", "GRAM"]):
                return 1

        # Default to session 1 if unclear
        return 1

    def _create_enrollments_for_group(self, class_header, class_ids, system_user):
        """Create enrollments for all ClassIDs in a group, deduplicating students."""
        from django.db import connection

        # Get all unique students across all ClassIDs in this group
        with connection.cursor() as cursor:
            # Use DISTINCT to get unique students across all class parts
            cursor.execute(
                """
                SELECT DISTINCT lct."ID", lct."Attendance", lct."Grade", lct."Passed", lct."Credit"
                FROM legacy_course_takers lct
                WHERE lct."ClassID" = ANY(%s)
                ORDER BY lct."ID"
                """,
                [class_ids],
            )

            unique_enrollments = cursor.fetchall()

        total_created = 0

        for enrollment_data in unique_enrollments:
            student_id, attendance, grade, passed, credit = enrollment_data

            try:
                # Use StudentLookupService to find student by legacy ID
                from apps.people.services import StudentLookupService

                student = StudentLookupService.find_by_legacy_id(str(student_id))
                if not student:
                    self.record_rejection("student_not_found", str(student_id), f"Student {student_id} not found")
                    continue

                # Map attendance to enrollment status manually since service doesn't exist
                status = self._map_legacy_attendance_to_status(
                    attendance=attendance.strip() if attendance else None, passed=passed.strip() if passed else None
                )

                # Create enrollment with get_or_create to prevent duplicates
                from apps.enrollment.models import ClassHeaderEnrollment

                enrollment, created = ClassHeaderEnrollment.objects.get_or_create(
                    student=student,
                    class_header=class_header,
                    defaults={
                        "enrolled_by": system_user,
                        "enrollment_date": class_header.term.start_date,
                        "status": status,
                        "final_grade": grade.strip() if grade else None,
                        "notes": f"Legacy import: attendance={attendance}, credit={credit}",
                    },
                )

                if created:
                    total_created += 1

            except Exception as e:
                self.record_rejection(
                    "enrollment_creation_error",
                    str(student_id),
                    f"Failed to create enrollment in class {class_header.course.code}: {e!s}",
                )
                continue

        if total_created > 0:
            self.stdout.write(f"Created {total_created} enrollments for class {class_header.course.code}")
            self.record_success("enrollments", total_created)

        return total_created

    def _map_normalized_part_to_type(self, course_code):
        """Map CourseCode to proper ClassPartType based on the actual course content."""
        from apps.scheduling.class_part_types import ClassPartType

        if not course_code:
            return ClassPartType.MAIN, 1

        course_code_upper = course_code.upper().strip()

        # Map CourseCode values to ClassPartType based on subject matter
        COURSE_CODE_MAPPING = {
            # Ventures series - Conversation practice
            "V-1A": (ClassPartType.VENTURES, 1),
            "V-1B": (ClassPartType.VENTURES, 1),
            "V-2A": (ClassPartType.VENTURES, 1),
            "V-2B": (ClassPartType.VENTURES, 1),
            "V-3A": (ClassPartType.VENTURES, 1),
            "V-3B": (ClassPartType.VENTURES, 1),
            "V-4A": (ClassPartType.VENTURES, 1),
            "V-4B": (ClassPartType.VENTURES, 1),
            "VT-1": (ClassPartType.VENTURES, 1),  # Ventures Transitions
            # Reading Explorer series - Reading skills
            "RE-01": (ClassPartType.READING, 1),
            "RE-02A": (ClassPartType.READING, 1),
            "RE-02B": (ClassPartType.READING, 1),
            "RE-03A": (ClassPartType.READING, 1),
            "RE-03B": (ClassPartType.READING, 1),
            "RE-04A": (ClassPartType.READING, 1),
            "RE-04B": (ClassPartType.READING, 1),
            "RE-FOUND": (ClassPartType.READING, 1),
            # Computer skills
            "HCOMP-7": (ClassPartType.COMPUTER, 1),
            "HCOMP-8": (ClassPartType.COMPUTER, 1),
            "HCOMP-9": (ClassPartType.COMPUTER, 1),
            "FCOMP-1": (ClassPartType.COMPUTER, 1),
            # Writing courses
            "GREAT-2": (ClassPartType.WRITING, 1),
            "GREAT-3": (ClassPartType.WRITING, 1),
            "GREAT-4": (ClassPartType.WRITING, 1),
            "GREAT-FOUND": (ClassPartType.WRITING, 1),
            "EW-1": (ClassPartType.WRITING, 1),  # Effective Academic Writing
            "EW-3": (ClassPartType.WRITING, 1),
            "LONGMAN-1&SR-ELEM": (ClassPartType.WRITING, 1),
            "LONGMAN-2&SR-PRE": (ClassPartType.WRITING, 1),
            "LONGMAN-3&SR-INT": (ClassPartType.WRITING, 1),
            "LONGMAN-4&SR-UPINT": (ClassPartType.WRITING, 1),
            # Grammar/Conversation - IEAP Interchange series
            "INTER-1": (ClassPartType.GRAMMAR, 1),
            "INTER-2": (ClassPartType.GRAMMAR, 1),
            "INTER-3": (ClassPartType.GRAMMAR, 1),
            "INTER-BEG": (ClassPartType.GRAMMAR, 1),
            # Speaking/Conversation - Passages series
            "PASS-04": (ClassPartType.GRAMMAR, 1),
            # Project series - project-based learning
            "PRO-1A": (ClassPartType.PROJECT, 1),
            "PRO-1B": (ClassPartType.PROJECT, 1),
            "PRO-2A": (ClassPartType.PROJECT, 1),
            "PRO-2B": (ClassPartType.PROJECT, 1),
            "PRO-3A": (ClassPartType.PROJECT, 1),
            # English in Common - conversation
            "EC-1A": (ClassPartType.CONVERSATION, 1),
            "EC-1B": (ClassPartType.CONVERSATION, 1),
            "EC-2A": (ClassPartType.CONVERSATION, 1),
            "EC-2B": (ClassPartType.CONVERSATION, 1),
            "EC-3A": (ClassPartType.CONVERSATION, 1),
            "EC-3B": (ClassPartType.CONVERSATION, 1),
            "EC-4A": (ClassPartType.CONVERSATION, 1),
            "EC-5A": (ClassPartType.CONVERSATION, 1),
            "EC-6A": (ClassPartType.CONVERSATION, 1),
            # Four Corners - conversation
            "FC-1A": (ClassPartType.CONVERSATION, 1),
            "FC-1B": (ClassPartType.CONVERSATION, 1),
            "FC-2A": (ClassPartType.CONVERSATION, 1),
            "FC-2B": (ClassPartType.CONVERSATION, 1),
            "FC-3A": (ClassPartType.CONVERSATION, 1),
            "FC-3B": (ClassPartType.CONVERSATION, 1),
            "FC-4A": (ClassPartType.CONVERSATION, 1),
            # Blueprint series - business English
            "BP-2": (ClassPartType.MAIN, 1),
            "BP-3": (ClassPartType.MAIN, 1),
            "BP-4": (ClassPartType.MAIN, 1),
        }

        # Return mapped values or default to MAIN
        return COURSE_CODE_MAPPING.get(course_code_upper, (ClassPartType.MAIN, 1))
