"""Comprehensive tests for the curriculum app models.

This test module validates all functionality of the curriculum models
while ensuring they maintain clean architecture principles and support
both language and academic sections of the school.

Test coverage includes:
- Model creation and validation
- Custom methods and properties
- Business logic constraints
- Academic hierarchy relationships
- Course progression logic
- Term validation and cohort tracking
- Prerequisite relationships
- Edge cases and error conditions
"""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from apps.curriculum.models import (
    Course,
    CoursePrerequisite,
    Cycle,
    Division,
    Major,
    Term,
    Textbook,
)

User = get_user_model()


class DivisionModelTest(TestCase):
    """Test Division model functionality."""

    def test_division_creation(self):
        """Test basic division creation."""
        division = Division.objects.create(
            name="Language Division",
            short_name="LANG",
            description="Language instruction division",
            display_order=1,
        )
        assert division.name == "Language Division"
        assert division.short_name == "LANG"
        assert division.is_active
        assert division.display_order == 1

    def test_short_name_uppercase_conversion(self):
        """Test that short names are automatically converted to uppercase."""
        division = Division(name="Academic Division", short_name="acad")
        division.clean()  # Run validation which includes uppercase conversion
        division.save()
        assert division.short_name == "ACAD"

    def test_division_str_representation(self):
        """Test string representation of division."""
        division = Division.objects.create(name="Test Division")
        assert str(division) == "Test Division"

    def test_division_ordering(self):
        """Test division ordering by display_order and name."""
        div1 = Division.objects.create(name="B Division", display_order=2)
        div2 = Division.objects.create(name="A Division", display_order=1)
        div3 = Division.objects.create(name="A Early Division", display_order=1)

        divisions = list(Division.objects.all())
        assert divisions[0] == div2  # display_order 1, name "A Division"
        assert divisions[1] == div3  # display_order 1, name "A Early Division"
        assert divisions[2] == div1  # display_order 2


class CycleModelTest(TestCase):
    """Test Cycle model functionality."""

    def setUp(self):
        """Set up test data."""
        self.division = Division.objects.create(
            name="Academic Division",
            short_name="ACAD",
        )

    def test_cycle_creation(self):
        """Test basic cycle creation."""
        cycle = Cycle.objects.create(
            division=self.division,
            name="Bachelor's Program",
            short_name="BA",
            typical_duration_terms=8,
        )
        assert cycle.division == self.division
        assert cycle.name == "Bachelor's Program"
        assert cycle.short_name == "BA"
        assert cycle.typical_duration_terms == 8

    def test_cycle_str_representation(self):
        """Test string representation of cycle."""
        cycle = Cycle.objects.create(division=self.division, name="Foundation Year")
        expected = f"{self.division.short_name} - Foundation Year"
        assert str(cycle) == expected

    def test_unique_short_name_per_division(self):
        """Test that short names must be unique within a division."""
        Cycle.objects.create(division=self.division, name="Cycle 1", short_name="C1")

        with pytest.raises(IntegrityError):
            Cycle.objects.create(
                division=self.division,
                name="Cycle 2",
                short_name="C1",
            )

    def test_short_name_can_repeat_across_divisions(self):
        """Test that short names can be the same across different divisions."""
        division2 = Division.objects.create(name="Language Division")

        cycle1 = Cycle.objects.create(
            division=self.division,
            name="Foundation",
            short_name="FOUND",
        )
        cycle2 = Cycle.objects.create(
            division=division2,
            name="Foundation",
            short_name="FOUND",
        )

        assert cycle1.short_name == cycle2.short_name


