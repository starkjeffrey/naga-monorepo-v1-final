"""
Enhanced Stage3 Data Cleaning with Cross-Table Dependencies

Supports header-detail optimization where dimension tables (like academicclasses)
are processed first and their cleaned values are cached for reuse in fact tables
(like academiccoursetakers).
"""

import logging
import time
from typing import Any

from django.db import connection

from ..cleaners.engine import Stage3DataCleaner
from ..configs.base import TableConfig
from .dependencies import CrossTableCleaningCache, TableDependencyResolver


class DependencyAwareStage3Clean:
    """Enhanced Stage 3 cleaner with cross-table dependency support"""

    def __init__(self, run_id: int):
        self.run_id = run_id
        self.logger = logging.getLogger(__name__)
        self.dependency_resolver = TableDependencyResolver()
        self.cleaning_cache = CrossTableCleaningCache()
        self.processed_tables: dict[str, dict[str, Any]] = {}

    def setup_dependencies(self) -> None:
        """Setup standard dependencies for academic data pipeline"""
        from .dependencies import setup_academic_dependencies

        setup_academic_dependencies(self.dependency_resolver)

    def execute_multi_table_pipeline(self, table_configs: list[TableConfig], dry_run: bool = False) -> dict[str, Any]:
        """
        Execute Stage3 cleaning across multiple tables with dependency optimization.

        Processing flow:
        1. Analyze dependencies and determine processing order
        2. Process header tables first (e.g., academicclasses)
        3. Cache cleaned shared field values
        4. Process detail tables using cached values (e.g., academiccoursetakers)
        """

        start_time = time.time()

        try:
            self.logger.info("Starting dependency-aware Stage 3 cleaning")

            # Setup dependencies
            self.setup_dependencies()

            # Determine processing order
            table_names = [config.table_name for config in table_configs]
            processing_order = self.dependency_resolver.get_processing_order(table_names)

            # Process tables in dependency order
            total_processed = 0
            all_results = {}

            for table_name in processing_order:
                config = next(cfg for cfg in table_configs if cfg.table_name == table_name)

                self.logger.info(f"Processing table: {table_name}")

                if self.dependency_resolver.is_header_table(table_name):
                    # Process header table and cache shared fields
                    result = self._process_header_table(config, dry_run)
                    self._cache_shared_fields(config, result)
                else:
                    # Process detail table using cached values
                    result = self._process_detail_table(config, dry_run)

                all_results[table_name] = result
                total_processed += result.get("total_rows_cleaned", 0)

                self.processed_tables[table_name] = result

            execution_time = time.time() - start_time

            # Generate performance summary
            cache_stats = self.cleaning_cache.get_cache_stats()

            summary = {
                "total_tables_processed": len(processing_order),
                "total_rows_processed": total_processed,
                "processing_order": processing_order,
                "execution_time_seconds": execution_time,
                "table_results": all_results,
                "cache_performance": cache_stats,
                "optimization_summary": self._generate_optimization_summary(),
            }

            self.logger.info(
                f"Dependency-aware Stage 3 completed in {execution_time:.2f}s - {total_processed} total rows processed"
            )

            return summary

        except Exception as e:
            self.logger.error(f"Dependency-aware Stage 3 failed: {e!s}")
            raise

    def _process_header_table(self, config: TableConfig, dry_run: bool) -> dict[str, Any]:
        """Process a header table (dimension table) that provides shared fields"""

        self.logger.info(f"Processing header table: {config.table_name}")

        # Create standard Stage3 cleaner for this table
        cleaner = Stage3DataCleaner(config, self.logger, self.run_id)

        # Execute normal cleaning
        stage2_result = {"total_rows": self._get_table_row_count(config.raw_table_name)}
        result = cleaner.execute(stage2_result, dry_run)

        self.logger.info(f"Header table {config.table_name} processed: {result.get('total_rows_cleaned', 0)} rows")

        return result

    def _process_detail_table(self, config: TableConfig, dry_run: bool) -> dict[str, Any]:
        """Process a detail table that uses cached shared field values"""

        self.logger.info(f"Processing detail table: {config.table_name}")

        # Create enhanced cleaner that uses cache
        cleaner = CachedFieldStage3Cleaner(
            config, self.logger, self.run_id, self.dependency_resolver, self.cleaning_cache
        )

        # Execute cleaning with cache support
        stage2_result = {"total_rows": self._get_table_row_count(config.raw_table_name)}
        result = cleaner.execute(stage2_result, dry_run)

        self.logger.info(f"Detail table {config.table_name} processed: {result.get('total_rows_cleaned', 0)} rows")

        return result

    def _cache_shared_fields(self, config: TableConfig, result: dict[str, Any]) -> None:
        """Extract and cache cleaned shared field values from processed header table"""

        if not self.dependency_resolver.is_header_table(config.table_name):
            return

        self.logger.info(f"Caching shared fields for header table: {config.table_name}")

        # Get all shared fields provided by this table
        self.dependency_resolver.get_dependent_tables(config.table_name)

        with connection.cursor() as cursor:
            # For each shared field, extract original -> cleaned mappings
            for mapping in config.column_mappings:
                shared_field_info = self.dependency_resolver.get_shared_field_mapping(
                    config.table_name, mapping.source_name
                )

                if shared_field_info:
                    self._extract_and_cache_field_mappings(cursor, config, mapping, shared_field_info)

    def _extract_and_cache_field_mappings(self, cursor, config: TableConfig, mapping, shared_field_info) -> None:
        """Extract original->cleaned field mappings and cache them"""

        # Query to get original vs cleaned values
        query = f'''
            SELECT DISTINCT
                raw."{mapping.source_name}" as original_value,
                cleaned."{mapping.target_name}" as cleaned_value
            FROM "{config.raw_table_name}" raw
            INNER JOIN "{config.cleaned_table_name}" cleaned
                ON raw."_csv_row_number" = cleaned."_original_row_id"
            WHERE raw."{mapping.source_name}" IS NOT NULL
                AND cleaned."{mapping.target_name}" IS NOT NULL
        '''

        cursor.execute(query)
        mappings = {row[0]: row[1] for row in cursor.fetchall()}

        # Cache the mappings
        self.cleaning_cache.cache_cleaned_field_values(config.table_name, mapping.source_name, mappings)

        self.logger.info(f"Cached {len(mappings)} mappings for {config.table_name}.{mapping.source_name}")

    def _get_table_row_count(self, table_name: str) -> int:
        """Get row count for a table"""
        with connection.cursor() as cursor:
            cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            return cursor.fetchone()[0]

    def _generate_optimization_summary(self) -> dict[str, Any]:
        """Generate summary of optimization benefits"""

        optimization_summary: dict[str, Any] = {
            "shared_field_optimizations": [],
            "estimated_processing_saved": 0,
            "cache_effectiveness": {},
        }

        # Calculate optimization benefits
        for cache_key, stats in self.cleaning_cache.get_cache_stats().items():
            if stats["hits"] > 0:
                saved_operations = stats["hits"]  # Each hit saved a cleaning operation

                optimization_summary["shared_field_optimizations"].append(
                    {
                        "field": cache_key,
                        "cache_hits": stats["hits"],
                        "operations_saved": saved_operations,
                        "hit_rate": stats["hit_rate"],
                    }
                )

                optimization_summary["estimated_processing_saved"] += saved_operations

        return optimization_summary


