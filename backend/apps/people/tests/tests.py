"""Comprehensive tests for the people app models.

This test module validates all functionality of the ported models from version 0
while ensuring they maintain clean architecture principles and avoid circular
dependencies.

Test coverage includes:
- Model creation and validation
- Custom methods and properties
- Business logic constraints
- Audit logging functionality
- Edge cases and error conditions
"""

from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from apps.common.constants import (
    CambodianProvinces,
    get_province_display_name,
    is_cambodian_province,
)
from apps.common.utils import get_current_date
from apps.people.constants import (
    EMAIL_MATCH_CONFIDENCE,
    EMAIL_MATCH_WEIGHT,
    EXACT_NAME_MATCH_CONFIDENCE,
    FUZZY_MATCH_CONFIDENCE,
    MAX_AGE_APPLY,
    MAX_LEVEL_SKIP,
    MAX_PHONE_DIGITS,
    MIN_AGE_APPLY,
    MIN_PHONE_DIGITS,
    NAME_SIMILARITY_WEIGHT,
    NAME_VALIDATION_REGEX,
    PHONE_MATCH_CONFIDENCE,
    PHONE_MATCH_WEIGHT,
    SIMILAR_NAME_THRESHOLD,
    STUDENT_ID_START,
    TEST_STUDENT_ID,
)
from apps.people.models import (
    EmergencyContact,
    Gender,
    Person,
    PersonEventLog,
    PhoneNumber,
    StaffProfile,
    StudentAuditLog,
    StudentProfile,
    TeacherLeaveRequest,
    TeacherProfile,
)

User = get_user_model()


class ConstantsTest(TestCase):
    """Test constants and utility functions."""

    def test_province_constants(self):
        """Test that province constants are properly defined."""
        # Test that main provinces exist
        assert CambodianProvinces.PHNOM_PENH == "PHNOM_PENH"
        assert CambodianProvinces.SIEM_REAP == "SIEM_REAP"
        assert CambodianProvinces.INTERNATIONAL == "INTERNATIONAL"

    def test_get_province_display_name(self):
        """Test getting display names for provinces."""
        assert get_province_display_name(CambodianProvinces.PHNOM_PENH) == "Phnom Penh"
        assert get_province_display_name(CambodianProvinces.INTERNATIONAL) == "International/Other"

    def test_is_cambodian_province(self):
        """Test identifying Cambodian vs international provinces."""
        assert is_cambodian_province(CambodianProvinces.PHNOM_PENH)
        assert is_cambodian_province(CambodianProvinces.SIEM_REAP)
        assert not is_cambodian_province(CambodianProvinces.INTERNATIONAL)


