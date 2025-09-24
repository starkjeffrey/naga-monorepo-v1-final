"""People services for business logic and workflows.

This module provides business logic services for people-related operations including:
- Student number generation and management
- Person and profile creation workflows
- Student conversion from level testing applicants
- Duplicate person detection and merging
- Profile management and validation
- Audit logging for person changes

All services follow clean architecture principles and avoid circular dependencies
while providing comprehensive people management functionality.
"""

import re
from typing import TYPE_CHECKING, Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.utils import timezone

from apps.common.constants import is_cambodian_province
from apps.people.models import (
    EmergencyContact,
    Person,
    PersonEventLog,
    PhoneNumber,
    StudentAuditLog,
    StudentProfile,
)

from .constants import (
    EMAIL_MATCH_CONFIDENCE,
    EXACT_NAME_MATCH_CONFIDENCE,
    MAX_AGE_YEARS,
    MAX_STUDENT_ID_DIGITS,
    PHONE_MATCH_CONFIDENCE,
    STUDENT_ID_START,
)

if TYPE_CHECKING:
    from users.models import User
else:
    User = get_user_model()


# Python 3.13+ Type Aliases
type StudentConversionResult = tuple[Person, StudentProfile]
type PersonMatchData = dict[str, Any]
type UniqueMatches = dict[int, PersonMatchData]
type ValidationErrors = list[str]
type ValidationResult = tuple[bool, ValidationErrors]
type PersonMergeResult = Person
type ConfidenceScore = float


