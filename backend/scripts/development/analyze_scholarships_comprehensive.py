#!/usr/bin/env python3
"""
Comprehensive Scholarship Analysis Script
Extracts scholarship amounts, programs, and date ranges for each student

Addresses user request: "I need both scholarship amount AND program the student
was studying. 2 things for each person. and start and stop dates"
"""

import csv
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

import django

# Setup Django
sys.path.append("/Users/jeffreystark/PycharmProjects/naga-monorepo/backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

# Import Django models after setup
from apps.curriculum.models import Term


def get_term_dates_from_db():
    """Get term start/end dates from database."""
    term_dates = {}

    try:
        for term in Term.objects.all():
            term_dates[term.code] = {
                "start_date": term.start_date.strftime("%Y-%m-%d") if term.start_date else None,
                "end_date": term.end_date.strftime("%Y-%m-%d") if term.end_date else None,
                "name": term.description,
            }
    except Exception as e:
        print(f"⚠️ Error loading terms from database: {e}")

    return term_dates


def extract_scholarship_percentage(note):
    """Extract scholarship percentage from note."""
    if not note:
        return None

    # Match patterns like "30% for Alumni", "20% Alumni", "Staff 50%", etc.
    patterns = [
        r"(\d+(?:\.\d+)?)\s*%\s*(?:for\s+)?(?:alumni|alumna|alum)",
        r"(?:alumni|alumna|alum)\s+(\d+(?:\.\d+)?)\s*%",
        r"staff\s+(\d+(?:\.\d+)?)\s*%",
        r"(\d+(?:\.\d+)?)\s*%\s*staff",
        r"merit\s+(\d+(?:\.\d+)?)\s*%",
        r"(\d+(?:\.\d+)?)\s*%\s*merit",
        r"scholar\w*\s+(\d+(?:\.\d+)?)\s*%",
        r"(\d+(?:\.\d+)?)\s*%\s*scholar\w*",
    ]

    for pattern in patterns:
        match = re.search(pattern, note, re.IGNORECASE)
        if match:
            return float(match.group(1))

    return None


def classify_scholarship_type(note):
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


def get_program_name(program_code):
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


def lookup_term_dates(term_id, term_dates_cache):
    """Lookup actual start/end dates from database for term ID."""
    if not term_id or term_id not in term_dates_cache:
        return None, None

    term_info = term_dates_cache[term_id]
    return term_info["start_date"], term_info["end_date"]


def analyze_scholarships():
    """Main analysis function."""
    print("🎓 Starting Comprehensive Scholarship Analysis")
    print("=" * 60)

    # Load term dates from database
    print("📅 Loading term dates from database...")
    term_dates_cache = get_term_dates_from_db()
    print(f"   Loaded {len(term_dates_cache)} terms from database")

    # Load receipt data
    csv_path = Path("data/legacy/all_receipt_headers_250723.csv")
    if not csv_path.exists():
        print(f"❌ Error: CSV file not found at {csv_path}")
        return

    print(f"📊 Loading data from: {csv_path}")

    # Student scholarship data
    student_scholarships = defaultdict(list)
    scholarship_summary = []

    # Program statistics
    program_stats = defaultdict(int)
    scholarship_type_stats = defaultdict(int)

    # Read and process CSV
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
            scholarship_percentage = extract_scholarship_percentage(note)
            if not scholarship_percentage:
                continue

            scholarship_records += 1

            # Extract student and program information
            student_id = row.get("ID", "").strip()
            student_name = row.get("name", "").strip()
            program_code = row.get("Program", "").strip()
            term_id = row.get("TermID", "").strip()
            receipt_no = row.get("ReceiptNo", "").strip()
            total_amount = row.get("Amount", "0").strip()

            # Get program name and dates
            program_name = get_program_name(program_code)
            start_date, end_date = lookup_term_dates(term_id, term_dates_cache)

            # Classify scholarship type
            scholarship_type = classify_scholarship_type(note)

            # Calculate scholarship amount
            try:
                amount = float(total_amount) if total_amount else 0
                scholarship_amount = amount * (scholarship_percentage / 100)
            except (ValueError, TypeError):
                scholarship_amount = 0

            # Create scholarship record
            scholarship_record = {
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

            student_scholarships[student_id].append(scholarship_record)
            scholarship_summary.append(scholarship_record)

            # Update statistics
            program_stats[program_name] += 1
            scholarship_type_stats[scholarship_type] += 1

    print("📈 Processing Complete:")
    print(f"   Total records processed: {total_records:,}")
    print(f"   Scholarship records found: {scholarship_records:,}")
    print(f"   Unique students with scholarships: {len(student_scholarships):,}")

    # Generate comprehensive report
    generate_scholarship_report(scholarship_summary, program_stats, scholarship_type_stats)

    # Generate student-specific summary
    generate_student_summary(student_scholarships)

    print("\n✅ Analysis Complete!")
    print("📁 Reports generated:")
    print("   - project-docs/scholarship-analysis/comprehensive_scholarship_report.csv")
    print("   - project-docs/scholarship-analysis/student_scholarship_summary.csv")
    print("   - project-docs/scholarship-analysis/scholarship_statistics.txt")


def generate_scholarship_report(scholarship_summary, program_stats, scholarship_type_stats):
    """Generate comprehensive scholarship report."""
    output_dir = Path("project-docs/scholarship-analysis")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Main detailed report
    report_path = output_dir / "comprehensive_scholarship_report.csv"

    fieldnames = [
        "student_id",
        "student_name",
        "program_code",
        "program_name",
        "term_id",
        "start_date",
        "end_date",
        "scholarship_type",
        "scholarship_percentage",
        "total_amount",
        "scholarship_amount",
        "receipt_no",
        "original_note",
    ]

    with open(report_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        # Sort by student ID, then by start date
        sorted_scholarships = sorted(scholarship_summary, key=lambda x: (x["student_id"], x["start_date"] or ""))
        writer.writerows(sorted_scholarships)

    # Statistics report
    stats_path = output_dir / "scholarship_statistics.txt"
    with open(stats_path, "w", encoding="utf-8") as file:
        file.write("SCHOLARSHIP ANALYSIS STATISTICS\n")
        file.write("=" * 50 + "\n\n")

        file.write("SCHOLARSHIPS BY PROGRAM:\n")
        file.write("-" * 30 + "\n")
        for program, count in sorted(program_stats.items()):
            file.write(f"{program}: {count} scholarships\n")

        file.write("\nSCHOLARSHIPS BY TYPE:\n")
        file.write("-" * 30 + "\n")
        for scholarship_type, count in sorted(scholarship_type_stats.items()):
            file.write(f"{scholarship_type}: {count} scholarships\n")

        # Calculate totals
        total_scholarship_amount = sum(s["scholarship_amount"] for s in scholarship_summary)
        total_base_amount = sum(s["total_amount"] for s in scholarship_summary)

        file.write("\nFINANCIAL SUMMARY:\n")
        file.write("-" * 30 + "\n")
        file.write(f"Total scholarship amount: ${total_scholarship_amount:,.2f}\n")
        file.write(f"Total base amount: ${total_base_amount:,.2f}\n")
        if total_base_amount > 0:
            file.write(
                f"Average scholarship percentage: {(total_scholarship_amount / total_base_amount * 100):.1f}%\n"
            )
        else:
            file.write("Average scholarship percentage: N/A (no base amount)\n")


def generate_student_summary(student_scholarships):
    """Generate per-student scholarship summary."""
    output_dir = Path("project-docs/scholarship-analysis")
    summary_path = output_dir / "student_scholarship_summary.csv"

    fieldnames = [
        "student_id",
        "student_name",
        "total_scholarships",
        "programs_studied",
        "scholarship_types",
        "date_range",
        "total_scholarship_amount",
        "average_scholarship_percentage",
        "terms_with_scholarships",
    ]

    with open(summary_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for student_id, scholarships in sorted(student_scholarships.items()):
            if not scholarships:
                continue

            # Aggregate student data
            student_name = scholarships[0]["student_name"]
            programs = list({s["program_name"] for s in scholarships})
            scholarship_types = list({s["scholarship_type"] for s in scholarships})

            # Date range
            start_dates = [s["start_date"] for s in scholarships if s["start_date"]]
            end_dates = [s["end_date"] for s in scholarships if s["end_date"]]

            if start_dates and end_dates:
                date_range = f"{min(start_dates)} to {max(end_dates)}"
            else:
                date_range = "No term dates in database"

            # Financial totals
            total_amount = sum(s["scholarship_amount"] for s in scholarships)
            base_total = sum(s["total_amount"] for s in scholarships)
            avg_percentage = (total_amount / base_total * 100) if base_total > 0 else 0

            # Terms
            terms = list({s["term_id"] for s in scholarships})

            writer.writerow(
                {
                    "student_id": student_id,
                    "student_name": student_name,
                    "total_scholarships": len(scholarships),
                    "programs_studied": "; ".join(programs),
                    "scholarship_types": "; ".join(scholarship_types),
                    "date_range": date_range,
                    "total_scholarship_amount": f"${total_amount:.2f}",
                    "average_scholarship_percentage": f"{avg_percentage:.1f}%",
                    "terms_with_scholarships": "; ".join(terms),
                }
            )


if __name__ == "__main__":
    # Change to backend directory
    import os

    backend_dir = Path(__file__).parent.parent.parent
    os.chdir(backend_dir)

    analyze_scholarships()
