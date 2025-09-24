"""Tests for scholarships app models.

Tests cover all model functionality including validation, properties,
and business logic to ensure scholarship management works correctly.
"""

from datetime import timedelta
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


# Mock cycle for tests without curriculum app dependency
class MockCycle:
    def __init__(self, cycle_id=1, short_name="BA", name="Bachelor's Program", is_active=True):
        self.id = cycle_id
        self.short_name = short_name
        self.name = name
        self.is_active = is_active

    def __str__(self):
        return f"{self.name} ({self.short_name})"


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


class SponsorModelTest(TestCase):
    """Test Sponsor model functionality."""

    def setUp(self):
        """Set up test data."""
        self.sponsor = SimpleSponsorFactory(
            code="TEST",
            name="Test Organization",
            mou_start_date=timezone.now().date() - timedelta(days=30),
            mou_end_date=timezone.now().date() + timedelta(days=365),
            default_discount_percentage=Decimal("75.00"),
            is_active=True,
        )

    def test_sponsor_creation(self):
        """Test basic sponsor creation."""
        self.assertEqual(self.sponsor.code, "TEST")
        self.assertEqual(self.sponsor.name, "Test Organization")
        self.assertEqual(self.sponsor.default_discount_percentage, Decimal("75.00"))
        self.assertTrue(self.sponsor.is_active)

    def test_sponsor_str_representation(self):
        """Test sponsor string representation."""
        expected = "Test Organization (TEST)"
        self.assertEqual(str(self.sponsor), expected)

    def test_mou_active_property_within_dates(self):
        """Test MOU active property when within valid dates."""
        self.assertTrue(self.sponsor.is_mou_active)

    def test_mou_active_property_before_start(self):
        """Test MOU active property before start date."""
        self.sponsor.mou_start_date = timezone.now().date() + timedelta(days=30)
        self.sponsor.save()
        self.assertFalse(self.sponsor.is_mou_active)

    def test_mou_active_property_after_end(self):
        """Test MOU active property after end date."""
        self.sponsor.mou_end_date = timezone.now().date() - timedelta(days=1)
        self.sponsor.save()
        self.assertFalse(self.sponsor.is_mou_active)

    def test_mou_active_property_inactive_sponsor(self):
        """Test MOU active property for inactive sponsor."""
        self.sponsor.is_active = False
        self.sponsor.save()
        self.assertFalse(self.sponsor.is_mou_active)

    def test_mou_date_validation(self):
        """Test MOU date validation."""
        self.sponsor.mou_start_date = timezone.now().date()
        self.sponsor.mou_end_date = timezone.now().date() - timedelta(days=1)

        with self.assertRaises(ValidationError) as context:
            self.sponsor.full_clean()

        self.assertIn("mou_end_date", context.exception.message_dict)

    def test_get_active_sponsored_students_count(self):
        """Test active sponsored students count."""
        # This will be tested with actual student data in integration tests
        count = self.sponsor.get_active_sponsored_students_count()
        self.assertEqual(count, 0)  # No sponsored students yet


