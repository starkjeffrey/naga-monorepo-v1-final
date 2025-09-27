#!/usr/bin/env python3
"""
ClassID Parser Variance Report

Analyzes differences between automated parser and manual parsing work
for 2021+ legacy course taker data.
"""

import os
import sys
from collections import defaultdict
from pathlib import Path

import django

# Setup Django
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.db import connection

from scripts.legacy_imports.classid_parser import parse_full_classid


def generate_variance_report():
    """Generate a comprehensive variance report between parser and manual work."""

    print("📊 ClassID Parser Variance Report")
    print("=" * 60)
    print("Comparing automated parser vs manual parsing for 2021+ data")
    print()

    # Get all manually parsed records from 2021+
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                "ClassID",
                "NormalizedCourse",
                "NormalizedPart",
                "NormalizedSection",
                split_part("ClassID", '!$', 2) as program,
                split_part("ClassID", '!$', 4) as part4
            FROM legacy_course_takers
            WHERE "NormalizedCourse" != ''
                AND "NormalizedCourse" IS NOT NULL
                AND "ClassID" IS NOT NULL
                AND "ClassID" != ''
                AND "parsed_termid" >= '21'
            ORDER BY "ClassID"
        """)

        all_records = cursor.fetchall()

    print(f"📄 Analyzing {len(all_records):,} manually parsed records...")

    # Analysis tracking
    total_records = len(all_records)
    perfect_matches = 0
    discrepancies = {
        "course_only": [],
        "part_only": [],
        "section_only": [],
        "course_part": [],
        "course_section": [],
        "part_section": [],
        "all_three": [],
    }

    pattern_analysis = defaultdict(lambda: {"total": 0, "mismatches": 0, "examples": []})
    program_analysis = defaultdict(lambda: {"total": 0, "mismatches": 0})

    for record in all_records:
        classid, expected_course, expected_part, expected_section, program, part4 = record

        # Parse with our function
        parsed_course, parsed_part, parsed_section = parse_full_classid(classid)

        # Track pattern statistics
        pattern_analysis[part4]["total"] += 1
        program_analysis[program]["total"] += 1

        # Check matches
        course_match = parsed_course == expected_course
        part_match = parsed_part == expected_part
        section_match = parsed_section == expected_section

        if course_match and part_match and section_match:
            perfect_matches += 1
        else:
            # Track pattern mismatches
            pattern_analysis[part4]["mismatches"] += 1
            program_analysis[program]["mismatches"] += 1

            # Add example for this pattern
            if len(pattern_analysis[part4]["examples"]) < 3:
                pattern_analysis[part4]["examples"].append(
                    {
                        "classid": classid,
                        "expected": (expected_course, expected_part, expected_section),
                        "parsed": (parsed_course, parsed_part, parsed_section),
                    }
                )

            # Categorize the type of discrepancy
            issues = []
            if not course_match:
                issues.append("course")
            if not part_match:
                issues.append("part")
            if not section_match:
                issues.append("section")

            key = "_".join(sorted(issues)) + "_only" if len(issues) == 1 else "_".join(sorted(issues))
            if key not in discrepancies:
                key = "mixed"
                if key not in discrepancies:
                    discrepancies[key] = []

            discrepancies[key].append(
                {
                    "classid": classid,
                    "expected": (expected_course, expected_part, expected_section),
                    "parsed": (parsed_course, parsed_part, parsed_section),
                    "program": program,
                    "part4": part4,
                }
            )

    # Print summary statistics
    print("\n📈 OVERALL ACCURACY")
    print("-" * 30)
    accuracy = (perfect_matches / total_records) * 100
    print(f"Perfect matches: {perfect_matches:,} / {total_records:,} ({accuracy:.1f}%)")
    print(f"Total discrepancies: {total_records - perfect_matches:,} ({100 - accuracy:.1f}%)")

    # Print discrepancy breakdown
    print("\n🔍 DISCREPANCY BREAKDOWN")
    print("-" * 30)
    for disc_type, disc_list in discrepancies.items():
        if disc_list:
            print(f"{disc_type.replace('_', ' ').title()}: {len(disc_list):,}")

    # Print top problematic patterns
    print("\n⚠️  TOP PROBLEMATIC PATTERNS")
    print("-" * 40)
    pattern_errors = [
        (pattern, data["mismatches"], data["total"])
        for pattern, data in pattern_analysis.items()
        if data["mismatches"] > 0
    ]
    pattern_errors.sort(key=lambda x: x[1], reverse=True)

    for pattern, mismatches, total in pattern_errors[:15]:
        error_rate = (mismatches / total) * 100
        print(f"{pattern:20} {mismatches:4}/{total:4} ({error_rate:5.1f}% error)")

        # Show examples for top patterns
        if mismatches >= 10 and pattern in pattern_analysis:
            for i, example in enumerate(pattern_analysis[pattern]["examples"][:2], 1):
                print(f"  Example {i}: {example['classid']}")
                print(f"    Expected: {example['expected']}")
                print(f"    Parsed:   {example['parsed']}")

    # Print program analysis
    print("\n📚 ACCURACY BY PROGRAM")
    print("-" * 30)
    for program, data in sorted(program_analysis.items()):
        if data["total"] > 0:
            accuracy = ((data["total"] - data["mismatches"]) / data["total"]) * 100
            print(
                f"Program {program}: {data['total'] - data['mismatches']:,}/{data['total']:,} ({accuracy:.1f}% accurate)"
            )

    # Print recommendations
    print("\n💡 RECOMMENDATIONS")
    print("-" * 20)

    # Find patterns with high error rates and significant volume
    high_error_patterns = [
        (pattern, data["mismatches"], data["total"])
        for pattern, data in pattern_analysis.items()
        if data["mismatches"] > 10 and (data["mismatches"] / data["total"]) > 0.1
    ]

    if high_error_patterns:
        print("Focus on improving these patterns:")
        for pattern, mismatches, total in sorted(high_error_patterns, key=lambda x: x[1], reverse=True)[:5]:
            error_rate = (mismatches / total) * 100
            print(f"  • {pattern} ({mismatches:,} errors, {error_rate:.1f}% error rate)")
    else:
        print("✅ All major patterns have low error rates!")
        print("   Remaining discrepancies are likely edge cases.")

    return {
        "total_records": total_records,
        "perfect_matches": perfect_matches,
        "accuracy_percent": accuracy,
        "discrepancies": discrepancies,
        "pattern_analysis": dict(pattern_analysis),
        "program_analysis": dict(program_analysis),
    }


if __name__ == "__main__":
    generate_variance_report()
