# Scheduling App

## Overview

The `scheduling` app manages operational class scheduling, room assignments, session organization, and teacher allocations for the Naga SIS. This domain layer app transforms curriculum templates into actual scheduled classes that students can enroll in and teachers can deliver.

## Features

### Class Scheduling & Management

- **Class header creation** from curriculum course templates
- **Section management** with multiple sections per course
- **Teacher assignments** with primary and assistant teachers
- **Room allocation** with capacity and resource validation

### Session Organization

- **Class session grouping** for IEAP (Intensive English for Academic Purposes)
- **Combined class management** for administrative grouping
- **Session enrollment** supporting program-specific requirements
- **Flexible scheduling** for intensive and regular programs

### Specialized Class Types

- **Reading classes** with tiered level management
- **Language classes** with progression tracking
- **Combined classes** for cross-program coordination
- **Test period management** with absence penalty resets

### Operational Support

- **Capacity management** with enrollment limits
- **Schedule conflict detection** and resolution
- **Resource allocation** (rooms, equipment, teachers)
- **Academic calendar integration** with term-based scheduling

## Models

### Core Scheduling

#### ClassHeader

The primary scheduled class entity representing a course offering in a specific term.

```python
# Create a scheduled class
class_header = ClassHeader.objects.create(
    course=english_101,
    term=fall_2024,
    section="A",
    capacity=25,
    class_type=ClassType.ACADEMIC,
    status=ClassStatus.ACTIVE
)

# Add teacher assignment
ClassHeaderTeacher.objects.create(
    class_header=class_header,
    teacher=teacher_profile,
    role=TeacherRole.PRIMARY
)
```

#### ClassPart

Individual components of a class (lectures, labs, exams, etc.).

```python
# Create class components from template
for template in course.course_part_templates.all():
    class_part = ClassPart.objects.create(
        class_header=class_header,
        template=template,
        name=template.part_name,
        weight=template.weight,
        max_score=template.max_score or 100
    )

    # Assign teacher and room
    class_part.teacher = primary_teacher
    class_part.room = assigned_room
    class_part.save()
```

### Session Management

#### ClassSession

Groups related classes for intensive programs like IEAP.

```python
# Create IEAP session grouping
session = ClassSession.objects.create(
    name="IEAP Fall 2024 - Group 1",
    term=fall_2024,
    session_type=SessionType.IEAP,
    start_date=date(2024, 8, 1),
    end_date=date(2024, 12, 15)
)

# Add classes to session
session.class_headers.add(speaking_class, listening_class, reading_class)
```

#### CombinedClassGroup

Administrative grouping of classes for management purposes.

```python
# Group related classes for administration
combined_group = CombinedClassGroup.objects.create(
    name="Business English Cluster",
    description="All business-focused English classes",
    term=fall_2024
)

combined_group.class_headers.add(
    business_english_1,
    business_english_2,
    business_writing
)
```

### Specialized Classes

#### ReadingClass

Tiered reading classes with level-based organization.

```python
# Create tiered reading class
reading_class = ReadingClass.objects.create(
    class_header=reading_101,
    tier_name="Advanced Reading",
    level=ReadingLevel.ADVANCED,
    max_students_per_tier=15,
    is_placement_based=True
)

# Students are placed based on placement test results
ReadingClassStudent.objects.create(
    reading_class=reading_class,
    student=student_profile,
    placement_score=85,
    tier_assignment="Tier 1"
)
```

#### TestPeriodReset

Manages absence penalty resets for academic integrity.

```python
# Reset absence penalties for test period
reset = TestPeriodReset.objects.create(
    class_header=class_header,
    reset_date=date(2024, 10, 15),
    reason="Midterm examination period",
    applied_by=academic_admin,
    affected_students_count=23
)
```

## Services

### Scheduling Service

Comprehensive class scheduling with validation and conflict detection.

```python
from apps.scheduling.services import SchedulingService

# Create class from course template
class_data = {
    'course': course,
    'term': term,
    'section': 'A',
    'capacity': 25,
    'teacher': primary_teacher,
    'room': classroom_101
}

class_header = SchedulingService.create_class_from_template(class_data)

# Check for scheduling conflicts
conflicts = SchedulingService.check_scheduling_conflicts(
    teacher=teacher,
    room=room,
    time_slot=proposed_time
)
```

