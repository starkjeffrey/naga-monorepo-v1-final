"""Management command to import terms from CSV into curriculum.Term model."""

import contextlib
import csv
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_date

from apps.curriculum.models import Term


class Command(BaseCommand):
    """Import terms from CSV file into Term model."""

    help = "Import terms from CSV file into curriculum.Term model"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="data/migrate/all_terms_250714.csv",
            help="Path to the CSV file with terms data",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be imported without actually importing",
        )
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing terms before importing",
        )

    def handle(self, *args, **options):
        csv_file = options["file"]
        dry_run = options["dry_run"]
        clear = options["clear"]

        self.stdout.write(f"📄 Reading terms from: {csv_file}")

        try:
            with open(csv_file) as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"❌ File not found: {csv_file}"))
            return

        self.stdout.write(f"📋 Found {len(rows)} terms to process")

        if dry_run:
            self.stdout.write(self.style.WARNING("🔍 DRY RUN - No changes will be made"))

        if clear and not dry_run:
            Term.objects.all().delete()
            self.stdout.write("🗑️  Cleared existing terms")

        created = 0
        updated = 0
        errors = 0

        with transaction.atomic():
            for row in rows:
                try:
                    term_id = row.get("TermID", "").strip()
                    term_name = row.get("TermName", "").strip()

                    if not term_id or not term_name:
                        self.stdout.write("⚠️  Skipping row with missing TermID or TermName")
                        continue

                    # Parse dates
                    start_date = None
                    end_date = None
                    add_date = None
                    drop_date = None

                    if row.get("StartDate") and row.get("StartDate") != "NULL":
                        try:
                            start_date = parse_date(row["StartDate"].split()[0])  # Take just the date part
                        except (ValueError, TypeError, IndexError):
                            pass
                    if row.get("EndDate") and row.get("EndDate") != "NULL":
                        with contextlib.suppress(Exception):
                            end_date = parse_date(row["EndDate"].split()[0])
                    if row.get("AddDate") and row.get("AddDate") != "NULL":
                        with contextlib.suppress(Exception):
                            add_date = parse_date(row["AddDate"].split()[0])
                    if row.get("DropDate") and row.get("DropDate") != "NULL":
                        with contextlib.suppress(Exception):
                            drop_date = parse_date(row["DropDate"].split()[0])
                    if row.get("LDPDate") and row.get("LDPDate") != "NULL":
                        with contextlib.suppress(Exception):
                            parse_date(row["LDPDate"].split()[0])

                    # Default start_date if none provided (required field)
                    if not start_date:
                        start_date = datetime.now().date()

                    # Get term type from CSV
                    term_type = row.get("TermType", "").strip()
                    # Keep empty if not provided, let model handle validation

                    if dry_run:
                        self.stdout.write(f"  Would create/update: {term_id} - {term_name} ({term_type})")
                        continue

                    # Create or update term using 'code' field (not 'name')
                    term, was_created = Term.objects.update_or_create(
                        code=term_id,  # Using TermID as code (correct field)
                        defaults={
                            "description": f"{term_name} - {row.get('Desp', '').strip()}".rstrip(" -").rstrip(),
                            "term_type": term_type,
                            "start_date": start_date,
                            "end_date": end_date,
                            "add_date": add_date,
                            "drop_date": drop_date,
                            "is_active": True,
                        },
                    )

                    if was_created:
                        created += 1
                        if created % 50 == 0:
                            self.stdout.write(f"  📋 Created {created} terms...")
                    else:
                        updated += 1

                except Exception as e:
                    errors += 1
                    self.stdout.write(self.style.ERROR(f"❌ Error processing {term_id}: {e}"))

        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"✅ Import complete! Created: {created}, Updated: {updated}, Errors: {errors}"),
            )
        else:
            self.stdout.write(self.style.SUCCESS(f"🔍 Dry run complete! Would process {len(rows)} terms"))
