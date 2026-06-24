"""
apps.projects — Repository Layer
All ORM queries for Project are here. Services call these; views never touch ORM directly.
"""
from typing import Optional
from django.db.models import QuerySet

from .models import Project


class ProjectRepository:
    """Data access layer for Project model."""

    @staticmethod
    def get_all() -> QuerySet[Project]:
        return Project.objects.select_related("owner").order_by("name")

    @staticmethod
    def get_active() -> QuerySet[Project]:
        return Project.objects.filter(status=Project.Status.ACTIVE).select_related("owner")

    @staticmethod
    def get_by_id(project_id: str) -> Optional[Project]:
        try:
            return Project.objects.select_related("owner").get(pk=project_id)
        except Project.DoesNotExist:
            return None

    @staticmethod
    def get_by_slug(slug: str) -> Optional[Project]:
        try:
            return Project.objects.select_related("owner").get(slug=slug)
        except Project.DoesNotExist:
            return None

    @staticmethod
    def exists_by_slug(slug: str) -> bool:
        return Project.objects.filter(slug=slug).exists()

    @staticmethod
    def exists_by_name(name: str) -> bool:
        return Project.objects.filter(name=name).exists()

    @staticmethod
    def create(**kwargs) -> Project:
        return Project.objects.create(**kwargs)

    @staticmethod
    def update(project: Project, **fields) -> Project:
        for key, value in fields.items():
            setattr(project, key, value)
        project.save(update_fields=list(fields.keys()) + ["updated_at"])
        return project

    @staticmethod
    def delete(project: Project) -> None:
        project.delete()

    @staticmethod
    def search(query: str) -> QuerySet[Project]:
        return Project.objects.filter(
            name__icontains=query
        ).union(
            Project.objects.filter(slug__icontains=query)
        ).union(
            Project.objects.filter(domain__icontains=query)
        )

    @staticmethod
    def get_by_status(status: str) -> QuerySet[Project]:
        return Project.objects.filter(status=status).select_related("owner")