### Session Service

Session management for intensive programs.

```python
from apps.scheduling.services import SessionService

# Create IEAP session with multiple classes
session_data = {
    'name': 'IEAP Fall 2024 - Group 1',
    'term': fall_2024,
    'classes': [
        {'course': 'GESL-01', 'teacher': teacher1},
        {'course': 'GESL-02', 'teacher': teacher2},
        {'course': 'GESL-03', 'teacher': teacher3}
    ]
}

session = SessionService.create_ieap_session(session_data)
```

### Capacity Service

Enrollment capacity management with waitlist support.

```python
from apps.scheduling.services import CapacityService

# Check enrollment capacity
capacity_info = CapacityService.get_capacity_status(class_header)
# Returns: {
#     'total_capacity': 25,
#     'enrolled_count': 23,
#     'available_spots': 2,
#     'waitlist_count': 5,
#     'can_enroll': True
# }

# Update capacity with validation
CapacityService.update_class_capacity(
    class_header=class_header,
    new_capacity=30,
    reason="Room change to larger classroom"
)
```

## Views & Templates

### Class Management Views

```python
from apps.scheduling.views import ClassHeaderListView

class TeacherClassListView(ClassHeaderListView):
    """Classes assigned to logged-in teacher."""
    template_name = 'scheduling/teacher_classes.html'

    def get_queryset(self):
        return ClassHeader.objects.filter(
            classheaderteacher__teacher__user=self.request.user,
            term__is_current=True
        ).select_related('course', 'term').prefetch_related(
            'classheaderteacher_set__teacher'
        )
```

### Schedule Display

```python
# Weekly schedule view
def weekly_schedule(request, week_start):
    schedule_data = SchedulingService.get_weekly_schedule(
        week_start=week_start,
        teacher=request.user.teacher_profile
    )

    return render(request, 'scheduling/weekly_schedule.html', {
        'schedule': schedule_data,
        'week_start': week_start
    })
```

## Management Commands

### Class Creation

```bash
# Create classes from course templates
python manage.py create_classes_from_templates --term=fall2024 --program=bachelor

# Import class schedules from external system
python manage.py import_class_schedules --file=schedule.csv --validate

# Generate IEAP sessions automatically
python manage.py generate_ieap_sessions --term=fall2024 --groups=4
```

### Schedule Management

```bash
# Validate all schedules for conflicts
python manage.py validate_schedules --term=current --fix-conflicts

# Optimize room assignments
python manage.py optimize_room_assignments --term=fall2024

# Generate schedule reports
python manage.py generate_schedule_reports --format=pdf --email=admin@pucsr.edu.kh
```

## API Endpoints

### Class Schedule API

```python
# Get class schedule for term
GET /api/scheduling/classes/?term=fall2024&teacher={teacher_id}

{
    "classes": [
        {
            "id": 123,
            "course": {
                "code": "GESL-01",
                "name": "General English Skills Level 1"
            },
            "section": "A",
            "term": "Fall 2024",
            "capacity": 25,
            "enrolled_count": 23,
            "schedule": {
                "days": ["Monday", "Wednesday", "Friday"],
                "time": "09:00-10:30",
                "room": "Room 101"
            },
            "teachers": [
                {
                    "name": "Dr. Smith",
                    "role": "primary"
                }
            ]
        }
    ]
}
```

### Session Management API

```python
# Get IEAP session information
GET /api/scheduling/sessions/{session_id}/

{
    "id": 1,
    "name": "IEAP Fall 2024 - Group 1",
    "type": "ieap",
    "term": "Fall 2024",
    "dates": {
        "start": "2024-08-01",
        "end": "2024-12-15"
    },
    "classes": [
        {
            "course_code": "GESL-01",
            "section": "A",
            "teacher": "Dr. Smith",
            "room": "Room 101"
        }
    ],
    "enrollment_count": 20,
    "capacity": 25
}
```

## Integration Examples

### With Enrollment App

```python
# Check enrollment eligibility considering capacity
def can_enroll_student(student, class_header):
    from apps.enrollment.services import EnrollmentService

    # Check academic eligibility
    academic_eligible = EnrollmentService.check_academic_eligibility(
        student, class_header.course
    )

    # Check capacity availability
    capacity_available = CapacityService.has_capacity(class_header)

    # Check prerequisite completion
    prereqs_met = EnrollmentService.check_prerequisites(
        student, class_header.course
    )

    return academic_eligible and capacity_available and prereqs_met
```

