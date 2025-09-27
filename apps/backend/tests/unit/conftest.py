"""
Configuration for unit tests.

Unit tests should be isolated and fast, mocking external dependencies.
"""

from unittest.mock import Mock, patch

import pytest
from django.test import override_settings


@pytest.fixture
def mock_redis():
    """Mock Redis connection for unit tests."""
    with patch("django_redis.get_redis_connection") as mock_conn:
        mock_conn.return_value = Mock()
        yield mock_conn.return_value


@pytest.fixture
def mock_dramatiq():
    """Mock Dramatiq broker for unit tests."""
    with patch("dramatiq.get_broker") as mock_broker:
        yield mock_broker.return_value


@pytest.fixture
def mock_email():
    """Mock email sending for unit tests."""
    with patch("django.core.mail.send_mail") as mock_send:
        yield mock_send


@pytest.fixture
def isolated_settings():
    """Isolated Django settings for unit tests."""
    with override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.dummy.DummyCache",
            }
        },
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


@pytest.fixture(autouse=True)
def enable_db_access_for_all_unit_tests(db):
    """
    Allow database access for all unit tests.

    This is automatically applied to all unit tests to simplify test writing
    while maintaining the fast execution of unit tests.
    """
    pass
