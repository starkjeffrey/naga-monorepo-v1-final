"""
PRODUCTION LOADER: 2025 Academic Course Takers

Based on proven patterns from successful loaders:
- Explosion-tolerant with iterative fixes
- Pydantic validation for data quality
- Batch processing with comprehensive error handling
- Creates full class hierarchy: ClassHeader -> ClassSession -> ClassPart -> Enrollment
- Audit trail with BaseMigrationCommand
"""

import csv
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import CommandError
from django.db import transaction
from pydantic import BaseModel, Field, field_validator

from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Course, Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.people.models import StudentProfile
from apps.scheduling.class_part_types import ClassPartType
from apps.scheduling.models import ClassHeader, ClassPart, ClassSession


class Course2025Taker(BaseModel):
    """Production Pydantic model for 2025 academic course takers"""

    # Core identifiers
    student_id: str = Field(..., min_length=1, max_length=10)
    class_id: str = Field(..., min_length=5, max_length=255)
    ipk: str = Field(..., description="Legacy primary key")

    # Academic data
    credit: int | None = Field(None, ge=0, le=20)
    grade_point: float | None = Field(None, ge=0, le=4.5)
    total_point: float | None = Field(None, ge=0)
    grade: str | None = Field(None, max_length=10)
    passed: bool | None = None

    # Registration info
    attendance: str | None = Field(None, max_length=20)
    remarks: str | None = Field(None, max_length=100)

    # Timestamps
    add_time: str | None = None
    last_update: str | None = None
    created_date: str | None = None
    modified_date: str | None = None

    @field_validator("student_id")
    @classmethod
    def validate_student_id(cls, v):
        if not v or not v.strip():
            raise ValueError("student_id required")
        return v.strip()

    @field_validator("class_id")
    @classmethod
    def validate_class_id(cls, v):
        if not v or not v.strip():
            raise ValueError("class_id required")
        # Validate 2025 format: 250xxx-xxx!$...
        if not v.startswith("25"):
            raise ValueError(f"Expected 2025 class_id, got: {v[:10]}")
        return v.strip()

    @field_validator("grade")
    @classmethod
    def validate_grade(cls, v):
        if not v:
            return None
        v = v.strip().upper()
        valid_grades = {
            "A+",
            "A",
            "A-",
            "B+",
            "B",
            "B-",
            "C+",
            "C",
            "C-",
            "D+",
            "D",
            "D-",
            "F",
            "W",
            "I",
            "IP",
            "P",
            "NP",
        }
        if v not in valid_grades:
            raise ValueError(f"Invalid grade: {v}")
        return v

    @field_validator("attendance")
    @classmethod
    def validate_attendance(cls, v):
        if not v:
            return None
        v = v.strip().title()
        if v not in ["Normal", "Leave", "Drop", "Audit"]:
            raise ValueError(f"Invalid attendance: {v}")
        return v

    class Config:
        str_strip_whitespace = True