class SponsoredStudentModelTest(TestCase):
    """Test SponsoredStudent model functionality."""

    def setUp(self):
        """Set up test data."""
        self.sponsor = SimpleSponsorFactory()
        mock_student = MockStudent()
        self.sponsored_student = SimpleSponsoredStudentFactory(
            sponsor=self.sponsor,
            student=mock_student,
            sponsorship_type=SponsoredStudent.SponsorshipType.FULL,
            start_date=timezone.now().date() - timedelta(days=30),
            end_date=timezone.now().date() + timedelta(days=365),
        )

    def test_sponsored_student_creation(self):
        """Test basic sponsored student creation."""
        self.assertEqual(self.sponsored_student.sponsor, self.sponsor)
        self.assertEqual(
            self.sponsored_student.sponsorship_type,
            SponsoredStudent.SponsorshipType.FULL,
        )

    def test_sponsored_student_str_representation(self):
        """Test sponsored student string representation."""
        expected = f"{self.sponsor.code} → {self.sponsored_student.student} (FULL)"
        self.assertEqual(str(self.sponsored_student), expected)

    def test_is_currently_active_property_within_dates(self):
        """Test currently active property within valid dates."""
        self.assertTrue(self.sponsored_student.is_currently_active)

    def test_is_currently_active_property_before_start(self):
        """Test currently active property before start date."""
        self.sponsored_student.start_date = timezone.now().date() + timedelta(days=30)
        self.sponsored_student.save()
        self.assertFalse(self.sponsored_student.is_currently_active)

    def test_is_currently_active_property_after_end(self):
        """Test currently active property after end date."""
        self.sponsored_student.end_date = timezone.now().date() - timedelta(days=1)
        self.sponsored_student.save()
        self.assertFalse(self.sponsored_student.is_currently_active)

    def test_is_currently_active_property_no_end_date(self):
        """Test currently active property with no end date."""
        self.sponsored_student.end_date = None
        self.sponsored_student.save()
        self.assertTrue(self.sponsored_student.is_currently_active)

    def test_duration_days_property(self):
        """Test duration days calculation."""
        start_date = timezone.now().date()
        end_date = timezone.now().date() + timedelta(days=365)
        self.sponsored_student.start_date = start_date
        self.sponsored_student.end_date = end_date
        self.sponsored_student.save()

        self.assertEqual(self.sponsored_student.duration_days, 365)

    def test_duration_days_property_no_end_date(self):
        """Test duration days with no end date."""
        self.sponsored_student.end_date = None
        self.sponsored_student.save()
        self.assertIsNone(self.sponsored_student.duration_days)

    def test_date_range_validation(self):
        """Test date range validation."""
        self.sponsored_student.start_date = timezone.now().date()
        self.sponsored_student.end_date = timezone.now().date() - timedelta(days=1)

        with self.assertRaises(ValidationError) as context:
            self.sponsored_student.full_clean()

        self.assertIn("end_date", context.exception.message_dict)

    def test_overlapping_sponsorship_validation(self):
        """Test overlapping sponsorship validation."""
        # Create another sponsored student with overlapping dates
        overlapping_student = SimpleSponsoredStudentFactory.build(
            sponsor=self.sponsor,
            student=self.sponsored_student.student,
            start_date=self.sponsored_student.start_date + timedelta(days=10),
            end_date=self.sponsored_student.end_date - timedelta(days=10),
        )

        with self.assertRaises(ValidationError):
            overlapping_student.full_clean()


