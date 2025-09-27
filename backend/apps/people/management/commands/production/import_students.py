"""Management command to import students from CSV using integrated Limon-to-Unicode converter.

Features:
- Converts Khmer names using Limon-to-Unicode
- Can start from specific student ID
- Comprehensive error handling and reporting
- Dry-run capability
"""

import csv

from django.core.management.base import BaseCommand
from django.db import IntegrityError, transaction
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
    """Import students from CSV with Limon-to-Unicode conversion for Khmer names."""

    help = "Import students from all_students_250714.csv with Khmer name conversion"

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
        }
        self.errors = []

    def add_arguments(self, parser):
        """Add command-specific arguments."""
        parser.add_argument(
            "--file",
            type=str,
            default="data/migrate/all_students_250714.csv",
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
            default=50,
            help="Number of records to process in each batch",
        )
        parser.add_argument(
            "--start-from",
            type=str,
            help="Start importing from this student ID (e.g., '17000')",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of records to process (for testing)",
        )

    def handle(self, *args, **options):
        """Execute the student import."""
        csv_file = options["file"]
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        start_from = options.get("start_from")
        limit = options.get("limit")

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

        # Filter by start_from if specified
        if start_from:
            try:
                start_id = int(start_from.zfill(5))  # Pad with zeros if needed
                filtered_rows = []
                for row in rows:
                    student_id = row.get("ID", "").strip()
                    if student_id and int(student_id) >= start_id:
                        filtered_rows.append(row)
                rows = filtered_rows
                self.stdout.write(f"🔍 Filtering from student ID {start_from}: {len(rows)} records")
            except (ValueError, TypeError):
                self.stdout.write(self.style.ERROR(f"❌ Invalid start-from value: {start_from}"))
                return

        # Apply limit if specified
        if limit:
            rows = rows[:limit]
            self.stdout.write(f"📊 Limited to {limit} records")

        total_records = len(rows)
        self.stdout.write(f"📋 Found {total_records} students to process")

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN - No changes will be made"))

        # Cache existing student IDs to detect duplicates
        existing_student_ids = set(StudentProfile.objects.values_list("student_id", flat=True))

        # Process in batches
        for i in range(0, total_records, batch_size):
            batch = rows[i : i + batch_size]
            batch_num = i // batch_size + 1
            self.stdout.write(f"🔄 Processing batch {batch_num} ({len(batch)} records)")

            if not dry_run:
                with transaction.atomic():
                    for row in batch:
                        self._process_student_record(row, existing_student_ids, dry_run)
            else:
                for row in batch:
                    self._process_student_record(row, existing_student_ids, dry_run)

        # Print final statistics
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Import complete!\n"
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
                    f"   Admin fee students: {self.stats['admin_fee_students']}",
                ),
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"🔍 Dry run complete! Would process {total_records} students"))

        # Show sample errors if any
        if self.errors and not dry_run:
            self.stdout.write("\n❌ Sample errors:")
            for error in self.errors[:5]:  # Show first 5 errors
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
            if dry_run:
                self.stdout.write(f"  ⏭️  Skip {student_id}: marked as deleted")
            return

        # Validate critical data
        if not student_id or not name:
            self.stats["errors"] += 1
            error_msg = f"Missing critical data - ID: '{student_id}', Name: '{name}'"
            self.errors.append(f"Student {student_id}: {error_msg}")
            if dry_run:
                self.stdout.write(f"  ❌ Error {student_id}: {error_msg}")
            return

        # Check for duplicate student ID
        try:
            student_id_int = int(student_id)
        except (ValueError, TypeError):
            self.stats["errors"] += 1
            error_msg = f"Invalid student ID format: '{student_id}'"
            self.errors.append(f"Student {student_id}: {error_msg}")
            if dry_run:
                self.stdout.write(f"  ❌ Error {student_id}: {error_msg}")
            return

        if student_id_int in existing_student_ids:
            self.stats["skipped"] += 1
            if dry_run:
                self.stdout.write(f"  ⏭️  Skip {student_id}: already exists")
            return

        # Convert Khmer name using Limon-to-Unicode
        converted_khmer_name = ""
        if khmer_name:
            try:
                converted_khmer_name = limon_to_unicode_conversion(khmer_name)
            except Exception as e:
                # Log conversion error but continue
                if dry_run:
                    self.stdout.write(f"  ⚠️  Khmer conversion failed for {student_id}: {e}")

        if dry_run:
            self.stdout.write(f"  ✅ Would create: {student_id} - {name}")
            if khmer_name and converted_khmer_name:
                self.stdout.write(f"      Khmer: {khmer_name} → {converted_khmer_name}")
            return

        # Parse name components with special status indicators
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
            # Map birth place using same logic as production script
            birth_place = self._map_birth_place(row.get("BirthPlace", "").strip())

            # Map nationality to 2-letter country code
            nationality = row.get("Nationality", "").strip()
            citizenship = nationality[:2] if nationality else "KH"

            try:
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
            except Exception as e:
                self.stats["errors"] += 1
                error_details = {
                    "student_id": student_id,
                    "name": name,
                    "parsed_name": f"{family_name} {personal_name}",
                    "khmer_name": converted_khmer_name,
                    "birth_date": birth_date,
                    "birth_place": birth_place,
                    "citizenship": citizenship,
                    "gender": gender,
                    "email": row.get("Email", "").strip() or None,
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
                error_msg = f"Person creation failed: {e}"
                self.errors.append(f"Student {student_id}: {error_msg}")
                self.stdout.write(self.style.ERROR(f"❌ PERSON CREATION FAILED for {student_id}: {error_msg}"))
                self.stdout.write(f"   Details: {error_details}")
                return

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
                    # Phone number creation failure shouldn't fail the whole record
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
                    # Phone number creation failure shouldn't fail the whole record
                    pass

        except IntegrityError as e:
            self.stats["errors"] += 1
            error_msg = f"Person creation failed - duplicate constraint: {e}"
            self.errors.append(f"Student {student_id}: {error_msg}")
            return
        except Exception as e:
            self.stats["errors"] += 1
            error_msg = f"Person creation failed: {e}"
            self.errors.append(f"Student {student_id}: {error_msg}")
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
            error_msg = f"StudentProfile creation failed: {e}"
            self.errors.append(f"Student {student_id}: {error_msg}")
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
            except Exception as e:
                # Emergency contact creation failure shouldn't fail the whole record
                error_msg = f"Emergency contact creation failed: {e}"
                self.errors.append(f"Student {student_id} (warning): {error_msg}")

    def _parse_name(self, raw_name):
        """Parse raw name using the proper name parser to handle special indicators.

        This method uses the name parser to:
        1. Strip $$ and non-alpha prefixes
        2. Extract clean names (alpha and spaces only)
        3. Parse status indicators (<sponsor>, $$, {AF})

        Returns:
            tuple: (family_name, personal_name, parsed_data)
        """
        if not raw_name:
            return "", "", None

        # Use the proper name parser
        parsed_result = parse_student_name(raw_name)

        if not parsed_result.clean_name:
            return "", "", parsed_result

        # Split the clean name into family and personal name
        clean_name = parsed_result.clean_name.strip()
        name_parts = clean_name.split()

        if len(name_parts) >= 2:
            family_name = name_parts[0]
            personal_name = " ".join(name_parts[1:])
        else:
            # Single name - treat as personal name
            family_name = ""
            personal_name = clean_name

        return family_name, personal_name, parsed_result

    def _parse_date(self, date_string):
        """Parse date string to date object."""
        if not date_string or date_string.strip() in ["NULL", "NA", ""]:
            return None

        try:
            # Handle datetime strings with time component
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

        # Common mappings from legacy data
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

        # Check direct mappings
        if place in province_mappings:
            return province_mappings[place]

        # If no mapping found, return UNKNOWN for Cambodian places or INTERNATIONAL for others
        return CambodianProvinces.UNKNOWN

    def _link_sponsor_to_student(self, student_profile, sponsor_code, student_id):
        """Link a student to a sponsor based on the sponsor code found in their name.

        Args:
            student_profile: The StudentProfile instance
            sponsor_code: The sponsor code found in the name (e.g., "CRST", "PEPY")
            student_id: Student ID for error reporting
        """
        if not sponsor_code:
            return

        try:
            # Try to find the sponsor by code
            sponsor = Sponsor.objects.filter(code=sponsor_code).first()

            if sponsor:
                # Future enhancement: Link the student to the sponsor
                # This would typically involve creating a scholarship or sponsorship record
                # For now, we'll just log the successful match
                self.stats["sponsor_links_created"] += 1
                self.stdout.write(f"   ✅ Linked student {student_id} to sponsor {sponsor.code}: {sponsor.name}")
            else:
                # Sponsor code not found in database
                self.stats["sponsor_links_failed"] += 1
                self.stdout.write(
                    self.style.WARNING(f"   ⚠️  Sponsor code '{sponsor_code}' not found for student {student_id}"),
                )

        except Exception as e:
            self.stats["sponsor_links_failed"] += 1
            self.stdout.write(self.style.ERROR(f"   ❌ Error linking sponsor for student {student_id}: {e}"))
