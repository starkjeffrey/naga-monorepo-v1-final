"""Integration tests for complete OAuth authentication flow.

This module contains end-to-end integration tests that verify:
- Complete Google OAuth to JWT token flow
- Frontend-backend integration
- Database persistence and retrieval
- Security across the entire authentication pipeline
"""

from datetime import timedelta
from unittest.mock import patch

from django.test import TransactionTestCase
from django.test.client import Client
from django.utils import timezone

from apps.mobile.models import MobileAuthAttempt, MobileAuthToken
from apps.mobile.services import MobileAuthService
from apps.people.models import Person, StudentProfile
from users.models import User


class TestMobileAuthIntegration(TransactionTestCase):
    """Integration tests for complete mobile authentication flow."""

    def setUp(self):
        """Set up test data for integration tests."""
        self.client = Client()

        # Create test user
        self.user = User.objects.create_user(email="integration.test@pucsr.edu.kh", password="testpassword123")

        # Create test person
        self.person = Person.objects.create(
            user=self.user,
            family_name="Integration",
            personal_name="Test",
            school_email="integration.test@pucsr.edu.kh",
            phone="012345678",
        )

        # Create test student profile
        self.student_profile = StudentProfile.objects.create(
            person=self.person,
            student_id=99999,
            current_status="ACTIVE",
            enrollment_date=timezone.now().date(),
        )

        # Mock Google OAuth data
        self.mock_google_idinfo = {
            "iss": "accounts.google.com",
            "email": "integration.test@pucsr.edu.kh",
            "name": "Integration Test",
            "picture": "https://example.com/picture.jpg",
            "sub": "google-user-id-integration",
        }

        self.valid_auth_request = {
            "google_token": "valid-google-token",
            "email": "integration.test@pucsr.edu.kh",
            "device_id": "integration-test-device",
        }

    def test_complete_authentication_flow(self):
        """Test complete end-to-end authentication flow."""
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = self.mock_google_idinfo

            # Step 1: Initial authentication request
            response = self.client.post(
                "/api/mobile/auth/google",
                self.valid_auth_request,
                content_type="application/json",
            )

            # Verify authentication response
            self.assertEqual(response.status_code, 200)

            auth_data = response.json()
            self.assertTrue(auth_data["success"])
            self.assertIn("jwt_token", auth_data)
            self.assertEqual(auth_data["student_id"], 99999)
            self.assertEqual(auth_data["email"], "integration.test@pucsr.edu.kh")

            jwt_token = auth_data["jwt_token"]

            # Step 2: Verify token is stored in database
            auth_token = MobileAuthToken.objects.get(user=self.user)
            self.assertEqual(auth_token.device_id, "integration-test-device")
            self.assertFalse(auth_token.revoked)

            # Step 3: Verify authentication attempt is logged
            attempt = MobileAuthAttempt.objects.get(
                email="integration.test@pucsr.edu.kh",
                status=MobileAuthAttempt.Status.SUCCESS,
            )
            self.assertEqual(attempt.student_id, 99999)
            self.assertEqual(attempt.device_id, "integration-test-device")

            # Step 4: Use JWT token to access protected endpoint
            profile_response = self.client.get("/api/mobile/profile", HTTP_AUTHORIZATION=f"Bearer {jwt_token}")

            self.assertEqual(profile_response.status_code, 200)

            profile_data = profile_response.json()
            self.assertEqual(profile_data["student_id"], 99999)
            self.assertEqual(profile_data["school_email"], "integration.test@pucsr.edu.kh")
            self.assertEqual(profile_data["family_name"], "Integration")
            self.assertEqual(profile_data["personal_name"], "Test")

            # Step 5: Validate token using validation endpoint
            validation_response = self.client.post(
                "/api/mobile/auth/validate",
                {"token": jwt_token},
                content_type="application/json",
            )

            self.assertEqual(validation_response.status_code, 200)

            validation_data = validation_response.json()
            self.assertTrue(validation_data["valid"])
            self.assertEqual(validation_data["claims"]["student_id"], 99999)

            # Step 6: Logout and verify token is revoked
            logout_response = self.client.post(
                "/api/mobile/auth/logout",
                {},
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {jwt_token}",
            )

            self.assertEqual(logout_response.status_code, 200)

            logout_data = logout_response.json()
            self.assertTrue(logout_data["success"])

            # Step 7: Verify token is marked as revoked
            auth_token.refresh_from_db()
            self.assertTrue(auth_token.revoked)

            # Step 8: Verify revoked token cannot access protected endpoints
            protected_response = self.client.get("/api/mobile/profile", HTTP_AUTHORIZATION=f"Bearer {jwt_token}")

            self.assertEqual(protected_response.status_code, 401)

    def test_authentication_flow_with_invalid_google_token(self):
        """Test authentication flow with invalid Google token."""
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.side_effect = ValueError("Invalid token")

            response = self.client.post(
                "/api/mobile/auth/google",
                self.valid_auth_request,
                content_type="application/json",
            )

            self.assertEqual(response.status_code, 401)

            auth_data = response.json()
            self.assertFalse(auth_data["success"])
            self.assertIn("Invalid Google authentication token", auth_data["error"])

            attempt = MobileAuthAttempt.objects.get(
                email="integration.test@pucsr.edu.kh",
                status=MobileAuthAttempt.Status.FAILED_INVALID_TOKEN,
            )
            self.assertEqual(attempt.device_id, "integration-test-device")

            # Verify no auth token is created
            self.assertFalse(MobileAuthToken.objects.filter(user=self.user).exists())

    def test_authentication_flow_with_nonexistent_student(self):
        """Test authentication flow with non-existent student."""
        nonexistent_email = "nonexistent.student@pucsr.edu.kh"

        mock_google_idinfo = {
            "iss": "accounts.google.com",
            "email": nonexistent_email,
            "name": "Nonexistent Student",
            "sub": "google-user-id-nonexistent",
        }

        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = mock_google_idinfo

            response = self.client.post(
                "/api/mobile/auth/google",
                {
                    "google_token": "valid-google-token",
                    "email": nonexistent_email,
                    "device_id": "test-device",
                },
                content_type="application/json",
            )

            self.assertEqual(response.status_code, 400)

            auth_data = response.json()
            self.assertFalse(auth_data["success"])
            self.assertIn("Student profile not found", auth_data["error"])

            attempt = MobileAuthAttempt.objects.get(
                email=nonexistent_email,
                status=MobileAuthAttempt.Status.FAILED_STUDENT_NOT_FOUND,
            )
            self.assertEqual(attempt.device_id, "test-device")

    def test_concurrent_authentication_attempts(self):
        """Test handling of concurrent authentication attempts."""
        import threading

        results = []
        errors = []

        def auth_attempt(device_suffix):
            try:
                with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
                    mock_verify.return_value = self.mock_google_idinfo

                    response = self.client.post(
                        "/api/mobile/auth/google",
                        {
                            "google_token": "valid-google-token",
                            "email": "integration.test@pucsr.edu.kh",
                            "device_id": f"concurrent-device-{device_suffix}",
                        },
                        content_type="application/json",
                    )

                    results.append(
                        {
                            "status_code": response.status_code,
                            "device_suffix": device_suffix,
                            "data": response.json(),
                        },
                    )
            except Exception as e:
                errors.append(str(e))

        # Create 5 concurrent authentication attempts
        threads = []
        for i in range(5):
            thread = threading.Thread(target=auth_attempt, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        self.assertEqual(len(results), 5)
        self.assertEqual(len(errors), 0)

        successful_results = [r for r in results if r["status_code"] == 200]
        self.assertEqual(len(successful_results), 5)

        # Verify all tokens are different
        tokens = [r["data"]["jwt_token"] for r in successful_results]
        self.assertEqual(len(set(tokens)), 5)  # All tokens should be unique

        # Verify all tokens are stored in database
        auth_tokens = MobileAuthToken.objects.filter(user=self.user)
        self.assertEqual(auth_tokens.count(), 5)

    def test_token_expiration_handling(self):
        """Test handling of expired tokens."""
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = self.mock_google_idinfo

            # Step 1: Authenticate and get token
            response = self.client.post(
                "/api/mobile/auth/google",
                self.valid_auth_request,
                content_type="application/json",
            )

            auth_data = response.json()
            jwt_token = auth_data["jwt_token"]

            # Step 2: Manually expire the token in database
            auth_token = MobileAuthToken.objects.get(user=self.user)
            auth_token.expires_at = timezone.now() - timedelta(hours=1)
            auth_token.save()

            # Step 3: Try to use expired token
            profile_response = self.client.get("/api/mobile/profile", HTTP_AUTHORIZATION=f"Bearer {jwt_token}")

            # Should be rejected due to expired token
            self.assertEqual(profile_response.status_code, 401)

            # Step 4: Verify token validation endpoint reports expired
            validation_response = self.client.post(
                "/api/mobile/auth/validate",
                {"token": jwt_token},
                content_type="application/json",
            )

            validation_data = validation_response.json()
            self.assertFalse(validation_data["valid"])
            self.assertIn("expired", validation_data["error"].lower())

    def test_rate_limiting_integration(self):
        """Test rate limiting across multiple requests."""
        with patch("apps.mobile.services.MobileAuthService.RATE_LIMIT_ATTEMPTS", 3):
            with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
                mock_verify.side_effect = ValueError("Invalid token")

                for _ in range(3):
                    response = self.client.post(
                        "/api/mobile/auth/google",
                        {
                            "google_token": "invalid-token",
                            "email": "integration.test@pucsr.edu.kh",
                            "device_id": "rate-limit-test",
                        },
                        content_type="application/json",
                        HTTP_X_FORWARDED_FOR="192.168.1.100",
                    )

                    self.assertEqual(response.status_code, 401)

                response = self.client.post(
                    "/api/mobile/auth/google",
                    {
                        "google_token": "invalid-token",
                        "email": "integration.test@pucsr.edu.kh",
                        "device_id": "rate-limit-test",
                    },
                    content_type="application/json",
                    HTTP_X_FORWARDED_FOR="192.168.1.100",
                )

                self.assertEqual(response.status_code, 429)

                rate_limit_data = response.json()
                self.assertFalse(rate_limit_data["success"])
                self.assertIn("Rate limit exceeded", rate_limit_data["error"])

                attempt = MobileAuthAttempt.objects.get(
                    email="integration.test@pucsr.edu.kh",
                    status=MobileAuthAttempt.Status.FAILED_RATE_LIMITED,
                )
                self.assertEqual(attempt.device_id, "rate-limit-test")

    def test_security_headers_integration(self):
        """Test that security headers are properly set."""
        response = self.client.get("/api/mobile/health")

        # Verify security headers
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertEqual(response["X-XSS-Protection"], "1; mode=block")
        self.assertEqual(response["Referrer-Policy"], "strict-origin-when-cross-origin")

        # Verify CORS headers
        self.assertEqual(response["Access-Control-Allow-Origin"], "*")
        self.assertIn("Authorization", response["Access-Control-Allow-Headers"])

    def test_user_person_relationship_integration(self):
        """Test that User-Person relationship works correctly."""
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = self.mock_google_idinfo

            # Authenticate
            response = self.client.post(
                "/api/mobile/auth/google",
                self.valid_auth_request,
                content_type="application/json",
            )

            auth_data = response.json()
            # jwt_token is available in auth_data if needed

            # Verify User-Person relationship
            self.assertEqual(self.person.user, self.user)
            self.assertEqual(self.user.person, self.person)

            # Verify student profile access through relationship
            self.assertEqual(self.user.person.student_profile, self.student_profile)
            self.assertEqual(self.student_profile.person.user, self.user)

            # Verify JWT token contains correct person UUID
            self.assertEqual(auth_data["person_uuid"], str(self.person.unique_id))

    def test_database_transaction_integrity(self):
        """Test database transaction integrity during authentication."""
        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = self.mock_google_idinfo

            # Mock database error during token creation
            with patch("apps.mobile.models.MobileAuthToken.objects.create") as mock_create:
                mock_create.side_effect = Exception("Database error")

                # Authentication should fail gracefully
                response = self.client.post(
                    "/api/mobile/auth/google",
                    self.valid_auth_request,
                    content_type="application/json",
                )

                # Should handle error gracefully
                self.assertIn(response.status_code, [400, 500])

                # Verify no partial data is left in database
                self.assertEqual(MobileAuthToken.objects.filter(user=self.user).count(), 0)

    def test_cleanup_expired_tokens_integration(self):
        """Test cleanup of expired tokens."""
        # Create expired tokens
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

        # Run cleanup
        cleaned_count = MobileAuthService.cleanup_expired_tokens()

        self.assertEqual(cleaned_count, 1)

        # Verify only valid token remains
        remaining_tokens = MobileAuthToken.objects.filter(user=self.user)
        self.assertEqual(remaining_tokens.count(), 1)
        self.assertEqual(remaining_tokens.first().token_id, "valid-token-123")

    def test_multiple_device_authentication(self):
        """Test authentication from multiple devices for same user."""
        devices = ["mobile-phone", "tablet", "laptop"]
        tokens = []

        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = self.mock_google_idinfo

            # Authenticate from multiple devices
            for device in devices:
                response = self.client.post(
                    "/api/mobile/auth/google",
                    {
                        "google_token": "valid-google-token",
                        "email": "integration.test@pucsr.edu.kh",
                        "device_id": device,
                    },
                    content_type="application/json",
                )

                self.assertEqual(response.status_code, 200)
                auth_data = response.json()
                tokens.append(auth_data["jwt_token"])

            # Verify all tokens are unique
            self.assertEqual(len(set(tokens)), 3)

            # Verify all tokens work for API access
            for token in tokens:
                profile_response = self.client.get("/api/mobile/profile", HTTP_AUTHORIZATION=f"Bearer {token}")
                self.assertEqual(profile_response.status_code, 200)

            # Verify all tokens are stored in database
            auth_tokens = MobileAuthToken.objects.filter(user=self.user)
            self.assertEqual(auth_tokens.count(), 3)

            device_ids = list(auth_tokens.values_list("device_id", flat=True))
            self.assertEqual(set(device_ids), set(devices))

    def test_revoke_all_user_tokens_integration(self):
        """Test revoking all tokens for a user."""
        devices = ["device1", "device2", "device3"]
        tokens = []

        with patch("google.oauth2.id_token.verify_oauth2_token") as mock_verify:
            mock_verify.return_value = self.mock_google_idinfo

            # Create multiple tokens
            for device in devices:
                response = self.client.post(
                    "/api/mobile/auth/google",
                    {
                        "google_token": "valid-google-token",
                        "email": "integration.test@pucsr.edu.kh",
                        "device_id": device,
                    },
                    content_type="application/json",
                )

                auth_data = response.json()
                tokens.append(auth_data["jwt_token"])

            # Revoke all tokens
            revoked_count = MobileAuthService.revoke_all_user_tokens("integration.test@pucsr.edu.kh")
            self.assertEqual(revoked_count, 3)

            # Verify all tokens are revoked
            for token in tokens:
                profile_response = self.client.get("/api/mobile/profile", HTTP_AUTHORIZATION=f"Bearer {token}")
                self.assertEqual(profile_response.status_code, 401)

            # Verify all tokens are marked as revoked in database
            revoked_tokens = MobileAuthToken.objects.filter(user=self.user, revoked=True)
            self.assertEqual(revoked_tokens.count(), 3)


class TestMobileAuthErrorScenarios(TransactionTestCase):
    """Test error scenarios and edge cases."""

    def test_malformed_requests(self):
        """Test handling of malformed requests."""
        client = Client()

        # Test with invalid JSON
        response = client.post("/api/mobile/auth/google", "invalid-json", content_type="application/json")
        self.assertEqual(response.status_code, 400)

        # Test with missing fields
        response = client.post(
            "/api/mobile/auth/google",
            {"google_token": "test"},
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 422)

        # Test with empty request body
        response = client.post("/api/mobile/auth/google", {}, content_type="application/json")
        self.assertEqual(response.status_code, 422)

    def test_unsupported_methods(self):
        """Test unsupported HTTP methods."""
        client = Client()

        # Test GET on auth endpoint
        response = client.get("/api/mobile/auth/google")
        self.assertEqual(response.status_code, 405)

        # Test PUT on auth endpoint
        response = client.put("/api/mobile/auth/google")
        self.assertEqual(response.status_code, 405)

        # Test DELETE on auth endpoint
        response = client.delete("/api/mobile/auth/google")
        self.assertEqual(response.status_code, 405)

    def test_large_request_handling(self):
        """Test handling of large requests."""
        client = Client()

        # Create large request payload
        large_payload = {
            "google_token": "a" * 100000,  # Very large token
            "email": "test@pucsr.edu.kh",
            "device_id": "test-device",
        }

        response = client.post("/api/mobile/auth/google", large_payload, content_type="application/json")

        # Should handle large requests gracefully
        self.assertIn(response.status_code, [400, 413, 422])
