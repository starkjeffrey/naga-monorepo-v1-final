from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.common.constants import Gender
from apps.people.constants import CambodianProvinces
from apps.people.models import (
    EmergencyContact,
    Person,
    StudentProfile,
    TeacherProfile,
)

User = get_user_model()


class PersonModelTest(TestCase):
    """Test Person model functionality."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="password",
        )

        self.person_data = {
            "family_name": "Smith",
            "personal_name": "John",
            "preferred_gender": Gender.MALE,
            "date_of_birth": date(1990, 1, 1),
            "email": "john.smith@example.com",
            "phone_number": "012345678",
            "nationality": "Cambodian",
            "birth_province": CambodianProvinces.PHNOM_PENH,
        }

    def test_person_creation(self):
        """Test basic person creation."""
        person = Person.objects.create(**self.person_data)
        assert person.family_name == "SMITH"  # Should be uppercase
        assert person.personal_name == "JOHN"  # Should be uppercase
        assert person.full_name == "SMITH JOHN"  # Auto-generated
        assert person.unique_id is not None

    def test_name_processing(self):
        """Test name processing and normalization."""
        person = Person.objects.create(
            family_name="jones",
            personal_name="mary",
            preferred_gender=Gender.FEMALE,
        )
        assert person.family_name == "JONES"
        assert person.personal_name == "MARY"
        assert person.full_name == "JONES MARY"

    def test_name_change_tracking_without_database_query(self):
        """Test that name changes are tracked without database query."""
        person = Person.objects.create(
            family_name="Original",
            personal_name="Name",
        )
        old_full_name = person.full_name

        # Change name without saving
        person.family_name = "Changed"
        person.personal_name = "Person"

        # Full name should still reflect original values until save
        assert person.full_name == old_full_name

    def test_field_tracking_on_refresh_from_db(self):
        """Test that original field values are tracked after refresh_from_db."""
        person = Person.objects.create(
            family_name="Test",
            personal_name="Person",
        )

        # Update in database directly
        Person.objects.filter(id=person.id).update(personal_name="UPDATED")

        # Refresh from database
        person.refresh_from_db()

        # Original values should be updated
        assert person._original_personal_name == "PERSON"

    def test_age_calculation(self):
        """Test age calculation property."""
        # Person with DOB
        person = Person.objects.create(
            family_name="Age",
            personal_name="Test",
            date_of_birth=date.today() - timedelta(days=365 * 30),  # ~30 years old
        )
        assert 29 <= person.age <= 30  # Allow for test execution date variations

        # Person without DOB
        person = Person.objects.create(
            family_name="No",
            personal_name="Age",
        )
        assert person.age is None

    def test_display_name_property(self):
        """Test display name property."""
        person = Person.objects.create(
            family_name="Legal Family",
            personal_name="Legal Personal",
            preferred_name="Preferred",
        )
        assert person.display_name == "Legal Family Legal Personal"

        # With preferred name
        person.use_preferred_name = True
        assert "Preferred" in person.display_name

    def test_legal_name_validation(self):
        """Test legal name validation."""
        person = Person.objects.create(
            family_name="Valid-Name",
            personal_name="Valid'Name",
        )
        person.full_clean()  # Should not raise

    def test_birth_province_validation(self):
        """Test birth province validation."""
        person = Person.objects.create(
            family_name="Test",
            personal_name="Person",
            birth_province=CambodianProvinces.PHNOM_PENH,
        )
        person.full_clean()  # Should not raise

    def test_role_properties(self):
        """Test role property helpers."""
        person = Person.objects.create(
            family_name="Test",
            personal_name="Person",
        )

        # Initially no roles
        assert not person.has_student_role
        assert not person.has_teacher_role
        assert not person.has_staff_role

        # Add student profile
        StudentProfile.objects.create(person=person, student_id="S12345")
        person.refresh_from_db()
        assert person.has_student_role

        # Add teacher profile
        TeacherProfile.objects.create(person=person)
        person.refresh_from_db()
        assert person.has_teacher_role

    def test_unique_email_constraint(self):
        """Test unique email constraint."""
        Person.objects.create(**self.person_data)

        # Create another person with same email
        person_data2 = self.person_data.copy()
        person_data2["family_name"] = "Johnson"
        person_data2["personal_name"] = "Robert"

        # Should raise IntegrityError due to unique constraint
        with self.assertRaises(Exception):
            Person.objects.create(**person_data2)

        # But different email should work
        person_data2["email"] = "different@example.com"
        Person.objects.create(**person_data2)


class StudentProfileModelTest(TestCase):
    """Test StudentProfile model functionality."""

    def setUp(self):
        """Set up test data."""
        self.person = Person.objects.create(
            family_name="Student",
            personal_name="Test",
            preferred_gender=Gender.MALE,
        )
        self.TEST_STUDENT_ID = "S12345"

    def test_student_profile_creation(self):
        """Test basic student profile creation."""
        profile = StudentProfile.objects.create(
            person=self.person,
            student_id=self.TEST_STUDENT_ID,
            enrollment_status="ACTIVE",
        )
        assert profile.student_id == self.TEST_STUDENT_ID
        assert profile.person == self.person
        assert profile.enrollment_status == "ACTIVE"

    def test_student_id_uniqueness(self):
        """Test student ID uniqueness constraint."""
        StudentProfile.objects.create(
            person=self.person,
            student_id=self.TEST_STUDENT_ID,
        )

        # Create another person
        person2 = Person.objects.create(
            family_name="Another",
            personal_name="Student",
        )

        # Try to create profile with same student ID
        with self.assertRaises(Exception):
            StudentProfile.objects.create(person=person2, student_id=self.TEST_STUDENT_ID)

    def test_student_status_properties(self):
        """Test student status property helpers."""
        profile = StudentProfile.objects.create(
            person=self.person,
            student_id=self.TEST_STUDENT_ID,
            enrollment_status="ACTIVE",
        )

        assert profile.is_active
        assert not profile.is_graduated
        assert not profile.is_withdrawn

        profile.enrollment_status = "GRADUATED"
        profile.save()
        assert not profile.is_active
        assert profile.is_graduated


class EmergencyContactModelTest(TestCase):
    """Test EmergencyContact model functionality."""

    def setUp(self):
        """Set up test data."""
        self.person = Person.objects.create(
            family_name="Test",
            personal_name="Person",
        )

    def test_emergency_contact_creation(self):
        """Test emergency contact creation."""
        contact = EmergencyContact.objects.create(
            person=self.person,
            name="Emergency Contact",
            relationship="Parent",
            phone_number="012345678",
            is_primary=True,
        )

        assert contact.name == "Emergency Contact"
        assert contact.relationship == "Parent"
        assert contact.phone_number == "012345678"
        assert contact.is_primary

    def test_multiple_primary_contacts(self):
        """Test handling of multiple primary contacts."""
        # Create first primary contact
        EmergencyContact.objects.create(
            person=self.person,
            name="Primary Contact 1",
            relationship="Parent",
            phone_number="012345678",
            is_primary=True,
        )

        # Create second primary contact
        contact2 = EmergencyContact.objects.create(
            person=self.person,
            name="Primary Contact 2",
            relationship="Sibling",
            phone_number="087654321",
            is_primary=True,
        )

        # First contact should no longer be primary
        contact1 = EmergencyContact.objects.get(name="Primary Contact 1")
        assert not contact1.is_primary
        assert contact2.is_primary
