#!/usr/bin/env python3
"""
Direct database query to get scholarship analysis with actual term dates
"""

import csv
import re
import sqlite3
from collections import defaultdict
from pathlib import Path


def extract_scholarship_percentage(note):
    """Extract scholarship percentage from note."""
    if not note:
        return None

    # Match patterns for scholarship percentages
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


def query_database_terms():
    """Query the database directly for terms."""
    import os

    # Try to find the SQLite database file
    db_paths = ["db.sqlite3", "../db.sqlite3", "../../db.sqlite3"]

    db_path = None
    for path in db_paths:
        if os.path.exists(path):
            db_path = path
            break

    if not db_path:
        print("❌ Could not find database file")
        return {}

    print(f"📊 Querying database at: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Query terms table
        cursor.execute(
            """
            SELECT code, start_date, end_date, description
            FROM curriculum_term
            WHERE start_date IS NOT NULL AND end_date IS NOT NULL
        """
        )

        terms = {}
        for row in cursor.fetchall():
            code, start_date, end_date, description = row
            terms[code] = {"start_date": start_date, "end_date": end_date, "description": description or ""}

        conn.close()
        print(f"✅ Found {len(terms)} terms with dates in database")
        return terms

    except Exception as e:
        print(f"❌ Database query failed: {e}")
        return {}


def analyze_scholarships_with_db_dates():
    """Main analysis function with database term lookup."""
    print("🎓 Scholarship Analysis with Database Term Dates")
    print("=" * 55)

    # Get term dates from database
    term_dates = query_database_terms()

    # Load CSV data
    csv_path = Path("data/legacy/all_receipt_headers_250723.csv")
    print(f"📊 Loading scholarship data from: {csv_path}")

    scholarships = []

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

            # Extract data
            student_id = row.get("ID", "").strip()
            student_name = row.get("name", "").strip()
            program_code = row.get("Program", "").strip()
            term_id = row.get("TermID", "").strip()
            receipt_no = row.get("ReceiptNo", "").strip()
            amount = float(row.get("Amount", "0") or "0")

            # Get program name
            program_name = get_program_name(program_code)

            # Get actual term dates from database
            start_date, end_date = None, None
            if term_id in term_dates:
                start_date = term_dates[term_id]["start_date"]
                end_date = term_dates[term_id]["end_date"]

            # Classify scholarship type
            scholarship_type = classify_scholarship_type(note)

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

    print("📈 Processing complete:")
    print(f"   Total records processed: {total_records:,}")
    print(f"   Scholarship records found: {scholarship_records:,}")

    # Group by student
    student_scholarships = defaultdict(list)
    for scholarship in scholarships:
        student_scholarships[scholarship["student_id"]].append(scholarship)

    print(f"   Unique students with scholarships: {len(student_scholarships):,}")

    # Generate student summary report with actual dates
    generate_student_report_with_db_dates(student_scholarships, term_dates)

    print("\n✅ Analysis complete!")
    print("📁 Report: project-docs/scholarship-analysis/students_with_database_dates.csv")


def generate_student_report_with_db_dates(student_scholarships, term_dates):
    """Generate student summary with database dates."""
    output_dir = Path("project-docs/scholarship-analysis")
    output_dir.mkdir(parents=True, exist_ok=True)

    report_path = output_dir / "students_with_database_dates.csv"

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
        "terms_missing_dates",
    ]

    # Track statistics
    students_with_all_dates = 0
    students_with_some_dates = 0
    students_with_no_dates = 0

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

            # Date range analysis
            start_dates = [s["start_date"] for s in scholarships if s["start_date"]]
            end_dates = [s["end_date"] for s in scholarships if s["end_date"]]
            terms_with_dates = [s["term_id"] for s in scholarships if s["start_date"]]
            terms_without_dates = [s["term_id"] for s in scholarships if not s["start_date"]]

            # Determine date range status
            if len(terms_with_dates) == len(scholarships):
                students_with_all_dates += 1
                date_range = f"{min(start_dates)} to {max(end_dates)}"
            elif len(terms_with_dates) > 0:
                students_with_some_dates += 1
                date_range = (
                    f"PARTIAL: {min(start_dates)} to {max(end_dates)} (missing {len(terms_without_dates)} terms)"
                )
            else:
                students_with_no_dates += 1
                date_range = "NO DATABASE DATES FOUND"

            # Financial totals
            total_amount = sum(s["scholarship_amount"] for s in scholarships)
            base_total = sum(s["total_amount"] for s in scholarships)
            avg_percentage = (total_amount / base_total * 100) if base_total > 0 else 0

            # Terms
            all_terms = list({s["term_id"] for s in scholarships})

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
                    "terms_with_scholarships": "; ".join(all_terms),
                    "terms_missing_dates": "; ".join(set(terms_without_dates)) if terms_without_dates else "",
                }
            )

    # Print summary statistics
    total_students = len(student_scholarships)
    print("\n📊 Date Coverage Analysis:")
    print(
        f"   Students with ALL dates: {students_with_all_dates} ({students_with_all_dates / total_students * 100:.1f}%)"
    )
    print(
        f"   Students with SOME dates: {students_with_some_dates} ({students_with_some_dates / total_students * 100:.1f}%)"
    )
    print(
        f"   Students with NO dates: {students_with_no_dates} ({students_with_no_dates / total_students * 100:.1f}%)"
    )


if __name__ == "__main__":
    analyze_scholarships_with_db_dates()
