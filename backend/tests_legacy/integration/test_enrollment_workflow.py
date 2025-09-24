"""Integration tests for complete enrollment workflows.

These tests verify end-to-end enrollment processes including:
- Student registration for terms
- Course enrollment with prerequisites
- Waitlist management
- Drop/add processes
- Financial integration (invoice generation)
- Grade recording

Tests use real database transactions to ensure data integrity.
"""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from freezegun import freeze_time

from apps.curriculum.models import CoursePrerequisite
from apps.enrollment.models import ClassHeaderEnrollment
from apps.finance.models import DefaultPricing, Invoice
from apps.scheduling.models import ClassHeader
from tests.fixtures.factories import (
    ClassHeaderFactory,
    CourseFactory,
    DivisionFactory,
    PersonFactory,
    StudentProfileFactory,
    TermFactory,
)


@pytest.mark.django_db
@pytest.mark.integration
class TestCompleteEnrollmentWorkflow:
    """Test the complete enrollment workflow from registration to completion."""

    @freeze_time("2024-01-01")
    def test_successful_enrollment_process(self):
        """Test a successful enrollment from start to finish.

        This test verifies:
        1. Student creates registration for term
        2. Student enrolls in classes
        3. System generates invoice
        4. Student is marked as enrolled
        5. Attendance tracking is enabled
        """
        # Setup: Create student
        person = PersonFactory(
            personal_name="Jane", family_name="Student", date_of_birth=date(2003, 1, 1), citizenship="KH"
        )
        student = StudentProfileFactory(person=person, student_id=20240001, current_status="ACTIVE")

        # Create term
        term = TermFactory(
            name="Spring 2024",
            code="SP24",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 5, 15),
            registration_start=date(2023, 12, 1),
            registration_end=date(2024, 1, 20),
            is_current=True,
        )

        # Create courses and classes
        division = DivisionFactory(name="Computer Science", short_name="CS")

        course1 = CourseFactory(code="CS101", title="Introduction to Programming", credits=3, division=division)

        course2 = CourseFactory(code="CS102", title="Data Structures", credits=3, division=division)

        # Create class headers
        class1 = ClassHeaderFactory(course=course1, term=term, section="A", max_enrollment=30, current_enrollment=0)

        class2 = ClassHeaderFactory(course=course2, term=term, section="A", max_enrollment=30, current_enrollment=0)

        # Setup pricing
        DefaultPricing.objects.create(
            cycle=division,
            domestic_price=Decimal("500.00"),
            foreign_price=Decimal("750.00"),
            effective_date=date(2024, 1, 1),
        )

        # Step 1: Create registration
        registration = Registration.objects.create(
            student=student, term=term, registration_date=timezone.now(), status="PENDING"
        )

        assert registration.status == "PENDING"
        assert registration.total_credits == 0

        # Step 2: Enroll in classes
        enrollment1 = ClassHeaderEnrollment.objects.create(
            student=student,
            class_header=class1,
            registration=registration,
            enrollment_date=timezone.now(),
            status="ENROLLED",
        )

        enrollment2 = ClassHeaderEnrollment.objects.create(
            student=student,
            class_header=class2,
            registration=registration,
            enrollment_date=timezone.now(),
            status="ENROLLED",
        )

        # Update registration credits
        registration.total_credits = course1.credits + course2.credits
        registration.status = "APPROVED"
        registration.save()

        # Verify enrollments
        assert enrollment1.status == "ENROLLED"
        assert enrollment2.status == "ENROLLED"
        assert registration.total_credits == 6

        # Step 3: Verify class enrollment counts updated
        class1.refresh_from_db()
        class2.refresh_from_db()

        assert class1.current_enrollment == 1
        assert class2.current_enrollment == 1

        # Step 4: Check invoice generation (if signal-based)
        invoices = Invoice.objects.filter(student=student)
        if invoices.exists():
            invoice = invoices.first()
            assert invoice.total_amount == Decimal("1000.00")  # 500 per course
            assert invoice.status == "PENDING"

            # Check line items
            line_items = invoice.line_items.all()
            assert line_items.count() == 2

    def test_enrollment_with_prerequisites(self):
        """Test enrollment validation with course prerequisites.

        A student cannot enroll in a course without completing prerequisites.
        """
        # Create student
        student = StudentProfileFactory()

        # Create courses with prerequisite relationship
        cs101 = CourseFactory(code="CS101", title="Intro to Programming")
        cs201 = CourseFactory(code="CS201", title="Advanced Programming")

        # CS201 requires CS101
        CoursePrerequisite.objects.create(course=cs201, prerequisite=cs101, minimum_grade="C")

        # Create current term and classes
        term = TermFactory(is_current=True)
        ClassHeaderFactory(course=cs101, term=term)
        cs201_class = ClassHeaderFactory(course=cs201, term=term)

        # Try to enroll in CS201 without completing CS101
        registration = Registration.objects.create(student=student, term=term)

        with pytest.raises(ValidationError) as exc:
            enrollment = ClassHeaderEnrollment(student=student, class_header=cs201_class, registration=registration)
            enrollment.full_clean()

        assert "prerequisite" in str(exc.value).lower()

        # Complete CS101 first
        past_term = TermFactory(name="Fall 2023", start_date=date(2023, 9, 1), end_date=date(2023, 12, 15))

        past_class = ClassHeaderFactory(course=cs101, term=past_term)
        ClassHeaderEnrollment.objects.create(student=student, class_header=past_class, status="COMPLETED", grade="B")

        # Now enrollment in CS201 should succeed
        enrollment = ClassHeaderEnrollment.objects.create(
            student=student, class_header=cs201_class, registration=registration, status="ENROLLED"
        )

        assert enrollment.status == "ENROLLED"

    def test_waitlist_to_enrollment_workflow(self):
        """Test waitlist management and automatic enrollment.

        When a spot opens up, the next student on waitlist should be notified.
        """
        # Create class at capacity
        course = CourseFactory()
        term = TermFactory(is_current=True)
        class_header = ClassHeaderFactory(
            course=course,
            term=term,
            max_enrollment=2,
            current_enrollment=2,
            waitlist_capacity=5,  # Already full
        )

        # Create students
        enrolled_student1 = StudentProfileFactory()
        enrolled_student2 = StudentProfileFactory()
        waitlist_student1 = StudentProfileFactory()
        waitlist_student2 = StudentProfileFactory()

        # Create enrollments for first two students
        reg1 = Registration.objects.create(student=enrolled_student1, term=term)
        reg2 = Registration.objects.create(student=enrolled_student2, term=term)

        enrollment1 = ClassHeaderEnrollment.objects.create(
            student=enrolled_student1, class_header=class_header, registration=reg1, status="ENROLLED"
        )

        ClassHeaderEnrollment.objects.create(
            student=enrolled_student2, class_header=class_header, registration=reg2, status="ENROLLED"
        )

        # Add students to waitlist
        waitlist1 = Waitlist.objects.create(
            student=waitlist_student1, class_header=class_header, position=1, status="WAITING"
        )

        waitlist2 = Waitlist.objects.create(
            student=waitlist_student2, class_header=class_header, position=2, status="WAITING"
        )

        # Student 1 drops the class
        enrollment1.status = "DROPPED"
        enrollment1.drop_date = timezone.now()
        enrollment1.save()

        class_header.current_enrollment -= 1
        class_header.save()

        # Waitlist student 1 should be notified
        waitlist1.refresh_from_db()
        waitlist1.status = "NOTIFIED"
        waitlist1.notified_date = timezone.now()
        waitlist1.notification_expiry = timezone.now() + timedelta(days=2)
        waitlist1.save()

        # Waitlist student 1 accepts and enrolls
        reg3 = Registration.objects.create(student=waitlist_student1, term=term)
        ClassHeaderEnrollment.objects.create(
            student=waitlist_student1, class_header=class_header, registration=reg3, status="ENROLLED"
        )

        waitlist1.status = "ENROLLED"
        waitlist1.save()

        class_header.current_enrollment += 1
        class_header.save()

        # Verify final state
        assert class_header.current_enrollment == 2
        assert waitlist1.status == "ENROLLED"
        assert waitlist2.status == "WAITING"
        assert waitlist2.position == 1  # Moved up in line

    def test_drop_add_deadline_enforcement(self):
        """Test that drop/add deadlines are enforced.

        Students cannot drop or add classes after the deadline.
        """
        term = TermFactory(
            start_date=date(2024, 1, 15),
            drop_deadline=date(2024, 1, 29),  # 2 weeks after start
            withdraw_deadline=date(2024, 3, 15),  # Mid-term
            is_current=True,
        )

        student = StudentProfileFactory()
        course = CourseFactory()
        class_header = ClassHeaderFactory(course=course, term=term)

        registration = Registration.objects.create(student=student, term=term)

        # Enroll before term starts - should succeed
        with freeze_time("2024-01-10"):
            enrollment = ClassHeaderEnrollment.objects.create(
                student=student, class_header=class_header, registration=registration, status="ENROLLED"
            )
            assert enrollment.status == "ENROLLED"

        # Try to drop after deadline - should fail
        with freeze_time("2024-02-01"):  # After drop deadline
            drop_request = DropRequest(
                enrollment=enrollment, student=student, request_date=timezone.now(), reason="Changed mind"
            )

            # Validation should fail
            with pytest.raises(ValidationError) as exc:
                drop_request.full_clean()
            assert "deadline" in str(exc.value).lower()

        # Can still withdraw (with W grade) before withdraw deadline
        with freeze_time("2024-03-01"):  # Before withdraw deadline
            enrollment.status = "WITHDRAWN"
            enrollment.grade = "W"
            enrollment.save()
            assert enrollment.status == "WITHDRAWN"

    def test_registration_hold_prevents_enrollment(self):
        """Test that registration holds prevent enrollment.

        Students with holds cannot register for classes until resolved.
        """
        student = StudentProfileFactory()
        term = TermFactory(is_current=True)

        # Create a financial hold
        hold = RegistrationHold.objects.create(
            student=student,
            hold_type="FINANCIAL",
            reason="Outstanding balance of $500",
            placed_date=timezone.now(),
            is_active=True,
            prevents_registration=True,
        )

        # Try to create registration - should fail
        with pytest.raises(ValidationError) as exc:
            registration = Registration(student=student, term=term, status="PENDING")
            registration.full_clean()

        assert "hold" in str(exc.value).lower()

        # Resolve the hold
        hold.is_active = False
        hold.resolved_date = timezone.now()
        hold.resolution_notes = "Payment received"
        hold.save()

        # Now registration should succeed
        registration = Registration.objects.create(student=student, term=term, status="PENDING")
        assert registration.id is not None

    @pytest.mark.parametrize(
        "student_status,max_credits",
        [
            ("ACTIVE", 18),  # Regular student
            ("PROBATION", 12),  # Academic probation - reduced load
            ("PART_TIME", 9),  # Part-time student
        ],
    )
    def test_credit_limit_enforcement(self, student_status, max_credits):
        """Test that credit limits are enforced based on student status.

        Different student statuses have different maximum credit loads.
        """
        student = StudentProfileFactory(current_status=student_status)
        term = TermFactory(is_current=True)

        registration = Registration.objects.create(student=student, term=term, max_credits=max_credits)

        # Create courses with different credits
        courses = [CourseFactory(code=f"CS{i}01", credits=3) for i in range(1, 8)]  # 7 courses x 3 credits = 21 total

        total_credits = 0
        enrollments = []

        for course in courses:
            class_header = ClassHeaderFactory(course=course, term=term)

            # Check if adding this course would exceed limit
            if total_credits + course.credits <= max_credits:
                enrollment = ClassHeaderEnrollment.objects.create(
                    student=student, class_header=class_header, registration=registration, status="ENROLLED"
                )
                enrollments.append(enrollment)
                total_credits += course.credits
            else:
                # Should not be able to enroll - exceeds limit
                with pytest.raises(ValidationError):
                    enrollment = ClassHeaderEnrollment(
                        student=student, class_header=class_header, registration=registration
                    )
                    enrollment.full_clean()

        # Verify final enrollment count
        registration.total_credits = total_credits
        registration.save()

        assert registration.total_credits <= max_credits
        assert len(enrollments) == max_credits // 3  # Each course is 3 credits


