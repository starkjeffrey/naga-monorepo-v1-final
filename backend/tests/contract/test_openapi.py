"""
Test OpenAPI schema generation and validation.
"""

import json

import pytest


@pytest.mark.contract
class TestOpenAPISchema:
    """Test OpenAPI schema generation and validity."""

    def test_openapi_schema_accessible(self, django_client):
        """Test that OpenAPI schema endpoint is accessible."""
        response = django_client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        assert response["Content-Type"] == "application/json"

    def test_openapi_schema_valid_json(self, django_client):
        """Test that OpenAPI schema returns valid JSON."""
        response = django_client.get("/api/v1/openapi.json")

        try:
            schema = json.loads(response.content)
        except json.JSONDecodeError:
            pytest.fail("OpenAPI schema is not valid JSON")

        assert isinstance(schema, dict)

    def test_openapi_schema_structure(self, django_client):
        """Test that OpenAPI schema has required structure."""
        response = django_client.get("/api/v1/openapi.json")
        schema = json.loads(response.content)

        # Check required OpenAPI 3.0 fields
        assert "openapi" in schema
        assert schema["openapi"].startswith("3.")
        assert "info" in schema
        assert "paths" in schema

        # Check info section
        info = schema["info"]
        assert "title" in info
        assert "version" in info

        # Check paths exist
        assert isinstance(schema["paths"], dict)
        assert len(schema["paths"]) > 0

    def test_api_endpoints_documented(self, django_client):
        """Test that main API endpoints are documented in schema."""
        response = django_client.get("/api/v1/openapi.json")
        schema = json.loads(response.content)
        paths = schema["paths"]

        # Check that key endpoints are documented
        expected_endpoint_patterns = ["/api/v1/auth", "/api/v1/finance", "/api/v1/attendance", "/api/v1/grading"]

        documented_paths = list(paths.keys())

        for pattern in expected_endpoint_patterns:
            matching_paths = [path for path in documented_paths if path.startswith(pattern)]
            assert len(matching_paths) > 0, f"No endpoints found for pattern: {pattern}"

    def test_schema_components_defined(self, django_client):
        """Test that schema components are properly defined."""
        response = django_client.get("/api/v1/openapi.json")
        schema = json.loads(response.content)

        if "components" in schema:
            components = schema["components"]

            # Check schemas are defined
            if "schemas" in components:
                schemas = components["schemas"]
                assert isinstance(schemas, dict)

                # Check for common model schemas
                expected_schemas = ["Student", "Teacher", "Course", "Enrollment", "Invoice", "Payment", "Term"]

                for expected_schema in expected_schemas:
                    # Use case-insensitive matching since schema names might vary
                    schema_names = [name.lower() for name in schemas.keys()]
                    assert any(expected_schema.lower() in name for name in schema_names), (
                        f"Schema for {expected_schema} not found"
                    )

    @pytest.mark.parametrize(
        "endpoint",
        ["/api/v1/auth/login", "/api/v1/auth/logout", "/api/v1/finance/invoices", "/api/v1/attendance/sessions"],
    )
    def test_endpoint_methods_documented(self, django_client, endpoint):
        """Test that endpoints have proper HTTP methods documented."""
        response = django_client.get("/api/v1/openapi.json")
        schema = json.loads(response.content)
        paths = schema["paths"]

        # Find matching path (might have path parameters)
        matching_path = None
        for path in paths:
            if endpoint in path or path in endpoint:
                matching_path = path
                break

        if matching_path:
            endpoint_spec = paths[matching_path]
            assert isinstance(endpoint_spec, dict)

            # Check that at least one HTTP method is documented
            http_methods = ["get", "post", "put", "patch", "delete"]
            documented_methods = [method for method in http_methods if method in endpoint_spec]
            assert len(documented_methods) > 0, f"No HTTP methods documented for {matching_path}"

            # Check that each method has required fields
            for method in documented_methods:
                method_spec = endpoint_spec[method]
                assert "responses" in method_spec, f"No responses defined for {method} {matching_path}"

    def test_security_schemes_defined(self, django_client):
        """Test that security schemes are properly defined."""
        response = django_client.get("/api/v1/openapi.json")
        schema = json.loads(response.content)

        # Check if security is defined at root level or components level
        has_security = False

        if "security" in schema:
            has_security = True

        if "components" in schema and "securitySchemes" in schema["components"]:
            has_security = True
            security_schemes = schema["components"]["securitySchemes"]
            assert isinstance(security_schemes, dict)
            assert len(security_schemes) > 0

        # For an API, we expect some form of security to be defined
        assert has_security, "No security schemes defined in API"
