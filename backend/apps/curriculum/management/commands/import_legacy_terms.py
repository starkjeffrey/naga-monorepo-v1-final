"""
Import legacy terms from CSV file into the curriculum Term model.

This command imports term data from the legacy system CSV export,
mapping legacy fields to the current Term model structure.
"""

import csv
import logging
from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.curriculum.models import Term

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import legacy terms from CSV file"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            help="Path to the CSV file containing legacy term data",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without making changes",
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="Update existing terms if they already exist",
        )

    def handle(self, *args, **options):
        csv_file = options["csv_file"]
        dry_run = options["dry_run"]
        update_existing = options["update_existing"]

        self.stdout.write(f"Importing terms from {csv_file}")
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        try:
            with open(csv_file, encoding="utf-8") as f:
                self._import_terms(f, dry_run, update_existing)
        except FileNotFoundError as err:
            raise CommandError(f"CSV file not found: {csv_file}") from err
        except Exception as e:
            raise CommandError(f"Error importing terms: {e}") from e

    def _import_terms(self, csv_file, dry_run: bool, update_existing: bool):
        """Import terms from CSV file."""
        reader = csv.DictReader(csv_file)

        # Validate CSV headers
        required_fields = ["TermID", "TermName", "StartDate", "EndDate", "TermType"]
        missing_fields = [field for field in required_fields if field not in reader.fieldnames]
        if missing_fields:
            raise CommandError(f"Missing required CSV fields: {missing_fields}")

        stats = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": 0,
        }

        with transaction.atomic():
            for row_num, row in enumerate(reader, start=2):  # Start at 2 since CSV has header
                try:
                    result = self._process_term_row(row, dry_run, update_existing)
                    stats[result] += 1

                    if row_num % 50 == 0:
                        self.stdout.write(f"Processed {row_num - 1} rows...")

                except Exception as e:
                    stats["errors"] += 1
                    self.stdout.write(self.style.ERROR(f"Error processing row {row_num}: {e}"))
                    self.stdout.write(f"Row data: {row}")

            if dry_run:
                # Roll back the transaction in dry run mode
                transaction.set_rollback(True)

        # Print summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("IMPORT SUMMARY")
        self.stdout.write("=" * 50)
        for status, count in stats.items():
            style = self.style.SUCCESS if status in ["created", "updated"] else self.style.WARNING
            if status == "errors":
                style = self.style.ERROR
            self.stdout.write(style(f"{status.title()}: {count}"))

    def _process_term_row(self, row: dict, dry_run: bool, update_existing: bool) -> str:
        """Process a single term row from CSV."""
        # Extract and clean data
        term_id = row["TermID"].strip()
        term_name = row["TermName"].strip()
        start_date_str = row["StartDate"].strip()
        end_date_str = row["EndDate"].strip()
        term_type_str = row["TermType"].strip()
        description = row.get("Desp", "").strip()

        # Parse dates
        start_date = self._parse_date(start_date_str)
        end_date = self._parse_date(end_date_str)

        # Map term type from legacy to current choices
        term_type = self._map_term_type(term_type_str)

        # Parse optional dates
        add_date = self._parse_optional_date(row.get("AddDate"))
        drop_date = self._parse_optional_date(row.get("DropDate"))
        ldp_date = self._parse_optional_date(row.get("LDPDate"))  # Last Day to Pay -> payment deadline

        # Check if term already exists
        existing_term = Term.objects.filter(code=term_id).first()

        if existing_term:
            if not update_existing:
                self.stdout.write(f"Skipping existing term: {term_id}")
                return "skipped"

            # Update existing term
            if not dry_run:
                existing_term.description = description or term_name
                existing_term.term_type = term_type
                existing_term.start_date = start_date
                existing_term.end_date = end_date
                existing_term.add_date = add_date
                existing_term.drop_date = drop_date
                existing_term.payment_deadline_date = ldp_date
                existing_term.save()

            self.stdout.write(f"Updated term: {term_id}")
            return "updated"

        # Create new term
        if not dry_run:
            Term.objects.create(
                code=term_id,
                description=description or term_name,
                term_type=term_type,
                start_date=start_date,
                end_date=end_date,
                add_date=add_date,
                drop_date=drop_date,
                payment_deadline_date=ldp_date,
                is_active=True,
            )

        self.stdout.write(f"Created term: {term_id}")
        return "created"

    def _parse_date(self, date_str: str) -> date:
        """Parse date string from CSV."""
        if not date_str or date_str.upper() == "NULL":
            raise ValueError("Date is required")

        try:
            # Handle format: 2025-07-01 00:00:00.000
            if " " in date_str:
                date_str = date_str.split(" ")[0]
            return datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            try:
                # Try alternative format
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError as e:
                raise ValueError(f"Could not parse date '{date_str}': {e}") from e

    def _parse_optional_date(self, date_str: str | None) -> date | None:
        """Parse optional date string from CSV."""
        if not date_str or date_str.upper() == "NULL" or date_str == "1900-01-01 00:00:00.000":
            return None

        try:
            return self._parse_date(date_str)
        except ValueError:
            return None

    def _map_term_type(self, legacy_type: str) -> str:
        """Map legacy term type to current Term.TermType choices."""
        legacy_type = legacy_type.strip().upper()

        type_mapping = {
            "ENG A": Term.TermType.ENGLISH_A,
            "ENG B": Term.TermType.ENGLISH_B,
            "BA": Term.TermType.BACHELORS,
            "MA": Term.TermType.MASTERS,
            "X": Term.TermType.SPECIAL,
        }

        mapped_type = type_mapping.get(legacy_type)
        if not mapped_type:
            raise ValueError(f"Unknown term type: {legacy_type}")

        return mapped_type
