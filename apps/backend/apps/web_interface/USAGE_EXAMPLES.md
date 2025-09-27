# Web Interface Usage Examples and Integration Guide

## Overview

This guide provides practical examples and integration patterns for working with the `web_interface` app. It demonstrates how to extend the interface, create new views, integrate with other Django apps, and implement custom functionality.

## Quick Start Example

### Creating a New Feature: Document Management

Let's walk through creating a complete document management feature from scratch.

#### 1. Add URL Routes

```python
# apps/web_interface/urls.py
urlpatterns = [
    # ... existing patterns ...
    
    # Document Management
    path("documents/", include([
        path("", document_views.DocumentListView.as_view(), name="document-list"),
        path("new/", document_views.DocumentCreateView.as_view(), name="document-create"),
        path("<int:pk>/", document_views.DocumentDetailView.as_view(), name="document-detail"),
        path("<int:pk>/download/", document_views.DocumentDownloadView.as_view(), name="document-download"),
    ])),
    
    # Modal endpoints
    path("modals/", include([
        # ... existing modals ...
        path("document/create/", modal_views.DocumentCreateModalView.as_view(), name="modal-document-create"),
        path("document/upload/", modal_views.DocumentUploadModalView.as_view(), name="modal-document-upload"),
    ])),
]
```

#### 2. Create View Classes

```python
# apps/web_interface/views/document_views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.views.generic import ListView, DetailView, CreateView
from django.urls import reverse_lazy

from apps.academic_records.models import Document  # Assuming documents app exists
from ..permissions import RoleBasedPermissionMixin
from ..utils import is_htmx_request

class DocumentListView(RoleBasedPermissionMixin, ListView):
    """List view for document management."""
    
    model = Document
    template_name = 'web_interface/pages/documents/document_list.html'
    context_object_name = 'documents'
    paginate_by = 25
    required_roles = ['admin', 'staff']
    
    def get_template_names(self):
        """Return HTMX partial template if request is from HTMX."""
        if is_htmx_request(self.request):
            return ['web_interface/pages/documents/document_list_content.html']
        return [self.template_name]
    
    def get_queryset(self):
        """Filter documents based on search and status."""
        queryset = Document.objects.select_related(
            'student__person', 'document_type'
        ).order_by('-created_at')
        
        # Search functionality
        search_query = self.request.GET.get('search', '').strip()
        if search_query:
            queryset = queryset.filter(
                Q(student__person__personal_name__icontains=search_query) |
                Q(student__person__family_name__icontains=search_query) |
                Q(student__student_id__icontains=search_query) |
                Q(document_type__name__icontains=search_query)
            )
        
        # Status filter
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        """Add extra context for the template."""
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'Document Management',
            'current_page': 'documents',
            'search_query': self.request.GET.get('search', ''),
            'status_filter': self.request.GET.get('status', ''),
            'status_choices': Document.STATUS_CHOICES,
        })
        return context


class DocumentDetailView(RoleBasedPermissionMixin, DetailView):
    """Detail view for individual documents."""
    
    model = Document
    template_name = 'web_interface/pages/documents/document_detail.html'
    context_object_name = 'document'
    required_roles = ['admin', 'staff']
    
    def get_queryset(self):
        return Document.objects.select_related(
            'student__person', 'document_type', 'created_by'
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': f'Document: {self.object}',
            'current_page': 'documents',
        })
        return context


class DocumentCreateView(RoleBasedPermissionMixin, CreateView):
    """Create view for new documents."""
    
    model = Document
    template_name = 'web_interface/pages/documents/document_create.html'
    fields = ['student', 'document_type', 'file', 'notes']
    required_roles = ['admin', 'staff']
    success_url = reverse_lazy('web_interface:document-list')
    
    def form_valid(self, form):
        """Set the created_by user before saving."""
        form.instance.created_by = self.request.user
        return super().form_valid(form)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'Create Document',
            'current_page': 'documents',
        })
        return context


class DocumentDownloadView(RoleBasedPermissionMixin, DetailView):
    """Download view for document files."""
    
    model = Document
    required_roles = ['admin', 'staff', 'student']
    
    def get_queryset(self):
        queryset = Document.objects.all()
        
        # Students can only download their own documents
        if self.request.user.person and hasattr(self.request.user.person, 'studentprofile'):
            student_profile = self.request.user.person.studentprofile
            queryset = queryset.filter(student=student_profile)
        
        return queryset
    
    def get(self, request, *args, **kwargs):
        """Return file download response."""
        document = self.get_object()
        
        if not document.file:
            raise Http404("File not found")
        
        response = HttpResponse(
            document.file.read(),
            content_type='application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="{document.file.name}"'
        return response
```

