"""
apps.deployments — Celery Tasks
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="deployments.run_deployment", max_retries=0)
def run_deployment(self, *, deployment_id: str) -> dict:
    """Execute a full deployment pipeline."""
    from .services import DeploymentService
    svc = DeploymentService()
    svc.execute_deployment(deployment_id)
    return {"deployment_id": deployment_id, "status": "completed"}


@shared_task(bind=True, name="deployments.run_rollback", max_retries=0)
def run_rollback(self, *, deployment_id: str, target_commit: str) -> dict:
    """Execute a rollback to a specific git commit."""
    from .repositories import DeploymentRepository
    from apps.core.utils import run_command

    repo = DeploymentRepository()
    deployment = repo.get_by_id(deployment_id)
    if not deployment:
        logger.error("Rollback deployment %s not found", deployment_id)
        return {"error": "not_found"}

    project = deployment.project
    log_lines = []

    def log(msg):
        log_lines.append(msg)
        logger.info("[Rollback %s] %s", deployment_id, msg)

    try:
        from datetime import datetime, timezone
        from .models import Deployment
        from apps.projects.models import Project

        repo.update(deployment, status=Deployment.Status.RUNNING,
                    started_at=datetime.now(tz=timezone.utc))

        log(f"=== ROLLBACK to commit {target_commit[:7]} ===")
        run_command(["git", "-C", project.repo_path, "checkout", target_commit], timeout=60)
        log("Checkout complete")

        pip = f"{project.venv_path}/bin/pip"
        python = f"{project.venv_path}/bin/python"
        manage = f"{project.repo_path}/manage.py"

        run_command([pip, "install", "-r", f"{project.repo_path}/requirements.txt", "--quiet"], timeout=300)
        log("pip install complete")

        run_command([python, manage, "migrate", "--noinput",
                     f"--settings={project.django_settings_module}"], timeout=120)
        log("migrate complete")

        run_command(["sudo", "systemctl", "restart", project.systemd_service], timeout=30)
        log("Service restarted")

        repo.update(deployment, status=Deployment.Status.ROLLED_BACK,
                    finished_at=datetime.now(tz=timezone.utc), log="\n".join(log_lines))

        from apps.projects.repositories import ProjectRepository
        ProjectRepository.update(project, status=Project.Status.ACTIVE)

        log("=== ROLLBACK SUCCEEDED ===")
        return {"deployment_id": deployment_id, "status": "rolled_back"}

    except Exception as exc:  # noqa: BLE001
        log(f"ROLLBACK FAILED: {exc}")
        from datetime import datetime, timezone
        from .models import Deployment
        repo.update(deployment, status=Deployment.Status.FAILED,
                    finished_at=datetime.now(tz=timezone.utc), log="\n".join(log_lines))
        return {"deployment_id": deployment_id, "status": "failed", "error": str(exc)}


@shared_task(name="deployments.cleanup_old_deployment_logs")
def cleanup_old_deployment_logs() -> dict:
    """Delete deployment records older than 90 days to keep the DB lean."""
    from datetime import datetime, timezone, timedelta
    from .models import Deployment

    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=90)
    deleted, _ = Deployment.objects.filter(
        created_at__lt=cutoff,
        status__in=[Deployment.Status.SUCCESS, Deployment.Status.FAILED, Deployment.Status.ROLLED_BACK],
    ).delete()

    logger.info("Cleaned up %d old deployment records", deleted)
    return {"deleted": deleted}