class StudentNumberService:
    """Service for generating and managing student numbers."""

    @classmethod
    def generate_next_student_number(cls) -> int:
        """Generate the next available student number using PostgreSQL sequence.

        Uses database-level sequence for thread safety and optimal performance.
        This is the only supported method as of the architecture refactor.

        Returns:
            Next available student number as integer

        Raises:
            ValueError: If unable to generate student number
        """
        return cls._generate_using_postgres_sequence()

    @classmethod
    def _generate_using_postgres_sequence(cls) -> int:
        """Generate student number using PostgreSQL sequence for thread safety.

        This is the recommended approach as it's atomic and handles concurrency.
        """
        with connection.cursor() as cursor:
            # Create sequence if it doesn't exist
            cursor.execute(
                """
                CREATE SEQUENCE IF NOT EXISTS student_number_seq
                START WITH 100001
                INCREMENT BY 1
                NO MAXVALUE
                NO CYCLE;
            """
            )

            # Get next value from sequence
            cursor.execute("SELECT nextval('student_number_seq');")
            student_number = cursor.fetchone()[0]

            # Database sequences are atomic and guarantee uniqueness
            # No need for additional existence check
            return student_number

    @classmethod
    def validate_student_number(cls, student_number: int) -> ValidationResult:
        """Validate a student number against business rules.

        Args:
            student_number: Student number to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check if number is positive and reasonable
        if student_number <= 0:
            errors.append("Student number must be positive")

        # Check minimum number (institutional policy)
        if student_number < STUDENT_ID_START:
            errors.append(f"Student number must be at least {STUDENT_ID_START}")

        # Check if already in use
        if StudentProfile.objects.filter(student_id=student_number).exists():
            errors.append(f"Student number {student_number} is already in use")

        # Check format (all digits, reasonable length)
        if len(str(student_number)) > MAX_STUDENT_ID_DIGITS:
            errors.append(f"Student number cannot exceed {MAX_STUDENT_ID_DIGITS} digits")

        return len(errors) == 0, errors

    @classmethod
    def reserve_student_number(cls, student_number: int, notes: str = "") -> bool:
        """Reserve a specific student number for future use.

        This could be used for special cases like transfer students
        who need to maintain their previous student number.

        Args:
            student_number: Number to reserve
            notes: Reason for reservation

        Returns:
            True if successfully reserved, False otherwise
        """
        is_valid, _errors = cls.validate_student_number(student_number)
        # Could implement a reservation table if needed
        return is_valid


class StudentConversionService:
    """Service for converting level testing applicants to full students."""

    @classmethod
    @transaction.atomic
    def convert_potential_student_to_full_student(
        cls,
        potential_student,
        converted_by: "User",
        additional_info: dict | None = None,
    ) -> StudentConversionResult:
        """Convert a level testing PotentialStudent to a full Person and StudentProfile.

        Args:
            potential_student: PotentialStudent instance from level_testing app
            converted_by: User performing the conversion
            additional_info: Optional additional information for the conversion

        Returns:
            Tuple of (Person, StudentProfile) instances

        Raises:
            ValidationError: If conversion violates business rules
        """
        # Validate conversion eligibility
        validation_errors = cls._validate_conversion_eligibility(potential_student)
        if validation_errors:
            raise ValidationError(validation_errors)

        # Check for existing conversion
        if potential_student.converted_person_id:
            msg = "Student has already been converted"
            raise ValidationError(msg)

        # Create Person from PotentialStudent data
        person = cls._create_person_from_potential_student(potential_student)

        # Generate student number
        student_number = StudentNumberService.generate_next_student_number()

        # Create StudentProfile
        student_profile = cls._create_student_profile(
            person=person,
            student_number=student_number,
            potential_student=potential_student,
            additional_info=additional_info,
        )

        # Update PotentialStudent with conversion information
        cls._update_potential_student_conversion_info(
            potential_student=potential_student,
            person=person,
            student_profile=student_profile,
            converted_by=converted_by,
        )

        # Create audit log
        cls._log_student_conversion(
            potential_student=potential_student,
            person=person,
            student_profile=student_profile,
            converted_by=converted_by,
        )

        return person, student_profile

    @classmethod
    def _validate_conversion_eligibility(cls, potential_student) -> ValidationErrors:
        """Validate that a potential student is eligible for conversion."""
        errors = []

        # Check status requirements
        if potential_student.status != "PAID":
            errors.append("Student must have paid status to be converted")

        # Check duplicate screening
        if potential_student.duplicate_check_status != "CONFIRMED_NEW":
            errors.append("Student must pass duplicate screening before conversion")

        # Check if already converted
        if potential_student.converted_person_id:
            errors.append("Student has already been converted")

        # Check required information completeness
        required_fields = [
            "personal_name_eng",
            "family_name_eng",
            "date_of_birth",
            "phone_number",
        ]

        errors.extend(
            f"Required field '{field}' is missing"
            for field in required_fields
            if not getattr(potential_student, field, None)
        )

        return errors

    @classmethod
    def _create_person_from_potential_student(cls, potential_student) -> Person:
        """Create a Person instance from PotentialStudent data."""
        # Determine birth province
        birth_province = None
        if potential_student.birth_province:
            # Map from potential student province to Person province choices
            birth_province = potential_student.birth_province

        # Create Person
        person = Person.objects.create(
            family_name=potential_student.family_name_eng,
            personal_name=potential_student.personal_name_eng,
            khmer_name=(
                potential_student.personal_name_khm + " " + potential_student.family_name_khm
                if potential_student.personal_name_khm and potential_student.family_name_khm
                else ""
            ),
            preferred_gender=cls._convert_gender(potential_student.preferred_gender),
            date_of_birth=potential_student.date_of_birth,
            birth_province=birth_province,
            citizenship="KH",  # Default, could be enhanced based on birth_province
            personal_email=potential_student.personal_email,
        )

        # Create phone numbers
        if potential_student.phone_number:
            PhoneNumber.objects.create(
                person=person,
                number=potential_student.phone_number,
                comment="Primary phone from level testing application",
                is_preferred=True,
                is_telegram=False,  # Could be enhanced to detect Telegram
            )

        if potential_student.telegram_number and potential_student.telegram_number != potential_student.phone_number:
            PhoneNumber.objects.create(
                person=person,
                number=potential_student.telegram_number,
                comment="Telegram number from level testing application",
                is_preferred=False,
                is_telegram=True,
            )

        return person

    @classmethod
    def _convert_gender(cls, potential_student_gender: str) -> str:
        """Convert potential student gender to Person gender choices using pattern matching."""
        match potential_student_gender.lower():
            case "m" | "male":
                return "M"
            case "f" | "female":
                return "F"
            case "n" | "nonbinary" | "non-binary":
                return "N"
            case _:
                return "X"  # Default to "Prefer not to say"

    @classmethod
    def _create_student_profile(
        cls,
        person: Person,
        student_number: int,
        potential_student,
        additional_info: dict | None = None,
    ) -> StudentProfile:
        """Create StudentProfile from Person and additional information."""
        # Determine study time preference using pattern matching
        preferred_slot = potential_student.preferred_time_slot.lower() if potential_student.preferred_time_slot else ""

        match preferred_slot:
            case "morning":
                study_time = "morning"
            case "afternoon":
                study_time = "afternoon"
            case "evening":
                study_time = "evening"
            case _:
                study_time = "evening"  # Default

        return StudentProfile.objects.create(
            person=person,
            student_id=student_number,
            current_status=StudentProfile.Status.ACTIVE,
            study_time_preference=study_time,
            is_transfer_student=False,
            last_enrollment_date=timezone.now().date(),
        )

    @classmethod
    def _update_potential_student_conversion_info(
        cls,
        potential_student,
        person: Person,
        student_profile: StudentProfile,
        converted_by: "User",
    ) -> None:
        """Update PotentialStudent with conversion information."""
        potential_student.converted_person_id = person.id
        potential_student.converted_student_number = student_profile.student_id
        potential_student.status = "CONVERTED"
        potential_student.save(
            update_fields=[
                "converted_person_id",
                "converted_student_number",
                "status",
                "updated_at",
            ],
        )

    @classmethod
    def _log_student_conversion(
        cls,
        potential_student,
        person: Person,
        student_profile: StudentProfile,
        converted_by: "User",
    ) -> None:
        """Create audit logs for the student conversion."""
        # Log in PersonEventLog
        PersonEventLog.objects.create(
            person=person,
            action=PersonEventLog.ActionType.OTHER,
            changed_by=converted_by,
            details={
                "conversion_type": "level_testing_to_student",
                "original_test_number": potential_student.test_number,
                "student_number": student_profile.student_id,
                "conversion_date": timezone.now().isoformat(),
            },
            notes=(
                f"Converted from level testing applicant {potential_student.test_number} "
                f"to student {student_profile.student_id}"
            ),
        )

        # Log in StudentAuditLog
        StudentAuditLog.objects.create(
            student=student_profile,
            action=StudentAuditLog.ActionType.OTHER,
            changed_by=converted_by,
            changes={
                "action": "student_creation_from_level_testing",
                "original_test_number": potential_student.test_number,
                "conversion_date": timezone.now().isoformat(),
            },
            notes=f"Student profile created from level testing application {potential_student.test_number}",
        )

    @classmethod
    def get_conversion_history(cls, potential_student) -> dict | None:
        """Get conversion history for a potential student."""
        if not potential_student.converted_person_id:
            return None

        try:
            person = Person.objects.get(id=potential_student.converted_person_id)
            student_profile = person.student_profile
        except (Person.DoesNotExist, AttributeError):
            return None
        else:
            return {
                "person": person,
                "student_profile": student_profile,
                "conversion_date": potential_student.updated_at,
                "test_number": potential_student.test_number,
                "student_number": student_profile.student_id,
            }

    @classmethod
    def find_potential_student_by_student_number(cls, student_number: int):
        """Find the original level testing application for a student number."""
        try:
            from apps.level_testing.models import PotentialStudent

            return PotentialStudent.objects.get(converted_student_number=student_number)
        except (PotentialStudent.DoesNotExist, ImportError):
            return None


class PersonValidationService:
    """Service for person data validation and business rules."""

    @classmethod
    def validate_person_data(cls, person_data: dict) -> ValidationResult:
        """Validate person data against business rules.

        Args:
            person_data: Dictionary with person information

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Validate required fields
        errors.extend(cls._validate_required_fields(person_data))

        # Validate name formats
        errors.extend(cls._validate_name_formats(person_data))

        # Validate birth province and citizenship consistency
        errors.extend(cls._validate_province_citizenship(person_data))

        # Validate email formats
        errors.extend(cls._validate_email_formats(person_data))

        # Validate date of birth
        errors.extend(cls._validate_birth_date(person_data))

        return len(errors) == 0, errors

    @classmethod
    def _validate_required_fields(cls, person_data: dict) -> list[str]:
        """Validate required fields."""
        required_fields = ["family_name", "personal_name"]
        return [f"Field '{field}' is required" for field in required_fields if not person_data.get(field, "").strip()]

    @classmethod
    def _validate_name_formats(cls, person_data: dict) -> list[str]:
        """Validate name formats."""
        errors = []
        if "family_name" in person_data:
            if not cls._is_valid_name(person_data["family_name"]):
                errors.append("Family name contains invalid characters")

        if "personal_name" in person_data:
            if not cls._is_valid_name(person_data["personal_name"]):
                errors.append("Personal name contains invalid characters")
        return errors

    @classmethod
    def _validate_province_citizenship(cls, person_data: dict) -> list[str]:
        """Validate birth province and citizenship consistency."""
        errors = []
        birth_province = person_data.get("birth_province")
        citizenship = person_data.get("citizenship", "KH")

        if birth_province and citizenship != "KH":
            if is_cambodian_province(birth_province):
                errors.append(
                    "Cambodian birth province not valid for non-Cambodian citizens",
                )
        return errors

    @classmethod
    def _validate_email_formats(cls, person_data: dict) -> list[str]:
        """Validate email formats."""
        errors = []
        email_fields = ["school_email", "personal_email"]
        for field in email_fields:
            email = person_data.get(field)
            if email and not cls._is_valid_email(email):
                errors.append(f"Invalid email format for {field}")
        return errors

    @classmethod
    def _validate_birth_date(cls, person_data: dict) -> list[str]:
        """Validate date of birth."""
        errors = []
        date_of_birth = person_data.get("date_of_birth")
        if date_of_birth and not cls._is_valid_birth_date(date_of_birth):
            errors.append("Invalid date of birth")
        return errors

    @classmethod
    def _is_valid_name(cls, name: str) -> bool:
        """Validate name contains only allowed characters."""
        # Allow letters, spaces, hyphens, apostrophes
        pattern = r"^[a-zA-Z\s\-']+$"
        return bool(re.match(pattern, name.strip()))

    @classmethod
    def _is_valid_email(cls, email: str) -> bool:
        """Basic email format validation."""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email.strip()))

    @classmethod
    def _is_valid_birth_date(cls, birth_date) -> bool:
        """Validate birth date is reasonable."""
        if not birth_date:
            return False

        today = timezone.now().date()

        # Must be in the past
        if birth_date >= today:
            return False

        # Must not be more than MAX_AGE_YEARS years ago
        min_date = today.replace(year=today.year - MAX_AGE_YEARS)
        return not birth_date < min_date


