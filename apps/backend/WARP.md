# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the backend Django application in this monorepo.

## 🚨 CRITICAL: DOCKER-FIRST PROJECT 🚨

**This is a Docker-based project. PostgreSQL database ONLY runs in Docker containers.**

- ❌ **UV/pip commands that need database will FAIL** (no native PostgreSQL installed)
- ❌ **Any Django management command requiring database WILL FAIL**
- ✅ **Use Docker commands for ALL development operations**
- ✅ **UV commands only work for: linting, formatting, type checking, unit tests (SQLite)**

## 🚀 MCP SERVERS - USE THESE FIRST! 🚀

**Always prefer MCP servers over writing scripts. They save time and reduce errors.**

### Available MCP Servers

1. **PostgreSQL MCP** (`postgresql://debug:debug@localhost:5432/naga_local`)
   - ✅ **USE FOR:** Database queries, table inspection, data analysis
   - ✅ **INSTEAD OF:** Writing Python scripts with Django ORM or Docker compose exec commands

2. **Context7 MCP** - Django documentation, API patterns, best practices
3. **GitHub MCP** - Repository operations, PR management, issue tracking  
4. **Playwright MCP** - Screenshots, browser automation, UI testing
5. **Filesystem MCP** - File operations, directory browsing

## Backend Development Commands

### Docker Commands (REQUIRED for Database Operations)

| Task | Docker Command (REQUIRED) | UV Command |
|------|---------------------------|------------|
| Dev Server | `docker compose -f docker-compose.eval.yml up` | ❌ **FAILS** |
| Migrations | `docker compose -f docker-compose.eval.yml run --rm django python manage.py migrate` | ❌ **FAILS** |
| Shell | `docker compose -f docker-compose.eval.yml run --rm django python manage.py shell` | ❌ **FAILS** |
| Tests | `docker compose -f docker-compose.eval.yml run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test django pytest` | ✅ `uv run pytest` (SQLite only) |
| Lint/Format | `docker compose -f docker-compose.eval.yml run --rm django ruff check` | ✅ `uv run ruff check` |

### Make Commands (Available via Makefile)

**Quick Development Commands:**
```bash
# Setup and install dependencies
make setup

# Code quality checks
make quality                    # Run lint + typecheck
make fmt                       # Format code with ruff
make lint                      # Lint with ruff 
make typecheck                 # Type check with mypy

# Testing shortcuts
make test-fast                 # Fast unit tests (no slow tests)
make test-unit                 # All unit tests
make test-int                  # Integration tests
make test-critical             # Critical business logic tests
make coverage                  # Generate HTML coverage report

# Development workflow
make pre-commit                # Run before commits (format + lint + fast tests)
make pre-push                  # Run before push (quality + coverage check)
```

### Common Django Operations

```bash
# Database operations (Docker REQUIRED)
docker compose -f docker-compose.eval.yml run --rm django python manage.py makemigrations
docker compose -f docker-compose.eval.yml run --rm django python manage.py migrate
docker compose -f docker-compose.eval.yml run --rm django python manage.py shell

# Testing with PostgreSQL
docker compose -f docker-compose.eval.yml run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test django pytest apps/finance/tests/ -v

# Code quality (UV works)
uv run ruff check
uv run ruff format
uv run mypy apps/
```

## Backend Architecture

### Clean Architecture (13 Django Apps)

```text
Foundation Layer:    accounts/, common/
Core Domain:         people/, curriculum/, scheduling/, enrollment/  
Business Logic:      academic/, grading/, attendance/, finance/, scholarships/
Services:            academic_records/, level_testing/, language/
```

### App Responsibilities

**Foundation Layer:**
- `accounts/` - Authentication and user management
- `common/` - Shared utilities, base models, constants

**Core Domain:**
- `people/` - Person profiles, contacts, staff/student data
- `curriculum/` - Courses, programs, academic structure
- `scheduling/` - Class schedules, rooms, time slots
- `enrollment/` - Student registration and course enrollment

**Business Logic:**
- `academic/` - Academic records, transcripts, degrees
- `grading/` - Grade management and calculations
- `attendance/` - Attendance tracking and reporting
- `finance/` - Billing, payments, financial records
- `scholarships/` - Financial aid and scholarship management

**Services:**
- `academic_records/` - Transcript and record services
- `level_testing/` - Placement testing and assessments
- `language/` - Language-specific functionality

### API Structure

