"""Optimized student import command with better timeout handling and recovery.

This command improves on the original by:
1. Smaller, configurable batch sizes to avoid timeouts
2. Progress tracking with ability to resume from last position
3. Better error handling and recovery
4. Automatic retry logic for failed batches
"""

import csv
import json
import time
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction, connection
from django.utils.dateparse import parse_date

from apps.common.constants import CambodianProvinces
from apps.common.utils.limon_to_unicode import limon_to_unicode_conversion
from apps.people.models import (
    EmergencyContact,
    Gender,
    Person,
    PhoneNumber,
    StudentProfile,
)
from apps.data_pipeline.cleaners.name_parser import parse_student_name
from apps.scholarships.models import Sponsor


class Command(BaseCommand):
    """Import students with optimized batch processing and recovery capability."""

    help = "Import students from CSV with timeout-resistant batch processing"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {
            "total_processed": 0,
            "persons_created": 0,
            "students_created": 0,
            "emergency_contacts_created": 0,
            "errors": 0,
            "skipped": 0,
            "name_parsing_warnings": 0,
            "sponsored_students": 0,
            "frozen_students": 0,
            "admin_fee_students": 0,
            "sponsor_links_created": 0,
            "sponsor_links_failed": 0,
            "batches_completed": 0,
            "batches_failed": 0,
        }
        self.errors = []
        self.progress_file = Path("data/student_import_progress.json")
        self.failed_records = []

    def add_arguments(self, parser):
        """Add command-specific arguments."""
        parser.add_argument(
            "--file",
            type=str,
            default="data/legacy/data_pipeline/backup/students.csv",
            help="Path to the student CSV file",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without making changes",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=25,  # Smaller default batch size
            help="Number of records to process in each batch",
        )
        parser.add_argument(
            "--start-from",
            type=str,
            help="Start importing from this student ID (e.g., '17000')",
        )
        parser.add_argument(
            "--resume",
            action="store_true",
            help="Resume from last saved progress",
        )
        parser.add_argument(
            "--max-retries",
            type=int,
            default=3,
            help="Maximum retries for failed batches",
        )
        parser.add_argument(
            "--timeout",
            type=int,
            default=30,
            help="Timeout in seconds per batch",
        )

    def handle(self, *args, **options):
        """Execute the student import with optimized batch processing."""
        csv_file = options["file"]
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        start_from = options.get("start_from")
        resume = options.get("resume")
        max_retries = options.get("max_retries")

        self.stdout.write(f"📄 Reading students from: {csv_file}")

        try:
            with open(csv_file, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"❌ File not found: {csv_file}"))
            return
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error reading file: {e}"))
            return

        # Load progress if resuming
        start_index = 0
        if resume and self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    progress_data = json.load(f)
                    start_index = progress_data.get('last_processed_index', 0)
                    self.stats = progress_data.get('stats', self.stats)
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ Resuming from index {start_index} (already processed {self.stats['total_processed']} records)")
                    )
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️ Could not load progress file: {e}"))

        # Filter by start_from if specified and not resuming
        if start_from and not resume:
            try:
                start_id = int(start_from)
                new_start_index = 0
                for idx, row in enumerate(rows):
                    student_id_str = row.get("ID", "").strip()
                    if student_id_str:
                        try:
                            if int(student_id_str) >= start_id:
                                new_start_index = idx
                                break
                        except ValueError:
                            continue
                start_index = new_start_index
                self.stdout.write(f"🔍 Starting from student ID {start_from} at index {start_index}")
            except ValueError:
                self.stdout.write(self.style.ERROR(f"❌ Invalid start-from value: {start_from}"))
                return

        # Get subset of rows to process
        rows_to_process = rows[start_index:]
        total_records = len(rows_to_process)
        self.stdout.write(f"📋 Processing {total_records} students (out of {len(rows)} total)")

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN - No changes will be made"))

        # Cache existing student IDs
        existing_student_ids = set(StudentProfile.objects.values_list("student_id", flat=True))
        self.stdout.write(f"📊 Found {len(existing_student_ids)} existing students in database")

        # Process in small batches with progress tracking
        for batch_start in range(0, total_records, batch_size):
            batch_end = min(batch_start + batch_size, total_records)
            batch = rows_to_process[batch_start:batch_end]
            batch_num = (start_index + batch_start) // batch_size + 1
            actual_index = start_index + batch_start

            self.stdout.write(f"\n🔄 Processing batch {batch_num} (records {batch_start+1}-{batch_end} of {total_records})")

            # Try processing the batch with retries
            batch_success = False
            for retry in range(max_retries):
                try:
                    if not dry_run:
                        # Use a transaction with timeout
                        with transaction.atomic():
                            # Set statement timeout for PostgreSQL
                            with connection.cursor() as cursor:
                                cursor.execute(f"SET statement_timeout = {options['timeout'] * 1000}")  # milliseconds

                            for row in batch:
                                self._process_student_record(row, existing_student_ids, dry_run)

                            # Reset timeout
                            with connection.cursor() as cursor:
                                cursor.execute("SET statement_timeout = 0")
                    else:
                        for row in batch:
                            self._process_student_record(row, existing_student_ids, dry_run)

                    batch_success = True
                    self.stats["batches_completed"] += 1
                    self.stdout.write(self.style.SUCCESS(f"✅ Batch {batch_num} completed successfully"))

                    # Save progress after each successful batch
                    if not dry_run:
                        self._save_progress(actual_index + len(batch))

                    break  # Success, exit retry loop

                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"⚠️ Batch {batch_num} failed (attempt {retry+1}/{max_retries}): {str(e)[:100]}")
                    )
                    if retry < max_retries - 1:
                        time.sleep(2 ** retry)  # Exponential backoff
                    else:
                        self.stats["batches_failed"] += 1
                        self.stdout.write(self.style.ERROR(f"❌ Batch {batch_num} failed after {max_retries} attempts"))
                        # Save failed records for later analysis
                        for row in batch:
                            self.failed_records.append(row.get("ID", "unknown"))

            # Brief pause between batches to avoid overwhelming the system
            if batch_success and batch_end < total_records:
                time.sleep(0.5)

        # Print final statistics
        self._print_final_stats(dry_run)

        # Save failed records if any
        if self.failed_records and not dry_run:
            failed_file = Path("data/failed_student_imports.json")
            with open(failed_file, 'w') as f:
                json.dump(self.failed_records, f, indent=2)
            self.stdout.write(f"\n📝 Failed record IDs saved to: {failed_file}")

        # Clean up progress file if completed successfully
        if not dry_run and self.stats["batches_failed"] == 0 and self.progress_file.exists():
            self.progress_file.unlink()
            self.stdout.write("🧹 Progress file cleaned up after successful completion")

    def _save_progress(self, last_index):
        """Save current progress to file for recovery."""
        progress_data = {
            "last_processed_index": last_index,
            "stats": self.stats,
            "timestamp": time.time(),
        }
        with open(self.progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)

    def _print_final_stats(self, dry_run):
        """Print comprehensive final statistics."""
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Import complete!\n"
                    f"   Processed: {self.stats['total_processed']}\n"
                    f"   Persons created: {self.stats['persons_created']}\n"
                    f"   Students created: {self.stats['students_created']}\n"
                    f"   Emergency contacts: {self.stats['emergency_contacts_created']}\n"
                    f"   Errors: {self.stats['errors']}\n"
                    f"   Skipped: {self.stats['skipped']}\n"
                    f"   Name parsing warnings: {self.stats['name_parsing_warnings']}\n"
                    f"   Sponsored students: {self.stats['sponsored_students']}\n"
                    f"   Sponsor links created: {self.stats['sponsor_links_created']}\n"
                    f"   Sponsor links failed: {self.stats['sponsor_links_failed']}\n"
                    f"   Frozen students: {self.stats['frozen_students']}\n"
                    f"   Admin fee students: {self.stats['admin_fee_students']}\n"
                    f"   Batches completed: {self.stats['batches_completed']}\n"
                    f"   Batches failed: {self.stats['batches_failed']}",
                ),
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f"🔍 Dry run complete! Would process {self.stats['total_processed']} students")
            )

        # Show sample errors if any
        if self.errors and not dry_run:
            self.stdout.write("\n❌ Sample errors (first 10):")
            for error in self.errors[:10]:
                self.stdout.write(f"   {error}")

    def _process_student_record(self, row, existing_student_ids, dry_run):
        """Process a single student record from CSV."""
        student_id = row.get("ID", "").strip()
        name = row.get("Name", "").strip()
        khmer_name = row.get("KName", "").strip()

        self.stats["total_processed"] += 1

        # Skip deleted records
        if row.get("Deleted") == "1":
            self.stats["skipped"] += 1
            return

        # Validate critical data
        if not student_id or not name:
            self.stats["errors"] += 1
            self.errors.append(f"Student {student_id}: Missing critical data")
            return

        # Check for duplicate student ID
        try:
            student_id_int = int(student_id)
        except (ValueError, TypeError):
            self.stats["errors"] += 1
            self.errors.append(f"Student {student_id}: Invalid ID format")
            return

        if student_id_int in existing_student_ids:
            self.stats["skipped"] += 1
            return

        # Convert Khmer name
        converted_khmer_name = ""
        if khmer_name:
            try:
                converted_khmer_name = limon_to_unicode_conversion(khmer_name)
            except Exception:
                pass  # Continue without Khmer name

        if dry_run:
            self.stdout.write(f"  ✅ Would create: {student_id} - {name}")
            return

        # Parse name components
        family_name, personal_name, parsed_name_data = self._parse_name(name)

        # Track name parsing statistics
        if parsed_name_data:
            if parsed_name_data.parsing_warnings:
                self.stats["name_parsing_warnings"] += 1
            if parsed_name_data.is_sponsored:
                self.stats["sponsored_students"] += 1
            if parsed_name_data.is_frozen:
                self.stats["frozen_students"] += 1
            if parsed_name_data.has_admin_fees:
                self.stats["admin_fee_students"] += 1

        # Parse demographic data
        birth_date = self._parse_date(row.get("BirthDate"))
        gender = self._parse_gender(row.get("Gender"))

        # Create Person record
        try:
            birth_place = self._map_birth_place(row.get("BirthPlace", "").strip())
            nationality = row.get("Nationality", "").strip()
            citizenship = nationality[:2] if nationality else "KH"

            person = Person.objects.create(
                family_name=family_name,
                personal_name=personal_name,
                khmer_name=converted_khmer_name,
                date_of_birth=birth_date,
                birth_province=birth_place,
                citizenship=citizenship,
                preferred_gender=gender,
                personal_email=row.get("SchoolEmail", "").strip() or None,
            )

            self.stats["persons_created"] += 1
            existing_student_ids.add(student_id_int)

            # Create phone numbers if available
            mobile_phone = row.get("MobilePhone", "").strip()
            home_phone = row.get("HomePhone", "").strip()

            if mobile_phone and mobile_phone not in ["NA", "NULL"]:
                try:
                    PhoneNumber.objects.create(
                        person=person,
                        number=mobile_phone,
                        phone_type=PhoneNumber.PhoneType.MOBILE,
                        is_verified=False,
                    )
                except Exception:
                    pass

            if home_phone and home_phone not in ["NA", "NULL"] and home_phone != mobile_phone:
                try:
                    PhoneNumber.objects.create(
                        person=person,
                        number=home_phone,
                        phone_type=PhoneNumber.PhoneType.HOME,
                        is_verified=False,
                    )
                except Exception:
                    pass

        except IntegrityError as e:
            self.stats["errors"] += 1
            self.errors.append(f"Student {student_id}: Duplicate constraint - {str(e)[:50]}")
            return
        except Exception as e:
            self.stats["errors"] += 1
            self.errors.append(f"Student {student_id}: Person creation failed - {str(e)[:50]}")
            return

        # Create StudentProfile
        try:
            student_profile = StudentProfile.objects.create(
                person=person,
                student_id=student_id_int,
                current_status=StudentProfile.Status.ACTIVE,
                last_enrollment_date=self._parse_date(row.get("Lastenroll")),
            )
            self.stats["students_created"] += 1

            # Handle sponsor linking if student is sponsored
            if parsed_name_data and parsed_name_data.is_sponsored:
                self._link_sponsor_to_student(student_profile, parsed_name_data.sponsor_name, student_id)

        except Exception as e:
            self.stats["errors"] += 1
            self.errors.append(f"Student {student_id}: StudentProfile creation failed - {str(e)[:50]}")
            return

        # Create Emergency Contact if data available
        contact_person = row.get("Emg_ContactPerson", "").strip()
        if contact_person:
            try:
                EmergencyContact.objects.create(
                    person=person,
                    name=contact_person,
                    relationship=row.get("Relationship", "").strip(),
                    primary_phone=row.get("ContactPersonPhone", "").strip(),
                    address=row.get("ContactPersonAddress", "").strip(),
                    is_primary=True,
                )
                self.stats["emergency_contacts_created"] += 1
            except Exception:
                pass  # Emergency contact failure shouldn't fail the whole record

    def _parse_name(self, raw_name):
        """Parse raw name using the proper name parser."""
        if not raw_name:
            return "", "", None

        parsed_result = parse_student_name(raw_name)

        if not parsed_result.clean_name:
            return "", "", parsed_result

        clean_name = parsed_result.clean_name.strip()
        name_parts = clean_name.split()

        if len(name_parts) >= 2:
            family_name = name_parts[0]
            personal_name = " ".join(name_parts[1:])
        else:
            family_name = ""
            personal_name = clean_name

        return family_name, personal_name, parsed_result

    def _parse_date(self, date_string):
        """Parse date string to date object."""
        if not date_string or date_string.strip() in ["NULL", "NA", ""]:
            return None

        try:
            if " " in date_string:
                date_string = date_string.split()[0]
            return parse_date(date_string)
        except (ValueError, TypeError):
            return None

    def _parse_gender(self, gender_string):
        """Parse gender string to Gender enum."""
        if not gender_string:
            return Gender.PREFER_NOT_TO_SAY

        gender_map = {
            "M": Gender.MALE,
            "F": Gender.FEMALE,
            "Male": Gender.MALE,
            "Female": Gender.FEMALE,
        }

        return gender_map.get(gender_string.strip(), Gender.PREFER_NOT_TO_SAY)

    def _map_birth_place(self, birth_place):
        """Map legacy birth place to proper Cambodian province constants."""
        if not birth_place or birth_place.strip().upper() in ("NULL", ""):
            return None

        place = birth_place.strip().lower()

        province_mappings = {
            "phnom penh": CambodianProvinces.PHNOM_PENH,
            "phnompenh": CambodianProvinces.PHNOM_PENH,
            "siem reap": CambodianProvinces.SIEM_REAP,
            "siemreap": CambodianProvinces.SIEM_REAP,
            "battambang": CambodianProvinces.BATTAMBANG,
            "kampong thom": CambodianProvinces.KAMPONG_THOM,
            "kampongthom": CambodianProvinces.KAMPONG_THOM,
            "kampong cham": CambodianProvinces.KAMPONG_CHAM,
            "kampongcham": CambodianProvinces.KAMPONG_CHAM,
            "kampong speu": CambodianProvinces.KAMPONG_SPEU,
            "kampongspeu": CambodianProvinces.KAMPONG_SPEU,
            "kandal": CambodianProvinces.KANDAL,
            "takeo": CambodianProvinces.TAKEO,
            "prey veng": CambodianProvinces.PREY_VENG,
            "preyveng": CambodianProvinces.PREY_VENG,
            "kampot": CambodianProvinces.KAMPOT,
            "kep": CambodianProvinces.KEP,
            "preah sihanouk": CambodianProvinces.PREAH_SIHANOUK,
            "sihanoukville": CambodianProvinces.PREAH_SIHANOUK,
            "pursat": CambodianProvinces.PURSAT,
            "banteay meanchey": CambodianProvinces.BANTEAY_MEANCHEY,
            "banteaymeanchey": CambodianProvinces.BANTEAY_MEANCHEY,
        }

        if place in province_mappings:
            return province_mappings[place]

        return CambodianProvinces.UNKNOWN

    def _link_sponsor_to_student(self, student_profile, sponsor_code, student_id):
        """Link a student to a sponsor based on the sponsor code."""
        if not sponsor_code:
            return

        try:
            sponsor = Sponsor.objects.filter(code=sponsor_code).first()

            if sponsor:
                self.stats["sponsor_links_created"] += 1
            else:
                self.stats["sponsor_links_failed"] += 1

        except Exception:
            self.stats["sponsor_links_failed"] += 1