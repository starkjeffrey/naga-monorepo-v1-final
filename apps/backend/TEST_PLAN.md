# Naga SIS Comprehensive Test Plan

## Executive Summary

This document outlines the comprehensive pytest-based testing strategy for the Naga Student Information System (SIS) Django monorepo. The strategy emphasizes heavy unit testing (70%), targeted integration testing (20%), and focused contract/API testing (10%) to achieve ≥85% overall coverage and ≥95% coverage for critical financial and academic modules.

## System Architecture Overview

### Django Applications (23 total)

#### Foundation Layer
- `accounts` - Authentication, authorization, role management
- `common` - Shared utilities, base models, audit logging

#### Core Domain
- `people` - Person profiles, contacts, staff/student data
- `curriculum` - Courses, programs, academic structure
- `scheduling` - Class schedules, rooms, time slots
- `enrollment` - Student registration, course enrollment

#### Business Logic
- `academic` - Academic records, transcripts, degrees
- `grading` - Grade management, GPA calculations
- `attendance` - Attendance tracking, session management
- `finance` - Billing, payments, GL integration, reconciliation
- `scholarships` - Financial aid, discount management

#### Service Layer
- `academic_records` - Transcript services, record management
- `level_testing` - Placement testing, assessments
- `language` - Language-specific functionality

#### Interface Layer
- `web_interface` - Web UI views and templates
- `mobile` - Mobile-specific endpoints
- `moodle` - LMS integration

#### Support
- `analytics` - Reporting and analytics
- `settings` - System configuration
- `users` - User management
- `workflow` - Business process automation

### External Boundaries

| Boundary | Technology | Mock Strategy |
|----------|------------|---------------|
| Database | PostgreSQL | pytest-django fixtures, factory_boy |
| Cache | Redis | fakeredis, redis-py-mock |
| Queue | Dramatiq + Redis | dramatiq test runner |
| WebSocket | Channels + Redis | channels.testing |
| HTTP | httpx | respx |
| Email | Django mail | django.core.mail.outbox |
| Storage | Local/S3 | django.core.files.uploadedfile |

### Django-Ninja API

- **Main API**: `/api/v1/`
- **OpenAPI**: `/api/v1/openapi.json`
- **Authentication**: JWT with role-based permissions
- **Routers**: attendance, auth, finance, grading, permissions

## Testing Strategy

### Test Ratios

```
┌─────────────────────────────────────────┐
│         Test Pyramid Distribution        │
├─────────────────────────────────────────┤
│                                         │
│            E2E/Contract                 │
│               (10%)                     │
│          ╱─────────╲                   │
│         ╱           ╲                  │
│        ╱ Integration ╲                 │
│       ╱     (20%)     ╲                │
│      ╱─────────────────╲               │
│     ╱                   ╲              │
│    ╱     Unit Tests      ╲             │
│   ╱        (70%)          ╲            │
│  ╱───────────────────────────╲         │
└─────────────────────────────────────────┘
```

### Coverage Goals

| Module Category | Target Coverage | Justification |
|----------------|-----------------|---------------|
| Global | ≥85% | Industry standard for Django projects |
| Finance modules | ≥95% | Critical: handles money, invoicing, payments |
| Academic modules | ≥95% | Critical: transcripts, GPA, enrollment |
| Authentication | ≥95% | Critical: security boundary |
| API endpoints | ≥90% | External contract compliance |
| Services layer | ≥90% | Business logic concentration |
| Models | ≥85% | Core data integrity |
| Utilities | ≥80% | Support functions |
| Admin interfaces | ≥60% | Generated code, UI testing preferred |
| Migrations | Excluded | Auto-generated, tested via integration |

### Test Layout

```
backend/
├── tests/                          # New test root
│   ├── __init__.py
│   ├── conftest.py                # Root fixtures and configuration
│   ├── factories/                 # Centralized test factories
│   │   ├── __init__.py
│   │   ├── people.py
│   │   ├── finance.py
│   │   ├── enrollment.py
│   │   └── curriculum.py
│   ├── fixtures/                  # Shared test data
│   │   ├── users.json
│   │   ├── courses.json
│   │   └── terms.json
│   ├── unit/                      # Unit tests
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_models/
│   │   ├── test_services/
│   │   ├── test_utils/
│   │   └── test_validators/
│   ├── integration/               # Integration tests
│   │   ├── __init__.py
│   │   ├── conftest.py
│   │   ├── test_workflows/
│   │   ├── test_signals/
│   │   └── test_transactions/
│   └── contract/                  # API contract tests
│       ├── __init__.py
│       ├── conftest.py
│       ├── test_openapi.py
│       └── test_endpoints/
│
├── apps/                          # Per-app test structure
│   ├── finance/
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── conftest.py
│   │       ├── unit/
│   │       │   ├── test_models.py
│   │       │   ├── test_services.py
│   │       │   └── test_validators.py
│   │       └── integration/
│   │           ├── test_payment_flow.py
│   │           └── test_reconciliation.py
│   └── [other apps follow same pattern]
│
└── tests_legacy/                  # Archived old tests
```

