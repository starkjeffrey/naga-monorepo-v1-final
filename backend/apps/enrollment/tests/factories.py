"""Factory-boy factories for enrollment models.

This module provides factory classes for generating realistic test data
for enrollment-related models including:
- Class header enrollments
- Student enrollment statuses and history
- Waitlist management
- Enrollment prerequisites and validation

Following clean architecture principles with realistic data generation
that supports comprehensive testing of enrollment workflows.
"""

from datetime import timedelta

import factory
from factory import Faker
from factory.django import DjangoModelFactory

from apps.enrollment.models import ClassHeaderEnrollment


class ClassHeaderEnrollmentFactory(DjangoModelFactory):
    """Factory for creating class header enrollments."""

    class Meta:
        model = ClassHeaderEnrollment
        django_get_or_create = ("student", "class_header")

    # Will be set by external factories
    student = None
    class_header = None

    enrollment_date = Faker("date_between", start_date="-30d", end_date="today")

    status = Faker(
        "random_element",
        elements=[
            "ENROLLED",
            "WAITLISTED",
            "DROPPED",
            "COMPLETED",
            "FAILED",
            "WITHDRAWN",
            "PENDING",
            "ACTIVE",
        ],
    )

    # Academic tracking
    grade = factory.LazyAttribute(
        lambda obj: (
            None
            if obj.status in ["ENROLLED", "WAITLISTED", "PENDING", "ACTIVE", "DROPPED", "WITHDRAWN"]
            else factory.factory.Faker(
                "random_element",
                elements=[
                    "A+",
                    "A",
                    "A-",
                    "B+",
                    "B",
                    "B-",
                    "C+",
                    "C",
                    "C-",
                    "D+",
                    "D",
                    "F",
                    "I",
                    "W",
                ],
            )
        ),
    )

    credits_earned = factory.LazyAttribute(
        lambda obj: (
            obj.class_header.course.credits
            if obj.status == "COMPLETED" and obj.grade not in ["F", "W"]
            else (0 if obj.status in ["FAILED", "WITHDRAWN", "DROPPED"] or obj.grade in ["F", "W"] else None)
        ),  # Pending completion
    )

    # Enrollment details
    enrollment_method = Faker(
        "random_element",
        elements=[
            "ONLINE",
            "ADVISOR",
            "OFFICE",
            "PHONE",
            "WALK_IN",
        ],
    )

    # Waitlist information
    waitlist_position = factory.LazyAttribute(
        lambda obj: (factory.factory.Faker("random_int", min=1, max=20) if obj.status == "WAITLISTED" else None),
    )

    waitlist_date = factory.LazyAttribute(lambda obj: obj.enrollment_date if obj.status == "WAITLISTED" else None)

    # Payment and financial
    tuition_paid = factory.LazyAttribute(
        lambda obj: obj.status in ["ENROLLED", "ACTIVE", "COMPLETED"]
        and factory.factory.Faker("boolean", chance_of_getting_true=80),
    )

    # Completion tracking
    completion_date = factory.LazyAttribute(
        lambda obj: (
            obj.enrollment_date + timedelta(days=factory.factory.Faker("random_int", min=90, max=120))
            if obj.status == "COMPLETED"
            else None
        ),
    )

    drop_date = factory.LazyAttribute(
        lambda obj: (
            obj.enrollment_date + timedelta(days=factory.factory.Faker("random_int", min=1, max=60))
            if obj.status in ["DROPPED", "WITHDRAWN"]
            else None
        ),
    )

    # Administrative notes
    notes = factory.LazyAttribute(
        lambda obj: (
            {
                "WAITLISTED": f"Student placed on waitlist position {obj.waitlist_position}",
                "DROPPED": f"Student dropped course on {obj.drop_date}",
                "WITHDRAWN": f"Student withdrew on {obj.drop_date}",
                "FAILED": "Student did not meet course requirements",
                "COMPLETED": f"Course completed successfully with grade {obj.grade}",
            }.get(obj.status, "")
            if factory.factory.Faker("boolean", chance_of_getting_true=30)
            else ""
        ),
    )

    # Timestamps
    created_at = factory.LazyAttribute(lambda obj: obj.enrollment_date)
    updated_at = factory.LazyAttribute(lambda obj: obj.completion_date or obj.drop_date or obj.enrollment_date)


# Utility factories for creating enrollment scenarios


