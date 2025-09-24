"""Automated creation of missing students and terms identified in legacy data analysis.

This command handles the 72 missing students and 5 missing terms that are blocking
enterprise-scale processing of 98K+ legacy receipts.
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.curriculum.models import Term
from apps.people.models import Person, StudentProfile


class Command(BaseCommand):
    """Create missing students and terms for seamless A/R reconstruction."""

    help = "Automatically create missing students and terms from legacy data analysis"

    def add_arguments(self, parser):
        parser.add_argument(
            "--missing-students-file",
            type=str,
            default="project-docs/legacy-analysis/missing-students-detailed.csv",
            help="Path to missing students CSV file",
        )

        parser.add_argument(
            "--missing-terms-file",
            type=str,
            default="project-docs/legacy-analysis/missing-terms.txt",
            help="Path to missing terms text file",
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be created without actually creating",
        )

    def handle(self, *args, **options):
        """Execute automated creation of missing entities."""
        self.dry_run = options["dry_run"]

        if self.dry_run:
            self.stdout.write("🔍 DRY RUN MODE - No changes will be made")

        self.stdout.write("🚀 Creating missing entities for seamless processing...")

        # Create missing terms first (students may depend on them)
        missing_terms = self.create_missing_terms(options["missing_terms_file"])

        # Create missing students
        missing_students = self.create_missing_students(options["missing_students_file"])

        # Summary
        self.stdout.write("\n✅ ENTITY CREATION COMPLETE")
        self.stdout.write(f"   Terms Created: {missing_terms}")
        self.stdout.write(f"   Students Created: {missing_students}")

        if not self.dry_run:
            self.stdout.write("\n🎯 Ready for enterprise processing!")
            self.stdout.write("   Run: python manage.py smart_batch_processor")

    def create_missing_terms(self, terms_file: str) -> int:
        """Create the 4 legitimate missing terms identified in analysis."""
        self.stdout.write("📚 Creating missing terms...")

        # The 4 legitimate missing terms from analysis (excluding deleted records)
        missing_terms = ["2011T1", "2023TXE", "2023T1", "2013TD"]

        self.stdout.write(f"   Creating {len(missing_terms)} missing terms:")
        for term_code_display in missing_terms:
            self.stdout.write(f"     - {term_code_display}")

        created_count = 0

        for term_code in missing_terms:
            # Check if term already exists
            if Term.objects.filter(code=term_code).exists():
                self.stdout.write(f"   i  Term {term_code} already exists")
                continue

            if not self.dry_run:
                try:
                    with transaction.atomic():
                        # Parse term code to extract meaningful data
                        year, term_info = self.parse_term_code(term_code)

                        Term.objects.create(
                            code=term_code,
                            description=f"Legacy Term {term_code}",
                            start_date=timezone.now().date(),
                            end_date=timezone.now().date(),
                            is_active=False,  # Legacy terms are not active
                        )

                        created_count += 1
                        self.stdout.write(f"   ✅ Created term: {term_code}")

                except Exception as e:
                    self.stdout.write(f"   ❌ Failed to create term {term_code}: {e}")
            else:
                self.stdout.write(f"   [DRY RUN] Would create term: {term_code}")
                created_count += 1

        return created_count

    def create_missing_students(self, students_file: str) -> int:
        """Create missing students from analysis file."""
        self.stdout.write("👥 Creating missing students...")

        students_path = Path(students_file)
        if not students_path.exists():
            self.stdout.write(f"   ⚠️  Students file not found: {students_file}")
            return 0

        # Load unique missing students (file may have duplicates)
        unique_students = {}

        with open(students_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                student_id = int(row["Student_ID"])
                if student_id not in unique_students:
                    unique_students[student_id] = {
                        "name": row["Student_Name"],
                        "receipt_count": int(row["Receipt_Count"]),
                        "priority": row["Priority"],
                    }

        self.stdout.write(f"   Found {len(unique_students)} unique missing students")

        created_count = 0

        for student_id, data in unique_students.items():
            # Check if student already exists
            if StudentProfile.objects.filter(student_id=student_id).exists():
                self.stdout.write(f"   i  Student {student_id} already exists")
                continue

            if not self.dry_run:
                try:
                    with transaction.atomic():
                        # Parse name into first/last name
                        name_str = str(data["name"]).strip()
                        name_parts = name_str.split()
                        first_name = name_parts[0] if name_parts else "Unknown"
                        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else "Student"

                        # Create Person first
                        person = Person.objects.create(
                            personal_name=first_name,
                            family_name=last_name,
                            full_name=name_str,
                        )

                        # Create StudentProfile
                        StudentProfile.objects.create(
                            person=person,
                            student_id=student_id,
                            current_status=StudentProfile.Status.GRADUATED,  # Assume legacy students are graduated
                        )

                        created_count += 1
                        self.stdout.write(f"   ✅ Created student: {student_id} - {data['name']}")

                except Exception as e:
                    self.stdout.write(f"   ❌ Failed to create student {student_id}: {e}")
            else:
                self.stdout.write(f"   [DRY RUN] Would create student: {student_id} - {data['name']}")
                created_count += 1

        return created_count

    def parse_term_code(self, term_code: str) -> tuple:
        """Parse term code to extract year and term information."""
        try:
            # Handle different term code formats
            if term_code.startswith("20"):  # Standard format like 2023T1E
                year = int(term_code[:4])
                return year, term_code[4:]
            else:
                # Legacy format - estimate year
                return 2020, term_code
        except (ValueError, IndexError):
            return 2020, term_code