#### 3. Create Modal Views

```python
# apps/web_interface/views/modal_views.py (add to existing file)

class DocumentCreateModalView(RoleBasedPermissionMixin, TemplateView):
    """Modal view for creating documents."""
    
    template_name = 'web_interface/modals/document_create_modal.html'
    required_roles = ['admin', 'staff']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from apps.academic_records.forms import DocumentCreateForm
        context['form'] = DocumentCreateForm()
        
        # Get student from query params for pre-population
        student_id = self.request.GET.get('student_id')
        if student_id:
            try:
                from apps.people.models import StudentProfile
                student = StudentProfile.objects.get(pk=student_id)
                context['form'].initial['student'] = student
                context['preselected_student'] = student
            except StudentProfile.DoesNotExist:
                pass
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Handle form submission via HTMX."""
        from apps.academic_records.forms import DocumentCreateForm
        
        form = DocumentCreateForm(request.POST, request.FILES)
        
        if form.is_valid():
            document = form.save(commit=False)
            document.created_by = request.user
            document.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Document created successfully',
                'redirect_url': reverse('web_interface:document-list')
            })
        else:
            # Return form with errors
            context = self.get_context_data()
            context['form'] = form
            return render(request, self.template_name, context, status=400)


class DocumentUploadModalView(RoleBasedPermissionMixin, TemplateView):
    """Modal view for bulk document upload."""
    
    template_name = 'web_interface/modals/document_upload_modal.html'
    required_roles = ['admin', 'staff']
    
    def post(self, request, *args, **kwargs):
        """Handle multiple file upload."""
        files = request.FILES.getlist('files')
        student_id = request.POST.get('student_id')
        document_type_id = request.POST.get('document_type_id')
        
        if not files:
            return JsonResponse({'error': 'No files selected'}, status=400)
        
        try:
            from apps.people.models import StudentProfile
            from apps.academic_records.models import DocumentType
            
            student = StudentProfile.objects.get(pk=student_id)
            document_type = DocumentType.objects.get(pk=document_type_id)
            
            created_documents = []
            
            for file in files:
                document = Document.objects.create(
                    student=student,
                    document_type=document_type,
                    file=file,
                    created_by=request.user,
                    notes=f'Bulk upload: {file.name}'
                )
                created_documents.append(document)
            
            return JsonResponse({
                'success': True,
                'message': f'{len(created_documents)} documents uploaded successfully',
                'redirect_url': reverse('web_interface:document-list')
            })
            
        except (StudentProfile.DoesNotExist, DocumentType.DoesNotExist):
            return JsonResponse({'error': 'Invalid student or document type'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
```

#### 4. Create Templates

**Main List Template (`templates/web_interface/pages/documents/document_list.html`)**

```html
{% extends "web_interface/base/dashboard_base.html" %}
{% load static web_interface_tags %}

{% block page_title %}Document Management{% endblock %}

{% block top_actions %}
    <div class="search-container">
        <input type="text" 
               class="form-control search-input" 
               placeholder="Search documents..."
               hx-get="{% url 'web_interface:document-list' %}"
               hx-trigger="keyup changed delay:300ms"
               hx-target="#document-content"
               name="search"
               value="{{ search_query }}">
    </div>
    
    {% modal_trigger "Upload Documents" "/web/modals/document/upload/" "btn-success" "fas fa-upload" %}
    {% modal_trigger "Add Document" "/web/modals/document/create/" "btn-primary" "fas fa-plus" %}
{% endblock %}

{% block dashboard_content %}
    <div class="document-management">
        <!-- Filters -->
        <div class="filters-panel">
            <form hx-get="{% url 'web_interface:document-list' %}" 
                  hx-target="#document-content"
                  hx-trigger="change">
                <div class="filter-row">
                    <div class="filter-group">
                        <label>Status:</label>
                        <select name="status" class="form-control">
                            <option value="">All Statuses</option>
                            {% for value, label in status_choices %}
                                <option value="{{ value }}" {% if status_filter == value %}selected{% endif %}>
                                    {{ label }}
                                </option>
                            {% endfor %}
                        </select>
                    </div>
                    <div class="filter-group">
                        <button type="button" class="btn btn-outline-secondary" 
                                onclick="this.form.reset(); htmx.trigger(this.form, 'change')">
                            Clear Filters
                        </button>
                    </div>
                </div>
                <!-- Preserve search query -->
                <input type="hidden" name="search" value="{{ search_query }}">
            </form>
        </div>
        
        <!-- Document Content -->
        <div id="document-content" class="document-content">
            {% include "web_interface/pages/documents/document_list_content.html" %}
        </div>
    </div>
{% endblock %}
```

