"""Base Transformation Classes

Abstract base classes and data structures for all transformers.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class TransformationContext:
    """
    Context passed to transformers containing metadata about the transformation.
    Think of this as a backpack of information that travels with each transformation.
    """

    source_table: str
    source_column: str
    target_column: str
    row_number: int
    pipeline_run_id: int | None = None
    metadata: dict[str, Any] | None = None


class BaseTransformer(ABC):
    """
    Abstract base class for all transformers.
    This ensures every transformer follows the same pattern, making them predictable and testable.
    """

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize()

    def _initialize(self):  # noqa: B027
        """
        Override this to load any resources needed by the transformer.
        This might include loading mapping tables, compiling regex patterns, etc.
        Default implementation does nothing.
        """
        # Default implementation - subclasses can override if needed
        pass

    @abstractmethod
    def transform(self, value: Any, context: TransformationContext) -> Any:
        """
        The main transformation method that every transformer must implement.
        Returns the transformed value.
        """
        pass

    @abstractmethod
    def can_transform(self, value: Any) -> bool:
        """
        Check if this transformer can handle the given value.
        This helps prevent errors and allows for conditional transformation.
        """
        pass

    def transform_with_fallback(self, value: Any, context: TransformationContext, fallback_value: Any = None) -> Any:
        """
        Safe transformation with fallback on error.
        This is crucial for production - we don't want one bad value to crash everything.
        """
        try:
            if self.can_transform(value):
                return self.transform(value, context)
            return fallback_value if fallback_value is not None else value
        except Exception as e:
            self.logger.warning(f"Transformation failed for {context.source_column}: {e}. Using fallback value.")
            return fallback_value if fallback_value is not None else value