- **Endpoints:** `backend/api/` (django-ninja)
- **Schema Generation:** Automatic OpenAPI schema
- **Type Sharing:** Types exported to `libs/shared/api-types/`

### Django-Ninja API Patterns

**Router Organization:**
```python
# api/v1/finance.py
from ninja import Router
from api.v1.auth import jwt_auth

router = Router(auth=jwt_auth, tags=["finance"])

@router.post("/invoices", response=InvoiceSchema)
def create_invoice(request, data: CreateInvoiceSchema):
    """Create a new invoice."""
    # Implementation
```

**Authentication:**
- JWT authentication via `api.v1.auth.jwt_auth`
- Session authentication for web interface
- Role-based permissions via decorators

**Schema Patterns:**
- Input schemas: `*Schema` (e.g., `CreateInvoiceSchema`)
- Output schemas: `*ResponseSchema` (e.g., `InvoiceResponseSchema`)
- Shared schemas in `api/v1/schemas.py`

## Critical Rules (ZERO TOLERANCE)

### Architecture Alerts

**🚨 IMMEDIATELY STOP if detecting:**

- Circular dependencies between Django apps
- Mixed app responsibilities (single app handling multiple domains)
- Bidirectional dependencies (A imports B, B imports A)

### Docker Command Requirements

**🚨 DOCKER COMMANDS ONLY - NO EXCEPTIONS:**

- **❌ NEVER use `uv run python manage.py` commands that access PostgreSQL database**
- **❌ NEVER use `USE_DOCKER=no` for migrations, shell, or database operations**
- **✅ ALWAYS use `docker compose -f docker-compose.eval.yml run --rm django` for ALL database operations**
- **✅ UV commands ONLY for: linting (`uv run ruff`), formatting, type checking, SQLite-only tests**

### Database Restrictions  

- **❌ NEVER make direct database schema changes** outside Django migrations
- **✅ ALL schema changes MUST go through Django migrations**
- **✅ ALL migration scripts MUST inherit from `BaseMigrationCommand`**

### Environment Protocol

- **EVALUATION environment:** Main environment for development and occasional feedback from school staff

## Code Quality Standards

### Python Requirements

- Python 3.13.7+ with comprehensive type hints
- **CRITICAL:** Never use f-strings in logging - use lazy formatting
- Ruff formatting (119 char line length)
- Google-style docstrings

### Django Patterns

- Use Class-based views for complex logic
- Django forms for ALL user inputs
- Django ORM with proper indexing
- Model validators and constraints
- Proper signal usage for decoupled communication

### Critical Coding Rules

#### ❌ NEVER Use F-strings in Logging

```python
# BAD - Violates PEP 8, causes performance issues
logger.info(f"User {user.name} logged in with ID {user.id}")

# GOOD - Use lazy formatting
logger.info("User %s logged in with ID %s", user.name, user.id)
```

#### ✅ ALWAYS Use Type Hints

```python
from typing import Optional, List
from django.db import models

def process_enrollment(
    student: Student,
    courses: List[Course],
    term: Optional[Term] = None
) -> Enrollment:
    """Process student enrollment for given courses."""
    ...
```

#### ✅ ALWAYS Use BaseMigrationCommand

```python
# ✅ CORRECT - Provides automatic audit reporting
from apps.common.management.base_migration import BaseMigrationCommand

class Command(BaseMigrationCommand):
    def get_rejection_categories(self):
        return [
            "missing_required_field",
            "duplicate_record",
            "validation_error",
            "foreign_key_not_found"
        ]
    
    def execute_migration(self, *args, **options):
        # Record input statistics
        self.record_input_stats(
            total_records=count,
            source_file=filepath
        )
        
        # Process with error tracking
        for record in records:
            try:
                # Process record
                self.record_success("student_created", 1)
            except ValidationError as e:
                self.record_rejection(
                    category="validation_error",
                    record_id=record['id'],
                    reason=str(e)
                )
```

**Audit reports are automatically generated in:** `project-docs/migration-reports/`

### Management Command Organization

- **Production commands:** `apps/*/management/commands/production/` - Stable, well-tested commands
- **Transitional commands:** `apps/*/management/commands/transitional/` - Migration and setup commands
- **Ephemeral commands:** `apps/*/management/commands/ephemeral/` - Experimental commands (relaxed quality standards)

### Django App Structure Patterns

