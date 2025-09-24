#!/usr/bin/env python3
"""
Quick script to lookup term dates directly from CSV scholarship data
"""

import csv
from collections import Counter
from pathlib import Path


def analyze_term_dates():
    """Analyze what terms appear in scholarship data."""

    csv_path = Path("data/legacy/all_receipt_headers_250723.csv")
    print(f"📊 Analyzing terms from: {csv_path}")

    # Track scholarship terms
    scholarship_terms = []

    # Extract scholarship percentage patterns
    def has_scholarship(note):
        if not note:
            return False
        note_lower = note.lower()
        return any(word in note_lower for word in ["alumni", "staff", "scholar", "merit", "phann"]) and "%" in note

    with open(csv_path, encoding="utf-8") as file:
        reader = csv.DictReader(file)

        for row in reader:
            # Skip deleted records
            if row.get("Deleted", "0").strip() == "1":
                continue

            note = row.get("Notes", "").strip()
            if has_scholarship(note):
                term_id = row.get("TermID", "").strip()
                if term_id:
                    scholarship_terms.append(term_id)

    # Analyze term patterns
    term_counts = Counter(scholarship_terms)
    print(f"\n📈 Found {len(scholarship_terms)} scholarship records across {len(term_counts)} unique terms")

    print("\n🔍 Top 20 Terms with Scholarships:")
    for term, count in term_counts.most_common(20):
        print(f"   {term}: {count} scholarships")

    # Analyze term patterns
    print("\n📊 Term Format Analysis:")

    # Group by patterns
    patterns: dict[str, list[str]] = {
        "New Format (YYMMDDP-TN)": [],
        "Academic Year (YYYY-YYYYTN)": [],
        "Simple Year (YYYYTN)": [],
        "Other Formats": [],
    }

    for term in term_counts.keys():
        if "-" in term and len(term) > 10:
            # Looks like new format: 240214B-T1
            patterns["New Format (YYMMDDP-TN)"].append(term)
        elif "-" in term and term.count("-") == 1:
            # Looks like academic year: 2016-2017T3
            patterns["Academic Year (YYYY-YYYYTN)"].append(term)
        elif term[:4].isdigit() and "T" in term:
            # Looks like simple year: 2018T1
            patterns["Simple Year (YYYYTN)"].append(term)
        else:
            patterns["Other Formats"].append(term)

    for pattern_name, terms in patterns.items():
        if terms:
            print(f"\n{pattern_name}: {len(terms)} terms")
            for term in sorted(terms)[:5]:  # Show first 5 examples
                count = term_counts[term]
                print(f"   {term} ({count} scholarships)")
            if len(terms) > 5:
                print(f"   ... and {len(terms) - 5} more")

    # Create lookup for the problematic terms
    print("\n💡 Creating manual date lookup for historical terms...")

    # Extract the most common historical terms
    historical_terms = []
    for pattern_name, terms in patterns.items():
        if pattern_name != "New Format (YYMMDDP-TN)":
            historical_terms.extend(terms)

    # Sort by frequency
    frequent_historical = [(term, term_counts[term]) for term in historical_terms]
    frequent_historical.sort(key=lambda x: x[1], reverse=True)

    print("📋 Most Frequent Historical Terms (need manual date mapping):")
    for term, count in frequent_historical[:15]:
        print(f"   {term}: {count} scholarships")

    return frequent_historical


if __name__ == "__main__":
    analyze_term_dates()