**Content Partial (`templates/web_interface/pages/documents/document_list_content.html`)**

```html
{% load web_interface_tags %}

<div class="document-list">
    {% if documents %}
        {% for document in documents %}
            <div class="document-row" data-document-id="{{ document.id }}">
                <div class="document-icon">
                    {% if document.file %}
                        <i class="fas fa-file-alt"></i>
                    {% else %}
                        <i class="fas fa-file-times text-muted"></i>
                    {% endif %}
                </div>
                <div class="document-info">
                    <div class="document-name">
                        <strong>{{ document.document_type.name }}</strong>
                        <span class="document-student">{{ document.student.person.get_full_name }}</span>
                    </div>
                    <div class="document-details">
                        <span class="document-date">{{ document.created_at|date:"M d, Y" }}</span>
                        {% status_badge document.status %}
                        {% if document.notes %}
                            <span class="document-notes" title="{{ document.notes }}">
                                <i class="fas fa-sticky-note"></i>
                            </span>
                        {% endif %}
                    </div>
                </div>
                <div class="document-size">
                    {% if document.file %}
                        {{ document.file.size|filesizeformat }}
                    {% else %}
                        <span class="text-muted">No file</span>
                    {% endif %}
                </div>
                <div class="document-actions">
                    <a href="{% url 'web_interface:document-detail' document.pk %}" 
                       class="btn btn-sm btn-outline-primary">View</a>
                    
                    {% if document.file %}
                        <a href="{% url 'web_interface:document-download' document.pk %}" 
                           class="btn btn-sm btn-outline-success">Download</a>
                    {% endif %}
                    
                    {% modal_trigger "Edit" "/web/modals/document-edit/"|add:document.pk|add:"/" "btn-sm btn-outline-secondary" "fas fa-edit" %}
                </div>
            </div>
        {% endfor %}
        
        <!-- Pagination -->
        {% if is_paginated %}
            <nav class="pagination">
                <div class="pagination-info">
                    Showing {{ page_obj.start_index }}-{{ page_obj.end_index }} of {{ page_obj.paginator.count }} documents
                </div>
                <div class="pagination-controls">
                    {% if page_obj.has_previous %}
                        <button hx-get="?page=1&search={{ search_query }}&status={{ status_filter }}" 
                                hx-target="#document-content" 
                                class="btn btn-sm btn-outline-secondary">First</button>
                        <button hx-get="?page={{ page_obj.previous_page_number }}&search={{ search_query }}&status={{ status_filter }}" 
                                hx-target="#document-content" 
                                class="btn btn-sm btn-outline-secondary">Previous</button>
                    {% endif %}
                    
                    <span class="current-page">Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}</span>
                    
                    {% if page_obj.has_next %}
                        <button hx-get="?page={{ page_obj.next_page_number }}&search={{ search_query }}&status={{ status_filter }}" 
                                hx-target="#document-content" 
                                class="btn btn-sm btn-outline-secondary">Next</button>
                        <button hx-get="?page={{ page_obj.paginator.num_pages }}&search={{ search_query }}&status={{ status_filter }}" 
                                hx-target="#document-content" 
                                class="btn btn-sm btn-outline-secondary">Last</button>
                    {% endif %}
                </div>
            </nav>
        {% endif %}
    {% else %}
        <div class="empty-state">
            <div class="empty-state-icon">📄</div>
            <h3>No Documents Found</h3>
            <p>Try adjusting your search criteria or upload new documents.</p>
            {% modal_trigger "Upload First Document" "/web/modals/document/upload/" "btn-primary" "fas fa-upload" %}
        </div>
    {% endif %}
</div>
```

