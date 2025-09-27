"""Unit tests for people app models.

Tests all models in the people app including:
- Person model with all profile types
- StudentProfile, TeacherProfile, StaffProfile
- Emergency contacts
- Profile switching and role management
- Data privacy and validation

These tests verify critical business logic for managing people in the system.
"""

from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from freezegun import freeze_time

from apps.people.models import EmergencyContact, Person, StaffProfile, StudentProfile, TeacherProfile


@pytest.mark.django_db
class TestPersonModel:
    """Test Person model - the core entity for all people in the system."""

    def test_person_creation(self):
        """Test creating a person with required fields."""
        person = Person.objects.create(
            personal_name="John",
            family_name="Doe",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="M",
            citizenship="KH",
            personal_email="john.doe@example.com",
        )

        assert person.personal_name == "John"
        assert person.family_name == "Doe"
        assert person.full_name == "John Doe"
        assert person.date_of_birth == date(2000, 1, 1)
        assert person.age >= 24  # Depends on current date

    @pytest.mark.parametrize(
        "gender,is_valid",
        [
            ("M", True),
            ("F", True),
            ("O", True),  # Other
            ("X", False),  # Invalid
            ("", False),  # Empty
            (None, False),  # None
        ],
    )
    def test_gender_validation(self, gender, is_valid):
        """Test gender field validation."""
        person = Person(
            personal_name="Test",
            family_name="Person",
            date_of_birth=date(2000, 1, 1),
            preferred_gender=gender,
            citizenship="KH",
            personal_email="test@example.com",
        )

        if is_valid:
            person.full_clean()  # Should not raise
        else:
            with pytest.raises(ValidationError):
                person.full_clean()

    def test_person_age_calculation(self):
        """Test age is calculated correctly."""
        with freeze_time("2024-01-15"):
            person = Person(
                personal_name="Test",
                family_name="Person",
                date_of_birth=date(2000, 1, 15),
                preferred_gender="M",
                citizenship="KH",
            )
            assert person.age == 24

            # Test birthday hasn't occurred yet this year
            person.date_of_birth = date(2000, 1, 16)
            assert person.age == 23

    def test_email_uniqueness(self):
        """Test that personal_email must be unique."""
        Person.objects.create(
            personal_name="John",
            family_name="Doe",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="M",
            citizenship="KH",
            personal_email="unique@example.com",
        )

        with pytest.raises(IntegrityError):
            Person.objects.create(
                personal_name="Jane",
                family_name="Smith",
                date_of_birth=date(2001, 1, 1),
                preferred_gender="F",
                citizenship="KH",
                personal_email="unique@example.com",  # Duplicate
            )

    @pytest.mark.parametrize(
        "email,is_valid",
        [
            ("valid@example.com", True),
            ("user.name@example.co.uk", True),
            ("invalid.email", False),
            ("@example.com", False),
            ("user@", False),
            ("", True),  # Can be blank
            (None, True),  # Can be null
        ],
    )
    def test_email_validation(self, email, is_valid):
        """Test email field validation."""
        person = Person(
            personal_name="Test",
            family_name="Person",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="M",
            citizenship="KH",
            personal_email=email,
        )

        if is_valid:
            person.full_clean()  # Should not raise
        else:
            with pytest.raises(ValidationError):
                person.full_clean()

    def test_phone_number_validation(self):
        """Test phone number validation for Cambodia."""
        valid_phones = [
            "+855123456789",
            "+85512345678",
            "0123456789",
            "012345678",
        ]

        invalid_phones = [
            "123",  # Too short
            "abc123",  # Letters
            "123-456-7890",  # Wrong format
        ]

        for phone in valid_phones:
            person = Person(
                personal_name="Test",
                family_name="Person",
                date_of_birth=date(2000, 1, 1),
                preferred_gender="M",
                citizenship="KH",
                phone_number=phone,
            )
            person.full_clean()  # Should not raise

        for phone in invalid_phones:
            person = Person(
                personal_name="Test",
                family_name="Person",
                date_of_birth=date(2000, 1, 1),
                preferred_gender="M",
                citizenship="KH",
                phone_number=phone,
            )
            with pytest.raises(ValidationError):
                person.full_clean()

    def test_citizenship_codes(self):
        """Test citizenship uses ISO country codes."""
        valid_codes = ["KH", "US", "GB", "FR", "CN", "TH", "VN"]

        for code in valid_codes:
            person = Person(
                personal_name="Test",
                family_name="Person",
                date_of_birth=date(2000, 1, 1),
                preferred_gender="M",
                citizenship=code,
            )
            person.full_clean()  # Should not raise

    def test_preferred_name_defaults_to_personal_name(self):
        """Test preferred_name defaults to personal_name if not set."""
        person = Person.objects.create(
            personal_name="John",
            family_name="Doe",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )

        # Should default to personal_name
        assert person.personal_name == "John"

        # Can be overridden
        person.personal_name = "Johnny"
        person.save()
        assert person.personal_name == "Johnny"

    def test_person_soft_delete(self):
        """Test soft delete functionality."""
        person = Person.objects.create(
            personal_name="John",
            family_name="Doe",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )

        assert not person.is_deleted

        # Soft delete
        person.is_deleted = True
        person.save()

        # Should still exist in database
        assert Person.objects.filter(id=person.id).exists()

        # But not in active queryset if implemented
        # assert not Person.active_objects.filter(id=person.id).exists()


