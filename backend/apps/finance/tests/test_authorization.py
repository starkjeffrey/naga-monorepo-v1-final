"""Tests for finance API authorization and access control.

These tests verify that the enhanced authorization system properly
controls access to financial data based on user roles and relationships.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from ninja.errors import HttpError

from apps.common.utils import get_current_date
from apps.curriculum.models import Term
from apps.finance.api import (
    can_access_student_financial_data,
    can_modify_student_financial_data,
    verify_invoice_access,
    verify_invoice_modify,
    verify_payment_access,
    verify_payment_modify,
)
from apps.finance.models import Invoice, Payment
from apps.people.models import Person, StudentProfile

User = get_user_model()


class FinanceAuthorizationTest(TestCase):
    """Test finance authorization helper functions."""

    def setUp(self):
        """Set up test data for authorization tests."""
        # Create users with different roles
        self.superuser = User.objects.create_user(
            email="admin@example.com",
            password="testpass123",
            is_superuser=True,
            is_staff=True,
        )

        self.staff_user = User.objects.create_user(email="staff@example.com", password="testpass123", is_staff=True)

        self.regular_user = User.objects.create_user(email="user@example.com", password="testpass123", is_staff=False)

        # Create student person and profile
        student_person = Person.objects.create(
            personal_name="Student",
            family_name="Test",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="M",
            citizenship="US",
        )

        self.student = StudentProfile.objects.create(
            person=student_person,
            student_id=5001,
            last_enrollment_date=get_current_date(),
        )

        other_student_person = Person.objects.create(
            personal_name="Other",
            family_name="Student",
            date_of_birth=date(2001, 1, 1),
            preferred_gender="F",
            citizenship="US",
        )

        self.other_student = StudentProfile.objects.create(
            person=other_student_person,
            student_id=5002,
            last_enrollment_date=get_current_date(),
        )

        # Create student user (user who is also a student)
        self.student_user = User.objects.create_user(
            email="student@example.com",
            password="testpass123",
            is_staff=False,
        )

        # Link student user to student profile
        student_user_person = Person.objects.create(
            personal_name="User",
            family_name="Student",
            date_of_birth=date(1999, 1, 1),
            preferred_gender="M",
            citizenship="US",
        )

        self.student_user_profile = StudentProfile.objects.create(
            person=student_user_person,
            student_id=5003,
            last_enrollment_date=get_current_date(),
        )

        # Link the user to the person
        self.student_user.person = student_user_person
        self.student_user.save()

    def test_can_access_student_financial_data_superuser(self):
        """Test that superusers can access all student financial data."""
        result = can_access_student_financial_data(self.superuser, self.student)
        self.assertTrue(result, "Superuser should be able to access all student data")

        result = can_access_student_financial_data(self.superuser, self.other_student)
        self.assertTrue(result, "Superuser should be able to access any student data")

    def test_can_access_student_financial_data_staff(self):
        """Test that staff users can access student financial data."""
        result = can_access_student_financial_data(self.staff_user, self.student)
        self.assertTrue(result, "Staff user should be able to access student data")

        result = can_access_student_financial_data(self.staff_user, self.other_student)
        self.assertTrue(result, "Staff user should be able to access any student data")

    def test_can_access_student_financial_data_own_data(self):
        """Test that students can access their own financial data."""
        result = can_access_student_financial_data(self.student_user, self.student_user_profile)
        self.assertTrue(result, "Student should be able to access their own financial data")

    def test_can_access_student_financial_data_other_student(self):
        """Test that students cannot access other students' financial data."""
        result = can_access_student_financial_data(self.student_user, self.student)
        self.assertFalse(result, "Student should not be able to access other students' data")

    def test_can_access_student_financial_data_regular_user(self):
        """Test that regular users cannot access student financial data."""
        result = can_access_student_financial_data(self.regular_user, self.student)
        self.assertFalse(result, "Regular user should not be able to access student data")

    def test_can_modify_student_financial_data_superuser(self):
        """Test that superusers can modify student financial data."""
        result = can_modify_student_financial_data(self.superuser, self.student)
        self.assertTrue(result, "Superuser should be able to modify student financial data")

    def test_can_modify_student_financial_data_staff(self):
        """Test that staff users can modify student financial data."""
        result = can_modify_student_financial_data(self.staff_user, self.student)
        self.assertTrue(result, "Staff user should be able to modify student financial data")

    def test_can_modify_student_financial_data_student(self):
        """Test that students cannot modify financial data."""
        result = can_modify_student_financial_data(self.student_user, self.student_user_profile)
        self.assertFalse(result, "Students should not be able to modify financial data")

    def test_can_modify_student_financial_data_regular_user(self):
        """Test that regular users cannot modify student financial data."""
        result = can_modify_student_financial_data(self.regular_user, self.student)
        self.assertFalse(result, "Regular user should not be able to modify student financial data")


