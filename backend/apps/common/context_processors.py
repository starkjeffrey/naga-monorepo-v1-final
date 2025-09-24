"""Context processors for providing global template context.

This module provides context processors that make data available to all templates,
including navigation menus, user permissions, and system-wide settings.
"""

import contextlib

from django.urls import reverse
from django.urls.exceptions import NoReverseMatch
from django.utils.translation import gettext_lazy as _

from apps.curriculum.services import TermService


def navigation_context(request):
    """Provide navigation context based on user permissions and roles.

    Returns a hierarchical navigation structure that automatically shows/hides
    menu items based on the user's permissions and group memberships.

    Args:
        request: HTTP request object with user information

    Returns:
        Dictionary with navigation data for templates
    """
    if not request.user.is_authenticated:
        return {"navigation": []}

    # Define the complete navigation structure with permission requirements
    navigation_config = [
        {
            "label": _("Dashboard"),
            "icon": "fas fa-tachometer-alt",
            "url": "home",
            "permission": None,  # Available to all authenticated users
            "order": 10,
        },
        {
            "label": _("Level Testing"),
            "icon": "fas fa-clipboard-check",
            "order": 20,
            "children": [
                {
                    "label": _("Student Application"),
                    "url": "level_testing:application_start",
                    "permission": None,  # Public application
                    "description": _("Apply for placement testing"),
                },
                {
                    "label": _("Staff Dashboard"),
                    "url": "level_testing:staff_dashboard",
                    "permission": "level_testing.view_potentialstudent",
                    "description": _("Manage test applications"),
                },
                {
                    "label": _("Applications"),
                    "url": "level_testing:staff_applications",
                    "permission": "level_testing.view_potentialstudent",
                    "description": _("View all applications"),
                },
                {
                    "label": _("Payment Processing"),
                    "url": "level_testing:staff_applications",
                    "permission": "level_testing.change_testpayment",
                    "description": _("Process test payments"),
                    "url_params": "?payment_status=unpaid",
                },
            ],
        },
        {
            "label": _("Student Management"),
            "icon": "fas fa-users",
            "order": 30,
            "children": [
                {
                    "label": _("Students"),
                    "url": "admin:people_person_changelist",
                    "permission": "people.view_person",
                    "description": _("Manage student records"),
                },
                {
                    "label": _("Enrollment"),
                    "url": "admin:enrollment_enrollment_changelist",
                    "permission": "enrollment.view_enrollment",
                    "description": _("Student enrollment management"),
                },
                {
                    "label": _("Attendance"),
                    "url": "admin:attendance_attendance_changelist",
                    "permission": "attendance.view_attendance",
                    "description": _("Track student attendance"),
                },
            ],
        },
        {
            "label": _("Academic"),
            "icon": "fas fa-graduation-cap",
            "order": 40,
            "children": [
                {
                    "label": _("Courses"),
                    "url": "admin:academic_course_changelist",
                    "permission": "academic.view_course",
                    "description": _("Course catalog management"),
                },
                {
                    "label": _("Programs"),
                    "url": "admin:curriculum_program_changelist",
                    "permission": "curriculum.view_program",
                    "description": _("Academic programs"),
                },
                {
                    "label": _("Scheduling"),
                    "url": "admin:scheduling_classschedule_changelist",
                    "permission": "scheduling.view_classschedule",
                    "description": _("Class scheduling"),
                },
                {
                    "label": _("Grading"),
                    "url": "admin:grading_grade_changelist",
                    "permission": "grading.view_grade",
                    "description": _("Grade management"),
                },
            ],
        },
        {
            "label": _("Finance"),
            "icon": "fas fa-dollar-sign",
            "order": 50,
            "children": [
                {
                    "label": _("Payments Overview"),
                    "url": "admin:finance_payment_changelist",
                    "permission": "finance.view_payment",
                    "description": _("Payment management"),
                },
                {
                    "label": _("Invoicing"),
                    "url": "admin:finance_invoice_changelist",
                    "permission": "finance.view_invoice",
                    "description": _("Invoice management"),
                },
                {
                    "label": _("Financial Reports"),
                    "url": "admin:finance_financialreport_changelist",
                    "permission": "finance.view_financialreport",
                    "description": _("Financial reporting"),
                },
                {
                    "label": _("Test Fee Reports"),
                    "url": "level_testing:staff_applications",
                    "permission": "level_testing.view_testpayment",
                    "description": _("Level testing revenue"),
                    "url_params": "?payment_status=paid",
                },
                # Registrar gets limited finance access
                {
                    "label": _("Student Billing"),
                    "url": "admin:finance_payment_changelist",
                    "permission": "finance.view_payment",
                    "groups": ["registrar"],  # Only show to registrar group
                    "description": _("Student payment tracking"),
                    "url_params": "?status=pending",
                },
            ],
        },
        {
            "label": _("Reports"),
            "icon": "fas fa-chart-bar",
            "order": 60,
            "children": [
                {
                    "label": _("Enrollment Reports"),
                    "url": "admin:enrollment_enrollment_changelist",
                    "permission": "enrollment.view_enrollment",
                    "description": _("Enrollment statistics"),
                },
                {
                    "label": _("Financial Reports"),
                    "url": "admin:finance_financialreport_changelist",
                    "permission": "finance.view_financialreport",
                    "description": _("Revenue and expenses"),
                },
                {
                    "label": _("Academic Reports"),
                    "url": "admin:grading_grade_changelist",
                    "permission": "grading.view_grade",
                    "description": _("Academic performance"),
                },
            ],
        },
        {
            "label": _("Administration"),
            "icon": "fas fa-cogs",
            "order": 70,
            "children": [
                {
                    "label": _("Django Admin"),
                    "url": "admin:index",
                    "permission": None,
                    "staff_required": True,
                    "description": _("Full system administration"),
                },
                {
                    "label": _("User Management"),
                    "url": "admin:users_user_changelist",
                    "permission": "users.view_user",
                    "description": _("Manage system users"),
                },
                {
                    "label": _("System Settings"),
                    "url": "admin:sites_site_changelist",
                    "permission": "sites.view_site",
                    "superuser_required": True,
                    "description": _("System configuration"),
                },
            ],
        },
    ]

    # Filter navigation based on user permissions
    filtered_navigation = []
    user = request.user
    user_groups = set(user.groups.values_list("name", flat=True))

    for section in navigation_config:
        # Check if user has access to any items in this section
        accessible_children = []

        if "children" in section:
            for item in section["children"]:
                if _user_can_access_item(user, item, user_groups):
                    # Build the URL with parameters if specified
                    url = item.get("url", "#")
                    if url != "#":
                        try:
                            url = reverse(url) + item["url_params"] if "url_params" in item else reverse(url)
                        except (NoReverseMatch, AttributeError, TypeError):
                            url = "#"  # Fallback if URL can't be resolved

                    accessible_children.append(
                        {
                            "label": item["label"],
                            "url": url,
                            "description": item.get("description", ""),
                            "badge": item.get("badge", None),
                        },
                    )

        if accessible_children or _user_can_access_item(user, section, user_groups):
            section_data = {
                "label": section["label"],
                "icon": section.get("icon", "fas fa-circle"),
                "order": section.get("order", 999),
                "children": accessible_children,
            }

            # Add direct URL if section is directly accessible
            if "url" in section and _user_can_access_item(user, section, user_groups):
                with contextlib.suppress(Exception):
                    section_data["url"] = reverse(section["url"])

            filtered_navigation.append(section_data)

    # Sort navigation by order
    filtered_navigation.sort(key=lambda x: x["order"])

    return {
        "navigation": filtered_navigation,
        "user_role_display": _get_user_role_display(user, user_groups),
    }