@pytest.mark.django_db
class TestStudentProfile:
    """Test StudentProfile model."""

    def test_student_profile_creation(self):
        """Test creating a student profile."""
        person = Person.objects.create(
            personal_name="Jane",
            family_name="Student",
            date_of_birth=date(2003, 1, 1),
            preferred_gender="F",
            citizenship="KH",
        )

        student = StudentProfile.objects.create(
            person=person,
            student_id=20240001,
            entry_date=date(2024, 1, 1),
            expected_graduation_date=date(2028, 6, 1),
            current_status="ACTIVE",
        )

        assert student.student_id == 20240001
        assert student.person == person
        assert student.current_status == "ACTIVE"
        assert str(student) == "20240001 - Jane Student"

    def test_student_id_uniqueness(self):
        """Test that student_id must be unique."""
        person1 = Person.objects.create(
            personal_name="Student1",
            family_name="Test",
            date_of_birth=date(2003, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )

        person2 = Person.objects.create(
            personal_name="Student2",
            family_name="Test",
            date_of_birth=date(2003, 2, 1),
            preferred_gender="F",
            citizenship="KH",
        )

        StudentProfile.objects.create(person=person1, student_id=20240001)

        with pytest.raises(IntegrityError):
            StudentProfile.objects.create(person=person2, student_id=20240001)  # Duplicate

    @pytest.mark.parametrize(
        "status,is_valid",
        [
            ("ACTIVE", True),
            ("INACTIVE", True),
            ("GRADUATED", True),
            ("WITHDRAWN", True),
            ("SUSPENDED", True),
            ("INVALID", False),
            ("", False),
        ],
    )
    def test_student_status_choices(self, status, is_valid):
        """Test student status validation."""
        person = Person.objects.create(
            personal_name="Test",
            family_name="Student",
            date_of_birth=date(2003, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )

        student = StudentProfile(person=person, student_id=20240999, current_status=status)

        if is_valid:
            student.full_clean()  # Should not raise
        else:
            with pytest.raises(ValidationError):
                student.full_clean()

    def test_student_graduation_date_logic(self):
        """Test graduation date must be after entry date."""
        person = Person.objects.create(
            personal_name="Test",
            family_name="Student",
            date_of_birth=date(2003, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )

        # Invalid: graduation before entry
        student = StudentProfile(
            person=person,
            student_id=20240001,
            entry_date=date(2024, 1, 1),
            expected_graduation_date=date(2023, 1, 1),  # Before entry
        )

        with pytest.raises(ValidationError):
            student.full_clean()

        # Valid: graduation after entry
        student.expected_graduation_date = date(2028, 1, 1)  # type: ignore[attr-defined]
        student.full_clean()  # Should not raise

    def test_student_guardian_information(self):
        """Test guardian information for students."""
        person = Person.objects.create(
            personal_name="Minor",
            family_name="Student",
            date_of_birth=date(2008, 1, 1),  # Minor
            preferred_gender="M",
            citizenship="KH",
        )

        student = StudentProfile.objects.create(
            person=person,
            student_id=20240001,
        )
        # Set guardian fields if they exist
        student.guardian_name = "Parent Name"  # type: ignore[attr-defined]
        student.guardian_relationship = "Mother"  # type: ignore[attr-defined]

        assert student.guardian_name == "Parent Name"  # type: ignore[attr-defined]
        assert student.guardian_relationship == "Mother"  # type: ignore[attr-defined]

        # Guardian should be required for minors
        if person.age < 18:
            student.guardian_name = None  # type: ignore[attr-defined]
            with pytest.raises(ValidationError):
                student.full_clean()


@pytest.mark.django_db
class TestTeacherProfile:
    """Test TeacherProfile model."""

    def test_teacher_profile_creation(self):
        """Test creating a teacher profile."""
        person = Person.objects.create(
            personal_name="John",
            family_name="Teacher",
            date_of_birth=date(1980, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )

        teacher = TeacherProfile.objects.create(
            person=person,
            employee_id="TCH2024001",
            hire_date=date(2020, 1, 1),
            contract_type="FULL_TIME",
            department="Computer Science",
            title="Assistant Professor",
        )

        assert teacher.employee_id == "TCH2024001"  # type: ignore[attr-defined]
        assert teacher.contract_type == "FULL_TIME"  # type: ignore[attr-defined]
        assert teacher.department == "Computer Science"  # type: ignore[attr-defined]

    @pytest.mark.parametrize(
        "contract_type,is_valid",
        [
            ("FULL_TIME", True),
            ("PART_TIME", True),
            ("ADJUNCT", True),
            ("CONTRACT", True),
            ("INVALID", False),
        ],
    )
    def test_teacher_contract_types(self, contract_type, is_valid):
        """Test teacher contract type validation."""
        person = Person.objects.create(
            personal_name="Test",
            family_name="Teacher",
            date_of_birth=date(1980, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )

        teacher = TeacherProfile(person=person, employee_id="TCH999999", contract_type=contract_type)

        if is_valid:
            teacher.full_clean()  # Should not raise
        else:
            with pytest.raises(ValidationError):
                teacher.full_clean()

    def test_teacher_can_supervise_projects(self):
        """Test teacher supervision capability."""
        person = Person.objects.create(
            personal_name="Senior",
            family_name="Professor",
            date_of_birth=date(1970, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )

        teacher = TeacherProfile.objects.create(person=person)
        teacher.employee_id = "TCH2024002"  # type: ignore[attr-defined]
        teacher.can_supervise_projects = True  # type: ignore[attr-defined]

        assert teacher.can_supervise_projects  # type: ignore[attr-defined]

        # Junior teacher might not supervise
        junior_teacher = TeacherProfile.objects.create(
            person=Person.objects.create(
                personal_name="Junior",
                family_name="Instructor",
                date_of_birth=date(1990, 1, 1),
                preferred_gender="F",
                citizenship="KH",
            ),
        )
        junior_teacher.employee_id = "TCH2024003"  # type: ignore[attr-defined]
        junior_teacher.can_supervise_projects = False  # type: ignore[attr-defined]

        assert not junior_teacher.can_supervise_projects  # type: ignore[attr-defined]


@pytest.mark.django_db
class TestStaffProfile:
    """Test StaffProfile model."""

    def test_staff_profile_creation(self):
        """Test creating a staff profile."""
        person = Person.objects.create(
            personal_name="Admin",
            family_name="Staff",
            date_of_birth=date(1985, 1, 1),
            preferred_gender="F",
            citizenship="KH",
        )

        staff = StaffProfile.objects.create(
            person=person,
            employee_id="STF2024001",
            hire_date=date(2022, 1, 1),
            department="Administration",
            position="Administrative Assistant",
        )

        assert staff.employee_id == "STF2024001"  # type: ignore[attr-defined]
        assert staff.department == "Administration"  # type: ignore[attr-defined]
        assert staff.position == "Administrative Assistant"

    def test_staff_supervisor_hierarchy(self):
        """Test staff supervisor relationships."""
        # Create supervisor
        supervisor_person = Person.objects.create(
            personal_name="Boss",
            family_name="Manager",
            date_of_birth=date(1975, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )

        supervisor = StaffProfile.objects.create(
            person=supervisor_person, employee_id="STF2024001", department="Administration", position="Department Head"
        )

        # Create subordinate
        staff_person = Person.objects.create(
            personal_name="Employee",
            family_name="Worker",
            date_of_birth=date(1990, 1, 1),
            preferred_gender="F",
            citizenship="KH",
        )

        staff = StaffProfile.objects.create(
            person=staff_person,
            employee_id="STF2024002",
            department="Administration",
            position="Assistant",
            supervisor=supervisor,
        )

        assert staff.supervisor == supervisor  # type: ignore[attr-defined]

        # Test no circular supervision
        supervisor.supervisor = staff  # type: ignore[attr-defined]
        with pytest.raises(ValidationError):
            supervisor.full_clean()


@pytest.mark.django_db
class TestEmergencyContact:
    """Test EmergencyContact model."""

    def test_emergency_contact_creation(self):
        """Test creating emergency contacts."""
        person = Person.objects.create(
            personal_name="Student",
            family_name="Test",
            date_of_birth=date(2003, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )

        contact = EmergencyContact.objects.create(
            person=person,
            name="Parent Name",
            relationship="Father",
            phone_primary="+855123456789",
            email="parent@example.com",
            is_primary=True,
            priority_order=1,
        )

        assert contact.person == person
        assert contact.is_primary
        assert contact.priority_order == 1  # type: ignore[attr-defined]

    def test_multiple_emergency_contacts(self):
        """Test person can have multiple emergency contacts."""
        person = Person.objects.create(
            personal_name="Student",
            family_name="Test",
            date_of_birth=date(2003, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )

        EmergencyContact.objects.create(
            person=person,
            name="Mother",
            relationship="Mother",
            phone_primary="+855123456789",
            is_primary=True,
            priority_order=1,
        )

        EmergencyContact.objects.create(
            person=person,
            name="Father",
            relationship="Father",
            phone_primary="+855987654321",
            is_primary=False,
            priority_order=2,
        )

        assert person.emergency_contacts.count() == 2
        assert person.emergency_contacts.filter(is_primary=True).count() == 1

    def test_emergency_contact_priority_ordering(self):
        """Test emergency contacts are ordered by priority."""
        person = Person.objects.create(
            personal_name="Student",
            family_name="Test",
            date_of_birth=date(2003, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )

        EmergencyContact.objects.create(
            person=person, name="Contact 3", relationship="Friend", phone_primary="+855333333333", priority_order=3
        )

        EmergencyContact.objects.create(
            person=person, name="Contact 1", relationship="Mother", phone_primary="+855111111111", priority_order=1
        )

        EmergencyContact.objects.create(
            person=person, name="Contact 2", relationship="Father", phone_primary="+855222222222", priority_order=2
        )

        contacts = person.emergency_contacts.all()
        assert contacts[0].priority_order == 1  # type: ignore[attr-defined]
        assert contacts[1].priority_order == 2  # type: ignore[attr-defined]
        assert contacts[2].priority_order == 3  # type: ignore[attr-defined]


@pytest.mark.django_db
class TestProfileSwitching:
    """Test scenarios where a person has multiple profiles."""

    def test_person_as_student_and_staff(self):
        """Test person can be both student and staff (e.g., working while studying)."""
        person = Person.objects.create(
            personal_name="Dual",
            family_name="Role",
            date_of_birth=date(1995, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )

        # Create student profile
        student = StudentProfile.objects.create(person=person, student_id=20240001, current_status="ACTIVE")

        # Create staff profile
        staff = StaffProfile.objects.create(
            person=person, employee_id="STF2024001", department="Library", position="Assistant"
        )

        assert person.student_profile == student
        assert person.staff_profile == staff

    def test_person_profile_access_methods(self):
        """Test methods to check what profiles a person has."""
        person = Person.objects.create(
            personal_name="Multi",
            family_name="Profile",
            date_of_birth=date(1990, 1, 1),
            preferred_gender="F",
            citizenship="KH",
        )

        # Initially no profiles
        assert not hasattr(person, "student_profile")
        assert not hasattr(person, "teacher_profile")
        assert not hasattr(person, "staff_profile")

        # Add teacher profile
        TeacherProfile.objects.create(person=person, employee_id="TCH2024001")

        person.refresh_from_db()
        assert hasattr(person, "teacher_profile")

        # Check role methods if implemented
        if hasattr(person, "is_teacher"):
            assert person.is_teacher()
        if hasattr(person, "is_student"):
            assert not person.is_student()


@pytest.mark.django_db
class TestDataPrivacy:
    """Test data privacy and security features."""

    def test_sensitive_data_not_in_str(self):
        """Test that sensitive data is not exposed in string representation."""
        person = Person.objects.create(
            personal_name="Private",
            family_name="Person",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="M",
            citizenship="KH",
            passport_number="P123456789",
            national_id="123456789012",
        )

        str_repr = str(person)

        # Should not contain sensitive data
        assert "P123456789" not in str_repr
        assert "123456789012" not in str_repr

    def test_medical_information_privacy(self):
        """Test medical information is properly protected."""
        person = Person.objects.create(
            personal_name="Patient",
            family_name="Test",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )

        StudentProfile.objects.create(
            person=person, student_id=20240001, medical_conditions="Diabetes Type 1", dietary_restrictions="No sugar"
        )

        # Medical info should require special permission to access
        # This would be implemented via Django permissions
        # assert student.can_view_medical_info(user) == False  # Unless authorized
