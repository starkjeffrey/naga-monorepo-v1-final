# Pending Architectural Decisions - 2025-07-09

## Overview

This document outlines pending architectural decisions that require input for implementation in the people app code review cleanup.

## Task 11: Create BaseProfileAdmin - Extract Shared Functionality

### Current Situation

Three admin classes share significant duplicate code:

- `StudentProfileAdmin`
- `TeacherProfileAdmin`
- `StaffProfileAdmin`

### Shared Functionality Identified

All three classes have:

- `get_queryset()` implementations that call `select_related("person")`
- `person_name` display method that returns `obj.person.full_name`
- Similar patterns for person-related field access

### Design Questions

1. **Base Class Structure**: Should we create a `BaseProfileAdmin` abstract class or use composition?
2. **Field Inheritance**: Which fields should be inherited vs. overridden in child classes?
3. **Method Overrides**: How should we handle admin methods that are similar but not identical?
4. **Backwards Compatibility**: Do we need to maintain existing admin functionality exactly?

### Proposed Implementation Approach

```python
class BaseProfileAdmin(admin.ModelAdmin):
    """Base admin class for profile models linked to Person."""

    def get_queryset(self, request):
        """Optimize queryset to prevent N+1 queries for person access."""
        return super().get_queryset(request).select_related("person")

    @admin.display(description="Name", ordering="person__full_name")
    def person_name(self, obj):
        """Display person's full name."""
        return obj.person.full_name

    # Additional shared methods...
```

### Questions for Implementation

- Should we extract more shared functionality beyond queryset and person_name?
- How should we handle the different list_display configurations?
- Are there any admin customizations that should remain profile-specific?

## Task 13: Replace Local Imports with Django Signals

### Current Situation

Admin actions use local imports to avoid circular dependencies:

```python
def activate_students(self, request, queryset):
    # ...
    from apps.common.models import SystemAuditLog  # Local import
    # Create audit logs...
```

### Architectural Concern

Local imports often indicate design issues and tight coupling between components.

### Proposed Solution: Django Signals

Decouple audit logging from admin actions using Django signals:

```python
# In apps/people/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.common.models import SystemAuditLog

@receiver(post_save, sender=StudentProfile)
def log_student_profile_changes(sender, instance, created, **kwargs):
    # Handle audit logging automatically
    pass
```

### Design Questions

1. **Signal Scope**: Should we create signals for all profile changes or just admin actions?
2. **Signal Organization**: Where should signal handlers be defined and registered?
3. **Data Flow**: How should we pass context (user, reason, etc.) to signal handlers?
4. **Performance**: Will signals introduce performance overhead for bulk operations?
5. **Testing**: How should we test signal-based audit logging?

### Implementation Considerations

- Signal handlers would need access to request context (user, IP, etc.)
- Bulk operations might trigger many signals - performance impact?
- Signal registration needs to happen at app startup
- Error handling in signal handlers shouldn't break main operations

### Questions for Implementation

- Should we use custom signals or built-in Django signals?
- How should we handle the transition from current local imports to signals?
- Are there any admin actions that should NOT trigger signals?
- Should signals be synchronous or asynchronous?

## Implementation Priority

Both tasks are marked as **low priority** and can be implemented incrementally without breaking existing functionality.

## Next Steps

Please review these questions and provide guidance on:

1. Whether to proceed with these architectural changes
2. Preferred implementation approaches
3. Any additional considerations or constraints
4. Priority ordering if both should be implemented

---

_Document created: 2025-07-09_
_Context: People app code review cleanup - architectural improvements_
