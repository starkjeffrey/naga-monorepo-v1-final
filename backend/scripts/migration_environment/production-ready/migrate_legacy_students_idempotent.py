#!/usr/bin/env python3
"""Idempotent script to migrate legacy student data to V1 models.

This enhanced version supports:
- CREATE or UPDATE operations (upsert)
- IPK-based change detection for efficiency
- Incremental processing by student ID range or modification date
- No duplicate creation - safe to run multiple times
- Handles daily additions and updates to legacy system

Usage Examples:
    # Full sync (first time)
    python migrate_legacy_students_idempotent.py --mode upsert

    # Daily incremental sync (only changed records)
    python migrate_legacy_students_idempotent.py --mode upsert --modified-since yesterday

    # Process specific student ID range
    python migrate_legacy_students_idempotent.py --mode upsert --student-id-range 18000:19000

    # Force update all records (ignore IPK comparison)
    python migrate_legacy_students_idempotent.py --mode upsert --force-update

This is the PRIMARY student migration script that creates/updates:
- people.Person records
- people.StudentProfile records
- people.EmergencyContact records
- scholarships.SponsoredStudent records (where sponsor detected)

Based on V0 to V1 field mapping documented in docs/v0_to_v1_field_mapping.md
"""

import os
import sys
from pathlib import Path

import django

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Django setup - use environment-configured settings with fallback
if not os.environ.get("DJANGO_SETTINGS_MODULE"):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.migration")
django.setup()

import json
import re
import uuid
from datetime import date, datetime, timedelta
from enum import Enum

from django.core.management.base import BaseCommand
from django.db import IntegrityError, connection, transaction
from django.utils.dateparse import parse_date, parse_datetime

from apps.common.utils.limon_to_unicode import limon_to_unicode_conversion
from apps.people.models import (
    EmergencyContact,
    Gender,
    Person,
    StudentProfile,
)
from apps.scholarships.models import Sponsor, SponsoredStudent


