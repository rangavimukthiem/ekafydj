"""
apps.backups — Service Layer
Handles database dumps, media archives, and optional S3 uploads.
"""
import logging
import os
import gzip
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings

from apps.audit.services import AuditService
from apps.core.exceptions import BackupError
from apps.core.utils import run_command, format_bytes
from apps.projects.models import Project

from .models import Backup
from .repositories import BackupRepository

logger = logging.getLogger(__name__)


class BackupService:
    """Creates and manages backups for managed projects."""

    def __init__(self, acting_user=None):
        self.acting_user = acting_user
        self.repo = BackupRepository()
        self.audit = AuditService()

    def trigger_backup(
        self,
        project: Project,
        backup_type: str = "db",
        is_scheduled: bool = False,
    ) -> Backup:
        """Create a Backup record and enqueue the Celery task."""
        backup = self.repo.create(
            project=project,
            triggered_by=self.acting_user,
            backup_type=backup_type,
            status=Backup.Status.PENDING,
            is_scheduled=is_scheduled,
        )

        from .tasks import run_backup
        task = run_backup.apply_async(kwargs={"backup_id": str(backup.pk)}, countdown=1)
        self.repo.update(backup, task_id=task.id)

        self.audit.log(
            user=self.acting_user,
            action="backup.triggered",
            resource_type="backup",
            resource_id=str(backup.pk),
            resource_name=project.name,
            meta={"type": backup_type, "scheduled": is_scheduled},
        )
        return backup

    def execute_backup(self, backup_id: str) -> None:
        """
        Execute the backup. Runs inside Celery worker.
        """
        backup = self.repo.get_by_id(backup_id)
        if not backup:
            return

        project = backup.project
        self.repo.update(backup, status=Backup.Status.RUNNING)

        try:
            timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_dir = Path(settings.EKAFY_BACKUPS_DIR) / project.slug
            backup_dir.mkdir(parents=True, exist_ok=True)

            file_path = None

            if backup.backup_type in ("db", "full"):
                file_path = self._dump_database(project, backup_dir, timestamp)

            if backup.backup_type in ("media", "full"):
                media_path = self._archive_media(project, backup_dir, timestamp)
                if not file_path:
                    file_path = media_path

            if not file_path or not Path(file_path).exists():
                raise BackupError("Backup file was not created.")

            file_size = Path(file_path).stat().st_size
            file_name = Path(file_path).name

            backup = self.repo.update(
                backup,
                file_path=str(file_path),
                file_name=file_name,
                file_size=file_size,
                log=f"Backup completed: {file_name} ({format_bytes(file_size)})",
            )

            # Optional S3 upload
            if settings.USE_S3_BACKUPS:
                self._upload_to_s3(backup, file_path)

            backup = self.repo.update(backup, status=Backup.Status.SUCCESS)

            self.audit.log(
                user=backup.triggered_by,
                action="backup.completed",
                resource_type="backup",
                resource_id=str(backup.pk),
                resource_name=project.name,
                meta={"file": file_name, "size_bytes": file_size},
            )

            # Cleanup old backups
            self._cleanup_old_backups(project)

        except Exception as exc:  # noqa: BLE001
            logger.error("Backup failed for project %s: %s", project.name, exc)
            self.repo.update(backup, status=Backup.Status.FAILED, log=str(exc))
            self.audit.log(
                user=backup.triggered_by,
                action="backup.failed",
                resource_type="backup",
                resource_id=str(backup.pk),
                resource_name=project.name,
                meta={"error": str(exc)},
            )

    def delete_backup(self, backup: Backup) -> None:
        """Delete a backup record and its file."""
        file_path = Path(backup.file_path) if backup.file_path else None
        if file_path and file_path.exists():
            file_path.unlink()

        self.audit.log(
            user=self.acting_user,
            action="backup.deleted",
            resource_type="backup",
            resource_id=str(backup.pk),
            resource_name=backup.project.name,
        )
        self.repo.delete(backup)

    def _dump_database(self, project: Project, backup_dir: Path, timestamp: str) -> str:
        """Run pg_dump for a project's database."""
        filename = f"{project.slug}_db_{timestamp}.sql.gz"
        out_path = backup_dir / filename

        env = os.environ.copy()
        env["PGPASSWORD"] = project.db_password

        try:
            with gzip.open(out_path, "wb") as compressed:
                result = subprocess.run(
                    [
                        "pg_dump",
                        "-U",
                        project.db_user,
                        "-h",
                        project.db_host,
                        "-p",
                        str(project.db_port),
                        project.db_name,
                    ],
                    stdout=compressed,
                    stderr=subprocess.PIPE,
                    env=env,
                    timeout=300,
                    check=False,
                )
        except subprocess.TimeoutExpired as exc:
            raise BackupError(f"pg_dump timed out for database {project.db_name}") from exc

        if result.returncode != 0:
            raise BackupError(result.stderr.decode("utf-8", errors="replace"))
        return str(out_path)

    def _archive_media(self, project: Project, backup_dir: Path, timestamp: str) -> str:
        """Create a tar.gz archive of the project's media directory."""
        media_dir = f"{project.repo_path}/media"
        filename = f"{project.slug}_media_{timestamp}.tar.gz"
        out_path = backup_dir / filename

        run_command(
            ["tar", "-czf", str(out_path), "-C", media_dir, "."],
            timeout=300,
        )
        return str(out_path)

    def _upload_to_s3(self, backup: Backup, file_path: str) -> None:
        """Upload a backup file to S3/Backblaze B2."""
        import boto3
        self.repo.update(backup, status=Backup.Status.UPLOADING)
        try:
            s3 = boto3.client(
                "s3",
                endpoint_url=settings.AWS_S3_ENDPOINT_URL or None,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
            key = f"ekafy/{backup.project.slug}/{Path(file_path).name}"
            s3.upload_file(file_path, settings.AWS_STORAGE_BUCKET_NAME, key)
            s3_url = f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{key}"
            self.repo.update(backup, s3_key=key, s3_url=s3_url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("S3 upload failed for backup %s: %s", backup.pk, exc)

    def _cleanup_old_backups(self, project: Project) -> None:
        """Delete backups older than the project's retention period."""
        try:
            schedule = project.backup_schedule
            retention = schedule.retention_days
        except Exception:  # noqa: BLE001
            retention = 30

        old = self.repo.get_old_backups(str(project.pk), retention)
        for backup in old:
            try:
                self.delete_backup(backup)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to delete old backup %s: %s", backup.pk, exc)