**Modal Template (`templates/web_interface/modals/document_create_modal.html`)**

```html
{% extends "web_interface/modals/base_modal.html" %}
{% load static %}

{% block modal_title %}Create Document{% endblock %}

{% block modal_body %}
    <form hx-post="{% url 'web_interface:modal-document-create' %}" 
          hx-encoding="multipart/form-data"
          hx-target="#modal-container"
          enctype="multipart/form-data">
        {% csrf_token %}
        
        {% if preselected_student %}
            <div class="alert alert-info">
                <strong>Creating document for:</strong> {{ preselected_student.person.get_full_name }} ({{ preselected_student.student_id }})
            </div>
        {% endif %}
        
        <div class="form-group">
            <label for="id_student">Student *</label>
            {{ form.student }}
            {% if form.student.errors %}
                <div class="invalid-feedback d-block">{{ form.student.errors.0 }}</div>
            {% endif %}
        </div>
        
        <div class="form-group">
            <label for="id_document_type">Document Type *</label>
            {{ form.document_type }}
            {% if form.document_type.errors %}
                <div class="invalid-feedback d-block">{{ form.document_type.errors.0 }}</div>
            {% endif %}
        </div>
        
        <div class="form-group">
            <label for="id_file">File *</label>
            {{ form.file }}
            {% if form.file.errors %}
                <div class="invalid-feedback d-block">{{ form.file.errors.0 }}</div>
            {% endif %}
            <small class="form-text text-muted">
                Maximum file size: 10MB. Supported formats: PDF, DOC, DOCX, JPG, PNG
            </small>
        </div>
        
        <div class="form-group">
            <label for="id_notes">Notes</label>
            {{ form.notes }}
            {% if form.notes.errors %}
                <div class="invalid-feedback d-block">{{ form.notes.errors.0 }}</div>
            {% endif %}
        </div>
    </form>
{% endblock %}

{% block modal_actions %}
    <button type="submit" 
            form="document-create-form"
            class="btn btn-primary">
        <i class="fas fa-save"></i> Create Document
    </button>
{% endblock %}
```

#### 5. Update Navigation

Add the new feature to the navigation structure in `utils.py`:

```python
# apps/web_interface/utils.py
def get_navigation_structure():
    return {
        "admin": [
            {
                "title": "Main",
                "items": [
                    # ... existing items ...
                    {"name": "Documents", "icon": "📄", "page": "documents", "url_name": "web_interface:document-list"},
                ],
            },
            # ... other sections ...
        ],
        "staff": [
            {
                "title": "Student Services",
                "items": [
                    # ... existing items ...
                    {"name": "Documents", "icon": "📄", "page": "documents", "url_name": "web_interface:document-list"},
                ],
            },
            # ... other sections ...
        ],
    }
```

#### 6. Add CSS Styles

Add document-specific styles to `dashboard.css`:

```css
/* Document Management Styles */
.document-list {
    display: flex;
    flex-direction: column;
    gap: 1px;
    background: #dee2e6;
    border-radius: var(--border-radius);
    overflow: hidden;
}

.document-row {
    background: white;
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 20px;
    transition: background 0.2s ease;
}

.document-row:hover {
    background: #f8f9fa;
}

.document-icon {
    width: 40px;
    height: 40px;
    border-radius: 8px;
    background: var(--primary-color);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
}

.document-info {
    flex: 1;
}

.document-name {
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 5px;
}

.document-name strong {
    font-size: 16px;
    color: #333;
}

.document-student {
    font-size: 13px;
    color: #666;
    background: #e9ecef;
    padding: 2px 8px;
    border-radius: 12px;
}

.document-details {
    display: flex;
    align-items: center;
    gap: 15px;
}

.document-date {
    font-size: 13px;
    color: #666;
}

.document-notes {
    color: #28a745;
    cursor: help;
}

.document-size {
    font-size: 13px;
    color: #666;
    min-width: 80px;
    text-align: right;
}

.document-actions {
    display: flex;
    gap: 8px;
}

/* Filters Panel */
.filters-panel {
    background: white;
    border-radius: var(--border-radius);
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: var(--box-shadow);
}

.filter-row {
    display: flex;
    align-items: end;
    gap: 20px;
}

.filter-group {
    flex: 1;
}

.filter-group label {
    display: block;
    margin-bottom: 5px;
    font-weight: 500;
    color: #333;
}
```

