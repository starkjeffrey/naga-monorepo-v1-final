# Attendance App Documentation

## Overview

The `attendance` app is a comprehensive mobile-first attendance tracking system for the Naga Student Information System. It provides real-time attendance recording with geofencing validation, substitute teacher management, and configurable program-specific policies.

## Architecture

### Domain Position
- **Layer**: Business Logic Layer
- **Dependencies**: `scheduling` → `curriculum` + `people`, `enrollment`
- **Purpose**: Mobile-based attendance tracking and policy enforcement

### Key Features
1. **Mobile-First Design**: Teacher and student mobile app integration
2. **Geofencing Validation**: Location-based attendance verification
3. **Substitute Management**: Complete substitute teacher workflow
4. **Program-Specific Policies**: Configurable rules per academic program
5. **Multiple Fallbacks**: Manual entry and Django admin options

## Models

### AttendanceSettings
Program-specific attendance policies and configurations.

```python
# Example: IEAP program settings
ieap_settings = AttendanceSettings.objects.create(
    program=ieap_division,
    allows_permission_requests=False,  # IEAP doesn't allow excuses
    auto_approve_permissions=False,
    parent_notification_required=False,
    attendance_required_percentage=Decimal("80.00"),
    late_threshold_minutes=15,
    attendance_affects_grade=True,
    attendance_grade_weight=Decimal("0.100")  # 10% of grade
)
```

### AttendanceSession
Individual class session with teacher-generated attendance codes.

**Key Fields**:
- `attendance_code`: 5-character code (excludes confusing characters)
- `code_window_minutes`: How long code remains valid (default: 15)
- `geofence_radius_meters`: Location validation radius (default: 50)
- `is_substitute_session`: Whether taught by substitute teacher

**Substitute Management**:
```python
# Assign substitute teacher
session.assign_substitute(
    substitute_teacher=substitute_profile,
    reason="Regular teacher on sick leave",
    assigned_by=admin_user
)

# Remove substitute (return to regular teacher)
session.remove_substitute()
```

### AttendanceRecord
Individual student attendance records with comprehensive tracking.

**Status Options**:
- `PRESENT`: Student attended on time
- `ABSENT`: Student did not attend
- `LATE`: Student arrived after threshold
- `PERMISSION`: Excused absence

**Data Sources**:
- `MOBILE_CODE`: Student submitted code via app
- `MOBILE_MANUAL`: Teacher manual entry
- `DJANGO_MANUAL`: Admin entry
- `AUTO_ABSENT`: System default
- `PERMISSION_REQUEST`: Via permission system

### PermissionRequest
Student requests for excused absences with program-specific workflows.

**Program Policies**:
- **IEAP**: No permission requests allowed
- **High School**: Auto-approved with parent notification
- **BA/MA**: Requires teacher/admin approval

### RosterSync
Daily synchronization tracking with enrollment data.

**Sync Types**:
- `MIDNIGHT`: Automatic midnight sync
- `NOON`: Automatic noon sync
- `MANUAL`: On-demand sync

## Services

### RosterSyncService
Manages daily roster synchronization for mobile apps.

```python
# Run daily sync
result = RosterSyncService.sync_daily_rosters(sync_type="MIDNIGHT")
# Returns: {'success_count': 45, 'error_count': 2, 'total_classes': 47}
```

### AttendanceCodeService
Generates and validates attendance codes.

**Code Generation**:
- 6 characters (uppercase letters + digits)
- Excludes confusing characters (O, 0, I, 1)
- Ensures uniqueness among active sessions

```python
# Create session with backend-generated code
session = AttendanceCodeService.create_backend_generated_session(
    class_part=class_part,
    teacher_user=teacher.user,
    latitude=13.4123,
    longitude=103.8667
)

# Validate student submission
result = AttendanceCodeService.validate_student_code_submission(
    session=session,
    student_id=student.student_id,
    submitted_code="ABC123",
    latitude=13.4125,
    longitude=103.8665
)
```

### PermissionRequestService
Handles permission requests with program-specific policies.

```python
# Create permission request
result = PermissionRequestService.create_permission_request(
    student_id=123,
    class_part_id=456,
    session_date=date(2024, 7, 20),
    reason="Medical appointment"
)
```

### SubstituteTeacherService
Complete substitute teacher management workflow.

```python
# Create leave request
leave_result = SubstituteTeacherService.create_leave_request(
    teacher_id=teacher.id,
    leave_date=date(2024, 7, 15),
    leave_type="SICK",
    reason="Flu symptoms",
    is_emergency=True,
    affected_class_part_ids=[101, 102, 103]
)

# Find available substitutes
available_subs = SubstituteTeacherService.find_available_substitutes(
    leave_date=date(2024, 7, 15),
    required_qualifications=["BA_QUALIFIED"]
)

# Assign substitute
assign_result = SubstituteTeacherService.assign_substitute(
    leave_request_id=leave_result['leave_request_id'],
    substitute_teacher_id=substitute.id,
    assigned_by_user=admin_user
)

# Get statistics
stats = SubstituteTeacherService.get_substitute_statistics(
    start_date=date(2024, 7, 1),
    end_date=date(2024, 7, 31)
)
```

