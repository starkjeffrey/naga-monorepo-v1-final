# Data Migration Documentation

## 🔄 Legacy Data Migration

This directory contains comprehensive documentation for migrating data from the legacy Naga system (v0) to the new clean architecture system (v1).

## 📁 Contents

### Migration Reports
- **migration-reports/** - Detailed audit reports from data migration operations
  - JSON format with comprehensive statistics
  - Success/failure rates with error categorization
  - Performance metrics and data integrity validation
  - **Required for all migration operations**

### Migration Guides
- **migration_environment_guide.md** - Migration environment setup and usage
- **student_migration_notes_250626.md** - Specific notes on student data migration
- **naga_import_procedures.md** - Standard import procedures and protocols

### Field Mapping
- **v0_to_v1_field_mapping.md** - Comprehensive field mapping from legacy to new system
  - Database schema differences
  - Data transformation requirements
  - Business logic changes

## ⚠️ Critical Migration Standards

### Mandatory Requirements
- **ALL migration scripts MUST inherit from `BaseMigrationCommand`**
- **Comprehensive audit reporting** for every migration operation
- **Rejection categorization** for all failed records
- **Data integrity validation** before and after migration

### Migration Environment Protocol
- **MIGRATION DATABASE CONTAINS REAL LEGACY DATA**
- **Never create fake or placeholder data**
- **Stop immediately if missing required information**
- **All migration data must derive from actual legacy sources**

### Audit Trail Requirements
```python
# Required structure for all migration scripts
from apps.common.management.base_migration import BaseMigrationCommand

class Command(BaseMigrationCommand):
    def get_rejection_categories(self):
        return ["missing_data", "duplicate_constraint", "validation_error"]
    
    def execute_migration(self, *args, **options):
        # Automatic comprehensive audit reporting
        self.record_input_stats(total_records=count)
        self.record_success("records_created", count)
        self.record_rejection("missing_data", record_id, reason)
```

## 📊 Migration Report Structure

### JSON Report Format
```json
{
  "migration_name": "student_migration",
  "timestamp": "2025-01-01T12:00:00Z",
  "input_stats": {
    "total_records": 1000,
    "source_file": "students.csv",
    "file_size": "2.5MB"
  },
  "processing_stats": {
    "records_processed": 1000,
    "records_succeeded": 950,
    "records_failed": 50
  },
  "rejection_categories": {
    "missing_data": 25,
    "duplicate_constraint": 15,
    "validation_error": 10
  },
  "performance_metrics": {
    "total_duration": "120s",
    "records_per_second": 8.33,
    "memory_usage": "256MB"
  }
}
```

## 🔒 Data Integrity Standards

### Validation Requirements
- **Idempotent operations** - Safe to run multiple times
- **Atomic transactions** - All or nothing for batches
- **Pre-processing validation** - Validate before any data changes
- **Missing entity detection** - Comprehensive reporting of missing dependencies
- **Rollback capability** - Ability to undo failed operations

### Legacy Data Constraints
- **Real institutional data** - Never invent or create fake records
- **Historical accuracy** - Maintain data integrity from legacy system
- **Business rule preservation** - Ensure business logic consistency
- **Audit trail completeness** - Full traceability of all changes

## 📚 Related Documentation
- [Architecture](../architecture/) - Clean architecture principles for migration
- [Development](../development/) - Environment setup for migration work
- [Operations](../operations/) - Database maintenance during migration