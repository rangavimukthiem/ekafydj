"""
apps.deployments — Repository Layer
"""
from typing import Optional
from django.db.models import QuerySet
from .models import Deployment


class DeploymentRepository:

    @staticmethod
    def get_all() -> QuerySet[Deployment]:
        return Deployment.objects.select_related("project", "triggered_by").order_by("-created_at")

    @staticmethod
    def get_for_project(project_id: str) -> QuerySet[Deployment]:
        return Deployment.objects.filter(
            project_id=project_id
        ).select_related("triggered_by").order_by("-created_at")

    @staticmethod
    def get_by_id(deployment_id: str) -> Optional[Deployment]:
        try:
            return Deployment.objects.select_related("project", "triggered_by").get(pk=deployment_id)
        except Deployment.DoesNotExist:
            return None

    @staticmethod
    def get_running_for_project(project_id: str) -> Optional[Deployment]:
        return Deployment.objects.filter(
            project_id=project_id,
            status=Deployment.Status.RUNNING,
        ).first()

    @staticmethod
    def create(**kwargs) -> Deployment:
        return Deployment.objects.create(**kwargs)

    @staticmethod
    def update(deployment: Deployment, **fields) -> Deployment:
        for k, v in fields.items():
            setattr(deployment, k, v)
        deployment.save(update_fields=list(fields.keys()) + ["updated_at"])
        return deployment

    @staticmethod
    def get_last_success_for_project(project_id: str) -> Optional[Deployment]:
        return Deployment.objects.filter(
            project_id=project_id,
            status=Deployment.Status.SUCCESS,
        ).order_by("-created_at").first()