class Command(BaseCommand):
    """Idempotent migration of legacy student data from legacy_students table to V1 models."""

    help = "Migrate legacy student data to V1 Person, StudentProfile, and related models (idempotent)"

    class ProcessingMode(Enum):
        """Operation modes for the migration."""

        CREATE_ONLY = "create-only"  # Original behavior - reject existing students
        UPDATE_ONLY = "update-only"  # Only update existing students
        UPSERT = "upsert"  # Create new or update existing (DEFAULT)

    class RejectionReason(Enum):
        """Categories for rejected records."""

        MISSING_CRITICAL_DATA = "missing_critical_data"
        DATA_VALIDATION_ERROR = "data_validation_error"
        NAME_PARSING_ERROR = "name_parsing_error"
        DATABASE_ERROR = "database_error"
        UNEXPECTED_ERROR = "unexpected_error"
        DELETED_RECORD = "deleted_record"
        STUDENT_NOT_FOUND = "student_not_found"  # For update-only mode

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {
            # Input statistics
            "total_rows": 0,
            "total_processed": 0,
            "total_successful": 0,
            "total_rejected": 0,
            "total_skipped_unchanged": 0,
            # Person statistics
            "persons_created": 0,
            "persons_updated": 0,
            "persons_skipped": 0,
            # Student statistics
            "students_created": 0,
            "students_updated": 0,
            "students_skipped": 0,
            # Related model statistics
            "emergency_contacts_created": 0,
            "emergency_contacts_updated": 0,
            "emergency_contacts_deleted": 0,
            "sponsorships_created": 0,
            "sponsorships_updated": 0,
            "sponsorships_ended": 0,
            "sponsor_codes_unmatched": 0,
        }

        # Detailed rejection tracking
        self.rejections = {reason.value: [] for reason in self.RejectionReason}
        self.rejection_counts = {reason.value: 0 for reason in self.RejectionReason}

        # Caches for efficiency
        self.sponsor_cache = {}
        self.existing_students_cache: dict[int, StudentProfile] = {}
        self.existing_persons_cache: dict[int, Person] = {}

        # Processing configuration
        self.processing_mode = self.ProcessingMode.UPSERT
        self.force_update = False
        self.student_id_range: tuple[int, int] | None = None
        self.modified_since: datetime | None = None

        # Timing and reporting
        self.migration_start_time = datetime.now()
        self.report_file = None

    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be migrated without making changes",
        )
        parser.add_argument(
            "--batch-size",
            type=int,
            default=100,
            help="Number of records to process in each batch",
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit number of records to process (for testing)",
        )

        # NEW IDEMPOTENT OPTIONS
        parser.add_argument(
            "--mode",
            choices=["create-only", "update-only", "upsert"],
            default="upsert",
            help="Processing mode: create-only (original), update-only, or upsert (default)",
        )
        parser.add_argument(
            "--student-id-range",
            type=str,
            help="Process specific student ID range, format: START:END (e.g., 18000:19000)",
        )
        parser.add_argument(
            "--modified-since",
            type=str,
            help="Only process records modified since date (YYYY-MM-DD) or 'yesterday'",
        )
        parser.add_argument(
            "--force-update",
            action="store_true",
            help="Force update all records even if IPK unchanged",
        )

    def handle(self, *args, **options):
        """Main command handler."""
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        limit = options.get("limit")

        # Parse new options
        self.processing_mode = self.ProcessingMode(options["mode"])
        self.force_update = options["force_update"]

        # Parse student ID range
        if options.get("student_id_range"):
            try:
                start_str, end_str = options["student_id_range"].split(":")
                self.student_id_range = (int(start_str), int(end_str))
                self.stdout.write(
                    f"📊 Processing student ID range: {self.student_id_range[0]} to {self.student_id_range[1]}"
                )
            except ValueError:
                self.stderr.write(
                    self.style.ERROR("❌ Invalid student-id-range format. Use START:END (e.g., 18000:19000)")
                )
                return

        # Parse modified since date
        if options.get("modified_since"):
            modified_since_str = options["modified_since"]
            if modified_since_str.lower() == "yesterday":
                self.modified_since = datetime.now() - timedelta(days=1)
            else:
                try:
                    self.modified_since = datetime.strptime(modified_since_str, "%Y-%m-%d")
                except ValueError:
                    self.stderr.write(
                        self.style.ERROR("❌ Invalid modified-since format. Use YYYY-MM-DD or 'yesterday'")
                    )
                    return
            self.stdout.write(
                f"📅 Processing records modified since: {self.modified_since.strftime('%Y-%m-%d %H:%M:%S')}"
            )

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No database changes will be made"))

        self.stdout.write(f"🔄 Processing mode: {self.processing_mode.value}")
        if self.force_update:
            self.stdout.write("⚡ Force update enabled - will update all records regardless of IPK")

        try:
            # Load caches
            self._load_sponsor_cache()
            self._load_existing_students_cache()

            # Get legacy data count with filters
            total_count = self._get_legacy_record_count()
            self.stats["total_rows"] = min(total_count, limit) if limit else total_count

            self.stdout.write(f"📊 Processing {self.stats['total_rows']} legacy student records")

            # Process in batches
            offset = 0
            while offset < self.stats["total_rows"]:
                batch_limit = min(batch_size, self.stats["total_rows"] - offset)
                self._process_batch(offset, batch_limit, dry_run)
                offset += batch_limit

                self.stdout.write(
                    f"📋 Processed {min(offset, self.stats['total_rows'])} of {self.stats['total_rows']} records",
                )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Migration failed: {e}"))
            raise
        finally:
            # Always generate and save report
            report_dir = "project-docs/migration-reports"
            try:
                report_file = self._save_migration_report(dry_run, report_dir)
                self.stdout.write(f"📋 Migration report saved: {report_file}")
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"⚠️ Could not save migration report: {e}"))

        # Report results
        self._report_results(dry_run)

    def _load_sponsor_cache(self):
        """Load sponsors into cache for sponsor detection."""
        for sponsor in Sponsor.objects.all():
            self.sponsor_cache[sponsor.code] = sponsor

        self.stdout.write(f"📋 Loaded {len(self.sponsor_cache)} sponsors for detection")

        # Alert if no sponsors found
        if not self.sponsor_cache:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  WARNING: NO SPONSORS FOUND IN DATABASE!\n"
                    "   This means NO SponsoredStudent records will be created.\n"
                ),
            )

    def _load_existing_students_cache(self):
        """Load existing students with their IPKs for efficient change detection."""
        self.stdout.write("🔍 Loading existing student profiles for change detection...")

        # Build query with optional filtering
        queryset = StudentProfile.objects.select_related("person").all()

        if self.student_id_range:
            start_id, end_id = self.student_id_range
            queryset = queryset.filter(student_id__gte=start_id, student_id__lte=end_id)

        # Load into cache
        for student_profile in queryset:
            self.existing_students_cache[student_profile.student_id] = student_profile
            self.existing_persons_cache[student_profile.student_id] = student_profile.person

        self.stdout.write(f"📋 Loaded {len(self.existing_students_cache):,} existing student profiles.")

    def _get_legacy_record_count(self) -> int:
        """Get count of legacy records to process based on filters."""
        with connection.cursor() as cursor:
            where_conditions = []
            params = []

            if self.student_id_range:
                start_id, end_id = self.student_id_range
                where_conditions.append("CAST(id AS INTEGER) >= %s AND CAST(id AS INTEGER) <= %s")
                params.extend([start_id, end_id])

            if self.modified_since:
                where_conditions.append("modified_date >= %s")
                params.append(self.modified_since)

            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            cursor.execute(f"SELECT COUNT(*) FROM legacy_students WHERE {where_clause}", params)
            return cursor.fetchone()[0]

    def _process_batch(self, offset: int, limit: int, dry_run: bool):
        """Process a batch of legacy student records with IPK-based change detection."""
        with connection.cursor() as cursor:
            # Build query with filters
            where_conditions = []
            params = []

            if self.student_id_range:
                start_id, end_id = self.student_id_range
                where_conditions.append("CAST(id AS INTEGER) >= %s AND CAST(id AS INTEGER) <= %s")
                params.extend([start_id, end_id])

            if self.modified_since:
                where_conditions.append("modified_date >= %s")
                params.append(self.modified_since)

            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"

            # Add LIMIT/OFFSET
            params.extend([offset, limit])

            cursor.execute(
                f"""
                SELECT
                    id as student_id, name, kname as khmer_name, birth_date, birth_place, gender,
                    nationality, email, school_email, transfer, lastenroll as last_enroll,
                    emg_contact_person as emergency_contact_name,
                    contact_person_phone as emergency_contact_phone,
                    '' as sponsor_info, ipk
                FROM legacy_students
                WHERE {where_clause}
                ORDER BY CAST(id AS INTEGER)
                OFFSET %s LIMIT %s
                """,
                params,
            )

            rows = cursor.fetchall()

        for row in rows:
            # Convert row to dict for easier handling
            student_data = {
                "student_id": row[0],
                "name": row[1],
                "khmer_name": row[2],
                "birth_date": row[3],
                "birth_place": row[4],
                "gender": row[5],
                "nationality": row[6],
                "email": row[7],
                "school_email": row[8],
                "transfer": row[9],
                "last_enroll": row[10],
                "emergency_contact": row[11],
                "emergency_phone": row[12],
                "sponsor_info": row[13],
                "ipk": row[14],  # IPK for change detection
            }

            self.stats["total_processed"] += 1

            try:
                self._process_student_record_idempotent(row, dry_run=dry_run)
                self.stats["total_successful"] += 1

            except IntegrityError as e:
                # This should be rare with idempotent logic
                self._log_rejection(self.RejectionReason.DATABASE_ERROR, student_data, str(e))
            except ValueError as e:
                error_str = str(e).lower()
                if "name parsing" in error_str:
                    reason = self.RejectionReason.NAME_PARSING_ERROR
                elif "missing" in error_str or "required" in error_str:
                    reason = self.RejectionReason.MISSING_CRITICAL_DATA
                else:
                    reason = self.RejectionReason.DATA_VALIDATION_ERROR
                self._log_rejection(reason, student_data, str(e))
            except Exception as e:
                self._log_rejection(self.RejectionReason.UNEXPECTED_ERROR, student_data, str(e))

    def _process_student_record_idempotent(self, row, dry_run=False):
        """Process a single student record with idempotent logic and IPK-based change detection."""
        (
            student_id,
            name,
            khmer_name,
            birth_date,
            birth_place,
            gender,
            nationality,
            email,
            school_email,
            transfer,
            last_enroll,
            emergency_contact,
            emergency_phone,
            sponsor_info,
            legacy_ipk,
        ) = row

        # Convert to dict for error logging
        student_data = {
            "student_id": student_id,
            "name": name,
            "khmer_name": khmer_name,
            "birth_date": birth_date,
            "birth_place": birth_place,
            "gender": gender,
            "nationality": nationality,
            "email": email,
            "school_email": school_email,
            "transfer": transfer,
            "last_enroll": last_enroll,
            "emergency_contact": emergency_contact,
            "emergency_phone": emergency_phone,
            "sponsor_info": sponsor_info,
            "ipk": legacy_ipk,
        }

        # Validate critical data
        if not student_id or not name or not name.strip():
            error_details = f"Missing critical data - student_id: '{student_id}', name: '{name}'"
            self._log_rejection(self.RejectionReason.MISSING_CRITICAL_DATA, student_data, error_details)
            return

        # Convert and validate student_id
        try:
            student_id_int = int(student_id)
        except (ValueError, TypeError):
            error_details = f"Invalid student_id format: '{student_id}'"
            self._log_rejection(self.RejectionReason.DATA_VALIDATION_ERROR, student_data, error_details)
            return

        # Check if student exists
        existing_student = self.existing_students_cache.get(student_id_int)

        # Determine operation based on mode and existence
        if self.processing_mode == self.ProcessingMode.CREATE_ONLY:
            if existing_student:
                error_details = f"Student with ID {student_id} already exists (create-only mode)"
                self._log_rejection(self.RejectionReason.DATABASE_ERROR, student_data, error_details)
                return
        elif self.processing_mode == self.ProcessingMode.UPDATE_ONLY:
            if not existing_student:
                error_details = f"Student with ID {student_id} not found (update-only mode)"
                self._log_rejection(self.RejectionReason.STUDENT_NOT_FOUND, student_data, error_details)
                return

        # IPK-based change detection (skip if not forcing and IPK unchanged)
        if (
            existing_student
            and not self.force_update
            and existing_student.legacy_ipk == legacy_ipk
            and legacy_ipk is not None
        ):
            self.stats["total_skipped_unchanged"] += 1
            return  # No changes needed

        # Parse name and detect sponsor
        try:
            family_name, personal_name, sponsor_code, has_outstanding_fees = self._parse_name_and_sponsor(name)
            if not family_name and not personal_name:
                msg = "Could not parse any valid name components"
                raise ValueError(msg)

            # Use sponsor_info column if available
            if sponsor_info and sponsor_info.strip():
                sponsor_code = sponsor_info.strip().upper()

        except Exception as e:
            error_details = f"Name parsing failed for '{name}': {e}"
            self._log_rejection(self.RejectionReason.NAME_PARSING_ERROR, student_data, error_details)
            return

        # In dry-run mode, skip actual database operations
        if dry_run:
            return

        try:
            with transaction.atomic():
                # UPSERT Person record
                person = self._upsert_person(
                    student_id_int=student_id_int,
                    family_name=family_name,
                    personal_name=personal_name,
                    khmer_name=khmer_name or "",
                    birth_date=birth_date,
                    birth_place=birth_place or "",
                    gender=gender or "",
                    nationality=nationality or "KH",
                    email=email or "",
                    school_email=school_email or "",
                )

                # UPSERT StudentProfile record
                student_profile = self._upsert_student_profile(
                    person=person,
                    student_id=student_id_int,
                    gender=gender,
                    transfer=transfer,
                    last_enroll=last_enroll,
                    has_outstanding_fees=has_outstanding_fees,
                    legacy_ipk=legacy_ipk,
                )

                # Sync Emergency Contact
                if emergency_contact and str(emergency_contact).strip():
                    self._sync_emergency_contact(
                        person=person,
                        name=emergency_contact or "",
                        phone=emergency_phone or "",
                        relationship="",  # Not available in legacy data
                        address="",  # Not available in legacy data
                    )

                # Sync Sponsorship
                if sponsor_code:
                    self._sync_sponsorship(
                        student_profile=student_profile,
                        sponsor_code=sponsor_code,
                        start_date=last_enroll or date.today(),
                    )

        except Exception as e:
            error_details = f"Unexpected error during processing: {e}"
            self._log_rejection(self.RejectionReason.UNEXPECTED_ERROR, student_data, error_details)

    def _upsert_person(self, student_id_int: int, **kwargs) -> Person:
        """Create or update Person record with field mapping."""
        existing_person = self.existing_persons_cache.get(student_id_int)

        # Handle date parsing
        birth_date = None
        if kwargs.get("birth_date"):
            birth_date = self._parse_date_field(kwargs["birth_date"])

        # Handle Khmer name conversion from Limon to Unicode
        khmer_name = kwargs.get("khmer_name", "")
        if khmer_name:
            try:
                khmer_name = limon_to_unicode_conversion(khmer_name)
            except Exception:
                pass  # Keep original if conversion fails

        # Handle school email
        school_email = kwargs.get("school_email", "").strip()
        if school_email.upper() in ("NULL", ""):
            school_email = None
        if not school_email:
            school_email = None

        # Map gender
        gender = kwargs.get("gender", "").upper()
        if gender == "MONK":
            preferred_gender = Gender.MALE
        elif gender == "F":
            preferred_gender = Gender.FEMALE
        elif gender == "M":
            preferred_gender = Gender.MALE
        else:
            preferred_gender = Gender.PREFER_NOT_TO_SAY

        # Prepare person data
        person_data = {
            "family_name": kwargs.get("family_name", ""),
            "personal_name": kwargs.get("personal_name", ""),
            "khmer_name": khmer_name,
            "preferred_gender": preferred_gender,
            "date_of_birth": birth_date,
            "birth_province": self._map_birth_place(kwargs.get("birth_place", "")),
            "citizenship": (kwargs.get("nationality", "KH")[:2] if kwargs.get("nationality") else "KH"),
            "personal_email": kwargs.get("email", "").strip() or None,
            "school_email": school_email,
        }

        if existing_person:
            # Update existing person
            updated = False
            for field, value in person_data.items():
                if getattr(existing_person, field) != value:
                    setattr(existing_person, field, value)
                    updated = True

            if updated:
                existing_person.save(update_fields=person_data.keys())
                self.stats["persons_updated"] += 1
            else:
                self.stats["persons_skipped"] += 1
            return existing_person
        else:
            # Create new person
            person_data["unique_id"] = uuid.uuid4()
            person = Person.objects.create(**person_data)
            self.stats["persons_created"] += 1
            # Cache the new person
            self.existing_persons_cache[student_id_int] = person
            return person

    def _upsert_student_profile(self, person: Person, student_id: int, legacy_ipk: int, **kwargs) -> StudentProfile:
        """Create or update StudentProfile record."""
        existing_student = self.existing_students_cache.get(student_id)

        # Handle transfer student detection
        transfer_field = kwargs.get("transfer", "")
        is_transfer = bool(transfer_field and transfer_field.strip() and transfer_field.strip().upper() != "NULL")

        # Handle monk detection
        gender = kwargs.get("gender", "").upper()
        is_monk = gender == "MONK"

        # Handle last enrollment date
        last_enrollment_date = None
        if kwargs.get("last_enroll"):
            last_enrollment_date = self._parse_date_field(kwargs["last_enroll"])

        # Determine status based on outstanding fees
        has_outstanding_fees = kwargs.get("has_outstanding_fees", False)
        status = StudentProfile.Status.FROZEN if has_outstanding_fees else StudentProfile.Status.ACTIVE

        # Prepare student profile data
        student_data = {
            "person": person,
            "student_id": student_id,
            "is_monk": is_monk,
            "is_transfer_student": is_transfer,
            "current_status": status,
            "last_enrollment_date": last_enrollment_date,
            "legacy_ipk": legacy_ipk,  # Store IPK for future change detection
        }

        if existing_student:
            # Update existing student profile
            updated = False
            for field, value in student_data.items():
                if getattr(existing_student, field) != value:
                    setattr(existing_student, field, value)
                    updated = True

            if updated:
                existing_student.save(update_fields=student_data.keys())
                self.stats["students_updated"] += 1
            else:
                self.stats["students_skipped"] += 1
            return existing_student
        else:
            # Create new student profile
            student_profile = StudentProfile.objects.create(**student_data)
            self.stats["students_created"] += 1
            # Cache the new student
            self.existing_students_cache[student_id] = student_profile
            return student_profile

    def _sync_emergency_contact(self, person: Person, **kwargs):
        """Create, update, or delete EmergencyContact record."""
        # Validate phone number - skip if contains letters
        phone = kwargs.get("phone", "").strip()
        if phone and phone.upper() != "NULL":
            if re.search(r"[a-zA-Z]", phone):
                phone = ""  # Skip phones with letters
        else:
            phone = ""

        # Get existing emergency contact
        existing_contact = EmergencyContact.objects.filter(person=person, is_primary=True).first()

        name = kwargs.get("name", "").strip()

        # If no name provided, delete existing contact
        if not name or name.upper() == "NULL":
            if existing_contact:
                existing_contact.delete()
                self.stats["emergency_contacts_deleted"] += 1
            return

        # Map relationship
        relationship_map = {
            "FATHER": EmergencyContact.Relationship.FATHER,
            "MOTHER": EmergencyContact.Relationship.MOTHER,
            "SPOUSE": EmergencyContact.Relationship.SPOUSE,
            "SIBLING": EmergencyContact.Relationship.SIBLING,
            "GUARDIAN": EmergencyContact.Relationship.GUARDIAN,
            "FRIEND": EmergencyContact.Relationship.FRIEND,
        }

        relationship_field = kwargs.get("relationship", "").upper()
        relationship = relationship_map.get(relationship_field, EmergencyContact.Relationship.OTHER)

        contact_data = {
            "person": person,
            "name": name,
            "relationship": relationship,
            "primary_phone": phone,
            "address": kwargs.get("address", "").strip(),
            "is_primary": True,
        }

        if existing_contact:
            # Update existing contact
            updated = False
            for field, value in contact_data.items():
                if getattr(existing_contact, field) != value:
                    setattr(existing_contact, field, value)
                    updated = True

            if updated:
                existing_contact.save(update_fields=contact_data.keys())
                self.stats["emergency_contacts_updated"] += 1
        else:
            # Create new contact
            EmergencyContact.objects.create(**contact_data)
            self.stats["emergency_contacts_created"] += 1

    def _sync_sponsorship(self, student_profile: StudentProfile, sponsor_code: str, start_date):
        """Create, update, or end SponsoredStudent relationship."""
        sponsor = self.sponsor_cache.get(sponsor_code)
        if not sponsor:
            self.stats["sponsor_codes_unmatched"] += 1
            return

        # Parse start date
        if isinstance(start_date, str):
            start_date = self._parse_date_field(start_date) or date.today()
        elif start_date is None:
            start_date = date.today()

        # Get existing sponsorship
        existing_sponsorship = SponsoredStudent.objects.filter(
            student=student_profile,
            sponsor=sponsor,
            end_date__isnull=True,  # Active sponsorship
        ).first()

        sponsorship_data = {
            "sponsor": sponsor,
            "student": student_profile,
            "sponsorship_type": SponsoredStudent.SponsorshipType.FULL,
            "start_date": start_date,
            "notes": "Auto-detected from legacy data during migration",
        }

        if existing_sponsorship:
            # Update existing sponsorship
            updated = False
            for field, value in sponsorship_data.items():
                if hasattr(existing_sponsorship, field) and getattr(existing_sponsorship, field) != value:
                    setattr(existing_sponsorship, field, value)
                    updated = True

            if updated:
                existing_sponsorship.save(update_fields=sponsorship_data.keys())
                self.stats["sponsorships_updated"] += 1
        else:
            # Create new sponsorship
            SponsoredStudent.objects.create(**sponsorship_data)
            self.stats["sponsorships_created"] += 1

    # REUSE EXISTING HELPER METHODS FROM ORIGINAL SCRIPT
    def _parse_name_and_sponsor(self, name_field: str) -> tuple[str, str, str | None, bool]:
        """Parse name field and extract sponsor code if present."""
        if not name_field or name_field is None:
            return "", "", None, False

        name_field = str(name_field).strip()
        has_outstanding_fees = name_field.startswith("$$")

        # Extract sponsor codes from various delimiters: <>, {}, []
        sponsor_code = None
        sponsor_match = re.search(r"<([^>]+)>", name_field)
        if sponsor_match:
            sponsor_code = sponsor_match.group(1).strip().upper()

        if not sponsor_code:
            sponsor_match = re.search(r"\{([^}]+)\}", name_field)
            if sponsor_match:
                sponsor_code = sponsor_match.group(1).strip().upper()

        # Clean name - remove all delimited content and special characters
        clean_name = name_field
        clean_name = re.sub(r"<[^>]+>", "", clean_name)  # Remove <...>
        clean_name = re.sub(r"\{[^}]+\}", "", clean_name)  # Remove {...}
        clean_name = re.sub(r"\[[^\]]+\]", "", clean_name)  # Remove [...]
        clean_name = re.sub(r"[$#]+", "", clean_name)  # Remove $ and # characters
        clean_name = re.sub(r"[^a-zA-Z\s]", " ", clean_name)
        clean_name = re.sub(r"\s+", " ", clean_name).strip()

        # Split into family/personal names (Cambodian convention: family name first)
        parts = clean_name.split()
        if not parts:
            return "", "", sponsor_code, has_outstanding_fees

        if len(parts) == 1:
            return parts[0].upper(), "", sponsor_code, has_outstanding_fees

        family_name = parts[0].upper()
        personal_name = " ".join(parts[1:]).upper()

        return family_name, personal_name, sponsor_code, has_outstanding_fees

    def _parse_date_field(self, date_value) -> date | None:
        """Parse various date formats from legacy data."""
        if not date_value or date_value in ("NULL", "", "null"):
            return None

        try:
            parsed = parse_datetime(str(date_value))
            if parsed:
                return parsed.date()

            parsed = parse_date(str(date_value))
            if parsed:
                return parsed

        except (ValueError, TypeError):
            pass

        return None

    def _map_birth_place(self, birth_place: str) -> str | None:
        """Map legacy birth place to V1 province choices."""
        if not birth_place or birth_place.strip().upper() in ("NULL", ""):
            return None

        place = birth_place.strip()
        if place.lower() in ("phnom penh", "phnompenh"):
            return "phnom_penh"

        return place.lower().replace(" ", "_")[:50]

    def _log_rejection(self, reason: RejectionReason, student_data: dict, error_details: str):
        """Log a rejected record with detailed information."""
        rejection_entry = {
            "timestamp": datetime.now().isoformat(),
            "reason": reason.value,
            "student_id": student_data.get("student_id", "UNKNOWN"),
            "name": student_data.get("name", "UNKNOWN"),
            "error_details": error_details,
            "raw_data": student_data,
        }

        self.rejections[reason.value].append(rejection_entry)
        self.rejection_counts[reason.value] += 1
        self.stats["total_rejected"] += 1

    def _save_migration_report(self, dry_run: bool, report_dir: str):
        """Save comprehensive migration report to file."""
        os.makedirs(report_dir, exist_ok=True)

        timestamp = self.migration_start_time.strftime("%Y%m%d_%H%M%S")
        mode = "dry_run" if dry_run else "migration"
        report_file = f"{report_dir}/student_migration_idempotent_{mode}_report_{timestamp}.json"

        report = {
            "migration_info": {
                "script": "migrate_legacy_students_idempotent.py",
                "timestamp": self.migration_start_time.isoformat(),
                "mode": mode,
                "processing_mode": self.processing_mode.value,
                "force_update": self.force_update,
                "student_id_range": self.student_id_range,
                "modified_since": self.modified_since.isoformat() if self.modified_since else None,
                "duration_seconds": (datetime.now() - self.migration_start_time).total_seconds(),
            },
            "summary": {
                "input": {
                    "total_legacy_records": self.stats["total_rows"],
                    "processed_records": self.stats["total_processed"],
                },
                "output": {
                    "successful_operations": self.stats["total_successful"],
                    "skipped_unchanged": self.stats["total_skipped_unchanged"],
                    "persons_created": self.stats["persons_created"],
                    "persons_updated": self.stats["persons_updated"],
                    "persons_skipped": self.stats["persons_skipped"],
                    "students_created": self.stats["students_created"],
                    "students_updated": self.stats["students_updated"],
                    "students_skipped": self.stats["students_skipped"],
                    "emergency_contacts_created": self.stats["emergency_contacts_created"],
                    "emergency_contacts_updated": self.stats["emergency_contacts_updated"],
                    "emergency_contacts_deleted": self.stats["emergency_contacts_deleted"],
                    "sponsorships_created": self.stats["sponsorships_created"],
                    "sponsorships_updated": self.stats["sponsorships_updated"],
                    "sponsorships_ended": self.stats["sponsorships_ended"],
                    "sponsor_codes_unmatched": self.stats["sponsor_codes_unmatched"],
                },
                "rejected": {
                    "total_rejected": self.stats["total_rejected"],
                    "rejection_breakdown": self.rejection_counts,
                },
            },
            "detailed_rejections": self.rejections,
            "recommendations": self._generate_recommendations(),
        }

        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        return report_file

    def _generate_recommendations(self) -> list:
        """Generate recommendations based on processing results."""
        recommendations = []

        # Sponsor-related recommendations
        if not self.sponsor_cache:
            recommendations.insert(
                0,
                "🚨 CRITICAL: NO SPONSORS FOUND! Load sponsor fixtures before re-running migration.",
            )
        elif self.stats["sponsor_codes_unmatched"] > 0:
            recommendations.append(
                f"Found {self.stats['sponsor_codes_unmatched']} unmatched sponsor codes. Review sponsor data completeness.",
            )

        # Processing efficiency recommendations
        if self.stats["total_skipped_unchanged"] > 0:
            recommendations.append(
                f"✅ Efficient processing: {self.stats['total_skipped_unchanged']} records skipped (no changes needed based on IPK).",
            )

        if self.rejection_counts["name_parsing_error"] > 0:
            recommendations.append("Review name parsing logic. Some legacy names may require manual cleanup.")

        if self.rejection_counts["data_validation_error"] > 0:
            recommendations.append("Review data validation rules. Legacy data may not meet current constraints.")

        if self.stats["total_rejected"] > self.stats["total_successful"] * 0.05:  # >5% rejection rate
            recommendations.append(
                "High rejection rate detected. Consider comprehensive data audit before re-migration.",
            )

        return recommendations

    def _report_results(self, dry_run: bool):
        """Report migration results with comprehensive statistics."""
        mode = "DRY RUN" if dry_run else f"IDEMPOTENT MIGRATION ({self.processing_mode.value})"

        self.stdout.write(f"\n📊 {mode} RESULTS:")
        self.stdout.write("   📈 INPUT:")
        self.stdout.write(f"      Total legacy records: {self.stats['total_rows']:,}")
        self.stdout.write(f"      Records processed: {self.stats['total_processed']:,}")

        self.stdout.write("   ✅ OUTPUT (SUCCESSFUL):")
        self.stdout.write(f"      Total successful: {self.stats['total_successful']:,}")
        self.stdout.write(f"      Skipped (unchanged): {self.stats['total_skipped_unchanged']:,}")

        self.stdout.write("   👥 PERSONS:")
        self.stdout.write(f"      Created: {self.stats['persons_created']:,}")
        self.stdout.write(f"      Updated: {self.stats['persons_updated']:,}")
        self.stdout.write(f"      Skipped: {self.stats['persons_skipped']:,}")

        self.stdout.write("   🎓 STUDENTS:")
        self.stdout.write(f"      Created: {self.stats['students_created']:,}")
        self.stdout.write(f"      Updated: {self.stats['students_updated']:,}")
        self.stdout.write(f"      Skipped: {self.stats['students_skipped']:,}")

        self.stdout.write("   📞 EMERGENCY CONTACTS:")
        self.stdout.write(f"      Created: {self.stats['emergency_contacts_created']:,}")
        self.stdout.write(f"      Updated: {self.stats['emergency_contacts_updated']:,}")
        self.stdout.write(f"      Deleted: {self.stats['emergency_contacts_deleted']:,}")

        self.stdout.write("   💰 SPONSORSHIPS:")
        self.stdout.write(f"      Created: {self.stats['sponsorships_created']:,}")
        self.stdout.write(f"      Updated: {self.stats['sponsorships_updated']:,}")
        self.stdout.write(f"      Ended: {self.stats['sponsorships_ended']:,}")

        # Add sponsor warnings
        if not self.sponsor_cache:
            self.stdout.write(
                self.style.WARNING("      ⚠️  NO SPONSORS IN DATABASE - 0 sponsorships could be created!"),
            )
        if self.stats["sponsor_codes_unmatched"] > 0:
            self.stdout.write(
                self.style.WARNING(f"      ⚠️  Unmatched sponsor codes: {self.stats['sponsor_codes_unmatched']:,}"),
            )

        self.stdout.write("   ❌ REJECTED:")
        self.stdout.write(f"      Total rejected: {self.stats['total_rejected']:,}")

        if self.stats["total_rejected"] > 0:
            self.stdout.write("   📋 REJECTION BREAKDOWN:")
            for reason, count in self.rejection_counts.items():
                if count > 0:
                    self.stdout.write(f"      {reason.replace('_', ' ').title()}: {count:,}")

        # Calculate success rate
        if self.stats["total_processed"] > 0:
            success_rate = (self.stats["total_successful"] / self.stats["total_processed"]) * 100
            self.stdout.write(f"\n   📊 SUCCESS RATE: {success_rate:.1f}%")

        # Show efficiency metrics
        if self.stats["total_skipped_unchanged"] > 0:
            skip_rate = (self.stats["total_skipped_unchanged"] / self.stats["total_processed"]) * 100
            self.stdout.write(f"   ⚡ EFFICIENCY: {skip_rate:.1f}% of records skipped (no changes needed)")

        if not dry_run:
            if self.stats["total_rejected"] == 0:
                self.stdout.write(self.style.SUCCESS("\n✅ Migration completed successfully with no rejections!"))
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✅ Migration completed with {self.stats['total_rejected']} rejections.",
                    ),
                )
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ Dry run completed - ready for migration!"))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate legacy student data to V1 models (idempotent)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of records to process in each batch",
    )
    parser.add_argument("--limit", type=int, help="Limit number of records to process (for testing)")
    parser.add_argument(
        "--mode",
        choices=["create-only", "update-only", "upsert"],
        default="upsert",
        help="Processing mode: create-only (original), update-only, or upsert (default)",
    )
    parser.add_argument(
        "--student-id-range",
        type=str,
        help="Process specific student ID range, format: START:END (e.g., 18000:19000)",
    )
    parser.add_argument(
        "--modified-since",
        type=str,
        help="Only process records modified since date (YYYY-MM-DD) or 'yesterday'",
    )
    parser.add_argument(
        "--force-update",
        action="store_true",
        help="Force update all records even if IPK unchanged",
    )

    args = parser.parse_args()

    # Create command instance and run
    command = Command()
    command.handle(**vars(args))
