"""Security tests for mobile authentication services.

This module contains comprehensive security tests for:
- Google OAuth token verification
- JWT token generation and validation
- Rate limiting and authentication attempts
- User-student ID mapping
"""

from datetime import timedelta
from unittest.mock import patch

import jwt
from django.conf import settings
from django.test import TestCase
from django.utils import timezone

from apps.mobile.models import MobileAuthAttempt, MobileAuthToken
from apps.mobile.services import MobileAuthService, MobileUserService
from apps.people.models import Person, StudentProfile
from users.models import User


class TestMobileAuthServiceSecurity(TestCase):
    """Security tests for MobileAuthService."""

    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(email="test.student@pucsr.edu.kh", password="testpassword123")

        # Create test person
        self.person = Person.objects.create(
            user=self.user,
            family_name="Test",
            personal_name="Student",
            school_email="test.student@pucsr.edu.kh",
            phone="012345678",
        )

        # Create test student profile
        self.student_profile = StudentProfile.objects.create(
            person=self.person,
            student_id=12345,
            current_status="ACTIVE",
            enrollment_date=timezone.now().date(),
        )

        # Mock Google client ID
        self.google_client_id = "test-google-client-id"

    def test_google_token_verification_valid_token(self):
        """Test Google token verification with valid token."""
        mock_idinfo = {
            "iss": "accounts.google.com",
            "email": "test.student@pucsr.edu.kh",
            "name": "Test Student",
            "picture": "https://example.com/picture.jpg",
            "sub": "google-user-id-123",
        }

        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_idinfo

            result = MobileAuthService.verify_google_token("valid-google-token", "test.student@pucsr.edu.kh")

            self.assertTrue(result["valid"])
            self.assertEqual(result["email"], "test.student@pucsr.edu.kh")
            self.assertEqual(result["name"], "Test Student")

    def test_google_token_verification_invalid_issuer(self):
        """Test Google token verification with invalid issuer."""
        mock_idinfo = {
            "iss": "malicious.com",  # Invalid issuer
            "email": "test.student@pucsr.edu.kh",
            "name": "Test Student",
            "sub": "google-user-id-123",
        }

        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_idinfo

            result = MobileAuthService.verify_google_token("invalid-issuer-token", "test.student@pucsr.edu.kh")

            self.assertFalse(result["valid"])
            self.assertIn("Invalid token issuer", result["error"])

    def test_google_token_verification_email_mismatch(self):
        """Test Google token verification with email mismatch."""
        mock_idinfo = {
            "iss": "accounts.google.com",
            "email": "different.student@pucsr.edu.kh",  # Different email
            "name": "Test Student",
            "sub": "google-user-id-123",
        }

        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_idinfo

            result = MobileAuthService.verify_google_token("email-mismatch-token", "test.student@pucsr.edu.kh")

            self.assertFalse(result["valid"])
            self.assertIn("Email mismatch", result["error"])

    def test_google_token_verification_invalid_domain(self):
        """Test Google token verification with invalid email domain."""
        mock_idinfo = {
            "iss": "accounts.google.com",
            "email": "test.student@gmail.com",  # Invalid domain
            "name": "Test Student",
            "sub": "google-user-id-123",
        }

        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_idinfo

            result = MobileAuthService.verify_google_token("invalid-domain-token", "test.student@gmail.com")

            self.assertFalse(result["valid"])
            self.assertIn("Invalid email domain", result["error"])

    def test_google_token_verification_exception_handling(self):
        """Test Google token verification with exception."""
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.side_effect = ValueError("Invalid token")

            result = MobileAuthService.verify_google_token("invalid-token", "test.student@pucsr.edu.kh")

            self.assertFalse(result["valid"])
            self.assertIn("Invalid token", result["error"])

    def test_find_student_by_email_success(self):
        """Test successful student lookup by email."""
        result = MobileAuthService.find_student_by_email("test.student@pucsr.edu.kh")

        self.assertIsNotNone(result)
        person, student_id = result
        self.assertEqual(person.unique_id, self.person.unique_id)
        self.assertEqual(student_id, 12345)

    def test_find_student_by_email_not_found(self):
        """Test student lookup with non-existent email."""
        result = MobileAuthService.find_student_by_email("nonexistent@pucsr.edu.kh")

        self.assertIsNone(result)

    def test_find_student_by_email_no_student_profile(self):
        """Test student lookup for person without student profile."""
        # Create person without student profile
        Person.objects.create(
            family_name="No",
            personal_name="Profile",
            school_email="no.profile@pucsr.edu.kh",
        )

        result = MobileAuthService.find_student_by_email("no.profile@pucsr.edu.kh")

        self.assertIsNone(result)

    def test_jwt_token_generation(self):
        """Test JWT token generation with valid data."""
        device_id = "test-device-123"

        result = MobileAuthService.generate_jwt_token(
            person=self.person,
            student_id=12345,
            email="test.student@pucsr.edu.kh",
            device_id=device_id,
        )

        self.assertIn("jwt_token", result)
        self.assertIn("token_id", result)
        self.assertIn("expires_at", result)
        self.assertIn("expires_in", result)

        # Verify token can be decoded
        decoded = jwt.decode(
            result["jwt_token"],
            getattr(settings, "JWT_SECRET_KEY", settings.SECRET_KEY),
            algorithms=["HS256"],
        )

        self.assertEqual(decoded["student_id"], 12345)
        self.assertEqual(decoded["email"], "test.student@pucsr.edu.kh")
        self.assertEqual(decoded["device_id"], device_id)
        self.assertIn("STUDENT", decoded["roles"])

    def test_jwt_token_validation_valid_token(self):
        """Test JWT token validation with valid token."""
        # Generate token
        token_data = MobileAuthService.generate_jwt_token(
            person=self.person,
            student_id=12345,
            email="test.student@pucsr.edu.kh",
            device_id="test-device-123",
        )

        # Validate token
        result = MobileAuthService.validate_jwt_token(token_data["jwt_token"])

        self.assertTrue(result["valid"])
        self.assertEqual(result["student_id"], 12345)
        self.assertEqual(result["email"], "test.student@pucsr.edu.kh")

    def test_jwt_token_validation_expired_token(self):
        """Test JWT token validation with expired token."""
        # Create expired token
        payload = {
            "sub": "student_12345",
            "email": "test.student@pucsr.edu.kh",
            "student_id": 12345,
            "iss": "naga-sis",
            "aud": "naga-mobile",
            "exp": int((timezone.now() - timedelta(hours=1)).timestamp()),  # Expired 1 hour ago
        }

        expired_token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")

        result = MobileAuthService.validate_jwt_token(expired_token)

        self.assertFalse(result["valid"])
        self.assertIn("expired", result["error"].lower())

    def test_jwt_token_validation_invalid_signature(self):
        """Test JWT token validation with invalid signature."""
        # Create token with wrong secret
        payload = {
            "sub": "student_12345",
            "email": "test.student@pucsr.edu.kh",
            "student_id": 12345,
            "iss": "naga-sis",
            "aud": "naga-mobile",
            "exp": int((timezone.now() + timedelta(hours=1)).timestamp()),
        }

        invalid_token = jwt.encode(payload, "wrong-secret", algorithm="HS256")

        result = MobileAuthService.validate_jwt_token(invalid_token)

        self.assertFalse(result["valid"])
        self.assertIn("Invalid token", result["error"])

    def test_jwt_token_validation_revoked_token(self):
        """Test JWT token validation with revoked token."""
        # Generate token
        token_data = MobileAuthService.generate_jwt_token(
            person=self.person,
            student_id=12345,
            email="test.student@pucsr.edu.kh",
            device_id="test-device-123",
        )

        # Revoke token
        MobileAuthService.revoke_token(token_data["token_id"])

        # Validate token
        result = MobileAuthService.validate_jwt_token(token_data["jwt_token"])

        self.assertFalse(result["valid"])
        self.assertIn("revoked", result["error"].lower())

    def test_token_revocation(self):
        """Test token revocation functionality."""
        # Generate token
        token_data = MobileAuthService.generate_jwt_token(
            person=self.person,
            student_id=12345,
            email="test.student@pucsr.edu.kh",
            device_id="test-device-123",
        )

        # Revoke token
        success = MobileAuthService.revoke_token(token_data["token_id"])

        self.assertTrue(success)

        # Verify token is marked as revoked
        auth_token = MobileAuthToken.objects.get(token_id=token_data["token_id"])
        self.assertTrue(auth_token.revoked)

    def test_revoke_nonexistent_token(self):
        """Test revoking non-existent token."""
        success = MobileAuthService.revoke_token("nonexistent-token-id")

        self.assertFalse(success)

    def test_revoke_all_user_tokens(self):
        """Test revoking all tokens for a user."""
        # Generate multiple tokens
        for i in range(3):
            MobileAuthService.generate_jwt_token(
                person=self.person,
                student_id=12345,
                email="test.student@pucsr.edu.kh",
                device_id=f"test-device-{i}",
            )

        # Revoke all tokens
        count = MobileAuthService.revoke_all_user_tokens("test.student@pucsr.edu.kh")

        self.assertEqual(count, 3)

        # Verify all tokens are revoked
        revoked_tokens = MobileAuthToken.objects.filter(user=self.user, revoked=True).count()

        self.assertEqual(revoked_tokens, 3)

    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        identifier = "test-ip-123"

        # Should not be rate limited initially
        self.assertFalse(MobileAuthService.check_rate_limit(identifier))

        for _i in range(MobileAuthService.RATE_LIMIT_ATTEMPTS):
            MobileAuthService.check_rate_limit(identifier)

        # Should be rate limited now
        self.assertTrue(MobileAuthService.check_rate_limit(identifier))

    def test_auth_attempt_logging(self):
        """Test authentication attempt logging."""
        MobileAuthService.log_auth_attempt(
            email="test.student@pucsr.edu.kh",
            status=MobileAuthAttempt.Status.SUCCESS,
            device_id="test-device-123",
            ip_address="192.168.1.1",
            user_agent="Mobile App 1.0",
            student_id=12345,
        )

        # Verify log entry was created
        attempt = MobileAuthAttempt.objects.get(
            email="test.student@pucsr.edu.kh",
            status=MobileAuthAttempt.Status.SUCCESS,
        )

        self.assertEqual(attempt.student_id, 12345)
        self.assertEqual(attempt.device_id, "test-device-123")
        self.assertEqual(attempt.ip_address, "192.168.1.1")

    def test_cleanup_expired_tokens(self):
        """Test cleanup of expired tokens."""
        # Create expired token
        MobileAuthToken.objects.create(
            user=self.user,
            device_id="expired-device",
            token_id="expired-token-123",
            expires_at=timezone.now() - timedelta(hours=1),
        )

        # Create valid token
        MobileAuthToken.objects.create(
            user=self.user,
            device_id="valid-device",
            token_id="valid-token-123",
            expires_at=timezone.now() + timedelta(hours=1),
        )

        # Cleanup expired tokens
        count = MobileAuthService.cleanup_expired_tokens()

        self.assertEqual(count, 1)

        # Verify only valid token remains
        remaining_tokens = MobileAuthToken.objects.all()
        self.assertEqual(remaining_tokens.count(), 1)
        self.assertEqual(remaining_tokens.first().token_id, "valid-token-123")


