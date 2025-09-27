# Data Pipeline System

A robust, 5-stage ETL (Extract, Transform, Load) pipeline designed for processing educational data at a Cambodian university. The system handles complex data transformations including Khmer text encoding conversion, academic data standardization, and multi-step validation workflows.

## Features

- **5-Stage Pipeline Architecture**: Modular pipeline with clear separation of concerns
- **Resume Capability**: Continue processing from any failed stage
- **Khmer Text Support**: Automatic Limon to Unicode conversion for Khmer language data
- **Education-Specific Transformations**: Academic term parsing, course code mapping, student type categorization
- **Comprehensive Validation**: Business rule validation with detailed error reporting
- **Production-Ready**: Transaction safety, rollback capabilities, and audit trails
- **Monitoring & Logging**: Detailed execution tracking and performance metrics

## Quick Start

### Prerequisites

- Docker and Docker Compose
- PostgreSQL database (runs in Docker container)
- Django 5.0+ (runs in Docker container)
- Python 3.13+ (runs in Docker container)

### Basic Usage

**🚨 IMPORTANT: This is a Docker-first project. All database operations must use Docker commands.**

1. **Run a complete pipeline for student data:**
   ```bash
   docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline students --source-file data/students_2024.csv
   ```

2. **Resume from a specific stage:**
   ```bash
   docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline students --source-file data/students_2024.csv --resume-from 3
   ```

3. **Validate configuration without processing:**
   ```bash
   docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline students --source-file data/students_2024.csv --dry-run
   ```

### Example Output
```
Pipeline Execution Report
========================
Table: students
Source File: data/students_2024.csv
Total Records: 1,247
Processing Time: 45.3 seconds

Stage Results:
✓ Stage 1 - Import Raw Data: 1,247 records imported
✓ Stage 2 - Validate Data: 1,231 records validated (16 rejected)
✓ Stage 3 - Clean & Transform: 1,231 records transformed
✓ Stage 4 - Map to Domain: 1,231 records mapped
✓ Stage 5 - Commit to Production: 1,231 records committed

Rejection Summary:
- missing_required_field: 12 records
- invalid_date_format: 3 records  
- duplicate_student_id: 1 record
```

## Architecture Overview

### 5-Stage Pipeline Process

```
CSV File → Stage 1 → Stage 2 → Stage 3 → Stage 4 → Stage 5 → Production DB
          Import   Validate  Transform   Map      Commit
```

1. **Stage 1 - Import Raw Data**: Read CSV files into staging tables
2. **Stage 2 - Validate Data**: Apply business rules and data quality checks
3. **Stage 3 - Clean & Transform**: Apply transformations (encoding, formatting, etc.)
4. **Stage 4 - Map to Domain**: Convert to canonical domain models
5. **Stage 5 - Commit to Production**: Safely persist to production tables

### Core Components

- **Pipeline Orchestrator** (`core/pipeline.py`): Coordinates stage execution
- **Stage Classes** (`core/stages.py`): Implement individual pipeline stages  
- **Transformers** (`core/transformations/`): Handle data transformations
- **Validators** (`validators/`): Implement validation rules
- **Configuration System** (`configs/`): Table-specific pipeline settings
- **Management Commands** (`management/commands/`): CLI interfaces

## Supported Data Types

### Academic Data
- **Students**: Personal information, enrollment data, academic status
- **Academic Classes**: Course schedules, instructor assignments, enrollment capacity
- **Academic Course Takers**: Student course enrollment records
- **Terms**: Academic term definitions and scheduling
- **Receipt Headers/Items**: Financial transaction records

### Transformation Capabilities

#### Khmer Text Processing
```python
# Automatic Limon to Unicode conversion
"ចន សុភា" ← "jan suPhea" (Limon encoding)
```

#### Academic Data Standardization
```python  
# Course code mapping
"ENG101" → "ENGL1301"

# Term code parsing  
"2024S1" → {"year": 2024, "semester": "Spring", "code": "2024SP"}

# Student type expansion
"R" → "regular", "T" → "transfer", "I" → "international"
```

#### Date Standardization
```python
# Multiple date format support
"05/15/1995", "1995-05-15", "15-05-95" → "1995-05-15"
```

## Configuration System

### Table Configuration Structure

Each data source requires a configuration defining how to process the data:

