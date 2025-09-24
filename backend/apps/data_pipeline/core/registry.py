"""
Pipeline Registry

Central registry for table configurations and pipeline orchestration.
"""

import importlib
import logging
from typing import Any, cast

from ..configs.base import TableConfig
from .parsers import ClassIDParser, StudentNameParser


class PipelineRegistry:
    """Central registry for pipeline configurations and components"""

    def __init__(self):
        self._configs: dict[str, TableConfig] = {}
        self._parsers: dict[str, type] = {}
        self._transformers: dict[str, type] = {}
        self._initialized = False
        self.logger = logging.getLogger(__name__)

    def initialize(self):
        """Initialize registry with all configurations"""
        if self._initialized:
            return

        # Register built-in parsers
        self.register_parser("classid", ClassIDParser)
        self.register_parser("student_name", StudentNameParser)

        # Auto-discover and register table configurations
        self._discover_configurations()

        # Register transformers
        self._discover_transformers()

        self._initialized = True

    def register_config(self, config: TableConfig):
        """Register a table configuration"""
        # Validate the configuration
        errors = config.validate()
        if errors:
            raise ValueError(f"Invalid configuration for {config.table_name}: {errors}")

        self._configs[config.table_name] = config
        self.logger.info(f"Registered configuration for table: {config.table_name}")

    def get_config(self, table_name: str) -> TableConfig:
        """Get configuration for a specific table"""
        self.initialize()

        if table_name not in self._configs:
            raise ValueError(f"No configuration found for table: {table_name}")

        return self._configs[table_name]

    def register_parser(self, name: str, parser_class: type):
        """Register a field parser"""
        self._parsers[name] = parser_class
        self.logger.debug(f"Registered parser: {name}")

    def get_parser(self, name: str):
        """Get a parser instance by name"""
        if name not in self._parsers:
            raise ValueError(f"Parser not found: {name}")

        return self._parsers[name]()

    def register_transformer(self, name: str, transformer_class: type):
        """Register a data transformer"""
        self._transformers[name] = transformer_class
        self.logger.debug(f"Registered transformer: {name}")

    def get_transformer(self, name: str):
        """Get a transformer instance by name"""
        if name not in self._transformers:
            raise ValueError(f"Transformer not found: {name}")

        return self._transformers[name]()

    def list_tables(self) -> list[str]:
        """List all registered table names"""
        self.initialize()
        return list(self._configs.keys())

    def get_pipeline_order(self) -> list[str]:
        """
        Get tables in optimal processing order based on dependencies.
        Tables with no dependencies come first.
        """
        self.initialize()

        # Simple dependency resolution
        no_deps = []
        with_deps = {}

        for table_name, config in self._configs.items():
            deps = getattr(config, "dependencies", [])
            if not deps:
                no_deps.append(table_name)
            else:
                with_deps[table_name] = deps

        # Start with tables that have no dependencies
        ordered = no_deps.copy()

        # Resolve dependencies
        max_iterations = len(with_deps) * 2
        iteration = 0

        while with_deps and iteration < max_iterations:
            iteration += 1
            resolved_this_round = []

            for table_name, deps in with_deps.items():
                # Check if all dependencies are already processed
                if all(dep in ordered for dep in deps):
                    ordered.append(table_name)
                    resolved_this_round.append(table_name)

            # Remove resolved tables
            for table_name in resolved_this_round:
                del with_deps[table_name]

            # If we made no progress, there might be circular dependencies
            if not resolved_this_round and with_deps:
                self.logger.warning(f"Could not resolve dependencies for: {list(with_deps.keys())}")
                # Add remaining tables anyway
                ordered.extend(sorted(with_deps.keys()))
                break

        return ordered

    def validate_all(self) -> dict[str, list[str]]:
        """Validate all registered configurations"""
        self.initialize()

        validation_results = {}

        for table_name, config in self._configs.items():
            errors = config.validate()
            if errors:
                validation_results[table_name] = errors

        return validation_results

    def _discover_configurations(self):
        """Auto-discover table configurations from configs/ directory"""
        config_modules = [
            "apps.data_pipeline.configs.students",
            "apps.data_pipeline.configs.academicclasses",
            "apps.data_pipeline.configs.academiccoursetakers",
            "apps.data_pipeline.configs.terms",
            "apps.data_pipeline.configs.receipt_headers",
            "apps.data_pipeline.configs.receipt_items",
        ]

        for module_path in config_modules:
            try:
                module = importlib.import_module(module_path)

                # Look for CONFIG objects
                for attr_name in dir(module):
                    if attr_name.endswith("_CONFIG"):
                        config = getattr(module, attr_name)
                        if isinstance(config, TableConfig):
                            self.register_config(config)

            except ImportError as e:
                self.logger.debug(f"Could not import {module_path}: {e}")
            except Exception as e:
                self.logger.error(f"Error loading {module_path}: {e}")

    def _discover_transformers(self):
        """Auto-discover transformers from transformations/ directory"""
        try:
            from ..transformations.registry import transformer_registry

            # Register all transformers from the transformer registry
            for name, transformer_class in transformer_registry.get_all().items():
                self.register_transformer(name, transformer_class)

        except ImportError:
            self.logger.warning("Transformer registry not found")

    def get_config_for_stage(self, table_name: str, stage: int) -> dict[str, Any]:
        """Get stage-specific configuration for a table"""
        config = self.get_config(table_name)

        stage_configs = {
            1: {"table_name": f"{table_name}_stage1_raw", "preserve_original": True, "all_text_columns": True},
            2: {"table_name": f"{table_name}_stage1_raw", "profile_columns": True, "generate_recommendations": True},
            3: {
                "input_table": f"{table_name}_stage1_raw",
                "output_table": f"{table_name}_stage3_cleaned",
                "parse_complex_fields": table_name == "academiccoursetakers",
                "parser": "classid" if table_name == "academiccoursetakers" else None,
            },
            4: {
                "input_table": f"{table_name}_stage3_cleaned",
                "valid_table": f"{table_name}_stage4_valid",
                "invalid_table": f"{table_name}_stage4_invalid",
                "validator_class": config.validator_class,
            },
            5: {
                "input_table": f"{table_name}_stage4_valid",
                "output_table": f"{table_name}_stage5_transformed",
                "transformation_rules": config.transformation_rules,
            },
            6: {
                "input_table": f"{table_name}_stage5_transformed",
                "headers_table": f"{table_name}_headers",
                "lines_table": f"{table_name}_lines",
                "enabled": config.supports_record_splitting,
            },
        }

        return cast("dict[str, Any]", stage_configs.get(stage, {}))


# Global registry instance
registry = PipelineRegistry()


def get_registry() -> PipelineRegistry:
    """Get the global registry instance"""
    registry.initialize()
    return registry
