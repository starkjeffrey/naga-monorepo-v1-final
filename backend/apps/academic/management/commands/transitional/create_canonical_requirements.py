"""Create canonical requirements for any major from a CSV file.

This unified migration script creates canonical requirements for any major,
validating that all courses exist as active courses. It replaces the individual
per-major commands and includes N+1 query optimization.
"""

import csv
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management.base import CommandError
from django.db import models
from django.utils import timezone

from apps.academic.canonical_models import CanonicalRequirement
from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Course, Major, Term

User = get_user_model()


class Command(BaseMigrationCommand):
    """Create canonical requirements for a major from a CSV file."""

    help = "Create canonical requirements for a major from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("major_code", type=str, help="The code for the major (e.g., BUSADMIN, TESOL)")
        parser.add_argument("csv_path", type=str, help="The path to the CSV file containing course codes")
        parser.add_argument(
            "--expected-credits", type=int, help="Expected total credits (optional, for validation)", default=None
        )
        parser.add_argument(
            "--expected-records", type=int, help="Expected number of records (optional, for validation)", default=None
        )

    def get_rejection_categories(self):
        """Define categories for rejected records."""
        return [
            "course_not_found",
            "course_inactive",
            "multiple_active_courses",
            "major_not_found",
            "term_not_found",
            "duplicate_requirement",
            "invalid_sequence",
            "missing_data",
            "credit_mismatch",
            "validation_error",
        ]

    def execute_migration(self, *args, **options):
        """Execute the migration to create canonical requirements."""
        major_code = options["major_code"]
        csv_path = options["csv_path"]
        expected_credits = options.get("expected_credits")
        expected_records = options.get("expected_records")

        current_date = timezone.now().date()

        # Validate CSV file exists
        if not Path(csv_path).exists():
            raise CommandError(f"CSV file not found: {csv_path}")

        # Record input statistics
        stats_dict = {
            "source_file": csv_path,
            "major_code": major_code,
        }
        if expected_records:
            stats_dict["expected_records"] = expected_records
        if expected_credits:
            stats_dict["expected_credits"] = expected_credits

        self.record_input_stats(**stats_dict)

        # Get major
        try:
            major = Major.objects.get(code=major_code)
            self.record_success("major_found", 1)
            self.stdout.write(f"{major_code} major found: {major.name}")
        except Major.DoesNotExist:
            self.record_rejection("major_not_found", major_code, f"{major_code} major not found")
            raise CommandError(f"Major with code '{major_code}' not found") from None

        # Get current term (or create a default one)
        current_term = self.get_current_term()
        if not current_term:
            self.record_rejection("term_not_found", "current", "No current term found")
            raise CommandError("No current term found")

        # Get system user for created_by
        self.get_system_user()

        # OPTIMIZATION: Read all course codes from CSV first
        self.stdout.write("Reading course codes from CSV...")
        course_codes_from_csv = []

        try:
            with open(csv_path, encoding="utf-8-sig") as file:
                reader = csv.reader(file)
                for row in reader:
                    if row and row[0].strip():
                        course_codes_from_csv.append(row[0].strip())
        except FileNotFoundError:
            self.record_rejection("missing_data", csv_path, f"CSV file not found: {csv_path}")
            raise CommandError(f"CSV file not found: {csv_path}") from None
        except Exception as e:
            self.record_rejection("missing_data", csv_path, f"Error reading CSV: {e!s}")
            raise CommandError(f"Error reading CSV: {e!s}") from e

        if not course_codes_from_csv:
            raise CommandError("No course codes found in CSV file")

        self.stdout.write(f"Found {len(course_codes_from_csv)} course codes in CSV")

        # OPTIMIZATION: Fetch all relevant courses in a SINGLE query
        self.stdout.write("Fetching all courses from database...")
        courses_from_db = Course.objects.filter(
            code__in=course_codes_from_csv,
            is_active=True,
            start_date__lte=current_date,
        ).filter(models.Q(end_date__isnull=True) | models.Q(end_date__gte=current_date))

        # Create a dictionary for fast lookups
        course_cache = {}
        for course in courses_from_db:
            if course.code not in course_cache:
                course_cache[course.code] = []
            course_cache[course.code].append(course)

        self.stdout.write(f"Found {len(course_cache)} unique course codes in database")

        # Process using the cache (no more DB queries in the loop)
        sequence = 1
        total_credits = 0
        requirements_created = 0

        for course_code in course_codes_from_csv:
            courses = course_cache.get(course_code, [])

            if not courses:
                self.record_rejection(
                    "course_not_found",
                    course_code,
                    f"No active course found for {course_code} on {current_date}",
                )
                sequence += 1
                continue

            if len(courses) > 1:
                self.record_rejection(
                    "multiple_active_courses",
                    course_code,
                    f"Multiple active courses found for {course_code} - validation failure",
                )
                sequence += 1
                continue

            # Get the single active course
            course = courses[0]

            # Create canonical requirement with FK to course
            try:
                _canonical_req, created = CanonicalRequirement.objects.get_or_create(
                    major=major,
                    required_course=course,  # FK to Course model
                    sequence_number=sequence,
                    defaults={
                        "effective_term": current_term,
                        "name": f"{course.code} - {course.title}",
                        "is_active": True,
                    },
                )

                if created:
                    total_credits += course.credits  # Use course.credits via FK
                    requirements_created += 1
                    self.record_success("requirement_created", 1)
                    self.stdout.write(f"{course_code} (seq {sequence}): {course.credits} credits")
                else:
                    self.record_rejection(
                        "duplicate_requirement",
                        course_code,
                        f"Canonical requirement already exists for {course_code}",
                    )

            except ValidationError as e:
                self.record_rejection("validation_error", course_code, f"Validation error: {e!s}")

            sequence += 1

        # Validate total credits if expected
        if expected_credits is not None:
            if total_credits != expected_credits:
                self.record_rejection(
                    "credit_mismatch",
                    f"Total: {total_credits}",
                    f"Expected {expected_credits} credits, got {total_credits}",
                )
                self.stdout.write(
                    self.style.WARNING(f"Credit mismatch: expected {expected_credits}, got {total_credits}")
                )
            else:
                self.record_success("credit_validation_passed", 1)
                self.stdout.write(f"Total credits validation passed: {total_credits}")

        # Validate record count if expected
        if expected_records is not None:
            if requirements_created != expected_records:
                self.stdout.write(
                    self.style.WARNING(
                        f"Record count mismatch: expected {expected_records}, created {requirements_created}"
                    )
                )

        # Record final success stats
        self.record_success("total_requirements_created", requirements_created)
        self.record_success("total_credits_calculated", total_credits)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created {requirements_created} canonical requirements for {major.name} "
                f"totaling {total_credits} credits",
            ),
        )

    def get_current_term(self):
        """Get current active term or the most recent one."""
        try:
            # Try to get current active term
            return Term.objects.filter(is_active=True).first()
        except Term.DoesNotExist:
            pass

        try:
            # Fallback to most recent term
            return Term.objects.order_by("-start_date").first()
        except Term.DoesNotExist:
            return None
