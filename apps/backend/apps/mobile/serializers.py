"""Backward compatibility module for mobile serializers.

This module provides compatibility with legacy test code that expects
DRF-style serializers. In Django-Ninja, we use Pydantic schemas instead.

For actual schema definitions, see schemas.py.
"""

# Import schemas and provide them with serializer names for backward compatibility
from .schemas import (
    AttendanceCreateSchema as AttendanceCreateSerializer,
)
from .schemas import (
    AttendanceSchema as AttendanceSerializer,
)
from .schemas import (
    AttendanceUpdateSchema as AttendanceUpdateSerializer,
)
from .schemas import (
    ClassScheduleSchema as ClassScheduleSerializer,
)
from .schemas import (
    GradeSchema as GradeSerializer,
)
from .schemas import (
    NotificationSchema as NotificationSerializer,
)
from .schemas import (
    StudentProfileSchema as StudentProfileSerializer,
)

# Legacy compatibility exports
__all__ = [
    "AttendanceCreateSerializer",
    "AttendanceSerializer",
    "AttendanceUpdateSerializer",
    "ClassScheduleSerializer",
    "GradeSerializer",
    "NotificationSerializer",
    "StudentProfileSerializer",
]
