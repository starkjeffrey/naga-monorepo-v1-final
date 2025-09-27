# Naga SIS Enhanced API v2 Documentation

## Overview

The Naga SIS Enhanced API v2 provides comprehensive endpoints for the React frontend with advanced features including:

- **Enhanced Django-Ninja API endpoints** with advanced search and analytics
- **GraphQL API** with real-time subscriptions
- **WebSocket connections** for collaborative features
- **Redis caching** for optimal performance
- **AI-powered predictions** and insights

## Base URLs

- **API v2**: `https://your-domain.com/api/v2/`
- **GraphQL**: `https://your-domain.com/graphql/`
- **WebSocket**: `wss://your-domain.com/ws/`

## Authentication

All API endpoints use JWT authentication. Include the token in the Authorization header:

```bash
Authorization: Bearer <your-jwt-token>
```

## API Endpoints

### Students API (`/api/v2/students/`)

#### Advanced Student Search
```http
GET /api/v2/students/search/
```

**Query Parameters:**
- `query` (string): Search query
- `fuzzy_search` (boolean): Enable fuzzy matching
- `page` (integer): Page number (default: 1)
- `page_size` (integer): Results per page (default: 25, max: 100)
- `sort[]` (array): Sort options

**Request Example:**
```bash
curl -X GET "https://your-domain.com/api/v2/students/search/?query=john&fuzzy_search=true&page=1&page_size=25" \
  -H "Authorization: Bearer <token>"
```

**Response Example:**
```json
[
  {
    "unique_id": "550e8400-e29b-41d4-a716-446655440000",
    "student_id": "STU001",
    "full_name": "John Doe",
    "email": "john.doe@example.com",
    "program": "Computer Science",
    "level": "Undergraduate",
    "status": "enrolled",
    "photo_url": "https://example.com/photos/john.jpg",
    "match_score": 0.95,
    "risk_score": 0.15,
    "success_prediction": 0.85,
    "last_activity": "2023-12-01T10:30:00Z",
    "enrollment_count": 5,
    "attendance_rate": 0.92
  }
]
```

#### Get Student Details
```http
GET /api/v2/students/{student_id}/
```

**Response includes:**
- Complete student information
- Analytics and predictions
- Recent enrollments
- Payment history
- Activity timeline

#### Bulk Student Actions
```http
POST /api/v2/students/bulk-actions/
```

**Request Body:**
```json
{
  "action": "update_status",
  "target_ids": ["uuid1", "uuid2"],
  "parameters": {
    "status": "active"
  },
  "dry_run": false
}
```

#### Student Analytics
```http
GET /api/v2/students/{student_id}/analytics/
```

Returns detailed analytics including:
- Success prediction score
- Risk factors
- Performance trends
- Attendance patterns
- Engagement metrics

#### Student Timeline
```http
GET /api/v2/students/{student_id}/timeline/
```

**Query Parameters:**
- `page` (integer): Page number
- `page_size` (integer): Events per page
- `event_types[]` (array): Filter by event types

#### Photo Upload
```http
POST /api/v2/students/{student_id}/photos/upload/
```

**Form Data:**
- `photo` (file): Image file (JPEG, PNG, WebP)
- `is_primary` (boolean): Set as primary photo

### Academic API (`/api/v2/academics/`)

#### Grade Spreadsheet
```http
GET /api/v2/academics/grades/spreadsheet/{class_id}/
```

Returns grade data in spreadsheet format with:
- Student list
- Assignment columns
- Grade matrix
- Completion statistics

#### Bulk Grade Update
```http
POST /api/v2/academics/grades/spreadsheet/{class_id}/bulk-update/
```

**Request Body:**
```json
[
  {
    "student_id": "uuid1",
    "assignment_id": "uuid2",
    "score": 85.5,
    "notes": "Good improvement",
    "last_modified": "2023-12-01T10:30:00Z"
  }
]
```

#### Schedule Conflict Detection
```http
GET /api/v2/academics/schedule/conflicts/
```

**Query Parameters:**
- `term_id` (uuid): Filter by term
- `room_id` (uuid): Filter by room
- `instructor_id` (uuid): Filter by instructor

#### Transcript Generation
```http
GET /api/v2/academics/transcripts/generate/{student_id}/
```

**Query Parameters:**
- `template` (string): Template type (default: "official")
- `include_unofficial` (boolean): Include unofficial courses