```python
# Example: apps/data_pipeline/configs/students.py
def get_students_config() -> TableConfig:
    return TableConfig(
        table_name="students",
        source_file_pattern="students_*.csv",
        column_mappings=[
            ColumnMapping(
                source_column="name_km", 
                target_column="name_khmer",
                data_type="text",
                transformation="khmer_unicode_conversion"
            )
        ],
        transformation_rules=[
            TransformationRule(
                column_pattern="*_km",
                transformer_class="khmer_text"
            )
        ],
        validation_rules=[
            ValidationRule(
                field="student_id",
                rule_type="format", 
                parameters={"pattern": r"^\d{8}$"}
            )
        ]
    )
```

### Available Configurations

- `students.py` - Student personal and enrollment data
- `academicclasses.py` - Course scheduling and class management
- `academiccoursetakers.py` - Student course enrollment records  
- `terms.py` - Academic term definitions
- `receipt_headers.py` - Financial receipt header data
- `receipt_items.py` - Financial receipt line item data

## Management Commands

### Primary Commands

#### `run_pipeline`
Execute the complete data pipeline for a specific table.

```bash
# Basic execution
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline <table_name> --source-file <csv_file>

# Resume from specific stage
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline students --source-file data.csv --resume-from 3

# Dry run (validation only)
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline students --source-file data.csv --dry-run

# Verbose output
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline students --source-file data.csv --verbosity 2
```

#### `validate_configs`
Validate pipeline configurations for consistency and completeness.

```bash
# Validate all configurations
docker compose -f docker-compose.local.yml run --rm django python manage.py validate_configs

# Validate specific table
docker compose -f docker-compose.local.yml run --rm django python manage.py validate_configs --table students

# Detailed validation report
docker compose -f docker-compose.local.yml run --rm django python manage.py validate_configs --detailed
```

#### `profile_raw_data`
Generate data profiling reports for source files.

```bash
# Profile specific file
docker compose -f docker-compose.local.yml run --rm django python manage.py profile_raw_data --file data/students.csv

# Profile all configured data sources
docker compose -f docker-compose.local.yml run --rm django python manage.py profile_raw_data --all-tables

# Generate detailed statistics
docker compose -f docker-compose.local.yml run --rm django python manage.py profile_raw_data --file data.csv --detailed --output report.json
```

## Data Transformations

### Built-in Transformers

#### Khmer Text Transformer
Converts Limon-encoded Khmer text to Unicode standard.

```python
# Configuration
TransformationRule(
    column_pattern="*_km",  # All columns ending in _km
    transformer_class="khmer_text",
    parameters={
        "source_encoding": "limon",
        "target_encoding": "unicode"
    }
)
```

#### Cambodian Education Transformer  
Handles education-specific data transformations.

```python
# Course code transformation
TransformationRule(
    column_pattern="course_code", 
    transformer_class="cambodian_education",
    parameters={"transformation_type": "course_code"}
)

# Academic term parsing
TransformationRule(
    column_pattern="term_code",
    transformer_class="cambodian_education", 
    parameters={"transformation_type": "term_code"}
)
```

### Creating Custom Transformers

1. **Create transformer class:**
```python
# apps/data_pipeline/core/transformations/my_transformer.py
from .base import BaseTransformer, TransformationContext

class MyCustomTransformer(BaseTransformer):
    def can_transform(self, value) -> bool:
        return isinstance(value, str)
        
    def transform(self, value: str, context: TransformationContext):
        # Your transformation logic here
        return value.upper()
```

2. **Register the transformer:**
```python
# In registry.py
registry.register("my_transformer", MyCustomTransformer)
```

3. **Use in configuration:**
```python
TransformationRule(
    column_pattern="my_column",
    transformer_class="my_transformer"
)
```

## Validation System

### Built-in Validation Rules

#### Format Validation
```python
ValidationRule(
    field="student_id",
    rule_type="format",
    parameters={"pattern": r"^\d{8}$"},
    error_message="Student ID must be 8 digits"
)
```

#### Range Validation
```python
ValidationRule(
    field="age", 
    rule_type="range",
    parameters={"min_value": 16, "max_value": 65}
)
```

#### Required Field Validation
```python
ValidationRule(
    field="full_name",
    rule_type="required"
)
```

### Custom Validators

Create table-specific validation logic:

```python
# apps/data_pipeline/validators/my_table.py
from .base import BaseValidator, ValidationResult

class MyTableValidator(BaseValidator):
    def validate_record(self, record: dict) -> ValidationResult:
        errors = []
        
        # Custom business logic validation
        if not self.validate_business_rule(record):
            errors.append("Business rule violation")
            
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
```

## Monitoring and Debugging

### Pipeline Execution Tracking

The system automatically tracks all pipeline executions:

