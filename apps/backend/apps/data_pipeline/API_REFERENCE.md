# Data Pipeline API Reference

This document provides comprehensive API reference for the data pipeline's key classes and methods.

## Core Classes

### Pipeline Stage Classes

#### `Stage1ImportRawData`
**Location**: `apps/data_pipeline/core/stages.py:15`

The entry point stage that imports raw data from CSV files into staging tables.

```python
class Stage1ImportRawData(BasePipelineStage):
    def execute(self, config: TableConfig, context: PipelineContext) -> StageResult:
        """Import raw data from CSV file into raw data table."""
        # Returns StageResult with processed/rejected counts
```

**Parameters**:
- `config`: TableConfig instance with source file path and column mappings
- `context`: PipelineContext containing run metadata

**Returns**: `StageResult` with processing statistics

---

#### `Stage2ValidateData`
**Location**: `apps/data_pipeline/core/stages.py:45`

Validates imported data against business rules and data quality constraints.

```python
class Stage2ValidateData(BasePipelineStage):
    def execute(self, config: TableConfig, context: PipelineContext) -> StageResult:
        """Validate raw data using configured validators."""
        # Returns validation results with error categorization
```

**Key Features**:
- Configurable validation rules per table
- Error categorization and reporting
- Data quality metrics collection

---

#### `Stage3CleanAndTransform`
**Location**: `apps/data_pipeline/core/stages.py:78`

Applies data transformations and cleaning operations using configured transformers.

```python
class Stage3CleanAndTransform(BasePipelineStage):
    def execute(self, config: TableConfig, context: PipelineContext) -> StageResult:
        """Clean and transform data using transformation rules."""
        # Returns transformation results with fallback handling
```

**Transformation Types**:
- Text encoding (Limon to Unicode)
- Date format standardization
- Education-specific transformations
- Custom field mappings

---

#### `Stage4MapToDomain`
**Location**: `apps/data_pipeline/core/stages.py:112`

Maps cleaned data to canonical domain models using configured field mappings.

```python
class Stage4MapToDomain(BasePipelineStage):
    def execute(self, config: TableConfig, context: PipelineContext) -> StageResult:
        """Map cleaned data to canonical domain models."""
        # Returns mapping results with relationship handling
```

**Domain Models**:
- Students → People, enrollment data
- Courses → Curriculum structures
- Academic classes → Scheduling data
- Financial records → Finance models

---

#### `Stage5CommitToProduction`
**Location**: `apps/data_pipeline/core/stages.py:145`

Safely commits validated and mapped data to production tables.

```python
class Stage5CommitToProduction(BasePipelineStage):
    def execute(self, config: TableConfig, context: PipelineContext) -> StageResult:
        """Commit canonical data to production tables."""
        # Returns commit results with conflict resolution
```

**Safety Features**:
- Transaction-based commits
- Conflict detection and resolution
- Rollback capabilities
- Audit trail generation

## Configuration System

### `TableConfig`
**Location**: `apps/data_pipeline/configs/base.py:15`

Central configuration class for table-specific pipeline settings.

```python
@dataclass
class TableConfig:
    table_name: str
    source_file_pattern: str
    column_mappings: List[ColumnMapping]
    transformation_rules: List[TransformationRule]
    validation_rules: List[ValidationRule]
    domain_mapping: DomainMapping
```

**Attributes**:
- `table_name`: Target table identifier
- `source_file_pattern`: Glob pattern for source CSV files
- `column_mappings`: Source to target column mappings
- `transformation_rules`: Data transformation specifications
- `validation_rules`: Data quality validation rules
- `domain_mapping`: Canonical model mapping configuration

---

### `ColumnMapping`
**Location**: `apps/data_pipeline/configs/base.py:45`

Defines how source columns map to target columns with optional transformations.

```python
@dataclass
class ColumnMapping:
    source_column: str
    target_column: str
    data_type: str
    is_required: bool = False
    default_value: Any = None
    transformation: str = None
```

