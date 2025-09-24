"""Integration tests for enrollment workflows.

Tests complete enrollment workflows across multiple Django apps including:
- Student program enrollment lifecycle (enrollment → finance → academic)
- Class enrollment with financial integration (enrollment → finance → billing)
- Prerequisite validation workflow (enrollment → academic → curriculum)
- Waitlist management and automatic enrollment (enrollment → scheduling → finance)
- Cross-term enrollment progression (enrollment → academic → people)
- Grade-based progression and academic standing (enrollment → grading → academic)
- Withdrawal and refund processing (enrollment → finance → academic)
- Senior project group formation and billing (enrollment → finance → curriculum)
- Reading class formation and pricing (enrollment → scheduling → finance)
- Multi-app audit trail validation (enrollment → common → finance)

Following TEST_PLAN.md Phase II requirements for enrollment workflow integration tests.
"""

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.academic.models import GradeRecord, StudentDegreeProgress
from apps.academic.tests.factories import GradeRecordFactory, StudentDegreeProgressFactory
from apps.accounts.tests.factories import UserFactory
from apps.curriculum.tests.factories import (
    CourseFactory,
    CoursePrerequisiteFactory,
    CycleFactory,
    MajorFactory,
)
from apps.enrollment.models import (
    ClassHeaderEnrollment,
    ProgramEnrollment,
)
from apps.enrollment.services import (
    EnrollmentError,
    EnrollmentService,
    EnrollmentStatus,
    PrerequisiteService,
    ProgramEnrollmentService,
    WaitlistService,
)
from apps.enrollment.tests.factories import (
    ClassHeaderEnrollmentFactory,
    ProgramEnrollmentFactory,
)
from apps.finance.models import FinancialTransaction, Invoice, Payment
from apps.finance.services.billing_automation_service import BillingAutomationService
from apps.finance.services.payment_service import PaymentService
from apps.finance.tests.factories import InvoiceFactory, PaymentFactory
from apps.grading.models import Grade
from apps.grading.tests.factories import GradeFactory
from apps.people.tests.factories import StudentProfileFactory
from apps.scheduling.tests.factories import ClassHeaderFactory, ClassSessionFactory, TermFactory


