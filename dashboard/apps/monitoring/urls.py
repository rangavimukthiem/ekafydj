from django.urls import path
from . import views

app_name = "monitoring"

urlpatterns = [
    path("", views.MonitoringDashboardView.as_view(), name="dashboard"),
    path("api/metrics/", views.MetricsApiView.as_view(), name="api-metrics"),
    path("current/", views.CurrentMetricsView.as_view(), name="current"),
]
