"""Create canonical requirements for BA TESOL major from BA-TESOL.csv.

This migration script creates canonical requirements for the BA TESOL major,
validating that all courses exist as active courses.
"""

import csv

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.academic.canonical_models import CanonicalRequirement
from apps.common.management.base_migration import BaseMigrationCommand
from apps.curriculum.models import Course, Major, Term

User = get_user_model()


class Command(BaseMigrationCommand):
    """Create canonical requirements for BA TESOL major from BA-TESOL.csv."""

    help = "Create canonical requirements for BA TESOL major from BA-TESOL.csv"

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
        # Load BA-TESOL.csv
        csv_path = "data/legacy/BA-TESOL.csv"
        current_date = timezone.now().date()

        # Record input statistics
        self.record_input_stats(total_records=42, source_file=csv_path)

        # Get TESOL major
        try:
            major = Major.objects.get(code="TESOL")
            self.record_success("major_found", 1)
            self.stdout.write(f"TESOL major found: {major.name}")
        except Major.DoesNotExist:
            self.record_rejection("major_not_found", "TESOL", "TESOL major not found")
            return

        # Get current term (or create a default one)
        current_term = self.get_current_term()
        if not current_term:
            self.record_rejection("term_not_found", "current", "No current term found")
            return

        # Process each course requirement
        sequence = 1
        total_credits = 0
        requirements_created = 0

        try:
            with open(csv_path, encoding="utf-8-sig") as file:
                reader = csv.reader(file)
                for row in reader:
                    if not row or not row[0].strip():
                        continue

                    course_code = row[0].strip()

                    # Get ACTIVE course only
                    active_courses = Course.objects.filter(
                        code=course_code,
                        is_active=True,
                        start_date__lte=current_date,
                    )

                    # Filter out courses that have ended
                    active_courses = active_courses.filter(
                        models.Q(end_date__isnull=True) | models.Q(end_date__gte=current_date),
                    )

                    if not active_courses.exists():
                        self.record_rejection(
                            "course_not_found",
                            course_code,
                            f"No active course found for {course_code} on {current_date}",
                        )
                        sequence += 1
                        continue

                    if active_courses.count() > 1:
                        self.record_rejection(
                            "multiple_active_courses",
                            course_code,
                            f"Multiple active courses found for {course_code} - validation failure",
                        )
                        sequence += 1
                        continue

                    # Get the single active course
                    course = active_courses.first()

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

        except FileNotFoundError:
            self.record_rejection("missing_data", csv_path, f"CSV file not found: {csv_path}")
            return
        except Exception as e:
            self.record_rejection("missing_data", csv_path, f"Error reading CSV: {e!s}")
            return

        # Record final success stats
        self.record_success("total_requirements_created", requirements_created)
        self.record_success("total_credits_calculated", total_credits)

        # Special validation for COMP-210 (if it exists in TESOL)
        comp210_req = CanonicalRequirement.objects.filter(major=major, required_course__code="COMP-210").first()

        if comp210_req:
            self.record_success("comp210_validation", 1)
            self.stdout.write(f"COMP-210 credits: {comp210_req.required_course.credits}")

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
