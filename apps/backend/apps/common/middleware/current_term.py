"""Current term caching middleware.

This middleware caches all active terms in the request object to avoid
repeated database queries. Handles multiple concurrent terms (ENG_A, ENG_B, BA, MA).
"""

from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin

from apps.curriculum.services import TermService


class CurrentTermMiddleware(MiddlewareMixin):
    """Middleware that adds all active terms to the request object.

    This avoids repeated database queries when checking if requirements
    or overrides are currently effective. The system typically has 4 active
    terms at any given time (ENG_A, ENG_B, BA, MA).
    """

    def process_request(self, request):
        """Add all active terms to request object with Redis caching."""
        # Cache all active terms
        cache_key_all = "active_terms_all"
        active_terms = cache.get(cache_key_all)

        if active_terms is None:
            # Not in cache, fetch from database
            active_terms = TermService.get_all_active_terms()
            # Cache for 5 minutes (terms don't change often)
            cache.set(cache_key_all, active_terms, 300)

        # Cache active terms by type for easy access
        cache_key_by_type = "active_terms_by_type"
        active_terms_by_type = cache.get(cache_key_by_type)

        if active_terms_by_type is None:
            active_terms_by_type = TermService.get_active_terms_by_type()
            cache.set(cache_key_by_type, active_terms_by_type, 300)

        # Add to request for use throughout the request lifecycle
        request.active_terms = active_terms  # List of all active terms
        request.active_terms_by_type = active_terms_by_type  # Dict by term type

        # Keep backward compatibility - set current_term to first active term
        request.current_term = active_terms[0] if active_terms else None

        return None


def get_current_term_from_request():
    """Get the current term from the request context.

    This helper function should be used in models and services
    to access the cached current term instead of hitting the database.

    Returns:
        Term: The current term, or None if not in a request context
    """
    from django.core.exceptions import ImproperlyConfigured

    try:
        from apps.common.utils import get_current_request

        request = get_current_request()
        if request and hasattr(request, "current_term"):
            return request.current_term
    except (ImportError, ImproperlyConfigured):
        pass

    # Fallback to database query if not in request context
    return TermService.get_current_term()
