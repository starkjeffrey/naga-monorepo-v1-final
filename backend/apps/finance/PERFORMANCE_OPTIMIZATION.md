# Finance App Performance Optimization Guide

## Problem Statement
The finance app invoice admin becomes unresponsive with 500+ invoices and needs to handle 90,000+ records efficiently.

## Root Causes Identified

### 1. N+1 Query Problems
- `student_display()` method accesses `student.person.last_name` without proper select_related
- `amount_due_display()` calculates `amount_due` property on each row
- InvoiceLineItemInline causes additional queries for each invoice
- Search fields include deep relationships causing inefficient queries

### 2. Missing Database Indexes
- No composite indexes for common filter combinations
- Missing indexes on foreign key lookups used in admin
- No conditional indexes for status-based queries

### 3. Inefficient Admin Configuration
- Heavy calculations in list_display methods
- No query optimization for different views (list vs detail)
- Inline display in list view causing unnecessary queries

## Solutions Implemented

### 1. Optimized Admin Class (`admin_optimized.py`)

#### Key Optimizations:
- **Pre-calculated fields**: Use `annotate()` to calculate amount_due in database
- **Selective prefetching**: Only prefetch related data when needed
- **Optimized display methods**: Use pre-fetched data only
- **Conditional inlines**: Remove inlines from list view, add only in detail view
- **Limited search fields**: Focus on indexed fields for search
- **Pagination limits**: Reasonable defaults (50 per page)

#### Code Structure:
```python
# Annotate calculated fields in queryset
qs = qs.annotate(
    calculated_amount_due=F("total_amount") - F("paid_amount")
)

# Essential select_related only
qs = qs.select_related("student__person", "term")

# Conditional prefetching based on view
if request.resolver_match.url_name == "finance_invoice_change":
    # Prefetch only for detail view
```

### 2. Database Indexes (`migrations/0003_optimize_invoice_indexes.py`)

#### Indexes Added:
1. **Composite index for list queries**: `['status', 'issue_date', '-id']`
2. **Student lookup index**: `['student', 'term', '-issue_date']`
3. **Conditional overdue index**: `['status', 'due_date']` where status IN ('OVERDUE', 'SENT')
4. **Amount calculations index**: `['total_amount', 'paid_amount']`
5. **Line item indexes**: For invoice and enrollment lookups

### 3. Additional Optimizations

#### Search Optimization:
```python
def get_search_results(self, request, queryset, search_term):
    if search_term.isdigit():
        # Direct student ID search for numeric input
        queryset = queryset.filter(student__student_id=search_term)
        return queryset, False
    return super().get_search_results(request, queryset, search_term)
```

#### Dynamic List Display:
- Simplified columns when filtering/searching
- Remove expensive calculations from filtered views

## Implementation Steps

### 1. Update Django Admin
```python
# In apps/finance/admin.py, replace InvoiceAdmin with:
from apps.finance.admin_optimized import OptimizedInvoiceAdmin
```

### 2. Run Database Migration
```bash
docker compose -f docker-compose.local.yml run --rm django python manage.py migrate finance
```

### 3. Analyze Query Performance
```python
# Add to settings for development
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

### 4. Monitor with Django Debug Toolbar
```python
# Ensure these are optimized in settings:
DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': lambda request: DEBUG,
    'RESULTS_CACHE_SIZE': 100,
    'SHOW_COLLAPSED': True,
}
```

## Performance Metrics

### Before Optimization:
- Page load time: 30+ seconds (500 records)
- Database queries: 500+ (N+1 problem)
- Memory usage: High due to property calculations

### After Optimization (Expected):
- Page load time: <2 seconds (90,000 records)
- Database queries: 3-5 for list view
- Memory usage: Minimal, calculations in database

## Additional Recommendations

### 1. Implement Database Connection Pooling
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,  # Connection pooling
        # ... other settings
    }
}
```

### 2. Add Redis Caching for Frequent Queries
```python
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}
```

### 3. Implement Admin List View Caching
```python
from django.views.decorators.cache import cache_page

@cache_page(60 * 5)  # Cache for 5 minutes
def changelist_view(self, request, extra_context=None):
    return super().changelist_view(request, extra_context)
```

### 4. Consider Materialized Views for Reports
For complex financial reports, create PostgreSQL materialized views:
```sql
CREATE MATERIALIZED VIEW finance_invoice_summary AS
SELECT 
    i.id,
    i.invoice_number,
    i.student_id,
    i.term_id,
    i.total_amount,
    i.paid_amount,
    (i.total_amount - i.paid_amount) as amount_due,
    COUNT(ili.id) as line_item_count
FROM finance_invoice i
LEFT JOIN finance_invoice_line_item ili ON ili.invoice_id = i.id
GROUP BY i.id;

CREATE INDEX ON finance_invoice_summary (student_id, term_id);
CREATE INDEX ON finance_invoice_summary (amount_due) WHERE amount_due > 0;
```

### 5. Implement Asynchronous Tasks
For bulk operations, use Dramatiq:
```python
@dramatiq.actor
def bulk_update_invoice_status():
    """Update overdue invoices asynchronously."""
    from datetime import date
    Invoice.objects.filter(
        status='SENT',
        due_date__lt=date.today()
    ).update(status='OVERDUE')
```

## Testing Performance

### 1. Generate Test Data
```python
# management/commands/generate_test_invoices.py
from django.core.management.base import BaseCommand
from apps.finance.models import Invoice
from apps.people.models import StudentProfile
from apps.curriculum.models import Term
import random

class Command(BaseCommand):
    def handle(self, *args, **options):
        students = list(StudentProfile.objects.all()[:1000])
        terms = list(Term.objects.all())
        
        invoices = []
        for i in range(90000):
            invoice = Invoice(
                invoice_number=f'INV-{i:06d}',
                student=random.choice(students),
                term=random.choice(terms),
                total_amount=random.uniform(100, 5000),
                paid_amount=random.uniform(0, 5000),
                # ... other fields
            )
            invoices.append(invoice)
            
            if len(invoices) >= 1000:
                Invoice.objects.bulk_create(invoices)
                invoices = []
                self.stdout.write(f'Created {i} invoices...')
```

### 2. Benchmark Queries
```python
from django.test.utils import override_settings
from django.test import TestCase
from django.test.client import Client
import time

class InvoiceAdminPerformanceTest(TestCase):
    def test_invoice_list_performance(self):
        client = Client()
        client.login(username='admin', password='password')
        
        start = time.time()
        response = client.get('/admin/finance/invoice/')
        end = time.time()
        
        self.assertLess(end - start, 2.0, "Invoice list should load in under 2 seconds")
        self.assertLess(len(connection.queries), 10, "Should use less than 10 queries")
```

## Maintenance Guidelines

1. **Monitor Query Performance**: Use Django Debug Toolbar in development
2. **Regular VACUUM**: Schedule PostgreSQL VACUUM ANALYZE for tables
3. **Index Maintenance**: Monitor index usage and bloat
4. **Partition Large Tables**: Consider partitioning invoices by year
5. **Archive Old Data**: Move invoices older than 5 years to archive tables