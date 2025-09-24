"""Factory classes for common app models and user creation."""

import factory
from django.contrib.auth import get_user_model
from factory.django import DjangoModelFactory

User = get_user_model()


class UserFactory(DjangoModelFactory):
    """Factory for creating User instances."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.email}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True
    is_staff = False
    is_superuser = False


class SuperUserFactory(UserFactory):
    """Factory for creating superuser instances."""

    is_staff = True
    is_superuser = True
    username = factory.Sequence(lambda n: f"admin{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.email}@example.com")


class StaffUserFactory(UserFactory):
    """Factory for creating staff user instances."""

    is_staff = True
    username = factory.Sequence(lambda n: f"staff{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.email}@example.com")
