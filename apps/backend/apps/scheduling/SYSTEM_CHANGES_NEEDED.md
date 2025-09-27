# System Changes Needed for Scheduling Interface

**Created**: July 20, 2024  
**Author**: Claude Code  
**Status**: Documentation Only - No Changes Implemented

## Overview

This document outlines backend changes and considerations needed to fully implement the scheduling interface. These are suggestions that require approval before implementation.

## Important Note

All UI templates and components have been created and are ready to use. However, they currently use placeholder views and mock data. The changes documented below are needed to connect the UI to real data and functionality.

## 1. URL Configuration

### Required: Add scheduling URLs to main urlpatterns

```python
# In config/urls.py, add:
path('scheduling/', include('apps.scheduling.urls', namespace='scheduling')),
```

### Required: Create apps/scheduling/urls.py

```python
from django.urls import path
from . import views

app_name = 'scheduling'

urlpatterns = [
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('classes/', views.ClassListView.as_view(), name='class_list'),
    path('classes/create/', views.ClassCreateWizard.as_view(), name='class_create'),
    path('classes/<int:pk>/', views.ClassDetailView.as_view(), name='class_detail'),
    # ... more patterns
]
```

## 2. View Classes Needed

### Base Views Required:

1. `DashboardView` - Summary statistics and quick actions
2. `ClassListView` - Filterable list with HTMX support
3. `ClassDetailView` - Full class information
4. `ClassCreateWizard` - Multi-step creation form
5. `EnrollmentManagementView` - Add/drop students
6. `StudentScheduleView` - View student's schedule
7. `ArchiveView` - Historical data browser

### HTMX Endpoints Required:

1. `htmx_search_students` - Live student search
2. `htmx_filter_classes` - Dynamic filtering
3. `htmx_update_status` - Inline status updates
4. `htmx_enrollment_widget` - Enrollment management
5. `htmx_load_class_parts` - Lazy load class parts

## 3. Model Enhancements

### ClassHeader additions:

```python
# Suggested computed properties
@property
def schedule_display(self):
    """Human-readable schedule summary"""
    parts = self.class_sessions.first().class_parts.all()
    # ... format schedule

@property
def conflict_check(self):
    """Check for scheduling conflicts"""
    # ... implement conflict detection
```

### Manager Methods:

```python
class ClassHeaderManager(models.Manager):
    def for_current_term(self):
        """Get classes for current/upcoming term"""
        # ... implementation

    def with_availability(self):
        """Annotate with enrollment counts"""
        # ... use aggregation
```

## 4. Permissions & Security

### Required Permissions:

1. `can_view_all_classes` - View any class
2. `can_create_class` - Create new classes
3. `can_edit_class` - Modify class details
4. `can_manage_enrollments` - Add/drop students
5. `can_view_archive` - Access historical data

### Permission Groups:

- **Registrar**: All permissions
- **Academic Admin**: View and edit classes
- **Department Head**: View department classes
- **Advisor**: View student schedules

## 5. Service Layer Functions

### apps/scheduling/services.py additions:

```python
def create_class_from_template(template, term, section):
    """Create ClassHeader from curriculum template"""

def check_enrollment_eligibility(student, class_header):
    """Verify student can enroll"""

def enroll_student(student, class_header):
    """Process enrollment with validations"""

def get_schedule_conflicts(student, class_header):
    """Check for time conflicts"""
```

## 6. Template Structure

### Directory Layout:

```
templates/
  scheduling/
    base_scheduling.html          # App-specific base
    dashboard.html               # Main dashboard
    class_list.html             # Class listing
    class_detail.html           # Single class view
    enrollment_manage.html      # Enrollment interface
    components/
      term_selector.html        # Reusable components
      class_card.html
      enrollment_widget.html
    partials/                   # HTMX fragments
      class_row.html
      enrollment_list.html
      student_search_results.html
```

## 7. Static Files Organization

### JavaScript Modules:

```
static/js/scheduling/
  dashboard.js      # Dashboard-specific JS
  enrollment.js     # Enrollment management
  schedule-grid.js  # Calendar visualization
  components/       # Reusable JS components
```

### CSS Structure:

```
static/css/scheduling/
  scheduling.css    # App-specific styles
  components.css    # Component library
```

## 8. Performance Considerations

### Database Optimizations:

1. Add indexes for common queries:

   ```python
   class Meta:
       indexes = [
           models.Index(fields=['term', 'status']),
           models.Index(fields=['course', 'term']),
       ]
   ```

2. Implement select_related/prefetch_related:
   ```python
   ClassHeader.objects.select_related(
       'course', 'term', 'combined_class_instance'
   ).prefetch_related(
       'class_sessions__class_parts'
   )
   ```

### Caching Strategy:

1. Cache term lists (changes rarely)
2. Cache course catalog (changes per term)
3. Use Redis for enrollment counts
4. Session-based filter preferences

## 9. Integration Points

### With Other Apps:

1. **enrollment app**: Create/update ClassHeaderEnrollment
2. **people app**: Access student/teacher profiles
3. **curriculum app**: Read courses and terms
4. **common app**: Use rooms and facilities
5. **finance app**: Trigger billing on enrollment

### External Systems:

1. **Email notifications**: On enrollment changes
2. **Calendar export**: ICS file generation
3. **Reporting**: Connect to analytics

## 10. Testing Requirements

### Unit Tests:

1. Model validation tests
2. Service function tests
3. Permission tests
4. Conflict detection tests

### Integration Tests:

1. Full enrollment workflow
2. Multi-user concurrent access
3. Term rollover scenarios

### UI Tests:

1. HTMX interaction tests
2. Mobile responsiveness
3. Accessibility compliance

## Implementation Priority

### Phase 1 (Core Functionality):

1. Basic views and templates
2. Class list and detail views
3. Simple enrollment add/drop

### Phase 2 (Enhanced Features):

1. Create class wizard
2. Advanced filtering
3. Conflict checking

### Phase 3 (Polish):

1. Schedule visualization
2. Bulk operations
3. Historical analytics

## Notes for Implementation

1. All changes should maintain the clean architecture principles
2. No circular dependencies between apps
3. Use Django's built-in features where possible
4. Keep HTMX interactions simple and focused
5. Ensure mobile-first responsive design

These changes require approval before implementation. The current design uses only templates and static files without modifying the existing models or creating database migrations.