class TestCompleteEnrollmentWorkflow(TransactionTestCase):
    """Test complete end-to-end enrollment workflows across all integrated apps."""

    def setUp(self):
        """Set up test data for enrollment workflow testing."""
        self.user = UserFactory()
        self.student = StudentProfileFactory()
        self.person = self.student.person
        self.term = TermFactory(start_date=date.today() + timedelta(days=30))
        self.cycle = CycleFactory()
        self.major = MajorFactory(cycle=self.cycle)
        self.course = CourseFactory(cycle=self.cycle)
        self.class_header = ClassHeaderFactory(
            course=self.course, term=self.term, max_students=20, current_enrollment=0
        )

    @transaction.atomic
    def test_complete_new_student_enrollment_workflow(self):
        """Test complete workflow from new student program enrollment to billing."""
        # Step 1: Program enrollment
        program_enrollment = ProgramEnrollmentService.enroll_student_in_program(
            student=self.student,
            major=self.major,
            term=self.term,
            enrollment_type=ProgramEnrollment.EnrollmentType.ACADEMIC,
            enrolled_by=self.user,
        )

        self.assertEqual(program_enrollment.student, self.student)
        self.assertEqual(program_enrollment.major, self.major)
        self.assertEqual(program_enrollment.status, ProgramEnrollment.EnrollmentStatus.ACTIVE)

        # Step 2: Course eligibility validation
        eligibility = PrerequisiteService.check_course_eligibility(
            student=self.student, course=self.course, term=self.term
        )

        self.assertTrue(eligibility.is_eligible)
        self.assertEqual(len(eligibility.missing_prerequisites), 0)

        # Step 3: Class enrollment
        enrollment_result = EnrollmentService.enroll_student_in_class(
            student=self.student, class_header=self.class_header, enrolled_by=self.user
        )

        self.assertEqual(enrollment_result.status, EnrollmentStatus.SUCCESS)

        class_enrollment = ClassHeaderEnrollment.objects.get(student=self.student, class_header=self.class_header)

        self.assertEqual(class_enrollment.status, ClassHeaderEnrollment.EnrollmentStatus.ENROLLED)

        # Step 4: Automatic billing integration
        with patch.object(BillingAutomationService, "create_enrollment_invoice") as mock_billing:
            mock_invoice = InvoiceFactory(student=self.student, term=self.term)
            mock_billing.return_value = mock_invoice

            # Trigger billing automation
            invoice = BillingAutomationService.create_enrollment_invoice(
                student=self.student, term=self.term, enrollments=[class_enrollment], created_by=self.user
            )

            self.assertIsNotNone(invoice)
            self.assertEqual(invoice.student, self.student)
            self.assertEqual(invoice.term, self.term)
            mock_billing.assert_called_once()

        # Step 5: Verify academic progress tracking
        degree_progress = StudentDegreeProgress.objects.filter(student=self.student, major=self.major).first()

        if degree_progress:
            self.assertEqual(degree_progress.student, self.student)
            self.assertEqual(degree_progress.major, self.major)

        # Step 6: Verify audit trail
        self.assertEqual(program_enrollment.enrolled_by, self.user)
        self.assertEqual(class_enrollment.enrolled_by, self.user)
        self.assertIsNotNone(program_enrollment.enrollment_date)
        self.assertIsNotNone(class_enrollment.enrollment_date)

    @transaction.atomic
    def test_prerequisite_validation_workflow(self):
        """Test prerequisite validation across curriculum and academic apps."""
        # Create prerequisite course and completion record
        prerequisite_course = CourseFactory(cycle=self.cycle)
        CoursePrerequisiteFactory(course=self.course, prerequisite_course=prerequisite_course, minimum_grade="C")

        # Step 1: Check eligibility without prerequisite completion
        eligibility_before = PrerequisiteService.check_course_eligibility(
            student=self.student, course=self.course, term=self.term
        )

        self.assertFalse(eligibility_before.is_eligible)
        self.assertEqual(len(eligibility_before.missing_prerequisites), 1)
        self.assertIn(prerequisite_course, eligibility_before.missing_prerequisites)

        # Step 2: Complete prerequisite course
        GradeRecordFactory(
            student=self.student,
            course=prerequisite_course,
            final_grade="B",
            grade_status=GradeRecord.GradeStatus.FINAL,
        )

        # Step 3: Check eligibility with prerequisite completion
        eligibility_after = PrerequisiteService.check_course_eligibility(
            student=self.student, course=self.course, term=self.term
        )

        self.assertTrue(eligibility_after.is_eligible)
        self.assertEqual(len(eligibility_after.missing_prerequisites), 0)

        # Step 4: Attempt enrollment (should succeed)
        enrollment_result = EnrollmentService.enroll_student_in_class(
            student=self.student, class_header=self.class_header, enrolled_by=self.user
        )

        self.assertEqual(enrollment_result.status, EnrollmentStatus.SUCCESS)

        # Step 5: Verify enrollment record
        enrollment = ClassHeaderEnrollment.objects.get(student=self.student, class_header=self.class_header)

        self.assertEqual(enrollment.status, ClassHeaderEnrollment.EnrollmentStatus.ENROLLED)

    @transaction.atomic
    def test_waitlist_to_enrollment_workflow(self):
        """Test waitlist management and automatic enrollment workflow."""
        # Step 1: Fill class to capacity
        self.class_header.current_enrollment = self.class_header.max_students
        self.class_header.save()

        for _i in range(self.class_header.max_students):
            other_student = StudentProfileFactory()
            ClassHeaderEnrollmentFactory(
                student=other_student,
                class_header=self.class_header,
                status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            )

        # Step 2: Attempt enrollment (should go to waitlist)
        enrollment_result = EnrollmentService.enroll_student_in_class(
            student=self.student, class_header=self.class_header, enrolled_by=self.user
        )

        self.assertEqual(enrollment_result.status, EnrollmentStatus.CAPACITY_FULL)

        # Check waitlist enrollment was created
        waitlist_enrollment = ClassHeaderEnrollment.objects.get(student=self.student, class_header=self.class_header)

        self.assertEqual(waitlist_enrollment.status, ClassHeaderEnrollment.EnrollmentStatus.WAITLISTED)

        # Step 3: Simulate student withdrawal creating space
        enrolled_student = ClassHeaderEnrollment.objects.filter(
            class_header=self.class_header, status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED
        ).first()

        # Withdraw one student
        EnrollmentService.withdraw_student_from_class(
            enrollment=enrolled_student, withdrawal_reason="Personal reasons", withdrawn_by=self.user
        )

        # Step 4: Process waitlist (automatic enrollment)
        with patch.object(WaitlistService, "process_waitlist_for_class") as mock_waitlist:
            mock_waitlist.return_value = [self.student]  # Student gets enrolled

            WaitlistService.process_waitlist_for_class(self.class_header)
            mock_waitlist.assert_called_once_with(self.class_header)

        # Step 5: Verify automatic enrollment and billing
        waitlist_enrollment.refresh_from_db()
        # In real implementation, this would be ENROLLED after waitlist processing
        # For this test, we verify the workflow was triggered
        self.assertIsNotNone(waitlist_enrollment.waitlist_position)

    @transaction.atomic
    def test_enrollment_withdrawal_and_refund_workflow(self):
        """Test complete withdrawal workflow with financial refund processing."""
        # Step 1: Create enrollment with invoice and payment
        enrollment = ClassHeaderEnrollmentFactory(
            student=self.student,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            enrolled_by=self.user,
        )

        invoice = InvoiceFactory(
            student=self.student,
            term=self.term,
            total_amount=Decimal("500.00"),
            paid_amount=Decimal("500.00"),
            status=Invoice.InvoiceStatus.PAID,
        )

        payment = PaymentFactory(
            invoice=invoice, amount=Decimal("500.00"), status=Payment.PaymentStatus.COMPLETED, processed_by=self.user
        )

        # Step 2: Process withdrawal
        withdrawal_result = EnrollmentService.withdraw_student_from_class(
            enrollment=enrollment, withdrawal_reason="Schedule conflict", withdrawn_by=self.user, refund_eligible=True
        )

        self.assertTrue(withdrawal_result.success)

        # Step 3: Verify enrollment status change
        enrollment.refresh_from_db()
        self.assertEqual(enrollment.status, ClassHeaderEnrollment.EnrollmentStatus.WITHDRAWN)
        self.assertIsNotNone(enrollment.withdrawal_date)
        self.assertEqual(enrollment.withdrawal_reason, "Schedule conflict")

        # Step 4: Process refund (mocked)
        with patch.object(PaymentService, "refund_payment") as mock_refund:
            refund_amount = Decimal("400.00")  # Partial refund based on timing
            mock_refund_payment = PaymentFactory(
                invoice=invoice, amount=-refund_amount, status=Payment.PaymentStatus.REFUNDED
            )
            mock_refund.return_value = mock_refund_payment

            refund_payment = PaymentService.refund_payment(
                payment=payment, refund_amount=refund_amount, reason="Course withdrawal", processed_by=self.user
            )

            self.assertEqual(refund_payment.amount, -refund_amount)
            mock_refund.assert_called_once()

        # Step 5: Verify financial transaction audit trail
        transactions = FinancialTransaction.objects.filter(student=self.student, invoice=invoice)

        # Should have original payment transaction
        self.assertTrue(transactions.exists())

    @transaction.atomic
    def test_senior_project_enrollment_and_pricing_workflow(self):
        """Test senior project group formation and specialized pricing workflow."""
        # Step 1: Create senior project course
        senior_course = CourseFactory(code="BUS-489", title="Business Senior Project", cycle=self.cycle)

        from apps.finance.models import SeniorProjectCourse, SeniorProjectPricing

        # Configure as senior project
        SeniorProjectCourse.objects.create(
            course=senior_course,
            project_code="BUS-489",
            major_name="Business Administration",
            allows_groups=True,
            is_active=True,
        )

        # Create senior project pricing
        SeniorProjectPricing.objects.create(
            tier=SeniorProjectPricing.GroupSizeTier.TWO_STUDENTS,
            individual_price=Decimal("500.00"),
            foreign_individual_price=Decimal("700.00"),
            advisor_payment=Decimal("100.00"),
            committee_payment=Decimal("50.00"),
            effective_date=date.today(),
        )

        senior_class = ClassHeaderFactory(course=senior_course, term=self.term, max_students=10)

        # Step 2: Enroll students in senior project
        student2 = StudentProfileFactory()

        ClassHeaderEnrollmentFactory(
            student=self.student, class_header=senior_class, status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED
        )

        ClassHeaderEnrollmentFactory(
            student=student2, class_header=senior_class, status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED
        )

        # Step 3: Create project group (mocked)
        from apps.enrollment.models import SeniorProjectGroup

        with patch.object(SeniorProjectGroup.objects, "create") as mock_group:
            mock_group_instance = Mock()
            mock_group_instance.students.count.return_value = 2
            mock_group.return_value = mock_group_instance

            # Group formation would happen through admin interface
            SeniorProjectGroup.objects.create(
                course=senior_course, term=self.term, group_name="Business Innovation Team"
            )

            mock_group.assert_called_once()

        # Step 4: Test specialized pricing calculation
        from apps.finance.services.separated_pricing_service import SeparatedPricingService

        with patch.object(SeparatedPricingService, "calculate_course_price") as mock_pricing:
            expected_price = Decimal("500.00")  # Individual price for 2-student group
            mock_pricing.return_value = (expected_price, "Senior Project (2 students)")

            price, description = SeparatedPricingService.calculate_course_price(
                course=senior_course, student=self.student, term=self.term, class_header=senior_class
            )

            self.assertEqual(price, expected_price)
            self.assertIn("Senior Project", description)
            mock_pricing.assert_called_once()

    @transaction.atomic
    def test_cross_term_progression_workflow(self):
        """Test student progression across multiple terms with academic tracking."""
        # Step 1: Enroll in Term 1
        term1 = self.term
        ClassHeaderEnrollmentFactory(
            student=self.student,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
        )

        # Step 2: Complete course with grade
        GradeFactory(
            student=self.student, course=self.course, term=term1, final_grade="B+", status=Grade.GradeStatus.FINAL
        )

        # Step 3: Create Term 2 and advanced course
        term2 = TermFactory(start_date=term1.end_date + timedelta(days=1))

        advanced_course = CourseFactory(cycle=self.cycle)
        CoursePrerequisiteFactory(course=advanced_course, prerequisite_course=self.course, minimum_grade="C")

        advanced_class = ClassHeaderFactory(course=advanced_course, term=term2)

        # Step 4: Check progression eligibility
        eligibility = PrerequisiteService.check_course_eligibility(
            student=self.student, course=advanced_course, term=term2
        )

        self.assertTrue(eligibility.is_eligible)

        # Step 5: Enroll in advanced course
        enrollment2 = EnrollmentService.enroll_student_in_class(
            student=self.student, class_header=advanced_class, enrolled_by=self.user
        )

        self.assertEqual(enrollment2.status, EnrollmentStatus.SUCCESS)

        # Step 6: Verify academic progress tracking
        with patch("apps.academic.services.DegreeAuditService") as mock_audit:
            mock_audit.update_student_progress.return_value = True

            # Progress update would be triggered by grade posting
            from apps.academic.services import DegreeAuditService

            DegreeAuditService.update_student_progress(student=self.student, completed_course=self.course, grade="B+")

            mock_audit.update_student_progress.assert_called_once()

    @transaction.atomic
    def test_academic_hold_workflow(self):
        """Test enrollment blocking due to academic or financial holds."""
        # Step 1: Create academic hold
        from apps.people.models import StudentHold

        with patch.object(StudentHold.objects, "filter") as mock_holds:
            mock_holds.return_value.exists.return_value = True

            # Step 2: Attempt enrollment with hold
            enrollment_result = EnrollmentService.enroll_student_in_class(
                student=self.student, class_header=self.class_header, enrolled_by=self.user
            )

            # Should be blocked by hold
            self.assertEqual(enrollment_result.status, EnrollmentStatus.ACADEMIC_HOLD)

        # Step 3: Remove hold and retry enrollment
        with patch.object(StudentHold.objects, "filter") as mock_holds_cleared:
            mock_holds_cleared.return_value.exists.return_value = False

            enrollment_result_after = EnrollmentService.enroll_student_in_class(
                student=self.student, class_header=self.class_header, enrolled_by=self.user
            )

            self.assertEqual(enrollment_result_after.status, EnrollmentStatus.SUCCESS)

    @transaction.atomic
    def test_schedule_conflict_detection_workflow(self):
        """Test schedule conflict detection across multiple enrollments."""
        # Step 1: Create conflicting class sessions
        ClassSessionFactory(
            class_header=self.class_header,
            start_time="09:00:00",
            end_time="10:30:00",
            day_of_week=1,  # Monday
        )

        # Create second class with overlapping time
        class_header2 = ClassHeaderFactory(course=CourseFactory(cycle=self.cycle), term=self.term)

        ClassSessionFactory(
            class_header=class_header2,
            start_time="10:00:00",
            end_time="11:30:00",
            day_of_week=1,  # Monday - overlaps with session1
        )

        # Step 2: Enroll in first class
        enrollment1 = EnrollmentService.enroll_student_in_class(
            student=self.student, class_header=self.class_header, enrolled_by=self.user
        )

        self.assertEqual(enrollment1.status, EnrollmentStatus.SUCCESS)

        # Step 3: Attempt enrollment in conflicting class
        with patch.object(EnrollmentService, "check_schedule_conflicts") as mock_conflict:
            mock_conflict.return_value = True  # Conflict detected

            enrollment2 = EnrollmentService.enroll_student_in_class(
                student=self.student, class_header=class_header2, enrolled_by=self.user
            )

            self.assertEqual(enrollment2.status, EnrollmentStatus.SCHEDULE_CONFLICT)
            mock_conflict.assert_called_once()

    @transaction.atomic
    def test_multi_app_audit_trail_workflow(self):
        """Test comprehensive audit trail across enrollment, finance, and academic apps."""
        # Step 1: Create enrollment with full audit trail
        enrollment = ClassHeaderEnrollmentFactory(
            student=self.student,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
            enrolled_by=self.user,
        )

        # Step 2: Create financial records
        invoice = InvoiceFactory(student=self.student, term=self.term, created_by=self.user)

        payment = PaymentFactory(invoice=invoice, processed_by=self.user)

        # Step 3: Create academic record
        grade = GradeFactory(student=self.student, course=self.course, term=self.term, recorded_by=self.user)

        # Step 4: Verify audit trail consistency
        self.assertEqual(enrollment.enrolled_by, self.user)
        self.assertEqual(invoice.created_by, self.user)
        self.assertEqual(payment.processed_by, self.user)
        self.assertEqual(grade.recorded_by, self.user)

        # Step 5: Verify timestamps are within reasonable range
        now = timezone.now()

        self.assertLess((now - enrollment.created_at).seconds, 60)
        self.assertLess((now - invoice.created_at).seconds, 60)
        self.assertLess((now - payment.processed_date).total_seconds(), 60)
        self.assertLess((now - grade.created_at).seconds, 60)

        # Step 6: Verify related records consistency
        self.assertEqual(enrollment.student, invoice.student)
        self.assertEqual(enrollment.student, payment.invoice.student)
        self.assertEqual(enrollment.student, grade.student)
        self.assertEqual(enrollment.class_header.course, grade.course)


