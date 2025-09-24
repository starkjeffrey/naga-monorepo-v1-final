"""Student name parsing utilities for Naga SIS.

This module provides comprehensive name parsing for legacy CSV data that contains
embedded status indicators within student names.

Parsing Rules:
1. Strip off $$ and any non-alpha characters leading up to first alpha of name
2. Take contiguous alpha & spaces string as the name
3. From the first non-alpha after the name -> send this string for post-processing
4. Post-processing indicators:
   - $$ = FROZEN student account (not sponsored!)
   - <sponsor_name> = SPONSORED student with sponsor name (need SIS Sponsor table lookup)
   - {AF} = subject to admin fees
   - Name itself should only contain alpha, spaces, and hyphens

Usage:
    from apps.people.utils.name_parser import parse_student_name, StudentNameData

    result = parse_student_name("$$John Smith<ABC Foundation>$$")
    print(result.clean_name)  # "John Smith"
    print(result.is_sponsored)  # True
    print(result.sponsor_name)  # "ABC Foundation"
    print(result.is_frozen)  # True
"""

import re
from dataclasses import dataclass


@dataclass
class StudentNameData:
    """Parsed student name data with status indicators."""

    clean_name: str
    """The clean name containing only alpha characters, spaces, and hyphens."""

    is_sponsored: bool = False
    """True if student has a sponsor."""

    sponsor_name: str | None = None
    """Name of the sponsor if sponsored student."""

    is_frozen: bool = False
    """True if student account is frozen."""

    has_admin_fees: bool = False
    """True if student is subject to admin fees."""

    raw_indicators: str = ""
    """Raw indicator string found after the name."""

    parsing_warnings: list[str] | None = None
    """List of parsing warnings or issues."""

    def __post_init__(self):
        if self.parsing_warnings is None:
            self.parsing_warnings = []

    @property
    def has_special_status(self) -> bool:
        """True if student has any special status indicators."""
        return self.is_sponsored or self.is_frozen or self.has_admin_fees

    @property
    def status_summary(self) -> str:
        """Human-readable summary of student status."""
        statuses = []
        if self.is_sponsored:
            sponsor = f" ({self.sponsor_name})" if self.sponsor_name else ""
            statuses.append(f"Sponsored{sponsor}")
        if self.is_frozen:
            statuses.append("Frozen")
        if self.has_admin_fees:
            statuses.append("Admin Fees")

        return ", ".join(statuses) if statuses else "Regular"


