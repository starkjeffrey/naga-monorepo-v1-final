# Web Interface API Endpoints Documentation

## Overview

The `web_interface` app provides HTTP endpoints for the Naga SIS web-based user interface. All endpoints are designed to work with HTMX for dynamic content loading and form submissions, while maintaining compatibility with traditional HTTP requests.

## Authentication

All endpoints require authentication except the login page. Users are redirected to the login page if not authenticated.

```python
# All views inherit from LoginRequiredMixin
class BaseView(LoginRequiredMixin):
    login_url = '/web/login/'
```

## Endpoint Categories

### Authentication Endpoints

| Endpoint | Method | Description | View Class | Template |
|----------|---------|-------------|------------|----------|
| `/web/` | GET | Login page (root redirect) | `auth_views.LoginView` | `login.html` |
| `/web/login/` | GET, POST | User login | `auth_views.LoginView` | `login.html` |
| `/web/logout/` | POST | User logout | `auth_views.LogoutView` | - |
| `/web/role-switch/` | POST | Switch user role | `auth_views.RoleSwitchView` | - |

#### Authentication Details

**Login Endpoint (`/web/login/`)**

```http
POST /web/login/
Content-Type: application/x-www-form-urlencoded

email=user@example.com&password=secret&next=/web/dashboard/
```

Response (JSON for AJAX requests):
```json
{
  "success": true,
  "redirect_url": "/web/dashboard/",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "current_role": "admin"
  }
}
```

**Role Switch Endpoint (`/web/role-switch/`)**

```http
POST /web/role-switch/
Content-Type: application/json

{"role": "teacher"}
```

Response:
```json
{
  "success": true,
  "current_role": "teacher",
  "navigation": [...] 
}
```

### Dashboard Endpoints

| Endpoint | Method | Description | Permissions | HTMX Support |
|----------|---------|-------------|-------------|---------------|
| `/web/dashboard/` | GET | Role-specific dashboard | Any authenticated user | ✅ |

**Dashboard Response Structure:**

```http
GET /web/dashboard/
HX-Request: true
```

Returns role-specific HTML content with statistics:

```html
<!-- Admin Dashboard -->
<div class="dashboard-stats">
    <div class="stat-card">
        <h3>1,234</h3>
        <p>Total Students</p>
    </div>
    <div class="stat-card">
        <h3>45</h3>
        <p>Active Classes</p>
    </div>
</div>
```

### Student Management Endpoints

| Endpoint | Method | Description | Permissions | HTMX Support |
|----------|---------|-------------|-------------|---------------|
| `/web/students/` | GET | Student list with search/filter | Admin, Staff | ✅ |
| `/web/students/new/` | GET, POST | Create new student | Admin, Staff | ✅ |
| `/web/students/<pk>/` | GET | Student detail view | Admin, Staff, Student (own) | ✅ |
| `/web/students/<pk>/edit/` | GET, POST | Edit student | Admin, Staff | ✅ |
| `/web/students/<pk>/enrollment/` | GET | Student enrollment history | Admin, Staff, Student (own) | ✅ |

**Student List Endpoint (`/web/students/`)**

Query Parameters:
- `search`: Search term for name, student_id, email
- `status`: Filter by student status
- `program`: Filter by program
- `page`: Pagination
- `page_size`: Items per page (10, 25, 50, 100)

```http
GET /web/students/?search=john&status=ACTIVE&page=2&page_size=25
HX-Request: true
```

Response (HTMX partial):
```html
<div class="student-list">
    <div class="student-row" data-student-id="123">
        <div class="student-info">
            <strong>John Doe</strong>
            <span class="student-id">S001</span>
            <span class="badge badge-success">Active</span>
        </div>
        <div class="student-actions">
            <a href="/web/students/123/" class="btn btn-sm btn-outline-primary">View</a>
            <button data-modal-url="/web/modals/student-edit/123/" class="btn btn-sm btn-outline-secondary">Edit</button>
        </div>
    </div>
</div>
```

**Student Create Endpoint (`/web/students/new/`)**

