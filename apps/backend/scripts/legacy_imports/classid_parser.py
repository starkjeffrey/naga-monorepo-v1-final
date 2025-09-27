#!/usr/bin/env python3
"""
ClassID Parser for Legacy Course Takers

Parses the 4th section of ClassID to extract:
- NormalizedCourse (e.g., EHSS-1 -> EHSS-01)
- NormalizedSection (A-D letters)
- NormalizedPart (5th section of ClassID)

Tests against existing manual parsing for 2020+ records.
"""

import os
import re
import sys
from pathlib import Path

import django

# Setup Django
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.db import connection


def parse_classid_part4(part4: str) -> tuple[str | None, str | None]:
    """
    Parse the 4th part of ClassID to extract course code and section.

    Args:
        part4: The 4th section of ClassID (e.g., "EHSS-1A", "E1-A", "E/BEGINNER")

    Returns:
        Tuple of (normalized_course, normalized_section)

    Examples:
        "EHSS-1A" -> ("EHSS-01", "A")
        "E1-A" -> ("IEAP-01", "A")  # E courses are IEAP
        "E/BEGINNER" -> ("IEAP-BEG", "")
        "EHSS-1E" -> ("EHSS-01", "") # E is evening, not section
    """
    if not part4 or part4.strip() == "":
        return None, None

    part4 = part4.strip()

    # Handle edge cases
    if part4 in ["SPLIT", "NULL", "N/A", ""]:
        return None, None

    normalized_course = None
    normalized_section = None

    # Handle 2021+ patterns first (more structured)

    # Academic program indicators - course code is in 5th part, return None here
    if part4 in ["MBA", "MED", "SENIOR_PROJECT"]:
        return None, None  # Course code comes from 5th part for academic programs

    # Pattern: IEAP course with time suffix (IEAP-1/M, IEAP-2/E, etc.)
    # Remove time suffix, use time_slot field instead
    match = re.match(r"^IEAP-(\d+)/[AME]$", part4)
    if match:
        course_number = match.groups()[0]
        return f"IEAP-{course_number.zfill(2)}", ""

    # Pattern: IEAP-BEGINNER with time suffix (IEAP-BEGINNER/M, IEAP-BEGINNER/E)
    match = re.match(r"^IEAP-BEGINNER/[AME]$", part4)
    if match:
        return "IEAP-BEG", ""

    # Pattern: BEGINNER with section (BEGINNER/A, BEGINNER/B, etc.) - section comes after punctuation
    match = re.match(r"^BEGINNER/([A-D])$", part4)
    if match:
        section = match.groups()[0]
        return "IEAP-BEG", section

    # Pattern: BEGINNER with time suffix (BEGINNER/M, BEGINNER/E) - maps to IEAP-BEG for program 582
    match = re.match(r"^BEGINNER/[ME]$", part4)
    if match:
        return "IEAP-BEG", ""

    # Pattern: Simple BEGINNER (no time suffix) - maps to IEAP-BEG for program 582
    if part4 == "BEGINNER":
        return "IEAP-BEG", ""

    # Pattern: PRE-BEGINNER with section (PRE-BEGINNER/A, PRE-BEGINNER/B, etc.) - section comes after punctuation
    match = re.match(r"^PRE-BEGINNER/([A-D])$", part4)
    if match:
        section = match.groups()[0]
        return "IEAP-PRE", section

    # Pattern: PRE-BEGINNER with time suffix (PRE-BEGINNER/M, PRE-BEGINNER/E) - maps to IEAP-PRE for program 582
    match = re.match(r"^PRE-BEGINNER/[ME]$", part4)
    if match:
        return "IEAP-PRE", ""

    # Pattern: Simple PRE-BEGINNER - maps to IEAP-PRE for program 582
    if part4 == "PRE-BEGINNER":
        return "IEAP-PRE", ""

    # IMPORTANT: PRE-BEGINNER patterns must come BEFORE general PRE- patterns!
    # Pattern: Compact PRE-BEGINNER with section + time (PRE-BEGINNERA/E, PRE-BEGINNERB/M)
    # Format: PRE-BEGINNER + section letter + /time → Course: IEAP-PRE, Section: A/B/C/D
    match = re.match(r"^PRE-BEGINNER([A-D])/[AME]$", part4)
    if match:
        section = match.groups()[0]
        return "IEAP-PRE", section

    # Pattern: PRE-course with section (PRE-B2/A, PRE-B2/B, etc.)
    match = re.match(r"^(PRE-[A-Z0-9]+)/([A-D])$", part4)
    if match:
        course_code, section = match.groups()
        return course_code, section

    # Pattern: PRE-course with time/other (PRE-B2/E1, PRE-B2/E, etc.)
    match = re.match(r"^(PRE-[A-Z0-9]+)/(.+)$", part4)
    if match:
        course_code, _suffix = match.groups()
        return course_code, ""

    # Pattern: PRE-course with attached section (PRE-B2A, PRE-B1B, etc.) - section letter is attached
    match = re.match(r"^(PRE-[A-Z0-9]+)([A-D])$", part4)
    if match:
        course_code, section = match.groups()
        return course_code, section

    # Pattern: Simple PRE-course (PRE-B2, PRE-B1, etc.)
    match = re.match(r"^(PRE-[A-Z0-9]+)$", part4)
    if match:
        course_code = match.groups()[0]
        return course_code, ""

    # Pattern: XPRESS courses (XPRESS-LEVEL-1, XPRESS-LEVEL-2, etc.)
    match = re.match(r"^XPRESS-LEVEL-(\d+)$", part4)
    if match:
        level = match.groups()[0]
        return f"EXPRESS-{level.zfill(2)}", ""

    # Pattern: IEAP course with section (IEAP-3A, IEAP-4B -> IEAP-03 section A, IEAP-04 section B)
    match = re.match(r"^IEAP-(\d+)([A-D])$", part4)
    if match:
        course_number, section = match.groups()
        return f"IEAP-{course_number.zfill(2)}", section

    # Pattern: IEAP course with time-of-day suffix (IEAP-4M, IEAP-4E -> IEAP-04, no section)
    match = re.match(r"^IEAP-(\d+)[ME]$", part4)
    if match:
        course_number = match.groups()[0]
        return f"IEAP-{course_number.zfill(2)}", ""

    # Pattern: Compact beginner with letter suffix (BEGINNERA/E, BEGINNERB/E)
    # Note: The letter is NOT a section, it's part of the course designation
    match = re.match(r"^BEGINNER[A-D]/[AME]$", part4)
    if match:
        return "IEAP-BEG", ""

    # Pattern: BEGINNER with section but no time (BEGINNER/B)
    match = re.match(r"^BEGINNER/([A-D])$", part4)
    if match:
        section = match.groups()[0]
        return "IEAP-BEG", section

    # Pattern: FREE courses - special case for FREE-COMP
    if part4 == "FREE-COMP":
        return "IEAP-COMP", ""

    # Pattern: FREE courses (FREE/COMPUTER -> IEAP-COMP, other FREE courses as-is)
    match = re.match(r"^FREE/(.+)$", part4)
    if match:
        course_type = match.groups()[0]
        if course_type == "COMPUTER":
            return "IEAP-COMP", ""
        return f"FREE-{course_type}", ""

    # Pattern: IEAP course with section and time (IEAP-4A/E)
    match = re.match(r"^IEAP-(\d+)([A-D])/[AME]$", part4)
    if match:
        course_number, section = match.groups()
        return f"IEAP-{course_number.zfill(2)}", section

    # Special handling for E-prefix courses (IEAP)
    if part4.startswith("E"):
        # Pattern 1: E/BEGINNER -> IEAP-BEG
        if part4 == "E/BEGINNER":
            return "IEAP-BEG", ""

        # Pattern 2: E-2A, E-1B, etc. -> IEAP-01, IEAP-02 with section
        match = re.match(r"^E-(\d+)([A-D])$", part4)
        if match:
            course_number, section = match.groups()
            return f"IEAP-{course_number.zfill(2)}", section

        # Pattern 3: E1-A, E2-B, etc. -> IEAP-01, IEAP-02 with section
        match = re.match(r"^E(\d+)-([A-D])$", part4)
        if match:
            course_number, section = match.groups()
            return f"IEAP-{course_number.zfill(2)}", section

        # Pattern 4: E-2, E-1, etc. -> IEAP-01, IEAP-02 (no section)
        match = re.match(r"^E-(\d+)$", part4)
        if match:
            course_number = match.groups()[0]
            return f"IEAP-{course_number.zfill(2)}", ""

        # Pattern 5: E1, E2, etc. -> IEAP-01, IEAP-02 (no section)
        match = re.match(r"^E(\d+)$", part4)
        if match:
            course_number = match.groups()[0]
            return f"IEAP-{course_number.zfill(2)}", ""

        # Pattern 6: E1E -> IEAP-01 (Evening, no section)
        match = re.match(r"^E(\d+)E$", part4)
        if match:
            course_number = match.groups()[0]
            return f"IEAP-{course_number.zfill(2)}", ""

    # Standard patterns for other courses
    patterns = [
        # Pattern 1: COURSE-NUMBER/SECTION (e.g., EHSS-1/A)
        r"^([A-Z]+)-(\d+)/([A-D])$",
        # Pattern 2: COURSE-NUMBERSECTION (e.g., EHSS-1A)
        r"^([A-Z]+)-(\d+)([A-D])$",
        # Pattern 3: COURSE-NUMBERE (E = Evening, not section)
        r"^([A-Z]+)-(\d+)E$",
        # Pattern 4: COURSE-NUMBER (no section)
        r"^([A-Z]+)-(\d+)$",
        # Pattern 5: Complex course codes (e.g., IEAP-BEGINNER)
        r"^([A-Z]+)-([A-Z]+)$",
    ]

    # Try each pattern
    for i, pattern in enumerate(patterns):
        match = re.match(pattern, part4)
        if match:
            if i == 0:  # COURSE-NUMBER/SECTION
                course_prefix, course_number, section = match.groups()
                normalized_course = f"{course_prefix}-{course_number.zfill(2)}"
                normalized_section = section
            elif i == 1:  # COURSE-NUMBERSECTION
                course_prefix, course_number, section = match.groups()
                normalized_course = f"{course_prefix}-{course_number.zfill(2)}"
                normalized_section = section
            elif i == 2:  # COURSE-NUMBERE (Evening)
                course_prefix, course_number = match.groups()
                normalized_course = f"{course_prefix}-{course_number.zfill(2)}"
                normalized_section = ""  # E is evening, not section
            elif i == 3:  # COURSE-NUMBER
                course_prefix, course_number = match.groups()
                normalized_course = f"{course_prefix}-{course_number.zfill(2)}"
                normalized_section = ""
            elif i == 4:  # Complex course codes like IEAP-BEGINNER
                course_prefix, course_suffix = match.groups()
                # Special handling for known patterns
                if course_suffix == "BEGINNER":
                    normalized_course = f"{course_prefix}-BEG"
                elif course_suffix == "INTERMEDIATE":
                    normalized_course = f"{course_prefix}-INT"
                elif course_suffix == "ADVANCED":
                    normalized_course = f"{course_prefix}-ADV"
                else:
                    normalized_course = f"{course_prefix}-{course_suffix}"
                normalized_section = ""
            break

    # If no pattern matched, try to handle manually
    if normalized_course is None:
        # Handle special cases or log for manual review
        print(f"⚠️  Could not parse: '{part4}'")
        return None, None

    return normalized_course, normalized_section


