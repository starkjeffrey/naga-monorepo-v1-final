# Attendance App

## Overview

The `attendance` app manages class attendance tracking with mobile app integration, geofencing validation, and comprehensive reporting for the Naga SIS. This business logic layer app provides real-time attendance recording, automated policy enforcement, and detailed analytics for academic and administrative purposes.

## Features

### Mobile-First Attendance Tracking

- **Teacher mobile app integration** with QR code scanning and geofencing
- **Student attendance verification** with proximity-based validation
- **Real-time attendance recording** with immediate synchronization
- **Offline capability** with sync when connection is restored

### Geofencing & Location Validation

- **Campus boundary enforcement** preventing remote attendance recording
- **Classroom-specific validation** ensuring attendance accuracy
- **GPS coordinate tracking** with privacy controls and data retention
- **Location spoofing prevention** with multiple validation layers

### Attendance Policies & Automation

- **Configurable attendance policies** with automatic enforcement
- **Absence penalty calculation** with progressive consequences
- **Excused absence management** with approval workflows
- **Attendance warning notifications** for at-risk students

### Comprehensive Reporting

- **Real-time attendance dashboards** for teachers and administrators
- **Student attendance patterns** with early intervention alerts
- **Class-level analytics** with participation trends
- **Academic impact correlation** linking attendance to performance

## Models

### Core Attendance

#### AttendanceSession

Scheduled attendance recording periods for class components.

```python
# Create attendance session for class
attendance_session = AttendanceSession.objects.create(
    class_part=speaking_class_part,
    session_date=date(2024, 7, 15),
    start_time=time(9, 0),
    end_time=time(10, 30),
    location_required=True,
    geofence_coordinates={
        "latitude": 13.4123,
        "longitude": 103.8667,
        "radius_meters": 50
    },
    status=SessionStatus.ACTIVE
)
```

#### AttendanceRecord

Individual student attendance records with comprehensive tracking.

```python
# Record student attendance
attendance_record = AttendanceRecord.objects.create(
    attendance_session=attendance_session,
    student=student_profile,
    status=AttendanceStatus.PRESENT,
    recorded_at=timezone.now(),
    recorded_by=teacher_user,
    location_data={
        "latitude": 13.4125,
        "longitude": 103.8665,
        "accuracy_meters": 5,
        "recorded_at": "2024-07-15T09:05:00Z"
    },
    recording_method=RecordingMethod.MOBILE_APP,
    device_info={
        "device_id": "teacher_phone_001",
        "app_version": "1.2.3",
        "platform": "iOS"
    }
)

# Handle late arrival
late_record = AttendanceRecord.objects.create(
    attendance_session=attendance_session,
    student=late_student,
    status=AttendanceStatus.LATE,
    recorded_at=timezone.now(),
    minutes_late=15,
    recorded_by=teacher_user,
    notes="Student arrived during discussion section"
)
```

### Permission & Excuse Management

#### PermissionRequest

Student requests for excused absences with approval workflow.

```python
# Student requests excused absence
permission_request = PermissionRequest.objects.create(
    student=student_profile,
    class_part=class_part,
    absence_date=date(2024, 7, 20),
    request_type=RequestType.MEDICAL,
    reason="Medical appointment",
    supporting_documents=["medical_note.pdf"],
    submitted_at=timezone.now(),
    status=RequestStatus.PENDING
)

# Teacher/admin approves request
permission_request.approve(
    approved_by=teacher_user,
    approval_notes="Valid medical documentation provided",
    approved_at=timezone.now()
)
```

### Integration Models

#### RosterSync

Synchronization tracking with external systems like Moodle.

```python
# Track Moodle attendance sync
roster_sync = RosterSync.objects.create(
    class_part=class_part,
    external_system=ExternalSystem.MOODLE,
    sync_type=SyncType.ATTENDANCE_EXPORT,
    sync_status=SyncStatus.IN_PROGRESS,
    records_processed=0,
    last_sync_date=timezone.now()
)

# Update sync progress
roster_sync.update_progress(
    records_processed=25,
    records_failed=2,
    status=SyncStatus.COMPLETED
)
```

## Services

### Attendance Service

Comprehensive attendance management with policy enforcement.

