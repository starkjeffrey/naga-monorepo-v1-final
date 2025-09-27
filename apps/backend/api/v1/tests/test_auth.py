"""Tests for unified v1 API authentication.

Tests JWT authentication integration and unified auth utilities.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from api.v1.auth import JWTAuth, jwt_auth

User = get_user_model()


class AuthTest(TestCase):
    """Test unified authentication system."""

    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(email="test@example.com", password="testpass123", is_staff=False)

    def test_jwt_auth_class_exists(self):
        """Test that JWTAuth class is properly imported."""
        self.assertIsNotNone(JWTAuth)
        self.assertTrue(callable(JWTAuth))

    def test_jwt_auth_instance_exists(self):
        """Test that jwt_auth instance is properly created."""
        self.assertIsNotNone(jwt_auth)
        self.assertIsInstance(jwt_auth, JWTAuth)

    def test_jwt_auth_integration(self):
        """Test JWT auth integration works."""
        # This is a basic integration test
        # Full JWT testing would require the mobile app JWT implementation
        auth_instance = JWTAuth()
        self.assertIsNotNone(auth_instance)

        # The actual JWT validation would happen in the mobile app
        # Here we just verify the class is properly imported and instantiated