# Program to course prefix mapping for validation
PROGRAM_COURSE_MAPPING = {
    "582": ["IEAP", "E"],  # IEAP program, E courses map to IEAP
    "632": ["GESL", "PRE"],  # GESL program, includes predecessor courses (confirmed correct)
    "688": ["EHSS", "PRE"],  # EHSS program, includes predecessor courses
    "87": ["COMEX", "ECON", "EDUC", "ACAD"],  # BA program (various prefixes)
    "147": ["COMEX", "ECON", "EDUC", "ACAD"],  # MA program (various prefixes)
    "1187": ["EXPRESS", "XPRESS"],  # EXPRESS program (handles XPRESS courses)
    "1427": ["JAP", "KANJI"],  # Japanese language program
    "2076": ["IEAP", "FREE"],  # FREE program (maps to IEAP for FREE/COMPUTER courses)
    # Additional programs can be added as discovered
}


def validate_course_program_match(program: str, course_code: str) -> bool:
    """
    Validate that the course code matches the expected program.

    Args:
        program: Program code (e.g., "582", "632", "688")
        course_code: Parsed course code (e.g., "IEAP-01", "GESL-02", "PRE-B1")

    Returns:
        True if course matches program, False otherwise
    """
    if not program or not course_code:
        return True  # Skip validation if missing data

    # Handle EXPRESS programs (12*)
    if program.startswith("12"):
        # EXPRESS courses - need to define expected prefixes
        return True  # For now, accept all EXPRESS courses

    expected_prefixes = PROGRAM_COURSE_MAPPING.get(program, [])
    if not expected_prefixes:
        return True  # Unknown program, skip validation

    # Extract course prefix from course code
    if "-" in course_code:
        course_prefix = course_code.split("-")[0]
    else:
        course_prefix = course_code

    return course_prefix in expected_prefixes