## Integration Patterns

### 1. Integrating with Existing Django Apps

#### Service Integration

```python
# apps/web_interface/views/finance_views.py
from apps.finance.services import InvoiceService, PaymentService

class InvoiceCreateView(RoleBasedPermissionMixin, CreateView):
    def form_valid(self, form):
        # Use service layer for business logic
        invoice_data = {
            'student': form.cleaned_data['student'],
            'amount': form.cleaned_data['amount'],
            'due_date': form.cleaned_data['due_date'],
            'line_items': self.get_line_items_from_form(form)
        }
        
        invoice = InvoiceService.create_invoice_with_line_items(invoice_data)
        
        # Return HTMX response
        if is_htmx_request(self.request):
            return JsonResponse({
                'success': True,
                'message': 'Invoice created successfully',
                'redirect_url': reverse('web_interface:invoice-detail', kwargs={'pk': invoice.pk})
            })
        
        return redirect('web_interface:invoice-detail', pk=invoice.pk)
```

#### Model Integration

```python
# apps/web_interface/views/student_views.py
from apps.people.models import StudentProfile, Person
from apps.enrollment.models import ProgramEnrollment, ClassHeaderEnrollment
from apps.grading.models import GPARecord

class StudentDetailView(RoleBasedPermissionMixin, DetailView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        student = self.object
        
        # Get related data from multiple apps
        context.update({
            'program_enrollments': ProgramEnrollment.objects.filter(student=student),
            'class_enrollments': ClassHeaderEnrollment.objects.filter(
                student=student
            ).select_related('class_header__course').order_by('-created_at')[:10],
            'gpa_records': GPARecord.objects.filter(student=student).order_by('-calculation_date')[:5],
            'recent_payments': Payment.objects.filter(
                student=student
            ).order_by('-payment_date')[:5],
        })
        
        return context
```

### 2. Custom Components and Widgets

#### Custom Form Widget

```python
# apps/web_interface/widgets.py
from django import forms

class HTMXSelectWidget(forms.Select):
    """Select widget with HTMX search capabilities."""
    
    def __init__(self, search_url=None, *args, **kwargs):
        self.search_url = search_url
        super().__init__(*args, **kwargs)
    
    def render(self, name, value, attrs=None, renderer=None):
        if attrs is None:
            attrs = {}
        
        # Add HTMX attributes
        if self.search_url:
            attrs.update({
                'hx-get': self.search_url,
                'hx-trigger': 'keyup changed delay:300ms',
                'hx-target': f'#{name}_results',
            })
        
        html = super().render(name, value, attrs, renderer)
        
        # Add search results container
        if self.search_url:
            html += f'<div id="{name}_results" class="search-results"></div>'
        
        return html

# Usage in forms
class StudentEnrollmentForm(forms.ModelForm):
    student = forms.ModelChoiceField(
        queryset=StudentProfile.objects.all(),
        widget=HTMXSelectWidget(search_url='/web/search/students/')
    )
```

#### Custom Template Filter

```python
# apps/web_interface/templatetags/web_interface_tags.py
@register.filter
def get_dashboard_stats(user):
    """Get role-specific dashboard statistics."""
    from .views.dashboard_views import DashboardView
    
    # Create a mock request object
    from django.http import HttpRequest
    request = HttpRequest()
    request.user = user
    
    # Get dashboard context
    dashboard_view = DashboardView()
    dashboard_view.request = request
    
    current_role = request.session.get('current_role', 'student')
    
    if current_role == 'admin':
        return dashboard_view.get_admin_context()
    elif current_role == 'staff':
        return dashboard_view.get_staff_context()
    elif current_role == 'teacher':
        return dashboard_view.get_teacher_context()
    elif current_role == 'finance':
        return dashboard_view.get_finance_context()
    else:
        return dashboard_view.get_student_context()

# Usage in template
{% with stats=user|get_dashboard_stats %}
    <div class="dashboard-stats">
        {% for key, value in stats.items %}
            <div class="stat-card">
                <h3>{{ value }}</h3>
                <p>{{ key|title|spacify }}</p>
            </div>
        {% endfor %}
    </div>
{% endwith %}
```

### 3. Advanced HTMX Patterns

#### Infinite Scroll