Each Django app follows this standardized structure:
```text
apps/app_name/
├── __init__.py
├── admin.py                    # Django admin configuration
├── apps.py                     # App configuration
├── models.py                   # Core models
├── services.py                 # Business logic layer
├── constants.py                # App-specific constants
├── factories.py               # Test factories (if present)
├── fixtures/                  # JSON fixtures for data
├── management/commands/       # Django management commands
├── migrations/                # Database migrations
├── services/                  # Complex service modules (if needed)
├── tests/                     # Test suite
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── conftest.py           # Pytest fixtures
├── templates/app_name/        # Django templates
├── static/app_name/           # Static files
└── views.py                   # Django views
```

## Testing

### Test Strategy

- **Unit Tests:** SQLite for speed (`uv run pytest`)
- **Integration Tests:** PostgreSQL via Docker for realistic testing
- **Test-Driven Development:** Write tests before implementation

### Running Tests

```bash
# Unit tests (fast, SQLite)
uv run pytest

# Integration tests (realistic, PostgreSQL)
docker compose -f docker-compose.eval.yml run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test django pytest

# Specific app
docker compose -f docker-compose.eval.yml run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test django pytest apps/finance/tests/ -v

# Single test
docker compose -f docker-compose.eval.yml run --rm -e DJANGO_SETTINGS_MODULE=config.settings.test django pytest apps/finance/tests/test_models.py::TestFinanceModels::test_specific -v

# Run tests matching pattern
uv run pytest -k "payment" -v

# With coverage report
uv run pytest --cov=apps --cov-report=term-missing
```

### Test Configuration

- **SQLite in-memory** for fast unit tests (~10 seconds)
- **PostgreSQL** for integration tests (~30+ seconds)
- **Coverage requirement:** 85% minimum (CI fails if lower)
- **Test markers:** unit, integration, contract, e2e, slow, finance, academic, security, performance, smoke, wip, financial_compliance, transaction_safety
- **Automatic fixtures:** db, user, admin_user, authenticated_client
- **Test timeout:** 30 seconds per test
- **Parallel execution:** Available via pytest-xdist (`-n auto`)

## Key Backend File Locations

- **Django Apps:** `backend/apps/`
- **API Endpoints:** `backend/api/` (django-ninja)
- **Settings:** `backend/config/`
- **Scripts:** `backend/scripts/`
- **Project Documentation:** `backend/project-docs/`
- **Migration Data:** `backend/data/` (excluded from git)
- **Fixtures:** `backend/fixtures/` and `backend/apps/*/fixtures/`
- **Templates:** `backend/templates/` and `backend/apps/*/templates/`
- **Static Files:** `backend/static/` and `backend/apps/*/static/`
- **Docker Compose Files:** `docker-compose.*.yml` (eval, shared, production, test variants)
- **Development Config:** `Makefile`, `pyproject.toml`, `pytest.ini`

## Database Access Patterns

### Preferred: MCP PostgreSQL Server

```python
# Use PostgreSQL MCP for queries instead of writing scripts
# Example: Table inspection, data analysis, reporting queries
```

### Django ORM Best Practices

```python
# Efficient queries
students = Student.objects.select_related('person').prefetch_related('enrollments__course')

# Avoid N+1 queries
for student in students:
    print(student.person.name)  # Already loaded
    print(student.enrollments.all())  # Already prefetched
```

### Migration Commands

```bash
# Create migrations
docker compose -f docker-compose.eval.yml run --rm django python manage.py makemigrations

# Apply migrations  
docker compose -f docker-compose.eval.yml run --rm django python manage.py migrate

# Check migration status
docker compose -f docker-compose.eval.yml run --rm django python manage.py showmigrations
```

## Dependency Management

### App Dependencies (Clean Architecture)

```python
# ✅ ALLOWED: Lower layer imports
from apps.common.models import TimestampedModel
from apps.people.models import Person

# ❌ FORBIDDEN: Circular imports
# If apps/academic imports apps/enrollment AND
# apps/enrollment imports apps/academic = CIRCULAR
```

### Import Patterns

```python
# ✅ GOOD: Explicit, clear dependencies
from apps.people.models import Student
from apps.curriculum.models import Course

# ❌ AVOID: Generic imports that hide dependencies
from apps.people import *
```

## Error Handling

### Django Error Patterns

```python
from django.core.exceptions import ValidationError
from django.db import IntegrityError
import logging

logger = logging.getLogger(__name__)

def safe_create_student(data):
    try:
        student = Student.objects.create(**data)
        logger.info("Student created successfully: %s", student.id)
        return student
    except ValidationError as e:
        logger.error("Validation error creating student: %s", e)
        raise
    except IntegrityError as e:
        logger.error("Database integrity error: %s", e)
        raise
```

