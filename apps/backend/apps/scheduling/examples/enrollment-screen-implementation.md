# Complete Implementation Guide: Class Enrollment Display System

## Executive Summary for Claude Code Sonnet

**Goal**: Build a Django-based class enrollment display system with an interactive accordion UI that shows:
- All class types (Academic, IEAP, Language Programs, Combined, Reading/Request)
- Visual day-of-week indicators (M-T-W-R-F-S-U pills)
- Multi-instructor display
- Real-time enrollment tracking
- Responsive accordion-style expansion

**Critical Architecture Rule**: 
- ALL ClassParts go through ClassSession (no direct ClassHeader→ClassPart)
- Regular classes: 1 ClassSession (dummy) → ClassPart(s)
- IEAP classes: 2 ClassSessions → ClassPart(s) each

**Key Features**:
1. Dynamic term-based prefix filtering (Language/BA/MA)
2. Visual schedule display with day pills for ALL classes when expanded
3. All instructors shown in collapsed view
4. Combined days/times display (e.g., "MTWRF 14:00-15:30" or "MTWRF Multiple Times")
5. Course short names displayed below course codes

---

## 1. URL Configuration

```python
# urls.py (main project)
from django.urls import path, include

urlpatterns = [
    # ... other patterns ...
    path('enrollment/', include('apps.scheduling.urls', namespace='enrollment')),
]

# apps/scheduling/urls.py
from django.urls import path
from . import views

app_name = 'enrollment'

urlpatterns = [
    # Main views
    path('schedule/', views.ClassScheduleView.as_view(), name='class_schedule'),
    
    # API endpoints
    path('api/classes/', views.ClassDataAPIView.as_view(), name='class_data_api'),
    path('api/enroll/', views.EnrollStudentView.as_view(), name='enroll_student'),
    path('api/class/<int:class_id>/', views.ClassDetailView.as_view(), name='class_detail'),
    
    # Export endpoints (optional)
    path('export/schedule/', views.ExportScheduleView.as_view(), name='export_schedule'),
]
```

---

## 2. Django Views