### With Attendance App

```python
# Create attendance sessions for all class parts
def setup_attendance_tracking(class_header):
    from apps.attendance.services import AttendanceService

    for class_part in class_header.class_parts.all():
        if class_part.requires_attendance:
            AttendanceService.create_attendance_session(
                class_part=class_part,
                session_date=class_part.scheduled_date,
                duration_minutes=class_part.duration
            )
```

### With Grading App

```python
# Setup grade structure from class parts
def initialize_grade_structure(class_header):
    from apps.grading.services import GradingService

    for enrollment in class_header.enrollments.all():
        for class_part in class_header.class_parts.all():
            GradingService.create_grade_placeholder(
                enrollment=enrollment,
                class_part=class_part,
                max_score=class_part.max_score,
                weight=class_part.weight
            )
```

## Validation & Business Rules

### Scheduling Validation

```python
def validate_class_schedule(class_header):
    """Comprehensive schedule validation."""
    errors = []

    # Check teacher availability
    teacher_conflicts = check_teacher_conflicts(
        class_header.teachers.all(),
        class_header.scheduled_times.all()
    )
    if teacher_conflicts:
        errors.extend(teacher_conflicts)

    # Check room availability
    room_conflicts = check_room_conflicts(
        class_header.room,
        class_header.scheduled_times.all()
    )
    if room_conflicts:
        errors.extend(room_conflicts)

    # Validate capacity vs room size
    if class_header.capacity > class_header.room.capacity:
        errors.append("Class capacity exceeds room capacity")

    return errors
```

### Session Validation

```python
def validate_ieap_session(session):
    """Validate IEAP session requirements."""
    required_courses = ['GESL-01', 'GESL-02', 'GESL-03', 'GESL-04']
    session_courses = [
        ch.course.code for ch in session.class_headers.all()
    ]

    missing_courses = set(required_courses) - set(session_courses)
    if missing_courses:
        raise ValidationError(
            f"IEAP session missing required courses: {missing_courses}"
        )

    # Validate date alignment
    for class_header in session.class_headers.all():
        if not (session.start_date <= class_header.start_date <= session.end_date):
            raise ValidationError(
                f"Class {class_header} dates outside session period"
            )
```

## Performance Optimization

### Query Optimization

```python
# Efficient schedule loading with relationships
def get_teacher_schedule(teacher, term):
    return ClassHeader.objects.filter(
        classheaderteacher__teacher=teacher,
        term=term
    ).select_related(
        'course', 'term', 'room'
    ).prefetch_related(
        'class_parts__teacher',
        'classheaderteacher_set__teacher',
        'enrollments__student'
    )
```

### Caching Strategy

```python
from django.core.cache import cache

def get_room_schedule(room, date_range):
    """Cached room schedule for performance."""
    cache_key = f"room_schedule_{room.id}_{date_range[0]}_{date_range[1]}"
    schedule = cache.get(cache_key)

    if not schedule:
        schedule = SchedulingService.build_room_schedule(room, date_range)
        cache.set(cache_key, schedule, 900)  # 15 minutes

    return schedule
```

## Testing

### Test Coverage

```bash
# Run scheduling app tests
pytest apps/scheduling/

# Test specific functionality
pytest apps/scheduling/tests/test_capacity_management.py
pytest apps/scheduling/tests/test_schedule_conflicts.py
pytest apps/scheduling/tests/test_ieap_sessions.py
```

### Test Factories

```python
from apps.scheduling.tests.factories import (
    ClassHeaderFactory,
    ClassPartFactory,
    ClassSessionFactory,
    ReadingClassFactory
)

# Create test scheduling data
class_header = ClassHeaderFactory(
    course__code="TEST-101",
    capacity=25
)

class_part = ClassPartFactory(
    class_header=class_header,
    name="Midterm Exam",
    weight=Decimal("0.30")
)
```

## Configuration

### Settings

