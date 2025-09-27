"""Security tests for mobile API endpoints.

This module contains comprehensive security tests for:
- API authentication and authorization
- Input validation and sanitization
- Rate limiting and abuse prevention
- Error handling and information disclosure
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.utils import timezone

from apps.mobile.models import MobileAuthAttempt
from apps.mobile.services import MobileAuthService
from apps.people.models import Person, StudentProfile

User = get_user_model()


class TestMobileAPISecurityEndpoints(TestCase):
    """Security tests for mobile API endpoints."""

    def setUp(self):
        """Set up test data and client."""
        self.client = Client()

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

        # Generate valid JWT token for authenticated requests
        self.token_data = MobileAuthService.generate_jwt_token(
            person=self.person,
            student_id=12345,
            email="test.student@pucsr.edu.kh",
            device_id="test-device-123",
        )

        self.valid_token = self.token_data["jwt_token"]

    def test_google_auth_success(self):
        """Test successful Google authentication."""
        mock_idinfo = {
            "iss": "accounts.google.com",
            "email": "test.student@pucsr.edu.kh",
            "name": "Test Student",
            "picture": "https://example.com/picture.jpg",
            "sub": "google-user-id-123",
        }

        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_idinfo

            response = self.client.post(
                "/api/mobile/auth/google",
                {
                    "google_token": "valid-google-token",
                    "email": "test.student@pucsr.edu.kh",
                    "device_id": "test-device-123",
                },
                content_type="application/json",
            )

            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertTrue(data["success"])
            self.assertIn("jwt_token", data)
            self.assertEqual(data["student_id"], 12345)
            self.assertEqual(data["email"], "test.student@pucsr.edu.kh")

    def test_google_auth_invalid_token(self):
        """Test Google authentication with invalid token."""
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.side_effect = ValueError("Invalid token")

            response = self.client.post(
                "/api/mobile/auth/google",
                {
                    "google_token": "invalid-google-token",
                    "email": "test.student@pucsr.edu.kh",
                    "device_id": "test-device-123",
                },
                content_type="application/json",
            )

            self.assertEqual(response.status_code, 401)

            data = response.json()
            self.assertFalse(data["success"])
            self.assertIn("Invalid Google authentication token", data["error"])

    def test_google_auth_invalid_email_domain(self):
        """Test Google authentication with invalid email domain."""
        mock_idinfo = {
            "iss": "accounts.google.com",
            "email": "test.student@gmail.com",  # Invalid domain
            "name": "Test Student",
            "sub": "google-user-id-123",
        }

        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_idinfo

            response = self.client.post(
                "/api/mobile/auth/google",
                {
                    "google_token": "valid-google-token",
                    "email": "test.student@gmail.com",
                    "device_id": "test-device-123",
                },
                content_type="application/json",
            )

            self.assertEqual(response.status_code, 401)

            data = response.json()
            self.assertFalse(data["success"])
            self.assertIn("Invalid Google authentication token", data["error"])

    def test_google_auth_student_not_found(self):
        """Test Google authentication with non-existent student."""
        mock_idinfo = {
            "iss": "accounts.google.com",
            "email": "nonexistent.student@pucsr.edu.kh",
            "name": "Nonexistent Student",
            "sub": "google-user-id-123",
        }

        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_idinfo

            response = self.client.post(
                "/api/mobile/auth/google",
                {
                    "google_token": "valid-google-token",
                    "email": "nonexistent.student@pucsr.edu.kh",
                    "device_id": "test-device-123",
                },
                content_type="application/json",
            )

            self.assertEqual(response.status_code, 400)

            data = response.json()
            self.assertFalse(data["success"])
            self.assertIn("Student profile not found", data["error"])

    def test_google_auth_rate_limiting(self):
        """Test rate limiting for Google authentication."""
        for i in range(6):  # Exceed rate limit
            with patch("apps.mobile.services.MobileAuthService.check_rate_limit") as mock_rate_limit:
                mock_rate_limit.return_value = i >= 5

                response = self.client.post(
                    "/api/mobile/auth/google",
                    {
                        "google_token": "invalid-token",
                        "email": "test.student@pucsr.edu.kh",
                        "device_id": "test-device-123",
                    },
                    content_type="application/json",
                )

                if i >= 5:
                    self.assertEqual(response.status_code, 429)
                    data = response.json()
                    self.assertFalse(data["success"])
                    self.assertIn("Rate limit exceeded", data["error"])

    def test_google_auth_missing_required_fields(self):
        """Test Google authentication with missing required fields."""
        # Missing google_token
        response = self.client.post(
            "/api/mobile/auth/google",
            {"email": "test.student@pucsr.edu.kh", "device_id": "test-device-123"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422)  # Validation error

        # Missing email
        response = self.client.post(
            "/api/mobile/auth/google",
            {"google_token": "valid-google-token", "device_id": "test-device-123"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422)  # Validation error

        # Missing device_id
        response = self.client.post(
            "/api/mobile/auth/google",
            {
                "google_token": "valid-google-token",
                "email": "test.student@pucsr.edu.kh",
            },
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 422)  # Validation error

    def test_google_auth_malformed_json(self):
        """Test Google authentication with malformed JSON."""
        response = self.client.post(
            "/api/mobile/auth/google",
            "invalid-json-data",
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)

    def test_google_auth_sql_injection_attempt(self):
        """Test Google authentication with SQL injection attempt."""
        mock_idinfo = {
            "iss": "accounts.google.com",
            "email": "test.student@pucsr.edu.kh",
            "name": "Test Student",
            "sub": "google-user-id-123",
        }

        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_idinfo

            response = self.client.post(
                "/api/mobile/auth/google",
                {
                    "google_token": "'; DROP TABLE students; --",
                    "email": "test.student@pucsr.edu.kh",
                    "device_id": "test-device-123",
                },
                content_type="application/json",
            )

            # Should handle gracefully without causing SQL injection
            self.assertIn(response.status_code, [400, 401])

    def test_token_validation_success(self):
        """Test successful token validation."""
        response = self.client.post(
            "/api/mobile/auth/validate",
            {"token": self.valid_token},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["valid"])
        self.assertIn("claims", data)
        self.assertEqual(data["claims"]["student_id"], 12345)

    def test_token_validation_invalid_token(self):
        """Test token validation with invalid token."""
        response = self.client.post(
            "/api/mobile/auth/validate",
            {"token": "invalid-jwt-token"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertFalse(data["valid"])
        self.assertIn("error", data)

    def test_token_validation_expired_token(self):
        """Test token validation with expired token."""
        # Create expired token
        from datetime import timedelta

        import jwt

        payload = {
            "sub": "student_12345",
            "email": "test.student@pucsr.edu.kh",
            "student_id": 12345,
            "iss": "naga-sis",
            "aud": "naga-mobile",
            "exp": int((timezone.now() - timedelta(hours=1)).timestamp()),
        }

        expired_token = jwt.encode(payload, "secret-key", algorithm="HS256")

        response = self.client.post(
            "/api/mobile/auth/validate",
            {"token": expired_token},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertFalse(data["valid"])
        self.assertIn("error", data)

    def test_logout_success(self):
        """Test successful logout."""
        response = self.client.post(
            "/api/mobile/auth/logout",
            {},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.valid_token}",
        )

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("Token revoked successfully", data["message"])

    def test_logout_missing_auth_header(self):
        """Test logout without authentication header."""
        response = self.client.post("/api/mobile/auth/logout", {}, content_type="application/json")

        self.assertEqual(response.status_code, 401)

    def test_logout_invalid_token(self):
        """Test logout with invalid token."""
        response = self.client.post(
            "/api/mobile/auth/logout",
            {},
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer invalid-token",
        )

        self.assertEqual(response.status_code, 401)

    def test_get_profile_success(self):
        """Test successful profile retrieval."""
        response = self.client.get("/api/mobile/profile", HTTP_AUTHORIZATION=f"Bearer {self.valid_token}")

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["student_id"], 12345)
        self.assertEqual(data["school_email"], "test.student@pucsr.edu.kh")
        self.assertEqual(data["family_name"], "Test")
        self.assertEqual(data["personal_name"], "Student")

    def test_get_profile_missing_auth_header(self):
        """Test profile retrieval without authentication header."""
        response = self.client.get("/api/mobile/profile")

        self.assertEqual(response.status_code, 401)

    def test_get_profile_invalid_token(self):
        """Test profile retrieval with invalid token."""
        response = self.client.get("/api/mobile/profile", HTTP_AUTHORIZATION="Bearer invalid-token")

        self.assertEqual(response.status_code, 401)

    def test_get_profile_authorization_header_format(self):
        """Test profile retrieval with various authorization header formats."""
        # Missing Bearer prefix
        response = self.client.get("/api/mobile/profile", HTTP_AUTHORIZATION=self.valid_token)

        self.assertEqual(response.status_code, 401)

        # Wrong prefix
        response = self.client.get("/api/mobile/profile", HTTP_AUTHORIZATION=f"Basic {self.valid_token}")

        self.assertEqual(response.status_code, 401)

        # Multiple Bearer prefixes
        response = self.client.get(
            "/api/mobile/profile",
            HTTP_AUTHORIZATION=f"Bearer Bearer {self.valid_token}",
        )

        self.assertEqual(response.status_code, 401)

    def test_health_check_public_access(self):
        """Test health check endpoint public access."""
        response = self.client.get("/api/mobile/health")

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["version"], "1.0.0")

    def test_cors_headers(self):
        """Test CORS headers are set correctly."""
        response = self.client.get("/api/mobile/health")

        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        self.assertIn("GET", response["Access-Control-Allow-Methods"])
        self.assertIn("POST", response["Access-Control-Allow-Methods"])
        self.assertIn("Authorization", response["Access-Control-Allow-Headers"])

    def test_security_headers(self):
        """Test security headers are set correctly."""
        response = self.client.get("/api/mobile/health")

        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-XSS-Protection"], "1; mode=block")
        self.assertEqual(response["Referrer-Policy"], "strict-origin-when-cross-origin")

    def test_request_size_limit(self):
        """Test request size limitation."""
        # Create large request payload
        large_payload = {
            "google_token": "a" * 1000000,  # 1MB token
            "email": "test.student@pucsr.edu.kh",
            "device_id": "test-device-123",
        }

        response = self.client.post("/api/mobile/auth/google", large_payload, content_type="application/json")

        # Should be rejected due to size limit
        self.assertEqual(response.status_code, 413)

    def test_content_type_validation(self):
        """Test content type validation for POST requests."""
        # Test with invalid content type
        response = self.client.post(
            "/api/mobile/auth/google",
            "google_token=test&email=test@pucsr.edu.kh&device_id=test",
            content_type="text/plain",
        )

        self.assertEqual(response.status_code, 400)

    def test_information_disclosure_prevention(self):
        """Test that sensitive information is not disclosed in error messages."""
        # Test with non-existent student
        mock_idinfo = {
            "iss": "accounts.google.com",
            "email": "nonexistent.student@pucsr.edu.kh",
            "name": "Nonexistent Student",
            "sub": "google-user-id-123",
        }

        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_idinfo

            response = self.client.post(
                "/api/mobile/auth/google",
                {
                    "google_token": "valid-google-token",
                    "email": "nonexistent.student@pucsr.edu.kh",
                    "device_id": "test-device-123",
                },
                content_type="application/json",
            )

            data = response.json()

            # Should not reveal internal system information
            self.assertNotIn("database", data["error"].lower())
            self.assertNotIn("sql", data["error"].lower())
            self.assertNotIn("internal", data["error"].lower())
            self.assertNotIn("debug", data["error"].lower())

    def test_authentication_attempt_logging(self):
        """Test that authentication attempts are logged."""
        initial_count = MobileAuthAttempt.objects.count()

        # Make authentication attempt
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.side_effect = ValueError("Invalid token")

            self.client.post(
                "/api/mobile/auth/google",
                {
                    "google_token": "invalid-token",
                    "email": "test.student@pucsr.edu.kh",
                    "device_id": "test-device-123",
                },
                content_type="application/json",
            )

        self.assertEqual(MobileAuthAttempt.objects.count(), initial_count + 1)

        attempt = MobileAuthAttempt.objects.latest("created_at")
        self.assertEqual(attempt.email, "test.student@pucsr.edu.kh")
        self.assertEqual(attempt.status, MobileAuthAttempt.Status.FAILED_INVALID_TOKEN)

    def test_concurrent_authentication_attempts(self):
        """Test handling of concurrent authentication attempts."""
        import threading

        results = []

        def auth_attempt():
            mock_idinfo = {
                "iss": "accounts.google.com",
                "email": "test.student@pucsr.edu.kh",
                "name": "Test Student",
                "sub": "google-user-id-123",
            }

            with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
                mock_verify.return_value = mock_idinfo

                response = self.client.post(
                    "/api/mobile/auth/google",
                    {
                        "google_token": "valid-google-token",
                        "email": "test.student@pucsr.edu.kh",
                        "device_id": f"test-device-{threading.current_thread().ident}",
                    },
                    content_type="application/json",
                )

                results.append(response.status_code)

        # Create multiple threads
        threads = []
        for _i in range(5):
            thread = threading.Thread(target=auth_attempt)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify all requests were handled correctly
        self.assertEqual(len(results), 5)
        self.assertTrue(all(status == 200 for status in results))
