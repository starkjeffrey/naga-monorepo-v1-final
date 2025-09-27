"""Enhanced security middleware for Staff-Web V2 system."""

import json
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from django.http import HttpRequest, JsonResponse
from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.models import AnonymousUser
from django.utils.deprecation import MiddlewareMixin
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string

logger = logging.getLogger(__name__)


class RateLimitMiddleware(MiddlewareMixin):
    """Rate limiting middleware with user-specific and IP-based limits."""

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.rate_limits = {
            # API endpoints - requests per minute
            'api': {'authenticated': 300, 'anonymous': 60},
            'auth': {'authenticated': 30, 'anonymous': 10},
            'upload': {'authenticated': 20, 'anonymous': 5},
            'search': {'authenticated': 120, 'anonymous': 30},
            'websocket': {'authenticated': 100, 'anonymous': 10},
        }

    def process_request(self, request: HttpRequest) -> Optional[JsonResponse]:
        """Process incoming request for rate limiting."""
        # Skip rate limiting for certain paths
        if self._should_skip_rate_limit(request):
            return None

        # Determine rate limit category
        category = self._get_rate_limit_category(request)

        # Get user identifier (authenticated user ID or IP)
        identifier = self._get_user_identifier(request)

        # Check rate limit
        if self._is_rate_limited(request, category, identifier):
            return self._rate_limit_response(request, category)

        return None

    def _should_skip_rate_limit(self, request: HttpRequest) -> bool:
        """Check if rate limiting should be skipped."""
        skip_paths = [
            '/admin/',
            '/silk/',
            '/static/',
            '/media/',
            '/health/',
            '/favicon.ico',
        ]
        return any(request.path.startswith(path) for path in skip_paths)

    def _get_rate_limit_category(self, request: HttpRequest) -> str:
        """Determine rate limit category based on request path."""
        path = request.path.lower()

        if path.startswith('/api/v2/') or path.startswith('/api/v1/'):
            if 'auth' in path or 'login' in path:
                return 'auth'
            elif 'upload' in path or request.method == 'POST' and 'files' in request.content_type:
                return 'upload'
            elif 'search' in path or request.GET.get('search'):
                return 'search'
            return 'api'
        elif path.startswith('/ws/'):
            return 'websocket'
        else:
            return 'api'  # Default category

    def _get_user_identifier(self, request: HttpRequest) -> str:
        """Get unique identifier for rate limiting."""
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"user_{request.user.id}"
        else:
            # Use IP address for anonymous users
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR', 'unknown')
            return f"ip_{ip}"

    def _is_rate_limited(self, request: HttpRequest, category: str, identifier: str) -> bool:
        """Check if request exceeds rate limit."""
        is_authenticated = hasattr(request, 'user') and request.user.is_authenticated
        user_type = 'authenticated' if is_authenticated else 'anonymous'

        limit = self.rate_limits.get(category, {}).get(user_type, 60)

        # Create cache key
        cache_key = f"rate_limit:{category}:{identifier}"

        # Get current count
        current_count = cache.get(cache_key, 0)

        if current_count >= limit:
            return True

        # Increment counter
        cache.set(cache_key, current_count + 1, 60)  # 1-minute window

        return False

    def _rate_limit_response(self, request: HttpRequest, category: str) -> JsonResponse:
        """Return rate limit exceeded response."""
        logger.warning(
            "Rate limit exceeded for %s on %s category",
            self._get_user_identifier(request),
            category
        )

        return JsonResponse({
            'error': 'Rate limit exceeded',
            'category': category,
            'retry_after': 60,
            'timestamp': datetime.now().isoformat()
        }, status=429)


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add comprehensive security headers."""

    def process_response(self, request: HttpRequest, response):
        """Add security headers to response."""
        # Content Security Policy
        csp_directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "style-src 'self' 'unsafe-inline'",
            "img-src 'self' data: blob:",
            "font-src 'self'",
            "connect-src 'self' ws: wss:",
            "frame-src 'none'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
        ]
        response['Content-Security-Policy'] = '; '.join(csp_directives)

        # Additional security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'

        # HSTS for HTTPS
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

        return response


class APISecurityMiddleware(MiddlewareMixin):
    """Enhanced API security with authentication verification."""

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.protected_paths = [
            '/api/v2/',
            '/ws/v2/',
        ]
        self.public_paths = [
            '/api/v2/health/',
            '/api/v2/info/',
            '/api/v1/auth/login/',
            '/api/v2/auth/login/',
        ]

    def process_request(self, request: HttpRequest) -> Optional[JsonResponse]:
        """Process API security checks."""
        # Skip non-API requests
        if not self._is_protected_path(request):
            return None

        # Allow public endpoints
        if self._is_public_path(request):
            return None

        # Verify authentication
        if not self._is_authenticated(request):
            return self._authentication_required_response()

        # Log API access
        self._log_api_access(request)

        return None

    def _is_protected_path(self, request: HttpRequest) -> bool:
        """Check if path requires protection."""
        return any(request.path.startswith(path) for path in self.protected_paths)

    def _is_public_path(self, request: HttpRequest) -> bool:
        """Check if path is public."""
        return any(request.path.startswith(path) for path in self.public_paths)

    def _is_authenticated(self, request: HttpRequest) -> bool:
        """Check if request is properly authenticated."""
        # Check for JWT token in Authorization header
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if auth_header and auth_header.startswith('Bearer '):
            # JWT validation would happen in the API auth layer
            return True

        # Check for session authentication
        if hasattr(request, 'user') and request.user.is_authenticated:
            return True

        return False

    def _authentication_required_response(self) -> JsonResponse:
        """Return authentication required response."""
        return JsonResponse({
            'error': 'Authentication required',
            'message': 'Valid authentication credentials are required for this endpoint',
            'timestamp': datetime.now().isoformat()
        }, status=401)

    def _log_api_access(self, request: HttpRequest):
        """Log API access for security monitoring."""
        logger.info(
            "API access: %s %s by user %s from %s",
            request.method,
            request.path,
            getattr(request.user, 'id', 'anonymous'),
            request.META.get('REMOTE_ADDR', 'unknown')
        )


class CSRFEnhancementMiddleware(MiddlewareMixin):
    """Enhanced CSRF protection with additional validation."""

    def process_request(self, request: HttpRequest) -> Optional[JsonResponse]:
        """Enhanced CSRF validation."""
        # Skip for API endpoints that use JWT
        if request.path.startswith('/api/') and 'Bearer' in request.META.get('HTTP_AUTHORIZATION', ''):
            return None

        # Enhanced CSRF check for sensitive operations
        if self._requires_enhanced_csrf(request):
            if not self._validate_enhanced_csrf(request):
                return JsonResponse({
                    'error': 'CSRF validation failed',
                    'message': 'Enhanced CSRF protection requires additional validation',
                    'timestamp': datetime.now().isoformat()
                }, status=403)

        return None

    def _requires_enhanced_csrf(self, request: HttpRequest) -> bool:
        """Check if request requires enhanced CSRF protection."""
        sensitive_operations = [
            'delete',
            'upload',
            'admin',
            'financial',
            'grade',
            'bulk',
        ]

        path_lower = request.path.lower()
        return (
            request.method in ['POST', 'PUT', 'DELETE', 'PATCH'] and
            any(op in path_lower for op in sensitive_operations)
        )

    def _validate_enhanced_csrf(self, request: HttpRequest) -> bool:
        """Validate enhanced CSRF token."""
        # Check for custom CSRF header
        custom_csrf = request.META.get('HTTP_X_CSRFTOKEN')
        django_csrf = request.META.get('HTTP_X_CSRFTOKEN')

        # Basic validation - in production, implement more sophisticated checks
        return bool(custom_csrf or django_csrf)


class AuditLogMiddleware(MiddlewareMixin):
    """Audit logging middleware for security monitoring."""

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.sensitive_operations = [
            'login',
            'logout',
            'password',
            'delete',
            'admin',
            'grade',
            'financial',
            'student',
            'bulk',
        ]

    def process_request(self, request: HttpRequest):
        """Log request start time."""
        request._audit_start_time = time.time()

    def process_response(self, request: HttpRequest, response):
        """Log completed requests for audit trail."""
        if self._should_audit(request):
            self._create_audit_log(request, response)

        return response

    def _should_audit(self, request: HttpRequest) -> bool:
        """Determine if request should be audited."""
        path_lower = request.path.lower()

        # Audit API endpoints
        if request.path.startswith('/api/'):
            return True

        # Audit sensitive operations
        if any(op in path_lower for op in self.sensitive_operations):
            return True

        # Audit failed requests
        if hasattr(request, '_response_status') and request._response_status >= 400:
            return True

        return False

    def _create_audit_log(self, request: HttpRequest, response):
        """Create audit log entry."""
        duration = time.time() - getattr(request, '_audit_start_time', time.time())

        audit_data = {
            'timestamp': datetime.now().isoformat(),
            'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            'method': request.method,
            'path': request.path,
            'status_code': response.status_code,
            'duration_ms': round(duration * 1000, 2),
            'ip_address': request.META.get('REMOTE_ADDR'),
            'user_agent': request.META.get('HTTP_USER_AGENT', '')[:200],
            'query_params': dict(request.GET) if request.GET else None,
        }

        # Log sensitive operations with higher priority
        if any(op in request.path.lower() for op in self.sensitive_operations):
            logger.warning("Sensitive operation audit: %s", json.dumps(audit_data))
        else:
            logger.info("API audit: %s", json.dumps(audit_data))


class BlockedIPMiddleware(MiddlewareMixin):
    """Block requests from known malicious IPs."""

    def __init__(self, get_response=None):
        super().__init__(get_response)
        self.blocked_ips = self._load_blocked_ips()

    def process_request(self, request: HttpRequest) -> Optional[JsonResponse]:
        """Check if IP is blocked."""
        client_ip = self._get_client_ip(request)

        if client_ip in self.blocked_ips:
            logger.warning("Blocked IP attempted access: %s", client_ip)
            return JsonResponse({
                'error': 'Access denied',
                'message': 'Your IP address has been blocked',
                'timestamp': datetime.now().isoformat()
            }, status=403)

        return None

    def _get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', 'unknown')

    def _load_blocked_ips(self) -> set:
        """Load blocked IPs from cache or configuration."""
        blocked_ips = cache.get('blocked_ips', set())

        # Add any configured blocked IPs
        if hasattr(settings, 'BLOCKED_IPS'):
            blocked_ips.update(settings.BLOCKED_IPS)

        return blocked_ips