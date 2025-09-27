"""Pipeline Table Configurations

Configuration modules for each table processed by the pipeline.
Each configuration defines column mappings, cleaning rules, validation, and transformations.
"""

from .base import (
    ColumnMapping,
    PipelineLogger,
    PipelineResult,
    TableConfig,
    TransformationRule,
)

# Import table-specific configurations
try:
    from .academicclasses import ACADEMICCLASSES_CONFIG
except ImportError:
    ACADEMICCLASSES_CONFIG = None

try:
    from .academiccoursetakers import ACADEMICCOURSETAKERS_CONFIG
except ImportError:
    ACADEMICCOURSETAKERS_CONFIG = None

try:
    from .receipt_headers import RECEIPT_HEADERS_CONFIG
except ImportError:
    RECEIPT_HEADERS_CONFIG = None

try:
    from .receipt_items import RECEIPT_ITEMS_CONFIG
except ImportError:
    RECEIPT_ITEMS_CONFIG = None

try:
    from .students import STUDENTS_CONFIG
except ImportError:
    STUDENTS_CONFIG = None

try:
    from .terms import TERMS_CONFIG
except ImportError:
    TERMS_CONFIG = None

__all__ = [
    "ACADEMICCLASSES_CONFIG",
    "ACADEMICCOURSETAKERS_CONFIG",
    "RECEIPT_HEADERS_CONFIG",
    "RECEIPT_ITEMS_CONFIG",
    # Table configurations
    "STUDENTS_CONFIG",
    "TERMS_CONFIG",
    # Base classes
    "ColumnMapping",
    "PipelineLogger",
    "PipelineResult",
    "TableConfig",
    "TransformationRule",
]