```http
POST /web/students/new/
Content-Type: application/x-www-form-urlencoded
HX-Request: true

personal_name=Jane&family_name=Smith&student_id=S002&admission_date=2024-01-15
```

Success Response (JSON):
```json
{
  "success": true,
  "message": "Student created successfully",
  "redirect_url": "/web/students/124/",
  "student_id": 124
}
```

Error Response (HTML form with errors):
```html
<form hx-post="/web/students/new/" hx-target="#form-container">
    <div class="form-group">
        <label>Student ID</label>
        <input type="text" name="student_id" value="S002" class="form-control is-invalid">
        <div class="invalid-feedback">Student ID already exists</div>
    </div>
</form>
```

### Academic Management Endpoints

| Endpoint | Method | Description | Permissions | HTMX Support |
|----------|---------|-------------|-------------|---------------|
| `/web/academic/courses/` | GET | Course list | Admin, Staff | ✅ |
| `/web/academic/enrollment/` | GET, POST | Enrollment management | Admin, Staff | ✅ |
| `/web/academic/grades/` | GET, POST | Grade management | Admin, Staff, Teacher | ✅ |
| `/web/academic/schedules/` | GET | Schedule management | Admin, Staff | ✅ |
| `/web/academic/transcripts/` | GET | Transcript management | Admin, Staff | ✅ |

**Course List Endpoint (`/web/academic/courses/`)**

```http
GET /web/academic/courses/?search=english&active=true
HX-Request: true
```

Response:
```html
<div class="course-grid">
    <div class="course-card" data-course-id="ENG101">
        <h4>ENG101 - English Basics</h4>
        <p>Credits: 3 | Status: Active</p>
        <div class="course-actions">
            <button class="btn btn-sm btn-primary">View Students</button>
            <button class="btn btn-sm btn-outline-secondary">Edit Course</button>
        </div>
    </div>
</div>
```

### Finance Management Endpoints

| Endpoint | Method | Description | Permissions | HTMX Support |
|----------|---------|-------------|-------------|---------------|
| `/web/finance/billing/` | GET | Billing and invoice list | Admin, Finance | ✅ |
| `/web/finance/invoice/<pk>/` | GET | Invoice detail | Admin, Finance | ✅ |
| `/web/finance/invoice/create/` | GET, POST | Create invoice | Admin, Finance | ✅ |
| `/web/finance/payments/` | GET, POST | Payment processing | Admin, Finance | ✅ |
| `/web/finance/payments/quick/` | GET, POST | Quick payment entry | Admin, Finance | ✅ |
| `/web/finance/accounts/<student_id>/` | GET | Student account view | Admin, Finance | ✅ |
| `/web/finance/cashier/` | GET, POST | Cashier session | Admin, Finance | ✅ |
| `/web/finance/reports/` | GET | Financial reports | Admin, Finance | ✅ |

**Billing List Endpoint (`/web/finance/billing/`)**

Query Parameters:
- `status`: Invoice status filter (DRAFT, SENT, PAID, OVERDUE)
- `student`: Student filter
- `date_from`: Start date filter
- `date_to`: End date filter
- `amount_min`: Minimum amount
- `amount_max`: Maximum amount

```http
GET /web/finance/billing/?status=OVERDUE&date_from=2024-01-01&student=123
HX-Request: true
```

Response:
```html
<div class="invoice-list">
    <div class="invoice-row" data-invoice-id="INV-001">
        <div class="invoice-info">
            <strong>INV-001</strong>
            <span>Jane Smith (S002)</span>
            <span class="badge badge-danger">Overdue</span>
        </div>
        <div class="invoice-amount">$1,250.00</div>
        <div class="invoice-actions">
            <button data-modal-url="/web/modals/payment-process/INV-001/" class="btn btn-sm btn-success">Process Payment</button>
        </div>
    </div>
</div>
```

**Quick Payment Endpoint (`/web/finance/payments/quick/`)**