class PeopleConstantsTest(TestCase):
    """Test people app constants and configuration values."""

    def test_age_validation_constants(self):
        """Test age validation constants are reasonable."""
        assert MIN_AGE_APPLY == 12
        assert MAX_AGE_APPLY == 65
        assert MIN_AGE_APPLY < MAX_AGE_APPLY
        assert MIN_AGE_APPLY > 0
        assert MAX_AGE_APPLY < 120

    def test_phone_validation_constants(self):
        """Test phone number validation constants."""
        assert MIN_PHONE_DIGITS == 8
        assert MAX_PHONE_DIGITS == 15
        assert MIN_PHONE_DIGITS < MAX_PHONE_DIGITS
        assert MIN_PHONE_DIGITS > 0
        assert MAX_PHONE_DIGITS <= 20  # Reasonable upper bound

    def test_duplicate_detection_confidence_thresholds(self):
        """Test duplicate detection confidence thresholds are valid."""
        # All confidence values should be between 0 and 1
        assert 0 < EXACT_NAME_MATCH_CONFIDENCE <= 1
        assert 0 < PHONE_MATCH_CONFIDENCE <= 1
        assert 0 < EMAIL_MATCH_CONFIDENCE <= 1
        assert 0 < SIMILAR_NAME_THRESHOLD <= 1
        assert 0 < FUZZY_MATCH_CONFIDENCE <= 1

        # Exact match should have highest confidence
        assert EXACT_NAME_MATCH_CONFIDENCE > FUZZY_MATCH_CONFIDENCE
        assert EMAIL_MATCH_CONFIDENCE > FUZZY_MATCH_CONFIDENCE

    def test_similarity_weights_sum_to_one(self):
        """Test that similarity weights approximately sum to 1.0."""
        total_weight = NAME_SIMILARITY_WEIGHT + PHONE_MATCH_WEIGHT + EMAIL_MATCH_WEIGHT
        assert abs(total_weight - 1.0) < 0.01  # Allow small floating point errors

    def test_similarity_weights_are_positive(self):
        """Test that all similarity weights are positive."""
        assert NAME_SIMILARITY_WEIGHT > 0
        assert PHONE_MATCH_WEIGHT > 0
        assert EMAIL_MATCH_WEIGHT > 0

    def test_student_id_start_is_reasonable(self):
        """Test that student ID start value is reasonable."""
        assert STUDENT_ID_START == 100001
        assert STUDENT_ID_START > 0
        assert len(str(STUDENT_ID_START)) >= 5  # At least 5 digits

    def test_max_level_skip_is_reasonable(self):
        """Test that maximum level skip is reasonable."""
        assert MAX_LEVEL_SKIP == 3
        assert MAX_LEVEL_SKIP > 0
        assert MAX_LEVEL_SKIP < 10  # Reasonable upper bound

    def test_name_validation_regex_is_valid(self):
        """Test that name validation regex is valid and reasonable."""
        import re

        # Should be a valid regex
        regex = re.compile(NAME_VALIDATION_REGEX)

        # Test valid names
        valid_names = ["John", "Mary-Jane", "O'Connor", "Jean Paul"]
        for name in valid_names:
            assert regex.match(name), f"'{name}' should be valid"

        # Test invalid names (with numbers or special characters)
        invalid_names = ["John123", "Mary@Jane", "Test.Name", "Name_With_Underscore"]
        for name in invalid_names:
            assert not regex.match(name), f"'{name}' should be invalid"

    def test_constants_types_are_correct(self):
        """Test that constants have correct types."""
        # Integer constants
        assert isinstance(MIN_AGE_APPLY, int)
        assert isinstance(MAX_AGE_APPLY, int)
        assert isinstance(MIN_PHONE_DIGITS, int)
        assert isinstance(MAX_PHONE_DIGITS, int)
        assert isinstance(STUDENT_ID_START, int)
        assert isinstance(MAX_LEVEL_SKIP, int)

        # Float constants
        assert isinstance(EXACT_NAME_MATCH_CONFIDENCE, int | float)
        assert isinstance(PHONE_MATCH_CONFIDENCE, int | float)
        assert isinstance(EMAIL_MATCH_CONFIDENCE, int | float)
        assert isinstance(SIMILAR_NAME_THRESHOLD, int | float)
        assert isinstance(FUZZY_MATCH_CONFIDENCE, int | float)
        assert isinstance(NAME_SIMILARITY_WEIGHT, int | float)
        assert isinstance(PHONE_MATCH_WEIGHT, int | float)
        assert isinstance(EMAIL_MATCH_WEIGHT, int | float)

        # String constants
        assert isinstance(NAME_VALIDATION_REGEX, str)


