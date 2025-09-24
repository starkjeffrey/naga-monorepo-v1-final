"""Factory-boy factories for curriculum models.

This module provides factory classes for generating realistic test data
for curriculum-related models including:
- Academic divisions and departments
- Courses with prerequisites and descriptions
- Academic terms and schedules
- Class headers and sections
- Academic programs and requirements

Following clean architecture principles with realistic data generation
that supports comprehensive testing of academic workflows.
"""

from datetime import date, timedelta

import factory
from django.utils import timezone
from factory import Faker, SubFactory
from factory.django import DjangoModelFactory

from apps.curriculum.models import Course, Division, Term


class DivisionFactory(DjangoModelFactory):
    """Factory for creating academic divisions."""

    class Meta:
        model = Division
        django_get_or_create = ("short_name",)

    name = Faker(
        "random_element",
        elements=[
            "Computer Science",
            "Business Administration",
            "Engineering",
            "Liberal Arts",
            "Natural Sciences",
            "Social Sciences",
            "Mathematics",
            "Languages and Literature",
            "Fine Arts",
            "Health Sciences",
            "Education",
            "Communication Studies",
        ],
    )

    short_name = factory.LazyAttribute(
        lambda obj: {
            "Computer Science": "CS",
            "Business Administration": "BA",
            "Engineering": "ENG",
            "Liberal Arts": "LA",
            "Natural Sciences": "NS",
            "Social Sciences": "SS",
            "Mathematics": "MATH",
            "Languages and Literature": "LANG",
            "Fine Arts": "FA",
            "Health Sciences": "HS",
            "Education": "EDU",
            "Communication Studies": "COMM",
        }.get(obj.name, obj.name[:4].upper()),
    )

    description = factory.LazyAttribute(
        lambda obj: (
            f"The {obj.name} division offers comprehensive academic programs "
            f"focusing on {obj.name.lower()} education and research."
        ),
    )

    is_active = Faker("boolean", chance_of_getting_true=95)

    display_order = factory.Sequence(lambda n: n * 100)


class CourseFactory(DjangoModelFactory):
    """Factory for creating courses."""

    class Meta:
        model = Course
        django_get_or_create = ("code",)

    division = SubFactory(DivisionFactory)

    code = factory.Sequence(lambda n: f"COURSE{n:03d}")

    title = factory.LazyAttribute(
        lambda obj: {
            "CS": Faker(
                "random_element",
                elements=[
                    "Introduction to Programming",
                    "Data Structures and Algorithms",
                    "Database Management Systems",
                    "Web Development",
                    "Software Engineering",
                    "Computer Networks",
                    "Artificial Intelligence",
                    "Machine Learning",
                    "Cybersecurity Fundamentals",
                    "Mobile App Development",
                    "Advanced Programming",
                    "System Analysis and Design",
                ],
            ),
            "BA": Faker(
                "random_element",
                elements=[
                    "Introduction to Business",
                    "Financial Accounting",
                    "Marketing Principles",
                    "Human Resource Management",
                    "Operations Management",
                    "Business Ethics",
                    "Strategic Management",
                    "International Business",
                    "Entrepreneurship",
                    "Business Communication",
                    "Project Management",
                    "Business Statistics",
                ],
            ),
            "ENG": Faker(
                "random_element",
                elements=[
                    "Engineering Mathematics",
                    "Physics for Engineers",
                    "Engineering Drawing",
                    "Materials Science",
                    "Thermodynamics",
                    "Fluid Mechanics",
                    "Electrical Circuits",
                    "Mechanical Design",
                    "Environmental Engineering",
                    "Engineering Economics",
                    "Safety Engineering",
                    "Quality Control",
                ],
            ),
            "MATH": Faker(
                "random_element",
                elements=[
                    "Calculus I",
                    "Calculus II",
                    "Linear Algebra",
                    "Statistics",
                    "Discrete Mathematics",
                    "Differential Equations",
                    "Abstract Algebra",
                    "Real Analysis",
                    "Probability Theory",
                    "Number Theory",
                    "Mathematical Modeling",
                    "Applied Mathematics",
                ],
            ),
        }.get(obj.division.short_name, f"Introduction to {obj.division.name}"),
    )

    credits = Faker("random_element", elements=[1, 2, 3, 4, 6])

    description = factory.LazyAttribute(
        lambda obj: (
            f"This course provides students with a comprehensive understanding of {obj.title.lower()}. "
            f"Students will learn fundamental concepts, practical applications, and develop essential "
            f"skills in this subject area."
        ),
    )

    level = Faker(
        "random_element",
        elements=[
            ("UNDERGRADUATE", "Undergraduate"),
            ("GRADUATE", "Graduate"),
            ("DOCTORAL", "Doctoral"),
        ],
    )

    # Course requirements
    prerequisites_text = factory.LazyAttribute(
        lambda obj: (
            f"Completion of {obj.division.short_name}100-level courses"
            if int(obj.code[-3:]) > 200 and Faker("boolean", chance_of_getting_true=60)
            else ""
        ),
    )

    learning_objectives = factory.LazyAttribute(
        lambda obj: (
            f"Upon completion of {obj.title}, students will be able to demonstrate understanding "
            f"of key concepts, apply theoretical knowledge to practical situations, and analyze "
            f"complex problems in the field."
            if Faker("boolean", chance_of_getting_true=70)
            else ""
        ),
    )

    # Delivery format
    delivery_format = Faker(
        "random_element",
        elements=[
            ("IN_PERSON", "In-Person"),
            ("ONLINE", "Online"),
            ("HYBRID", "Hybrid"),
            ("INTENSIVE", "Intensive"),
        ],
    )

    # Course status
    is_active = Faker("boolean", chance_of_getting_true=90)

    # Academic standards
    minimum_grade = Faker("random_element", elements=["D", "C-", "C", "C+"])

    repeatable = Faker("boolean", chance_of_getting_true=20)

    max_enrollments = factory.LazyAttribute(
        lambda obj: (
            None
            if obj.repeatable
            else (Faker("random_int", min=1, max=3) if Faker("boolean", chance_of_getting_true=30) else None)
        ),
    )


