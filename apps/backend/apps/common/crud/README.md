# Django CRUD Framework

A reusable, feature-rich CRUD framework for Django that provides:

- **List Views** with sorting, searching, filtering, and pagination
- **Column Management** - Show/hide columns with persistence
- **Export Functionality** - CSV and XLSX export
- **HTMX Integration** - Smooth, no-refresh interactions
- **Permission Management** - Built-in permission checks
- **Responsive Design** - Mobile-friendly with Tailwind CSS
- **Dark Mode Support** - Full dark mode compatibility
- **Customizable Templates** - Easy to override and extend

## Quick Start

### 1. Basic Usage

```python
# views.py
from django.urls import reverse_lazy
from apps.common.crud import CRUDListView, CRUDCreateView, CRUDUpdateView
from apps.common.crud import CRUDDetailView, CRUDDeleteView
from apps.common.crud.config import CRUDConfig, FieldConfig
from .models import Student

class StudentListView(CRUDListView):
    model = Student

    crud_config = CRUDConfig(
        page_title="Student Management",
        page_subtitle="Manage student records",
        page_icon="fas fa-graduation-cap",

        # Define fields to display
        fields=[
            FieldConfig(name="student_id", verbose_name="Student ID"),
            FieldConfig(name="name", searchable=True),
            FieldConfig(name="email", searchable=True),
            FieldConfig(name="major", field_type="foreign_key", searchable=True),
            FieldConfig(name="gpa", field_type="number", format=2),
            FieldConfig(name="is_active", field_type="boolean"),
            FieldConfig(name="created_at", field_type="datetime"),
        ],

        # Enable features
        enable_search=True,
        enable_export=True,
        enable_column_toggle=True,

        # URLs
        list_url_name="students:list",
        create_url_name="students:create",
        update_url_name="students:update",
        delete_url_name="students:delete",
        detail_url_name="students:detail",

        # Row actions
        row_actions=[
            {"type": "view"},
            {"type": "edit"},
            {"type": "delete"},
        ]
    )

class StudentCreateView(CRUDCreateView):
    model = Student
    fields = ['student_id', 'name', 'email', 'major', 'gpa']
    crud_config = CRUDConfig(
        page_icon="fas fa-user-plus",
        list_url_name="students:list",
    )

class StudentUpdateView(CRUDUpdateView):
    model = Student
    fields = ['name', 'email', 'major', 'gpa', 'is_active']
    crud_config = CRUDConfig(
        page_icon="fas fa-user-edit",
        list_url_name="students:list",
    )

class StudentDetailView(CRUDDetailView):
    model = Student
    crud_config = CRUDConfig(
        page_icon="fas fa-user",
        fields=[
            FieldConfig(name="student_id", verbose_name="Student ID"),
            FieldConfig(name="name"),
            FieldConfig(name="email"),
            FieldConfig(name="major"),
            FieldConfig(name="gpa", field_type="number", format=2),
            FieldConfig(name="is_active", field_type="boolean"),
            FieldConfig(name="created_at", field_type="datetime"),
            FieldConfig(name="updated_at", field_type="datetime"),
        ],
        list_url_name="students:list",
        update_url_name="students:update",
        delete_url_name="students:delete",
    )

class StudentDeleteView(CRUDDeleteView):
    model = Student
    crud_config = CRUDConfig(
        list_url_name="students:list",
    )
```

### 2. URLs Configuration

```python
# urls.py
from django.urls import path
from . import views

app_name = 'students'

urlpatterns = [
    path('', views.StudentListView.as_view(), name='list'),
    path('add/', views.StudentCreateView.as_view(), name='create'),
    path('<int:pk>/', views.StudentDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.StudentUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.StudentDeleteView.as_view(), name='delete'),
]
```

### 3. Advanced Features

#### Custom Field Renderers

```python
from django.utils.html import format_html

def render_status(value, field_config):
    """Custom renderer for status field."""
    if value == 'active':
        return format_html(
            '<span class="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">Active</span>'
        )
    return format_html(
        '<span class="px-2 py-1 text-xs rounded-full bg-gray-100 text-gray-800">Inactive</span>'
    )

crud_config = CRUDConfig(
    fields=[
        FieldConfig(
            name="status",
            renderer=render_status
        ),
    ]
)
```

#### Custom Filters

```python
# In your list view
class StudentListView(CRUDListView):
    model = Student

    def get_queryset(self):
        queryset = super().get_queryset()

        # Add custom filtering
        major_id = self.request.GET.get('major')
        if major_id:
            queryset = queryset.filter(major_id=major_id)

        status = self.request.GET.get('status')
        if status == 'active':
            queryset = queryset.filter(is_active=True)
        elif status == 'inactive':
            queryset = queryset.filter(is_active=False)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add filter options to context
        context['majors'] = Major.objects.all()
        return context
```

Then in your template, extend the filter section:

```html
{% extends "common/crud/list.html" %}

{% block additional_filters %}
    <select name="major"
            class="block px-3 py-2 border border-gray-300 rounded-md"
            hx-get="{{ request.path }}"
            hx-trigger="change"
            hx-target="#crud-table-container"
            hx-include="[name='search'], [name='sort_by'], [name='direction']">
        <option value="">All Majors</option>
        {% for major in majors %}
            <option value="{{ major.id }}"
                    {% if request.GET.major == major.id|stringformat:"s" %}selected{% endif %}>
                {{ major.name }}
            </option>
        {% endfor %}
    </select>
{% endblock %}
```

#### Bulk Actions

