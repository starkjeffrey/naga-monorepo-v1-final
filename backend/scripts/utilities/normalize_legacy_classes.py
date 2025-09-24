#!/usr/bin/env python3
"""Legacy Class Data Normalization Script

This script analyzes the legacy academic classes CSV file and generates
MSSQL UPDATE statements to normalize the course codes and sections.

Usage:
    python normalize_legacy_classes.py

Requirements:
- Input file: backend/data/legacy/all_academicclasses_250719.csv
- Output: MSSQL UPDATE statements for normalization
"""

import csv
import re
from collections import defaultdict
from pathlib import Path


class LegacyClassNormalizer:
    """Normalize legacy class data to standard course codes."""

    def __init__(self):
        self.program_mapping = {
            582: "IEAP",  # IEAP
            632: "GESL",  # GESL and PRE-B1 and PRE-B2
            688: "EHSS",  # EHSS
        }

        self.tod_mapping = {
            "morning": "M",
            "afternoon": "A",
            "evening": "E",
            "weekend": "W",
        }

        # Track patterns for analysis
        self.patterns = defaultdict(list)
        self.unique_patterns = set()

    def normalize_tod(self, schooltime):
        """Convert schooltime to normalized TOD code."""
        if not schooltime:
            return None
        return self.tod_mapping.get(schooltime.lower())

    def parse_des_group_id(self, des_group_id, program):
        """Parse desGroupID to extract course, level, and section info."""
        if not des_group_id:
            return None, None, None, None

        # Clean the input - remove extra whitespace
        cleaned = des_group_id.strip()

        # Initialize return values
        normalized_course = None
        normalized_part = None
        normalized_section = None
        normalized_tod = None

        # Track this pattern
        self.patterns[program].append(cleaned)
        self.unique_patterns.add((program, cleaned))

        self.program_mapping.get(program, "UNKNOWN")

        # Handle different patterns based on program
        if program == 582:  # IEAP
            normalized_course, normalized_part, normalized_section, normalized_tod = self._parse_ieap(cleaned)
        elif program == 632:  # GESL
            normalized_course, normalized_part, normalized_section, normalized_tod = self._parse_gesl(cleaned)
        elif program == 688:  # EHSS
            normalized_course, normalized_part, normalized_section, normalized_tod = self._parse_ehss(cleaned)

        return normalized_course, normalized_part, normalized_section, normalized_tod

    def _parse_ieap(self, cleaned):
        """Parse IEAP (582) patterns."""
        normalized_course = None
        normalized_part = None
        normalized_section = None
        normalized_tod = None

        # Handle NULL
        if cleaned == "NULL":
            return None, None, None, None

        # Handle special cases first
        if cleaned.lower() in ["special-classes"]:
            # Leave blank for manual handling
            return None, None, None, None

        if cleaned.lower() in ["split-class"]:
            normalized_course = "Split-Class"
            return (
                normalized_course,
                normalized_part,
                normalized_section,
                normalized_tod,
            )

        # Handle Pre-Beginner patterns (from analysis)
        if re.match(r"^Pre-Beginner/?([ABCME]?)(\d?)$", cleaned, re.IGNORECASE):
            normalized_course = "Pre-BEG"
            match = re.match(r"^Pre-Beginner/?([ABCME]?)(\d?)$", cleaned, re.IGNORECASE)
            suffix = match.group(1).upper() if match else ""
            if suffix in ["A", "B", "C"]:
                normalized_section = suffix
            elif suffix in ["M", "E"]:
                normalized_tod = suffix

        # Handle beginner patterns
        elif re.match(r"^[EAM]/?Beginner/?[ABC]?$", cleaned, re.IGNORECASE):
            normalized_course = "IEAP-BEG"
            section_match = re.search(r"/([ABC])$", cleaned, re.IGNORECASE)
            if section_match:
                normalized_section = section_match.group(1).upper()

        elif re.match(
            r"^Beginner(-1[MAE]|/?[MABE]|\-[MAE]|/[MAE]\d?|-?Split)$",
            cleaned,
            re.IGNORECASE,
        ):
            normalized_course = "IEAP-BEG"
            # Check for split
            if "split" in cleaned.lower():
                normalized_section = "SPLIT"
            else:
                # Extract section if present (not TOD)
                section_match = re.search(r"/([ABC])$", cleaned, re.IGNORECASE)
                if section_match:
                    normalized_section = section_match.group(1).upper()
                # Handle patterns like BeginnerA/E where A is section, E is TOD
                elif re.search(r"Beginner([ABC])/[EMW]", cleaned, re.IGNORECASE):
                    match = re.search(r"Beginner([ABC])/[EMW]", cleaned, re.IGNORECASE)
                    normalized_section = match.group(1).upper()

        # Handle IEAP- prefixed patterns (already normalized)
        elif re.match(r"^IEAP-(\d+|Beginner)/?([ABCME]?\d?)/?([ABCME]?)$", cleaned, re.IGNORECASE):
            match = re.match(
                r"^IEAP-(\d+|Beginner)/?([ABCME]?\d?)/?([ABCME]?)$",
                cleaned,
                re.IGNORECASE,
            )
            level = match.group(1)
            if level.lower() == "beginner":
                normalized_course = "IEAP-BEG"
            else:
                normalized_course = f"IEAP-{level.zfill(2)}"

            suffix1 = match.group(2).upper() if match.group(2) else ""
            suffix2 = match.group(3).upper() if match.group(3) else ""

            # Handle subsections (E1, E2, M1, M2, etc.)
            if re.match(r"^[EMW](\d+)$", suffix1):
                subsection_num = suffix1[1:]
                if subsection_num == "1":
                    normalized_section = "A"
                elif subsection_num == "2":
                    normalized_section = "B"
                elif subsection_num == "3":
                    normalized_section = "C"
                elif subsection_num == "4":
                    normalized_section = "D"
            # Regular section handling
            elif suffix1 and suffix1[0] in ["A", "B", "C", "D"]:
                normalized_section = suffix1[0]
            elif suffix2 and suffix2 in ["A", "B", "C", "D"]:
                normalized_section = suffix2

        # Handle level patterns like E1A, M2B, A3, etc. (with split handling)
        elif re.match(r"^[MAE]-?(\d+)-?([ABCabc]?)-?(Split)?$", cleaned, re.IGNORECASE):
            match = re.match(r"^[MAE]-?(\d+)-?([ABCabc]?)-?(Split)?$", cleaned, re.IGNORECASE)
            level = match.group(1).zfill(2)
            normalized_course = f"IEAP-{level}"
            if match.group(3) and match.group(3).lower() == "split":
                normalized_section = "SPLIT"
            elif match.group(2):
                normalized_section = match.group(2).upper()

        # Handle patterns with subsections like E/2a, E/2b (case insensitive)
        elif re.match(r"^[MAE]/(\d+)([ABCabc])$", cleaned, re.IGNORECASE):
            match = re.match(r"^[MAE]/(\d+)([ABCabc])$", cleaned, re.IGNORECASE)
            level = match.group(1).zfill(2)
            normalized_course = f"IEAP-{level}"
            normalized_section = match.group(2).upper()

        # Handle GESL patterns in IEAP program (from analysis)
        elif re.match(r"^GESL-(\d+)([ABC]?)$", cleaned, re.IGNORECASE):
            match = re.match(r"^GESL-(\d+)([ABC]?)$", cleaned, re.IGNORECASE)
            level = match.group(1).zfill(2)
            normalized_course = f"GESL-{level}"
            if match.group(2):
                normalized_section = match.group(2).upper()

        return normalized_course, normalized_part, normalized_section, normalized_tod

    def _parse_gesl(self, cleaned):
        """Parse GESL (632) patterns."""
        normalized_course = None
        normalized_part = None
        normalized_section = None
        normalized_tod = None

        # Handle NULL
        if cleaned == "NULL":
            return None, None, None, None

        # Handle Pre-B patterns (Pre-B1, Pre-B2, etc.)
        if re.match(r"^PRE-B(\d+)([ABC]?)$", cleaned, re.IGNORECASE):
            match = re.match(r"^PRE-B(\d+)([ABC]?)$", cleaned, re.IGNORECASE)
            level = match.group(1).zfill(2)
            normalized_course = f"Pre-B-{level}"
            if match.group(2):
                normalized_section = match.group(2).upper()

        elif re.match(r"^Pre-B(\d+)/?([ABCDE]?\d?)/?([ABCDE]?)$", cleaned, re.IGNORECASE):
            match = re.match(r"^Pre-B(\d+)/?([ABCDE]?\d?)/?([ABCDE]?)$", cleaned, re.IGNORECASE)
            level = match.group(1).zfill(2)
            normalized_course = f"Pre-B-{level}"

            # Handle subsections and sections
            suffix1 = match.group(2).upper() if match.group(2) else ""
            suffix2 = match.group(3).upper() if match.group(3) else ""

            # Check for subsections (E1, E2, E3, etc. where E is TOD)
            if re.match(r"^[EMW](\d+)$", suffix1):
                # This is a subsection like E1, E2, E3
                subsection_num = suffix1[1:]
                # Convert numbers to letters: 1->A, 2->B, 3->C, 4->D
                if subsection_num == "1":
                    normalized_section = "A"
                elif subsection_num == "2":
                    normalized_section = "B"
                elif subsection_num == "3":
                    normalized_section = "C"
                elif subsection_num == "4":
                    normalized_section = "D"
            # Extract section from first suffix if it's A,B,C,D (not TOD)
            elif suffix1 and suffix1[0] in ["A", "B", "C", "D"]:
                normalized_section = suffix1[0]
            elif suffix2 and suffix2 in ["A", "B", "C", "D"]:
                normalized_section = suffix2

        elif re.match(r"^Pre-Beginner(\d+)/?([ABC]?)$", cleaned, re.IGNORECASE):
            match = re.match(r"^Pre-Beginner(\d+)/?([ABC]?)$", cleaned, re.IGNORECASE)
            level = match.group(1).zfill(2)
            normalized_course = f"Pre-B-{level}"
            if match.group(2):
                normalized_section = match.group(2).upper()

        # Handle GESL patterns
        elif re.match(r"^GESl?-(\d+)/?([ABCE]?)$", cleaned, re.IGNORECASE):
            match = re.match(r"^GESl?-(\d+)/?([ABCE]?)$", cleaned, re.IGNORECASE)
            level = match.group(1).zfill(2)
            suffix = match.group(2).upper()
            normalized_course = f"GESL-{level}"
            if suffix in ["A", "B", "C"]:
                normalized_section = suffix
            elif suffix == "E":
                normalized_tod = "E"

        # Handle Level patterns (LEVEL-1, Level-1, etc.)
        elif re.match(r"^LEVEL?-(\d+)([ABC]?)$", cleaned, re.IGNORECASE):
            match = re.match(r"^LEVEL?-(\d+)([ABC]?)$", cleaned, re.IGNORECASE)
            level = match.group(1).zfill(2)
            normalized_course = f"GESL-{level}"
            if match.group(2):
                normalized_section = match.group(2).upper()

        # Handle IEAP-style patterns in GESL program (E1A, E2A, etc.)
        elif re.match(r"^[EAM](\d+)([ABC]?)$", cleaned, re.IGNORECASE):
            match = re.match(r"^[EAM](\d+)([ABC]?)$", cleaned, re.IGNORECASE)
            level = match.group(1).zfill(2)
            normalized_course = f"IEAP-{level}"
            if match.group(2):
                normalized_section = match.group(2).upper()

        return normalized_course, normalized_part, normalized_section, normalized_tod

    def _parse_ehss(self, cleaned):
        """Parse EHSS (688) patterns."""
        normalized_course = None
        normalized_part = None
        normalized_section = None
        normalized_tod = None

        # Handle NULL
        if cleaned == "NULL":
            return None, None, None, None

        # Handle special cases
        if cleaned.lower() == "test":
            normalized_course = "Test"

        elif cleaned.lower() in ["split-class", "split-class/ehss-2"]:
            normalized_course = "Split-Class"

        elif re.match(r"^Ventures-(\d+)([ABC]?)$", cleaned, re.IGNORECASE):
            match = re.match(r"^Ventures-(\d+)([ABC]?)$", cleaned, re.IGNORECASE)
            level = match.group(1).zfill(2)
            normalized_course = f"Ventures-{level}"
            if match.group(2):
                normalized_section = match.group(2).upper()

        # Handle EHSS patterns
        elif re.match(r"^[Ee]?[Hh]?[Ss]?[Ss]?-(\d+)([ABCDE]?)$", cleaned, re.IGNORECASE):
            match = re.match(r"^[Ee]?[Hh]?[Ss]?[Ss]?-(\d+)([ABCDE]?)$", cleaned, re.IGNORECASE)
            level = match.group(1).zfill(2)
            suffix = match.group(2).upper()
            normalized_course = f"EHSS-{level}"
            if suffix in ["A", "B", "C", "D"]:
                normalized_section = suffix
            elif suffix == "E":
                normalized_tod = "E"

        # Handle Level patterns in EHSS
        elif re.match(r"^Level-(\d+)([ABC]?)$", cleaned, re.IGNORECASE):
            match = re.match(r"^Level-(\d+)([ABC]?)$", cleaned, re.IGNORECASE)
            level = match.group(1).zfill(2)
            normalized_course = f"EHSS-{level}"
            if match.group(2):
                normalized_section = match.group(2).upper()

        # Handle GESL patterns in EHSS program
        elif re.match(r"^GESL-(\d+)([ABC]?)$", cleaned, re.IGNORECASE):
            match = re.match(r"^GESL-(\d+)([ABC]?)$", cleaned, re.IGNORECASE)
            level = match.group(1).zfill(2)
            normalized_course = f"GESL-{level}"
            if match.group(2):
                normalized_section = match.group(2).upper()

        return normalized_course, normalized_part, normalized_section, normalized_tod

    def analyze_file(self, csv_file_path):
        """Analyze the CSV file and generate UPDATE statements."""
        updates = []

        with open(csv_file_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Skip shadow records
                if row.get("IsShadow") == "1":
                    continue

                program = int(row["Program"])

                # Only process IEAP, GESL, EHSS programs
                if program not in [582, 632, 688]:
                    continue

                class_id = row["ClassID"]
                des_group_id = row["desGroupID"]
                school_time = row["SchoolTime"]

                # Parse the desGroupID
                norm_course, norm_part, norm_section, _norm_tod_from_des = self.parse_des_group_id(
                    des_group_id,
                    program,
                )

                # Normalize TOD from schooltime
                norm_tod_from_time = self.normalize_tod(school_time)

                # Generate UPDATE statement
                if norm_course:
                    update_parts = []
                    update_parts.append(f"NormalizedCourse = '{norm_course}'")

                    if norm_part:
                        update_parts.append(f"NormalizedPart = '{norm_part}'")
                    else:
                        update_parts.append("NormalizedPart = NULL")

                    if norm_section:
                        update_parts.append(f"NormalizedSection = '{norm_section}'")
                    else:
                        update_parts.append("NormalizedSection = NULL")

                    if norm_tod_from_time:
                        update_parts.append(f"NormalizedTOD = '{norm_tod_from_time}'")
                    else:
                        update_parts.append("NormalizedTOD = NULL")

                    update_sql = f"UPDATE all_academicclasses_250719 SET {', '.join(update_parts)} WHERE ClassID = '{class_id}';"
                    updates.append(update_sql)

        return updates

    def print_pattern_analysis(self):
        """Print analysis of patterns found."""
        print("=== PATTERN ANALYSIS ===")
        print()

        for program in sorted(self.patterns.keys()):
            program_name = self.program_mapping.get(program, "UNKNOWN")
            print(f"Program {program} ({program_name}):")

            unique_for_program = set(self.patterns[program])
            for pattern in sorted(unique_for_program):
                count = self.patterns[program].count(pattern)
                print(f"  {pattern!r} (x{count})")
            print()


def main():
    """Main function to run the normalization."""
    script_dir = Path(__file__).parent
    csv_file = script_dir.parent / "data" / "legacy" / "all_academicclasses_250719.csv"

    if not csv_file.exists():
        print(f"Error: CSV file not found at {csv_file}")
        return

    normalizer = LegacyClassNormalizer()

    print("Analyzing legacy class data...")
    updates = normalizer.analyze_file(csv_file)

    print(f"Generated {len(updates)} UPDATE statements")
    print()

    # Print pattern analysis
    normalizer.print_pattern_analysis()

    # Write UPDATE statements to file
    output_file = script_dir / "legacy_class_updates.sql"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("-- Legacy Class Normalization UPDATE Statements\n")
        f.write("-- Generated automatically from all_academicclasses_250719.csv\n")
        f.write("-- Only processes records where IsShadow = 0 and Program in (582, 632, 688)\n\n")

        for update in updates:
            f.write(update + "\n")

    print(f"UPDATE statements written to: {output_file}")

    # Show first few examples
    print("\nFirst 10 UPDATE statements:")
    for i, update in enumerate(updates[:10]):
        print(f"{i + 1:2d}. {update}")


if __name__ == "__main__":
    main()
