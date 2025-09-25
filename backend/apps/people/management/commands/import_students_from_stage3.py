"""
Production Student Loader from Data Pipeline Stage3

Loads students from the data pipeline's students_stage3_cleaned table into Django models.
Uses BaseMigrationCommand for comprehensive audit trails and error handling.

CRITICAL BUSINESS RULES:
- Load ALL students (no filtering by year - "waste of time")
- Use integer student IDs that match enrollment data
- Create proper Person and StudentProfile records
- Comprehensive audit trails for all operations
"""

import logging
from datetime import datetime
from decimal import Decimal

from django.core.management.base import CommandError
from django.db import connection, transaction

from apps.common.management.base_migration import BaseMigrationCommand
from apps.people.models import Person, StudentProfile

logger = logging.getLogger(__name__)


class Command(BaseMigrationCommand):
    """Production loader for students from data pipeline stage3"""

    help = "Load students from students_stage3_cleaned into Django models"

    def get_rejection_categories(self):
        return [
            "missing_student_id",
            "invalid_student_id",
            "duplicate_student_id",
            "missing_required_data",
            "person_creation_failed",
            "student_profile_creation_failed"
        ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be loaded without making changes"
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=500,
            help="Batch size for processing (default: 500)"
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of students to process (for testing)"
        )

    def execute_migration(self, *args, **options):
        self.dry_run = options.get("dry_run", False)
        self.batch_size = options.get("batch_size", 500)
        self.limit = options.get("limit")

        self.stdout.write("🚀 PRODUCTION Student Loader from Stage3 Data")
        self.stdout.write(f"   Dry run: {self.dry_run}")

        if self.dry_run:
            self.stdout.write("   ⚠️  DRY RUN MODE - No changes will be made")

        # Check if stage3 data exists
        if not self.verify_stage3_data():
            raise CommandError("students_stage3_cleaned table not found - run pipeline first")

        # Record input statistics
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM students_stage3_cleaned")
            total_students = cursor.fetchone()[0]

        self.record_input_stats(
            total_records=total_students,
            source_file="students_stage3_cleaned (data pipeline stage3)"
        )

        self.stdout.write(f"📊 Processing {total_students:,} students from pipeline stage3")

        # Process students in batches
        self.process_students()

        # Generate final report
        self.generate_final_report()

    def verify_stage3_data(self):
        """Verify that students_stage3_cleaned table exists and has data"""
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_name = 'students_stage3_cleaned'
            """)
            return cursor.fetchone()[0] > 0

    def process_students(self):
        """Process students in batches from stage3 data"""

        with connection.cursor() as cursor:
            # Get students with required data
            query = """
                SELECT
                    student_id,
                    name_english,
                    name_khmer,
                    email_personal,
                    mobile_phone,
                    birth_date,
                    gender,
                    nationality
                FROM students_stage3_cleaned
                WHERE student_id IS NOT NULL
                AND student_id != ''
                ORDER BY student_id
            """

            if self.limit:
                query += f" LIMIT {self.limit}"

            cursor.execute(query)

            batch = []
            for row in cursor.fetchall():
                batch.append(row)

                if len(batch) >= self.batch_size:
                    self.process_student_batch(batch)
                    batch = []

            # Process remaining batch
            if batch:
                self.process_student_batch(batch)

    def process_student_batch(self, batch):
        """Process a batch of student records"""

        for record in batch:
            (student_id, name_english, name_khmer, email_personal,
             mobile_phone, birth_date, gender, nationality) = record

            try:
                self.process_single_student(
                    student_id, name_english, name_khmer, email_personal,
                    mobile_phone, birth_date, gender, nationality
                )

            except Exception as e:
                self.record_rejection(
                    category="student_profile_creation_failed",
                    record_id=student_id,
                    reason=f"Failed to process student: {str(e)}"
                )
                logger.error("Failed to process student %s: %s", student_id, e)

    def process_single_student(self, student_id, name_english, name_khmer,
                              email_personal, mobile_phone, birth_date,
                              gender, nationality):
        """Process a single student record"""

        # Validate student_id
        if not student_id or not str(student_id).strip():
            self.record_rejection(
                category="missing_student_id",
                record_id="unknown",
                reason="Empty or null student_id"
            )
            return

        try:
            student_id_int = int(student_id)
        except (ValueError, TypeError):
            self.record_rejection(
                category="invalid_student_id",
                record_id=student_id,
                reason=f"Cannot convert student_id to integer: {student_id}"
            )
            return

        # Check for duplicate
        if not self.dry_run and StudentProfile.objects.filter(student_id=student_id_int).exists():
            self.record_rejection(
                category="duplicate_student_id",
                record_id=student_id,
                reason=f"Student {student_id} already exists"
            )
            return

        # Parse name
        first_name, last_name = self.parse_name(name_english)

        # Create Person and StudentProfile
        if not self.dry_run:
            with transaction.atomic():
                person = self.create_person_record(
                    first_name, last_name, name_khmer, email_personal,
                    mobile_phone, birth_date, gender, nationality, student_id
                )

                student = self.create_student_profile(student_id_int, person)

        self.record_success("student_created", 1)

    def parse_name(self, name_english):
        """Parse English name into first and last name"""
        if not name_english or not name_english.strip():
            return "Unknown", "Unknown"

        name_english = name_english.strip()

        # Handle "Last, First" format
        if ',' in name_english:
            parts = name_english.split(',', 1)
            last_name = parts[0].strip()
            first_name = parts[1].strip() if len(parts) > 1 else "Unknown"
        # Handle "First Last" format
        elif ' ' in name_english:
            parts = name_english.split(' ', 1)
            first_name = parts[0].strip()
            last_name = parts[1].strip() if len(parts) > 1 else "Unknown"
        # Single name - use as first name
        else:
            first_name = name_english
            last_name = "Unknown"

        return first_name, last_name

    def parse_birth_date(self, birth_date_str):
        """Parse various birth date formats to Django-compatible format"""
        if not birth_date_str or not str(birth_date_str).strip():
            return None

        birth_date_str = str(birth_date_str).strip()

        # Handle single character values (probably gender mixed in birth_date column)
        if len(birth_date_str) <= 2:
            return None

        # Check for 1900 = "not available"
        if "1900" in birth_date_str:
            return None

        try:
            # Handle "Sep  3 1990 12:00:00:000AM" format
            if "12:00:00:000AM" in birth_date_str:
                date_part = birth_date_str.split(" 12:00:00:000AM")[0]
                parsed_date = datetime.strptime(date_part, "%b %d %Y")
                return parsed_date.date()

            # Handle "Sep 3 1990" format (no time)
            elif birth_date_str.count(" ") >= 2:
                try:
                    parsed_date = datetime.strptime(birth_date_str, "%b %d %Y")
                    return parsed_date.date()
                except ValueError:
                    # Try with extra spaces "Sep  3 1990"
                    parts = birth_date_str.split()
                    if len(parts) >= 3:
                        cleaned = f"{parts[0]} {parts[1]} {parts[2]}"
                        parsed_date = datetime.strptime(cleaned, "%b %d %Y")
                        return parsed_date.date()

            # Handle YYYY-MM-DD format (already correct)
            elif "-" in birth_date_str:
                parsed_date = datetime.strptime(birth_date_str, "%Y-%m-%d")
                return parsed_date.date()

        except ValueError as e:
            logger.warning("Could not parse birth date '%s': %s", birth_date_str, e)
            return None

        return None

    def generate_unique_email(self, email_personal, student_id):
        """Return actual email if valid, otherwise null (no synthetic generation)"""

        # Only use email_personal if it's a valid email format
        if email_personal and '@' in str(email_personal) and len(str(email_personal)) > 5:
            email_personal = str(email_personal).strip()
            # Check if it looks like an actual email (not phone numbers, 'Nurse', etc.)
            if not any(invalid in email_personal for invalid in [' ', '(', ')', 'Nurse', '0', '012', '017', '090']):
                # Additional check for basic email format
                if email_personal.count('@') == 1 and '.' in email_personal.split('@')[1]:
                    return email_personal

        # Return None for null email (students before 2018 or bad data)
        return None

    def create_person_record(self, first_name, last_name, name_khmer, email_personal,
                           mobile_phone, birth_date, gender, nationality, student_id):
        """Create Person record"""

        # Generate a unique email address
        school_email = self.generate_unique_email(email_personal, student_id)

        person_data = {
            'family_name': last_name[:50] if last_name else "Unknown",  # Ensure fits in field
            'personal_name': first_name[:50] if first_name else "Unknown",
        }

        # Only add school_email if we have a valid one
        if school_email:
            person_data['school_email'] = school_email

        # Add optional fields if available
        if gender:
            person_data['preferred_gender'] = gender[:1].upper() if len(gender) > 0 else None

        # Parse birth date with proper error handling
        parsed_birth_date = self.parse_birth_date(birth_date)
        if parsed_birth_date:
            person_data['date_of_birth'] = parsed_birth_date

        person = Person.objects.create(**person_data)

        self.record_success("person_created", 1)
        return person

    def create_student_profile(self, student_id_int, person):
        """Create StudentProfile record"""

        student = StudentProfile.objects.create(
            student_id=student_id_int,
            person=person
        )

        self.record_success("student_profile_created", 1)
        return student

    def generate_final_report(self):
        """Generate final migration report"""

        self.stdout.write("\n" + "="*60)
        self.stdout.write("🎯 PRODUCTION STUDENT LOADER RESULTS")
        self.stdout.write("="*60)

        # Get current statistics
        stats = {}
        try:
            # Count successful operations
            created_students = StudentProfile.objects.count()
            created_persons = Person.objects.count()

            self.stdout.write(f"📊 Processing Statistics:")
            self.stdout.write(f"   Students created: {stats.get('student_created', 0):,}")
            self.stdout.write(f"   Persons created: {stats.get('person_created', 0):,}")
            self.stdout.write(f"   Student profiles created: {stats.get('student_profile_created', 0):,}")

            self.stdout.write(f"\n📈 Final Counts:")
            self.stdout.write(f"   Total StudentProfile records: {created_students:,}")
            self.stdout.write(f"   Total Person records: {created_persons:,}")

        except Exception as e:
            self.stdout.write(f"⚠️  Could not get final statistics: {e}")

        if not self.dry_run:
            self.stdout.write("\n✅ Students successfully loaded into Django models")
            self.stdout.write("   Ready for enrollment loading!")
        else:
            self.stdout.write("\n⚠️  DRY RUN completed - no data was modified")

        self.stdout.write("\n🔍 Next Steps:")
        self.stdout.write("   1. Run enrollment loader: python manage.py load_2025_fixed")
        self.stdout.write("   2. Validate enrollment data matches student IDs")
        self.stdout.write("   3. Generate enrollment reports for verification")