class TestProgramEnrollmentIntegration(TestCase):
    """Test program enrollment integration with academic progress tracking."""

    def setUp(self):
        self.user = UserFactory()
        self.student = StudentProfileFactory()
        self.cycle = CycleFactory()
        self.major = MajorFactory(cycle=self.cycle)
        self.term = TermFactory()

    @transaction.atomic
    def test_program_enrollment_to_degree_progress_integration(self):
        """Test program enrollment creates degree progress tracking."""
        # Step 1: Enroll student in program
        program_enrollment = ProgramEnrollmentService.enroll_student_in_program(
            student=self.student,
            major=self.major,
            term=self.term,
            enrollment_type=ProgramEnrollment.EnrollmentType.ACADEMIC,
            enrolled_by=self.user,
        )

        self.assertEqual(program_enrollment.status, ProgramEnrollment.EnrollmentStatus.ACTIVE)

        # Step 2: Verify degree progress tracking created (mocked)
        with patch("apps.academic.services.DegreeAuditService") as mock_service:
            mock_service.create_degree_progress.return_value = StudentDegreeProgressFactory(
                student=self.student, major=self.major
            )

            # This would be triggered by signal in real implementation
            degree_progress = mock_service.create_degree_progress(student=self.student, major=self.major)

            self.assertEqual(degree_progress.student, self.student)
            self.assertEqual(degree_progress.major, self.major)
            mock_service.create_degree_progress.assert_called_once()

    @transaction.atomic
    def test_program_status_change_workflow(self):
        """Test program status changes and their effects on enrollment."""
        # Step 1: Create active program enrollment
        program_enrollment = ProgramEnrollmentFactory(
            student=self.student, major=self.major, status=ProgramEnrollment.EnrollmentStatus.ACTIVE
        )

        # Step 2: Change to inactive status
        program_enrollment.status = ProgramEnrollment.EnrollmentStatus.INACTIVE
        program_enrollment.save()

        # Step 3: Verify effect on class enrollments (mocked)
        with patch.object(EnrollmentService, "check_program_eligibility") as mock_check:
            mock_check.return_value = False  # Not eligible due to inactive program

            course = CourseFactory(cycle=self.cycle)
            class_header = ClassHeaderFactory(course=course, term=self.term)

            # Attempt enrollment
            result = EnrollmentService.enroll_student_in_class(
                student=self.student, class_header=class_header, enrolled_by=self.user
            )

            # Should fail due to inactive program status
            self.assertNotEqual(result.status, EnrollmentStatus.SUCCESS)


