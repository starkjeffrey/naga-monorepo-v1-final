"""Template tags for CRUD framework."""

from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe

from ..crud.utils import get_field_value as util_get_field_value

register = template.Library()


@register.filter
def render_field(obj, field):
    """Render a field value with its custom renderer if provided."""
    if not obj or not field:
        return ""

    value = util_get_field_value(obj, field.name)

    # Get rendered value (with or without custom renderer)
    rendered_value = value
    if hasattr(field, "renderer") and field.renderer:
        try:
            rendered_value = field.renderer(value, field)
        except Exception:
            # Fall back to default rendering if renderer fails
            rendered_value = str(value) if value is not None else "—"
    elif value is None:
        rendered_value = "—"
    elif isinstance(value, bool):
        if value:
            rendered_value = '<i class="fas fa-check text-green-600"></i>'
        else:
            rendered_value = '<i class="fas fa-times text-red-600"></i>'
    else:
        rendered_value = str(value)

    # Wrap in link if link_url is provided
    if hasattr(field, "link_url") and field.link_url:
        try:
            from django.utils.html import escape

            url = reverse(field.link_url, kwargs={"pk": obj.pk})
            escaped_url = escape(url)
            # Don't escape rendered_value if it's already HTML from a custom renderer
            if hasattr(field, "renderer") and field.renderer:
                # Custom renderer already returns safe HTML
                return mark_safe(
                    f'<a href="{escaped_url}" class="text-blue-600 hover:text-blue-800 hover:underline">'
                    f"{rendered_value}</a>"
                )
            else:
                # Escape plain text values
                escaped_value = escape(rendered_value)
                return mark_safe(
                    f'<a href="{escaped_url}" class="text-blue-600 hover:text-blue-800 hover:underline">'
                    f"{escaped_value}</a>"
                )
        except Exception as e:
            # If reverse fails, just return the value without link
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Failed to create link for {field.link_url}: {e}")
            pass

    # Return the rendered value (already wrapped in link if needed)
    return mark_safe(rendered_value)


@register.filter
def format_pk(url_pattern, pk):
    """Format URL pattern with object PK."""
    if not url_pattern:
        return ""

    # Handle named URL patterns
    if "/" not in url_pattern and ":" in url_pattern:
        try:
            return reverse(url_pattern, kwargs={"pk": pk})
        except Exception:
            return ""

    # Handle raw URL patterns
    return url_pattern.replace("{pk}", str(pk))
