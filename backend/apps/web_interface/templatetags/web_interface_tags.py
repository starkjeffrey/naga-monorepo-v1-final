"""
Template tags for the web interface app.

This module provides custom template tags and filters for the user-facing
web interface, including navigation helpers and utility functions.
"""

from django import template
from django.contrib.auth import get_user_model
from django.utils.translation import gettext as _

from ..permissions import RoleBasedPermissionMixin
from ..utils import format_currency as util_format_currency
from ..utils import get_status_badge_class
from ..utils import get_user_navigation as utils_get_user_navigation

register = template.Library()
User = get_user_model()


@register.simple_tag
def get_user_navigation(user):
    """
    Get navigation structure for a user based on their roles.

    Args:
        user: Django User instance

    Returns:
        List of navigation sections
    """
    return utils_get_user_navigation(user)


@register.simple_tag
def get_user_roles(user):
    """
    Get list of roles for a user.

    Args:
        user: Django User instance

    Returns:
        List of role names
    """
    if not user.is_authenticated:
        return []

    permission_mixin = RoleBasedPermissionMixin()
    return permission_mixin.get_user_roles(user)


@register.filter
def has_permission(user, permission):
    """
    Check if user has a specific permission.

    Args:
        user: Django User instance
        permission: Permission name to check

    Returns:
        bool: True if user has permission
    """
    from ..permissions import has_permission as _has_permission

    return _has_permission(user, permission)


@register.filter
def status_badge_class(status):
    """
    Get CSS class for status badges.

    Args:
        status: Status value

    Returns:
        CSS class name
    """
    return get_status_badge_class(status)


@register.filter
def format_currency_filter(amount, currency="USD"):
    """
    Format currency amount for display.

    Args:
        amount: Currency amount
        currency: Currency code (USD, KHR)

    Returns:
        Formatted currency string
    """
    if amount is None:
        return ""
    return util_format_currency(float(amount), currency)


@register.filter
def format_currency(amount, currency="USD"):
    """
    Format currency amount for display (alias for format_currency_filter).

    Args:
        amount: Currency amount
        currency: Currency code (USD, KHR)

    Returns:
        Formatted currency string
    """
    if amount is None:
        return ""
    return util_format_currency(float(amount), currency)


@register.inclusion_tag("web_interface/components/status_badge.html")
def status_badge(status, text=None):
    """
    Render a status badge.

    Args:
        status: Status value
        text: Display text (defaults to status)

    Returns:
        Rendered template
    """
    return {"status": status, "text": text or status.title(), "class": get_status_badge_class(status)}


@register.inclusion_tag("web_interface/components/action_button.html")
def action_button(url, text, icon=None, classes="action-btn", **kwargs):
    """
    Render an action button.

    Args:
        url: Button URL
        text: Button text
        icon: Optional icon
        classes: CSS classes
        **kwargs: Additional HTML attributes

    Returns:
        Rendered template
    """
    return {"url": url, "text": text, "icon": icon, "classes": classes, "attrs": kwargs}


@register.inclusion_tag("web_interface/components/modal_trigger.html")
def modal_trigger(modal_type, text, classes="header-btn", **kwargs):
    """
    Render a modal trigger button.

    Args:
        modal_type: Type of modal to open
        text: Button text
        classes: CSS classes
        **kwargs: Additional attributes

    Returns:
        Rendered template
    """
    return {"modal_type": modal_type, "text": text, "classes": classes, "attrs": kwargs}


@register.inclusion_tag("web_interface/components/pagination.html")
def pagination(page_obj, base_url=None):
    """
    Render pagination controls.

    Args:
        page_obj: Django Paginator page object
        base_url: Base URL for pagination links

    Returns:
        Rendered template
    """
    return {"page_obj": page_obj, "base_url": base_url or ""}


@register.inclusion_tag("web_interface/components/search_form.html")
def search_form(form, target="#contentArea", placeholder="Search..."):
    """
    Render a search form.

    Args:
        form: Django form instance
        target: HTMX target for results
        placeholder: Input placeholder text

    Returns:
        Rendered template
    """
    return {"form": form, "target": target, "placeholder": placeholder}


@register.simple_tag
def active_nav_item(request, pattern):
    """
    Check if current request path matches navigation pattern.

    Args:
        request: Django request object
        pattern: URL pattern to match

    Returns:
        'active' if matches, empty string otherwise
    """
    if request.path.startswith(pattern):
        return "active"
    return ""


@register.filter
def add_class(field, css_class):
    """
    Add CSS class to form field.

    Args:
        field: Django form field
        css_class: CSS class to add

    Returns:
        Field with updated class
    """
    return field.as_widget(attrs={"class": css_class})


@register.filter
def field_type(field):
    """
    Get form field type.

    Args:
        field: Django form field

    Returns:
        Field type name
    """
    return field.field.widget.__class__.__name__.lower()


@register.simple_tag
def page_title(title, subtitle=None):
    """
    Generate page title with optional subtitle.

    Args:
        title: Main title
        subtitle: Optional subtitle

    Returns:
        Formatted title string
    """
    if subtitle:
        return f"{title} - {subtitle}"
    return title


@register.filter
def trans(value):
    """
    Translate a value using Django's translation system.

    Args:
        value: Value to translate

    Returns:
        Translated value
    """
    return _(str(value))


