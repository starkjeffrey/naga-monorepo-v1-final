# Staff-Web V2 API Documentation

## Overview

The Staff-Web V2 Enhanced API provides comprehensive endpoints for modern student information system management with advanced features including AI predictions, real-time collaboration, automated workflows, and sophisticated analytics.

## Base URL

```
Production: https://api.naga.edu.kh/api/v2/
Development: http://localhost:8000/api/v2/
```

## Authentication

All API endpoints require JWT authentication unless otherwise specified.

```http
Authorization: Bearer <your-jwt-token>
```

## API Architecture

### Core Domains

1. **Students** (`/api/v2/students/`) - Enhanced student management with analytics
2. **Academics** (`/api/v2/academics/`) - Advanced grade entry and course management
3. **Finance** (`/api/v2/finance/`) - POS system and financial analytics
4. **Innovation** (`/api/v2/innovation/`) - AI/ML, automation, and advanced features

### Technology Stack

- **Framework**: Django-Ninja v2 with async support
- **Real-time**: Django Channels + Redis WebSockets
- **GraphQL**: Strawberry GraphQL with subscriptions
- **Caching**: Redis with multi-level TTL strategies
- **AI/ML**: Custom prediction models with caching
- **Documentation**: Auto-generated OpenAPI 3.0 schema

## Student Management API

### Advanced Student Search

```http
GET /api/v2/students/search/
```

**Features:**
- Fuzzy search with match scoring
- Advanced filtering (program, level, status, risk factors)
- Real-time analytics integration
- Faceted search results
- Pagination with performance optimization

**Query Parameters:**
```json
{
  "query": "john doe",
  "fuzzy_search": true,
  "status": ["active", "enrolled"],
  "risk_levels": ["high", "medium"],
  "has_overdue_payments": false,
  "min_gpa": 3.0,
  "page": 1,
  "page_size": 25
}
```

**Response:**
```json
{
  "results": [
    {
      "unique_id": "uuid",
      "student_id": "ST12345",
      "full_name": "John Doe",
      "email": "john.doe@student.edu",
      "program": "Computer Science",
      "level": "Undergraduate",
      "status": "active",
      "photo_url": "/media/photos/student.jpg",
      "match_score": 0.95,
      "risk_score": 0.15,
      "success_prediction": 0.87,
      "last_activity": "2024-03-15T10:30:00Z",
      "enrollment_count": 5,
      "attendance_rate": 0.92
    }
  ],
  "total_count": 150,
  "page": 1,
  "has_next": true
}
```

### Student Analytics

```http
GET /api/v2/students/{student_id}/analytics/
```

**Response:**
```json
{
  "success_prediction": 0.87,
  "risk_factors": ["low_attendance", "payment_overdue"],
  "performance_trend": "improving",
  "attendance_rate": 0.85,
  "grade_average": 82.5,
  "payment_status": "current",
  "engagement_score": 0.78
}
```

### Bulk Operations

```http
POST /api/v2/students/bulk-actions/
```

**Request:**
```json
{
  "action": "update_status",
  "target_ids": ["uuid1", "uuid2", "uuid3"],
  "parameters": {"status": "graduated"},
  "dry_run": false
}
```

**Response:**
```json
{
  "success_count": 2,
  "failure_count": 1,
  "total_count": 3,
  "successes": [
    {"id": "uuid1", "message": "Status updated to graduated"},
    {"id": "uuid2", "message": "Status updated to graduated"}
  ],
  "failures": [
    {"id": "uuid3", "error": "Student not found"}
  ],
  "dry_run": false
}
```

### Student Timeline

```http
GET /api/v2/students/{student_id}/timeline/
```

**Features:**
- Multi-source event aggregation
- Event type filtering
- Pagination with performance optimization
- Real-time updates

## Innovation API (AI/ML & Automation)

### AI Predictions

```http
POST /api/v2/innovation/ai/predictions/
```

**Student Success Prediction:**
```json
{
  "model_type": "success_prediction",
  "input_data": {"student_id": "uuid"},
  "confidence_threshold": 0.7
}
```

**Response:**
```json
{
  "prediction": 0.87,
  "confidence": 0.92,
  "model_version": "success_v1.2",
  "features_used": ["attendance_rate", "grade_average", "payment_health"],
  "explanation": "Based on 3 key factors including attendance, grades, and payments",
  "recommendations": [
    "Maintain current study habits",
    "Consider leadership opportunities"
  ]
}
```

