"""
Test factories for enrollment-related models.
"""

import factory
from factory import fuzzy

from apps.enrollment.models import CourseOffering, Enrollment


class CourseOfferingFactory(factory.django.DjangoModelFactory):
    """Factory for CourseOffering model."""

    class Meta:
        model = CourseOffering

    course = factory.SubFactory("tests.factories.curriculum.CourseFactory")
    term = factory.SubFactory("tests.factories.curriculum.TermFactory")
    teacher = factory.SubFactory("tests.factories.people.TeacherProfileFactory")
    section = factory.Faker("word")
    max_enrollment = fuzzy.FuzzyInteger(10, 30)
    current_enrollment = fuzzy.FuzzyInteger(0, 20)
    status = fuzzy.FuzzyChoice(["OPEN", "CLOSED", "CANCELLED"])

    # Schedule fields
    start_date = factory.Faker("date_this_year")
    end_date = factory.LazyAttribute(lambda obj: obj.start_date.replace(month=obj.start_date.month + 3))
    meeting_days = factory.List(
        [
            fuzzy.FuzzyChoice(["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY"]).fuzz()
            for _ in range(2)  # Two meeting days
        ]
    )
    start_time = factory.Faker("time")
    end_time = factory.LazyAttribute(lambda obj: obj.start_time.replace(hour=obj.start_time.hour + 2))


class EnrollmentFactory(factory.django.DjangoModelFactory):
    """Factory for Enrollment model."""

    class Meta:
        model = Enrollment

    student = factory.SubFactory("tests.factories.people.StudentProfileFactory")
    course_offering = factory.SubFactory(CourseOfferingFactory)
    enrollment_date = factory.Faker("date_this_year")
    status = fuzzy.FuzzyChoice(["ENROLLED", "WITHDRAWN", "COMPLETED"])
    grade = fuzzy.FuzzyChoice(["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "D", "F", None])

    @factory.post_generation
    def update_course_offering_enrollment(self, create, extracted, **kwargs):
        """Update course offering enrollment count after creating enrollment."""
        if create:
            self.course_offering.current_enrollment += 1
            self.course_offering.save()
