"""Common template tags for CRUD and other utilities."""

from django import template
from django.utils.html import escape

from ..crud.utils import (
    build_field_link as util_build_field_link,
)
from ..crud.utils import (
    format_field_value as util_format_field_value,
)
from ..crud.utils import (
    get_cell_css_class as util_get_cell_css_class,
)
from ..crud.utils import (
    get_field_value as util_get_field_value,
)

register = template.Library()


@register.filter
def getattr(obj, field_name):
    """Get attribute from object - alias for template usage."""
    return util_get_field_value(obj, field_name)


@register.filter
def get_field_value(obj, field_name):
    """Get field value from object."""
    return util_get_field_value(obj, field_name)


@register.filter
def format_field_value(value, field_config):
    """Format field value for display."""
    return util_format_field_value(value, field_config)


@register.filter
def get_cell_css_class(field_config, obj):
    """Get CSS class for table cell."""
    value = util_get_field_value(obj, field_config.name)
    return util_get_cell_css_class(field_config, value)


@register.filter
def build_field_link(value, params):
    """Build link for field.
    Usage: {{ value|build_field_link:field:obj }}
    """
    # This is a workaround since Django doesn't support multiple params in filters
    return value


@register.simple_tag
def format_field_with_link(obj, field_config):
    """Format field with optional link."""
    value = util_get_field_value(obj, field_config.name)
    if field_config.link_url:
        return util_build_field_link(value, field_config, obj)
    return util_format_field_value(value, field_config)


@register.filter
def format_with_obj(url_pattern, obj):
    """Format URL pattern with object attributes."""
    if not url_pattern:
        return ""

    url = url_pattern
    # Replace common placeholders with escaped values
    replacements = {
        "{pk}": escape(str(obj.pk)),
        "{id}": escape(str(obj.pk)),
    }

    for placeholder, value in replacements.items():
        url = url.replace(placeholder, value)

    # Replace attribute placeholders like {slug}, {username}, etc.
    import re

    pattern = r"\{(\w+)\}"
    matches = re.findall(pattern, url)
    for match in matches:
        if hasattr(obj, match):
            # Escape the attribute value to prevent XSS
            escaped_value = escape(str(getattr(obj, match)))
            url = url.replace(f"{{{match}}}", escaped_value)

    return url


@register.filter
def add(value, arg):
    """Add two values."""
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        return value


@register.filter
def get_choice_display(obj, field_name):
    """Get the display value for a choice field."""
    if not obj or not field_name:
        return ""

    # Get the display method name
    display_method = f"get_{field_name}_display"

    # Check if the method exists
    if hasattr(obj, display_method):
        return getattr(obj, display_method)()

    # Fallback to the raw value
    return getattr(obj, field_name, "")