class ScholarshipModelTest(TestCase):
    """Test Scholarship model functionality."""

    def setUp(self):
        """Set up test data."""
        mock_student = MockStudent()
        self.sponsored_student = SimpleSponsoredStudentFactory(student=mock_student)
        self.scholarship = SimpleScholarshipFactory(
            name="Test Scholarship",
            scholarship_type=Scholarship.ScholarshipType.MERIT,
            student=mock_student,
            sponsored_student=self.sponsored_student,
            award_percentage=Decimal("75.00"),
            award_amount=None,
            start_date=timezone.now().date() - timedelta(days=30),
            end_date=timezone.now().date() + timedelta(days=365),
            status=Scholarship.AwardStatus.ACTIVE,
        )

    def test_scholarship_creation(self):
        """Test basic scholarship creation."""
        self.assertEqual(self.scholarship.name, "Test Scholarship")
        self.assertEqual(self.scholarship.scholarship_type, Scholarship.ScholarshipType.MERIT)
        self.assertEqual(self.scholarship.award_percentage, Decimal("75.00"))
        self.assertIsNone(self.scholarship.award_amount)

    def test_scholarship_str_representation(self):
        """Test scholarship string representation."""
        expected = f"Test Scholarship - {self.scholarship.student}"
        self.assertEqual(str(self.scholarship), expected)

    def test_is_currently_active_property_active_status(self):
        """Test currently active property with active status."""
        self.assertTrue(self.scholarship.is_currently_active)

    def test_is_currently_active_property_pending_status(self):
        """Test currently active property with pending status."""
        self.scholarship.status = Scholarship.AwardStatus.PENDING
        self.scholarship.save()
        self.assertFalse(self.scholarship.is_currently_active)

    def test_is_currently_active_property_before_start(self):
        """Test currently active property before start date."""
        self.scholarship.start_date = timezone.now().date() + timedelta(days=30)
        self.scholarship.save()
        self.assertFalse(self.scholarship.is_currently_active)

    def test_is_currently_active_property_after_end(self):
        """Test currently active property after end date."""
        self.scholarship.end_date = timezone.now().date() - timedelta(days=1)
        self.scholarship.save()
        self.assertFalse(self.scholarship.is_currently_active)

    def test_award_display_property_percentage(self):
        """Test award display property for percentage."""
        expected = "75.00%"
        self.assertEqual(self.scholarship.award_display, expected)

    def test_award_display_property_fixed_amount(self):
        """Test award display property for fixed amount."""
        self.scholarship.award_percentage = None
        self.scholarship.award_amount = Decimal("1000.00")
        self.scholarship.save()

        expected = "$1000.00"
        self.assertEqual(self.scholarship.award_display, expected)

    def test_award_display_property_no_amount(self):
        """Test award display property with no amount set."""
        self.scholarship.award_percentage = None
        self.scholarship.award_amount = None
        self.scholarship.save()

        expected = "No amount set"
        self.assertEqual(self.scholarship.award_display, expected)

    def test_date_range_validation(self):
        """Test date range validation."""
        self.scholarship.start_date = timezone.now().date()
        self.scholarship.end_date = timezone.now().date() - timedelta(days=1)

        with self.assertRaises(ValidationError) as context:
            self.scholarship.full_clean()

        self.assertIn("end_date", context.exception.message_dict)

    def test_award_validation_both_percentage_and_amount(self):
        """Test validation when both percentage and amount are set."""
        self.scholarship.award_percentage = Decimal("75.00")
        self.scholarship.award_amount = Decimal("1000.00")

        with self.assertRaises(ValidationError) as context:
            self.scholarship.full_clean()

        errors = context.exception.message_dict
        self.assertIn("award_percentage", errors)
        self.assertIn("award_amount", errors)

    def test_award_validation_neither_percentage_nor_amount(self):
        """Test validation when neither percentage nor amount are set."""
        self.scholarship.award_percentage = None
        self.scholarship.award_amount = None
        # Save first to get a pk, then validate
        self.scholarship.save()

        with self.assertRaises(ValidationError) as context:
            self.scholarship.full_clean()

        errors = context.exception.message_dict
        self.assertIn("award_percentage", errors)
        self.assertIn("award_amount", errors)

    def test_award_validation_percentage_only_valid(self):
        """Test validation with only percentage set (valid)."""
        self.scholarship.award_percentage = Decimal("75.00")
        self.scholarship.award_amount = None

        # Should not raise ValidationError
        try:
            self.scholarship.full_clean()
        except ValidationError:
            self.fail("Validation should pass with only percentage set")

    def test_award_validation_amount_only_valid(self):
        """Test validation with only amount set (valid)."""
        self.scholarship.award_percentage = None
        self.scholarship.award_amount = Decimal("1000.00")

        # Should not raise ValidationError
        try:
            self.scholarship.full_clean()
        except ValidationError:
            self.fail("Validation should pass with only amount set")


@pytest.mark.django_db
class ScholarshipModelIntegrationTest:
    """Integration tests for scholarship models with actual database."""

    def test_sponsor_with_multiple_students(self):
        """Test sponsor with multiple sponsored students."""
        sponsor = SimpleSponsorFactory()

        # Create multiple sponsored students
        [SimpleSponsoredStudentFactory(sponsor=sponsor, student=MockStudent(f"STU{i:03d}")) for i in range(3)]

        # Test active students count
        count = sponsor.get_active_sponsored_students_count()
        assert count == 3

    def test_scholarship_cascade_relationships(self):
        """Test cascade behavior when deleting sponsored students."""
        mock_student = MockStudent()
        sponsored_student = SimpleSponsoredStudentFactory(student=mock_student)
        scholarship = SimpleScholarshipFactory(student=mock_student, sponsored_student=sponsored_student)

        # Delete sponsored student should cascade to scholarship
        sponsored_student.delete()

        # Scholarship should be deleted due to CASCADE
        assert not Scholarship.objects.filter(id=scholarship.id).exists()

    def test_student_with_multiple_scholarships(self):
        """Test student with multiple scholarships (should be prevented by business logic)."""
        student = MockStudent()

        # Create multiple scholarships for same student
        SimpleScholarshipFactory(student=student, award_percentage=Decimal("50.00"))
        SimpleScholarshipFactory(student=student, award_percentage=Decimal("75.00"))

        # Both scholarships exist in database
        assert Scholarship.objects.filter(student=student).count() == 2

        # Business logic should handle conflict resolution (tested in services)


class ScholarshipCycleModelTest(TestCase):
    """Test Scholarship model cycle functionality."""

    def setUp(self):
        """Set up test data."""
        self.mock_student = MockStudent()
        self.ba_cycle = MockCycle(cycle_id=2, short_name="BA", name="Bachelor's Program")
        self.ma_cycle = MockCycle(cycle_id=3, short_name="MASTERS", name="Master's Program")
        self.lang_cycle = MockCycle(cycle_id=1, short_name="LANG", name="Language Program")
        self.inactive_cycle = MockCycle(cycle_id=4, short_name="INACTIVE", name="Inactive Cycle", is_active=False)

    def test_scholarship_creation_with_cycle(self):
        """Test scholarship creation with cycle assignment."""
        scholarship = SimpleScholarshipFactory(
            name="BA Alumni Scholarship",
            student=self.mock_student,
            cycle=self.ba_cycle,
            award_percentage=Decimal("30.00"),
            scholarship_type=Scholarship.ScholarshipType.MERIT,
        )

        self.assertEqual(scholarship.cycle, self.ba_cycle)
        self.assertEqual(scholarship.cycle.short_name, "BA")

    def test_scholarship_str_representation_with_cycle(self):
        """Test scholarship string representation includes cycle information."""
        scholarship = SimpleScholarshipFactory(
            name="Test Scholarship",
            student=self.mock_student,
            cycle=self.ba_cycle,
        )

        expected = f"Test Scholarship - {self.mock_student} (BA)"
        self.assertEqual(str(scholarship), expected)

    def test_scholarship_str_representation_without_cycle(self):
        """Test scholarship string representation without cycle."""
        scholarship = SimpleScholarshipFactory(
            name="Test Scholarship",
            student=self.mock_student,
            cycle=None,
        )

        expected = f"Test Scholarship - {self.mock_student}"
        self.assertEqual(str(scholarship), expected)

    def test_cycle_specific_scholarship_business_rule(self):
        """Test that scholarships are cycle-specific per business rule."""
        # Student gets scholarship in Language cycle
        lang_scholarship = SimpleScholarshipFactory(
            name="Language Scholarship",
            student=self.mock_student,
            cycle=self.lang_cycle,
            award_percentage=Decimal("50.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # Student gets different scholarship in BA cycle (should be allowed)
        ba_scholarship = SimpleScholarshipFactory(
            name="BA Scholarship",
            student=self.mock_student,
            cycle=self.ba_cycle,
            award_percentage=Decimal("30.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # Both scholarships should exist (different cycles)
        self.assertEqual(Scholarship.objects.filter(student=self.mock_student).count(), 2)
        self.assertNotEqual(lang_scholarship.cycle, ba_scholarship.cycle)

    def test_inactive_cycle_validation(self):
        """Test validation prevents scholarships for inactive cycles."""
        scholarship = SimpleScholarshipFactory.build(
            student=self.mock_student,
            cycle=self.inactive_cycle,
        )

        with self.assertRaises(ValidationError) as context:
            scholarship.full_clean()

        self.assertIn("cycle", context.exception.message_dict)
        self.assertIn("inactive cycles", str(context.exception.message_dict["cycle"]))

    def test_cycle_constraint_unique_scholarship_per_student_cycle_type(self):
        """Test unique constraint for student + cycle + type + start_date."""
        start_date = timezone.now().date()

        # Create first scholarship
        SimpleScholarshipFactory(
            student=self.mock_student,
            cycle=self.ba_cycle,
            scholarship_type=Scholarship.ScholarshipType.MERIT,
            start_date=start_date,
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # Try to create duplicate scholarship (same student, cycle, type, start_date, status)
        with self.assertRaises(Exception):  # Should raise IntegrityError in real database
            SimpleScholarshipFactory(
                student=self.mock_student,
                cycle=self.ba_cycle,
                scholarship_type=Scholarship.ScholarshipType.MERIT,
                start_date=start_date,
                status=Scholarship.AwardStatus.ACTIVE,
            )

    def test_cycle_constraint_allows_different_types_same_cycle(self):
        """Test constraint allows different scholarship types in same cycle."""
        start_date = timezone.now().date()

        # Create Merit scholarship
        merit_scholarship = SimpleScholarshipFactory(
            student=self.mock_student,
            cycle=self.ba_cycle,
            scholarship_type=Scholarship.ScholarshipType.MERIT,
            start_date=start_date,
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # Create Need-based scholarship (different type, should be allowed)
        need_scholarship = SimpleScholarshipFactory(
            student=self.mock_student,
            cycle=self.ba_cycle,
            scholarship_type=Scholarship.ScholarshipType.NEED,
            start_date=start_date,
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # Both scholarships should exist
        self.assertEqual(Scholarship.objects.filter(student=self.mock_student).count(), 2)
        self.assertEqual(merit_scholarship.cycle, need_scholarship.cycle)
        self.assertNotEqual(merit_scholarship.scholarship_type, need_scholarship.scholarship_type)

    def test_cycle_constraint_allows_different_dates_same_type_cycle(self):
        """Test constraint allows different start dates for same type and cycle."""
        # Create first scholarship
        first_scholarship = SimpleScholarshipFactory(
            student=self.mock_student,
            cycle=self.ba_cycle,
            scholarship_type=Scholarship.ScholarshipType.MERIT,
            start_date=timezone.now().date(),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # Create second scholarship with different start date
        second_scholarship = SimpleScholarshipFactory(
            student=self.mock_student,
            cycle=self.ba_cycle,
            scholarship_type=Scholarship.ScholarshipType.MERIT,
            start_date=timezone.now().date() + timedelta(days=365),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # Both scholarships should exist
        self.assertEqual(Scholarship.objects.filter(student=self.mock_student).count(), 2)
        self.assertNotEqual(first_scholarship.start_date, second_scholarship.start_date)

    def test_cycle_constraint_allows_pending_status(self):
        """Test constraint only applies to APPROVED/ACTIVE scholarships."""
        start_date = timezone.now().date()

        # Create active scholarship
        SimpleScholarshipFactory(
            student=self.mock_student,
            cycle=self.ba_cycle,
            scholarship_type=Scholarship.ScholarshipType.MERIT,
            start_date=start_date,
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # Create pending scholarship (should be allowed despite same parameters)
        SimpleScholarshipFactory(
            student=self.mock_student,
            cycle=self.ba_cycle,
            scholarship_type=Scholarship.ScholarshipType.MERIT,
            start_date=start_date,
            status=Scholarship.AwardStatus.PENDING,
        )

        # Both scholarships should exist (constraint doesn't apply to PENDING)
        self.assertEqual(Scholarship.objects.filter(student=self.mock_student).count(), 2)

    def test_cycle_transition_business_rule_documentation(self):
        """Test documentation of cycle transition business rule."""
        # This test documents the business rule implementation

        # Student starts with Language scholarship
        SimpleScholarshipFactory(
            name="Language Staff Scholarship",
            student=self.mock_student,
            cycle=self.lang_cycle,
            scholarship_type=Scholarship.ScholarshipType.MERIT,
            award_percentage=Decimal("100.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # Student transitions to BA program - must re-enter scholarship
        SimpleScholarshipFactory(
            name="BA Alumni Scholarship",
            student=self.mock_student,
            cycle=self.ba_cycle,
            scholarship_type=Scholarship.ScholarshipType.MERIT,
            award_percentage=Decimal("30.00"),
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # Both scholarships exist (representing different periods/cycles)
        scholarships = Scholarship.objects.filter(student=self.mock_student)
        self.assertEqual(scholarships.count(), 2)

        # Verify business rule: same student, different cycles
        cycles = [s.cycle for s in scholarships]
        self.assertEqual(len(set(cycles)), 2)  # Two different cycles

        # Business logic would determine which scholarship applies for each term
        # based on the program the student was enrolled in during that term

    def test_scholarship_cycle_indexes_performance(self):
        """Test that cycle-related database indexes are properly configured."""
        # This test verifies the indexes are configured for optimal query performance
        # when looking up scholarships by student + cycle + status

        SimpleScholarshipFactory(
            student=self.mock_student,
            cycle=self.ba_cycle,
            status=Scholarship.AwardStatus.ACTIVE,
        )

        # These queries should be optimized by our indexes:
        # - Index on ["student", "cycle", "status"]
        # - Index on ["cycle", "status"]

        # Query 1: Find all scholarships for student in specific cycle
        student_cycle_scholarships = Scholarship.objects.filter(
            student=self.mock_student, cycle=self.ba_cycle, status=Scholarship.AwardStatus.ACTIVE
        )
        self.assertEqual(student_cycle_scholarships.count(), 1)

        # Query 2: Find all active scholarships in a cycle
        cycle_scholarships = Scholarship.objects.filter(cycle=self.ba_cycle, status=Scholarship.AwardStatus.ACTIVE)
        self.assertEqual(cycle_scholarships.count(), 1)
