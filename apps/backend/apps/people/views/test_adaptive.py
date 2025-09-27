"""Test view for adaptive navigation - NO LOGIN REQUIRED."""

from django.views.generic import TemplateView


class TestAdaptiveView(TemplateView):
    """Test view to verify adaptive navigation CSS loading."""

    template_name = "people/test_adaptive.html"

    def get_context_data(self, **kwargs):
        """Add test context."""
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "user": {
                    "full_name": "Test User",
                    "is_authenticated": True,
                }
            }
        )
        return context
