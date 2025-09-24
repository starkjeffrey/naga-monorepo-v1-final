# Attendance API - Request/Response Schemas

## AttendanceSessionResponseSchema
**Description:** Schema for attendance session response.
**Properties:**
- **id** (integer): Id [Required]
- **class_part_id** (integer): Class Part Id [Required]
- **class_name** (string): Class Name [Required]
- **session_date** (string): Session Date [Required]
- **start_time** (string): Start Time [Required]
- **attendance_code** (string): Attendance Code [Required]
- **code_expires_at** (string): Code Expires At [Required]
- **is_active** (boolean): Is Active [Required]
- **total_students** (integer): Total Students [Required]
- **present_count** (integer): Present Count [Required]
- **absent_count** (integer): Absent Count [Required]

## AttendanceSessionCreateSchema
**Description:** Schema for teacher creating attendance session.
**Properties:**
- **class_part_id** (integer): Class Part Id [Required]
- **attendance_code** (string): Attendance Code [Required]
- **latitude** (unknown): Latitude [Optional]
- **longitude** (unknown): Longitude [Optional]
- **is_makeup_class** (boolean): Is Makeup Class [Optional]
- **makeup_reason** (unknown): Makeup Reason [Optional]

## ClassRosterResponseSchema
**Description:** Schema for class roster response.
**Properties:**
- **class_part_id** (integer): Class Part Id [Required]
- **class_name** (string): Class Name [Required]
- **session_date** (string): Session Date [Required]
- **total_students** (integer): Total Students [Required]
- **students** (array): Students [Required]
- **last_synced** (string): Last Synced [Required]

## RosterStudentSchema
**Description:** Schema for student in class roster.
**Properties:**
- **student_id** (integer): Student Id [Required]
- **student_name** (string): Student Name [Required]
- **enrollment_status** (string): Enrollment Status [Required]
- **is_audit** (boolean): Is Audit [Required]
- **photo_url** (unknown): Photo Url [Optional]

## ManualAttendanceSchema
**Description:** Schema for teacher manual attendance entry.
**Properties:**
- **session_id** (integer): Session Id [Required]
- **student_id** (integer): Student Id [Required]
- **status** (string): Status [Required]
- **notes** (unknown): Notes [Optional]

## StudentCodeResponseSchema
**Description:** Schema for code submission response.
**Properties:**
- **success** (boolean): Success [Required]
- **status** (string): Status [Required]
- **message** (string): Message [Required]
- **within_geofence** (unknown): Within Geofence [Optional]
- **distance_meters** (unknown): Distance Meters [Optional]

## StudentCodeSubmissionSchema
**Description:** Schema for student code submission.
**Properties:**
- **session_id** (integer): Session Id [Required]
- **submitted_code** (string): Submitted Code [Required]
- **latitude** (unknown): Latitude [Optional]
- **longitude** (unknown): Longitude [Optional]

## PagedAttendanceSessionResponseSchema
**Properties:**
- **items** (array): Items [Required]
- **count** (integer): Count [Required]

