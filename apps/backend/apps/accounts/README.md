# Accounts App

## Overview

The `accounts` app manages user authentication, authorization, roles, and organizational structure within the Naga SIS. This foundation layer app provides the security and permission framework that all other applications depend on.

## Features

### Role-Based Access Control (RBAC)

- **Hierarchical roles** with inheritance
- **Permission-based authorization** with fine-grained control
- **Temporal role assignments** with start/end dates
- **Role override capabilities** for administrative actions

### Organizational Structure

- **Department management** with hierarchical organization
- **Position definitions** with role mappings
- **Teaching assignments** with course and schedule tracking
- **Staff assignments** with responsibility areas

### Authorization Framework

- **Policy-based permissions** with contextual evaluation
- **Teaching authorization** with course-specific validation
- **Administrative authority** with audit trail
- **Override mechanisms** with justification requirements

## Models

### Core Authorization

#### Role

System roles that define permission sets.

```python
# Define system roles
teacher_role = Role.objects.create(
    name="Teacher",
    description="Faculty member with teaching responsibilities",
    permissions=["view_students", "manage_grades", "take_attendance"]
)

admin_role = Role.objects.create(
    name="Academic Admin",
    description="Academic administration with student management",
    permissions=["manage_enrollments", "override_grades", "manage_schedules"]
)
```

#### UserRole

Associates users with roles and defines scope.

```python
# Assign role to user with temporal constraints
user_role = UserRole.objects.create(
    user=teacher_user,
    role=teacher_role,
    start_date=date(2024, 8, 1),
    end_date=date(2025, 5, 31),  # Academic year
    is_active=True
)
```

### Organizational Structure

#### Department

Academic and administrative departments.

```python
# Create department hierarchy
academic_affairs = Department.objects.create(
    name="Academic Affairs",
    department_type=DepartmentType.ADMINISTRATIVE,
    parent=None
)

english_dept = Department.objects.create(
    name="English Department",
    department_type=DepartmentType.ACADEMIC,
    parent=academic_affairs
)
```

#### Position

Job positions with associated roles and responsibilities.

```python
# Define institutional positions
position = Position.objects.create(
    title="Senior English Instructor",
    department=english_dept,
    position_type=PositionType.TEACHING,
    required_roles=[teacher_role],
    description="Senior faculty position with mentoring responsibilities"
)
```

#### PositionAssignment

Associates staff with positions over time.

```python
# Assign person to position
assignment = PositionAssignment.objects.create(
    person=teacher_person,
    position=english_instructor,
    start_date=date(2024, 8, 1),
    assignment_type=AssignmentType.PRIMARY,
    fte_percentage=Decimal("1.00")  # Full-time
)
```

### Teaching Authorization

#### TeachingAssignment

Authorizes teachers for specific courses and terms.

```python
# Authorize teacher for course
teaching_assignment = TeachingAssignment.objects.create(
    teacher=teacher_profile,
    course=english_101,
    term=fall_2024,
    assignment_type=TeachingAssignmentType.PRIMARY,
    authorization_level=AuthorizationLevel.FULL
)
```

## Services

### Authorization Service

Centralized authorization logic with caching and audit trails.

```python
from apps.accounts.services import AuthorizationService

# Check if user can perform action
can_grade = AuthorizationService.can_user_perform_action(
    user=request.user,
    action="grade_student",
    context={"course": course, "student": student}
)

# Get user's effective permissions
permissions = AuthorizationService.get_user_permissions(
    user=request.user,
    context={"department": english_dept}
)
```

### Role Service

Role management with inheritance and temporal validation.

```python
from apps.accounts.services import RoleService

# Get active roles for user
active_roles = RoleService.get_active_roles(
    user=request.user,
    as_of_date=date.today()
)

# Check role inheritance
has_permission = RoleService.user_has_permission(
    user=request.user,
    permission="manage_grades",
    context={"course": course}
)
```

## Authorization Policies

### Teaching Policies

Specialized policies for academic authorization.

