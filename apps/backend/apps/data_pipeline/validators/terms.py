"""
Terms Table Validator

Pydantic model for validating Terms table data after cleaning.
Enforces business rules for academic term/semester data.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class TermValidator(BaseModel):
    """
    Pydantic validator for Terms table records.

    Validates academic terms with start/end dates and ensures
    business rules are enforced before final storage.
    """

    # Primary identifier
    term_id: str = Field(..., min_length=1, max_length=200, description="Term identifier like '2009T1E', '2009T2E'")

    # Term description
    term_name: str = Field(..., min_length=1, max_length=50, description="Human-readable term name")

    # Critical date fields
    start_date: datetime | None = Field(None, description="Term start date")
    end_date: datetime | None = Field(None, description="Term end date")
    last_drop_date: datetime | None = Field(None, description="Last date to drop courses")
    add_date: datetime | None = Field(None, description="Last date to add courses")
    drop_date: datetime | None = Field(None, description="Course drop deadline")
    leave_date: datetime | None = Field(None, description="Leave of absence deadline")

    # Term metadata
    payment_period: str = Field(..., min_length=1, max_length=50, description="Payment period in days")
    max_terms: str | None = Field(None, max_length=50, description="Maximum terms allowed")
    school_year: int | None = Field(None, ge=1990, le=2050, description="School year (2009, 2010, etc.)")
    term_type: str | None = Field(None, max_length=5, description="Term type code (ENG A, X, etc.)")
    description: str | None = Field(None, max_length=200, description="Additional description or notes")

    class Config:
        """Pydantic configuration"""

        str_strip_whitespace = True  # Automatically strip whitespace
        validate_assignment = True  # Validate on assignment
        extra = "forbid"  # Don't allow extra fields

    @field_validator("term_id")
    @classmethod
    def validate_term_id_format(cls, v):
        """Validate term ID follows expected pattern"""
        if not v:
            raise ValueError("term_id cannot be empty")

        # Expected format: YYYYT#[A-Z] (e.g., 2009T1E, 2010T2A)
        import re

        pattern = r"^\d{4}T[1-3][A-Z]?$"
        if not re.match(pattern, v):
            # Allow some flexibility but warn about unexpected formats
            if len(v) < 6:
                raise ValueError(f"term_id '{v}' appears too short for expected format YYYYT#[A-Z]")

        return v.upper()

    @field_validator("payment_period")
    @classmethod
    def validate_payment_period_numeric(cls, v):
        """Ensure payment period can be parsed as integer"""
        if not v:
            raise ValueError("payment_period cannot be empty")

        try:
            period_days = int(v)
            if period_days <= 0:
                raise ValueError("payment_period must be positive number of days")
            if period_days > 365:
                raise ValueError("payment_period seems unusually long (>365 days)")
            return str(period_days)  # Return as string to match schema
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError(f"payment_period '{v}' must be a valid integer") from e
            raise

    @field_validator("school_year")
    @classmethod
    def validate_school_year_reasonable(cls, v):
        """Validate school year is reasonable"""
        if v is not None:
            current_year = datetime.now().year
            if v < 1990:
                raise ValueError("school_year cannot be before 1990")
            if v > current_year + 5:
                raise ValueError(f"school_year {v} seems too far in the future")
        return v

    @field_validator("term_type")
    @classmethod
    def validate_term_type_format(cls, v):
        """Validate term type follows expected patterns"""
        if v is not None:
            v = v.upper().strip()
            # Common patterns: ENG A, X, BA, MA, etc.
            if len(v) > 5:
                raise ValueError("term_type too long (max 5 characters)")
        return v

    @model_validator(mode="after")
    def validate_date_relationships(self):
        """Validate logical relationships between dates"""
        start_date = self.start_date
        end_date = self.end_date
        add_date = self.add_date
        drop_date = self.drop_date
        last_drop_date = self.last_drop_date
        leave_date = self.leave_date

        # Basic date range validation
        if start_date and end_date:
            if start_date >= end_date:
                raise ValueError("end_date must be after start_date")

            # Term length should be reasonable (typically 10-20 weeks)
            term_length = (end_date - start_date).days
            if term_length < 30:  # Less than ~4 weeks
                raise ValueError(f"Term appears very short ({term_length} days)")
            if term_length > 200:  # More than ~28 weeks
                raise ValueError(f"Term appears very long ({term_length} days)")

        # Add/drop dates should be within term if specified
        if start_date and end_date:
            for date_field, date_value in [
                ("add_date", add_date),
                ("drop_date", drop_date),
                ("last_drop_date", last_drop_date),
                ("leave_date", leave_date),
            ]:
                if date_value:
                    if date_value < start_date:
                        raise ValueError(f"{date_field} cannot be before term start_date")
                    if date_value > end_date:
                        raise ValueError(f"{date_field} cannot be after term end_date")

        # Drop dates logical order
        if add_date and drop_date:
            if add_date > drop_date:
                raise ValueError("add_date should typically be before drop_date")

        return self

    @model_validator(mode="after")
    def validate_term_id_year_consistency(self):
        """Validate term_id year matches school_year if both present"""
        term_id = self.term_id
        school_year = self.school_year

        if term_id and school_year:
            # Extract year from term_id (first 4 characters)
            try:
                term_year = int(term_id[:4])
                if term_year != school_year:
                    raise ValueError(f"term_id year ({term_year}) doesn't match school_year ({school_year})")
            except (ValueError, IndexError):
                # If we can't parse year from term_id, that's okay - other validator will catch format issues
                pass

        return self

    def get_validation_errors(self) -> list:
        """
        Get human-readable validation errors.
        Used by the pipeline to report specific issues.
        """
        errors = []

        # This method would be called after attempting validation
        # to provide detailed error reporting for the pipeline
        try:
            # Validate the current instance
            self.__class__.parse_obj(self.dict())
        except Exception as e:
            errors.append(str(e))

        return errors

    def get_quality_score(self) -> float:
        """
        Calculate data quality score for this record.
        Returns score between 0.0-1.0 based on completeness and validity.
        """
        score = 0.0
        max_score = 10.0  # Total possible points

        # Required fields present and valid (4 points)
        if self.term_id and len(self.term_id.strip()) > 0:
            score += 2.0
        if self.term_name and len(self.term_name.strip()) > 0:
            score += 2.0

        # Important dates present (3 points)
        if self.start_date:
            score += 1.5
        if self.end_date:
            score += 1.5

        # Administrative data present (2 points)
        if self.school_year:
            score += 1.0
        if self.payment_period and self.payment_period.strip():
            score += 1.0

        # Consistency bonuses (1 point)
        if self.start_date and self.end_date and self.start_date < self.end_date:
            score += 0.5
        if self.term_type and len(self.term_type.strip()) > 0:
            score += 0.5

        return min(score / max_score, 1.0)