```python
# Scheduling configuration
NAGA_SCHEDULING_CONFIG = {
    'DEFAULT_CLASS_CAPACITY': 25,
    'MAX_CAPACITY_PER_CLASS': 40,
    'IEAP_SESSION_REQUIRED_COURSES': ['GESL-01', 'GESL-02', 'GESL-03', 'GESL-04'],
    'ALLOW_TEACHER_OVERLOAD': False,
    'MAX_CLASSES_PER_TEACHER_PER_TERM': 6,
    'ROOM_BUFFER_MINUTES': 15  # Buffer between classes
}

# Reading class configuration
NAGA_READING_CLASS_CONFIG = {
    'MAX_TIERS': 3,
    'PLACEMENT_SCORE_RANGES': {
        'TIER_1': (80, 100),
        'TIER_2': (60, 79),
        'TIER_3': (0, 59)
    }
}
```

## Security & Access Control

### Schedule Management Authorization

```python
from apps.accounts.decorators import require_permission

@require_permission('scheduling.manage_classes')
def create_class_header(request):
    """Create new class - requires scheduling permission."""
    pass

@require_permission('scheduling.assign_teachers')
def assign_teacher_to_class(request, class_id, teacher_id):
    """Assign teacher - requires teacher assignment permission."""
    pass
```

## Dependencies

### Internal Dependencies

- `curriculum`: Course templates and term definitions
- `people`: Teacher and staff profiles
- `common`: Room management and audit framework

### External Dependencies

- No external dependencies required

## Architecture Notes

### Design Principles

- **Domain layer focus**: Operational scheduling without business logic
- **Template-driven creation**: Classes created from curriculum templates
- **Flexible session management**: Support for various program types
- **Capacity management**: Enrollment limits with waitlist support

### Key Relationships

- **ClassHeader** is the central scheduling entity
- **ClassPart** provides component-level granularity
- **ClassSession** groups classes for intensive programs
- **Teacher assignments** support multiple teachers per class

### Future Enhancements

- **Automated scheduling**: AI-powered optimal schedule generation
- **Resource optimization**: Advanced room and teacher allocation
- **Mobile scheduling**: Teacher mobile app for schedule management
- **Integration APIs**: External calendar system synchronization

## UI/UX Implementation (July 2024)

### Overview

A modern, HTMX-powered user interface has been designed and partially implemented for the scheduling app. This provides a responsive, real-time interface for managing classes, enrollments, and schedules.

### Implementation Status

- ✅ **Design Documentation**: Complete UI/UX design in `SCHEDULING_DESIGN.md`
- ✅ **Component Library**: Reusable TailwindCSS components created
- ✅ **Base Templates**: Scheduling-specific layout templates
- ✅ **URL Structure**: Basic URL routing configured
- ✅ **Template Integration**: Hooked into main base.html navigation
- ⏳ **Views**: Placeholder views created, full implementation pending
- ⏳ **HTMX Endpoints**: API endpoints for dynamic updates pending

### Key UI Features

1. **Dashboard View**: Quick overview with summary cards and recent classes
2. **Class Management**: Searchable, filterable table with inline editing
3. **Enrollment Widget**: Real-time student enrollment interface
4. **Schedule Visualization**: Weekly calendar view with conflict detection
5. **Mobile Responsive**: Adaptive layouts for all screen sizes

### Templates Created

- `templates/scheduling/base_scheduling.html` - Base layout for scheduling pages
- `templates/scheduling/dashboard.html` - Main dashboard interface
- `templates/scheduling/class_list.html` - Class listing with filters
- `templates/scheduling/class_detail.html` - Detailed class view
- `templates/scheduling/components/*.html` - Reusable UI components

### Component Library

Located in `templates/components/`:

- `card.html` - Flexible card component with variants
- `modal.html` - HTMX-powered modal dialogs
- `alerts.html` - Alert messages with auto-dismiss
- `data_table.html` - Responsive data table with sorting

### Template Tags

Custom filters in `templatetags/scheduling_extras.py`:

- `lookup` - Dynamic attribute access
- `mul`, `div` - Mathematical operations
- `get_item` - Dictionary access with variable keys

### HTMX Integration

The interface uses HTMX for seamless interactions:

- Real-time search and filtering
- Modal loading for quick views
- Inline editing without page refresh
- Live enrollment updates
- Automatic CSRF token handling

### Next Steps

See `SYSTEM_CHANGES_NEEDED.md` for the backend implementation requirements to complete the UI functionality.
