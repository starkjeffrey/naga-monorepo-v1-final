# data_pipeline/core/transformations/education.py
import re
from typing import Any

from .base import BaseTransformer, TransformationContext


class CambodianEducationTransformer(BaseTransformer):
    """
    Transformations specific to the Cambodian education system.
    This handles academic terms, course codes, and other education-specific conversions.
    """

    def _initialize(self):
        """Set up education-specific mappings and patterns."""
        # Map old course codes to new curriculum
        self.course_mappings = {
            "ENG101": "ENGL1301",
            "MATH101": "MATH1301",
            # Add your complete mappings
        }

        # Academic term patterns
        self.term_patterns = {
            "S1": "Spring",
            "S2": "Fall",
            "S3": "Summer",
        }

        # Student type mappings
        self.student_type_map = {
            "R": "regular",
            "T": "transfer",
            "I": "international",
            "E": "exchange",
        }

    def can_transform(self, value: Any) -> bool:
        """Check if the value is something we can transform."""
        return isinstance(value, str) and bool(value)

    def transform(self, value: str, context: TransformationContext) -> Any:
        """
        Route to appropriate transformation based on context.
        This is like a traffic controller directing data to the right transformation.
        """
        column = context.source_column.lower()

        if "course" in column or "class" in column:
            return self.transform_course_code(value)
        elif "term" in column:
            return self.transform_term_code(value)
        elif "student_type" in column:
            return self.transform_student_type(value)
        else:
            return value

    def transform_course_code(self, old_code: str) -> str:
        """Transform legacy course codes to new curriculum codes."""
        # First try direct mapping
        if old_code in self.course_mappings:
            return self.course_mappings[old_code]

        # Try pattern-based transformation
        # For example: "CS101-L" might become "COMP1301-LAB"
        if "-L" in old_code:
            base_code = old_code.replace("-L", "")
            if base_code in self.course_mappings:
                return f"{self.course_mappings[base_code]}-LAB"

        # Return original if no mapping found
        return old_code

    def transform_term_code(self, term_code: str) -> dict[str, Any]:
        """
        Parse term codes into structured data.
        Example: "2024S1" -> {"year": 2024, "semester": "Spring", "code": "2024SP"}
        """
        # Extract year and semester
        year_match = re.search(r"(\d{4})", term_code)
        semester_match = re.search(r"S(\d)", term_code)

        if year_match and semester_match:
            year = int(year_match.group(1))
            semester_num = semester_match.group(1)
            semester_name = self.term_patterns.get(f"S{semester_num}", "Unknown")

            # Create standardized code
            semester_abbrev = {"Spring": "SP", "Fall": "FA", "Summer": "SU"}.get(semester_name, "XX")

            return {"year": year, "semester": semester_name, "code": f"{year}{semester_abbrev}", "original": term_code}

        return {"original": term_code, "error": "Could not parse"}

    def transform_student_type(self, type_code: str) -> str:
        """Transform single-letter student type codes to full descriptions."""
        return self.student_type_map.get(type_code.upper(), "unknown")