def parse_full_classid(classid: str) -> tuple[str | None, str | None, str | None]:
    """
    Parse full ClassID to extract normalized course, part, and section.

    Args:
        classid: Full ClassID (e.g., "250804E-T3BE!$688!$E!$EHSS-4A!$V-2B")

    Returns:
        Tuple of (normalized_course, normalized_part, normalized_section)

    Logic:
        Academic classes (87, 147, 688):
            - 4th part has course+section, 5th part is content description
            - NormalizedCourse from 4th, NormalizedPart from 5th, NormalizedSection from 4th
        Language classes (582=IEAP, 632=GESL, 12*=EXPRESS):
            - 4th part is level description, 5th part is course code
            - NormalizedCourse from 5th, NormalizedPart from 4th, no section
    """
    if not classid or classid.strip() == "":
        return None, None, None

    # Split ClassID by !$
    parts = classid.split("!$")

    if len(parts) < 4:
        return None, None, None

    # Get program (2nd part) to determine if Academic or Language
    program = parts[1] if len(parts) > 1 else ""
    part4 = parts[3] if len(parts) > 3 else ""
    part5 = parts[4] if len(parts) > 4 else ""

    # Determine if Academic or Language program
    is_academic = program in ["87", "147"]  # BA and Masters programs
    is_language = program in ["582", "632", "688", "1427", "1187", "2076"] or program.startswith(
        "12"
    )  # 688 = EHSS = Language for High School

    if is_academic:
        # Academic (BA/Masters): Use 5th part as-is for course code, 4th part is content description
        normalized_course = part5 if part5 else None
        normalized_part = part4  # Program indicator (MBA, MED, etc.)
        normalized_section = ""  # Academic classes typically don't have sections like A, B, C

        return normalized_course, normalized_part, normalized_section

    elif is_language:
        # Language: Parse 4th part for course+section, 5th part is content description
        normalized_course, normalized_section = parse_classid_part4(part4)
        normalized_part = part5  # Content description is in 5th part

        # Validate course matches program
        if normalized_course and not validate_course_program_match(program, normalized_course):
            print(f"⚠️  Course/Program mismatch: {normalized_course} in program {program} ({classid})")

        return normalized_course, normalized_part, normalized_section

    else:
        # Unknown program type, try academic logic as fallback
        normalized_course, normalized_section = parse_classid_part4(part4)
        normalized_part = part5

        print(f"⚠️  Unknown program type: {program} in {classid}")

        return normalized_course, normalized_part, normalized_section