class MajorModelTest(TestCase):
    """Test Major model functionality."""

    def setUp(self):
        """Set up test data."""
        self.division = Division.objects.create(name="Academic Division")
        self.cycle = Cycle.objects.create(
            division=self.division,
            name="Bachelor's Program",
        )

    def test_major_creation(self):
        """Test basic major creation."""
        major = Major.objects.create(
            cycle=self.cycle,
            name="Computer Science",
            short_name="CS",
            code="COMP_SCI",
            total_credits_required=120,
        )
        assert major.cycle == self.cycle
        assert major.name == "Computer Science"
        assert major.short_name == "CS"
        assert major.code == "COMP_SCI"
        assert major.total_credits_required == 120

    def test_major_str_representation(self):
        """Test string representation of major."""
        major = Major.objects.create(cycle=self.cycle, name="Mathematics")
        expected = f"{self.cycle} - Mathematics"
        assert str(major) == expected

    def test_full_hierarchy_name_property(self):
        """Test full hierarchy name property."""
        major = Major.objects.create(cycle=self.cycle, name="Mathematics")
        expected = f"{self.division.name} > {self.cycle.name} > Mathematics"
        assert major.full_hierarchy_name == expected

    def test_unique_code_per_cycle(self):
        """Test that major codes must be unique within a cycle."""
        Major.objects.create(cycle=self.cycle, name="Major 1", code="MAJ1")

        with pytest.raises(IntegrityError):
            Major.objects.create(cycle=self.cycle, name="Major 2", code="MAJ1")

    def test_code_uppercase_conversion(self):
        """Test that codes are automatically converted to uppercase."""
        major = Major(cycle=self.cycle, name="Test Major", code="test_code")
        major.clean()  # Run validation which includes uppercase conversion
        major.save()
        assert major.code == "TEST_CODE"


class TermModelTest(TestCase):
    """Test Term model functionality."""

    def test_term_creation(self):
        """Test basic term creation."""
        term = Term.objects.create(
            code="Fall 2024",
            term_type=Term.TermType.BACHELORS,
            ba_cohort_number=15,
            start_date=datetime.date(2024, 9, 1),
            end_date=datetime.date(2024, 12, 15),
            add_date=datetime.date(2024, 9, 10),
            drop_date=datetime.date(2024, 10, 1),
        )
        assert term.code == "Fall 2024"
        assert term.term_type == Term.TermType.BACHELORS
        assert term.ba_cohort_number == 15

    def test_term_date_validation(self):
        """Test validation of term dates."""
        # End date before start date should fail
        with pytest.raises(ValidationError):
            term = Term(
                code="Invalid Term",
                start_date=datetime.date(2024, 12, 1),
                end_date=datetime.date(2024, 9, 1),
            )
            term.full_clean()

    def test_add_date_validation(self):
        """Test validation of add deadline."""
        # Add date before start date should fail
        with pytest.raises(ValidationError):
            term = Term(
                code="Invalid Term",
                start_date=datetime.date(2024, 9, 1),
                end_date=datetime.date(2024, 12, 1),
                add_date=datetime.date(2024, 8, 1),
            )
            term.full_clean()

    def test_term_str_representation(self):
        """Test string representation of term."""
        term = Term.objects.create(
            code="Spring 2024",
            start_date=datetime.date(2024, 1, 15),
            end_date=datetime.date(2024, 5, 15),
        )
        assert str(term) == "Spring 2024"

    def test_cohort_tracking(self):
        """Test cohort number tracking for different term types."""
        ba_term = Term.objects.create(
            code="BA Term",
            term_type=Term.TermType.BACHELORS,
            ba_cohort_number=10,
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2024, 6, 1),
        )
        ma_term = Term.objects.create(
            code="MA Term",
            term_type=Term.TermType.MASTERS,
            ma_cohort_number=5,
            start_date=datetime.date(2024, 1, 1),
            end_date=datetime.date(2024, 6, 1),
        )

        assert ba_term.ba_cohort_number == 10
        assert ba_term.ma_cohort_number is None
        assert ma_term.ma_cohort_number == 5
        assert ma_term.ba_cohort_number is None


