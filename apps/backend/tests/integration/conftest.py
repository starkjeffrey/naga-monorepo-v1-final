"""
Configuration for integration tests.

Integration tests use real database transactions and test component interactions.
"""

import pytest
from django.contrib.auth import get_user_model
from django.db import transaction

from tests.factories import (
    CourseFactory,
    MajorFactory,
    PersonFactory,
    StudentProfileFactory,
    TeacherProfileFactory,
    TermFactory,
)

# Note: get_user_model() moved inside fixtures to avoid Django setup issues


@pytest.fixture
def integration_user(db):
    """Create a test user for integration tests."""
    User = get_user_model()
    return User.objects.create_user(
        username="integration_test_user", email="integration@test.com", password="testpass123"
    )


@pytest.fixture
def test_term(db):
    """Create a test term for integration tests."""
    return TermFactory(name="Integration Test Term", code="ITT001", is_active=True)


@pytest.fixture
def test_course(db):
    """Create a test course for integration tests."""
    return CourseFactory(code="TEST101", title="Integration Test Course", credit_hours=3, is_active=True)


@pytest.fixture
def test_major(db):
    """Create a test major for integration tests."""
    return MajorFactory(name="Integration Test Major", code="ITM001", degree_type="BACHELOR", is_active=True)


@pytest.fixture
def test_student(db, integration_user):
    """Create a test student for integration tests."""
    person = PersonFactory(first_name="Integration", last_name="Student", email=integration_user.email)
    return StudentProfileFactory(person=person, student_id="INT001", status="ACTIVE")


@pytest.fixture
def test_teacher(db):
    """Create a test teacher for integration tests."""
    person = PersonFactory(first_name="Integration", last_name="Teacher")
    return TeacherProfileFactory(person=person, employee_id="INTEMP001", status="ACTIVE")


@pytest.fixture
def transaction_test_case():
    """
    Provide TransactionTestCase-like functionality for pytest.

    Use this for tests that need to test transaction behavior,
    database constraints, or signal handling.
    """

    class TransactionTestCaseFixture:
        def __enter__(self):
            transaction.set_autocommit(False)
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            transaction.rollback()
            transaction.set_autocommit(True)

    return TransactionTestCaseFixture()