```python
from apps.accounts.policies.teaching_policies import TeachingPolicy

class CourseGradingPolicy(TeachingPolicy):
    def can_grade_course(self, user, course, term=None):
        """Check if user can grade specific course."""
        # Check teaching assignment
        if self.has_teaching_assignment(user, course, term):
            return True

        # Check administrative override
        if self.has_grading_override_permission(user):
            return True

        return False
```

### Authority Policies

Administrative authorization with override tracking.

```python
from apps.accounts.policies.authority_policies import AuthorityPolicy

class EnrollmentPolicy(AuthorityPolicy):
    def can_modify_enrollment(self, user, enrollment):
        """Check enrollment modification authorization."""
        return (
            self.is_academic_admin(user) or
            self.is_department_admin(user, enrollment.course.department) or
            self.has_override_authority(user, "enrollment_modification")
        )
```

## Mixins

### Authorization Mixins

Reusable authorization patterns for views and APIs.

```python
from apps.accounts.mixins import TeachingRequiredMixin

class GradeEntryView(TeachingRequiredMixin, UpdateView):
    """Grade entry requires teaching authorization."""
    model = Grade

    def get_authorization_context(self):
        grade = self.get_object()
        return {
            "course": grade.enrollment.course,
            "term": grade.enrollment.term
        }
```

## Management Commands

### Role Management

```bash
# Setup default roles and permissions
python manage.py setup_default_roles

# Sync user roles with position assignments
python manage.py sync_position_roles

# Audit role assignments
python manage.py audit_role_assignments --expired-only
```

### User Management

```bash
# Create administrative user
python manage.py create_admin_user --username=admin --email=admin@pucsr.edu.kh

# Import staff from CSV
python manage.py import_staff --file=staff_data.csv --dry-run

# Deactivate former employees
python manage.py deactivate_former_staff --term=fall2024
```

## API Endpoints

### Role Management

```python
# Get user's roles and permissions
GET /api/accounts/users/{user_id}/roles/
{
    "active_roles": [
        {
            "role": "Teacher",
            "start_date": "2024-08-01",
            "end_date": "2025-05-31",
            "permissions": ["view_students", "manage_grades"]
        }
    ]
}

# Check specific permission
GET /api/accounts/users/{user_id}/permissions/can_grade_course/
{
    "can_perform": true,
    "context": {"course_id": 123},
    "authorization_source": "teaching_assignment"
}
```

### Department Structure

```python
# Get department hierarchy
GET /api/accounts/departments/
{
    "departments": [
        {
            "id": 1,
            "name": "Academic Affairs",
            "type": "administrative",
            "children": [
                {
                    "id": 2,
                    "name": "English Department",
                    "type": "academic"
                }
            ]
        }
    ]
}
```

## Authorization Decorators

### Function-Based Views

```python
from apps.accounts.decorators import (
    require_permission,
    require_teaching_assignment,
    require_role
)

@require_permission('manage_students')
def student_list_view(request):
    """Requires manage_students permission."""
    pass

@require_teaching_assignment
def grade_entry_view(request, course_id):
    """Requires teaching assignment for course."""
    pass

@require_role('Academic Admin')
def admin_dashboard(request):
    """Requires specific role."""
    pass
```

### Class-Based Views

```python
from django.contrib.auth.mixins import PermissionRequiredMixin
from apps.accounts.mixins import TeachingRequiredMixin

class StudentGradeView(TeachingRequiredMixin, UpdateView):
    permission_required = 'accounts.grade_students'
    model = Grade
```

## Security Features

### Permission Validation

- **Contextual permissions** based on relationships
- **Temporal validation** with date range checking
- **Hierarchical authorization** with role inheritance
- **Override tracking** with audit trail

### Session Management

- **Role switching** for users with multiple roles
- **Permission caching** for performance
- **Session timeout** with security policies
- **Multi-factor authentication** integration ready

## Configuration

### Settings

