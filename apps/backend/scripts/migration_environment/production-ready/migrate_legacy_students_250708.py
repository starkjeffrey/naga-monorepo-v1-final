"""Script to migrate legacy student data to V1 models.

This is the PRIMARY student migration script that creates:
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
from datetime import date, datetime
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
    """Migrate legacy student data from legacy_students table to V1 models."""

    help = "Migrate legacy student data to V1 Person, StudentProfile, and related models"

    class RejectionReason(Enum):
        """Categories for rejected records."""

        MISSING_CRITICAL_DATA = "missing_critical_data"
        DUPLICATE_CONSTRAINT = "duplicate_constraint"
        DATA_VALIDATION_ERROR = "data_validation_error"
        NAME_PARSING_ERROR = "name_parsing_error"
        DATABASE_ERROR = "database_error"
        UNEXPECTED_ERROR = "unexpected_error"
        DELETED_RECORD = "deleted_record"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {
            "total_rows": 0,
            "persons_created": 0,
            "students_created": 0,
            "emergency_contacts_created": 0,
            "sponsorships_created": 0,
            "total_processed": 0,
            "total_successful": 0,
            "total_rejected": 0,
            "sponsor_codes_unmatched": 0,  # Track sponsor codes that couldn't be linked
        }
        # Detailed rejection tracking
        self.rejections = {reason.value: [] for reason in self.RejectionReason}
        self.rejection_counts = {reason.value: 0 for reason in self.RejectionReason}
        self.sponsor_cache = {}
        self.existing_student_ids = set()
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

    def _generate_report_filename(self, report_dir: str, dry_run: bool) -> str:
        """Generate timestamped report filename."""
        timestamp = self.migration_start_time.strftime("%Y%m%d_%H%M%S")
        mode = "dry_run" if dry_run else "migration"
        return f"{report_dir}/student_migration_{mode}_report_{timestamp}.json"

    def _save_migration_report(self, dry_run: bool, report_dir: str):
        """Save comprehensive migration report to file."""
        os.makedirs(report_dir, exist_ok=True)

        report = {
            "migration_info": {
                "script": "migrate_legacy_students_250626.py",
                "timestamp": self.migration_start_time.isoformat(),
                "mode": "dry_run" if dry_run else "migration",
                "duration_seconds": (datetime.now() - self.migration_start_time).total_seconds(),
            },
            "summary": {
                "input": {
                    "total_legacy_records": self.stats["total_rows"],
                    "processed_records": self.stats["total_processed"],
                },
                "output": {
                    "successful_migrations": self.stats["total_successful"],
                    "persons_created": self.stats["persons_created"],
                    "students_created": self.stats["students_created"],
                    "emergency_contacts_created": self.stats["emergency_contacts_created"],
                    "sponsorships_created": self.stats["sponsorships_created"],
                    "sponsor_codes_unmatched": self.stats["sponsor_codes_unmatched"],
                },
                "rejected": {
                    "total_rejected": self.stats["total_rejected"],
                    "rejection_breakdown": self.rejection_counts,
                },
                "sponsor_warnings": {
                    "sponsors_in_database": len(self.sponsor_cache),
                    "unmatched_sponsor_codes": self.stats["sponsor_codes_unmatched"],
                    "no_sponsors_warning": len(self.sponsor_cache) == 0,
                },
            },
            "detailed_rejections": self.rejections,
            "recommendations": self._generate_recommendations(),
        }

        report_file = self._generate_report_filename(report_dir, dry_run)
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2, default=str)

        self.report_file = report_file
        return report_file

    def _generate_recommendations(self) -> list:
        """Generate recommendations based on rejection patterns."""
        recommendations = []

        # Sponsor-related recommendations (CRITICAL - check first)
        if not self.sponsor_cache:
            recommendations.insert(
                0,
                "🚨 CRITICAL: NO SPONSORS FOUND! Load sponsor fixtures before re-running migration to create sponsorship relationships.",
            )
        elif self.stats["sponsor_codes_unmatched"] > 0:
            recommendations.append(
                f"Found {self.stats['sponsor_codes_unmatched']} unmatched sponsor codes. Review sponsor data completeness.",
            )

        if self.rejection_counts["duplicate_constraint"] > 0:
            recommendations.append(
                "Review duplicate email constraints. Consider data deduplication or email generation strategy.",
            )

        if self.rejection_counts["missing_critical_data"] > 0:
            recommendations.append("Review data quality in legacy system. Consider data cleanup before re-migration.")

        if self.rejection_counts["name_parsing_error"] > 0:
            recommendations.append("Review name parsing logic. Some legacy names may require manual cleanup.")

        if self.rejection_counts["data_validation_error"] > 0:
            recommendations.append("Review data validation rules. Legacy data may not meet current constraints.")

        if self.stats["total_rejected"] > self.stats["total_successful"] * 0.05:  # >5% rejection rate
            recommendations.append(
                "High rejection rate detected. Consider comprehensive data audit before re-migration.",
            )

        return recommendations

    def handle(self, *args, **options):
        """Main command handler."""
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]
        limit = options.get("limit")

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No database changes will be made"))

        try:
            # Load sponsor cache and existing student IDs
            self._load_sponsor_cache()
            self._cache_existing_student_ids()

            # Get legacy data count
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM legacy_students")
                total_count = cursor.fetchone()[0]
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
                    "   Students with sponsor codes in their names will be imported\n"
                    "   but their sponsorship relationships will NOT be recorded.\n",
                ),
            )

            # Ask for confirmation to continue
            if not self.dry_run:
                response = input("\n   Do you want to continue without creating sponsorships? (yes/no): ")
                if response.lower() not in ("yes", "y"):
                    self.stdout.write(self.style.ERROR("❌ Migration cancelled by user."))
                    raise SystemExit(1)

    def _cache_existing_student_ids(self):
        """Cache all existing student IDs to eliminate N+1 queries."""
        self.stdout.write("🔍 Caching existing student IDs...")
        self.existing_student_ids = set(StudentProfile.objects.values_list("student_id", flat=True))
        self.stdout.write(f"📋 Found {len(self.existing_student_ids):,} existing students.")

    def _process_batch(self, offset: int, limit: int, dry_run: bool):
        """Process a batch of legacy student records."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    student_id, name, khmer_name, birth_date, birth_place as birth_province, gender,
                    nationality as citizenship, email, school_email, transfer, last_enroll,
                    emergency_contact as emergency_contact_name, emergency_phone as emergency_contact_phone, '' as sponsor_info
                FROM legacy_students
                ORDER BY CAST(student_id AS INTEGER)
                OFFSET %s LIMIT %s
            """,
                [offset, limit],
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
            }

            self.stats["total_processed"] += 1

            try:
                self._process_student_record(row, dry_run=dry_run)
                self.stats["total_successful"] += 1

            except IntegrityError as e:
                self._log_rejection(self.RejectionReason.DUPLICATE_CONSTRAINT, student_data, str(e))
            except ValueError as e:
                # Determine if it's parsing or validation error
                error_str = str(e).lower()
                if "name parsing" in error_str:
                    reason = self.RejectionReason.NAME_PARSING_ERROR
                elif "missing" in error_str or "required" in error_str:
                    reason = self.RejectionReason.MISSING_CRITICAL_DATA
                else:
                    reason = self.RejectionReason.DATA_VALIDATION_ERROR
                self._log_rejection(reason, student_data, str(e))
            except Exception as e:
                # This is now a true catch-all for unexpected errors
                self._log_rejection(self.RejectionReason.UNEXPECTED_ERROR, student_data, str(e))

    def _process_student_record(self, row, dry_run=False):
        """Process a single student record with comprehensive error handling."""
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
        }

        # Validate critical data
        if not student_id or not name or not name.strip():
            error_details = f"Missing critical data - student_id: '{student_id}', name: '{name}'"
            self._log_rejection(self.RejectionReason.MISSING_CRITICAL_DATA, student_data, error_details)
            return

        # Check for existing student by student_id (using cached set - no database query)
        try:
            student_id_int = int(student_id)
            if student_id_int in self.existing_student_ids:
                error_details = f"Student with ID {student_id} already exists in database"
                self._log_rejection(
                    self.RejectionReason.DUPLICATE_CONSTRAINT,
                    student_data,
                    error_details,
                )
                return
        except (ValueError, TypeError):
            error_details = f"Invalid student_id format: '{student_id}'"
            self._log_rejection(self.RejectionReason.DATA_VALIDATION_ERROR, student_data, error_details)
            return

        # Parse name and detect sponsor (always validate this logic)
        try:
            family_name, personal_name, sponsor_code, has_outstanding_fees = self._parse_name_and_sponsor(name)
            if not family_name and not personal_name:
                msg = "Could not parse any valid name components"
                raise ValueError(msg)

            # Use sponsor_info column directly if available (more reliable than parsing from name)
            sponsor_info = student_data.get("sponsor_info", "").strip()
            if sponsor_info:
                sponsor_code = sponsor_info.upper()

        except Exception as e:
            error_details = f"Name parsing failed for '{name}': {e}"
            self._log_rejection(self.RejectionReason.NAME_PARSING_ERROR, student_data, error_details)
            return

        # In dry-run mode, skip actual database operations
        if dry_run:
            return

        try:
            with transaction.atomic():
                # Create Person record
                try:
                    person = self._create_person(
                        family_name=family_name,
                        personal_name=personal_name,
                        khmer_name=khmer_name or "",
                        birth_date=birth_date,
                        birth_place=birth_place or "",
                        gender=gender or "",
                        nationality=nationality or "KH",
                        email=email or "",
                        school_email=school_email or "",
                        student_id=student_id,
                    )
                except Exception as e:
                    # Check if it's a unique constraint violation
                    if "unique constraint" in str(e).lower() or "duplicate" in str(e).lower():
                        error_details = f"Duplicate constraint violation: {e}"
                        self._log_rejection(
                            self.RejectionReason.DUPLICATE_CONSTRAINT,
                            student_data,
                            error_details,
                        )
                    else:
                        error_details = f"Person creation failed: {e}"
                        self._log_rejection(
                            self.RejectionReason.DATABASE_ERROR,
                            student_data,
                            error_details,
                        )
                    return

                # Create StudentProfile record
                try:
                    student_profile = self._create_student_profile(
                        person=person,
                        student_id=student_id,
                        gender=gender,
                        transfer=transfer,
                        last_enroll=last_enroll,
                        has_outstanding_fees=has_outstanding_fees,
                    )
                except Exception as e:
                    error_details = f"StudentProfile creation failed: {e}"
                    self._log_rejection(self.RejectionReason.DATABASE_ERROR, student_data, error_details)
                    return

                # Create Emergency Contact if data exists
                if emergency_contact and str(emergency_contact).strip():
                    try:
                        self._create_emergency_contact(
                            person=person,
                            name=emergency_contact or "",
                            phone=emergency_phone or "",
                            relationship="",  # Not available in database
                            address="",  # Not available in database
                        )
                    except Exception as e:
                        # Emergency contact failures are not critical - log but continue
                        error_details = f"Emergency contact creation failed (non-critical): {e}"
                        # Don't reject the whole record for this

                # Create Sponsorship if sponsor detected
                if sponsor_code:
                    if sponsor_code in self.sponsor_cache:
                        try:
                            self._create_sponsorship(
                                student_profile=student_profile,
                                sponsor_code=sponsor_code,
                                start_date=last_enroll or date.today(),
                            )
                        except Exception as e:
                            # Sponsorship failures are not critical - log but continue
                            error_details = f"Sponsorship creation failed (non-critical): {e}"
                            # Don't reject the whole record for this
                    else:
                        # Track unmatched sponsor codes
                        self.stats["sponsor_codes_unmatched"] += 1
                        if not self.sponsor_cache:
                            # No sponsors in database at all
                            self.stdout.write(
                                self.style.WARNING(
                                    f"⚠️  Student {student_id} has sponsor code <{sponsor_code}> but NO SPONSORS exist in database",
                                ),
                            )

        except Exception as e:
            # Catch any unexpected errors
            error_details = f"Unexpected error during processing: {e}"
            self._log_rejection(self.RejectionReason.UNEXPECTED_ERROR, student_data, error_details)

    def _parse_name_and_sponsor(self, name_field: str) -> tuple[str, str, str | None, bool]:
        """Parse name field and extract sponsor code if present.

        Examples:
            "JOHN DOE" -> ("JOHN", "DOE", None, False)
            "$$ JOHN DOE <PLF> $$" -> ("JOHN", "DOE", "PLF", True)
            "JOHN DOE <CRST>" -> ("JOHN", "DOE", "CRST", False)
            "$$ JOHN DOE $$" -> ("JOHN", "DOE", None, True)
            "JOHN DOE {AF}" -> ("JOHN", "DOE", "AF", False)
            "[INFO] JOHN DOE" -> ("JOHN", "DOE", None, False)

        Returns:
            tuple: (family_name, personal_name, sponsor_code, has_outstanding_fees)
        """
        if not name_field or name_field is None:
            return "", "", None, False

        name_field = str(name_field).strip()

        # Check for outstanding fees marker ($$)
        has_outstanding_fees = name_field.startswith("$$")

        # Extract sponsor codes from various delimiters: <>, {}, []
        sponsor_code = None

        # Try <CODE> pattern first (most common)
        sponsor_match = re.search(r"<([^>]+)>", name_field)
        if sponsor_match:
            sponsor_code = sponsor_match.group(1).strip().upper()

        # Try {CODE} pattern if no <> found
        if not sponsor_code:
            sponsor_match = re.search(r"\{([^}]+)\}", name_field)
            if sponsor_match:
                sponsor_code = sponsor_match.group(1).strip().upper()

        # Note: [] is often used for other info, not sponsor codes

        # Clean name - remove all delimited content and special characters
        clean_name = name_field

        # Remove content in various delimiters
        clean_name = re.sub(r"<[^>]+>", "", clean_name)  # Remove <...>
        clean_name = re.sub(r"\{[^}]+\}", "", clean_name)  # Remove {...}
        clean_name = re.sub(r"\[[^\]]+\]", "", clean_name)  # Remove [...]

        # Remove special markers
        clean_name = re.sub(r"[$#]+", "", clean_name)  # Remove $ and # characters

        # Remove any non-alphabetic characters except spaces
        clean_name = re.sub(r"[^a-zA-Z\s]", " ", clean_name)

        # Normalize multiple spaces to single space
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

    def _create_person(self, **kwargs) -> Person:
        """Create Person record with field mapping."""
        # Handle date parsing
        birth_date = None
        if kwargs.get("birth_date"):
            birth_date = self._parse_date_field(kwargs["birth_date"])

        # Handle Khmer name conversion from Limon to Unicode
        khmer_name = kwargs.get("khmer_name", "")
        if khmer_name:
            try:
                khmer_name = limon_to_unicode_conversion(khmer_name)
            except Exception as e:
                # Log conversion failure but keep original
                self._log_rejection(
                    self.RejectionReason.DATA_VALIDATION_ERROR,
                    kwargs,
                    f"Khmer name conversion failed: {e}, keeping original: {khmer_name}",
                )
                pass  # Keep original if conversion fails

        # Handle school email - DO NOT auto-generate (emails only started in 2018)
        school_email = kwargs.get("school_email", "").strip()
        # Treat 'NULL' string as empty value
        if school_email.upper() in ("NULL", ""):
            school_email = None
        # Only use school email if it was actually provided in legacy data
        # DO NOT auto-generate - students before 2018 never had institutional emails
        if not school_email:
            school_email = None

        # Map gender (handle MONK case)
        gender = kwargs.get("gender", "").upper()
        if gender == "MONK":
            preferred_gender = Gender.MALE
        elif gender == "F":
            preferred_gender = Gender.FEMALE
        elif gender == "M":
            preferred_gender = Gender.MALE
        else:
            preferred_gender = Gender.PREFER_NOT_TO_SAY

        person = Person.objects.create(
            unique_id=uuid.uuid4(),
            family_name=kwargs.get("family_name", ""),  # Already uppercase from parser
            personal_name=kwargs.get("personal_name", ""),  # Already uppercase from parser
            khmer_name=khmer_name,
            preferred_gender=preferred_gender,
            date_of_birth=birth_date,
            birth_province=self._map_birth_place(kwargs.get("birth_place", "")),
            citizenship=(kwargs.get("nationality", "KH")[:2] if kwargs.get("nationality") else "KH"),
            personal_email=kwargs.get("email", "").strip() or None,
            school_email=school_email or None,
        )

        self.stats["persons_created"] += 1
        return person

    def _create_student_profile(self, person: Person, **kwargs) -> StudentProfile:
        """Create StudentProfile record."""
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

        student_profile = StudentProfile.objects.create(
            person=person,
            student_id=int(kwargs["student_id"]),
            is_monk=is_monk,
            is_transfer_student=is_transfer,
            current_status=status,
            last_enrollment_date=last_enrollment_date,
        )

        self.stats["students_created"] += 1
        return student_profile

    def _create_emergency_contact(self, person: Person, **kwargs):
        """Create EmergencyContact record with phone validation."""
        # Validate phone number - skip if contains letters
        phone = kwargs.get("phone", "").strip()
        if phone and phone.upper() != "NULL":
            # Check if phone contains letters (invalid)
            if re.search(r"[a-zA-Z]", phone):
                phone = ""  # Skip phones with letters
        else:
            phone = ""

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

        EmergencyContact.objects.create(
            person=person,
            name=kwargs.get("name", "").strip(),
            relationship=relationship,
            primary_phone=phone,
            address=kwargs.get("address", "").strip(),
            is_primary=True,  # Mark as primary since it's the only one
        )

        self.stats["emergency_contacts_created"] += 1

    def _create_sponsorship(self, student_profile: StudentProfile, sponsor_code: str, start_date):
        """Create SponsoredStudent relationship."""
        sponsor = self.sponsor_cache.get(sponsor_code)
        if not sponsor:
            return

        # Parse start date
        if isinstance(start_date, str):
            start_date = self._parse_date_field(start_date) or date.today()
        elif start_date is None:
            start_date = date.today()

        SponsoredStudent.objects.create(
            sponsor=sponsor,
            student=student_profile,
            sponsorship_type=SponsoredStudent.SponsorshipType.FULL,
            start_date=start_date,
            notes="Auto-detected from name field during migration",
        )

        self.stats["sponsorships_created"] += 1

    def _parse_date_field(self, date_value) -> date | None:
        """Parse various date formats from legacy data."""
        if not date_value or date_value in ("NULL", "", "null"):
            return None

        try:
            # Try datetime first, then date
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

        # Simple mapping - could be expanded
        place = birth_place.strip()
        if place.lower() in ("phnom penh", "phnompenh"):
            return "phnom_penh"

        # Default to the place as-is if it's a valid choice
        # In production, this should map to actual BIRTH_PLACE_CHOICES
        return place.lower().replace(" ", "_")[:50]

    def _report_results(self, dry_run: bool):
        """Report migration results with comprehensive statistics."""
        mode = "DRY RUN" if dry_run else "MIGRATION"

        self.stdout.write(f"\n📊 {mode} RESULTS:")
        self.stdout.write("   📈 INPUT:")
        self.stdout.write(f"      Total legacy records: {self.stats['total_rows']:,}")
        self.stdout.write(f"      Records processed: {self.stats['total_processed']:,}")

        self.stdout.write("   ✅ OUTPUT (SUCCESSFUL):")
        self.stdout.write(f"      Total successful: {self.stats['total_successful']:,}")
        self.stdout.write(f"      Persons created: {self.stats['persons_created']:,}")
        self.stdout.write(f"      Students created: {self.stats['students_created']:,}")
        self.stdout.write(f"      Emergency contacts: {self.stats['emergency_contacts_created']:,}")
        self.stdout.write(f"      Sponsorships created: {self.stats['sponsorships_created']:,}")

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

            # Show sample rejections
            self.stdout.write("\n   🔍 SAMPLE REJECTIONS:")
            sample_count = 0
            for reason, rejections in self.rejections.items():
                if rejections and sample_count < 3:
                    sample = rejections[0]
                    self.stdout.write(
                        f"      [{reason}] Student {sample['student_id']} ({sample['name']}): {sample['error_details'][:100]}...",
                    )
                    sample_count += 1

        # Calculate success rate
        if self.stats["total_processed"] > 0:
            success_rate = (self.stats["total_successful"] / self.stats["total_processed"]) * 100
            self.stdout.write(f"\n   📊 SUCCESS RATE: {success_rate:.1f}%")

        # Show report file location
        if self.report_file:
            self.stdout.write(f"\n   📋 DETAILED REPORT: {self.report_file}")

        if not dry_run:
            if self.stats["total_rejected"] == 0:
                self.stdout.write(self.style.SUCCESS("\n✅ Migration completed successfully with no rejections!"))
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"\n✅ Migration completed with {self.stats['total_rejected']} rejections. See report for details.",
                    ),
                )
        else:
            self.stdout.write(self.style.SUCCESS("\n✅ Dry run completed - ready for migration!"))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate legacy student data to V1 models")
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

    args = parser.parse_args()

    # Create command instance and run
    command = Command()
    command.handle(dry_run=args.dry_run, batch_size=args.batch_size, limit=args.limit)
