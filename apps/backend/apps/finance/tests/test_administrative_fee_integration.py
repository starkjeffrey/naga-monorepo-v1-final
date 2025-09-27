"""Integration tests for the administrative fee system.

Tests the complete workflow of detecting cycle changes, applying fees,
creating document quotas, and processing document requests with excess charges.
"""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.test import TransactionTestCase

from apps.academic_records.models import DocumentQuota, DocumentRequest, DocumentTypeConfig
from apps.academic_records.services import DocumentQuotaService
from apps.curriculum.models import Major, Term
from apps.enrollment.models import ClassHeaderEnrollment, StudentCycleStatus
from apps.enrollment.services import CycleDetectionService
from apps.finance.models import AdministrativeFeeConfig, DocumentExcessFee, Invoice
from apps.finance.services import AdministrativeFeeService
from apps.people.models import Person, StudentProfile
from apps.scheduling.models import ClassHeader

User = get_user_model()


class AdministrativeFeeIntegrationTest(TransactionTestCase):
    """Test complete administrative fee workflow."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(email="test@example.com", password="testpass123")

        # Create terms
        self.term1 = Term.objects.create(
            code="2024-1", name="Spring 2024", start_date=date(2024, 1, 1), end_date=date(2024, 5, 31), is_active=True
        )

        self.term2 = Term.objects.create(
            code="2024-2", name="Fall 2024", start_date=date(2024, 9, 1), end_date=date(2024, 12, 31), is_active=False
        )

        # Create majors
        self.language_major = Major.objects.create(
            code="ENG", name="English Language", major_type="LANGUAGE", is_active=True
        )

        self.bachelor_major = Major.objects.create(
            code="CS", name="Computer Science", major_type="BACHELOR", is_active=True
        )

        self.master_major = Major.objects.create(
            code="MBA", name="Master of Business Administration", major_type="MASTER", is_active=True
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

        self.bachelor_master_config = AdministrativeFeeConfig.objects.create(
            cycle_type=StudentCycleStatus.CycleType.BACHELOR_TO_MASTER,
            fee_amount=Decimal("200.00"),
            included_document_units=20,
            description="Bachelor to Master transition fee",
            is_active=True,
            created_by=self.user,
        )

        # Create excess fee configurations
        for cycle_type in StudentCycleStatus.CycleType:
            DocumentExcessFee.objects.create(
                cycle_type=cycle_type, fee_per_unit=Decimal("5.00"), is_active=True, created_by=self.user
            )

        # Create document types
        self.transcript = DocumentTypeConfig.objects.create(
            code="TRANS",
            name="Official Transcript",
            category="ACADEMIC",
            unit_cost=5,
            processing_time_hours=48,
            requires_approval=True,
            is_active=True,
        )

        self.letter = DocumentTypeConfig.objects.create(
            code="LETTER",
            name="Enrollment Letter",
            category="LETTER",
            unit_cost=2,
            processing_time_hours=24,
            requires_approval=False,
            is_active=True,
        )

    def test_complete_new_student_workflow(self):
        """Test complete workflow for a new student."""
        # Step 1: Create new student
        person = Person.objects.create(
            personal_name="John",
            family_name="Doe",
            date_of_birth=date(2002, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )

        student = StudentProfile.objects.create(
            person=person, student_id="240001", admission_date=date.today(), primary_major=self.language_major
        )

        # Step 2: Detect cycle change (new entry)
        cycle_status = CycleDetectionService.detect_cycle_change(student, self.language_major)

        self.assertIsNotNone(cycle_status)
        self.assertEqual(cycle_status.cycle_type, StudentCycleStatus.CycleType.NEW_ENTRY)

        # Step 3: Process administrative fees for term
        with transaction.atomic():
            results = AdministrativeFeeService.process_term_administrative_fees(self.term1)

        self.assertEqual(results["processed"], 1)
        self.assertEqual(results["fees_applied"], 1)
        self.assertEqual(results["total_revenue"], Decimal("100.00"))

        # Step 4: Verify invoice and quota created
        invoice = Invoice.objects.filter(student=student, term=self.term1).first()
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.total_amount, Decimal("100.00"))

        quota = DocumentQuota.objects.filter(student=student, term=self.term1).first()
        self.assertIsNotNone(quota)
        self.assertEqual(quota.initial_units, 10)

        # Step 5: Student requests documents within quota
        request1 = DocumentRequest.objects.create(
            document_type=self.letter,  # 2 units
            student=student,
            delivery_method="EMAIL",
            requested_by=self.user,
        )

        success, usage, excess = DocumentQuotaService.process_document_request(request1)
        self.assertTrue(success)
        self.assertIsNotNone(usage)
        self.assertIsNone(excess)

        # Verify quota usage
        quota.refresh_from_db()
        self.assertEqual(quota.used_units, 2)
        self.assertEqual(quota.remaining_units, 8)

        # Step 6: Student requests documents exceeding quota
        request2 = DocumentRequest.objects.create(
            document_type=self.transcript,  # 5 units
            student=student,
            delivery_method="EMAIL",
            requested_by=self.user,
        )

        request3 = DocumentRequest.objects.create(
            document_type=self.transcript,  # 5 units (will exceed)
            student=student,
            delivery_method="EMAIL",
            requested_by=self.user,
        )

        # Process second request (within quota)
        success, usage, excess = DocumentQuotaService.process_document_request(request2)
        self.assertTrue(success)
        self.assertIsNotNone(usage)
        self.assertIsNone(excess)

        # Process third request (exceeds quota)
        success, usage, excess = DocumentQuotaService.process_document_request(request3)
        self.assertTrue(success)
        self.assertIsNotNone(usage)  # Uses remaining 3 units
        self.assertIsNotNone(excess)  # Charges for 2 excess units

        # Verify excess charge
        self.assertEqual(excess.quantity, 2)
        self.assertEqual(excess.line_total, Decimal("10.00"))

        # Verify quota fully used
        quota.refresh_from_db()
        self.assertEqual(quota.used_units, 10)
        self.assertEqual(quota.remaining_units, 0)

    def test_student_cycle_transition_workflow(self):
        """Test workflow for student transitioning between cycles."""
        # Create student in language program
        person = Person.objects.create(
            personal_name="Jane",
            family_name="Smith",
            date_of_birth=date(2001, 1, 1),
            preferred_gender="F",
            citizenship="KH",
        )

        student = StudentProfile.objects.create(
            person=person, student_id="230001", admission_date=date(2023, 1, 1), primary_major=self.language_major
        )

        # Initial new entry status
        initial_status = CycleDetectionService.detect_cycle_change(student, self.language_major)

        # Apply initial fee
        with transaction.atomic():
            AdministrativeFeeService.process_term_administrative_fees(self.term1)

        # Verify initial quota
        initial_quota = DocumentQuota.objects.filter(student=student, term=self.term1).first()
        self.assertEqual(initial_quota.initial_units, 10)

        # Student transitions to bachelor program
        student.primary_major = self.bachelor_major
        student.save()

        # Create enrollment in bachelor course
        from apps.curriculum.models import Course

        bachelor_course = Course.objects.create(
            code="CS101", name="Introduction to Computer Science", major=self.bachelor_major, credits=3
        )

        class_header = ClassHeader.objects.create(
            course=bachelor_course, term=self.term2, section="A", max_capacity=30
        )

        ClassHeaderEnrollment.objects.create(
            student=student,
            class_header=class_header,
            enrollment_status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
        )

        # Detect cycle change
        transition_status = CycleDetectionService.detect_cycle_change(student, self.bachelor_major)

        self.assertIsNotNone(transition_status)
        self.assertEqual(transition_status.cycle_type, StudentCycleStatus.CycleType.LANGUAGE_TO_BACHELOR)

        # Process fees for new term
        with transaction.atomic():
            results = AdministrativeFeeService.process_term_administrative_fees(self.term2)

        self.assertEqual(results["fees_applied"], 1)
        self.assertEqual(results["total_revenue"], Decimal("150.00"))

        # Verify new quota for new term
        new_quota = DocumentQuota.objects.filter(student=student, term=self.term2).first()
        self.assertEqual(new_quota.initial_units, 15)

        # Verify old status deactivated
        initial_status.refresh_from_db()
        self.assertFalse(initial_status.is_active)

    def test_multiple_students_batch_processing(self):
        """Test batch processing of multiple students."""
        students = []

        # Create mix of students
        for i in range(5):
            person = Person.objects.create(
                personal_name=f"Student{i}",
                family_name="Test",
                date_of_birth=date(2000, 1, 1),
                preferred_gender="M",
                citizenship="KH",
            )

            if i < 2:  # New students
                major = self.language_major
                cycle_type = StudentCycleStatus.CycleType.NEW_ENTRY
            elif i < 4:  # Language to Bachelor
                major = self.bachelor_major
                cycle_type = StudentCycleStatus.CycleType.LANGUAGE_TO_BACHELOR
            else:  # Bachelor to Master
                major = self.master_major
                cycle_type = StudentCycleStatus.CycleType.BACHELOR_TO_MASTER

            student = StudentProfile.objects.create(
                person=person, student_id=f"24000{i + 1}", admission_date=date.today(), primary_major=major
            )

            # Create appropriate cycle status
            if cycle_type == StudentCycleStatus.CycleType.NEW_ENTRY:
                StudentCycleStatus.objects.create(
                    student=student, cycle_type=cycle_type, target_program=major, is_active=True
                )
            else:
                # Create with source program
                source = (
                    self.language_major
                    if cycle_type == StudentCycleStatus.CycleType.LANGUAGE_TO_BACHELOR
                    else self.bachelor_major
                )
                StudentCycleStatus.objects.create(
                    student=student, cycle_type=cycle_type, source_program=source, target_program=major, is_active=True
                )

            students.append(student)

        # Process all fees
        with transaction.atomic():
            results = AdministrativeFeeService.process_term_administrative_fees(self.term1)

        # Verify results
        self.assertEqual(results["processed"], 5)
        self.assertEqual(results["fees_applied"], 5)
        # 2 * 100 + 2 * 150 + 1 * 200 = 700
        self.assertEqual(results["total_revenue"], Decimal("700.00"))

        # Verify all quotas created
        for student in students:
            quota = DocumentQuota.objects.filter(student=student, term=self.term1).first()
            self.assertIsNotNone(quota)

    def test_fee_persistence_across_terms(self):
        """Test that fees persist across multiple terms until graduation."""
        # Create student
        person = Person.objects.create(
            personal_name="Persistent",
            family_name="Student",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="M",
            citizenship="KH",
        )

        student = StudentProfile.objects.create(
            person=person, student_id="240099", admission_date=date.today(), primary_major=self.language_major
        )

        # Create cycle status
        StudentCycleStatus.objects.create(
            student=student,
            cycle_type=StudentCycleStatus.CycleType.NEW_ENTRY,
            target_program=self.language_major,
            is_active=True,
        )

        # Process fees for multiple terms
        terms = [self.term1, self.term2]

        for term in terms:
            with transaction.atomic():
                AdministrativeFeeService.process_term_administrative_fees(term)

            # Verify fee applied each term
            invoice = Invoice.objects.filter(student=student, term=term).first()
            self.assertIsNotNone(invoice)
            self.assertEqual(invoice.total_amount, Decimal("100.00"))

            # Verify quota created each term
            quota = DocumentQuota.objects.filter(student=student, term=term).first()
            self.assertIsNotNone(quota)
            self.assertEqual(quota.initial_units, 10)
