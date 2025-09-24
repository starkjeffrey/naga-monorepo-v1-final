# Naga SIS Test Suite Rewrite Plan

## Executive Summary

Complete test suite rewrite for the Naga Student Information System backend, covering 19 Django apps with a focus on clean architecture, comprehensive coverage, and maintainable test patterns.

## Current State Analysis

### Test Coverage by App

| App | Test Files | Coverage Status | Priority |
|-----|-----------|-----------------|----------|
| **finance** | 20 | Well-tested ✅ | Reference |
| **scholarships** | 9 | Moderate 🟡 | High |
| **language** | 6 | Moderate 🟡 | Medium |
| **enrollment** | 4 | Basic 🟠 | Critical |
| **mobile** | 3 | Basic 🟠 | Low |
| **grading** | 2 | Minimal ❌ | High |
| **curriculum** | 1 | Minimal ❌ | Critical |
| **scheduling** | 1 | Minimal ❌ | High |
| **academic_records** | 1 | Minimal ❌ | Medium |
| **people** | 0 | No tests ⚠️ | Critical |
| **attendance** | 0 | No tests ⚠️ | High |
| **accounts** | 0 | No tests ⚠️ | Critical |
| **common** | 0 | No tests ⚠️ | Critical |
| **academic** | 0 | No tests ⚠️ | High |
| **level_testing** | 0 | No tests ⚠️ | Low |
| **analytics** | 0 | No tests ⚠️ | Low |
| **moodle** | 0 | No tests ⚠️ | Low |
| **web_interface** | 0 | No tests ⚠️ | Medium |

### Dependency Analysis

#### Level 0 - Foundation (No Dependencies)
- **common** - Base utilities, audit logging, holidays
- **accounts** - User management, authentication
- **level_testing** - Standalone placement testing

#### Level 1 - Core Domain (Foundation Dependencies)
- **people** → accounts, common
- **curriculum** → common
- **scheduling** → common, curriculum

#### Level 2 - Business Domain (Core Dependencies)
- **enrollment** → accounts, common, curriculum, people
- **grading** → common, curriculum, people, scheduling
- **attendance** → common, enrollment, people, scheduling
- **finance** → common, curriculum, enrollment, people

#### Level 3 - Advanced Features (Business Dependencies)
- **academic** → common, curriculum, enrollment, grading, people
- **scholarships** → common, curriculum, finance, people
- **language** → common, curriculum, enrollment, people, scheduling

#### Level 4 - Service Layer (Multi-Domain Dependencies)
- **academic_records** → academic, common, curriculum, enrollment, finance
- **web_interface** → curriculum, enrollment, finance, grading, people
- **mobile** → common, people
- **moodle** → common, curriculum, people
- **analytics** → curriculum, enrollment, people

## Test Strategy

### Testing Principles

1. **Clean Architecture Alignment**
   - Unit tests for domain logic (no dependencies)
   - Integration tests for app interactions
   - End-to-end tests for critical workflows

2. **Test Isolation**
   - Use factories, not fixtures
   - SQLite for unit tests (speed)
   - PostgreSQL for integration tests (accuracy)
   - Transaction rollback between tests

3. **Coverage Goals**
   - 100% coverage for business logic
   - 90% coverage for models and services
   - 80% coverage for views and serializers
   - Critical path testing for all workflows

### Test Categories

#### 🧪 Unit Tests
- **Scope**: Individual functions, methods, validators
- **Database**: In-memory SQLite
- **Mocking**: External dependencies mocked
- **Speed**: <0.1s per test
- **Naming**: `test_unit_*.py`

#### 🔄 Integration Tests
- **Scope**: Multi-component interactions
- **Database**: SQLite with transactions
- **Mocking**: Minimal, only external services
- **Speed**: <1s per test
- **Naming**: `test_integration_*.py`

#### 🌐 End-to-End Tests
- **Scope**: Complete user workflows
- **Database**: PostgreSQL (Docker)
- **Mocking**: No mocking
- **Speed**: <5s per test
- **Naming**: `test_e2e_*.py`

#### ⚡ Performance Tests
- **Scope**: Load testing, query optimization
- **Database**: PostgreSQL with realistic data
- **Metrics**: Response time, query count, memory usage
- **Naming**: `test_performance_*.py`

#### 🔒 Security Tests
- **Scope**: Permission checks, data isolation
- **Focus**: Multi-tenant isolation, role-based access
- **Naming**: `test_security_*.py`

## Implementation Plan

### Phase 1: Foundation & Infrastructure (Week 1)