#### QR Code Attendance
```http
POST /api/v2/academics/attendance/qr-scan/
```

**Request Body:**
```json
{
  "qr_data": "class_id:student_id:session_date",
  "location": "Room 101",
  "timestamp": "2023-12-01T10:30:00Z"
}
```

#### Course Prerequisites
```http
GET /api/v2/academics/courses/{course_id}/prerequisites/
```

Returns prerequisite chain visualization data.

### Finance API (`/api/v2/finance/`)

#### Point-of-Sale Transaction
```http
POST /api/v2/finance/pos/transaction/
```

**Request Body:**
```json
{
  "amount": "150.00",
  "payment_method": "credit_card",
  "student_id": "uuid1",
  "description": "Tuition payment",
  "line_items": [
    {
      "description": "Fall 2023 Tuition",
      "quantity": 1,
      "unit_price": "150.00"
    }
  ]
}
```

#### Financial Analytics
```http
GET /api/v2/finance/analytics/dashboard/
```

**Query Parameters:**
- `date_range` (integer): Days to look back (default: 30)
- `include_forecasts` (boolean): Include revenue forecasts

#### Scholarship Matching
```http
GET /api/v2/finance/scholarships/matching/{student_id}/
```

Returns AI-powered scholarship matches with:
- Match score
- Criteria analysis
- Recommendations

#### Payment Reminders
```http
POST /api/v2/finance/automation/payment-reminders/
```

**Request Body:**
```json
{
  "student_ids": ["uuid1", "uuid2"],
  "reminder_days": [7, 3, 1],
  "template": "default"
}
```

#### Revenue Forecast
```http
GET /api/v2/finance/reports/revenue-forecast/
```

**Query Parameters:**
- `months_ahead` (integer): Forecast period (1-24)
- `confidence_level` (float): Confidence level (0.5-0.95)

### Communications API (`/api/v2/communications/`)

#### Message Threads
```http
GET /api/v2/communications/threads/
```

**Query Parameters:**
- `participant_id` (uuid): Filter by participant
- `unread_only` (boolean): Show only unread threads
- `page` (integer): Page number
- `page_size` (integer): Threads per page

#### Create Thread
```http
POST /api/v2/communications/threads/
```

**Request Body:**
```json
{
  "subject": "Grade Inquiry",
  "participant_ids": ["uuid1", "uuid2"],
  "initial_message": "I have a question about my grade.",
  "tags": ["academic", "urgent"]
}
```

#### Send Message
```http
POST /api/v2/communications/threads/{thread_id}/messages/
```

**Request Body:**
```json
{
  "content": "Thank you for your response.",
  "message_type": "text",
  "attachments": []
}
```

#### Send Notification
```http
POST /api/v2/communications/notifications/send/
```

**Request Body:**
```json
{
  "recipient_ids": ["uuid1", "uuid2"],
  "title": "Grade Available",
  "message": "Your grade for MATH101 is now available.",
  "notification_type": "info",
  "channels": ["push", "email"]
}
```

### Documents API (`/api/v2/documents/`)

#### OCR Processing
```http
POST /api/v2/documents/ocr/process/
```

**Form Data:**
- `document` (file): Document to process
- `document_type` (string): Type hint for better processing
- `extract_entities` (boolean): Extract structured entities

#### Document Intelligence
```http
GET /api/v2/documents/intelligence/{document_id}/
```

Returns intelligent analysis with:
- Document type classification
- Key field extraction
- Validation status
- Processing recommendations

#### Batch Upload
```http
POST /api/v2/documents/upload/batch/
```

**Form Data:**
- `documents[]` (files): Multiple documents
- `document_type` (string): Type for all documents
- `auto_process` (boolean): Automatically start OCR

#### Document Search
```http
GET /api/v2/documents/search/
```

**Query Parameters:**
- `query` (string): Search query
- `document_types[]` (array): Filter by types
- `date_from` (datetime): Start date
- `date_to` (datetime): End date

### Automation API (`/api/v2/automation/`)

#### Workflow Management
```http
GET /api/v2/automation/workflows/
POST /api/v2/automation/workflows/
GET /api/v2/automation/workflows/{workflow_id}/
```

#### Execute Workflow
```http
POST /api/v2/automation/workflows/{workflow_id}/execute/
```

**Request Body:**
```json
{
  "input_data": {},
  "dry_run": false
}
```

#### Workflow Templates
```http
GET /api/v2/automation/templates/
POST /api/v2/automation/templates/{template_id}/instantiate/
```