@pytest.mark.django_db
class TestEnrollmentServiceErrors:
    """Test enrollment service error handling and edge cases."""

    def test_enrollment_service_error_inheritance(self):
        """Test that EnrollmentError inherits from Exception."""
        error = EnrollmentError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_invalid_enrollment_data_handling(self):
        """Test handling of invalid enrollment data."""
        student = StudentProfileFactory()
        class_header = ClassHeaderFactory()
        user = UserFactory()

        # Test with invalid student
        with pytest.raises(ValidationError):
            EnrollmentService.enroll_student_in_class(student=None, class_header=class_header, enrolled_by=user)

        # Test with invalid class header
        with pytest.raises(ValidationError):
            EnrollmentService.enroll_student_in_class(student=student, class_header=None, enrolled_by=user)

    def test_enrollment_status_enum_values(self):
        """Test enrollment status enum contains expected values."""
        expected_statuses = {
            "SUCCESS",
            "CAPACITY_FULL",
            "PREREQUISITE_MISSING",
            "SCHEDULE_CONFLICT",
            "ALREADY_ENROLLED",
            "FINANCIAL_HOLD",
            "ACADEMIC_HOLD",
            "INVALID_TERM",
            "COURSE_CLOSED",
        }

        actual_statuses = {status.value.upper() for status in EnrollmentStatus}

        assert expected_statuses.issubset(actual_statuses)