class CourseModelTest(TestCase):
    """Test Course model functionality."""

    def setUp(self):
        """Set up test data."""
        self.division = Division.objects.create(
            name="Academic Division",
            short_name="ACAD",
        )
        self.cycle = Cycle.objects.create(
            division=self.division,
            name="Bachelor's Program",
        )
        self.major = Major.objects.create(
            cycle=self.cycle,
            name="Computer Science",
            code="CS",
        )

    def test_course_creation(self):
        """Test basic course creation."""
        course = Course.objects.create(
            code="CS101",
            title="Introduction to Computer Science",
            short_title="Intro CS",
            cycle=self.cycle,
            credits=3,
            is_language=False,
            recommended_term=1,
        )
        assert course.code == "CS101"
        assert course.title == "Introduction to Computer Science"
        assert course.cycle == self.cycle
        assert course.credits == 3
        assert not course.is_language

    def test_course_str_representation(self):
        """Test string representation of course."""
        course = Course.objects.create(
            code="ENG101",
            title="English Composition",
            cycle=self.cycle,
        )
        assert str(course) == "ENG101: English Composition"

    def test_unique_course_code(self):
        """Test that course codes with overlapping date ranges are not allowed."""
        Course.objects.create(
            code="MATH101",
            title="Algebra",
            cycle=self.cycle,
            start_date=datetime.date(2020, 1, 1),
            end_date=datetime.date(2025, 12, 31),
        )

        # Same code with overlapping dates should fail validation
        with pytest.raises(ValidationError):
            course = Course(
                code="MATH101",
                title="Different Course",
                cycle=self.cycle,
                start_date=datetime.date(2024, 1, 1),
                end_date=datetime.date(2026, 12, 31),
            )
            course.full_clean()

    def test_is_currently_active_property(self):
        """Test is_currently_active property logic."""
        # Active course within date range
        active_course = Course.objects.create(
            code="ACTIVE101",
            title="Active Course",
            cycle=self.cycle,
            start_date=datetime.date(2020, 1, 1),
            is_active=True,
        )
        assert active_course.is_currently_active

        # Inactive course
        inactive_course = Course.objects.create(
            code="INACT101",
            title="Inactive Course",
            cycle=self.cycle,
            is_active=False,
        )
        assert not inactive_course.is_currently_active

        # Course with future start date
        future_course = Course.objects.create(
            code="FUT101",
            title="Future Course",
            cycle=self.cycle,
            start_date=datetime.date(2030, 1, 1),
            is_active=True,
        )
        assert not future_course.is_currently_active

    def test_course_date_validation(self):
        """Test validation of course dates."""
        # End date before start date should fail
        with pytest.raises(ValidationError):
            course = Course(
                code="INV101",
                title="Invalid Course",
                cycle=self.cycle,
                start_date=datetime.date(2024, 12, 1),
                end_date=datetime.date(2024, 6, 1),
            )
            course.full_clean()

    def test_term_progression_validation(self):
        """Test validation of term progression fields."""
        # Latest term before earliest term should fail
        with pytest.raises(ValidationError):
            course = Course(
                code="INV102",
                title="Invalid Course",
                cycle=self.cycle,
                earliest_term=5,
                latest_term=3,
            )
            course.full_clean()

        # Recommended term before earliest term should fail
        with pytest.raises(ValidationError):
            course = Course(
                code="INV103",
                title="Invalid Course",
                cycle=self.cycle,
                earliest_term=3,
                recommended_term=2,
            )
            course.full_clean()

        # Recommended term after latest term should fail
        with pytest.raises(ValidationError):
            course = Course(
                code="INV104",
                title="Invalid Course",
                cycle=self.cycle,
                latest_term=5,
                recommended_term=6,
            )
            course.full_clean()

    def test_major_association(self):
        """Test many-to-many relationship with majors."""
        course = Course.objects.create(
            code="CS201",
            title="Data Structures",
            cycle=self.cycle,
        )

        course.majors.add(self.major)
        assert self.major in course.majors.all()
        assert course in self.major.courses.all()


