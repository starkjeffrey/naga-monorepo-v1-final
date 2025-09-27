"""Test student profile view for adaptive navigation - NO LOGIN REQUIRED."""

from django.views.generic import TemplateView


class TestStudentAdaptiveView(TemplateView):
    """Test student profile view to verify adaptive navigation CSS loading without login."""

    template_name = "people/test_student_simple.html"

    def get_context_data(self, **kwargs):
        """Add mock student context for testing."""
        context = super().get_context_data(**kwargs)

        class MockPerson:
            def __init__(self):
                self.full_name = "John Doe"
                self.first_name = "John"
                self.last_name = "Doe"
                self.school_email = "john.doe@test.edu"
                self.current_photo_url = None
                self.current_address = None
                self.phone_numbers = MockQuerySet()

        class MockQuerySet:
            def __init__(self):
                self.first = None

        class MockMajorDeclaration:
            def __init__(self):
                self.major = MockMajor()

        class MockMajor:
            def __init__(self):
                self.name = "Computer Science"

        class MockStudent:
            def __init__(self):
                self.person = MockPerson()
                self.student_id = "TEST123"
                self.current_status = "ACTIVE"
                self.major_declaration = MockMajorDeclaration()
                self.catalog_year = "2024"
                self.pk = 1

        context.update(
            {
                # Mock student object
                "object": MockStudent(),
                "student": MockStudent(),
                # Page setup
                "page_title": "Test Student Profile - John Doe",
                "breadcrumbs": [
                    {"name": "Home", "url": "/"},
                    {"name": "Students", "url": "/people/students/"},
                    {"name": "John Doe", "active": True},
                ],
                # Student metrics for header
                "cumulative_gpa": 3.85,
                "total_credits": 75,
                "current_term_credits": 15,
                "account_balance": -1250.00,  # Negative means they owe
                "attendance_rate": 94.5,
                "has_holds": False,
                "has_outstanding_balance": True,
                "low_attendance": False,
                "has_alerts": True,
                "degree_progress_percentage": 62.5,
                # Current enrollments for overview
                "current_enrollments": [
                    {
                        "class_section": {
                            "course": {"code": "ENG101", "title": "English Composition"},
                            "section_number": "A",
                            "schedule_display": "MWF 9:00-10:30",
                        },
                        "grade": "A-",
                        "attendance_rate": 95.0,
                    },
                    {
                        "class_section": {
                            "course": {"code": "MATH201", "title": "Calculus I"},
                            "section_number": "B",
                            "schedule_display": "TTh 11:00-12:30",
                        },
                        "grade": "B+",
                        "attendance_rate": 88.0,
                    },
                ],
                "user": {
                    "full_name": "Test Admin",
                    "is_authenticated": True,
                },
            }
        )
        return context
