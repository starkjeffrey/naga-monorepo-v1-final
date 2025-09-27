"""Import staff data from CSV into User accounts and StaffProfile records.

This script imports staff data into two locations:
1. users.User - for official school email authentication accounts
2. people.Person + people.StaffProfile - for staff information and profiles

The script follows the clean architecture pattern and creates comprehensive
audit reports for all import operations.
"""

import csv
from datetime import date
from pathlib import Path

from django.contrib.auth import get_user_model
from django.db import transaction

from apps.accounts.models import Department
from apps.common.management.base_migration import BaseMigrationCommand
from apps.people.models import Person, StaffProfile

User = get_user_model()


class Command(BaseMigrationCommand):
    """Import staff data from CSV into User accounts and StaffProfile records."""

    help = "Import staff data from CSV into User accounts and StaffProfile records"

    def get_rejection_categories(self):
        return [
            "missing_email",
            "invalid_email",
            "duplicate_email",
            "missing_name",
            "missing_department",
            "invalid_phone",
            "database_error",
            "person_creation_failed",
            "user_creation_failed",
            "staff_profile_creation_failed",
        ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            default="data/migrate/staff.csv",
            help="Path to staff CSV file (default: data/migrate/staff.csv)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be imported without creating records",
        )
        parser.add_argument(
            "--default-start-date",
            default="2020-01-01",
            help="Default employment start date for staff (YYYY-MM-DD)",
        )

    def execute_migration(self, *args, **options):
        """Execute staff data import."""
        csv_file = options["csv_file"]
        dry_run = options["dry_run"]
        default_start_date = options["default_start_date"]

        self.stdout.write(f"📊 Importing staff data from {csv_file}")
        if dry_run:
            self.stdout.write("🔍 DRY RUN MODE - No records will be created")

        # Load caches for efficiency
        self._load_caches()

        # Read and process CSV
        csv_path = Path(csv_file)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")

        staff_data = self._read_csv_staff(csv_path)

        self.record_input_stats(
            csv_file=str(csv_path),
            total_staff_records=len(staff_data),
            default_start_date=default_start_date,
            dry_run=dry_run,
        )

        # Process each staff member
        created_users = 0
        created_persons = 0
        created_staff_profiles = 0

        for row_num, staff_record in enumerate(staff_data, start=2):  # Start at 2 for CSV line numbers
            self.stdout.write(f"\n🔄 Processing row {row_num}: {staff_record.get('Name', 'Unknown')}")

            if not dry_run:
                with transaction.atomic():
                    result = self._process_staff_record(staff_record, default_start_date, dry_run)
                    if result:
                        created_users += result.get("user_created", 0)
                        created_persons += result.get("person_created", 0)
                        created_staff_profiles += result.get("staff_profile_created", 0)
            else:
                result = self._process_staff_record(staff_record, default_start_date, dry_run)
                if result:
                    created_users += result.get("user_created", 0)
                    created_persons += result.get("person_created", 0)
                    created_staff_profiles += result.get("staff_profile_created", 0)

        # Record success metrics
        self.record_success("users_created", created_users)
        self.record_success("persons_created", created_persons)
        self.record_success("staff_profiles_created", created_staff_profiles)

        if dry_run:
            self.stdout.write("\n✅ DRY RUN COMPLETE")
            self.stdout.write(f"   Would create {created_users} user accounts")
            self.stdout.write(f"   Would create {created_persons} person records")
            self.stdout.write(f"   Would create {created_staff_profiles} staff profiles")
        else:
            self.stdout.write("\n✅ IMPORT COMPLETE")
            self.stdout.write(f"   Created {created_users} user accounts")
            self.stdout.write(f"   Created {created_persons} person records")
            self.stdout.write(f"   Created {created_staff_profiles} staff profiles")

    def _load_caches(self):
        """Load data caches for efficient lookup."""
        # Cache departments
        self.department_cache = {dept.name: dept for dept in Department.objects.all()}

        # Create default departments if they don't exist
        default_departments = [
            ("Admin", "ADMIN"),
            ("HR", "HUMAN_RESOURCES"),
            ("Language", "LANG"),
            ("Enrolment", "ENROLL"),
            ("Security", "SEC"),
            ("Bookstore", "BOOKS"),
            ("Academic", "ACAD"),
            ("Finance", "FIN"),
            ("Testing", "TEST"),
            ("Library", "LIB"),
            ("Maintenance", "MAINT"),
        ]

        for dept_name, dept_code in default_departments:
            if dept_name not in self.department_cache:
                try:
                    dept, created = Department.objects.get_or_create(
                        name=dept_name,
                        defaults={"code": dept_code, "is_active": True},
                    )
                    self.department_cache[dept_name] = dept
                    if created:
                        self.stdout.write(f"📁 Created department: {dept_name} ({dept_code})")
                except Exception as e:
                    # Try to find existing department by name
                    existing_dept = Department.objects.filter(name=dept_name).first()
                    if existing_dept:
                        self.department_cache[dept_name] = existing_dept
                        self.stdout.write(f"📁 Found existing department: {dept_name}")
                    else:
                        self.stdout.write(f"⚠️  Could not create department {dept_name}: {e}")

        self.stdout.write(f"📚 Cached {len(self.department_cache)} departments")

    def _read_csv_staff(self, csv_path):
        """Read CSV file and return staff data."""
        staff_data = []

        with open(csv_path, encoding="utf-8-sig") as csvfile:  # utf-8-sig handles BOM
            reader = csv.DictReader(csvfile)
            for row in reader:
                # Clean empty columns
                cleaned_row = {k: v.strip() if v else "" for k, v in row.items() if k}
                staff_data.append(cleaned_row)

        self.stdout.write(f"📄 Read {len(staff_data)} staff records from CSV")
        return staff_data

    def _process_staff_record(self, staff_record, default_start_date, dry_run):
        """Process a single staff record."""
        # Extract data from CSV
        name = staff_record.get("Name", "").strip()
        position = staff_record.get("Position", "").strip()
        phone = staff_record.get("Phone", "").strip()
        staff_record.get("Department", "").strip()
        email = staff_record.get("email", "").strip()

        # Validate required fields
        if not email:
            self.record_rejection("missing_email", name, "No email address provided")
            return None

        if not name:
            self.record_rejection("missing_name", email, "No name provided")
            return None

        # Validate email format
        if "@" not in email or not email.endswith("@pucsr.edu.kh"):
            self.record_rejection("invalid_email", email, f"Invalid email format: {email}")
            return None

        # Check what already exists
        existing_user = User.objects.filter(email=email).first()
        existing_person = Person.objects.filter(school_email=email).first()
        existing_staff = None

        if existing_person:
            existing_staff = StaffProfile.objects.filter(person=existing_person).first()

        # Determine what needs to be created
        needs_user = not existing_user
        needs_person = not existing_person
        needs_staff_profile = not existing_staff

        # If everything exists, skip
        if existing_user and existing_person and existing_staff:
            self.record_rejection(
                "duplicate_email",
                email,
                f"Complete staff record already exists: {email}",
            )
            return None

        # Parse name into family and personal names
        name_parts = name.split(" ", 1)
        family_name = name_parts[0] if name_parts else name
        personal_name = name_parts[1] if len(name_parts) > 1 else ""

        # Clean phone number
        phone.replace(" ", "").replace("-", "") if phone else ""

        if dry_run:
            parts = []
            if needs_user:
                parts.append("User")
            if needs_person:
                parts.append("Person")
            if needs_staff_profile:
                parts.append("StaffProfile")
            self.stdout.write(f"  ✅ Would create {', '.join(parts)}: {name} ({email})")
            return {
                "user_created": 1 if needs_user else 0,
                "person_created": 1 if needs_person else 0,
                "staff_profile_created": 1 if needs_staff_profile else 0,
            }

        try:
            person = existing_person

            # Create User account if needed
            if needs_user:
                User.objects.create_user(
                    email=email,
                    name=name,
                    password=None,  # Password will be set via password reset
                    is_active=True,
                    is_staff=True,  # All staff get Django admin access
                )

            # Create Person record if needed
            if needs_person:
                person = Person.objects.create(
                    family_name=family_name,
                    personal_name=personal_name,
                    school_email=email,
                    citizenship="KH",  # Default to Cambodia
                )

            # Create StaffProfile if needed
            if needs_staff_profile:
                StaffProfile.objects.create(
                    person=person,
                    position=position or "Staff",
                    status=StaffProfile.Status.ACTIVE,
                    start_date=date.fromisoformat(default_start_date),
                )

            parts = []
            if needs_user:
                parts.append("User")
            if needs_person:
                parts.append("Person")
            if needs_staff_profile:
                parts.append("StaffProfile")
            self.stdout.write(f"  ✅ Created {', '.join(parts)}: {name} ({email})")

            return {
                "user_created": 1 if needs_user else 0,
                "person_created": 1 if needs_person else 0,
                "staff_profile_created": 1 if needs_staff_profile else 0,
            }

        except Exception as e:
            self.record_rejection("database_error", email, str(e))
            return None

    def _get_or_create_department(self, department_name):
        """Get or create department record."""
        if not department_name:
            return None

        if department_name in self.department_cache:
            return self.department_cache[department_name]

        # Create new department
        dept, created = Department.objects.get_or_create(
            name=department_name,
            defaults={"code": department_name.upper()[:20], "is_active": True},
        )
        self.department_cache[department_name] = dept

        if created:
            self.stdout.write(f"📁 Created new department: {department_name}")

        return dept
