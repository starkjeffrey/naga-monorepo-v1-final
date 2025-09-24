"""Tests for unified v1 API schemas.

Tests shared response schemas, error handling patterns,
and common data structures.
"""

from datetime import datetime

from django.test import TestCase

from api.v1.schemas import (
    COMMON_ERROR_RESPONSES,
    ApiInfoResponse,
    ErrorResponse,
    HealthResponse,
    PaginatedResponse,
    StandardResponse,
    ValidationErrorDetail,
    ValidationErrorResponse,
)


class SchemasTest(TestCase):
    """Test unified API schemas."""

    def test_health_response_schema(self):
        """Test HealthResponse schema validation."""
        # Valid data
        valid_data = {"status": "healthy", "version": "1.0.0", "services": {"database": "healthy", "redis": "healthy"}}

        response = HealthResponse(**valid_data)
        self.assertEqual(response.status, "healthy")
        self.assertEqual(response.version, "1.0.0")
        self.assertIsInstance(response.timestamp, datetime)

    def test_api_info_response_schema(self):
        """Test ApiInfoResponse schema validation."""
        valid_data = {
            "title": "Test API",
            "version": "1.0.0",
            "description": "Test Description",
            "docs_url": "/docs/",
            "contact": {"name": "Test Team"},
        }

        response = ApiInfoResponse(**valid_data)
        self.assertEqual(response.title, "Test API")
        self.assertEqual(response.version, "1.0.0")

    def test_error_response_schema(self):
        """Test ErrorResponse schema validation."""
        valid_data = {"error": "Test error message", "code": "TEST_ERROR", "details": {"field": "value"}}

        response = ErrorResponse(**valid_data)
        self.assertEqual(response.error, "Test error message")
        self.assertEqual(response.code, "TEST_ERROR")
        self.assertIsInstance(response.timestamp, datetime)

    def test_validation_error_response_schema(self):
        """Test ValidationErrorResponse schema validation."""
        error_detail = ValidationErrorDetail(field="email", message="This field is required", code="required")

        response = ValidationErrorResponse(details=[error_detail])
        self.assertEqual(len(response.details), 1)
        self.assertEqual(response.details[0].field, "email")

    def test_standard_response_schema(self):
        """Test StandardResponse schema validation."""
        response = StandardResponse(success=True, message="Operation completed", data={"result": "success"})

        self.assertTrue(response.success)
        self.assertEqual(response.message, "Operation completed")
        self.assertIsInstance(response.timestamp, datetime)

    def test_paginated_response_schema(self):
        """Test PaginatedResponse generic schema."""
        from api.v1.schemas import PaginationMeta

        meta = PaginationMeta(page=1, per_page=10, total=100, pages=10, has_prev=False, has_next=True, next_num=2)

        response = PaginatedResponse(data=["item1", "item2"], meta=meta)

        self.assertEqual(len(response.data), 2)
        self.assertEqual(response.meta.total, 100)
        self.assertTrue(response.success)

    def test_common_error_responses(self):
        """Test common error response definitions."""
        self.assertIn(400, COMMON_ERROR_RESPONSES)
        self.assertIn(401, COMMON_ERROR_RESPONSES)
        self.assertIn(403, COMMON_ERROR_RESPONSES)
        self.assertIn(404, COMMON_ERROR_RESPONSES)
        self.assertIn(500, COMMON_ERROR_RESPONSES)

        # Check structure
        error_400 = COMMON_ERROR_RESPONSES[400]
        self.assertIn("model", error_400)
        self.assertIn("description", error_400)

    def test_schema_serialization(self):
        """Test that schemas can be serialized to dict/JSON."""
        response = HealthResponse(status="healthy", version="1.0.0")

        # Should be serializable
        data = response.model_dump()
        self.assertIn("status", data)
        self.assertIn("version", data)
        self.assertIn("timestamp", data)

    def test_schema_validation_errors(self):
        """Test schema validation with invalid data."""
        from pydantic import ValidationError

        # Missing required field
        with self.assertRaises(ValidationError):
            ErrorResponse()  # Missing 'error' field

        # Invalid type
        with self.assertRaises(ValidationError):
            HealthResponse(status=123)  # Should be string
