"""
Root conftest.py - Shared pytest fixtures and configuration for Naga SIS test suite.

This module provides:
- Database fixtures and transaction management
- Authentication and user fixtures
- Mock services and external boundaries
- Time manipulation utilities
- Test data factories
- API test clients
- Performance benchmarking utilities
"""

import json
import logging
import os
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, patch

import factory
import faker
import httpx
import pytest
import respx
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.utils import timezone as django_timezone
from freezegun import freeze_time
from ninja.testing import TestClient as NinjaTestClient

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Configure logging for tests
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Initialize faker with seed for deterministic data
fake = faker.Faker()
faker.Faker.seed(12345)

User = get_user_model()

# ============================================================================
# PYTEST CONFIGURATION HOOKS
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers if not already registered
    config.addinivalue_line("markers", "benchmark: mark test as a performance benchmark")
    config.addinivalue_line("markers", "requires_celery: mark test as requiring Celery/Dramatiq")

    # Set test environment variables
    os.environ.setdefault("TESTING", "true")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.test")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add automatic markers."""
    for item in items:
        # Add django_db marker to all tests in integration folder
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.django_db)

        # Add unit marker to all tests in unit folder
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)

        # Skip WIP tests in CI
        if os.environ.get("CI") and item.get_closest_marker("wip"):
            item.add_marker(pytest.mark.skip(reason="WIP test skipped in CI"))


