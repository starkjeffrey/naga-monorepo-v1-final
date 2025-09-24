"""Unit tests for DocumentQuotaService.

Tests the business logic for managing document quotas and tracking usage.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.academic_records.models import DocumentQuota, DocumentRequest, DocumentTypeConfig
from apps.academic_records.services import DocumentQuotaService
from apps.curriculum.models import Major, Term
from apps.enrollment.models import StudentCycleStatus
from apps.finance.models import DocumentExcessFee, InvoiceLineItem
from apps.people.models import Person, StudentProfile

User = get_user_model()


class DocumentQuotaServiceTest(TestCase):
    """Test document quota service business logic."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(email="test@example.com", password="testpass123")

        # Create term
        self.term = Term.objects.create(
            code="2024-1", name="Spring 2024", start_date=date(2024, 1, 1), end_date=date(2024, 5, 31), is_active=True
        )

        # Create major
        self.major = Major.objects.create(code="CS", name="Computer Science", major_type="BACHELOR", is_active=True)

        # Create student
        person = Person.objects.create(
            personal_name="Test",
            family_name="Student",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )

        self.student = StudentProfile.objects.create(
            person=person, student_id="240001", admission_date=date.today(), primary_major=self.major
        )

        # Create document types
        self.transcript = DocumentTypeConfig.objects.create(
            code="TRANS",
            name="Official Transcript",
            category="ACADEMIC",
            unit_cost=3,
            processing_time_hours=48,
            requires_approval=True,
            auto_generate=False,
            is_active=True,
        )

        self.letter = DocumentTypeConfig.objects.create(
            code="LETTER",
            name="Enrollment Letter",
            category="LETTER",
            unit_cost=1,
            processing_time_hours=24,
            requires_approval=False,
            auto_generate=True,
            is_active=True,
        )

        # Create cycle status
        self.cycle_status = StudentCycleStatus.objects.create(
            student=self.student,
            cycle_type=StudentCycleStatus.CycleType.NEW_ENTRY,
            target_program=self.major,
            is_active=True,
        )

        # Create document quota
        self.quota = DocumentQuota.objects.create(
            student=self.student, term=self.term, initial_units=10, used_units=0, is_active=True
        )

        # Create fee configurations
        self.excess_fee_config = DocumentExcessFee.objects.create(
            cycle_type=StudentCycleStatus.CycleType.NEW_ENTRY,
            fee_per_unit=Decimal("5.00"),
            is_active=True,
            created_by=self.user,
        )

    def test_get_quota_summary(self):
        """Test getting quota summary for a student."""
        summary = DocumentQuotaService.get_quota_summary(self.student, self.term)

        self.assertTrue(summary["has_quota"])
        self.assertEqual(summary["total_units"], 10)
        self.assertEqual(summary["used_units"], 0)
        self.assertEqual(summary["remaining_units"], 10)
        self.assertEqual(summary["usage_percentage"], 0.0)
        self.assertFalse(summary["is_expired"])
        self.assertEqual(summary["cycle_type"], "NEW_ENTRY")

    def test_get_quota_summary_no_quota(self):
        """Test quota summary when student has no quota."""
        # Delete quota
        self.quota.delete()

        summary = DocumentQuotaService.get_quota_summary(self.student, self.term)

        self.assertFalse(summary["has_quota"])
        self.assertEqual(summary["total_units"], 0)
        self.assertEqual(summary["used_units"], 0)
        self.assertEqual(summary["remaining_units"], 0)
        self.assertIsNone(summary["cycle_type"])

    def test_get_quota_summary_with_usage(self):
        """Test quota summary with partial usage."""
        # Update usage
        self.quota.used_units = 7
        self.quota.save()

        summary = DocumentQuotaService.get_quota_summary(self.student, self.term)

        self.assertEqual(summary["used_units"], 7)
        self.assertEqual(summary["remaining_units"], 3)
        self.assertEqual(summary["usage_percentage"], 70.0)

    def test_process_document_request_within_quota(self):
        """Test processing document request within quota limits."""
        # Create document request
        request = DocumentRequest.objects.create(
            document_type=self.letter,  # 1 unit
            student=self.student,
            delivery_method="EMAIL",
            requested_by=self.user,
        )

        # Process request
        success, quota_usage, excess_charge = DocumentQuotaService.process_document_request(request)

        self.assertTrue(success)
        self.assertIsNotNone(quota_usage)
        self.assertIsNone(excess_charge)

        # Verify quota usage
        self.assertEqual(quota_usage.quota, self.quota)
        self.assertEqual(quota_usage.units_used, 1)
        self.assertFalse(quota_usage.is_excess)

        # Verify quota updated
        self.quota.refresh_from_db()
        self.assertEqual(self.quota.used_units, 1)
        self.assertEqual(self.quota.remaining_units, 9)

    def test_process_document_request_exceeding_quota(self):
        """Test processing document request that exceeds quota."""
        # Use up most of quota
        self.quota.used_units = 8
        self.quota.save()

        # Create document request for 3 units (exceeds remaining 2)
        request = DocumentRequest.objects.create(
            document_type=self.transcript,  # 3 units
            student=self.student,
            delivery_method="EMAIL",
            requested_by=self.user,
        )

        # Process request
        success, quota_usage, excess_charge = DocumentQuotaService.process_document_request(request)

        self.assertTrue(success)
        self.assertIsNotNone(quota_usage)
        self.assertIsNotNone(excess_charge)

        # Verify quota usage (partial)
        self.assertEqual(quota_usage.units_used, 2)  # Remaining quota
        self.assertFalse(quota_usage.is_excess)

        # Verify excess charge
        self.assertEqual(excess_charge.line_item_type, InvoiceLineItem.LineItemType.DOC_EXCESS)
        self.assertEqual(excess_charge.quantity, 1)  # 1 excess unit
        self.assertEqual(excess_charge.unit_price, Decimal("5.00"))
        self.assertEqual(excess_charge.line_total, Decimal("5.00"))

        # Verify quota fully used
        self.quota.refresh_from_db()
        self.assertEqual(self.quota.used_units, 10)
        self.assertEqual(self.quota.remaining_units, 0)

    def test_process_document_request_no_quota(self):
        """Test processing document request when student has no quota."""
        # Delete quota
        self.quota.delete()

        # Create document request
        request = DocumentRequest.objects.create(
            document_type=self.transcript,  # 3 units
            student=self.student,
            delivery_method="EMAIL",
            requested_by=self.user,
        )

        # Process request
        success, quota_usage, excess_charge = DocumentQuotaService.process_document_request(request)

        self.assertTrue(success)
        self.assertIsNone(quota_usage)
        self.assertIsNotNone(excess_charge)

        # Verify full excess charge
        self.assertEqual(excess_charge.quantity, 3)
        self.assertEqual(excess_charge.line_total, Decimal("15.00"))

    def test_process_document_request_creates_invoice(self):
        """Test that excess charges create invoices correctly."""
        # Use up quota
        self.quota.used_units = 10
        self.quota.save()

        # Create document request
        request = DocumentRequest.objects.create(
            document_type=self.transcript, student=self.student, delivery_method="EMAIL", requested_by=self.user
        )

        # Process request
        success, quota_usage, excess_charge = DocumentQuotaService.process_document_request(request)

        self.assertTrue(success)
        self.assertIsNotNone(excess_charge)

        # Verify invoice was created
        invoice = excess_charge.invoice
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.student, self.student)
        self.assertEqual(invoice.term, self.term)
        self.assertEqual(invoice.total_amount, Decimal("15.00"))

    def test_get_or_create_active_quota(self):
        """Test getting or creating active quota."""
        # Delete existing quota
        self.quota.delete()

        # Get or create
        quota = DocumentQuotaService.get_or_create_active_quota(self.student, self.term, initial_units=20)

        self.assertIsNotNone(quota)
        self.assertEqual(quota.student, self.student)
        self.assertEqual(quota.term, self.term)
        self.assertEqual(quota.initial_units, 20)
        self.assertTrue(quota.is_active)

    def test_get_or_create_active_quota_existing(self):
        """Test getting existing active quota."""
        quota = DocumentQuotaService.get_or_create_active_quota(self.student, self.term, initial_units=20)

        # Should return existing quota
        self.assertEqual(quota, self.quota)
        self.assertEqual(quota.initial_units, 10)  # Not updated

    def test_calculate_units_to_use(self):
        """Test calculating units to use from quota."""
        # Test with sufficient quota
        units = DocumentQuotaService.calculate_units_to_use(self.quota, 5)
        self.assertEqual(units, 5)

        # Test with insufficient quota
        self.quota.used_units = 8
        self.quota.save()
        units = DocumentQuotaService.calculate_units_to_use(self.quota, 5)
        self.assertEqual(units, 2)  # Only remaining units

        # Test with no remaining quota
        self.quota.used_units = 10
        self.quota.save()
        units = DocumentQuotaService.calculate_units_to_use(self.quota, 5)
        self.assertEqual(units, 0)

    def test_inactive_quota_not_used(self):
        """Test that inactive quotas are not used."""
        # Deactivate quota
        self.quota.is_active = False
        self.quota.save()

        # Create document request
        request = DocumentRequest.objects.create(
            document_type=self.letter, student=self.student, delivery_method="EMAIL", requested_by=self.user
        )

        # Process request
        success, quota_usage, excess_charge = DocumentQuotaService.process_document_request(request)

        # Should charge excess fee
        self.assertTrue(success)
        self.assertIsNone(quota_usage)
        self.assertIsNotNone(excess_charge)
        self.assertEqual(excess_charge.quantity, 1)
