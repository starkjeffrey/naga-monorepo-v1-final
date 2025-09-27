# Student Management API Validation Commands

This document provides comprehensive curl commands to test all Student Management API endpoints and validate the integration between the frontend components and the Django-Ninja v2 backend.

## Prerequisites

1. **Backend server running**: Ensure the Django backend is running on the expected URL
2. **Authentication**: Some commands require authentication tokens
3. **Test data**: Some endpoints require existing student data

### Environment Variables

```bash
# Set these variables for your environment
export API_BASE_URL="http://localhost:8000/api/v2"
export AUTH_TOKEN="your-jwt-token-here"
export STUDENT_ID="existing-student-id"
export COURSE_ID="existing-course-id"
```

## 1. Student CRUD Operations

### 1.1 Get All Students (with pagination)

```bash
# Basic student list
curl -X GET "${API_BASE_URL}/students/" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"

# With pagination and search
curl -X GET "${API_BASE_URL}/students/?page=1&pageSize=25&search=john" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"

# With filters
curl -X GET "${API_BASE_URL}/students/?status=active&program=Computer%20Science" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"
```

### 1.2 Get Single Student

```bash
# Get student by ID
curl -X GET "${API_BASE_URL}/students/${STUDENT_ID}" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"

# Get student with full details
curl -X GET "${API_BASE_URL}/students/${STUDENT_ID}?include=enrollments,notes,alerts" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"
```

### 1.3 Create New Student

```bash
# Create student with basic data
curl -X POST "${API_BASE_URL}/students/" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "studentId": "A12345678",
    "firstName": "John",
    "lastName": "Doe",
    "email": "john.doe@example.com",
    "phone": "+1-555-123-4567",
    "dateOfBirth": "1995-01-15",
    "gender": "male",
    "nationality": "United States",
    "address": "123 Main St",
    "city": "Anytown",
    "state": "CA",
    "postalCode": "12345",
    "country": "United States",
    "program": "Computer Science",
    "academicYear": "Sophomore",
    "enrollmentDate": "2023-08-15",
    "status": "active",
    "emergencyContact": {
      "name": "Jane Doe",
      "relationship": "parent",
      "phone": "+1-555-987-6543",
      "email": "jane.doe@example.com"
    }
  }'

# Create student with photo upload
curl -X POST "${API_BASE_URL}/students/" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -F "studentId=A87654321" \
  -F "firstName=Jane" \
  -F "lastName=Smith" \
  -F "email=jane.smith@example.com" \
  -F "program=Engineering" \
  -F "academicYear=Freshman" \
  -F "enrollmentDate=2023-08-15" \
  -F "status=active" \
  -F "photo=@path/to/student-photo.jpg"
```

### 1.4 Update Student

```bash
# Update basic information
curl -X PATCH "${API_BASE_URL}/students/${STUDENT_ID}" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+1-555-999-8888",
    "address": "456 Oak Avenue",
    "status": "active",
    "gpa": 3.75
  }'

# Update emergency contact
curl -X PATCH "${API_BASE_URL}/students/${STUDENT_ID}" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "emergencyContact": {
      "name": "John Doe Sr.",
      "relationship": "father",
      "phone": "+1-555-111-2222",
      "email": "john.sr@example.com"
    }
  }'
```

### 1.5 Delete Student

```bash
# Delete student (soft delete)
curl -X DELETE "${API_BASE_URL}/students/${STUDENT_ID}" \
  -H "Authorization: Bearer ${AUTH_TOKEN}"

# Force delete (hard delete) - admin only
curl -X DELETE "${API_BASE_URL}/students/${STUDENT_ID}?force=true" \
  -H "Authorization: Bearer ${AUTH_TOKEN}"
```

## 2. Advanced Search Operations

### 2.1 Advanced Search