class StudentNameParser:
    """Parser for student names with embedded status indicators."""

    def __init__(self):
        # Pattern to find first alpha character
        self._first_alpha_pattern = re.compile(r"[A-Za-z]")
        # Pattern for valid name characters (alpha, spaces, and hyphens)
        self._name_pattern = re.compile(r"^[A-Za-z\s\-]+")
        # Pattern for sponsor indicators <something>
        self._sponsor_pattern = re.compile(r"<([^>]*)>")

    def parse(self, raw_name: str) -> StudentNameData:
        """Parse a raw name string according to the defined rules.

        Args:
            raw_name: Raw name string from CSV or input

        Returns:
            StudentNameData object with parsed components
        """
        if not raw_name or not raw_name.strip():
            return StudentNameData(clean_name="", parsing_warnings=["Empty or blank name provided"])

        try:
            # Step 1: Find first alphabetic character
            working_string = raw_name.strip()
            first_alpha_match = self._first_alpha_pattern.search(working_string)

            if not first_alpha_match:
                return StudentNameData(
                    clean_name="",
                    parsing_warnings=[f"No alphabetic characters found in: '{raw_name}'"],
                )

            # Start from first alpha character (strips leading non-alpha)
            start_pos = first_alpha_match.start()
            name_and_indicators = working_string[start_pos:]

            # Step 2: Extract contiguous alpha & spaces as the name
            name_match = self._name_pattern.match(name_and_indicators)
            if not name_match:
                return StudentNameData(
                    clean_name="",
                    parsing_warnings=[f"No valid name pattern found in: '{name_and_indicators}'"],
                )

            # Extract clean name and normalize spaces
            clean_name = self._normalize_name(name_match.group(0))

            # Step 3: Get indicators string (everything after the name)
            name_end_pos = name_match.end()
            indicators_string = name_and_indicators[name_end_pos:]

            # Step 4: Parse status indicators
            result = StudentNameData(clean_name=clean_name, raw_indicators=indicators_string)

            self._parse_status_indicators(indicators_string, result)
            self._validate_parsed_name(result)

            return result

        except Exception as e:
            return StudentNameData(clean_name="", parsing_warnings=[f"Unexpected parsing error: {e!s}"])

    def _normalize_name(self, name: str) -> str:
        """Normalize name by cleaning up spaces."""
        # Remove extra whitespace and normalize spaces
        return " ".join(name.split())

    def _parse_status_indicators(self, indicators: str, result: StudentNameData) -> None:
        """Parse indicator string for status flags."""
        if not indicators:
            return

        # Check for sponsor indicator <something>
        sponsor_matches = self._sponsor_pattern.findall(indicators)
        if sponsor_matches:
            result.is_sponsored = True
            # Use first sponsor found, warn if multiple
            result.sponsor_name = sponsor_matches[0].strip() or None

            if len(sponsor_matches) > 1:
                result.parsing_warnings.append(f"Multiple sponsors found: {sponsor_matches}, using first one")

        # Check for frozen student indicator $$
        if "$$" in indicators:
            result.is_frozen = True

        # Check for admin fees indicator {AF}
        if "{AF}" in indicators:
            result.has_admin_fees = True

    def _validate_parsed_name(self, result: StudentNameData) -> None:
        """Validate that the parsed name meets quality standards."""
        name = result.clean_name

        if not name:
            return

        # Check for any remaining invalid characters
        invalid_chars = re.findall(r"[^A-Za-z\s\-]", name)
        if invalid_chars:
            result.parsing_warnings.append(f"Invalid characters found in name '{name}': {set(invalid_chars)}")

        # Check for unusual patterns that might indicate parsing issues
        if len(name) < 2:
            result.parsing_warnings.append(f"Name is very short: '{name}'")

        if name.upper() == name:
            # All caps - common in legacy data but worth noting
            pass  # This is actually normal for legacy data

        # Check for repeated characters that might indicate data issues
        if re.search(r"(.)\1{3,}", name):  # 4+ repeated characters
            result.parsing_warnings.append(f"Repeated characters in name: '{name}'")


# Module-level convenience function
_parser_instance = StudentNameParser()


def parse_student_name(raw_name: str) -> StudentNameData:
    """Parse a student name string with embedded status indicators.

    This is the main function to use for parsing student names in the application.

    Args:
        raw_name: Raw name string from CSV or user input

    Returns:
        StudentNameData object with parsed name and status information

    Example:
        >>> result = parse_student_name("$$John Smith<ABC Foundation>")
        >>> result.clean_name
        'John Smith'
        >>> result.is_sponsored
        True
        >>> result.sponsor_name
        'ABC Foundation'
        >>> result.is_frozen
        True
    """
    return _parser_instance.parse(raw_name)


def get_clean_name(raw_name: str) -> str:
    """Extract just the clean name from a raw name string.

    Convenience function for when you only need the cleaned name.

    Args:
        raw_name: Raw name string

    Returns:
        Clean name string containing only alpha characters, spaces, and hyphens
    """
    result = parse_student_name(raw_name)
    return result.clean_name


def has_special_status(raw_name: str) -> bool:
    """Check if a name contains any special status indicators.

    Args:
        raw_name: Raw name string

    Returns:
        True if name contains sponsored, frozen, or admin fee indicators
    """
    result = parse_student_name(raw_name)
    return result.has_special_status