class TextbookModelTest(TestCase):
    """Test Textbook model functionality."""

    def test_textbook_creation(self):
        """Test basic textbook creation."""
        textbook = Textbook.objects.create(
            title="Introduction to Computer Science",
            author="Jane Doe",
            isbn="978-0123456789",
            publisher="Tech Books",
            edition="3rd",
            year=2023,
        )
        assert textbook.title == "Introduction to Computer Science"
        assert textbook.author == "Jane Doe"
        assert textbook.isbn == "978-0123456789"
        assert textbook.edition == "3rd"
        assert textbook.year == 2023

    def test_textbook_str_representation(self):
        """Test string representation of textbook."""
        textbook = Textbook.objects.create(
            title="Python Programming",
            author="John Smith",
        )
        assert str(textbook) == "Python Programming by John Smith"

    def test_citation_property(self):
        """Test citation property generation."""
        textbook = Textbook.objects.create(
            title="Advanced Mathematics",
            author="Dr. Mathematics",
            edition="2nd",
            publisher="Academic Press",
            year=2022,
        )
        expected_citation = "Dr. Mathematics, Advanced Mathematics, 2nd edition, Academic Press, 2022"
        assert textbook.citation == expected_citation

    def test_citation_with_missing_fields(self):
        """Test citation generation with missing optional fields."""
        textbook = Textbook.objects.create(
            title="Basic Chemistry",
            author="Chemistry Prof",
        )
        expected_citation = "Chemistry Prof, Basic Chemistry"
        assert textbook.citation == expected_citation


class CoursePrerequisiteModelTest(TestCase):
    """Test CoursePrerequisite model functionality."""

    def setUp(self):
        """Set up test data."""
        self.division = Division.objects.create(name="Academic Division")
        self.cycle = Cycle.objects.create(
            division=self.division,
            name="Bachelor's Program",
        )
        self.prerequisite_course = Course.objects.create(
            code="CS101",
            title="Programming Fundamentals",
            cycle=self.cycle,
        )
        self.main_course = Course.objects.create(
            code="CS201",
            title="Data Structures",
            cycle=self.cycle,
        )

    def test_prerequisite_creation(self):
        """Test basic prerequisite creation."""
        prereq = CoursePrerequisite.objects.create(
            prerequisite=self.prerequisite_course,
            course=self.main_course,
            notes="Must pass with C+ or better",
        )
        assert prereq.prerequisite == self.prerequisite_course
        assert prereq.course == self.main_course
        assert prereq.notes == "Must pass with C+ or better"

    def test_prerequisite_str_representation(self):
        """Test string representation of prerequisite."""
        prereq = CoursePrerequisite.objects.create(
            prerequisite=self.prerequisite_course,
            course=self.main_course,
        )
        expected = f"{self.prerequisite_course.code} → {self.main_course.code}"
        assert str(prereq) == expected

    def test_self_prerequisite_validation(self):
        """Test that a course cannot be prerequisite for itself."""
        with pytest.raises(ValidationError):
            prereq = CoursePrerequisite(
                prerequisite=self.main_course,
                course=self.main_course,
            )
            prereq.full_clean()

    def test_unique_prerequisite_relationship(self):
        """Test that prerequisite relationships must be unique."""
        CoursePrerequisite.objects.create(
            prerequisite=self.prerequisite_course,
            course=self.main_course,
        )

        with pytest.raises(IntegrityError):
            CoursePrerequisite.objects.create(
                prerequisite=self.prerequisite_course,
                course=self.main_course,
            )

    def test_prerequisite_date_validation(self):
        """Test validation of prerequisite effective dates."""
        with pytest.raises(ValidationError):
            prereq = CoursePrerequisite(
                prerequisite=self.prerequisite_course,
                course=self.main_course,
                start_date=datetime.date(2024, 12, 1),
                end_date=datetime.date(2024, 6, 1),
            )
            prereq.full_clean()

    def test_prerequisite_reverse_relationships(self):
        """Test reverse relationship access."""
        prereq = CoursePrerequisite.objects.create(
            prerequisite=self.prerequisite_course,
            course=self.main_course,
        )

        # Test reverse relationships
        assert prereq in self.prerequisite_course.enables_courses.all()
        assert prereq in self.main_course.required_prerequisites.all()


