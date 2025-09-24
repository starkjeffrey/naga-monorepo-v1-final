# Naga SIS Architecture Documentation

## Table of Contents

1. [Overview](#overview)
2. [Clean Architecture Principles](#clean-architecture-principles)
3. [System Architecture](#system-architecture)
4. [Django Apps Structure](#django-apps-structure)
5. [Data Flow](#data-flow)
6. [API Design](#api-design)
7. [Security Architecture](#security-architecture)
8. [Performance Architecture](#performance-architecture)
9. [Deployment Architecture](#deployment-architecture)
10. [Decision Records](#decision-records)

## Overview

The Naga Student Information System follows clean architecture principles to create a maintainable, scalable, and testable system. This document outlines the architectural decisions, patterns, and structures used throughout the project.

## Clean Architecture Principles

### Core Principles

1. **Dependency Rule**: Dependencies point inward toward business logic
2. **Separation of Concerns**: Each layer has a specific responsibility
3. **Independence**: Business logic is independent of frameworks, UI, and databases
4. **Testability**: Business logic can be tested without external dependencies

### Architectural Layers

```
┌─────────────────────────────────────────────────────────┐
│                    Presentation Layer                    │
│         (Django Views, django-ninja API, Templates)      │
├─────────────────────────────────────────────────────────┤
│                    Application Layer                     │
│              (Use Cases, Service Classes)                │
├─────────────────────────────────────────────────────────┤
│                     Domain Layer                         │
│           (Models, Business Rules, Entities)             │
├─────────────────────────────────────────────────────────┤
│                  Infrastructure Layer                    │
│      (Database, External APIs, File System, Cache)       │
└─────────────────────────────────────────────────────────┘
```

## System Architecture

### High-Level Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Vue.js PWA    │     │  Mobile Apps    │     │  External APIs  │
│   (Frontend)    │     │   (Capacitor)   │     │   (Keycloak)    │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                         │
         └───────────────────────┴─────────────────────────┘
                                 │
                         ┌───────▼────────┐
                         │  Load Balancer │
                         │    (Nginx)     │
                         └───────┬────────┘
                                 │
         ┌───────────────────────┴─────────────────────────┐
         │                                                 │
    ┌────▼─────┐                                    ┌─────▼────┐
    │  Django  │                                    │  Django  │
    │ Instance │                                    │ Instance │
    └────┬─────┘                                    └─────┬────┘
         │                                                 │
         └───────────────────────┬─────────────────────────┘
                                 │
                 ┌───────────────┴──────────────┐
                 │                              │
          ┌──────▼──────┐              ┌───────▼──────┐
          │ PostgreSQL  │              │    Redis     │
          │  (Primary)  │              │   (Cache)    │
          └─────────────┘              └──────────────┘
```

### Component Architecture

```yaml
Frontend Components:
  - Vue 3 Composition API
  - Quasar Framework UI
  - Pinia State Management
  - Vue Router Navigation
  - Axios HTTP Client
  - IndexedDB Offline Storage

Backend Components:
  - Django 5.2+ Framework
  - django-ninja REST API
  - PostgreSQL Database
  - Redis Cache & Sessions
  - Dramatiq Task Queue
  - Celery Beat Scheduler

Infrastructure Components:
  - Docker Containers
  - Nginx Reverse Proxy
  - Prometheus Monitoring
  - Grafana Dashboards
  - Sentry Error Tracking
  - GitHub Actions CI/CD
```

## Django Apps Structure

### Layer Organization

```
Foundation Layer (No dependencies on other apps):
├── common/        # Shared utilities, base models, audit logging
├── accounts/      # User authentication and authorization
├── geography/     # Locations and geographic data
└── facilities/    # Buildings and room management

Domain Layer (Core business entities):
├── people/        # Person profiles, students, staff
├── curriculum/    # Courses, programs, academic terms
├── academic/      # Requirements, prerequisites, graduation
└── scheduling/    # Class schedules and time management

Business Logic Layer (Complex operations):
├── enrollment/    # Student registration and enrollment
├── finance/       # Billing, payments, pricing
├── scholarships/  # Financial aid and sponsorships
├── grading/       # Grade management and GPA calculation
└── attendance/    # Class attendance tracking

Service Layer (External interfaces):
├── documents/     # Document generation and management
├── workflow/      # Business process automation
├── moodle/        # LMS integration
└── mobile/        # Mobile-specific APIs
```

### Dependency Rules

1. **Foundation Layer**: No dependencies on other apps
2. **Domain Layer**: May depend only on Foundation Layer
3. **Business Logic Layer**: May depend on Domain and Foundation
4. **Service Layer**: May depend on all lower layers

### App Communication Patterns

```python
# Good: Service class pattern
from apps.enrollment.services import EnrollmentService
from apps.finance.services import BillingService

class CourseRegistrationService:
    def register_student(self, student_id, course_id):
        # Use services to coordinate between apps
        enrollment = EnrollmentService.create_enrollment(student_id, course_id)
        invoice = BillingService.create_invoice(enrollment)
        return enrollment, invoice

# Bad: Direct model imports create circular dependencies
# from apps.finance.models import Invoice  # AVOID THIS!
```

## Data Flow

### Request Processing Flow

```
1. HTTP Request → Nginx
2. Nginx → Django ASGI Server (Uvicorn)
3. Django Middleware Pipeline
   - Security Middleware
   - Authentication Middleware
   - Session Middleware
   - Custom Audit Middleware
4. URL Router → View/API Endpoint
5. View → Service Layer
6. Service → Domain Models
7. Domain Models → Database
8. Response flows back through layers
```

### Data Processing Patterns

#### Command Query Responsibility Segregation (CQRS)

```python
# Write Operations (Commands)
class StudentEnrollmentCommand:
    def execute(self, student_id: str, program_id: str) -> Enrollment:
        # Complex business logic for enrollment
        # Validation, prerequisites, capacity checks
        # Transaction management
        # Event publishing
        pass

# Read Operations (Queries)
class StudentTranscriptQuery:
    def get_transcript(self, student_id: str) -> TranscriptData:
        # Optimized read-only query
        # May use different database or cache
        # No business logic, just data retrieval
        pass
```

#### Event-Driven Architecture

```python
# Domain Events
class StudentEnrolledEvent:
    student_id: str
    course_id: str
    term_id: str
    timestamp: datetime

# Event Handlers
class BillingEventHandler:
    def handle_student_enrolled(self, event: StudentEnrolledEvent):
        # Create invoice for enrolled course
        pass

class NotificationEventHandler:
    def handle_student_enrolled(self, event: StudentEnrolledEvent):
        # Send confirmation email
        pass
```

## API Design

### RESTful Principles

1. **Resource-Based**: URLs represent resources, not actions
2. **HTTP Methods**: GET, POST, PUT, PATCH, DELETE with proper semantics
3. **Status Codes**: Appropriate HTTP status codes for all responses
4. **Stateless**: No session state stored on server
5. **HATEOAS**: Hypermedia links for resource navigation

### API Versioning Strategy

```python
# URL-based versioning
api_v1 = NinjaAPI(version="1.0.0", urls_namespace="v1")
api_v2 = NinjaAPI(version="2.0.0", urls_namespace="v2")

# Header-based versioning for specific endpoints
@api.get("/resource/")
def get_resource(request, version: str = Header("X-API-Version")):
    if version == "2.0":
        return ResourceV2Schema
    return ResourceV1Schema
```

### Schema Design

```python
# Input validation with Pydantic
class CourseCreateSchema(Schema):
    code: str = Field(..., min_length=3, max_length=10)
    name: str = Field(..., min_length=5, max_length=100)
    credits: int = Field(..., ge=1, le=6)
    prerequisites: List[str] = []
    
    @validator('code')
    def validate_code_format(cls, v):
        if not re.match(r'^[A-Z]{2,4}\d{3}$', v):
            raise ValueError('Invalid course code format')
        return v

# Output serialization
class CourseResponseSchema(Schema):
    id: int
    code: str
    name: str
    credits: int
    prerequisites: List[CourseMinimalSchema]
    created_at: datetime
    updated_at: datetime
    _links: Dict[str, str]  # HATEOAS links
```

## Security Architecture

### Authentication & Authorization

```
┌─────────────────┐
│   User Login    │
└────────┬────────┘
         │
    ┌────▼────┐
    │Keycloak │──────┐ SSO Integration
    └────┬────┘      │
         │           │
    ┌────▼────┐      │
    │  JWT    │◄─────┘
    │ Token   │
    └────┬────┘
         │
    ┌────▼────────┐
    │   Django    │
    │ Middleware  │
    └────┬────────┘
         │
    ┌────▼────────┐
    │ Permission  │
    │   Check     │
    └─────────────┘
```

### Security Layers

1. **Network Security**
   - SSL/TLS encryption
   - Firewall rules
   - DDoS protection

2. **Application Security**
   - Input validation
   - SQL injection prevention
   - XSS protection
   - CSRF tokens

3. **Data Security**
   - Encryption at rest
   - Encryption in transit
   - PII data masking
   - Audit logging

### Role-Based Access Control (RBAC)

```python
# Permission structure
class Permissions:
    # Resource-based permissions
    STUDENT_VIEW_OWN = "student.view_own"
    STUDENT_VIEW_ALL = "student.view_all"
    STUDENT_CREATE = "student.create"
    STUDENT_UPDATE = "student.update"
    STUDENT_DELETE = "student.delete"
    
    # Role definitions
    ROLES = {
        "student": [STUDENT_VIEW_OWN],
        "teacher": [STUDENT_VIEW_ALL],
        "admin": [STUDENT_VIEW_ALL, STUDENT_CREATE, STUDENT_UPDATE],
        "superadmin": ["*"]  # All permissions
    }
```

## Performance Architecture

### Caching Strategy

```
┌─────────────┐
│   Request   │
└──────┬──────┘
       │
┌──────▼──────┐
│ CDN Cache   │ Static assets
└──────┬──────┘
       │
┌──────▼──────┐
│Redis Cache  │ Session data, frequent queries
└──────┬──────┘
       │
┌──────▼──────┐
│ DB Query    │ Query optimization, indexing
│   Cache     │
└──────┬──────┘
       │
┌──────▼──────┐
│ PostgreSQL  │
└─────────────┘
```

### Performance Optimization Techniques

1. **Database Optimization**
   - Proper indexing strategy
   - Query optimization
   - Connection pooling
   - Read replicas for reports

2. **Application Optimization**
   - Lazy loading
   - Pagination
   - Async processing
   - Response compression

3. **Frontend Optimization**
   - Code splitting
   - Lazy routing
   - Image optimization
   - Service worker caching

### Scalability Patterns

```yaml
Horizontal Scaling:
  - Multiple Django instances
  - Load balancer distribution
  - Shared session storage (Redis)
  - Stateless application design

Vertical Scaling:
  - Database connection pooling
  - Query optimization
  - Caching layers
  - Background job processing

Data Partitioning:
  - Sharding by institution
  - Archive old data
  - Separate OLTP/OLAP databases
  - CDN for static assets
```

## Deployment Architecture

### Container Architecture

```dockerfile
# Multi-stage build for optimization
FROM python:3.13.7-slim as builder
# Build dependencies

FROM python:3.13.7-slim as runtime
# Runtime optimized image
```

### Environment Configuration

```yaml
Environments:
  Development:
    - Local Docker Compose
    - Hot reloading
    - Debug enabled
    - SQLite for testing
    
  Staging:
    - Production-like setup
    - Real database
    - Performance testing
    - Integration testing
    
  Production:
    - High availability
    - Auto-scaling
    - Monitoring
    - Backup strategies
```

### CI/CD Pipeline

```
┌────────┐     ┌────────┐     ┌────────┐     ┌────────┐
│  Code  │────▶│  Test  │────▶│ Build  │────▶│Deploy  │
│ Commit │     │  Suite │     │ Images │     │  Prod  │
└────────┘     └────────┘     └────────┘     └────────┘
                    │              │               │
                    ▼              ▼               ▼
               Unit Tests    Security Scan   Blue-Green
               Lint/Format   Optimization    Health Check
               Type Check    Multi-arch      Rollback
```

## Decision Records

### ADR-001: Django Ninja over Django REST Framework

**Status**: Accepted  
**Date**: 2024-01-01

**Context**: Need for a modern, fast, type-safe API framework

**Decision**: Use django-ninja instead of Django REST Framework

**Consequences**:
- ✅ Better performance (3-5x faster)
- ✅ Type safety with Pydantic
- ✅ Modern Python 3.8+ features
- ✅ Automatic API documentation
- ❌ Smaller ecosystem
- ❌ Less community resources

### ADR-002: Clean Architecture Implementation

**Status**: Accepted  
**Date**: 2024-01-05

**Context**: Previous version had circular dependency issues

**Decision**: Implement strict clean architecture with layered apps

**Consequences**:
- ✅ No circular dependencies
- ✅ Clear separation of concerns
- ✅ Easier testing
- ✅ Better maintainability
- ❌ More initial complexity
- ❌ Learning curve for team

### ADR-003: Event-Driven Architecture for Inter-App Communication

**Status**: Accepted  
**Date**: 2024-01-10

**Context**: Need for loose coupling between apps

**Decision**: Use domain events and service classes for communication

**Consequences**:
- ✅ Loose coupling
- ✅ Easier to add new features
- ✅ Better testability
- ❌ More complex debugging
- ❌ Potential event ordering issues

### ADR-004: PostgreSQL as Primary Database

**Status**: Accepted  
**Date**: 2024-01-01

**Context**: Need for reliable, scalable database with good Django support

**Decision**: Use PostgreSQL 16 as primary database

**Consequences**:
- ✅ Excellent Django support
- ✅ ACID compliance
- ✅ Advanced features (JSON, arrays, full-text search)
- ✅ Good performance
- ❌ More complex than SQLite
- ❌ Requires more resources

## Best Practices

### Code Organization

1. **Single Responsibility**: Each module/class has one reason to change
2. **DRY Principle**: Don't Repeat Yourself - use service classes
3. **YAGNI**: You Aren't Gonna Need It - avoid over-engineering
4. **Explicit is Better**: Clear, readable code over clever solutions

### Testing Strategy

```python
# Unit Tests - Test business logic in isolation
def test_calculate_gpa():
    grades = [Grade(points=4.0), Grade(points=3.7)]
    assert calculate_gpa(grades) == 3.85

# Integration Tests - Test component interaction
def test_enrollment_creates_invoice():
    enrollment = EnrollmentService.create(student, course)
    assert Invoice.objects.filter(enrollment=enrollment).exists()

# E2E Tests - Test complete workflows
def test_student_registration_flow():
    # Test from API request to database
    response = client.post("/api/register/", data)
    assert response.status_code == 201
    assert Student.objects.filter(email=data["email"]).exists()
```

### Documentation Standards

1. **Code Documentation**: Docstrings for all public methods
2. **API Documentation**: OpenAPI/Swagger specifications
3. **Architecture Documentation**: This document and ADRs
4. **User Documentation**: Guides and tutorials
5. **Inline Comments**: Explain "why", not "what"

## Monitoring and Observability

### Metrics Collection

```yaml
Business Metrics:
  - Active students
  - Course enrollment rates
  - Payment processing time
  - Document generation time

Technical Metrics:
  - Response time percentiles
  - Error rates
  - Database query time
  - Cache hit rates

Infrastructure Metrics:
  - CPU/Memory usage
  - Disk I/O
  - Network throughput
  - Container health
```

### Logging Strategy

```python
# Structured logging
logger.info("student_enrolled", extra={
    "student_id": student.id,
    "course_id": course.id,
    "term_id": term.id,
    "timestamp": datetime.now(),
    "ip_address": request.META.get("REMOTE_ADDR")
})

# Log levels
DEBUG: Detailed diagnostic information
INFO: General informational messages
WARNING: Warning messages for concerning behavior
ERROR: Error conditions that need attention
CRITICAL: Critical issues requiring immediate action
```

## Future Considerations

### Planned Enhancements

1. **Microservices Migration** (Phase 2)
   - Extract billing service
   - Separate notification service
   - Independent scaling

2. **GraphQL API** (Evaluation)
   - For complex data requirements
   - Mobile app optimization
   - Real-time subscriptions

3. **AI/ML Integration**
   - Student success prediction
   - Automated scheduling optimization
   - Chatbot support

4. **Blockchain** (Research)
   - Credential verification
   - Tamper-proof transcripts
   - Cross-institution transfers