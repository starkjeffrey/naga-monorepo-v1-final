"""Unit tests for AdministrativeFeeService.

Tests the business logic for applying administrative fees to students
who change academic cycles or are new students.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.academic_records.models import DocumentQuota
from apps.curriculum.models import Major, Term
from apps.enrollment.models import StudentCycleStatus
from apps.finance.models import AdministrativeFeeConfig, DocumentExcessFee, Invoice, InvoiceLineItem
from apps.finance.services import AdministrativeFeeService
from apps.people.models import Person, StudentProfile

User = get_user_model()


class AdministrativeFeeServiceTest(TestCase):
    """Test administrative fee service business logic."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(email="test@example.com", password="testpass123")

        # Create term
        self.term = Term.objects.create(
            code="2024-1", name="Spring 2024", start_date=date(2024, 1, 1), end_date=date(2024, 5, 31), is_active=True
        )

        # Create majors
        self.language_major = Major.objects.create(
            code="ENG", name="English Language", major_type="LANGUAGE", is_active=True
        )

        self.bachelor_major = Major.objects.create(
            code="CS", name="Computer Science", major_type="BACHELOR", is_active=True
        )

        # Create fee configurations
        self.new_entry_config = AdministrativeFeeConfig.objects.create(
            cycle_type=StudentCycleStatus.CycleType.NEW_ENTRY,
            fee_amount=Decimal("100.00"),
            included_document_units=10,
            description="New student administrative fee",
            is_active=True,
            created_by=self.user,
        )

        self.language_bachelor_config = AdministrativeFeeConfig.objects.create(
            cycle_type=StudentCycleStatus.CycleType.LANGUAGE_TO_BACHELOR,
            fee_amount=Decimal("150.00"),
            included_document_units=15,
            description="Language to Bachelor transition fee",
            is_active=True,
            created_by=self.user,
        )

        # Create document excess fee config
        self.excess_fee_config = DocumentExcessFee.objects.create(
            cycle_type=StudentCycleStatus.CycleType.NEW_ENTRY,
            fee_per_unit=Decimal("5.00"),
            is_active=True,
            created_by=self.user,
        )

        # Create test students
        self.students = []
        for i in range(3):
            person = Person.objects.create(
                personal_name=f"Test{i}",
                family_name="Student",
                date_of_birth=date(2000, 1, 1),
                preferred_gender="M",
                citizenship="KH",
            )

            student = StudentProfile.objects.create(
                person=person,
                student_id=f"24000{i + 1}",
                admission_date=date.today(),
                primary_major=self.language_major,
            )
            self.students.append(student)

    def test_apply_administrative_fee_new_student(self):
        """Test applying administrative fee to new student."""
        student = self.students[0]

        # Create cycle status
        cycle_status = StudentCycleStatus.objects.create(
            student=student,
            cycle_type=StudentCycleStatus.CycleType.NEW_ENTRY,
            target_program=self.language_major,
            is_active=True,
        )

        # Apply fee
        invoice = AdministrativeFeeService.apply_administrative_fee(
            student=student, term=self.term, cycle_status=cycle_status
        )

        # Verify invoice
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.student, student)
        self.assertEqual(invoice.term, self.term)
        self.assertEqual(invoice.total_amount, Decimal("100.00"))

        # Verify line item
        line_item = invoice.line_items.first()
        self.assertIsNotNone(line_item)
        self.assertEqual(line_item.line_item_type, InvoiceLineItem.LineItemType.ADMIN_FEE)
        self.assertEqual(line_item.description, "Administrative Fee - New Student Entry")
        self.assertEqual(line_item.unit_price, Decimal("100.00"))
        self.assertEqual(line_item.quantity, 1)
        self.assertEqual(line_item.line_total, Decimal("100.00"))

        # Verify document quota was created
        quota = DocumentQuota.objects.filter(student=student, term=self.term, is_active=True).first()
        self.assertIsNotNone(quota)
        self.assertEqual(quota.initial_units, 10)
        self.assertEqual(quota.used_units, 0)
        self.assertEqual(quota.administrative_fee_id, line_item.id)

    def test_apply_administrative_fee_cycle_transition(self):
        """Test applying fee for cycle transition."""
        student = self.students[1]

        # Update student to bachelor
        student.primary_major = self.bachelor_major
        student.save()

        # Create cycle status
        cycle_status = StudentCycleStatus.objects.create(
            student=student,
            cycle_type=StudentCycleStatus.CycleType.LANGUAGE_TO_BACHELOR,
            source_program=self.language_major,
            target_program=self.bachelor_major,
            is_active=True,
        )

        # Apply fee
        invoice = AdministrativeFeeService.apply_administrative_fee(
            student=student, term=self.term, cycle_status=cycle_status
        )

        # Verify invoice
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.total_amount, Decimal("150.00"))

        # Verify line item
        line_item = invoice.line_items.first()
        self.assertEqual(line_item.description, "Administrative Fee - Language to Bachelor Transition")
        self.assertEqual(line_item.unit_price, Decimal("150.00"))

        # Verify document quota
        quota = DocumentQuota.objects.filter(student=student, term=self.term).first()
        self.assertEqual(quota.initial_units, 15)

    def test_no_duplicate_fees_same_term(self):
        """Test that duplicate fees are not applied in same term."""
        student = self.students[2]

        # Create cycle status
        cycle_status = StudentCycleStatus.objects.create(
            student=student,
            cycle_type=StudentCycleStatus.CycleType.NEW_ENTRY,
            target_program=self.language_major,
            is_active=True,
        )

        # Apply fee first time
        AdministrativeFeeService.apply_administrative_fee(student=student, term=self.term, cycle_status=cycle_status)

        # Try to apply again
        invoice2 = AdministrativeFeeService.apply_administrative_fee(
            student=student, term=self.term, cycle_status=cycle_status
        )

        # Should return None (no duplicate)
        self.assertIsNone(invoice2)

        # Verify only one invoice exists
        invoice_count = Invoice.objects.filter(student=student, term=self.term).count()
        self.assertEqual(invoice_count, 1)

    def test_process_term_administrative_fees(self):
        """Test bulk processing of administrative fees for a term."""
        # Create cycle statuses for all students
        for i, student in enumerate(self.students):
            if i == 0:
                cycle_type = StudentCycleStatus.CycleType.NEW_ENTRY
            else:
                cycle_type = StudentCycleStatus.CycleType.LANGUAGE_TO_BACHELOR
                student.primary_major = self.bachelor_major
                student.save()

            StudentCycleStatus.objects.create(
                student=student, cycle_type=cycle_type, target_program=student.primary_major, is_active=True
            )

        # Process term fees
        results = AdministrativeFeeService.process_term_administrative_fees(self.term)

        # Verify results
        self.assertEqual(results["processed"], 3)
        self.assertEqual(results["fees_applied"], 3)
        # Total: 1 * 100 + 2 * 150 = 400
        self.assertEqual(results["total_revenue"], Decimal("400.00"))
        self.assertEqual(len(results["errors"]), 0)

        # Verify invoices created
        invoice_count = Invoice.objects.filter(term=self.term).count()
        self.assertEqual(invoice_count, 3)

        # Verify quotas created
        quota_count = DocumentQuota.objects.filter(term=self.term).count()
        self.assertEqual(quota_count, 3)

    def test_inactive_configuration_not_applied(self):
        """Test that inactive fee configurations are not applied."""
        # Deactivate configuration
        self.new_entry_config.is_active = False
        self.new_entry_config.save()

        student = self.students[0]
        cycle_status = StudentCycleStatus.objects.create(
            student=student,
            cycle_type=StudentCycleStatus.CycleType.NEW_ENTRY,
            target_program=self.language_major,
            is_active=True,
        )

        # Try to apply fee
        invoice = AdministrativeFeeService.apply_administrative_fee(
            student=student, term=self.term, cycle_status=cycle_status
        )

        # Should return None
        self.assertIsNone(invoice)

    def test_get_excess_fee_configuration(self):
        """Test getting excess fee configuration."""
        student = self.students[0]
        cycle_status = StudentCycleStatus.objects.create(
            student=student,
            cycle_type=StudentCycleStatus.CycleType.NEW_ENTRY,
            target_program=self.language_major,
            is_active=True,
        )

        # Get configuration
        config = AdministrativeFeeService.get_excess_fee_configuration(cycle_status)

        self.assertIsNotNone(config)
        self.assertEqual(config.fee_per_unit, Decimal("5.00"))

    def test_process_with_existing_invoice(self):
        """Test that students with existing invoices are skipped."""
        student = self.students[0]

        # Create existing invoice
        Invoice.objects.create(
            student=student,
            term=self.term,
            issue_date=date.today(),
            due_date=date.today(),
            subtotal=Decimal("50.00"),
            tax_amount=Decimal("0.00"),
            total_amount=Decimal("50.00"),
            currency="USD",
            created_by=self.user,
        )

        # Create cycle status
        StudentCycleStatus.objects.create(
            student=student,
            cycle_type=StudentCycleStatus.CycleType.NEW_ENTRY,
            target_program=self.language_major,
            is_active=True,
        )

        # Process term
        results = AdministrativeFeeService.process_term_administrative_fees(self.term)

        # Should skip student with existing invoice
        self.assertEqual(results["processed"], 1)
        self.assertEqual(results["fees_applied"], 0)
        self.assertEqual(results["total_revenue"], Decimal("0.00"))
