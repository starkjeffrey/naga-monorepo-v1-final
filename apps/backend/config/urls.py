from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.http import HttpResponseRedirect
from django.urls import include, path
from django.views import defaults as default_views

# Direct import to avoid config.api re-export issues
from api.v1 import api
from api.v2 import api as api_v2

from .legacy_urls import legacy_urlpatterns

# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# CRITICAL: DO NOT MODIFY THE ROOT URL CONFIGURATION BELOW
# The web_interface MUST remain at root path ("") for Student Locator to work
# This configuration has been broken multiple times - DO NOT REVERT
# Contact repository owner before making ANY changes to path("", ...)
# !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

urlpatterns = [
    # CRITICAL: Web Interface at root
    path("", include("apps.web_interface.urls", namespace="web_interface")),
    # Django Admin - preserve access
    path(settings.ADMIN_URL, admin.site.urls),
    # Django Silk for performance profiling
    path("silk/", include("silk.urls", namespace="silk")),
    # API endpoints
    path("api/v1/", api.urls),
    path("api/v2/", api_v2.urls),
    # GraphQL endpoint - temporarily disabled due to circular import
    # path("graphql/", include("config.graphql_urls")),
    # Legacy system backup
    path("legacy/", include(legacy_urlpatterns)),
    # Authentication - preserve allauth but redirect login to main interface
    path("accounts/login/", lambda request: __import__("django.http").http.HttpResponseRedirect("/")),
    path("accounts/", include("allauth.urls")),
    # Favicon redirect
    path("favicon.ico", lambda request: HttpResponseRedirect(f"{settings.STATIC_URL}favicon.ico")),
    # App-specific URLs
    path("academic-records/", include("apps.academic_records.urls", namespace="academic_records")),
    path("attendance/", include("apps.attendance.urls", namespace="attendance")),
    path("level-testing/", include("apps.level_testing.urls", namespace="level_testing")),
    path("people/", include("apps.people.urls", namespace="people")),
    path("scheduling/", include("apps.scheduling.urls", namespace="scheduling")),
    path("finance/", include("apps.finance.urls", namespace="finance")),
    path("users/", include("apps.users.urls", namespace="users")),  # Re-enabled
    # path("settings/", include("apps.settings.urls", namespace="settings")),  # Import error with GradeLevel
    # Internationalization
    path("i18n/", include("django.conf.urls.i18n")),
    # ...
    # Media files
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]
if settings.DEBUG:
    # Static file serving when using Gunicorn + Uvicorn for local web socket development
    urlpatterns += staticfiles_urlpatterns()


# Custom error handlers
handler400 = default_views.bad_request
handler403 = default_views.permission_denied
handler404 = default_views.page_not_found
handler500 = default_views.server_error


# RUNTIME VALIDATION: Ensure critical URL configuration is correct
def _validate_critical_urls():
    """Runtime validation to detect URL configuration regressions."""
    import sys

    # Find the web_interface pattern (might not be first if debug_toolbar is enabled)
    web_interface_found = False
    web_interface_at_root = False

    for pattern in urlpatterns:
        pattern_str = str(pattern.pattern) if hasattr(pattern, "pattern") else ""
        urlconf_str = str(pattern.urlconf_name) if hasattr(pattern, "urlconf_name") else ""

        # Check if this is the web_interface pattern
        if "web_interface" in urlconf_str:
            web_interface_found = True
            # Check if it's at the root path (empty string pattern)
            if pattern_str in ("", "^"):
                web_interface_at_root = True
                break

    if not web_interface_found:
        print("🚨 CRITICAL URL ERROR: web_interface URLs not found!", file=sys.stderr)
        print("🚨 Student Locator will be BROKEN!", file=sys.stderr)
        print("🚨 Fix config/urls.py immediately!", file=sys.stderr)
    elif not web_interface_at_root:
        print("🚨 CRITICAL URL ERROR: web_interface is NOT at root path!", file=sys.stderr)
        print("🚨 Student Locator will be BROKEN!", file=sys.stderr)
        print("🚨 Fix config/urls.py immediately!", file=sys.stderr)


# Run validation in DEBUG mode
if settings.DEBUG:
    try:
        _validate_critical_urls()
    except Exception:
        pass  # Don't break startup if validation fails

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    # Transaction browser for AR reconstruction batches
    # TODO: Re-enable when scratchpad module is properly configured
    # from scratchpad.transaction_django_view import urlpatterns as transaction_urls
    # urlpatterns += [path("transaction-browser/", include(transaction_urls))]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
            *urlpatterns,
        ]
