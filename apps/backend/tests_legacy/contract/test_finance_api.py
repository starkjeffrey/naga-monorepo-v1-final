"""
Contract/API tests for Finance endpoints.

Tests validate:
- OpenAPI schema compliance
- Response structure and types
- Authentication and authorization
- Error handling
- Business logic constraints
"""

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest
from ninja.testing import TestClient

from api.v1 import api
from apps.people.models import StudentProfile


@pytest.mark.contract
@pytest.mark.finance
class TestFinanceAPIContract:
    """Test Finance API endpoints against contract."""

    @pytest.fixture
    def api_client(self):
        """Create Ninja test client."""
        return TestClient(api)

    @pytest.fixture
    def auth_headers(self, regular_user):
        """Create JWT auth headers."""
        from api.v1.auth import create_jwt_token

        token = create_jwt_token(regular_user)
        return {"Authorization": f"Bearer {token}"}

    @pytest.fixture
    def finance_admin_headers(self, finance_admin):
        """Create finance admin JWT headers."""
        from api.v1.auth import create_jwt_token

        token = create_jwt_token(finance_admin)
        return {"Authorization": f"Bearer {token}"}

    def test_openapi_schema_available(self, api_client):
        """Test OpenAPI schema is available and valid."""
        response = api_client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()

        # Validate schema structure
        assert "openapi" in schema
        assert schema["openapi"].startswith("3.")
        assert "info" in schema
        assert schema["info"]["title"] == "Naga SIS API"
        assert "paths" in schema
        assert "components" in schema

    def test_health_check_endpoint(self, api_client):
        """Test health check endpoint returns expected structure."""
        response = api_client.get("/health/")

        assert response.status_code == 200
        data = response.json()

        # Validate response schema
        assert "status" in data
        assert data["status"] == "healthy"
        assert "version" in data
        assert "services" in data
        assert isinstance(data["services"], dict)

    @pytest.mark.django_db
    def test_get_student_invoices_authentication_required(self, api_client):
        """Test invoice endpoint requires authentication."""
        response = api_client.get("/finance/invoices/student/1/")

        assert response.status_code == 401
        assert "detail" in response.json()

    @pytest.mark.django_db
    def test_get_student_invoices_response_structure(self, api_client, auth_headers, student_user):
        """Test invoice list response structure."""
        with patch("api.v1.finance.StudentProfile.objects.get") as mock_get:
            mock_student = Mock(spec=StudentProfile)
            mock_student.invoices.filter.return_value = []
            mock_get.return_value = mock_student

            response = api_client.get(f"/finance/invoices/student/{student_user.id}/", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            # Validate response structure
            assert isinstance(data, list)

    @pytest.mark.django_db
    def test_create_invoice_validation(self, api_client, finance_admin_headers):
        """Test invoice creation with validation."""
        invalid_payload = {
            "student_id": "invalid",
            "term_id": 1,
            "line_items": [],  # Empty line items
        }

        response = api_client.post("/finance/invoices/", json=invalid_payload, headers=finance_admin_headers)

        assert response.status_code == 422  # Validation error
        error = response.json()
        assert "detail" in error

    @pytest.mark.django_db
    def test_create_invoice_success(self, api_client, finance_admin_headers):
        """Test successful invoice creation."""
        with patch("api.v1.finance.InvoiceService.create_invoice") as mock_create:
            mock_invoice = Mock(
                id=1, invoice_number="INV-2025SP-001", total_amount=Decimal("1000.00"), status="pending"
            )
            mock_create.return_value = mock_invoice

            payload = {"student_id": 1, "term_id": 1, "line_items": [{"description": "Tuition", "amount": "1000.00"}]}

            response = api_client.post("/finance/invoices/", json=payload, headers=finance_admin_headers)

            assert response.status_code == 201
            data = response.json()
            assert "invoice_number" in data
            assert data["invoice_number"] == "INV-2025SP-001"

    @pytest.mark.django_db
    def test_process_payment_validation(self, api_client, finance_admin_headers):
        """Test payment processing validation."""
        # Test negative amount
        payload = {"invoice_id": 1, "amount": "-100.00", "payment_method": "cash"}

        response = api_client.post("/finance/payments/", json=payload, headers=finance_admin_headers)

        assert response.status_code == 422

        # Test invalid payment method
        payload["amount"] = "100.00"
        payload["payment_method"] = "invalid_method"

        response = api_client.post("/finance/payments/", json=payload, headers=finance_admin_headers)

        assert response.status_code == 422

    @pytest.mark.django_db
    def test_process_payment_success(self, api_client, finance_admin_headers):
        """Test successful payment processing."""
        with patch("api.v1.finance.PaymentService.process_payment") as mock_process:
            mock_payment = Mock(
                id=1, reference_number="PAY-20250115-000001", amount=Decimal("500.00"), status="completed"
            )
            mock_process.return_value = mock_payment

            payload = {"invoice_id": 1, "amount": "500.00", "payment_method": "credit_card", "reference": "CC-12345"}

            response = api_client.post("/finance/payments/", json=payload, headers=finance_admin_headers)

            assert response.status_code == 201
            data = response.json()
            assert "reference_number" in data
            assert data["status"] == "completed"

    @pytest.mark.django_db
    def test_get_pricing_tiers(self, api_client, auth_headers):
        """Test pricing tiers endpoint."""
        with patch("api.v1.finance.PricingService.get_pricing_tiers") as mock_tiers:
            mock_tiers.return_value = [
                {"tier": 1, "min_credits": 1, "max_credits": 3, "price_per_credit": "150.00"},
                {"tier": 2, "min_credits": 4, "max_credits": 6, "price_per_credit": "140.00"},
            ]

            response = api_client.get("/finance/pricing/tiers/", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2
            assert all("price_per_credit" in tier for tier in data)

    @pytest.mark.django_db
    def test_calculate_course_price(self, api_client, auth_headers):
        """Test course price calculation endpoint."""
        with patch("api.v1.finance.PricingService.calculate_course_price") as mock_calc:
            mock_calc.return_value = {"base_price": "450.00", "fees": "50.00", "total": "500.00"}

            response = api_client.get("/finance/pricing/course/CS101/", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()
            assert "base_price" in data
            assert "fees" in data
            assert "total" in data
            assert Decimal(data["total"]) == Decimal("500.00")

    @pytest.mark.django_db
    @pytest.mark.parametrize(
        "role,expected_status",
        [
            ("student", 403),  # Forbidden
            ("teacher", 403),  # Forbidden
            ("finance_admin", 200),  # Allowed
            ("admin", 200),  # Allowed
        ],
    )
    def test_administrative_fee_access_control(self, api_client, role, expected_status, create_user):
        """Test administrative fee endpoint access control."""
        from api.v1.auth import create_jwt_token

        user = create_user(username=f"{role}_user")
        if role in ["finance_admin", "admin"]:
            user.is_staff = True
            user.save()

        token = create_jwt_token(user)
        headers = {"Authorization": f"Bearer {token}"}

        with patch("api.v1.finance.AdministrativeFeeConfig.objects.all") as mock_all:
            mock_all.return_value = []

            response = api_client.get("/finance/administrative-fees/", headers=headers)

            assert response.status_code == expected_status

    @pytest.mark.django_db
    def test_error_response_format(self, api_client, auth_headers):
        """Test error response format consistency."""
        # Test 404 error
        response = api_client.get("/finance/invoices/99999/", headers=auth_headers)

        assert response.status_code == 404
        error = response.json()
        assert "detail" in error

        # Test 400 error
        with patch("api.v1.finance.InvoiceService.create_invoice") as mock_create:
            mock_create.side_effect = ValueError("Invalid data")

            response = api_client.post("/finance/invoices/", json={"invalid": "data"}, headers=auth_headers)

            assert response.status_code in [400, 422]
            error = response.json()
            assert "detail" in error

    @pytest.mark.django_db
    def test_pagination_parameters(self, api_client, auth_headers):
        """Test pagination parameters in list endpoints."""
        with patch("api.v1.finance.Invoice.objects.filter") as mock_filter:
            mock_filter.return_value.count.return_value = 50
            mock_filter.return_value.__getitem__.return_value = []

            response = api_client.get("/finance/invoices/?page=1&page_size=10", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            # Check for pagination metadata
            if isinstance(data, dict):
                assert "results" in data
                assert "count" in data
                assert "next" in data or "previous" in data

    @pytest.mark.django_db
    def test_date_filtering(self, api_client, finance_admin_headers):
        """Test date range filtering in endpoints."""
        with patch("api.v1.finance.Payment.objects.filter") as mock_filter:
            mock_filter.return_value = []

            response = api_client.get(
                "/finance/payments/?from_date=2025-01-01&to_date=2025-01-31", headers=finance_admin_headers
            )

            assert response.status_code == 200

            # Verify filter was called with date parameters
            mock_filter.assert_called()

    @pytest.mark.django_db
    def test_decimal_precision_in_responses(self, api_client, auth_headers):
        """Test decimal values maintain precision in API responses."""
        with patch("api.v1.finance.Invoice.objects.get") as mock_get:
            mock_invoice = Mock(
                total_amount=Decimal("1234.56"), paid_amount=Decimal("789.01"), balance=Decimal("445.55")
            )
            mock_get.return_value = mock_invoice

            response = api_client.get("/finance/invoices/1/", headers=auth_headers)

            assert response.status_code == 200
            data = response.json()

            # Verify decimal precision is maintained
            assert data["total_amount"] == "1234.56"
            assert data["paid_amount"] == "789.01"
            assert data["balance"] == "445.55"


@pytest.mark.contract
class TestOpenAPIValidation:
    """Validate API responses against OpenAPI schema."""

    @pytest.fixture
    def openapi_schema(self, api_client):
        """Load OpenAPI schema."""
        response = api_client.get("/openapi.json")
        return response.json()

    def test_all_endpoints_documented(self, openapi_schema):
        """Test all API endpoints are documented in OpenAPI."""
        paths = openapi_schema.get("paths", {})

        # Finance endpoints that should be documented
        expected_endpoints = [
            "/api/v1/finance/invoices/",
            "/api/v1/finance/payments/",
            "/api/v1/finance/pricing/tiers/",
            "/api/v1/finance/administrative-fees/",
        ]

        for endpoint in expected_endpoints:
            assert any(endpoint in path for path in paths), f"{endpoint} not documented"

    def test_response_schemas_defined(self, openapi_schema):
        """Test response schemas are defined for all endpoints."""
        paths = openapi_schema.get("paths", {})
        openapi_schema.get("components", {}).get("schemas", {})

        for path, methods in paths.items():
            for method, operation in methods.items():
                if method in ["get", "post", "put", "patch", "delete"]:
                    responses = operation.get("responses", {})

                    # Check success response has schema
                    success_codes = ["200", "201"]
                    has_success_schema = False

                    for code in success_codes:
                        if code in responses:
                            response = responses[code]
                            if "content" in response:
                                content = response["content"]
                                if "application/json" in content:
                                    has_success_schema = "schema" in content["application/json"]

                    assert has_success_schema or method == "delete", f"{method.upper()} {path} missing response schema"

    def test_authentication_documented(self, openapi_schema):
        """Test authentication is properly documented."""
        security_schemes = openapi_schema.get("components", {}).get("securitySchemes", {})

        # Should have JWT bearer authentication defined
        assert "bearerAuth" in security_schemes or "JWT" in security_schemes

        # Check endpoints have security requirements
        paths = openapi_schema.get("paths", {})
        secured_endpoints = 0

        for _path, methods in paths.items():
            for _method, operation in methods.items():
                if "security" in operation:
                    secured_endpoints += 1

        assert secured_endpoints > 0, "No endpoints have security requirements"