```bash
# Complex search with filters
curl -X POST "${API_BASE_URL}/students/search" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "john doe",
    "filters": {
      "status": ["active", "pending"],
      "program": ["Computer Science", "Engineering"],
      "academicYear": ["Sophomore", "Junior"],
      "enrollmentDateRange": {
        "start": "2023-01-01",
        "end": "2023-12-31"
      },
      "gpaRange": {
        "min": 3.0,
        "max": 4.0
      },
      "hasAlerts": false
    },
    "sorting": {
      "field": "fullName",
      "direction": "asc"
    },
    "pagination": {
      "page": 1,
      "pageSize": 25
    },
    "facets": ["status", "program", "academicYear"]
  }'
```

### 2.2 Quick Search

```bash
# Quick search for student locator
curl -X GET "${API_BASE_URL}/students/quick-search?q=john" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"

# Search by student ID
curl -X GET "${API_BASE_URL}/students/quick-search?q=A12345678" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"
```

### 2.3 Photo Search

```bash
# Search by photo (facial recognition)
curl -X POST "${API_BASE_URL}/students/search/photo" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -F "photo=@path/to/search-photo.jpg"
```

### 2.4 Search Suggestions

```bash
# Get search suggestions
curl -X GET "${API_BASE_URL}/students/search/suggestions?q=joh" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"
```

## 3. Photo Management

### 3.1 Upload Photo

```bash
# Upload student photo
curl -X POST "${API_BASE_URL}/students/${STUDENT_ID}/photo" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -F "photo=@path/to/student-photo.jpg"
```

### 3.2 Delete Photo

```bash
# Delete student photo
curl -X DELETE "${API_BASE_URL}/students/${STUDENT_ID}/photo" \
  -H "Authorization: Bearer ${AUTH_TOKEN}"
```

### 3.3 OCR Processing

```bash
# Process document with OCR
curl -X POST "${API_BASE_URL}/students/ocr/process" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -F "document=@path/to/id-document.jpg"
```

## 4. Notes and Alerts Management

### 4.1 Student Notes

```bash
# Add note to student
curl -X POST "${API_BASE_URL}/students/${STUDENT_ID}/notes" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Student showed improvement in recent assessments.",
    "category": "academic",
    "isPrivate": false
  }'

# Get student notes
curl -X GET "${API_BASE_URL}/students/${STUDENT_ID}/notes" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"
```

### 4.2 Student Alerts

```bash
# Add alert to student
curl -X POST "${API_BASE_URL}/students/${STUDENT_ID}/alerts" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "financial",
    "severity": "medium",
    "message": "Payment overdue for current semester",
    "details": "Balance of $2,500 past due date"
  }'

# Get student alerts
curl -X GET "${API_BASE_URL}/students/${STUDENT_ID}/alerts" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"

# Clear specific alert
curl -X DELETE "${API_BASE_URL}/students/${STUDENT_ID}/alerts/alert_id_here" \
  -H "Authorization: Bearer ${AUTH_TOKEN}"
```

## 5. Analytics and Reporting

### 5.1 Student Analytics

```bash
# Get student analytics
curl -X GET "${API_BASE_URL}/students/${STUDENT_ID}/analytics?timeframe=semester" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"

# Get analytics for different timeframe
curl -X GET "${API_BASE_URL}/students/${STUDENT_ID}/analytics?timeframe=year" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"
```

### 5.2 AI Predictions

```bash
# Get AI predictions for student
curl -X GET "${API_BASE_URL}/students/${STUDENT_ID}/predictions" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"
```

### 5.3 Risk Assessment

```bash
# Get student risk assessment
curl -X GET "${API_BASE_URL}/students/${STUDENT_ID}/risk-assessment" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"
```

### 5.4 Cohort Comparison

```bash
# Compare with cohort
curl -X GET "${API_BASE_URL}/students/${STUDENT_ID}/compare?cohort_type=program" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"

# Compare with year cohort
curl -X GET "${API_BASE_URL}/students/${STUDENT_ID}/compare?cohort_type=year" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"
```

