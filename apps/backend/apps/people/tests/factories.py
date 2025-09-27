"""Factory-boy factories for people models.

This module provides factory classes for generating realistic test data
for person and student-related models including:
- Person profiles with realistic contact information
- Student profiles with academic status
- Instructor and staff profiles
- Contact information and emergency contacts

Following clean architecture principles with realistic data generation
that supports comprehensive testing of people workflows.
"""

import factory
from factory import Faker, SubFactory
from factory.django import DjangoModelFactory

from apps.people.models import EmergencyContact, Person, StudentProfile


class PersonFactory(DjangoModelFactory):
    """Factory for creating person records."""

    class Meta:
        model = Person
        django_get_or_create = ("personal_email",)

    personal_name = Faker("first_name")
    family_name = Faker("last_name")

    date_of_birth = Faker("date_of_birth", minimum_age=16, maximum_age=65)

    preferred_gender = Faker(
        "random_element",
        elements=["M", "F", "O", "N"],
    )

    citizenship = Faker(
        "random_element",
        elements=[
            "KH",  # Cambodia
            "US",  # United States
            "GB",  # United Kingdom
            "AU",  # Australia
            "CA",  # Canada
            "DE",  # Germany
            "FR",  # France
            "JP",  # Japan
            "CN",  # China
            "TH",  # Thailand
            "VN",  # Vietnam
            "SG",  # Singapore
        ],
    )

    # Note: phone_numbers is a JSONField in the Person model, not a single field

    personal_email = factory.LazyAttribute(
        lambda obj: (
            f"{obj.personal_name.lower()}.{obj.family_name.lower()}@"
            f"{factory.Faker('random_element', elements=['gmail.com', 'yahoo.com', 'hotmail.com'])}"
        )
    )

    school_email = factory.LazyAttribute(
        lambda obj: (
            f"{obj.personal_name.lower()}.{obj.family_name.lower()}@naga.edu.kh"
            if factory.Faker("boolean", chance_of_getting_true=70)
            else ""
        ),
    )

    birth_province = Faker(
        "random_element",
        elements=[
            "Phnom Penh",
            "Siem Reap",
            "Battambang",
            "Sihanoukville",
            "Kandal",
            "Takeo",
            "Kampong Cham",
        ],
    )


class StudentProfileFactory(DjangoModelFactory):
    """Factory for creating student profiles."""

    class Meta:
        model = StudentProfile
        django_get_or_create = ("student_id",)

    person = SubFactory(PersonFactory)

    student_id = factory.Sequence(lambda n: 20250000 + n)

    is_monk = Faker("boolean", chance_of_getting_true=5)
    is_transfer_student = Faker("boolean", chance_of_getting_true=15)

    current_status = Faker(
        "random_element",
        elements=[
            "ACTIVE",
            "INACTIVE",
            "GRADUATED",
            "TRANSFERRED",
            "SUSPENDED",
            "WITHDRAWN",
        ],
    )

    study_time_preference = Faker(
        "random_element",
        elements=["MORNING", "AFTERNOON", "EVENING", "WEEKEND"],
    )

    last_enrollment_date = Faker("date_between", start_date="-2y", end_date="today")


class EmergencyContactFactory(DjangoModelFactory):
    """Factory for creating emergency contacts."""

    class Meta:
        model = EmergencyContact

    person = SubFactory(PersonFactory)

    contact_name = Faker("name")

    relationship = Faker(
        "random_element",
        elements=[
            "PARENT",
            "GUARDIAN",
            "SPOUSE",
            "SIBLING",
            "RELATIVE",
            "FRIEND",
            "OTHER",
        ],
    )

    phone_number = factory.LazyAttribute(lambda obj: f"+855{factory.Faker('random_number', digits=8)}")

    email = factory.LazyAttribute(
        lambda obj: (
            f"{obj.contact_name.lower().replace(' ', '.')}@"
            f"{factory.Faker('random_element', elements=['gmail.com', 'yahoo.com', 'hotmail.com'])}"
            if factory.Faker("boolean", chance_of_getting_true=60)
            else ""
        ),
    )

    address = Faker("address")

    is_primary = factory.LazyAttribute(lambda obj: factory.Faker("boolean", chance_of_getting_true=50))

    notes = factory.LazyAttribute(
        lambda obj: (
            f"Emergency contact - {obj.relationship.replace('_', ' ').lower()}"
            if factory.Faker("boolean", chance_of_getting_true=20)
            else ""
        ),
    )


# Utility factory for creating complete student packages
class StudentPackageFactory:
    """Factory for creating complete student packages with related data."""

    @classmethod
    def create_student_with_contacts(cls, **kwargs):
        """Create a student with emergency contacts."""
        student = StudentProfileFactory(**kwargs)

        # Create 1-3 emergency contacts
        contact_count = factory.Faker("random_int", min=1, max=3)
        contacts = EmergencyContactFactory.create_batch(contact_count, person=student.person)

        # Ensure at least one is primary
        if contacts:
            contacts[0].is_primary = True
            contacts[0].save()

        return student

    @classmethod
    def create_diverse_student_cohort(cls, count=20):
        """Create a diverse cohort of students for testing."""
        students = []

        # Mix of nationalities
        nationalities = ["KH", "US", "GB", "AU", "CA", "TH", "VN", "SG"]
        enrollment_types = ["FULL_TIME", "PART_TIME", "ONLINE", "EVENING"]
        academic_levels = ["UNDERGRADUATE", "GRADUATE", "CERTIFICATE"]
        statuses = [
            "ACTIVE",
            "ACTIVE",
            "ACTIVE",
            "INACTIVE",
            "GRADUATED",
        ]  # Weighted toward active

        for _i in range(count):
            person_data = {
                "citizenship": factory.Faker("random_element", elements=nationalities),
            }

            student_data = {
                "enrollment_type": factory.Faker("random_element", elements=enrollment_types),
                "academic_level": factory.Faker("random_element", elements=academic_levels),
                "status": factory.Faker("random_element", elements=statuses),
            }

            # Create person first
            person = PersonFactory(**person_data)

            # Create student with that person
            student = StudentProfileFactory(person=person, **student_data)

            # Add emergency contacts
            EmergencyContactFactory.create_batch(factory.Faker("random_int", min=1, max=2), person=person)

            students.append(student)

        return students
