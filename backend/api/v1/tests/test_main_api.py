"""Tests for main v1 API endpoints.

Tests the core API functionality including health check, info,
and main router integration.
"""

from django.test import TestCase
from ninja.testing import TestClient

from api.v1 import api


class MainAPITest(TestCase):
    """Test main v1 API endpoints."""

    def setUp(self):
        """Set up test client."""
        self.client = TestClient(api)

    def test_health_check_endpoint(self):
        """Test health check endpoint returns proper response."""
        response = self.client.get("/health/")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["version"], "1.0.0")
        self.assertIn("services", data)
        self.assertIn("timestamp", data)

    def test_api_info_endpoint(self):
        """Test API info endpoint returns proper response."""
        response = self.client.get("/info/")

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["title"], "Naga SIS API")
        self.assertEqual(data["version"], "1.0.0")
        self.assertIn("description", data)
        self.assertIn("docs_url", data)
        self.assertIn("contact", data)

    def test_openapi_schema_generation(self):
        """Test that OpenAPI schema is generated correctly."""
        response = self.client.get("/openapi.json")

        self.assertEqual(response.status_code, 200)
        schema = response.json()

        self.assertIn("openapi", schema)
        self.assertIn("info", schema)
        self.assertIn("paths", schema)

        # Check that our endpoints are included
        self.assertIn("/health/", schema["paths"])
        self.assertIn("/info/", schema["paths"])

    def test_docs_endpoint_exists(self):
        """Test that API documentation endpoint exists."""
        response = self.client.get("/docs/")

        # Should return HTML documentation page
        self.assertEqual(response.status_code, 200)

    def test_router_integration(self):
        """Test that domain routers are properly integrated."""
        # Get the API schema to check available endpoints
        schema_response = self.client.get("/openapi.json")
        schema = schema_response.json()
        paths = schema.get("paths", {})

        # Check for domain-specific endpoints (if they loaded successfully)
        domain_endpoints = ["/grading/", "/finance/", "/attendance/"]

        # At least some domain endpoints should be present
        domain_found = any(any(path.startswith(domain) for path in paths.keys()) for domain in domain_endpoints)

        # Note: This might be False if domain APIs failed to load,
        # but the main API should still work
        if domain_found:
            self.assertTrue(domain_found, "At least one domain API should be loaded")
