# Web Interface Templates and Static Assets Documentation

## Overview

The `web_interface` app uses a comprehensive template and static asset system built on Django templates with HTMX integration. The design follows a component-based architecture with responsive layouts and bilingual support.

## Template Architecture

### Template Directory Structure

```
templates/web_interface/
├── base/                   # Base templates and layouts
│   ├── base.html          # Master template with HTMX setup
│   ├── dashboard_base.html # Dashboard-specific layout
│   └── login.html         # Authentication template
├── components/            # Reusable UI components
│   ├── action_button.html
│   ├── loading_spinner.html
│   ├── modal_trigger.html
│   └── status_badge.html
├── dashboards/           # Role-specific dashboard content
│   └── dashboard_content.html
├── modals/              # Modal dialog templates
│   ├── base_modal.html
│   ├── confirmation_modal.html
│   ├── invoice_create_modal.html
│   ├── payment_process_modal.html
│   ├── quick_payment_modal.html
│   └── student_create_modal.html
└── pages/              # Page-specific templates
    ├── academic/       # Academic management pages
    ├── common/        # Shared page templates
    │   └── placeholder.html
    ├── finance/       # Financial management pages
    │   ├── billing.html
    │   └── billing_content.html
    └── students/      # Student management pages
        ├── student_list.html
        └── student_list_content.html
```

### Template Hierarchy

#### 1. Base Template (`base/base.html`)

The master template that defines the overall page structure:

```html
<!DOCTYPE html>
<html lang="{% if LANGUAGE_CODE == 'km' %}km{% else %}en{% endif %}">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <meta name="csrf-token" content="{{ csrf_token }}" />
    <title>{% block title %}Naga SIS{% endblock %}</title>
    
    <!-- Core Styles -->
    <link rel="stylesheet" href="{% static 'web_interface/css/dashboard.css' %}" />
    {% block extra_css %}{% endblock %}
    
    <!-- HTMX -->
    <script src="https://unpkg.com/htmx.org@1.9.10"></script>
    {% block extra_head %}{% endblock %}
</head>
<body class="{% block body_class %}{% endblock %}">
    <!-- Alert Container -->
    <div id="alerts" style="position: fixed; top: 20px; right: 20px; z-index: 9999"></div>
    
    <!-- Main Content -->
    {% block content %}{% endblock %}
    
    <!-- Core Scripts -->
    <script src="{% static 'web_interface/js/dashboard.js' %}"></script>
    <script src="{% static 'web_interface/js/htmx-extensions.js' %}"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

**Key Features:**
- Bilingual HTML lang attribute
- CSRF token in meta tag for JavaScript access
- HTMX CDN integration
- Fixed alert container for notifications
- Extensible blocks for customization

#### 2. Dashboard Base (`base/dashboard_base.html`)

Extended layout for dashboard pages:

```html
{% extends "web_interface/base/base.html" %}
{% load static web_interface_tags %}

{% block body_class %}dashboard-layout{% endblock %}

{% block content %}
<div class="dashboard-container">
    <!-- Sidebar Navigation -->
    <nav class="sidebar" id="sidebar">
        <div class="sidebar-header">
            <h1 class="sidebar-logo">Naga SIS</h1>
            <div class="user-info">
                <div class="user-avatar">{{ request.user.get_short_name|first }}</div>
                <div class="user-details">
                    <div class="user-name">{{ request.user.get_full_name }}</div>
                    <div class="user-role">{{ current_role|title }}</div>
                </div>
            </div>
        </div>
        
        <!-- Role Switch -->
        <div class="role-switch">
            <select hx-post="{% url 'web_interface:role-switch' %}" 
                    hx-trigger="change" 
                    hx-target="#dashboard-content">
                {% for role in available_roles %}
                    <option value="{{ role.key }}" 
                            {% if role.key == current_role %}selected{% endif %}>
                        {{ role.name }}
                    </option>
                {% endfor %}
            </select>
        </div>
        
        <!-- Navigation Menu -->
        <div class="nav-menu">
            {% for section in navigation %}
                <div class="nav-section">
                    <h3 class="nav-section-title">{{ section.title }}</h3>
                    <ul class="nav-items">
                        {% for item in section.items %}
                            <li class="nav-item">
                                <a href="{% if item.url_name %}{% url item.url_name %}{% else %}#{% endif %}" 
                                   class="nav-link {% if current_page == item.page %}active{% endif %}"
                                   data-page="{{ item.page }}">
                                    <span class="nav-icon">{{ item.icon }}</span>
                                    <span class="nav-text">{{ item.name }}</span>
                                </a>
                            </li>
                        {% endfor %}
                    </ul>
                </div>
            {% endfor %}
        </div>
        
        <!-- Language Switch -->
        <div class="language-switch">
            <button class="lang-btn {% if LANGUAGE_CODE == 'en' %}active{% endif %}">English</button>
            <button class="lang-btn {% if LANGUAGE_CODE == 'km' %}active{% endif %}">ភាសាខ្មែរ</button>
        </div>
    </nav>
    
    <!-- Main Content Area -->
    <main class="main-content" id="main-content">
        <!-- Top Bar -->
        <header class="top-bar">
            <button class="mobile-menu-toggle">☰</button>
            <div class="page-title">
                <h1>{% block page_title %}{{ page_title }}{% endblock %}</h1>
                {% if page_subtitle %}
                    <p class="page-subtitle">{{ page_subtitle }}</p>
                {% endif %}
            </div>
            <div class="top-bar-actions">
                {% block top_actions %}{% endblock %}
            </div>
        </header>
        
        <!-- Page Content -->
        <div class="page-content" id="dashboard-content">
            {% block dashboard_content %}{% endblock %}
        </div>
    </main>
