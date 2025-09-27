"""from datetime import date
Comprehensive tests for people services.

Tests all business logic services in the people app including:
- StudentNumberService: Student number generation and management
- StudentConversionService: Level testing applicant to student conversion
- PersonValidationService: Person data validation
- DuplicateDetectionService: Duplicate person detection
- PersonMergeService: Person record merging

These tests ensure proper business logic implementation while maintaining
clean architecture principles and avoiding circular dependencies.
"""

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.common.constants import CambodianProvinces
from apps.people.models import (
    EmergencyContact,
    Person,
    PersonEventLog,
    PhoneNumber,
    StudentAuditLog,
    StudentProfile,
)
from apps.people.services import (
    DuplicateDetectionService,
    PersonMergeService,
    PersonValidationService,
    StudentConversionService,
    StudentNumberService,
)

User = get_user_model()


class StudentNumberServiceTest(TransactionTestCase):
    """Test StudentNumberService functionality."""

    def setUp(self):
        """Set up test data."""
        self.person = Person.objects.create(
            personal_name="John",
            family_name="Doe",
            date_of_birth="1990-01-01",
        )

    def test_generate_next_student_number_postgres_sequence(self):
        """Test generating student number using PostgreSQL sequence."""
        student_number = StudentNumberService.generate_next_student_number(use_postgres_sequence=True)

        assert student_number >= 100001
        assert isinstance(student_number, int)

    def test_generate_next_student_number_application_logic_new_installation(self):
        """Test generating student number using application logic on new installation."""
        student_number = StudentNumberService.generate_next_student_number(use_postgres_sequence=False)

        assert student_number == 100001

    def test_generate_next_student_number_application_logic_existing_students(self):
        """Test generating student number with existing students."""
        # Create existing student
        StudentProfile.objects.create(
            person=self.person,
            student_id=100005,
        )

        student_number = StudentNumberService.generate_next_student_number(use_postgres_sequence=False)

        assert student_number == 100006

    def test_generate_next_student_number_application_logic_with_gaps(self):
        """Test generating student number with gaps in sequence."""
        # Create students with gaps
        person2 = Person.objects.create(
            personal_name="Jane",
            family_name="Smith",
            date_of_birth="1991-01-01",
        )

        StudentProfile.objects.create(person=self.person, student_id=100001)
        StudentProfile.objects.create(person=person2, student_id=100005)

        student_number = StudentNumberService.generate_next_student_number(use_postgres_sequence=False)

        assert student_number == 100006

    def test_validate_student_number_valid(self):
        """Test validating a valid student number."""
        is_valid, errors = StudentNumberService.validate_student_number(123456)

        assert is_valid
        assert len(errors) == 0

    def test_validate_student_number_negative(self):
        """Test validating a negative student number."""
        is_valid, errors = StudentNumberService.validate_student_number(-123)

        assert not is_valid
        assert "must be positive" in errors[0]

    def test_validate_student_number_too_small(self):
        """Test validating a student number below minimum."""
        is_valid, errors = StudentNumberService.validate_student_number(99999)

        assert not is_valid
        assert "must be at least 100001" in errors[0]

    def test_validate_student_number_already_in_use(self):
        """Test validating a student number that's already in use."""
        StudentProfile.objects.create(person=self.person, student_id=123456)

        is_valid, errors = StudentNumberService.validate_student_number(123456)

        assert not is_valid
        assert "already in use" in errors[0]

    def test_validate_student_number_too_long(self):
        """Test validating a student number that's too long."""
        is_valid, errors = StudentNumberService.validate_student_number(12345678901)

        assert not is_valid
        assert "cannot exceed 10 digits" in errors[0]

    def test_reserve_student_number_valid(self):
        """Test reserving a valid student number."""
        success = StudentNumberService.reserve_student_number(123456, "Reserved for transfer student")

        assert success

    def test_reserve_student_number_invalid(self):
        """Test reserving an invalid student number."""
        success = StudentNumberService.reserve_student_number(-123, "Invalid number")

        assert not success


