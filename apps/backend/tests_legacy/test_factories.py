"""Sample tests demonstrating the SQLite test factories.

This file shows how to use the factory_boy factories with the SQLite TEST environment
for fast, deterministic testing.
"""

from django.test import TestCase

from apps.enrollment.models import ClassHeaderEnrollment
from apps.people.models import StudentProfile
from tests.utils import (
    create_basic_test_environment,
    create_bulk_students,
    create_full_class_enrollment,
    create_ieap_class_scenario,
    create_student_enrollment_scenario,
)


class TestFactoriesBasic(TestCase):
    """Test basic factory functionality."""

    def test_basic_environment_creation(self):
        """Test creating basic test environment."""
        env = create_basic_test_environment()

        # Verify all components were created
        self.assertIsNotNone(env["admin"])
        self.assertIsNotNone(env["lang_division"])
        self.assertIsNotNone(env["acad_division"])
        self.assertIsNotNone(env["current_term"])
        self.assertIsNotNone(env["eng_course"])
        self.assertIsNotNone(env["math_course"])

        # Verify data integrity
        self.assertEqual(env["lang_division"].short_name, "LANG")
        self.assertEqual(env["acad_division"].short_name, "ACAD")
        self.assertEqual(env["eng_course"].code, "ENG-01")
        self.assertEqual(env["math_course"].code, "MATH-101")

    def test_student_enrollment_scenario(self):
        """Test student enrollment scenario."""
        scenario = create_student_enrollment_scenario()

        student = scenario["student"]

        # Verify student has enrollments
        enrollments = ClassHeaderEnrollment.objects.filter(student=student)
        self.assertEqual(enrollments.count(), 2)

        # Verify enrollment statuses
        active_count = enrollments.filter(status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED).count()
        completed_count = enrollments.filter(status=ClassHeaderEnrollment.EnrollmentStatus.COMPLETED).count()

        self.assertEqual(active_count, 1)
        self.assertEqual(completed_count, 1)

    def test_ieap_class_structure(self):
        """Test IEAP class with multiple sessions."""
        scenario = create_ieap_class_scenario()

        ieap_class = scenario["ieap_class"]

        # Verify class has 2 sessions
        sessions = ieap_class.class_sessions.all()
        self.assertEqual(sessions.count(), 2)

        # Verify each session has parts
        session1 = scenario["session1"]
        session2 = scenario["session2"]

        self.assertEqual(session1.class_parts.count(), 2)
        self.assertEqual(session2.class_parts.count(), 2)

        # Verify part codes are unique within sessions
        session1_codes = list(session1.class_parts.values_list("class_part_code", flat=True))
        session2_codes = list(session2.class_parts.values_list("class_part_code", flat=True))

        self.assertEqual(len(set(session1_codes)), len(session1_codes))  # No duplicates
        self.assertEqual(len(set(session2_codes)), len(session2_codes))  # No duplicates

    def test_bulk_student_creation(self):
        """Test creating multiple students efficiently."""
        students = create_bulk_students(count=25)

        self.assertEqual(len(students), 25)
        self.assertEqual(StudentProfile.objects.count(), 25)

        # Verify all students have unique IDs
        student_ids = [s.student_id for s in students]
        self.assertEqual(len(set(student_ids)), 25)

    def test_full_class_enrollment(self):
        """Test creating a fully enrolled class."""
        scenario = create_full_class_enrollment(class_size=12)

        class_header = scenario["class_header"]
        students = scenario["students"]
        enrollments = scenario["enrollments"]

        self.assertEqual(len(students), 12)
        self.assertEqual(len(enrollments), 12)
        self.assertEqual(class_header.enrollment_count, 12)

        # Verify all enrollments are active
        active_enrollments = ClassHeaderEnrollment.objects.filter(
            class_header=class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
        )
        self.assertEqual(active_enrollments.count(), 12)


class TestFactoriesPerformance(TestCase):
    """Test factory performance for SQLite."""

    def test_rapid_student_creation(self):
        """Test creating students rapidly."""
        import time

        start_time = time.time()
        students = create_bulk_students(count=100)
        end_time = time.time()

        creation_time = end_time - start_time

        self.assertEqual(len(students), 100)
        self.assertLess(creation_time, 2.0)  # Should be very fast with SQLite

    def test_complex_scenario_creation(self):
        """Test creating complex scenarios rapidly."""
        import time

        start_time = time.time()

        # Create multiple complex scenarios
        scenarios = []
        for _i in range(10):
            scenario = create_student_enrollment_scenario()
            scenarios.append(scenario)

        end_time = time.time()
        creation_time = end_time - start_time

        self.assertEqual(len(scenarios), 10)
        self.assertLess(creation_time, 5.0)  # Should be fast


class TestFactoriesIntegration(TestCase):
    """Test factories work with actual model methods."""

    def test_student_profile_methods(self):
        """Test that factory-created students work with model methods."""
        scenario = create_student_enrollment_scenario()
        student = scenario["student"]

        # Test model properties
        self.assertIsNotNone(student.full_name)
        self.assertIsNotNone(student.display_name)
        self.assertTrue(student.is_active)

        # Test enrollment-related methods
        enrollments = student.enrollments.all()
        self.assertEqual(enrollments.count(), 2)

    def test_class_header_enrollment_count(self):
        """Test that class enrollment counts work correctly."""
        scenario = create_full_class_enrollment(class_size=8)
        class_header = scenario["class_header"]

        # Test enrollment count property
        self.assertEqual(class_header.enrollment_count, 8)
        self.assertFalse(class_header.is_full)  # max_enrollment is 8, so exactly full
        self.assertEqual(class_header.available_spots, 0)

    def test_course_relationships(self):
        """Test that course relationships work correctly."""
        env = create_basic_test_environment()

        lang_course = env["eng_course"]
        lang_division = env["lang_division"]

        # Test course-division relationship
        self.assertEqual(lang_course.division, lang_division)
        self.assertTrue(lang_course.is_language)

        # Test reverse relationship
        division_courses = lang_division.courses.all()
        self.assertIn(lang_course, division_courses)