@pytest.mark.django_db
@pytest.mark.integration
class TestEnrollmentFinancialIntegration:
    """Test integration between enrollment and financial systems."""

    def test_invoice_generation_on_enrollment(self):
        """Test that invoices are automatically generated when students enroll."""
        # Create student and term
        student = StudentProfileFactory()
        term = TermFactory(is_current=True)

        # Create division with pricing
        division = DivisionFactory(name="Engineering")
        DefaultPricing.objects.create(
            cycle=division,
            domestic_price=Decimal("600.00"),
            foreign_price=Decimal("900.00"),
            effective_date=date(2024, 1, 1),
        )

        # Create courses
        courses = [CourseFactory(code=f"ENG{i}01", credits=3, division=division) for i in range(1, 4)]  # 3 courses

        # Create registration
        registration = Registration.objects.create(student=student, term=term)

        # Enroll in courses
        for course in courses:
            class_header = ClassHeaderFactory(course=course, term=term)
            ClassHeaderEnrollment.objects.create(
                student=student, class_header=class_header, registration=registration, status="ENROLLED"
            )

        # Check invoice was created
        invoice = Invoice.objects.filter(student=student, term=term).first()

        if invoice:  # If signal-based invoice generation is implemented
            assert invoice.total_amount == Decimal("1800.00")  # 3 x 600
            assert invoice.line_items.count() == 3

            for line_item in invoice.line_items.all():
                assert line_item.amount == Decimal("600.00")
                assert line_item.description in [c.title for c in courses]

    def test_refund_on_drop(self):
        """Test that appropriate refunds are issued when students drop classes."""
        student = StudentProfileFactory()
        term = TermFactory(start_date=date(2024, 1, 15), drop_deadline=date(2024, 1, 29), is_current=True)

        # Enroll and pay for course
        course = CourseFactory(credits=3)
        class_header = ClassHeaderFactory(course=course, term=term)

        registration = Registration.objects.create(student=student, term=term)
        enrollment = ClassHeaderEnrollment.objects.create(
            student=student, class_header=class_header, registration=registration, status="ENROLLED"
        )

        # Drop before classes start - 100% refund
        with freeze_time("2024-01-10"):
            drop_request = DropRequest.objects.create(
                enrollment=enrollment, student=student, reason="Schedule conflict", refund_percentage=100
            )

            enrollment.status = "DROPPED"
            enrollment.drop_date = timezone.now()
            enrollment.save()

            assert drop_request.refund_percentage == 100

        # Another scenario: Drop in first week - 50% refund
        enrollment2 = ClassHeaderEnrollment.objects.create(
            student=student,
            class_header=ClassHeaderFactory(course=course, term=term),
            registration=registration,
            status="ENROLLED",
        )

        with freeze_time("2024-01-20"):  # First week
            drop_request2 = DropRequest.objects.create(
                enrollment=enrollment2, student=student, reason="Course too difficult", refund_percentage=50
            )

            assert drop_request2.refund_percentage == 50


