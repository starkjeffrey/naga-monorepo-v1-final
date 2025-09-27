"""Level testing services for business logic operations.

This module contains service classes that implement business logic for the level
testing app while maintaining clean architecture principles. Services avoid
circular dependencies by using ID references for external models.

Key services:
- DuplicateDetectionService: Identifies potential duplicates against people app
- TestWorkflowService: Manages test application workflow
- FinanceIntegrationService: Handles test fee integration with finance app
"""

import logging
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Any

from django.utils import timezone

logger = logging.getLogger(__name__)


class DuplicateDetectionService:
    """Service for detecting potential duplicate students against existing Person records.

    Implements fuzzy matching algorithms to identify potential duplicates based on:
    - Name similarity (English and Khmer)
    - Birth date matches
    - Phone number matches
    - Email matches
    - Province matches

    Uses confidence scoring to rank potential matches for staff review.
    """

    # Confidence thresholds for different match types
    EXACT_NAME_THRESHOLD = 0.95
    SIMILAR_NAME_THRESHOLD = 0.75
    PHONE_MATCH_WEIGHT = 0.9
    EMAIL_MATCH_WEIGHT = 0.9
    DOB_MATCH_WEIGHT = 0.8
    SIMILAR_DOB_WEIGHT = 0.6  # For similar (not exact) birth dates
    PROVINCE_MATCH_WEIGHT = 0.6  # Increased per user requirements
    PROGRAM_LEVEL_MATCH_WEIGHT = 0.4  # New: program/level matching

    def __init__(self):
        """Initialize the duplicate detection service."""
        self.person_model = None
        self.duplicate_candidate_model = None
        self._initialize_models()

    def _initialize_models(self) -> None:
        """Initialize model references to avoid circular imports."""
        try:
            from apps.level_testing.models import DuplicateCandidate
            from apps.people.models import Person

            self.person_model = Person
            self.duplicate_candidate_model = DuplicateCandidate
        except ImportError as e:
            logger.warning("Could not import models for duplicate detection: %s", e)

    def check_for_duplicates(self, potential_student) -> list[dict[str, Any]]:
        """Check for potential duplicates against existing Person records.

        Args:
            potential_student: PotentialStudent instance to check

        Returns:
            List of potential duplicate matches with confidence scores
        """
        if not self.person_model:
            logger.error("Person model not available for duplicate detection")
            return []

        potential_duplicates = []

        # Get all existing persons for comparison (optimized to prevent N+1 queries)
        existing_persons = (
            self.person_model.objects.filter(is_deleted=False)
            .select_related(
                "student_profile",  # Optimize debt checking
            )
            .prefetch_related(
                "student_profile__program_enrollments",  # Optimize program checking
            )
        )

        for person in existing_persons:
            match_data = self._analyze_potential_match(potential_student, person)

            if match_data["confidence_score"] > 0.3:  # Minimum threshold
                potential_duplicates.append(match_data)

        # Sort by confidence score (highest first)
        potential_duplicates.sort(key=lambda x: x["confidence_score"], reverse=True)

        return potential_duplicates[:10]  # Return top 10 matches

    def _analyze_potential_match(self, potential_student, person) -> dict[str, Any]:
        """Analyze a potential match between a potential student and existing person.

        Args:
            potential_student: PotentialStudent instance
            person: Person instance from people app

        Returns:
            Dictionary with match analysis results
        """
        match_data = {
            "person_id": person.id,
            "person_name": self._get_person_full_name(person),
            "match_type": "COMBINED",
            "confidence_score": 0.0,
            "match_factors": [],
            "has_outstanding_debt": False,
            "debt_amount": None,
        }

        confidence_score = 0.0
        match_factors = []

        # Check name similarity (English)
        name_score = self._calculate_name_similarity(
            potential_student.full_name_eng,
            self._get_person_full_name(person),
        )

        if name_score >= self.EXACT_NAME_THRESHOLD:
            confidence_score += 0.4
            match_factors.append("Exact name match")
            match_data["match_type"] = "EXACT_NAME"
        elif name_score >= self.SIMILAR_NAME_THRESHOLD:
            confidence_score += 0.3
            match_factors.append("Similar name")
            match_data["match_type"] = "SIMILAR_NAME"

        # Check birth date (exact and similar) - enhanced per user requirements
        dob_match_type = self._enhanced_date_comparison(
            potential_student.date_of_birth,
            getattr(person, "date_of_birth", None),
        )
        if dob_match_type == "exact":
            confidence_score += self.DOB_MATCH_WEIGHT * 0.4
            match_factors.append("Exact birth date match")
            if match_data["match_type"] == "COMBINED":
                match_data["match_type"] = "DOB_MATCH"
        elif dob_match_type == "similar":
            confidence_score += self.SIMILAR_DOB_WEIGHT * 0.3
            match_factors.append("Similar birth date (within 30 days)")
            if match_data["match_type"] == "COMBINED":
                match_data["match_type"] = "SIMILAR_DOB_MATCH"

        # Check phone number
        phone_attr = getattr(person, "phone_number", None)
        if self._phone_numbers_match(
            potential_student.phone_number,
            str(phone_attr) if phone_attr else "",
        ):
            confidence_score += self.PHONE_MATCH_WEIGHT * 0.25
            match_factors.append("Phone number match")
            if match_data["match_type"] == "COMBINED":
                match_data["match_type"] = "PHONE_MATCH"

        # Check email
        email_attr = getattr(person, "personal_email", None)
        if self._emails_match(
            potential_student.personal_email,
            str(email_attr) if email_attr else "",
        ):
            confidence_score += self.EMAIL_MATCH_WEIGHT * 0.2
            match_factors.append("Email match")
            if match_data["match_type"] == "COMBINED":
                match_data["match_type"] = "EMAIL_MATCH"

        # Check province
        province_attr = getattr(person, "birth_province", None)
        if self._provinces_match(
            potential_student.birth_province,
            str(province_attr) if province_attr else "",
        ):
            confidence_score += self.PROVINCE_MATCH_WEIGHT * 0.1
            match_factors.append("Same birth province")

        # Check program/level matching (new per user requirements)
        program_level_match = self._check_program_level_similarity(potential_student, person)
        if program_level_match["match_found"]:
            confidence_score += self.PROGRAM_LEVEL_MATCH_WEIGHT * 0.2
            match_factors.append(program_level_match["message"])

        # Check for outstanding debt (if person has student profile)
        debt_info = self._check_outstanding_debt(person)
        if debt_info["has_debt"]:
            match_data["has_outstanding_debt"] = True
            match_data["debt_amount"] = debt_info["amount"]
            confidence_score += 0.1  # Slight boost for debt concerns

        match_data["confidence_score"] = min(1.0, confidence_score)
        match_data["match_factors"] = match_factors

        return match_data

    def _calculate_name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names using SequenceMatcher.

        Args:
            name1: First name to compare
            name2: Second name to compare

        Returns:
            Similarity score between 0.0 and 1.0
        """
        if not name1 or not name2:
            return 0.0

        # Normalize names for comparison
        name1_norm = name1.lower().strip()
        name2_norm = name2.lower().strip()

        # Direct comparison
        direct_similarity = SequenceMatcher(None, name1_norm, name2_norm).ratio()

        # Also check token-based similarity (handle different word orders)
        tokens1 = set(name1_norm.split())
        tokens2 = set(name2_norm.split())

        if tokens1 and tokens2:
            token_similarity = len(tokens1 & tokens2) / len(tokens1 | tokens2)
            # Use the higher of the two similarities
            return max(direct_similarity, token_similarity)

        return direct_similarity

    def _enhanced_date_comparison(self, date1, date2) -> str:
        """Enhanced date comparison for similar (not just exact) birthdate matching.

        Per user requirements: "similar birthdate" should be a matching factor.

        Args:
            date1: First date to compare
            date2: Second date to compare

        Returns:
            "exact" for exact matches, "similar" for within 30 days, "no_match" otherwise
        """
        if not date1 or not date2:
            return "no_match"

        if date1 == date2:
            return "exact"

        # Check if dates are within 30 days of each other

        diff = abs((date1 - date2).days)
        if diff <= 30:
            return "similar"

        return "no_match"

    def _check_program_level_similarity(self, potential_student, person) -> dict[str, Any]:
        """Check if potential student and existing person have similar program/level enrollments.

        Per user requirements: "enrolling in the same program at approximately the same level
        as a possible duplicate would be a hint."

        Args:
            potential_student: PotentialStudent instance
            person: Person instance from people app

        Returns:
            Dictionary with match_found boolean and descriptive message
        """
        result = {"match_found": False, "message": ""}

        # Get person's student profile and program enrollments (already prefetched)
        if not hasattr(person, "student_profile") or not person.student_profile:
            return result

        student_profile = person.student_profile
        program_enrollments = student_profile.program_enrollments.filter(status="ACTIVE")

        if not program_enrollments.exists():
            return result

        # TODO: Implement program/level matching logic
        # This requires business clarification:
        # 1. How to map potential_student.preferred_program to curriculum.Major?
        # 2. What constitutes "approximately the same level"?
        # 3. Should we match by division/cycle or specific program?

        # Placeholder implementation for now
        # Check if potential student's preferred program matches any active enrollment
        for enrollment in program_enrollments:
            if (
                hasattr(potential_student, "preferred_program")
                and potential_student.preferred_program
                and enrollment.program.name.lower() in potential_student.preferred_program.lower()
            ):
                result["match_found"] = True
                result["message"] = f"Similar program enrollment: {enrollment.program.name}"
                break

        return result

    def _dates_match(self, date1, date2) -> bool:
        """Check if two dates match."""
        if not date1 or not date2:
            return False
        return date1 == date2

    def _phone_numbers_match(self, phone1: str, phone2: str) -> bool:
        """Check if two phone numbers match.

        Normalizes phone numbers by removing non-digit characters.
        """
        if not phone1 or not phone2:
            return False

        # Normalize phone numbers (keep only digits)
        phone1_norm = "".join(filter(str.isdigit, phone1))
        phone2_norm = "".join(filter(str.isdigit, phone2))

        if len(phone1_norm) < 8 or len(phone2_norm) < 8:
            return False

        # Check if they match exactly or if one contains the other
        return (
            phone1_norm == phone2_norm
            or phone1_norm.endswith(phone2_norm[-8:])
            or phone2_norm.endswith(phone1_norm[-8:])
        )

    def _emails_match(self, email1: str, email2: str) -> bool:
        """Check if two email addresses match."""
        if not email1 or not email2:
            return False
        return email1.lower().strip() == email2.lower().strip()

    def _provinces_match(self, province1: str, province2: str) -> bool:
        """Check if two provinces match."""
        if not province1 or not province2:
            return False
        return province1 == province2

    def _get_person_full_name(self, person) -> str:
        """Get full name from person object.

        Handles different possible name field structures in Person model.
        """
        # Try different possible name field combinations
        if hasattr(person, "full_name_eng") and person.full_name_eng:
            return person.full_name_eng

        if hasattr(person, "personal_name_eng") and hasattr(person, "family_name_eng"):
            if person.personal_name_eng and person.family_name_eng:
                return f"{person.personal_name_eng} {person.family_name_eng}"

        if hasattr(person, "first_name") and hasattr(person, "last_name"):
            if person.first_name and person.last_name:
                return f"{person.first_name} {person.last_name}"

        # Fallback to string representation
        return str(person)

    def _check_outstanding_debt(self, person) -> dict[str, Any]:
        """Check if person has outstanding debt.

        This would integrate with the finance app to check for unpaid balances.
        For now, returns a placeholder implementation.
        """
        # TODO: Implement actual debt checking with finance app integration
        # This would query the finance app for outstanding balances

        # Placeholder implementation
        return {
            "has_debt": False,
            "amount": None,
        }

    def create_duplicate_candidates(
        self,
        potential_student,
        matches: list[dict[str, Any]],
    ) -> int:
        """Create DuplicateCandidate records for potential matches.

        Args:
            potential_student: PotentialStudent instance
            matches: List of potential match data

        Returns:
            Number of duplicate candidates created
        """
        if not self.duplicate_candidate_model:
            logger.error("DuplicateCandidate model not available")
            return 0

        created_count = 0

        for match in matches:
            # Skip low confidence matches
            if match["confidence_score"] < 0.5:
                continue

            # Check if duplicate candidate already exists
            existing = self.duplicate_candidate_model.objects.filter(
                potential_student=potential_student,
                existing_person_id=match["person_id"],
            ).first()

            if existing:
                continue  # Skip if already exists

            try:
                self.duplicate_candidate_model.objects.create(
                    potential_student=potential_student,
                    existing_person_id=match["person_id"],
                    match_type=match["match_type"],
                    confidence_score=Decimal(str(match["confidence_score"])),
                    matched_name=match["person_name"],
                    has_outstanding_debt=match["has_outstanding_debt"],
                    debt_amount=match["debt_amount"],
                )
                created_count += 1

                logger.info(
                    "Created duplicate candidate: %s → %s (confidence: %.2f)",
                    potential_student.full_name_eng,
                    match["person_name"],
                    match["confidence_score"],
                )

            except Exception as e:
                logger.exception(
                    "Failed to create duplicate candidate for %s: %s",
                    potential_student.full_name_eng,
                    e,
                )

        return created_count

    def merge_student_records(self, potential_student, target_person_id: int, merged_by) -> bool:
        """TODO: Implement student record merging functionality.

        Per user requirements: "We don't want to create a new student number for a returning student.
        So we should use what information we have to determine that the person is a duplicate...
        Need a 'super function' to merge duplicates."

        This should:
        1. Merge potential student data with existing Person record
        2. Update existing student profile with any new information
        3. Mark potential student as converted to existing student
        4. Create audit trail of the merge operation
        5. Handle conflicts in data (e.g., different phone numbers)
        6. Transfer any test payments to existing student record

        Args:
            potential_student: PotentialStudent to merge
            target_person_id: ID of existing Person to merge into
            merged_by: User performing the merge operation

        Returns:
            True if merge successful, False otherwise
        """
        # TODO: Implement comprehensive student record merging
        logger.info(
            "Student record merging requested: %s → Person #%s",
            potential_student.full_name_eng,
            target_person_id,
        )
        return False  # Placeholder

    def update_potential_student_duplicate_status(self, potential_student) -> None:
        """Update the potential student's duplicate check status based on candidates.

        Args:
            potential_student: PotentialStudent instance to update
        """
        from apps.level_testing.models import DuplicateStatus

        candidates = potential_student.duplicate_candidates.all()

        if not candidates:
            potential_student.duplicate_check_status = DuplicateStatus.CONFIRMED_NEW
            potential_student.duplicate_check_performed = True
        else:
            # Check for high-confidence matches or debt concerns
            high_confidence = candidates.filter(confidence_score__gte=0.8)
            debt_concerns = candidates.filter(has_outstanding_debt=True)

            if debt_concerns.exists():
                potential_student.duplicate_check_status = DuplicateStatus.DEBT_CONCERN
            elif high_confidence.exists():
                potential_student.duplicate_check_status = DuplicateStatus.MANUAL_REVIEW
            else:
                potential_student.duplicate_check_status = DuplicateStatus.PENDING

            potential_student.duplicate_check_performed = True

        potential_student.save(
            update_fields=["duplicate_check_status", "duplicate_check_performed"],
        )


class TestWorkflowService:
    """Service for managing the test application workflow.

    Handles status transitions and business logic for moving potential students
    through the testing process from initial application to enrollment or decline.
    """

    def __init__(self):
        """Initialize the test workflow service."""
        self.duplicate_service = DuplicateDetectionService()

    def process_registration(self, potential_student) -> bool:
        """Process registration for a potential student.

        Performs duplicate checking and advances status if appropriate.

        Args:
            potential_student: PotentialStudent instance

        Returns:
            True if registration processed successfully
        """
        from apps.level_testing.models import ApplicationStatus, DuplicateStatus

        try:
            # Perform duplicate detection
            matches = self.duplicate_service.check_for_duplicates(potential_student)
            candidates_created = self.duplicate_service.create_duplicate_candidates(
                potential_student,
                matches,
            )

            # Update duplicate status
            self.duplicate_service.update_potential_student_duplicate_status(
                potential_student,
            )

            # Advance status based on duplicate check results
            if potential_student.duplicate_check_status == DuplicateStatus.CONFIRMED_NEW:
                potential_student.advance_status(
                    ApplicationStatus.REGISTERED,
                    "Registration complete. No duplicates found.",
                    user=None,
                )
            else:
                potential_student.advance_status(
                    ApplicationStatus.DUPLICATE_CHECK,
                    f"Registration complete. {candidates_created} potential duplicates found for review.",
                    user=None,
                )

            logger.info(
                "Processed registration for %s. Status: %s, Duplicate status: %s",
                potential_student.full_name_eng,
                potential_student.status,
                potential_student.duplicate_check_status,
            )

            return True

        except Exception as e:
            logger.exception(
                "Failed to process registration for %s: %s",
                potential_student.full_name_eng,
                e,
            )
            return False

    def clear_duplicate_concerns(
        self,
        potential_student,
        cleared_by,
        notes: str = "",
    ) -> bool:
        """Clear duplicate concerns for a potential student.

        Args:
            potential_student: PotentialStudent instance
            cleared_by: User who is clearing the concerns
            notes: Notes about the clearance

        Returns:
            True if cleared successfully
        """
        from apps.level_testing.models import ApplicationStatus, DuplicateStatus

        try:
            potential_student.duplicate_check_status = DuplicateStatus.CONFIRMED_NEW
            potential_student.duplicate_check_cleared_by = cleared_by
            potential_student.duplicate_check_cleared_at = timezone.now()
            potential_student.duplicate_check_notes = notes

            potential_student.save(
                update_fields=[
                    "duplicate_check_status",
                    "duplicate_check_cleared_by",
                    "duplicate_check_cleared_at",
                    "duplicate_check_notes",
                ],
            )

            # Advance to registered status if coming from duplicate check
            if potential_student.status == ApplicationStatus.DUPLICATE_CHECK:
                potential_student.advance_status(
                    ApplicationStatus.REGISTERED,
                    f"Duplicate concerns cleared by {cleared_by.email}",
                    user=cleared_by,
                )

            logger.info(
                "Cleared duplicate concerns for %s by %s",
                potential_student.full_name_eng,
                cleared_by.email,
            )

            return True

        except Exception as e:
            logger.exception(
                "Failed to clear duplicate concerns for %s: %s",
                potential_student.full_name_eng,
                e,
            )
            return False


class FinanceIntegrationService:
    """Service for integrating test fees with the finance app.

    Handles creation of external fee transactions and G/L reporting integration.
    """

    def __init__(self):
        """Initialize the finance integration service."""
        self.transaction_model = None
        self._initialize_models()

    def _initialize_models(self) -> None:
        """Initialize model references to avoid circular imports."""
        try:
            pass
        except ImportError as e:
            logger.warning("Could not import finance models: %s", e)

    def create_test_fee_transaction(self, test_payment) -> int | None:
        """Create a finance transaction for a test fee payment.

        Args:
            test_payment: TestPayment instance

        Returns:
            Finance transaction ID if successful, None otherwise
        """
        # TODO: Implement actual finance integration
        # This would create a transaction in the finance app

        try:
            # Placeholder implementation
            # In reality, this would:
            # 1. Create a Transaction record in the finance app
            # 2. Set appropriate G/L accounts for test fees
            # 3. Handle different payment methods
            # 4. Return the transaction ID

            logger.info(
                "Would create finance transaction for test payment: %s - $%s",
                test_payment.potential_student.full_name_eng,
                test_payment.amount,
            )

            return 999999  # Placeholder

        except Exception as e:
            logger.exception("Failed to create finance transaction: %s", e)
            return None

    def update_payment_status(self, test_payment, transaction_id: int) -> bool:
        """Update test payment with finance transaction reference.

        Args:
            test_payment: TestPayment instance
            transaction_id: Finance transaction ID

        Returns:
            True if updated successfully
        """
        try:
            test_payment.finance_transaction_id = transaction_id
            test_payment.save(update_fields=["finance_transaction_id"])

            logger.info(
                "Updated test payment %s with finance transaction %s",
                test_payment.id,
                transaction_id,
            )

            return True

        except Exception as e:
            logger.exception("Failed to update payment status: %s", e)
            return False
