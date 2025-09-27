"""Management command to import legacy Moodle CSV data into PostgreSQL.

This command imports the all_moo.csv file into the legacy_moo table,

providing a foundation for analysis and migration to the new API-based

Moodle integration system.
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.common.integrations.moodle.legacy_models import LegacyMoodleMapping


class Command(BaseCommand):
    help = "Import legacy Moodle CSV data (all_moo.csv) into PostgreSQL legacy_moo table"

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            type=str,
            default="data/legacy/all_moo.csv",
            help="Path to the all_moo.csv file",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without saving to database",
        )

        parser.add_argument(
            "--clear-existing",
            action="store_true",
            help="Clear existing legacy_moo data before importing",
        )

        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Number of records to process in each batch",
        )

        parser.add_argument(
            "--progress-every",
            type=int,
            default=5000,
            help="Show progress every N records",
        )

    def handle(self, *args, **options):
        csv_path = options["csv"]

        dry_run = options["dry_run"]

        clear_existing = options["clear_existing"]

        batch_size = options["batch_size"]

        progress_every = options["progress_every"]

        if not Path(csv_path).exists():
            msg = f"CSV file not found: {csv_path}"

            raise CommandError(msg)

        self.stdout.write(f"Starting import from {csv_path}")

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN MODE ---"))

        # Clear existing data if requested

        if clear_existing and not dry_run:
            count = LegacyMoodleMapping.objects.count()

            if count > 0:
                self.stdout.write(f"Clearing {count} existing records...")

                LegacyMoodleMapping.objects.all().delete()

                self.stdout.write(self.style.SUCCESS("Existing data cleared"))

        # Count total rows for progress tracking

        with Path(csv_path).open(encoding="utf-8") as file:
            total_rows = sum(1 for _ in csv.reader(file)) - 1  # Subtract header

        self.stdout.write(f"Total rows to process: {total_rows}")

        # Process the CSV file

        processed = 0

        created = 0

        updated = 0

        errors = 0

        batch_records = []

        try:
            with Path(csv_path).open(encoding="utf-8") as file:
                reader = csv.DictReader(file)

                for row_num, row in enumerate(reader, 1):
                    try:
                        # Clean and prepare the data

                        record_data = self._prepare_record_data(row, row_num)

                        if dry_run:
                            # In dry run, just show what would be created

                            self._display_dry_run_record(record_data, row_num)

                        else:
                            batch_records.append(record_data)

                            # Process batch when it reaches batch_size

                            if len(batch_records) >= batch_size:
                                batch_created, batch_updated, batch_errors = self._process_batch(batch_records)

                                created += batch_created

                                updated += batch_updated

                                errors += batch_errors

                                batch_records = []

                        processed += 1

                        # Show progress

                        if processed % progress_every == 0:
                            progress_pct = (processed / total_rows) * 100

                            self.stdout.write(
                                f"Progress: {processed}/{total_rows} ({progress_pct:.1f}%) - "
                                f"Created: {created}, Updated: {updated}, Errors: {errors}",
                            )

                    except Exception as e:
                        self.stderr.write(f"Error processing row {row_num}: {e}")

                        errors += 1

                # Process remaining batch

                if batch_records and not dry_run:
                    batch_created, batch_updated, batch_errors = self._process_batch(batch_records)

                    created += batch_created

                    updated += batch_updated

                    errors += batch_errors

        except Exception as e:
            msg = f"Error reading CSV file: {e}"

            raise CommandError(msg) from e

        # Final summary

        self.stdout.write("\n--- Import Summary ---")

        self.stdout.write(f"Total rows processed: {processed}")

        self.stdout.write(f"Records created: {created}")

        self.stdout.write(f"Records updated: {updated}")

        self.stdout.write(f"Errors: {errors}")

        if not dry_run:
            # Generate analysis report

            self._generate_analysis_report()

        if dry_run:
            self.stdout.write(self.style.WARNING("--- DRY RUN COMPLETE ---"))

        else:
            self.stdout.write(self.style.SUCCESS("--- Import Complete ---"))

    def _prepare_record_data(self, row: dict[str, str], row_num: int) -> dict[str, any]:
        """Clean and prepare record data from CSV row."""
        # Handle NULL values and clean data

        def clean_value(value):
            if not value or value.upper() == "NULL":
                return ""

            return value.strip()

        return {
            "classid": clean_value(row.get("classid", "")),
            "coursecode": clean_value(row.get("coursecode", "")),
            "termid": clean_value(row.get("termid", "")),
            "combo": clean_value(row.get("combo", "")),
            "instructor": clean_value(row.get("instructor", "")),
            "moodleclass": clean_value(row.get("moodleclass", "")),
            "groupinmoodle": clean_value(row.get("groupinmoodle", "")),
            "shared": clean_value(row.get("shared", "")),
            "shortcoursetitle": clean_value(row.get("shortcoursetitle", "")),
            "zoom": clean_value(row.get("zoom", "")),
            "sharedacl": clean_value(row.get("sharedacl", "")),
            "zoomacl": clean_value(row.get("zoomacl", "")),
            "groupname": clean_value(row.get("groupname", "")),
            "weight": clean_value(row.get("weight", "")),
            "parent": clean_value(row.get("parent", "")),
            "template": clean_value(row.get("template", "")),
            "ipk": clean_value(row.get("IPK", "")),  # Note: uppercase in CSV
        }

    def _display_dry_run_record(self, record_data: dict[str, any], row_num: int):
        """Display record information in dry run mode."""
        classid = record_data["classid"]

        moodleclass = record_data["moodleclass"]

        instructor = record_data["instructor"]

        self.stdout.write(f"Row {row_num}: {classid} -> {moodleclass} (Instructor: {instructor})")

    def _process_batch(self, batch_records: list[dict[str, any]]) -> tuple[int, int, int]:
        """Process a batch of records."""
        created = 0

        updated = 0

        errors = 0

        with transaction.atomic():
            for record_data in batch_records:
                try:
                    classid = record_data["classid"]

                    if not classid:
                        errors += 1

                        continue

                    # Check if record already exists

                    existing = LegacyMoodleMapping.objects.filter(classid=classid).first()

                    if existing:
                        # Update existing record

                        for field, value in record_data.items():
                            setattr(existing, field, value)

                        existing.save()

                        updated += 1

                    else:
                        # Create new record

                        LegacyMoodleMapping.objects.create(**record_data)

                        created += 1

                except Exception as e:
                    self.stderr.write(f"Error saving record {record_data.get('classid', 'unknown')}: {e}")

                    errors += 1

        return created, updated, errors

    def _generate_analysis_report(self):
        """Generate analysis report of imported data."""
        self.stdout.write("\n--- Analysis Report ---")

        total_records = LegacyMoodleMapping.objects.count()

        self.stdout.write(f"Total records imported: {total_records}")

        # Unique terms

        unique_terms = LegacyMoodleMapping.objects.values("termid").distinct().count()

        self.stdout.write(f"Unique terms: {unique_terms}")

        # Unique Moodle courses

        unique_moodle_courses = (
            LegacyMoodleMapping.objects.exclude(moodleclass="").values("moodleclass").distinct().count()
        )

        self.stdout.write(f"Unique Moodle courses: {unique_moodle_courses}")

        # Combined courses

        combined_courses = LegacyMoodleMapping.objects.filter(is_combined_course=True).count()

        self.stdout.write(f"Combined courses: {combined_courses}")

        # Records with groups

        with_groups = LegacyMoodleMapping.objects.filter(has_group=True).count()

        self.stdout.write(f"Records with groups: {with_groups}")

        # Unique instructors

        unique_instructors = LegacyMoodleMapping.objects.exclude(instructor="").values("instructor").distinct().count()

        self.stdout.write(f"Unique instructors: {unique_instructors}")

        # Language vs Academic courses

        language_courses = (
            LegacyMoodleMapping.objects.filter(coursecode__startswith="GESL").count()
            + LegacyMoodleMapping.objects.filter(coursecode__startswith="IEAP").count()
            + LegacyMoodleMapping.objects.filter(coursecode__startswith="EHSS").count()
        )

        academic_courses = (
            LegacyMoodleMapping.objects.filter(coursecode__startswith="ACCT").count()
            + LegacyMoodleMapping.objects.filter(coursecode__startswith="BUS").count()
            + LegacyMoodleMapping.objects.filter(coursecode__startswith="ECON").count()
        )

        self.stdout.write(f"Language courses: {language_courses}")

        self.stdout.write(f"Academic courses: {academic_courses}")

        # Top 10 most common Moodle courses

        self.stdout.write("\nTop 10 Moodle courses by usage:")

        top_courses = (
            LegacyMoodleMapping.objects.exclude(moodleclass="")
            .values("moodleclass")
            .annotate(count=models.Count("id"))
            .order_by("-count")[:10]
        )

        for course in top_courses:
            self.stdout.write(f"  {course['moodleclass']}: {course['count']} classes")

        # Historical teaching data

        self.stdout.write("\nInstructor teaching history:")

        instructor_stats = (
            LegacyMoodleMapping.objects.exclude(instructor="")
            .values("instructor")
            .annotate(
                class_count=models.Count("id"),
                course_count=models.Count("coursecode", distinct=True),
                term_count=models.Count("termid", distinct=True),
            )
            .order_by("-class_count")[:10]
        )

        for stat in instructor_stats:
            self.stdout.write(
                f"  {stat['instructor']}: {stat['class_count']} classes, "
                f"{stat['course_count']} courses, {stat['term_count']} terms",
            )


# Import Count for the analysis queries

from django.db import models