**Usage Example**:
```python
ColumnMapping(
    source_column="student_name_km",
    target_column="name_khmer", 
    data_type="text",
    is_required=True,
    transformation="khmer_unicode_conversion"
)
```

---

### `TransformationRule`
**Location**: `apps/data_pipeline/configs/base.py:78`

Specifies data transformation operations to apply to specific columns.

```python
@dataclass
class TransformationRule:
    column_pattern: str
    transformer_class: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    conditions: List[str] = field(default_factory=list)
```

**Transformer Classes Available**:
- `KhmerTextTransformer`: Limon to Unicode conversion
- `CambodianEducationTransformer`: Academic term/course mappings
- `DateStandardizationTransformer`: Date format normalization

## Transformation System

### `BaseTransformer`
**Location**: `apps/data_pipeline/core/transformations/base.py:23`

Abstract base class for all data transformers.

```python
class BaseTransformer(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._initialize()
    
    @abstractmethod
    def transform(self, value: Any, context: TransformationContext) -> Any:
        """Transform the input value."""
        pass
    
    @abstractmethod  
    def can_transform(self, value: Any) -> bool:
        """Check if transformer can handle this value."""
        pass
    
    def transform_with_fallback(self, value: Any, context: TransformationContext, fallback_value: Any = None) -> Any:
        """Safe transformation with error handling."""
        # Returns transformed value or fallback on error
```

**Key Methods**:
- `transform()`: Core transformation logic
- `can_transform()`: Value compatibility check
- `transform_with_fallback()`: Safe transformation with error handling
- `_initialize()`: Optional setup method for resources

---

### `TransformationContext`
**Location**: `apps/data_pipeline/core/transformations/base.py:8`

Context object passed to transformers containing transformation metadata.

```python
@dataclass
class TransformationContext:
    source_table: str
    source_column: str
    target_column: str
    row_number: int
    pipeline_run_id: int | None = None
    metadata: dict[str, Any] = None
```

**Usage**: Provides transformers with context about the current transformation operation for logging and debugging.

---

### `CambodianEducationTransformer`
**Location**: `apps/data_pipeline/core/transformations/education.py:8`

Specialized transformer for Cambodian education system data.

```python
class CambodianEducationTransformer(BaseTransformer):
    def transform_course_code(self, old_code: str) -> str:
        """Transform legacy course codes to new curriculum codes."""
        # Maps old course codes like "ENG101" to "ENGL1301"
    
    def transform_term_code(self, term_code: str) -> dict[str, Any]:
        """Parse term codes into structured data."""  
        # Parses "2024S1" into {"year": 2024, "semester": "Spring", "code": "2024SP"}
    
    def transform_student_type(self, type_code: str) -> str:
        """Transform student type codes to descriptions."""
        # Maps "R" to "regular", "T" to "transfer", etc.
```

**Mappings Available**:
- Course code mappings (legacy to new curriculum)
- Academic term parsing (year/semester extraction)
- Student type code expansion

## Pipeline Orchestration

### `DataPipeline`
**Location**: `apps/data_pipeline/core/pipeline.py:25`

Main orchestrator class that coordinates the 5-stage pipeline execution.

```python
class DataPipeline:
    def __init__(self):
        self.stages = [
            Stage1ImportRawData(),
            Stage2ValidateData(), 
            Stage3CleanAndTransform(),
            Stage4MapToDomain(),
            Stage5CommitToProduction()
        ]
    
    def execute(self, config: TableConfig, resume_from_stage: int = 1) -> PipelineResult:
        """Execute the complete pipeline or resume from specific stage."""
        # Returns comprehensive pipeline execution results
    
    def validate_configuration(self, config: TableConfig) -> List[str]:
        """Validate pipeline configuration before execution."""
        # Returns list of configuration errors
```

**Key Features**:
- Sequential stage execution with dependency management
- Resume capability from any stage
- Configuration validation
- Comprehensive error reporting and logging
- Transaction management across stages

