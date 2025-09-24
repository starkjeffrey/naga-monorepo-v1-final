# Naga SIS API Documentation

## Overview

The Naga Student Information System API is built using Django Ninja, providing a modern, fast, and type-safe REST API for managing academic operations. The API follows RESTful principles and provides comprehensive endpoints for all system modules.

## Base URL

- **Development**: `http://localhost:8000/api`
- **Production**: `https://api.naga-sis.edu.kh/api`
- **API Documentation**: `/api/docs/` (Interactive Swagger UI)

## Authentication

The API uses JWT (JSON Web Token) authentication with multi-factor authentication support.

### Authentication Flow

```
1. Login with credentials → POST /api/auth/login
2. Receive access and refresh tokens
3. Include access token in requests: Authorization: Bearer <token>
4. Refresh token when expired → POST /api/auth/refresh
```

### Required Headers

```http
Authorization: Bearer <access_token>
Content-Type: application/json
Accept: application/json
X-Client-Version: 1.0.0
```

## API Modules

### 1. Attendance Module (`/api/attendance/`)

Manages class attendance tracking with QR code support and mobile integration.

#### Endpoints

- `GET /api/attendance/sessions/` - List attendance sessions
- `POST /api/attendance/sessions/` - Create new attendance session
- `GET /api/attendance/sessions/{id}/` - Get session details
- `POST /api/attendance/check-in/` - Student check-in via QR code
- `GET /api/attendance/reports/` - Generate attendance reports
- `GET /api/attendance/student/{student_id}/` - Get student attendance history

#### Example: Create Attendance Session

```http
POST /api/attendance/sessions/
Content-Type: application/json

{
  "class_id": "CS101-2024-1",
  "date": "2024-01-15",
  "start_time": "08:00",
  "end_time": "10:00",
  "location": "Room A101",
  "type": "lecture"
}
```

### 2. Curriculum Module (`/api/curriculum/`)

Manages courses, programs, and academic requirements.

#### Endpoints

- `GET /api/curriculum/courses/` - List all courses
- `POST /api/curriculum/courses/` - Create new course
- `GET /api/curriculum/courses/{code}/` - Get course details
- `GET /api/curriculum/programs/` - List academic programs
- `GET /api/curriculum/programs/{id}/requirements/` - Get program requirements
- `GET /api/curriculum/terms/` - List academic terms
- `POST /api/curriculum/senior-projects/` - Create senior project

#### Example: Get Course Details

```http
GET /api/curriculum/courses/CS101/
Accept: application/json

Response:
{
  "code": "CS101",
  "name": "Introduction to Computer Science",
  "credits": 3,
  "description": "Fundamentals of programming and computational thinking",
  "prerequisites": [],
  "offered_terms": ["Fall", "Spring"],
  "capacity": 30
}
```

### 3. Grading Module (`/api/grading/`)

Handles grade management, GPA calculations, and transcript generation.

#### Endpoints

- `GET /api/grading/grades/` - List grades
- `POST /api/grading/grades/` - Submit grades
- `PUT /api/grading/grades/{id}/` - Update grade
- `GET /api/grading/gpa/{student_id}/` - Calculate student GPA
- `GET /api/grading/transcript/{student_id}/` - Generate transcript
- `POST /api/grading/grade-appeal/` - Submit grade appeal

#### Grade Submission Format

```http
POST /api/grading/grades/
Content-Type: application/json

{
  "student_id": "STU2024001",
  "course_code": "CS101",
  "term_id": "2024-1",
  "grade": "A",
  "points": 4.0,
  "status": "final"
}
```

### 4. Finance Module (`/api/finance/`)

Manages billing, payments, scholarships, and financial aid.

#### Endpoints

- `GET /api/finance/invoices/` - List invoices
- `POST /api/finance/invoices/` - Create invoice
- `GET /api/finance/invoices/{id}/` - Get invoice details
- `POST /api/finance/payments/` - Process payment
- `GET /api/finance/scholarships/` - List scholarships
- `POST /api/finance/scholarships/apply/` - Apply for scholarship
- `GET /api/finance/tuition-rates/` - Get tuition rates
- `GET /api/finance/payment-history/{student_id}/` - Student payment history

#### Payment Processing

```http
POST /api/finance/payments/
Content-Type: application/json

{
  "invoice_id": "INV-2024-001",
  "amount": 500.00,
  "payment_method": "bank_transfer",
  "reference_number": "TXN123456",
  "payment_date": "2024-01-15"
}
```

