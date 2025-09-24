import factory
from django.contrib.auth import get_user_model
from django.db import models
from factory.django import DjangoModelFactory
from faker import Faker

from apps.people.models import Gender, Person, StudentProfile

User = get_user_model()
fake = Faker()


# Define UserType choices inline since it's not in models.py
class UserType(models.TextChoices):
    ADMIN = "ADMIN", "Administrator"
    FACULTY = "FACULTY", "Faculty"
    STAFF = "STAFF", "Staff"
    STUDENT = "STUDENT", "Student"
    PARENT = "PARENT", "Parent"
    OTHER = "OTHER", "Other"


class UserFactory(DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("email",)

    email = factory.LazyAttribute(lambda _: fake.unique.email())
    first_name = factory.LazyAttribute(lambda _: fake.first_name())
    last_name = factory.LazyAttribute(lambda _: fake.last_name())
    is_active = True
    user_type = UserType.STUDENT

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override the default _create to handle password hashing."""
        password = kwargs.pop("password", "testpass123")
        user = super()._create(model_class, *args, **kwargs)
        user.set_password(password)
        user.save()
        return user


# Gender choices imported from models


class PersonFactory(DjangoModelFactory):
    class Meta:
        model = Person
        django_get_or_create = ("email",)

    first_name = factory.LazyAttribute(lambda _: fake.first_name())
    last_name = factory.LazyAttribute(lambda _: fake.last_name())
    email = factory.LazyAttribute(lambda _: fake.unique.email())
    date_of_birth = factory.LazyAttribute(lambda _: fake.date_of_birth(minimum_age=18, maximum_age=30))
    preferred_gender = factory.Iterator([x[0] for x in Gender.choices])
    phone_number = factory.LazyAttribute(lambda _: fake.phone_number())
    address = factory.LazyAttribute(lambda _: fake.street_address())
    city = factory.LazyAttribute(lambda _: fake.city())
    country = factory.LazyAttribute(lambda _: fake.country_code())

    user = factory.SubFactory(
        UserFactory,
        first_name=factory.SelfAttribute("..first_name"),
        last_name=factory.SelfAttribute("..last_name"),
        email=factory.SelfAttribute("..email"),
    )


# StudentStatus choices imported from StudentProfile.Status


class StudentProfileFactory(DjangoModelFactory):
    class Meta:
        model = StudentProfile
        django_get_or_create = ("student_id",)

    person = factory.SubFactory(PersonFactory)
    student_id = factory.LazyAttribute(
        lambda _: f"{fake.random_int(min=2000, max=2099)}-{fake.random_int(min=10000, max=99999)}",
    )
    admission_date = factory.LazyAttribute(lambda _: fake.date_between(start_date="-4y", end_date="today"))
    current_status = factory.Iterator([x[0] for x in StudentProfile.Status.choices])

    @factory.post_generation
    def majors(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for major in extracted:
                self.majors.add(major)
        else:
            # Default to adding one random major if none provided
            from apps.curriculum.factories import MajorFactory

            major = MajorFactory()
            self.majors.add(major)
