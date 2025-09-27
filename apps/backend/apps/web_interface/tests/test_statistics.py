"""
Statistics calculation tests for web interface views.

This module tests that statistics are calculated efficiently in the database
rather than in Python, and that the results are accurate.
"""

from django.test import TestCase

from apps.common.factories import UserFactory
from apps.curriculum.models import Course, Division, Major, Term
from apps.enrollment.models import ClassHeaderEnrollment
from apps.people.models import Person, StudentProfile
from apps.scheduling.models import ClassHeader


class TestStatisticsCalculation(TestCase):
    """Test suite for statistics calculation optimizations."""

    def setUp(self):
        """Set up test data with known statistics."""
        # Create test data
        self.division = Division.objects.create(name="Test Division", code="TEST")

        self.major = Major.objects.create(name="Test Major", code="TMAJ", division=self.division)

        self.term = Term.objects.create(
            name="Test Term", start_date="2024-01-01", end_date="2024-05-01", is_active=True
        )

        # Create classes with known enrollment patterns
        self.classes = []

        # Class 1: Full class (10/10)
        course1 = Course.objects.create(
            title="Full Course",
            course_code="FULL001",
            credit_hours=3,
            division=self.division,
            major=self.major,
            is_active=True,
        )
        class1 = ClassHeader.objects.create(course=course1, term=self.term, max_enrollment=10, is_active=True)
        self.classes.append(class1)

        # Class 2: Nearly full class (8/10 = 80%)
        course2 = Course.objects.create(
            title="Nearly Full Course",
            course_code="NEAR001",
            credit_hours=3,
            division=self.division,
            major=self.major,
            is_active=True,
        )
        class2 = ClassHeader.objects.create(course=course2, term=self.term, max_enrollment=10, is_active=True)
        self.classes.append(class2)

        # Class 3: Half full class (5/10)
        course3 = Course.objects.create(
            title="Half Full Course",
            course_code="HALF001",
            credit_hours=3,
            division=self.division,
            major=self.major,
            is_active=True,
        )
        class3 = ClassHeader.objects.create(course=course3, term=self.term, max_enrollment=10, is_active=True)
        self.classes.append(class3)

        # Create students and enrollments to match the pattern above
        students = []
        for i in range(23):  # 10 + 8 + 5 = 23 total enrollments
            person = Person.objects.create(first_name=f"Student{i}", last_name="Test", email=f"student{i}@example.com")
            student = StudentProfile.objects.create(person=person, student_id=f"STU{i:03d}")
            students.append(student)

        # Enroll students according to our pattern
        student_index = 0

        # Full class: 10 students
        for _i in range(10):
            ClassHeaderEnrollment.objects.create(
                student=students[student_index], class_header=class1, status="ENROLLED"
            )
            student_index += 1

        # Nearly full class: 8 students
        for _i in range(8):
            ClassHeaderEnrollment.objects.create(
                student=students[student_index], class_header=class2, status="ENROLLED"
            )
            student_index += 1

        # Half full class: 5 students
        for _i in range(5):
            ClassHeaderEnrollment.objects.create(
                student=students[student_index], class_header=class3, status="ENROLLED"
            )
            student_index += 1

    def test_statistics_calculation_accuracy(self):
        """Verify database-calculated statistics match expected values."""
        from django.db.models import Case, Count, F, IntegerField, Q, Sum, When

        # Use the same logic as the optimized view
        classes_queryset = ClassHeader.objects.filter(term=self.term).annotate(
            enrolled_count=Count("class_header_enrollments", filter=Q(class_header_enrollments__status="ENROLLED")),
            seats_available=Case(
                When(max_enrollment__gt=F("enrolled_count"), then=F("max_enrollment") - F("enrolled_count")),
                default=0,
                output_field=IntegerField(),
            ),
        )

        # Calculate statistics
        stats = classes_queryset.aggregate(
            available_seats=Sum("seats_available"),
            nearly_full=Count("id", filter=Q(enrolled_count__gte=F("max_enrollment") * 0.8)),
            full_classes=Count("id", filter=Q(enrolled_count__gte=F("max_enrollment"))),
            total_enrolled=Sum("enrolled_count"),
        )

        # Convert None values to 0
        stats = {key: value or 0 for key, value in stats.items()}

        # Verify expected values
        # Available seats: Class1(0) + Class2(2) + Class3(5) = 7
        self.assertEqual(stats["available_seats"], 7)

        # Nearly full classes: Class1(100% >= 80%) + Class2(80% >= 80%) = 2
        self.assertEqual(stats["nearly_full"], 2)

        # Full classes: Only Class1 (100% >= 100%) = 1
        self.assertEqual(stats["full_classes"], 1)

        # Total enrolled: 10 + 8 + 5 = 23
        self.assertEqual(stats["total_enrolled"], 23)

    def test_statistics_performance(self):
        """Verify statistics are calculated efficiently in the database."""
        from django.db.models import Case, Count, F, IntegerField, Q, Sum, When

        # The entire statistics calculation should be a single aggregate query
        with self.assertNumQueries(1):
            classes_queryset = ClassHeader.objects.filter(term=self.term).annotate(
                enrolled_count=Count(
                    "class_header_enrollments", filter=Q(class_header_enrollments__status="ENROLLED")
                ),
                seats_available=Case(
                    When(max_enrollment__gt=F("enrolled_count"), then=F("max_enrollment") - F("enrolled_count")),
                    default=0,
                    output_field=IntegerField(),
                ),
            )

            # This should be the only query executed
            classes_queryset.aggregate(
                available_seats=Sum("seats_available"),
                nearly_full=Count("id", filter=Q(enrolled_count__gte=F("max_enrollment") * 0.8)),
                full_classes=Count("id", filter=Q(enrolled_count__gte=F("max_enrollment"))),
                total_enrolled=Sum("enrolled_count"),
            )

    def test_enrollment_management_view_statistics_performance(self):
        """Test that the actual EnrollmentManagementView uses efficient statistics."""
        staff_user = UserFactory()
        staff_user.is_staff = True
        staff_user.save()
        self.client.force_login(staff_user)

        # The view should load efficiently with database-calculated stats
        # Allow reasonable queries: 1 for current term, 1 for available terms,
        # 1 for classes with stats, 1 for recent enrollments, 1 for pending enrollments
        with self.assertNumQueries(5):
            response = self.client.get("/academic/enrollment/")

        self.assertEqual(response.status_code, 200)

        # Verify statistics are in the context and accurate
        stats = response.context["stats"]
        self.assertEqual(stats["available_seats"], 7)
        self.assertEqual(stats["nearly_full"], 2)
        self.assertEqual(stats["full_classes"], 1)
        self.assertEqual(stats["total_enrolled"], 23)

    def test_statistics_with_no_classes(self):
        """Test statistics calculation when no classes exist."""
        from django.db.models import Case, Count, F, IntegerField, Q, Sum, When

        # Create empty term
        empty_term = Term.objects.create(
            name="Empty Term", start_date="2024-06-01", end_date="2024-10-01", is_active=False
        )

        classes_queryset = ClassHeader.objects.filter(term=empty_term).annotate(
            enrolled_count=Count("class_header_enrollments", filter=Q(class_header_enrollments__status="ENROLLED")),
            seats_available=Case(
                When(max_enrollment__gt=F("enrolled_count"), then=F("max_enrollment") - F("enrolled_count")),
                default=0,
                output_field=IntegerField(),
            ),
        )

        stats = classes_queryset.aggregate(
            available_seats=Sum("seats_available"),
            nearly_full=Count("id", filter=Q(enrolled_count__gte=F("max_enrollment") * 0.8)),
            full_classes=Count("id", filter=Q(enrolled_count__gte=F("max_enrollment"))),
            total_enrolled=Sum("enrolled_count"),
        )

        # Convert None values to 0
        stats = {key: value or 0 for key, value in stats.items()}

        # All statistics should be 0 when no classes exist
        self.assertEqual(stats["available_seats"], 0)
        self.assertEqual(stats["nearly_full"], 0)
        self.assertEqual(stats["full_classes"], 0)
        self.assertEqual(stats["total_enrolled"], 0)
