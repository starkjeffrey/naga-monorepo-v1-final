# Attendance API - Complete Endpoint Reference

## Base URL: `/api/attendance/`

---

## 👨‍🏫 Teacher Endpoints

### 1. Start Attendance Session
**POST** `/teacher/start-session`

Creates a new attendance session with a generated code for students.

**Request Body:**
```json
{
  "class_part_id": 123,
  "attendance_code": "ABC123",
  "latitude": 11.5564,
  "longitude": 104.9282,
  "is_makeup_class": false,
  "makeup_reason": "Weather cancellation"
}
```

**Response:**
```json
{
  "id": 456,
  "class_part_id": 123,
  "class_name": "English Intermediate A",
  "session_date": "2024-06-16",
  "start_time": "09:00:00",
  "attendance_code": "ABC123",
  "code_expires_at": "2024-06-16T10:00:00Z",
  "is_active": true,
  "total_students": 25,
  "present_count": 0,
  "absent_count": 0
}
```

### 2. Get Class Roster
**GET** `/teacher/class-roster/{class_part_id}`

Retrieves current class roster for teacher's mobile app.

**Response:**
```json
{
  "class_part_id": 123,
  "class_name": "English Intermediate A",
  "session_date": "2024-06-16",
  "total_students": 25,
  "students": [
    {
      "student_id": 789,
      "student_name": "John Doe",
      "enrollment_status": "ACTIVE",
      "is_audit": false,
      "photo_url": "/media/photos/student_789.jpg"
    }
  ],
  "last_synced": "2024-06-16T08:30:00Z"
}
```

### 3. Manual Attendance Entry
**POST** `/teacher/manual-attendance`

Allows teacher to manually mark attendance for students.

**Request Body:**
```json
{
  "session_id": 456,
  "student_id": 789,
  "status": "PRESENT",
  "notes": "Late arrival - 10 minutes"
}
```

### 4. End Attendance Session
**POST** `/teacher/end-session/{session_id}`

Ends the attendance session and finalizes attendance records.

---

## 👨‍🎓 Student Endpoints

### 1. Submit Attendance Code
**POST** `/student/submit-code`

Student submits attendance code with optional location data.

**Request Body:**
```json
{
  "session_id": 456,
  "submitted_code": "ABC123",
  "latitude": 11.5564,
  "longitude": 104.9282
}
```

**Response:**
```json
{
  "success": true,
  "status": "PRESENT",
  "message": "Attendance recorded successfully",
  "within_geofence": true,
  "distance_meters": 25.4
}
```

### 2. Get My Attendance
**GET** `/student/my-attendance`

Retrieves student's attendance history with pagination.

**Query Parameters:**
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20)
- `start_date`: Filter from date (YYYY-MM-DD)
- `end_date`: Filter to date (YYYY-MM-DD)

### 3. Request Permission
**POST** `/student/request-permission`

Student requests permission for absence or late arrival.

---

## 👨‍💼 Admin Endpoints

### 1. List Sessions
**GET** `/admin/sessions`

Lists all attendance sessions with filtering and pagination.

**Query Parameters:**
- `page`: Page number
- `limit`: Items per page  
- `class_part_id`: Filter by class
- `date_from`: Start date filter
- `date_to`: End date filter
- `teacher_id`: Filter by teacher

### 2. Attendance Report
**GET** `/admin/attendance-report`

Generates comprehensive attendance reports.

### 3. Sync Rosters
**POST** `/admin/sync-rosters`

Synchronizes class rosters with enrollment system.

---

## 🔒 Authentication

All endpoints require appropriate role-based authentication:

**Teacher Endpoints:**
```python
@teacher_required
```

**Student Endpoints:**
```python
@student_required  
```

**Admin Endpoints:**
```python
@admin_required
```

---

## 📍 Mobile-Specific Features

### Geofence Validation
- Automatic location verification for attendance integrity
- Configurable radius per classroom/building
- Distance calculations included in responses

### Offline Support
- Roster data can be cached locally
- Code submissions can be queued when offline
- Sync mechanism for when connection restored

### Real-time Updates
- Live attendance count updates
- Session status changes
- Roster synchronization alerts

---

## 🚨 Error Responses

**401 Unauthorized:**
```json
{"error": "Authentication required"}
```

**403 Forbidden:**
```json
{"error": "Teacher access required"}
```

**400 Bad Request:**
```json
{"error": "Invalid attendance code"}
```

**404 Not Found:**
```json
{"error": "Session not found"}
```

---

## 💡 Mobile Implementation Tips

1. **Cache roster data** locally for offline functionality
2. **Implement retry logic** for code submissions
3. **Use location services** for geofence validation
4. **Handle time zone** conversions properly
5. **Implement push notifications** for session updates
6. **Store attendance codes** securely on device
7. **Validate input** before sending requests

This API is **100% production-ready** for mobile development! 🚀