class InvoiceAuthorizationTest(TestCase):
    """Test invoice-specific authorization functions."""

    def setUp(self):
        """Set up test data for invoice authorization tests."""
        # Create users
        self.staff_user = User.objects.create_user(
            email="invoice_staff@example.com",
            password="testpass123",
            is_staff=True,
        )

        self.regular_user = User.objects.create_user(
            email="invoice_user@example.com",
            password="testpass123",
            is_staff=False,
        )

        # Create student
        student_person = Person.objects.create(
            personal_name="Invoice",
            family_name="Student",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="F",
            citizenship="US",
        )

        self.student = StudentProfile.objects.create(
            person=student_person,
            student_id=6001,
            last_enrollment_date=get_current_date(),
        )

        # Create term and invoice
        self.term = Term.objects.create(
            name="Invoice Test Term",
            start_date=get_current_date(),
            end_date=get_current_date() + timedelta(days=90),
        )

        self.invoice = Invoice.objects.create(
            invoice_number="AUTH-TEST-001",
            student=self.student,
            term=self.term,
            issue_date=get_current_date(),
            due_date=get_current_date() + timedelta(days=30),
            subtotal=Decimal("500.00"),
            total_amount=Decimal("500.00"),
            currency="USD",
        )

    def test_verify_invoice_access_authorized(self):
        """Test invoice access verification for authorized users."""
        # Staff user should be able to access invoice
        try:
            verify_invoice_access(self.staff_user, self.invoice)
            # If no exception raised, test passes
        except HttpError:
            self.fail("Staff user should be able to access invoice")

    def test_verify_invoice_access_unauthorized(self):
        """Test invoice access verification for unauthorized users."""
        # Regular user should not be able to access invoice
        with self.assertRaises(HttpError) as context:
            verify_invoice_access(self.regular_user, self.invoice)

        self.assertEqual(context.exception.status_code, 403)
        self.assertIn("Permission denied", str(context.exception))

    def test_verify_invoice_modify_authorized(self):
        """Test invoice modification verification for authorized users."""
        # Staff user should be able to modify invoice
        try:
            verify_invoice_modify(self.staff_user, self.invoice)
            # If no exception raised, test passes
        except HttpError:
            self.fail("Staff user should be able to modify invoice")

    def test_verify_invoice_modify_unauthorized(self):
        """Test invoice modification verification for unauthorized users."""
        # Regular user should not be able to modify invoice
        with self.assertRaises(HttpError) as context:
            verify_invoice_modify(self.regular_user, self.invoice)

        self.assertEqual(context.exception.status_code, 403)
        self.assertIn("Permission denied", str(context.exception))


class PaymentAuthorizationTest(TestCase):
    """Test payment-specific authorization functions."""

    def setUp(self):
        """Set up test data for payment authorization tests."""
        # Create users
        self.staff_user = User.objects.create_user(
            email="payment_staff@example.com",
            password="testpass123",
            is_staff=True,
        )

        self.regular_user = User.objects.create_user(
            email="payment_user@example.com",
            password="testpass123",
            is_staff=False,
        )

        # Create student
        student_person = Person.objects.create(
            personal_name="Payment",
            family_name="Student",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="M",
            citizenship="US",
        )

        self.student = StudentProfile.objects.create(
            person=student_person,
            student_id=7001,
            last_enrollment_date=get_current_date(),
        )

        # Create term, invoice, and payment
        self.term = Term.objects.create(
            name="Payment Test Term",
            start_date=get_current_date(),
            end_date=get_current_date() + timedelta(days=90),
        )

        self.invoice = Invoice.objects.create(
            invoice_number="PAY-AUTH-001",
            student=self.student,
            term=self.term,
            issue_date=get_current_date(),
            due_date=get_current_date() + timedelta(days=30),
            subtotal=Decimal("300.00"),
            total_amount=Decimal("300.00"),
            currency="USD",
        )

        self.payment = Payment.objects.create(
            payment_reference="PAY-AUTH-TEST-001",
            invoice=self.invoice,
            amount=Decimal("300.00"),
            currency="USD",
            payment_method="CASH",
            payment_date=get_current_date(),
            status=Payment.PaymentStatus.COMPLETED,
            payer_name="Payment Student",
            processed_by=self.staff_user,
        )

    def test_verify_payment_access_authorized(self):
        """Test payment access verification for authorized users."""
        # Staff user should be able to access payment
        try:
            verify_payment_access(self.staff_user, self.payment)
            # If no exception raised, test passes
        except HttpError:
            self.fail("Staff user should be able to access payment")

    def test_verify_payment_access_unauthorized(self):
        """Test payment access verification for unauthorized users."""
        # Regular user should not be able to access payment
        with self.assertRaises(HttpError) as context:
            verify_payment_access(self.regular_user, self.payment)

        self.assertEqual(context.exception.status_code, 403)
        self.assertIn("Permission denied", str(context.exception))

    def test_verify_payment_modify_authorized(self):
        """Test payment modification verification for authorized users."""
        # Staff user should be able to modify payment
        try:
            verify_payment_modify(self.staff_user, self.payment)
            # If no exception raised, test passes
        except HttpError:
            self.fail("Staff user should be able to modify payment")

    def test_verify_payment_modify_unauthorized(self):
        """Test payment modification verification for unauthorized users."""
        # Regular user should not be able to modify payment
        with self.assertRaises(HttpError) as context:
            verify_payment_modify(self.regular_user, self.payment)

        self.assertEqual(context.exception.status_code, 403)
        self.assertIn("Permission denied", str(context.exception))