```python
# Django settings for accounts app
NAGA_ACCOUNTS_CONFIG = {
    'DEFAULT_ROLE_DURATION_DAYS': 365,
    'REQUIRE_MFA_FOR_ADMIN': True,
    'PERMISSION_CACHE_TIMEOUT': 300,  # 5 minutes
    'ROLE_INHERITANCE_ENABLED': True,
    'AUDIT_AUTHORIZATION_FAILURES': True
}

# Permission groups
NAGA_PERMISSION_GROUPS = {
    'STUDENT_MANAGEMENT': [
        'view_students',
        'add_students',
        'change_students'
    ],
    'ACADEMIC_ADMIN': [
        'manage_enrollments',
        'override_grades',
        'manage_schedules'
    ]
}
```

### Environment Variables

```bash
# Session security
SESSION_TIMEOUT_MINUTES=30
REQUIRE_MFA_FOR_ADMIN=true

# Permission caching
PERMISSION_CACHE_BACKEND=redis
PERMISSION_CACHE_TIMEOUT=300

# Role management
DEFAULT_ROLE_DURATION=365
ROLE_INHERITANCE_DEPTH=3
```

## Testing

### Test Coverage

```bash
# Run accounts app tests
pytest apps/accounts/

# Test specific areas
pytest apps/accounts/tests/test_authorization.py
pytest apps/accounts/tests/test_role_inheritance.py
pytest apps/accounts/tests/test_teaching_policies.py
```

### Test Factories

```python
from apps.accounts.tests.factories import (
    UserFactory,
    RoleFactory,
    DepartmentFactory,
    TeachingAssignmentFactory
)

# Create test data
user = UserFactory()
role = RoleFactory(name="Test Teacher")
assignment = TeachingAssignmentFactory(
    teacher__user=user,
    course__name="Test Course"
)
```

## Integration Examples

### With Other Apps

```python
# Check if user can view student records
from apps.accounts.services import AuthorizationService

def get_student_list(request):
    if not AuthorizationService.can_user_perform_action(
        user=request.user,
        action="view_students"
    ):
        raise PermissionDenied("Insufficient permissions")

    return Student.objects.filter(
        department__in=user.accessible_departments.all()
    )
```

### Teaching Authorization

```python
# Validate teacher can grade specific class
from apps.accounts.policies.teaching_policies import TeachingPolicy

def submit_grades(request, class_id):
    class_header = get_object_or_404(ClassHeader, id=class_id)

    policy = TeachingPolicy()
    if not policy.can_grade_course(
        user=request.user,
        course=class_header.course,
        term=class_header.term
    ):
        raise PermissionDenied("Not authorized to grade this class")

    # Process grade submission
```

## Monitoring & Maintenance

### Regular Tasks

- **Role expiration cleanup**: Remove expired role assignments
- **Permission audit**: Verify role-permission consistency
- **Teaching assignment validation**: Ensure current assignments
- **Authorization failure analysis**: Review denied access patterns

### Performance Monitoring

- **Permission check latency**: Monitor authorization speed
- **Cache hit rates**: Optimize permission caching
- **Database query patterns**: Optimize role queries
- **Session management**: Monitor concurrent sessions

## Migration Patterns

### Role Data Migration

```python
from apps.accounts.models import Role, UserRole

# Migrate legacy roles
def migrate_legacy_roles():
    for legacy_user in LegacyUser.objects.all():
        if legacy_user.is_teacher:
            teacher_role = Role.objects.get(name="Teacher")
            UserRole.objects.create(
                user=legacy_user.new_user,
                role=teacher_role,
                start_date=legacy_user.hire_date
            )
```

## Dependencies

### Internal Dependencies

- `common`: Base models and audit framework
- Django's built-in User model and permissions

### External Dependencies

- `django-guardian`: Object-level permissions
- `django-role-permissions`: Enhanced role management
- `redis`: Permission caching (optional)

## Architecture Notes

### Design Principles

- **Foundation layer**: Other apps depend on accounts for authorization
- **Single responsibility**: Focus on authentication and authorization only
- **Extensible policies**: Easy to add new authorization rules
- **Performance-conscious**: Efficient permission checking with caching

### Security Considerations

- **Principle of least privilege**: Default to restrictive permissions
- **Defense in depth**: Multiple authorization layers
- **Audit everything**: Complete authorization decision logging
- **Temporal security**: Time-bound role assignments