```http
POST /web/finance/payments/quick/
Content-Type: application/json
HX-Request: true

{
  "student_id": "S002",
  "amount": 500.00,
  "payment_method": "CASH",
  "notes": "Partial payment for tuition"
}
```

Response:
```json
{
  "success": true,
  "message": "Payment processed successfully",
  "payment_id": "PAY-789",
  "receipt_url": "/web/finance/receipt/789/",
  "remaining_balance": 750.00
}
```

### Modal Endpoints

| Endpoint | Method | Description | Returns | HTMX Required |
|----------|---------|-------------|---------|---------------|
| `/web/modals/student/create/` | GET | Student creation modal | HTML modal | ✅ |
| `/web/modals/invoice/create/` | GET | Invoice creation modal | HTML modal | ✅ |
| `/web/modals/payment/process/` | GET | Payment processing modal | HTML modal | ✅ |
| `/web/modals/payment/quick/` | GET | Quick payment modal | HTML modal | ✅ |
| `/web/modals/confirmation/` | GET | Generic confirmation modal | HTML modal | ✅ |

**Modal Response Format:**

```html
<div id="modal-overlay" class="modal-overlay" onclick="closeModal()">
    <div class="modal-container" onclick="event.stopPropagation()">
        <div class="modal-header">
            <h3 class="modal-title">Create Student</h3>
            <button type="button" class="modal-close-btn" onclick="closeModal()">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="modal-body">
            <form hx-post="/web/students/new/" hx-target="#modal-container">
                <!-- form content -->
            </form>
        </div>
    </div>
</div>
```

### Search Endpoints

| Endpoint | Method | Description | Permissions | Response Format |
|----------|---------|-------------|-------------|-----------------|
| `/web/search/students/` | GET, POST | Student search | Admin, Staff, Teacher | HTML partial |
| `/web/search/finance/students/` | GET, POST | Student search for finance | Admin, Finance | HTML partial |

**Student Search Endpoint (`/web/search/students/`)**

```http
POST /web/search/students/
Content-Type: application/json
HX-Request: true

{"query": "jane smith"}
```

Response:
```html
<div class="search-results">
    <div class="search-result" data-student-id="124">
        <div class="result-info">
            <strong>Jane Smith</strong>
            <span>S002 | Computer Science</span>
        </div>
        <div class="result-actions">
            <button onclick="selectStudent(124)" class="btn btn-sm btn-primary">Select</button>
        </div>
    </div>
</div>
```

## HTMX Integration

### Headers

All HTMX requests include these headers:

```http
HX-Request: true
X-Requested-With: XMLHttpRequest
X-CSRFToken: <csrf_token>
```

### Response Patterns

**Successful Form Submission:**
```json
{
  "success": true,
  "message": "Operation completed successfully",
  "redirect_url": "/web/target-page/",
  "data": {...}
}
```

**Form Validation Errors:**
```html
<form hx-post="/web/endpoint/" hx-target="#form-container">
    <!-- form with error classes and messages -->
    <div class="form-group">
        <input type="text" class="form-control is-invalid">
        <div class="invalid-feedback">Error message</div>
    </div>
</form>
```

**Partial Content Updates:**
```html
<!-- Updated content that replaces target element -->
<div class="updated-content">
    <!-- new content -->
</div>
```

### HTMX Attributes Used

- `hx-get`: Load content on trigger
- `hx-post`: Submit form data
- `hx-target`: Specify update target
- `hx-swap`: Control swap method (innerHTML, outerHTML, etc.)
- `hx-trigger`: Specify trigger events
- `hx-vals`: Add extra values to request

## Error Handling

### HTTP Status Codes

- `200 OK`: Successful request
- `302 Found`: Redirect (authentication required)
- `400 Bad Request`: Form validation errors
- `403 Forbidden`: Permission denied
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

### Error Response Format

**Permission Denied (403):**
```json
{
  "error": "You don't have permission to access this resource",
  "required_roles": ["admin", "staff"],
  "user_roles": ["student"]
}
```

**Validation Error (400):**
```json
{
  "error": "Validation failed",
  "form_errors": {
    "student_id": ["Student ID already exists"],
    "email": ["Enter a valid email address"]
  }
}
```