class StudentConversionServiceTest(TestCase):
    """Test StudentConversionService functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        self.potential_student = MagicMock()
        self.potential_student.id = 1
        self.potential_student.test_number = "T0001234"
        self.potential_student.status = "PAID"
        self.potential_student.duplicate_check_status = "CONFIRMED_NEW"
        self.potential_student.converted_person_id = None
        self.potential_student.personal_name_eng = "John"
        self.potential_student.family_name_eng = "Smith"
        self.potential_student.personal_name_khm = "ចន"
        self.potential_student.family_name_khm = "ស្មីត"
        self.potential_student.preferred_gender = "M"
        self.potential_student.date_of_birth = timezone.now().date() - timezone.timedelta(days=7300)  # ~20 years old
        self.potential_student.birth_province = CambodianProvinces.PHNOM_PENH
        self.potential_student.personal_email = "john.smith@example.com"
        self.potential_student.phone_number = "+855123456789"
        self.potential_student.telegram_number = "+855987654321"
        self.potential_student.preferred_time_slot = "morning"
        self.potential_student.updated_at = timezone.now()

    @patch.object(StudentNumberService, "generate_next_student_number")
    def test_convert_potential_student_to_full_student_success(self, mock_generate_number):
        """Test successful conversion of potential student to full student."""
        mock_generate_number.return_value = 100001

        person, student_profile = StudentConversionService.convert_potential_student_to_full_student(
            potential_student=self.potential_student,
            converted_by=self.user,
        )

        # Verify Person was created correctly
        assert person.personal_name == "JOHN"  # Should be uppercase
        assert person.family_name == "SMITH"  # Should be uppercase
        assert person.khmer_name == "ចន ស្មីត"
        assert person.preferred_gender == "M"
        assert person.personal_email == "john.smith@example.com"

        # Verify StudentProfile was created correctly
        assert student_profile.person == person
        assert student_profile.student_id == 100001
        assert student_profile.current_status == StudentProfile.Status.ACTIVE
        assert student_profile.study_time_preference == "morning"
        assert not student_profile.is_transfer_student

        # Verify phone numbers were created
        phone_numbers = PhoneNumber.objects.filter(person=person)
        assert phone_numbers.count() == 2

        primary_phone = phone_numbers.get(is_preferred=True)
        assert primary_phone.number == "+855123456789"
        assert not primary_phone.is_telegram

        telegram_phone = phone_numbers.get(is_telegram=True)
        assert telegram_phone.number == "+855987654321"
        assert not telegram_phone.is_preferred

        # Verify audit logs were created
        assert PersonEventLog.objects.filter(person=person).exists()
        assert StudentAuditLog.objects.filter(student=student_profile).exists()

        mock_generate_number.assert_called_once_with()

    def test_convert_potential_student_validation_not_paid(self):
        """Test conversion fails when student hasn't paid."""
        self.potential_student.status = "PENDING"

        with pytest.raises(ValidationError) as exc_info:
            StudentConversionService.convert_potential_student_to_full_student(
                potential_student=self.potential_student,
                converted_by=self.user,
            )

        assert "must have paid status" in str(exc_info.value)

    def test_convert_potential_student_validation_duplicate_not_confirmed(self):
        """Test conversion fails when duplicate check not confirmed."""
        self.potential_student.duplicate_check_status = "NEEDS_REVIEW"

        with pytest.raises(ValidationError) as exc_info:
            StudentConversionService.convert_potential_student_to_full_student(
                potential_student=self.potential_student,
                converted_by=self.user,
            )

        assert "must pass duplicate screening" in str(exc_info.value)

    def test_convert_potential_student_validation_already_converted(self):
        """Test conversion fails when already converted."""
        self.potential_student.converted_person_id = 123

        with pytest.raises(ValidationError) as exc_info:
            StudentConversionService.convert_potential_student_to_full_student(
                potential_student=self.potential_student,
                converted_by=self.user,
            )

        assert "already been converted" in str(exc_info.value)

    def test_convert_potential_student_validation_missing_required_fields(self):
        """Test conversion fails when required fields are missing."""
        self.potential_student.personal_name_eng = None

        with pytest.raises(ValidationError) as exc_info:
            StudentConversionService.convert_potential_student_to_full_student(
                potential_student=self.potential_student,
                converted_by=self.user,
            )

        assert "Required field 'personal_name_eng' is missing" in str(exc_info.value)

    def test_convert_gender_mapping(self):
        """Test gender conversion mapping."""
        assert StudentConversionService._convert_gender("M") == "M"
        assert StudentConversionService._convert_gender("F") == "F"
        assert StudentConversionService._convert_gender("Male") == "M"
        assert StudentConversionService._convert_gender("Female") == "F"
        assert StudentConversionService._convert_gender("male") == "M"
        assert StudentConversionService._convert_gender("female") == "F"
        assert StudentConversionService._convert_gender("Unknown") == "X"

    def test_get_conversion_history_exists(self):
        """Test getting conversion history for converted student."""
        # Create a real conversion
        person = Person.objects.create(
            personal_name="John",
            family_name="Smith",
            date_of_birth="1990-01-01",
        )

        student_profile = StudentProfile.objects.create(
            person=person,
            student_id=100001,
        )

        self.potential_student.converted_person_id = person.id

        history = StudentConversionService.get_conversion_history(self.potential_student)

        assert history is not None
        assert history["person"] == person
        assert history["student_profile"] == student_profile
        assert history["test_number"] == "T0001234"
        assert history["student_number"] == 100001

    def test_get_conversion_history_not_converted(self):
        """Test getting conversion history for non-converted student."""
        self.potential_student.converted_person_id = None

        history = StudentConversionService.get_conversion_history(self.potential_student)

        assert history is None

    @patch("apps.people.services.PotentialStudent")
    def test_find_potential_student_by_student_number(self, mock_potential_student_model):
        """Test finding potential student by student number."""
        mock_potential_student_model.objects.get.return_value = self.potential_student

        result = StudentConversionService.find_potential_student_by_student_number(100001)

        assert result == self.potential_student
        mock_potential_student_model.objects.get.assert_called_once_with(converted_student_number=100001)

    @patch("apps.people.services.PotentialStudent")
    def test_find_potential_student_by_student_number_not_found(self, mock_potential_student_model):
        """Test finding potential student by student number when not found."""
        mock_potential_student_model.objects.get.side_effect = Exception("Not found")

        result = StudentConversionService.find_potential_student_by_student_number(100001)

        assert result is None


