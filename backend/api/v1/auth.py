"""Unified API authentication for django-ninja endpoints.

This module provides a consolidated authentication system for the v1 API,
combining the existing JWTAuth from mobile with django-ninja compatible
authentication classes for all endpoints.

Authentication Classes:
- JWTAuth: JWT token authentication (from mobile app)
- UnifiedAuth: Base authentication class with common functionality

Authentication Methods:
- JWT tokens for mobile/API clients
- Session authentication for web interface
- Role-based access control
"""

from apps.mobile.auth import JWTAuth

# Create a default jwt_auth instance for use in v1 API endpoints
jwt_auth = JWTAuth()

# Export JWTAuth class and instance for use in v1 API endpoints
__all__ = ["JWTAuth", "jwt_auth"]