```python
from apps.attendance.services import AttendanceService

# Record attendance with validation
attendance_result = AttendanceService.record_attendance(
    teacher=teacher_profile,
    session=attendance_session,
    attendance_data=[
        {
            'student_id': 123,
            'status': 'present',
            'recorded_at': '2024-07-15T09:05:00Z',
            'location': {'lat': 13.4125, 'lng': 103.8665}
        },
        {
            'student_id': 124,
            'status': 'absent',
            'recorded_at': '2024-07-15T09:05:00Z'
        }
    ],
    validation_options={
        'check_geofence': True,
        'require_location': True,
        'validate_time_window': True
    }
)

# Returns validation results and created records
{
    'success': True,
    'records_created': 2,
    'validation_errors': [],
    'attendance_records': [attendance_record_1, attendance_record_2]
}
```

### Geofencing Service

Location validation and campus boundary enforcement.

```python
from apps.attendance.services import GeofencingService

# Validate attendance location
location_validation = GeofencingService.validate_attendance_location(
    latitude=13.4125,
    longitude=103.8665,
    class_part=class_part,
    recorded_at=timezone.now()
)

# Returns comprehensive validation result
{
    'is_valid': True,
    'within_campus': True,
    'within_classroom_radius': True,
    'distance_from_center': 12.5,  # meters
    'accuracy_sufficient': True,
    'validation_timestamp': '2024-07-15T09:05:00Z'
}
```

### Absence Policy Service

Automated attendance policy enforcement and penalty calculation.

```python
from apps.attendance.services import AbsencePolicyService

# Calculate absence penalties for student
penalty_calculation = AbsencePolicyService.calculate_penalties(
    student=student_profile,
    class_part=class_part,
    term=current_term
)

# Returns detailed penalty breakdown
{
    'total_absences': 8,
    'excused_absences': 2,
    'unexcused_absences': 6,
    'policy_violations': [
        {
            'violation_type': 'excessive_absences',
            'threshold': 5,
            'current_count': 6,
            'penalty': 'grade_reduction_5_percent'
        }
    ],
    'current_penalties': {
        'grade_reduction_percentage': 5,
        'warning_level': 'final_warning',
        'at_risk_status': True
    }
}
```

## Views & API

### Mobile Attendance API

RESTful API designed for mobile app integration.

```python
# Record attendance via mobile app
POST /api/attendance/sessions/{session_id}/record/
{
    "attendance_records": [
        {
            "student_id": 123,
            "status": "present",
            "location": {
                "latitude": 13.4125,
                "longitude": 103.8665,
                "accuracy": 5
            },
            "recorded_at": "2024-07-15T09:05:00Z"
        }
    ],
    "device_info": {
        "device_id": "teacher_phone_001",
        "app_version": "1.2.3",
        "platform": "iOS"
    }
}

# Response
{
    "success": true,
    "records_processed": 1,
    "validation_results": [
        {
            "student_id": 123,
            "status": "recorded",
            "validation_passed": true,
            "warnings": []
        }
    ],
    "session_summary": {
        "total_students": 25,
        "present": 23,
        "absent": 2,
        "late": 0
    }
}
```

### Attendance Dashboard

Real-time attendance monitoring for teachers and administrators.

```python
from apps.attendance.views import AttendanceDashboardView

class TeacherAttendanceDashboard(AttendanceDashboardView):
    template_name = 'attendance/teacher_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        teacher = self.request.user.teacher_profile

        context.update({
            'current_classes': self.get_teacher_current_classes(teacher),
            'today_sessions': self.get_today_sessions(teacher),
            'attendance_alerts': self.get_attendance_alerts(teacher),
            'weekly_summary': self.get_weekly_summary(teacher)
        })
        return context
```

## Management Commands

### Attendance Processing

```bash
# Process daily attendance and calculate penalties
python manage.py process_daily_attendance --date=2024-07-15

# Generate attendance warnings for at-risk students
python manage.py generate_attendance_warnings --term=current

# Sync attendance with external systems
python manage.py sync_attendance_external --system=moodle --term=current

# Import attendance from legacy system
python manage.py import_legacy_attendance --file=attendance.csv --validate
```

### Reports & Analytics

```bash
# Generate attendance reports
python manage.py generate_attendance_reports --term=current --format=pdf

# Calculate term attendance statistics
python manage.py calculate_attendance_stats --term=current

# Generate early intervention reports
python manage.py generate_intervention_reports --threshold=3-absences
```

## Integration Examples

