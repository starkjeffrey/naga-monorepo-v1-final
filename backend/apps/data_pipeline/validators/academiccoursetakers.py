"""
Academic Course Takers Table Validator

Pydantic model for validating Academic Course Takers data after cleaning.
Enforces business rules for student enrollments, grades, and academic performance.
"""

import re

from pydantic import BaseModel, Field, field_validator, model_validator


class AcademicCourseTakerValidator(BaseModel):
    """
    Pydantic validator for Academic Course Takers table records.

    Validates student course enrollments with strict academic integrity rules
    for grades, credits, and GPA calculations.
    """

    # Primary identifiers - critical for joins
    student_id: str = Field(..., min_length=1, max_length=10, description="Student ID reference")
    class_id: str = Field(..., min_length=1, max_length=255, description="Academic class section identifier")

    # Academic performance - core data
    repeat_count: int | None = Field(None, ge=0, le=10, description="Number of times course was repeated")
    lab_score: float | None = Field(None, ge=0, le=100, description="Laboratory component score")
    unit_score: float | None = Field(None, ge=0, le=100, description="Unit test score")
    credit_hours: int | None = Field(None, ge=0, le=20, description="Credit hours for course")
    grade_points: float | None = Field(None, ge=0, le=4.0, description="Grade points earned (GPA scale)")
    total_points: float | None = Field(None, ge=0, description="Total points calculation")
    final_grade: str | None = Field(None, max_length=10, description="Final letter grade")
    previous_grade: str | None = Field(None, max_length=10, description="Previous grade if repeated")
    is_passed: bool | None = Field(None, description="Whether student passed the course")

    # Registration details
    registration_mode: str | None = Field(None, max_length=20, description="Registration method")
    attendance_status: str | None = Field(None, max_length=20, description="Attendance status")

    # Comments and notes
    instructor_comment: str | None = Field(None, max_length=100, description="Instructor comments")
    administrative_remarks: str | None = Field(None, max_length=50, description="Administrative remarks")
    quick_note: str | None = Field(None, max_length=50, description="Quick note")

    # Parsed course information
    parsed_term_id: str | None = Field(None, max_length=255, description="Parsed term ID from class_id")
    parsed_course_code: str | None = Field(None, max_length=255, description="Parsed course code")

    # Legacy system identifier
    legacy_id: int | None = Field(None, description="Legacy system auto-increment primary key (renamed from IPK)")

    # Timestamps
    added_timestamp: str | None = Field(None, description="When enrollment was added (string representation)")
    last_updated: str | None = Field(None, description="Last update timestamp (string representation)")

    class Config:
        """Pydantic configuration"""

        str_strip_whitespace = True
        validate_assignment = True
        extra = "ignore"  # Ignore extra fields like parsed columns and processing metadata

    @field_validator("student_id")
    @classmethod
    def validate_student_id_format(cls, v):
        """Validate student ID format"""
        if not v or not v.strip():
            raise ValueError("student_id cannot be empty")

        v = v.strip().upper()

        # Should be alphanumeric and reasonable length
        if not re.match(r"^[A-Z0-9]+$", v):
            raise ValueError("student_id should contain only letters and numbers")

        if len(v) < 3 or len(v) > 10:
            raise ValueError("student_id length should be 3-10 characters")

        return v

    @field_validator("class_id")
    @classmethod
    def validate_class_id_format(cls, v):
        """Validate class ID format"""
        if not v or not v.strip():
            raise ValueError("class_id cannot be empty")

        v = v.strip().upper()

        # Class IDs should be reasonable length and contain identifiable components
        if len(v) < 5:
            raise ValueError("class_id appears too short")

        # Should contain some pattern like course-section-term
        # Common patterns: ENG101-001-2009T1, HIST200-A-2010T1
        if not re.search(r"[A-Z]{2,}[0-9]{2,}", v):
            # Not matching expected course code pattern, but allow with warning
            pass

        return v

    @field_validator("final_grade", "previous_grade")
    @classmethod
    def validate_grade_values(cls, v):
        """Validate grade values against standard grading scale"""
        if v is not None:
            v = v.strip().upper()
            if len(v) == 0:
                return None

            # Standard letter grades
            valid_grades = {
                "A+",
                "A",
                "A-",
                "B+",
                "B",
                "B-",
                "C+",
                "C",
                "C-",
                "D+",
                "D",
                "D-",
                "F",
                "W",  # Withdrawn
                "I",  # Incomplete
                "P",  # Pass (pass/fail)
                "NP",  # No Pass
                "AU",  # Audit
                "IP",  # In Progress
            }

            if v not in valid_grades:
                # Allow non-standard grades but note for review
                if len(v) > 10:
                    raise ValueError(f"Grade '{v}' is too long")
                # Check for obviously invalid grades
                if any(char in v for char in "!@#$%^&*(){}[]|\\"):
                    raise ValueError(f"Grade '{v}' contains invalid characters")

        return v

    @field_validator("grade_points")
    @classmethod
    def validate_grade_points_scale(cls, v):
        """Validate grade points are on expected scale"""
        if v is not None:
            # Most institutions use 0.0-4.0 scale
            if v < 0:
                raise ValueError("grade_points cannot be negative")
            if v > 4.5:  # Allow some flexibility for different scales
                raise ValueError(f"grade_points {v} seems unusually high (typical max is 4.0)")

            # Should have reasonable precision (not more than 2 decimal places typically)
            if round(v, 2) != v:
                # Allow but note
                pass

        return v

    @field_validator("credit_hours")
    @classmethod
    def validate_credit_hours_reasonable(cls, v):
        """Validate credit hours are reasonable"""
        if v is not None:
            if v < 0:
                raise ValueError("credit_hours cannot be negative")
            if v == 0:
                # Zero credits courses exist (audits, etc.)
                pass
            if v > 20:
                raise ValueError(f"credit_hours {v} seems unusually high")

        return v

    @field_validator("repeat_count")
    @classmethod
    def validate_repeat_count_reasonable(cls, v):
        """Validate repeat count is reasonable"""
        if v is not None:
            if v < 0:
                raise ValueError("repeat_count cannot be negative")
            if v > 5:
                raise ValueError(f"repeat_count {v} seems unusually high")

        return v

    @field_validator("lab_score", "unit_score")
    @classmethod
    def validate_score_ranges(cls, v, field):
        """Validate test scores are in reasonable ranges"""
        if v is not None:
            if v < 0:
                raise ValueError(f"{field.name} cannot be negative")
            if v > 100:
                raise ValueError(f"{field.name} {v} exceeds 100% - unusual for test scores")

        return v

    @model_validator(mode="after")
    def validate_grade_consistency(self):
        """Validate grade, points, and pass status are consistent"""
        final_grade = self.final_grade.strip().upper() if self.final_grade else ""
        grade_points = self.grade_points
        is_passed = self.is_passed

        if final_grade and grade_points is not None:
            # Check grade-to-points consistency (approximate)
            grade_point_mapping = {
                "A+": 4.0,
                "A": 4.0,
                "A-": 3.7,
                "B+": 3.3,
                "B": 3.0,
                "B-": 2.7,
                "C+": 2.3,
                "C": 2.0,
                "C-": 1.7,
                "D+": 1.3,
                "D": 1.0,
                "D-": 0.7,
                "F": 0.0,
                "W": 0.0,
                "I": 0.0,
            }

            expected_points = grade_point_mapping.get(final_grade)
            if expected_points is not None:
                # Allow some tolerance for different institutional scales
                if abs(grade_points - expected_points) > 0.5:
                    # Note inconsistency but don't fail validation
                    pass

        if final_grade and is_passed is not None:
            # Check grade-to-pass consistency
            passing_grades = {"A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "D-", "P"}
            failing_grades = {"F", "NP"}

            if final_grade in passing_grades and not is_passed:
                raise ValueError(f"Grade '{final_grade}' is passing but is_passed is False")
            elif final_grade in failing_grades and is_passed:
                raise ValueError(f"Grade '{final_grade}' is failing but is_passed is True")

        return self

    @model_validator(mode="after")
    def validate_total_points_calculation(self):
        """Validate total points calculation if components are present"""
        grade_points = self.grade_points
        credit_hours = self.credit_hours
        total_points = self.total_points

        if grade_points is not None and credit_hours is not None and total_points is not None:
            expected_total = grade_points * credit_hours

            # Allow some tolerance for rounding differences
            if abs(total_points - expected_total) > 0.01:
                # Note calculation inconsistency but don't fail
                # This is common due to rounding or different calculation methods
                pass

        return self

    @model_validator(mode="after")
    def validate_repeat_logic(self):
        """Validate repeat course logic"""
        repeat_count = self.repeat_count or 0
        previous_grade = self.previous_grade
        final_grade = self.final_grade

        if repeat_count and repeat_count > 0:
            # If this is a repeat, there should typically be a previous grade
            if not previous_grade:
                # Note but don't fail - previous grade might not be recorded
                pass

            # Previous grade should typically be worse than current (if both present)
            if previous_grade and final_grade:
                grade_hierarchy = {
                    "F": 0,
                    "D-": 1,
                    "D": 2,
                    "D+": 3,
                    "C-": 4,
                    "C": 5,
                    "C+": 6,
                    "B-": 7,
                    "B": 8,
                    "B+": 9,
                    "A-": 10,
                    "A": 11,
                    "A+": 12,
                    "W": -1,
                    "I": -1,  # Special cases
                }

                prev_rank = grade_hierarchy.get(previous_grade.upper(), -2)
                curr_rank = grade_hierarchy.get(final_grade.upper(), -2)

                if prev_rank >= 0 and curr_rank >= 0 and prev_rank >= curr_rank:
                    # Previous grade same or better - unusual but not invalid
                    pass

        return self

    @model_validator(mode="after")
    def validate_timestamp_logic(self):
        """Validate timestamp relationships"""
        added = self.added_timestamp
        updated = self.last_updated

        if added and updated:
            if updated < added:
                raise ValueError("last_updated cannot be before added_timestamp")

        return self

    def get_quality_score(self) -> float:
        """Calculate data quality score for this enrollment record"""
        score = 0.0
        max_score = 15.0  # Total possible points

        # Required identifiers (4 points)
        if self.student_id and len(self.student_id.strip()) > 0:
            score += 2.0
        if self.class_id and len(self.class_id.strip()) > 0:
            score += 2.0

        # Core academic data (6 points)
        if self.final_grade and len(self.final_grade.strip()) > 0:
            score += 2.0
        if self.grade_points is not None:
            score += 1.5
        if self.credit_hours is not None:
            score += 1.5
        if self.is_passed is not None:
            score += 1.0

        # Consistency bonuses (3 points)
        if self.final_grade and self.grade_points is not None:
            # Bonus for having both grade and points
            score += 1.0
        if self.grade_points is not None and self.credit_hours is not None:
            # Bonus for GPA calculation possible
            score += 1.0
        if self.parsed_course_code and len(self.parsed_course_code.strip()) > 0:
            # Bonus for parsed course information
            score += 1.0

        # Data completeness (2 points)
        optional_fields = [self.registration_mode, self.attendance_status, self.parsed_term_id]
        completeness = sum(1 for field in optional_fields if field and field.strip())
        score += (completeness / len(optional_fields)) * 2.0

        return min(score / max_score, 1.0)
