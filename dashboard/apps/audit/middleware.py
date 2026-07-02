"""
apps.audit — Middleware
Attaches user and IP to request for use by the audit service.
"""
import threading

_local = threading.local()


def get_current_request():
    return getattr(_local, "request", None)


class AuditMiddleware:
    """Store the current request in thread-local for use by services."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _local.request = request
        try:
            return self.get_response(request)
        finally:
            _local.request = None
