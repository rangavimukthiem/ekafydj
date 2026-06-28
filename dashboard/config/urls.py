from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from api.router import router  

urlpatterns = [
    path("django-admin/", admin.site.urls),

    path("account/", include(("two_factor.urls", "two_factor"), namespace="two_factor")),

    path("", include("apps.projects.urls")),

    path("deployments/", include("apps.deployments.urls")),
    path("services/", include("apps.services.urls")),
    path("logs/", include("apps.logs.urls")),
    path("backups/", include("apps.backups.urls")),
    path("monitoring/", include("apps.monitoring.urls")),
    path("users/", include("apps.users.urls")),
    path("audit/", include("apps.audit.urls")),

    # ✅ FIXED LINE
    path("api/v1/", include(router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

    try:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
    except ImportError:
        pass