class RoleBasedAccessTest(TestCase):
    """Test role-based access patterns across the finance system."""

    def setUp(self):
        """Set up comprehensive test data for role-based testing."""
        # Create users with different permission levels
        self.admin = User.objects.create_user(
            email="admin@naga.edu",
            password="testpass123",
            is_superuser=True,
            is_staff=True,
        )

        self.finance_staff = User.objects.create_user(email="finance@naga.edu", password="testpass123", is_staff=True)

        self.teacher = User.objects.create_user(email="teacher@naga.edu", password="testpass123", is_staff=False)

        self.student_user = User.objects.create_user(email="student@naga.edu", password="testpass123", is_staff=False)

        # Create student profile linked to user
        student_person = Person.objects.create(
            personal_name="Role",
            family_name="Student",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="M",
            citizenship="US",
        )

        self.student_profile = StudentProfile.objects.create(
            person=student_person,
            student_id=8001,
            last_enrollment_date=get_current_date(),
        )

        # Link student user to profile
        self.student_user.person = student_person
        self.student_user.save()

    def test_admin_full_access(self):
        """Test that admins have full access to all financial operations."""
        # Admin can access any student's data
        self.assertTrue(can_access_student_financial_data(self.admin, self.student_profile))

        # Admin can modify any student's data
        self.assertTrue(can_modify_student_financial_data(self.admin, self.student_profile))

    def test_finance_staff_access(self):
        """Test that finance staff have appropriate access levels."""
        # Finance staff can access student data
        self.assertTrue(can_access_student_financial_data(self.finance_staff, self.student_profile))

        # Finance staff can modify student data
        self.assertTrue(can_modify_student_financial_data(self.finance_staff, self.student_profile))

    def test_teacher_limited_access(self):
        """Test that teachers have limited access (view only for their students)."""
        # Current implementation allows all staff access
        # In a more refined system, this would check teacher-student relationships
        # For now, teachers are not staff so they have no access
        self.assertFalse(can_access_student_financial_data(self.teacher, self.student_profile))
        self.assertFalse(can_modify_student_financial_data(self.teacher, self.student_profile))

    def test_student_own_data_access(self):
        """Test that students can only access their own data."""
        # Student can access their own data
        self.assertTrue(can_access_student_financial_data(self.student_user, self.student_profile))

        # Student cannot modify their own financial data
        self.assertFalse(can_modify_student_financial_data(self.student_user, self.student_profile))

    def test_cross_student_access_denied(self):
        """Test that students cannot access other students' data."""
        # Create another student
        other_person = Person.objects.create(
            personal_name="Other",
            family_name="Student",
            date_of_birth=date(2001, 1, 1),
            preferred_gender="F",
            citizenship="US",
        )

        other_student = StudentProfile.objects.create(
            person=other_person,
            student_id=8002,
            last_enrollment_date=get_current_date(),
        )

        # Student should not be able to access other student's data
        self.assertFalse(can_access_student_financial_data(self.student_user, other_student))
        self.assertFalse(can_modify_student_financial_data(self.student_user, other_student))

    def test_permission_hierarchy(self):
        """Test the permission hierarchy works correctly."""
        users_and_expected_access = [
            (self.admin, True, True),  # Admin: full access
            (self.finance_staff, True, True),  # Staff: full access
            (self.teacher, False, False),  # Teacher: no access (not staff)
            (self.student_user, True, False),  # Student: view own, no modify
        ]

        for user, expected_access, expected_modify in users_and_expected_access:
            with self.subTest(user=user.email):
                actual_access = can_access_student_financial_data(user, self.student_profile)
                actual_modify = can_modify_student_financial_data(user, self.student_profile)

                self.assertEqual(
                    actual_access,
                    expected_access,
                    f"{user.email} access permission mismatch",
                )
                self.assertEqual(
                    actual_modify,
                    expected_modify,
                    f"{user.email} modify permission mismatch",
                )