</div>
{% endblock %}
```

**Key Features:**
- Responsive sidebar navigation
- Role-based menu generation
- HTMX-powered role switching
- Mobile menu support
- Language switching interface
- Extensible top actions area

#### 3. Login Template (`base/login.html`)

Authentication page with clean, centered design:

```html
{% extends "web_interface/base/base.html" %}
{% load static %}

{% block title %}Login - Naga SIS{% endblock %}

{% block body_class %}login-page{% endblock %}

{% block content %}
<div class="login-container">
    <div class="login-card">
        <div class="login-header">
            <h1>Naga SIS</h1>
            <p>Student Information System</p>
        </div>
        
        <form id="loginForm" method="post" class="login-form">
            {% csrf_token %}
            
            <div class="form-group">
                <label for="email">Email Address</label>
                <input type="email" id="email" name="email" 
                       class="form-control" required autofocus>
            </div>
            
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" 
                       class="form-control" required>
            </div>
            
            <button type="submit" class="btn btn-primary btn-block">
                Sign In
            </button>
            
            {% if form.errors %}
                <div class="alert alert-danger">
                    {{ form.errors }}
                </div>
            {% endif %}
        </form>
        
        <div class="login-footer">
            <div class="language-switch">
                <button class="lang-btn {% if LANGUAGE_CODE == 'en' %}active{% endif %}">English</button>
                <button class="lang-btn {% if LANGUAGE_CODE == 'km' %}active{% endif %}">ភាសាខ្មែរ</button>
            </div>
        </div>
    </div>
</div>
{% endblock %}
```

### Component Templates

#### 1. Status Badge (`components/status_badge.html`)

Reusable status indicator component:

```html
{% load web_interface_tags %}

<span class="badge badge-{{ status|get_status_class }}"
      data-tooltip="Status: {{ status|title }}">
    {{ status|title }}
</span>
```

Usage in templates:
```html
{% include "web_interface/components/status_badge.html" with status=student.current_status %}
```

#### 2. Action Button (`components/action_button.html`)

Consistent button component for actions:

```html
<button type="button" 
        class="btn {{ button_class|default:'btn-primary' }} {{ size|default:'btn-sm' }}"
        {% if modal_url %}data-modal-url="{{ modal_url }}"{% endif %}
        {% if href %}onclick="window.location.href='{{ href }}'"{% endif %}
        {% if hx_get %}hx-get="{{ hx_get }}"{% endif %}
        {% if hx_post %}hx-post="{{ hx_post }}"{% endif %}
        {% if hx_target %}hx-target="{{ hx_target }}"{% endif %}
        {% if tooltip %}data-tooltip="{{ tooltip }}"{% endif %}>
    {% if icon %}<i class="{{ icon }}"></i>{% endif %}
    {{ text }}
</button>
```

Usage:
```html
{% include "web_interface/components/action_button.html" with text="Edit Student" button_class="btn-outline-secondary" modal_url="/web/modals/student-edit/123/" icon="fas fa-edit" %}
```

#### 3. Modal Trigger (`components/modal_trigger.html`)

Button that opens HTMX modals:

```html
<button type="button" 
        class="modal-trigger btn {{ button_class|default:'btn-primary' }}"
        data-modal-url="{{ modal_url }}"
        {% if student_id %}data-student-id="{{ student_id }}"{% endif %}
        {% if invoice_id %}data-invoice-id="{{ invoice_id }}"{% endif %}>
    {% if icon %}<i class="{{ icon }}"></i>{% endif %}
    {{ text }}
