"""Custom template tags for the scheduling app."""

from django import template

register = template.Library()


@register.filter
def lookup(dictionary, key):
    """Template filter to access dictionary values or object attributes dynamically.

    Usage in template:
        {{ row|lookup:column.field }}

    This allows accessing object attributes when the attribute name is stored
    in a variable (column.field in this case).
    """
    if hasattr(dictionary, key):
        value = getattr(dictionary, key)
        # If it's a method, call it
        if callable(value):
            return value()
        return value
    elif hasattr(dictionary, "get"):
        return dictionary.get(key, "")
    return ""


@register.filter
def mul(value, arg):
    """Multiply the value by the argument."""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def div(value, arg):
    """Divide the value by the argument."""
    try:
        return float(value) / float(arg) if float(arg) != 0 else 0
    except (ValueError, TypeError):
        return 0


@register.simple_tag
def get_item(dictionary, key):
    """Get an item from a dictionary using a variable key."""
    return dictionary.get(key)