## Git Workflow

### Commit Message Format

Use this exact format:
```
<emoji> <TYPE in ALL CAPS>: <short summary>
```

**Emoji Map:**
```
✨ FEAT     → new feature
🐛 FIX      → bug fix  
🔒 SECURITY → security fix/hardening
📝 DOCS     → documentation only
♻️ REFACTOR → code refactor (no behavior change)
🚀 PERF     → performance improvement
✅ TEST     → tests
📦 BUILD    → build/dependencies
⚙️ CI       → CI/config
🔧 CHORE    → chores (no src/test changes)
```

**Examples:**
```
🔒 SECURITY: Harden URL configuration against regressions
🐛 FIX: Prevent crash on empty payload in payments worker
✨ FEAT: Add CSV export for enrollment report
```

### Dual Repository Push

Always push to both repositories:
```bash
git push origin main && git push gitlab main
```

## Type Checking

### MyPy Configuration

**Run type checking:**
```bash
# Type check all apps
uv run mypy apps/

# Type check specific app
uv run mypy apps/finance/

# Ignore import errors (useful for initial setup)
uv run mypy apps/ --ignore-missing-imports
```

**Strategic Type Checking:**
- ✅ Strict for: services, utils, policies
- ⚠️ Relaxed for: models, views, forms (Django magic)
- ❌ Ignored for: migrations, tests, ephemeral commands

## Troubleshooting

### Common Issues

**1. Database Connection Errors**
```bash
# Ensure Docker services are running
docker compose -f docker-compose.eval.yml ps

# Restart database
docker compose -f docker-compose.eval.yml restart postgres
```

**2. Migration Conflicts**
```bash
# Show migration status
docker compose -f docker-compose.eval.yml run --rm django python manage.py showmigrations

# Fake reverse specific migration
docker compose -f docker-compose.eval.yml run --rm django python manage.py migrate app_name migration_name --fake
```

**3. Test Database Issues**
```bash
# Force recreate test database
docker compose -f docker-compose.eval.yml run --rm django python manage.py test --keepdb=0

# Use SQLite for faster tests
DJANGO_SETTINGS_MODULE=config.settings.test uv run pytest
```

**4. Redis/Cache Issues**
```bash
# Clear Redis cache
docker compose -f docker-compose.eval.yml run --rm django python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Restart Redis
docker compose -f docker-compose.eval.yml restart redis
```

**5. Permission Errors in Development**
```bash
# Fix file permissions after Docker operations
sudo chown -R $(whoami):$(whoami) .

# Check Docker service status
docker compose -f docker-compose.eval.yml ps

# View logs for specific service
docker compose -f docker-compose.eval.yml logs django -f
```

## Performance and Optimization

### Database Query Optimization

**Always use select_related and prefetch_related:**
```python
# Efficient queries - avoid N+1 problems
students = Student.objects.select_related('person').prefetch_related(
    'enrollments__course',
    'enrollments__class_header__term'
)

# Use only() for large models when you need few fields
students = Student.objects.only('id', 'student_id', 'person__name')
```

**Use database functions and aggregations:**
```python
from django.db.models import Count, Sum, Q

# Complex aggregations at database level
course_stats = Course.objects.annotate(
    enrollment_count=Count('class_headers__enrollments'),
    total_credits=Sum('credit_hours')
)
```

### Development Environment Performance

**Fast test feedback loop:**
```bash
# Use SQLite for rapid unit tests
make test-fast

# Use focused test runs during development
uv run pytest -k "test_specific_feature" --tb=short

# Use make commands for common operations
make lint          # Much faster than docker version for quick checks
make fmt           # Fast code formatting
```

## Deployment and DevOps

### Docker Compose Environments

- **`docker-compose.eval.yml`** - Main development/evaluation environment
- **`docker-compose.shared.yml`** - Shared services (Traefik, networks)
- **`docker-compose.production.yml`** - Production configuration
- **`docker-compose.test.yml`** - Testing environment with PostgreSQL

### Deployment Scripts

```bash
# Deploy complete infrastructure
./scripts/deploy-all.sh

# Deploy evaluation environment only
./scripts/deploy-eval.sh
```

---

**Important:** This document focuses on backend-specific rules. For monorepo-wide commands and frontend guidelines, see the root-level documentation.