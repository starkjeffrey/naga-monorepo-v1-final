"""Factories for curriculum models."""

import datetime

import factory
from factory.django import DjangoModelFactory
from faker import Faker

from apps.curriculum.models import Course, Cycle, Division, Major, Term

fake = Faker()


class DivisionFactory(DjangoModelFactory):
    class Meta:
        model = Division
        django_get_or_create = ("name",)

    name = factory.LazyAttribute(lambda _: f"Division {fake.unique.word().title()}")
    short_name = factory.LazyAttribute(lambda o: o.name[:10])
    description = factory.Faker("paragraph")
    is_active = True
    display_order = 100


class CycleFactory(DjangoModelFactory):
    class Meta:
        model = Cycle
        django_get_or_create = ("name",)

    name = factory.LazyAttribute(lambda _: f"{fake.unique.word().title()} Cycle")
    short_name = factory.LazyAttribute(lambda o: o.name[:10])
    # Cycle doesn't have degree_awarded - that's in Major model
    division = factory.SubFactory(DivisionFactory)
    typical_duration_terms = 8  # Default to 8 terms (4 years)
    description = factory.Faker("paragraph")
    is_active = True
    display_order = 100


class MajorFactory(DjangoModelFactory):
    class Meta:
        model = Major
        django_get_or_create = ("name",)

    name = factory.LazyAttribute(lambda _: f"{fake.unique.word().title()} Major")
    short_name = factory.LazyAttribute(lambda o: o.name[:10])
    code = factory.LazyAttribute(lambda _: fake.unique.lexify(text="M??").upper())
    description = factory.Faker("paragraph")
    cycle = factory.SubFactory(CycleFactory)
    total_credits_required = 120  # Default to 120 credits
    is_active = True
    display_order = 100


class TermFactory(DjangoModelFactory):
    class Meta:
        model = Term
        django_get_or_create = ("code",)

    code = factory.LazyAttribute(lambda _: f"{fake.month_name()} {fake.year()}")
    description = factory.Faker("sentence")
    term_type = factory.Iterator([x[0] for x in Term.TermType.choices])
    is_active = True

    # Set up dates in a way that ensures proper ordering
    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        # Generate dates before creating the model
        start_date = fake.date_between(start_date="today", end_date="+1y")
        end_date = fake.date_between(
            start_date=start_date + datetime.timedelta(days=30),  # At least 30 days
            end_date=start_date + datetime.timedelta(days=180),  # At most 6 months
        )

        # Add required dates to kwargs
        kwargs.update(
            {
                "start_date": start_date,
                "end_date": end_date,
                "discount_end_date": fake.date_between(
                    start_date="-30d",
                    end_date=start_date - datetime.timedelta(days=1),
                ),
                "add_date": start_date + datetime.timedelta(days=7),  # 1 week after start
                "drop_date": start_date + datetime.timedelta(days=14),  # 2 weeks after start
                "payment_deadline_date": start_date - datetime.timedelta(days=14),  # 2 weeks before start
            },
        )

        # Set cohort numbers based on term type
        if kwargs.get("term_type") == Term.TermType.BACHELORS:
            kwargs["ba_cohort_number"] = fake.random_int(min=1, max=20)
        elif kwargs.get("term_type") == Term.TermType.MASTERS:
            kwargs["ma_cohort_number"] = fake.random_int(min=1, max=20)

        return super()._create(model_class, *args, **kwargs)


class CourseFactory(DjangoModelFactory):
    class Meta:
        model = Course
        django_get_or_create = ("code",)

    title = factory.LazyAttribute(lambda _: f"{fake.unique.bs().title()}")
    short_title = factory.LazyAttribute(lambda o: o.title[:30])
    code = factory.LazyAttribute(lambda _: f"{fake.lexify(text='???').upper()}{fake.numerify(text='###')}")
    credits = factory.LazyAttribute(lambda _: fake.random_int(min=1, max=6))
    is_active = True
    description = factory.LazyAttribute(lambda _: fake.paragraph(nb_sentences=3))
    cycle = factory.SubFactory(CycleFactory)

    # Note: Course has direct cycle FK, no need for post_generation


# Specialized factories for different types of divisions and courses
class AcademicDivisionFactory(DivisionFactory):
    """Factory for academic divisions (non-language)."""

    name = factory.LazyAttribute(lambda _: "Academic Division")
    short_name = factory.LazyAttribute(lambda _: "ACAD")
    description = factory.Faker("paragraph")


class LanguageDivisionFactory(DivisionFactory):
    """Factory for language divisions."""

    name = factory.LazyAttribute(lambda _: "Language Division")
    short_name = factory.LazyAttribute(lambda _: "LANG")
    description = factory.Faker("paragraph")


class AcademicCourseFactory(CourseFactory):
    """Factory for academic courses (non-language)."""

    is_language = False
    cycle = factory.SubFactory(CycleFactory, division=factory.SubFactory(AcademicDivisionFactory))
    credits = factory.LazyAttribute(lambda _: 3)


class LanguageCourseFactory(CourseFactory):
    """Factory for language courses."""

    is_language = True
    cycle = factory.SubFactory(CycleFactory, division=factory.SubFactory(LanguageDivisionFactory))
    credits = factory.LazyAttribute(lambda _: 3)