@register.simple_tag
def query_string(request, **kwargs):
    """
    Generate query string with updated parameters.

    Args:
        request: Django request object
        **kwargs: Parameters to update

    Returns:
        Updated query string
    """
    # Defensive programming: handle case where request might be a string
    if isinstance(request, str):
        from django.http import QueryDict
        query_dict = QueryDict(mutable=True)
    elif hasattr(request, 'GET'):
        query_dict = request.GET.copy()
    else:
        from django.http import QueryDict
        query_dict = QueryDict(mutable=True)

    for key, value in kwargs.items():
        if value is not None:
            query_dict[key] = value
        elif key in query_dict:
            del query_dict[key]

    if query_dict:
        return "?" + query_dict.urlencode()
    return ""


@register.filter
def get_item(dictionary, key):
    """
    Get item from dictionary by key.

    Args:
        dictionary: Dictionary object
        key: Key to look up

    Returns:
        Value or None
    """
    if hasattr(dictionary, "get"):
        return dictionary.get(key)
    return None


@register.filter
def multiply(value, multiplier):
    """
    Multiply two values.

    Args:
        value: First value
        multiplier: Multiplier

    Returns:
        Product
    """
    try:
        return float(value) * float(multiplier)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """
    Calculate percentage.

    Args:
        value: Value
        total: Total

    Returns:
        Percentage as float
    """
    try:
        if float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError):
        return 0


@register.simple_tag
def settings_value(name, default=None):
    """
    Get Django settings value.

    Args:
        name: Settings name
        default: Default value if not found

    Returns:
        Settings value
    """
    from django.conf import settings

    return getattr(settings, name, default)


@register.filter
def truncate_chars(value, max_length):
    """
    Truncate string to maximum length.

    Args:
        value: String to truncate
        max_length: Maximum length

    Returns:
        Truncated string
    """
    if len(str(value)) <= max_length:
        return value
    return str(value)[: max_length - 3] + "..."


@register.simple_tag(takes_context=True)
def absolute_url(context, url):
    """
    Convert relative URL to absolute URL.

    Args:
        context: Template context
        url: Relative URL

    Returns:
        Absolute URL
    """
    request = context["request"]
    return request.build_absolute_uri(url)


@register.inclusion_tag("web_interface/components/loading_spinner.html")
def loading_spinner(size="md", text=None):
    """
    Render loading spinner.

    Args:
        size: Spinner size (sm, md, lg)
        text: Loading text

    Returns:
        Rendered template
    """
    return {"size": size, "text": text or _("Loading...")}


@register.filter
def add_enrolled_counts(classes):
    """
    Calculate total enrolled count from all classes.

    Args:
        classes: QuerySet of class headers

    Returns:
        Total enrolled count
    """
    total = 0
    for cls in classes:
        if hasattr(cls, "enrolled_count") and cls.enrolled_count is not None:
            total += cls.enrolled_count
        else:
            # Fallback if annotation not available
            from apps.enrollment.models import ClassHeaderEnrollment

            total += ClassHeaderEnrollment.objects.filter(class_header=cls, status="ENROLLED").count()
    return total


@register.filter
def nearly_full_count(classes):
    """
    Count classes that are nearly full (80% or more capacity).

    Args:
        classes: QuerySet of class headers

    Returns:
        Count of nearly full classes
    """
    count = 0
    for cls in classes:
        if hasattr(cls, "enrolled_count") and hasattr(cls, "max_enrollment"):
            enrolled = cls.enrolled_count or 0
            capacity = cls.max_enrollment or 30
            if enrolled >= capacity * 0.8:
                count += 1
        else:
            # Fallback calculation
            from apps.enrollment.models import ClassHeaderEnrollment

            enrolled = ClassHeaderEnrollment.objects.filter(class_header=cls, status="ENROLLED").count()
            capacity = cls.max_enrollment or 30
            if enrolled >= capacity * 0.8:
                count += 1
    return count


@register.filter
def full_classes_count(classes):
    """
    Count classes that are full or over capacity.

    Args:
        classes: QuerySet of class headers

    Returns:
        Count of full classes
    """
    count = 0
    for cls in classes:
        if hasattr(cls, "enrolled_count") and hasattr(cls, "max_enrollment"):
            enrolled = cls.enrolled_count or 0
            capacity = cls.max_enrollment or 30
            if enrolled >= capacity:
                count += 1
        else:
            # Fallback calculation
            from apps.enrollment.models import ClassHeaderEnrollment

            enrolled = ClassHeaderEnrollment.objects.filter(class_header=cls, status="ENROLLED").count()
            capacity = cls.max_enrollment or 30
            if enrolled >= capacity:
                count += 1
    return count


@register.filter
def clean_khmer_name(khmer_name):
    """
    Clean Khmer name by removing suffixes like {AF}, (ST), <PLF>, etc.

    Args:
        khmer_name: Khmer name string

    Returns:
        Cleaned Khmer name
    """
    if not khmer_name:
        return khmer_name

    # Remove common suffixes and tags
    import re

    # Remove patterns like {AF}, (ST), <PLF>, <CRST>, <PEPY>, etc.
    patterns_to_remove = [
        r'\{[^}]*\}',  # {AF}, {FRIENDS}, etc.
        r'\([^)]*\)',  # (ST), (PLF), etc.
        r'<[^>]*>',    # <PLF>, <CRST>, <PEPY>, etc.
        r'\$\$.*',     # $$ and everything after
    ]

    cleaned_name = khmer_name.strip()
    for pattern in patterns_to_remove:
        cleaned_name = re.sub(pattern, '', cleaned_name).strip()

    return cleaned_name
