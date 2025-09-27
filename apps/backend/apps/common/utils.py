"""Common utility functions for the Naga SIS project.

This module provides shared utility functions that can be used across
all apps without creating circular dependencies.
"""

import re
from datetime import date
from typing import Any
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

# Phone number validation constants
MIN_PHONE_LENGTH = 8
MAX_PHONE_LENGTH = 15
LOCAL_PHONE_CUTOFF = 10


def get_current_date() -> date:
    """Get current date using timezone-aware datetime.

    This function replaces date.today() to ensure timezone awareness
    and resolve DTZ011 linting errors.

    Returns:
        Current date in the configured timezone
    """
    return timezone.now().date()


def generate_unique_code(prefix: str = "", length: int = 8) -> str:
    """Generate a unique alphanumeric code with optional prefix.

    Args:
        prefix: Optional prefix for the code
        length: Length of the random portion (default 8)

    Returns:
        Unique code string
    """
    unique_part = str(uuid4()).replace("-", "")[:length].upper()
    return f"{prefix}{unique_part}" if prefix else unique_part


def validate_phone_number(phone: str) -> None:
    """Validate phone number format.

    Args:
        phone: Phone number string to validate

    Raises:
        ValidationError: If phone number is invalid
    """
    # Remove all non-digit characters for validation
    digits_only = re.sub(r"\D", "", phone)

    # Check if it's a valid length (8-15 digits as per international standards)
    if not MIN_PHONE_LENGTH <= len(digits_only) <= MAX_PHONE_LENGTH:
        raise ValidationError(_("Phone number must be between 8 and 15 digits long."))


def normalize_phone_number(phone: str, default_country_code: str = "855") -> str:
    """Normalize phone number to a consistent format.

    Args:
        phone: Raw phone number string
        default_country_code: Country code to use for local numbers (default: 855 for Cambodia)

    Returns:
        Normalized phone number

    Note:
        This function only adds country codes for clearly local numbers.
        International numbers should already include their country code.
    """
    if not phone:
        return ""

    # Remove all non-digit characters except +
    normalized = re.sub(r"[^\d+]", "", phone)

    if not normalized:
        return ""

    # If already has + prefix, assume it's correctly formatted international number
    if normalized.startswith("+"):
        return normalized

    # For numbers without +, be more conservative about adding country codes
    # Only add default country code for clearly local numbers (8-9 digits for Cambodia)
    if 8 <= len(normalized) <= 9:
        # This looks like a local Cambodian number
        normalized = f"+{default_country_code}{normalized}"
    elif len(normalized) >= 10:
        # This might be an international number without +, or a local number with area code
        # Be conservative and ask user to clarify rather than guessing
        # For now, add + but log a warning in production systems
        normalized = f"+{normalized}"
    else:
        # Too short to be a valid phone number, return as-is
        pass

    return normalized


def safe_get_attr(obj: Any, attr_path: str, default: Any = None) -> Any:
    """Safely get nested attribute from object.

    Args:
        obj: Object to get attribute from
        attr_path: Dot-separated attribute path (e.g., "user.profile.name")
        default: Default value if attribute doesn't exist

    Returns:
        Attribute value or default
    """
    try:
        for attr in attr_path.split("."):
            obj = getattr(obj, attr)
    except (AttributeError, TypeError):
        return default
    else:
        return obj


def truncate_string(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate string to maximum length with suffix.

    Args:
        text: String to truncate
        max_length: Maximum length including suffix
        suffix: Suffix to add when truncating

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text

    truncate_length = max_length - len(suffix)
    if truncate_length <= 0:
        return suffix[:max_length]

    return text[:truncate_length] + suffix


def format_name(first_name: str, last_name: str, format_type: str = "full") -> str:
    """Format person name according to specified format.

    Args:
        first_name: Person's first name
        last_name: Person's last name
        format_type: Format type ("full", "last_first", "initials")

    Returns:
        Formatted name string
    """
    first_name = first_name.strip()
    last_name = last_name.strip()

    if format_type == "full":
        return f"{first_name} {last_name}".strip()
    if format_type == "last_first":
        return f"{last_name}, {first_name}".strip()
    if format_type == "initials":
        first_initial = first_name[0].upper() if first_name else ""
        last_initial = last_name[0].upper() if last_name else ""
        return f"{first_initial}{last_initial}"
    return f"{first_name} {last_name}".strip()


def generate_slug_with_uniqueness(
    model_class,
    title: str,
    slug_field: str = "slug",
) -> str:
    """Generate a unique slug for a model instance.

    Args:
        model_class: The model class to check uniqueness against
        title: The title/name to create slug from
        slug_field: The name of the slug field (default 'slug')

    Returns:
        Unique slug string
    """
    base_slug = slugify(title)
    if not base_slug:
        base_slug = "untitled"

    slug = base_slug
    counter = 1

    # Check for uniqueness and append counter if needed
    filter_kwargs = {slug_field: slug}
    while model_class.objects.filter(**filter_kwargs).exists():
        slug = f"{base_slug}-{counter}"
        filter_kwargs[slug_field] = slug
        counter += 1

    return slug


def model_to_dict_with_relations(
    instance,
    exclude_fields: list | None = None,
) -> dict:
    """Convert model instance to dictionary including foreign key representations.

    Args:
        instance: Model instance to convert
        exclude_fields: List of field names to exclude

    Returns:
        Dictionary representation of the model
    """
    exclude_fields = exclude_fields or []
    data = {}

    for field in instance._meta.fields:
        if field.name in exclude_fields:
            continue

        value = getattr(instance, field.name)

        # Handle foreign keys
        if field.many_to_one and value:
            data[field.name] = {
                "id": value.pk,
                "str": str(value),
            }
        else:
            data[field.name] = value

    return data


def bulk_update_status(queryset, new_status: str, user=None) -> int:
    """Bulk update status for queryset with proper audit trail.

    Args:
        queryset: QuerySet to update
        new_status: New status value
        user: User performing the update (for audit trail)

    Returns:
        Number of records updated
    """
    update_fields = {
        "status": new_status,
        "status_changed_at": timezone.now(),
    }

    # Add user tracking if the model supports it and user is provided
    if user and hasattr(queryset.model, "updated_by"):
        update_fields["updated_by"] = user

    # Add timestamp tracking if the model supports it
    if hasattr(queryset.model, "updated_at"):
        update_fields["updated_at"] = timezone.now()

    return queryset.update(**update_fields)


def get_model_changes(
    old_instance,
    new_instance,
    exclude_fields: list | None = None,
) -> dict:
    """Get dictionary of changed fields between two model instances.

    Args:
        old_instance: Original model instance
        new_instance: Updated model instance
        exclude_fields: Fields to exclude from comparison

    Returns:
        Dictionary of changed fields with old and new values
    """
    exclude_fields = exclude_fields or ["updated_at", "modified_at"]
    changes = {}

    for field in old_instance._meta.fields:
        if field.name in exclude_fields:
            continue

        old_value = getattr(old_instance, field.name)
        new_value = getattr(new_instance, field.name)

        if old_value != new_value:
            changes[field.name] = {"old": old_value, "new": new_value}

    return changes