class DuplicateDetectionService:
    """Service for detecting potential duplicate person records."""

    @classmethod
    def find_potential_duplicates(cls, person_data: dict) -> list[dict]:
        """Find potential duplicate person records.

        Args:
            person_data: Dictionary with person information to check

        Returns:
            List of potential matches with confidence scores
        """
        matches: list[PersonMatchData] = []

        # Exact name match
        exact_matches = cls._find_exact_name_matches(person_data)
        matches.extend(exact_matches)

        # Similar name match
        similar_matches = cls._find_similar_name_matches(person_data)
        matches.extend(similar_matches)

        # Phone number match
        phone_matches = cls._find_phone_number_matches(person_data)
        matches.extend(phone_matches)

        # Email match
        email_matches = cls._find_email_matches(person_data)
        matches.extend(email_matches)

        # Date of birth match
        dob_matches = cls._find_date_of_birth_matches(person_data)
        matches.extend(dob_matches)

        # Remove duplicates and sort by confidence
        unique_matches: UniqueMatches = {}
        for match in matches:
            person_id = match["person"].id
            if person_id not in unique_matches or match["confidence"] > unique_matches[person_id]["confidence"]:
                unique_matches[person_id] = match

        return sorted(
            unique_matches.values(),
            key=lambda x: x["confidence"],
            reverse=True,
        )

    @classmethod
    def _find_exact_name_matches(cls, person_data: dict) -> list[dict]:
        """Find exact name matches."""
        matches: list[dict] = []

        family_name = person_data.get("family_name", "").upper().strip()
        personal_name = person_data.get("personal_name", "").upper().strip()

        if family_name and personal_name:
            exact_matches = Person.objects.filter(
                family_name__iexact=family_name,
                personal_name__iexact=personal_name,
            )

            matches.extend(
                {
                    "person": person,
                    "match_type": "exact_name",
                    "confidence": EXACT_NAME_MATCH_CONFIDENCE,
                    "details": f"Exact match: {person.full_name}",
                }
                for person in exact_matches
            )

        return matches

    @classmethod
    def _find_similar_name_matches(cls, person_data: dict) -> list[dict]:
        """Find similar name matches using fuzzy matching."""
        # This could implement sophisticated fuzzy matching
        return []

    @classmethod
    def _find_phone_number_matches(cls, person_data: dict) -> list[dict]:
        """Find matches based on phone numbers."""
        matches: list[PersonMatchData] = []

        phone_number = person_data.get("phone_number", "").strip()

        if phone_number:
            phone_matches = PhoneNumber.objects.filter(
                number=phone_number,
            ).select_related("person")

            matches.extend(
                {
                    "person": phone.person,
                    "match_type": "phone_number",
                    "confidence": PHONE_MATCH_CONFIDENCE,
                    "details": f"Phone number match: {phone_number}",
                }
                for phone in phone_matches
            )

        return matches

    @classmethod
    def _find_email_matches(cls, person_data: dict) -> list[dict]:
        """Find matches based on email addresses."""
        matches: list[PersonMatchData] = []

        email_fields = ["school_email", "personal_email"]

        for field in email_fields:
            email = person_data.get(field, "").strip()
            if email:
                if field == "school_email":
                    email_matches = Person.objects.filter(school_email__iexact=email)
                else:
                    email_matches = Person.objects.filter(personal_email__iexact=email)

                matches.extend(
                    {
                        "person": person,
                        "match_type": "email",
                        "confidence": EMAIL_MATCH_CONFIDENCE,
                        "details": f"Email match: {email}",
                    }
                    for person in email_matches
                )

        return matches

    @classmethod
    def _find_date_of_birth_matches(cls, person_data: dict) -> list[dict]:
        """Find matches based on date of birth."""
        matches: list[PersonMatchData] = []

        date_of_birth = person_data.get("date_of_birth")

        if date_of_birth:
            dob_matches = Person.objects.filter(date_of_birth=date_of_birth)

            matches.extend(
                {
                    "person": person,
                    "match_type": "date_of_birth",
                    "confidence": 0.60,
                    "details": f"Date of birth match: {date_of_birth}",
                }
                for person in dob_matches
            )

        return matches


