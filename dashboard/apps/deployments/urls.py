from django.urls import path
from . import views

app_name = "deployments"

urlpatterns = [
    path("", views.DeploymentListView.as_view(), name="list"),
    path("<uuid:pk>/", views.DeploymentDetailView.as_view(), name="detail"),
    path("<uuid:pk>/log-stream/", views.DeploymentLogStreamView.as_view(), name="log-stream"),
    path("<uuid:pk>/status/", views.DeploymentStatusView.as_view(), name="status"),
    path("<uuid:pk>/rollback/", views.RollbackView.as_view(), name="rollback"),
    path("trigger/<slug:slug>/", views.TriggerDeploymentView.as_view(), name="trigger"),
]
