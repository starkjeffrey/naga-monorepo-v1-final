"""
Unit tests for Moodle integration models.

Tests the Moodle integration models for synchronization and health checking.
"""

import pytest
from django.utils import timezone

from apps.moodle.models import MoodleHealthCheck, MoodleSync


@pytest.mark.django_db
def test_moodle_sync_creation():
    """Test basic MoodleSync model creation."""
    sync = MoodleSync.objects.create(sync_type="USER", entity_id=123, status="PENDING", operation="CREATE")

    assert sync.sync_type == "USER"
    assert sync.entity_id == 123
    assert sync.status == "PENDING"
    assert sync.operation == "CREATE"
    assert sync.created_at is not None


@pytest.mark.django_db
def test_moodle_sync_str_representation():
    """Test string representation of MoodleSync."""
    sync = MoodleSync.objects.create(sync_type="COURSE", entity_id=456, status="SUCCESS", operation="UPDATE")

    expected = "MoodleSync(COURSE:456 - UPDATE - SUCCESS)"
    assert str(sync) == expected


@pytest.mark.django_db
def test_moodle_sync_status_choices():
    """Test that status choices are properly validated."""
    # Valid status
    sync = MoodleSync.objects.create(sync_type="ENROLLMENT", entity_id=789, status="FAILED", operation="DELETE")

    assert sync.status == "FAILED"


@pytest.mark.django_db
def test_moodle_sync_error_message_optional():
    """Test that error_message is optional for successful syncs."""
    sync = MoodleSync.objects.create(sync_type="USER", entity_id=100, status="SUCCESS", operation="CREATE")

    assert sync.error_message is None


@pytest.mark.django_db
def test_moodle_sync_with_error_message():
    """Test MoodleSync with error message for failed sync."""
    error_msg = "Connection timeout to Moodle server"
    sync = MoodleSync.objects.create(
        sync_type="COURSE", entity_id=200, status="FAILED", operation="CREATE", error_message=error_msg
    )

    assert sync.error_message == error_msg


@pytest.mark.django_db
def test_moodle_health_check_creation():
    """Test basic MoodleHealthCheck model creation."""
    health_check = MoodleHealthCheck.objects.create(check_type="CONNECTION", status="HEALTHY", response_time_ms=150)

    assert health_check.check_type == "CONNECTION"
    assert health_check.status == "HEALTHY"
    assert health_check.response_time_ms == 150
    assert health_check.checked_at is not None


@pytest.mark.django_db
def test_moodle_health_check_str_representation():
    """Test string representation of MoodleHealthCheck."""
    check_time = timezone.now()
    health_check = MoodleHealthCheck.objects.create(
        check_type="API", status="UNHEALTHY", response_time_ms=5000, checked_at=check_time
    )

    expected = f"MoodleHealthCheck(API - UNHEALTHY at {check_time})"
    assert str(health_check) == expected


@pytest.mark.django_db
def test_moodle_health_check_with_details():
    """Test MoodleHealthCheck with additional details."""
    details = {"error": "Authentication failed", "code": 401}
    health_check = MoodleHealthCheck.objects.create(
        check_type="AUTHENTICATION", status="UNHEALTHY", response_time_ms=1000, details=details
    )

    assert health_check.details == details
    assert health_check.details["error"] == "Authentication failed"


@pytest.mark.django_db
def test_moodle_health_check_no_details():
    """Test MoodleHealthCheck without details (should be null)."""
    health_check = MoodleHealthCheck.objects.create(check_type="CONNECTION", status="HEALTHY", response_time_ms=100)

    assert health_check.details is None


@pytest.mark.django_db
def test_moodle_health_check_ordering():
    """Test that health checks are ordered by checked_at descending."""
    # Create multiple health checks
    check1 = MoodleHealthCheck.objects.create(check_type="CONNECTION", status="HEALTHY", response_time_ms=100)

    check2 = MoodleHealthCheck.objects.create(check_type="API", status="HEALTHY", response_time_ms=200)

    # Get all checks (should be ordered by checked_at desc)
    checks = list(MoodleHealthCheck.objects.all())

    # Most recent should be first
    assert checks[0] == check2
    assert checks[1] == check1