### 5.5 Generate Insights

```bash
# Generate AI insights
curl -X POST "${API_BASE_URL}/students/${STUDENT_ID}/insights" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"
```

## 6. Enrollment Operations

### 6.1 Student Enrollments

```bash
# Get student enrollments
curl -X GET "${API_BASE_URL}/students/${STUDENT_ID}/enrollments" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"

# Get enrollments for specific term
curl -X GET "${API_BASE_URL}/students/${STUDENT_ID}/enrollments?term=Fall2023" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"
```

### 6.2 Enroll in Courses

```bash
# Enroll student in courses
curl -X POST "${API_BASE_URL}/students/${STUDENT_ID}/enrollments" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "course_ids": ["course_id_1", "course_id_2", "course_id_3"],
    "enrollment_type": "enroll",
    "override_restrictions": false,
    "validate_prerequisites": true
  }'
```

### 6.3 Withdraw from Course

```bash
# Withdraw from course
curl -X DELETE "${API_BASE_URL}/students/${STUDENT_ID}/enrollments/enrollment_id_here" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Schedule conflict",
    "effective_date": "2023-10-15"
  }'
```

### 6.4 Available Courses

```bash
# Get available courses for student
curl -X GET "${API_BASE_URL}/students/${STUDENT_ID}/available-courses" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"
```

## 7. Communication

### 7.1 Send Email

```bash
# Send email to student
curl -X POST "${API_BASE_URL}/students/${STUDENT_ID}/email" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -F "subject=Important: Academic Status Update" \
  -F "body=Please contact your academic advisor to discuss your progress." \
  -F "attachment_0=@path/to/document.pdf"
```

### 7.2 Send SMS

```bash
# Send SMS to student
curl -X POST "${API_BASE_URL}/students/${STUDENT_ID}/sms" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Reminder: Your tuition payment is due on Friday."
  }'
```

### 7.3 Communication History

```bash
# Get communication history
curl -X GET "${API_BASE_URL}/students/${STUDENT_ID}/communications" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"

# Filter by communication type
curl -X GET "${API_BASE_URL}/students/${STUDENT_ID}/communications?type=email" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"
```

## 8. Bulk Operations

### 8.1 Import Students

```bash
# Import students from CSV
curl -X POST "${API_BASE_URL}/students/import" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -F "file=@path/to/students.csv" \
  -F "options={\"skipDuplicates\":true,\"updateExisting\":false,\"validateOnly\":false}"
```

### 8.2 Validate Import File

```bash
# Validate import file before processing
curl -X POST "${API_BASE_URL}/students/import/validate" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -F "file=@path/to/students.csv"
```

### 8.3 Export Students

```bash
# Export specific students
curl -X POST "${API_BASE_URL}/students/export" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "student_ids": ["student1", "student2", "student3"],
    "format": "excel",
    "includeHeaders": true,
    "includePhotos": false,
    "fields": ["fullName", "email", "program", "status", "gpa"]
  }' \
  --output students_export.xlsx

# Export all students with filters
curl -X POST "${API_BASE_URL}/students/export/all" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "filters": {
      "status": ["active"],
      "program": ["Computer Science"]
    },
    "format": "csv",
    "includeHeaders": true
  }' \
  --output filtered_students.csv
```

### 8.4 Bulk Status Update

```bash
# Bulk update student statuses
curl -X POST "${API_BASE_URL}/students/bulk/update-status" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "student_ids": ["student1", "student2", "student3"],
    "status": "graduated"
  }'
```

### 8.5 Bulk Email Campaign

```bash
# Send bulk email campaign
curl -X POST "${API_BASE_URL}/students/bulk/email" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -F "campaign={\"name\":\"Welcome Campaign\",\"subject\":\"Welcome to University\",\"content\":\"Welcome message here\",\"recipientIds\":[\"student1\",\"student2\"]}" \
  -F "attachment_0=@path/to/welcome-guide.pdf"
```

