"""
Field Parsers for Complex Data

Specialized parsers for handling complex fields like ClassID.
"""

import re
from typing import Any


class ClassIDParser:
    """Parser for complex ClassID fields in enrollment data"""

    # Program code mappings
    PROGRAM_CODES = {
        "582": "IEAP",
        "583": "GEP",
        "584": "ESP",
        # Add more as needed
    }

    # Level mappings
    LEVEL_MAPPINGS = {
        "BEGINNER": "BEG",
        "E-BEGINNER": "BEG",
        "INTERMEDIATE": "INT",
        "ADVANCED": "ADV",
    }

    def parse(self, classid: str, time_slot: str | None = None) -> dict[str, Any]:
        """
        Parse ClassID into components.

        Examples:
            'XXX-582-2024S1-E-BEGINNER-XXX' → {program: 'IEAP', level: 'BEG', ...}
            'XXX-582-2024S1-E/2A-XXX' → {program: 'IEAP', level: '02', section: 'A', ...}
        """
        if not classid:
            return {"error": "Empty ClassID"}

        parts = str(classid).split("-")

        if len(parts) < 4:
            return {
                "error": "Invalid ClassID format",
                "original": classid,
                "confidence": "LOW",
            }

        result = {"original": classid, "confidence": "HIGH"}

        # Parse each part
        result.update(self._parse_program(parts[1] if len(parts) > 1 else None))
        result.update(self._parse_term(parts[2] if len(parts) > 2 else None))
        result.update(self._parse_level_section(parts[3] if len(parts) > 3 else None, time_slot))

        # Generate course code
        if result.get("program") and result.get("level"):
            result["course_code"] = f"{result['program']}-{result['level']}"

        return result

    def _parse_program(self, program_part: str) -> dict[str, str]:
        """Parse program code"""
        if not program_part:
            return {"program": None}

        return {
            "program": self.PROGRAM_CODES.get(program_part, program_part),
            "program_code": program_part,
        }

    def _parse_term(self, term_part: str) -> dict[str, str]:
        """Parse term identifier"""
        if not term_part:
            return {"term": None}

        # Parse patterns like 2024S1, 2024F, etc.
        match = re.match(r"(\d{4})([SF])(\d)?", term_part)
        if match:
            year = match.group(1)
            semester = "Spring" if match.group(2) == "S" else "Fall"
            section = match.group(3) or ""

            return {
                "term": term_part,
                "year": year,
                "semester": semester,
                "term_section": section,
            }

        return {"term": term_part}

    def _parse_level_section(self, level_part: str, time_slot: str | None) -> dict[str, Any]:
        """Parse the complex level/section part"""
        if not level_part:
            return {"level": None, "section": None}

        result = {}

        # Pattern 1: "E-BEGINNER" (time-level)
        if "-" in level_part:
            parts = level_part.split("-")

            # First part might be time indicator
            if parts[0] in ["E", "M", "A"]:
                result["time_indicator"] = parts[0]
                level_str = parts[1] if len(parts) > 1 else ""
            else:
                level_str = level_part

            # Map level
            result["level"] = self.LEVEL_MAPPINGS.get(level_str, level_str)
            result["confidence"] = "HIGH"

        # Pattern 2: "E/2A" (time/level-section)
        elif "/" in level_part:
            parts = level_part.split("/")

            # First part might be time
            if parts[0] in ["E", "M", "A"]:
                result["time_indicator"] = parts[0]
                level_section = parts[1] if len(parts) > 1 else ""
            else:
                level_section = level_part.replace("/", "")

            # Parse level and section from "2A" pattern
            match = re.match(r"^(\d+)([A-D])?$", level_section)
            if match:
                result["level"] = f"{int(match.group(1)):02d}"
                if match.group(2):
                    result["section"] = match.group(2)
            else:
                result["level"] = level_section

            result["confidence"] = "MEDIUM"

        # Pattern 3: "2A" (level-section)
        else:
            match = re.match(r"^(\d+)([A-D])?$", level_part)
            if match:
                result["level"] = f"{int(match.group(1)):02d}"
                if match.group(2):
                    result["section"] = match.group(2)
                result["confidence"] = "HIGH"
            else:
                # Might be a named level
                result["level"] = self.LEVEL_MAPPINGS.get(level_part, level_part)
                result["confidence"] = "LOW"

        # Use time_slot to validate/enhance time_indicator
        if time_slot and "time_indicator" not in result:
            if "evening" in time_slot.lower():
                result["time_indicator"] = "E"
            elif "morning" in time_slot.lower():
                result["time_indicator"] = "M"
            elif "afternoon" in time_slot.lower():
                result["time_indicator"] = "A"

        return result


class StudentNameParser:
    """Parser for student names with Khmer/English components"""

    def parse(self, name: str, language: str = "unknown") -> dict[str, str]:
        """Parse student name into components"""
        # Implementation here
        pass