### JavaScript Error Handling

```javascript
// HTMX error handling
document.addEventListener('htmx:responseError', (event) => {
    console.error('HTMX Error:', event.detail);
    DashboardApp.showAlert('An error occurred. Please try again.', 'error');
});
```

## Pagination

### Query Parameters

- `page`: Page number (1-based)
- `page_size`: Items per page (10, 25, 50, 100)

### Response Format

**HTML Response includes:**
```html
<div class="pagination-info">
    Showing 26-50 of 247 results
</div>

<nav class="pagination">
    <button hx-get="?page=1" hx-target="#content">First</button>
    <button hx-get="?page=2" hx-target="#content">Previous</button>
    <span class="current">3</span>
    <button hx-get="?page=4" hx-target="#content">Next</button>
    <button hx-get="?page=10" hx-target="#content">Last</button>
</nav>
```

## Rate Limiting

### Current Limits

- Search endpoints: 60 requests per minute per user
- Form submissions: 30 requests per minute per user
- General endpoints: 120 requests per minute per user

### Rate Limit Headers

```http
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1704067200
```

## Caching

### Cache Headers

Static content (CSS, JS, images):
```http
Cache-Control: public, max-age=3600
ETag: "abc123"
```

Dynamic content:
```http
Cache-Control: no-cache, no-store, must-revalidate
Pragma: no-cache
```

### Cache Invalidation

- Form submissions invalidate related list views
- Role changes invalidate navigation cache
- Student updates invalidate dashboard statistics

## Security Considerations

### CSRF Protection

All POST, PUT, DELETE requests require CSRF tokens:

```html
<input type="hidden" name="csrfmiddlewaretoken" value="{{ csrf_token }}">
```

HTMX requests automatically include CSRF tokens:

```javascript
htmx.config.beforeSend = function(xhr) {
    xhr.setRequestHeader('X-CSRFToken', DashboardApp.csrfToken);
};
```

### Permission Validation

Every view checks user permissions:

```python
class StudentListView(RoleBasedPermissionMixin, ListView):
    required_roles = ['admin', 'staff']
```

### Input Validation

All forms use Django form validation:

```python
class StudentCreateForm(forms.ModelForm):
    def clean_student_id(self):
        student_id = self.cleaned_data['student_id']
        if StudentProfile.objects.filter(student_id=student_id).exists():
            raise ValidationError('Student ID already exists')
        return student_id
```

## Testing Endpoints

### Using curl

**Login:**
```bash
curl -X POST http://localhost:8000/web/login/ \
     -d "email=admin@example.com&password=secret" \
     -c cookies.txt
```

**HTMX Request:**
```bash
curl -X GET http://localhost:8000/web/students/ \
     -H "HX-Request: true" \
     -b cookies.txt
```

### Using Python requests

```python
import requests

session = requests.Session()

# Login
login_data = {'email': 'admin@example.com', 'password': 'secret'}
session.post('http://localhost:8000/web/login/', data=login_data)

# HTMX request
headers = {'HX-Request': 'true', 'X-Requested-With': 'XMLHttpRequest'}
response = session.get('http://localhost:8000/web/students/', headers=headers)
```

## Performance Optimization

### Database Queries

Views use `select_related()` and `prefetch_related()` to minimize database queries:

```python
def get_queryset(self):
    return StudentProfile.objects.select_related(
        'person', 'program'
    ).prefetch_related(
        'enrollments__class_header__course'
    )
```

### Template Optimization

- Use template fragments for HTMX partials
- Minimize template inheritance depth
- Cache expensive template computations

### HTMX Optimization

- Use `hx-preserve` for elements that shouldn't be replaced
- Implement proper loading indicators
- Use `hx-swap` strategically to minimize DOM updates

## Conclusion

The web interface API provides a comprehensive set of endpoints for managing all aspects of the Naga SIS through a modern web interface. The HTMX integration enables dynamic user interactions while maintaining the simplicity and reliability of server-side rendering.