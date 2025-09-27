"""
Test factories for people-related models.
"""

from decimal import Decimal

import factory
from factory import fuzzy

from apps.people.models import Person, StudentProfile, TeacherProfile


class PersonFactory(factory.django.DjangoModelFactory):
    """Factory for Person model."""

    class Meta:
        model = Person

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.LazyAttribute(lambda obj: f"{obj.first_name.lower()}.{obj.last_name.lower()}@example.com")
    phone_number = factory.Faker("phone_number")
    date_of_birth = factory.Faker("date_of_birth", minimum_age=18, maximum_age=65)
    gender = fuzzy.FuzzyChoice(["M", "F", "O"])
    nationality = factory.Faker("country_code")

    # Address fields
    address_line_1 = factory.Faker("street_address")
    address_line_2 = factory.Faker("secondary_address")
    city = factory.Faker("city")
    province = factory.Faker("state")
    postal_code = factory.Faker("postcode")
    country = factory.Faker("country_code")


class StudentProfileFactory(factory.django.DjangoModelFactory):
    """Factory for StudentProfile model."""

    class Meta:
        model = StudentProfile

    person = factory.SubFactory(PersonFactory)
    student_id = factory.Sequence(lambda n: f"STU{n:06d}")
    enrollment_date = factory.Faker("date_this_year")
    status = fuzzy.FuzzyChoice(["ACTIVE", "INACTIVE", "GRADUATED", "WITHDRAWN"])
    emergency_contact_name = factory.Faker("name")
    emergency_contact_phone = factory.Faker("phone_number")

    @factory.post_generation
    def programs(self, create, extracted, **kwargs):
        """Add programs to student after creation."""
        if not create or not extracted:
            return
        self.programs.add(*extracted)


class TeacherProfileFactory(factory.django.DjangoModelFactory):
    """Factory for TeacherProfile model."""

    class Meta:
        model = TeacherProfile

    person = factory.SubFactory(PersonFactory)
    employee_id = factory.Sequence(lambda n: f"EMP{n:06d}")
    hire_date = factory.Faker("date_this_year")
    status = fuzzy.FuzzyChoice(["ACTIVE", "INACTIVE", "TERMINATED"])
    salary = fuzzy.FuzzyDecimal(Decimal("1000.00"), Decimal("5000.00"), precision=2)
    department = factory.Faker("word")

    @factory.post_generation
    def specializations(self, create, extracted, **kwargs):
        """Add subject specializations after creation."""
        if not create or not extracted:
            return
        self.specializations.add(*extracted)