```html
<!-- Template with infinite scroll -->
<div id="student-list" class="student-list">
    {% for student in students %}
        <!-- Student rows -->
    {% endfor %}
    
    {% if page_obj.has_next %}
        <div hx-get="?page={{ page_obj.next_page_number }}"
             hx-trigger="revealed"
             hx-swap="outerHTML"
             hx-target="this">
            <div class="loading-more">Loading more students...</div>
        </div>
    {% endif %}
</div>
```

#### Form Validation with HTMX

```python
# View for real-time form validation
class StudentValidationView(View):
    def post(self, request):
        field_name = request.POST.get('field_name')
        field_value = request.POST.get('field_value')
        
        errors = []
        
        if field_name == 'student_id':
            if StudentProfile.objects.filter(student_id=field_value).exists():
                errors.append('Student ID already exists')
        elif field_name == 'email':
            if Person.objects.filter(email=field_value).exists():
                errors.append('Email already exists')
        
        if errors:
            return JsonResponse({'valid': False, 'errors': errors})
        else:
            return JsonResponse({'valid': True})
```

```html
<!-- Template with real-time validation -->
<input type="text" 
       name="student_id" 
       class="form-control"
       hx-post="{% url 'web_interface:validate-field' %}"
       hx-vals='{"field_name": "student_id"}'
       hx-target="#student_id_feedback"
       hx-trigger="blur">
<div id="student_id_feedback" class="form-feedback"></div>
```

#### Dependent Dropdowns

```html
<!-- Course selection affects available classes -->
<select name="course" 
        hx-get="{% url 'web_interface:get-classes' %}"
        hx-target="#class_select"
        hx-trigger="change">
    <option value="">Select Course</option>
    {% for course in courses %}
        <option value="{{ course.id }}">{{ course.name }}</option>
    {% endfor %}
</select>

<div id="class_select">
    <select name="class_header" disabled>
        <option value="">Select course first</option>
    </select>
</div>
```

### 4. Custom Permissions and Access Control

#### Custom Permission Decorator

```python
# apps/web_interface/decorators.py
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse

def require_student_access(view_func):
    """Decorator to ensure user can only access their own student data."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        student_id = kwargs.get('student_id') or kwargs.get('pk')
        
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # Check if user is staff/admin
        if request.user.groups.filter(name__in=['staff', 'admin']).exists():
            return view_func(request, *args, **kwargs)
        
        # Check if user is accessing their own data
        if hasattr(request.user, 'person') and hasattr(request.user.person, 'studentprofile'):
            if str(request.user.person.studentprofile.id) == str(student_id):
                return view_func(request, *args, **kwargs)
        
        # Check if HTMX request for proper error response
        if request.headers.get('HX-Request'):
            return JsonResponse({'error': 'Access denied'}, status=403)
        
        raise PermissionDenied("You can only access your own information")
    
    return wrapper

# Usage
class StudentDetailView(DetailView):
    @method_decorator(require_student_access)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
```

#### Dynamic Permission Checking

```python
# apps/web_interface/utils.py
def user_can_access_student(user, student_profile):
    """Check if user can access specific student data."""
    
    # Superuser has access to everything
    if user.is_superuser:
        return True
    
    # Staff can access all students
    if user.groups.filter(name__in=['staff', 'admin']).exists():
        return True
    
    # Teachers can access their students
    if hasattr(user, 'person') and hasattr(user.person, 'teacherprofile'):
        teacher_profile = user.person.teacherprofile
        
        # Check if teacher teaches any classes with this student
        from apps.enrollment.models import ClassHeaderEnrollment
        common_classes = ClassHeaderEnrollment.objects.filter(
            student=student_profile,
            class_header__teacher=teacher_profile
        ).exists()
        
        if common_classes:
            return True
    
    # Students can access their own data
    if hasattr(user, 'person') and hasattr(user.person, 'studentprofile'):
        if user.person.studentprofile == student_profile:
            return True
    
    return False

# Usage in templates
{% if user|can_access_student:student %}
    <a href="{% url 'web_interface:student-detail' student.pk %}">View Details</a>
{% endif %}
```

### 5. Performance Optimization Examples

#### Database Query Optimization