```python
from apps.data_pipeline.models import PipelineRun, StageExecution

# Get recent pipeline runs
recent_runs = PipelineRun.objects.order_by('-created_at')[:10]
for run in recent_runs:
    print(f"{run.table_name}: {run.status} - {run.total_records_processed} processed")

# Get detailed stage information
run = PipelineRun.objects.get(id=123)
for stage in run.stage_executions.all():
    print(f"Stage {stage.stage_number}: {stage.status} - {stage.execution_time_seconds}s")
```

### Error Analysis

Analyze rejection reasons and patterns:

```python
# Examine rejection categories
run = PipelineRun.objects.latest('created_at') 
error_summary = run.error_summary

for category, count in error_summary.items():
    print(f"{category}: {count} records rejected")

# Get detailed error information by stage
for stage in run.stage_executions.all():
    if stage.error_details:
        print(f"Stage {stage.stage_number} errors:")
        for error_type, details in stage.error_details.items():
            print(f"  {error_type}: {details}")
```

### Performance Monitoring

Track pipeline performance metrics:

```python
# Average execution time by table
from django.db.models import Avg
from apps.data_pipeline.models import PipelineRun

performance_stats = PipelineRun.objects.values('table_name').annotate(
    avg_time=Avg('execution_time_seconds'),
    avg_processed=Avg('total_records_processed'),
    avg_rejected=Avg('records_rejected')
)

for stat in performance_stats:
    print(f"{stat['table_name']}: {stat['avg_time']:.1f}s avg, "
          f"{stat['avg_processed']:.0f} records avg")
```

## Testing

### Running Tests

```bash
# Run all data pipeline tests
pytest apps/data_pipeline/tests/

# Run specific test categories  
pytest apps/data_pipeline/tests/ -m "unit"
pytest apps/data_pipeline/tests/ -m "integration" 

# Test with coverage
pytest apps/data_pipeline/tests/ --cov=apps.data_pipeline
```

### Test Structure

- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - End-to-end pipeline tests
- `tests/fixtures/` - Test data files
- `conftest.py` - Shared test fixtures

### Example Test

```python
# tests/integration/test_student_pipeline.py
import pytest
from apps.data_pipeline.core.pipeline import DataPipeline
from apps.data_pipeline.configs.students import get_students_config

class TestStudentPipeline:
    def test_complete_pipeline_execution(self):
        # Create test data file
        test_csv = "student_id,name_en,name_km\n12345678,John Doe,ចន សុភា"
        
        # Execute pipeline
        pipeline = DataPipeline()
        config = get_students_config() 
        result = pipeline.execute(config, test_csv)
        
        # Verify results
        assert result.success == True
        assert result.total_records_processed == 1
        
        # Verify data was created in database
        from apps.people.models import Person
        person = Person.objects.get(name_english='John Doe')
        assert person.name_khmer == 'ចន សុភា'
```

## Security Considerations

### Data Protection
- All transformations preserve data integrity
- Failed records are logged but not permanently stored in raw form
- Personal data is handled according to privacy policies
- Database transactions ensure consistency

### Access Control
- Pipeline execution requires appropriate Django permissions
- Source files should be stored in secure, access-controlled locations
- Database connections use principle of least privilege
- Audit trails track all pipeline executions

## Performance Optimization

### Large Dataset Processing

For processing large datasets (>10,000 records):

```bash
# Use chunked processing for large files
docker compose -f docker-compose.local.yml run --rm django python manage.py shell -c "
import pandas as pd
from apps.data_pipeline.core.pipeline import DataPipeline

# Process in 1000-record chunks
for chunk_df in pd.read_csv('large_file.csv', chunksize=1000):
    chunk_file = f'temp_chunk.csv'
    chunk_df.to_csv(chunk_file, index=False)
    # Process chunk with pipeline
"
```

### Database Optimization

- Configure appropriate database connection pooling
- Use bulk database operations where possible
- Consider indexing on frequently queried columns
- Monitor query performance during pipeline execution

### Memory Management

- Pipeline stages process data in streams where possible
- Large transformations use chunked processing
- Temporary data is cleaned up automatically
- Memory usage is monitored and logged

## Troubleshooting

### Common Issues and Solutions

#### Pipeline Fails at Stage 2 (Validation)
```bash
# Check validation errors in detail
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline students --source-file data.csv --verbosity 2

# Review specific validation failures
docker compose -f docker-compose.local.yml run --rm django python manage.py shell -c "
from apps.data_pipeline.models import PipelineRun
run = PipelineRun.objects.latest('created_at')
stage2 = run.stage_executions.get(stage_number=2)
print(stage2.error_details)
"
```