class PersonValidationServiceTest(TestCase):
    """Test PersonValidationService functionality."""

    def test_validate_person_data_valid(self):
        """Test validating valid person data."""
        person_data = {
            "family_name": "Smith",
            "personal_name": "John",
            "date_of_birth": timezone.now().date() - timezone.timedelta(days=7300),
            "birth_province": CambodianProvinces.PHNOM_PENH,
            "citizenship": "KH",
            "personal_email": "john@example.com",
        }

        is_valid, errors = PersonValidationService.validate_person_data(person_data)

        assert is_valid
        assert len(errors) == 0

    def test_validate_person_data_missing_required_fields(self):
        """Test validating person data with missing required fields."""
        person_data = {
            "family_name": "",  # Missing
            "personal_name": "John",
        }

        is_valid, errors = PersonValidationService.validate_person_data(person_data)

        assert not is_valid
        assert "Field 'family_name' is required" in errors

    def test_validate_person_data_invalid_name_characters(self):
        """Test validating person data with invalid name characters."""
        person_data = {
            "family_name": "Smith123",  # Invalid characters
            "personal_name": "John",
        }

        is_valid, errors = PersonValidationService.validate_person_data(person_data)

        assert not is_valid
        assert "Family name contains invalid characters" in errors

    def test_validate_person_data_cambodian_province_non_cambodian_citizen(self):
        """Test validating non-Cambodian citizen with Cambodian province."""
        person_data = {
            "family_name": "Smith",
            "personal_name": "John",
            "birth_province": CambodianProvinces.PHNOM_PENH,
            "citizenship": "US",
        }

        with patch("apps.people.services.is_cambodian_province", return_value=True):
            is_valid, errors = PersonValidationService.validate_person_data(person_data)

        assert not is_valid
        assert "not valid for non-Cambodian citizens" in errors[0]

    def test_validate_person_data_invalid_email(self):
        """Test validating person data with invalid email."""
        person_data = {
            "family_name": "Smith",
            "personal_name": "John",
            "personal_email": "invalid-email",
        }

        is_valid, errors = PersonValidationService.validate_person_data(person_data)

        assert not is_valid
        assert "Invalid email format" in errors[0]

    def test_validate_person_data_invalid_birth_date_future(self):
        """Test validating person data with future birth date."""
        person_data = {
            "family_name": "Smith",
            "personal_name": "John",
            "date_of_birth": timezone.now().date() + timezone.timedelta(days=30),
        }

        is_valid, errors = PersonValidationService.validate_person_data(person_data)

        assert not is_valid
        assert "Invalid date of birth" in errors

    def test_validate_person_data_invalid_birth_date_too_old(self):
        """Test validating person data with birth date too far in past."""
        person_data = {
            "family_name": "Smith",
            "personal_name": "John",
            "date_of_birth": timezone.now().date() - timezone.timedelta(days=44000),  # ~120 years
        }

        is_valid, errors = PersonValidationService.validate_person_data(person_data)

        assert not is_valid
        assert "Invalid date of birth" in errors

    def test_is_valid_name(self):
        """Test name validation method."""
        assert PersonValidationService._is_valid_name("John")
        assert PersonValidationService._is_valid_name("Mary-Jane")
        assert PersonValidationService._is_valid_name("O'Connor")
        assert PersonValidationService._is_valid_name("van der Berg")
        assert not PersonValidationService._is_valid_name("John123")
        assert not PersonValidationService._is_valid_name("John@email")

    def test_is_valid_email(self):
        """Test email validation method."""
        assert PersonValidationService._is_valid_email("john@example.com")
        assert PersonValidationService._is_valid_email("john.doe+test@university.edu")
        assert not PersonValidationService._is_valid_email("invalid-email")
        assert not PersonValidationService._is_valid_email("@example.com")
        assert not PersonValidationService._is_valid_email("john@")


