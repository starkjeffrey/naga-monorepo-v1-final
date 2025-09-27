"""
UUID utilities for the Naga SIS system.

Provides UUID7 generation with fallback to UUID4 for compatibility.
UUID7 includes timestamp information and is more database-friendly.
"""

import uuid

try:
    from uuid_extensions import uuid7

    HAS_UUID7 = True
except ImportError:
    HAS_UUID7 = False


def generate_uuid() -> uuid.UUID:
    """
    Generate a UUID for new records.

    Uses UUID7 (time-ordered) if available, falls back to UUID4 (random).

    UUID7 benefits:
    - Time-ordered (sortable by creation time)
    - Better database index performance
    - Still cryptographically random
    - Native in Python 3.14+

    Returns:
        UUID7 if uuid7 package available, otherwise UUID4
    """
    if HAS_UUID7:
        return uuid7()
    else:
        return uuid.uuid4()


def generate_uuid7() -> uuid.UUID:
    """
    Explicitly generate UUID7 if available.

    Returns:
        UUID7 if available, otherwise UUID4
    """
    return generate_uuid()


def generate_uuid4() -> uuid.UUID:
    """
    Explicitly generate UUID4 (random).

    Returns:
        Standard UUID4
    """
    return uuid.uuid4()