## Testing Conventions

### AAA Pattern (Arrange-Act-Assert)

```python
def test_invoice_creation():
    # Arrange
    student = StudentFactory()
    course = CourseFactory(price=Decimal("1000.00"))
    
    # Act
    invoice = InvoiceService.create_invoice(student, course)
    
    # Assert
    assert invoice.total_amount == Decimal("1000.00")
    assert invoice.status == Invoice.Status.PENDING
```

### Parametrization

```python
@pytest.mark.parametrize("amount,expected_tax", [
    (Decimal("100.00"), Decimal("10.00")),
    (Decimal("200.00"), Decimal("20.00")),
    (Decimal("0.00"), Decimal("0.00")),
])
def test_tax_calculation(amount, expected_tax):
    assert calculate_tax(amount) == expected_tax
```

### Fixtures

```python
@pytest.fixture
def authenticated_client(db, django_user_model):
    """Provides authenticated test client."""
    user = django_user_model.objects.create_user(
        username="testuser",
        password="testpass123"
    )
    client = Client()
    client.force_login(user)
    return client

@pytest.fixture
def finance_admin(db):
    """Creates finance admin user with permissions."""
    return UserFactory(role="finance_admin")
```

### Factory Pattern (factory_boy)

```python
class StudentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StudentProfile
    
    student_id = factory.Sequence(lambda n: f"STU{n:06d}")
    person = factory.SubFactory(PersonFactory)
    enrollment_date = factory.Faker("date_this_year")
    
    @factory.post_generation
    def courses(self, create, extracted, **kwargs):
        if not create or not extracted:
            return
        for course in extracted:
            EnrollmentFactory(student=self, course=course)
```

### Property-Based Testing (Hypothesis)

```python
from hypothesis import given, strategies as st

@given(
    amount=st.decimals(min_value=0, max_value=100000, places=2),
    discount_percent=st.integers(min_value=0, max_value=100)
)
def test_discount_calculation_properties(amount, discount_percent):
    result = apply_discount(amount, discount_percent)
    assert result >= 0
    assert result <= amount
    if discount_percent == 0:
        assert result == amount
    if discount_percent == 100:
        assert result == 0
```

## Data Management

### Test Data Strategy

1. **Factory-Based Generation**
   - Use factory_boy for model instances
   - Maintain factories in centralized location
   - Inherit from base factories for variations

2. **Faker Integration**
   ```python
   faker.seed(12345)  # Deterministic data
   ```

3. **Fixture Data**
   - Minimal JSON fixtures for reference data
   - Load via Django fixtures or custom loaders

4. **Database State**
   ```python
   @pytest.mark.django_db(transaction=True)
   def test_concurrent_enrollment():
       # Test with real transactions
   ```

## Isolation Rules

### Unit Tests
- **Mock ALL external boundaries**
- Use `unittest.mock` or `pytest-mock`
- No database access (use factories)
- No network calls (use respx)
- No file I/O (use StringIO/BytesIO)
- Execution time < 100ms per test

### Integration Tests
- **Use ephemeral test database**
- Redis via fakeredis or test container
- Real Django ORM operations
- Test signal handling
- Test transaction behavior
- Execution time < 1s per test

### Contract/API Tests
- **Validate against OpenAPI schema**
- Use Django test client or httpx
- Test authentication flows
- Validate response shapes
- Test error responses
- Test pagination and filtering

## Dependencies

### Core Testing Stack

```toml
[project.optional-dependencies]
test = [
    # Test Framework
    "pytest>=8.3.4",
    "pytest-django>=4.10.0",
    "pytest-cov>=7.0.0",
    "pytest-xdist>=3.6.0",          # Parallel execution
    "pytest-timeout>=2.3.0",         # Test timeouts
    "pytest-mock>=3.14.0",           # Mock helpers
    "pytest-benchmark>=5.0.0",       # Performance testing
    
    # Test Data
    "factory-boy>=3.3.3",
    "faker>=33.0.0",
    "pytest-factoryboy>=2.7.0",
    
    # Property Testing
    "hypothesis>=6.100.0",
    "hypothesis-django>=0.3.0",
    
    # Mocking
    "respx>=0.21.0",                # httpx mocking
    "fakeredis>=2.25.0",            # Redis mocking
    "freezegun>=1.5.1",             # Time mocking
    
    # Coverage
    "coverage[toml]>=7.5.3",
    "django-coverage-plugin>=3.1.0",
    
    # API Testing
    "httpx>=0.28.1",
    "jsonschema>=4.23.0",
]
```