### With Mobile App

```python
# Sync attendance session with mobile app
def sync_attendance_session_mobile(session_id):
    session = AttendanceSession.objects.get(id=session_id)

    # Prepare mobile app data
    mobile_data = {
        'session_id': session.id,
        'class_info': {
            'course_name': session.class_part.class_header.course.name,
            'section': session.class_part.class_header.section,
            'room': session.class_part.room.name if session.class_part.room else None
        },
        'students': [
            {
                'id': enrollment.student.id,
                'name': enrollment.student.person.full_name_eng,
                'photo_url': enrollment.student.person.photo_url
            }
            for enrollment in session.class_part.class_header.enrollments.all()
        ],
        'geofence': session.geofence_coordinates,
        'time_window': {
            'start': session.start_time,
            'end': session.end_time,
            'grace_period_minutes': 15
        }
    }

    return mobile_data
```

### With Grading App

```python
# Apply attendance penalties to grades
def apply_attendance_penalties_to_grades(student, class_part, term):
    from apps.grading.services import GradingService

    # Calculate attendance impact
    penalty_info = AbsencePolicyService.calculate_penalties(
        student=student,
        class_part=class_part,
        term=term
    )

    if penalty_info['current_penalties']['grade_reduction_percentage'] > 0:
        # Apply penalty to final grade
        GradingService.apply_attendance_penalty(
            student=student,
            class_part=class_part,
            penalty_percentage=penalty_info['current_penalties']['grade_reduction_percentage'],
            reason=f"Attendance policy violation: {penalty_info['total_absences']} absences"
        )
```

### With Notification System

```python
# Send attendance alerts
def send_attendance_alerts(student, absence_count):
    from apps.common.services import NotificationService

    if absence_count >= 3:
        # Alert student
        NotificationService.send_notification(
            recipient=student.person.user,
            notification_type='attendance_warning',
            title='Attendance Warning',
            message=f'You have {absence_count} absences. Please contact your instructor.',
            priority='high'
        )

        # Alert teacher
        for teacher in student.get_current_teachers():
            NotificationService.send_notification(
                recipient=teacher.user,
                notification_type='student_at_risk',
                title='Student Attendance Alert',
                message=f'{student.person.full_name_eng} has {absence_count} absences',
                priority='medium'
            )
```

## Validation & Business Rules

### Attendance Validation

```python
def validate_attendance_record(attendance_data, session):
    """Comprehensive attendance record validation."""
    errors = []

    # Time window validation
    now = timezone.now()
    session_start = datetime.combine(session.session_date, session.start_time)
    session_end = datetime.combine(session.session_date, session.end_time)

    if now < session_start - timedelta(minutes=15):
        errors.append("Cannot record attendance before session start time")

    if now > session_end + timedelta(hours=2):
        errors.append("Cannot record attendance more than 2 hours after session end")

    # Location validation
    if session.location_required and 'location' not in attendance_data:
        errors.append("Location data required for this session")

    if 'location' in attendance_data:
        location_valid = GeofencingService.validate_location(
            attendance_data['location'],
            session.geofence_coordinates
        )
        if not location_valid:
            errors.append("Location outside valid attendance area")

    # Student enrollment validation
    student_id = attendance_data['student_id']
    if not is_student_enrolled(student_id, session.class_part):
        errors.append("Student not enrolled in this class")

    return errors

def validate_geofence_coordinates(coordinates):
    """Validate geofence configuration."""
    required_fields = ['latitude', 'longitude', 'radius_meters']

    for field in required_fields:
        if field not in coordinates:
            raise ValidationError(f"Missing required geofence field: {field}")

    # Validate coordinate ranges
    lat, lng = coordinates['latitude'], coordinates['longitude']
    if not (-90 <= lat <= 90):
        raise ValidationError("Invalid latitude range")
    if not (-180 <= lng <= 180):
        raise ValidationError("Invalid longitude range")

    # Validate radius
    radius = coordinates['radius_meters']
    if not (10 <= radius <= 1000):
        raise ValidationError("Radius must be between 10 and 1000 meters")
```

## Testing

### Test Coverage

```bash
# Run attendance app tests
pytest apps/attendance/

# Test specific functionality
pytest apps/attendance/test_api.py
pytest apps/attendance/tests/test_geofencing.py
pytest apps/attendance/tests/test_mobile_integration.py
```

