"""Load course data from version 0 courses_clean.json fixture into the V1 system.

This script imports course data from the V0 fixture file into our current V1
curriculum.Course model, preparing for enrollment import.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date

from apps.curriculum.models import Course, Division, Major


class Command(BaseCommand):
    """Load courses from V0 courses_clean.json fixture."""

    help = "Load courses from version 0 courses_clean.json fixture into V1 system"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {
            "courses_created": 0,
            "courses_updated": 0,
            "courses_skipped": 0,
            "errors": 0,
        }
        self.division_cache = {}
        self.major_cache = {}

    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            "--file",
            required=True,
            help="Path to the V0 courses_clean.json fixture file",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without making changes",
        )
        parser.add_argument(
            "--update",
            action="store_true",
            help="Update existing courses if they exist",
        )

    def handle(self, *args, **options):
        """Load courses from V0 fixture file."""
        v0_fixture_path = Path(options["file"])
        dry_run = options["dry_run"]
        update_existing = options["update"]

        if not v0_fixture_path.exists():
            msg = f"V0 courses fixture not found at: {v0_fixture_path}"
            raise CommandError(msg)

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN MODE - No database changes will be made"))

        self.stdout.write(f"📋 Loading courses from: {v0_fixture_path}")

        # Load caches
        self._load_caches()

        # Load and process fixture
        with open(v0_fixture_path) as f:
            course_data = json.load(f)

        for item in course_data:
            if item["model"] != "core.course":
                continue

            try:
                self._process_course(item["fields"], dry_run, update_existing)
            except Exception as e:
                self.stats["errors"] += 1
                self.stdout.write(self.style.ERROR(f"❌ Error processing course {item.get('pk', 'unknown')}: {e}"))

        # Report results
        self._report_results(dry_run)

    def _load_caches(self):
        """Load related data into caches."""
        # Load divisions
        for division in Division.objects.all():
            self.division_cache[division.name.lower()] = division

        # Load majors
        for major in Major.objects.all():
            if major.code:
                self.major_cache[major.code.upper()] = major

        self.stdout.write(f"   📋 Loaded {len(self.division_cache)} divisions, {len(self.major_cache)} majors")

    def _process_course(self, fields: dict, dry_run: bool, update_existing: bool):
        """Process a single course from V0 data."""
        course_code = fields["code"]

        # Parse dates
        parse_date(fields["start_date"]) if fields["start_date"] else None
        parse_date(fields["end_date"]) if fields["end_date"] else None

        # Determine course level based on V0 cycle field
        from typing import Any
        CourseLevel: Any = getattr(Course, "CourseLevel", None)
        cycle_mapping: dict[str, Any] = (
            {
                "LANGUAGE": CourseLevel.LANGUAGE,
                "BA": CourseLevel.BACHELORS,
                "MA": CourseLevel.MASTERS,
            }
            if CourseLevel is not None
            else {"LANGUAGE": "LANGUAGE", "BA": "BA", "MA": "MA"}
        )

        v0_cycle = fields.get("cycle", "LANGUAGE")
        course_level = cycle_mapping.get(v0_cycle, Course.CourseLevel.LANGUAGE)

        # Get or create a default division
        division, _ = Division.objects.get_or_create(
            name=("Language Division" if fields.get("is_language", True) else "Academic Division"),
            defaults={
                "short_name": "LANG" if fields.get("is_language", True) else "ACAD",
                "description": f"Auto-created division for {v0_cycle} courses",
                "is_active": True,
            },
        )

        # Map V0 fields to V1 Course model
        course_data = {
            "code": course_code,
            "title": fields["title"],
            "short_title": fields.get("short_title", "") or "",
            "description": fields.get("notes", "") or "",
            "division": division,
            "cycle": course_level,
            "credits": int(fields.get("credits", 3)),
            "is_language": fields.get("is_language", False),
            "is_foundation_year": fields.get("is_foundation_year", False),
        }

        if dry_run:
            action = "CREATE"
            if Course.objects.filter(code=course_code).exists():
                action = "UPDATE" if update_existing else "SKIP"

            self.stdout.write(
                f"   📝 {action}: {course_code} - {fields['title']} "
                f"({fields.get('credits', 0)} credits, "
                f"{'Language' if fields.get('is_language') else 'Academic'})",
            )

            if action == "CREATE":
                self.stats["courses_created"] += 1
            elif action == "UPDATE":
                self.stats["courses_updated"] += 1
            else:
                self.stats["courses_skipped"] += 1
            return

        # Create or update course
        course, created = Course.objects.get_or_create(code=course_code, defaults=course_data)

        if created:
            self.stats["courses_created"] += 1
            self.stdout.write(f"   ✅ Created: {course.code} - {course.title} ({course.credits} credits)")
        elif update_existing:
            # Update existing course
            for field, value in course_data.items():
                setattr(course, field, value)
            course.save()
            self.stats["courses_updated"] += 1
            self.stdout.write(f"   🔄 Updated: {course.code} - {course.title}")
        else:
            self.stats["courses_skipped"] += 1
            self.stdout.write(f"   ⏭️  Skipped: {course.code} (already exists)")

    def _report_results(self, dry_run: bool):
        """Report course loading results."""
        mode = "DRY RUN" if dry_run else "LOADING"

        self.stdout.write(f"\n📊 {mode} RESULTS:")
        self.stdout.write(f"   Courses created: {self.stats['courses_created']:,}")
        self.stdout.write(f"   Courses updated: {self.stats['courses_updated']:,}")
        self.stdout.write(f"   Courses skipped: {self.stats['courses_skipped']:,}")
        self.stdout.write(f"   Errors: {self.stats['errors']:,}")

        total_processed = self.stats["courses_created"] + self.stats["courses_updated"] + self.stats["courses_skipped"]
        self.stdout.write(f"   Total processed: {total_processed:,}")

        # Verify total courses in system
        if not dry_run:
            total_courses = Course.objects.count()
            self.stdout.write(f"\n📋 Total courses now in system: {total_courses:,}")

        if not dry_run and self.stats["errors"] == 0:
            self.stdout.write(self.style.SUCCESS("\n✅ Course loading completed successfully!"))
        elif dry_run:
            self.stdout.write(self.style.SUCCESS("\n✅ Dry run completed - ready for course loading!"))
        else:
            self.stdout.write(self.style.WARNING(f"\n⚠️  Course loading completed with {self.stats['errors']} errors"))