</button>
```

#### 4. Loading Spinner (`components/loading_spinner.html`)

Consistent loading indicator:

```html
<div class="loading-spinner {{ size|default:'medium' }}"
     {% if message %}data-loading-text="{{ message }}"{% endif %}>
    <div class="spinner"></div>
    {% if message %}
        <div class="loading-text">{{ message }}</div>
    {% endif %}
</div>
```

### Modal Templates

#### Base Modal Structure (`modals/base_modal.html`)

Template for modal dialogs:

```html
<div id="modal-overlay" class="modal-overlay" onclick="closeModal()">
    <div class="modal-container {{ modal_size|default:'modal-medium' }}" onclick="event.stopPropagation()">
        <div class="modal-header">
            <h3 class="modal-title">{% block modal_title %}Modal Title{% endblock %}</h3>
            <button type="button" class="modal-close-btn" onclick="closeModal()">
                <i class="fas fa-times"></i>
            </button>
        </div>
        <div class="modal-body">
            {% block modal_body %}
                <!-- Modal content goes here -->
            {% endblock %}
        </div>
        {% block modal_footer %}
            <div class="modal-footer">
                <button type="button" class="btn btn-secondary" onclick="closeModal()">
                    Cancel
                </button>
                {% block modal_actions %}{% endblock %}
            </div>
        {% endblock %}
    </div>
</div>
```

### Page Templates

#### Student List (`pages/students/student_list.html`)

Full page template for student management:

```html
{% extends "web_interface/base/dashboard_base.html" %}
{% load static web_interface_tags %}

{% block page_title %}Student Management{% endblock %}

{% block top_actions %}
    <div class="search-container">
        <input type="text" 
               class="form-control search-input" 
               placeholder="Search students..."
               hx-get="{% url 'web_interface:student-search' %}"
               hx-trigger="keyup changed delay:300ms"
               hx-target="#student-content"
               name="search">
    </div>
    
    {% include "web_interface/components/modal_trigger.html" with text="Add Student" modal_url="/web/modals/student/create/" button_class="btn-primary" icon="fas fa-plus" %}
{% endblock %}

{% block dashboard_content %}
    <div class="student-management">
        <!-- Filters -->
        <div class="filters-panel">
            <form hx-get="{% url 'web_interface:student-list' %}" 
                  hx-target="#student-content"
                  hx-trigger="change">
                <div class="filter-row">
                    <div class="filter-group">
                        <label>Status:</label>
                        <select name="status" class="form-control">
                            <option value="">All Statuses</option>
                            <option value="ACTIVE">Active</option>
                            <option value="INACTIVE">Inactive</option>
                            <option value="GRADUATED">Graduated</option>
                        </select>
                    </div>
                    <div class="filter-group">
                        <label>Program:</label>
                        <select name="program" class="form-control">
                            <option value="">All Programs</option>
                            {% for program in programs %}
                                <option value="{{ program.id }}">{{ program.name }}</option>
                            {% endfor %}
                        </select>
                    </div>
                </div>
            </form>
        </div>
        
        <!-- Student Content -->
        <div id="student-content" class="student-content">
            {% include "web_interface/pages/students/student_list_content.html" %}
        </div>
    </div>
{% endblock %}
```

#### Student List Content (`pages/students/student_list_content.html`)

HTMX partial for student list updates:

```html
{% load web_interface_tags %}

