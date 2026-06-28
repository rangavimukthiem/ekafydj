"""
api — DRF Router
Registers all ViewSets under /api/v1/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .viewsets.projects import ProjectViewSet
from .viewsets.deployments import DeploymentViewSet
from .viewsets.backups import BackupViewSet
from .viewsets.monitoring import SystemMetricViewSet

app_name = "api"

router = DefaultRouter()
router.register(r"projects", ProjectViewSet, basename="project")
router.register(r"deployments", DeploymentViewSet, basename="deployment")
router.register(r"backups", BackupViewSet, basename="backup")
router.register(r"metrics", SystemMetricViewSet, basename="metric")