---

### `PipelineContext`
**Location**: `apps/data_pipeline/core/pipeline.py:8`

Context object that maintains state throughout pipeline execution.

```python
@dataclass
class PipelineContext:
    run_id: int
    execution_start: datetime
    source_file_path: str
    total_input_records: int
    current_stage: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
```

**Purpose**: Tracks pipeline execution state and provides context to all stages and transformers.

## Data Models

### `PipelineRun`
**Location**: `apps/data_pipeline/models.py:15`

Django model tracking pipeline execution instances.

```python
class PipelineRun(TimestampedModel):
    table_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=PipelineStatus.choices)
    source_file_path = models.TextField()
    total_records_processed = models.IntegerField(default=0)
    records_rejected = models.IntegerField(default=0)
    execution_time_seconds = models.FloatField(null=True)
    error_summary = models.JSONField(default=dict)
```

**Status Values**: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED`

---

### `StageExecution`
**Location**: `apps/data_pipeline/models.py:45`

Tracks individual stage execution within pipeline runs.

```python
class StageExecution(TimestampedModel):
    pipeline_run = models.ForeignKey(PipelineRun, on_delete=models.CASCADE)
    stage_number = models.IntegerField()
    stage_name = models.CharField(max_length=100) 
    status = models.CharField(max_length=20)
    records_processed = models.IntegerField(default=0)
    records_rejected = models.IntegerField(default=0)
    execution_time_seconds = models.FloatField(null=True)
    error_details = models.JSONField(default=dict)
```

**Relationships**: Each `PipelineRun` has multiple `StageExecution` records (one per stage).

## Management Commands

### `run_pipeline`
**Location**: `apps/data_pipeline/management/commands/run_pipeline.py:15`

Primary command-line interface for executing data pipeline operations.

```bash
# Execute full pipeline for students table
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline students --source-file /path/to/students.csv

# Resume from stage 3
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline students --source-file /path/to/students.csv --resume-from 3

# Dry run mode (validation only)
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline students --source-file /path/to/students.csv --dry-run

# Verbose output
docker compose -f docker-compose.local.yml run --rm django python manage.py run_pipeline students --source-file /path/to/students.csv --verbosity 2
```

**Command Arguments**:
- `table_name`: Target table configuration to use
- `--source-file`: Path to source CSV file
- `--resume-from`: Stage number to resume from (1-5)
- `--dry-run`: Validate configuration without executing
- `--verbosity`: Output detail level (0-2)

---

### `validate_configs`
**Location**: `apps/data_pipeline/management/commands/validate_configs.py:20`

Validates all pipeline configurations for consistency and completeness.

```bash
# Validate all configurations
docker compose -f docker-compose.local.yml run --rm django python manage.py validate_configs

# Validate specific table
docker compose -f docker-compose.local.yml run --rm django python manage.py validate_configs --table students

# Include detailed validation reports
docker compose -f docker-compose.local.yml run --rm django python manage.py validate_configs --detailed
```

**Validation Checks**:
- Configuration file syntax and structure
- Column mapping consistency
- Transformer class availability
- Domain model compatibility
- Circular dependency detection

---

### `profile_raw_data`
**Location**: `apps/data_pipeline/management/commands/profile_raw_data.py:25`

Analyzes source data files to generate data profiling reports.

```bash
# Profile all data files  
docker compose -f docker-compose.local.yml run --rm django python manage.py profile_raw_data

# Profile specific file
docker compose -f docker-compose.local.yml run --rm django python manage.py profile_raw_data --file /path/to/students.csv

