"""Factory-boy factories for grading models.

This module provides factory classes for generating realistic test data
for grading and assessment models including:
- Grading scales and grade conversions
- Class part and session grades
- GPA records and grade history
- Grade change tracking

Following clean architecture principles with realistic data generation
that supports comprehensive testing of grading workflows.
"""

from decimal import Decimal

import factory
from factory import Faker, SubFactory
from factory.django import DjangoModelFactory

from apps.grading.models import (
    ClassPartGrade,
    ClassSessionGrade,
    GPARecord,
    GradeChangeHistory,
    GradeConversion,
    GradingScale,
)


class GradingScaleFactory(DjangoModelFactory):
    """Factory for creating grading scales."""

    class Meta:
        model = GradingScale
        django_get_or_create = ("name",)

    name = Faker(
        "random_element",
        elements=["Language Standard Scale", "Language IEAP Scale", "Academic Scale"],
    )

    scale_type = Faker(
        "random_element",
        elements=[
            GradingScale.ScaleType.LANGUAGE_STANDARD,
            GradingScale.ScaleType.LANGUAGE_IEAP,
            GradingScale.ScaleType.ACADEMIC,
        ],
    )

    description = factory.LazyAttribute(
        lambda obj: f"Grading scale for {obj.scale_type.replace('_', ' ').lower()} assessment",
    )

    is_active = Faker("boolean", chance_of_getting_true=80)


class GradeConversionFactory(DjangoModelFactory):
    """Factory for creating grade conversions."""

    class Meta:
        model = GradeConversion

    grading_scale = SubFactory(GradingScaleFactory)

    letter_grade = Faker(
        "random_element",
        elements=["A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F"],
    )

    min_percentage = factory.LazyAttribute(
        lambda obj: {
            "A+": Decimal("97.0"),
            "A": Decimal("93.0"),
            "A-": Decimal("90.0"),
            "B+": Decimal("87.0"),
            "B": Decimal("83.0"),
            "B-": Decimal("80.0"),
            "C+": Decimal("77.0"),
            "C": Decimal("73.0"),
            "C-": Decimal("70.0"),
            "D+": Decimal("67.0"),
            "D": Decimal("63.0"),
            "F": Decimal("0.0"),
        }.get(obj.letter_grade, Decimal("70.0")),
    )

    max_percentage = factory.LazyAttribute(
        lambda obj: {
            "A+": Decimal("100.0"),
            "A": Decimal("96.9"),
            "A-": Decimal("92.9"),
            "B+": Decimal("89.9"),
            "B": Decimal("86.9"),
            "B-": Decimal("82.9"),
            "C+": Decimal("79.9"),
            "C": Decimal("76.9"),
            "C-": Decimal("72.9"),
            "D+": Decimal("69.9"),
            "D": Decimal("66.9"),
            "F": Decimal("62.9"),
        }.get(obj.letter_grade, Decimal("100.0")),
    )

    gpa_points = factory.LazyAttribute(
        lambda obj: {
            "A+": Decimal("4.0"),
            "A": Decimal("4.0"),
            "A-": Decimal("3.7"),
            "B+": Decimal("3.3"),
            "B": Decimal("3.0"),
            "B-": Decimal("2.7"),
            "C+": Decimal("2.3"),
            "C": Decimal("2.0"),
            "C-": Decimal("1.7"),
            "D+": Decimal("1.3"),
            "D": Decimal("1.0"),
            "F": Decimal("0.0"),
        }.get(obj.letter_grade, Decimal("2.0")),
    )


