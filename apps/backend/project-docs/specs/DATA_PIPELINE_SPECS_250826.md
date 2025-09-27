Data Pipeline Implementation Specifications for Claude Code
Project Overview
You are implementing a robust data pipeline system for migrating legacy SIS (Student Information System) data from MSSQL to a new Django/PostgreSQL system. The legacy system has inconsistent data validation, with fields containing various representations of NULL ("NULL", "NA", "", blank spaces) and inconsistent date formats.
The pipeline will process 7 tables through a standardized 4-stage cleaning process, with table-specific customization only where necessary.
Critical Requirements

Conservative Approach: Always reprocess all data from scratch rather than incremental updates, as legacy data can be updated at any point
No IPK-based incremental processing: While "start at IPK 4000" might occasionally help, we need full reprocessing to catch updates to existing records (names, dates, etc.)
Data Preservation: Never lose source data - all original values must be traceable
Configuration-Driven: One pipeline implementation, 7 configuration files

Architecture Overview
Create a Django app called data_pipeline that implements a 4-stage processing pipeline:

Stage 1: Raw import (all fields as TEXT)
Stage 2: Data profiling (analyze patterns, nulls, types)
Stage 3: Cleaning (standardize nulls, formats, etc.)
Stage 4: Validation (Pydantic models with business rules)

Directory Structure to Create
data_pipeline/
├── __init__.py
├── apps.py
├── models.py              # Pipeline metadata models
├── management/
│   ├── __init__.py
│   └── commands/          # Django management commands
│       ├── __init__.py
│       ├── run_pipeline.py
│       ├── validate_configs.py
│       └── profile_raw_data.py
├── core/
│   ├── __init__.py
│   ├── pipeline.py        # Main pipeline class
│   ├── stages.py          # Stage implementations
│   └── registry.py        # Table registry
├── configs/
│   ├── __init__.py
│   ├── base.py           # Base configuration classes
│   ├── students.py       # Table-specific configs (7 files total)
│   ├── academic_classes.py
│   └── ...
├── cleaners/
│   ├── __init__.py
│   ├── engine.py         # Cleaning rules engine
│   └── rules.py          # Specific cleaning rules
├── validators/           # Pydantic models for Stage 4
│   ├── __init__.py
│   ├── students.py
│   ├── academic_classes.py
│   └── ...
├── migrations/           # Django migrations for pipeline tables
├── admin.py              # Admin interface for monitoring
└── tests/
    ├── __init__.py
    ├── test_pipeline.py
    └── test_cleaners.py
Implementation Details
1. Models (data_pipeline/models.py)
pythonfrom django.db import models
from django.contrib.postgres.fields import JSONField

class PipelineRun(models.Model):
    """Track pipeline execution"""
    table_name = models.CharField(max_length=100)
    stage = models.IntegerField()
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ])
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    source_file = models.CharField(max_length=500)
    records_processed = models.IntegerField(default=0)
    records_valid = models.IntegerField(default=0)
    records_invalid = models.IntegerField(default=0)
    error_log = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = 'pipeline_runs'
        ordering = ['-started_at']

class DataProfile(models.Model):
    """Store profiling results from Stage 2"""
    pipeline_run = models.ForeignKey(PipelineRun, on_delete=models.CASCADE)
    table_name = models.CharField(max_length=100)
    column_name = models.CharField(max_length=100)
    null_count = models.IntegerField()
    unique_count = models.IntegerField()
    min_value = models.TextField(null=True)
    max_value = models.TextField(null=True)
    common_values = models.JSONField(default=list)
    detected_type = models.CharField(max_length=50)
    
    class Meta:
        db_table = 'pipeline_data_profiles'

class ValidationError(models.Model):
    """Track validation errors from Stage 4"""
    pipeline_run = models.ForeignKey(PipelineRun, on_delete=models.CASCADE)
    row_number = models.IntegerField()
    column_name = models.CharField(max_length=100)
    error_type = models.CharField(max_length=100)
    error_message = models.TextField()
    raw_value = models.TextField()
    
    class Meta:
        db_table = 'pipeline_validation_errors'
        indexes = [
            models.Index(fields=['pipeline_run', 'error_type']),
        ]
2. Base Configuration (data_pipeline/configs/base.py)
pythonfrom dataclasses import dataclass
from typing import Dict, List, Type, Optional
from pydantic import BaseModel