class EnrollmentScenarioFactory:
    """Factory for creating realistic enrollment scenarios."""

    @classmethod
    def create_successful_enrollment(cls, student=None, class_header=None):
        """Create a successful enrollment from start to completion."""
        from apps.people.tests.factories import StudentProfileFactory
        from apps.scheduling.tests.factories import ClassHeaderFactory

        if not student:
            student = StudentProfileFactory()
        if not class_header:
            class_header = ClassHeaderFactory()

        return ClassHeaderEnrollmentFactory(
            student=student,
            class_header=class_header,
            status="COMPLETED",
            tuition_paid=True,
            grade=factory.factory.Faker("random_element", elements=["A+", "A", "A-", "B+", "B", "B-", "C+", "C"]),
        )

    @classmethod
    def create_dropped_enrollment(cls, student=None, class_header=None):
        """Create an enrollment where student dropped the course."""
        from apps.people.tests.factories import StudentProfileFactory
        from apps.scheduling.tests.factories import ClassHeaderFactory

        if not student:
            student = StudentProfileFactory()
        if not class_header:
            class_header = ClassHeaderFactory()

        return ClassHeaderEnrollmentFactory(
            student=student,
            class_header=class_header,
            status="DROPPED",
            tuition_paid=factory.factory.Faker("boolean"),
            grade=None,
        )

    @classmethod
    def create_waitlisted_enrollment(cls, student=None, class_header=None):
        """Create a waitlisted enrollment."""
        from apps.people.tests.factories import StudentProfileFactory
        from apps.scheduling.tests.factories import ClassHeaderFactory

        if not student:
            student = StudentProfileFactory()
        if not class_header:
            class_header = ClassHeaderFactory(max_enrollment=20)  # Small class

        return ClassHeaderEnrollmentFactory(
            student=student,
            class_header=class_header,
            status="WAITLISTED",
            tuition_paid=False,
            grade=None,
            waitlist_position=factory.factory.Faker("random_int", min=1, max=10),
        )

    @classmethod
    def create_student_enrollment_history(cls, student=None, enrollment_count=5):
        """Create enrollment history for a student across multiple terms."""
        from apps.people.tests.factories import StudentProfileFactory
        from apps.scheduling.tests.factories import ClassHeaderFactory, TermFactory

        if not student:
            student = StudentProfileFactory()

        enrollments = []

        # Create terms for enrollment history
        terms = TermFactory.create_batch(3)

        for _ in range(enrollment_count):
            term = factory.factory.Faker("random_element", elements=terms)
            class_header = ClassHeaderFactory(term=term)

            # Weight toward successful completions
            status = factory.factory.Faker(
                "random_element",
                elements=[
                    "COMPLETED",
                    "COMPLETED",
                    "COMPLETED",  # Weight 60%
                    "ENROLLED",
                    "ACTIVE",
                    "DROPPED",
                    "WITHDRAWN",
                    "FAILED",
                ],
            )

            enrollment = ClassHeaderEnrollmentFactory(student=student, class_header=class_header, status=status)

            enrollments.append(enrollment)

        return enrollments

    @classmethod
    def create_full_class_enrollment(cls, class_header=None):
        """Create a full class with realistic enrollment distribution."""
        from apps.people.tests.factories import StudentProfileFactory
        from apps.scheduling.tests.factories import ClassHeaderFactory

        if not class_header:
            class_header = ClassHeaderFactory(max_enrollment=25)

        enrollments = []

        # Fill to capacity
        for _ in range(class_header.max_enrollment):
            student = StudentProfileFactory()

            # Most students are actively enrolled
            status = factory.factory.Faker(
                "random_element",
                elements=[
                    "ENROLLED",
                    "ENROLLED",
                    "ENROLLED",  # Weight 70%
                    "ACTIVE",
                    "DROPPED",
                    "WITHDRAWN",
                    "PENDING",
                ],
            )

            enrollment = ClassHeaderEnrollmentFactory(
                student=student,
                class_header=class_header,
                status=status,
                enrollment_date=class_header.term.registration_start
                + timedelta(days=factory.factory.Faker("random_int", min=0, max=14)),
            )

            enrollments.append(enrollment)

        # Add some waitlisted students
        waitlist_count = factory.factory.Faker("random_int", min=2, max=8)
        for i in range(waitlist_count):
            student = StudentProfileFactory()
            enrollment = ClassHeaderEnrollmentFactory(
                student=student,
                class_header=class_header,
                status="WAITLISTED",
                waitlist_position=i + 1,
            )
            enrollments.append(enrollment)

        return enrollments

    @classmethod
    def create_semester_enrollments(cls, term=None, student_count=50):
        """Create realistic enrollments for an entire semester."""
        from apps.people.tests.factories import StudentProfileFactory
        from apps.scheduling.tests.factories import ClassHeaderFactory, TermFactory

        if not term:
            term = TermFactory()

        # Create various classes for the term
        class_headers = ClassHeaderFactory.create_batch(8, term=term)

        # Create students
        students = StudentProfileFactory.create_batch(student_count)

        enrollments = []

        for student in students:
            # Each student enrolls in 3-6 classes
            enrollment_count = factory.factory.Faker("random_int", min=3, max=6)
            import random

            student_classes = random.sample(class_headers, min(enrollment_count, len(class_headers)))

            for class_header in student_classes:
                # Check if class is full
                current_enrollment = ClassHeaderEnrollment.objects.filter(
                    class_header=class_header,
                    status__in=["ENROLLED", "ACTIVE"],
                ).count()

                if current_enrollment >= class_header.max_enrollment:
                    status = "WAITLISTED"
                else:
                    status = factory.factory.Faker(
                        "random_element",
                        elements=[
                            "ENROLLED",
                            "ENROLLED",
                            "ENROLLED",  # Weight 85%
                            "ACTIVE",
                            "PENDING",
                        ],
                    )

                enrollment = ClassHeaderEnrollmentFactory(student=student, class_header=class_header, status=status)

                enrollments.append(enrollment)

        return enrollments