### Test Factories

```python
from apps.attendance.tests.factories import (
    AttendanceSessionFactory,
    AttendanceRecordFactory,
    PermissionRequestFactory
)

# Create test attendance data
session = AttendanceSessionFactory(
    class_part__class_header__course__name="Test Course",
    location_required=True
)

attendance_record = AttendanceRecordFactory(
    attendance_session=session,
    status=AttendanceStatus.PRESENT
)
```

## Performance Optimization

### Bulk Attendance Recording

```python
def bulk_record_attendance(session, attendance_data_list):
    """Efficiently record attendance for multiple students."""
    # Validate all records first
    validation_errors = []
    for data in attendance_data_list:
        errors = validate_attendance_record(data, session)
        if errors:
            validation_errors.extend(errors)

    if validation_errors:
        raise ValidationError(validation_errors)

    # Bulk create attendance records
    attendance_records = []
    for data in attendance_data_list:
        record = AttendanceRecord(
            attendance_session=session,
            student_id=data['student_id'],
            status=data['status'],
            recorded_at=timezone.now(),
            location_data=data.get('location'),
            recording_method=RecordingMethod.MOBILE_APP
        )
        attendance_records.append(record)

    # Bulk create for performance
    AttendanceRecord.objects.bulk_create(attendance_records, batch_size=50)

    return attendance_records
```

### Query Optimization

```python
def get_attendance_summary_optimized(class_part, date_range):
    """Optimized attendance summary queries."""
    return AttendanceRecord.objects.filter(
        attendance_session__class_part=class_part,
        attendance_session__session_date__range=date_range
    ).select_related(
        'student__person',
        'attendance_session'
    ).values(
        'student__id',
        'student__person__first_name_eng',
        'student__person__last_name_eng'
    ).annotate(
        total_sessions=Count('attendance_session', distinct=True),
        present_count=Count(Case(When(status='present', then=1))),
        absent_count=Count(Case(When(status='absent', then=1))),
        late_count=Count(Case(When(status='late', then=1)))
    )
```

## Configuration

### Settings

```python
# Attendance configuration
NAGA_ATTENDANCE_CONFIG = {
    'GEOFENCE_DEFAULT_RADIUS': 50,  # meters
    'ATTENDANCE_GRACE_PERIOD': 15,  # minutes after session start
    'LATE_THRESHOLD_MINUTES': 10,   # minutes to be considered late
    'ABSENCE_WARNING_THRESHOLD': 3, # absences before warning
    'MAXIMUM_DAILY_SESSIONS': 8,    # sessions per day limit
    'LOCATION_ACCURACY_REQUIRED': 20  # meters
}

# Absence policy
NAGA_ABSENCE_POLICY = {
    'MAXIMUM_UNEXCUSED_ABSENCES': 5,
    'GRADE_REDUCTION_PER_EXCESS_ABSENCE': 2,  # percentage
    'AUTOMATIC_FAILURE_THRESHOLD': 10,  # absences
    'EXCUSED_ABSENCE_GRACE_DAYS': 2,    # days to submit excuse
    'MEDICAL_EXCUSE_VALIDITY_DAYS': 30  # days medical excuse valid
}
```

## Dependencies

### Internal Dependencies

- `scheduling`: Class part and session information
- `people`: Student and teacher profiles
- `enrollment`: Student enrollment verification
- `common`: Base models and audit framework

### External Dependencies

- `geopandas`: Geographic calculations (optional)
- `geopy`: Distance and location calculations
- `django-rest-framework`: API framework for mobile integration

## Architecture Notes

### Design Principles

- **Mobile-first**: Designed for teacher mobile app integration
- **Real-time**: Immediate attendance recording and validation
- **Policy-driven**: Configurable attendance policies and enforcement
- **Location-aware**: Geofencing and campus boundary enforcement

### Security Considerations

- **Location privacy**: GPS data retention policies and anonymization
- **Anti-spoofing**: Multiple validation layers for location accuracy
- **Audit trail**: Complete tracking of all attendance modifications
- **Role-based access**: Appropriate permissions for different user types

### Future Enhancements

- **Facial recognition**: Automated student identification
- **Bluetooth beacons**: Enhanced location accuracy indoors
- **Predictive analytics**: Early intervention for at-risk students
- **Wearable integration**: Smartwatch and fitness tracker compatibility
