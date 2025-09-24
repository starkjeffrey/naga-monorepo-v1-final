"""Tests for academic progression builder service.

Tests the detection algorithms, confidence scoring, and journey building
functionality of the progression system.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.test import TestCase

from apps.curriculum.models import Course, Major, Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.enrollment.models_progression import (
    AcademicJourney,
)
from apps.enrollment.progression_builder import ProgressionBuilder
from apps.people.models import Person, StudentProfile
from apps.scheduling.models import ClassHeader


@pytest.mark.django_db
class TestProgressionBuilder(TestCase):
    """Test progression builder functionality."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        # Create test person and student
        cls.person = Person.objects.create(
            personal_name="Test",
            family_name="Student",
            full_name="Test Student",
            date_of_birth=date(2000, 1, 1),
        )
        cls.student = StudentProfile.objects.create(
            person=cls.person,
            student_id="12345",
        )

        # Create majors
        cls.ieap_major = Major.objects.create(
            code="IEAP",
            name="Intensive English for Academic Purposes",
            major_type=Major.MajorType.LANGUAGE,
        )
        cls.ir_major = Major.objects.create(
            code="IR",
            name="International Relations",
            major_type=Major.MajorType.MAJOR,
        )
        cls.business_major = Major.objects.create(
            code="BUS",
            name="Business Administration",
            major_type=Major.MajorType.MAJOR,
        )

        # Create terms
        cls.term1 = Term.objects.create(
            code="2020-1",
            name="Spring 2020",
            start_date=date(2020, 1, 1),
            end_date=date(2020, 5, 1),
        )
        cls.term2 = Term.objects.create(
            code="2020-2",
            name="Fall 2020",
            start_date=date(2020, 9, 1),
            end_date=date(2020, 12, 15),
        )
        cls.term3 = Term.objects.create(
            code="2021-1",
            name="Spring 2021",
            start_date=date(2021, 1, 1),
            end_date=date(2021, 5, 1),
        )

        # Create courses
        cls.ieap1 = Course.objects.create(
            code="IEAP-101",
            name="IEAP Level 1",
            credits=Decimal("3.0"),
        )
        cls.ieap2 = Course.objects.create(
            code="IEAP-201",
            name="IEAP Level 2",
            credits=Decimal("3.0"),
        )
        cls.ir_course = Course.objects.create(
            code="IR-480",
            name="IR Senior Seminar",
            credits=Decimal("3.0"),
        )
        cls.bus_course = Course.objects.create(
            code="BUS-489",
            name="Business Capstone",
            credits=Decimal("3.0"),
        )

    def setUp(self):
        """Set up for each test."""
        self.builder = ProgressionBuilder()

    def create_enrollment(self, student, course, term, status="COMPLETED"):
        """Helper to create an enrollment."""
        class_header = ClassHeader.objects.create(
            course=course,
            term=term,
            section_id="01",
            class_type=ClassHeader.ClassType.LECTURE,
        )

        return ClassHeaderEnrollment.objects.create(
            student=student,
            class_header=class_header,
            status=status,
            final_grade="A" if status == "COMPLETED" else "",
        )

    def test_detect_language_phase(self):
        """Test language program phase detection."""
        # Create IEAP enrollments
        enrollments = [
            self.create_enrollment(self.student, self.ieap1, self.term1),
            self.create_enrollment(self.student, self.ieap2, self.term2),
        ]

        phase = self.builder.detect_language_phase(enrollments)

        self.assertIsNotNone(phase)
        self.assertEqual(phase["type"], "language")
        self.assertEqual(phase["program"], "Intensive English for Academic Purposes")
        self.assertEqual(phase["final_level"], "2")
        self.assertEqual(phase["terms"], 2)
        self.assertGreaterEqual(phase["confidence"], 0.7)

    def test_detect_major_by_signature_courses(self):
        """Test major detection using signature courses."""
        # Create IR signature course enrollment
        enrollments = [
            self.create_enrollment(self.student, self.ir_course, self.term3),
        ]

        result = self.builder.detect_by_signature_courses(enrollments)

        self.assertIsNotNone(result["major"])
        self.assertEqual(result["major"].name, "International Relations")
        self.assertGreater(result["confidence"], 0)
        self.assertIn("IR-480", result["matches"])

    def test_build_student_journey_complete(self):
        """Test building a complete student journey."""
        # Create a complete journey: IEAP -> BA
        self.create_enrollment(self.student, self.ieap1, self.term1)
        self.create_enrollment(self.student, self.ieap2, self.term2)
        self.create_enrollment(self.student, self.ir_course, self.term3)

        journey = self.builder.build_student_journey(self.student.id)

        self.assertIsInstance(journey, AcademicJourney)
        self.assertEqual(journey.student, self.student)
        self.assertEqual(journey.total_terms_enrolled, 3)
        self.assertGreater(journey.total_credits_earned, 0)
        self.assertEqual(journey.data_source, AcademicJourney.DataSource.LEGACY)

        # Check milestones were created
        milestones = journey.milestones.all()
        self.assertGreater(milestones.count(), 0)

    def test_confidence_scoring(self):
        """Test confidence scoring for uncertain data."""
        # Create only one enrollment (insufficient data)
        self.create_enrollment(self.student, self.ir_course, self.term1)

        journey = self.builder.build_student_journey(self.student.id)

        # Should have lower confidence with limited data
        self.assertLess(journey.confidence_score, Decimal("1.0"))
        self.assertTrue(journey.requires_review)

    def test_no_enrollments_error(self):
        """Test handling of student with no enrollments."""
        empty_student = StudentProfile.objects.create(
            person=Person.objects.create(
                personal_name="Empty",
                family_name="Student",
                full_name="Empty Student",
            ),
            student_id="99999",
        )

        with self.assertRaises(ValueError) as context:
            self.builder.build_student_journey(empty_student.id)

        self.assertIn("No enrollments found", str(context.exception))

    def test_major_change_detection(self):
        """Test detection of major changes."""
        # Create enrollments showing major change from IR to Business
        self.create_enrollment(self.student, self.ir_course, self.term1)
        self.create_enrollment(self.student, self.bus_course, self.term3)

        # This would be enhanced to detect the major change
        # For now, just verify it processes without error
        journey = self.builder.build_student_journey(self.student.id)
        self.assertIsNotNone(journey)