## API Endpoints

### Teacher Endpoints

#### Start Attendance Session
```
POST /api/attendance/teacher/start-session
{
    "class_part_id": 123,
    "latitude": 13.4123,
    "longitude": 103.8667,
    "is_makeup_class": false
}

Response:
{
    "id": 456,
    "attendance_code": "ABC123",
    "code_expires_at": "2024-07-15T09:20:00Z",
    "total_students": 25
}
```

#### Get Class Roster
```
GET /api/attendance/teacher/class-roster/{class_part_id}

Response:
{
    "class_part_id": 123,
    "total_students": 25,
    "students": [
        {
            "student_id": 1001,
            "student_name": "John Doe",
            "enrollment_status": "ENROLLED",
            "is_audit": false
        }
    ],
    "last_synced": "2024-07-15T00:00:00Z"
}
```

#### Manual Attendance Entry
```
POST /api/attendance/teacher/manual-attendance
{
    "session_id": 456,
    "student_id": 1001,
    "status": "PRESENT",
    "notes": "Arrived 5 minutes late"
}
```

### Student Endpoints

#### Submit Attendance Code
```
POST /api/attendance/student/submit-code
{
    "submitted_code": "ABC123",
    "latitude": 13.4125,
    "longitude": 103.8665
}

Response:
{
    "success": true,
    "status": "PRESENT",
    "message": "Attendance recorded as PRESENT",
    "within_geofence": true,
    "distance_meters": 25
}
```

#### Get Attendance Statistics
```
GET /api/attendance/student/my-attendance/{class_part_id}

Response:
{
    "total_sessions": 20,
    "present_sessions": 18,
    "absent_sessions": 1,
    "late_sessions": 1,
    "attendance_percentage": 95.0,
    "punctuality_percentage": 90.0
}
```

#### Request Permission
```
POST /api/attendance/student/request-permission
{
    "class_part_id": 123,
    "session_date": "2024-07-20",
    "reason": "Medical appointment at hospital"
}
```

### Admin Endpoints

#### List Attendance Sessions
```
GET /api/attendance/admin/sessions?limit=20&offset=0
```

#### Generate Attendance Report
```
GET /api/attendance/admin/attendance-report/{class_part_id}
    ?start_date=2024-07-01&end_date=2024-07-31

Response:
{
    "class_name": "ENG-101 Section A",
    "report_period": "2024-07-01 to 2024-07-31",
    "student_statistics": {
        "1001": {
            "student_name": "John Doe",
            "total_sessions": 15,
            "present": 14,
            "absent": 0,
            "late": 1,
            "attendance_percentage": 93.33
        }
    }
}
```

## Business Rules

### Attendance Code Validation
1. Code must match exactly (case-sensitive)
2. Submission must be within time window
3. Student must be enrolled in the class
4. Location validation if geofencing enabled

### Late Arrival Logic
- On-time: Submission within `late_threshold_minutes` of class start
- Late: Submission after threshold but within code window
- Absent: No submission or after code window expires

### Permission Request Workflow
1. **IEAP**: Requests blocked at creation
2. **High School**: Auto-approved, parents notified
3. **BA/MA**: Pending until teacher/admin approval

### Substitute Teacher Rules
1. Cannot be on leave themselves
2. Cannot already be assigned elsewhere
3. Original teacher permissions transfer to substitute
4. Attendance sessions update to show substitute

## Performance Optimizations

### Bulk Operations
```python
# Bulk create attendance records
attendance_records = []
for enrollment in enrollments:
    record = AttendanceRecord(
        attendance_session=session,
        student=enrollment.student,
        status=AttendanceRecord.AttendanceStatus.ABSENT,
        data_source=AttendanceRecord.DataSource.AUTO_ABSENT
    )
    attendance_records.append(record)

AttendanceRecord.objects.bulk_create(attendance_records, batch_size=50)
```

### Query Optimization
```python
# Optimized attendance summary query
summary = AttendanceRecord.objects.filter(
    attendance_session__class_part=class_part,
    attendance_session__session_date__range=date_range
).select_related(
    'student__person',
    'attendance_session'
).values(
    'student__id'
).annotate(
    total_sessions=Count('id'),
    present_count=Count(Case(When(status='PRESENT', then=1))),
    absent_count=Count(Case(When(status='ABSENT', then=1)))
)
```

## Configuration

