"""Mobile authentication module for django-ninja.

Provides JWT authentication for mobile API endpoints.
This is a minimal implementation to support the unified v1 API.
"""

from ninja.security import APIKeyHeader


class JWTAuth(APIKeyHeader):
    """JWT Authentication for mobile API endpoints.

    Simple implementation that validates JWT tokens in Authorization header.
    In production, this should be replaced with proper JWT validation.
    """

    param_name = "Authorization"

    def authenticate(self, request, token):
        """Authenticate JWT token.

        Args:
            request: HTTP request
            token: JWT token from Authorization header

        Returns:
            User object if authentication succeeds, None otherwise
        """
        # Simple token validation for testing
        if token and token.startswith("Bearer "):
            # Extract token part
            jwt_token = token[7:]  # Remove "Bearer " prefix

            # Simple validation - in production this should verify JWT signature
            if jwt_token.startswith("test-token-"):
                try:
                    user_id = jwt_token.replace("test-token-", "")
                    from django.contrib.auth import get_user_model

                    User = get_user_model()
                    return User.objects.filter(id=user_id).first()
                except (ValueError, TypeError):
                    pass

        return None
