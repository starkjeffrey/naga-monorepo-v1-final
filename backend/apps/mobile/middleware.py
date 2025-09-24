"""Mobile API middleware for authentication and security.

This middleware handles JWT token validation, rate limiting,
and security headers for mobile API endpoints.
"""

import logging

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin

from apps.mobile.services import MobileAuthService

logger = logging.getLogger(__name__)


class MobileAuthMiddleware(MiddlewareMixin):
    """Middleware for mobile API authentication and security.

    This middleware:
    1. Validates JWT tokens for mobile API endpoints
    2. Adds authentication context to requests
    3. Handles authentication errors consistently
    4. Provides security headers
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        """Process incoming request for mobile API authentication."""
        # Only process mobile API endpoints
        if not request.path.startswith("/api/mobile/"):
            return None

        # Skip authentication for certain endpoints
        if self.is_public_endpoint(request.path):
            return None

        # Extract and validate JWT token
        auth_result = self.authenticate_request(request)

        if auth_result["success"]:
            # Add authentication context to request
            request.mobile_auth = auth_result["claims"]
            request.student = auth_result["claims"].get("student_id")
            request.verified_email = auth_result["claims"].get("email")
            return None
        else:
            # Return authentication error
            return self.create_auth_error_response(auth_result["error"])

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Add security headers to mobile API responses."""
        if request.path.startswith("/api/mobile/"):
            # Add security headers
            response["X-Content-Type-Options"] = "nosniff"
            response["X-Frame-Options"] = "DENY"
            response["X-XSS-Protection"] = "1; mode=block"
            response["Referrer-Policy"] = "strict-origin-when-cross-origin"

            # Add CORS headers for mobile apps
            response["Access-Control-Allow-Origin"] = "*"
            response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response["Access-Control-Allow-Headers"] = "Authorization, Content-Type, Accept, X-Requested-With"
            response["Access-Control-Max-Age"] = "86400"

        return response

    def is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public (doesn't require authentication)."""
        public_endpoints = [
            "/api/mobile/auth/google",
            "/api/mobile/auth/validate",
            "/api/mobile/health",
            "/api/mobile/docs",
            "/api/mobile/openapi.json",
        ]

        return any(path.startswith(endpoint) for endpoint in public_endpoints)

    def authenticate_request(self, request: HttpRequest) -> dict:
        """Authenticate request using JWT token."""
        # Extract Authorization header
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")

        if not auth_header:
            return {
                "success": False,
                "error": "Missing authorization header",
                "error_code": "MISSING_AUTH_HEADER",
            }

        if not auth_header.startswith("Bearer "):
            return {
                "success": False,
                "error": "Invalid authorization header format",
                "error_code": "INVALID_AUTH_FORMAT",
            }

        # Extract token
        token = auth_header[7:]  # Remove "Bearer " prefix

        # Validate token
        validation_result = MobileAuthService.validate_jwt_token(token)

        if validation_result["valid"]:
            return {"success": True, "claims": validation_result["claims"]}
        else:
            return {
                "success": False,
                "error": validation_result["error"],
                "error_code": "INVALID_TOKEN",
            }

    def create_auth_error_response(self, error: str) -> JsonResponse:
        """Create consistent authentication error response."""
        return JsonResponse(
            {"success": False, "error": error, "error_code": "AUTHENTICATION_FAILED"},
            status=401,
        )


class MobileRateLimitMiddleware(MiddlewareMixin):
    """Rate limiting middleware for mobile API endpoints.

    Implements rate limiting based on IP address and user
    to prevent abuse of mobile API endpoints.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        """Check rate limits for mobile API requests."""
        # Only process mobile API endpoints
        if not request.path.startswith("/api/mobile/"):
            return None

        # Skip rate limiting for certain endpoints
        if self.is_exempt_endpoint(request.path):
            return None

        # Get client identifier (IP address)
        client_ip = self.get_client_ip(request)

        # Check rate limit
        if MobileAuthService.check_rate_limit(client_ip):
            logger.warning("Rate limit exceeded for IP: %s", client_ip)
            return JsonResponse(
                {
                    "success": False,
                    "error": "Rate limit exceeded. Please try again later.",
                    "error_code": "RATE_LIMITED",
                },
                status=429,
            )

        return None

    def is_exempt_endpoint(self, path: str) -> bool:
        """Check if endpoint is exempt from rate limiting."""
        exempt_endpoints = [
            "/api/mobile/health",
            "/api/mobile/docs",
            "/api/mobile/openapi.json",
        ]

        return any(path.startswith(endpoint) for endpoint in exempt_endpoints)

    def get_client_ip(self, request: HttpRequest) -> str:
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")


class MobileSecurityMiddleware(MiddlewareMixin):
    """Security middleware for mobile API endpoints.

    Implements additional security measures for mobile
    API endpoints including request validation and logging.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_request(self, request: HttpRequest) -> HttpResponse | None:
        """Validate and secure mobile API requests."""
        # Only process mobile API endpoints
        if not request.path.startswith("/api/mobile/"):
            return None

        # Log all mobile API requests for security monitoring
        self.log_api_request(request)

        # Validate request size
        if self.is_request_too_large(request):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Request too large",
                    "error_code": "REQUEST_TOO_LARGE",
                },
                status=413,
            )

        # Validate content type for POST requests
        if request.method == "POST" and not self.is_valid_content_type(request):
            return JsonResponse(
                {
                    "success": False,
                    "error": "Invalid content type",
                    "error_code": "INVALID_CONTENT_TYPE",
                },
                status=400,
            )

        return None

    def log_api_request(self, request: HttpRequest) -> None:
        """Log API request for security monitoring."""
        try:
            client_ip = self.get_client_ip(request)
            user_agent = request.META.get("HTTP_USER_AGENT", "")

            logger.info(
                "Mobile API request: %s %s from %s",
                request.method,
                request.path,
                client_ip,
                extra={
                    "user_agent": user_agent,
                    "content_length": request.META.get("CONTENT_LENGTH", 0),
                    "request_id": getattr(request, "id", None),
                },
            )
        except Exception as e:
            logger.error("Error logging API request: %s", str(e))

    def is_request_too_large(self, request: HttpRequest) -> bool:
        """Check if request is too large."""
        max_size = getattr(settings, "MOBILE_API_MAX_REQUEST_SIZE", 1024 * 1024)  # 1MB default
        content_length = request.META.get("CONTENT_LENGTH")

        if content_length:
            try:
                return int(content_length) > max_size
            except ValueError:
                return False

        return False

    def is_valid_content_type(self, request: HttpRequest) -> bool:
        """Validate content type for POST requests."""
        content_type = request.META.get("CONTENT_TYPE", "")
        valid_types = [
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
        ]

        return any(content_type.startswith(valid_type) for valid_type in valid_types)

    def get_client_ip(self, request: HttpRequest) -> str:
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