@dataclass
class ColumnMapping:
    """Maps source column to target with cleaning rules"""
    source_name: str
    target_name: str
    data_type: str  # From MSSQL DDL
    nullable: bool
    cleaning_rules: List[str] = None  # e.g., ['trim', 'uppercase', 'null_standardize']
    business_rules: List[str] = None  # Stage 5 hints

@dataclass
class TableConfig:
    """Complete configuration for one table's pipeline"""
    # Basic info
    table_name: str
    source_file_pattern: str
    
    # Stage 1 config (generic)
    raw_table_name: str  # e.g., "raw_students"
    
    # Stage 2 config (generic)
    profile_table_name: str  # e.g., "profile_students"
    
    # Stage 3 config (semi-custom)
    cleaned_table_name: str  # e.g., "cleaned_students"
    column_mappings: List[ColumnMapping]
    cleaning_rules: Dict[str, any]  # Table-specific rules
    
    # Stage 4 config (custom)
    validated_table_name: str  # e.g., "validated_students"
    validator_class: Type[BaseModel]  # Pydantic model
    
    # Stage 5 hints (for later)
    target_django_model: Optional[str] = None
    business_transformations: Optional[Dict] = None
3. Core Pipeline (data_pipeline/core/pipeline.py)
pythonclass DataPipeline:
    """Generic pipeline that processes any table through stages 1-4"""
    
    def __init__(self, table_config: TableConfig):
        self.config = table_config
        self.logger = self._setup_logging()
    
    def run(self, source_file: Path) -> PipelineResult:
        """Execute all stages for a table"""
        stage1_result = self.stage1_raw_import(source_file)
        stage2_result = self.stage2_profile(stage1_result)
        stage3_result = self.stage3_clean(stage2_result)
        stage4_result = self.stage4_validate(stage3_result)
        return stage4_result
    
    def stage1_raw_import(self, source_file: Path):
        """Generic TEXT import - same for all tables"""
        # This is 100% generic - no customization needed
        
    def stage2_profile(self, raw_table: str):
        """Generic profiling - same for all tables"""
        # Analyzes patterns, nulls, etc. - no customization needed
    
    def stage3_clean(self, profiled_data: ProfileResult):
        """Apply table-specific cleaning rules from config"""
        # Uses config.cleaning_rules
        
    def stage4_validate(self, cleaned_table: str):
        """Apply table-specific validation using config.validator_class"""
        # Uses config.validator_class (Pydantic model)
4. Management Command (data_pipeline/management/commands/run_pipeline.py)
pythonfrom django.core.management.base import BaseCommand
from django.db import connection, transaction
from data_pipeline.core import DataPipeline, TableRegistry
from data_pipeline.models import PipelineRun

class Command(BaseCommand):
    help = 'Run data pipeline for specified tables'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--tables',
            nargs='+',
            default=['all'],
            help='Tables to process (default: all)'
        )
        parser.add_argument(
            '--stage',
            type=int,
            choices=[1, 2, 3, 4],
            help='Run up to specified stage only'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate without importing'
        )
    
    def handle(self, *args, **options):
        tables = options['tables']
        
        if 'all' in tables:
            tables = TableRegistry.list_all()
        
        for table_name in tables:
            self.stdout.write(f"Processing {table_name}...")
            
            # Create pipeline run record
            run = PipelineRun.objects.create(
                table_name=table_name,
                stage=1,
                status='running'
            )
            
            try:
                config = TableRegistry.get_config(table_name)
                pipeline = DataPipeline(config, run_id=run.id)
                
                with transaction.atomic():
                    result = pipeline.run(
                        max_stage=options.get('stage'),
                        dry_run=options['dry_run']
                    )
                
                run.status = 'completed'
                run.records_processed = result.total_records
                run.records_valid = result.valid_records
                run.save()
                
                self.stdout.write(
                    self.style.SUCCESS(f'✓ {table_name} completed')
                )
                
            except Exception as e:
                run.status = 'failed'
                run.error_log = {'error': str(e)}
                run.save()
                
                self.stdout.write(
                    self.style.ERROR(f'✗ {table_name} failed: {e}')
                )
Information You Need to Gather
Before implementing each table's configuration, gather the following from the user:
For Each Table (7 total):

MSSQL DDL - Request: "Please provide the CREATE TABLE statement from MSSQL for the [table_name] table"
CSV File Details - Request: "What is the exact filename pattern for the [table_name] CSV export? (e.g., 'all_students_*.csv')"
NULL Patterns - Request: "What NULL representations appear in [table_name]? Common ones are 'NULL', 'null', 'NA', '', but are there others?"
Date Formats - Request: "What date formats appear in [table_name]? (e.g., 'YYYY-MM-DD', 'MM/DD/YYYY', etc.)"
Stage 4 Validation Rules - Request: "For [table_name], please describe:

Required fields that must not be null
Valid value ranges (e.g., GPA between 0.0-4.0)
Valid enumerations (e.g., status can only be 'active', 'inactive', 'graduated')
Format requirements (e.g., student_id must be 10 digits)
Cross-field validations (e.g., end_date must be after start_date)
Any special business rules"


Special Cleaning Rules - Request: "Are there any special cleaning requirements for [table_name]? For example:

Phone number formatting
Name standardization
Code mappings
Special characters to remove"



Implementation Steps

Create Django App
bashpython manage.py startapp data_pipeline

Add to INSTALLED_APPS
python# config/settings/base.py
INSTALLED_APPS = [
    # ...
    'data_pipeline.apps.DataPipelineConfig',
]

Implement Core Pipeline Components

Start with the generic components (Stage 1-3)
These work the same for all tables


For Each Table (iterate through all 7):

Gather DDL and requirements from user
Create config file in configs/
Create Pydantic validator in validators/
Test with sample data


Create Admin Interface

Register models for monitoring
Create views for validation errors


Testing

Unit tests for each stage
Integration tests for full pipeline
Validation tests for each table



Key Implementation Notes
Stage 1 (Raw Import)

Import EVERYTHING as TEXT
Add metadata columns: _import_id, _import_timestamp, _csv_row_number
Never modify the data at this stage
Use Django's database connection for all operations

Stage 2 (Profiling)

Count nulls, uniques, patterns
Detect probable data types
Find common values
Store results in DataProfile model
This informs Stage 3 cleaning rules

Stage 3 (Cleaning)

Apply standardization rules from config
Convert NULL representations to actual NULL
Trim whitespace
Standardize dates to ISO format
Keep original value reference
Log all transformations

Stage 4 (Validation)

Use Pydantic models provided by user
Capture ALL errors, don't stop on first
Store errors in ValidationError model
Produce both valid and invalid record sets
Generate detailed error report

Sample Validator Template
When the user provides validation requirements, create validators following this pattern:
python# data_pipeline/validators/students.py
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional

class StudentValidator(BaseModel):
    student_id: str = Field(..., min_length=10, max_length=10)
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    birth_date: Optional[datetime] = None
    gpa: Optional[float] = Field(None, ge=0.0, le=4.0)
    status: str = Field(..., pattern='^(active|inactive|graduated)$')
    
    @field_validator('student_id')
    @classmethod
    def validate_student_id(cls, v):
        if not v.isdigit():
            raise ValueError('Student ID must contain only digits')
        return v
    
    @field_validator('birth_date')
    @classmethod
    def validate_birth_date(cls, v):
        if v and v > datetime.now():
            raise ValueError('Birth date cannot be in the future')
        return v
Testing Approach
python# data_pipeline/tests/test_pipeline.py
from django.test import TestCase
from data_pipeline.core import DataPipeline
from data_pipeline.configs.students import STUDENTS_CONFIG

class PipelineTestCase(TestCase):
    def test_stage1_preserves_all_data(self):
        """Ensure no data loss in Stage 1"""
        pass
    
    def test_stage3_standardizes_nulls(self):
        """Ensure all NULL representations are standardized"""
        pass
    
    def test_stage4_catches_validation_errors(self):
        """Ensure Pydantic validation works correctly"""
        pass
Usage Examples
The system should support these commands:
bash# Process all tables
python manage.py run_pipeline --tables all

# Process single table
python manage.py run_pipeline --tables students

# Run up to Stage 3 only
python manage.py run_pipeline --tables students --stage 3

# Dry run (validation only)
python manage.py run_pipeline --tables all --dry-run

# Profile existing raw data
python manage.py profile_raw_data --table raw_students

# Validate configurations
python manage.py validate_configs
Success Criteria

Data Integrity: No data loss from source CSV to raw tables
Traceability: Every record traceable back to source
Error Capture: All validation errors logged and retrievable
Repeatability: Same input produces same output
Performance: Can handle tables with 1M+ records
Monitoring: Admin can see pipeline status and errors
Configurability: New tables can be added without code changes

Begin Implementation
Start by asking the user for:

The DDL for the first table
Sample data showing the NULL patterns and data quality issues
Specific validation rules for Stage 4

Then implement the pipeline incrementally, testing each stage before moving to the next.