#### 1.1 Test Infrastructure Setup
- [ ] Create `tests/` base directory structure
- [ ] Setup pytest configuration with plugins
- [ ] Create base test classes and mixins
- [ ] Setup factory_boy for all models
- [ ] Create test data generators
- [ ] Setup coverage reporting

#### 1.2 Foundation Layer Tests
- [ ] **common** app (Critical)
  - Unit tests for utilities
  - Audit logging tests
  - Holiday management tests
  - Base model tests

- [ ] **accounts** app (Critical)
  - Authentication flow tests
  - Permission tests
  - MFA tests
  - User management tests

### Phase 2: Core Domain (Week 2)

#### 2.1 People Management
- [ ] **people** app (Critical)
  - Person model tests
  - Student/Teacher/Staff tests
  - Emergency contact tests
  - Profile management tests

#### 2.2 Academic Structure
- [ ] **curriculum** app (Critical)
  - Course catalog tests
  - Program requirement tests
  - Senior project tests
  - Prerequisite tests

- [ ] **scheduling** app (High)
  - Class schedule tests
  - Room allocation tests
  - Time conflict tests
  - Capacity tests

### Phase 3: Business Logic (Week 3)

#### 3.1 Enrollment & Registration
- [ ] **enrollment** app (Critical)
  - Registration workflow tests
  - Enrollment validation tests
  - Waitlist tests
  - Drop/Add tests

#### 3.2 Academic Progress
- [ ] **grading** app (High)
  - Grade calculation tests
  - GPA computation tests
  - Grade submission tests
  - Transcript tests

- [ ] **attendance** app (High)
  - Attendance tracking tests
  - Mobile check-in tests
  - Attendance reports tests

### Phase 4: Financial Systems (Week 4)

#### 4.1 Core Finance
- [ ] **finance** app (Reference Implementation)
  - Review existing comprehensive tests
  - Ensure transaction safety
  - QuickBooks integration tests
  - Payment workflow tests

#### 4.2 Financial Aid
- [ ] **scholarships** app (High)
  - Scholarship application tests
  - Award calculation tests
  - Sponsor management tests
  - Financial aid tests

### Phase 5: Advanced Features (Week 5)

#### 5.1 Academic Services
- [ ] **academic** app (High)
  - Requirement checking tests
  - Equivalency tests
  - Graduation audit tests
  - Academic standing tests

- [ ] **academic_records** app (Medium)
  - Transcript generation tests
  - Official document tests
  - Record verification tests

#### 5.2 Specialized Features
- [ ] **language** app (Medium)
  - Language course tests
  - Level progression tests
  - Certificate tests

- [ ] **level_testing** app (Low)
  - Placement test tests
  - Fee processing tests
  - Result recording tests

### Phase 6: External Integrations (Week 6)

#### 6.1 User Interfaces
- [ ] **web_interface** app (Medium)
  - View tests
  - Template rendering tests
  - Form submission tests

- [ ] **mobile** app (Low)
  - API endpoint tests
  - Mobile-specific logic tests

#### 6.2 External Systems
- [ ] **moodle** app (Low)
  - Integration tests
  - Sync tests

- [ ] **analytics** app (Low)
  - Report generation tests
  - Data aggregation tests

## Test Standards & Patterns

### File Organization
```
apps/{app_name}/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── factories.py             # Factory definitions
│   ├── test_unit_models.py     # Model unit tests
│   ├── test_unit_services.py   # Service unit tests
│   ├── test_unit_validators.py # Validator tests
│   ├── test_integration_*.py   # Integration tests
│   ├── test_e2e_*.py           # End-to-end tests
│   └── test_security_*.py      # Security tests
```

### Naming Conventions
- Test files: `test_{type}_{component}.py`
- Test classes: `Test{Component}{Type}`
- Test methods: `test_{scenario}_{expected_outcome}`
- Factories: `{Model}Factory`

### Test Structure Template
```python
"""Test module for {component}."""

import pytest
from django.test import TestCase
from django.db import transaction

from apps.{app}.models import {Model}
from apps.{app}.services import {Service}
from .factories import {Model}Factory


class Test{Model}Unit(TestCase):
    """Unit tests for {Model}."""

    def setUp(self):
        """Set up test fixtures."""
        self.instance = {Model}Factory.build()

    def test_validation_valid_data(self):
        """Test model validation with valid data."""
        # Arrange
        data = {...}

        # Act
        instance = {Model}(**data)

        # Assert
        instance.full_clean()  # Should not raise

    def test_validation_invalid_data(self):
        """Test model validation with invalid data."""
        # Arrange
        data = {...}

        # Act & Assert
        with pytest.raises(ValidationError):
            instance = {Model}(**data)
            instance.full_clean()


class Test{Service}Integration(TestCase):
    """Integration tests for {Service}."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = {Service}()
        self.test_data = {Model}Factory.create_batch(3)

    @transaction.atomic
    def test_workflow_complete_cycle(self):
        """Test complete workflow from start to finish."""
        # Arrange
        initial_state = {...}

        # Act
        result = self.service.process_workflow(initial_state)

        # Assert
        assert result.status == 'completed'
        assert result.errors == []
```

