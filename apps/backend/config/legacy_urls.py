"""Legacy URL patterns for backward compatibility."""

from django.urls import include, path
from django.views.generic import TemplateView

legacy_urlpatterns = [
    # Legacy pages
    path("", TemplateView.as_view(template_name="pages/home.html"), name="legacy-home"),
    path("about/", TemplateView.as_view(template_name="pages/about.html"), name="legacy-about"),
    # Legacy test pages
    path("test-topnav/", TemplateView.as_view(template_name="pages/test_topnav.html"), name="legacy-test-topnav"),
    path(
        "test-simple-topnav/",
        TemplateView.as_view(template_name="pages/test_simple_topnav.html"),
        name="legacy-test-simple-topnav",
    ),
    path(
        "test-fixed-topnav/",
        TemplateView.as_view(template_name="pages/test_fixed_topnav.html"),
        name="legacy-test-fixed-topnav",
    ),
    path(
        "test-svg-topnav/",
        TemplateView.as_view(template_name="pages/test_svg_topnav.html"),
        name="legacy-test-svg-topnav",
    ),
    path("test-base2/", TemplateView.as_view(template_name="pages/test_base2.html"), name="legacy-test-base2"),
    path(
        "test-new-base/", TemplateView.as_view(template_name="pages/test_new_base.html"), name="legacy-test-new-base"
    ),
    # Legacy admin apps
    path(
        "admin-apps/",
        include(
            [
                path("users/", include("users.urls", namespace="legacy-users")),
                # Temporarily disabled apps
                # path("level-testing/", include("apps.level_testing.urls", namespace="legacy-level-testing")),
                # path("people/", include("apps.people.urls", namespace="legacy-people")),
                # path("scheduling/", include("apps.scheduling.urls", namespace="legacy-scheduling")),
                # path("finance/", include("apps.finance.urls", namespace="legacy-finance")),
            ]
        ),
    ),
]
