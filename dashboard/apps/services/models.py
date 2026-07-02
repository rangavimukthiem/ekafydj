"""
apps.services - Models for service status snapshots.
"""
from django.db import models

from apps.core.models import BaseModel
from apps.projects.models import Project


class ServiceStatus(BaseModel):
    """Point-in-time status of a managed project's systemd service."""

    class State(models.TextChoices):
        ACTIVE = "active", "Active"
        INACTIVE = "inactive", "Inactive"
        FAILED = "failed", "Failed"
        UNKNOWN = "unknown", "Unknown"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="service_statuses")
    service_name = models.CharField(max_length=100)
    state = models.CharField(max_length=20, choices=State.choices, default=State.UNKNOWN, db_index=True)
    return_code = models.IntegerField(default=0)
    output = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Service Status"
        verbose_name_plural = "Service Statuses"

    def __str__(self) -> str:
        return f"{self.service_name} [{self.state}]"
