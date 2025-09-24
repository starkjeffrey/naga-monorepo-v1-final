"""
Data Pipeline Cross-Table Dependencies

Handles table processing order optimization and shared field caching
for header-detail relationships like academicclasses -> academiccoursetakers.
"""

import logging
from collections import defaultdict, deque
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field


@dataclass
class SharedFieldMapping:
    """Configuration for shared field optimization"""
    field_name: str
    source_table: str
    target_tables: List[str]
    cleaning_rules: List[str] = field(default_factory=list)
    cache_size_estimate: int = 1000  # Expected number of unique values


@dataclass  
class TableDependency:
    """Represents a table dependency relationship"""
    target_table: str
    source_table: str
    shared_fields: List[str]
    dependency_type: str = "shared_field"  # shared_field, foreign_key, etc.


class TableDependencyResolver:
    """Resolves table processing order based on cross-table dependencies"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.dependencies: Dict[str, List[TableDependency]] = defaultdict(list)
        self.shared_fields: Dict[str, SharedFieldMapping] = {}
        self.table_metadata: Dict[str, Dict[str, Any]] = {}
        
    def add_shared_field_dependency(self, 
                                   source_table: str,
                                   target_tables: List[str], 
                                   field_name: str,
                                   cleaning_rules: List[str] = None) -> None:
        """Register a shared field dependency for optimization"""
        
        if cleaning_rules is None:
            cleaning_rules = []
            
        # Create shared field mapping
        shared_field = SharedFieldMapping(
            field_name=field_name,
            source_table=source_table,
            target_tables=target_tables,
            cleaning_rules=cleaning_rules
        )
        
        self.shared_fields[f"{source_table}.{field_name}"] = shared_field
        
        # Create dependency relationships
        for target_table in target_tables:
            dependency = TableDependency(
                target_table=target_table,
                source_table=source_table,
                shared_fields=[field_name]
            )
            self.dependencies[target_table].append(dependency)
            
        self.logger.info(
            f"Added shared field dependency: {source_table}.{field_name} "
            f"-> {target_tables}"
        )
    
    def register_table_metadata(self, table_name: str, metadata: Dict[str, Any]) -> None:
        """Register table metadata for processing optimization"""
        self.table_metadata[table_name] = metadata
        
    def get_processing_order(self, tables: List[str]) -> List[str]:
        """
        Calculate optimal processing order using topological sort.
        
        Tables with dependencies are processed after their prerequisites.
        """
        # Build adjacency list for dependency graph
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        # Initialize all tables with zero in-degree
        for table in tables:
            in_degree[table] = 0
            
        # Build dependency graph
        for table in tables:
            if table in self.dependencies:
                for dependency in self.dependencies[table]:
                    source = dependency.source_table
                    if source in tables:  # Only consider tables in current processing set
                        graph[source].append(table)
                        in_degree[table] += 1
        
        # Topological sort using Kahn's algorithm
        queue = deque([table for table in tables if in_degree[table] == 0])
        processing_order = []
        
        while queue:
            current_table = queue.popleft()
            processing_order.append(current_table)
            
            # Process neighbors
            for neighbor in graph[current_table]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # Check for circular dependencies
        if len(processing_order) != len(tables):
            remaining = set(tables) - set(processing_order)
            self.logger.error(f"Circular dependency detected in tables: {remaining}")
            # Add remaining tables in original order as fallback
            processing_order.extend(remaining)
            
        self.logger.info(f"Table processing order: {processing_order}")
        return processing_order
    
    def get_table_dependencies(self, table_name: str) -> List[TableDependency]:
        """Get all dependencies for a specific table"""
        return self.dependencies.get(table_name, [])
        
    def get_shared_field_mapping(self, source_table: str, field_name: str) -> Optional[SharedFieldMapping]:
        """Get shared field mapping for optimization"""
        key = f"{source_table}.{field_name}"
        return self.shared_fields.get(key)
    
    def is_header_table(self, table_name: str) -> bool:
        """Check if table is a header table (provides shared fields)"""
        return any(
            mapping.source_table == table_name 
            for mapping in self.shared_fields.values()
        )
    
    def get_dependent_tables(self, source_table: str) -> List[str]:
        """Get all tables that depend on the given source table"""
        dependent_tables = []
        for mapping in self.shared_fields.values():
            if mapping.source_table == source_table:
                dependent_tables.extend(mapping.target_tables)
        return list(set(dependent_tables))  # Remove duplicates


class CrossTableCleaningCache:
    """Caches cleaned field values for reuse across tables"""
    
    def __init__(self, max_cache_size: int = 100000):
        self.logger = logging.getLogger(__name__)
        self.field_caches: Dict[str, Dict[str, str]] = {}
        self.cache_stats: Dict[str, Dict[str, int]] = defaultdict(lambda: {'hits': 0, 'misses': 0})
        self.max_cache_size = max_cache_size
        
    def cache_cleaned_field_values(self, 
                                  table_name: str,
                                  field_name: str, 
                                  mappings: Dict[str, str]) -> None:
        """Cache cleaned field values for a specific table.field"""
        
        cache_key = f"{table_name}.{field_name}"
        
        # Prevent cache overflow
        if len(mappings) > self.max_cache_size:
            self.logger.warning(
                f"Cache size limit exceeded for {cache_key}: {len(mappings)} > {self.max_cache_size}"
            )
            # Keep only the most common values (implementation could be enhanced)
            mappings = dict(list(mappings.items())[:self.max_cache_size])
        
        self.field_caches[cache_key] = mappings
        
        self.logger.info(
            f"Cached {len(mappings)} cleaned values for {cache_key}"
        )
    
    def get_cleaned_value(self, 
                         table_name: str, 
                         field_name: str, 
                         original_value: str) -> Optional[str]:
        """Retrieve cached cleaned value"""
        
        cache_key = f"{table_name}.{field_name}"
        
        if cache_key not in self.field_caches:
            self.cache_stats[cache_key]['misses'] += 1
            return None
            
        cached_mapping = self.field_caches[cache_key]
        
        if original_value in cached_mapping:
            self.cache_stats[cache_key]['hits'] += 1
            return cached_mapping[original_value]
        else:
            self.cache_stats[cache_key]['misses'] += 1
            return None
    
    def get_cache_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get cache performance statistics"""
        stats = {}
        for cache_key, stat_data in self.cache_stats.items():
            total = stat_data['hits'] + stat_data['misses']
            hit_rate = stat_data['hits'] / total if total > 0 else 0
            
            stats[cache_key] = {
                'hits': stat_data['hits'],
                'misses': stat_data['misses'], 
                'total_requests': total,
                'hit_rate': hit_rate,
                'cache_size': len(self.field_caches.get(cache_key, {}))
            }
            
        return stats
    
    def clear_cache(self, table_name: str = None, field_name: str = None) -> None:
        """Clear cache for specific table.field or entire cache"""
        
        if table_name and field_name:
            cache_key = f"{table_name}.{field_name}"
            if cache_key in self.field_caches:
                del self.field_caches[cache_key]
                self.logger.info(f"Cleared cache for {cache_key}")
        else:
            self.field_caches.clear()
            self.cache_stats.clear() 
            self.logger.info("Cleared all caches")


# Example usage configuration for academicclasses -> academiccoursetakers
def setup_academic_dependencies(resolver: TableDependencyResolver) -> None:
    """Configure academic table dependencies"""
    
    # academicclasses provides cleaned classid for academiccoursetakers
    resolver.add_shared_field_dependency(
        source_table="academicclasses",
        target_tables=["academiccoursetakers"],
        field_name="classid",
        cleaning_rules=["trim", "uppercase", "normalize_class_id"]
    )
    
    # Register table metadata for optimization
    resolver.register_table_metadata("academicclasses", {
        "estimated_rows": 500,
        "filters": {"is_shadow": 0},
        "primary_keys": ["classid"],
        "provides_shared_fields": ["classid"]
    })
    
    resolver.register_table_metadata("academiccoursetakers", {
        "estimated_rows": 15000,
        "depends_on": ["academicclasses"], 
        "foreign_keys": {"classid": "academicclasses.classid"}
    })