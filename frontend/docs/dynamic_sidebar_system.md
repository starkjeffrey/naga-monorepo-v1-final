# Dynamic Sidebar System Documentation

## Overview

The Naga SIS dynamic sidebar system provides role-based navigation that automatically adapts based on user permissions and group memberships. This eliminates the need for manual customization of navigation menus for different user roles.

## Architecture

### Core Components

1. **Context Processors** (`apps/common/context_processors.py`)
2. **Responsive Base Template** (`new_naga_sis_backend/templates/base_with_sidebar.html`)
3. **Navigation Configuration** (defined in context processors)
4. **Role-Based Display Logic** (template-level filtering)

## Features

### ✅ Implemented Features

- **Automatic Role Detection** - Users are automatically assigned display names based on groups
- **Permission-Based Filtering** - Navigation items appear/disappear based on user permissions
- **Responsive Design** - Mobile-first sidebar that works on all screen sizes
- **Hierarchical Navigation** - Sections with collapsible subsections
- **User Profile Display** - Shows user name, role, and institution information
- **Dynamic URL Generation** - Navigation URLs are automatically generated with parameters
- **Context-Aware Highlighting** - Current page is highlighted in navigation

### 🎯 Role-Based Navigation Logic

The system determines what navigation items to show using this hierarchy:

1. **Superuser** - Sees everything
2. **Permission Check** - User must have specific permission for the item
3. **Group Membership** - Some items are restricted to specific groups
4. **Staff Requirement** - Some items require `is_staff=True`

## Navigation Structure

### Available Sections

| Section | Description | Key Permissions |
|---------|-------------|-----------------|
| **Dashboard** | Home page access | Available to all authenticated users |
| **Level Testing** | Test applications and administration | `level_testing.view_potentialstudent` |
| **Student Management** | Student records and enrollment | `people.view_person`, `enrollment.view_enrollment` |
| **Academic** | Courses, programs, scheduling | `academic.view_course`, `curriculum.view_program` |
| **Finance** | Payments, invoicing, reports | `finance.view_payment`, `finance.view_invoice` |
| **Reports** | System-wide reporting | Various view permissions |
| **Administration** | System administration | `is_staff` required |

### Role-Specific Access

| Role | Primary Sections | Limited Access |
|------|------------------|----------------|
| **Superuser** | All sections | Full access to everything |
| **Finance Manager** | Finance, Reports | Full financial data access |
| **Registrar** | Student Management, Finance | Limited to student billing |
| **Academic Coordinator** | Academic, Student Management | Course and program management |
| **Administrative Clerk** | Level Testing | Test administration and payments |

## Implementation Details

### Context Processors

#### `navigation_context(request)`

Located in `apps/common/context_processors.py`, this function:

1. Checks if user is authenticated
2. Builds complete navigation structure from configuration
3. Filters items based on user permissions and groups
4. Returns filtered navigation and user role display

**Key Features:**
- Permission checking via `user.has_perm()`
- Group membership filtering
- URL generation with parameters
- Hierarchical structure support

#### `system_context(request)`

Provides system-wide variables:
- `system_name` - "PUCSR Student Information System"
- `system_version` - "1.0"
- `institution_name` - "Preah Kossomak Campus"
- `current_term` - "Spring 2024"

### Template Integration

#### Base Template (`base_with_sidebar.html`)

**Key Elements:**
- Responsive sidebar with mobile hamburger menu
- User profile section with avatar and role display
- Collapsible navigation sections
- Mobile overlay for tablet/phone views
- JavaScript for mobile menu functionality

**CSS Classes:**
- `.nav-section-toggle` - Collapsible section headers
- `.nav-section-content` - Hidden by default, shown when expanded
- `.sidebar-mobile` - Mobile-specific sidebar behavior
- `.custom-scrollbar` - Styled scrollbar for navigation

#### Page Templates

Templates using the sidebar should extend `base_with_sidebar.html`:

```django
{% extends "base_with_sidebar.html" %}
{% load i18n %}

{% block title %}{% trans "Page Title" %} - {{ block.super }}{% endblock %}

{% block content %}
<!-- Your page content here -->
{% endblock %}
```

## User Management

### Test Users

The system includes pre-configured test users for development and testing:

| Email | Password | Role | Groups |
|-------|----------|------|--------|
| `admin@test.com` | `admin123` | System Administrator | (superuser) |
| `finance_manager@test.com` | `test123` | Finance Manager | `finance_manager` |
| `registrar@test.com` | `test123` | Registrar | `registrar` |
| `academic_coordinator@test.com` | `test123` | Academic Coordinator | `academic_coordinator` |
| `clerk@test.com` | `test123` | Administrative Clerk | `clerk` |

### Role Display Mapping

The system maps Django groups to user-friendly role names:

```python
role_mapping = {
    'finance_manager': 'Finance Manager',
    'registrar': 'Registrar',
    'academic_coordinator': 'Academic Coordinator',
    'clerk': 'Administrative Clerk',
    'teacher': 'Teacher',
    'staff': 'Staff Member',
}
```

## Configuration

### Adding New Navigation Items

To add new navigation items, edit the `navigation_config` in `apps/common/context_processors.py`:

```python
{
    'label': _('New Section'),
    'icon': 'fas fa-new-icon',
    'order': 80,
    'children': [
        {
            'label': _('New Feature'),
            'url': 'app_name:view_name',
            'permission': 'app_name.view_model',
            'description': _('Description of new feature'),
        },
    ]
}
```

### Permission Requirements

**Navigation Item Options:**
- `permission` - Django permission string (e.g., `'app.view_model'`)
- `groups` - List of required group names
- `staff_required` - Boolean, requires `is_staff=True`
- `superuser_required` - Boolean, requires `is_superuser=True`
- `url_params` - Additional URL parameters (e.g., `'?status=pending'`)

### URL Configuration

Navigation URLs are generated using Django's `reverse()` function. Ensure all URLs in the navigation configuration are properly defined in your URLconf.

## Testing

### Manual Testing

1. **Start the development server:**
   ```bash
   docker compose -f docker-compose.local.yml up
   ```

2. **Visit the application:**
   - Go to http://localhost:8000
   - Login with any of the test user credentials
   - Observe role-specific navigation

3. **Test responsiveness:**
   - Resize browser window to test mobile layout
   - Verify hamburger menu functionality
   - Check sidebar collapsing behavior

### Automated Testing

Use the provided test script to verify context processor functionality:

```bash
docker compose -f docker-compose.local.yml run --rm django python manage.py shell -c "
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from apps.common.context_processors import navigation_context

# Test navigation context for different users
# (See scratchpad/simple_sidebar_test.py for full example)
"
```

## Troubleshooting

### Common Issues

1. **Navigation not appearing:**
   - Ensure template extends `base_with_sidebar.html`
   - Check that context processors are configured in `settings/base.py`
   - Verify user has required permissions

2. **Permission errors:**
   - Check that Django permissions exist for the specified models
   - Ensure users are assigned to correct groups
   - Verify permission strings match Django's format (`app.action_model`)

3. **Mobile layout issues:**
   - Ensure Tailwind CSS is loading properly
   - Check JavaScript console for mobile menu errors
   - Verify responsive CSS classes are applied

### Debug Information

The context processor provides debug information:
- `user_role_display` - Shows the detected user role
- `navigation` - Contains the filtered navigation structure

Add to templates for debugging:
```django
<!-- Debug Information -->
{% if user.is_superuser %}
<div class="debug-info">
    <p>Role: {{ user_role_display }}</p>
    <p>Groups: {{ user.groups.all|join:", " }}</p>
    <p>Navigation sections: {{ navigation|length }}</p>
</div>
{% endif %}
```

## Future Enhancements

### Planned Features

- **Dynamic Badge Counts** - Show notification counts on navigation items
- **Bookmarked Pages** - Allow users to bookmark frequently used pages
- **Recent Activity** - Show recently accessed pages in navigation
- **Custom User Preferences** - Allow users to customize sidebar layout

### Performance Optimizations

- **Caching** - Cache navigation structure for better performance
- **Lazy Loading** - Load navigation sections on demand
- **Permission Caching** - Cache permission checks for session duration

## Integration with Clean Architecture

The dynamic sidebar system follows the project's clean architecture principles:

- **Separation of Concerns** - Navigation logic is isolated in context processors
- **No Circular Dependencies** - Context processors don't depend on specific apps
- **Domain-Driven Design** - Navigation structure reflects business domains
- **Maintainable Code** - Easy to add new sections without touching existing code

## Security Considerations

- **Permission-Based Access** - All navigation items require appropriate permissions
- **Group Validation** - Group membership is verified at render time
- **URL Security** - Navigation URLs respect Django's permission decorators
- **Staff Protection** - Administrative functions require staff status

---

## Quick Reference

### Key Files
- `apps/common/context_processors.py` - Navigation logic
- `new_naga_sis_backend/templates/base_with_sidebar.html` - Sidebar template
- `config/settings/base.py` - Context processor configuration

### Key URLs
- http://localhost:8000 - Main application
- http://localhost:8000/admin/ - Django admin (staff required)

### Key Commands
```bash
# Start development server
docker compose -f docker-compose.local.yml up

# Test navigation context
docker compose -f docker-compose.local.yml run --rm django python manage.py shell

# View application logs
docker compose -f docker-compose.local.yml logs django
```

---

*Documentation generated for Naga SIS Version 1.0 - Dynamic Sidebar System*
*Last updated: June 15, 2025*