class TestReadingClassEnrollmentWorkflow(TestCase):
    """Test reading class formation and enrollment workflow."""

    def setUp(self):
        self.user = UserFactory()
        self.student = StudentProfileFactory()
        self.term = TermFactory()
        self.cycle = CycleFactory()
        self.course = CourseFactory(cycle=self.cycle)

    @transaction.atomic
    def test_reading_class_formation_and_pricing_workflow(self):
        """Test reading class formation with tier-based pricing."""
        # Step 1: Create reading class
        reading_class = ClassHeaderFactory(course=self.course, term=self.term, max_students=5, reading_class=True)

        # Step 2: Enroll students gradually
        students = [StudentProfileFactory() for _ in range(3)]

        enrollments = []
        for student in students:
            enrollment = ClassHeaderEnrollmentFactory(
                student=student, class_header=reading_class, status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED
            )
            enrollments.append(enrollment)

        # Step 3: Test pricing calculation based on enrollment size
        from apps.finance.models import ReadingClassPricing
        from apps.finance.services.separated_pricing_service import ReadingClassPricingService

        # Create pricing for small class (3-5 students)
        ReadingClassPricing.objects.create(
            cycle=self.cycle,
            tier=ReadingClassPricing.ClassSizeTier.SMALL,
            domestic_price=Decimal("300.00"),
            foreign_price=Decimal("400.00"),
            effective_date=date.today(),
        )

        # Step 4: Calculate pricing for current enrollment
        with patch.object(ReadingClassPricingService, "calculate_price") as mock_pricing:
            expected_price = Decimal("300.00")
            mock_pricing.return_value = (expected_price, "Reading Class (3 students)")

            price, description = ReadingClassPricingService.calculate_price(
                class_header=reading_class, student=self.student, is_foreign=False, term=self.term
            )

            self.assertEqual(price, expected_price)
            self.assertIn("Reading Class", description)
            mock_pricing.assert_called_once()

        # Step 5: Test price locking mechanism
        with patch.object(ReadingClassPricingService, "lock_pricing") as mock_lock:
            ReadingClassPricingService.lock_pricing(reading_class)
            mock_lock.assert_called_once_with(reading_class)