class PersonModelTest(TestCase):
    """Test Person model functionality."""

    def setUp(self):
        """Set up test data."""
        self.person_data = {
            "family_name": "Smith",
            "personal_name": "John",
            "khmer_name": "ស្មីត ចន",
            "preferred_gender": Gender.MALE,
            "date_of_birth": date(1990, 1, 1),
            "birth_province": CambodianProvinces.PHNOM_PENH,
            "citizenship": "KH",
        }

    def test_person_creation(self):
        """Test basic person creation."""
        person = Person.objects.create(**self.person_data)
        assert person.family_name == "SMITH"  # Should be uppercase
        assert person.personal_name == "JOHN"  # Should be uppercase
        assert person.full_name == "SMITH JOHN"  # Auto-generated
        assert person.unique_id is not None

    def test_name_processing(self):
        """Test automatic name processing and full_name generation."""
        person = Person.objects.create(**self.person_data)
        assert person.family_name == "SMITH"
        assert person.personal_name == "JOHN"
        assert person.full_name == "SMITH JOHN"

        # Test name updates
        person.family_name = "jones"
        person.personal_name = "mary"
        person.save()
        assert person.family_name == "JONES"
        assert person.personal_name == "MARY"
        assert person.full_name == "JONES MARY"

    def test_name_change_tracking_without_database_query(self):
        """Test that name changes are detected without database queries."""
        person = Person.objects.create(**self.person_data)

        # Verify initial tracking state
        assert person._original_family_name == "SMITH"
        assert person._original_personal_name == "JOHN"

        # Change only family name
        person.family_name = "BROWN"
        person.save()

        # Should detect change and update full_name
        assert person.full_name == "BROWN JOHN"
        assert person._original_family_name == "BROWN"

        # Change only personal name
        person.personal_name = "JANE"
        person.save()

        # Should detect change and update full_name
        assert person.full_name == "BROWN JANE"
        assert person._original_personal_name == "JANE"

        # No changes should not update full_name unnecessarily
        old_full_name = person.full_name
        person.save()  # No changes
        assert person.full_name == old_full_name

    def test_field_tracking_on_refresh_from_db(self):
        """Test that field tracking updates when refreshing from database."""
        person = Person.objects.create(**self.person_data)

        # Modify in another instance
        Person.objects.filter(pk=person.pk).update(family_name="UPDATED", personal_name="PERSON")

        # Refresh should update tracking
        person.refresh_from_db()
        assert person._original_family_name == "UPDATED"
        assert person._original_personal_name == "PERSON"

    def test_age_calculation(self):
        """Test age property calculation."""
        person = Person.objects.create(**self.person_data)
        expected_age = timezone.now().date().year - 1990
        # Account for birthday not having passed this year
        if timezone.now().date() < date(timezone.now().date().year, 1, 1):
            expected_age -= 1
        assert person.age == expected_age

        # Test with no birth date
        person.date_of_birth = None
        assert person.age is None

    def test_display_name_property(self):
        """Test display name logic for preferred vs legal names."""
        person = Person.objects.create(**self.person_data)

        # Default: use preferred name
        assert person.display_name == "SMITH JOHN"

        # Set legal name but don't use it
        person.alternate_family_name = "Legal Family"
        person.alternate_personal_name = "Legal Personal"
        person.save()
        assert person.display_name == "SMITH JOHN"

        # Use legal name for documents
        person.use_legal_name_for_documents = True
        person.save()
        assert person.display_name == "Legal Family Legal Personal"

    def test_legal_name_validation(self):
        """Test validation when legal names are required."""
        person_data = self.person_data.copy()
        person_data["use_legal_name_for_documents"] = True

        # Should raise validation error without alternate names
        with pytest.raises(ValidationError):
            Person(**person_data).full_clean()

        # Should work with alternate names
        person_data["alternate_family_name"] = "Legal Family"
        person_data["alternate_personal_name"] = "Legal Personal"
        person = Person(**person_data)
        person.full_clean()  # Should not raise

    def test_birth_province_validation(self):
        """Test validation of birth province for non-Cambodian citizens."""
        person_data = self.person_data.copy()
        person_data["citizenship"] = "US"

        # Should raise validation error with Cambodian province for non-KH citizen
        with pytest.raises(ValidationError):
            Person(**person_data).full_clean()

        # Should work with International for non-KH citizen
        person_data["birth_province"] = CambodianProvinces.INTERNATIONAL
        person = Person(**person_data)
        person.full_clean()  # Should not raise

        # Should work without birth province
        person_data["birth_province"] = ""
        person = Person(**person_data)
        person.full_clean()  # Should not raise

    def test_role_properties(self):
        """Test role checking properties."""
        person = Person.objects.create(**self.person_data)

        # Initially no roles
        assert not person.has_student_role
        assert not person.has_teacher_role
        assert not person.has_staff_role

        # Create student profile
        StudentProfile.objects.create(person=person, student_id=TEST_STUDENT_ID)
        assert person.has_student_role
        assert not person.has_teacher_role
        assert not person.has_staff_role

    def test_unique_email_constraint(self):
        """Test that school emails must be unique."""
        Person.objects.create(**self.person_data, school_email="test@school.edu")

        person_data2 = self.person_data.copy()
        person_data2["family_name"] = "Different"

        with pytest.raises(IntegrityError):
            Person.objects.create(**person_data2, school_email="test@school.edu")


