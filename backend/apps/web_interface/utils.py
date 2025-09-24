"""
Utility functions for the web interface.

This module contains helper functions and utilities used across
the web interface views, forms, and templates.
"""

import logging
import os
from typing import Any

from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.test import Client

User = get_user_model()


def get_navigation_structure() -> dict[str, list[dict[str, Any]]]:
    """
    Get navigation structure based on user roles.

    Returns:
        Dict mapping role names to navigation sections
    """
    return {
        "admin": [
            {
                "title": "Main",
                "items": [
                    {"name": "Dashboard", "icon": "📊", "page": "dashboard", "url_name": "web_interface:dashboard"},
                    {
                        "name": "Student Locator",
                        "icon": "🔍",
                        "page": "student-locator",
                        "url_name": "web_interface:student-locator",
                    },
                    {"name": "Students", "icon": "👥", "page": "students", "url_name": "web_interface:student-list"},
                    {"name": "Teachers", "icon": "👨‍🏫", "page": "teachers", "url_name": "web_interface:teacher-list"},
                    {"name": "Courses", "icon": "📚", "page": "courses", "url_name": "web_interface:course-list"},
                    {"name": "Classes", "icon": "🏫", "page": "classes", "url_name": "web_interface:class-list"},
                ],
            },
            {
                "title": "Academic",
                "items": [
                    {
                        "name": "Enrollment Management",
                        "icon": "📝",
                        "page": "enrollment",
                        "url_name": "web_interface:enrollment-management",
                    },
                    {"name": "Grades", "icon": "📊", "page": "grades", "url_name": "web_interface:grades"},
                    {
                        "name": "Transcripts",
                        "icon": "📄",
                        "page": "transcripts",
                        "url_name": "web_interface:transcripts",
                    },
                    {"name": "Schedules", "icon": "📅", "page": "schedules", "url_name": "web_interface:schedules"},
                ],
            },
            {
                "title": "Enrollment Templates",
                "items": [
                    {
                        "name": "Enrollment Wizard",
                        "icon": "🧙",
                        "page": "enrollment-wizard",
                        "url_name": "web_interface:enrollment-wizard",
                    },
                    {
                        "name": "Quick Enrollment",
                        "icon": "⚡",
                        "page": "quick-enrollment",
                        "url_name": "web_interface:quick-enrollment-modal",
                    },
                    {
                        "name": "Enhanced Class Cards",
                        "icon": "🎴",
                        "page": "class-cards",
                        "url_name": "web_interface:enhanced-class-cards",
                    },
                ],
            },
            {
                "title": "Financial",
                "items": [
                    {"name": "Billing", "icon": "💰", "page": "billing", "url_name": "web_interface:billing"},
                    {
                        "name": "Payments",
                        "icon": "💳",
                        "page": "payments",
                        "url_name": "web_interface:payment-processing",
                    },
                    {"name": "Scholarships", "icon": "🎓", "page": "scholarships"},
                    {
                        "name": "Reports",
                        "icon": "📈",
                        "page": "reports",
                        "url_name": "web_interface:reports-dashboard",
                    },
                ],
            },
            {
                "title": "Settings",
                "items": [
                    {"name": "System Config", "icon": "⚙️", "page": "config", "url_name": "admin:index"},
                    {"name": "Users", "icon": "👤", "page": "users", "url_name": "web_interface:user-list"},
                    {"name": "Backup", "icon": "💾", "page": "backup", "url_name": "web_interface:backup"},
                ],
            },
        ],
        "student": [
            {
                "title": "My Academic",
                "items": [
                    {"name": "Dashboard", "icon": "📊", "page": "dashboard", "url_name": "web_interface:dashboard"},
                    {"name": "My Courses", "icon": "📚", "page": "mycourses", "url_name": "web_interface:my-courses"},
                    {"name": "Schedule", "icon": "📅", "page": "schedule", "url_name": "web_interface:my-schedule"},
                    {"name": "Grades", "icon": "📊", "page": "grades", "url_name": "web_interface:my-grades"},
                    {
                        "name": "Transcript",
                        "icon": "📄",
                        "page": "transcript",
                        "url_name": "web_interface:my-transcript",
                    },
                ],
            },
            {
                "title": "Registration",
                "items": [
                    {
                        "name": "Course Registration",
                        "icon": "📝",
                        "page": "registration",
                        "url_name": "web_interface:course-registration",
                    },
                    {"name": "Drop/Add", "icon": "🔄", "page": "dropadd", "url_name": "web_interface:drop-add"},
                ],
            },
            {
                "title": "Financial",
                "items": [
                    {
                        "name": "Account Balance",
                        "icon": "💰",
                        "page": "balance",
                        "url_name": "web_interface:my-balance",
                    },
                    {
                        "name": "Make Payment",
                        "icon": "💳",
                        "page": "payment",
                        "url_name": "web_interface:make-payment",
                    },
                    {
                        "name": "Payment History",
                        "icon": "📜",
                        "page": "history",
                        "url_name": "web_interface:payment-history",
                    },
                ],
            },
        ],
        "teacher": [
            {
                "title": "Teaching",
                "items": [
                    {"name": "Dashboard", "icon": "📊", "page": "dashboard", "url_name": "web_interface:dashboard"},
                    {"name": "My Classes", "icon": "🏫", "page": "myclasses", "url_name": "web_interface:my-classes"},
                    {"name": "Attendance", "icon": "✅", "page": "attendance", "url_name": "web_interface:attendance"},
                    {"name": "Grade Entry", "icon": "📝", "page": "grading", "url_name": "web_interface:grade-entry"},
                ],
            },
            {
                "title": "Academic",
                "items": [
                    {
                        "name": "Student Lists",
                        "icon": "👥",
                        "page": "students",
                        "url_name": "web_interface:my-students",
                    },
                    {"name": "Schedule", "icon": "📅", "page": "schedule", "url_name": "web_interface:my-schedule"},
                    {"name": "Reports", "icon": "📈", "page": "reports", "url_name": "web_interface:teaching-reports"},
                ],
            },
        ],
        "staff": [
            {
                "title": "Student Services",
                "items": [
                    {"name": "Dashboard", "icon": "📊", "page": "dashboard", "url_name": "web_interface:dashboard"},
                    {
                        "name": "Student Locator",
                        "icon": "🔍",
                        "page": "student-locator",
                        "url_name": "web_interface:student-locator",
                    },
                    {
                        "name": "Student Records",
                        "icon": "👥",
                        "page": "students",
                        "url_name": "web_interface:student-list",
                    },
                    {
                        "name": "Enrollment Management",
                        "icon": "📝",
                        "page": "enrollment",
                        "url_name": "web_interface:enrollment-management",
                    },
                    {
                        "name": "Transcripts",
                        "icon": "📄",
                        "page": "transcripts",
                        "url_name": "web_interface:transcripts",
                    },
                ],
            },
            {
                "title": "Academic",
                "items": [
                    {
                        "name": "Course Management",
                        "icon": "📚",
                        "page": "courses",
                        "url_name": "web_interface:course-list",
                    },
                    {
                        "name": "Class Scheduling",
                        "icon": "📅",
                        "page": "scheduling",
                        "url_name": "web_interface:schedules",
                    },
                    {"name": "Grade Management", "icon": "📊", "page": "grades", "url_name": "web_interface:grades"},
                ],
            },
            {
                "title": "Enrollment Templates",
                "items": [
                    {
                        "name": "Enrollment Wizard",
                        "icon": "🧙",
                        "page": "enrollment-wizard",
                        "url_name": "web_interface:enrollment-wizard",
                    },
                    {
                        "name": "Quick Enrollment",
                        "icon": "⚡",
                        "page": "quick-enrollment",
                        "url_name": "web_interface:quick-enrollment-modal",
                    },
                    {
                        "name": "Enhanced Class Cards",
                        "icon": "🎴",
                        "page": "class-cards",
                        "url_name": "web_interface:enhanced-class-cards",
                    },
                ],
            },
        ],
        "finance": [
            {
                "title": "Financial",
                "items": [
                    {"name": "Dashboard", "icon": "📊", "page": "dashboard", "url_name": "web_interface:dashboard"},
                    {"name": "Billing", "icon": "💰", "page": "billing", "url_name": "web_interface:billing"},
                    {
                        "name": "Payments",
                        "icon": "💳",
                        "page": "payments",
                        "url_name": "web_interface:payment-processing",
                    },
                    {
                        "name": "Quick Payment",
                        "icon": "⚡",
                        "page": "quick-payment",
                        "url_name": "web_interface:quick-payment",
                    },
                    {"name": "Cashier Session", "icon": "🏧", "page": "cashier", "url_name": "web_interface:cashier"},
                ],
            },
            {
                "title": "Reports & Students",
                "items": [
                    {
                        "name": "Student Locator",
                        "icon": "🔍",
                        "page": "student-locator",
                        "url_name": "web_interface:student-locator",
                    },
                    {
                        "name": "Financial Reports",
                        "icon": "📈",
                        "page": "reports",
                        "url_name": "web_interface:reports-dashboard",
                    },
                    {
                        "name": "Student Search",
                        "icon": "🔍",
                        "page": "student-search",
                        "url_name": "web_interface:student-list",
                    },
                ],
            },
        ],
    }