class ClassPartGradeFactory(DjangoModelFactory):
    """Factory for creating class part grades."""

    class Meta:
        model = ClassPartGrade

    # Note: These will need to be connected to actual ClassPart and StudentProfile instances

    percentage_grade = Faker(
        "random_element",
        elements=[
            Decimal("95.5"),
            Decimal("88.0"),
            Decimal("92.3"),
            Decimal("76.8"),
            Decimal("84.2"),
            Decimal("91.7"),
            Decimal("78.5"),
            Decimal("89.1"),
        ],
    )

    letter_grade = factory.LazyAttribute(
        lambda obj: (
            "A"
            if obj.percentage_grade >= 90
            else (
                "B"
                if obj.percentage_grade >= 80
                else ("C" if obj.percentage_grade >= 70 else "D" if obj.percentage_grade >= 60 else "F")
            )
        ),
    )

    gpa_points = factory.LazyAttribute(
        lambda obj: (
            Decimal("4.0")
            if obj.letter_grade == "A"
            else (
                Decimal("3.0")
                if obj.letter_grade == "B"
                else (
                    Decimal("2.0")
                    if obj.letter_grade == "C"
                    else Decimal("1.0")
                    if obj.letter_grade == "D"
                    else Decimal("0.0")
                )
            )
        ),
    )

    is_final = Faker("boolean", chance_of_getting_true=20)

    comments = factory.LazyAttribute(
        lambda obj: (
            f"Good performance with {obj.percentage_grade}% achievement"
            if obj.percentage_grade >= 80
            else (
                f"Needs improvement - scored {obj.percentage_grade}%"
                if Faker("boolean", chance_of_getting_true=30)
                else ""
            )
        ),
    )


class ClassSessionGradeFactory(DjangoModelFactory):
    """Factory for creating class session grades."""

    class Meta:
        model = ClassSessionGrade

    # Note: These will need to be connected to actual instances

    percentage_grade = Faker(
        "random_element",
        elements=[
            Decimal("94.0"),
            Decimal("87.5"),
            Decimal("91.2"),
            Decimal("79.8"),
            Decimal("85.6"),
            Decimal("93.1"),
            Decimal("77.3"),
            Decimal("88.9"),
        ],
    )

    letter_grade = factory.LazyAttribute(
        lambda obj: (
            "A"
            if obj.percentage_grade >= 90
            else (
                "B"
                if obj.percentage_grade >= 80
                else ("C" if obj.percentage_grade >= 70 else "D" if obj.percentage_grade >= 60 else "F")
            )
        ),
    )

    is_final = Faker("boolean", chance_of_getting_true=25)

    assignment_type = Faker(
        "random_element",
        elements=[
            "homework",
            "quiz",
            "exam",
            "project",
            "participation",
            "presentation",
        ],
    )

    comments = factory.LazyAttribute(
        lambda obj: (
            f"Excellent {obj.assignment_type} submission"
            if obj.percentage_grade >= 90
            else (
                f"Good {obj.assignment_type} work"
                if obj.percentage_grade >= 80
                else (
                    ""
                    if Faker("boolean", chance_of_getting_true=60)
                    else f"Please see me about your {obj.assignment_type}"
                )
            )
        ),
    )


class GPARecordFactory(DjangoModelFactory):
    """Factory for creating GPA records."""

    class Meta:
        model = GPARecord

    cumulative_gpa = Faker(
        "random_element",
        elements=[
            Decimal("3.85"),
            Decimal("3.42"),
            Decimal("2.98"),
            Decimal("3.67"),
            Decimal("2.76"),
            Decimal("3.21"),
            Decimal("3.94"),
            Decimal("2.54"),
        ],
    )

    term_gpa = factory.LazyAttribute(
        lambda obj: obj.cumulative_gpa
        + Faker(
            "random_element",
            elements=[
                Decimal("0.15"),
                Decimal("-0.12"),
                Decimal("0.08"),
                Decimal("-0.05"),
            ],
        ),
    )

    total_credit_hours = Faker("random_int", min=12, max=120)

    total_quality_points = factory.LazyAttribute(lambda obj: obj.cumulative_gpa * obj.total_credit_hours)

    class_rank = Faker("random_int", min=1, max=200)

    academic_standing = factory.LazyAttribute(
        lambda obj: (
            "DEAN_LIST"
            if obj.cumulative_gpa >= Decimal("3.5")
            else (
                "GOOD_STANDING"
                if obj.cumulative_gpa >= Decimal("2.0")
                else ("PROBATION" if obj.cumulative_gpa >= Decimal("1.5") else "SUSPENSION")
            )
        ),
    )