class StudentLookupService:
    """Service for finding students by various identifiers.

    Centralizes student lookup logic with support for legacy IDs,
    current IDs, and various ID formats.
    """

    @staticmethod
    def find_by_legacy_id(legacy_id: str, include_inactive: bool = False) -> StudentProfile | None:
        """Find a student by their legacy 5-digit ID.

        Args:
            legacy_id: The legacy student ID (will be normalized)
            include_inactive: Whether to include inactive students

        Returns:
            StudentProfile instance or None
        """
        if not legacy_id:
            return None

        # Clean and normalize the ID
        cleaned_id = legacy_id.strip()

        # Remove any non-numeric characters
        numeric_id = "".join(c for c in cleaned_id if c.isdigit())

        if not numeric_id:
            return None

        # Try multiple formats
        try:
            # Convert to integer
            student_id_int = int(numeric_id)

            # Build query - only use student_id field since legacy_student_id doesn't exist
            from django.db.models import Q

            query = Q(student_id=student_id_int)

            # Base queryset
            queryset = StudentProfile.objects.select_related("person")

            # Filter by active status if requested
            if not include_inactive:
                queryset = queryset.filter(is_deleted=False)

            # Try to find the student
            return queryset.filter(query).first()

        except (ValueError, TypeError):
            return None

    @staticmethod
    def find_by_person_id(person_id: int, include_inactive: bool = False) -> StudentProfile | None:
        """Find a student by their person ID.

        Args:
            person_id: The person ID
            include_inactive: Whether to include inactive students

        Returns:
            StudentProfile instance or None
        """
        queryset = StudentProfile.objects.select_related("person")

        if not include_inactive:
            queryset = queryset.filter(is_deleted=False)

        return queryset.filter(person_id=person_id).first()

    @staticmethod
    def find_by_email(email: str, include_inactive: bool = False) -> StudentProfile | None:
        """Find a student by their email address.

        Args:
            email: The email address
            include_inactive: Whether to include inactive students

        Returns:
            StudentProfile instance or None
        """
        if not email:
            return None

        from django.db.models import Q

        queryset = StudentProfile.objects.select_related("person")

        if not include_inactive:
            queryset = queryset.filter(is_deleted=False)

        # Try both person email and school email
        return queryset.filter(
            Q(person__personal_email__iexact=email)
            | Q(person__school_email__iexact=email)
            | Q(school_email__iexact=email)
        ).first()

    @staticmethod
    def search_students(search_term: str, include_inactive: bool = False, limit: int = 10) -> list[StudentProfile]:
        """Search for students by name or ID.

        Args:
            search_term: The search term
            include_inactive: Whether to include inactive students
            limit: Maximum number of results

        Returns:
            List of StudentProfile instances
        """
        if not search_term:
            return []

        from django.db.models import Q

        queryset = StudentProfile.objects.select_related("person")

        if not include_inactive:
            queryset = queryset.filter(is_deleted=False)

        # Build search query
        search_query = Q()

        # Check if search term is numeric (could be ID)
        if search_term.isdigit():
            try:
                student_id = int(search_term)
                search_query |= Q(student_id=student_id)
            except ValueError:
                pass

        # Search by name (first, last, or full)
        search_query |= (
            Q(person__personal_name__icontains=search_term)
            | Q(person__family_name__icontains=search_term)
            | Q(person__khmer_name__icontains=search_term)
        )

        # Search by email
        search_query |= (
            Q(person__personal_email__icontains=search_term)
            | Q(person__school_email__icontains=search_term)
            | Q(school_email__icontains=search_term)
        )

        return list(queryset.filter(search_query)[:limit])