def get_user_navigation(user) -> list[dict[str, Any]]:
    """
    Get navigation structure for a specific user based on their roles.

    Args:
        user: Django User instance

    Returns:
        List of navigation sections for the user
    """
    if not user.is_authenticated:
        return []

    # Import here to avoid circular imports
    from .permissions import RoleBasedPermissionMixin

    roles = RoleBasedPermissionMixin().get_user_roles(user)
    navigation_structure = get_navigation_structure()

    # Admin gets full navigation
    if "admin" in roles:
        return navigation_structure["admin"]

    # For other roles, return the first matching role's navigation
    # Priority order: staff, teacher, finance, student
    for role in ["staff", "teacher", "finance", "student"]:
        if role in roles and role in navigation_structure:
            return navigation_structure[role]

    # Default to student navigation if no specific role found
    return navigation_structure.get("student", [])


def get_page_title_map() -> dict[str, str]:
    """Get mapping of page names to display titles."""
    return {
        "dashboard": "Dashboard",
        "students": "Student Management",
        "teachers": "Teacher Management",
        "courses": "Course Management",
        "classes": "Class Management",
        "enrollment": "Class Schedule & Enrollment",
        "grades": "Grade Management",
        "transcripts": "Transcript Management",
        "schedules": "Schedule Management",
        "billing": "Billing & Invoices",
        "payments": "Payment Processing",
        "scholarships": "Scholarship Management",
        "reports": "Reports",
        "config": "System Configuration",
        "users": "User Management",
        "backup": "Backup Management",
        "mycourses": "My Courses",
        "myclasses": "My Classes",
        "attendance": "Attendance Management",
        "grading": "Grade Entry",
        "registration": "Course Registration",
        "dropadd": "Drop/Add Courses",
        "balance": "Account Balance",
        "payment": "Make Payment",
        "history": "Payment History",
        "accounts": "Student Accounts",
        "cashier": "Cashier Session",
        "reconciliation": "Daily Reconciliation",
    }