```python
# Optimized list view with select_related and prefetch_related
class OptimizedStudentListView(ListView):
    def get_queryset(self):
        return StudentProfile.objects.select_related(
            'person',
            'program'
        ).prefetch_related(
            'enrollments__class_header__course',
            'gpa_records'
        ).annotate(
            total_credits=Sum('enrollments__class_header__course__credits'),
            latest_gpa=Subquery(
                GPARecord.objects.filter(
                    student=OuterRef('pk')
                ).order_by('-calculation_date').values('gpa')[:1]
            )
        )
```

#### Template Fragment Caching

```html
{% load cache %}

{% cache 300 student_stats student.id %}
    <div class="student-stats">
        <div class="stat">
            <span class="stat-value">{{ student.total_credits|default:0 }}</span>
            <span class="stat-label">Credits</span>
        </div>
        <div class="stat">
            <span class="stat-value">{{ student.latest_gpa|floatformat:2|default:"N/A" }}</span>
            <span class="stat-label">GPA</span>
        </div>
    </div>
{% endcache %}
```

#### HTMX Response Caching

```python
from django.core.cache import cache
from django.utils.cache import get_cache_key

class CachedStudentSearchView(View):
    def get(self, request):
        # Create cache key from search parameters
        search_query = request.GET.get('search', '')
        cache_key = f'student_search:{hash(search_query)}'
        
        # Try to get from cache first
        cached_response = cache.get(cache_key)
        if cached_response:
            return cached_response
        
        # Generate response
        students = StudentProfile.objects.filter(
            person__personal_name__icontains=search_query
        )[:10]
        
        response = render(request, 'web_interface/partials/student_search_results.html', {
            'students': students
        })
        
        # Cache for 5 minutes
        cache.set(cache_key, response, 300)
        return response
```

### 6. Testing Examples

#### View Testing

```python
# apps/web_interface/tests/test_document_views.py
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.people.models import Person, StudentProfile
from apps.academic_records.models import Document, DocumentType

User = get_user_model()

class DocumentViewTests(TestCase):
    def setUp(self):
        """Set up test data."""
        # Create user and person
        self.user = User.objects.create_user(
            email='admin@example.com',
            password='testpass123'
        )
        self.user.is_staff = True
        self.user.save()
        
        self.person = Person.objects.create(
            personal_name='Admin',
            family_name='User',
            preferred_gender='M',
            date_of_birth='1980-01-01',
            citizenship='US'
        )
        self.user.person = self.person
        self.user.save()
        
        # Create student
        self.student_person = Person.objects.create(
            personal_name='Test',
            family_name='Student',
            preferred_gender='F',
            date_of_birth='2000-01-01',
            citizenship='US'
        )
        self.student = StudentProfile.objects.create(
            person=self.student_person,
            student_id='S001'
        )
        
        # Create document type
        self.document_type = DocumentType.objects.create(
            name='Transcript',
            description='Official transcript'
        )
    
    def test_document_list_requires_login(self):
        """Test that document list requires authentication."""
        response = self.client.get(reverse('web_interface:document-list'))
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_document_list_with_staff_user(self):
        """Test document list with staff user."""
        self.client.login(email='admin@example.com', password='testpass123')
        response = self.client.get(reverse('web_interface:document-list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Document Management')
    
    def test_document_list_htmx_request(self):
        """Test document list with HTMX request."""
        self.client.login(email='admin@example.com', password='testpass123')
        response = self.client.get(
            reverse('web_interface:document-list'),
            HTTP_HX_REQUEST='true'
        )
        self.assertEqual(response.status_code, 200)
        # Should return partial template
        self.assertTemplateUsed(response, 'web_interface/pages/documents/document_list_content.html')
    
    def test_document_search(self):
        """Test document search functionality."""
        # Create a document
        Document.objects.create(
            student=self.student,
            document_type=self.document_type,
            created_by=self.user,
            notes='Test document'
        )
        
        self.client.login(email='admin@example.com', password='testpass123')
        response = self.client.get(
            reverse('web_interface:document-list'),
            {'search': 'Test Student'}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Student')
    
    def test_document_create_modal(self):
        """Test document creation modal."""
        self.client.login(email='admin@example.com', password='testpass123')
        response = self.client.get(reverse('web_interface:modal-document-create'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Document')
        self.assertContains(response, 'id_student')
    
    def test_document_create_with_file(self):
        """Test document creation with file upload."""
        self.client.login(email='admin@example.com', password='testpass123')
        
        # Create a test file
        test_file = SimpleUploadedFile(
            "test.pdf",
            b"test file content",
            content_type="application/pdf"
        )
        
        response = self.client.post(
            reverse('web_interface:modal-document-create'),
            {
                'student': self.student.id,
                'document_type': self.document_type.id,
                'file': test_file,
                'notes': 'Test upload'
            },
            HTTP_HX_REQUEST='true'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Check that document was created
        self.assertTrue(
            Document.objects.filter(
                student=self.student,
                document_type=self.document_type
            ).exists()
        )
```