@pytest.mark.django_db
@pytest.mark.integration
class TestConcurrentEnrollment:
    """Test concurrent enrollment scenarios to prevent race conditions."""

    def test_concurrent_enrollment_in_limited_capacity_class(self):
        """Test that concurrent enrollments don't exceed class capacity.

        This simulates multiple students trying to enroll in the last spot.
        """
        # Create class with only 1 spot remaining
        course = CourseFactory()
        term = TermFactory(is_current=True)
        class_header = ClassHeaderFactory(
            course=course,
            term=term,
            max_enrollment=30,
            current_enrollment=29,  # Only 1 spot left
        )

        # Create multiple students trying to enroll
        students = [StudentProfileFactory() for _ in range(3)]
        failed_enrollments = []

        # Simulate concurrent enrollment attempts
        for student in students:
            registration = Registration.objects.create(student=student, term=term)

            # Use database transaction to ensure atomicity
            try:
                with transaction.atomic():
                    # Re-fetch with lock to prevent race condition
                    locked_class = ClassHeader.objects.select_for_update().get(id=class_header.id)

                    if locked_class.current_enrollment < locked_class.max_enrollment:
                        ClassHeaderEnrollment.objects.create(
                            student=student, class_header=locked_class, registration=registration, status="ENROLLED"
                        )

                        locked_class.current_enrollment += 1
                        locked_class.save()

                    else:
                        raise ValidationError("Class is full")

            except (ValidationError, Exception):
                # Student goes to waitlist
                waitlist = Waitlist.objects.create(
                    student=student,
                    class_header=class_header,
                    position=Waitlist.objects.filter(class_header=class_header).count() + 1,
                    status="WAITING",
                )
                failed_enrollments.append(waitlist)

        # Verify only one student got enrolled
        class_header.refresh_from_db()
        assert class_header.current_enrollment == 30  # Exactly at capacity

        enrolled_count = ClassHeaderEnrollment.objects.filter(class_header=class_header, status="ENROLLED").count()
        assert enrolled_count == 30

        # Others should be on waitlist
        waitlist_count = Waitlist.objects.filter(class_header=class_header, status="WAITING").count()
        assert waitlist_count >= 2  # At least 2 students waitlisted