### 5. Academic Records Module (`/api/academic-records/`)

Manages official documents, transcripts, and certifications.

#### Endpoints

- `GET /api/academic-records/transcripts/{student_id}/` - Get transcript
- `POST /api/academic-records/transcript-request/` - Request official transcript
- `GET /api/academic-records/documents/` - List document types
- `POST /api/academic-records/document-request/` - Request document
- `GET /api/academic-records/verifications/{code}/` - Verify document
- `GET /api/academic-records/degree-audit/{student_id}/` - Degree audit

#### Document Request

```http
POST /api/academic-records/document-request/
Content-Type: application/json

{
  "student_id": "STU2024001",
  "document_type": "transcript",
  "purpose": "job_application",
  "copies": 2,
  "delivery_method": "pickup",
  "urgent": false
}
```

### 6. Mobile Module (`/api/mobile/`)

Specialized endpoints for mobile applications with offline support.

#### Endpoints

- `POST /api/mobile/auth/login/` - Mobile-specific login
- `GET /api/mobile/sync/` - Sync offline data
- `GET /api/mobile/schedule/` - Get class schedule
- `POST /api/mobile/attendance/check-in/` - QR code check-in
- `GET /api/mobile/notifications/` - Push notifications
- `GET /api/mobile/offline-data/` - Download offline data package

#### Offline Data Sync

```http
POST /api/mobile/sync/
Content-Type: application/json

{
  "last_sync": "2024-01-14T10:00:00Z",
  "device_id": "mobile-001",
  "pending_actions": [
    {
      "action": "attendance_checkin",
      "timestamp": "2024-01-15T08:05:00Z",
      "data": {...}
    }
  ]
}
```

## Common Response Formats

### Success Response

```json
{
  "success": true,
  "data": {
    // Response data
  },
  "meta": {
    "timestamp": "2024-01-15T10:00:00Z",
    "version": "1.0.0"
  }
}
```

### Error Response

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field_name": ["Error message"]
    }
  },
  "meta": {
    "timestamp": "2024-01-15T10:00:00Z",
    "request_id": "req_123456"
  }
}
```

### Pagination

```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "total_pages": 5,
    "has_next": true,
    "has_previous": false
  }
}
```

## Status Codes

- `200 OK` - Successful request
- `201 Created` - Resource created successfully
- `204 No Content` - Successful request with no response body
- `400 Bad Request` - Invalid request data
- `401 Unauthorized` - Authentication required
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Conflict with existing resource
- `422 Unprocessable Entity` - Validation error
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

## Rate Limiting

API requests are rate-limited to ensure fair usage:

- **Authenticated requests**: 1000 requests per hour
- **Unauthenticated requests**: 100 requests per hour
- **Bulk operations**: 10 requests per minute

Rate limit headers:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642252800
```

## Webhooks

The API supports webhooks for real-time event notifications:

### Available Events

- `student.enrolled` - Student enrollment
- `payment.received` - Payment processed
- `grade.submitted` - Grade submission
- `attendance.marked` - Attendance recorded
- `document.ready` - Document available for pickup

### Webhook Payload

```json
{
  "event": "payment.received",
  "timestamp": "2024-01-15T10:00:00Z",
  "data": {
    "payment_id": "PAY-123",
    "student_id": "STU2024001",
    "amount": 500.00
  },
  "signature": "sha256=..."
}
```

## API Versioning

The API uses URL-based versioning. The current version is `v1`.

Future versions will be available at:
- `/api/v2/`
- `/api/v3/`

## SDK and Client Libraries

Official client libraries are available for:

- **JavaScript/TypeScript**: `npm install @naga-sis/js-client`
- **Python**: `pip install naga-sis-client`
- **Mobile (React Native)**: `npm install @naga-sis/mobile-client`

## Testing

### Test Environment

- Base URL: `https://api-test.naga-sis.edu.kh/api`
- Test credentials available upon request

### Postman Collection

Download our Postman collection for easy API testing:
[Naga SIS API Collection](https://postman.com/naga-sis/api-collection)

## Support

For API support and questions:

- **Documentation**: [https://docs.naga-sis.edu.kh](https://docs.naga-sis.edu.kh)
- **Developer Portal**: [https://developers.naga-sis.edu.kh](https://developers.naga-sis.edu.kh)
- **Email**: api-support@naga-sis.edu.kh
- **GitHub Issues**: [https://github.com/naga-sis/api/issues](https://github.com/naga-sis/api/issues)