### Analytics API (`/api/v2/analytics/`)

#### Dashboard Metrics
```http
GET /api/v2/analytics/dashboard/metrics/
```

**Query Parameters:**
- `date_range_days` (integer): Analysis period

#### Custom Reports
```http
GET /api/v2/analytics/reports/custom/
```

**Query Parameters:**
- `report_type` (string): Type of report
- `filters` (object): Report filters
- `format` (string): Output format (json, csv)

#### Predictive Insights
```http
GET /api/v2/analytics/insights/predictive/
```

**Query Parameters:**
- `model_type` (string): Prediction model
- `confidence_threshold` (float): Minimum confidence

### AI Predictions API (`/api/v2/ai/`)

#### Make Prediction
```http
POST /api/v2/ai/predict/
```

**Request Body:**
```json
{
  "model_type": "success_prediction",
  "input_data": {
    "gpa": 3.5,
    "attendance_rate": 0.92,
    "engagement_score": 0.8
  },
  "confidence_threshold": 0.7
}
```

#### Available Models
```http
GET /api/v2/ai/models/available/
```

#### Model Performance
```http
GET /api/v2/ai/models/{model_id}/performance/
```

#### Batch Predictions
```http
POST /api/v2/ai/batch-predict/
```

## GraphQL API

### Endpoint
```
POST /graphql/
```

### Introspection
Enable GraphiQL playground in development at `/graphql/`

### Sample Queries

#### Dashboard Metrics
```graphql
query DashboardMetrics($dateRange: Int!) {
  dashboardMetrics(dateRangeDays: $dateRange) {
    studentMetrics {
      totalCount { value label trend changePercent }
      atRiskCount { value label trend changePercent }
    }
    academicMetrics {
      gradesEntered
      attendanceRate
    }
    financialMetrics {
      totalRevenue { value label trend }
      pendingPayments { value label trend }
    }
    lastUpdated
  }
}
```

#### Student Search
```graphql
query StudentSearch($filters: StudentSearchFilters!, $pagination: PaginationInput!) {
  students(filters: $filters, pagination: $pagination) {
    edges {
      node {
        uniqueId
        studentId
        person { fullName email }
        analytics {
          successPrediction
          riskFactors
          attendanceRate
        }
      }
    }
    pageInfo {
      hasNextPage
      totalCount
    }
  }
}
```

#### Grade Spreadsheet
```graphql
query GradeSpreadsheet($classId: ID!) {
  gradeSpreadsheet(classId: $classId) {
    classHeader {
      course { code name }
      instructor
    }
    assignments {
      uniqueId
      name
      maxScore
      dueDate
    }
    rows {
      studentId
      studentName
      grades
    }
    completionRate
  }
}
```

### Sample Mutations

#### Update Grade
```graphql
mutation UpdateGrade($gradeUpdate: GradeUpdateInput!) {
  updateGrade(gradeUpdate: $gradeUpdate) {
    success
    message
    grade {
      uniqueId
      score
      assignment { name }
    }
  }
}
```

#### Process POS Transaction
```graphql
mutation ProcessPOSTransaction($transaction: POSTransactionInput!) {
  processPosTransaction(transactionInput: $transaction) {
    transactionId
    amount
    status
    receiptNumber
    processedAt
  }
}
```

### Sample Subscriptions

#### Grade Entry Updates
```graphql
subscription GradeEntryUpdates($classId: ID!) {
  gradeEntryUpdates(classId: $classId) {
    studentId
    assignmentId
    newScore
    updatedBy
    timestamp
    conflict
  }
}
```

#### Dashboard Updates
```graphql
subscription DashboardUpdates {
  dashboardMetricsUpdates {
    metrics {
      studentMetrics { totalCount { value } }
    }
    updatedFields
    timestamp
  }
}
```

## WebSocket Connections

### Grade Entry Collaboration
```javascript
const ws = new WebSocket('wss://your-domain.com/ws/grades/live-entry/class123/');

// Send grade update
ws.send(JSON.stringify({
  type: 'grade_update',
  student_id: 'uuid1',
  assignment_id: 'uuid2',
  value: 85.5,
  field_name: 'score'
}));

// Receive updates
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'grade_entry_update') {
    // Update UI with real-time changes
  }
};
```

### Dashboard Metrics
```javascript
const ws = new WebSocket('wss://your-domain.com/ws/dashboard/metrics/');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'metrics_update') {
    // Update dashboard with real-time metrics
  }
};
```