class Command(BaseMigrationCommand):
    """Production loader for 2025 academic course takers"""

    help = "Load 2025 academiccoursetakers into production Django models"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {
            "total_processed": 0,
            "successful_validations": 0,
            "class_headers_created": 0,
            "class_sessions_created": 0,
            "class_parts_created": 0,
            "enrollments_created": 0,
            "enrollments_updated": 0,
            "validation_errors": 0,
            "missing_students": 0,
            "missing_courses": 0,
            "missing_terms": 0,
        }

        # Caches
        self.student_cache = {}
        self.course_cache = {}
        self.term_cache = {}
        self.class_header_cache = {}

        # Missing data tracking
        self.missing_students = set()
        self.missing_courses = set()
        self.missing_terms = set()

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="/Volumes/Projects/naga-monorepo-v1-final/backend/data/legacy/data_pipeline/inputs/academiccoursetakers_2025_subset.csv",
            help="Path to 2025 academiccoursetakers CSV",
        )
        parser.add_argument("--dry-run", action="store_true", help="Validate without loading")
        parser.add_argument("--batch-size", type=int, default=500, help="Batch size")
        parser.add_argument("--limit", type=int, help="Limit records for testing")

    def get_rejection_categories(self):
        return [
            "validation_error",
            "missing_student",
            "missing_course",
            "missing_term",
            "duplicate_enrollment",
            "processing_error",
        ]

    def execute_migration(self, *args, **options):
        file_path = Path(options["file"])
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        limit = options.get("limit")

        self.stdout.write(self.style.SUCCESS("🚀 PRODUCTION LOADER: 2025 Academic Course Takers"))
        self.stdout.write(f"📂 File: {file_path}")
        self.stdout.write(f"📦 Batch size: {batch_size:,}")

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN - No database changes"))

        if limit:
            self.stdout.write(f"📊 Processing limit: {limit:,} records")

        if not file_path.exists():
            raise CommandError(f"File not found: {file_path}")

        # Count records for audit
        with file_path.open() as f:
            total_csv_records = sum(1 for _ in csv.DictReader(f))

        self.record_input_stats(
            csv_file=str(file_path),
            total_csv_records=total_csv_records,
            limit_applied=limit or "none",
            batch_size=batch_size,
        )

        # Load caches
        self.load_reference_caches()

        # Process the data
        self.process_csv_file(file_path, dry_run, batch_size, limit)

        # Record final stats
        for stat_name, count in self.stats.items():
            if count > 0:
                self.record_success(stat_name, count)

        # Generate report
        self.generate_production_report(dry_run)

    def load_reference_caches(self):
        """Load students, courses, terms into memory"""
        self.stdout.write("🏗️ Loading reference data...")

        # Load students with proper ID formatting
        for student in StudentProfile.objects.select_related("person").only("student_id", "person"):
            # Store with various ID formats for flexibility
            student_key = str(student.student_id).zfill(5)
            self.student_cache[student_key] = student
            self.student_cache[str(student.student_id)] = student

        # Load courses
        for course in Course.objects.only("code", "credits", "title"):
            self.course_cache[course.code] = course

        # Load terms
        for term in Term.objects.only("code", "start_date", "end_date"):
            self.term_cache[term.code] = term

        # Get system user
        User = get_user_model()
        self.system_user = User.objects.first()
        if not self.system_user:
            raise CommandError("No users found - create a user first")

        self.stdout.write(
            f"   📋 Loaded: {len(self.student_cache):,} students, {len(self.course_cache):,} courses, {len(self.term_cache):,} terms"
        )

    def process_csv_file(self, file_path, dry_run, batch_size, limit):
        """Process CSV file in batches"""

        with file_path.open() as f:
            reader = csv.DictReader(f)
            batch = []

            for row_num, row in enumerate(reader, 1):
                if limit and row_num > limit:
                    break

                batch.append((row_num, row))
                self.stats["total_processed"] += 1

                if len(batch) >= batch_size:
                    self.process_batch(batch, dry_run)
                    batch = []

                    if row_num % 5000 == 0:
                        self.stdout.write(f"📋 Processed {row_num:,} records...")

            # Process remaining batch
            if batch:
                self.process_batch(batch, dry_run)

    def process_batch(self, batch, dry_run):
        """Process a batch with transaction safety"""

        if not dry_run:
            with transaction.atomic():
                for row_num, row in batch:
                    self.process_single_record(row_num, row, dry_run)
        else:
            for row_num, row in batch:
                self.process_single_record(row_num, row, dry_run)

    def process_single_record(self, row_num, row, dry_run):
        """Process single enrollment record"""

        try:
            # Validate with Pydantic
            course_taker_data = {
                "student_id": row.get("ID", "").strip(),
                "class_id": row.get("ClassID", "").strip(),
                "ipk": row.get("IPK", "").strip(),
                "credit": self.parse_int(row.get("Credit")),
                "grade_point": self.parse_float(row.get("GradePoint")),
                "total_point": self.parse_float(row.get("TotalPoint")),
                "grade": row.get("Grade", "").strip() or None,
                "passed": self.parse_bool(row.get("Passed")),
                "attendance": row.get("Attendance", "").strip() or None,
                "remarks": row.get("Remarks", "").strip() or None,
                "add_time": row.get("AddTime", "").strip() or None,
                "last_update": row.get("LastUpdate", "").strip() or None,
                "created_date": row.get("CreatedDate", "").strip() or None,
                "modified_date": row.get("ModifiedDate", "").strip() or None,
            }

            course_taker = Course2025Taker(**course_taker_data)
            self.stats["successful_validations"] += 1

            # Parse class structure from ClassID
            class_info = self.parse_class_id(course_taker.class_id)

            # Validate dependencies exist
            missing_deps = []
            if course_taker.student_id not in self.student_cache:
                self.missing_students.add(course_taker.student_id)
                self.stats["missing_students"] += 1
                missing_deps.append("student")

            if class_info["course_code"] not in self.course_cache:
                self.missing_courses.add(class_info["course_code"])
                self.stats["missing_courses"] += 1
                missing_deps.append("course")

            if class_info["term_code"] not in self.term_cache:
                self.missing_terms.add(class_info["term_code"])
                self.stats["missing_terms"] += 1
                missing_deps.append("term")

            # Record rejections for missing dependencies
            if missing_deps:
                for dep in missing_deps:
                    self.record_rejection(
                        category=f"missing_{dep}",
                        record_id=f"Row{row_num}_{course_taker.student_id}_{course_taker.class_id}",
                        reason=f"Missing {dep}: {class_info.get(f'{dep}_code', 'N/A')}",
                        raw_data=dict(row),
                    )
                return

            # Create class structure and enrollment (if not dry run)
            if not dry_run:
                self.create_class_structure_and_enrollment(course_taker, class_info)

        except Exception as e:
            self.stats["validation_errors"] += 1
            self.record_rejection(
                category="validation_error" if "validation" in str(e).lower() else "processing_error",
                record_id=f"Row{row_num}_{row.get('ID', 'N/A')}",
                reason=str(e),
                raw_data=dict(row),
            )

            if self.stats["validation_errors"] <= 10:
                self.stdout.write(self.style.ERROR(f"   ❌ Row {row_num}: {e}"))

    def parse_class_id(self, class_id):
        """Parse ClassID into components"""
        # Format: 250106E-T1AE!$632!$E!$GESL-2!$FC-1B
        parts = class_id.split("!$")

        term_part = parts[0] if parts else ""
        term_code = term_part[:6] if len(term_part) >= 6 else term_part

        # Extract course from the last meaningful part
        course_code = "UNKNOWN"
        if len(parts) >= 4:
            # Try to extract course from parts[3] (e.g., "GESL-2")
            course_part = parts[3]
            if "-" in course_part:
                course_code = course_part
            else:
                course_code = course_part[:10]  # Fallback

        return {
            "term_code": term_code,
            "course_code": course_code,
            "section_id": parts[1] if len(parts) > 1 else "A",
            "time_of_day": parts[2] if len(parts) > 2 else "M",
            "class_part": parts[4] if len(parts) > 4 else "Main",
        }

    def create_class_structure_and_enrollment(self, course_taker, class_info):
        """Create ClassHeader -> ClassSession -> ClassPart -> Enrollment"""

        # Get references
        student = self.student_cache[course_taker.student_id]
        course = self.course_cache[class_info["course_code"]]
        term = self.term_cache[class_info["term_code"]]

        # Create or get ClassHeader
        class_header = self.get_or_create_class_header(course_taker.class_id, course, term, class_info)

        # Create or get ClassSession
        class_session = self.get_or_create_class_session(class_header, class_info["class_part"])

        # Create or get ClassPart
        self.get_or_create_class_part(class_session, class_info["class_part"])

        # Create or update enrollment
        self.create_or_update_enrollment(student, class_header, course_taker)

    def get_or_create_class_header(self, class_id, course, term, class_info):
        """Get or create ClassHeader using full ClassID as unique key"""

        if class_id in self.class_header_cache:
            return self.class_header_cache[class_id]

        # Map time of day
        time_mapping = {
            "M": ClassHeader.TimeOfDay.MORNING,
            "A": ClassHeader.TimeOfDay.AFTERNOON,
            "E": ClassHeader.TimeOfDay.EVENING,
            "N": ClassHeader.TimeOfDay.NIGHT,
        }
        time_of_day = time_mapping.get(class_info["time_of_day"], ClassHeader.TimeOfDay.MORNING)

        # Create ClassHeader
        class_header = ClassHeader.objects.create(
            course=course,
            term=term,
            section_id=class_info["section_id"][:5],  # Truncate for DB constraint
            time_of_day=time_of_day,
            status=ClassHeader.ClassStatus.ACTIVE,
            class_type=ClassHeader.ClassType.STANDARD,
        )

        self.stats["class_headers_created"] += 1
        self.class_header_cache[class_id] = class_header
        return class_header

    def get_or_create_class_session(self, class_header, part_name):
        """Create ClassSession with alphabetical logic"""

        # Determine session number (simplified logic)
        session_number = 1
        if part_name and any(word in part_name.upper() for word in ["2", "B", "WRITING", "ADV"]):
            session_number = 2

        session, created = ClassSession.objects.get_or_create(
            class_header=class_header,
            session_number=session_number,
            defaults={"session_name": f"Session {session_number}", "notes": f"Auto-created for {part_name or 'main'}"},
        )

        if created:
            self.stats["class_sessions_created"] += 1

        return session

    def get_or_create_class_part(self, class_session, part_name):
        """Create ClassPart"""

        part, created = ClassPart.objects.get_or_create(
            class_session=class_session,
            class_part_code="A",  # Use constraint field
            defaults={
                "name": part_name or "Main",
                "class_part_type": ClassPartType.MAIN,
                "meeting_days": "",
                "notes": f"Auto-created part for {part_name or 'main'}",
            },
        )

        if created:
            self.stats["class_parts_created"] += 1

        return part

    def create_or_update_enrollment(self, student, class_header, course_taker):
        """Create or update enrollment with proper status"""

        # Determine enrollment status from grade and attendance
        status = self.determine_enrollment_status(course_taker.grade, course_taker.attendance)

        # Clean grade
        clean_grade = course_taker.grade if course_taker.grade and course_taker.grade not in ["NULL", ""] else ""

        enrollment, created = ClassHeaderEnrollment.objects.get_or_create(
            student=student,
            class_header=class_header,
            defaults={
                "status": status,
                "enrollment_date": class_header.term.start_date,
                "final_grade": clean_grade,
                "enrolled_by": self.system_user,
                "notes": f"Legacy ClassID: {course_taker.class_id}. IPK: {course_taker.ipk}",
            },
        )

        if created:
            self.stats["enrollments_created"] += 1
        else:
            # Update if different
            updated = False
            if enrollment.final_grade != clean_grade:
                enrollment.final_grade = clean_grade
                updated = True
            if enrollment.status != status:
                enrollment.status = status
                updated = True
            if updated:
                enrollment.save()
                self.stats["enrollments_updated"] += 1

    def determine_enrollment_status(self, grade, attendance):
        """Determine enrollment status from grade and attendance"""

        if attendance == "Drop":
            return ClassHeaderEnrollment.EnrollmentStatus.DROPPED
        elif attendance == "Leave":
            return ClassHeaderEnrollment.EnrollmentStatus.INACTIVE
        elif not grade or grade == "IP":
            return ClassHeaderEnrollment.EnrollmentStatus.ACTIVE
        elif grade == "W":
            return ClassHeaderEnrollment.EnrollmentStatus.WITHDRAWN
        elif grade == "F":
            return ClassHeaderEnrollment.EnrollmentStatus.FAILED
        elif grade == "I":
            return ClassHeaderEnrollment.EnrollmentStatus.INCOMPLETE
        else:
            # A, B, C, D grades
            return ClassHeaderEnrollment.EnrollmentStatus.COMPLETED

    def parse_int(self, value):
        if not value or str(value).upper() in ("NULL", ""):
            return None
        try:
            return int(float(str(value)))
        except:
            return None

    def parse_float(self, value):
        if not value or str(value).upper() in ("NULL", ""):
            return None
        try:
            return float(str(value))
        except:
            return None

    def parse_bool(self, value):
        if not value or str(value).upper() in ("NULL", ""):
            return None
        return str(value).strip() in ("1", "True", "true", "Yes", "yes")

    def generate_production_report(self, dry_run):
        """Generate comprehensive production report"""

        mode = "DRY RUN" if dry_run else "PRODUCTION LOAD"

        self.stdout.write(f"\n🎯 {mode} RESULTS:")
        self.stdout.write(f"   📊 Total processed: {self.stats['total_processed']:,}")
        self.stdout.write(f"   ✅ Successful validations: {self.stats['successful_validations']:,}")
        self.stdout.write(f"   ❌ Validation errors: {self.stats['validation_errors']:,}")

        if not dry_run:
            self.stdout.write("\n🏗️ CLASS STRUCTURE CREATED:")
            self.stdout.write(f"   📚 ClassHeaders: {self.stats['class_headers_created']:,}")
            self.stdout.write(f"   🎯 ClassSessions: {self.stats['class_sessions_created']:,}")
            self.stdout.write(f"   📦 ClassParts: {self.stats['class_parts_created']:,}")

            self.stdout.write("\n👥 ENROLLMENT RESULTS:")
            self.stdout.write(f"   ➕ Created: {self.stats['enrollments_created']:,}")
            self.stdout.write(f"   📝 Updated: {self.stats['enrollments_updated']:,}")

        missing_total = self.stats["missing_students"] + self.stats["missing_courses"] + self.stats["missing_terms"]
        if missing_total > 0:
            self.stdout.write(f"\n⚠️ MISSING DEPENDENCIES: {missing_total:,}")
            self.stdout.write(f"   👤 Students: {self.stats['missing_students']:,}")
            self.stdout.write(f"   📚 Courses: {self.stats['missing_courses']:,}")
            self.stdout.write(f"   📅 Terms: {self.stats['missing_terms']:,}")

        if self.stats["validation_errors"] == 0:
            self.stdout.write(self.style.SUCCESS(f"\n🎉 {mode} COMPLETED SUCCESSFULLY!"))
        else:
            self.stdout.write(self.style.WARNING(f"\n⚠️ {mode} completed with validation issues"))
