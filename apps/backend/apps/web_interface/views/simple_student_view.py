"""
Simple student list view to bypass complex filtering system.
This is a temporary view to show actual student data.
"""

from django.views.generic import ListView

from apps.people.models import StudentProfile

from ..permissions import StaffRequiredMixin


class SimpleStudentListView(StaffRequiredMixin, ListView):
    """Simple student list without complex filtering."""

    model = StudentProfile
    template_name = "web_interface/pages/students/simple_student_list.html"
    context_object_name = "students"
    paginate_by = 50

    def get_queryset(self):
        """Get recent active students."""
        return (
            StudentProfile.objects.filter(is_deleted=False)
            .select_related("person")
            .order_by("-last_enrollment_date", "-created_at")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Students (Simple View)",
                "current_page": "students",
            }
        )
        return context
