# API Documentation

## 🌐 API Specifications & Integration Guides

This directory contains comprehensive API documentation, specifications, and integration guides for the Naga SIS system.

## 📁 Contents

### API Specifications
- **api_documentation.json** - OpenAPI specifications for all endpoints
- **attendance_api_schemas.md** - Attendance system data schemas and validation
- **attendance_api_endpoints.md** - Attendance API endpoint documentation

### Integration Guides
- **mobile_api_guide.md** - Mobile app API integration patterns
- **necessary_mods_to_apis_250617.md** - Required API modifications and updates

## 🔧 API Architecture

### Framework & Standards
- **django-ninja** - Fast, type-safe API framework (NOT Django REST Framework)
- **OpenAPI/Swagger** - Auto-generated documentation at `/api/docs`
- **Type Safety** - Full TypeScript integration with runtime validation
- **Schema Sharing** - Django Models → OpenAPI → TypeScript → Zod validation

### API Design Principles
- **RESTful conventions** with clear resource hierarchies
- **Consistent error responses** with detailed error codes
- **Input validation** using Pydantic models
- **Rate limiting** and security controls
- **Versioning strategy** for API evolution

## 📱 Mobile API Integration

### Authentication & Security
- **Keycloak integration** for role-based access control
- **JWT tokens** for stateless authentication
- **CORS configuration** for web app access
- **API rate limiting** to prevent abuse

### Data Synchronization
- **Offline-first design** for mobile PWA
- **Incremental sync** for large datasets
- **Conflict resolution** for concurrent updates
- **Background sync** with service workers

## 🎯 API Endpoints Overview

### Core Endpoints
- `/api/students/` - Student management and profiles
- `/api/courses/` - Course catalog and scheduling
- `/api/enrollment/` - Student enrollment operations
- `/api/attendance/` - Attendance tracking and QR codes
- `/api/grading/` - Grade management and GPA calculation
- `/api/finance/` - Billing, payments, and financial records

### Business-Specific Endpoints
- `/api/scholarships/` - Scholarship and financial aid
- `/api/level-testing/` - Language level testing system
- `/api/documents/` - Document management and verification
- `/api/reports/` - Academic and financial reporting

## 🔍 API Development Workflow

### Schema Generation
```bash
# Generate TypeScript types from Django models
python manage.py generate_api_types

# Update frontend types
cd frontend && npm run update-types

# Validate API schema consistency
python manage.py validate_api_schema
```

### Testing Strategy
- **Unit tests** for individual endpoints
- **Integration tests** for complex workflows
- **Performance tests** for high-traffic endpoints
- **Security tests** for authentication and authorization

## 📊 API Monitoring

### Metrics Collection
- **Request/response times** via Prometheus
- **Error rates** by endpoint and status code
- **Authentication failures** and security events
- **Rate limiting** violations and patterns

### Business Metrics
- **Student enrollment** API usage patterns
- **Attendance tracking** QR code generation rates
- **Grade submission** timing and volume
- **Financial transaction** API security monitoring

## 🛡️ Security Standards

### Input Validation
- **Pydantic models** for request validation
- **SQL injection prevention** via ORM
- **XSS protection** with output encoding
- **CSRF protection** for state-changing operations

### Authentication & Authorization
- **Role-based permissions** via Keycloak
- **API key management** for external integrations
- **JWT token validation** and refresh handling
- **Audit logging** for sensitive operations

## 📚 Related Documentation
- [Development](../development/) - API development standards and workflow
- [Architecture](../architecture/) - API architecture and design patterns
- [Operations](../operations/) - API deployment and monitoring