<div class="student-list">
    {% if students %}
        {% for student in students %}
            <div class="student-row" data-student-id="{{ student.id }}">
                <div class="student-avatar">
                    {{ student.person.get_full_name|first }}
                </div>
                <div class="student-info">
                    <div class="student-name">
                        <strong>{{ student.person.get_full_name }}</strong>
                        <span class="student-id">{{ student.student_id }}</span>
                    </div>
                    <div class="student-details">
                        <span class="student-program">{{ student.program.name }}</span>
                        {% include "web_interface/components/status_badge.html" with status=student.current_status %}
                    </div>
                </div>
                <div class="student-stats">
                    <div class="stat">
                        <span class="stat-label">GPA:</span>
                        <span class="stat-value">{{ student.current_gpa|floatformat:2|default:"N/A" }}</span>
                    </div>
                    <div class="stat">
                        <span class="stat-label">Credits:</span>
                        <span class="stat-value">{{ student.credits_earned|default:"0" }}</span>
                    </div>
                </div>
                <div class="student-actions">
                    <a href="{% url 'web_interface:student-detail' student.pk %}" 
                       class="btn btn-sm btn-outline-primary">View</a>
                    {% include "web_interface/components/modal_trigger.html" with text="Edit" button_class="btn-sm btn-outline-secondary" modal_url="/web/modals/student-edit/"|add:student.pk|add:"/" icon="fas fa-edit" %}
                    {% include "web_interface/components/modal_trigger.html" with text="Enroll" button_class="btn-sm btn-success" modal_url="/web/modals/enrollment-create/" student_id=student.pk icon="fas fa-plus" %}
                </div>
            </div>
        {% endfor %}
        
        <!-- Pagination -->
        {% if is_paginated %}
            <nav class="pagination">
                <div class="pagination-info">
                    Showing {{ page_obj.start_index }}-{{ page_obj.end_index }} of {{ page_obj.paginator.count }} students
                </div>
                <div class="pagination-controls">
                    {% if page_obj.has_previous %}
                        <button hx-get="?page=1" hx-target="#student-content" class="btn btn-sm btn-outline-secondary">First</button>
                        <button hx-get="?page={{ page_obj.previous_page_number }}" hx-target="#student-content" class="btn btn-sm btn-outline-secondary">Previous</button>
                    {% endif %}
                    
                    <span class="current-page">Page {{ page_obj.number }} of {{ page_obj.paginator.num_pages }}</span>
                    
                    {% if page_obj.has_next %}
                        <button hx-get="?page={{ page_obj.next_page_number }}" hx-target="#student-content" class="btn btn-sm btn-outline-secondary">Next</button>
                        <button hx-get="?page={{ page_obj.paginator.num_pages }}" hx-target="#student-content" class="btn btn-sm btn-outline-secondary">Last</button>
                    {% endif %}
                </div>
            </nav>
        {% endif %}
    {% else %}
        <div class="empty-state">
            <div class="empty-state-icon">👥</div>
            <h3>No Students Found</h3>
            <p>Try adjusting your search criteria or add a new student.</p>
            {% include "web_interface/components/modal_trigger.html" with text="Add First Student" modal_url="/web/modals/student/create/" button_class="btn-primary" icon="fas fa-plus" %}
        </div>
    {% endif %}
</div>
```

## Static Assets

### CSS Architecture

#### Main Stylesheet (`static/web_interface/css/dashboard.css`)

Comprehensive styles for the dashboard interface:

```css
/* Variables */
:root {
    --primary-color: #007bff;
    --secondary-color: #6c757d;
    --success-color: #28a745;
    --warning-color: #ffc107;
    --danger-color: #dc3545;
    --info-color: #17a2b8;
    
    --sidebar-width: 280px;
    --topbar-height: 60px;
    --border-radius: 6px;
    --box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    
    --font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-size-base: 14px;
    --line-height-base: 1.5;
}

/* Layout */
.dashboard-layout {
    font-family: var(--font-family);
    font-size: var(--font-size-base);
    line-height: var(--line-height-base);
    background-color: #f8f9fa;
    margin: 0;
    padding: 0;
}

.dashboard-container {
    display: flex;
    min-height: 100vh;
}

/* Sidebar */
.sidebar {
    width: var(--sidebar-width);
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    position: fixed;
    height: 100vh;
    overflow-y: auto;
    z-index: 1000;
    transition: transform 0.3s ease;
}

.sidebar-header {
    padding: 20px;
    border-bottom: 1px solid rgba(255,255,255,0.1);
}

.sidebar-logo {
    font-size: 24px;
    font-weight: bold;
    margin: 0 0 15px 0;
}

.user-info {
    display: flex;
    align-items: center;
    gap: 12px;
}

.user-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: rgba(255,255,255,0.2);
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 16px;
}

.user-details {
    flex: 1;
}

.user-name {
    font-weight: 600;
    font-size: 14px;
}

.user-role {
    font-size: 12px;
    opacity: 0.8;
}

/* Navigation */
.nav-menu {
    padding: 20px 0;
}

.nav-section {
    margin-bottom: 30px;
}

.nav-section-title {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin: 0 0 15px 20px;
    opacity: 0.7;
    font-weight: 600;
}

.nav-items {
    list-style: none;
    padding: 0;
    margin: 0;
}

.nav-item {
    margin: 2px 0;
}

