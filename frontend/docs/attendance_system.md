# Attendance System Documentation

## Overview

The attendance system is a comprehensive mobile-first solution designed for educational institutions. It follows clean architecture principles and integrates seamlessly with the enrollment and scheduling systems.

## Architecture

### Clean Dependencies
- **attendance** → **scheduling** → **curriculum** + **people**
- No circular dependencies
- Single responsibility per app
- Well-defined interfaces between apps

### Key Components

1. **Models** (`apps/attendance/models.py`)
   - `AttendanceSettings`: Program-specific policies and configurations
   - `AttendanceSession`: Individual class sessions with teacher-generated codes
   - `AttendanceRecord`: Student attendance records with validation details
   - `PermissionRequest`: Excused absence requests with approval workflows
   - `RosterSync`: Daily enrollment synchronization for mobile apps
   - `AttendanceArchive`: Historical attendance data for completed terms

2. **Services** (`apps/attendance/services.py`)
   - `RosterSyncService`: Daily roster synchronization (midnight/noon)
   - `AttendanceCodeService`: Code validation and session management
   - `PermissionRequestService`: Permission request handling with program policies

3. **API Endpoints** (`apps/attendance/api.py`)
   - Teacher endpoints: session creation, roster access, manual entry
   - Student endpoints: code submission, attendance statistics
   - Admin endpoints: reporting, management, roster sync

4. **Admin Interface** (`apps/attendance/admin.py`)
   - Comprehensive Django admin with statistics and bulk actions
   - Attendance monitoring and troubleshooting tools
   - Permission request approval workflows

## Key Features

### Mobile-First Design
- Teachers generate 5-digit codes using mobile apps
- Students submit codes through mobile apps
- Django serves as data warehouse and API backend
- Multiple fallback options for reliability

### Geofencing & Validation
- GPS location validation for attendance integrity
- Configurable geofence radius per session
- Distance tracking for audit purposes
- Real-time code validation with time windows

### Program-Specific Policies
- **IEAP**: No permission requests allowed
- **High School**: Auto-approved permissions with parent notification
- **BA/MA**: Teacher/admin approval required for permissions

### Attendance Statuses
- **PRESENT**: Student attended on time
- **LATE**: Student arrived after threshold (configurable)
- **ABSENT**: Student did not attend
- **PERMISSION**: Excused absence with approval

### Data Sources
- **MOBILE_CODE**: Student code submission via mobile app
- **MOBILE_MANUAL**: Teacher manual entry via mobile app
- **DJANGO_MANUAL**: Admin entry via Django interface
- **AUTO_ABSENT**: Automatically marked absent initially
- **PERMISSION_REQUEST**: Through permission request system

### Roster Synchronization
- Daily sync at midnight and noon
- Handles enrollment changes throughout the term
- Provides current student lists to mobile apps
- Change tracking and audit trails

## API Endpoints

### Teacher Endpoints
- `POST /api/attendance/teacher/start-session/` - Start attendance session
- `GET /api/attendance/teacher/class-roster/{id}/` - Get class roster
- `POST /api/attendance/teacher/manual-attendance/` - Manual attendance entry
- `POST /api/attendance/teacher/end-session/{id}/` - End attendance session

### Student Endpoints
- `POST /api/attendance/student/submit-code/` - Submit attendance code
- `GET /api/attendance/student/my-attendance/{id}/` - Get attendance statistics
- `POST /api/attendance/student/request-permission/` - Request excused absence

### Admin Endpoints
- `GET /api/attendance/admin/sessions/` - List all sessions (paginated)
- `GET /api/attendance/admin/attendance-report/{id}/` - Generate reports
- `POST /api/attendance/admin/sync-rosters/` - Manual roster sync

## Database Schema

### Key Relationships
- AttendanceSession → ClassPart (scheduling)
- AttendanceRecord → AttendanceSession + StudentProfile (people)
- PermissionRequest → StudentProfile + ClassPart
- RosterSync → ClassPart
- AttendanceSettings → Division (curriculum)

### Indexing Strategy
- Optimized for date-based queries
- Student and class lookups
- Status filtering and reporting

## Integration Points

### With Enrollment System
- Daily roster synchronization
- Enrollment status validation
- Student enrollment changes

### With Scheduling System
- Class session integration
- Teacher assignment validation
- Room and time information

### With People System
- Student and teacher profiles
- Contact information for notifications
- Role-based permissions

### External Systems (Future)
- **Moodle**: Attendance grade synchronization
- **Parent Portal**: High school notifications
- **Sponsor Reporting**: Monthly attendance reports
- **Mobile Apps**: Real-time data exchange

## Deployment Notes

### Dependencies
- Django 5.2+
- django-ninja for API
- geopy for geofencing (to be installed)
- PostgreSQL for data storage

### Configuration
- Attendance policies per program in AttendanceSettings
- Geofence radius and code windows configurable
- Grade weight settings for different programs

### Monitoring
- Comprehensive admin interface for monitoring
- Roster sync success/failure tracking
- Attendance statistics and reporting
- API endpoint monitoring

## Future Enhancements

1. **Geofencing**: Install geopy dependency for location validation
2. **Statistics Dashboard**: Web-based dashboard for management
3. **External Integrations**: Moodle, parent portal, sponsor reporting
4. **Mobile Apps**: Dedicated iOS/Android applications
5. **Advanced Analytics**: Attendance patterns and insights
6. **Notification System**: Automated alerts for absences

## Testing

The system includes comprehensive test coverage for:
- Model validation and business rules
- API endpoint functionality
- Service layer business logic
- Admin interface operations
- Integration with other apps

## Security Considerations

- Role-based access control for API endpoints
- Audit trails for all attendance modifications
- Secure code generation and validation
- Location data privacy and retention policies