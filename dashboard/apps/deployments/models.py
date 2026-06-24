"""
apps.deployments — Deployment Model
Tracks every deployment event for every managed project.
"""
from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.projects.models import Project


class Deployment(BaseModel):
    """Records a single deployment run for a managed project."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        ROLLED_BACK = "rolled_back", "Rolled Back"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="deployments",
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_deployments",
    )

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)

    # Git info captured at deploy time
    commit_hash = models.CharField(max_length=40, blank=True)
    commit_message = models.TextField(blank=True)
    commit_author = models.CharField(max_length=200, blank=True)
    git_branch = models.CharField(max_length=100, blank=True)

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    # Full deployment log (stdout + stderr captured)
    log = models.TextField(blank=True)

    # Celery task ID for tracking
    task_id = models.CharField(max_length=255, blank=True, db_index=True)

    # Rollback: previous deployment reference
    rollback_of = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="rollbacks",
    )

    class Meta(BaseModel.Meta):
        verbose_name = "Deployment"
        verbose_name_plural = "Deployments"

    def __str__(self) -> str:
        return f"{self.project.name} @ {self.created_at:%Y-%m-%d %H:%M} [{self.status}]"

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at and self.finished_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None

    @property
    def is_terminal(self) -> bool:
        return self.status in (self.Status.SUCCESS, self.Status.FAILED, self.Status.ROLLED_BACK)

    @property
    def short_commit(self) -> str:
        return self.commit_hash[:7] if self.commit_hash else "unknown"

    @property
    def status_badge_class(self) -> str:
        return {
            "pending": "badge-warning",
            "running": "badge-info",
            "success": "badge-success",
            "failed": "badge-error",
            "rolled_back": "badge-neutral",
        }.get(self.status, "badge-ghost")