def test_parser_accuracy():
    """Test parser against existing manual parsing for 2020+ records."""

    print("🧪 Testing ClassID Parser Accuracy")
    print("=" * 60)

    # Get existing manually parsed records from 2020+
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
                AND "parsed_termid" >= '20'
            ORDER BY "ClassID"
            LIMIT 100
        """)

        test_records = cursor.fetchall()

    total_tests = 0
    course_matches = 0
    part_matches = 0
    section_matches = 0
    perfect_matches = 0

    errors = []

    for record in test_records:
        classid, expected_course, expected_part, expected_section = record

        # Parse with our function
        parsed_course, parsed_part, parsed_section = parse_full_classid(classid)

        total_tests += 1

        # Check matches
        course_match = parsed_course == expected_course
        part_match = parsed_part == expected_part
        section_match = parsed_section == expected_section

        if course_match:
            course_matches += 1
        if part_match:
            part_matches += 1
        if section_match:
            section_matches += 1
        if course_match and part_match and section_match:
            perfect_matches += 1

        # Log errors
        if not (course_match and part_match and section_match):
            error = {
                "classid": classid,
                "expected": (expected_course, expected_part, expected_section),
                "parsed": (parsed_course, parsed_part, parsed_section),
                "course_match": course_match,
                "part_match": part_match,
                "section_match": section_match,
            }
            errors.append(error)

    # Print results
    print(f"📊 Test Results ({total_tests} records)")
    print("-" * 40)
    print(f"Course accuracy: {course_matches}/{total_tests} ({course_matches / total_tests * 100:.1f}%)")
    print(f"Part accuracy: {part_matches}/{total_tests} ({part_matches / total_tests * 100:.1f}%)")
    print(f"Section accuracy: {section_matches}/{total_tests} ({section_matches / total_tests * 100:.1f}%)")
    print(f"Perfect matches: {perfect_matches}/{total_tests} ({perfect_matches / total_tests * 100:.1f}%)")

    # Show first few errors
    if errors:
        print(f"\n❌ First {min(10, len(errors))} errors:")
        for i, error in enumerate(errors[:10]):
            print(f"{i + 1}. {error['classid']}")
            print(f"   Expected: {error['expected']}")
            print(f"   Parsed:   {error['parsed']}")
            print()

    return {
        "total_tests": total_tests,
        "course_accuracy": course_matches / total_tests,
        "part_accuracy": part_matches / total_tests,
        "section_accuracy": section_matches / total_tests,
        "perfect_accuracy": perfect_matches / total_tests,
        "errors": errors,
    }


def parse_unparsed_records():
    """Parse the unparsed records (high IPK values) and show results."""

    print("\n🎯 Parsing Unparsed Records")
    print("=" * 60)

    # Get unparsed records
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                "IPK",
                "ClassID"
            FROM legacy_course_takers
            WHERE ("NormalizedCourse" = '' OR "NormalizedCourse" IS NULL)
                AND "ClassID" IS NOT NULL
                AND "ClassID" != ''
            ORDER BY CAST("IPK" AS INTEGER) DESC
            LIMIT 50
        """)

        unparsed_records = cursor.fetchall()

    print(f"📄 Found {len(unparsed_records)} unparsed records")

    results = []
    for ipk, classid in unparsed_records:
        parsed_course, parsed_part, parsed_section = parse_full_classid(classid)

        result = {
            "ipk": ipk,
            "classid": classid,
            "normalized_course": parsed_course,
            "normalized_part": parsed_part,
            "normalized_section": parsed_section,
        }
        results.append(result)

        print(f"IPK {ipk}: {classid}")
        print(f"  → Course: {parsed_course}, Part: {parsed_part}, Section: {parsed_section}")

    return results