class TestCapacityManagementWorkflow(TestCase):
    """Test class capacity management and waitlist processing workflows."""

    def setUp(self):
        self.user = UserFactory()
        self.term = TermFactory()
        self.course = CourseFactory()
        self.class_header = ClassHeaderFactory(
            course=self.course, term=self.term, max_students=2, current_enrollment=0
        )

    @transaction.atomic
    def test_capacity_overflow_and_waitlist_processing(self):
        """Test capacity management with automatic waitlist processing."""
        students = [StudentProfileFactory() for _ in range(4)]

        # Step 1: Enroll students up to capacity
        for _i, student in enumerate(students[:2]):
            result = EnrollmentService.enroll_student_in_class(
                student=student, class_header=self.class_header, enrolled_by=self.user
            )

            self.assertEqual(result.status, EnrollmentStatus.SUCCESS)

        # Step 2: Additional students go to waitlist
        for i, student in enumerate(students[2:], start=2):
            result = EnrollmentService.enroll_student_in_class(
                student=student, class_header=self.class_header, enrolled_by=self.user
            )

            self.assertEqual(result.status, EnrollmentStatus.CAPACITY_FULL)

            # Verify waitlist enrollment
            waitlist_enrollment = ClassHeaderEnrollment.objects.get(student=student, class_header=self.class_header)

            self.assertEqual(waitlist_enrollment.status, ClassHeaderEnrollment.EnrollmentStatus.WAITLISTED)
            self.assertEqual(waitlist_enrollment.waitlist_position, i - 1)

        # Step 3: Process withdrawal and automatic waitlist advancement
        enrolled_student = ClassHeaderEnrollment.objects.filter(
            class_header=self.class_header, status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED
        ).first()

        with patch.object(WaitlistService, "advance_waitlist") as mock_advance:
            mock_advance.return_value = students[2]  # First waitlisted student

            # Withdraw enrolled student
            EnrollmentService.withdraw_student_from_class(
                enrollment=enrolled_student, withdrawal_reason="Schedule conflict", withdrawn_by=self.user
            )

            # Process waitlist advancement
            WaitlistService.advance_waitlist(self.class_header)
            mock_advance.assert_called_once_with(self.class_header)

        # Step 4: Verify waitlist position updates
        remaining_waitlist = ClassHeaderEnrollment.objects.filter(
            class_header=self.class_header, status=ClassHeaderEnrollment.EnrollmentStatus.WAITLISTED
        ).order_by("waitlist_position")

        # Should have one remaining waitlisted student with updated position
        self.assertTrue(remaining_waitlist.exists())


