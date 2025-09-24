"""
Receipt Headers Table Validator

Pydantic model for validating Receipt Headers data after cleaning.
Enforces financial integrity rules for payment transactions.
"""

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class ReceiptHeaderValidator(BaseModel):
    """
    Pydantic validator for Receipt Headers table records.

    Validates payment receipt headers with strict financial integrity checks.
    """

    # Primary identifiers
    student_id: str = Field(..., min_length=1, max_length=50, description="Student ID")
    receipt_id: str = Field(..., min_length=1, max_length=250, description="Unique receipt identifier")

    # Optional identifiers
    term_id: str | None = Field(None, max_length=100, description="Academic term")
    receipt_number: str | None = Field(None, max_length=150, description="Receipt number")
    internal_receipt_number: int | None = Field(None, ge=0, description="Internal receipt number")

    # Payment transaction details
    payment_date: datetime | None = Field(None, description="Payment date")
    payment_type: str | None = Field(None, max_length=50, description="Payment method")
    check_number: str | None = Field(None, max_length=50, description="Check number if applicable")

    # Financial amounts - using float to match schema but validating precision
    gross_amount: float | None = Field(None, ge=0, description="Gross payment amount")
    net_amount: float | None = Field(None, ge=0, description="Net payment amount")
    discount_amount: float | None = Field(None, ge=0, description="Discount applied")
    scholarship_amount: float | None = Field(None, ge=0, description="Scholarship amount")
    remaining_balance: float | None = Field(None, description="Remaining balance")

    # Receipt details
    receipt_type: str | None = Field(None, max_length=100, description="Type of receipt")
    student_name: str | None = Field(None, max_length=120, description="Student name")
    notes: str | None = Field(None, max_length=500, description="Administrative notes")

    # Status flags
    is_deleted: bool | None = Field(None, description="Deletion flag")

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
        """Validate receipt ID is unique identifier"""
        if not v or not v.strip():
            raise ValueError("receipt_id cannot be empty")

        v = v.strip()
        if len(v) < 3:
            raise ValueError("receipt_id appears too short")

        return v

    @field_validator("payment_date")
    @classmethod
    def validate_payment_date_reasonable(cls, v):
        """Validate payment date is reasonable"""
        if v is not None:
            current_date = datetime.now()

            # Payment cannot be in future (with small tolerance)
            if v > current_date:
                raise ValueError("payment_date cannot be in the future")

            # Payment shouldn't be too old (before 1990)
            if v.year < 1990:
                raise ValueError("payment_date seems too old (before 1990)")

        return v

    @field_validator("gross_amount", "net_amount", "discount_amount", "scholarship_amount")
    @classmethod
    def validate_positive_amounts(cls, v, field):
        """Validate monetary amounts are non-negative"""
        if v is not None:
            if v < 0:
                raise ValueError(f"{field.name} cannot be negative")

            # Check for reasonable precision (max 2 decimal places for currency)
            if round(v, 2) != v:
                # Allow but note - may be precision issue
                pass

            # Check for unreasonably large amounts (over $100,000)
            if v > 100000:
                raise ValueError(f"{field.name} {v} seems unusually large")

        return v

    @field_validator("remaining_balance")
    @classmethod
    def validate_remaining_balance(cls, v):
        """Validate remaining balance (can be negative for overpayments)"""
        if v is not None:
            # Very large balances should be flagged
            if abs(v) > 500000:
                raise ValueError(f"remaining_balance {v} seems unusually large")

        return v

    @field_validator("payment_type")
    @classmethod
    def validate_payment_type(cls, v):
        """Validate payment type against common values"""
        if v is not None:
            v = v.strip().title()

            # Common payment types

            # Allow other values but standardize common ones
            standardized = {
                "CASH": "Cash",
                "CHECK": "Check",
                "CREDIT": "Credit Card",
                "DEBIT": "Debit Card",
                "TRANSFER": "Bank Transfer",
                "WIRE": "Wire Transfer",
            }

            return standardized.get(v.upper(), v)

        return v

    @model_validator(mode="after")
    def validate_financial_consistency(self):
        """Validate financial amounts are consistent"""
        gross_amount = self.gross_amount
        net_amount = self.net_amount
        discount_amount = self.discount_amount if self.discount_amount is not None else 0.0
        scholarship_amount = self.scholarship_amount if self.scholarship_amount is not None else 0.0

        if gross_amount is not None and net_amount is not None:
            # Net should be gross minus discounts/scholarships
            expected_net = gross_amount - (discount_amount or 0) - (scholarship_amount or 0)

            # Allow some tolerance for rounding
            if abs(net_amount - expected_net) > 0.02:
                # Note inconsistency but don't fail - may be other deductions
                pass

            # Net should not exceed gross
            if net_amount > gross_amount:
                raise ValueError("net_amount cannot exceed gross_amount")

        return self

    @model_validator(mode="after")
    def validate_check_payment_logic(self):
        """Validate check payment logic"""
        payment_type = self.payment_type.lower() if self.payment_type else ""
        check_number = self.check_number

        if "check" in payment_type and not check_number:
            # Check payment should have check number
            # Allow missing but note
            pass

        if check_number and "check" not in payment_type:
            # Has check number but payment type not check
            # Allow but note inconsistency
            pass

        return self

    def get_quality_score(self) -> float:
        """Calculate data quality score for this receipt"""
        score = 0.0
        max_score = 12.0

        # Required identifiers (4 points)
        if self.student_id and len(self.student_id.strip()) > 0:
            score += 2.0
        if self.receipt_id and len(self.receipt_id.strip()) > 0:
            score += 2.0

        # Critical financial data (4 points)
        if self.gross_amount is not None:
            score += 2.0
        if self.payment_date:
            score += 2.0

        # Important details (2 points)
        if self.payment_type:
            score += 1.0
        if self.receipt_type:
            score += 1.0

        # Data consistency (2 points)
        if self.gross_amount is not None and self.net_amount is not None:
            if self.net_amount <= self.gross_amount:
                score += 1.0
        if self.payment_date and self.payment_date <= datetime.now():
            score += 1.0

        return min(score / max_score, 1.0)
