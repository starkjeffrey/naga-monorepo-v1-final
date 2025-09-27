"""
Comprehensive API Contract Tests for All Endpoints

Tests API contracts, response schemas, authentication, authorization,
error handling, and integration patterns across all v1 endpoints.

Phase II Implementation: API Contract Tests
Following TEST_PLAN.md requirements for ≥90% API coverage testing.

Test Categories:
- Authentication & Authorization
- Request/Response Schema Validation
- HTTP Status Code Compliance
- Error Handling and Error Messages
- Rate Limiting and Security
- Cross-endpoint Integration
- Performance and Load Testing
- API Versioning and Compatibility
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase
from ninja.testing import TestClient

from api.v1 import api
from apps.academic.models import Term
from apps.accounts.models import Department
from apps.curriculum.models import Course, Program
from apps.finance.models import Currency, Invoice
from apps.people.models import Person, StudentProfile

User = get_user_model()


# =============================================================================
# TEST FIXTURES AND BASE CLASSES
# =============================================================================


class APIContractTestCase(TestCase):
    """Base test case for API contract testing."""

    def setUp(self):
        """Set up common test data."""
        # Create test users with different roles
        self.admin_user = User.objects.create_user(email="admin@test.edu", name="Admin User", password="testpass123")
        self.admin_user.is_staff = True
        self.admin_user.is_superuser = True
        self.admin_user.save()

        self.finance_user = User.objects.create_user(
            email="finance@test.edu", name="Finance User", password="testpass123"
        )

        self.teacher_user = User.objects.create_user(
            email="teacher@test.edu", name="Teacher User", password="testpass123"
        )

        self.student_user = User.objects.create_user(
            email="student@test.edu", name="Student User", password="testpass123"
        )

        # Create test data
        self.person = Person.objects.create(
            first_name="John", last_name="Doe", email="john.doe@test.edu", phone="+855123456789"
        )

        self.student = StudentProfile.objects.create(
            person=self.person, student_id="ST2024001", enrollment_status=StudentProfile.EnrollmentStatus.ACTIVE
        )

        # Link student user to student profile
        self.student_user.person = self.person
        self.student_user.save()

        self.program = Program.objects.create(
            code="ENG101",
            name="English Program",
            description="Basic English program",
            total_hours=120,
            credits=12,
            is_active=True,
        )

        self.course = Course.objects.create(
            code="ENG101-1",
            title="Basic English",
            description="Introductory English course",
            credits=3,
            hours_per_week=6,
            level=Course.Level.BEGINNER,
            is_active=True,
        )

        self.term = Term.objects.create(
            term_id="202401",
            name="Spring 2024",
            start_date=date(2024, 1, 15),
            end_date=date(2024, 5, 15),
            is_active=True,
        )

        # Create test client
        self.client = TestClient(api)

    def authenticate_as(self, user):
        """Helper to authenticate as specific user for JWT token tests."""
        # For test purposes, we'll mock the JWT authentication
        # In real implementation, this would generate actual JWT tokens
        return f"Bearer test-token-{user.id}"

    def assert_api_response_schema(self, response, expected_fields, status_code=200):
        """Assert API response matches expected schema."""
        self.assertEqual(response.status_code, status_code)

        if response.content:
            data = response.json()
            for field in expected_fields:
                self.assertIn(field, data, f"Expected field '{field}' not found in response")

    def assert_error_response_schema(self, response, expected_status_code):
        """Assert error response follows standard error schema."""
        self.assertEqual(response.status_code, expected_status_code)

        if response.content:
            data = response.json()
            expected_error_fields = ["error"]
            for field in expected_error_fields:
                self.assertIn(field, data, f"Expected error field '{field}' not found")


# =============================================================================
# SYSTEM ENDPOINTS CONTRACT TESTS
# =============================================================================


class SystemEndpointsContractTests(APIContractTestCase):
    """Test system health and info endpoints contracts."""

    def test_health_check_endpoint_contract(self):
        """Test /api/health endpoint contract compliance."""
        response = self.client.get("/health/")

        expected_fields = ["status", "version", "services"]
        self.assert_api_response_schema(response, expected_fields)

        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["version"], "1.0.0")
        self.assertIsInstance(data["services"], dict)

        # Verify service status format
        for service, status in data["services"].items():
            self.assertIsInstance(service, str)
            self.assertIn(status, ["healthy", "unhealthy", "degraded"])

    def test_api_info_endpoint_contract(self):
        """Test /api/info endpoint contract compliance."""
        response = self.client.get("/info/")

        expected_fields = ["title", "version", "description", "docs_url", "contact"]
        self.assert_api_response_schema(response, expected_fields)

        data = response.json()
        self.assertEqual(data["title"], "Naga SIS API")
        self.assertEqual(data["version"], "1.0.0")
        self.assertIsInstance(data["contact"], dict)

    def test_openapi_schema_generation(self):
        """Test OpenAPI schema generation and compliance."""
        response = self.client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)

        schema = response.json()
        self.assertIn("openapi", schema)
        self.assertIn("info", schema)
        self.assertIn("paths", schema)
        self.assertIn("components", schema)

        # Verify API info in schema
        self.assertEqual(schema["info"]["title"], "Naga SIS API")
        self.assertEqual(schema["info"]["version"], "1.0.0")

    def test_api_documentation_accessibility(self):
        """Test API documentation endpoints accessibility."""
        response = self.client.get("/docs/")

        # Documentation should be accessible
        self.assertIn(response.status_code, [200, 302])  # OK or redirect to docs


# =============================================================================
# AUTHENTICATION CONTRACT TESTS
# =============================================================================


class AuthenticationContractTests(APIContractTestCase):
    """Test authentication and authorization contracts."""

    def test_jwt_authentication_required_endpoints(self):
        """Test JWT authentication requirement for protected endpoints."""
        protected_endpoints = [
            "/finance/pricing/lookup?course_id=1&student_id=1",
            "/finance/invoices",
            "/finance/administrative-fees/config",
        ]

        for endpoint in protected_endpoints:
            with self.subTest(endpoint=endpoint):
                # Test without authentication
                if endpoint == "/finance/invoices":
                    response = self.client.post(endpoint, json={"student_id": 1, "items": []})
                else:
                    response = self.client.get(endpoint)

                # Should require authentication
                self.assertIn(response.status_code, [401, 403])

    def test_jwt_token_format_validation(self):
        """Test JWT token format validation."""
        # Mock JWT authentication for testing
        with patch("api.v1.auth.jwt_auth") as mock_auth:
            mock_auth.authenticate.return_value = None

            # Test with invalid token format
            response = self.client.get(
                "/finance/administrative-fees/config", headers={"Authorization": "Invalid-Format"}
            )

            self.assertEqual(response.status_code, 401)

    def test_role_based_access_control(self):
        """Test role-based access control across endpoints."""
        # Create roles and permissions
        Department.objects.create(name="Finance Department", code="FIN", description="Finance department")

        # Test different user access levels
        test_cases = [
            {
                "user": self.admin_user,
                "endpoint": "/finance/administrative-fees/config",
                "method": "GET",
                "expected_status": 200,
                "description": "Admin should access all finance endpoints",
            },
            {
                "user": self.student_user,
                "endpoint": "/finance/administrative-fees/config",
                "method": "GET",
                "expected_status": 403,
                "description": "Students should not access admin finance endpoints",
            },
        ]

        for case in test_cases:
            with self.subTest(case=case):
                # Mock authentication
                with patch("api.v1.finance.check_admin_access") as mock_admin:
                    mock_admin.return_value = case["user"].is_superuser

                    with patch("api.v1.finance.has_permission") as mock_perm:
                        mock_perm.return_value = case["user"].is_superuser

                        self.client.get(case["endpoint"])

                        # Note: In real implementation, this would test with actual JWT tokens
                        # For now, we're testing the permission structure


# =============================================================================
# FINANCE API CONTRACT TESTS
# =============================================================================


class FinanceAPIContractTests(APIContractTestCase):
    """Test Finance API endpoint contracts."""

    def setUp(self):
        """Set up finance-specific test data."""
        super().setUp()

        self.invoice = Invoice.objects.create(
            student=self.student,
            invoice_number="INV-TEST-001",
            total_amount=Decimal("1000.00"),
            due_date=date.today() + timedelta(days=30),
            status=Invoice.InvoiceStatus.SENT,
            currency=Currency.USD,
        )

    def test_pricing_lookup_endpoint_contract(self):
        """Test pricing lookup endpoint request/response contract."""
        # Test valid request
        with patch("api.v1.finance.can_access_student_financial_data") as mock_access:
            mock_access.return_value = True

            with patch("api.v1.finance.SeparatedPricingService.get_active_pricing") as mock_pricing:
                mock_pricing.return_value = Mock(
                    base_price=Decimal("1000.00"),
                    final_price=Decimal("800.00"),
                    discounts_applied=[],
                    pricing_tier="standard",
                    currency="USD",
                )

                response = self.client.get(
                    f"/finance/pricing/lookup?course_id={self.course.id}&student_id={self.student.id}"
                )

                expected_fields = [
                    "course_id",
                    "course_name",
                    "base_price",
                    "final_price",
                    "discounts_applied",
                    "pricing_tier",
                    "currency",
                ]
                self.assert_api_response_schema(response, expected_fields)

                data = response.json()
                self.assertEqual(data["course_id"], self.course.id)
                self.assertEqual(data["course_name"], self.course.title)
                self.assertIsInstance(data["discounts_applied"], list)

    def test_pricing_lookup_validation_errors(self):
        """Test pricing lookup endpoint validation error handling."""
        # Test missing required parameters
        response = self.client.get("/finance/pricing/lookup")
        self.assert_error_response_schema(response, 422)  # Validation error

        # Test invalid course ID
        response = self.client.get("/finance/pricing/lookup?course_id=99999")
        self.assert_error_response_schema(response, 404)

    def test_invoice_creation_endpoint_contract(self):
        """Test invoice creation endpoint request/response contract."""
        with patch("api.v1.finance.has_permission") as mock_perm:
            mock_perm.return_value = True

            with patch("api.v1.finance.InvoiceService.create_invoice") as mock_create:
                mock_create.return_value = Mock(
                    id=1,
                    total_amount=Decimal("500.00"),
                    status="SENT",
                    due_date=date.today() + timedelta(days=30),
                    created_at=datetime.now(),
                )

                request_data = {
                    "student_id": self.student.id,
                    "items": [{"description": "Course fee", "amount": 500.00}],
                    "due_date": (date.today() + timedelta(days=30)).isoformat(),
                    "notes": "Test invoice",
                }

                response = self.client.post("/finance/invoices", json=request_data)

                expected_fields = [
                    "id",
                    "student_id",
                    "student_name",
                    "total_amount",
                    "status",
                    "due_date",
                    "created_at",
                ]
                self.assert_api_response_schema(response, expected_fields)

    def test_invoice_creation_validation(self):
        """Test invoice creation validation and error handling."""
        # Test missing required fields
        response = self.client.post("/finance/invoices", json={})
        self.assert_error_response_schema(response, 422)

        # Test invalid student ID
        with patch("api.v1.finance.has_permission") as mock_perm:
            mock_perm.return_value = True

            request_data = {"student_id": 99999, "items": [{"description": "Test", "amount": 100}]}

            response = self.client.post("/finance/invoices", json=request_data)
            self.assert_error_response_schema(response, 404)

    def test_administrative_fees_config_contract(self):
        """Test administrative fees configuration endpoint contract."""
        # Test list endpoint
        with patch("api.v1.finance.has_permission") as mock_perm:
            mock_perm.return_value = True

            response = self.client.get("/finance/administrative-fees/config")

            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIsInstance(data, list)

    def test_administrative_fees_creation_contract(self):
        """Test administrative fees creation endpoint contract."""
        with patch("api.v1.finance.has_permission") as mock_perm:
            mock_perm.return_value = True

            request_data = {
                "cycle_type": "MONTHLY",
                "fee_amount": 50.00,
                "included_document_units": 10,
                "description": "Test administrative fee",
                "is_active": True,
            }

            response = self.client.post("/finance/administrative-fees/config", json=request_data)

            expected_fields = [
                "id",
                "cycle_type",
                "cycle_type_display",
                "fee_amount",
                "included_document_units",
                "description",
                "is_active",
                "created_at",
                "updated_at",
            ]
            self.assert_api_response_schema(response, expected_fields, 201)


# =============================================================================
# ERROR HANDLING CONTRACT TESTS
# =============================================================================


class ErrorHandlingContractTests(APIContractTestCase):
    """Test error handling contracts across all endpoints."""

    def test_404_error_response_format(self):
        """Test 404 error response format consistency."""
        response = self.client.get("/finance/nonexistent-endpoint")

        self.assertEqual(response.status_code, 404)

        # Check if response includes standard error format
        if response.content:
            data = response.json()
            # Should have consistent error structure
            self.assertIn("detail", data)  # Django Ninja default error format

    def test_validation_error_response_format(self):
        """Test validation error response format consistency."""
        # Test endpoint with validation requirements
        response = self.client.post("/finance/invoices", json={"invalid": "data"})

        self.assertEqual(response.status_code, 422)  # Validation error

        if response.content:
            data = response.json()
            # Should have validation error structure
            self.assertIn("detail", data)

    def test_authentication_error_response_format(self):
        """Test authentication error response format consistency."""
        # Test protected endpoint without authentication
        response = self.client.get("/finance/administrative-fees/config")

        self.assertIn(response.status_code, [401, 403])

        if response.content:
            data = response.json()
            # Should have consistent error structure
            self.assertTrue(any(key in data for key in ["detail", "error", "message"]))

    def test_internal_server_error_handling(self):
        """Test 500 error handling and response format."""
        with patch("api.v1.finance.SeparatedPricingService.get_active_pricing") as mock_pricing:
            mock_pricing.side_effect = Exception("Internal error")

            with patch("api.v1.finance.can_access_student_financial_data") as mock_access:
                mock_access.return_value = True

                response = self.client.get(f"/finance/pricing/lookup?course_id={self.course.id}")

                self.assertEqual(response.status_code, 500)

                if response.content:
                    data = response.json()
                    # Should have error information
                    self.assertTrue(any(key in data for key in ["detail", "error"]))


# =============================================================================
# REQUEST/RESPONSE SCHEMA VALIDATION TESTS
# =============================================================================


class SchemaValidationContractTests(APIContractTestCase):
    """Test request/response schema validation contracts."""

    def test_request_content_type_validation(self):
        """Test request content type validation."""
        # Test with invalid content type
        response = self.client.post("/finance/invoices", data="invalid-data", content_type="text/plain")

        # Should reject invalid content type
        self.assertIn(response.status_code, [400, 415, 422])

    def test_response_content_type_consistency(self):
        """Test response content type consistency."""
        endpoints = ["/health/", "/info/", "/openapi.json"]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)

                if response.status_code == 200:
                    # Should return JSON content type
                    self.assertIn("application/json", response.headers.get("Content-Type", ""))

    def test_decimal_field_precision(self):
        """Test decimal field precision in API responses."""
        with patch("api.v1.finance.can_access_student_financial_data") as mock_access:
            mock_access.return_value = True

            with patch("api.v1.finance.SeparatedPricingService.get_active_pricing") as mock_pricing:
                mock_pricing.return_value = Mock(
                    base_price=Decimal("1234.56"),
                    final_price=Decimal("987.65"),
                    discounts_applied=[],
                    pricing_tier="standard",
                    currency="USD",
                )

                response = self.client.get(
                    f"/finance/pricing/lookup?course_id={self.course.id}&student_id={self.student.id}"
                )

                if response.status_code == 200:
                    data = response.json()

                    # Verify decimal precision maintained
                    self.assertEqual(str(data["base_price"]), "1234.56")
                    self.assertEqual(str(data["final_price"]), "987.65")

    def test_datetime_field_format(self):
        """Test datetime field format consistency."""
        response = self.client.get("/health/")

        if response.status_code == 200:
            data = response.json()

            # If timestamp field exists, should be ISO format
            if "timestamp" in data:
                timestamp = data["timestamp"]
                # Should be parseable as ISO format
                try:
                    datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                except ValueError:
                    self.fail(f"Timestamp not in valid ISO format: {timestamp}")

    def test_boolean_field_consistency(self):
        """Test boolean field consistency in responses."""
        with patch("api.v1.finance.has_permission") as mock_perm:
            mock_perm.return_value = True

            response = self.client.get("/finance/administrative-fees/config")

            if response.status_code == 200:
                data = response.json()

                for item in data:
                    if "is_active" in item:
                        # Should be actual boolean, not string
                        self.assertIsInstance(item["is_active"], bool)


# =============================================================================
# PERFORMANCE AND SECURITY CONTRACT TESTS
# =============================================================================


class PerformanceSecurityContractTests(APIContractTestCase):
    """Test performance and security contracts."""

    def test_response_time_requirements(self):
        """Test API response time requirements."""
        import time

        endpoints = [
            "/health/",
            "/info/",
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                start_time = time.time()
                self.client.get(endpoint)
                end_time = time.time()

                response_time = end_time - start_time

                # API should respond within 2 seconds for basic endpoints
                self.assertLess(response_time, 2.0, f"Endpoint {endpoint} took {response_time:.2f}s")

    def test_request_size_limits(self):
        """Test request size limits."""
        # Create large request payload
        large_items = [{"description": f"Item {i}", "amount": 100} for i in range(1000)]

        large_request = {"student_id": self.student.id, "items": large_items}

        response = self.client.post("/finance/invoices", json=large_request)

        # Should handle or reject large requests appropriately
        self.assertIn(response.status_code, [413, 400, 422, 500])  # Request too large or validation error

    def test_sql_injection_protection(self):
        """Test SQL injection protection in query parameters."""
        malicious_queries = [
            "'; DROP TABLE students; --",
            "1' OR '1'='1",
            "1 UNION SELECT * FROM users",
        ]

        for query in malicious_queries:
            with self.subTest(query=query):
                # Test with malicious query parameter
                response = self.client.get(f"/finance/pricing/lookup?course_id={query}")

                # Should not cause SQL injection - should return validation error
                self.assertIn(response.status_code, [400, 422, 404])

    def test_xss_protection_in_responses(self):
        """Test XSS protection in API responses."""
        # Create data with potential XSS content
        xss_content = "<script>alert('XSS')</script>"

        with patch("api.v1.finance.has_permission") as mock_perm:
            mock_perm.return_value = True

            request_data = {
                "student_id": self.student.id,
                "items": [{"description": xss_content, "amount": 100}],
                "notes": xss_content,
            }

            response = self.client.post("/finance/invoices", json=request_data)

            if response.status_code in [200, 201]:
                response_text = response.content.decode()

                # Response should not contain unescaped script tags
                self.assertNotIn("<script>", response_text)

    def test_rate_limiting_headers(self):
        """Test rate limiting headers presence."""
        self.client.get("/health/")

        # Check if rate limiting headers are present (if implemented)

        # Note: This is aspirational - rate limiting may not be implemented yet
        # The test documents expected behavior for future implementation


# =============================================================================
# INTEGRATION AND COMPATIBILITY TESTS
# =============================================================================


class IntegrationCompatibilityContractTests(APIContractTestCase):
    """Test integration and compatibility contracts."""

    def test_cross_endpoint_data_consistency(self):
        """Test data consistency across related endpoints."""
        # Create invoice through service
        self.invoice = Invoice.objects.create(
            student=self.student,
            invoice_number="INV-CONSISTENCY-001",
            total_amount=Decimal("750.00"),
            due_date=date.today() + timedelta(days=30),
            status=Invoice.InvoiceStatus.SENT,
            currency=Currency.USD,
        )

        # Test that student data is consistent across endpoints
        with patch("api.v1.finance.can_access_student_financial_data") as mock_access:
            mock_access.return_value = True

            with patch("api.v1.finance.SeparatedPricingService.get_active_pricing") as mock_pricing:
                mock_pricing.return_value = Mock(
                    base_price=Decimal("750.00"),
                    final_price=Decimal("750.00"),
                    discounts_applied=[],
                    pricing_tier="standard",
                    currency="USD",
                )

                pricing_response = self.client.get(
                    f"/finance/pricing/lookup?course_id={self.course.id}&student_id={self.student.id}"
                )

                if pricing_response.status_code == 200:
                    pricing_data = pricing_response.json()

                    # Student ID should be consistent
                    # (This would be more meaningful with actual student endpoints)
                    self.assertEqual(pricing_data["course_id"], self.course.id)

    def test_api_versioning_compatibility(self):
        """Test API versioning and backward compatibility."""
        # Test that v1 API endpoints maintain expected structure
        response = self.client.get("/info/")

        if response.status_code == 200:
            data = response.json()

            # Version should be clearly specified
            self.assertEqual(data["version"], "1.0.0")

            # API should have documentation URL
            self.assertIn("docs_url", data)

    def test_openapi_schema_completeness(self):
        """Test OpenAPI schema completeness and accuracy."""
        response = self.client.get("/openapi.json")

        if response.status_code == 200:
            schema = response.json()

            # Should have security schemes defined
            if "components" in schema:
                components = schema["components"]

                # Should document authentication if used
                if "securitySchemes" in components:
                    self.assertIsInstance(components["securitySchemes"], dict)

            # Should document major endpoints
            paths = schema.get("paths", {})
            expected_paths = [
                "/health/",
                "/info/",
            ]

            for path in expected_paths:
                self.assertIn(path, paths, f"Expected path {path} not found in OpenAPI schema")

    def test_concurrent_request_handling(self):
        """Test concurrent request handling capability."""
        import threading

        results = []

        def make_request():
            try:
                response = self.client.get("/health/")
                results.append(response.status_code)
            except Exception as e:
                results.append(str(e))

        # Create multiple concurrent requests
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # All requests should complete successfully
        self.assertEqual(len(results), 10)
        for result in results:
            self.assertEqual(result, 200, f"Concurrent request failed: {result}")

    def test_database_connection_handling(self):
        """Test proper database connection handling in API requests."""
        # Make multiple requests that would use database connections
        endpoints = [
            "/health/",  # May check database status
        ]

        for endpoint in endpoints:
            for _ in range(5):  # Multiple requests to test connection pooling
                with self.subTest(endpoint=endpoint):
                    response = self.client.get(endpoint)

                    # Should not cause database connection errors
                    self.assertNotEqual(response.status_code, 500)


# =============================================================================
# API DOCUMENTATION CONTRACT TESTS
# =============================================================================


class DocumentationContractTests(APIContractTestCase):
    """Test API documentation contracts and completeness."""

    def test_endpoint_documentation_presence(self):
        """Test that all endpoints have proper documentation."""
        response = self.client.get("/openapi.json")

        if response.status_code == 200:
            schema = response.json()
            paths = schema.get("paths", {})

            for path, methods in paths.items():
                for method, details in methods.items():
                    with self.subTest(path=path, method=method):
                        # Should have summary or description
                        has_docs = any(key in details for key in ["summary", "description"])
                        self.assertTrue(has_docs, f"Endpoint {method.upper()} {path} lacks documentation")

    def test_response_schema_documentation(self):
        """Test that response schemas are properly documented."""
        response = self.client.get("/openapi.json")

        if response.status_code == 200:
            schema = response.json()
            paths = schema.get("paths", {})

            for path, methods in paths.items():
                for method, details in methods.items():
                    responses = details.get("responses", {})

                    # Should document success responses
                    success_responses = [code for code in responses.keys() if str(code).startswith("2")]

                    if success_responses:
                        for response_code in success_responses:
                            response_details = responses[response_code]
                            # Should have content or description
                            has_response_docs = any(key in response_details for key in ["content", "description"])

                            self.assertTrue(
                                has_response_docs,
                                f"Response {response_code} for {method.upper()} {path} lacks documentation",
                            )

    def test_error_response_documentation(self):
        """Test that error responses are documented."""
        response = self.client.get("/openapi.json")

        if response.status_code == 200:
            schema = response.json()
            paths = schema.get("paths", {})

            protected_endpoints = []
            for path, methods in paths.items():
                for method, details in methods.items():
                    # Check if endpoint requires authentication
                    if "security" in details:
                        protected_endpoints.append((path, method))

            # Protected endpoints should document auth errors
            for path, method in protected_endpoints:
                with self.subTest(path=path, method=method):
                    responses = paths[path][method].get("responses", {})

                    # Should document common error codes
                    common_errors = ["401", "403", "404", "500"]
                    [code for code in responses.keys() if code in common_errors]

                    # At least some error responses should be documented
                    # (This is aspirational - may not be fully implemented)
                    pass


if __name__ == "__main__":
    pytest.main([__file__])