class StudentProfileService:
    """Service for student profile operations and workflows."""

    @classmethod
    @transaction.atomic
    def create_student_with_profile(
        cls,
        person_data: dict | None = None,
        student_data: dict | None = None,
        existing_person: Person | None = None,
        created_by: "User | None" = None,
    ) -> StudentProfile:
        """Create a student profile with associated person.

        This method handles two scenarios:
        1. Create a new person and student profile together
        2. Create a student profile for an existing person

        Args:
            person_data: Dictionary with person information (for new person)
            student_data: Dictionary with student profile information
            existing_person: Existing Person instance (if not creating new)
            created_by: User creating the profile

        Returns:
            Created StudentProfile instance

        Raises:
            ValidationError: If validation fails
        """
        if not existing_person and not person_data:
            raise ValidationError("Either existing_person or person_data must be provided")

        if existing_person and person_data:
            raise ValidationError("Cannot provide both existing_person and person_data")

        if student_data is None:
            student_data = {}

        # Create new person if needed
        if person_data:
            person = Person.objects.create(
                family_name=person_data.get("family_name"),
                personal_name=person_data.get("personal_name"),
                khmer_name=person_data.get("khmer_name", ""),
                preferred_gender=person_data.get("preferred_gender"),
                date_of_birth=person_data.get("date_of_birth"),
                personal_email=person_data.get("personal_email", ""),
                school_email=person_data.get("school_email", ""),
                citizenship=person_data.get("citizenship", "KH"),
            )
        else:
            # At this point, existing_person must not be None due to validation above
            if existing_person is None:
                raise ValidationError("existing_person cannot be None")
            person = existing_person

        # Generate student number if not provided
        if not student_data.get("student_id"):
            student_data["student_id"] = StudentNumberService.generate_next_student_number()

        # Create student profile
        student_profile = StudentProfile.objects.create(
            person=person,
            student_id=student_data.get("student_id"),
            is_monk=student_data.get("is_monk", False),
            is_transfer_student=student_data.get("is_transfer_student", False),
            study_time_preference=student_data.get("study_time_preference", "evening"),
            current_status=student_data.get("current_status", StudentProfile.Status.ACTIVE),
            last_enrollment_date=timezone.now().date(),
        )

        # Create audit log
        if created_by:
            StudentAuditLog.objects.create(
                student=student_profile,
                action=StudentAuditLog.ActionType.CREATE,
                changed_by=created_by,
                changes={
                    "student_id": student_profile.student_id,
                    "person_id": person.id,
                },
                notes="Student profile created",
            )

        return student_profile


