"""
Root configuration for Naga SIS test suite.

This file contains shared fixtures and configuration used across all tests.
It follows the TEST_PLAN.md specifications for comprehensive testing setup.
"""

import os

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import transaction
from django.test import override_settings

# Set up Django for testing
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")


# Database fixtures
@pytest.fixture(scope="session")
def django_db_setup():
    """Set up test database with basic fixtures."""
    settings.DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }


@pytest.fixture
def load_test_fixtures(db):
    """Load test fixtures for comprehensive testing."""
    call_command("loaddata", "tests/fixtures/users.json", verbosity=0)
    call_command("loaddata", "tests/fixtures/courses.json", verbosity=0)
    call_command("loaddata", "tests/fixtures/terms.json", verbosity=0)


# User fixtures
@pytest.fixture
def superuser(db):
    """Create superuser for testing admin functionality."""
    User = get_user_model()
    return User.objects.create_superuser(username="admin", email="admin@naga-sis.test", password="adminpass123")


@pytest.fixture
def staff_user(db):
    """Create staff user for testing staff functionality."""
    User = get_user_model()
    return User.objects.create_user(
        username="staff", email="staff@naga-sis.test", password="staffpass123", is_staff=True
    )


@pytest.fixture
def regular_user(db):
    """Create regular user for testing basic functionality."""
    User = get_user_model()
    return User.objects.create_user(username="user", email="user@naga-sis.test", password="userpass123")


# Authentication fixtures
@pytest.fixture
def authenticated_client(client, superuser):
    """Provide authenticated Django test client."""
    client.force_login(superuser)
    return client


@pytest.fixture
def staff_client(client, staff_user):
    """Provide staff-authenticated Django test client."""
    client.force_login(staff_user)
    return client


# Settings overrides for testing
@pytest.fixture
def test_settings():
    """Provide test-optimized Django settings."""
    with override_settings(
        # Disable migrations for speed
        MIGRATION_MODULES={
            "accounts": None,
            "academic": None,
            "academic_records": None,
            "attendance": None,
            "common": None,
            "curriculum": None,
            "enrollment": None,
            "finance": None,
            "grading": None,
            "language": None,
            "level_testing": None,
            "mobile": None,
            "moodle": None,
            "people": None,
            "scheduling": None,
            "scholarships": None,
            "settings": None,
            "users": None,
            "web_interface": None,
            "workflow": None,
        },
        # Use in-memory cache
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "test-cache",
            }
        },
        # Use locmem email backend
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        # Disable external services
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
        # Security settings for testing
        SECRET_KEY="test-secret-key-not-for-production",
        DEBUG=True,
        ALLOWED_HOSTS=["testserver", "localhost", "127.0.0.1"],
        # Media/Static for testing
        MEDIA_ROOT="/tmp/naga_test_media",
        STATIC_ROOT="/tmp/naga_test_static",
    ):
        yield


# Factory fixtures (import all factories for convenience)
@pytest.fixture
def person_factory():
    """Import PersonFactory for tests."""
    from tests.factories import PersonFactory

    return PersonFactory


@pytest.fixture
def student_factory():
    """Import StudentProfileFactory for tests."""
    from tests.factories import StudentProfileFactory

    return StudentProfileFactory


@pytest.fixture
def teacher_factory():
    """Import TeacherProfileFactory for tests."""
    from tests.factories import TeacherProfileFactory

    return TeacherProfileFactory


@pytest.fixture
def course_factory():
    """Import CourseFactory for tests."""
    from tests.factories import CourseFactory

    return CourseFactory


@pytest.fixture
def term_factory():
    """Import TermFactory for tests."""
    from tests.factories import TermFactory

    return TermFactory


@pytest.fixture
def invoice_factory():
    """Import InvoiceFactory for tests."""
    from tests.factories import InvoiceFactory

    return InvoiceFactory


@pytest.fixture
def payment_factory():
    """Import PaymentFactory for tests."""
    from tests.factories import PaymentFactory

    return PaymentFactory


@pytest.fixture
def enrollment_factory():
    """Import EnrollmentFactory for tests."""
    from tests.factories import EnrollmentFactory

    return EnrollmentFactory


# Transaction testing fixtures
@pytest.fixture
def transactional_db(db):
    """Enable transactional testing."""
    return db


@pytest.fixture
def atomic_transaction():
    """Provide atomic transaction context for testing."""

    def _atomic_transaction():
        return transaction.atomic()

    return _atomic_transaction


# Mock fixtures for external services
@pytest.fixture
def mock_redis():
    """Mock Redis for testing."""
    from unittest.mock import MagicMock, patch

    with patch("django_redis.get_redis_connection") as mock_conn:
        redis_mock = MagicMock()
        mock_conn.return_value = redis_mock
        yield redis_mock


@pytest.fixture
def mock_dramatiq():
    """Mock Dramatiq for testing."""
    from unittest.mock import MagicMock, patch

    with patch("dramatiq.get_broker") as mock_broker:
        broker_mock = MagicMock()
        mock_broker.return_value = broker_mock
        yield broker_mock


@pytest.fixture
def mock_email():
    """Mock email sending for testing."""
    from unittest.mock import patch

    with patch("django.core.mail.send_mail") as mock_send:
        yield mock_send


# Performance testing fixtures
@pytest.fixture
def benchmark_settings():
    """Settings optimized for performance benchmarking."""
    with override_settings(
        DEBUG=False,
        TEMPLATE_DEBUG=False,
        LOGGING_CONFIG=None,  # Disable logging for benchmarks
    ):
        yield


# API testing fixtures
@pytest.fixture
def api_client():
    """DRF API client for API testing."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def authenticated_api_client(api_client, superuser):
    """Authenticated DRF API client."""
    api_client.force_authenticate(user=superuser)
    return api_client


# Parametrized fixtures for comprehensive testing
@pytest.fixture(params=["sqlite3", "postgresql"])
def database_engine(request):
    """Test with different database engines."""
    return request.param


@pytest.fixture(params=[True, False])
def debug_mode(request):
    """Test with debug on/off."""
    with override_settings(DEBUG=request.param):
        yield request.param
