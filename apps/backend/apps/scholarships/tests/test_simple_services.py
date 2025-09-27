"""Simplified tests for scholarships app services.

Tests cover key business logic using simplified mock data.
"""

from decimal import Decimal

import pytest
from django.test import TestCase
from django.utils import timezone

from apps.scholarships.models import Scholarship
from apps.scholarships.tests.test_factories import (
    SimpleScholarshipFactory,
    SimpleSponsoredStudentFactory,
    SimpleSponsorFactory,
)


# Mock student for tests without people app dependency
class MockStudent:
    def __init__(self, student_id="TEST001"):
        self.student_id = student_id
        self.id = 1
        self.person = MockPerson()

    def __str__(self):
        return f"Student {self.student_id}"


class MockPerson:
    def __init__(self, full_name="Test Student"):
        self.full_name = full_name


@pytest.mark.django_db
class SimpleScholarshipTest(TestCase):
    """Test basic scholarship functionality."""

    def setUp(self):
        """Set up test data."""
        self.student = MockStudent("STU001")

    def test_single_scholarship_creation(self):
        """Test creating a single scholarship."""
        scholarship = SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("75.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        self.assertEqual(scholarship.award_percentage, Decimal("75.00"))
        self.assertEqual(scholarship.status, Scholarship.AwardStatus.ACTIVE)
        self.assertTrue(scholarship.is_currently_active)

    def test_multiple_scholarships_for_student(self):
        """Test creating multiple scholarships for same student."""
        SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("50.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )
        SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("75.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # Both should exist in database
        scholarships = Scholarship.objects.filter(student=self.student)
        self.assertEqual(scholarships.count(), 2)

    def test_fixed_amount_scholarship(self):
        """Test fixed amount scholarship."""
        scholarship = SimpleScholarshipFactory(
            student=self.student,
            award_percentage=None,
            award_amount=Decimal("1000.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        self.assertIsNone(scholarship.award_percentage)
        self.assertEqual(scholarship.award_amount, Decimal("1000.00"))
        self.assertEqual(scholarship.award_display, "$1000.00")

    def test_sponsored_student_scholarship(self):
        """Test scholarship linked to sponsored student."""
        sponsor = SimpleSponsorFactory(code="TEST")
        sponsored_student = SimpleSponsoredStudentFactory(
            sponsor=sponsor,
            student=self.student,
        )

        scholarship = SimpleScholarshipFactory(
            student=self.student,
            sponsored_student=sponsored_student,
            award_percentage=Decimal("100.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        self.assertEqual(scholarship.sponsored_student, sponsored_student)
        self.assertEqual(scholarship.student, self.student)
        self.assertTrue(scholarship.is_currently_active)


@pytest.mark.django_db
class SimpleSponsorTest(TestCase):
    """Test basic sponsor functionality."""

    def test_sponsor_creation(self):
        """Test creating a sponsor."""
        sponsor = SimpleSponsorFactory(
            code="TEST",
            name="Test Sponsor",
            default_discount_percentage=Decimal("75.00"),
        )

        self.assertEqual(sponsor.code, "TEST")
        self.assertEqual(sponsor.name, "Test Sponsor")
        self.assertEqual(sponsor.default_discount_percentage, Decimal("75.00"))

    def test_sponsor_with_students(self):
        """Test sponsor with sponsored students."""
        sponsor = SimpleSponsorFactory(code="MULTI")

        # Create multiple sponsored students
        students = []
        for i in range(3):
            student = MockStudent(f"STU{i:03d}")
            students.append(student)
            SimpleSponsoredStudentFactory(
                sponsor=sponsor,
                student=student,
            )

        # Test count
        count = sponsor.get_active_sponsored_students_count()
        self.assertEqual(count, 3)


@pytest.mark.django_db
class SimpleValidationTest(TestCase):
    """Test basic model validation."""

    def test_scholarship_award_validation(self):
        """Test scholarship award validation."""
        student = MockStudent()

        # Should not be able to have both percentage and amount
        with self.assertRaises(Exception):
            scholarship = SimpleScholarshipFactory(
                student=student,
                award_percentage=Decimal("50.00"),
                award_amount=Decimal("1000.00"),
            )
            scholarship.full_clean()

    def test_sponsor_mou_dates(self):
        """Test sponsor MOU date validation."""
        from datetime import timedelta

        sponsor = SimpleSponsorFactory(
            mou_start_date=timezone.now().date(),
            mou_end_date=timezone.now().date() + timedelta(days=365),
        )

        self.assertTrue(sponsor.is_mou_active)

        # Test expired MOU
        sponsor.mou_end_date = timezone.now().date() - timedelta(days=1)
        sponsor.save()
        self.assertFalse(sponsor.is_mou_active)