class TestMobileUserServiceSecurity(TestCase):
    """Security tests for MobileUserService."""

    def setUp(self):
        """Set up test data."""
        # Create test user
        self.user = User.objects.create_user(email="test.student@pucsr.edu.kh", password="testpassword123")

        # Create test person
        self.person = Person.objects.create(
            user=self.user,
            family_name="Test",
            personal_name="Student",
            school_email="test.student@pucsr.edu.kh",
            phone="012345678",
        )

        # Create test student profile
        self.student_profile = StudentProfile.objects.create(
            person=self.person,
            student_id=12345,
            current_status="ACTIVE",
            enrollment_date=timezone.now().date(),
        )

    def test_get_student_profile_success(self):
        """Test successful student profile retrieval."""
        profile = MobileUserService.get_student_profile(12345)

        self.assertIsNotNone(profile)
        self.assertEqual(profile["student_id"], 12345)
        self.assertEqual(profile["family_name"], "Test")
        self.assertEqual(profile["personal_name"], "Student")
        self.assertEqual(profile["school_email"], "test.student@pucsr.edu.kh")
        self.assertEqual(profile["current_status"], "ACTIVE")

    def test_get_student_profile_not_found(self):
        """Test student profile retrieval with non-existent student ID."""
        profile = MobileUserService.get_student_profile(99999)

        self.assertIsNone(profile)

    def test_get_student_profile_data_privacy(self):
        """Test that student profile doesn't expose sensitive data."""
        profile = MobileUserService.get_student_profile(12345)

        # Verify sensitive fields are not exposed
        sensitive_fields = ["password", "social_security", "birth_certificate"]
        for field in sensitive_fields:
            self.assertNotIn(field, profile)

    def test_get_student_profile_authorization(self):
        """Test that student profile only returns authorized data."""
        profile = MobileUserService.get_student_profile(12345)

        # Verify only authorized fields are returned
        expected_fields = {
            "student_id",
            "person_uuid",
            "family_name",
            "personal_name",
            "full_name",
            "school_email",
            "phone",
            "current_status",
            "enrollment_date",
            "graduation_date",
        }

        profile_fields = set(profile.keys())
        self.assertEqual(profile_fields, expected_fields)
