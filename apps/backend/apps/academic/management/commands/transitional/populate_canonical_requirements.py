"""Populate Canonical Requirements for FIN, INT, TOU majors from ba_req.csv

Reads the BA requirements CSV and creates CanonicalRequirement records
for Finance & Banking, International Relations, and Tourism & Hospitality majors.
"""

import csv
from pathlib import Path

from django.db import transaction

from apps.academic.canonical_models import CanonicalRequirement
from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Course, Major, Term


class Command(BaseMigrationCommand):
    """Populate canonical requirements for FIN, INT, TOU majors."""

    help = "Populate canonical requirements for Finance, International Relations, and Tourism majors"

    def get_rejection_categories(self):
        return [
            "missing_major",
            "missing_course",
            "missing_term",
            "duplicate_requirement",
            "database_error",
        ]

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv-file",
            default="data/migrate/ba_req.csv",
            help="Path to BA requirements CSV file (default: data/migrate/ba_req.csv)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be created without actually creating records",
        )

    def execute_migration(self, *args, **options):
        """Execute canonical requirement population."""
        csv_file = options["csv_file"]
        dry_run = options["dry_run"]

        self.stdout.write(f"📊 Populating canonical requirements from {csv_file}")
        if dry_run:
            self.stdout.write("🔍 DRY RUN MODE - No records will be created")

        # Load caches for efficiency
        self._load_caches()

        # Read and process CSV
        csv_path = Path(csv_file)
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_file}")

        requirements_data = self._read_csv_requirements(csv_path)

        self.record_input_stats(
            csv_file=str(csv_path),
            total_courses_in_csv=len(requirements_data),
            target_majors=["FIN-BANK", "IR", "TOUR-HOSP"],
            dry_run=dry_run,
        )

        # Process each major
        majors_to_process = [
            ("fin", "FIN-BANK", "Finance and Banking"),
            ("int", "IR", "International Relations"),
            ("tou", "TOUR-HOSP", "Tourism & Hospitality"),
        ]

        total_created = 0

        for csv_column, major_code, major_name in majors_to_process:
            self.stdout.write(f"\n🎯 Processing {major_name} ({major_code})")

            if not dry_run:
                with transaction.atomic():
                    created_count = self._process_major_requirements(
                        csv_column,
                        major_code,
                        requirements_data,
                        dry_run,
                    )
                    total_created += created_count
            else:
                created_count = self._process_major_requirements(csv_column, major_code, requirements_data, dry_run)
                total_created += created_count

        self.record_success("canonical_requirements_created", total_created)

        if dry_run:
            self.stdout.write(f"\n✅ DRY RUN COMPLETE - Would create {total_created} canonical requirements")
        else:
            self.stdout.write(f"\n✅ Created {total_created} canonical requirements")

    def _load_caches(self):
        """Load data caches for efficient lookup."""
        # Cache courses
        self.course_cache = {course.code: course for course in Course.objects.all()}

        # Cache majors
        self.major_cache = {major.code: major for major in Major.objects.all()}

        # Get default term (will use first term)
        self.default_term = Term.objects.first()
        if not self.default_term:
            raise ValueError("No terms found in database - cannot create canonical requirements")

        self.stdout.write(f"📚 Cached {len(self.course_cache)} courses, {len(self.major_cache)} majors")

    def _read_csv_requirements(self, csv_path):
        """Read CSV file and return requirements data."""
        requirements_data = []

        with open(csv_path, encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                requirements_data.append(row)

        self.stdout.write(f"📄 Read {len(requirements_data)} course requirements from CSV")
        return requirements_data

    def _process_major_requirements(self, csv_column, major_code, requirements_data, dry_run):
        """Process canonical requirements for a single major."""
        # Get the major
        major = self.major_cache.get(major_code)
        if not major:
            self.record_rejection("missing_major", major_code, f"Major {major_code} not found")
            return 0

        # Clear existing canonical requirements for this major if not dry run
        if not dry_run:
            existing_count = CanonicalRequirement.objects.filter(major=major).count()
            if existing_count > 0:
                self.stdout.write(f"🗑️  Clearing {existing_count} existing canonical requirements for {major_code}")
                CanonicalRequirement.objects.filter(major=major).delete()

        # Process each course requirement
        sequence_number = 1
        created_count = 0

        for row in requirements_data:
            course_code = row["code"]
            required = row.get(csv_column, "").strip()

            # Check if this course is required for this major (value of '1')
            if required != "1":
                continue

            # Get the course
            course = self.course_cache.get(course_code)
            if not course:
                self.record_rejection("missing_course", course_code, f"Course {course_code} not found")
                continue

            # Create canonical requirement name
            requirement_name = f"{course_code} - {course.title}"

            if dry_run:
                self.stdout.write(f"  {sequence_number:2d}. Would create: {requirement_name}")
                created_count += 1
                sequence_number += 1
                continue

            # Check for duplicates
            existing = CanonicalRequirement.objects.filter(major=major, required_course=course, is_active=True).first()

            if existing:
                self.record_rejection(
                    "duplicate_requirement",
                    course_code,
                    f"Canonical requirement already exists for {major_code} + {course_code}",
                )
                continue

            try:
                # Create canonical requirement
                canonical_req = CanonicalRequirement.objects.create(
                    major=major,
                    sequence_number=sequence_number,
                    required_course=course,
                    name=requirement_name,
                    description=f"Required course for {major.name} degree program",
                    effective_term=self.default_term,
                    is_active=True,
                    notes=f"Imported from ba_req.csv column '{csv_column}'",
                )

                created_count += 1
                sequence_number += 1
                self.stdout.write(f"  ✅ {canonical_req.sequence_number:2d}. {canonical_req.name}")

            except Exception as e:
                self.record_rejection("database_error", course_code, str(e))

        self.stdout.write(f"📈 {major_code}: {created_count} canonical requirements processed")
        return created_count
