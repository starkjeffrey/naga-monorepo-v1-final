"""
Django management command to enhance clerk verification report with scholarship percentages
"""

import csv
import re
from collections import defaultdict
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.curriculum.models import Term


class Command(BaseCommand):
    help = "Enhance clerk verification report with scholarship percentages"

    def handle(self, *args, **options):
        self.stdout.write("📊 Enhancing Clerk Verification Report with Scholarship Percentages")
        self.stdout.write("=" * 70)

        # Load term dates from database
        self.stdout.write("📅 Loading term dates from database...")
        term_dates_cache = {}

        for term in Term.objects.all():
            term_dates_cache[term.code] = {
                "start_date": term.start_date.strftime("%Y-%m-%d") if term.start_date else None,
                "end_date": term.end_date.strftime("%Y-%m-%d") if term.end_date else None,
                "description": term.description or term.code,
            }

        self.stdout.write(f"   Loaded {len(term_dates_cache)} terms from database")

        # Load CSV data
        csv_path = Path("data/legacy/all_receipt_headers_250723.csv")
        self.stdout.write(f"📊 Loading scholarship data from: {csv_path}")

        scholarships = []
        terms_not_found = set()

        with open(csv_path, encoding="utf-8") as file:
            reader = csv.DictReader(file)
            total_records = 0
            scholarship_records = 0

            for row in reader:
                total_records += 1

                # Skip deleted records
                if row.get("Deleted", "0").strip() == "1":
                    continue

                note = row.get("Notes", "").strip()
                if not note:
                    continue

                # Check if this note contains scholarship information
                scholarship_percentage = self.extract_scholarship_percentage(note)
                if not scholarship_percentage:
                    continue

                scholarship_records += 1

                # Extract data
                student_id = row.get("ID", "").strip()
                student_name = row.get("name", "").strip()
                program_code = row.get("Program", "").strip()
                term_id = row.get("TermID", "").strip()
                receipt_no = row.get("ReceiptNo", "").strip()
                amount = float(row.get("Amount", "0") or "0")

                # Get program name
                program_name = self.get_program_name(program_code)

                # Get actual term dates from database
                start_date, end_date = None, None
                if term_id in term_dates_cache:
                    start_date = term_dates_cache[term_id]["start_date"]
                    end_date = term_dates_cache[term_id]["end_date"]
                else:
                    terms_not_found.add(term_id)

                # Classify scholarship type
                scholarship_type = self.classify_scholarship_type(note)

                # Calculate scholarship amount
                scholarship_amount = amount * (scholarship_percentage / 100)

                scholarships.append(
                    {
                        "student_id": student_id,
                        "student_name": student_name,
                        "program_code": program_code,
                        "program_name": program_name,
                        "term_id": term_id,
                        "start_date": start_date,
                        "end_date": end_date,
                        "scholarship_type": scholarship_type,
                        "scholarship_percentage": scholarship_percentage,
                        "total_amount": amount,
                        "scholarship_amount": scholarship_amount,
                        "receipt_no": receipt_no,
                        "original_note": note,
                    }
                )

        self.stdout.write("📈 Processing complete:")
        self.stdout.write(f"   Total records processed: {total_records:,}")
        self.stdout.write(f"   Scholarship records found: {scholarship_records:,}")

        if terms_not_found:
            self.stdout.write(f"⚠️  Terms not found in database: {len(terms_not_found)}")

        # Group by student
        student_scholarships = defaultdict(list)
        for scholarship in scholarships:
            student_scholarships[scholarship["student_id"]].append(scholarship)

        self.stdout.write(f"   Unique students with scholarships: {len(student_scholarships):,}")

        # Generate enhanced clerk verification report
        self.generate_enhanced_clerk_report(student_scholarships)

        self.stdout.write("\n✅ Enhanced clerk verification report generated!")
        self.stdout.write(
            "📁 Report: project-docs/scholarship-analysis/enhanced_clerk_verification_with_percentages.csv"
        )

    def extract_scholarship_percentage(self, note):
        """Extract scholarship percentage from note."""
        if not note:
            return None

        # Match patterns for scholarship percentages
        patterns = [
            r"(\d+(?:\.\d+)?)\s*%\s*(?:for\s+)?(?:alumni|alumna|alum)",
            r"(?:alumni|alumna|alum)(?:\s+[^0-9]*)?(\d+(?:\.\d+)?)\s*%",
            r"staff\s+(\d+(?:\.\d+)?)\s*%",
            r"(\d+(?:\.\d+)?)\s*%\s*staff",
            r"merit\s+(\d+(?:\.\d+)?)\s*%",
            r"(\d+(?:\.\d+)?)\s*%\s*merit",
            r"scholar\w*\s+(\d+(?:\.\d+)?)\s*%",
            r"(\d+(?:\.\d+)?)\s*%\s*scholar\w*",
            r"sc\.\s+(\d+(?:\.\d+)?)\s*%",
            r"(\d+(?:\.\d+)?)\s*%.*sc\.",
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

        if any(word in note_lower for word in ["alumni", "alumna", "alum"]):
            return "Alumni Scholarship"
        elif "staff" in note_lower or "phann" in note_lower:
            return "Staff Scholarship"
        elif "merit" in note_lower:
            return "Merit Scholarship"
        elif any(word in note_lower for word in ["scholar", "sch"]):
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
            688: "English Advanced Program",
        }

        try:
            code = int(program_code) if program_code else None
            return program_mapping.get(code, f"Program {program_code}")
        except (ValueError, TypeError):
            return f"Program {program_code}"

    def determine_scholarship_percentage_display(self, scholarships):
        """Determine how to display scholarship percentage - single value or VARIABLE/UNCERTAIN."""
        percentages = [s["scholarship_percentage"] for s in scholarships]
        unique_percentages = list(set(percentages))

        if len(unique_percentages) == 1:
            return f"{unique_percentages[0]:.0f}%"
        elif len(unique_percentages) == 2:
            return f"VARIABLE ({min(unique_percentages):.0f}%/{max(unique_percentages):.0f}%)"
        else:
            return f"UNCERTAIN (multiple rates: {', '.join(f'{p:.0f}%' for p in sorted(unique_percentages))})"

    def generate_enhanced_clerk_report(self, student_scholarships):
        """Generate enhanced clerk verification report with percentages."""
        output_dir = Path("project-docs/scholarship-analysis")
        output_dir.mkdir(parents=True, exist_ok=True)

        report_path = output_dir / "enhanced_clerk_verification_with_percentages.csv"

        fieldnames = [
            "Student_Name",
            "Student_ID",
            "Program",
            "Scholarship_Type",
            "Scholarship_Percentage",
            "Date_Range_Database",
            "Total_Scholarship_Amount",
            "Original_Note_Sample",
        ]

        # Track statistics
        single_rate_students = 0
        variable_rate_students = 0
        uncertain_rate_students = 0

        with open(report_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

            for student_id, scholarships in sorted(student_scholarships.items()):
                if not scholarships:
                    continue

                # Aggregate student data
                student_name = scholarships[0]["student_name"]
                programs = list({s["program_name"] for s in scholarships})
                scholarship_types = list({s["scholarship_type"] for s in scholarships})

                # Date range analysis using actual database dates
                start_dates = [s["start_date"] for s in scholarships if s["start_date"]]
                end_dates = [s["end_date"] for s in scholarships if s["end_date"]]

                if start_dates and end_dates:
                    date_range = f"{min(start_dates)} to {max(end_dates)}"
                else:
                    date_range = "Date range unknown"

                # Financial totals
                total_amount = sum(s["scholarship_amount"] for s in scholarships)

                # Determine scholarship percentage display
                percentage_display = self.determine_scholarship_percentage_display(scholarships)

                # Track statistics
                if "VARIABLE" in percentage_display:
                    variable_rate_students += 1
                elif "UNCERTAIN" in percentage_display:
                    uncertain_rate_students += 1
                else:
                    single_rate_students += 1

                # Sample original note
                sample_note = scholarships[0]["original_note"]
                if len(scholarships) > 1:
                    sample_note = "Mixed scholarship types"

                writer.writerow(
                    {
                        "Student_Name": student_name,
                        "Student_ID": student_id,
                        "Program": "; ".join(programs),
                        "Scholarship_Type": "; ".join(scholarship_types),
                        "Scholarship_Percentage": percentage_display,
                        "Date_Range_Database": date_range,
                        "Total_Scholarship_Amount": f"${total_amount:.2f}",
                        "Original_Note_Sample": sample_note,
                    }
                )

        # Print summary statistics
        total_students = len(student_scholarships)
        self.stdout.write("\n📊 Scholarship Percentage Analysis:")
        self.stdout.write(
            f"   Students with SINGLE rate: {single_rate_students} "
            f"({single_rate_students / total_students * 100:.1f}%)"
        )
        self.stdout.write(
            f"   Students with VARIABLE rates: {variable_rate_students} "
            f"({variable_rate_students / total_students * 100:.1f}%)"
        )
        self.stdout.write(
            f"   Students with UNCERTAIN rates: {uncertain_rate_students} "
            f"({uncertain_rate_students / total_students * 100:.1f}%)"
        )