.nav-link {
    display: flex;
    align-items: center;
    padding: 12px 20px;
    color: rgba(255,255,255,0.9);
    text-decoration: none;
    transition: all 0.2s ease;
    border-left: 3px solid transparent;
}

.nav-link:hover {
    background: rgba(255,255,255,0.1);
    color: white;
    text-decoration: none;
}

.nav-link.active {
    background: rgba(255,255,255,0.15);
    border-left-color: white;
    color: white;
}

.nav-icon {
    font-size: 18px;
    margin-right: 12px;
    width: 20px;
    text-align: center;
}

/* Main Content */
.main-content {
    flex: 1;
    margin-left: var(--sidebar-width);
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

.top-bar {
    height: var(--topbar-height);
    background: white;
    border-bottom: 1px solid #dee2e6;
    padding: 0 30px;
    display: flex;
    align-items: center;
    gap: 20px;
    position: sticky;
    top: 0;
    z-index: 100;
}

.mobile-menu-toggle {
    display: none;
    background: none;
    border: none;
    font-size: 18px;
    cursor: pointer;
}

.page-title {
    flex: 1;
}

.page-title h1 {
    font-size: 24px;
    font-weight: 600;
    margin: 0;
    color: #333;
}

.page-subtitle {
    font-size: 14px;
    color: #666;
    margin: 2px 0 0 0;
}

.top-bar-actions {
    display: flex;
    align-items: center;
    gap: 15px;
}

.page-content {
    flex: 1;
    padding: 30px;
    background: #f8f9fa;
}

/* Components */
.btn {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    border: 1px solid transparent;
    border-radius: var(--border-radius);
    font-size: 14px;
    font-weight: 500;
    text-decoration: none;
    cursor: pointer;
    transition: all 0.2s ease;
    white-space: nowrap;
}

.btn-primary {
    background: var(--primary-color);
    color: white;
    border-color: var(--primary-color);
}

.btn-primary:hover {
    background: #0056b3;
    border-color: #0056b3;
    color: white;
    text-decoration: none;
}

.btn-outline-secondary {
    border-color: var(--secondary-color);
    color: var(--secondary-color);
    background: transparent;
}

.btn-outline-secondary:hover {
    background: var(--secondary-color);
    color: white;
}

.btn-sm {
    padding: 6px 12px;
    font-size: 13px;
}

/* Forms */
.form-control {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid #ced4da;
    border-radius: var(--border-radius);
    font-size: 14px;
    transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.form-control:focus {
    outline: none;
    border-color: var(--primary-color);
    box-shadow: 0 0 0 0.2rem rgba(0,123,255,0.25);
}

.form-group {
    margin-bottom: 20px;
}

.form-group label {
    display: block;
    margin-bottom: 5px;
    font-weight: 500;
    color: #333;
}

/* Badges */
.badge {
    display: inline-flex;
    align-items: center;
    padding: 4px 8px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border-radius: 12px;
    line-height: 1;
}

.badge-success {
    background: #d4edda;
    color: #155724;
}

.badge-warning {
    background: #fff3cd;
    color: #856404;
}

.badge-danger {
    background: #f8d7da;
    color: #721c24;
}

.badge-secondary {
    background: #e2e3e5;
    color: #383d41;
}

/* Modals */
.modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 2000;
    opacity: 0;
    animation: fadeIn 0.2s ease forwards;
}

.modal-container {
    background: white;
    border-radius: var(--border-radius);
    box-shadow: 0 10px 25px rgba(0,0,0,0.2);
    max-width: 90vw;
    max-height: 90vh;
    overflow: hidden;
    transform: scale(0.9);
    animation: scaleIn 0.2s ease forwards;
}

.modal-medium {
    width: 500px;
}

.modal-large {
    width: 800px;
}

.modal-header {
    padding: 20px 30px;
    border-bottom: 1px solid #dee2e6;
    display: flex;
    align-items: center;
    justify-content: space-between;
}

.modal-title {
    font-size: 18px;
    font-weight: 600;
    margin: 0;
    color: #333;
}

.modal-close-btn {
    background: none;
    border: none;
    font-size: 20px;
    cursor: pointer;
    color: #666;
    padding: 0;
    width: 30px;
    height: 30px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    transition: background 0.2s ease;
}

.modal-close-btn:hover {
    background: #f8f9fa;
}

.modal-body {
    padding: 30px;
    max-height: 60vh;
    overflow-y: auto;
}

.modal-footer {
    padding: 20px 30px;
    border-top: 1px solid #dee2e6;
    display: flex;
    gap: 10px;
    justify-content: flex-end;
}

/* Responsive Design */
@media (max-width: 768px) {
    .sidebar {
        transform: translateX(-100%);
    }
    
    .sidebar.open {
        transform: translateX(0);
    }
    
    .main-content {
        margin-left: 0;
    }
    
    .mobile-menu-toggle {
        display: block;
    }
    
    .page-content {
        padding: 20px 15px;
    }
    
    .top-bar {
        padding: 0 15px;
    }
}

/* Animations */
@keyframes fadeIn {
    to {
        opacity: 1;
    }
}

@keyframes scaleIn {
    to {
        transform: scale(1);
    }
}

/* Loading States */
.loading-spinner {
    display: inline-flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    padding: 20px;
}

.spinner {
    width: 20px;
    height: 20px;
    border: 2px solid #f3f3f3;
    border-top: 2px solid var(--primary-color);
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Student List Specific */
.student-list {
    display: flex;
    flex-direction: column;
    gap: 1px;
    background: #dee2e6;
    border-radius: var(--border-radius);
    overflow: hidden;
}

.student-row {
    background: white;
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 20px;
    transition: background 0.2s ease;
}

.student-row:hover {
    background: #f8f9fa;
}

.student-avatar {
    width: 50px;
    height: 50px;
    border-radius: 50%;
    background: var(--primary-color);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 18px;
}

.student-info {
    flex: 1;
}

.student-name {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 5px;
}

.student-name strong {
    font-size: 16px;
    color: #333;
}

.student-id {
    font-size: 12px;
    color: #666;
    background: #e9ecef;
    padding: 2px 6px;
    border-radius: 3px;
}

.student-details {
    display: flex;
    align-items: center;
    gap: 15px;
}

.student-program {
    font-size: 13px;
    color: #666;
}

.student-stats {
    display: flex;
    gap: 20px;
}

.stat {
    text-align: center;
}

.stat-label {
    display: block;
    font-size: 11px;
    color: #666;
    margin-bottom: 2px;
}

.stat-value {
    display: block;
    font-size: 14px;
    font-weight: 600;
    color: #333;
}

.student-actions {
    display: flex;
    gap: 8px;
}
```

### JavaScript Architecture

#### Main Dashboard Script (`static/web_interface/js/dashboard.js`)

The main JavaScript application handles all interactive features:

**Key Features:**
- **CSRF Token Management**: Automatic token handling for all requests
- **HTMX Integration**: Configuration and error handling for HTMX requests
- **Modal System**: Dynamic modal creation and management
- **Navigation**: Active state management and mobile menu
- **Search**: Debounced search with live results
- **Form Handling**: Loading states and validation
- **Alerts**: Toast-style notification system

**Core Functions:**
```javascript
// Initialize the application
DashboardApp.init()

// Modal management
DashboardApp.showModal(content)
DashboardApp.closeModal()

// Alert system
DashboardApp.showAlert(message, type)

// Utility functions
DashboardApp.formatCurrency(amount, currency)
DashboardApp.formatDate(dateString, options)
```

#### HTMX Extensions (`static/web_interface/js/htmx-extensions.js`)

Additional HTMX functionality and customizations:

```javascript
/**
 * HTMX Extensions for Naga SIS
 * 
 * Custom HTMX behaviors and extensions specific to the Naga SIS interface.
 */

(function() {
    'use strict';

    // Custom HTMX extension for form validation
    htmx.defineExtension('form-validation', {
        onEvent: function(name, evt) {
            if (name === "htmx:beforeRequest") {
                const form = evt.detail.elt;
                if (form.tagName === 'FORM') {
                    // Add client-side validation
                    if (!this.validateForm(form)) {
                        evt.preventDefault();
                        return false;
                    }
                }
            }
        },

        validateForm: function(form) {
            const requiredFields = form.querySelectorAll('[required]');
            let isValid = true;

            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    this.showFieldError(field, 'This field is required');
                    isValid = false;
                } else {
                    this.clearFieldError(field);
                }
            });

            return isValid;
        },

        showFieldError: function(field, message) {
            field.classList.add('is-invalid');
            
            let errorDiv = field.parentNode.querySelector('.invalid-feedback');
            if (!errorDiv) {
                errorDiv = document.createElement('div');
                errorDiv.className = 'invalid-feedback';
                field.parentNode.appendChild(errorDiv);
            }
            errorDiv.textContent = message;
        },

        clearFieldError: function(field) {
            field.classList.remove('is-invalid');
            const errorDiv = field.parentNode.querySelector('.invalid-feedback');
            if (errorDiv) {
                errorDiv.remove();
            }
        }
    });

    // Auto-loading indicators
    document.addEventListener('htmx:beforeRequest', function(event) {
        const target = event.target;
        if (target.hasAttribute('hx-indicator')) {
            const indicator = document.querySelector(target.getAttribute('hx-indicator'));
            if (indicator) {
                indicator.style.display = 'block';
            }
        }
    });

    document.addEventListener('htmx:afterRequest', function(event) {
        const target = event.target;
        if (target.hasAttribute('hx-indicator')) {
            const indicator = document.querySelector(target.getAttribute('hx-indicator'));
            if (indicator) {
                indicator.style.display = 'none';
            }
        }
    });

    // Auto-refresh functionality
    htmx.defineExtension('auto-refresh', {
        onEvent: function(name, evt) {
            if (name === "htmx:afterSettle") {
                const element = evt.detail.elt;
                const refreshInterval = element.getAttribute('data-refresh');
                
                if (refreshInterval) {
                    const interval = parseInt(refreshInterval) * 1000;
                    setTimeout(() => {
                        htmx.trigger(element, 'refresh');
                    }, interval);
                }
            }
        }
    });

})();
```

### Template Tags

Custom template tags for common UI patterns (`templatetags/web_interface_tags.py`):

```python
from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