def _user_can_access_item(user, item, user_groups):
    """Check if a user can access a navigation item based on permissions and groups.

    Args:
        user: Django User object
        item: Navigation item dictionary
        user_groups: Set of group names user belongs to

    Returns:
        Boolean indicating if user has access
    """
    # Check superuser requirement
    if item.get("superuser_required", False) and not user.is_superuser:
        return False

    # Check staff requirement
    if item.get("staff_required", False) and not user.is_staff:
        return False

    # Check group membership if specified
    if "groups" in item:
        required_groups = set(item["groups"])
        if not required_groups.intersection(user_groups):
            return False

    # Check specific permission if specified
    if item.get("permission"):
        return user.has_perm(item["permission"])

    return True


def _get_user_role_display(user, user_groups):
    """Get a user-friendly display of the user's primary role.

    Args:
        user: Django User object
        user_groups: Set of group names user belongs to

    Returns:
        String describing the user's primary role
    """
    if user.is_superuser:
        return _("System Administrator")

    # Define role hierarchy (first match wins)
    role_mapping = {
        "finance_manager": _("Finance Manager"),
        "registrar": _("Registrar"),
        "academic_coordinator": _("Academic Coordinator"),
        "clerk": _("Administrative Clerk"),
        "teacher": _("Teacher"),
        "staff": _("Staff Member"),
    }

    for group_name, role_display in role_mapping.items():
        if group_name in user_groups:
            return role_display

    if user.is_staff:
        return _("Staff Member")

    return _("User")