### 8.6 Bulk Enrollment

```bash
# Bulk enroll students in courses
curl -X POST "${API_BASE_URL}/students/bulk/enroll" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "student_ids": ["student1", "student2", "student3"],
    "course_ids": ["course1", "course2"],
    "enrollment_type": "enroll",
    "override_restrictions": false
  }'
```

## 9. Utility Operations

### 9.1 Get Statistics

```bash
# Get overall student statistics
curl -X GET "${API_BASE_URL}/students/statistics" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"
```

### 9.2 Get Lookup Data

```bash
# Get lookup data for forms
curl -X GET "${API_BASE_URL}/students/lookup-data" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"
```

### 9.3 Validate Student ID

```bash
# Validate student ID format
curl -X POST "${API_BASE_URL}/students/validate/student-id" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "student_id": "A12345678"
  }'
```

### 9.4 Check Email Exists

```bash
# Check if email already exists
curl -X POST "${API_BASE_URL}/students/validate/email" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john.doe@example.com",
    "exclude_id": "optional_student_id_to_exclude"
  }'
```

### 9.5 Get Audit Trail

```bash
# Get audit trail for student
curl -X GET "${API_BASE_URL}/students/${STUDENT_ID}/audit-trail" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"

# Get audit trail with date filter
curl -X GET "${API_BASE_URL}/students/${STUDENT_ID}/audit-trail?start_date=2023-01-01&end_date=2023-12-31" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json"
```

## 10. Test Scenarios

### 10.1 Complete Student Lifecycle Test

```bash
#!/bin/bash
# Complete student lifecycle test script

# 1. Create new student
echo "Creating new student..."
RESPONSE=$(curl -s -X POST "${API_BASE_URL}/students/" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "studentId": "A99999999",
    "firstName": "Test",
    "lastName": "Student",
    "email": "test.student@example.com",
    "program": "Computer Science",
    "academicYear": "Freshman",
    "enrollmentDate": "2023-08-15",
    "status": "active"
  }')

# Extract student ID from response
NEW_STUDENT_ID=$(echo $RESPONSE | jq -r '.id')
echo "Created student with ID: $NEW_STUDENT_ID"

# 2. Update student information
echo "Updating student information..."
curl -s -X PATCH "${API_BASE_URL}/students/${NEW_STUDENT_ID}" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+1-555-TEST-123",
    "gpa": 3.5
  }'

# 3. Add note
echo "Adding note..."
curl -s -X POST "${API_BASE_URL}/students/${NEW_STUDENT_ID}/notes" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Test note for validation"
  }'

# 4. Get student details
echo "Retrieving student details..."
curl -s -X GET "${API_BASE_URL}/students/${NEW_STUDENT_ID}" \
  -H "Authorization: Bearer ${AUTH_TOKEN}"

# 5. Search for student
echo "Searching for student..."
curl -s -X GET "${API_BASE_URL}/students/quick-search?q=Test%20Student" \
  -H "Authorization: Bearer ${AUTH_TOKEN}"

# 6. Clean up - delete test student
echo "Cleaning up test student..."
curl -s -X DELETE "${API_BASE_URL}/students/${NEW_STUDENT_ID}" \
  -H "Authorization: Bearer ${AUTH_TOKEN}"

echo "Student lifecycle test completed!"
```

### 10.2 Bulk Operations Test