class StudentProfileModelTest(TestCase):
    """Test StudentProfile model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="password",
        )
        self.person = Person.objects.create(
            family_name="Student",
            personal_name="Test",
            preferred_gender=Gender.MALE,
        )

    def test_student_profile_creation(self):
        """Test basic student profile creation."""
        student = StudentProfile.objects.create(
            person=self.person,
            student_id=TEST_STUDENT_ID,
            is_monk=True,
            current_status=StudentProfile.Status.ACTIVE,
        )
        assert student.student_id == TEST_STUDENT_ID
        assert student.is_monk
        assert student.current_status == StudentProfile.Status.ACTIVE

    def test_formatted_student_id(self):
        """Test formatted student ID property."""
        student = StudentProfile.objects.create(person=self.person, student_id=123)
        assert student.formatted_student_id == "00123"

    def test_status_change_with_logging(self):
        """Test status change method with audit logging."""
        student = StudentProfile.objects.create(person=self.person, student_id=TEST_STUDENT_ID)

        initial_count = StudentAuditLog.objects.count()
        student.change_status(
            StudentProfile.Status.ACTIVE,
            self.user,
            "Test status change",
        )

        assert student.current_status == StudentProfile.Status.ACTIVE
        assert StudentAuditLog.objects.count() == initial_count + 1

        log_entry = StudentAuditLog.objects.latest("timestamp")
        assert log_entry.action == StudentAuditLog.ActionType.STATUS
        assert log_entry.student == student
        assert log_entry.changed_by == self.user

    def test_invalid_status_change(self):
        """Test that invalid status values raise ValueError."""
        student = StudentProfile.objects.create(person=self.person, student_id=TEST_STUDENT_ID)

        with pytest.raises(ValueError, match="Invalid status"):
            student.change_status("INVALID_STATUS", self.user)

    def test_left_monkhood_method(self):
        """Test left_the_monkhood method."""
        student = StudentProfile.objects.create(
            person=self.person,
            student_id=TEST_STUDENT_ID,
            is_monk=True,
        )

        student.left_the_monkhood()
        assert not student.is_monk

        # Should be idempotent
        student.left_the_monkhood()
        assert not student.is_monk

    def test_unique_student_id(self):
        """Test that student IDs must be unique."""
        StudentProfile.objects.create(person=self.person, student_id=TEST_STUDENT_ID)

        person2 = Person.objects.create(family_name="Another", personal_name="Student")

        with pytest.raises(IntegrityError):
            StudentProfile.objects.create(person=person2, student_id=TEST_STUDENT_ID)


class TeacherProfileModelTest(TestCase):
    """Test TeacherProfile model functionality."""

    def setUp(self):
        """Set up test data."""
        self.person = Person.objects.create(
            family_name="Teacher",
            personal_name="Test",
            preferred_gender=Gender.FEMALE,
        )

    def test_teacher_profile_creation(self):
        """Test basic teacher profile creation."""
        teacher = TeacherProfile.objects.create(
            person=self.person,
            terminal_degree=TeacherProfile.Qualification.MASTER,
            status=TeacherProfile.Status.ACTIVE,
        )
        assert teacher.terminal_degree == TeacherProfile.Qualification.MASTER
        assert teacher.status == TeacherProfile.Status.ACTIVE
        assert teacher.start_date == get_current_date()

    def test_teacher_active_status(self):
        """Test is_teacher_active property."""
        # Active teacher
        teacher = TeacherProfile.objects.create(
            person=self.person,
            status=TeacherProfile.Status.ACTIVE,
            start_date=get_current_date(),
        )
        assert teacher.is_teacher_active

        # Inactive status
        teacher.status = TeacherProfile.Status.INACTIVE
        assert not teacher.is_teacher_active

        # Future start date
        teacher.status = TeacherProfile.Status.ACTIVE
        teacher.start_date = date(2030, 1, 1)
        assert not teacher.is_teacher_active

        teacher.start_date = get_current_date()
        teacher.end_date = date(2020, 1, 1)
        assert not teacher.is_teacher_active


class StaffProfileModelTest(TestCase):
    """Test StaffProfile model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="password",
        )
        self.person = Person.objects.create(
            family_name="Staff",
            personal_name="Test",
            preferred_gender=Gender.MALE,
        )

    def test_staff_profile_creation(self):
        """Test basic staff profile creation."""
        staff = StaffProfile.objects.create(
            person=self.person,
            position="Administrator",
            status=StaffProfile.Status.ACTIVE,
        )
        assert staff.position == "Administrator"
        assert staff.status == StaffProfile.Status.ACTIVE

    def test_staff_active_status(self):
        """Test is_staff_active property."""
        staff = StaffProfile.objects.create(
            person=self.person,
            status=StaffProfile.Status.ACTIVE,
            start_date=get_current_date(),
        )
        assert staff.is_staff_active

        # Test inactive status
        staff.status = StaffProfile.Status.INACTIVE
        assert not staff.is_staff_active

    def test_take_leave_method(self):
        """Test take_leave method and logging."""
        staff = StaffProfile.objects.create(
            person=self.person,
            status=StaffProfile.Status.ACTIVE,
        )

        initial_count = PersonEventLog.objects.count()
        staff.take_leave(user=self.user, notes="Medical leave")

        assert staff.status == StaffProfile.Status.ON_LEAVE
        assert PersonEventLog.objects.count() == initial_count + 1

        log_entry = PersonEventLog.objects.latest("timestamp")
        assert log_entry.action == PersonEventLog.ActionType.LEAVE
        assert log_entry.person == self.person

    def test_return_from_leave_method(self):
        """Test return_from_leave method and logging."""
        staff = StaffProfile.objects.create(
            person=self.person,
            status=StaffProfile.Status.ON_LEAVE,
        )

        initial_count = PersonEventLog.objects.count()
        staff.return_from_leave(user=self.user, notes="Returned from leave")

        assert staff.status == StaffProfile.Status.ACTIVE
        assert PersonEventLog.objects.count() == initial_count + 1