### Settings
```python
# config/settings/base.py
NAGA_ATTENDANCE_CONFIG = {
    'GEOFENCE_DEFAULT_RADIUS': 50,        # meters
    'ATTENDANCE_GRACE_PERIOD': 15,        # minutes after session start
    'LATE_THRESHOLD_MINUTES': 10,         # when LATE becomes ABSENT
    'ABSENCE_WARNING_THRESHOLD': 3,       # absences before warning
    'MAXIMUM_DAILY_SESSIONS': 8,          # prevent abuse
    'LOCATION_ACCURACY_REQUIRED': 20      # meters GPS accuracy
}

NAGA_ABSENCE_POLICY = {
    'MAXIMUM_UNEXCUSED_ABSENCES': 5,
    'GRADE_REDUCTION_PER_EXCESS_ABSENCE': 2,  # percentage
    'AUTOMATIC_FAILURE_THRESHOLD': 10,
    'EXCUSED_ABSENCE_GRACE_DAYS': 2,
    'MEDICAL_EXCUSE_VALIDITY_DAYS': 30
}
```

## Integration Points

### With Grading App
```python
# Apply attendance penalties to final grades
if penalty_info['current_penalties']['grade_reduction_percentage'] > 0:
    GradingService.apply_attendance_penalty(
        student=student,
        class_part=class_part,
        penalty_percentage=penalty_info['current_penalties']['grade_reduction_percentage'],
        reason=f"Attendance policy violation: {penalty_info['total_absences']} absences"
    )
```

### With Notification System
```python
# Send attendance warnings
if absence_count >= 3:
    NotificationService.send_notification(
        recipient=student.person.user,
        notification_type='attendance_warning',
        title='Attendance Warning',
        message=f'You have {absence_count} absences. Please contact your instructor.',
        priority='high'
    )
```

### With External Systems
- **Moodle**: Attendance data export via RosterSync
- **Parent Portal**: Permission request notifications
- **Sponsor System**: Attendance reports for sponsored students

## Security Considerations

1. **Location Privacy**: GPS data retained only as needed
2. **Anti-Spoofing**: Multiple validation layers
3. **Audit Trail**: Complete history of all changes
4. **Role-Based Access**: Teachers can only modify their own sessions
5. **Code Security**: Cryptographically secure random generation

## Django Admin Interface

The attendance app provides comprehensive admin interfaces for managing all aspects of the attendance system.

### AttendanceSettingsAdmin
Manages program-specific attendance policies.

**Features**:
- Configure permission request policies per program
- Set attendance thresholds and grade impacts
- Define geofencing and code window defaults

### AttendanceSessionAdmin
Monitor and manage attendance sessions.

**Features**:
- View real-time attendance statistics
- Color-coded attendance summaries
- Inline attendance records
- Bulk update statistics
- Deactivate expired sessions

**Key Displays**:
- `attendance_summary`: Color-coded attendance percentage
- `code_status`: Shows if code is still active

### AttendanceRecordAdmin
Manage individual student attendance records.

**Features**:
- View submission details and timing
- Location validation status
- Manual status corrections
- Bulk approve permissions

**Actions**:
- Mark as Present/Absent
- Approve permission requests
- Update data source tracking

### PermissionRequestAdmin
Handle permission request workflows.

**Features**:
- Program-specific approval workflows
- Parent notification tracking
- Bulk approve/deny actions

### RosterSyncAdmin
Monitor enrollment synchronization.

**Features**:
- Track sync success/failure
- View enrollment snapshots
- Monitor roster changes

### AttendanceArchiveAdmin
View historical attendance data.

**Features**:
- Read-only archive interface
- Calculated attendance grades
- Compressed session details

## Testing

The app includes comprehensive test coverage for:

### API Tests (`test_api.py`)
- Teacher session creation with backend-generated codes
- Student code submission workflows
- Authentication and permissions
- Geofence validation

### Model Tests (`tests.py`)
- Attendance record creation and validation
- Permission request workflows
- Substitute teacher assignments
- Archive generation

### Test Utilities
```python
# Base test class with common setup
class AttendanceAPIBaseTest(TestCase):
    def setUp(self):
        # Creates admin, teacher, student users
        # Sets up courses, terms, enrollments
        # Configures test attendance sessions
```

## Management Commands

While no custom management commands are currently implemented, the following would be useful additions:

### Suggested Commands
```bash
# Process daily attendance reports
python manage.py process_attendance_reports --date=2024-07-15

# Archive completed term attendance
python manage.py archive_term_attendance --term=2024-SPRING

# Generate attendance warnings
python manage.py generate_attendance_warnings --threshold=3

# Import legacy attendance data
python manage.py import_legacy_attendance data/attendance.csv
```

## Future Enhancements

1. **Facial Recognition**: Automated student identification
2. **Bluetooth Beacons**: Enhanced indoor location accuracy
3. **Predictive Analytics**: Early intervention for at-risk students
4. **Wearable Integration**: Smartwatch attendance marking
5. **QR Code Support**: Alternative to manual code entry
6. **Voice Attendance**: Voice-activated attendance for accessibility
7. **Biometric Integration**: Fingerprint or face ID verification
8. **Real-time Dashboards**: WebSocket-based live attendance monitoring