class CachedFieldStage3Cleaner(Stage3DataCleaner):
    """Stage3 cleaner that uses cached values for shared fields"""

    def __init__(self, config, logger, run_id, dependency_resolver, cleaning_cache):
        super().__init__(config, logger, run_id)
        self.dependency_resolver = dependency_resolver
        self.cleaning_cache = cleaning_cache

        # Add cached field lookup to cleaning engine
        self.cleaning_engine.add_custom_rule("use_cached_field", self._use_cached_field)

    def _clean_row(self, row_dict: dict[str, Any]) -> tuple[dict | None, dict]:
        """Override to use cached field values for shared fields"""

        # Check if this row has any shared field dependencies
        dependencies = self.dependency_resolver.get_table_dependencies(self.config.table_name)

        # Pre-populate shared field values from cache
        for dependency in dependencies:
            for shared_field in dependency.shared_fields:
                if shared_field in row_dict:
                    original_value = row_dict[shared_field]
                    cached_value = self.cleaning_cache.get_cleaned_value(
                        dependency.source_table, shared_field, original_value
                    )

                    if cached_value is not None:
                        # Replace with cached cleaned value
                        row_dict[f"_cached_{shared_field}"] = cached_value
                        self.logger.debug(
                            f"Using cached value for {shared_field}: '{original_value}' -> '{cached_value}'"
                        )

        # Continue with normal row cleaning
        return super()._clean_row(row_dict)

    def _use_cached_field(self, value: str, column_name: str | None = None) -> str:
        """Use cached cleaned value if available"""

        # This would be configured in column mappings to use cached values
        dependencies = self.dependency_resolver.get_table_dependencies(self.config.table_name)

        for dependency in dependencies:
            for shared_field in dependency.shared_fields:
                if column_name and shared_field in column_name:
                    cached_value = self.cleaning_cache.get_cleaned_value(dependency.source_table, shared_field, value)
                    if cached_value is not None:
                        return cached_value

        # Fallback to original value if no cache hit
        return value