#### JavaScript Testing

```javascript
// static/web_interface/tests/dashboard.test.js
describe('DashboardApp', function() {
    beforeEach(function() {
        // Set up DOM
        document.body.innerHTML = `
            <div id="alerts"></div>
            <div id="modal-container"></div>
        `;
        
        // Initialize app
        DashboardApp.init();
    });
    
    afterEach(function() {
        document.body.innerHTML = '';
    });
    
    describe('showAlert', function() {
        it('should create alert with correct content', function() {
            DashboardApp.showAlert('Test message', 'success');
            
            const alert = document.querySelector('.alert');
            expect(alert).not.toBeNull();
            expect(alert.classList.contains('alert-success')).toBe(true);
            expect(alert.textContent).toContain('Test message');
        });
        
        it('should auto-remove alert after timeout', function(done) {
            DashboardApp.showAlert('Test message', 'info');
            
            setTimeout(function() {
                const alert = document.querySelector('.alert');
                expect(alert).toBeNull();
                done();
            }, 5100); // Slightly more than 5 second timeout
        });
    });
    
    describe('modal management', function() {
        it('should show modal with content', function() {
            const modalContent = '<div class="test-modal">Test Content</div>';
            
            DashboardApp.showModal(modalContent);
            
            const modalContainer = document.getElementById('modal-container');
            expect(modalContainer).not.toBeNull();
            expect(modalContainer.innerHTML).toContain('Test Content');
        });
        
        it('should close modal and clean up DOM', function() {
            const modalContent = '<div class="test-modal">Test Content</div>';
            DashboardApp.showModal(modalContent);
            
            DashboardApp.closeModal();
            
            const modalContainer = document.getElementById('modal-container');
            expect(modalContainer.innerHTML).toBe('');
        });
    });
    
    describe('currency formatting', function() {
        it('should format USD correctly', function() {
            const formatted = DashboardApp.formatCurrency(1234.56, 'USD');
            expect(formatted).toBe('$1,234.56');
        });
        
        it('should format KHR correctly', function() {
            const formatted = DashboardApp.formatCurrency(1234.56, 'KHR');
            expect(formatted).toBe('៛1,235');
        });
    });
});
```

### 7. Deployment Examples

#### Docker Configuration

```dockerfile
# Dockerfile for web interface assets
FROM node:16-alpine AS assets

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --only=production

COPY static/ ./static/
RUN npm run build

FROM python:3.11

# Copy built assets
COPY --from=assets /app/dist/ /app/static/

# Continue with Django setup...
```

#### Nginx Configuration

```nginx
# nginx.conf for web interface
server {
    listen 80;
    server_name your-domain.com;
    
    # Static files
    location /static/ {
        alias /app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # HTMX requests
    location /web/ {
        proxy_pass http://django:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Special handling for HTMX requests
        proxy_set_header HX-Request $http_hx_request;
        proxy_set_header HX-Target $http_hx_target;
        proxy_set_header HX-Current-URL $http_hx_current_url;
    }
}
```

## Best Practices Summary

### 1. View Organization
- Keep views focused and single-purpose
- Use mixins for common functionality
- Separate HTMX logic from traditional views
- Implement proper error handling

### 2. Template Structure
- Use template inheritance effectively
- Create reusable components
- Keep templates focused on presentation
- Use HTMX attributes consistently

### 3. JavaScript Integration
- Keep JavaScript modular
- Use HTMX for server interactions
- Implement proper error handling
- Follow progressive enhancement

### 4. Performance
- Optimize database queries
- Use appropriate caching strategies
- Minimize template complexity
- Optimize static asset delivery

### 5. Security
- Implement proper permission checking
- Validate all user inputs
- Use CSRF protection consistently
- Sanitize dynamic content

This comprehensive guide demonstrates how to build upon the web interface foundation to create new features, integrate with other systems, and maintain high code quality standards.