# Generate detailed statistics
docker compose -f docker-compose.local.yml run --rm django python manage.py profile_raw_data --detailed --output /path/to/report.json
```

**Generated Reports**:
- Column data type distribution
- Null value percentages
- Unique value counts
- Data quality indicators
- Encoding detection results

## Registry System

### `TransformerRegistry`
**Location**: `apps/data_pipeline/core/transformations/registry.py:8`

Central registry for managing transformer classes with singleton pattern.

```python
class TransformerRegistry:
    _instance = None
    _transformers = {}
    
    def register(self, name: str, transformer_class: type):
        """Register a transformer class by name."""
        # Validates transformer class implements required interface
    
    def get_transformer(self, name: str) -> BaseTransformer:
        """Get transformer instance by name."""
        # Returns cached instance or creates new one
    
    def list_transformers(self) -> List[str]:
        """List all registered transformer names."""
        # Returns alphabetically sorted transformer names
```

**Usage Example**:
```python
registry = TransformerRegistry()
registry.register("khmer_text", KhmerTextTransformer)
transformer = registry.get_transformer("khmer_text")
```

**Built-in Transformers**:
- `khmer_text`: Limon to Unicode conversion
- `cambodian_education`: Academic data transformations  
- `date_standardization`: Date format normalization

## Validation System

### Validator Classes

#### `StudentsValidator`
**Location**: `apps/data_pipeline/validators/students.py:15`

Validates student data records against business rules.

```python
class StudentsValidator(BaseValidator):
    def validate_record(self, record: dict) -> ValidationResult:
        """Validate individual student record."""
        # Returns validation result with specific error details
    
    def validate_student_id(self, student_id: str) -> bool:
        """Validate student ID format and uniqueness."""
        
    def validate_enrollment_data(self, record: dict) -> List[str]:
        """Validate enrollment-related fields."""
```

**Validation Rules**:
- Student ID format and uniqueness
- Required field presence
- Academic program validity
- Enrollment date logic
- Contact information format

#### `AcademicClassesValidator`
**Location**: `apps/data_pipeline/validators/academicclasses.py:20`

Validates academic class and scheduling data.

```python  
class AcademicClassesValidator(BaseValidator):
    def validate_class_schedule(self, record: dict) -> ValidationResult:
        """Validate class scheduling data."""
        
    def validate_instructor_assignment(self, record: dict) -> bool:
        """Validate instructor assignment logic."""
        
    def validate_capacity_limits(self, record: dict) -> List[str]:
        """Validate enrollment capacity constraints."""
```

**Validation Rules**:
- Class schedule conflicts
- Instructor availability
- Room capacity constraints
- Academic term validity
- Course prerequisite requirements

## Error Handling

### `ValidationError`
**Location**: `apps/data_pipeline/core/exceptions.py:15`

Custom exception for data validation failures.

```python
class ValidationError(Exception):
    def __init__(self, field: str, value: Any, message: str, error_code: str = None):
        self.field = field
        self.value = value
        self.message = message
        self.error_code = error_code
        super().__init__(f"Validation failed for {field}: {message}")
```

### `TransformationError`
**Location**: `apps/data_pipeline/core/exceptions.py:35`

Exception for transformation operation failures.

```python
class TransformationError(Exception):
    def __init__(self, transformer: str, value: Any, message: str):
        self.transformer = transformer
        self.value = value
        self.message = message
        super().__init__(f"Transformation failed in {transformer}: {message}")
```

## Result Objects

### `StageResult`
**Location**: `apps/data_pipeline/core/results.py:8`

Contains execution results from individual pipeline stages.

```python
@dataclass
class StageResult:
    stage_name: str
    success: bool
    records_processed: int
    records_rejected: int
    execution_time_seconds: float
    error_summary: Dict[str, int]
    warnings: List[str]
    metadata: Dict[str, Any]
```

### `PipelineResult`
**Location**: `apps/data_pipeline/core/results.py:25`

Comprehensive results from complete pipeline execution.

```python
@dataclass
class PipelineResult:
    success: bool
    total_records_processed: int
    total_records_rejected: int
    total_execution_time_seconds: float
    stage_results: List[StageResult]
    overall_error_summary: Dict[str, int]
    pipeline_run_id: int
```

---

This API reference provides the technical foundation for working with the data pipeline system. For usage examples and implementation guides, see the accompanying documentation files.