def find_discrepancies():
    """Find discrepancies between parser and manual work for 2021+ data."""

    print("\n🔍 Finding Discrepancies Between Parser and Manual Work (2021+ only)")
    print("=" * 70)

    # Get manually parsed records from 2021 onwards only
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
                AND "parsed_termid" >= '21'  -- Focus on 2021+ data only
            ORDER BY "ClassID"
        """)

        all_records = cursor.fetchall()

    print(f"📄 Analyzing {len(all_records)} manually parsed records...")

    discrepancies = []

    for record in all_records:
        classid, expected_course, expected_part, expected_section = record

        # Parse with our function
        parsed_course, parsed_part, parsed_section = parse_full_classid(classid)

        # Check for discrepancies
        course_match = parsed_course == expected_course
        part_match = parsed_part == expected_part
        section_match = parsed_section == expected_section

        if not (course_match and part_match and section_match):
            discrepancy = {
                "classid": classid,
                "expected": (expected_course, expected_part, expected_section),
                "parsed": (parsed_course, parsed_part, parsed_section),
                "course_match": course_match,
                "part_match": part_match,
                "section_match": section_match,
            }
            discrepancies.append(discrepancy)

    # Print summary
    print("\n📊 DISCREPANCY ANALYSIS")
    print("-" * 50)

    if discrepancies:
        print(f"❌ Found {len(discrepancies)} discrepancies:")

        # Group by type of discrepancy
        course_issues = [d for d in discrepancies if not d["course_match"]]
        part_issues = [d for d in discrepancies if not d["part_match"]]
        section_issues = [d for d in discrepancies if not d["section_match"]]

        print(f"  Course mismatches: {len(course_issues)}")
        print(f"  Part mismatches: {len(part_issues)}")
        print(f"  Section mismatches: {len(section_issues)}")

        print("\n📋 First 20 discrepancies:")
        for i, disc in enumerate(discrepancies[:20]):
            print(f"\n{i + 1}. FULL ClassID: {disc['classid']}")
            print(
                f"   Manual:  Course={disc['expected'][0]}, Part={disc['expected'][1]}, Section={disc['expected'][2]}"
            )
            print(f"   Parsed:  Course={disc['parsed'][0]}, Part={disc['parsed'][1]}, Section={disc['parsed'][2]}")

            # Show what differs
            issues = []
            if not disc["course_match"]:
                issues.append("Course")
            if not disc["part_match"]:
                issues.append("Part")
            if not disc["section_match"]:
                issues.append("Section")
            print(f"   Issues: {', '.join(issues)}")

            # Parse ClassID to show the parts for interpretation
            parts = disc["classid"].split("!$")
            if len(parts) >= 5:
                print(
                    f"   ClassID Breakdown: Term={parts[0]}, Program={parts[1]}, Major={parts[2]}, Part4={parts[3]}, Part5={parts[4]}"
                )
            elif len(parts) >= 4:
                print(
                    f"   ClassID Breakdown: Term={parts[0]}, Program={parts[1]}, Major={parts[2]}, Part4={parts[3]}, Part5=(missing)"
                )
    else:
        print("✅ No discrepancies found! Parser matches manual work 100%")

    return discrepancies


def main():
    """Main execution function."""
    import argparse

    parser = argparse.ArgumentParser(description="Parse ClassID and test accuracy")
    parser.add_argument("--test", action="store_true", help="Test parser accuracy against existing data")
    parser.add_argument("--parse", action="store_true", help="Parse unparsed records")
    parser.add_argument(
        "--discrepancies", action="store_true", help="Find all discrepancies between parser and manual work"
    )
    parser.add_argument("--classid", help="Parse a specific ClassID")

    args = parser.parse_args()

    if args.classid:
        course, part, section = parse_full_classid(args.classid)
        print(f"ClassID: {args.classid}")
        print(f"Course: {course}")
        print(f"Part: {part}")
        print(f"Section: {section}")

    elif args.test:
        test_parser_accuracy()

    elif args.parse:
        parse_unparsed_records()

    elif args.discrepancies:
        find_discrepancies()

    else:
        # Run both by default
        test_parser_accuracy()
        parse_unparsed_records()


if __name__ == "__main__":
    main()
