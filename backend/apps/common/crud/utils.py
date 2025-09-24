"""CRUD Framework Utilities."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.db import models
from django.template.defaultfilters import truncatechars
from django.utils.formats import date_format, number_format
from django.utils.html import escape, format_html
from django.utils.safestring import SafeString
from django.utils.timezone import localtime

from .config import FieldConfig


def get_field_value(obj: models.Model, field_name: str) -> Any:
    """Get field value from object, handling relations."""
    if "." in field_name:
        # Handle nested relations like 'category.name'
        parts = field_name.split(".")
        value: Any = obj
        for part in parts:
            if value is None:
                return None
            value = getattr(value, part, None)
        return value

    # Handle special methods
    if hasattr(obj, f"get_{field_name}_display"):
        return getattr(obj, f"get_{field_name}_display")()

    return getattr(obj, field_name, None)


def format_field_value(value: Any, field_config: FieldConfig) -> str:
    """Format field value for display."""
    if value is None:
        return "-"

    # Custom renderer takes precedence
    if field_config.renderer:
        return field_config.renderer(value, field_config)

    # Format based on field type
    if field_config.field_type == "boolean":
        return format_boolean(value)

    elif field_config.field_type == "date":
        return format_date_value(value, field_config.format)

    elif field_config.field_type == "datetime":
        return format_datetime_value(value, field_config.format)

    elif field_config.field_type == "number":
        decimal_places = int(field_config.format) if field_config.format and field_config.format.isdigit() else None
        return format_number_value(value, decimal_places)

    elif field_config.field_type == "image":
        return format_image(value)

    elif field_config.field_type == "foreign_key":
        return escape(str(value)) if value else "-"

    else:
        # Text field - escape HTML to prevent XSS
        text: str | SafeString = escape(str(value))
        if field_config.truncate:
            text = truncatechars(text, field_config.truncate)
        return text


def format_boolean(value: bool) -> str:
    """Format boolean value."""
    if value:
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs '
            'font-medium bg-green-100 text-green-800">'
            '<svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">'
            '<path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 '
            '1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd"></path>'
            "</svg>"
            "Yes"
            "</span>",
        )
    else:
        return format_html(
            '<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs '
            'font-medium bg-red-100 text-red-800">'
            '<svg class="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">'
            '<path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 '
            "1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 "
            '10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>'
            "</svg>"
            "No"
            "</span>",
        )


def format_date_value(value: date, format_str: str | None = None) -> str:
    """Format date value."""
    if not isinstance(value, date):
        return str(value)

    if format_str:
        return value.strftime(format_str)

    return date_format(value, "SHORT_DATE_FORMAT")


def format_datetime_value(value: datetime, format_str: str | None = None) -> str:
    """Format datetime value."""
    if not isinstance(value, datetime):
        return str(value)

    # Convert to local time
    value = localtime(value)

    if format_str:
        return value.strftime(format_str)

    return date_format(value, "SHORT_DATETIME_FORMAT")


def format_number_value(value: Any, decimal_places: int | None = None) -> str:
    """Format number value."""
    if isinstance(value, int | float | Decimal):
        if decimal_places is not None:
            return number_format(value, decimal_places)
        return number_format(value)
    return str(value)


def format_image(value: Any) -> str:
    """Format image field."""
    if hasattr(value, "url"):
        # Escape the URL to prevent XSS attacks
        return format_html(
            '<img src="{}" alt="Image" class="h-10 w-10 rounded-full object-cover">',
            escape(str(value.url)),
        )
    return "-"


def get_cell_css_class(field_config: FieldConfig, value: Any) -> str:
    """Get CSS class for table cell."""
    classes = []

    if field_config.css_class:
        classes.append(field_config.css_class)

    # Add type-specific classes
    if field_config.field_type == "number":
        classes.append("text-right")
    elif field_config.field_type == "boolean":
        classes.append("text-center")
    elif field_config.field_type == "image":
        classes.append("text-center")

    return " ".join(classes)


def build_field_link(value: Any, field_config: FieldConfig, obj: models.Model) -> str:
    """Build link for field if configured."""
    if not field_config.link_url:
        return format_field_value(value, field_config)

    # Replace placeholders in URL with escaped values
    url = field_config.link_url
    if "{pk}" in url:
        url = url.replace("{pk}", escape(str(obj.pk)))
    if "{id}" in url:
        url = url.replace("{id}", escape(str(obj.pk)))
    if "{value}" in url and value:
        url = url.replace("{value}", escape(str(value)))

    formatted_value = format_field_value(value, field_config)

    return format_html(
        '<a href="{}" class="text-blue-600 hover:text-blue-800 hover:underline">{}</a>',
        escape(url),
        formatted_value,
    )
