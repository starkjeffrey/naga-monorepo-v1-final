"""Student Profile Adaptive Navigation Views."""

from apps.people.views.student_profile_mockup import (
    StudentProfileByStudentIdMixin,
    StudentProfileTabView,
)


class StudentProfileAdaptiveView(StudentProfileTabView):
    """Display the student profile with adaptive navigation."""

    template_name = "people/student_profile_adaptive.html"

    def get_context_data(self, **kwargs):
        """Add context for adaptive navigation."""
        # Get the base context from DetailView, not TabView
        context = super(StudentProfileTabView, self).get_context_data(**kwargs)
        student = self.object

        # Add breadcrumbs and page title like the mockup
        context.update(
            {
                "page_title": f"Student Profile - {student.person.full_name}",
                "breadcrumbs": [
                    {"name": "Home", "url": "/"},
                    {"name": "Students", "url": "/people/students/"},
                    {"name": student.person.full_name, "active": True},
                ],
            }
        )

        # Add mock data for the adaptive view
        context.update(
            {
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
                "current_enrollments": self._get_mock_current_enrollments(),
            }
        )

        return context


class StudentProfileAdaptiveTabView(StudentProfileTabView):
    """Handle HTMX tab content loading for adaptive navigation."""

    pass


# TEST ONLY: Views that use student_id instead of pk
class StudentProfileAdaptiveByStudentIdView(StudentProfileByStudentIdMixin, StudentProfileAdaptiveView):
    """Student profile adaptive accessed by student_id - TEST ONLY."""

    def get_context_data(self, **kwargs):
        """Override to set student_id context."""
        context = super().get_context_data(**kwargs)
        context["use_student_id_urls"] = True
        context["student_id"] = self.object.student_id
        return context


class StudentProfileAdaptiveTabByStudentIdView(StudentProfileByStudentIdMixin, StudentProfileAdaptiveTabView):
    """Student profile adaptive tab content accessed by student_id - TEST ONLY."""

    pass
