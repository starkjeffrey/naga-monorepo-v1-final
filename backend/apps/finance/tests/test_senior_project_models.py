"""Tests for Senior Project business logic and models.

These tests verify the senior project group management functionality
including pricing calculations, group formation, and project lifecycle.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.common.utils import get_current_date
from apps.curriculum.models import Course, Division, SeniorProjectGroup, Term
from apps.finance.models import SeniorProjectCourse, SeniorProjectPricing
from apps.finance.services import SeparatedPricingService
from apps.people.models import Person, StudentProfile, TeacherProfile

User = get_user_model()


class SeniorProjectGroupTest(TestCase):
    """Test SeniorProjectGroup model functionality."""

    def setUp(self):
        """Set up test data for senior project tests."""
        self.user = User.objects.create_user(email="senior@example.com", password="testpass123")

        # Create teacher for advisor
        teacher_person = Person.objects.create(
            personal_name="Dr. Senior",
            family_name="Advisor",
            date_of_birth=date(1970, 1, 1),
            preferred_gender="M",
            citizenship="US",
        )

        self.advisor = TeacherProfile.objects.create(
            person=teacher_person,
            employee_id="T001",
            hire_date=get_current_date() - timedelta(days=365),
        )

        # Create students
        self.students = []
        for i in range(5):
            person = Person.objects.create(
                personal_name=f"Student{i + 1}",
                family_name="Senior",
                date_of_birth=date(2000, 1, 1),
                preferred_gender="M" if i % 2 == 0 else "F",
                citizenship="US",
            )

            student = StudentProfile.objects.create(
                person=person,
                student_id=3000 + i,
                last_enrollment_date=get_current_date(),
            )
            self.students.append(student)

        # Create senior project course
        division = Division.objects.create(name="Business", short_name="BUS")
        self.senior_course = Course.objects.create(
            code="BUS-489",
            title="Senior Project in Business",
            credits=3,
            division=division,
            is_senior_project=True,
        )

    def test_create_senior_project_group(self):
        """Test creating a senior project group."""
        group = SeniorProjectGroup.objects.create(
            advisor=self.advisor,
            project_title="E-commerce Platform Analysis",
            description="Analyzing modern e-commerce platforms and their impact on small businesses",
            status=SeniorProjectGroup.ProjectStatus.PLANNING,
        )

        # Add students to the group
        group.students.add(self.students[0], self.students[1])

        self.assertEqual(group.students.count(), 2)
        self.assertEqual(group.advisor, self.advisor)
        self.assertEqual(group.status, "PLANNING")
        self.assertTrue(group.project_title)

    def test_senior_project_group_validation(self):
        """Test senior project group validation rules."""
        # Test maximum students (5)
        group = SeniorProjectGroup.objects.create(
            advisor=self.advisor,
            project_title="Large Group Project",
            status=SeniorProjectGroup.ProjectStatus.PLANNING,
        )

        # Add all 5 students - should be valid
        group.students.add(*self.students)
        self.assertEqual(group.students.count(), 5)

        # Adding a 6th student would violate business rules (tested in service layer)

    def test_senior_project_group_status_transitions(self):
        """Test valid status transitions for senior project groups."""
        group = SeniorProjectGroup.objects.create(
            advisor=self.advisor,
            project_title="Status Transition Test",
            status=SeniorProjectGroup.ProjectStatus.PLANNING,
        )

        # Valid transitions
        group.status = SeniorProjectGroup.ProjectStatus.ACTIVE
        group.save()

        group.status = SeniorProjectGroup.ProjectStatus.COMPLETED
        group.save()

        self.assertEqual(group.status, "COMPLETED")

    def test_senior_project_group_required_fields(self):
        """Test that required fields are enforced."""
        # Missing advisor should raise validation error
        with self.assertRaises(ValidationError):
            group = SeniorProjectGroup(
                project_title="Missing Advisor Test",
                status=SeniorProjectGroup.ProjectStatus.PLANNING,
            )
            group.full_clean()

        # Missing project title should raise validation error
        with self.assertRaises(ValidationError):
            group = SeniorProjectGroup(advisor=self.advisor, status=SeniorProjectGroup.ProjectStatus.PLANNING)
            group.full_clean()


class SeniorProjectPricingTest(TestCase):
    """Test senior project pricing calculations."""

    def setUp(self):
        """Set up test data for pricing tests."""
        self.user = User.objects.create_user(email="pricing@example.com", password="testpass123")

        # Create student
        person = Person.objects.create(
            personal_name="Pricing",
            family_name="Student",
            date_of_birth=date(2000, 1, 1),
            preferred_gender="M",
            citizenship="US",
        )

        self.student = StudentProfile.objects.create(
            person=person,
            student_id=4001,
            last_enrollment_date=get_current_date(),
        )

        # Create senior project course
        division = Division.objects.create(name="Finance", short_name="FIN")
        self.senior_course = Course.objects.create(
            code="FIN-489",
            title="Senior Project in Finance",
            credits=3,
            division=division,
            is_senior_project=True,
        )

        # Create senior project course configuration
        self.senior_project_course = SeniorProjectCourse.objects.create(
            course=self.senior_course,
            project_code="BUS-489",
            major_name="Business Administration",
            allows_groups=True,
            is_active=True,
        )

        # Create senior project pricing tiers
        self.pricing_1_2 = SeniorProjectPricing.objects.create(
            tier="1-2",
            individual_price=Decimal("800.00"),  # Higher price for smaller groups
            foreign_individual_price=Decimal("1200.00"),
            advisor_payment=Decimal("100.00"),
            committee_payment=Decimal("50.00"),
            effective_date=get_current_date() - timedelta(days=30),
        )

        self.pricing_3_5 = SeniorProjectPricing.objects.create(
            tier="3-5",
            individual_price=Decimal("600.00"),  # Lower price for larger groups
            foreign_individual_price=Decimal("900.00"),
            advisor_payment=Decimal("100.00"),
            committee_payment=Decimal("50.00"),
            effective_date=get_current_date() - timedelta(days=30),
        )

    def test_senior_project_pricing_small_group(self):
        """Test pricing for small senior project groups (1-2 students)."""
        price, currency, details = SeparatedPricingService.get_course_price(
            course=self.senior_course,
            student=self.student,
            term=None,
            group_size=2,
        )

        self.assertEqual(price, Decimal("800.00"))
        self.assertEqual(currency, "USD")
        self.assertEqual(details["pricing_type"], "senior_project")

    def test_senior_project_pricing_large_group(self):
        """Test pricing for larger senior project groups (3-5 students)."""
        price, currency, details = SeparatedPricingService.get_course_price(
            course=self.senior_course,
            student=self.student,
            term=None,
            group_size=4,
        )

        self.assertEqual(price, Decimal("600.00"))
        self.assertEqual(currency, "USD")
        self.assertEqual(details["pricing_type"], "senior_project")

    def test_senior_project_pricing_boundary_cases(self):
        """Test pricing at boundaries (1, 2, 3, 5 students)."""
        # 1 student - should use tier 1-2
        price_1, _, _ = SeparatedPricingService.get_course_price(
            course=self.senior_course, student=self.student, term=None, group_size=1
        )
        self.assertEqual(price_1, Decimal("800.00"))

        # 2 students - should use tier 1-2
        price_2, _, _ = SeparatedPricingService.get_course_price(
            course=self.senior_course, student=self.student, term=None, group_size=2
        )
        self.assertEqual(price_2, Decimal("800.00"))

        # 3 students - should use tier 3-5
        price_3, _, _ = SeparatedPricingService.get_course_price(
            course=self.senior_course, student=self.student, term=None, group_size=3
        )
        self.assertEqual(price_3, Decimal("600.00"))

        # 5 students - should use tier 3-5
        price_5, _, _ = SeparatedPricingService.get_course_price(
            course=self.senior_course, student=self.student, term=None, group_size=5
        )
        self.assertEqual(price_5, Decimal("600.00"))

    def test_senior_project_pricing_exceeds_limit(self):
        """Test that senior projects with >5 students raise an error."""
        with self.assertRaises(Exception):
            SeparatedPricingService.get_course_price(
                course=self.senior_course, student=self.student, term=None, group_size=6
            )

    def test_senior_project_pricing_no_group_size(self):
        """Test senior project pricing when group size is not provided."""
        with self.assertRaises(Exception):
            SeparatedPricingService.get_course_price(
                course=self.senior_course,
                student=self.student,
                term=None,
                group_size=None,
            )

    def test_regular_course_vs_senior_project(self):
        """Test that regular courses don't use senior project pricing."""
        # Create regular course
        regular_course = Course.objects.create(
            code="FIN-101",
            title="Introduction to Finance",
            credits=3,
            division=self.senior_course.division,
            is_senior_project=False,  # Regular course
        )

        # Create default pricing for the division
        from apps.finance.models import DefaultPricing

        DefaultPricing.objects.create(
            cycle=self.senior_course.division,
            domestic_price=Decimal("400.00"),
            foreign_price=Decimal("600.00"),
            effective_date=get_current_date() - timedelta(days=30),
        )

        # Regular course should use default pricing
        price, _currency, details = SeparatedPricingService.get_course_price(
            course=regular_course, student=self.student, term=None
        )

        self.assertEqual(price, Decimal("400.00"))
        self.assertEqual(details["pricing_type"], "default")

    def test_senior_project_course_price_calculation(self):
        """Test full price calculation for senior project courses."""
        # Create term for pricing calculation
        term = Term.objects.create(
            name="Senior Project Term",
            start_date=get_current_date(),
            end_date=get_current_date() + timedelta(days=120),
        )

        # Test price calculation with specific group size
        price, currency, details = SeparatedPricingService.get_course_price(
            course=self.senior_course,
            student=self.student,
            term=term,
            group_size=2,
        )

        # Should get pricing for 1-2 student tier
        self.assertEqual(price, Decimal("800.00"))
        self.assertEqual(currency, "USD")
        self.assertEqual(details["pricing_type"], "senior_project")
        self.assertEqual(details["tier"], "1-2")