class PersonEventLogModelTest(TestCase):
    """Test PersonEventLog model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="password",
        )
        self.person = Person.objects.create(family_name="Test", personal_name="Person")

    def test_log_role_change(self):
        """Test role change logging."""
        PersonEventLog.log_role_change(
            person=self.person,
            role="STUDENT",
            old_status="INACTIVE",
            new_status="ACTIVE",
            user=self.user,
            notes="Activated student role",
        )

        log_entry = PersonEventLog.objects.latest("timestamp")
        assert log_entry.action == PersonEventLog.ActionType.ROLE_CHANGE
        assert log_entry.person == self.person
        assert log_entry.changed_by == self.user
        assert log_entry.details["role"] == "STUDENT"

    def test_log_leave(self):
        """Test leave logging."""
        start_date = get_current_date()
        PersonEventLog.log_leave(
            person=self.person,
            start_date=start_date,
            user=self.user,
            notes="Started leave",
        )

        log_entry = PersonEventLog.objects.latest("timestamp")
        assert log_entry.action == PersonEventLog.ActionType.LEAVE
        assert log_entry.person == self.person


class PhoneNumberModelTest(TestCase):
    """Test PhoneNumber model functionality."""

    def setUp(self):
        """Set up test data."""
        self.person = Person.objects.create(family_name="Test", personal_name="Person")

    def test_phone_number_creation(self):
        """Test basic phone number creation."""
        phone = PhoneNumber.objects.create(
            person=self.person,
            number="+855123456789",
            comment="Primary phone",
            is_preferred=True,
            is_telegram=True,
        )
        assert phone.number == "+855123456789"
        assert phone.is_preferred
        assert phone.is_telegram

    def test_phone_number_validation_international_format(self):
        """Test phone number validation for international format."""
        valid_numbers = [
            "+855123456789",  # Cambodia
            "+1234567890",  # USA (short)
            "+441234567890",  # UK
            "+8612345678901",  # China (long)
            "85512345678",  # Local format without +
        ]

        for number in valid_numbers:
            phone = PhoneNumber(
                person=self.person,
                number=number,
            )
            phone.full_clean()  # Should not raise ValidationError

    def test_phone_number_validation_invalid_format(self):
        """Test phone number validation rejects invalid formats."""
        invalid_numbers = [
            "0123456789",  # Starting with 0
            "+0123456789",  # Starting with +0
            "12",  # Too short
            "+123456789012345678",  # Too long
            "abc123",  # Contains letters
            "++855123456789",  # Double plus
        ]

        for number in invalid_numbers:
            phone = PhoneNumber(
                person=self.person,
                number=number,
            )
            try:
                phone.full_clean()
                pytest.fail(f"Expected ValidationError for number '{number}' but none was raised")
            except ValidationError:
                pass  # Expected behavior

    def test_phone_number_validation_empty_allowed(self):
        """Test that empty phone numbers are allowed due to blank=True."""
        phone = PhoneNumber(
            person=self.person,
            number="",  # Empty should be allowed
        )
        phone.full_clean()  # Should not raise

    def test_phone_number_validation_edge_cases(self):
        """Test phone number validation edge cases."""
        # Test minimum valid length
        phone = PhoneNumber(
            person=self.person,
            number="12345678",  # 8 digits, minimum
        )
        phone.full_clean()  # Should not raise

        # Test maximum valid length
        phone = PhoneNumber(
            person=self.person,
            number="+123456789012345",  # 15 digits total
        )
        phone.full_clean()  # Should not raise

    def test_unique_preferred_constraint(self):
        """Test that only one preferred number is allowed per person."""
        PhoneNumber.objects.create(person=self.person, number="123", is_preferred=True)

        with pytest.raises(IntegrityError):
            PhoneNumber.objects.create(
                person=self.person,
                number="456",
                is_preferred=True,
            )


class EmergencyContactModelTest(TestCase):
    """Test EmergencyContact model functionality."""

    def setUp(self):
        """Set up test data."""
        self.person = Person.objects.create(family_name="Test", personal_name="Person")

    def test_emergency_contact_creation(self):
        """Test basic emergency contact creation."""
        contact = EmergencyContact.objects.create(
            person=self.person,
            name="John Doe",
            relationship=EmergencyContact.Relationship.FATHER,
            primary_phone="123456789",
            email="john@example.com",
            is_primary=True,
        )
        assert contact.name == "John Doe"
        assert contact.relationship == EmergencyContact.Relationship.FATHER
        assert contact.is_primary

    def test_unique_primary_constraint(self):
        """Test that only one primary contact is allowed per person."""
        EmergencyContact.objects.create(
            person=self.person,
            name="Contact 1",
            is_primary=True,
        )

        # Database constraint should prevent duplicate primary contacts
        with pytest.raises(IntegrityError):
            EmergencyContact.objects.create(
                person=self.person,
                name="Contact 2",
                is_primary=True,
            )

    def test_phone_number_validation(self):
        """Test validation of phone numbers."""
        contact = EmergencyContact(
            person=self.person,
            name="Test Contact",
            primary_phone="123456789",
            secondary_phone="123456789",  # Same as primary
        )

        with pytest.raises(ValidationError):
            contact.full_clean()

    def test_primary_contact_database_constraint(self):
        """Test that database constraint enforces unique primary contact."""
        EmergencyContact.objects.create(
            person=self.person,
            name="Contact 1",
            is_primary=True,
        )

        # Multiple non-primary contacts should work fine
        EmergencyContact.objects.create(
            person=self.person,
            name="Contact 2",
            is_primary=False,
        )

        EmergencyContact.objects.create(
            person=self.person,
            name="Contact 3",
            is_primary=False,
        )

        # But trying to create another primary should fail
        with pytest.raises(IntegrityError):
            EmergencyContact.objects.create(
                person=self.person,
                name="Contact 4",
                is_primary=True,
            )


class StudentAuditLogModelTest(TestCase):
    """Test StudentAuditLog model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="password",
        )
        self.person = Person.objects.create(family_name="Student", personal_name="Test")
        self.student = StudentProfile.objects.create(
            person=self.person,
            student_id=TEST_STUDENT_ID,
        )

    def test_status_change_logging(self):
        """Test status change logging."""
        StudentAuditLog.log_status_change(
            student=self.student,
            old_status=StudentProfile.Status.UNKNOWN,
            new_status=StudentProfile.Status.ACTIVE,
            user=self.user,
            notes="Activated student",
        )

        log_entry = StudentAuditLog.objects.latest("timestamp")
        assert log_entry.action == StudentAuditLog.ActionType.STATUS
        assert log_entry.student == self.student
        assert log_entry.changed_by == self.user
        assert log_entry.changes["old_value"] == StudentProfile.Status.UNKNOWN
        assert log_entry.changes["new_value"] == StudentProfile.Status.ACTIVE

    def test_log_str_representation(self):
        """Test string representation of log entries."""
        log = StudentAuditLog.log_status_change(
            student=self.student,
            old_status=StudentProfile.Status.UNKNOWN,
            new_status=StudentProfile.Status.ACTIVE,
            user=self.user,
        )

        str_repr = str(log)
        assert "12345: STUDENT TEST" in str_repr
        assert "Status Change" in str_repr
        assert "test@example.com" in str_repr


