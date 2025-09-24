"""Attendance tracking application.

This application provides comprehensive mobile-based attendance tracking with
geofence validation, substitute teacher management, and real-time roster
synchronization for the Naga Student Information System.

Core Components:
- Mobile Attendance: Code-based attendance submission with real-time validation
- Geofence Validation: Location-based attendance verification for integrity
- Roster Synchronization: Twice-daily sync with enrollment system for mobile apps
- Permission Requests: Program-specific excused absence workflows
- Substitute Management: Complete substitute teacher assignment and tracking
- Teacher Leave: Comprehensive leave request processing with automated coverage

Architecture:
- Mobile-first design optimized for teacher and student smartphone usage
- Real-time data synchronization ensuring mobile app accuracy
- Program-aware permission policies (IEAP strict, High School parent notification)
- Clean separation from scheduling while maintaining operational integration
- Comprehensive audit trail for attendance decisions and overrides

Key Models:
- AttendanceSession: Class sessions with unique attendance codes and geofence data
- AttendanceRecord: Individual student attendance with validation metadata
- RosterSync: Daily enrollment snapshots for mobile app synchronization
- PermissionRequest: Excused absence requests with program-specific workflows
- TeacherLeaveRequest: Leave management with substitute assignment tracking

Services:
- RosterSyncService: Automated roster synchronization (midnight/noon)
- AttendanceCodeService: Secure code generation and validation
- PermissionRequestService: Program-aware absence request processing
- SubstituteTeacherService: Complete substitute assignment workflow

Mobile Integration:
- Teacher mobile app: Session creation, manual attendance, roster access
- Student mobile app: Code submission, attendance status, permission requests
- Real-time validation with immediate feedback and error handling
- Offline capability with synchronization when connectivity restored
"""

default_app_config = "apps.attendance.apps.AttendanceConfig"
