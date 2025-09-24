"""Test factories for academic models."""

import factory
from factory.django import DjangoModelFactory

from apps.academic.models import (
    CourseEquivalency,
    StudentCourseOverride,
    TransferCredit,
)
from apps.curriculum.factories import CourseFactory, TermFactory
from apps.people.factories import StudentProfileFactory, UserFactory


class CourseEquivalencyFactory(DjangoModelFactory):
    """Factory for CourseEquivalency model."""

    class Meta:
        model = CourseEquivalency

    original_course = factory.SubFactory(CourseFactory)
    equivalent_course = factory.SubFactory(CourseFactory)
    effective_term = factory.SubFactory(TermFactory)
    is_bidirectional = True
    is_active = True


class TransferCreditFactory(DjangoModelFactory):
    """Factory for TransferCredit model."""

    class Meta:
        model = TransferCredit

    student = factory.SubFactory(StudentProfileFactory)
    external_institution = factory.Faker("company")
    external_course_code = factory.Sequence(lambda n: f"TRANSF{n:03d}")
    external_course_title = factory.Faker("sentence", nb_words=4)
    external_credits = 3.0
    internal_credits = 3.0
    credit_type = "ELECTIVE_CREDIT"
    approval_status = "PENDING"


class StudentCourseOverrideFactory(DjangoModelFactory):
    """Factory for StudentCourseOverride model."""

    class Meta:
        model = StudentCourseOverride

    student = factory.SubFactory(StudentProfileFactory)
    original_course = factory.SubFactory(CourseFactory)
    substitute_course = factory.SubFactory(CourseFactory)
    override_reason = "PREREQ_WAIVER"
    detailed_reason = factory.Faker("paragraph")
    effective_term = factory.SubFactory(TermFactory)
    approval_status = "PENDING"
    requested_by = factory.SubFactory(UserFactory)
