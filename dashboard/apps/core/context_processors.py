"""
apps.core — Template Context Processors
Inject global EKAFY context into all templates.
"""
from django.conf import settings


def ekafy_context(request):
    """Inject platform-level context into every template."""
    return {
        "EKAFY_VERSION": "1.0.0",
        "EKAFY_BASE_DIR": settings.EKAFY_BASE_DIR,
        "APP_NAME": "EKAFY",
        "APP_TAGLINE": "VPS Application Management Platform",
    }
