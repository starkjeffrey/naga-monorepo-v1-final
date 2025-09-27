# Common App - Comprehensive Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Components](#core-components)
4. [Base Models](#base-models)
5. [CRUD Framework](#crud-framework)
6. [Utilities](#utilities)
7. [Management Commands](#management-commands)
8. [Template Tags](#template-tags)
9. [API Reference](#api-reference)
10. [Usage Examples](#usage-examples)
11. [Testing](#testing)
12. [Contributing](#contributing)

## Overview

The `apps/common` module is the foundational layer of the Naga SIS Django backend, providing shared utilities, base models, audit logging, and infrastructure components used across all other applications. It follows clean architecture principles to avoid circular dependencies while maximizing code reuse.

### Key Features

- **🏗️ Base Models**: Comprehensive audit models with timestamps, user tracking, and soft delete
- **📊 CRUD Framework**: Feature-rich CRUD operations with search, export, and bulk actions
- **🔍 Audit Logging**: System-wide audit trails for compliance and tracking
- **🛠️ Utilities**: Phone normalization, ID formatting, and data transformation
- **📝 Management Commands**: Standardized migration framework with reporting
- **🏷️ Template Tags**: Common UI components and formatting helpers

### Architecture Position

```
┌─────────────────────┐
│   Business Layer    │ (scholarships, finance, grading)
│   (Domain Apps)     │
├─────────────────────┤
│   Core Layer        │ (people, curriculum, enrollment)
│   (Domain Apps)     │
├─────────────────────┤
│   Foundation Layer  │ ← apps/common (This module)
│   (Infrastructure)  │
└─────────────────────┘
```

## Architecture

### Design Principles

1. **Foundation Layer Positioning**: Provides base functionality only, no business logic
2. **Zero Dependencies**: No imports from domain or business layer apps
3. **Clean Architecture**: All components designed to prevent circular dependencies
4. **High Reusability**: Components usable across multiple apps without modification
5. **Separation of Concerns**: Clear boundaries between different types of functionality

### Directory Structure

```
apps/common/
├── crud/                    # CRUD Framework
│   ├── config.py           # Configuration classes
│   ├── mixins.py           # View mixins
│   ├── utils.py            # CRUD utilities
│   └── views.py            # Base CRUD views
├── management/              # Management Commands
│   ├── base_migration.py   # Migration command base
│   └── commands/           # Specific commands
├── migrations/              # Database migrations
├── policies/               # Policy framework
├── static/                 # Static files
├── templates/              # Template files
├── templatetags/           # Template tag libraries
├── utils/                  # Utility modules
├── admin.py               # Admin configurations
├── models.py              # Base models
├── utils.py               # Core utilities
└── views.py               # Common views
```

## Core Components

### Base Models Hierarchy

The common app provides four main base model classes:

1. **Component Models**: Single-responsibility mixins
   - `TimestampedModel`: Created/updated timestamps
   - `SoftDeleteModel`: Logical deletion
   - `UserTrackingModel`: User audit trails
   - `StatusModel`: Status management with change tracking

2. **Composite Models**: Combinations for specific use cases
   - `AuditModel`: Timestamps + Soft Delete (legacy)
   - `UserAuditModel`: Timestamps + User Tracking + Soft Delete (existing models)
   - `ComprehensiveAuditModel`: UUID + All audit features (new models)

3. **Specialized Models**: Domain-specific functionality
   - `SystemAuditLog`: Management override tracking
   - `StudentActivityLog`: Student action audit trail
   - `Room`: Physical classroom management
   - `Holiday`: Academic calendar

### CRUD Framework

A complete CRUD framework providing:

- **List Views**: Sorting, searching, filtering, pagination
- **Export Functionality**: CSV and XLSX export with streaming
- **Column Management**: Show/hide columns with user preferences
- **Bulk Actions**: Multi-select operations with confirmation
- **Permission Integration**: Automatic Django permission checking
- **HTMX Integration**: Smooth, no-refresh interactions

## Base Models

### TimestampedModel

Provides automatic timestamp tracking for creation and modification.

```python
class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True
```

**Usage:**
```python
class MyModel(TimestampedModel):
    name = models.CharField(max_length=100)
    # Automatically gets created_at and updated_at
```

### SoftDeleteModel

Implements logical deletion instead of physical deletion.

```python
class SoftDeleteModel(models.Model):
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    objects = SoftDeleteManager()      # Excludes deleted
    all_objects = models.Manager()     # Includes all
    
    class Meta:
        abstract = True
        
    def soft_delete(self):
        """Mark record as deleted"""
        
    def restore(self):
        """Restore deleted record"""
```

**Usage:**
```python
class MyModel(SoftDeleteModel):
    name = models.CharField(max_length=100)

# Usage
instance = MyModel.objects.create(name="Test")
instance.soft_delete()  # Marks as deleted
MyModel.objects.all()   # Excludes deleted records
MyModel.all_objects.all()  # Includes deleted records
instance.restore()      # Restores the record
```

### UserTrackingModel

Tracks which user created and last modified each record.

```python
class UserTrackingModel(models.Model):
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    class Meta:
        abstract = True
```

**Usage:**
```python
class MyModel(UserTrackingModel):
    name = models.CharField(max_length=100)

# In views/admin, set user fields:
instance.created_by = request.user
instance.updated_by = request.user
```

### StatusModel

Provides status tracking with change timestamps.

```python
class StatusModel(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("draft", "Draft"),
        ("archived", "Archived"),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    status_changed_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        abstract = True
```

**Usage:**
```python
class MyModel(StatusModel):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]
    name = models.CharField(max_length=100)

# Status changes are automatically tracked
instance.status = "approved"
instance.save()  # status_changed_at is automatically updated
```

### Composite Models

#### AuditModel (Legacy)

Combines timestamps and soft delete for basic audit needs.

```python
class AuditModel(TimestampedModel, SoftDeleteModel):
    """Basic audit trail without user tracking"""
    class Meta:
        abstract = True
```

#### UserAuditModel (Existing Models)

For existing models that need comprehensive audit capabilities added.

```python
class UserAuditModel(TimestampedModel, UserTrackingModel, SoftDeleteModel):
    """Full audit trail preserving existing primary keys"""
    class Meta:
        abstract = True
```

**Migration Example:**
```python
# Before
class Invoice(models.Model):
    amount = models.DecimalField(max_digits=10, decimal_places=2)

# After
class Invoice(UserAuditModel):
    amount = models.DecimalField(max_digits=10, decimal_places=2)
```

#### ComprehensiveAuditModel (New Models)

For new models requiring maximum audit capabilities from the start.

```python
class ComprehensiveAuditModel(UUIDModel, TimestampedModel, UserTrackingModel, SoftDeleteModel):
    """Complete audit trail with UUID primary keys"""
    class Meta:
        abstract = True
```

**Usage:**
```python
class NewDocument(ComprehensiveAuditModel):
    title = models.CharField(max_length=200)
    content = models.TextField()
    
    class Meta:
        verbose_name = "Document"
        verbose_name_plural = "Documents"
```

### Specialized Models

#### SystemAuditLog

Centralized audit log for all management override actions.

```python
class SystemAuditLog(TimestampedModel):
    class ActionType(models.TextChoices):
        ENROLLMENT_OVERRIDE = "ENROLLMENT_OVERRIDE"
        PREREQUISITE_OVERRIDE = "PREREQUISITE_OVERRIDE"
        CAPACITY_OVERRIDE = "CAPACITY_OVERRIDE"
        # ... more action types
    
    action_type = models.CharField(max_length=50, choices=ActionType.choices)
    performed_by = models.ForeignKey(User, on_delete=models.PROTECT)
    override_reason = models.TextField()
    override_details = models.JSONField(default=dict)
    # ... additional fields
```

**Usage:**
```python
# Log an override action
SystemAuditLog.log_override(
    action_type="ENROLLMENT_OVERRIDE",
    performed_by=request.user,
    target_object=enrollment,
    override_reason="Student met prerequisites through experience",
    original_restriction="Missing MATH-101 prerequisite",
    request=request  # For IP/user agent
)
```

#### StudentActivityLog

Comprehensive audit log for all student-related activities.

```python
class StudentActivityLog(TimestampedModel):
    class ActivityType(models.TextChoices):
        CLASS_ENROLLMENT = "CLASS_ENROLLMENT"
        CLASS_WITHDRAWAL = "CLASS_WITHDRAWAL"
        GRADE_CHANGE = "GRADE_CHANGE"
        # ... more activity types
    
    student_number = models.CharField(max_length=20, db_index=True)
    activity_type = models.CharField(max_length=40, choices=ActivityType.choices)
    description = models.TextField()
    activity_details = models.JSONField(default=dict)
    # ... additional fields
```

**Usage:**
```python
# Log student activity
StudentActivityLog.log_student_activity(
    student=student_profile,
    activity_type="CLASS_ENROLLMENT",
    description="Enrolled in GESL-01 Section A",
    performed_by=request.user,
    term=current_term,
    class_header=class_header
)

# Search activities
activities = StudentActivityLog.search_student_activities(
    student_number="12345",
    activity_type="CLASS_ENROLLMENT",
    date_from=date(2024, 1, 1),
    limit=50
)
```

## CRUD Framework

### Quick Start

```python
from apps.common.crud import CRUDListView, CRUDCreateView, CRUDUpdateView
from apps.common.crud.config import CRUDConfig, FieldConfig

class StudentListView(CRUDListView):
    model = Student
    
    crud_config = CRUDConfig(
        page_title="Student Management",
        page_subtitle="Manage student records",
        page_icon="fas fa-graduation-cap",
        
        fields=[
            FieldConfig(name="student_id", verbose_name="Student ID"),
            FieldConfig(name="name", searchable=True),
            FieldConfig(name="email", searchable=True),
            FieldConfig(name="major", field_type="foreign_key", searchable=True),
            FieldConfig(name="gpa", field_type="number", format=2),
            FieldConfig(name="is_active", field_type="boolean"),
        ],
        
        enable_search=True,
        enable_export=True,
        enable_column_toggle=True,
        
        row_actions=[
            {"type": "view"},
            {"type": "edit"},
            {"type": "delete"},
        ]
    )
```

### Features

#### Sorting and Searching

- **Multi-column sorting**: Click headers to sort, shift-click for multi-column
- **Global search**: Searches across all searchable fields
- **Field-specific search**: Advanced search with per-field filters

#### Export Functionality

```python
crud_config = CRUDConfig(
    enable_export=True,
    export_formats=["csv", "xlsx"],
    export_filename_prefix="students",
    fields=[
        FieldConfig(name="student_id", export=True),
        FieldConfig(name="ssn", export=False),  # Exclude sensitive data
    ]
)
```

#### Bulk Actions

```python
crud_config = CRUDConfig(
    enable_bulk_actions=True,
    bulk_actions=[
        {
            "name": "activate",
            "label": "Activate Selected",
            "icon": "fas fa-check",
            "confirm": "Are you sure?",
        },
    ]
)

# Handle in view
def post(self, request, *args, **kwargs):
    action = request.POST.get('bulk_action')
    selected_ids = request.POST.getlist('selected_items')
    
    if action == 'activate':
        Student.objects.filter(id__in=selected_ids).update(is_active=True)
        messages.success(request, f"Activated {len(selected_ids)} students.")
    
    return self.get(request, *args, **kwargs)
```

#### Custom Field Renderers

```python
def render_status(value, field_config):
    if value == 'active':
        return format_html(
            '<span class="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">Active</span>'
        )
    return format_html(
        '<span class="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-800">Inactive</span>'
    )

crud_config = CRUDConfig(
    fields=[
        FieldConfig(name="status", renderer=render_status),
    ]
)
```

## Utilities

### Phone Number Utilities

```python
from apps.common.utils import normalize_phone_number, validate_phone_number

# Normalize various phone formats
normalized = normalize_phone_number("012 345 678")  # Returns "+855012345678"
normalized = normalize_phone_number("+1-555-123-4567")  # Returns "+15551234567"

# Validate phone numbers
try:
    validate_phone_number("12345")  # Raises ValidationError
except ValidationError as e:
    print(e.message)
```

### String and Data Utilities

```python
from apps.common.utils import (
    truncate_string, format_name, generate_unique_code,
    safe_get_attr, model_to_dict_with_relations
)

# String manipulation
truncated = truncate_string("Long text here", 10, "...")  # "Long te..."
name = format_name("John", "Doe", "last_first")  # "Doe, John"

# Unique code generation
code = generate_unique_code("STU", 6)  # "STU4A7B9C"

# Safe attribute access
email = safe_get_attr(user, "profile.email", "N/A")

# Model to dict conversion
data = model_to_dict_with_relations(student, exclude_fields=['password'])
```

### Date and Time Utilities

```python
from apps.common.utils import get_current_date

# Timezone-aware current date
today = get_current_date()  # Returns timezone-aware date
```

### Student ID Formatting

```python
from apps.common.utils.student_id_formatter import format_student_id

# Format with institutional standards
formatted_id = format_student_id(12345)  # Returns "SIS-12345"
```

## Management Commands

### BaseMigrationCommand

All data migration commands must inherit from this base class for consistency and reporting.

```python
from apps.common.management.base_migration import BaseMigrationCommand

class Command(BaseMigrationCommand):
    help = "Import legacy student data"
    
    def handle_migration(self, *args, **options):
        """Main migration logic"""
        records = self.load_source_data()
        self.process_records(records)
    
    def validate_record(self, record):
        """Custom validation logic"""
        if not record.get('student_id'):
            return False, "Missing student ID"
        return True, None
    
    def transform_record(self, record):
        """Data transformation"""
        return {
            'student_id': record['id'],
            'name': f"{record['first_name']} {record['last_name']}",
            'email': record['email_address']
        }
```

### Features

- **Comprehensive Reporting**: Automatic JSON report generation
- **Error Categorization**: Structured error tracking and rejection reasons
- **Idempotent Operations**: Safe to run multiple times
- **Progress Tracking**: Real-time progress display
- **Rollback Support**: Automatic transaction management

### Built-in Commands

```bash
# Generate OpenAPI schema
python manage.py generate_openapi_schema

# Setup test data
python manage.py setup_test_data

# Database migration utilities
python manage.py migrate_both
python manage.py setup_migration_database
```

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

<!-- Safe attribute access -->
{{ student|safe_attr:"profile.major.name"|default:"No Major" }}
```

### CRUD Tags

```django
{% load crud_tags %}

<!-- Render complete CRUD table -->
{% crud_table config=config queryset=students %}

<!-- Export buttons -->
{% crud_export_buttons formats="csv,xlsx" %}

<!-- Bulk action controls -->
{% crud_bulk_actions actions=bulk_actions %}

<!-- Column toggle controls -->
{% crud_column_toggles fields=fields %}
```

## API Reference

### Base Model Methods

#### SoftDeleteModel

- `soft_delete()`: Mark record as deleted
- `restore()`: Restore deleted record

#### StatusModel

- Status changes automatically tracked
- Override `STATUS_CHOICES` in child models

#### SystemAuditLog

- `log_override(action_type, performed_by, **kwargs)`: Log override action

#### StudentActivityLog

- `log_student_activity(student, activity_type, description, **kwargs)`: Log activity
- `search_student_activities(**filters)`: Search activities
- `log_status_change(student, old_status, new_status, user)`: Log status changes
- `log_enrollment(student, class_header, term, user, action)`: Log enrollment actions
- `log_grade_change(student, class_code, old_grade, new_grade, user)`: Log grade changes

### CRUD Configuration Classes

#### CRUDConfig

Main configuration class for CRUD views.

```python
CRUDConfig(
    page_title="Data Management",
    page_subtitle=None,
    page_icon=None,
    fields=[],
    default_sort_field="-id",
    paginate_by=25,
    enable_search=True,
    enable_export=True,
    enable_bulk_actions=False,
    row_actions=[],
    bulk_actions=[],
    # ... more options
)
```

#### FieldConfig

Field-specific configuration.

```python
FieldConfig(
    name="field_name",           # Required
    verbose_name=None,           # Display name
    field_type="text",           # Field type
    sortable=True,               # Enable sorting
    searchable=False,            # Include in search
    hidden=False,                # Initially hidden
    truncate=None,               # Truncate length
    format=None,                 # Date/number format
    link_url=None,               # Make field a link
    renderer=None,               # Custom renderer function
    css_class=None,              # Additional CSS classes
    export=True,                 # Include in export
)
```

### Utility Functions

#### Phone Utilities

- `validate_phone_number(phone: str) -> None`: Validate phone format
- `normalize_phone_number(phone: str, country_code: str = "855") -> str`: Normalize phone

#### String Utilities

- `truncate_string(text: str, max_length: int, suffix: str = "...") -> str`
- `format_name(first: str, last: str, format_type: str = "full") -> str`
- `generate_unique_code(prefix: str = "", length: int = 8) -> str`

#### Data Utilities

- `safe_get_attr(obj: Any, attr_path: str, default: Any = None) -> Any`
- `model_to_dict_with_relations(instance, exclude_fields: list = None) -> dict`
- `get_model_changes(old_instance, new_instance, exclude_fields: list = None) -> dict`

## Usage Examples

### Creating a Complete CRUD Interface

```python
# models.py
class Course(UserAuditModel):
    code = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    credits = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

# views.py
from apps.common.crud import CRUDListView, CRUDCreateView, CRUDUpdateView
from apps.common.crud.config import CRUDConfig, FieldConfig

class CourseListView(CRUDListView):
    model = Course
    
    crud_config = CRUDConfig(
        page_title="Course Management",
        page_icon="fas fa-book",
        
        fields=[
            FieldConfig(name="code", searchable=True, link_url="/courses/{pk}/"),
            FieldConfig(name="title", searchable=True, truncate=50),
            FieldConfig(name="credits", field_type="number"),
            FieldConfig(name="is_active", field_type="boolean"),
            FieldConfig(name="created_at", field_type="datetime"),
        ],
        
        enable_search=True,
        enable_export=True,
        enable_bulk_actions=True,
        
        bulk_actions=[
            {
                "name": "activate",
                "label": "Activate Selected",
                "icon": "fas fa-check",
                "confirm": "Activate selected courses?",
            }
        ],
        
        row_actions=[
            {"type": "view"},
            {"type": "edit"},
            {"type": "delete"},
        ]
    )
    
    def post(self, request, *args, **kwargs):
        # Handle bulk actions
        action = request.POST.get('bulk_action')
        selected_ids = request.POST.getlist('selected_items')
        
        if action == 'activate':
            Course.objects.filter(id__in=selected_ids).update(is_active=True)
            messages.success(request, f"Activated {len(selected_ids)} courses.")
        
        return self.get(request, *args, **kwargs)

class CourseCreateView(CRUDCreateView):
    model = Course
    fields = ['code', 'title', 'credits', 'is_active']
    
    crud_config = CRUDConfig(
        page_title="Add Course",
        page_icon="fas fa-plus",
        list_url_name="courses:list",
    )

# urls.py
urlpatterns = [
    path('', CourseListView.as_view(), name='list'),
    path('add/', CourseCreateView.as_view(), name='create'),
    # ... more URLs
]
```

### Custom Migration Command

```python
# management/commands/import_legacy_courses.py
from apps.common.management.base_migration import BaseMigrationCommand
from .models import Course

class Command(BaseMigrationCommand):
    help = "Import legacy course data"
    
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--source-file', required=True, help='CSV file path')
    
    def handle_migration(self, *args, **options):
        source_file = options['source_file']
        records = self.load_csv_data(source_file)
        self.process_records(records)
    
    def validate_record(self, record):
        if not record.get('course_code'):
            return False, "Missing course code"
        if Course.objects.filter(code=record['course_code']).exists():
            return False, "Course already exists"
        return True, None
    
    def transform_record(self, record):
        return {
            'code': record['course_code'].upper(),
            'title': record['course_title'],
            'credits': int(record['credits']),
            'is_active': record.get('active', 'Y') == 'Y'
        }
    
    def create_object(self, transformed_data):
        return Course.objects.create(**transformed_data)
```

### Audit Logging Integration

```python
# In your views or services
from apps.common.models import SystemAuditLog, StudentActivityLog

# Log management override
def enroll_student_with_override(student, class_header, reason):
    # Perform enrollment
    enrollment = enroll_student(student, class_header)
    
    # Log the override
    SystemAuditLog.log_override(
        action_type="ENROLLMENT_OVERRIDE",
        performed_by=request.user,
        target_object=enrollment,
        override_reason=reason,
        original_restriction="Class capacity exceeded",
        request=request
    )
    
    # Log student activity
    StudentActivityLog.log_student_activity(
        student=student,
        activity_type="CLASS_ENROLLMENT",
        description=f"Enrolled in {class_header.course.code} with capacity override",
        performed_by=request.user,
        class_header=class_header,
        activity_details={"override_reason": reason}
    )
    
    return enrollment
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

# Run with coverage
pytest apps/common/ --cov=apps.common --cov-report=html
```

### Test Structure

```
apps/common/tests/
├── test_models.py          # Base model functionality
├── test_utils.py           # Utility function tests
├── test_crud.py            # CRUD framework tests
├── test_audit.py           # Audit logging tests
├── test_commands.py        # Management command tests
└── fixtures/               # Test data fixtures
```

### Writing Tests

```python
# tests/test_models.py
import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.common.models import StudentActivityLog

User = get_user_model()

class StudentActivityLogTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com'
        )
    
    def test_log_student_activity(self):
        activity = StudentActivityLog.log_student_activity(
            student=None,
            student_number="12345",
            activity_type="CLASS_ENROLLMENT",
            description="Test enrollment",
            performed_by=self.user
        )
        
        self.assertEqual(activity.student_number, "12345")
        self.assertEqual(activity.activity_type, "CLASS_ENROLLMENT")
        self.assertEqual(activity.performed_by, self.user)
    
    def test_search_activities(self):
        # Create test activities
        StudentActivityLog.log_student_activity(
            student=None,
            student_number="12345",
            activity_type="CLASS_ENROLLMENT",
            description="Enrolled in MATH-101",
            performed_by=self.user
        )
        
        # Search activities
        activities = StudentActivityLog.search_student_activities(
            student_number="12345",
            activity_type="CLASS_ENROLLMENT"
        )
        
        self.assertEqual(activities.count(), 1)
        self.assertEqual(activities.first().description, "Enrolled in MATH-101")
```

## Contributing

### Development Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Tests**
   ```bash
   pytest apps/common/
   ```

3. **Code Quality**
   ```bash
   # Linting
   ruff check apps/common/
   
   # Formatting
   ruff format apps/common/
   
   # Type checking
   mypy apps/common/
   ```

### Contributing Guidelines

1. **Follow Django Conventions**: Use Django best practices and naming conventions
2. **Maintain Clean Architecture**: No dependencies on business layer apps
3. **Write Tests**: All new functionality must include comprehensive tests
4. **Document Changes**: Update documentation for new features
5. **Type Hints**: Use type hints for all new functions and methods

### Code Standards

- **Line Length**: 88 characters (ruff default)
- **Import Organization**: Use `ruff` for automatic import sorting
- **Docstrings**: Google-style docstrings for all public functions
- **Type Hints**: Required for all new code
- **Error Handling**: Specific exceptions with helpful messages

### Architecture Considerations

When adding new functionality to the common app:

1. **Ensure Zero Dependencies**: No imports from other Naga SIS apps
2. **Maximize Reusability**: Design for use across multiple apps
3. **Follow Single Responsibility**: Each component should have one clear purpose
4. **Consider Performance**: Optimize for common use cases
5. **Plan for Extension**: Design APIs that can be extended without breaking changes

---

This documentation covers the comprehensive functionality of the `apps/common` module. For specific implementation details, refer to the source code and inline documentation.