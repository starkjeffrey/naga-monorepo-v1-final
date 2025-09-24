"""Factory definitions for enrollment-related models."""

import factory
from django.utils import timezone
from factory.django import DjangoModelFactory
from faker import Faker

from apps.enrollment.models import (
    AddRequest,
    ClassHeaderEnrollment,
    DropRequest,
    EnrollmentHistory,
    EnrollmentStatus,
    Registration,
    RegistrationHold,
    Waitlist,
)

from .factories import ClassHeaderFactory, StudentProfileFactory, TermFactory

fake = Faker()


class RegistrationFactory(DjangoModelFactory):
    """Factory for Registration model."""

    class Meta:
        model = Registration
        django_get_or_create = ["student", "term"]

    student = factory.SubFactory(StudentProfileFactory)
    term = factory.SubFactory(TermFactory)

    registration_date = factory.LazyFunction(timezone.now)
    status = factory.LazyAttribute(lambda o: fake.random_element(["PENDING", "APPROVED", "COMPLETED"]))

    total_credits = 0
    max_credits = 18
    min_credits = 12

    advisor_approval = False
    advisor_approval_date = None
    advisor_notes = None

    is_active = True


class ClassHeaderEnrollmentFactory(DjangoModelFactory):
    """Factory for ClassHeaderEnrollment model."""

    class Meta:
        model = ClassHeaderEnrollment

    student = factory.SubFactory(StudentProfileFactory)
    class_header = factory.SubFactory(ClassHeaderFactory)
    registration = factory.SubFactory(RegistrationFactory)

    enrollment_date = factory.LazyFunction(timezone.now)
    status = factory.LazyAttribute(lambda o: fake.random_element(["ENROLLED", "DROPPED", "WITHDRAWN", "COMPLETED"]))

    grade = None
    grade_points = None

    attendance_percentage = factory.LazyAttribute(
        lambda o: fake.random_int(70, 100) if o.status == "ENROLLED" else None
    )

    is_audit = False
    is_repeat = False

    drop_date = None
    drop_reason = None

    created_at = factory.LazyFunction(timezone.now)
    updated_at = factory.LazyFunction(timezone.now)


class WaitlistFactory(DjangoModelFactory):
    """Factory for Waitlist model."""

    class Meta:
        model = Waitlist

    student = factory.SubFactory(StudentProfileFactory)
    class_header = factory.SubFactory(ClassHeaderFactory)

    position = factory.Sequence(lambda n: n + 1)
    added_date = factory.LazyFunction(timezone.now)

    notified_date = None
    notification_expiry = None

    status = factory.LazyAttribute(
        lambda o: fake.random_element(["WAITING", "NOTIFIED", "ENROLLED", "EXPIRED", "CANCELLED"])
    )

    priority_score = factory.LazyAttribute(lambda o: fake.random_int(0, 100))

    notes = None


class EnrollmentStatusFactory(DjangoModelFactory):
    """Factory for EnrollmentStatus model."""

    class Meta:
        model = EnrollmentStatus

    enrollment = factory.SubFactory(ClassHeaderEnrollmentFactory)

    status = factory.LazyAttribute(lambda o: fake.random_element(["ENROLLED", "DROPPED", "WITHDRAWN"]))
    effective_date = factory.LazyFunction(timezone.now)

    reason = factory.LazyAttribute(lambda o: fake.text(max_nb_chars=200) if o.status != "ENROLLED" else None)
    approved_by = factory.SubFactory("tests.fixtures.factories.UserFactory")

    created_at = factory.LazyFunction(timezone.now)


class DropRequestFactory(DjangoModelFactory):
    """Factory for DropRequest model."""

    class Meta:
        model = DropRequest

    enrollment = factory.SubFactory(ClassHeaderEnrollmentFactory)
    student = factory.SubFactory(StudentProfileFactory)

    request_date = factory.LazyFunction(timezone.now)
    reason = factory.LazyAttribute(
        lambda o: fake.random_element(
            ["Schedule conflict", "Course too difficult", "Personal reasons", "Changed major", "Financial reasons"]
        )
    )

    detailed_reason = factory.LazyAttribute(lambda o: fake.text(max_nb_chars=500))

    status = factory.LazyAttribute(lambda o: fake.random_element(["PENDING", "APPROVED", "DENIED"]))

    reviewed_by = None
    review_date = None
    review_notes = None

    refund_percentage = factory.LazyAttribute(
        lambda o: (
            100 if fake.boolean(chance_of_getting_true=20) else 50 if fake.boolean(chance_of_getting_true=40) else 0
        )
    )


class AddRequestFactory(DjangoModelFactory):
    """Factory for AddRequest model."""

    class Meta:
        model = AddRequest

    student = factory.SubFactory(StudentProfileFactory)
    class_header = factory.SubFactory(ClassHeaderFactory)
    term = factory.SubFactory(TermFactory)

    request_date = factory.LazyFunction(timezone.now)
    reason = factory.LazyAttribute(lambda o: fake.text(max_nb_chars=200))

    status = factory.LazyAttribute(lambda o: fake.random_element(["PENDING", "APPROVED", "DENIED"]))

    prerequisite_override = False
    capacity_override = False
    time_conflict_override = False

    reviewed_by = None
    review_date = None
    review_notes = None


class EnrollmentHistoryFactory(DjangoModelFactory):
    """Factory for EnrollmentHistory model."""

    class Meta:
        model = EnrollmentHistory

    student = factory.SubFactory(StudentProfileFactory)
    class_header = factory.SubFactory(ClassHeaderFactory)

    action = factory.LazyAttribute(lambda o: fake.random_element(["ENROLLED", "DROPPED", "WITHDRAWN", "WAITLISTED"]))
    action_date = factory.LazyFunction(timezone.now)

    performed_by = factory.SubFactory("tests.fixtures.factories.UserFactory")

    old_status = None
    new_status = factory.LazyAttribute(lambda o: o.action)

    notes = factory.LazyAttribute(
        lambda o: fake.text(max_nb_chars=200) if fake.boolean(chance_of_getting_true=30) else None
    )


class RegistrationHoldFactory(DjangoModelFactory):
    """Factory for RegistrationHold model."""

    class Meta:
        model = RegistrationHold

    student = factory.SubFactory(StudentProfileFactory)

    hold_type = factory.LazyAttribute(
        lambda o: fake.random_element(["FINANCIAL", "ACADEMIC", "DISCIPLINARY", "ADMINISTRATIVE", "IMMUNIZATION"])
    )

    reason = factory.LazyAttribute(
        lambda o: {
            "FINANCIAL": "Outstanding balance",
            "ACADEMIC": "GPA below minimum",
            "DISCIPLINARY": "Disciplinary action pending",
            "ADMINISTRATIVE": "Missing documents",
            "IMMUNIZATION": "Vaccination records required",
        }[o.hold_type]
    )

    placed_date = factory.LazyFunction(timezone.now)
    placed_by = factory.SubFactory("tests.fixtures.factories.UserFactory")

    resolved_date = None
    resolved_by = None
    resolution_notes = None

    is_active = True
    prevents_registration = True
    prevents_transcript = factory.LazyAttribute(lambda o: o.hold_type == "FINANCIAL")