#### Khmer Text Not Converting Properly
```bash
# Test Khmer transformer directly
docker compose -f docker-compose.local.yml run --rm django python manage.py shell -c "
from apps.data_pipeline.core.transformations.registry import TransformerRegistry
transformer = TransformerRegistry().get_transformer('khmer_text')
result = transformer.transform('problematic_text', context)
print(f'Result: {result}')
"
```

#### Database Connection Issues
```bash
# Check database connectivity
docker compose -f docker-compose.local.yml run --rm django python manage.py shell -c "
from django.db import connection
cursor = connection.cursor()
cursor.execute('SELECT 1')
print('Database connection: OK')
"
```

#### Large File Processing Timeouts
```bash
# Process with resume capability
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline students --source-file large_file.csv
# If it fails at stage 3, resume from there:
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline students --source-file large_file.csv --resume-from 3
```

### Getting Help

1. **Check the logs**: Pipeline execution is logged in detail
2. **Use dry-run mode**: Test configurations without processing data
3. **Profile your data**: Use `profile_raw_data` to understand data quality issues
4. **Test transformations**: Test individual transformers with sample data
5. **Review configurations**: Use `validate_configs` to check for configuration errors

## File Structure

```
apps/data_pipeline/
├── README.md                          # This file
├── USAGE_GUIDE.md                     # Detailed usage examples  
├── API_REFERENCE.md                   # Complete API documentation
├── __init__.py
├── admin.py                           # Django admin configuration
├── apps.py                            # Django app configuration
├── models.py                          # Pipeline tracking models
├── configs/                           # Table configurations
│   ├── __init__.py
│   ├── base.py                        # Base configuration classes
│   ├── students.py                    # Student data configuration
│   ├── academicclasses.py             # Academic class configuration
│   ├── academiccoursetakers.py        # Course enrollment configuration
│   ├── terms.py                       # Academic terms configuration
│   ├── receipt_headers.py             # Receipt header configuration
│   └── receipt_items.py               # Receipt items configuration
├── core/                              # Core pipeline components
│   ├── __init__.py
│   ├── pipeline.py                    # Main pipeline orchestrator
│   ├── stages.py                      # Pipeline stage implementations
│   ├── registry.py                    # Component registry
│   └── transformations/               # Data transformation system
│       ├── __init__.py
│       ├── base.py                    # Base transformer classes
│       ├── registry.py                # Transformer registry
│       ├── education.py               # Education-specific transformers
│       └── text_encodings.py          # Text encoding transformers
├── validators/                        # Data validation system
│   ├── __init__.py
│   ├── students.py                    # Student data validators
│   ├── academicclasses.py             # Academic class validators
│   ├── academiccoursetakers.py        # Course enrollment validators
│   ├── terms.py                       # Terms validators
│   ├── receipt_headers.py             # Receipt header validators
│   └── receipt_items.py               # Receipt items validators
├── cleaners/                          # Legacy data cleaning (deprecated)
│   └── engine.py
├── management/commands/               # Django management commands
│   ├── __init__.py
│   ├── run_pipeline.py                # Main pipeline execution command
│   ├── validate_configs.py            # Configuration validation command
│   └── profile_raw_data.py            # Data profiling command
└── tests/                             # Test suite
    ├── __init__.py
    ├── conftest.py                    # Pytest configuration and fixtures
    ├── test_commands.py               # Management command tests
    ├── test_configurations.py         # Configuration tests
    ├── test_models.py                 # Model tests
    └── test_pipeline.py               # Pipeline integration tests
```

## Contributing

### Development Setup

1. **Install dependencies:**
   ```bash
   pip install -e .
   pip install -r requirements-dev.txt
   ```

2. **Run tests:**
   ```bash
   pytest apps/data_pipeline/tests/
   ```

3. **Code style:**
   ```bash
   ruff check apps/data_pipeline/
   ruff format apps/data_pipeline/
   ```

### Adding New Data Sources

1. Create configuration in `configs/new_table.py`
2. Add any required custom transformers in `core/transformations/`
3. Add validation logic in `validators/new_table.py`
4. Register configuration in `core/registry.py`
5. Add tests in `tests/`
6. Update documentation

### Code Standards

- Follow PEP 8 style guidelines
- Use type hints for all function signatures
- Write comprehensive docstrings
- Add unit tests for all new functionality
- Use logging instead of print statements
- Handle errors gracefully with appropriate fallbacks

---

**Version**: 1.0.0  
**Last Updated**: January 2025  
**Maintainer**: NAGA Development Team

For detailed API documentation, see [API_REFERENCE.md](API_REFERENCE.md).  
For usage examples and workflows, see [USAGE_GUIDE.md](USAGE_GUIDE.md).