class TestProgressionDetectionStrategies(TestCase):
    """Test individual detection strategies."""

    def setUp(self):
        """Set up test data."""
        self.builder = ProgressionBuilder()

        # Create mock enrollments with different course patterns
        self.ir_enrollments = self._create_mock_enrollments(["IR-480", "POL-405", "LAW-301", "ECON-455"])
        self.bus_enrollments = self._create_mock_enrollments(["BUS-489", "BUS-464", "BUS-465", "ECON-212"])
        self.mixed_enrollments = self._create_mock_enrollments(["ENGL-101", "MATH-102", "HIST-201", "PSYC-101"])

    def _create_mock_enrollments(self, course_codes):
        """Create mock enrollment objects."""
        enrollments = []
        for code in course_codes:
            enrollment = type(
                "MockEnrollment",
                (),
                {"class_header": type("MockHeader", (), {"course": type("MockCourse", (), {"code": code})})},
            )
            enrollments.append(enrollment)
        return enrollments

    def test_signature_course_detection_ir(self):
        """Test IR major detection by signature courses."""
        result = self.builder.detect_by_signature_courses(self.ir_enrollments)

        self.assertEqual(result["count"], 4)  # All 4 are IR signature courses
        self.assertGreaterEqual(result["confidence"], 0.8)

    def test_signature_course_detection_business(self):
        """Test Business major detection by signature courses."""
        result = self.builder.detect_by_signature_courses(self.bus_enrollments)

        self.assertEqual(result["count"], 4)  # All 4 are Business signature courses
        self.assertGreaterEqual(result["confidence"], 0.8)

    def test_no_signature_courses(self):
        """Test handling of enrollments with no signature courses."""
        result = self.builder.detect_by_signature_courses(self.mixed_enrollments)

        self.assertIsNone(result["major"])
        self.assertEqual(result["confidence"], 0)

    def test_course_frequency_detection(self):
        """Test major detection by department frequency."""
        result = self.builder.detect_by_course_frequency(self.bus_enrollments)

        self.assertIsNotNone(result["major"])
        self.assertEqual(result["department"], "BUS")
        self.assertGreater(result["confidence"], 0)

    def test_combine_detection_results(self):
        """Test combining multiple detection strategies."""
        results = [
            {
                "major": self.builder.major_cache.get("International Relations"),
                "confidence": 0.9,
                "strategy": "signature_courses",
            },
            {
                "major": self.builder.major_cache.get("International Relations"),
                "confidence": 0.6,
                "strategy": "course_frequency",
            },
        ]

        combined = self.builder.combine_detection_results(results)

        self.assertIsNotNone(combined["major"])
        self.assertTrue(combined["is_certain"])
        self.assertIn("signature_courses", combined["detection_method"])