# ============================================================================
# SESSION-LEVEL FIXTURES
# ============================================================================


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Override django_db_setup to create test database with proper settings.
    """
    with django_db_blocker.unblock():
        # Run any session-level database setup here
        pass


@pytest.fixture(scope="session", autouse=True)
def faker_session():
    """Provide session-level faker instance with fixed seed."""
    faker_instance = faker.Faker()
    faker_instance.seed_instance(12345)
    return faker_instance


# ============================================================================
# DATABASE FIXTURES
# ============================================================================


@pytest.fixture
def db_access_without_rollback(db, django_db_reset_sequences):
    """
    Provide database access without automatic rollback.
    Useful for testing transaction behavior.
    """
    pass


@pytest.fixture
def transactional_db(transactional_db):
    """
    Provide transactional database access for testing real transactions.
    """
    return transactional_db


# ============================================================================
# USER AND AUTHENTICATION FIXTURES
# ============================================================================


@pytest.fixture
def create_user(db):
    """Factory fixture to create users with optional attributes."""

    def _create_user(username=None, email=None, password="testpass123", is_staff=False, is_superuser=False, **kwargs):
        username = username or fake.user_name()
        email = email or fake.email()

        user = User.objects.create_user(
            username=username, email=email, password=password, is_staff=is_staff, is_superuser=is_superuser, **kwargs
        )
        return user

    return _create_user


@pytest.fixture
def admin_user(create_user):
    """Create an admin user."""
    return create_user(username="admin", email="admin@test.com", is_staff=True, is_superuser=True)


@pytest.fixture
def staff_user(create_user):
    """Create a staff user."""
    return create_user(username="staff", email="staff@test.com", is_staff=True)


@pytest.fixture
def regular_user(create_user):
    """Create a regular user."""
    return create_user(username="testuser", email="user@test.com")


@pytest.fixture
def finance_admin(create_user, db):
    """Create a finance admin with appropriate permissions."""
    user = create_user(username="finance_admin", is_staff=True)
    group, _ = Group.objects.get_or_create(name="Finance Admin")

    # Add finance-related permissions
    permissions = Permission.objects.filter(content_type__app_label="finance")
    group.permissions.set(permissions)
    user.groups.add(group)

    return user


@pytest.fixture
def student_user(create_user, db):
    """Create a student user with student profile."""
    from apps.people.models import Person, StudentProfile

    user = create_user(username="student", email="student@test.com")
    person = Person.objects.create(first_name="Test", last_name="Student", email="student@test.com", user=user)
    StudentProfile.objects.create(person=person, student_id=f"STU{fake.random_number(digits=6):06d}")
    return user


@pytest.fixture
def teacher_user(create_user, db):
    """Create a teacher user with teacher profile."""
    from apps.people.models import Person, TeacherProfile

    user = create_user(username="teacher", email="teacher@test.com")
    person = Person.objects.create(first_name="Test", last_name="Teacher", email="teacher@test.com", user=user)
    TeacherProfile.objects.create(person=person, employee_id=f"EMP{fake.random_number(digits=6):06d}")
    return user


# ============================================================================
# CLIENT FIXTURES
# ============================================================================


@pytest.fixture
def client():
    """Provide Django test client."""
    return Client()


@pytest.fixture
def authenticated_client(client, regular_user):
    """Provide authenticated Django test client."""
    client.force_login(regular_user)
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """Provide admin-authenticated Django test client."""
    client.force_login(admin_user)
    return client


@pytest.fixture
def api_client():
    """Provide httpx async client for API testing."""
    return httpx.Client(base_url="http://testserver", headers={"Content-Type": "application/json"})


@pytest.fixture
def authenticated_api_client(api_client, regular_user):
    """Provide authenticated API client with JWT token."""
    from api.v1.auth import create_jwt_token

    token = create_jwt_token(regular_user)
    api_client.headers["Authorization"] = f"Bearer {token}"
    return api_client


@pytest.fixture
def ninja_client():
    """Provide Django-Ninja test client."""
    from api.v1 import api

    return NinjaTestClient(api)


# ============================================================================
# MOCK FIXTURES
# ============================================================================


@pytest.fixture
def mock_redis():
    """Mock Redis cache."""
    with patch("django.core.cache.cache") as mock_cache:
        mock_cache.get.return_value = None
        mock_cache.set.return_value = True
        mock_cache.delete.return_value = True
        yield mock_cache


@pytest.fixture
def mock_dramatiq():
    """Mock Dramatiq task queue."""
    with patch("django_dramatiq.tasks") as mock_tasks:
        mock_tasks.send.return_value = Mock(message_id="test-message-id")
        yield mock_tasks


@pytest.fixture
def mock_email(settings):
    """Mock email backend."""
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    from django.core import mail

    mail.outbox = []
    return mail


@pytest.fixture
def mock_storage():
    """Mock file storage."""
    with patch("django.core.files.storage.default_storage") as mock_storage:
        mock_storage.save.return_value = "test-file.pdf"
        mock_storage.url.return_value = "/media/test-file.pdf"
        mock_storage.delete.return_value = None
        yield mock_storage


@pytest.fixture
def mock_external_api():
    """Mock external API calls using respx."""
    with respx.mock:
        # Mock common external APIs
        respx.get("https://api.example.com/health").mock(return_value=httpx.Response(200, json={"status": "ok"}))
        yield respx


# ============================================================================
# TIME FIXTURES
# ============================================================================


@pytest.fixture
def frozen_time():
    """Freeze time at a specific moment."""
    with freeze_time("2025-01-15 10:00:00", tz_offset=0) as frozen:
        yield frozen


@pytest.fixture
def mock_now(monkeypatch):
    """Mock Django timezone.now()."""
    fixed_time = datetime(2025, 1, 15, 10, 0, 0, tzinfo=UTC)
    monkeypatch.setattr(django_timezone, "now", lambda: fixed_time)
    return fixed_time


# ============================================================================
# TEST DATA FIXTURES
# ============================================================================


@pytest.fixture
def sample_term(db):
    """Create a sample academic term."""
    from apps.curriculum.models import Term

    return Term.objects.create(
        term_id="2025SP",
        name="Spring 2025",
        start_date=datetime(2025, 1, 15).date(),
        end_date=datetime(2025, 5, 15).date(),
        is_active=True,
    )


@pytest.fixture
def sample_course(db):
    """Create a sample course."""
    from apps.curriculum.models import Course

    return Course.objects.create(
        code="CS101", name="Introduction to Computer Science", credits=3, description="Basic computer science concepts"
    )


@pytest.fixture
def sample_invoice(db, student_user):
    """Create a sample invoice."""
    from apps.finance.models import Invoice
    from apps.people.models import StudentProfile

    student = StudentProfile.objects.get(person__user=student_user)

    return Invoice.objects.create(
        student=student,
        invoice_number=f"INV-{fake.random_number(digits=6):06d}",
        total_amount=Decimal("1000.00"),
        status="pending",
    )


# ============================================================================
# FACTORY FIXTURES
# ============================================================================


@pytest.fixture
def person_factory(db):
    """Factory for creating Person instances."""
    from apps.people.models import Person

    class PersonFactory(factory.django.DjangoModelFactory):
        class Meta:
            model = Person

        first_name = factory.Faker("first_name")
        last_name = factory.Faker("last_name")
        email = factory.Faker("email")
        phone = factory.Faker("phone_number")
        date_of_birth = factory.Faker("date_of_birth", minimum_age=18, maximum_age=65)

    return PersonFactory


@pytest.fixture
def student_factory(db, person_factory):
    """Factory for creating Student instances."""
    from apps.people.models import StudentProfile

    class StudentFactory(factory.django.DjangoModelFactory):
        class Meta:
            model = StudentProfile

        person = factory.SubFactory(person_factory)
        student_id = factory.Sequence(lambda n: f"STU{n:06d}")
        enrollment_date = factory.Faker("date_this_year")
        status = "active"

    return StudentFactory


@pytest.fixture
def course_factory(db):
    """Factory for creating Course instances."""
    from apps.curriculum.models import Course

    class CourseFactory(factory.django.DjangoModelFactory):
        class Meta:
            model = Course

        code = factory.Sequence(lambda n: f"CS{n:03d}")
        name = factory.Faker("catch_phrase")
        credits = factory.Faker("random_int", min=1, max=4)
        description = factory.Faker("paragraph")

    return CourseFactory


# ============================================================================
# PERFORMANCE FIXTURES
# ============================================================================


@pytest.fixture
def benchmark_timer():
    """Simple timer for performance benchmarking."""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def __enter__(self):
            self.start_time = time.perf_counter()
            return self

        def __exit__(self, *args):
            self.end_time = time.perf_counter()

        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return None

    return Timer


# ============================================================================
# SETTINGS OVERRIDE FIXTURES
# ============================================================================


@pytest.fixture
def debug_off(settings):
    """Disable DEBUG for testing production behavior."""
    settings.DEBUG = False
    return settings


@pytest.fixture
def use_sqlite(settings):
    """Use SQLite for faster tests that don't need PostgreSQL features."""
    settings.DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
    return settings


# ============================================================================
# CLEANUP FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def cleanup_media(settings):
    """Clean up media files after each test."""
    yield
    # Clean up any uploaded files
    import shutil

    media_root = Path(settings.MEDIA_ROOT)
    if media_root.exists() and "test" in str(media_root):
        shutil.rmtree(media_root, ignore_errors=True)
        media_root.mkdir(parents=True, exist_ok=True)


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    cache.clear()
    yield
    cache.clear()


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def assert_datetime_equal(dt1, dt2, tolerance_seconds=1):
    """Assert two datetimes are approximately equal."""
    if dt1 and dt2:
        diff = abs((dt1 - dt2).total_seconds())
        assert diff <= tolerance_seconds, f"Datetimes differ by {diff} seconds"
    else:
        assert dt1 == dt2


def create_test_file(filename="test.pdf", content=b"Test content", content_type="application/pdf"):
    """Create a test uploaded file."""
    return SimpleUploadedFile(filename, content, content_type=content_type)


def get_test_data_path(filename):
    """Get path to test data file."""
    return Path(__file__).parent / "fixtures" / filename


def load_json_fixture(filename):
    """Load JSON test fixture."""
    with open(get_test_data_path(filename)) as f:
        return json.load(f)