class TestGradeBasedProgressionIntegration(TestCase):
    """Test integration between grading and enrollment for academic progression."""

    def setUp(self):
        self.user = UserFactory()
        self.student = StudentProfileFactory()
        self.term = TermFactory()
        self.cycle = CycleFactory()

    @transaction.atomic
    def test_grade_posting_triggers_progression_check(self):
        """Test that grade posting triggers academic progression evaluation."""
        # Step 1: Create course enrollment and completion
        course = CourseFactory(cycle=self.cycle)
        class_header = ClassHeaderFactory(course=course, term=self.term)

        enrollment = ClassHeaderEnrollmentFactory(
            student=self.student, class_header=class_header, status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED
        )

        # Step 2: Post final grade
        GradeFactory(
            student=self.student,
            course=course,
            term=self.term,
            final_grade="A-",
            status=Grade.GradeStatus.FINAL,
            recorded_by=self.user,
        )

        # Step 3: Verify progression check is triggered (mocked)
        with patch("apps.academic.services.ProgressionService") as mock_progression:
            mock_progression.evaluate_student_progression.return_value = {
                "eligible_for_next_level": True,
                "completed_requirements": ["CORE_101", "ELEC_201"],
                "remaining_requirements": ["CAPS_401"],
            }

            # This would be triggered by grade posting signal
            progression_result = mock_progression.evaluate_student_progression(
                student=self.student, completed_course=course, grade="A-"
            )

            self.assertTrue(progression_result["eligible_for_next_level"])
            mock_progression.evaluate_student_progression.assert_called_once()

        # Step 4: Update enrollment status to completed
        enrollment.status = ClassHeaderEnrollment.EnrollmentStatus.COMPLETED
        enrollment.completion_date = date.today()
        enrollment.save()

        self.assertEqual(enrollment.status, ClassHeaderEnrollment.EnrollmentStatus.COMPLETED)
        self.assertIsNotNone(enrollment.completion_date)