def system_context(request):
    """Provide system-wide context variables.

    Args:
        request: HTTP request object

    Returns:
        Dictionary with system context data
    """
    # Get current term from session or database
    current_term = None
    term_id = getattr(request, "session", {}).get("current_term_id")

    if term_id:
        try:
            from apps.curriculum.models import Term

            current_term = Term.objects.get(id=term_id, is_deleted=False)
        except (Term.DoesNotExist, ImportError):
            pass

    # Fallback to most appropriate term for general use
    if not current_term:
        try:
            from django.utils import timezone

            from apps.curriculum.models import Term

            today = timezone.now().date()

            # First priority: Currently active terms
            current_term = (
                Term.objects.filter(
                    is_deleted=False,
                    start_date__lte=today,
                    end_date__gte=today,
                )
                .order_by("start_date")
                .first()
            )

            # Second priority: Terms starting soon (next month)
            if not current_term:
                current_term = (
                    Term.objects.filter(
                        is_deleted=False,
                        start_date__gt=today,
                        start_date__lte=today + timezone.timedelta(days=30),
                    )
                    .order_by("start_date")
                    .first()
                )

            # Last resort: Most recent term
            if not current_term:
                current_term = Term.objects.filter(is_deleted=False).order_by("-start_date").first()

        except ImportError:
            pass

    return {
        "system_name": "PUCSR Student Information System",
        "system_version": "1.0",
        "institution_name": "PUCSR Siem Reap",
        "current_term": current_term,
    }


def current_term_context(request):
    """Provide all active terms in context.

    This context processor ensures all active terms (ENG_A, ENG_B, BA, MA)
    are available in templates. The middleware caches these on the request
    object to avoid repeated database queries.

    Args:
        request: HTTP request object

    Returns:
        Dictionary with active terms
    """
    context = {}

    # Get active terms from middleware (already cached)
    if hasattr(request, "active_terms"):
        context["active_terms"] = request.active_terms
    else:
        # Fallback if middleware hasn't run
        active_terms = TermService.get_all_active_terms()
        context["active_terms"] = active_terms

    if hasattr(request, "active_terms_by_type"):
        context["active_terms_by_type"] = request.active_terms_by_type
    else:
        # Fallback if middleware hasn't run
        active_terms_by_type = TermService.get_active_terms_by_type()
        context["active_terms_by_type"] = active_terms_by_type

    # Keep backward compatibility - provide current_term as first active term
    if hasattr(request, "current_term"):
        context["current_term"] = request.current_term
        context["current_term_cached"] = request.current_term
    elif context.get("active_terms"):
        context["current_term"] = context["active_terms"][0]
        context["current_term_cached"] = context["active_terms"][0]
    else:
        context["current_term"] = None
        context["current_term_cached"] = None

    return context
