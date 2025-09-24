"""Factory-boy factories for scheduling models.

This module provides factory classes for generating realistic test data
for scheduling-related models including:
- Class headers (scheduled class instances)
- Class sessions and parts
- Room scheduling and availability
- Combined class groups

Following clean architecture principles with realistic data generation
that supports comprehensive testing of scheduling workflows.
"""

from datetime import timedelta

import factory
from django.utils import timezone
from factory import Faker
from factory.django import DjangoModelFactory

from apps.scheduling.models import ClassHeader


class ClassHeaderFactory(DjangoModelFactory):
    """Factory for creating class headers (scheduled class instances)."""

    class Meta:
        model = ClassHeader
        django_get_or_create = ("course", "term", "class_code")

    # Will be set by external factories
    course = None
    term = None

    class_code = factory.LazyAttribute(lambda obj: f"{obj.course.code}-A" if obj.course else "TEST101-A")

    max_enrollment = Faker("random_int", min=15, max=40)

    # Class scheduling
    meeting_days = factory.Iterator(
        [
            "MW",  # Monday/Wednesday
            "TTH",  # Tuesday/Thursday
            "MWF",  # Monday/Wednesday/Friday
            "MTWTHF",  # Daily
            "SAT",  # Saturday only
            "SUN",  # Sunday only
            "ONLINE",  # Online/No set days
        ],
    )

    start_time = factory.LazyAttribute(
        lambda obj: (None if obj.meeting_days == "ONLINE" else factory.factory.Faker("time_object")),
    )

    end_time = factory.LazyAttribute(
        lambda obj: (
            None
            if obj.meeting_days == "ONLINE" or not obj.start_time
            else (
                factory.datetime.datetime.combine(timezone.now().date(), obj.start_time)
                + timedelta(minutes=factory.factory.Faker("random_element", elements=[50, 75, 110, 150, 180]))
            ).time()
        ),
    )

    # Instructor information
    instructor_name = factory.LazyAttribute(
        lambda obj: (
            factory.factory.Faker("name") if factory.factory.Faker("boolean", chance_of_getting_true=85) else "TBA"
        ),
    )

    instructor_email = factory.LazyAttribute(
        lambda obj: (
            f"{obj.instructor_name.lower().replace(' ', '.')}@naga.edu.kh" if obj.instructor_name != "TBA" else ""
        ),
    )

    # Class status and notes
    status = Faker(
        "random_element",
        elements=[
            "SCHEDULED",
            "ACTIVE",
            "COMPLETED",
            "CANCELLED",
            "SUSPENDED",
        ],
    )

    instructor_notes = factory.LazyAttribute(
        lambda obj: (
            f"Class section {obj.class_code}" if factory.factory.Faker("boolean", chance_of_getting_true=25) else ""
        ),
    )
