"""Root conftest.py for pytest configuration.

This file contains shared fixtures and configuration that are available
to all tests in the project.
"""

import os
import sys
from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import override_settings

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Configure Django settings for testing
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")


def pytest_configure(config):
    """Configure pytest with Django settings."""
    import django

    # Override settings for testing
    settings.DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "TEST": {
            "NAME": ":memory:",
        },
    }

    # Disable migrations for speed
    settings.MIGRATION_MODULES = {app: None for app in settings.INSTALLED_APPS if app.startswith("apps.")}

    # Use fast password hasher for tests
    settings.PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]

    # Disable cache
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    }

    # Disable debug toolbar
    settings.DEBUG_TOOLBAR = False

    # Configure test email backend
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

    django.setup()


# --- Database Fixtures ---


@pytest.fixture(scope="session")
def django_db_setup():
    """Override django_db_setup to use SQLite in-memory database for all tests."""

    settings.DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }


@pytest.fixture
def db(db):
    """Ensure database is available and transactions are enabled."""
    return db


@pytest.fixture
def transactional_db(transactional_db):
    """Use transactional database for tests that need it."""
    return transactional_db


# --- User and Authentication Fixtures ---


@pytest.fixture
def user_model():
    """Return the User model."""
    return get_user_model()


@pytest.fixture
def create_user(user_model):
    """Factory fixture to create users."""

    def _create_user(email="test@example.com", password="testpass123", is_staff=False, is_superuser=False, **kwargs):
        user = user_model.objects.create_user(
            email=email, password=password, is_staff=is_staff, is_superuser=is_superuser, **kwargs
        )
        user.raw_password = password  # Store raw password for login tests
        return user

    return _create_user


@pytest.fixture
def user(create_user):
    """Create a regular user."""
    return create_user()


@pytest.fixture
def staff_user(create_user):
    """Create a staff user."""
    return create_user(email="staff@example.com", is_staff=True)


@pytest.fixture
def admin_user(create_user):
    """Create an admin user."""
    return create_user(email="admin@example.com", is_staff=True, is_superuser=True)


@pytest.fixture
def authenticated_client(client, user):
    """Return a client with an authenticated user."""
    client.force_login(user)
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """Return a client with an authenticated admin user."""
    client.force_login(admin_user)
    return client


# --- Request Factory Fixtures ---


@pytest.fixture
def api_client():
    """Return a DRF API client for testing API endpoints."""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def authenticated_api_client(api_client, user):
    """Return an authenticated API client."""
    api_client.force_authenticate(user=user)
    return api_client


@pytest.fixture
def admin_api_client(api_client, admin_user):
    """Return an API client authenticated as admin."""
    api_client.force_authenticate(user=admin_user)
    return api_client


# --- Mock and Patch Fixtures ---


@pytest.fixture
def mock_datetime(monkeypatch):
    """Mock datetime for consistent testing."""
    import datetime
    from unittest.mock import Mock

    mock_dt = Mock()
    mock_dt.now.return_value = datetime.datetime(2024, 1, 15, 10, 0, 0)
    mock_dt.today.return_value = datetime.date(2024, 1, 15)

    monkeypatch.setattr("django.utils.timezone.now", lambda: mock_dt.now())
    return mock_dt


@pytest.fixture
def mock_external_api(monkeypatch):
    """Mock external API calls."""
    from unittest.mock import Mock

    mock_api = Mock()
    mock_api.call.return_value = {"status": "success"}
    return mock_api


# --- Settings Override Fixtures ---


@pytest.fixture
def enable_debug():
    """Enable DEBUG for specific tests."""
    with override_settings(DEBUG=True):
        yield


@pytest.fixture
def disable_cache():
    """Disable caching for specific tests."""
    with override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.dummy.DummyCache",
            }
        }
    ):
        yield


# --- Test Data Fixtures ---


@pytest.fixture
def sample_data():
    """Provide sample test data."""
    return {
        "valid_email": "test@example.com",
        "invalid_email": "not-an-email",
        "valid_phone": "+855123456789",
        "invalid_phone": "123",
        "valid_date": "2024-01-15",
        "invalid_date": "not-a-date",
    }


# --- Performance Testing Fixtures ---


@pytest.fixture
def benchmark_data():
    """Generate data for benchmark tests."""
    return list(range(10000))


# --- Cleanup Fixtures ---


@pytest.fixture(autouse=True)
def cleanup_media(settings, tmpdir):
    """Use temporary directory for media files during tests."""
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture(autouse=True)
def reset_sequences(db):
    """Reset database sequences after each test."""
    from django.db import connection

    yield

    # Reset sequences for SQLite
    if connection.vendor == "sqlite":
        with connection.cursor() as cursor:
            # Check if sqlite_sequence table exists before deleting from it
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='sqlite_sequence'")
            if cursor.fetchone()[0] > 0:
                cursor.execute("DELETE FROM sqlite_sequence")


# --- Marker Fixtures ---


@pytest.fixture(autouse=True)
def check_markers(request):
    """Check for specific markers and apply configurations."""
    if request.node.get_closest_marker("slow"):
        # Increase timeout for slow tests
        request.config.option.timeout = 60

    if request.node.get_closest_marker("integration"):
        # Use real database for integration tests
        pass  # Configuration handled per test

    if request.node.get_closest_marker("performance"):
        # Enable profiling for performance tests
        pass  # Configuration handled per test


# --- Custom Assertions ---


@pytest.fixture
def assert_num_queries():
    """Assert the number of database queries."""
    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    def _assert_num_queries(num, func=None, *args, **kwargs):
        with CaptureQueriesContext(connection) as context:
            if func:
                result = func(*args, **kwargs)
            else:
                result = None

        queries = len(context.captured_queries)
        assert queries == num, f"Expected {num} queries, got {queries}"
        return result

    return _assert_num_queries


@pytest.fixture
def assert_email_sent():
    """Assert that an email was sent."""
    from django.core import mail

    def _assert_email_sent(count=1, subject=None, to=None):
        assert len(mail.outbox) == count, f"Expected {count} emails, got {len(mail.outbox)}"

        if subject:
            assert any(email.subject == subject for email in mail.outbox), f"No email with subject '{subject}' found"

        if to:
            assert any(to in email.to for email in mail.outbox), f"No email sent to '{to}'"

    return _assert_email_sent