class DuplicateDetectionServiceTest(TestCase):
    """Test DuplicateDetectionService functionality."""

    def setUp(self):
        """Set up test data."""
        self.person1 = Person.objects.create(
            personal_name="John",
            family_name="Smith",
            date_of_birth="1990-01-01",
            personal_email="john@example.com",
        )

        self.person2 = Person.objects.create(
            personal_name="Jane",
            family_name="Doe",
            date_of_birth="1991-01-01",
            personal_email="jane@example.com",
        )

        # Create phone numbers
        PhoneNumber.objects.create(
            person=self.person1,
            number="+855123456789",
            is_preferred=True,
        )

        PhoneNumber.objects.create(
            person=self.person2,
            number="+855987654321",
            is_preferred=True,
        )

    def test_find_potential_duplicates_exact_name_match(self):
        """Test finding duplicates with exact name match."""
        person_data = {
            "family_name": "Smith",
            "personal_name": "John",
        }

        matches = DuplicateDetectionService.find_potential_duplicates(person_data)

        assert len(matches) == 1
        assert matches[0]["person"] == self.person1
        assert matches[0]["match_type"] == "exact_name"
        assert matches[0]["confidence"] == 0.95

    def test_find_potential_duplicates_phone_number_match(self):
        """Test finding duplicates with phone number match."""
        person_data = {
            "family_name": "Different",
            "personal_name": "Name",
            "phone_number": "+855123456789",
        }

        matches = DuplicateDetectionService.find_potential_duplicates(person_data)

        assert len(matches) == 1
        assert matches[0]["person"] == self.person1
        assert matches[0]["match_type"] == "phone_number"
        assert matches[0]["confidence"] == 0.80

    def test_find_potential_duplicates_email_match(self):
        """Test finding duplicates with email match."""
        person_data = {
            "family_name": "Different",
            "personal_name": "Name",
            "personal_email": "john@example.com",
        }

        matches = DuplicateDetectionService.find_potential_duplicates(person_data)

        assert len(matches) == 1
        assert matches[0]["person"] == self.person1
        assert matches[0]["match_type"] == "email"
        assert matches[0]["confidence"] == 0.90

    def test_find_potential_duplicates_date_of_birth_match(self):
        """Test finding duplicates with date of birth match."""
        person_data = {
            "family_name": "Different",
            "personal_name": "Name",
            "date_of_birth": self.person1.date_of_birth,
        }

        matches = DuplicateDetectionService.find_potential_duplicates(person_data)

        assert len(matches) == 1
        assert matches[0]["person"] == self.person1
        assert matches[0]["match_type"] == "date_of_birth"
        assert matches[0]["confidence"] == 0.60

    def test_find_potential_duplicates_multiple_matches_highest_confidence(self):
        """Test finding duplicates with multiple matches, returning highest confidence."""
        person_data = {
            "family_name": "Smith",
            "personal_name": "John",
            "personal_email": "john@example.com",
            "phone_number": "+855123456789",
        }

        matches = DuplicateDetectionService.find_potential_duplicates(person_data)

        # Should have one match with highest confidence (exact name = 0.95)
        assert len(matches) == 1
        assert matches[0]["person"] == self.person1
        assert matches[0]["confidence"] == 0.95

    def test_find_potential_duplicates_no_matches(self):
        """Test finding duplicates with no matches."""
        person_data = {
            "family_name": "Unique",
            "personal_name": "Person",
            "personal_email": "unique@example.com",
            "phone_number": "+855000000000",
            "date_of_birth": "2000-01-01",
        }

        matches = DuplicateDetectionService.find_potential_duplicates(person_data)

        assert len(matches) == 0