class PersonMergeService:
    """Service for merging duplicate person records."""

    @classmethod
    @transaction.atomic
    def merge_person_records(
        cls,
        primary_person: Person,
        duplicate_person: Person,
        merged_by: "User",
        merge_strategy: str = "keep_primary",
    ) -> Person:
        """Merge two person records, keeping the primary and removing the duplicate.

        Args:
            primary_person: Person record to keep
            duplicate_person: Person record to merge and delete
            merged_by: User performing the merge
            merge_strategy: Strategy for handling conflicting data

        Returns:
            Updated primary Person record

        Raises:
            ValidationError: If merge is not valid
        """
        # Validate merge eligibility
        if primary_person.id == duplicate_person.id:
            msg = "Cannot merge person with themselves"
            raise ValidationError(msg)

        # Log the merge operation
        PersonEventLog.objects.create(
            person=primary_person,
            action=PersonEventLog.ActionType.OTHER,
            changed_by=merged_by,
            details={
                "action": "person_merge",
                "duplicate_person_id": duplicate_person.id,
                "duplicate_person_name": duplicate_person.full_name,
                "merge_strategy": merge_strategy,
            },
            notes=f"Merged duplicate person record {duplicate_person.full_name} (ID: {duplicate_person.id})",
        )

        # Merge related records
        cls._merge_phone_numbers(primary_person, duplicate_person)
        cls._merge_emergency_contacts(primary_person, duplicate_person)
        cls._merge_student_profiles(primary_person, duplicate_person, merged_by)

        # Delete duplicate person
        duplicate_person.delete()

        return primary_person

    @classmethod
    def _merge_phone_numbers(
        cls,
        primary_person: Person,
        duplicate_person: Person,
    ) -> None:
        """Merge phone numbers from duplicate to primary person."""
        duplicate_phones = PhoneNumber.objects.filter(person=duplicate_person)

        for phone in duplicate_phones:
            # Check if primary person already has this number
            existing = PhoneNumber.objects.filter(
                person=primary_person,
                number=phone.number,
            ).exists()

            if not existing:
                phone.person = primary_person
                phone.is_preferred = False  # Avoid conflicts
                phone.save()
            else:
                phone.delete()

    @classmethod
    def _merge_emergency_contacts(
        cls,
        primary_person: Person,
        duplicate_person: Person,
    ) -> None:
        """Merge emergency contacts from duplicate to primary person."""
        duplicate_contacts = EmergencyContact.objects.filter(person=duplicate_person)

        for contact in duplicate_contacts:
            contact.person = primary_person
            contact.is_primary = False  # Avoid conflicts
            contact.save()

    @classmethod
    def _merge_student_profiles(
        cls,
        primary_person: Person,
        duplicate_person: Person,
        merged_by: "User",
    ) -> None:
        """Handle student profile merging."""
        try:
            duplicate_student = duplicate_person.student_profile
            try:
                primary_student = primary_person.student_profile
                # Both have student profiles - this is complex, log for manual review
                PersonEventLog.objects.create(
                    person=primary_person,
                    action=PersonEventLog.ActionType.OTHER,
                    changed_by=merged_by,
                    details={
                        "action": "manual_review_required",
                        "reason": "both_persons_have_student_profiles",
                        "duplicate_student_id": duplicate_student.student_id,
                        "primary_student_id": primary_student.student_id,
                    },
                    notes="Manual review required: both persons have student profiles",
                )
            except AttributeError:
                # Only duplicate has student profile - transfer it
                duplicate_student.person = primary_person
                duplicate_student.save()
        except AttributeError:
            # Duplicate doesn't have student profile - nothing to do
            pass