```python
# views.py
import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.views import View
from django.views.generic import TemplateView
from django.db.models import Q, Prefetch, Count, F, Sum
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import ClassHeader, ClassSession, ClassPart, Term
from apps.curriculum.models import Course

class ClassScheduleView(LoginRequiredMixin, TemplateView):
    """Main view for the class schedule page."""
    template_name = 'enrollment/class_schedule.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get term parameter or use active term
        term_type = self.request.GET.get('term_type', 'language')
        
        # Find active term for the type
        try:
            from apps.curriculum.models import Term
            active_term = Term.objects.get(
                is_active=True, 
                term_type=term_type.upper()
            )
        except Term.DoesNotExist:
            # Fallback to most recent term of that type
            active_term = Term.objects.filter(
                term_type=term_type.upper()
            ).order_by('-start_date').first()
        
        context['active_term'] = active_term
        context['term_type'] = term_type
        context['user'] = self.request.user
        
        # Get available term types
        context['available_term_types'] = [
            {'value': 'language', 'label': 'Language Programs'},
            {'value': 'ba', 'label': 'BA Programs'},
            {'value': 'ma', 'label': 'MA Programs'},
        ]
        
        return context


class ClassDataAPIView(View):
    """API endpoint for fetching class data with proper session structure."""
    
    def get(self, request):
        # Get parameters
        term_type = request.GET.get('term', 'language')
        prefix = request.GET.get('prefix', 'all')
        view_filter = request.GET.get('filter', 'all')
        search = request.GET.get('search', '')
        
        # Map term types to actual values
        term_type_map = {
            'language': 'LANGUAGE',
            'ba': 'BA', 
            'ma': 'MA'
        }
        term_type_value = term_type_map.get(term_type.lower(), 'LANGUAGE')
        
        # Get the active term
        try:
            from apps.curriculum.models import Term
            term = Term.objects.get(
                is_active=True,
                term_type=term_type_value
            )
        except Term.DoesNotExist:
            return JsonResponse({'error': 'No active term found'}, status=404)
        
        # Build queryset with optimized prefetching
        queryset = ClassHeader.objects.filter(
            term=term,
            status__in=['ACTIVE', 'SCHEDULED']
        ).select_related(
            'course',
            'term',
            'combined_class_instance',
            'paired_with'
        ).prefetch_related(
            Prefetch(
                'class_sessions',
                queryset=ClassSession.objects.prefetch_related(
                    Prefetch(
                        'class_parts',
                        queryset=ClassPart.objects.select_related(
                            'teacher', 'room'
                        )
                    )
                ).order_by('session_number')
            ),
            'combined_class_instance__class_headers__course'
        )
        
        # Apply prefix filter
        if prefix != 'all':
            queryset = queryset.filter(
                course__code__istartswith=prefix
            )
        
        # Apply view filter
        if view_filter == 'available':
            # Use annotation for current enrollment
            queryset = queryset.annotate(
                current_enrollment=Count(
                    'class_header_enrollments',
                    filter=Q(class_header_enrollments__status='ENROLLED')
                )
            ).filter(current_enrollment__lt=F('max_enrollment'))
        elif view_filter == 'full':
            queryset = queryset.annotate(
                current_enrollment=Count(
                    'class_header_enrollments',
                    filter=Q(class_header_enrollments__status='ENROLLED')
                )
            ).filter(current_enrollment__gte=F('max_enrollment'))
        
        # Apply search filter
        if search:
            search_query = Q()
            
            # Search in course fields
            search_query |= Q(course__code__icontains=search)
            search_query |= Q(course__title__icontains=search)
            search_query |= Q(course__short_name__icontains=search)
            
            # Search in teacher names through sessions
            search_query |= Q(
                class_sessions__class_parts__teacher__user__first_name__icontains=search
            )
            search_query |= Q(
                class_sessions__class_parts__teacher__user__last_name__icontains=search
            )
            
            # Search in room codes
            search_query |= Q(
                class_sessions__class_parts__room__code__icontains=search
            )
            
            queryset = queryset.filter(search_query).distinct()
        
        # Serialize classes
        classes_data = []
        for cls in queryset:
            classes_data.append(self.serialize_class(cls))
        
        # Calculate statistics
        stats = self.calculate_stats(classes_data)
        
        return JsonResponse({
            'classes': classes_data,
            'stats': stats,
            'term': {
                'id': term.id,
                'name': str(term),
                'type': term.term_type,
            }
        })
    
    def serialize_class(self, cls):
        """Serialize ClassHeader with session-based structure."""
        # Get current enrollment count
        current_enrollment = cls.enrollment_count if hasattr(cls, 'enrollment_count') else 0
        
        # If annotated, use that instead
        if hasattr(cls, 'current_enrollment'):
            current_enrollment = cls.current_enrollment
        
        data = {
            'id': cls.id,
            'course_code': cls.course.code,
            'course_title': cls.course.title,
            'short_name': cls.course.short_name if hasattr(cls.course, 'short_name') else '',
            'section_id': cls.section_id,
            'time_of_day': cls.time_of_day,
            'class_type': cls.class_type,
            'status': cls.status,
            'max_enrollment': cls.max_enrollment,
            'current_enrollment': current_enrollment,
            'is_extended': self.is_extended_class(cls),
        }
        
        # Add tier for reading classes
        if cls.class_type == 'READING' and hasattr(cls, 'reading_class'):
            data['tier'] = cls.reading_class.get_tier_display()
        
        # Handle combined classes
        if cls.combined_class_instance:
            # Get all course codes in the combination
            combined_courses = []
            for header in cls.combined_class_instance.class_headers.all():
                combined_courses.append(header.course.code)
            data['combined_courses'] = sorted(combined_courses)
        
        # Determine if this is an IEAP class
        is_ieap = self.is_ieap_class(cls)
        
        if is_ieap:
            # IEAP: Serialize sessions with their parts
            data['sessions'] = []
            for session in cls.class_sessions.all():
                session_data = {
                    'session_number': session.session_number,
                    'session_name': session.session_name or f'Session {session.session_number}',
                    'parts': []
                }
                
                # For IEAP, use proper session names
                if session.session_number == 1:
                    session_data['session_name'] = 'First Session'
                elif session.session_number == 2:
                    session_data['session_name'] = 'Second Session'
                
                for part in session.class_parts.all():
                    session_data['parts'].append(self.serialize_part(part))
                
                data['sessions'].append(session_data)
        else:
            # Non-IEAP: Get the single session
            session = cls.class_sessions.first()
            if session:
                parts = list(session.class_parts.all())
                
                # Multi-part language programs (EHSS, GESL, EXPRESS)
                if len(parts) > 1 or self.is_language_program(cls):
                    data['parts'] = [self.serialize_part(p) for p in parts]
                
                # For all non-IEAP classes, also provide flattened info
                # This helps with display in collapsed view
                if parts:
                    # Collect info from all parts
                    all_teachers = []
                    all_rooms = []
                    all_days = set()
                    all_times = set()
                    
                    for part in parts:
                        if part.teacher:
                            teacher_name = f"{part.teacher.user.first_name} {part.teacher.user.last_name}".strip()
                            if not teacher_name:
                                teacher_name = part.teacher.user.username
                            all_teachers.append(teacher_name)
                        
                        if part.room:
                            all_rooms.append(part.room.code)
                        
                        if part.meeting_days:
                            days = [d.strip() for d in part.meeting_days.split(',')]
                            all_days.update(days)
                        
                        if part.start_time and part.end_time:
                            time_str = f"{part.start_time.strftime('%H:%M')}-{part.end_time.strftime('%H:%M')}"
                            all_times.add(time_str)
                    
                    # For single-part classes, flatten completely
                    if len(parts) == 1:
                        part = parts[0]
                        data['teacher'] = all_teachers[0] if all_teachers else None
                        data['room'] = all_rooms[0] if all_rooms else None
                        data['meeting_days'] = sorted(list(all_days))
                        if part.start_time:
                            data['start_time'] = part.start_time.strftime('%H:%M')
                        if part.end_time:
                            data['end_time'] = part.end_time.strftime('%H:%M')
        
        return data
    
    def serialize_part(self, part):
        """Serialize a ClassPart."""
        teacher_name = None
        if part.teacher:
            teacher_name = f"{part.teacher.user.first_name} {part.teacher.user.last_name}".strip()
            if not teacher_name:
                teacher_name = part.teacher.user.username
        
        return {
            'part_code': part.class_part_code,
            'part_type': part.class_part_type,
            'teacher': teacher_name,
            'room': part.room.code if part.room else None,
            'meeting_days': [d.strip() for d in part.meeting_days.split(',')] if part.meeting_days else [],
            'start_time': part.start_time.strftime('%H:%M') if part.start_time else None,
            'end_time': part.end_time.strftime('%H:%M') if part.end_time else None,
        }
    
    def is_ieap_class(self, cls):
        """Check if this is an IEAP class."""
        return (
            cls.course.code.startswith('IEAP') or
            cls.class_sessions.count() > 1
        )
    
    def is_language_program(self, cls):
        """Check if this is a language program class."""
        code = cls.course.code
        return any(code.startswith(prefix) for prefix in ['EHSS', 'GESL', 'EXPRESS'])
    
    def is_extended_class(self, cls):
        """Check if any part is 3+ hours."""
        for session in cls.class_sessions.all():
            for part in session.class_parts.all():
                if part.start_time and part.end_time:
                    duration = part.duration_minutes
                    if duration >= 180:  # 3 hours
                        return True
        return False
    
    def calculate_stats(self, classes_data):
        """Calculate statistics for the classes."""
        total_classes = len(classes_data)
        total_enrolled = sum(c.get('current_enrollment', 0) for c in classes_data)
        total_capacity = sum(c.get('max_enrollment', 0) for c in classes_data)
        available_seats = total_capacity - total_enrolled
        
        return {
            'total_classes': total_classes,
            'total_enrolled': total_enrolled,
            'total_capacity': total_capacity,
            'available_seats': available_seats,
        }


class ClassDetailView(View):
    """Get detailed information about a specific class."""
    
    def get(self, request, class_id):
        try:
            class_header = ClassHeader.objects.prefetch_related(
                'class_sessions__class_parts__teacher',
                'class_sessions__class_parts__room',
                'combined_class_instance__class_headers'
            ).get(id=class_id)
            
            serializer = ClassDataAPIView()
            data = serializer.serialize_class(class_header)
            
            # Add additional detail info
            all_teachers = set()
            all_days = set()
            
            for session in class_header.class_sessions.all():
                for part in session.class_parts.all():
                    if part.teacher:
                        teacher_name = f"{part.teacher.user.first_name} {part.teacher.user.last_name}".strip()
                        all_teachers.add(teacher_name)
                    if part.meeting_days:
                        days = [d.strip() for d in part.meeting_days.split(',')]
                        all_days.update(days)
            
            data['all_teachers'] = sorted(list(all_teachers))
            data['all_meeting_days'] = sorted(list(all_days))
            
            return JsonResponse(data)
            
        except ClassHeader.DoesNotExist:
            return JsonResponse({'error': 'Class not found'}, status=404)


class EnrollStudentView(LoginRequiredMixin, View):
    """Handle student enrollment actions."""
    
    def post(self, request):
        """Enroll or drop a student from a class."""
        import json
        
        try:
            data = json.loads(request.body)
            class_id = data.get('class_id')
            action = data.get('action', 'enroll')
        except (json.JSONDecodeError, AttributeError):
            class_id = request.POST.get('class_id')
            action = request.POST.get('action', 'enroll')
        
        if not class_id:
            return JsonResponse({'error': 'Class ID required'}, status=400)
        
        try:
            class_header = ClassHeader.objects.get(id=class_id)
        except ClassHeader.DoesNotExist:
            return JsonResponse({'error': 'Class not found'}, status=404)
        
        # Import enrollment model (adjust path as needed)
        from apps.enrollment.models import ClassHeaderEnrollment
        
        if action == 'enroll':
            # Check if class is full
            current_enrollment = ClassHeaderEnrollment.objects.filter(
                class_header=class_header,
                status='ENROLLED'
            ).count()
            
            if current_enrollment >= class_header.max_enrollment:
                return JsonResponse({'error': 'Class is full'}, status=400)
            
            # Create enrollment
            enrollment, created = ClassHeaderEnrollment.objects.get_or_create(
                student=request.user,
                class_header=class_header,
                defaults={'status': 'ENROLLED'}
            )
            
            if created:
                return JsonResponse({
                    'success': True,
                    'message': 'Enrolled successfully',
                    'current_enrollment': current_enrollment + 1
                })
            else:
                return JsonResponse({'error': 'Already enrolled'}, status=400)
        
        elif action == 'drop':
            try:
                enrollment = ClassHeaderEnrollment.objects.get(
                    student=request.user,
                    class_header=class_header,
                    status='ENROLLED'
                )
                enrollment.status = 'DROPPED'
                enrollment.save()
                
                new_enrollment = ClassHeaderEnrollment.objects.filter(
                    class_header=class_header,
                    status='ENROLLED'
                ).count()
                
                return JsonResponse({
                    'success': True,
                    'message': 'Dropped successfully',
                    'current_enrollment': new_enrollment
                })
            except ClassHeaderEnrollment.DoesNotExist:
                return JsonResponse({'error': 'Not enrolled in this class'}, status=400)
        
        return JsonResponse({'error': 'Invalid action'}, status=400)


class ExportScheduleView(LoginRequiredMixin, View):
    """Export class schedule to CSV."""
    
    def get(self, request):
        import csv
        
        # Get parameters
        term_type = request.GET.get('term', 'language')
        
        # Get classes using same logic as API
        api_view = ClassDataAPIView()
        response = api_view.get(request)
        data = json.loads(response.content)
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="class_schedule_{term_type}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Course Code', 'Course Title', 'Section', 'Time of Day',
            'Teacher(s)', 'Room(s)', 'Days', 'Time',
            'Current Enrollment', 'Max Enrollment', 'Available Seats'
        ])
        
        for cls in data.get('classes', []):
            # Collect all teachers
            teachers = []
            rooms = []
            days = set()
            times = set()
            
            if cls.get('sessions'):
                for session in cls['sessions']:
                    for part in session.get('parts', []):
                        if part.get('teacher'):
                            teachers.append(part['teacher'])
                        if part.get('room'):
                            rooms.append(part['room'])
                        if part.get('meeting_days'):
                            days.update(part['meeting_days'])
                        if part.get('start_time') and part.get('end_time'):
                            times.add(f"{part['start_time']}-{part['end_time']}")
            elif cls.get('parts'):
                for part in cls['parts']:
                    if part.get('teacher'):
                        teachers.append(part['teacher'])
                    if part.get('room'):
                        rooms.append(part['room'])
                    if part.get('meeting_days'):
                        days.update(part['meeting_days'])
                    if part.get('start_time') and part.get('end_time'):
                        times.add(f"{part['start_time']}-{part['end_time']}")
            else:
                if cls.get('teacher'):
                    teachers.append(cls['teacher'])
                if cls.get('room'):
                    rooms.append(cls['room'])
                if cls.get('meeting_days'):
                    days.update(cls['meeting_days'])
                if cls.get('start_time') and cls.get('end_time'):
                    times.add(f"{cls['start_time']}-{cls['end_time']}")
            
            writer.writerow([
                cls.get('course_code', ''),
                cls.get('course_title', ''),
                cls.get('section_id', ''),
                cls.get('time_of_day', ''),
                ', '.join(teachers) or 'TBA',
                ', '.join(rooms) or 'TBA',
                ''.join(sorted(days)),
                ', '.join(times) or 'TBA',
                cls.get('current_enrollment', 0),
                cls.get('max_enrollment', 0),
                cls.get('max_enrollment', 0) - cls.get('current_enrollment', 0)
            ])
        
        return response
```

