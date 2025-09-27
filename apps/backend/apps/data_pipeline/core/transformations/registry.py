"""Transformation Registry

Central registry for all data transformers.
"""

import logging

from .base import BaseTransformer
from .education import CambodianEducationTransformer
from .text_encodings import KhmerTextTransformer


class TransformerRegistry:
    """
    Central registry for all transformers.
    Think of this as a library where all transformers are catalogued and ready to use.
    This pattern ensures we only create one instance of each transformer (singleton pattern).
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        """Ensure only one instance of the registry exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._transformers = {}
        return cls._instance

    def __init__(self):
        """Initialize the registry once."""
        if not self._initialized:
            self._initialize_transformers()
            TransformerRegistry._initialized = True

    def _initialize_transformers(self):
        """
        Register all available transformers.
        Each transformer is created once and reused for all transformations.
        """
        self._transformers = {
            "khmer.limon_to_unicode": KhmerTextTransformer(),
            "khmer.detect_encoding": KhmerTextTransformer(),
            "education.course_code": CambodianEducationTransformer(),
            "education.term_code": CambodianEducationTransformer(),
            "education.student_type": CambodianEducationTransformer(),
        }

        logging.info(f"Initialized {len(self._transformers)} transformers")

    def get_transformer(self, transformer_name: str) -> BaseTransformer | None:
        """
        Retrieve a transformer by name.
        Returns None if transformer not found.
        """
        if transformer_name not in self._transformers:
            logging.warning(f"Transformer '{transformer_name}' not found in registry")
            return None
        return self._transformers[transformer_name]

    def list_transformers(self) -> list:
        """Get list of all available transformer names."""
        return list(self._transformers.keys())

    def register_transformer(self, name: str, transformer: BaseTransformer):
        """
        Dynamically register a new transformer.
        Useful for testing or adding custom transformers at runtime.
        """
        if name in self._transformers:
            logging.warning(f"Overwriting existing transformer: {name}")
        self._transformers[name] = transformer


# Create global registry instance
transformer_registry = TransformerRegistry()