def get_page_title(page_name: str) -> str:
    """
    Get display title for a page.

    Args:
        page_name: Internal page name

    Returns:
        Human-readable page title
    """
    page_titles = get_page_title_map()
    return page_titles.get(page_name, page_name.title())


def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Format currency amount for display.

    Args:
        amount: Currency amount
        currency: Currency code (USD, KHR)

    Returns:
        Formatted currency string
    """
    if currency == "USD":
        return f"${amount:,.2f}"
    elif currency == "KHR":
        return f"៛{amount:,.0f}"
    else:
        return f"{currency} {amount:,.2f}"


def get_status_badge_class(status: str) -> str:
    """
    Get CSS class for status badges.

    Args:
        status: Status value

    Returns:
        CSS class name
    """
    status_map = {
        "active": "badge-success",
        "inactive": "badge-secondary",
        "pending": "badge-warning",
        "completed": "badge-success",
        "cancelled": "badge-danger",
        "expired": "badge-danger",
        "paid": "badge-success",
        "unpaid": "badge-warning",
        "overdue": "badge-danger",
        "partial": "badge-info",
        "enrolled": "badge-success",
        "dropped": "badge-secondary",
        "graduated": "badge-info",
        "suspended": "badge-danger",
    }
    return status_map.get(status.lower(), "badge-secondary")


def is_htmx_request(request: HttpRequest) -> bool:
    """
    Check if the request is an HTMX request.

    Args:
        request: Django HttpRequest

    Returns:
        True if request is from HTMX
    """
    return request.headers.get("HX-Request") == "true"


def get_htmx_target(request: HttpRequest) -> str | None:
    """
    Get HTMX target element ID.

    Args:
        request: Django HttpRequest

    Returns:
        Target element ID or None
    """
    return request.headers.get("HX-Target")


# WebSocket and HTMX Testing Utilities

logger = logging.getLogger(__name__)


class HTMXTestMixin:
    """Mixin for testing HTMX functionality."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.client.force_login(self.user)

    def htmx_get(self, url: str, data: dict | None = None) -> Any:
        """Make an HTMX GET request."""
        headers = {
            "HTTP_HX_REQUEST": "true",
            "HTTP_X_REQUESTED_WITH": "XMLHttpRequest",
        }
        return self.client.get(url, data or {}, **headers)

    def htmx_post(self, url: str, data: dict | None = None) -> Any:
        """Make an HTMX POST request."""
        headers = {
            "HTTP_HX_REQUEST": "true",
            "HTTP_X_REQUESTED_WITH": "XMLHttpRequest",
        }
        return self.client.post(url, data or {}, **headers)


class WebSocketTestMixin:
    """Mixin for testing WebSocket functionality."""

    # Tests using this mixin set a user; annotate for type checkers
    user: Any

    async def get_websocket_communicator(self, consumer_class, path: str) -> WebsocketCommunicator:
        """Get a WebSocket communicator for testing."""
        application = URLRouter(
            [
                path(f"ws/{path}/", consumer_class.as_asgi()),
            ]
        )

        communicator = WebsocketCommunicator(application, f"/ws/{path}/")
        communicator.scope["user"] = self.user

        return communicator

    async def test_websocket_connection(self, consumer_class, path: str) -> bool:
        """Test WebSocket connection."""
        communicator = await self.get_websocket_communicator(consumer_class, path)

        try:
            connected, subprotocol = await communicator.connect()
            if connected:
                await communicator.disconnect()
                return True
            return False
        except Exception as e:
            logger.error(f"WebSocket connection test failed for {path}: {e}")
            return False


