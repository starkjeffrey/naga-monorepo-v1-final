"""Working tests for scholarships app models.

Uses real StudentProfile instances to avoid foreign key constraint issues.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.scholarships.models import Scholarship, SponsoredStudent
from apps.scholarships.tests.test_factories import (
    SimpleScholarshipFactory,
    SimpleSponsoredStudentFactory,
    SimpleSponsorFactory,
)


@pytest.mark.django_db
class WorkingSponsorTest(TestCase):
    """Test Sponsor model functionality - these work."""

    def test_sponsor_creation(self):
        """Test basic sponsor creation."""
        sponsor = SimpleSponsorFactory(
            code="TEST",
            name="Test Organization",
            default_discount_percentage=Decimal("75.00"),
            is_active=True,
        )
        self.assertEqual(sponsor.code, "TEST")
        self.assertEqual(sponsor.name, "Test Organization")
        self.assertEqual(sponsor.default_discount_percentage, Decimal("75.00"))
        self.assertTrue(sponsor.is_active)

    def test_sponsor_str_representation(self):
        """Test sponsor string representation."""
        sponsor = SimpleSponsorFactory(code="STR", name="String Test")
        expected = "String Test (STR)"
        self.assertEqual(str(sponsor), expected)

    def test_mou_active_property_within_dates(self):
        """Test MOU active property when within valid dates."""
        sponsor = SimpleSponsorFactory(
            mou_start_date=timezone.now().date() - timedelta(days=30),
            mou_end_date=timezone.now().date() + timedelta(days=365),
            is_active=True,
        )
        self.assertTrue(sponsor.is_mou_active)

    def test_mou_active_property_before_start(self):
        """Test MOU active property before start date."""
        sponsor = SimpleSponsorFactory(
            mou_start_date=timezone.now().date() + timedelta(days=30),
            mou_end_date=timezone.now().date() + timedelta(days=395),
            is_active=True,
        )
        self.assertFalse(sponsor.is_mou_active)

    def test_mou_active_property_after_end(self):
        """Test MOU active property after end date."""
        sponsor = SimpleSponsorFactory(
            mou_start_date=timezone.now().date() - timedelta(days=365),
            mou_end_date=timezone.now().date() - timedelta(days=1),
            is_active=True,
        )
        self.assertFalse(sponsor.is_mou_active)

    def test_mou_active_property_inactive_sponsor(self):
        """Test MOU active property for inactive sponsor."""
        sponsor = SimpleSponsorFactory(
            mou_start_date=timezone.now().date() - timedelta(days=30),
            mou_end_date=timezone.now().date() + timedelta(days=365),
            is_active=False,
        )
        self.assertFalse(sponsor.is_mou_active)

    def test_mou_date_validation(self):
        """Test MOU date validation."""
        sponsor = SimpleSponsorFactory(
            mou_start_date=timezone.now().date(),
            mou_end_date=timezone.now().date() - timedelta(days=1),
        )

        with self.assertRaises(ValidationError) as context:
            sponsor.full_clean()

        self.assertIn("mou_end_date", context.exception.message_dict)

    def test_get_active_sponsored_students_count(self):
        """Test active sponsored students count."""
        sponsor = SimpleSponsorFactory()
        count = sponsor.get_active_sponsored_students_count()
        self.assertEqual(count, 0)  # No sponsored students yet


@pytest.mark.django_db
class WorkingScholarshipValidationTest(TestCase):
    """Test scholarship validation without student dependencies."""

    def test_scholarship_model_validation_both_awards(self):
        """Test scholarship validation when both percentage and amount are set."""
        from apps.people.models import Person, StudentProfile

        # Create a real student profile
        person = Person.objects.create(
            family_name="Student",
            personal_name="Test",
            date_of_birth=date(2000, 1, 1),
        )
        student = StudentProfile.objects.create(
            person=person,
            student_id=1001,
        )

        scholarship = SimpleScholarshipFactory.build(
            student=student,
            award_percentage=Decimal("50.00"),
            award_amount=Decimal("1000.00"),
        )

        with self.assertRaises(ValidationError) as context:
            scholarship.full_clean()

        errors = context.exception.message_dict
        self.assertIn("award_percentage", errors)
        self.assertIn("award_amount", errors)

    def test_scholarship_model_validation_neither_award(self):
        """Test scholarship validation when neither percentage nor amount are set."""
        from apps.people.models import Person, StudentProfile

        # Create a real student profile
        person = Person.objects.create(
            family_name="Student",
            personal_name="Test",
            date_of_birth=date(2000, 1, 1),
        )
        student = StudentProfile.objects.create(
            person=person,
            student_id=1002,
        )

        scholarship = SimpleScholarshipFactory.build(
            student=student,
            award_percentage=None,
            award_amount=None,
        )

        with self.assertRaises(ValidationError) as context:
            scholarship.full_clean()

        errors = context.exception.message_dict
        self.assertIn("award_percentage", errors)
        self.assertIn("award_amount", errors)


@pytest.mark.django_db
class WorkingScholarshipBasicTest(TestCase):
    """Test basic scholarship functionality with real students."""

    def test_scholarship_creation_percentage(self):
        """Test creating a percentage-based scholarship."""
        from apps.people.models import Person, StudentProfile

        # Create a real student profile
        person = Person.objects.create(
            family_name="Student",
            personal_name="Merit",
            date_of_birth=date(2000, 1, 1),
        )
        student = StudentProfile.objects.create(
            person=person,
            student_id=2001,
        )

        scholarship = SimpleScholarshipFactory(
            student=student,
            award_percentage=Decimal("75.00"),
            award_amount=None,
            status=Scholarship.AwardStatus.ACTIVE,
        )

        self.assertEqual(scholarship.award_percentage, Decimal("75.00"))
        self.assertIsNone(scholarship.award_amount)
        self.assertEqual(scholarship.status, Scholarship.AwardStatus.ACTIVE)
        self.assertTrue(scholarship.is_currently_active)
        self.assertEqual(scholarship.award_display, "75.00%")

    def test_scholarship_creation_fixed_amount(self):
        """Test creating a fixed amount scholarship."""
        from apps.people.models import Person, StudentProfile

        # Create a real student profile
        person = Person.objects.create(
            family_name="Student",
            personal_name="Monk",
            date_of_birth=date(1995, 1, 1),
        )
        student = StudentProfile.objects.create(
            person=person,
            student_id=3001,
        )

        scholarship = SimpleScholarshipFactory(
            student=student,
            award_percentage=None,
            award_amount=Decimal("800.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        self.assertIsNone(scholarship.award_percentage)
        self.assertEqual(scholarship.award_amount, Decimal("800.00"))
        self.assertEqual(scholarship.award_display, "$800.00")
        self.assertTrue(scholarship.is_currently_active)

    def test_scholarship_string_representation(self):
        """Test scholarship string representation."""
        from apps.people.models import Person, StudentProfile

        # Create a real student profile
        person = Person.objects.create(
            family_name="Test",
            personal_name="String",
            date_of_birth=date(2000, 1, 1),
        )
        student = StudentProfile.objects.create(
            person=person,
            student_id=4001,
        )

        scholarship = SimpleScholarshipFactory(
            student=student,
            name="Test Scholarship",
        )

        expected = f"Test Scholarship - {student}"
        self.assertEqual(str(scholarship), expected)


@pytest.mark.django_db
class WorkingSponsoredStudentTest(TestCase):
    """Test sponsored student functionality with real students."""

    def test_sponsored_student_creation(self):
        """Test creating a sponsored student."""
        from apps.people.models import Person, StudentProfile

        # Create a real student profile
        person = Person.objects.create(
            family_name="Student",
            personal_name="Sponsored",
            date_of_birth=date(2000, 1, 1),
        )
        student = StudentProfile.objects.create(
            person=person,
            student_id=5001,
        )

        sponsor = SimpleSponsorFactory()
        sponsored_student = SimpleSponsoredStudentFactory(
            sponsor=sponsor,
            student=student,
            sponsorship_type=SponsoredStudent.SponsorshipType.FULL,
        )

        self.assertEqual(sponsored_student.sponsor, sponsor)
        self.assertEqual(sponsored_student.student, student)
        self.assertEqual(sponsored_student.sponsorship_type, SponsoredStudent.SponsorshipType.FULL)
        self.assertTrue(sponsored_student.is_currently_active)

    def test_sponsored_student_string_representation(self):
        """Test sponsored student string representation."""
        from apps.people.models import Person, StudentProfile

        # Create a real student profile
        person = Person.objects.create(
            family_name="Sponsored",
            personal_name="String",
            date_of_birth=date(2000, 1, 1),
        )
        student = StudentProfile.objects.create(
            person=person,
            student_id=6001,
        )

        sponsor = SimpleSponsorFactory(code="STRTEST")
        sponsored_student = SimpleSponsoredStudentFactory(
            sponsor=sponsor,
            student=student,
            sponsorship_type=SponsoredStudent.SponsorshipType.PARTIAL,
        )

        expected = f"STRTEST → {student} (PARTIAL)"
        self.assertEqual(str(sponsored_student), expected)