### Communication
```javascript
const ws = new WebSocket('wss://your-domain.com/ws/communications/room123/');

// Send message
ws.send(JSON.stringify({
  type: 'send_message',
  content: 'Hello, this is a test message',
  message_type: 'text'
}));

// Receive messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'new_message') {
    // Display new message in UI
  }
};
```

## Performance & Caching

### Cache Headers
The API includes appropriate cache headers:
- `Cache-Control: public, max-age=300` for moderately changing data
- `Cache-Control: private, max-age=60` for user-specific data
- `ETag` headers for conditional requests

### Rate Limiting
- **General API**: 1000 requests per hour per user
- **Search endpoints**: 100 requests per hour per user
- **File uploads**: 50 requests per hour per user
- **WebSocket connections**: 10 concurrent connections per user

### Pagination
All list endpoints support pagination:
- Default page size: 25 items
- Maximum page size: 100 items
- Use `page` and `page_size` parameters

### Filtering & Sorting
Most endpoints support:
- **Filtering**: Use query parameters matching field names
- **Sorting**: Use `sort` parameter with field names and direction
- **Search**: Use `query` parameter for text search

## Error Handling

### HTTP Status Codes
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `422` - Validation Error
- `429` - Rate Limited
- `500` - Internal Server Error

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The provided data is invalid",
    "details": {
      "field_name": ["This field is required"]
    },
    "request_id": "req_123456789"
  }
}
```

## SDK & Examples

### JavaScript/TypeScript SDK
```typescript
import { NagaAPI } from '@naga/api-client';

const api = new NagaAPI({
  baseURL: 'https://your-domain.com/api/v2/',
  token: 'your-jwt-token'
});

// Search students
const students = await api.students.search({
  query: 'john',
  fuzzy_search: true,
  page: 1,
  page_size: 25
});

// Update grades
const result = await api.academics.bulkUpdateGrades('class123', [
  {
    student_id: 'uuid1',
    assignment_id: 'uuid2',
    score: 85.5
  }
]);
```

### Python SDK
```python
from naga_api import NagaAPIClient

client = NagaAPIClient(
    base_url='https://your-domain.com/api/v2/',
    token='your-jwt-token'
)

# Search students
students = client.students.search(
    query='john',
    fuzzy_search=True,
    page=1,
    page_size=25
)

# Process payment
transaction = client.finance.process_pos_transaction({
    'amount': '150.00',
    'payment_method': 'credit_card',
    'student_id': 'uuid1',
    'description': 'Tuition payment'
})
```

## Testing

### API Testing
```bash
# Run API tests
npm run test:api

# Run with coverage
npm run test:api -- --coverage

# Test specific endpoint
npm run test:api -- --grep "students search"
```

### GraphQL Testing
```bash
# Run GraphQL tests
npm run test:graphql

# Test subscriptions
npm run test:graphql -- --grep "subscriptions"
```

### Load Testing
```bash
# Run load tests
npm run test:load

# Test specific endpoints
npm run test:load -- --target api/v2/students/search
```

## Security

### Authentication
- JWT tokens with 24-hour expiration
- Refresh tokens for seamless renewal
- Role-based access control (RBAC)

### Authorization
- Resource-level permissions
- Field-level access control
- API rate limiting by user role

### Data Protection
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CSRF protection for state-changing operations

## Monitoring & Observability

### Metrics Available
- Request/response times
- Error rates by endpoint
- Cache hit ratios
- WebSocket connection counts
- Database query performance

### Health Checks
```http
GET /api/v2/health/
GET /graphql/ (with introspection query)
```

### Logging
All API requests are logged with:
- Request ID
- User ID
- Endpoint accessed
- Response time
- Error details (if any)

## Migration Guide

### From v1 to v2
1. **Authentication**: Same JWT tokens work
2. **Base URLs**: Add `/v2/` to existing endpoints
3. **Response Format**: Enhanced with additional fields
4. **New Features**: GraphQL and WebSocket support

### Breaking Changes
- Some field names have been standardized
- Date formats are now ISO 8601
- Pagination format has changed

### Compatibility
- v1 API remains available at `/api/`
- Both versions can be used simultaneously
- Gradual migration recommended

---

For additional support or questions, contact the development team or refer to the interactive API documentation at `/api/v2/docs/` and GraphQL playground at `/graphql/`.