@register.simple_tag
def status_badge(status, size='normal'):
    """Render a status badge with appropriate styling."""
    size_class = 'badge-sm' if size == 'small' else ''
    status_class = get_status_badge_class(status)
    
    return format_html(
        '<span class="badge {} {}" data-tooltip="Status: {}">{}</span>',
        status_class,
        size_class,
        status.title(),
        status.title()
    )

@register.simple_tag
def action_button(text, button_class='btn-primary', href=None, modal_url=None, icon=None, size='sm'):
    """Render an action button with consistent styling."""
    size_class = f'btn-{size}' if size else ''
    icon_html = f'<i class="{icon}"></i>' if icon else ''
    
    if modal_url:
        return format_html(
            '<button type="button" class="btn {} {}" data-modal-url="{}">{} {}</button>',
            button_class,
            size_class,
            modal_url,
            icon_html,
            text
        )
    elif href:
        return format_html(
            '<a href="{}" class="btn {} {}">{} {}</a>',
            href,
            button_class,
            size_class,
            icon_html,
            text
        )
    else:
        return format_html(
            '<button type="button" class="btn {} {}">{} {}</button>',
            button_class,
            size_class,
            icon_html,
            text
        )

@register.simple_tag
def modal_trigger(text, modal_url, button_class='btn-primary', icon=None, student_id=None, invoice_id=None):
    """Render a button that triggers an HTMX modal."""
    icon_html = f'<i class="{icon}"></i>' if icon else ''
    data_attrs = []
    
    if student_id:
        data_attrs.append(f'data-student-id="{student_id}"')
    if invoice_id:
        data_attrs.append(f'data-invoice-id="{invoice_id}"')
    
    return format_html(
        '<button type="button" class="modal-trigger btn {}" data-modal-url="{}" {}>{} {}</button>',
        button_class,
        modal_url,
        ' '.join(data_attrs),
        icon_html,
        text
    )