**Risk Assessment:**
```json
{
  "model_type": "risk_assessment",
  "input_data": {"student_id": "uuid"},
  "confidence_threshold": 0.8
}
```

**Scholarship Matching:**
```json
{
  "model_type": "scholarship_matching",
  "input_data": {"student_id": "uuid"},
  "confidence_threshold": 0.6
}
```

### Workflow Automation

```http
GET /api/v2/innovation/automation/workflows/
```

**Available Workflows:**
- Student welcome sequence automation
- Payment reminder automation
- Grade posting notifications
- Risk intervention triggers

```http
POST /api/v2/innovation/automation/workflows/{workflow_id}/execute/
```

### Document Intelligence

```http
POST /api/v2/innovation/documents/ocr/
```

**Features:**
- Multi-format support (PDF, JPEG, PNG, TIFF)
- High-accuracy OCR with confidence scoring
- Entity extraction and classification
- Structured data output

**Request:**
```http
Content-Type: multipart/form-data

document: <file>
```

**Response:**
```json
{
  "document_id": "uuid",
  "confidence_score": 0.94,
  "extracted_text": "STUDENT TRANSCRIPT\nName: John Doe...",
  "entities": [
    {"type": "person", "value": "John Doe", "confidence": 0.95},
    {"type": "student_id", "value": "ST12345", "confidence": 0.98}
  ],
  "processed_data": {
    "document_type": "transcript",
    "student_name": "John Doe",
    "gpa": 3.75
  },
  "processing_time": 2.3
}
```

### Real-time Communications

```http
GET /api/v2/innovation/communications/threads/
```

**Message Thread Management:**
- Thread listing with pagination
- Message history retrieval
- File attachment support
- Real-time messaging via WebSockets

```http
POST /api/v2/innovation/communications/threads/{thread_id}/messages/
```

### Custom Analytics

```http
GET /api/v2/innovation/analytics/custom/dashboard/
```

**Features:**
- Dynamic chart generation
- Multiple visualization types (line, bar, pie, area)
- Real-time data updates
- Customizable time ranges and filters

**Query Parameters:**
```
?metrics=enrollment_trends,grade_distribution,revenue_forecast
```

## Academic Management API

### Grade Entry Spreadsheet

```http
GET /api/v2/academics/grades/spreadsheet/{class_id}/
```

**Features:**
- Grid-style grade entry interface
- Real-time collaboration support
- Automatic calculation and validation
- Bulk update capabilities

### Schedule Conflict Detection

```http
POST /api/v2/academics/schedule/conflicts/
```

**Real-time Conflict Analysis:**
- Time overlap detection
- Resource conflict identification
- Capacity validation
- Alternative suggestions

### QR Code Attendance

```http
POST /api/v2/academics/attendance/qr-scan/
```

**Features:**
- QR code generation and validation
- Mobile-optimized scanning
- Real-time attendance processing
- Bulk attendance updates

## Financial Management API

### Point of Sale (POS)

```http
POST /api/v2/finance/pos/transaction/
```

**Request:**
```json
{
  "amount": "150.00",
  "payment_method": "credit_card",
  "student_id": "uuid",
  "description": "Tuition payment",
  "line_items": [
    {"item": "Tuition", "amount": "150.00", "quantity": 1}
  ],
  "metadata": {"terminal_id": "POS001", "cashier": "user123"}
}
```

### Financial Analytics

```http
GET /api/v2/finance/analytics/
```

**Features:**
- Revenue forecasting
- Payment trend analysis
- Payment method breakdown
- Overdue payment tracking

## GraphQL API

### Endpoint

```
POST /api/v2/graphql/
```

### Dashboard Metrics Query

```graphql
query DashboardMetrics($dateRange: Int!) {
  dashboardMetrics(dateRangeDays: $dateRange) {
    studentMetrics {
      totalCount {
        value
        trend
        changePercent
      }
      atRiskCount {
        value
        trend
      }
      successRate {
        value
        trend
      }
    }
    financialMetrics {
      totalRevenue {
        value
        trend
        changePercent
      }
      pendingPayments {
        value
        trend
      }
    }
    lastUpdated
  }
}
```

### Real-time Subscriptions

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

