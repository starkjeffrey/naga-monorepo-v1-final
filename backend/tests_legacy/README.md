# Naga SIS Backend Test Suite

## Overview

This test suite provides comprehensive coverage for the Naga Student Information System backend using pytest. The tests are organized by type and follow best practices for Django testing with Python 3.13.

## Test Organization

```
tests/
├── unit/           # Isolated unit tests for models, forms, validators
├── integration/    # Tests for multi-component interactions
├── api/           # API endpoint tests
├── e2e/           # End-to-end user journey tests
└── fixtures/      # Shared test fixtures and factories
```

## Running Tests

### Run All Tests
```bash
# Using pytest directly (SQLite)
uv run pytest

# Using Docker (PostgreSQL)
docker compose -f docker-compose.local.yml run --rm django pytest
```

### Run Specific Test Categories
```bash
# Unit tests only
uv run pytest tests/unit/ -m unit

# Integration tests
uv run pytest tests/integration/ -m integration

# API tests
uv run pytest tests/api/ -m api

# End-to-end tests
uv run pytest tests/e2e/ -m e2e

# Quick smoke tests
uv run pytest -m smoke
```

### Run Tests for Specific Apps
```bash
# Test specific app
uv run pytest tests/unit/test_enrollment_models.py

# Test with pattern matching
uv run pytest -k "test_student"

# Test specific class
uv run pytest tests/unit/test_people_models.py::TestPersonModel

# Test specific method
uv run pytest tests/unit/test_people_models.py::TestPersonModel::test_person_creation
```

### Run Tests with Coverage
```bash
# Generate coverage report
uv run pytest --cov=apps --cov-report=html

# View coverage report
open htmlcov/index.html

# Coverage with missing lines
uv run pytest --cov=apps --cov-report=term-missing
```

### Run Tests in Parallel
```bash
# Install pytest-xdist first
uv pip install pytest-xdist

# Run tests in parallel
uv run pytest -n auto

# Run with specific number of workers
uv run pytest -n 4
```

## Test Markers

Tests are marked for easy filtering:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.api` - API tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Tests that take >1 second
- `@pytest.mark.security` - Security-related tests
- `@pytest.mark.performance` - Performance tests
- `@pytest.mark.smoke` - Quick smoke tests
- `@pytest.mark.wip` - Work in progress

### Running Tests by Marker
```bash
# Run only slow tests
uv run pytest -m slow

# Run all except slow tests
uv run pytest -m "not slow"

# Run unit and integration tests
uv run pytest -m "unit or integration"
```

## Test Fixtures

### User Fixtures
- `user` - Regular user
- `staff_user` - Staff user
- `admin_user` - Admin user
- `authenticated_client` - Logged in client
- `admin_client` - Admin logged in client

### Database Fixtures
- `db` - Database access
- `transactional_db` - Transactional database

### API Fixtures
- `api_client` - DRF API client
- `authenticated_api_client` - Authenticated API client
- `admin_api_client` - Admin API client

### Utility Fixtures
- `mock_datetime` - Mock datetime for consistent testing
- `assert_num_queries` - Assert number of database queries
- `assert_email_sent` - Assert emails were sent

## Writing Tests

### Unit Test Example
```python
import pytest
from apps.enrollment.models import ClassHeaderEnrollment

@pytest.mark.django_db
@pytest.mark.unit
class TestEnrollmentModel:
    def test_enrollment_validation(self):
        """Test enrollment business rules."""
        # Test implementation
        pass

    @pytest.mark.parametrize("status,expected", [
        ("ENROLLED", True),
        ("DROPPED", False),
        ("WITHDRAWN", False),
    ])
    def test_enrollment_status(self, status, expected):
        """Test enrollment status affects active state."""
        # Test implementation
        pass
```

### Integration Test Example
```python
@pytest.mark.django_db
@pytest.mark.integration
class TestEnrollmentWorkflow:
    def test_complete_enrollment_process(self, student, course):
        """Test full enrollment workflow from registration to confirmation."""
        # Test implementation
        pass
```

### API Test Example
```python
@pytest.mark.django_db
@pytest.mark.api
class TestEnrollmentAPI:
    def test_enroll_student_endpoint(self, authenticated_api_client):
        """Test POST /api/enrollments/ endpoint."""
        response = authenticated_api_client.post(
            '/api/enrollments/',
            data={'student_id': 1, 'class_id': 1}
        )
        assert response.status_code == 201
```

## Test Data Generation

We use `factory_boy` for generating test data:

```python
from tests.fixtures.factories import StudentProfileFactory, CourseFactory

# Create a student
student = StudentProfileFactory()

# Create multiple students
students = StudentProfileFactory.create_batch(5)

# Create with specific attributes
student = StudentProfileFactory(
    person__personal_name="John",
    current_status="ACTIVE"
)
```

## Coverage Requirements

Minimum coverage requirements by app category:

- **Critical Apps** (common, accounts, people, enrollment): 95%+
- **Core Apps** (curriculum, grading, finance): 90%+
- **Business Apps** (academic, scholarships, attendance): 85%+
- **Service Apps** (academic_records, web_interface): 80%+
- **Integration Apps** (mobile, moodle, analytics): 70%+

## Performance Testing

### Using pytest-benchmark
```python
@pytest.mark.performance
def test_enrollment_performance(benchmark):
    """Test enrollment creation performance."""
    result = benchmark(create_enrollment, student, course)
    assert result is not None
```

### Load Testing
```bash
# Run performance tests only
uv run pytest -m performance --benchmark-only

# Compare benchmark results
uv run pytest -m performance --benchmark-compare
```

## Debugging Tests

### Verbose Output
```bash
# Show test names as they run
uv run pytest -v

# Show captured output
uv run pytest -s

# Show local variables on failure
uv run pytest -l

# Stop on first failure
uv run pytest -x

# Enter debugger on failure
uv run pytest --pdb
```

### Specific Test Debugging
```bash
# Run single test with full output
uv run pytest path/to/test.py::TestClass::test_method -vvs
```

## Continuous Integration

Tests are automatically run on:
- Every commit (via pre-commit hooks)
- Every pull request (via GitHub Actions)
- Nightly full test suite run

### CI Configuration
```yaml
# .github/workflows/test.yml
- name: Run Tests
  run: |
    docker compose -f docker-compose.test.yml up -d
    docker compose -f docker-compose.test.yml run django pytest
    docker compose -f docker-compose.test.yml down
```

## Common Issues and Solutions

### Issue: Tests fail with "Database access not allowed"
**Solution**: Add `@pytest.mark.django_db` decorator to test class or method

### Issue: Tests are slow
**Solution**:
- Use SQLite for unit tests (automatic)
- Use `--reuse-db` flag
- Run tests in parallel with `-n auto`

### Issue: Flaky tests
**Solution**:
- Use `freezegun` for time-dependent tests
- Mock external services
- Use `transactional_db` fixture for isolation

### Issue: Import errors
**Solution**: Ensure `PYTHONPATH` includes project root and apps directory

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Use Fixtures**: Don't repeat setup code
3. **Parametrize**: Test multiple scenarios with one test
4. **Mock External Services**: Don't make real API calls
5. **Test Edge Cases**: Include boundary values and error conditions
6. **Clear Names**: Test names should describe what they test
7. **Fast Tests**: Keep individual tests under 1 second
8. **Documentation**: Add docstrings explaining complex tests

## Contributing

When adding new tests:
1. Follow existing patterns and organization
2. Add appropriate markers
3. Ensure tests pass locally before committing
4. Maintain or improve coverage
5. Update this README if adding new patterns
