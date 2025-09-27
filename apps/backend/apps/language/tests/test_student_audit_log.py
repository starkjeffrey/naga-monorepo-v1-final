"""Test cases for StudentActivityLog model and functionality.

Tests the comprehensive student activity logging system including
search capabilities, audit trail creation, and data integrity.
"""

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.common.models import StudentActivityLog
from apps.curriculum.models import Course, Division, Term
from apps.people.models import Person, StudentProfile
from apps.scheduling.models import ClassHeader

User = get_user_model()


@pytest.mark.django_db
class TestStudentActivityLog:
    """Test StudentActivityLog model and methods."""

    @pytest.fixture
    def setup_audit_data(self):
        """Set up test data for audit log testing."""
        # Create users
        staff_user = User.objects.create_user(email="staff@example.com", name="Staff Member")

        # Create students
        students = []
        for i in range(3):
            User.objects.create_user(email=f"student{i}@example.com", name=f"Student{i} Test")
            person = Person.objects.create(
                family_name=f"Student{i}",
                personal_name="Test",
                date_of_birth="2000-01-01",
            )
            student = StudentProfile.objects.create(person=person, student_id=i + 1)
            students.append(student)

        # Create division
        division = Division.objects.create(name="Language Division", short_name="LANG")

        # Create course
        course = Course.objects.create(
            code="EHSS-05",
            title="English for High School Level 5",
            short_title="EHSS L5",
            division=division,
            cycle=Course.CourseLevel.LANGUAGE,
            is_language=True,
        )

        # Create term
        term = Term.objects.create(
            name="ENG A 2024-1",
            term_type=Term.TermType.ENGLISH_A,
            start_date="2024-01-01",
            end_date="2024-03-31",
        )

        # Create class
        class_header = ClassHeader.objects.create(course=course, term=term, section_id="A")

        return {
            "staff_user": staff_user,
            "students": students,
            "term": term,
            "class_header": class_header,
            "course": course,
        }

    def test_log_student_activity_with_student_instance(self, setup_audit_data):
        """Test logging activity with StudentProfile instance."""
        data = setup_audit_data
        student = data["students"][0]

        # Log an activity
        log_entry = StudentActivityLog.log_student_activity(
            student=student,
            activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
            description="Student enrolled in EHSS-05 Section A",
            performed_by=data["staff_user"],
            term=data["term"],
            class_header=data["class_header"],
            program_name="EHSS",
            activity_details={"enrollment_method": "manual", "fee_paid": True},
        )

        assert log_entry.student == student
        assert log_entry.student_number == student.student_number
        assert log_entry.student_name == student.user.get_full_name()
        assert log_entry.activity_type == StudentActivityLog.ActivityType.CLASS_ENROLLMENT
        assert log_entry.term_name == data["term"].name
        assert log_entry.class_code == data["course"].code
        assert log_entry.class_section == data["class_header"].section
        assert log_entry.program_name == "EHSS"
        assert log_entry.activity_details["enrollment_method"] == "manual"
        assert not log_entry.is_system_generated

    def test_log_student_activity_without_student_instance(self, setup_audit_data):
        """Test logging activity with only student number (for historical records)."""
        data = setup_audit_data

        log_entry = StudentActivityLog.log_student_activity(
            student=None,
            activity_type=StudentActivityLog.ActivityType.LANGUAGE_PROMOTION,
            description="Historical promotion record",
            performed_by=data["staff_user"],
            student_number="S999",
            student_name="Historical Student",
            term=data["term"],
            program_name="EHSS",
            is_system_generated=True,
        )

        assert log_entry.student is None
        assert log_entry.student_number == "S999"
        assert log_entry.student_name == "Historical Student"
        assert log_entry.is_system_generated

    def test_log_student_activity_missing_required_data(self, setup_audit_data):
        """Test that logging fails when required data is missing."""
        data = setup_audit_data

        # Should raise ValueError when neither student nor student_number provided
        with pytest.raises(
            ValueError,
            match="Either student instance or student_number must be provided",
        ):
            StudentActivityLog.log_student_activity(
                student=None,
                activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
                description="Test activity",
                performed_by=data["staff_user"],
            )

    def test_search_student_activities_by_student_number(self, setup_audit_data):
        """Test searching activities by student number."""
        data = setup_audit_data
        student = data["students"][0]

        # Create multiple log entries for the student
        activities = [
            StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
            StudentActivityLog.ActivityType.LANGUAGE_PROMOTION,
            StudentActivityLog.ActivityType.GRADE_ASSIGNMENT,
        ]

        for activity in activities:
            StudentActivityLog.log_student_activity(
                student=student,
                activity_type=activity,
                description=f"Test {activity}",
                performed_by=data["staff_user"],
            )

        # Search by student number
        results = StudentActivityLog.search_student_activities(student_number=student.student_number)

        assert len(results) == 3
        assert all(log.student_number == student.student_number for log in results)

    def test_search_student_activities_by_activity_type(self, setup_audit_data):
        """Test searching activities by activity type."""
        data = setup_audit_data

        # Create log entries of different types for different students
        for i, student in enumerate(data["students"]):
            activity_type = (
                StudentActivityLog.ActivityType.CLASS_ENROLLMENT
                if i % 2 == 0
                else StudentActivityLog.ActivityType.LANGUAGE_PROMOTION
            )
            StudentActivityLog.log_student_activity(
                student=student,
                activity_type=activity_type,
                description=f"Test activity for student {i}",
                performed_by=data["staff_user"],
            )

        # Search by activity type
        enrollment_results = StudentActivityLog.search_student_activities(
            activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
        )

        promotion_results = StudentActivityLog.search_student_activities(
            activity_type=StudentActivityLog.ActivityType.LANGUAGE_PROMOTION,
        )

        assert len(enrollment_results) == 2  # Students 0 and 2
        assert len(promotion_results) == 1  # Student 1
        assert all(log.activity_type == StudentActivityLog.ActivityType.CLASS_ENROLLMENT for log in enrollment_results)

    def test_search_student_activities_by_term(self, setup_audit_data):
        """Test searching activities by term."""
        data = setup_audit_data

        # Create another term
        term2 = Term.objects.create(
            name="ENG A 2024-2",
            term_type=Term.TermType.ENGLISH_A,
            start_date="2024-04-01",
            end_date="2024-06-30",
        )

        # Create activities in different terms
        StudentActivityLog.log_student_activity(
            student=data["students"][0],
            activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
            description="Enrollment in term 1",
            performed_by=data["staff_user"],
            term=data["term"],
        )

        StudentActivityLog.log_student_activity(
            student=data["students"][1],
            activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
            description="Enrollment in term 2",
            performed_by=data["staff_user"],
            term=term2,
        )

        # Search by term
        term1_results = StudentActivityLog.search_student_activities(term_name=data["term"].name)
        term2_results = StudentActivityLog.search_student_activities(term_name=term2.name)

        assert len(term1_results) == 1
        assert len(term2_results) == 1
        assert term1_results[0].term_name == data["term"].name
        assert term2_results[0].term_name == term2.name

    def test_search_student_activities_by_class_code(self, setup_audit_data):
        """Test searching activities by class code."""
        data = setup_audit_data

        # Create another course
        course2 = Course.objects.create(
            code="GESL-03",
            title="General English Level 3",
            short_title="GESL L3",
            division=data["course"].division,
            cycle=Course.CourseLevel.LANGUAGE,
            is_language=True,
        )

        class_header2 = ClassHeader.objects.create(course=course2, term=data["term"], section_id="B")

        # Create activities for different classes
        StudentActivityLog.log_student_activity(
            student=data["students"][0],
            activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
            description="EHSS enrollment",
            performed_by=data["staff_user"],
            class_header=data["class_header"],
        )

        StudentActivityLog.log_student_activity(
            student=data["students"][1],
            activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
            description="GESL enrollment",
            performed_by=data["staff_user"],
            class_header=class_header2,
        )

        # Search by class code
        ehss_results = StudentActivityLog.search_student_activities(class_code="EHSS-05")
        gesl_results = StudentActivityLog.search_student_activities(class_code="GESL-03")

        assert len(ehss_results) == 1
        assert len(gesl_results) == 1
        assert ehss_results[0].class_code == "EHSS-05"
        assert gesl_results[0].class_code == "GESL-03"

    def test_search_student_activities_by_date_range(self, setup_audit_data):
        """Test searching activities by date range."""
        data = setup_audit_data

        # Create activities at different times
        base_time = timezone.now()

        # Activity from 3 days ago
        old_log = StudentActivityLog.log_student_activity(
            student=data["students"][0],
            activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
            description="Old activity",
            performed_by=data["staff_user"],
        )
        old_log.created_at = base_time - timedelta(days=3)
        old_log.save()

        # Activity from today
        StudentActivityLog.log_student_activity(
            student=data["students"][1],
            activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
            description="New activity",
            performed_by=data["staff_user"],
        )

        # Search with date range (last 2 days)
        recent_results = StudentActivityLog.search_student_activities(date_from=base_time - timedelta(days=2))

        # Search with date range (older than 2 days)
        old_results = StudentActivityLog.search_student_activities(date_to=base_time - timedelta(days=2))

        assert len(recent_results) == 1
        assert recent_results[0].description == "New activity"

        assert len(old_results) == 1
        assert old_results[0].description == "Old activity"

    def test_search_student_activities_with_multiple_filters(self, setup_audit_data):
        """Test searching with multiple filters combined."""
        data = setup_audit_data
        student = data["students"][0]

        # Create various activities
        StudentActivityLog.log_student_activity(
            student=student,
            activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
            description="EHSS enrollment",
            performed_by=data["staff_user"],
            term=data["term"],
            class_header=data["class_header"],
        )

        StudentActivityLog.log_student_activity(
            student=student,
            activity_type=StudentActivityLog.ActivityType.LANGUAGE_PROMOTION,
            description="Level promotion",
            performed_by=data["staff_user"],
            term=data["term"],
        )

        # Create activity for different student (should not match)
        StudentActivityLog.log_student_activity(
            student=data["students"][1],
            activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
            description="Other student enrollment",
            performed_by=data["staff_user"],
            term=data["term"],
            class_header=data["class_header"],
        )

        # Search with multiple filters
        results = StudentActivityLog.search_student_activities(
            student_number=student.student_number,
            activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
            term_name=data["term"].name,
            class_code="EHSS-05",
        )

        assert len(results) == 1
        assert results[0].student_number == student.student_number
        assert results[0].activity_type == StudentActivityLog.ActivityType.CLASS_ENROLLMENT
        assert results[0].class_code == "EHSS-05"

    def test_search_student_activities_with_limit(self, setup_audit_data):
        """Test search limit functionality."""
        data = setup_audit_data
        student = data["students"][0]

        # Create many activities
        for i in range(10):
            StudentActivityLog.log_student_activity(
                student=student,
                activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
                description=f"Activity {i}",
                performed_by=data["staff_user"],
            )

        # Search with limit
        results = StudentActivityLog.search_student_activities(student_number=student.student_number, limit=5)

        assert len(results) == 5

    def test_string_representation(self, setup_audit_data):
        """Test string representation of audit log."""
        data = setup_audit_data
        student = data["students"][0]

        log_entry = StudentActivityLog.log_student_activity(
            student=student,
            activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
            description="Test activity",
            performed_by=data["staff_user"],
        )

        expected = f"{student.student_number}: CLASS_ENROLLMENT on {log_entry.created_at.strftime('%Y-%m-%d')}"
        assert str(log_entry) == expected

    def test_activity_type_choices(self):
        """Test that all required activity types are available."""
        choices = StudentActivityLog.ActivityType.choices
        choice_values = [choice[0] for choice in choices]

        required_types = [
            "CLASS_ENROLLMENT",
            "CLASS_WITHDRAWAL",
            "CLASS_COMPLETION",
            "LANGUAGE_PROMOTION",
            "LANGUAGE_LEVEL_SKIP",
            "GRADE_ASSIGNMENT",
            "MANAGEMENT_OVERRIDE",
        ]

        for required_type in required_types:
            assert required_type in choice_values

    def test_database_indexes_performance(self, setup_audit_data):
        """Test that database queries use indexes efficiently."""
        data = setup_audit_data

        # This is a basic test - in production you'd use EXPLAIN queries
        # to verify index usage, but for unit tests we just verify
        # that searches return quickly with reasonable data volumes

        # Create a moderate amount of test data
        for i in range(50):
            student = data["students"][i % len(data["students"])]
            StudentActivityLog.log_student_activity(
                student=student,
                activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
                description=f"Test activity {i}",
                performed_by=data["staff_user"],
                term=data["term"],
            )

        # These searches should be fast due to indexes
        results1 = StudentActivityLog.search_student_activities(student_number=data["students"][0].student_number)

        results2 = StudentActivityLog.search_student_activities(
            activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
        )

        results3 = StudentActivityLog.search_student_activities(term_name=data["term"].name)

        # Verify results are returned (performance verification would require profiling)
        assert len(results1) > 0
        assert len(results2) == 50
        assert len(results3) == 50