```python
crud_config = CRUDConfig(
    enable_bulk_actions=True,
    bulk_actions=[
        {
            "name": "activate",
            "label": "Activate Selected",
            "icon": "fas fa-check",
            "confirm": "Are you sure you want to activate selected items?",
        },
        {
            "name": "deactivate",
            "label": "Deactivate Selected",
            "icon": "fas fa-times",
            "confirm": "Are you sure you want to deactivate selected items?",
        },
    ]
)

# Handle bulk actions in your view
def post(self, request, *args, **kwargs):
    action = request.POST.get('bulk_action')
    selected_ids = request.POST.getlist('selected_items')

    if action == 'activate':
        Student.objects.filter(id__in=selected_ids).update(is_active=True)
        messages.success(request, f"Activated {len(selected_ids)} students.")
    elif action == 'deactivate':
        Student.objects.filter(id__in=selected_ids).update(is_active=False)
        messages.success(request, f"Deactivated {len(selected_ids)} students.")

    return self.get(request, *args, **kwargs)
```

#### Field Links

```python
fields=[
    FieldConfig(
        name="student_id",
        link_url="/students/{pk}/",  # Links to detail view
    ),
    FieldConfig(
        name="major",
        field_type="foreign_key",
        link_url="/majors/{value.pk}/",  # Links to related object
    ),
]
```

#### Custom Context

```python
crud_config = CRUDConfig(
    extra_context={
        "stats": {
            "total_students": Student.objects.count(),
            "active_students": Student.objects.filter(is_active=True).count(),
        }
    }
)
```

### 4. Permissions

The framework automatically checks Django permissions:

- List views check `app.view_model` permission
- Create views check `app.add_model` permission
- Update views check `app.change_model` permission
- Delete views check `app.delete_model` permission

You can override these:

```python
crud_config = CRUDConfig(
    list_permission="students.view_student_records",
    create_permission="students.add_student_records",
    update_permission="students.change_student_records",
    delete_permission="students.delete_student_records",
    export_permission="students.export_student_records",
)
```

### 5. Export Configuration

```python
crud_config = CRUDConfig(
    enable_export=True,
    export_formats=["csv", "xlsx"],  # Default both
    export_filename_prefix="students",
    fields=[
        FieldConfig(name="student_id", export=True),
        FieldConfig(name="name", export=True),
        FieldConfig(name="email", export=True),
        FieldConfig(name="ssn", export=False),  # Exclude sensitive data
    ]
)
```

### 6. Auto-Generated Fields

If you don't specify fields, the framework will auto-generate them from your model:

```python
class SimpleListView(CRUDListView):
    model = Student
    crud_config = CRUDConfig(
        page_title="Students",
        # Fields will be auto-generated from Student model
    )
```

### 7. Custom Templates

Override any template by creating your own:

```
templates/
└── students/
    ├── student_list.html    # Extends common/crud/list.html
    ├── student_form.html    # Extends common/crud/form.html
    └── student_detail.html  # Extends common/crud/detail.html
```

Then update your config:

```python
crud_config = CRUDConfig(
    list_template="students/student_list.html",
    form_template="students/student_form.html",
    detail_template="students/student_detail.html",
)
```

## Configuration Reference

### CRUDConfig Options

| Option                  | Type              | Default           | Description              |
| ----------------------- | ----------------- | ----------------- | ------------------------ |
| `page_title`            | str               | "Data Management" | Page title               |
| `page_subtitle`         | str               | None              | Optional subtitle        |
| `page_icon`             | str               | None              | Font Awesome icon class  |
| `fields`                | List[FieldConfig] | []                | Field configurations     |
| `default_sort_field`    | str               | "-id"             | Default sort field       |
| `paginate_by`           | int               | 25                | Items per page           |
| `paginate_choices`      | List[int]         | [10, 25, 50, 100] | Page size options        |
| `enable_search`         | bool              | True              | Enable search            |
| `enable_filters`        | bool              | True              | Enable filters           |
| `enable_export`         | bool              | True              | Enable export            |
| `enable_column_toggle`  | bool              | True              | Enable column visibility |
| `enable_column_reorder` | bool              | True              | Enable drag-drop reorder |
| `enable_bulk_actions`   | bool              | False             | Enable bulk actions      |
| `enable_detail_view`    | bool              | True              | Enable detail view       |
| `enable_inline_edit`    | bool              | False             | Enable inline editing    |

### FieldConfig Options

| Option         | Type     | Default  | Description          |
| -------------- | -------- | -------- | -------------------- |
| `name`         | str      | Required | Field name           |
| `verbose_name` | str      | None     | Display name         |
| `field_type`   | str      | "text"   | Field type           |
| `sortable`     | bool     | True     | Enable sorting       |
| `searchable`   | bool     | False    | Include in search    |
| `hidden`       | bool     | False    | Initially hidden     |
| `truncate`     | int      | None     | Truncate text length |
| `format`       | str      | None     | Date/number format   |
| `link_url`     | str      | None     | Make field a link    |
| `renderer`     | Callable | None     | Custom renderer      |
| `css_class`    | str      | None     | Additional CSS       |
| `export`       | bool     | True     | Include in export    |

### Field Types

- `text` - Text fields
- `number` - Numeric fields (int, decimal, float)
- `boolean` - Boolean fields (shows as Yes/No badges)
- `date` - Date fields
- `datetime` - DateTime fields
- `image` - Image fields (shows thumbnails)
- `foreign_key` - Foreign key relationships

## Requirements

- Django 4.0+
- Python 3.8+
- HTMX (included via CDN in templates)
- Tailwind CSS (included via CDN in templates)
- Font Awesome (for icons)
- openpyxl (optional, for XLSX export)

```bash
pip install django openpyxl
```

## License

This CRUD framework is part of the Naga SIS project.
