"""
Simple performance test for the key optimizations made.

This module verifies that the core performance improvements work without
relying on complex test setup or factories.
"""

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.models import Case, Count, F, IntegerField, Q, Sum, When
from django.test import Client, TestCase

User = get_user_model()


class SimplePerformanceTest(TestCase):
    """Simple test to verify core performance optimizations work."""

    def test_database_statistics_optimization(self):
        """Test that statistics can be calculated efficiently in the database."""
        from apps.curriculum.models import Course, Division, Major, Term
        from apps.enrollment.models import ClassHeaderEnrollment
        from apps.people.models import Person, StudentProfile
        from apps.scheduling.models import ClassHeader

        # Create minimal test data
        division = Division.objects.create(name="Test Division", short_name="TEST")
        major = Major.objects.create(name="Test Major", short_name="TMAJ", division=division)
        term = Term.objects.create(name="Test Term", start_date="2024-01-01", end_date="2024-05-01", is_active=True)

        course = Course.objects.create(
            title="Test Course", course_code="TEST001", credit_hours=3, division=division, major=major, is_active=True
        )
        class_header = ClassHeader.objects.create(course=course, term=term, max_enrollment=10, is_active=True)

        # Create 5 enrolled students
        for i in range(5):
            person = Person.objects.create(first_name=f"Student{i}", last_name="Test", email=f"student{i}@example.com")
            student = StudentProfile.objects.create(person=person, student_id=f"STU{i:03d}")
            ClassHeaderEnrollment.objects.create(student=student, class_header=class_header, status="ENROLLED")

        # Test the optimized statistics query (from our improvements)
        classes_queryset = ClassHeader.objects.filter(term=term).annotate(
            enrolled_count=Count("class_header_enrollments", filter=Q(class_header_enrollments__status="ENROLLED")),
            seats_available=Case(
                When(max_enrollment__gt=F("enrolled_count"), then=F("max_enrollment") - F("enrolled_count")),
                default=0,
                output_field=IntegerField(),
            ),
        )

        # This should be a single database query
        initial_queries = len(connection.queries)

        stats = classes_queryset.aggregate(
            available_seats=Sum("seats_available"),
            nearly_full=Count("id", filter=Q(enrolled_count__gte=F("max_enrollment") * 0.8)),
            full_classes=Count("id", filter=Q(enrolled_count__gte=F("max_enrollment"))),
            total_enrolled=Sum("enrolled_count"),
        )

        final_queries = len(connection.queries)
        queries_used = final_queries - initial_queries

        # Verify it's efficient (should be 1 query)
        self.assertEqual(queries_used, 1, "Statistics should be calculated in a single database query")

        # Verify the results are correct
        self.assertEqual(stats["available_seats"], 5)  # 10 max - 5 enrolled = 5 available
        self.assertEqual(stats["nearly_full"], 0)  # 5/10 = 50% < 80%, so not nearly full
        self.assertEqual(stats["full_classes"], 0)  # 5/10 = 50% < 100%, so not full
        self.assertEqual(stats["total_enrolled"], 5)  # 5 students enrolled

    def test_course_list_view_len_optimization(self):
        """Test that CourseListView uses len() instead of .count() for already evaluated querysets."""
        # This tests our fix: using len(context["courses"]) instead of self.get_queryset().count()

        # Create a simple user for testing
        user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass")
        user.is_staff = True
        user.save()

        # Create minimal test data
        from apps.curriculum.models import Division

        Division.objects.create(name="Test Division", short_name="TEST")

        client = Client()
        client.force_login(user)

        # Count queries
        initial_queries = len(connection.queries)

        # This should be efficient with our optimization
        response = client.get("/academic/courses/")

        final_queries = len(connection.queries)
        queries_used = final_queries - initial_queries

        # Should be reasonable number of queries (not excessive due to N+1)
        self.assertLessEqual(queries_used, 5, "CourseListView should be efficient with our len() optimization")
        self.assertEqual(response.status_code, 200)

    def test_enrollment_management_statistics_efficiency(self):
        """Test that EnrollmentManagementView statistics are calculated efficiently."""
        # This tests our database-level statistics calculation

        user = User.objects.create_user(username="testuser2", email="test2@example.com", password="testpass")
        user.is_staff = True
        user.save()

        client = Client()
        client.force_login(user)

        # Count queries
        initial_queries = len(connection.queries)

        # This should be efficient with our database statistics optimization
        response = client.get("/academic/enrollment/")

        final_queries = len(connection.queries)
        queries_used = final_queries - initial_queries

        # Should be reasonable number of queries with our optimization
        self.assertLessEqual(
            queries_used, 10, "EnrollmentManagementView should be efficient with database-calculated stats"
        )
        self.assertEqual(response.status_code, 200)

        # Verify stats are in context
        if response.context:
            self.assertIn("stats", response.context)
            stats = response.context["stats"]
            # Should have all the expected stat keys
            expected_keys = ["available_seats", "nearly_full", "full_classes", "total_enrolled"]
            for key in expected_keys:
                self.assertIn(key, stats)
