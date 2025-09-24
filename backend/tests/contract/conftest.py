"""
Configuration for API contract tests.

Contract tests validate API endpoints against the OpenAPI schema and test
request/response contracts.
"""

import json

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework.test import APIClient

from tests.factories import PersonFactory, StudentProfileFactory, TeacherProfileFactory

User = get_user_model()


@pytest.fixture
def api_client():
    """DRF API client for contract tests."""
    return APIClient()


@pytest.fixture
def django_client():
    """Django test client for contract tests."""
    return Client()


@pytest.fixture
def admin_user(db):
    """Create admin user for contract tests."""
    return User.objects.create_superuser(
        username="contract_admin", email="admin@contract.test", password="adminpass123"
    )


@pytest.fixture
def finance_user(db):
    """Create finance user for contract tests."""
    user = User.objects.create_user(
        username="finance_user", email="finance@contract.test", password="financepass123", is_staff=True
    )
    # Add finance permissions here when implemented
    return user


@pytest.fixture
def academic_user(db):
    """Create academic user for contract tests."""
    user = User.objects.create_user(
        username="academic_user", email="academic@contract.test", password="academicpass123", is_staff=True
    )
    # Add academic permissions here when implemented
    return user


@pytest.fixture
def teacher_user(db):
    """Create teacher user for contract tests."""
    user = User.objects.create_user(username="teacher_user", email="teacher@contract.test", password="teacherpass123")
    person = PersonFactory(first_name="Contract", last_name="Teacher", email=user.email)
    teacher = TeacherProfileFactory(person=person, employee_id="CONTRTEACH001")
    return user, teacher


@pytest.fixture
def student_user(db):
    """Create student user for contract tests."""
    user = User.objects.create_user(username="student_user", email="student@contract.test", password="studentpass123")
    person = PersonFactory(first_name="Contract", last_name="Student", email=user.email)
    student = StudentProfileFactory(person=person, student_id="CONTRSTUD001")
    return user, student


@pytest.fixture
def authenticated_client(api_client, admin_user):
    """API client authenticated as admin."""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def finance_client(api_client, finance_user):
    """API client authenticated as finance user."""
    api_client.force_authenticate(user=finance_user)
    return api_client


@pytest.fixture
def academic_client(api_client, academic_user):
    """API client authenticated as academic user."""
    api_client.force_authenticate(user=academic_user)
    return api_client


@pytest.fixture
def teacher_client(api_client, teacher_user):
    """API client authenticated as teacher."""
    user, teacher = teacher_user
    api_client.force_authenticate(user=user)
    return api_client, teacher


@pytest.fixture
def student_client(api_client, student_user):
    """API client authenticated as student."""
    user, student = student_user
    api_client.force_authenticate(user=user)
    return api_client, student


@pytest.fixture
def openapi_schema():
    """Load OpenAPI schema for validation."""
    try:
        with open("openapi-schema.json") as f:
            return json.load(f)
    except FileNotFoundError:
        pytest.skip("OpenAPI schema file not found")


def assert_valid_response_schema(response_data, schema_definition):
    """
    Helper function to validate response against OpenAPI schema.

    Args:
        response_data: The response data to validate
        schema_definition: The schema definition from OpenAPI spec
    """
    from jsonschema import ValidationError, validate

    try:
        validate(instance=response_data, schema=schema_definition)
    except ValidationError as e:
        pytest.fail(f"Response schema validation failed: {e.message}")


@pytest.fixture
def schema_validator(openapi_schema):
    """Provide schema validation helper."""
    return lambda response_data, path: assert_valid_response_schema(response_data, openapi_schema["paths"][path])
