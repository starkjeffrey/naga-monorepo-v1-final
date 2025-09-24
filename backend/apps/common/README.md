# Common App

## Overview

The `common` app provides shared utilities, base models, audit logging, and infrastructure components used across the entire Naga SIS backend. This is a foundation layer app that other applications depend on for core functionality.

## Features

### Base Models & Mixins

- **AuditModel**: Base model with creation/modification tracking
- **OverlapCheckMixin**: Date range overlap validation
- **SoftDeleteMixin**: Logical deletion support
- **ActiveModel**: Active/inactive status management

### CRUD Framework

- **Flexible CRUD operations** with configurable field handling
- **Export functionality** (CSV, Excel) with streaming support
- **Bulk operations** with progress tracking
- **Advanced filtering** and search capabilities

### Utilities

- **Phone number normalization** with international support
- **Student ID formatting** following institutional standards
- **Dictionary utilities** for data transformation
- **Limon to Unicode conversion** for legacy data

### Audit & Logging

- **SystemAuditLog**: Management override tracking
- **StudentActivityLog**: Comprehensive student action logging
- **Change history** with detailed context preservation

### Management Commands

- **BaseMigrationCommand**: Standardized data migration framework
- **Comprehensive reporting** with structured JSON output
- **Error categorization** and rejection tracking
- **Idempotent operations** with rollback support

## Models

### Core Infrastructure

#### Room

Classroom and facility management.

```python
# Physical and virtual learning spaces
room = Room.objects.create(
    name="Room 101",
    room_type=RoomType.CLASSROOM,
    capacity=30,
    is_active=True
)
```

#### Holiday

Institutional holiday calendar.

```python
# Academic calendar management
holiday = Holiday.objects.create(
    name="Independence Day",
    date=date(2024, 11, 9),
    is_academic_closure=True
)
```

### Audit Models

#### SystemAuditLog

Management override and system action tracking.

```python
# Log administrative overrides
SystemAuditLog.log_override(
    user=admin_user,
    action="GRADE_OVERRIDE",
    details={"student": "12345", "original": "B", "new": "A"},
    reason="Calculation error correction"
)
```

#### StudentActivityLog

Comprehensive student action tracking.

```python
# Track student academic activities
activity = StudentActivityLog.objects.create(
    student=student_profile,
    activity_type=ActivityType.ENROLLMENT,
    description="Enrolled in GESL-01",
    term=current_term,
    class_header=class_header
)
```

## Services

### Phone Number Service

Normalizes phone numbers to international format with configurable country codes.

```python
from apps.common.utils import normalize_phone_number

# Normalize various phone formats
normalized = normalize_phone_number("012 345 678")  # Returns "+855012345678"
normalized = normalize_phone_number("+1-555-123-4567")  # Returns "+15551234567"
```

### Student ID Service

Formats student IDs according to institutional standards.

```python
from apps.common.utils.student_id_formatter import format_student_id

# Format student ID with proper padding
formatted_id = format_student_id(12345)  # Returns "SIS-12345"
```

## CRUD Framework

### Configuration

The CRUD framework provides a flexible system for managing data with minimal code:

```python
from apps.common.crud.config import CrudConfig
from apps.common.crud.views import CrudView

class StudentCrudView(CrudView):
    model = Student
    config = CrudConfig(
        fields=['first_name', 'last_name', 'email', 'phone'],
        searchable_fields=['first_name', 'last_name', 'email'],
        export_formats=['csv', 'xlsx'],
        bulk_operations=['activate', 'deactivate']
    )
```

### Features

- **Configurable field display** with custom formatting
- **Advanced search** with multi-field filtering
- **Export operations** with progress tracking
- **Bulk actions** with transaction safety
- **Permission integration** with role-based access

## Template Tags

### Common Tags

```django
{% load common_tags %}

<!-- Format objects with dynamic URLs -->
<a href="{% format_with_obj '/student/{student_id}/detail' student %}">
    View Student
</a>

<!-- Display formatted phone numbers -->
{{ student.phone|format_phone }}

<!-- Show relative dates -->
{{ enrollment.created_at|relative_date }}
```

### CRUD Tags

```django
{% load crud_tags %}

<!-- Render CRUD table -->
{% crud_table config=config queryset=students %}

<!-- Display export buttons -->
{% crud_export_buttons formats="csv,xlsx" %}

<!-- Bulk action dropdown -->
{% crud_bulk_actions actions=bulk_actions %}
```

## Management Commands

### Data Migration Framework

All data migration commands must inherit from `BaseMigrationCommand`:

```python
from apps.common.management.base_migration import BaseMigrationCommand

class Command(BaseMigrationCommand):
    help = "Import legacy student data"

    def handle_migration(self, *args, **options):
        # Migration logic here
        self.process_records(records)

    def validate_record(self, record):
        # Custom validation logic
        return True, None

    def transform_record(self, record):
        # Data transformation
        return transformed_record
```

### Setup Commands

```bash
# Setup test data for development
python manage.py setup_test_data

# Generate OpenAPI schema
python manage.py generate_openapi_schema

# Setup migration database
python manage.py setup_migration_database
```

## Fixtures

### Foundation Data

Load essential system data:

```bash
# Load rooms and basic geography
python manage.py loaddata apps/common/fixtures/01_foundation/

# Load holiday calendar
python manage.py loaddata apps/common/fixtures/01_foundation/cambodian_holidays.json
```

## Policies Framework

### Base Policies

```python
from apps.common.policies.base import BasePolicy

class StudentPolicy(BasePolicy):
    def can_enroll(self, user, student, course):
        # Policy logic
        return self.check_prerequisites(student, course)
```

### Policy Decorators

```python
from apps.common.policies.decorators import policy_required

@policy_required('student.can_enroll')
def enroll_student(request, student_id, course_id):
    # Enrollment logic
    pass
```

## Security Features

### Input Validation

- **Phone number validation** with format checking
- **Student ID validation** with checksum verification
- **Date range validation** with overlap prevention
- **File upload validation** with type and size limits

### Audit Trail

- **Complete action logging** with user context
- **Management override tracking** with justification
- **Data change history** with before/after values
- **Security event logging** with IP and session tracking

## Configuration

### Settings

```python
# Django settings
NAGA_PHONE_COUNTRY_CODE = "+855"  # Default country code
NAGA_STUDENT_ID_PREFIX = "SIS"    # Student ID prefix
NAGA_AUDIT_RETENTION_DAYS = 2555  # 7 years

# CRUD Framework
NAGA_CRUD_PAGE_SIZE = 25          # Default pagination
NAGA_CRUD_MAX_EXPORT = 10000      # Export size limit
```

### Environment Variables

```bash
# Phone normalization
PHONE_COUNTRY_CODE="+855"

# Student ID formatting
STUDENT_ID_PREFIX="SIS"
STUDENT_ID_PADDING=5

# Audit retention
AUDIT_RETENTION_DAYS=2555
```

## Testing

### Running Tests

```bash
# Run all common app tests
pytest apps/common/

# Run specific test categories
pytest apps/common/tests/test_models.py
pytest apps/common/tests/test_utils.py
pytest apps/common/tests/test_crud.py
```

### Test Coverage

- **Model validation**: All base model functionality
- **Utility functions**: Phone, ID formatting, date handling
- **CRUD operations**: Create, read, update, delete, export
- **Audit logging**: System and student activity tracking
- **Management commands**: Migration framework validation

## Dependencies

### Internal Dependencies

- Built-in Django models only
- No dependencies on other Naga SIS apps

### External Dependencies

- `phonenumbers`: International phone number validation
- `openpyxl`: Excel export functionality
- `django-extensions`: Enhanced management commands

## API Integration

### Internal APIs

The common app provides no external APIs but supports other apps with:

- Base model classes for consistent behavior
- Utility functions for data processing
- CRUD framework for rapid development

### Usage Examples

```python
# Using base models
from apps.common.models import AuditModel

class Student(AuditModel):
    name = models.CharField(max_length=100)
    # Automatically gets created_at, updated_at, created_by, updated_by

# Using utilities
from apps.common.utils import normalize_phone_number
from apps.common.utils.student_id_formatter import format_student_id

normalized_phone = normalize_phone_number(raw_phone)
formatted_id = format_student_id(student_id)
```

## Maintenance

### Regular Tasks

- **Audit log cleanup**: Remove logs older than retention period
- **Export file cleanup**: Clean temporary export files
- **Performance monitoring**: Monitor CRUD query performance

### Monitoring

- **Database query performance** for base models
- **Export operation success rates**
- **Audit log growth patterns**
- **CRUD framework usage statistics**

## Architecture Notes

### Design Principles

- **Foundation layer positioning**: Provides base functionality only
- **Zero business logic**: Contains no domain-specific rules
- **High reusability**: All components designed for multiple apps
- **Clean dependencies**: No imports from domain or business layers

### Future Considerations

- **Microservice extraction**: CRUD framework could become standalone
- **Audit service separation**: Consider dedicated audit microservice
- **Caching integration**: Add Redis caching for frequently used utilities
- **Event sourcing**: Consider event-driven audit logging