```bash
#!/bin/bash
# Bulk operations test script

# 1. Create test students for bulk operations
echo "Creating test students for bulk operations..."
for i in {1..5}; do
  curl -s -X POST "${API_BASE_URL}/students/" \
    -H "Authorization: Bearer ${AUTH_TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"studentId\": \"B0000000${i}\",
      \"firstName\": \"Bulk\",
      \"lastName\": \"Student${i}\",
      \"email\": \"bulk.student${i}@example.com\",
      \"program\": \"Engineering\",
      \"academicYear\": \"Sophomore\",
      \"enrollmentDate\": \"2023-08-15\",
      \"status\": \"active\"
    }" > /dev/null
done

# 2. Test bulk status update
echo "Testing bulk status update..."
curl -s -X POST "${API_BASE_URL}/students/bulk/update-status" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "student_ids": ["B00000001", "B00000002", "B00000003"],
    "status": "inactive"
  }'

# 3. Test bulk export
echo "Testing bulk export..."
curl -s -X POST "${API_BASE_URL}/students/export" \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "student_ids": ["B00000001", "B00000002", "B00000003", "B00000004", "B00000005"],
    "format": "csv",
    "includeHeaders": true
  }' \
  --output bulk_test_export.csv

# 4. Clean up test students
echo "Cleaning up test students..."
for i in {1..5}; do
  curl -s -X DELETE "${API_BASE_URL}/students/B0000000${i}" \
    -H "Authorization: Bearer ${AUTH_TOKEN}" > /dev/null
done

echo "Bulk operations test completed!"
```

## Expected Response Formats

### Success Response Example

```json
{
  "success": true,
  "data": {
    "id": "student_id_here",
    "studentId": "A12345678",
    "firstName": "John",
    "lastName": "Doe",
    "fullName": "John Doe",
    "email": "john.doe@example.com",
    "status": "active",
    "program": "Computer Science",
    "createdAt": "2023-08-15T10:00:00Z",
    "updatedAt": "2023-08-15T10:00:00Z"
  },
  "message": "Student created successfully",
  "timestamp": "2023-08-15T10:00:00Z"
}
```

### Error Response Example

```json
{
  "success": false,
  "error": "Validation error",
  "details": "Student ID already exists",
  "code": "DUPLICATE_STUDENT_ID",
  "field": "studentId",
  "timestamp": "2023-08-15T10:00:00Z"
}
```

### Paginated Response Example

```json
{
  "success": true,
  "data": [
    {
      "id": "student1",
      "studentId": "A12345678",
      "fullName": "John Doe",
      "email": "john.doe@example.com",
      "status": "active"
    }
  ],
  "total": 150,
  "page": 1,
  "pageSize": 25,
  "hasNext": true,
  "hasPrevious": false,
  "timestamp": "2023-08-15T10:00:00Z"
}
```

## Usage Notes

1. **Authentication**: Replace `${AUTH_TOKEN}` with actual JWT token
2. **Base URL**: Update `${API_BASE_URL}` for your environment
3. **File Uploads**: Use actual file paths for photo and document uploads
4. **Student IDs**: Replace placeholder IDs with actual values from your database
5. **Error Handling**: Check response status codes and error messages
6. **Rate Limiting**: Be aware of API rate limits for bulk operations
7. **File Downloads**: Use `--output` flag for export operations

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check authentication token and expiration
2. **404 Not Found**: Verify student ID exists and URL is correct
3. **422 Validation Error**: Check required fields and data formats
4. **429 Rate Limit**: Reduce request frequency for bulk operations
5. **500 Server Error**: Check backend logs for internal errors

### Debug Commands

```bash
# Verbose curl output
curl -v -X GET "${API_BASE_URL}/students/${STUDENT_ID}" \
  -H "Authorization: Bearer ${AUTH_TOKEN}"

# Save response headers
curl -D headers.txt -X GET "${API_BASE_URL}/students/" \
  -H "Authorization: Bearer ${AUTH_TOKEN}"

# Time the request
curl -w "@curl-format.txt" -X GET "${API_BASE_URL}/students/" \
  -H "Authorization: Bearer ${AUTH_TOKEN}"
```

Create `curl-format.txt` with:
```
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
```

---

This comprehensive validation suite ensures that all Student Management API endpoints are working correctly and the frontend integration is properly configured.