class GradeChangeHistoryFactory(DjangoModelFactory):
    """Factory for creating grade change history."""

    class Meta:
        model = GradeChangeHistory

    original_percentage = Faker(
        "random_element",
        elements=[Decimal("82.0"), Decimal("75.5"), Decimal("88.2"), Decimal("91.7")],
    )

    new_percentage = factory.LazyAttribute(
        lambda obj: obj.original_percentage
        + Faker(
            "random_element",
            elements=[Decimal("5.0"), Decimal("-3.0"), Decimal("2.5"), Decimal("-1.5")],
        ),
    )

    original_letter_grade = factory.LazyAttribute(
        lambda obj: (
            "A"
            if obj.original_percentage >= 90
            else ("B" if obj.original_percentage >= 80 else "C" if obj.original_percentage >= 70 else "D")
        ),
    )

    new_letter_grade = factory.LazyAttribute(
        lambda obj: (
            "A"
            if obj.new_percentage >= 90
            else ("B" if obj.new_percentage >= 80 else "C" if obj.new_percentage >= 70 else "D")
        ),
    )

    change_reason = Faker(
        "random_element",
        elements=[
            "Clerical error correction",
            "Late assignment submitted",
            "Extra credit applied",
            "Regrade request approved",
            "Administrative adjustment",
            "Make-up exam completed",
        ],
    )


# Utility factory for creating complete grading scenarios
class GradingScenarioFactory:
    """Factory for creating complete grading scenarios with related data."""

    @classmethod
    def create_standard_grading_system(cls):
        """Create a standard A-F grading system with conversions."""
        scale = GradingScaleFactory(
            name="Standard Letter Grades",
            description="Traditional A-F grading scale",
            minimum_passing_grade=Decimal("60.0"),
        )

        # Create grade conversions for the scale
        grades = [
            ("A+", Decimal("97.0"), Decimal("100.0"), Decimal("4.0")),
            ("A", Decimal("93.0"), Decimal("96.9"), Decimal("4.0")),
            ("A-", Decimal("90.0"), Decimal("92.9"), Decimal("3.7")),
            ("B+", Decimal("87.0"), Decimal("89.9"), Decimal("3.3")),
            ("B", Decimal("83.0"), Decimal("86.9"), Decimal("3.0")),
            ("B-", Decimal("80.0"), Decimal("82.9"), Decimal("2.7")),
            ("C+", Decimal("77.0"), Decimal("79.9"), Decimal("2.3")),
            ("C", Decimal("73.0"), Decimal("76.9"), Decimal("2.0")),
            ("C-", Decimal("70.0"), Decimal("72.9"), Decimal("1.7")),
            ("D+", Decimal("67.0"), Decimal("69.9"), Decimal("1.3")),
            ("D", Decimal("60.0"), Decimal("66.9"), Decimal("1.0")),
            ("F", Decimal("0.0"), Decimal("59.9"), Decimal("0.0")),
        ]

        conversions = []
        for letter, min_pct, max_pct, gpa in grades:
            conversion = GradeConversionFactory(
                grading_scale=scale,
                letter_grade=letter,
                min_percentage=min_pct,
                max_percentage=max_pct,
                gpa_points=gpa,
            )
            conversions.append(conversion)

        return scale, conversions

    @classmethod
    def create_student_grades_for_term(cls, student_profile, term, num_classes=4):
        """Create realistic grades for a student across multiple classes in a term."""
        grades = []

        # Simulate different performance levels
        performance_level = Faker("random_element", elements=["excellent", "good", "average", "struggling"])

        base_performance = {
            "excellent": (90, 98),
            "good": (80, 89),
            "average": (70, 79),
            "struggling": (60, 75),
        }

        min_grade, max_grade = base_performance[performance_level]

        for _i in range(num_classes):
            # Create some variation in performance across classes
            variation = Faker("random_int", min=-5, max=10)
            grade_pct = Faker("random_int", min=min_grade, max=max_grade) + variation
            grade_pct = max(0, min(100, grade_pct))  # Clamp to 0-100

            grade = ClassPartGradeFactory(
                percentage_grade=Decimal(str(grade_pct)),
                is_final=True,
            )
            grades.append(grade)

        # Create GPA record for the term
        total_gpa = sum(g.gpa_points for g in grades) / len(grades)
        gpa_record = GPARecordFactory(
            term_gpa=total_gpa,
            cumulative_gpa=total_gpa,  # Simplified for factory
        )

        return grades, gpa_record