@register.filter
def get_status_class(status):
    """Get CSS class for status values."""
    status_map = {
        'active': 'badge-success',
        'inactive': 'badge-secondary',
        'pending': 'badge-warning',
        'completed': 'badge-success',
        'cancelled': 'badge-danger',
        'expired': 'badge-danger',
        'paid': 'badge-success',
        'unpaid': 'badge-warning',
        'overdue': 'badge-danger',
        'partial': 'badge-info',
        'enrolled': 'badge-success',
        'dropped': 'badge-secondary',
        'graduated': 'badge-info',
        'suspended': 'badge-danger',
    }
    return status_map.get(status.lower(), 'badge-secondary')

@register.simple_tag
def format_currency(amount, currency='USD'):
    """Format currency for display."""
    if not amount:
        return '$0.00' if currency == 'USD' else '៛0'
    
    if currency == 'USD':
        return f'${float(amount):,.2f}'
    elif currency == 'KHR':
        return f'៛{float(amount):,.0f}'
    else:
        return f'{currency} {float(amount):,.2f}'

@register.inclusion_tag('web_interface/components/loading_spinner.html')
def loading_spinner(size='medium', message=None):
    """Render a loading spinner component."""
    return {
        'size': size,
        'message': message
    }

@register.inclusion_tag('web_interface/components/status_badge.html')
def status_badge_component(status, tooltip=None):
    """Render a status badge component."""
    return {
        'status': status,
        'tooltip': tooltip or f'Status: {status.title()}'
    }
