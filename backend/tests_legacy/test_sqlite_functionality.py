"""Test that demonstrates SQLite functionality for fast testing.

This test shows that the SQLite TEST environment works correctly
and can be used for rapid test development.
"""

from django.test import TestCase

from apps.curriculum.models import Course, Division, Term
from apps.people.models import Person, StudentProfile


class TestSQLiteFunctionality(TestCase):
    """Test basic SQLite functionality with manual model creation."""

    def test_basic_model_creation(self):
        """Test creating models manually in SQLite."""
        # Create division
        division = Division.objects.create(
            name="Language Division",
            short_name="LANG",
            description="English language courses",
            is_active=True,
            display_order=100,
        )

        # Create course
        course = Course.objects.create(
            code="ENG-01",
            title="English Level 1",
            credits=3,
            is_language=True,
            is_active=True,
            division=division,
        )

        # Create term
        Term.objects.create(
            name="2024T1",
            description="Spring Term 2024",
            start_date="2024-01-15",
            end_date="2024-05-15",
            is_active=True,
        )

        # Create person
        person = Person.objects.create(
            family_name="Doe",
            personal_name="John",
            full_name="DOE JOHN",
            school_email="test@pucsr.edu.kh",
            date_of_birth="1990-01-01",
            citizenship="KH",
        )

        # Create student
        student = StudentProfile.objects.create(
            person=person,
            student_id=1,
            current_status="ACTIVE",
            study_time_preference="FULL_TIME",
        )

        # Verify all objects were created
        self.assertEqual(Division.objects.count(), 1)
        self.assertEqual(Course.objects.count(), 1)
        self.assertEqual(Term.objects.count(), 1)
        self.assertEqual(Person.objects.count(), 1)
        self.assertEqual(StudentProfile.objects.count(), 1)

        # Verify relationships
        self.assertEqual(course.division, division)
        self.assertEqual(student.person, person)

    def test_sqlite_performance(self):
        """Test SQLite performance for bulk operations."""
        import time

        start_time = time.time()

        # Create division and course once
        Division.objects.create(name="Test Division", short_name="TEST", is_active=True, display_order=100)

        # Create multiple students
        students = []
        for i in range(50):
            person = Person.objects.create(
                family_name=f"Student{i}",
                personal_name="Test",
                full_name=f"STUDENT{i} TEST",
                school_email=f"test{i}@pucsr.edu.kh",
                date_of_birth="1990-01-01",
                citizenship="KH",
            )
            student = StudentProfile.objects.create(
                person=person,
                student_id=i,
                current_status="ACTIVE",
                study_time_preference="FULL_TIME",
            )
            students.append(student)

        end_time = time.time()
        creation_time = end_time - start_time

        self.assertEqual(len(students), 50)
        self.assertEqual(StudentProfile.objects.count(), 50)
        self.assertLess(creation_time, 1.0)  # Should be very fast

    def test_sqlite_isolation(self):
        """Test that each test gets isolated database."""
        # This test should see empty database despite previous test
        self.assertEqual(Division.objects.count(), 0)
        self.assertEqual(Person.objects.count(), 0)
        self.assertEqual(StudentProfile.objects.count(), 0)


class TestSQLiteVsPostgreSQL(TestCase):
    """Test differences between SQLite and PostgreSQL."""

    def test_sqlite_constraints(self):
        """Test that basic constraints work in SQLite."""
        Division.objects.create(name="Test Division", short_name="TEST", is_active=True, display_order=100)

        # Test unique constraint
        with self.assertRaises(Exception):
            Division.objects.create(
                name="Another Division",
                short_name="TEST",  # Same short_name should fail
                is_active=True,
                display_order=200,
            )
