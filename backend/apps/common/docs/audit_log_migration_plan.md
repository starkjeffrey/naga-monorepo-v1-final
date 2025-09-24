# Audit Log Migration Plan

## Overview

This document outlines the plan to consolidate the two existing audit log models (`people.StudentAuditLog` and `common.StudentActivityLog`) into a single, comprehensive `StudentActivityLog` model in the `common` app.

## Current State

### Two Separate Models

1. **`people.StudentAuditLog`**

   - Uses foreign key to `StudentProfile`
   - Tracks profile-specific changes (status, monk status, etc.)
   - Has generic foreign key support for related objects
   - Limited activity types

2. **`common.StudentActivityLog`**
   - Uses string-based references (student_number)
   - Tracks broader range of activities
   - Better search capabilities with multiple indexes
   - No circular dependencies

## Migration Strategy

### Phase 1: Enhancement (COMPLETED)

1. **Enhanced `StudentActivityLog` model** with:

   - Additional activity types from `StudentAuditLog`
   - Visibility control field
   - Helper methods for common scenarios
   - Better support for all use cases

2. **Created decorator system** (`@audit_student_activity`) for easy integration

3. **Built utilities** for batch operations and migration

### Phase 2: Migration Implementation

#### Step 1: Data Migration

```python
# Run migration script to copy existing StudentAuditLog records
from apps.common.audit_utils import migrate_student_audit_logs

# Test with dry run first
result = migrate_student_audit_logs(dry_run=True)
print(f"Would migrate {result['migrated']} records")

# Execute actual migration
result = migrate_student_audit_logs(dry_run=False)
print(f"Migrated {result['migrated']} records")
```

#### Step 2: Update Existing Code

Apps that need updating:

1. **`people` app**

   - Replace `StudentAuditLog.log_status_change()` with `StudentActivityLog.log_status_change()`
   - Replace `StudentAuditLog.log_monk_status_change()` with decorator or helper
   - Update admin to show new audit logs

2. **`enrollment` app**

   - Add `@audit_student_activity` decorator to enrollment methods
   - Replace any direct audit log creation

3. **`grading` app**

   - Add audit logging for grade assignments and changes
   - Use the decorator pattern for consistency

4. **`language` app**

   - Add audit logging for level promotions
   - Track language program transfers

5. **`scholarships` app**
   - Log scholarship assignments and revocations
   - Track sponsor changes

### Phase 3: Cleanup

1. Mark `StudentAuditLog` as deprecated
2. Add migration warning to the model
3. Update documentation
4. Remove old model after verification period

## Usage Examples

### Using Decorators

```python
from apps.common.audit_decorators import audit_student_activity
from apps.common.models import StudentActivityLog

class EnrollmentService:
    @audit_student_activity(
        activity_type=StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
        description_template="Enrolled in {class_header.course.code} Section {class_header.section_id}"
    )
    def enroll_student(self, student, class_header, term, user):
        # Your enrollment logic here
        enrollment = ClassHeaderEnrollment.objects.create(
            student=student,
            class_header=class_header,
            enrollment_date=timezone.now()
        )
        return enrollment

    @audit_student_activity(
        activity_type=StudentActivityLog.ActivityType.CLASS_WITHDRAWAL,
        student_source="enrollment.student",
        description_template="Withdrawn from {enrollment.class_header.course.code}"
    )
    def withdraw_student(self, enrollment, reason, user):
        # Your withdrawal logic here
        enrollment.status = 'withdrawn'
        enrollment.withdrawal_reason = reason
        enrollment.save()
```

### Using Helper Methods

```python
from apps.common.models import StudentActivityLog

# Log a status change
StudentActivityLog.log_status_change(
    student=student_profile,
    old_status='active',
    new_status='graduated',
    user=request.user,
    notes='Completed all requirements'
)

# Log a grade change
StudentActivityLog.log_grade_change(
    student=student_profile,
    class_code='CS101',
    old_grade='B+',
    new_grade='A-',
    user=request.user,
    reason='Grading error correction'
)

# Log an override
StudentActivityLog.log_override(
    student=student_profile,
    override_type='prerequisite',
    reason='Department approval for advanced placement',
    user=request.user,
    course_code='CS301',
    prerequisite_waived='CS201'
)
```

### Batch Operations

```python
from apps.common.audit_utils import batch_log_student_activities

# Log multiple activities at once
activities = []
for enrollment in enrollments:
    activities.append({
        'student': enrollment.student,
        'activity_type': StudentActivityLog.ActivityType.CLASS_ENROLLMENT,
        'description': f'Enrolled in {enrollment.class_header.course.code}',
        'user': request.user,
        'term': enrollment.class_header.term,
        'class_header': enrollment.class_header,
        'visibility': StudentActivityLog.VisibilityLevel.STUDENT_VISIBLE,
    })

count = batch_log_student_activities(activities)
print(f"Created {count} audit logs")
```

### Querying Activities

```python
# Search student activities
activities = StudentActivityLog.search_student_activities(
    student_number='12345',
    activity_type=StudentActivityLog.ActivityType.GRADE_CHANGE,
    term_name='2024-1',
    date_from=timezone.now() - timedelta(days=30)
)

# Get student-visible activities only
student_activities = StudentActivityLog.objects.filter(
    student_number='12345',
    visibility__in=[
        StudentActivityLog.VisibilityLevel.STUDENT_VISIBLE,
        StudentActivityLog.VisibilityLevel.PUBLIC
    ]
)
```

## Benefits of Consolidation

1. **Single source of truth** for all student activities
2. **No circular dependencies** with string-based references
3. **Better performance** with optimized indexes
4. **Flexible visibility control** for student portal integration
5. **Consistent API** across all apps
6. **Easy decorator-based integration**
7. **Comprehensive activity types** covering all use cases

## Timeline

- **Week 1**: Test migration scripts with production data snapshot
- **Week 2**: Update critical apps (enrollment, grading)
- **Week 3**: Update remaining apps
- **Week 4**: Monitor and verify all logging working correctly
- **Week 5**: Deprecate old model and plan removal

## Rollback Plan

If issues arise:

1. Both models can coexist during transition
2. Migration is non-destructive (creates new records)
3. Old code paths remain functional
4. Can revert decorator usage to direct model calls

## Success Criteria

- All StudentAuditLog records successfully migrated
- No loss of audit data
- All apps using new StudentActivityLog model
- Improved query performance for audit trails
- Student portal showing appropriate activities