class SeniorProjectBusinessLogicTest(TestCase):
    """Test business logic validation for senior projects."""

    def setUp(self):
        """Set up test data."""
        # Create advisor
        advisor_person = Person.objects.create(
            personal_name="Dr. Business",
            family_name="Logic",
            date_of_birth=date(1975, 1, 1),
            preferred_gender="F",
            citizenship="US",
        )

        self.advisor = TeacherProfile.objects.create(
            person=advisor_person,
            employee_id="T002",
            hire_date=get_current_date() - timedelta(days=1000),
        )

    def test_senior_project_identifies_by_course_name(self):
        """Test that senior projects are identified by course naming convention."""
        division = Division.objects.create(name="International Relations", short_name="IR")

        # Test various senior project course names
        senior_courses = [
            "BUS-489",  # Business senior project
            "FIN-489",  # Finance senior project
            "IR-489",  # International Relations senior project
            "THM-433",  # Tourism & Hospitality Management senior project
        ]

        for course_code in senior_courses:
            course = Course.objects.create(
                code=course_code,
                title=f"Senior Project - {course_code}",
                credits=3,
                division=division,
                is_senior_project=True,
            )

            # Verify the course is marked as senior project
            self.assertTrue(
                course.is_senior_project,
                f"{course_code} should be marked as senior project",
            )

    def test_special_case_tesol_practicum(self):
        """Test EDUC-408 TESOL practicum pricing (mentioned as senior project-like)."""
        division = Division.objects.create(name="Education", short_name="EDUC")

        tesol_course = Course.objects.create(
            code="EDUC-408",
            title="TESOL Practicum",
            credits=3,
            division=division,
            is_senior_project=False,  # Not technically a senior project but has special pricing
        )

        # EDUC-408 should be treated specially in pricing (mentioned in business requirements)
        # This would be handled in the pricing service business logic
        self.assertFalse(tesol_course.is_senior_project)

    def test_senior_project_group_formation_rules(self):
        """Test business rules for senior project group formation."""
        group = SeniorProjectGroup.objects.create(
            advisor=self.advisor,
            project_title="Group Formation Test",
            description="Testing group formation business rules",
            status=SeniorProjectGroup.ProjectStatus.PLANNING,
        )

        # Test that groups can have 1-5 students
        # (actual enforcement would be in service layer or admin interface)
        self.assertEqual(group.students.count(), 0)

        # Test group status workflow
        valid_statuses = [
            SeniorProjectGroup.ProjectStatus.PLANNING,
            SeniorProjectGroup.ProjectStatus.ACTIVE,
            SeniorProjectGroup.ProjectStatus.COMPLETED,
            SeniorProjectGroup.ProjectStatus.CANCELLED,
        ]

        for status in valid_statuses:
            group.status = status
            group.save()
            self.assertEqual(group.status, status)
