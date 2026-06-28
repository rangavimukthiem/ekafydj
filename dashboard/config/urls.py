"""
EKAFY — Root URL Configuration
"""
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include

urlpatterns = [
    # Admin
    path("django-admin/", admin.site.urls),

    # Two-Factor Auth
    path("account/", include("two_factor.urls")),

    # Dashboard (main app root)
    path("", include("apps.projects.urls")),

    # Modules (clean separated routing)
    path("deployments/", include("apps.deployments.urls")),
    path("services/", include("apps.services.urls")),
    path("logs/", include("apps.logs.urls")),
    path("backups/", include("apps.backups.urls")),
    path("monitoring/", include("apps.monitoring.urls")),
    path("users/", include("apps.users.urls")),
    path("audit/", include("apps.audit.urls")),

    # REST API
    path("api/v1/", include("api.router")),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    try:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
