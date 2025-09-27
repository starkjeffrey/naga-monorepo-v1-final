# Data Pipeline Usage Guide

This guide provides practical examples and step-by-step instructions for using the data pipeline system.

## Quick Start

**🚨 IMPORTANT: This is a Docker-first project. All database operations must use Docker commands.**

### 1. Basic Pipeline Execution

Execute a complete pipeline for student data:

```bash
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline students --source-file data/students_2024.csv
```

This command will:
- Import raw data from the CSV file
- Validate all records against business rules  
- Clean and transform data (Khmer text conversion, date formatting)
- Map to domain models (Student, Person, Enrollment records)
- Commit validated data to production tables

### 2. Pipeline with Resume Capability

If a pipeline fails at stage 3, resume from that point:

```bash
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline students --source-file data/students_2024.csv --resume-from 3
```

### 3. Dry Run for Validation

Test your configuration without processing data:

```bash
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline students --source-file data/students_2024.csv --dry-run
```

## Configuration Setup

### Creating a New Table Configuration

1. Create a configuration file in `apps/data_pipeline/configs/`:

```python
# apps/data_pipeline/configs/my_table.py
from .base import TableConfig, ColumnMapping, TransformationRule, ValidationRule, DomainMapping

def get_my_table_config() -> TableConfig:
    return TableConfig(
        table_name="my_table",
        source_file_pattern="my_table_*.csv",
        column_mappings=[
            ColumnMapping(
                source_column="old_name",
                target_column="new_name", 
                data_type="text",
                is_required=True
            ),
            ColumnMapping(
                source_column="date_col",
                target_column="standardized_date",
                data_type="date",
                transformation="date_standardization"
            )
        ],
        transformation_rules=[
            TransformationRule(
                column_pattern="*_km",  # All columns ending in _km
                transformer_class="khmer_text",
                parameters={"encoding": "limon"}
            )
        ],
        validation_rules=[
            ValidationRule(
                field="student_id", 
                rule_type="format",
                parameters={"pattern": r"^\d{8}$"}
            )
        ],
        domain_mapping=DomainMapping(
            target_model="people.Person",
            field_mappings={
                "new_name": "full_name",
                "standardized_date": "birth_date"
            }
        )
    )
```

2. Register the configuration in `apps/data_pipeline/core/registry.py`:

```python
from apps.data_pipeline.configs.my_table import get_my_table_config

def register_all_configs():
    registry = ConfigRegistry()
    registry.register("my_table", get_my_table_config())
    # ... other registrations
```

### Column Mapping Examples

**Basic mapping with type conversion:**
```python
ColumnMapping(
    source_column="student_id",
    target_column="id", 
    data_type="integer",
    is_required=True
)
```

**Optional field with default value:**
```python
ColumnMapping(
    source_column="phone",
    target_column="contact_phone",
    data_type="text",
    is_required=False,
    default_value="N/A"
)
```

**Field with transformation:**
```python  
ColumnMapping(
    source_column="name_khmer",
    target_column="name_unicode",
    data_type="text", 
    transformation="khmer_unicode_conversion"
)
```

## Data Transformations

### Using Built-in Transformers

#### Khmer Text Conversion

Automatically convert Limon-encoded Khmer text to Unicode:

```python
TransformationRule(
    column_pattern="*_km",  # Apply to all Khmer columns
    transformer_class="khmer_text",
    parameters={
        "source_encoding": "limon",
        "target_encoding": "unicode",
        "fallback_on_error": True
    }
)
```

#### Educational Data Transformation

Transform academic course codes and terms:

```python
TransformationRule(
    column_pattern="course_code",
    transformer_class="cambodian_education", 
    parameters={
        "transformation_type": "course_code",
        "curriculum_version": "2024"
    }
)

TransformationRule(
    column_pattern="academic_term",
    transformer_class="cambodian_education",
    parameters={
        "transformation_type": "term_code" 
    }
)
```

### Creating Custom Transformers

1. Create transformer class:

```python
# apps/data_pipeline/core/transformations/my_transformer.py
from .base import BaseTransformer, TransformationContext
from typing import Any

class MyCustomTransformer(BaseTransformer):
    def _initialize(self):
        """Setup any required resources."""
        self.lookup_table = {
            "A": "Excellent", 
            "B": "Good",
            "C": "Average"
        }
    
    def can_transform(self, value: Any) -> bool:
        """Check if we can transform this value."""
        return isinstance(value, str) and len(value) == 1
    
    def transform(self, value: str, context: TransformationContext) -> str:
        """Transform grade letters to descriptions."""
        return self.lookup_table.get(value.upper(), "Unknown")
```

2. Register the transformer:

```python
# apps/data_pipeline/core/transformations/registry.py  
from .my_transformer import MyCustomTransformer

def register_all_transformers():
    registry = TransformerRegistry()
    registry.register("grade_expansion", MyCustomTransformer)
    # ... other registrations
```

3. Use in configuration:

```python
TransformationRule(
    column_pattern="grade",
    transformer_class="grade_expansion"
)
```

## Data Validation

### Built-in Validation Rules

#### Format Validation

Validate field formats using regular expressions:

```python
ValidationRule(
    field="student_id",
    rule_type="format", 
    parameters={"pattern": r"^\d{8}$"},  # 8 digits
    error_message="Student ID must be exactly 8 digits"
)
```

#### Range Validation

Validate numeric ranges:

```python
ValidationRule(
    field="age",
    rule_type="range",
    parameters={"min_value": 16, "max_value": 65},
    error_message="Age must be between 16 and 65"
)
```

#### Required Field Validation

Ensure critical fields are present:

```python  
ValidationRule(
    field="full_name",
    rule_type="required",
    error_message="Student name is required"
)
```

#### Custom Business Logic Validation

Implement complex validation rules:

```python
ValidationRule(
    field="enrollment_date",
    rule_type="custom",
    validator_class="academic_date_validator",
    parameters={"academic_year": "2024-2025"}
)
```

### Creating Custom Validators

1. Create validator class:

```python
# apps/data_pipeline/validators/my_validator.py
from .base import BaseValidator, ValidationResult
from typing import Dict, Any

class MyTableValidator(BaseValidator):
    def validate_record(self, record: Dict[str, Any]) -> ValidationResult:
        """Validate complete record."""
        errors = []
        warnings = []
        
        # Custom validation logic
        if not self.validate_student_status(record):
            errors.append("Invalid student status combination")
            
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def validate_student_status(self, record: Dict[str, Any]) -> bool:
        """Custom business logic validation."""
        status = record.get('status', '')
        graduation_date = record.get('graduation_date')
        
        # Graduate students must have graduation date
        if status == 'GRADUATED' and not graduation_date:
            return False
            
        return True
```

2. Register the validator:

```python
ValidationRule(
    field="*",  # Apply to entire record
    rule_type="custom", 
    validator_class="my_table_validator"
)
```

## Common Workflows

### Processing Student Enrollment Data

Complete workflow for processing student enrollment data:

```bash
# 1. Validate configuration
docker compose -f docker-compose.local.yml run --rm django python manage.py validate_configs --table students

# 2. Profile source data to understand quality
docker compose -f docker-compose.local.yml run --rm django python manage.py profile_raw_data --file data/students_spring_2024.csv --detailed

# 3. Execute pipeline with verbose output
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline students \
    --source-file data/students_spring_2024.csv \
    --verbosity 2

# 4. Check results in database or admin interface
docker compose -f docker-compose.local.yml run --rm django python manage.py shell -c "
from apps.data_pipeline.models import PipelineRun
latest = PipelineRun.objects.latest('created_at')
print(f'Status: {latest.status}')
print(f'Records processed: {latest.total_records_processed}') 
print(f'Records rejected: {latest.records_rejected}')
"
```

### Processing Academic Course Data

```bash
# Process course catalog updates
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline academiccourses \
    --source-file data/courses_2024_fall.csv

# If transformation fails, resume from cleaning stage
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline academiccourses \
    --source-file data/courses_2024_fall.csv \
    --resume-from 3
```

### Processing Financial Data

```bash  
# Process receipt data with extra validation
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline receipt_headers \
    --source-file data/receipts_december.csv

docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline receipt_items \
    --source-file data/receipt_items_december.csv
```

## Monitoring and Debugging

### Checking Pipeline Status

View recent pipeline executions:

```python
from apps.data_pipeline.models import PipelineRun, StageExecution

# Get recent runs
recent_runs = PipelineRun.objects.order_by('-created_at')[:5]
for run in recent_runs:
    print(f"{run.table_name}: {run.status} ({run.total_records_processed} processed)")

# Get detailed stage information for a specific run
run = PipelineRun.objects.get(id=123)
stages = run.stage_executions.all()
for stage in stages:
    print(f"Stage {stage.stage_number}: {stage.status} - {stage.records_processed} processed")
```

### Analyzing Rejection Reasons

Understanding why records were rejected:

```python
from apps.data_pipeline.models import PipelineRun

run = PipelineRun.objects.latest('created_at')
error_summary = run.error_summary

# Print rejection categories and counts
for category, count in error_summary.items():
    print(f"{category}: {count} records")

# Get detailed stage errors
for stage in run.stage_executions.all():
    if stage.error_details:
        print(f"\nStage {stage.stage_number} errors:")
        for error_type, details in stage.error_details.items():
            print(f"  {error_type}: {details}")
```

### Debugging Transformation Issues

When transformations fail, examine the logs:

```bash
# Run with maximum verbosity
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline students \
    --source-file data/problematic_file.csv \
    --verbosity 2

# Check transformation-specific logs
grep "Transformation failed" logs/pipeline.log | head -10

# Test specific transformer manually
docker compose -f docker-compose.local.yml run --rm django python manage.py shell -c "
from apps.data_pipeline.core.transformations.registry import TransformerRegistry
from apps.data_pipeline.core.transformations.base import TransformationContext

registry = TransformerRegistry()
transformer = registry.get_transformer('khmer_text')

context = TransformationContext(
    source_table='students',
    source_column='name_km', 
    target_column='name_unicode',
    row_number=1
)

# Test problematic value
result = transformer.transform_with_fallback('problematic_text', context, 'FALLBACK')
print(f'Result: {result}')
"
```

## Performance Optimization

### Batch Processing Large Files

For large datasets, process in chunks:

```bash
# Custom management command for batch processing
docker compose -f docker-compose.local.yml run --rm django python manage.py shell -c "
from apps.data_pipeline.core.pipeline import DataPipeline
from apps.data_pipeline.configs.students import get_students_config
import pandas as pd

# Process large file in chunks
pipeline = DataPipeline()
config = get_students_config()

chunk_size = 1000
file_path = 'data/large_student_file.csv'

for chunk_num, chunk_df in enumerate(pd.read_csv(file_path, chunksize=chunk_size)):
    chunk_file = f'temp_chunk_{chunk_num}.csv'
    chunk_df.to_csv(chunk_file, index=False)
    
    try:
        result = pipeline.execute(config, chunk_file)
        print(f'Chunk {chunk_num}: {result.success}')
    except Exception as e:
        print(f'Chunk {chunk_num} failed: {e}')
"
```

### Optimizing Database Operations

For better performance with large datasets:

```python
# Configure database connection pooling
# In settings.py
DATABASES = {
    'default': {
        # ... connection settings ...
        'OPTIONS': {
            'MAX_CONNS': 20,
            'OPTIONS': {
                'MAX_CONN_AGE': 3600,  # 1 hour
            }
        }
    }
}

# Use bulk operations in custom stages
class OptimizedStage4MapToDomain(Stage4MapToDomain):
    def execute(self, config, context):
        # Use bulk_create instead of individual saves
        bulk_objects = []
        for record in cleaned_records:
            bulk_objects.append(DomainModel(**record))
            
            if len(bulk_objects) >= 1000:  # Batch size
                DomainModel.objects.bulk_create(bulk_objects)
                bulk_objects = []
        
        # Create remaining objects
        if bulk_objects:
            DomainModel.objects.bulk_create(bulk_objects)
```

## Error Handling Best Practices

### Graceful Error Recovery

Configure fallback values for common transformation failures:

```python
TransformationRule(
    column_pattern="optional_field",
    transformer_class="my_transformer", 
    parameters={
        "fallback_value": "UNKNOWN",
        "log_failures": True,
        "continue_on_error": True
    }
)
```

### Email Notifications for Pipeline Failures

Set up notifications for production environments:

```python
# In settings.py
PIPELINE_NOTIFICATIONS = {
    'email_on_failure': True,
    'admin_emails': ['admin@school.edu.kh'],
    'notification_levels': ['ERROR', 'CRITICAL']
}

# Custom notification handler
from django.core.mail import send_mail

class NotificationHandler:
    def notify_failure(self, pipeline_run):
        send_mail(
            subject=f'Pipeline Failed: {pipeline_run.table_name}',
            message=f'Pipeline run {pipeline_run.id} failed with {pipeline_run.records_rejected} rejected records.',
            recipient_list=settings.PIPELINE_NOTIFICATIONS['admin_emails']
        )
```

## Testing Pipeline Configurations

### Unit Testing Transformers

```python
# tests/test_transformers.py
import pytest
from apps.data_pipeline.core.transformations.education import CambodianEducationTransformer
from apps.data_pipeline.core.transformations.base import TransformationContext

class TestCambodianEducationTransformer:
    def test_course_code_transformation(self):
        transformer = CambodianEducationTransformer()
        context = TransformationContext(
            source_table='courses',
            source_column='old_code',
            target_column='new_code', 
            row_number=1
        )
        
        result = transformer.transform('ENG101', context)
        assert result == 'ENGL1301'
        
    def test_term_code_parsing(self):
        transformer = CambodianEducationTransformer()
        context = TransformationContext(
            source_table='terms',
            source_column='term_code',
            target_column='parsed_term',
            row_number=1
        )
        
        result = transformer.transform('2024S1', context)
        expected = {
            'year': 2024,
            'semester': 'Spring', 
            'code': '2024SP',
            'original': '2024S1'
        }
        assert result == expected
```

### Integration Testing Complete Pipeline

```python  
# tests/test_integration.py
import pytest
from django.test import TransactionTestCase
from apps.data_pipeline.core.pipeline import DataPipeline
from apps.data_pipeline.configs.students import get_students_config

class TestPipelineIntegration(TransactionTestCase):
    def test_complete_student_pipeline(self):
        # Create test CSV file
        test_data = """student_id,name_en,name_km,birth_date
12345678,John Doe,ចន សុភា,1995-05-15
87654321,Jane Smith,លី មករា,1996-03-22"""
        
        with open('test_students.csv', 'w') as f:
            f.write(test_data)
        
        # Execute pipeline
        pipeline = DataPipeline()
        config = get_students_config()
        result = pipeline.execute(config, 'test_students.csv')
        
        # Verify results
        assert result.success == True
        assert result.total_records_processed == 2
        assert result.total_records_rejected == 0
        
        # Verify data in database
        from apps.people.models import Person
        assert Person.objects.count() == 2
        
        person = Person.objects.get(name_english='John Doe')
        assert person.name_khmer is not None  # Should be transformed
```

## Maintenance and Operations

### Regular Data Quality Checks

Set up periodic data quality monitoring:

```bash
# Monthly data quality report
docker compose -f docker-compose.local.yml run --rm django python manage.py profile_raw_data --all-tables --output monthly_quality_report.json

# Check for configuration drift  
docker compose -f docker-compose.local.yml run --rm django python manage.py validate_configs --detailed

# Archive old pipeline run logs
docker compose -f docker-compose.local.yml run --rm django python manage.py shell -c "
from apps.data_pipeline.models import PipelineRun
from django.utils import timezone
from datetime import timedelta

# Archive runs older than 6 months
cutoff = timezone.now() - timedelta(days=180)
old_runs = PipelineRun.objects.filter(created_at__lt=cutoff)
print(f'Archiving {old_runs.count()} old pipeline runs')
# Implement archival logic
"
```

### Configuration Management

Version control for pipeline configurations:

```bash
# Export current configurations
docker compose -f docker-compose.local.yml run --rm django python manage.py shell -c "
from apps.data_pipeline.core.registry import ConfigRegistry
import json

registry = ConfigRegistry()
configs = {}
for name in registry.list_configs():
    config = registry.get_config(name)
    configs[name] = config.to_dict()  # Implement serialization

with open('pipeline_configs_backup.json', 'w') as f:
    json.dump(configs, f, indent=2)
"
```

This usage guide provides practical examples for implementing and operating the data pipeline system. For detailed API documentation, see API_REFERENCE.md.