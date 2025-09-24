"""
Test factories for curriculum-related models.
"""

import factory
from factory import fuzzy

from apps.curriculum.models import Course, Major, Term


class TermFactory(factory.django.DjangoModelFactory):
    """Factory for Term model."""

    class Meta:
        model = Term

    name = factory.Sequence(lambda n: f"Term {n:03d}")
    code = factory.Sequence(lambda n: f"T{n:03d}")
    start_date = factory.Faker("date_this_year")
    end_date = factory.LazyAttribute(lambda obj: obj.start_date.replace(month=obj.start_date.month + 4))
    is_active = True
    registration_start_date = factory.LazyAttribute(lambda obj: obj.start_date.replace(day=obj.start_date.day - 30))
    registration_end_date = factory.LazyAttribute(lambda obj: obj.start_date.replace(day=obj.start_date.day - 7))


class CourseFactory(factory.django.DjangoModelFactory):
    """Factory for Course model."""

    class Meta:
        model = Course

    code = factory.Sequence(lambda n: f"COURSE{n:03d}")
    title = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("text", max_nb_chars=500)
    credit_hours = fuzzy.FuzzyInteger(1, 6)
    level = fuzzy.FuzzyChoice(["UNDERGRADUATE", "GRADUATE"])
    department = factory.Faker("word")
    is_active = True

    # Prerequisites can be added via post-generation if needed
    @factory.post_generation
    def prerequisites(self, create, extracted, **kwargs):
        """Add prerequisite courses after creation."""
        if not create or not extracted:
            return
        self.prerequisites.add(*extracted)


class MajorFactory(factory.django.DjangoModelFactory):
    """Factory for Major model."""

    class Meta:
        model = Major

    name = factory.Faker("sentence", nb_words=2)
    code = factory.Sequence(lambda n: f"PROG{n:03d}")
    description = factory.Faker("text", max_nb_chars=1000)
    degree_type = fuzzy.FuzzyChoice(["BACHELOR", "MASTER", "DOCTORATE", "CERTIFICATE"])
    total_credits_required = fuzzy.FuzzyInteger(120, 180)
    duration_years = fuzzy.FuzzyInteger(2, 6)
    is_active = True

    @factory.post_generation
    def required_courses(self, create, extracted, **kwargs):
        """Add required courses to program after creation."""
        if not create or not extracted:
            return
        self.required_courses.add(*extracted)

    @factory.post_generation
    def elective_courses(self, create, extracted, **kwargs):
        """Add elective courses to program after creation."""
        if not create or not extracted:
            return
        self.elective_courses.add(*extracted)
