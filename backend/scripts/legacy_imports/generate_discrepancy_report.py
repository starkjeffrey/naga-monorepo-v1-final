#!/usr/bin/env python3
"""
Generate a simple discrepancy report showing manual vs automated parsing results.
Output: One line per discrepancy with tab-separated values.
"""

import os
import sys
from pathlib import Path

import django

# Setup Django
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.db import connection

from scripts.legacy_imports.classid_parser import parse_full_classid


def generate_discrepancy_report():
    """Generate tab-delimited discrepancy report."""

    print("Generating discrepancy report for 2021+ manually parsed data...")
    print("(Excluding unparsed records where NormalizedCourse is empty)")

    # Get all manually parsed records from 2021+ (exclude unparsed records)
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                "ClassID",
                "NormalizedCourse",
                "NormalizedPart",
                "NormalizedSection"
            FROM legacy_course_takers
            WHERE "NormalizedCourse" != ''
                AND "NormalizedCourse" IS NOT NULL
                AND "ClassID" IS NOT NULL
                AND "ClassID" != ''
                AND "parsed_termid" >= '21'
                AND "NormalizedCourse" != 'NULL'
                AND TRIM("NormalizedCourse") != ''
            ORDER BY "ClassID"
        """)

        all_records = cursor.fetchall()

    # Generate report file
    output_file = Path("parser_discrepancy_report.txt")

    with open(output_file, "w") as f:
        # Write header
        f.write("ClassID\tManual_Course\tManual_Part\tManual_Section\tParser_Course\tParser_Part\tParser_Section\n")

        discrepancy_count = 0
        total_count = 0

        for record in all_records:
            classid, expected_course, expected_part, expected_section = record
            total_count += 1

            # Parse with our function
            parsed_course, parsed_part, parsed_section = parse_full_classid(classid)

            # Check for discrepancies
            course_match = parsed_course == expected_course
            part_match = parsed_part == expected_part
            section_match = parsed_section == expected_section

            # Only write discrepancies
            if not (course_match and part_match and section_match):
                discrepancy_count += 1

                # Clean up None values for output
                expected_course = expected_course or ""
                expected_part = expected_part or ""
                expected_section = expected_section or ""
                parsed_course = parsed_course or ""
                parsed_part = parsed_part or ""
                parsed_section = parsed_section or ""

                # Write tab-delimited line
                f.write(
                    f"{classid}\t{expected_course}\t{expected_part}\t{expected_section}\t{parsed_course}\t{parsed_part}\t{parsed_section}\n"
                )

    print(f"Report saved to: {output_file.absolute()}")
    print(f"Found {discrepancy_count:,} discrepancies out of {total_count:,} records")
    print(f"Accuracy: {((total_count - discrepancy_count) / total_count * 100):.1f}%")


if __name__ == "__main__":
    generate_discrepancy_report()