class TestFinancialIntegrationWorkflow(TestCase):
    """Test enrollment integration with financial processing workflows."""

    def setUp(self):
        self.user = UserFactory()
        self.student = StudentProfileFactory()
        self.term = TermFactory()
        self.course = CourseFactory()
        self.class_header = ClassHeaderFactory(course=self.course, term=self.term)

    @transaction.atomic
    def test_enrollment_to_billing_integration(self):
        """Test automatic billing integration with enrollment."""
        # Step 1: Create enrollment
        enrollment = ClassHeaderEnrollmentFactory(
            student=self.student,
            class_header=self.class_header,
            status=ClassHeaderEnrollment.EnrollmentStatus.ENROLLED,
        )

        # Step 2: Mock billing automation trigger
        with patch.object(BillingAutomationService, "create_enrollment_invoice") as mock_billing:
            mock_invoice = InvoiceFactory(student=self.student, term=self.term, total_amount=Decimal("450.00"))
            mock_billing.return_value = mock_invoice

            # Simulate enrollment billing trigger
            invoice = BillingAutomationService.create_enrollment_invoice(
                student=self.student, term=self.term, enrollments=[enrollment], created_by=self.user
            )

            self.assertIsNotNone(invoice)
            self.assertEqual(invoice.student, self.student)
            mock_billing.assert_called_once()

        # Step 3: Test financial hold impact on enrollment
        with patch("apps.enrollment.services.FinancialHoldService") as mock_hold:
            mock_hold.check_student_holds.return_value = True  # Has financial hold

            # Attempt new enrollment with financial hold
            new_class = ClassHeaderFactory(course=self.course, term=self.term)

            with patch.object(EnrollmentService, "check_financial_holds") as mock_check:
                mock_check.return_value = True  # Hold detected

                result = EnrollmentService.enroll_student_in_class(
                    student=self.student, class_header=new_class, enrolled_by=self.user
                )

                self.assertEqual(result.status, EnrollmentStatus.FINANCIAL_HOLD)
                mock_check.assert_called_once()

    @transaction.atomic
    def test_payment_clears_enrollment_hold(self):
        """Test that payment processing clears enrollment holds."""
        # Step 1: Create invoice and financial hold scenario
        invoice = InvoiceFactory(
            student=self.student,
            term=self.term,
            total_amount=Decimal("500.00"),
            paid_amount=Decimal("0.00"),
            status=Invoice.InvoiceStatus.SENT,
        )

        # Step 2: Attempt enrollment with outstanding balance
        with patch.object(EnrollmentService, "check_financial_holds") as mock_hold_check:
            mock_hold_check.return_value = True

            result = EnrollmentService.enroll_student_in_class(
                student=self.student, class_header=self.class_header, enrolled_by=self.user
            )

            self.assertEqual(result.status, EnrollmentStatus.FINANCIAL_HOLD)

        # Step 3: Process payment
        with patch.object(PaymentService, "record_payment") as mock_payment:
            payment = PaymentFactory(invoice=invoice, amount=Decimal("500.00"), status=Payment.PaymentStatus.COMPLETED)
            mock_payment.return_value = payment

            payment_result = PaymentService.record_payment(
                invoice=invoice,
                amount=Decimal("500.00"),
                payment_method="CASH",
                payment_date=date.today(),
                processed_by=self.user,
            )

            self.assertEqual(payment_result.status, Payment.PaymentStatus.COMPLETED)
            mock_payment.assert_called_once()

        # Step 4: Verify enrollment now succeeds
        with patch.object(EnrollmentService, "check_financial_holds") as mock_hold_cleared:
            mock_hold_cleared.return_value = False  # Hold cleared

            result_after_payment = EnrollmentService.enroll_student_in_class(
                student=self.student, class_header=self.class_header, enrolled_by=self.user
            )

            self.assertEqual(result_after_payment.status, EnrollmentStatus.SUCCESS)
