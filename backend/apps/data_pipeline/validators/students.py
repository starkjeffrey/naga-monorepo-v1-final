"""
Students Table Validator

Pydantic model for validating Students table data after cleaning.
Enforces business rules for student personal and academic data.
"""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator


class StudentValidator(BaseModel):
    """
    Pydantic validator for Students table records.

    Validates student personal information, academic history, and program selections.
    Handles complex validation including encoding issues and data consistency.
    """

    # Primary identifier
    student_id: str = Field(..., min_length=1, max_length=10, description="Student ID - primary key")

    # Authentication fields
    username: str | None = Field(None, max_length=100, description="User interface login name")
    password_hash: str | None = Field(None, max_length=10, description="Legacy password hash")

    # Personal information - names
    name_english: str = Field(..., min_length=1, max_length=100, description="Student name in English")
    name_khmer: str | None = Field(None, max_length=100, description="Student name in Khmer script")
    name_khmer_alt: str | None = Field(None, max_length=100, description="Alternative Khmer name")

    # Demographic information
    birth_date: datetime | None = Field(None, description="Date of birth")
    birth_place: str | None = Field(None, max_length=50, description="Place of birth")
    gender: str | None = Field(None, max_length=30, description="Gender")
    marital_status: str | None = Field(None, max_length=30, description="Marital status")
    nationality: str | None = Field(None, max_length=50, description="Nationality")

    # Contact information
    home_address: str | None = Field(None, max_length=250, description="Home address")
    home_phone: str | None = Field(None, max_length=50, description="Home phone number")
    email_personal: str | None = Field(None, max_length=50, description="Personal email address")
    mobile_phone: str | None = Field(None, max_length=50, description="Mobile phone number")
    email_school: str | None = Field(None, max_length=100, description="School-issued email address")

    # Employment information
    employment_place: str | None = Field(None, max_length=200, description="Current workplace")
    employment_position: str | None = Field(None, max_length=150, description="Job position")

    # Family information
    father_name: str | None = Field(None, max_length=50, description="Father's name")
    spouse_name: str | None = Field(None, max_length=50, description="Spouse's name")

    # Emergency contact
    emergency_contact_name: str | None = Field(None, max_length=50, description="Emergency contact person name")
    emergency_contact_relationship: str | None = Field(
        None, max_length=50, description="Relationship to emergency contact"
    )
    emergency_contact_address: str | None = Field(None, max_length=250, description="Emergency contact address")
    emergency_contact_phone: str | None = Field(None, max_length=30, description="Emergency contact phone")

    # Education history
    high_school_name: str | None = Field(None, max_length=150, description="High school name")
    high_school_province: str | None = Field(None, max_length=100, description="High school province")
    high_school_year: int | None = Field(None, ge=1950, le=2030, description="High school graduation year")
    high_school_diploma: str | None = Field(None, max_length=10, description="High school diploma type")

    # English program
    english_program_school: str | None = Field(None, max_length=150, description="English language program school")
    english_program_level: str | None = Field(None, max_length=50, description="English proficiency level achieved")
    english_program_year: int | None = Field(None, ge=1990, le=2030, description="Year English program completed")

    # Bachelor's degree
    bachelor_school: str | None = Field(None, max_length=150, description="Bachelor's degree institution")
    bachelor_degree: str | None = Field(None, max_length=50, description="Bachelor's degree type")
    bachelor_major: str | None = Field(None, max_length=100, description="Bachelor's degree major")
    bachelor_year: int | None = Field(None, ge=1980, le=2030, description="Bachelor's degree graduation year")

    # Current program selection
    selected_program_name: str | None = Field(None, max_length=100, description="Selected program name")
    selected_major_name: str | None = Field(None, max_length=100, description="Selected major name")
    selected_faculty_name: str | None = Field(None, max_length=150, description="Selected faculty name")
    selected_degree_type: str | None = Field(None, max_length=100, description="Selected degree type")

    # Admission dates
    admission_date: datetime | None = Field(None, description="General admission date")
    admission_date_undergraduate: datetime | None = Field(None, description="Undergraduate program admission date")
    admission_date_master: datetime | None = Field(None, description="Master's program admission date")

    # Status fields
    is_admitted: bool | None = Field(None, description="Admission status flag")
    is_deleted: bool | None = Field(None, description="Deletion flag")
    status: str | None = Field(None, max_length=15, description="Current student status")

    # Enrollment tracking
    last_enrollment_date: datetime | None = Field(None, description="Last enrollment date")
    first_enrollment_date: datetime | None = Field(None, description="First enrollment date")

    # Notes
    notes: str | None = Field(None, max_length=255, description="Administrative notes about student")

    class Config:
        """Pydantic configuration"""

        str_strip_whitespace = True
        validate_assignment = True
        extra = "forbid"
        # Allow datetime inputs as strings
        json_encoders = {datetime: lambda v: v.isoformat() if v else None}

    @field_validator("student_id")
    @classmethod
    def validate_student_id_format(cls, v):
        """Validate student ID follows expected patterns"""
        if not v or not v.strip():
            raise ValueError("student_id cannot be empty")

        v = v.strip().upper()

        # Common patterns: ST001, MS2010001, etc.
        if len(v) < 3:
            raise ValueError("student_id appears too short")
        if len(v) > 10:
            raise ValueError("student_id too long (max 10 characters)")

        # Should contain some alphanumeric characters
        if not re.match(r"^[A-Z0-9]+$", v):
            raise ValueError("student_id should contain only letters and numbers")

        return v

    @field_validator("name_english")
    @classmethod
    def validate_english_name(cls, v):
        """Validate English name is reasonable"""
        if not v or not v.strip():
            raise ValueError("name_english is required and cannot be empty")

        v = v.strip()
        if len(v) < 2:
            raise ValueError("name_english appears too short")

        # Check for obvious encoding corruption (question marks, boxes, etc.)
        if "?" in v or "�" in v:
            raise ValueError("name_english appears to have encoding corruption")

        return v

    @field_validator("name_khmer", "name_khmer_alt")
    @classmethod
    def validate_khmer_names(cls, v):
        """Validate Khmer names, accounting for encoding issues"""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None

            # Check for obvious corruption indicators
            corruption_indicators = ["?", "�", "\x00", "\ufffd"]
            if any(indicator in v for indicator in corruption_indicators):
                # Log this as a known encoding issue but don't fail validation
                # The cleaning stage should have attempted to fix this
                pass

            # Khmer text should be reasonable length
            if len(v) > 100:
                raise ValueError("Khmer name too long")

        return v if v and v.strip() else None

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v):
        """Normalize and validate gender values"""
        if v is not None:
            v = v.strip().title()
            # Normalize common variations
            gender_mapping = {
                "M": "Male",
                "F": "Female",
                "MALE": "Male",
                "FEMALE": "Female",
                "Man": "Male",
                "Woman": "Female",
            }

            normalized = gender_mapping.get(v.upper(), v)
            if normalized not in ["Male", "Female"]:
                # Allow other values but note for review
                pass

            return normalized
        return v

    @field_validator("email_personal", "email_school")
    @classmethod
    def validate_email_format(cls, v):
        """Validate email addresses"""
        if v is not None:
            v = v.strip().lower()
            if len(v) == 0:
                return None

            # Basic email format validation
            email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            if not re.match(email_pattern, v):
                raise ValueError(f"Invalid email format: {v}")

            return v
        return v

    @field_validator("birth_date")
    @classmethod
    def validate_birth_date(cls, v):
        """Validate birth date is reasonable"""
        if v is not None:
            current_date = datetime.now()

            # Check for obviously wrong dates
            if v > current_date:
                raise ValueError("birth_date cannot be in the future")

            # Check age is reasonable (5-120 years old)
            age_years = (current_date - v).days / 365.25
            if age_years < 5:
                raise ValueError(f"Student appears too young ({age_years:.1f} years)")
            if age_years > 120:
                raise ValueError(f"Student appears too old ({age_years:.1f} years)")

            # Typical student age range (15-65 for higher education)
            if age_years < 15 or age_years > 65:
                # Allow but note as unusual
                pass

        return v

    @field_validator("high_school_year", "english_program_year", "bachelor_year")
    @classmethod
    def validate_education_years(cls, v, field):
        """Validate education completion years are reasonable"""
        if v is not None:
            current_year = datetime.now().year

            if v < 1950:
                raise ValueError(f"{field.name} cannot be before 1950")
            if v > current_year + 5:
                raise ValueError(f"{field.name} {v} is too far in the future")

        return v

    @field_validator("home_phone", "mobile_phone", "emergency_contact_phone")
    @classmethod
    def validate_phone_numbers(cls, v):
        """Basic phone number validation"""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None

            # Remove common formatting characters
            cleaned = re.sub(r"[\s\-\(\)\+]", "", v)

            # Should be mostly digits
            if not re.match(r"^[\d\+\(\)\-\s]+$", v):
                raise ValueError(f"Phone number contains invalid characters: {v}")

            # Reasonable length (7-20 digits)
            digit_count = len(re.sub(r"[^\d]", "", cleaned))
            if digit_count < 7 or digit_count > 20:
                raise ValueError(f"Phone number has unusual length: {v}")

        return v

    @model_validator(mode="after")
    def validate_name_requirements(self):
        """Ensure at least one name field is present and meaningful"""
        name_english = self.name_english.strip() if self.name_english else ""
        name_khmer = self.name_khmer.strip() if self.name_khmer else ""

        if not name_english and not name_khmer:
            raise ValueError("At least one name field (name_english or name_khmer) must be present")

        return self

    @model_validator(mode="after")
    def validate_admission_date_sequence(self):
        """Validate admission dates are in logical order"""
        admission_date = self.admission_date
        admission_undergraduate = self.admission_date_undergraduate
        admission_master = self.admission_date_master
        birth_date = self.birth_date

        # Admission dates should be after birth date
        if birth_date:
            for date_field, date_value in [
                ("admission_date", admission_date),
                ("admission_date_undergraduate", admission_undergraduate),
                ("admission_date_master", admission_master),
            ]:
                if date_value and date_value.date() <= birth_date.date():
                    raise ValueError(f"{date_field} must be after birth_date")

        # Graduate admission should typically be after undergraduate
        if admission_undergraduate and admission_master:
            if admission_master <= admission_undergraduate:
                raise ValueError("admission_date_master should typically be after admission_date_undergraduate")

        return self

    @model_validator(mode="after")
    def validate_enrollment_date_logic(self):
        """Validate enrollment dates are logical"""
        first_enrollment = self.first_enrollment_date
        last_enrollment = self.last_enrollment_date
        admission_date = self.admission_date

        if first_enrollment and last_enrollment:
            if last_enrollment < first_enrollment:
                raise ValueError("last_enrollment_date cannot be before first_enrollment_date")

        if admission_date and first_enrollment:
            # First enrollment should be on or after admission
            if first_enrollment.date() < admission_date.date():
                raise ValueError("first_enrollment_date should not be before admission_date")

        return self

    def get_quality_score(self) -> float:
        """Calculate data quality score for this student record"""
        score = 0.0
        max_score = 20.0  # Total possible points

        # Required fields (4 points)
        if self.student_id and len(self.student_id.strip()) > 0:
            score += 2.0
        if self.name_english and len(self.name_english.strip()) > 0:
            score += 2.0

        # Important demographic data (4 points)
        if self.birth_date:
            score += 1.0
        if self.gender:
            score += 1.0
        if self.nationality:
            score += 1.0
        if self.name_khmer and len(self.name_khmer.strip()) > 0:
            score += 1.0

        # Contact information (4 points)
        contact_fields = [self.home_address, self.home_phone, self.mobile_phone, self.email_personal]
        contact_score = sum(1 for field in contact_fields if field and field.strip())
        score += min(contact_score, 4.0)

        # Academic information (4 points)
        if self.selected_program_name:
            score += 1.0
        if self.selected_major_name:
            score += 1.0
        if self.admission_date:
            score += 1.0
        if self.status:
            score += 1.0

        # Data consistency bonuses (4 points)
        if self.email_personal and "@" in self.email_personal:
            score += 1.0
        if self.birth_date and self.admission_date and self.admission_date > self.birth_date:
            score += 1.0
        if self.first_enrollment_date and self.last_enrollment_date:
            if self.last_enrollment_date >= self.first_enrollment_date:
                score += 1.0
        if self.is_admitted is not None:
            score += 1.0

        return min(score / max_score, 1.0)
