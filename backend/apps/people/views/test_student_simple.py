"""Test view for base_adaptive_simple.html template."""

from django.views.generic import TemplateView


class TestStudentSimpleView(TemplateView):
    """Test view for the simple adaptive base template."""

    template_name = "people/test_student_simple.html"

    def get_context_data(self, **kwargs):
        """Add test data to context."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page_title": "Base Adaptive Simple Test",
                "page_subtitle": "Testing the simple adaptive base template",
                "page_icon": "fas fa-vial",
            }
        )
        return context