class PersonMergeServiceTest(TestCase):
    """Test PersonMergeService functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        self.primary_person = Person.objects.create(
            personal_name="John",
            family_name="Smith",
            date_of_birth="1990-01-01",
            personal_email="john@example.com",
        )

        self.duplicate_person = Person.objects.create(
            personal_name="John",
            family_name="Smith",
            date_of_birth="1990-01-01",
            personal_email="j.smith@example.com",
        )

        # Create related records for duplicate person
        PhoneNumber.objects.create(
            person=self.duplicate_person,
            number="+855123456789",
            is_preferred=True,
        )

        EmergencyContact.objects.create(
            person=self.duplicate_person,
            name="Jane Smith",
            relationship=EmergencyContact.Relationship.SPOUSE,
            primary_phone="+855987654321",
            is_primary=True,
        )

    def test_merge_person_records_success(self):
        """Test successful merging of person records."""
        duplicate_phone_count = PhoneNumber.objects.filter(person=self.duplicate_person).count()
        duplicate_contact_count = EmergencyContact.objects.filter(person=self.duplicate_person).count()

        merged_person = PersonMergeService.merge_person_records(
            primary_person=self.primary_person,
            duplicate_person=self.duplicate_person,
            merged_by=self.user,
        )

        assert merged_person == self.primary_person

        # Verify duplicate person was deleted
        assert not Person.objects.filter(id=self.duplicate_person.id).exists()

        # Verify related records were transferred
        primary_phones = PhoneNumber.objects.filter(person=self.primary_person)
        primary_contacts = EmergencyContact.objects.filter(person=self.primary_person)

        assert primary_phones.count() == duplicate_phone_count
        assert primary_contacts.count() == duplicate_contact_count

        # Verify audit log was created
        event_logs = PersonEventLog.objects.filter(person=self.primary_person)
        merge_log = event_logs.filter(action=PersonEventLog.ActionType.OTHER).first()
        assert merge_log is not None
        assert "person_merge" in merge_log.details["action"]

    def test_merge_person_records_same_person_error(self):
        """Test merging person with themselves raises error."""
        with pytest.raises(ValidationError) as exc_info:
            PersonMergeService.merge_person_records(
                primary_person=self.primary_person,
                duplicate_person=self.primary_person,
                merged_by=self.user,
            )

        assert "Cannot merge person with themselves" in str(exc_info.value)

    def test_merge_phone_numbers_no_duplicates(self):
        """Test merging phone numbers with no duplicates."""
        initial_count = PhoneNumber.objects.filter(person=self.primary_person).count()

        PersonMergeService._merge_phone_numbers(self.primary_person, self.duplicate_person)

        final_count = PhoneNumber.objects.filter(person=self.primary_person).count()
        assert final_count == initial_count + 1

        # Verify phone was transferred and marked as non-preferred
        transferred_phone = PhoneNumber.objects.filter(
            person=self.primary_person,
            number="+855123456789",
        ).first()
        assert transferred_phone is not None
        assert not transferred_phone.is_preferred

    def test_merge_phone_numbers_with_duplicates(self):
        """Test merging phone numbers with duplicate numbers."""
        # Create same phone number for primary person
        PhoneNumber.objects.create(
            person=self.primary_person,
            number="+855123456789",
            is_preferred=False,
        )

        initial_count = PhoneNumber.objects.filter(person=self.primary_person).count()

        PersonMergeService._merge_phone_numbers(self.primary_person, self.duplicate_person)

        final_count = PhoneNumber.objects.filter(person=self.primary_person).count()
        # Should not increase because duplicate was deleted
        assert final_count == initial_count

    def test_merge_emergency_contacts(self):
        """Test merging emergency contacts."""
        initial_count = EmergencyContact.objects.filter(person=self.primary_person).count()

        PersonMergeService._merge_emergency_contacts(self.primary_person, self.duplicate_person)

        final_count = EmergencyContact.objects.filter(person=self.primary_person).count()
        assert final_count == initial_count + 1

        # Verify contact was transferred and marked as non-primary
        transferred_contact = EmergencyContact.objects.filter(
            person=self.primary_person,
            name="Jane Smith",
        ).first()
        assert transferred_contact is not None
        assert not transferred_contact.is_primary

    def test_merge_student_profiles_only_duplicate_has_profile(self):
        """Test merging when only duplicate person has student profile."""
        duplicate_student = StudentProfile.objects.create(
            person=self.duplicate_person,
            student_id=100001,
        )

        PersonMergeService._merge_student_profiles(self.primary_person, self.duplicate_person, self.user)

        # Verify student profile was transferred
        duplicate_student.refresh_from_db()
        assert duplicate_student.person == self.primary_person

    def test_merge_student_profiles_both_have_profiles(self):
        """Test merging when both persons have student profiles."""
        StudentProfile.objects.create(
            person=self.primary_person,
            student_id=100001,
        )

        StudentProfile.objects.create(
            person=self.duplicate_person,
            student_id=100002,
        )

        PersonMergeService._merge_student_profiles(self.primary_person, self.duplicate_person, self.user)

        # Verify manual review log was created
        event_logs = PersonEventLog.objects.filter(person=self.primary_person)
        review_log = event_logs.filter(
            action=PersonEventLog.ActionType.OTHER,
            details__action="manual_review_required",
        ).first()
        assert review_log is not None
        assert "both_persons_have_student_profiles" in review_log.details["reason"]
