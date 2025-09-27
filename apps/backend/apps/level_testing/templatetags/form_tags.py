"""from datetime import date
Template tags for form manipulation in level testing app.

Provides utilities for adding CSS classes to form fields
and other form-related template operations.
"""

from django import template
from django.forms import BoundField

register = template.Library()


@register.filter
def add_class(field, css_classes):
    """Add CSS classes to a form field widget.

    Usage: {{ field|add_class:"class1 class2 class3" }}

    Args:
        field: A Django form field
        css_classes: String of CSS classes separated by spaces

    Returns:
        The field with updated CSS classes
    """
    if not isinstance(field, BoundField):
        return field

    # Get existing classes
    existing_classes = field.field.widget.attrs.get("class", "")

    # Combine existing and new classes
    all_classes = f"{existing_classes} {css_classes}".strip()

    # Update the widget attributes
    field.field.widget.attrs.update({"class": all_classes})

    return field


@register.filter
def add_attr(field, attrs):
    """Add HTML attributes to a form field widget.

    Usage: {{ field|add_attr:"placeholder=Enter your name,required=True" }}

    Args:
        field: A Django form field
        attrs: String of attributes in "key=value,key=value" format

    Returns:
        The field with updated attributes
    """
    if not isinstance(field, BoundField):
        return field

    # Parse attributes string
    attr_dict = {}
    if attrs:
        for attr_pair in attrs.split(","):
            if "=" in attr_pair:
                key, value = attr_pair.split("=", 1)
                attr_dict[key.strip()] = value.strip()

    # Update the widget attributes
    field.field.widget.attrs.update(attr_dict)

    return field


@register.filter
def field_type(field):
    """Get the type of a form field widget.

    Usage: {% if field|field_type == "TextInput" %}...{% endif %}

    Args:
        field: A Django form field

    Returns:
        String name of the widget class
    """
    if not isinstance(field, BoundField):
        return ""

    return field.field.widget.__class__.__name__


@register.filter
def is_checkbox(field):
    """Check if a form field is a checkbox.

    Usage: {% if field|is_checkbox %}...{% endif %}

    Args:
        field: A Django form field

    Returns:
        Boolean indicating if field is a checkbox
    """
    return field_type(field) == "CheckboxInput"


@register.filter
def is_select(field):
    """Check if a form field is a select dropdown.

    Usage: {% if field|is_select %}...{% endif %}

    Args:
        field: A Django form field

    Returns:
        Boolean indicating if field is a select
    """
    return field_type(field) == "Select"


@register.filter
def is_textarea(field):
    """Check if a form field is a textarea.

    Usage: {% if field|is_textarea %}...{% endif %}

    Args:
        field: A Django form field

    Returns:
        Boolean indicating if field is a textarea
    """
    return field_type(field) == "Textarea"
