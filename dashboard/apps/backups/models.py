"""
apps.backups — Backup Model
"""
from django.conf import settings
from django.db import models

from apps.core.models import BaseModel
from apps.projects.models import Project


class Backup(BaseModel):
    """Represents a single backup file for a managed project."""

    class BackupType(models.TextChoices):
        DATABASE = "db", "Database"
        MEDIA = "media", "Media Files"
        FULL = "full", "Full (DB + Media)"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        UPLOADING = "uploading", "Uploading to S3"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="backups",
    )
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_backups",
    )

    backup_type = models.CharField(max_length=10, choices=BackupType.choices, default=BackupType.DATABASE)
    status = models.CharField(max_length=15, choices=Status.choices, default=Status.PENDING, db_index=True)

    # File info
    file_path = models.CharField(max_length=500, blank=True)
    file_name = models.CharField(max_length=255, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)  # bytes

    # S3 info (optional)
    s3_key = models.CharField(max_length=500, blank=True)
    s3_url = models.CharField(max_length=1000, blank=True)

    # Log
    log = models.TextField(blank=True)

    # Celery task
    task_id = models.CharField(max_length=255, blank=True)

    # Scheduled (True = triggered by cron, False = manual)
    is_scheduled = models.BooleanField(default=False)

    class Meta(BaseModel.Meta):
        verbose_name = "Backup"
        verbose_name_plural = "Backups"

    def __str__(self) -> str:
        return f"{self.project.name} {self.backup_type} backup [{self.status}] @ {self.created_at:%Y-%m-%d}"

    @property
    def file_size_human(self) -> str:
        from apps.core.utils import format_bytes
        return format_bytes(self.file_size) if self.file_size else "—"


class BackupSchedule(models.Model):
    """Cron-based backup schedule per project."""

    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="backup_schedule",
    )
    enabled = models.BooleanField(default=True)
    backup_type = models.CharField(max_length=10, choices=Backup.BackupType.choices, default=Backup.BackupType.DATABASE)
    cron_expression = models.CharField(max_length=100, default="0 2 * * *")  # 2am daily
    retention_days = models.IntegerField(default=30)
    upload_to_s3 = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Backup Schedule"

    def __str__(self) -> str:
        return f"{self.project.name} ({self.cron_expression})"
