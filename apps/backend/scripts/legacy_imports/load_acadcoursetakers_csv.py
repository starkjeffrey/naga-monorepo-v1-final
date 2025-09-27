import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.models import StudentProfile  # Assumes you have a Student model
from apps.scheduling.models import (
    ClassHeader,  # Update if different
    ClassPart,  # Update if different
    Enrollment,  # Adjust if enrollment is tracked
)

# differently


PROGRAM_MAPPING = {
    "688": "EHSS",  # Language programs
    "87": "BA",
    "147": "MA",
    "582": "IEAP",
    "632": "GESL",
    "1187": "EXPRESS",
    "2076": "COMP",
    "2014": "FRENCH",
    "1427": "JAPANESE",
    "1949": "KOREAN",
    "832": "ESP",
}


class Command(BaseCommand):
    help = "Load legacy enrollment and grade data into ClassHeader, ClassPart, and Enrollment"

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="/Users/jeffreystark/PycharmProjects/naga/data/migration/all_academiccoursetakers.csv",
            help="Path to the CSV file",
        )

        parser.add_argument("--limit", type=int, default=None, help="Limit number of records to process")

        parser.add_argument("--start", type=int, default=0, help="Start line (zero-indexed)")

        parser.add_argument("--dry-run", action="store_true", help="Run without modifying the database")

    def handle(self, *args, **options):
        path = Path(options["file"])

        dry_run = options["dry_run"]

        limit = options["limit"]

        start = options["start"]

        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            rows = list(reader)[start : (start + limit if limit else None)]

        for idx, row in enumerate(rows, start=start):
            try:
                student_id = row["ID"]

                class_id = row["ClassID"]

                grade = row["Grade"].strip()

                credit = float(row["Credit"] or 0)

                parts = class_id.split("!$")

                if len(parts) < 5:
                    self.stderr.write(f"Line {idx}: Invalid CLASSID format: {class_id}")

                    continue

                termid, program_code, tod, part4, part5 = parts

                is_language = program_code not in {"87", "147"}

                header_name = part4 if is_language else part5

                part_name = part5 if is_language else part4

                if not dry_run:
                    with transaction.atomic():
                        header, _ = ClassHeader.objects.get_or_create(
                            term_id=termid,
                            name=header_name,
                            defaults={"program_code": program_code, "time_of_day": tod},
                        )

                        class_part, _ = ClassPart.objects.get_or_create(
                            header=header,
                            name=part_name,
                            defaults={"credit": credit},
                        )

                        student = StudentProfile.objects.get(legacy_id=student_id)

                        Enrollment.objects.update_or_create(
                            student=student,
                            class_part=class_part,
                            defaults={"grade": grade, "credit": credit},
                        )

                self.stdout.write(f"[{idx}] OK: Student {student_id} -> {header_name}/{part_name} Grade: {grade}")

            except Exception as e:
                self.stderr.write(f"[{idx}] ERROR: {e}")