```

### Asset Organization

#### CSS Structure
- **Base styles**: Layout, typography, colors
- **Component styles**: Buttons, forms, badges, modals
- **Page-specific styles**: Dashboard, lists, detail views
- **Responsive styles**: Mobile and tablet adaptations
- **Animation styles**: Transitions and loading states

#### JavaScript Structure
- **Core application**: Main dashboard functionality
- **HTMX extensions**: Custom HTMX behaviors
- **Component scripts**: Specific component interactions
- **Utility functions**: Common helper functions

#### Image Assets
```
static/web_interface/images/
├── logo/
│   ├── logo.svg
│   ├── logo-light.svg
│   └── favicon.ico
├── icons/
│   ├── status/
│   ├── actions/
│   └── navigation/
└── backgrounds/
    ├── login-bg.jpg
    └── dashboard-pattern.svg
```

## Performance Optimization

### Template Optimization
- Use template fragments for HTMX partials
- Minimize template inheritance depth
- Cache expensive template computations
- Use `{% load %}` sparingly and only when needed

### CSS Optimization
- Use CSS custom properties for theming
- Minimize specificity conflicts
- Group related styles together
- Use efficient selectors

### JavaScript Optimization
- Minimize DOM queries
- Use event delegation
- Debounce expensive operations
- Lazy load non-critical functionality

### HTMX Optimization
- Use `hx-preserve` for elements that shouldn't be replaced
- Implement proper loading indicators
- Use `hx-swap` strategically to minimize DOM updates
- Cache HTMX responses where appropriate

## Accessibility Features

### Semantic HTML
- Proper heading hierarchy
- ARIA labels and roles
- Form labels and fieldsets
- Landmark regions

### Keyboard Navigation
- Tab order management
- Focus indicators
- Keyboard shortcuts
- Modal focus trapping

### Screen Reader Support
- Alt text for images
- ARIA descriptions
- Live regions for dynamic updates
- Status announcements

### Color and Contrast
- WCAG AA compliant color ratios
- Color not used as sole indicator
- High contrast mode support
- Reduced motion preferences

## Internationalization

### Bilingual Support
- English/Khmer language switching
- RTL/LTR layout support
- Date and number formatting
- Cultural adaptations

### Template Localization
```html
{% load i18n %}

<h1>{% trans "Welcome to Naga SIS" %}</h1>

{% blocktrans %}
Hello {{ user_name }}, you have {{ message_count }} new messages.
{% endblocktrans %}
```

### JavaScript Localization
```javascript
// Localized strings
const translations = {
    'en': {
        'loading': 'Loading...',
        'error': 'An error occurred'
    },
    'km': {
        'loading': 'កំពុងផ្ទុក...',
        'error': 'មានកំហុសកើតឡើង'
    }
};
```

## Troubleshooting

### Common Template Issues
1. **Template not found**: Check template paths and inheritance
2. **Static files not loading**: Verify `{% load static %}` and `STATIC_URL`
3. **HTMX not working**: Check JavaScript console for errors
4. **Modal not opening**: Verify modal trigger attributes

### CSS Issues
1. **Styles not applying**: Check specificity and load order
2. **Responsive layout broken**: Test breakpoints and media queries
3. **Animation not smooth**: Check transform and transition properties

### JavaScript Issues
1. **HTMX requests failing**: Check CSRF tokens and headers
2. **Modal not closing**: Verify event handlers and DOM cleanup
3. **Search not working**: Check debounce timing and endpoints

## Future Enhancements

### Planned Template Improvements
1. **Component Library**: Develop comprehensive component system
2. **Theme System**: Multiple theme support
3. **Advanced Layouts**: Dashboard customization
4. **Mobile App Views**: PWA-optimized templates

### Asset Pipeline Improvements
1. **Build System**: Webpack or Vite integration
2. **CSS Preprocessing**: Sass or PostCSS
3. **JavaScript Bundling**: Module system and tree shaking
4. **Asset Optimization**: Minification and compression

This comprehensive template and asset system provides a solid foundation for the Naga SIS web interface, combining modern web technologies with Django's robust template system.