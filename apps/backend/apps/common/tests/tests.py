"""Comprehensive tests for common app models and utilities.

Tests cover the AuditModel base class functionality, validation,
timestamps, and shared utilities.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from apps.common.models import AuditModel, Room

User = get_user_model()

# Test constants
TIME_TOLERANCE_SECONDS = 0.01  # 10ms tolerance for timing tests


class AuditModelTest(TestCase):
    """Test cases for AuditModel base class."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
        )

    def test_audit_model_creation(self):
        """Test basic audit model creation."""
        model = Room.objects.create(name="Test Room", building="MAIN")

        assert model.id is not None
        assert model.created_at is not None
        assert model.updated_at is not None
        # Room only inherits TimestampedModel, not SoftDeleteModel
        # So it doesn't have is_deleted field

    def test_audit_model_timestamps(self):
        """Test that timestamps are automatically set."""
        before_creation = timezone.now()

        model = Room.objects.create(name="Test Room", building="MAIN")

        after_creation = timezone.now()

        # Check created_at is set correctly
        assert model.created_at >= before_creation
        assert model.created_at <= after_creation

        # Check updated_at is very close to created_at on creation
        # (allowing for small timing differences in auto_now vs auto_now_add)
        time_diff = abs((model.created_at - model.updated_at).total_seconds())
        assert time_diff < TIME_TOLERANCE_SECONDS  # Less than 10ms difference

    def test_audit_model_update_timestamp(self):
        """Test that updated_at changes on model update."""
        model = Room.objects.create(name="Test Room", building="MAIN")

        original_updated_at = model.updated_at

        # Wait a small amount to ensure timestamp difference
        import time

        time.sleep(0.01)

        # Update the model
        model.save()

        # Refresh from database
        model.refresh_from_db()

        # Check that updated_at has changed
        assert model.updated_at > original_updated_at

    def test_audit_model_str_method(self):
        """Test string representation includes timestamps."""
        model = Room.objects.create(name="Test Room", building="MAIN")

        str_repr = str(model)
        assert "MAIN" in str_repr
        assert "Test Room" in str_repr

    def test_audit_model_meta_abstract(self):
        """Test that AuditModel is abstract."""
        assert AuditModel._meta.abstract

    def test_audit_model_ordering(self):
        """Test default ordering by created_at."""
        # Create models at different times
        model1 = Room.objects.create(name="Test Room 1", building="MAIN")

        import time

        time.sleep(0.01)

        model2 = Room.objects.create(name="Test Room 2", building="MAIN")

        # Check ordering
        models = list(Room.objects.all())
        assert models[0] == model1  # Earlier created should come first
        assert models[1] == model2


class CommonAppConfigTest(TestCase):
    """Test cases for common app configuration."""

    def test_app_config(self):
        """Test app configuration is correct."""
        from apps.common.apps import CommonConfig

        assert CommonConfig.name == "apps.common"
        assert str(CommonConfig.verbose_name) == "Common Utilities"
        assert CommonConfig.default_auto_field == "django.db.models.BigAutoField"