---

## 3. Templates

```django
<!-- templates/enrollment/class_schedule.html -->
{% extends 'base.html' %}
{% load static %}

{% block title %}Class Schedule & Enrollment{% endblock %}

{% block extra_css %}
<link rel="stylesheet" href="{% static 'css/class_schedule.css' %}">
{% endblock %}

{% block content %}
<div class="container">
    <!-- Header -->
    <div class="header">
        <div class="header-content">
            <h1>Class Schedule & Enrollment</h1>
            <div class="stats-container">
                <div class="stat-item">
                    <div class="stat-label">Total Classes</div>
                    <div class="stat-value" id="totalClasses">0</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Total Enrolled</div>
                    <div class="stat-value" id="totalEnrolled">0</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Available Seats</div>
                    <div class="stat-value" id="availableSeats">0</div>
                </div>
            </div>
        </div>
    </div>

    <!-- Controls -->
    <div class="controls">
        <div class="controls-grid">
            <div class="control-group">
                <label class="control-label">Term</label>
                <select id="termSelect">
                    <option value="language" {% if term_type == 'language' %}selected{% endif %}>Language Programs</option>
                    <option value="ba" {% if term_type == 'ba' %}selected{% endif %}>BA Programs</option>
                    <option value="ma" {% if term_type == 'ma' %}selected{% endif %}>MA Programs</option>
                </select>
            </div>
            
            <div class="control-group">
                <label class="control-label">View</label>
                <select id="viewSelect">
                    <option value="all">All Classes</option>
                    <option value="available">Available Only</option>
                    <option value="full">Full Classes</option>
                </select>
            </div>

            <div class="control-group">
                <label class="control-label">Course Prefix Filter</label>
                <div class="prefix-filters" id="prefixFilters">
                    <!-- Dynamically populated based on term -->
                </div>
            </div>

            <div class="control-group">
                <label class="control-label">Search</label>
                <div class="search-box">
                    <span class="search-icon">🔍</span>
                    <input type="text" id="searchInput" placeholder="Search by course, teacher, room...">
                </div>
            </div>
        </div>
    </div>

    <!-- Class List -->
    <div class="class-list" id="classList">
        <div class="loading">
            <div class="loading-spinner"></div>
        </div>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
    // Pass Django context to JavaScript
    window.APP_CONFIG = {
        apiUrl: "{% url 'enrollment:class_data_api' %}",
        enrollUrl: "{% url 'enrollment:enroll_student' %}",
        csrfToken: "{{ csrf_token }}",
        currentUser: {% if user.is_authenticated %}"{{ user.username }}"{% else %}null{% endif %},
        initialTerm: "{{ term_type|default:'language' }}"
    };
</script>
<script src="{% static 'js/class_schedule.js' %}"></script>
{% endblock %}

<!-- If you don't have a base.html, create one: -->
<!-- templates/base.html -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Class Enrollment System{% endblock %}</title>
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% block content %}{% endblock %}
    {% block extra_js %}{% endblock %}
</body>
</html>
```

