"""
apps.backups — Repository Layer
"""
from typing import Optional
from django.db.models import QuerySet
from .models import Backup, BackupSchedule


class BackupRepository:

    @staticmethod
    def get_all() -> QuerySet[Backup]:
        return Backup.objects.select_related("project", "triggered_by").order_by("-created_at")

    @staticmethod
    def get_for_project(project_id: str) -> QuerySet[Backup]:
        return Backup.objects.filter(
            project_id=project_id
        ).select_related("triggered_by").order_by("-created_at")

    @staticmethod
    def get_by_id(backup_id: str) -> Optional[Backup]:
        try:
            return Backup.objects.select_related("project", "triggered_by").get(pk=backup_id)
        except Backup.DoesNotExist:
            return None

    @staticmethod
    def create(**kwargs) -> Backup:
        return Backup.objects.create(**kwargs)

    @staticmethod
    def update(backup: Backup, **fields) -> Backup:
        for k, v in fields.items():
            setattr(backup, k, v)
        backup.save(update_fields=list(fields.keys()) + ["updated_at"])
        return backup

    @staticmethod
    def delete(backup: Backup) -> None:
        backup.delete()

    @staticmethod
    def get_old_backups(project_id: str, retention_days: int) -> QuerySet[Backup]:
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=retention_days)
        return Backup.objects.filter(
            project_id=project_id,
            created_at__lt=cutoff,
            status=Backup.Status.SUCCESS,
        )

    @staticmethod
    def get_all_schedules() -> QuerySet[BackupSchedule]:
        return BackupSchedule.objects.select_related("project").filter(enabled=True)
