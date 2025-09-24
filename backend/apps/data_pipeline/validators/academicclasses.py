"""
Academic Classes Table Validator

Pydantic model for validating Academic Classes data after cleaning.
Enforces business rules for class sections and course scheduling.
"""

from pydantic import BaseModel, Field, field_validator


class AcademicClassValidator(BaseModel):
    """
    Pydantic validator for Academic Classes table records.

    Validates class section data including course information and scheduling.
    """

    # Required identifiers
    class_id: str = Field(..., min_length=1, max_length=255, description="Unique class section identifier")
    course_code: str = Field(..., min_length=1, max_length=100, description="Course code identifier")
    course_title: str = Field(..., min_length=1, max_length=255, description="Full course title")

    # Optional context
    term_id: str | None = Field(None, max_length=100, description="Academic term identifier")
    program_id: int | None = Field(None, description="Program ID reference")
    major_id: int | None = Field(None, description="Major ID reference")

    # Student enrollment
    student_count: int | None = Field(None, ge=0, le=1000, description="Number of students enrolled")

    # Scheduling
    class_time: str | None = Field(None, max_length=50, description="Class meeting time/schedule")

    class Config:
        """Pydantic configuration"""

        str_strip_whitespace = True
        validate_assignment = True
        extra = "forbid"

    @field_validator("class_id")
    @classmethod
    def validate_class_id_format(cls, v):
        """Validate class ID format"""
        if not v or not v.strip():
            raise ValueError("class_id cannot be empty")
        return v.strip().upper()

    @field_validator("course_code")
    @classmethod
    def validate_course_code_format(cls, v):
        """Validate course code format"""
        if not v or not v.strip():
            raise ValueError("course_code cannot be empty")
        return v.strip().upper()

    @field_validator("course_title")
    @classmethod
    def validate_course_title(cls, v):
        """Validate course title is meaningful"""
        if not v or not v.strip():
            raise ValueError("course_title cannot be empty")

        v = v.strip()
        if len(v) < 3:
            raise ValueError("course_title appears too short")

        return v

    def get_quality_score(self) -> float:
        """Calculate data quality score for this class record"""
        score = 0.0
        max_score = 10.0

        # Required fields (6 points)
        if self.class_id and len(self.class_id.strip()) > 0:
            score += 2.0
        if self.course_code and len(self.course_code.strip()) > 0:
            score += 2.0
        if self.course_title and len(self.course_title.strip()) > 0:
            score += 2.0

        # Important context (2 points)
        if self.term_id and len(self.term_id.strip()) > 0:
            score += 1.0
        if self.student_count is not None:
            score += 1.0

        # Additional details (2 points)
        if self.class_time and len(self.class_time.strip()) > 0:
            score += 1.0
        if self.program_id is not None:
            score += 1.0

        return min(score / max_score, 1.0)
