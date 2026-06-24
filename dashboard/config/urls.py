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
    path("account/", include("two_factor.urls", namespace="two_factor")),

    # Dashboard (main app)
    path("", include("apps.projects.urls", namespace="dashboard")),
    path("projects/", include("apps.projects.urls", namespace="projects")),
    path("deployments/", include("apps.deployments.urls", namespace="deployments")),
    path("services/", include("apps.services.urls", namespace="services")),
    path("logs/", include("apps.logs.urls", namespace="logs")),
    path("backups/", include("apps.backups.urls", namespace="backups")),
    path("monitoring/", include("apps.monitoring.urls", namespace="monitoring")),
    path("users/", include("apps.users.urls", namespace="users")),
    path("audit/", include("apps.audit.urls", namespace="audit")),

    # REST API
    path("api/v1/", include("api.router", namespace="api")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    try:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass
