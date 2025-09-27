"""Tests for unified scholarship service handling NGO and non-NGO scholarships."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.test import TestCase
from django.utils import timezone

from apps.scholarships.models import PaymentMode, Scholarship
from apps.scholarships.services import UnifiedScholarshipService
from apps.scholarships.tests.test_factories import (
    SimpleScholarshipFactory,
    SimpleSponsoredStudentFactory,
    SimpleSponsorFactory,
)


class MockTerm:
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date
        self.name = f"Term {start_date} to {end_date}"


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
class UnifiedScholarshipServiceTest(TestCase):
    """Test UnifiedScholarshipService functionality."""

    def setUp(self):
        """Set up test data."""
        self.student = MockStudent("TEST001")
        self.today = timezone.now().date()

        # Create test term
        self.current_term = MockTerm(
            start_date=self.today - timedelta(days=30), end_date=self.today + timedelta(days=60)
        )

        self.past_term = MockTerm(
            start_date=self.today - timedelta(days=180), end_date=self.today - timedelta(days=90)
        )

    def test_no_scholarship_returns_empty_benefit(self):
        """Test that no scholarship returns empty benefit."""
        benefit = UnifiedScholarshipService.get_scholarship_for_term(self.student, self.current_term)

        self.assertFalse(benefit.has_scholarship)
        self.assertEqual(benefit.discount_percentage, Decimal("0.00"))
        self.assertEqual(benefit.source_type, "NONE")
        self.assertIsNone(benefit.sponsor_code)

    def test_ngo_scholarship_via_sponsored_student(self):
        """Test NGO scholarship detection through SponsoredStudent."""
        # Create active NGO sponsor
        sponsor = SimpleSponsorFactory(
            code="CRST",
            name="Christian Reformed Service Team",
            default_discount_percentage=Decimal("75.00"),
            payment_mode=PaymentMode.DIRECT,
            is_active=True,
        )

        # Create sponsored student relationship
        SimpleSponsoredStudentFactory(
            sponsor=sponsor,
            student=self.student,
            start_date=self.today - timedelta(days=60),
            end_date=None,  # Ongoing
        )

        # Get scholarship benefit
        benefit = UnifiedScholarshipService.get_scholarship_for_term(self.student, self.current_term)

        self.assertTrue(benefit.has_scholarship)
        self.assertEqual(benefit.discount_percentage, Decimal("75.00"))
        self.assertEqual(benefit.source_type, "NGO")
        self.assertEqual(benefit.sponsor_code, "CRST")
        self.assertEqual(benefit.payment_mode, PaymentMode.DIRECT)
        self.assertFalse(benefit.requires_bulk_invoice)

    def test_ngo_scholarship_bulk_invoice_mode(self):
        """Test NGO scholarship with bulk invoice payment mode."""
        sponsor = SimpleSponsorFactory(
            code="PLF",
            payment_mode=PaymentMode.BULK_INVOICE,
            default_discount_percentage=Decimal("100.00"),
            billing_cycle="TERM",
        )

        SimpleSponsoredStudentFactory(sponsor=sponsor, student=self.student)

        benefit = UnifiedScholarshipService.get_scholarship_for_term(self.student, self.current_term)

        self.assertTrue(benefit.requires_bulk_invoice)
        self.assertEqual(benefit.payment_mode, PaymentMode.BULK_INVOICE)

    def test_non_ngo_scholarship_individual(self):
        """Test non-NGO individual scholarship."""
        SimpleScholarshipFactory(
            student=self.student,
            sponsored_student=None,  # Not linked to NGO
            award_percentage=Decimal("50.00"),
            status=Scholarship.AwardStatus.ACTIVE,
            start_date=self.today - timedelta(days=60),
            end_date=None,
        )

        benefit = UnifiedScholarshipService.get_scholarship_for_term(self.student, self.current_term)

        self.assertTrue(benefit.has_scholarship)
        self.assertEqual(benefit.discount_percentage, Decimal("50.00"))
        self.assertEqual(benefit.source_type, "NON_NGO")
        self.assertIsNone(benefit.sponsor_code)
        self.assertEqual(benefit.payment_mode, PaymentMode.DIRECT)

    def test_temporal_validation_past_scholarship_not_applied(self):
        """Test that past scholarships don't apply to current term."""
        # Create scholarship that ended before current term
        SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("75.00"),
            status=Scholarship.AwardStatus.ACTIVE,
            start_date=self.today - timedelta(days=200),
            end_date=self.today - timedelta(days=100),  # Ended in the past
        )

        benefit = UnifiedScholarshipService.get_scholarship_for_term(self.student, self.current_term)

        self.assertFalse(benefit.has_scholarship)
        self.assertIn("No non-NGO scholarship found", benefit.notes)

    def test_temporal_validation_future_scholarship_not_applied(self):
        """Test that future scholarships don't apply to past term."""
        # Create scholarship starting in the future
        SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("50.00"),
            status=Scholarship.AwardStatus.APPROVED,
            start_date=self.today + timedelta(days=90),  # Starts in future
            end_date=None,
        )

        benefit = UnifiedScholarshipService.get_scholarship_for_term(
            self.student,
            self.past_term,  # Check past term
        )

        self.assertFalse(benefit.has_scholarship)

    def test_ngo_takes_precedence_over_non_ngo(self):
        """Test that NGO scholarships are checked first."""
        # Create both NGO and non-NGO scholarships
        sponsor = SimpleSponsorFactory(default_discount_percentage=Decimal("60.00"))
        SimpleSponsoredStudentFactory(sponsor=sponsor, student=self.student)

        SimpleScholarshipFactory(
            student=self.student,
            award_percentage=Decimal("80.00"),  # Higher than NGO
            status=Scholarship.AwardStatus.ACTIVE,
        )

        benefit = UnifiedScholarshipService.get_scholarship_for_term(self.student, self.current_term)

        # Should get NGO scholarship (checked first)
        self.assertEqual(benefit.source_type, "NGO")
        self.assertEqual(benefit.discount_percentage, Decimal("60.00"))

    def test_inactive_sponsor_not_applied(self):
        """Test that inactive sponsor scholarships are not applied."""
        sponsor = SimpleSponsorFactory(
            is_active=False,  # Inactive sponsor
            default_discount_percentage=Decimal("100.00"),
        )
        SimpleSponsoredStudentFactory(sponsor=sponsor, student=self.student)

        benefit = UnifiedScholarshipService.get_scholarship_for_term(self.student, self.current_term)

        self.assertFalse(benefit.has_scholarship)
        self.assertIn("NGO sponsor is inactive", benefit.notes)

    def test_mou_validation_for_ngo_scholarships(self):
        """Test MOU date validation for NGO scholarships."""
        # Create sponsor with MOU that doesn't cover current term
        sponsor = SimpleSponsorFactory(
            mou_start_date=self.today - timedelta(days=365),
            mou_end_date=self.today - timedelta(days=100),  # MOU expired
            default_discount_percentage=Decimal("75.00"),
        )
        SimpleSponsoredStudentFactory(
            sponsor=sponsor,
            student=self.student,
            start_date=self.today - timedelta(days=200),  # Started during MOU
            end_date=None,
        )

        benefit = UnifiedScholarshipService.get_scholarship_for_term(self.student, self.current_term)

        self.assertFalse(benefit.has_scholarship)
        self.assertIn("MOU not active during term", benefit.notes)

    def test_calculate_scholarship_discount_percentage(self):
        """Test discount calculation with percentage scholarship."""
        sponsor = SimpleSponsorFactory(default_discount_percentage=Decimal("75.00"), payment_mode=PaymentMode.DIRECT)
        SimpleSponsoredStudentFactory(sponsor=sponsor, student=self.student)

        result = UnifiedScholarshipService.calculate_scholarship_discount(
            self.student, self.current_term, Decimal("1000.00")
        )

        self.assertEqual(result["original_amount"], Decimal("1000.00"))
        self.assertEqual(result["discount_amount"], Decimal("750.00"))
        self.assertEqual(result["final_amount"], Decimal("250.00"))
        self.assertEqual(result["payment_mode"], PaymentMode.DIRECT)
        self.assertFalse(result["requires_bulk_invoice"])

    def test_calculate_scholarship_discount_fixed_amount(self):
        """Test discount calculation with fixed amount scholarship."""
        SimpleScholarshipFactory(
            student=self.student,
            award_percentage=None,
            award_amount=Decimal("800.00"),  # Fixed amount
            status=Scholarship.AwardStatus.ACTIVE,
        )

        result = UnifiedScholarshipService.calculate_scholarship_discount(
            self.student, self.current_term, Decimal("1000.00")
        )

        self.assertEqual(result["discount_amount"], Decimal("800.00"))
        self.assertEqual(result["final_amount"], Decimal("200.00"))

    def test_calculate_scholarship_discount_capped_at_tuition(self):
        """Test that fixed amount discount is capped at tuition amount."""
        SimpleScholarshipFactory(
            student=self.student,
            award_amount=Decimal("1500.00"),  # More than tuition
            status=Scholarship.AwardStatus.ACTIVE,
        )

        result = UnifiedScholarshipService.calculate_scholarship_discount(
            self.student,
            self.current_term,
            Decimal("1000.00"),  # Tuition amount
        )

        # Discount should be capped at tuition amount
        self.assertEqual(result["discount_amount"], Decimal("1000.00"))
        self.assertEqual(result["final_amount"], Decimal("0.00"))

    def test_multiple_ngo_sponsors_highest_discount_wins(self):
        """Test that highest discount wins when student has multiple NGO sponsors."""
        # Create two sponsors with different discounts
        sponsor1 = SimpleSponsorFactory(code="NGO1", default_discount_percentage=Decimal("50.00"))
        sponsor2 = SimpleSponsorFactory(code="NGO2", default_discount_percentage=Decimal("75.00"))

        SimpleSponsoredStudentFactory(sponsor=sponsor1, student=self.student)
        SimpleSponsoredStudentFactory(sponsor=sponsor2, student=self.student)

        benefit = UnifiedScholarshipService.get_scholarship_for_term(self.student, self.current_term)

        # Should get highest discount
        self.assertEqual(benefit.discount_percentage, Decimal("75.00"))
        self.assertEqual(benefit.sponsor_code, "NGO2")
