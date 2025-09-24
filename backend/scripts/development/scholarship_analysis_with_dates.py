#!/usr/bin/env python3
"""
Simple Django management command to analyze scholarships with actual term dates
"""

from pathlib import Path


def run_django_management_command():
    """Create and run Django management command for scholarship analysis."""

    # Create the Django management command
    management_command = '''
import csv
import re
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from apps.curriculum.models import Term


class Command(BaseCommand):
    help = "Analyze scholarships with actual term dates from database"

    def handle(self, *args, **options):
        self.stdout.write("🎓 Starting Scholarship Analysis with Database Term Dates")
        self.stdout.write("=" * 65)

        # Load term dates from database
        self.stdout.write("📅 Loading term dates from database...")
        term_dates_cache = {}

        for term in Term.objects.all():
            term_dates_cache[term.term_id] = {
                'start_date': term.start_date.strftime("%Y-%m-%d") if term.start_date else None,
                'end_date': term.end_date.strftime("%Y-%m-%d") if term.end_date else None,
                'name': term.name
            }

        self.stdout.write(f"   Loaded {len(term_dates_cache)} terms from database")

        # Load CSV data
        csv_path = Path("data/legacy/all_receipt_headers_250723.csv")
        self.stdout.write(f"📊 Loading scholarship data from: {csv_path}")

        scholarships = []

        with open(csv_path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            total_records = 0
            scholarship_records = 0

            for row in reader:
                total_records += 1

                # Skip deleted records
                if row.get('Deleted', '0').strip() == '1':
                    continue

                note = row.get('Notes', '').strip()
                if not note:
                    continue

                # Check if this note contains scholarship information
                scholarship_percentage = self.extract_scholarship_percentage(note)
                if not scholarship_percentage:
                    continue

                scholarship_records += 1

                # Extract data
                student_id = row.get('ID', '').strip()
                student_name = row.get('name', '').strip()
                program_code = row.get('Program', '').strip()
                term_id = row.get('TermID', '').strip()
                receipt_no = row.get('ReceiptNo', '').strip()
                amount = float(row.get('Amount', '0') or '0')

                # Get program name
                program_name = self.get_program_name(program_code)

                # Get actual term dates from database
                start_date, end_date = None, None
                if term_id in term_dates_cache:
                    start_date = term_dates_cache[term_id]['start_date']
                    end_date = term_dates_cache[term_id]['end_date']

                # Classify scholarship type
                scholarship_type = self.classify_scholarship_type(note)

                # Calculate scholarship amount
                scholarship_amount = amount * (scholarship_percentage / 100)

                scholarships.append({
                    'student_id': student_id,
                    'student_name': student_name,
                    'program_code': program_code,
                    'program_name': program_name,
                    'term_id': term_id,
                    'start_date': start_date,
                    'end_date': end_date,
                    'scholarship_type': scholarship_type,
                    'scholarship_percentage': scholarship_percentage,
                    'total_amount': amount,
                    'scholarship_amount': scholarship_amount,
                    'receipt_no': receipt_no,
                    'original_note': note
                })

        self.stdout.write(f"📈 Processing complete:")
        self.stdout.write(f"   Total records processed: {total_records:,}")
        self.stdout.write(f"   Scholarship records found: {scholarship_records:,}")

        # Group by student
        student_scholarships = defaultdict(list)
        for scholarship in scholarships:
            student_scholarships[scholarship['student_id']].append(scholarship)

        self.stdout.write(f"   Unique students with scholarships: {len(student_scholarships):,}")

        # Generate student summary report with actual dates
        self.generate_student_report(student_scholarships)

        self.stdout.write("\\n✅ Analysis complete!")
        self.stdout.write("📁 Report: project-docs/scholarship-analysis/students_with_database_dates.csv")

    def extract_scholarship_percentage(self, note):
        """Extract scholarship percentage from note."""
        if not note:
            return None

        # Match patterns for scholarship percentages
        patterns = [
            r'(\\d+(?:\\.\\d+)?)\\s*%\\s*(?:for\\s+)?(?:alumni|alumna|alum)',
            r'(?:alumni|alumna|alum)\\s+(\\d+(?:\\.\\d+)?)\\s*%',
            r'staff\\s+(\\d+(?:\\.\\d+)?)\\s*%',
            r'(\\d+(?:\\.\\d+)?)\\s*%\\s*staff',
            r'merit\\s+(\\d+(?:\\.\\d+)?)\\s*%',
            r'(\\d+(?:\\.\\d+)?)\\s*%\\s*merit',
            r'scholar\\w*\\s+(\\d+(?:\\.\\d+)?)\\s*%',
            r'(\\d+(?:\\.\\d+)?)\\s*%\\s*scholar\\w*',
        ]

        for pattern in patterns:
            match = re.search(pattern, note, re.IGNORECASE)
            if match:
                return float(match.group(1))

        return None

    def classify_scholarship_type(self, note):
        """Classify scholarship type based on note content."""
        if not note:
            return "Unknown"

        note_lower = note.lower()

        if any(word in note_lower for word in ['alumni', 'alumna', 'alum']):
            return "Alumni Scholarship"
        elif 'staff' in note_lower or 'phann' in note_lower:
            return "Staff Scholarship"
        elif 'merit' in note_lower:
            return "Merit Scholarship"
        elif any(word in note_lower for word in ['scholar', 'sch']):
            return "General Scholarship"
        else:
            return "Unknown Scholarship"

    def get_program_name(self, program_code):
        """Convert program code to readable name."""
        program_mapping = {
            87: "BA Program (Cycle 2)",
            147: "MA Program (Cycle 3)",
            582: "English Foundation Program",
            632: "English Intermediate Program",
            688: "English Advanced Program"
        }

        try:
            code = int(program_code) if program_code else None
            return program_mapping.get(code, f"Program {program_code}")
        except (ValueError, TypeError):
            return f"Program {program_code}"

    def generate_student_report(self, student_scholarships):
        """Generate student summary with database dates."""
        output_dir = Path("project-docs/scholarship-analysis")
        output_dir.mkdir(parents=True, exist_ok=True)

        report_path = output_dir / "students_with_database_dates.csv"

        fieldnames = [
            'student_id', 'student_name', 'total_scholarships', 'programs_studied',
            'scholarship_types', 'date_range', 'total_scholarship_amount',
            'average_scholarship_percentage', 'terms_with_scholarships'
        ]

        with open(report_path, 'w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

            for student_id, scholarships in sorted(student_scholarships.items()):
                if not scholarships:
                    continue

                # Aggregate student data
                student_name = scholarships[0]['student_name']
                programs = list(set(s['program_name'] for s in scholarships))
                scholarship_types = list(set(s['scholarship_type'] for s in scholarships))

                # Date range using database dates
                start_dates = [s['start_date'] for s in scholarships if s['start_date']]
                end_dates = [s['end_date'] for s in scholarships if s['end_date']]

                if start_dates and end_dates:
                    date_range = f"{min(start_dates)} to {max(end_dates)}"
                else:
                    # Count how many terms have no dates
                    terms_without_dates = [s['term_id'] for s in scholarships if not s['start_date']]
                    if terms_without_dates:
                        date_range = f"Missing dates for {len(terms_without_dates)} terms: {'; '.join(set(terms_without_dates))}"
                    else:
                        date_range = "No terms found"

                # Financial totals
                total_amount = sum(s['scholarship_amount'] for s in scholarships)
                base_total = sum(s['total_amount'] for s in scholarships)
                avg_percentage = (total_amount / base_total * 100) if base_total > 0 else 0

                # Terms
                terms = list(set(s['term_id'] for s in scholarships))

                writer.writerow({
                    'student_id': student_id,
                    'student_name': student_name,
                    'total_scholarships': len(scholarships),
                    'programs_studied': '; '.join(programs),
                    'scholarship_types': '; '.join(scholarship_types),
                    'date_range': date_range,
                    'total_scholarship_amount': f"${total_amount:.2f}",
                    'average_scholarship_percentage': f"{avg_percentage:.1f}%",
                    'terms_with_scholarships': '; '.join(terms)
                })
'''

    # Write the management command
    command_dir = Path("apps/curriculum/management/commands")
    command_dir.mkdir(parents=True, exist_ok=True)

    command_file = command_dir / "analyze_scholarships_with_dates.py"
    with open(command_file, "w") as f:
        f.write(management_command)

    print(f"✅ Created Django management command: {command_file}")
    return str(command_file)


if __name__ == "__main__":
    command_file = run_django_management_command()
    print("\n🚀 Run the command with:")
    print("uv run python manage.py analyze_scholarships_with_dates")
