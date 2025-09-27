# Student Profile UI Design

## Overview
This is a modern, flexible student profile interface design using Django templates with HTMX and Tailwind CSS. The design follows current UI/UX best practices for student information systems.

## Design Features

### 1. Student Header Card
- **Photo Display**: Shows current student photo with update indicator
- **Basic Info**: Name, ID, email, phone
- **Status Badges**: Active/Inactive, Monk status, Transfer student
- **Quick Stats**: GPA, Credits, Current Term, Major

### 2. Vertical Tab Navigation
- **Left-side tabs** for better scalability (can handle 10+ sections)
- **Icon + Label** format for clarity
- **Notification badges** on tabs (e.g., "3" for enrollments, "!" for finance alerts)
- **HTMX-powered** for smooth transitions without page reloads

### 3. Tab Sections
1. **Overview**: Current enrollment, academic progress, recent activity
2. **Demographics**: Personal info, contact details, emergency contacts
3. **Academic**: Major history, degree progress, requirements
4. **Enrollment**: Current and past course enrollments
5. **Grades**: Grade history, GPA trends, transcripts
6. **Attendance**: Attendance records and patterns
7. **Finance**: Account balance, payments, scholarships
8. **Documents**: Official documents, forms, uploads
9. **Activity Log**: Audit trail of all changes

### 4. Modern UI Elements
- **Cards**: Clean white/dark mode cards for content grouping
- **Progress Bars**: Visual degree completion tracking
- **Status Badges**: Color-coded status indicators
- **Responsive Grid**: Adapts from mobile to desktop
- **Dark Mode Support**: Full dark mode compatibility

## Implementation Guide

### File Structure
```
apps/people/templates/people/
├── student_profile_mockup.html    # Main template with navigation
├── partials/
│   ├── tab_overview.html         # Overview tab content
│   ├── tab_demographics.html     # Demographics tab (example provided)
│   ├── tab_academic.html         # Academic tab content
│   ├── tab_enrollment.html       # Enrollment tab content
│   ├── tab_grades.html          # Grades tab content
│   ├── tab_attendance.html      # Attendance tab content
│   ├── tab_finance.html         # Finance tab content
│   ├── tab_documents.html       # Documents tab content
│   └── tab_activity.html        # Activity log tab content
```

### URL Configuration
Add to `apps/people/urls.py`:
```python
urlpatterns = [
    path('student/<int:pk>/', StudentProfileView.as_view(), name='student-profile'),
    path('student/<int:pk>/tab/<str:tab>/', StudentProfileTabView.as_view(), name='student-profile-tab'),
]
```

### View Implementation
```python
class StudentProfileView(DetailView):
    model = StudentProfile
    template_name = 'people/student_profile_mockup.html'
    context_object_name = 'student'

class StudentProfileTabView(DetailView):
    model = StudentProfile
    context_object_name = 'student'
    
    def get_template_names(self):
        tab = self.kwargs.get('tab', 'overview')
        return [f'people/partials/tab_{tab}.html']
```

### HTMX Integration
- Each tab button uses `hx-get` to load content
- Content loads into `#tab-content` div
- Loading indicator shows during requests
- URL updates without page reload for bookmarking

### Customization Options

#### Adding New Tabs
1. Add button to vertical navigation
2. Create partial template in `partials/` directory
3. Update view to handle new tab name

#### Modifying Layout
- Change from vertical to horizontal tabs by adjusting flexbox classes
- Adjust card spacing and padding through Tailwind utilities
- Customize color scheme through CSS variables

#### Data Integration
- Connect to existing models (Person, StudentProfile, etc.)
- Add real-time data updates with HTMX polling
- Implement search/filter functionality within tabs

## Benefits

1. **Scalable**: Vertical tabs can handle many sections without UI breaking
2. **Fast**: HTMX loads only needed content, reducing page weight
3. **Flexible**: Easy to add/remove/modify sections
4. **Modern**: Follows 2024 UI patterns and best practices
5. **Accessible**: Semantic HTML with ARIA attributes
6. **Responsive**: Works on all device sizes

## Next Steps

1. Review the mockup at `/people/student/[id]/` 
2. Provide feedback on layout and sections
3. Implement remaining tab partials
4. Add real data connections
5. Implement permission checks
6. Add print-friendly views