## Runtime Configuration

### Parallelization

```bash
# Use all CPU cores
pytest -n auto

# Use specific number of workers
pytest -n 4

# Distribute by test file
pytest --dist loadfile
```

### Warning Policy

```toml
[tool.pytest.ini_options]
filterwarnings = [
    "error::DeprecationWarning",
    "error::PendingDeprecationWarning",
    "ignore::UserWarning:django.*",
    "ignore::DeprecationWarning:pkg_resources.*",
]
```

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
      
      redis:
        image: redis:8.2
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.13'
      
      - name: Install uv
        run: pip install uv
      
      - name: Install dependencies
        run: |
          uv pip install -e .[test]
      
      - name: Lint
        run: |
          uv run ruff check
          uv run ruff format --check
      
      - name: Type Check
        run: uv run mypy apps/ api/
      
      - name: Unit Tests
        run: |
          uv run pytest tests/unit -n auto \
            --cov=apps --cov=api \
            --cov-report=xml \
            --cov-report=term-missing
      
      - name: Integration Tests
        run: |
          uv run pytest tests/integration -n auto
      
      - name: Contract Tests
        run: |
          uv run pytest tests/contract
      
      - name: Coverage Gate
        run: |
          coverage report --fail-under=85
      
      - name: Upload Coverage
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
```

## Local Development

### Makefile Targets

```makefile
.PHONY: test test-unit test-int test-api test-watch coverage clean-test

# Run all tests
test:
	uv run pytest -q

# Unit tests only (fast)
test-unit:
	uv run pytest -q tests/unit -n auto

# Integration tests
test-int:
	uv run pytest -q tests/integration -n auto

# API contract tests
test-api:
	uv run pytest -q tests/contract

# Watch mode for TDD
test-watch:
	uv run pytest-watch -- -q tests/unit

# Coverage report
coverage:
	uv run pytest --cov=apps --cov=api \
		--cov-report=html \
		--cov-report=term-missing \
		--cov-report=xml
	@echo "Coverage report: htmlcov/index.html"

# Coverage with enforcement
coverage-check: coverage
	@coverage report --fail-under=85

# Clean test artifacts
clean-test:
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -f coverage.xml
	rm -f .coverage
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -delete

# Run specific app tests
test-app:
	@read -p "App name: " app; \
	uv run pytest apps/$$app/tests -v

# Run tests matching pattern
test-match:
	@read -p "Pattern: " pattern; \
	uv run pytest -k "$$pattern" -v

# Performance benchmarks
test-bench:
	uv run pytest tests/unit \
		--benchmark-only \
		--benchmark-autosave

# Security tests
test-security:
	uv run pytest -m security -v
```

## Exit Criteria for Legacy Test Replacement

The new test suite can replace the legacy suite when:

1. ✅ **Coverage Goals Met**
   - Global coverage ≥85%
   - Critical modules ≥95%
   - All endpoints have contract tests

2. ✅ **Performance Targets**
   - Unit test suite < 2 minutes
   - Integration suite < 3 minutes
   - Full suite < 5 minutes

3. ✅ **Quality Gates**
   - Zero test flakiness over 10 runs
   - All tests pass in CI/CD
   - No warnings in test output

4. ✅ **Documentation**
   - All test utilities documented
   - Factory patterns documented
   - Common test patterns documented

5. ✅ **Team Readiness**
   - Test writing guide available
   - Team trained on pytest
   - CI/CD fully integrated

## High-Risk Testing Focus Areas

### Financial Calculations
- Decimal precision for money
- Currency conversion
- Tax calculations
- Discount application order
- Invoice generation
- Payment processing
- GL posting accuracy
- Reconciliation matching

### Academic Integrity
- GPA calculations
- Credit hour totals
- Prerequisite validation
- Graduation requirements
- Transcript generation
- Grade change audit trail

### Concurrency & Transactions
- Enrollment capacity limits
- Payment race conditions
- Grade submission deadlines
- Schedule conflicts
- Database deadlocks

### Security & Permissions
- JWT token validation
- Role-based access control
- Data isolation between users
- API rate limiting
- SQL injection prevention
- XSS protection

### Timezone & Internationalization
- Date/time conversions
- Academic calendar calculations
- Multi-language support
- Currency localization

## Test Execution Commands

### Using uv (Recommended)

```bash
# Install test dependencies
uv pip install -e .[test]

# Run all tests
uv run pytest -q

