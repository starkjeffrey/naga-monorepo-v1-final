"""Request-related utility functions.

This module provides utilities for working with Django requests,
including accessing the current request from anywhere in the code.
"""

import threading

_thread_locals = threading.local()


def get_current_request():
    """Get the current request object from thread-local storage.

    This requires the CurrentRequestMiddleware to be installed.

    Returns:
        HttpRequest: The current request, or None if not in a request context
    """
    return getattr(_thread_locals, "request", None)


def set_current_request(request):
    """Set the current request in thread-local storage.

    This is called by CurrentRequestMiddleware.

    Args:
        request: The HttpRequest object
    """
    _thread_locals.request = request


def clear_current_request():
    """Clear the current request from thread-local storage.

    This is called by CurrentRequestMiddleware at the end of a request.
    """
    if hasattr(_thread_locals, "request"):
        del _thread_locals.request


class CurrentRequestMiddleware:
    """Middleware that stores the current request in thread-local storage.

    This allows accessing the request from anywhere in the code,
    which is useful for request-scoped caching.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        set_current_request(request)
        try:
            response = self.get_response(request)
        finally:
            clear_current_request()
        return response