### Factory Pattern Template
```python
"""Factories for {app} app models."""

import factory
from factory.django import DjangoModelFactory
from faker import Faker

from apps.{app}.models import {Model}

fake = Faker()


class {Model}Factory(DjangoModelFactory):
    """Factory for {Model}."""

    class Meta:
        model = {Model}
        django_get_or_create = ['unique_field']

    # Simple fields
    name = factory.LazyAttribute(lambda o: fake.name())
    email = factory.LazyAttribute(lambda o: fake.email())

    # Related fields
    user = factory.SubFactory('apps.accounts.tests.factories.UserFactory')

    # Post-generation hooks
    @factory.post_generation
    def related_objects(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for obj in extracted:
                self.related.add(obj)
```

### Assertion Patterns
```python
# Model state assertions
assert instance.status == expected_status
assert instance.is_valid()

# Collection assertions
assert len(results) == expected_count
assert all(r.is_active for r in results)

# Exception assertions
with pytest.raises(ValidationError) as exc_info:
    service.validate(invalid_data)
assert 'expected_message' in str(exc_info.value)

# Database assertions
assert Model.objects.filter(criteria).exists()
assert Model.objects.count() == expected_count

# Performance assertions
with self.assertNumQueries(expected_queries):
    service.complex_operation()
```

## Quality Metrics

### Coverage Requirements
- **Critical Apps** (common, accounts, people, enrollment): 95%+
- **Core Apps** (curriculum, grading, finance): 90%+
- **Business Apps** (academic, scholarships, attendance): 85%+
- **Service Apps** (academic_records, web_interface): 80%+
- **Integration Apps** (mobile, moodle, analytics): 70%+

### Performance Targets
- Unit test suite: <30 seconds
- Integration test suite: <5 minutes
- Full test suite: <15 minutes
- Individual test: <1 second (unit), <5 seconds (integration)

### Quality Gates
- All tests must pass before merge
- Coverage must not decrease
- No flaky tests allowed
- Performance benchmarks must be met

## Tools & Technologies

### Testing Stack
- **pytest**: Test runner and framework
- **pytest-django**: Django integration
- **pytest-cov**: Coverage reporting
- **pytest-xdist**: Parallel test execution
- **factory_boy**: Test data generation
- **faker**: Realistic test data
- **freezegun**: Time mocking
- **responses**: HTTP mocking

### CI/CD Integration
- Run tests on every commit
- Parallel test execution
- Coverage reports to SonarQube
- Performance regression detection
- Automated test environment setup

## Success Criteria

1. **Zero untested critical paths** - All user workflows have E2E tests
2. **No regression bugs** - Comprehensive test coverage prevents regressions
3. **Fast feedback loop** - Tests run quickly for rapid development
4. **Clear failure messages** - Tests provide actionable error information
5. **Maintainable test code** - Tests follow consistent patterns and are easy to update

## Risk Mitigation

### Identified Risks
1. **Complex interdependencies** - Mitigate with proper test isolation
2. **Data consistency** - Use transactions and proper cleanup
3. **Performance degradation** - Monitor test execution time
4. **Flaky tests** - Eliminate race conditions and external dependencies
5. **Coverage gaps** - Regular coverage audits and reviews

### Mitigation Strategies
- Start with critical paths
- Build robust test infrastructure first
- Regular test review and refactoring
- Continuous monitoring of test metrics
- Team training on testing best practices

## Timeline

| Week | Phase | Deliverables |
|------|-------|--------------|
| 1 | Foundation | Test infrastructure, common, accounts |
| 2 | Core Domain | people, curriculum, scheduling |
| 3 | Business Logic | enrollment, grading, attendance |
| 4 | Financial | finance review, scholarships |
| 5 | Advanced | academic, academic_records, language |
| 6 | Integration | web_interface, mobile, analytics |

## Next Steps

1. Review and approve this test plan
2. Set up test infrastructure and tooling
3. Create base test classes and utilities
4. Begin Phase 1 implementation
5. Establish daily test metrics reporting

---

**Document Version**: 1.0
**Created**: 2024-12-XX
**Status**: Draft - Pending Review
**Owner**: Test Engineering Team