# Unit tests only
uv run pytest -q tests/unit

# Integration tests with parallel execution
uv run pytest -q tests/integration -n auto

# Contract/API tests
uv run pytest -q tests/contract

# Coverage report
uv run pytest --cov=apps --cov=api --cov-report=term-missing

# Run specific test file
uv run pytest tests/unit/test_models/test_finance.py -v

# Run tests matching pattern
uv run pytest -k "payment" -v

# Run with specific marker
uv run pytest -m "not slow" -v

# Benchmark tests
uv run pytest --benchmark-only

# Debug failing test
uv run pytest --pdb -x
```

## Migration Plan

### Phase 1: Setup (Week 1)
1. Create new test directory structure
2. Move existing tests to `tests_legacy/`
3. Set up pytest configuration
4. Create base fixtures and factories
5. Establish CI/CD pipeline

### Phase 2: Critical Path (Week 2-3)
1. Finance module unit tests
2. Enrollment workflow tests
3. Authentication/authorization tests
4. Payment processing integration tests
5. API contract tests for all endpoints

### Phase 3: Expansion (Week 4-5)
1. Academic module tests
2. Grading system tests
3. Attendance tracking tests
4. Scheduling tests
5. People management tests

### Phase 4: Completion (Week 6)
1. Remaining module tests
2. Performance benchmarks
3. Security test suite
4. Documentation completion
5. Team training

### Phase 5: Validation (Week 7)
1. Coverage verification
2. Performance validation
3. Flakiness elimination
4. Legacy test removal
5. Production deployment

## Best Practices

### Do's
- ✅ Write tests before fixing bugs
- ✅ Use descriptive test names
- ✅ Keep tests independent
- ✅ Mock at boundaries only
- ✅ Use factories over fixtures
- ✅ Test behavior, not implementation
- ✅ Parametrize similar tests
- ✅ Keep tests fast (<100ms for unit)
- ✅ Use deterministic data
- ✅ Test edge cases and errors

### Don'ts
- ❌ Share state between tests
- ❌ Use production data
- ❌ Test Django/library code
- ❌ Use time.sleep()
- ❌ Ignore test warnings
- ❌ Comment out failing tests
- ❌ Test private methods directly
- ❌ Mix test types in same file
- ❌ Use hard-coded test data
- ❌ Skip error path testing

## Adoption Checklist

- [ ] Archive existing tests to `tests_legacy/`
- [ ] Create new test directory structure
- [ ] Install test dependencies via `uv pip install -e .[test]`
- [ ] Configure pytest.ini and coverage settings
- [ ] Create root conftest.py with shared fixtures
- [ ] Implement base test factories
- [ ] Write unit tests for critical finance modules
- [ ] Write integration tests for payment workflow
- [ ] Create API contract tests
- [ ] Set up CI/CD pipeline with coverage gates
- [ ] Run full test suite and verify ≥85% coverage
- [ ] Document test patterns and utilities
- [ ] Train team on pytest and TDD practices
- [ ] Monitor test execution times and optimize
- [ ] Remove legacy tests after validation period

## Metrics & Monitoring

### Key Metrics
- **Coverage**: Track via codecov.io
- **Execution Time**: Monitor in CI/CD
- **Flakiness**: Track intermittent failures
- **Test Count**: Unit vs Integration vs Contract
- **Failure Rate**: By module and test type

### Quality Dashboard
```
┌─────────────────────────────────────────┐
│        Test Quality Dashboard           │
├─────────────────────────────────────────┤
│ Coverage:        88.3% ▲ (+2.1%)       │
│ Tests:           1,847 total            │
│   - Unit:        1,293 (70%)           │
│   - Integration:   369 (20%)           │
│   - Contract:      185 (10%)           │
│ Execution:       4m 32s ▼ (-18s)       │
│ Flakiness:       0.0% ✓                │
│ Last Run:        2025-08-23 19:45 UTC  │
└─────────────────────────────────────────┘
```

## Support & Resources

### Documentation
- Pytest: https://docs.pytest.org/
- pytest-django: https://pytest-django.readthedocs.io/
- factory_boy: https://factoryboy.readthedocs.io/
- Hypothesis: https://hypothesis.readthedocs.io/

### Internal Resources
- Test writing guide: `/docs/testing/writing-tests.md`
- Factory reference: `/docs/testing/factories.md`
- Common patterns: `/docs/testing/patterns.md`
- Troubleshooting: `/docs/testing/troubleshooting.md`

### Contact
- Test Architecture: QA Lead
- CI/CD Support: DevOps Team
- Training: Engineering Education

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-08-23  
**Author**: Senior Test Architect  
**Review**: Pending