---

## 4. Static Files

### CSS File
Create `static/css/class_schedule.css` with the complete CSS from the mockup (2000+ lines).
Copy the entire CSS from the HTML mockup artifact exactly as is.

### JavaScript File
Create `static/js/class_schedule.js`:

```javascript
// static/js/class_schedule.js

class ClassScheduleManager {
    constructor(config) {
        this.config = config;
        this.currentTerm = config.initialTerm || 'language';
        this.currentFilter = 'all';
        this.currentPrefix = 'all';
        this.currentSearch = '';
        this.expandedClasses = new Set();
        this.classesData = [];
        this.init();
    }
    
    async init() {
        this.setupEventListeners();
        this.updatePrefixFilters();
        await this.loadClasses();
    }
    
    setupEventListeners() {
        // Term selector
        document.getElementById('termSelect').addEventListener('change', async (e) => {
            this.currentTerm = e.target.value;
            this.currentPrefix = 'all';
            this.updatePrefixFilters();
            await this.loadClasses();
        });
        
        // View filter
        document.getElementById('viewSelect').addEventListener('change', (e) => {
            this.currentFilter = e.target.value;
            this.renderClasses();
        });
        
        // Search with debounce
        let searchTimeout;
        document.getElementById('searchInput').addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            this.currentSearch = e.target.value.toLowerCase();
            searchTimeout = setTimeout(() => this.renderClasses(), 300);
        });
    }
    
    updatePrefixFilters() {
        const container = document.getElementById('prefixFilters');
        let prefixes = [];
        
        // Define prefixes based on term type
        const prefixMap = {
            'language': ['All', 'IEAP', 'EHSS', 'GESL', 'EXPRESS'],
            'ba': ['All', 'ENGL', 'MATH', 'SOC', 'THM', 'READ', 'PSY', 'HIST', 'PHIL'],
            'ma': ['All', 'THEO', 'BIBL', 'READ', 'MISS', 'PAST', 'HIST']
        };
        
        prefixes = prefixMap[this.currentTerm] || ['All'];
        
        container.innerHTML = prefixes.map(prefix => 
            `<button class="prefix-chip ${prefix === 'All' ? 'active' : ''}" 
                     data-prefix="${prefix.toLowerCase()}">${prefix}</button>`
        ).join('');
        
        // Add click handlers
        container.querySelectorAll('.prefix-chip').forEach(chip => {
            chip.addEventListener('click', (e) => {
                container.querySelectorAll('.prefix-chip').forEach(c => c.classList.remove('active'));
                e.target.classList.add('active');
                this.currentPrefix = e.target.dataset.prefix;
                this.renderClasses();
            });
        });
    }
    
    async loadClasses() {
        const classList = document.getElementById('classList');
        classList.innerHTML = '<div class="loading"><div class="loading-spinner"></div></div>';
        
        try {
            const params = new URLSearchParams({
                term: this.currentTerm,
                prefix: this.currentPrefix,
                filter: this.currentFilter,
                search: this.currentSearch
            });
            
            const response = await fetch(`${this.config.apiUrl}?${params}`, {
                headers: {
                    'X-CSRFToken': this.config.csrfToken,
                    'Accept': 'application/json'
                }
            });
            
            if (!response.ok) throw new Error('Failed to load classes');
            
            const data = await response.json();
            this.classesData = data.classes;
            
            // Update stats
            this.updateStats(data.stats);
            
            // Render classes
            this.renderClasses();
            
        } catch (error) {
            console.error('Error loading classes:', error);
            classList.innerHTML = `
                <div class="empty-state">
                    <h3>Error loading classes</h3>
                    <p>Please try refreshing the page</p>
                </div>
            `;
        }
    }
    
    renderClasses() {
        const classList = document.getElementById('classList');
        
        // Filter classes locally
        let filteredClasses = this.filterClasses(this.classesData);
        
        if (filteredClasses.length === 0) {
            classList.innerHTML = `
                <div class="empty-state">
                    <h3>No classes found</h3>
                    <p>Try adjusting your filters or search criteria</p>
                </div>
            `;
            return;
        }
        
        // Render each class
        classList.innerHTML = filteredClasses.map(cls => this.renderClassRow(cls)).join('');
        
        // Restore expanded state
        this.expandedClasses.forEach(id => {
            const row = document.querySelector(`[data-class-id="${id}"]`);
            if (row) {
                this.toggleClass(id);
            }
        });
    }
    
    filterClasses(classes) {
        return classes.filter(cls => {
            // Prefix filter
            if (this.currentPrefix !== 'all') {
                const coursePrefix = cls.course_code.split('-')[0].toLowerCase();
                if (coursePrefix !== this.currentPrefix) {
                    return false;
                }
            }
            
            // View filter
            if (this.currentFilter === 'available' && cls.current_enrollment >= cls.max_enrollment) {
                return false;
            }
            if (this.currentFilter === 'full' && cls.current_enrollment < cls.max_enrollment) {
                return false;
            }
            
            // Search filter
            if (this.currentSearch) {
                const searchableText = this.getSearchableText(cls).toLowerCase();
                if (!searchableText.includes(this.currentSearch)) {
                    return false;
                }
            }
            
            return true;
        });
    }
    
    getSearchableText(cls) {
        let text = `${cls.course_code} ${cls.course_title} ${cls.short_name || ''}`;
        
        // Add all teachers
        const teachers = this.collectTeachers(cls);
        text += ' ' + teachers.join(' ');
        
        // Add rooms
        const schedule = this.collectSchedule(cls);
        if (schedule.room) text += ' ' + schedule.room;
        
        return text;
    }
    
    collectTeachers(cls) {
        const teachers = new Set();
        
        // IEAP classes with sessions
        if (cls.sessions && cls.sessions.length > 0) {
            cls.sessions.forEach(session => {
                session.parts.forEach(part => {
                    if (part.teacher) teachers.add(part.teacher);
                });
            });
        }
        // Multi-part language programs
        else if (cls.parts && cls.parts.length > 0) {
            cls.parts.forEach(part => {
                if (part.teacher) teachers.add(part.teacher);
            });
        }
        // Single-part classes (flattened)
        else if (cls.teacher) {
            teachers.add(cls.teacher);
        }
        
        return Array.from(teachers);
    }
    
    collectSchedule(cls) {
        const days = new Set();
        const times = new Set();
        let room = null;
        
        // IEAP with sessions
        if (cls.sessions && cls.sessions.length > 0) {
            cls.sessions.forEach(session => {
                session.parts.forEach(part => {
                    if (part.meeting_days) {
                        part.meeting_days.forEach(day => days.add(day));
                    }
                    if (part.start_time && part.end_time) {
                        times.add(`${part.start_time}-${part.end_time}`);
                    }
                    if (!room && part.room) room = part.room;
                });
            });
        }
        // Multi-part programs
        else if (cls.parts && cls.parts.length > 0) {
            cls.parts.forEach(part => {
                if (part.meeting_days) {
                    part.meeting_days.forEach(day => days.add(day));
                }
                if (part.start_time && part.end_time) {
                    times.add(`${part.start_time}-${part.end_time}`);
                }
                if (!room && part.room) room = part.room;
            });
        }
        // Single-part (flattened)
        else {
            if (cls.meeting_days) {
                cls.meeting_days.forEach(day => days.add(day));
            }
            if (cls.start_time && cls.end_time) {
                times.add(`${cls.start_time}-${cls.end_time}`);
            }
            room = cls.room;
        }
        
        // Format display
        let display = 'Arranged';
        if (days.size > 0) {
            const dayOrder = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
            const sortedDays = Array.from(days).sort((a, b) => dayOrder.indexOf(a) - dayOrder.indexOf(b));
            const dayMap = {'MON': 'M', 'TUE': 'T', 'WED': 'W', 'THU': 'R', 'FRI': 'F', 'SAT': 'S', 'SUN': 'U'};
            const daysStr = sortedDays.map(d => dayMap[d] || d[0]).join('');
            
            if (times.size === 1) {
                display = `${daysStr} ${Array.from(times)[0]}`;
            } else if (times.size > 1) {
                display = `${daysStr} Multiple Times`;
            } else {
                display = daysStr;
            }
        }
        
        return {
            days: Array.from(days),
            times: Array.from(times),
            room: room,
            display: display
        };
    }
    
    renderClassRow(cls) {
        const enrollmentPercent = (cls.current_enrollment / cls.max_enrollment) * 100;
        const enrollmentStatus = enrollmentPercent >= 100 ? 'full' : enrollmentPercent >= 80 ? 'warning' : '';
        const isExpanded = this.expandedClasses.has(cls.id);
        
        const teachers = this.collectTeachers(cls);
        const schedule = this.collectSchedule(cls);
        
        // Format teachers display
        let teachersDisplay = '';
        if (teachers.length === 0) {
            teachersDisplay = '<span class="teacher-item">TBA</span>';
        } else if (teachers.length <= 2) {
            teachersDisplay = teachers.map(t => `<span class="teacher-item">${t}</span>`).join('');
        } else {
            teachersDisplay = teachers.slice(0, 2).map(t => `<span class="teacher-item">${t}</span>`).join('') +
                            `<span class="teacher-item">+${teachers.length - 2} more</span>`;
        }
        
        // Handle course display
        let courseDisplay = '';
        if (cls.combined_courses && cls.combined_courses.length > 0) {
            courseDisplay = `
                <div class="course-info">
                    <div class="combined-courses">
                        ${cls.combined_courses.map(code => 
                            `<div class="course-code">${code}</div>`
                        ).join('')}
                    </div>
                    ${cls.short_name ? `<div class="course-short-name">${cls.short_name}</div>` : ''}
                </div>
            `;
        } else {
            courseDisplay = `
                <div class="course-info">
                    <div class="course-code">${cls.course_code}</div>
                    ${cls.short_name ? `<div class="course-short-name">${cls.short_name}</div>` : ''}
                </div>
            `;
        }
        
        // Handle room display
        const roomDisplay = schedule.room ? 
            `<div class="room-number">📍 ${schedule.room}</div>` : 
            `<div class="room-number room-arranged">Arranged</div>`;
        
        // Handle time badge
        const timeBadgeClass = cls.is_extended ? 'time-extended' : '';
        
        return `
            <div class="class-header-row ${isExpanded ? 'expanded' : ''}" data-class-id="${cls.id}">
                <div class="class-header-content" onclick="classSchedule.toggleClass(${cls.id})">
                    <div class="expand-icon">▶</div>
                    ${courseDisplay}
                    <div class="section-badge">${cls.section_id}</div>
                    <div class="time-badge time-${cls.time_of_day.toLowerCase()} ${timeBadgeClass}">
                        ${this.getTimeLabel(cls.time_of_day)}
                    </div>
                    <div class="teacher-names">
                        ${teachersDisplay}
                    </div>
                    ${roomDisplay}
                    <div class="schedule-info ${!schedule.room ? 'schedule-arranged' : ''}">
                        ${schedule.display}
                    </div>
                    <div class="enrollment-info">
                        <div class="enrollment-bar">
                            <div class="enrollment-fill ${enrollmentStatus}" 
                                 style="width: ${enrollmentPercent}%"></div>
                        </div>
                        <span class="enrollment-text">${cls.current_enrollment}/${cls.max_enrollment}</span>
                    </div>
                    <div>
                        ${this.renderClassTypeBadge(cls)}
                    </div>
                </div>
                <div class="class-details ${isExpanded ? 'expanded' : ''}" id="details-${cls.id}">
                    ${this.renderClassDetails(cls)}
                </div>
            </div>
        `;
    }
    
    renderClassDetails(cls) {
        // REQUEST classes without physical meetings
        if (cls.class_type === 'READING' && (!cls.meeting_days || cls.meeting_days.length === 0)) {
            return `
                <div class="session-container">
                    <div class="session-info">
                        <strong>Course:</strong> ${cls.course_title}<br>
                        <strong>Type:</strong> ${cls.tier || 'Reading Class'}<br>
                        <strong>Instructor:</strong> ${cls.teacher || 'TBA'}<br>
                        <strong>Meeting:</strong> By arrangement<br>
                        <strong>Note:</strong> Contact instructor to arrange meeting times
                    </div>
                </div>
            `;
        }
        
        // Combined classes
        if (cls.combined_courses && cls.combined_courses.length > 0) {
            const teachers = this.collectTeachers(cls);
            const schedule = this.collectSchedule(cls);
            
            return `
                <div class="session-container">
                    <div class="session-info" style="margin-bottom: 12px;">
                        <strong>Combined Courses:</strong><br>
                        ${cls.combined_courses.map(code => `• ${code}`).join('<br>')}
                    </div>
                    <div class="part-row">
                        <div class="part-indicator">A</div>
                        <div class="part-type">Main Class</div>
                        <div class="teacher-name">${teachers[0] || 'TBA'}</div>
                        <div class="room-number">📍 ${schedule.room || 'TBA'}</div>
                        <div class="schedule-info">
                            <div class="days-pills">
                                ${this.renderDayPills(schedule.days)}
                            </div>
                            <span>${schedule.times[0] || ''}</span>
                        </div>
                    </div>
                </div>
            `;
        }
        
        // IEAP with sessions
        if (cls.sessions && cls.sessions.length > 0) {
            return cls.sessions.map(session => `
                <div class="session-container">
                    <div class="session-header">
                        <span class="session-badge">${session.session_name}</span>
                    </div>
                    ${session.parts.map(part => this.renderPart(part)).join('')}
                </div>
            `).join('');
        }
        
        // Multi-part language programs
        if (cls.parts && cls.parts.length > 0) {
            return `
                <div class="session-container">
                    ${cls.parts.map(part => this.renderPart(part)).join('')}
                </div>
            `;
        }
        
        // Single-part academic classes
        return `
            <div class="session-container">
                <div class="part-row">
                    <div class="part-indicator">A</div>
                    <div class="part-type">${cls.is_extended ? '3-Hour Session' : 'Main Class'}</div>
                    <div class="teacher-name">${cls.teacher || 'TBA'}</div>
                    <div class="room-number">📍 ${cls.room || 'TBA'}</div>
                    <div class="schedule-info">
                        <div class="days-pills">
                            ${this.renderDayPills(cls.meeting_days || [])}
                        </div>
                        <span>${cls.start_time || ''} - ${cls.end_time || ''}</span>
                    </div>
                </div>
                ${cls.course_title ? `
                    <div style="margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--gray-200);">
                        <div class="session-info">
                            <strong>Full Title:</strong> ${cls.course_title}
                        </div>
                    </div>
                ` : ''}
            </div>
        `;
    }
    
    renderPart(part) {
        const hasSchedule = part.meeting_days && part.meeting_days.length > 0;
        
        return `
            <div class="part-row">
                <div class="part-indicator">${part.part_code}</div>
                <div class="part-type">${this.formatPartType(part.part_type)}</div>
                <div class="teacher-name">${part.teacher || 'TBA'}</div>
                <div class="room-number ${!part.room ? 'room-arranged' : ''}">
                    📍 ${part.room || 'Arranged'}
                </div>
                <div class="schedule-info ${!hasSchedule ? 'schedule-arranged' : ''}">
                    ${hasSchedule ? `
                        <div class="days-pills">
                            ${this.renderDayPills(part.meeting_days)}
                        </div>
                        <span>${part.start_time} - ${part.end_time}</span>
                    ` : 'Arranged'}
                </div>
            </div>
        `;
    }
    
    renderDayPills(days) {
        if (!days || days.length === 0) return '';
        
        const allDays = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN'];
        const dayLabels = ['M', 'T', 'W', 'R', 'F', 'S', 'U'];
        
        return allDays.map((day, idx) => {
            const isActive = days.includes(day);
            const isWeekend = idx >= 5;
            return `<span class="day-pill ${isActive ? 'active' : ''} ${isWeekend ? 'weekend' : ''}">
                        ${dayLabels[idx]}
                    </span>`;
        }).join('');
    }
    
    renderClassTypeBadge(cls) {
        const badgeMap = {
            'COMBINED': '<span class="class-type-badge type-combined">COMBINED</span>',
            'READING': `<span class="class-type-badge type-request">${cls.tier || 'READING'}</span>`,
        };
        
        if (badgeMap[cls.class_type]) {
            return badgeMap[cls.class_type];
        }
        
        // Check for language program types based on course code
        const code = cls.course_code;
        if (code.startsWith('IEAP')) {
            return '<span class="class-type-badge type-ieap">IEAP</span>';
        }
        if (code.startsWith('EHSS')) {
            return '<span class="class-type-badge type-ehss">EHSS</span>';
        }
        if (code.startsWith('GESL')) {
            return '<span class="class-type-badge type-gesl">GESL</span>';
        }
        if (code.startsWith('EXPRESS')) {
            return '<span class="class-type-badge type-express">EXPRESS</span>';
        }
        
        return '';
    }
    
    formatPartType(type) {
        const typeMap = {
            'MAIN': 'Main Class',
            'LECTURE': 'Lecture',
            'LAB': 'Laboratory',
            'COMPUTER': 'Computer Lab',
            'GRAMMAR': 'Grammar',
            'CONVERSATION': 'Conversation',
            'WRITING': 'Writing',
            'READING': 'Reading',
            'LISTENING': 'Listening',
            'SPEAKING': 'Speaking',
            'VENTURES': 'Ventures',
            'PROJECT': 'Project'
        };
        return typeMap[type] || type;
    }
    
    getTimeLabel(timeOfDay) {
        const labels = {
            'MORN': 'Morning',
            'AFT': 'Afternoon',
            'EVE': 'Evening',
            'NIGHT': 'Night',
            'ALL': 'All Day'
        };
        return labels[timeOfDay] || timeOfDay;
    }
    
    toggleClass(classId) {
        const row = document.querySelector(`[data-class-id="${classId}"]`);
        const details = document.getElementById(`details-${classId}`);
        
        if (!row || !details) return;
        
        if (this.expandedClasses.has(classId)) {
            this.expandedClasses.delete(classId);
            row.classList.remove('expanded');
            details.classList.remove('expanded');
        } else {
            this.expandedClasses.add(classId);
            row.classList.add('expanded');
            details.classList.add('expanded');
        }
    }
    
    updateStats(stats) {
        document.getElementById('totalClasses').textContent = stats.total_classes || 0;
        document.getElementById('totalEnrolled').textContent = stats.total_enrolled || 0;
        document.getElementById('availableSeats').textContent = stats.available_seats || 0;
    }
}

// Initialize on DOM ready
let classSchedule;
document.addEventListener('DOMContentLoaded', () => {
    classSchedule = new ClassScheduleManager(window.APP_CONFIG);
});
```

