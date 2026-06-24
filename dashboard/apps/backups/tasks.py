"""
apps.backups — Celery Tasks
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="backups.run_backup", max_retries=1)
def run_backup(self, *, backup_id: str) -> dict:
    """Execute a backup for the given backup record ID."""
    from .services import BackupService
    svc = BackupService()
    svc.execute_backup(backup_id)
    return {"backup_id": backup_id}


@shared_task(name="backups.run_scheduled_backups")
def run_scheduled_backups() -> dict:
    """
    Check all active backup schedules and trigger due backups.
    Runs every 30 minutes via Celery beat.
    """
    from .repositories import BackupRepository
    from .services import BackupService
    from .models import Backup

    schedules = BackupRepository.get_all_schedules()
    triggered = 0

    for schedule in schedules:
        project = schedule.project
        if project.status != "active":
            continue

        # Check if a backup already ran recently (within the cron window)
        from datetime import datetime, timezone, timedelta
        last = Backup.objects.filter(
            project=project,
            is_scheduled=True,
            status=Backup.Status.SUCCESS,
        ).order_by("-created_at").first()

        # Simple heuristic: don't re-run if last backup < 23h ago
        if last and (datetime.now(tz=timezone.utc) - last.created_at).total_seconds() < 82800:
            continue

        svc = BackupService()
        svc.trigger_backup(project, backup_type=schedule.backup_type, is_scheduled=True)
        triggered += 1
        logger.info("Triggered scheduled backup for project %s", project.name)

    return {"scheduled_backups_triggered": triggered}