class CurriculumIntegrationTest(TestCase):
    """Integration tests for curriculum models working together."""

    def setUp(self):
        """Set up comprehensive test data."""
        # Create organizational hierarchy
        self.lang_division = Division.objects.create(
            name="Language Division",
            short_name="LANG",
            display_order=1,
        )
        self.acad_division = Division.objects.create(
            name="Academic Division",
            short_name="ACAD",
            display_order=2,
        )

        # Create cycles
        self.foundation_cycle = Cycle.objects.create(
            division=self.lang_division,
            name="Foundation Year",
            short_name="FOUND",
        )
        self.bachelor_cycle = Cycle.objects.create(
            division=self.acad_division,
            name="Bachelor's Program",
            short_name="BA",
        )

        # Create majors
        self.cs_major = Major.objects.create(
            cycle=self.bachelor_cycle,
            name="Computer Science",
            code="CS",
            total_credits_required=120,
        )
        self.math_major = Major.objects.create(
            cycle=self.bachelor_cycle,
            name="Mathematics",
            code="MATH",
            total_credits_required=120,
        )

    def test_complete_curriculum_hierarchy(self):
        """Test the complete curriculum hierarchy works correctly."""
        # Verify hierarchy relationships
        assert self.cs_major.cycle == self.bachelor_cycle
        assert self.bachelor_cycle.division == self.acad_division

        # Test full hierarchy name
        expected = "Academic Division > Bachelor's Program > Computer Science"
        assert self.cs_major.full_hierarchy_name == expected

    def test_course_with_multiple_majors(self):
        """Test course associated with multiple majors."""
        course = Course.objects.create(
            code="MATH201",
            title="Calculus I",
            cycle=self.bachelor_cycle,
            credits=4,
            is_language=False,
        )

        # Associate with both majors
        course.majors.add(self.cs_major, self.math_major)

        assert course.majors.count() == 2
        assert course in self.cs_major.courses.all()
        assert course in self.math_major.courses.all()

    def test_language_vs_academic_courses(self):
        """Test distinction between language and academic courses."""
        # Language course
        lang_course = Course.objects.create(
            code="ENG101",
            title="English Fundamentals",
            cycle=self.foundation_cycle,
            is_language=True,
        )

        # Academic course
        acad_course = Course.objects.create(
            code="CS101",
            title="Programming Fundamentals",
            cycle=self.bachelor_cycle,
            is_language=False,
        )

        assert lang_course.is_language
        assert lang_course.cycle.division == self.lang_division
        assert not acad_course.is_language
        assert acad_course.cycle.division == self.acad_division

    def test_prerequisite_chain(self):
        """Test a chain of course prerequisites."""
        # Create course sequence
        cs101 = Course.objects.create(
            code="CS101",
            title="Programming I",
            cycle=self.bachelor_cycle,
        )
        cs102 = Course.objects.create(
            code="CS102",
            title="Programming II",
            cycle=self.bachelor_cycle,
        )
        cs201 = Course.objects.create(
            code="CS201",
            title="Data Structures",
            cycle=self.bachelor_cycle,
        )

        # Create prerequisite chain: CS101 → CS102 → CS201
        CoursePrerequisite.objects.create(prerequisite=cs101, course=cs102)
        CoursePrerequisite.objects.create(prerequisite=cs102, course=cs201)

        # Verify relationships
        assert cs101.enables_courses.count() == 1
        assert cs102.required_prerequisites.count() == 1
        assert cs102.enables_courses.count() == 1
        assert cs201.required_prerequisites.count() == 1