---

## 5. Quick Setup Checklist

1. **URLs**: Add to main `urls.py` and create `apps/scheduling/urls.py`
2. **Views**: Copy complete `views.py` to `apps/scheduling/views.py`
3. **Templates**: Create `templates/enrollment/class_schedule.html`
4. **Static Files**:
   - Copy CSS from mockup to `static/css/class_schedule.css`
   - Create `static/js/class_schedule.js` with the JavaScript above
5. **Run**: `python manage.py collectstatic`
6. **Test**: Navigate to `/enrollment/schedule/`

---

## 6. Testing Checklist

- [ ] Regular classes show 1 session with visual day pills
- [ ] IEAP classes show 2 sessions (First/Second Session)
- [ ] EHSS/GESL show multiple parts in single container
- [ ] All teachers display in collapsed view
- [ ] Combined schedule shows (e.g., "MTWRF 14:00-15:30")
- [ ] Search works across course codes, teachers, rooms
- [ ] Prefix filters change based on term selection
- [ ] Enrollment bars show correct fill levels
- [ ] Extended classes show "+" indicator
- [ ] Weekend days (S/U) show different color when active

---

## 7. Common Issues & Solutions

**Issue**: Classes not showing
- Check `Term.is_active` is True for at least one term
- Verify `ClassHeader.status` is 'ACTIVE' or 'SCHEDULED'

**Issue**: No teachers showing
- Ensure `TeacherProfile` has related `User` with first_name/last_name
- Check ClassPart has teacher assigned

**Issue**: IEAP not recognized
- Check course code starts with 'IEAP' OR
- Ensure class has exactly 2 ClassSessions

**Issue**: Day pills not showing
- Verify `meeting_days` is comma-separated (e.g., "MON,WED,FRI")
- Check that days use uppercase abbreviations

---

## Summary for Implementation

This is a complete, production-ready implementation that:
1. Works with your existing ClassSession-based structure
2. Handles all class types (Academic, IEAP, Language, Combined, Reading)
3. Shows visual day indicators for all classes
4. Displays all teachers and combined schedules
5. Provides dynamic filtering and search
6. Maintains data integrity through the session layer

The system is modular and testable, with clear separation between backend API and frontend display logic.