def test_htmx_endpoints():
    """Test all HTMX endpoints for proper response."""
    logger.info("Testing HTMX endpoints...")

    # Test endpoints that should exist
    test_urls = [
        "/dashboard/",
        "/academic/transcripts/",
        "/attendance/sessions/",
        "/people/roles/",
        "/settings/",
    ]

    client = Client()
    user = User.objects.create_user(username="htmx_testuser", email="htmx@test.com", password="testpass123")
    client.force_login(user)

    results = {}

    for url in test_urls:
        try:
            # Test regular request
            response = client.get(url)
            regular_status = response.status_code

            # Test HTMX request
            htmx_response = client.get(url, HTTP_HX_REQUEST="true")
            htmx_status = htmx_response.status_code

            results[url] = {
                "regular": regular_status,
                "htmx": htmx_status,
                "success": regular_status < 500 and htmx_status < 500,
            }

        except Exception as e:
            results[url] = {"error": str(e), "success": False}
            logger.error(f"Error testing {url}: {e}")

    return results


async def test_websocket_consumers():
    """Test all WebSocket consumers."""
    logger.info("Testing WebSocket consumers...")

    try:
        from apps.attendance.consumers import AttendanceConsumer
        from apps.enrollment.consumers import EnrollmentConsumer
        from apps.finance.consumers import PaymentConsumer
        from apps.web_interface.consumers import NotificationConsumer
    except ImportError as e:
        logger.error(f"Could not import consumers: {e}")
        return {"error": "Consumer import failed", "success": False}

    consumers_to_test = [
        (NotificationConsumer, "notifications"),
        (EnrollmentConsumer, "enrollment"),
        (AttendanceConsumer, "attendance"),
        (PaymentConsumer, "payments"),
    ]

    results = {}

    for consumer_class, path in consumers_to_test:
        try:
            # Create test application
            application = URLRouter(
                [
                    path(f"ws/{path}/", consumer_class.as_asgi()),
                ]
            )

            communicator = WebsocketCommunicator(application, f"/ws/{path}/")

            # Mock user for testing
            from django.contrib.auth.models import AnonymousUser

            communicator.scope["user"] = AnonymousUser()  # Test with anonymous user first

            connected, subprotocol = await communicator.connect()

            if connected:
                await communicator.disconnect()
                results[path] = {"status": "connected", "success": True}
            else:
                results[path] = {"status": "rejected", "success": True}  # Rejection is expected for anonymous

        except Exception as e:
            results[path] = {"error": str(e), "success": False}
            logger.error(f"WebSocket test failed for {path}: {e}")

    return results


def validate_tailwind_build():
    """Validate that Tailwind CSS is properly built."""
    tailwind_css_path = (
        "/Users/jeffreystark/PycharmProjects/naga-monorepo/backend/static/web_interface/css/tailwind.css"
    )

    if os.path.exists(tailwind_css_path):
        with open(tailwind_css_path) as f:
            content = f.read()

        # Check for key Tailwind classes
        required_classes = [".btn", ".btn-primary", ".card", ".form-input", ".alert", ".modal"]

        missing_classes = []
        for cls in required_classes:
            if cls not in content:
                missing_classes.append(cls)

        return {
            "file_exists": True,
            "file_size": len(content),
            "missing_classes": missing_classes,
            "success": len(missing_classes) == 0,
        }
    else:
        return {"file_exists": False, "success": False, "error": "Tailwind CSS file not found"}


def run_comprehensive_test():
    """Run comprehensive test of all functionality."""
    logger.info("Running comprehensive integration tests...")

    results = {
        "htmx_endpoints": test_htmx_endpoints(),
        "tailwind_validation": validate_tailwind_build(),
    }

    # Add timezone if available
    try:
        from django.utils import timezone

        results["timestamp"] = str(timezone.now())
    except ImportError:
        results["timestamp"] = "N/A"

    # Calculate overall success
    htmx_success = all(result.get("success", False) for result in results["htmx_endpoints"].values())
    tailwind_success = results["tailwind_validation"]["success"]

    results["overall_success"] = htmx_success and tailwind_success
    results["summary"] = {
        "htmx_endpoints_tested": len(results["htmx_endpoints"]),
        "htmx_successful": sum(1 for r in results["htmx_endpoints"].values() if r.get("success")),
        "tailwind_built": tailwind_success,
    }

    return results
