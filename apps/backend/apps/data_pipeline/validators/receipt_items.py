"""
Receipt Items Table Validator

Pydantic model for validating Receipt Items data after cleaning.
Enforces financial integrity rules for line items.
"""

from pydantic import BaseModel, Field, field_validator


class ReceiptItemValidator(BaseModel):
    """
    Pydantic validator for Receipt Items table records.

    Validates receipt line items with basic financial integrity checks.
    """

    # Required identifiers
    student_id: str = Field(..., min_length=1, max_length=20, description="Student ID")
    receipt_id: str = Field(..., min_length=1, max_length=250, description="Receipt identifier")
    item_description: str = Field(..., min_length=1, max_length=250, description="Item description")

    # Optional details
    term_id: str | None = Field(None, max_length=50, description="Academic term")
    program_id: int | None = Field(None, description="Program ID")

    # Financial amounts
    line_total: float | None = Field(None, ge=0, description="Line item total")
    discount_amount: float | None = Field(None, ge=0, description="Discount applied")

    class Config:
        """Pydantic configuration"""

        str_strip_whitespace = True
        validate_assignment = True
        extra = "forbid"

    @field_validator("student_id")
    @classmethod
    def validate_student_id_format(cls, v):
        """Validate student ID format"""
        if not v or not v.strip():
            raise ValueError("student_id cannot be empty")
        return v.strip().upper()

    @field_validator("receipt_id")
    @classmethod
    def validate_receipt_id_format(cls, v):
        """Validate receipt ID"""
        if not v or not v.strip():
            raise ValueError("receipt_id cannot be empty")
        return v.strip()

    @field_validator("item_description")
    @classmethod
    def validate_item_description(cls, v):
        """Validate item description is meaningful"""
        if not v or not v.strip():
            raise ValueError("item_description cannot be empty")

        v = v.strip()
        if len(v) < 3:
            raise ValueError("item_description appears too short")

        return v

    def get_quality_score(self) -> float:
        """Calculate data quality score for this receipt item"""
        score = 0.0
        max_score = 8.0

        # Required fields (6 points)
        if self.student_id and len(self.student_id.strip()) > 0:
            score += 2.0
        if self.receipt_id and len(self.receipt_id.strip()) > 0:
            score += 2.0
        if self.item_description and len(self.item_description.strip()) > 0:
            score += 2.0

        # Financial data (2 points)
        if self.line_total is not None:
            score += 1.0
        if self.term_id and len(self.term_id.strip()) > 0:
            score += 1.0

        return min(score / max_score, 1.0)