```graphql
subscription DashboardUpdates {
  dashboardMetricsUpdates {
    metrics {
      studentMetrics {
        totalCount { value }
      }
    }
    updatedFields
    timestamp
  }
}
```

## WebSocket API

### Grade Entry Collaboration

```
ws://localhost:8000/ws/grades/live-entry/<class_id>/
```

**Message Types:**
- `grade_update` - Real-time grade changes
- `field_lock` - Field locking for collaboration
- `cursor_position` - Live cursor tracking

**Example Message:**
```json
{
  "type": "grade_update",
  "student_id": "uuid",
  "assignment_id": "uuid",
  "field_name": "score",
  "value": 85.5,
  "timestamp": "2024-03-15T10:30:00Z"
}
```

### Dashboard Metrics

```
ws://localhost:8000/ws/dashboard/metrics/
```

**Real-time Updates:**
- Student count changes
- Financial metrics updates
- System health monitoring
- Performance metrics

### Communications

```
ws://localhost:8000/ws/communications/<room_id>/
```

**Features:**
- Real-time messaging
- Typing indicators
- Read receipts
- File sharing notifications

## Performance & Caching

### Cache Strategy

| Data Type | TTL | Strategy |
|-----------|-----|----------|
| Real-time metrics | 1 min | Very Short |
| Dashboard data | 5 min | Short |
| Search results | 15 min | Medium |
| Student analytics | 15 min | Medium |
| Course data | 1 hour | Long |
| System config | 24 hours | Very Long |

### Performance Targets

| Endpoint | Target Response Time |
|----------|---------------------|
| Student search | < 300ms |
| Analytics queries | < 500ms |
| AI predictions | < 2s (first call), < 100ms (cached) |
| GraphQL queries | < 400ms |
| WebSocket messages | < 50ms |

### Rate Limiting

- **Standard endpoints**: 1000 requests/hour per user
- **AI predictions**: 100 requests/hour per user
- **File uploads**: 50 uploads/hour per user
- **WebSocket connections**: 10 concurrent per user

## Error Handling

### Standard Error Response

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "student_id",
      "issue": "Invalid UUID format"
    },
    "timestamp": "2024-03-15T10:30:00Z",
    "request_id": "req_123456"
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 422 | Input validation failed |
| `NOT_FOUND` | 404 | Resource not found |
| `PERMISSION_DENIED` | 403 | Insufficient permissions |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `AI_MODEL_ERROR` | 500 | AI prediction failed |
| `CACHE_ERROR` | 500 | Cache operation failed |

## Security

### Authentication
- JWT tokens with 24-hour expiration
- Refresh token rotation
- Role-based access control (RBAC)

### Data Protection
- All endpoints require authentication
- Sensitive data encrypted at rest
- API request/response logging
- Input validation and sanitization

### File Upload Security
- File type validation
- Size limits (10MB for documents, 5MB for images)
- Virus scanning integration
- Secure file storage with access controls

## Development & Testing

### OpenAPI Schema
- Auto-generated documentation at `/api/v2/docs/`
- Interactive API explorer
- Schema export for client generation

### Testing
- Comprehensive test suite with >90% coverage
- Performance benchmarking
- Load testing capabilities
- GraphQL query testing

### Monitoring
- API response time tracking
- Error rate monitoring
- Cache hit rate analysis
- WebSocket connection health

## Migration from V1

### Breaking Changes
- New authentication system
- Enhanced response formats
- Additional required fields for some endpoints

### Compatibility
- V1 endpoints remain available during transition
- Gradual migration path provided
- Data migration tools available

### Timeline
- V2 Beta: Available now
- V2 Production: Q2 2024
- V1 Deprecation: Q4 2024

## SDK and Client Libraries

### Available SDKs
- JavaScript/TypeScript (React, Vue, Angular)
- Python (Django, FastAPI integration)
- Mobile (React Native, Flutter)

### GraphQL Code Generation
- Automatic TypeScript type generation
- Query optimization and caching
- Real-time subscription support

## Support

- **Documentation**: [https://docs.naga.edu.kh/api/v2/](https://docs.naga.edu.kh/api/v2/)
- **Issue Tracker**: [GitHub Issues](https://github.com/pannasastra/naga-sis/issues)
- **Community**: [Discord Server](https://discord.gg/naga-sis)
- **Email**: api-support@naga.edu.kh