class TeacherLeaveRequestModelTest(TestCase):
    """Test TeacherLeaveRequest model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="admin@test.com",
            password="testpass",
        )

        # Create teacher
        teacher_person = Person.objects.create(
            family_name="Teacher",
            personal_name="Leave",
            date_of_birth=date(1980, 1, 1),
        )
        self.teacher = TeacherProfile.objects.create(
            person=teacher_person,
            status=TeacherProfile.Status.ACTIVE,
        )

        # Create substitute teacher
        substitute_person = Person.objects.create(
            family_name="Substitute",
            personal_name="Teacher",
            date_of_birth=date(1975, 1, 1),
        )
        self.substitute_teacher = TeacherProfile.objects.create(
            person=substitute_person,
            status=TeacherProfile.Status.ACTIVE,
        )

    def test_teacher_leave_request_creation(self):
        """Test basic leave request creation."""
        leave_request = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=get_current_date() + timezone.timedelta(days=1),
            leave_type=TeacherLeaveRequest.LeaveType.SICK,
            reason="Flu symptoms, need to rest and recover",
            is_emergency=False,
            approval_status=TeacherLeaveRequest.ApprovalStatus.PENDING,
        )

        assert leave_request.teacher == self.teacher
        assert leave_request.leave_date == get_current_date() + timezone.timedelta(days=1)
        assert leave_request.leave_type == TeacherLeaveRequest.LeaveType.SICK
        assert leave_request.reason == "Flu symptoms, need to rest and recover"
        assert not leave_request.is_emergency
        assert leave_request.approval_status == TeacherLeaveRequest.ApprovalStatus.PENDING

    def test_leave_type_choices(self):
        """Test all leave type options."""
        leave_types = [
            TeacherLeaveRequest.LeaveType.SICK,
            TeacherLeaveRequest.LeaveType.PERSONAL,
            TeacherLeaveRequest.LeaveType.EMERGENCY,
            TeacherLeaveRequest.LeaveType.PROFESSIONAL,
            TeacherLeaveRequest.LeaveType.FAMILY,
            TeacherLeaveRequest.LeaveType.MEDICAL,
            TeacherLeaveRequest.LeaveType.OTHER,
        ]

        for leave_type in leave_types:
            request = TeacherLeaveRequest(
                teacher=self.teacher,
                leave_date=get_current_date() + timezone.timedelta(days=1),
                reason="Test reason",
                leave_type=leave_type,
            )
            assert request.leave_type == leave_type

    def test_approval_status_choices(self):
        """Test all approval status options."""
        approval_statuses = [
            TeacherLeaveRequest.ApprovalStatus.PENDING,
            TeacherLeaveRequest.ApprovalStatus.APPROVED,
            TeacherLeaveRequest.ApprovalStatus.DENIED,
            TeacherLeaveRequest.ApprovalStatus.CANCELLED,
        ]

        for status in approval_statuses:
            request = TeacherLeaveRequest(
                teacher=self.teacher,
                leave_date=get_current_date() + timezone.timedelta(days=1),
                reason="Test reason",
                approval_status=status,
            )
            assert request.approval_status == status

    def test_approve_method(self):
        """Test approval workflow method."""
        leave_request = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=get_current_date() + timezone.timedelta(days=2),
            leave_type=TeacherLeaveRequest.LeaveType.PERSONAL,
            reason="Personal appointment",
            approval_status=TeacherLeaveRequest.ApprovalStatus.PENDING,
        )

        # Initially pending
        assert leave_request.approval_status == TeacherLeaveRequest.ApprovalStatus.PENDING
        assert leave_request.approved_by is None
        assert leave_request.approved_at is None

        # Approve the request
        leave_request.approve(user=self.user, notes="Approved with documentation")

        leave_request.refresh_from_db()
        assert leave_request.approval_status == TeacherLeaveRequest.ApprovalStatus.APPROVED
        assert leave_request.approved_by == self.user
        assert leave_request.approved_at is not None
        assert "Approved with documentation" in leave_request.notes

    def test_deny_method(self):
        """Test denial workflow method."""
        leave_request = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=get_current_date() + timezone.timedelta(days=2),
            leave_type=TeacherLeaveRequest.LeaveType.PERSONAL,
            reason="Personal appointment",
            approval_status=TeacherLeaveRequest.ApprovalStatus.PENDING,
        )

        # Deny the request
        leave_request.deny(user=self.user, reason="Insufficient notice provided")

        leave_request.refresh_from_db()
        assert leave_request.approval_status == TeacherLeaveRequest.ApprovalStatus.DENIED
        assert leave_request.approved_by == self.user
        assert leave_request.approved_at is not None
        assert leave_request.denial_reason == "Insufficient notice provided"

    def test_assign_substitute_method(self):
        """Test substitute assignment method."""
        leave_request = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=get_current_date() + timezone.timedelta(days=2),
            leave_type=TeacherLeaveRequest.LeaveType.SICK,
            reason="Sick leave",
            approval_status=TeacherLeaveRequest.ApprovalStatus.APPROVED,
        )

        # Initially no substitute
        assert leave_request.substitute_teacher is None
        assert not leave_request.substitute_found

        # Assign substitute
        leave_request.assign_substitute(
            substitute=self.substitute_teacher,
            assigned_by=self.user,
        )

        leave_request.refresh_from_db()
        assert leave_request.substitute_teacher == self.substitute_teacher
        assert leave_request.substitute_assigned_by == self.user
        assert leave_request.substitute_assigned_at is not None
        assert leave_request.substitute_found

    def test_is_approved_property(self):
        """Test is_approved property."""
        # Create pending request
        pending_request = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=get_current_date() + timezone.timedelta(days=1),
            reason="Test reason",
            approval_status=TeacherLeaveRequest.ApprovalStatus.PENDING,
        )
        assert not pending_request.is_approved

        # Create approved request
        approved_request = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=get_current_date() + timezone.timedelta(days=2),
            reason="Test reason",
            approval_status=TeacherLeaveRequest.ApprovalStatus.APPROVED,
        )
        assert approved_request.is_approved

        # Create denied request
        denied_request = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=get_current_date() + timezone.timedelta(days=3),
            reason="Test reason",
            approval_status=TeacherLeaveRequest.ApprovalStatus.DENIED,
        )
        assert not denied_request.is_approved

    def test_needs_substitute_property(self):
        """Test needs_substitute property logic."""
        # Create mock class part for M2M field
        from unittest.mock import Mock

        mock_class_part = Mock()
        mock_class_part.id = 1

        # Create approved request without class parts
        request_no_classes = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=get_current_date() + timezone.timedelta(days=1),
            reason="Test reason",
            approval_status=TeacherLeaveRequest.ApprovalStatus.APPROVED,
        )
        assert not request_no_classes.needs_substitute  # No classes affected

        # Create approved request with substitute found
        request_with_substitute = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=get_current_date() + timezone.timedelta(days=2),
            reason="Test reason",
            approval_status=TeacherLeaveRequest.ApprovalStatus.APPROVED,
            substitute_found=True,
        )
        assert not request_with_substitute.needs_substitute  # Substitute already found

        # Create pending request (not approved)
        pending_request = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=get_current_date() + timezone.timedelta(days=3),
            reason="Test reason",
            approval_status=TeacherLeaveRequest.ApprovalStatus.PENDING,
        )
        assert not pending_request.needs_substitute  # Not approved yet

    def test_emergency_request_handling(self):
        """Test emergency request special handling."""
        # Test emergency request for past date (should be allowed)
        emergency_request = TeacherLeaveRequest(
            teacher=self.teacher,
            leave_date=get_current_date() - timezone.timedelta(days=1),  # Past date
            reason="Emergency family situation",
            is_emergency=True,
        )

        # Should not raise validation error for past date when emergency
        emergency_request.clean()

        # Save and verify
        emergency_request.save()
        assert emergency_request.is_emergency
        assert emergency_request.leave_date < get_current_date()

    def test_past_date_validation(self):
        """Test validation against requesting leave for past dates."""
        non_emergency_request = TeacherLeaveRequest(
            teacher=self.teacher,
            leave_date=get_current_date() - timezone.timedelta(days=1),  # Past date
            reason="Regular request",
            is_emergency=False,
        )

        with pytest.raises(ValidationError) as exc_info:
            non_emergency_request.clean()

        assert "Cannot request leave for past dates unless it's an emergency" in str(
            exc_info.value,
        )

    def test_denial_reason_validation(self):
        """Test validation for denial reason."""
        denied_request = TeacherLeaveRequest(
            teacher=self.teacher,
            leave_date=get_current_date() + timezone.timedelta(days=1),
            reason="Test reason",
            approval_status=TeacherLeaveRequest.ApprovalStatus.DENIED,
            # Missing denial_reason
        )

        with pytest.raises(ValidationError) as exc_info:
            denied_request.clean()

        assert "Denial reason is required for denied requests" in str(exc_info.value)

    def test_auto_substitute_found_flag(self):
        """Test automatic setting of substitute_found flag."""
        leave_request = TeacherLeaveRequest(
            teacher=self.teacher,
            leave_date=get_current_date() + timezone.timedelta(days=1),
            reason="Test reason",
            substitute_teacher=self.substitute_teacher,
            substitute_found=False,  # Set to False initially
        )

        # Should auto-set to True when substitute_teacher is assigned
        leave_request.clean()
        assert leave_request.substitute_found

    def test_string_representation(self):
        """Test string representation."""
        leave_request = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=date(2024, 3, 15),
            leave_type=TeacherLeaveRequest.LeaveType.PERSONAL,
            reason="Personal appointment",
        )

        expected = f"{self.teacher.person.full_name} - 2024-03-15 (Personal Leave)"
        assert str(leave_request) == expected

    def test_multiple_class_parts_assignment(self):
        """Test that multiple class parts can be assigned to a leave request."""
        # Note: This would require actual ClassPart objects in a real test
        # For now, we test the model structure
        leave_request = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=get_current_date() + timezone.timedelta(days=1),
            reason="Multiple classes affected",
        )

        # Test that the many-to-many field exists and is accessible
        # TeacherLeaveRequest moved to scheduling app
        # assert hasattr(leave_request, "affected_class_parts")
        assert leave_request.affected_sessions_count == 0  # No class parts assigned yet

    def test_notification_tracking(self):
        """Test notification tracking fields."""
        leave_request = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=get_current_date() + timezone.timedelta(days=1),
            reason="Test reason",
            notification_sent=True,
            substitute_found=True,
        )

        assert leave_request.notification_sent
        assert leave_request.substitute_found

    def test_substitute_confirmation_workflow(self):
        """Test substitute confirmation workflow."""
        leave_request = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=get_current_date() + timezone.timedelta(days=1),
            reason="Test reason",
            substitute_teacher=self.substitute_teacher,
            substitute_confirmed=False,
        )

        # Initially substitute not confirmed
        assert not leave_request.substitute_confirmed

        # Simulate substitute confirmation
        leave_request.substitute_confirmed = True
        leave_request.save()

        leave_request.refresh_from_db()
        assert leave_request.substitute_confirmed

    def test_leave_request_indexing(self):
        """Test that leave requests are properly indexed for querying."""
        # Create multiple leave requests
        sick_leave = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=get_current_date() + timezone.timedelta(days=1),
            leave_type=TeacherLeaveRequest.LeaveType.SICK,
            reason="Sick",
            is_emergency=True,
        )

        personal_leave = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=get_current_date() + timezone.timedelta(days=2),
            leave_type=TeacherLeaveRequest.LeaveType.PERSONAL,
            reason="Personal",
            is_emergency=False,
        )

        # Test querying by teacher
        teacher_requests = TeacherLeaveRequest.objects.filter(teacher=self.teacher)
        assert sick_leave in teacher_requests
        assert personal_leave in teacher_requests

        # Test querying by emergency status
        emergency_requests = TeacherLeaveRequest.objects.filter(is_emergency=True)
        assert sick_leave in emergency_requests
        assert personal_leave not in emergency_requests

        # Test querying by leave type
        sick_requests = TeacherLeaveRequest.objects.filter(
            leave_type=TeacherLeaveRequest.LeaveType.SICK,
        )
        assert sick_leave in sick_requests
        assert personal_leave not in sick_requests

    def test_comprehensive_leave_workflow(self):
        """Test complete leave request workflow."""
        # 1. Create leave request
        leave_request = TeacherLeaveRequest.objects.create(
            teacher=self.teacher,
            leave_date=get_current_date() + timezone.timedelta(days=3),
            leave_type=TeacherLeaveRequest.LeaveType.MEDICAL,
            reason="Medical procedure",
            is_emergency=False,
        )

        # 2. Department notified
        leave_request.notification_sent = True
        leave_request.save()

        # 3. Approve request
        leave_request.approve(user=self.user, notes="Medical documentation provided")

        # 4. Assign substitute
        leave_request.assign_substitute(
            substitute=self.substitute_teacher,
            assigned_by=self.user,
        )

        # 5. Substitute confirms
        leave_request.substitute_confirmed = True
        leave_request.save()

        # Verify complete workflow
        leave_request.refresh_from_db()
        assert leave_request.notification_sent
        assert leave_request.is_approved
        assert leave_request.substitute_found
        assert leave_request.substitute_confirmed
        assert leave_request.substitute_teacher == self.substitute_teacher
        assert "Medical documentation provided" in leave_request.notes