class TermFactory(DjangoModelFactory):
    """Factory for creating academic terms."""

    class Meta:
        model = Term
        django_get_or_create = ("name",)

    name = factory.LazyAttribute(
        lambda obj: (
            f"{Faker('random_element', elements=['Fall', 'Spring', 'Summer', 'Winter'])} "
            f"{Faker('random_int', min=2020, max=2030)}"
        ),
    )

    start_date = Faker("date_between", start_date="-1y", end_date="+1y")

    end_date = factory.LazyAttribute(
        lambda obj: obj.start_date + timedelta(days=Faker("random_int", min=90, max=120).generate({}))
    )

    registration_start = factory.LazyAttribute(
        lambda obj: obj.start_date - timedelta(days=Faker("random_int", min=14, max=45).generate({})),
    )

    registration_end = factory.LazyAttribute(
        lambda obj: obj.start_date + timedelta(days=Faker("random_int", min=7, max=21).generate({})),
    )

    # Term type and status
    term_type = factory.LazyAttribute(
        lambda obj: {
            "Fall": "FALL",
            "Spring": "SPRING",
            "Summer": "SUMMER",
            "Winter": "WINTER",
        }.get(obj.name.split()[0], "FALL"),
    )

    is_active = factory.LazyAttribute(lambda obj: obj.start_date <= timezone.now().date() <= obj.end_date)

    # Academic calendar details
    add_drop_deadline = factory.LazyAttribute(lambda obj: obj.start_date + timedelta(days=14))

    withdraw_deadline = factory.LazyAttribute(lambda obj: obj.end_date - timedelta(days=21))

    final_exam_start = factory.LazyAttribute(lambda obj: obj.end_date - timedelta(days=7))

    final_exam_end = factory.LazyAttribute(lambda obj: obj.end_date)

    # Term notes
    notes = factory.LazyAttribute(
        lambda obj: (
            f"Academic term {obj.name} running from {obj.start_date} to {obj.end_date}"
            if Faker("boolean", chance_of_getting_true=30)
            else ""
        ),
    )


# Utility factories for creating related academic data


class AcademicProgramFactory:
    """Factory for creating complete academic programs."""

    @classmethod
    def create_computer_science_program(cls):
        """Create a complete Computer Science program with courses."""
        # Create CS division
        cs_division = DivisionFactory(name="Computer Science", code="CS")

        # Core CS courses
        cs_courses = []
        course_data = [
            ("CS101", "Introduction to Programming", 3),
            ("CS102", "Programming Fundamentals", 3),
            ("CS201", "Data Structures", 4),
            ("CS202", "Algorithms", 4),
            ("CS301", "Database Systems", 3),
            ("CS302", "Software Engineering", 4),
            ("CS401", "Senior Project I", 3),
            ("CS402", "Senior Project II", 3),
        ]

        for code, title, credits in course_data:
            course = CourseFactory(division=cs_division, code=code, title=title, credits=credits)
            cs_courses.append(course)

        return cs_division, cs_courses

    @classmethod
    def create_business_program(cls):
        """Create a complete Business Administration program."""
        # Create Business division
        ba_division = DivisionFactory(name="Business Administration", code="BA")

        # Core Business courses
        ba_courses = []
        course_data = [
            ("BA101", "Introduction to Business", 3),
            ("BA150", "Business Mathematics", 3),
            ("BA201", "Financial Accounting", 4),
            ("BA202", "Managerial Accounting", 4),
            ("BA301", "Marketing Principles", 3),
            ("BA302", "Human Resources", 3),
            ("BA401", "Strategic Management", 4),
            ("BA450", "Business Capstone", 3),
        ]

        for code, title, credits in course_data:
            course = CourseFactory(division=ba_division, code=code, title=title, credits=credits)
            ba_courses.append(course)

        return ba_division, ba_courses


class TermScheduleFactory:
    """Factory for creating complete term schedules."""

    @classmethod
    def create_term_with_classes(cls, course_count=10, sections_per_course=2):
        """Create a term with multiple courses and class sections."""
        term = TermFactory()

        # Create diverse courses
        divisions = DivisionFactory.create_batch(3)
        courses = []

        for _ in range(course_count):
            import random

            course = CourseFactory(division=random.choice(divisions))
            courses.append(course)

            # Create sections for each course (will be handled by scheduling factories)

        return term, courses

    @classmethod
    def create_realistic_academic_year(cls):
        """Create a realistic academic year with multiple terms."""
        current_year = timezone.now().date().year

        # Create terms for academic year
        fall_term = TermFactory(
            name=f"Fall {current_year}",
            start_date=date(current_year, 8, 20),
            end_date=date(current_year, 12, 15),
            registration_start=date(current_year, 7, 15),
            registration_end=date(current_year, 9, 5),
        )

        spring_term = TermFactory(
            name=f"Spring {current_year + 1}",
            start_date=date(current_year + 1, 1, 15),
            end_date=date(current_year + 1, 5, 10),
            registration_start=date(current_year, 12, 1),
            registration_end=date(current_year + 1, 2, 1),
        )

        summer_term = TermFactory(
            name=f"Summer {current_year + 1}",
            start_date=date(current_year + 1, 6, 1),
            end_date=date(current_year + 1, 7, 30),
            registration_start=date(current_year + 1, 4, 15),
            registration_end=date(current_year + 1, 6, 10),
        )

        return [fall_term, spring_term, summer_term]
