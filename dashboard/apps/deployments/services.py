"""
apps.deployments — Service Layer
Full deployment lifecycle: git pull → pip install → migrate → collectstatic → restart.
"""
import logging
from datetime import datetime, timezone

from django.conf import settings

from apps.audit.services import AuditService
from apps.core.exceptions import DeploymentInProgressError, DeploymentError, ScriptExecutionError
from apps.core.utils import run_command, run_script
from apps.projects.models import Project
from apps.projects.repositories import ProjectRepository

from .models import Deployment
from .repositories import DeploymentRepository
from .tasks import run_deployment, run_rollback

logger = logging.getLogger(__name__)


class DeploymentService:
    """
    Executes the deployment pipeline for a managed project.
    Called from Celery tasks (async) or views (sync, dev only).
    """

    def __init__(self, acting_user=None):
        self.acting_user = acting_user
        self.deploy_repo = DeploymentRepository()
        self.project_repo = ProjectRepository()
        self.audit = AuditService()

    def trigger_deployment(self, project: Project, force: bool = False) -> Deployment:
        """
        Create a Deployment record and enqueue the Celery task.

        Args:
            project: The Project to deploy.
            force: If True, skip the in-progress check.

        Returns:
            The created Deployment instance.
        """
        # Guard: prevent concurrent deployments
        if not force:
            running = self.deploy_repo.get_running_for_project(str(project.pk))
            if running:
                raise DeploymentInProgressError(
                    f"A deployment is already running for '{project.name}'. "
                    f"Check deployment #{running.pk}."
                )

        deployment = self.deploy_repo.create(
            project=project,
            triggered_by=self.acting_user,
            status=Deployment.Status.PENDING,
            git_branch=project.git_branch,
        )

        # Enqueue Celery task
        task = run_deployment.apply_async(
            kwargs={"deployment_id": str(deployment.pk)},
            countdown=1,
        )
        self.deploy_repo.update(deployment, task_id=task.id)

        self.audit.log(
            user=self.acting_user,
            action="deployment.triggered",
            resource_type="deployment",
            resource_id=str(deployment.pk),
            resource_name=project.name,
            meta={"branch": project.git_branch},
        )

        logger.info("Deployment %s triggered for project %s (task=%s)", deployment.pk, project.name, task.id)
        return deployment

    def execute_deployment(self, deployment_id: str) -> None:
        """
        Execute the full deployment pipeline synchronously.
        This runs inside a Celery worker.
        """
        deployment = self.deploy_repo.get_by_id(deployment_id)
        if not deployment:
            logger.error("Deployment %s not found", deployment_id)
            return

        project = deployment.project
        log_lines: list[str] = []

        def log(msg: str) -> None:
            log_lines.append(msg)
            logger.info("[Deploy %s] %s", deployment.pk, msg)

        # Mark as running
        self.deploy_repo.update(
            deployment,
            status=Deployment.Status.RUNNING,
            started_at=datetime.now(tz=timezone.utc),
        )

        try:
            log(f"=== EKAFY Deployment started for {project.name} ===")
            log(f"Branch: {project.git_branch}")

            # Step 1: git pull
            log("--- Step 1/6: git pull ---")
            result = run_command(
                ["git", "-C", project.repo_path, "pull", "origin", project.git_branch],
                timeout=120,
            )
            log(result.stdout)

            # Capture commit info
            commit_info = run_command(
                ["git", "-C", project.repo_path, "log", "-1",
                 "--format=%H|%s|%an"],
                timeout=30,
            )
            if commit_info.stdout.strip():
                parts = commit_info.stdout.strip().split("|", 2)
                self.deploy_repo.update(
                    deployment,
                    commit_hash=parts[0] if len(parts) > 0 else "",
                    commit_message=parts[1] if len(parts) > 1 else "",
                    commit_author=parts[2] if len(parts) > 2 else "",
                )

            # Step 2: pip install
            log("--- Step 2/6: pip install -r requirements.txt ---")
            pip = f"{project.venv_path}/bin/pip"
            req_file = f"{project.repo_path}/requirements.txt"
            result = run_command([pip, "install", "-r", req_file, "--quiet"], timeout=300)
            log(result.stdout or "pip install completed")

            # Step 3: migrate
            log("--- Step 3/6: manage.py migrate ---")
            python = f"{project.venv_path}/bin/python"
            manage = f"{project.repo_path}/manage.py"
            result = run_command(
                [python, manage, "migrate", "--noinput",
                 f"--settings={project.django_settings_module}"],
                timeout=120,
            )
            log(result.stdout)

            # Step 4: collectstatic
            log("--- Step 4/6: manage.py collectstatic ---")
            result = run_command(
                [python, manage, "collectstatic", "--noinput",
                 f"--settings={project.django_settings_module}"],
                timeout=120,
            )
            log(result.stdout)

            # Step 5: restart service
            log(f"--- Step 5/6: systemctl restart {project.systemd_service} ---")
            result = run_command(["sudo", "systemctl", "restart", project.systemd_service], timeout=30)
            log(result.stdout or "Service restarted")

            # Step 6: update project status
            log("--- Step 6/6: Updating project status ---")
            self.project_repo.update(project, status=Project.Status.ACTIVE)

            log("=== Deployment SUCCEEDED ===")

            self.deploy_repo.update(
                deployment,
                status=Deployment.Status.SUCCESS,
                finished_at=datetime.now(tz=timezone.utc),
                log="\n".join(log_lines),
            )

            self.audit.log(
                user=deployment.triggered_by,
                action="deployment.succeeded",
                resource_type="deployment",
                resource_id=str(deployment.pk),
                resource_name=project.name,
                meta={"commit": deployment.commit_hash},
            )

        except ScriptExecutionError as exc:
            log(f"FAILED: {exc.message}")
            log(f"stderr: {exc.stderr}")
            self._mark_failed(deployment, log_lines, project)

        except Exception as exc:  # noqa: BLE001
            log(f"UNEXPECTED ERROR: {exc}")
            self._mark_failed(deployment, log_lines, project)

    def rollback(self, project: Project, to_deployment: Deployment) -> Deployment:
        """Roll back a project to a previous successful deployment commit."""
        if to_deployment.status != Deployment.Status.SUCCESS:
            raise DeploymentError("Can only roll back to a successful deployment.")

        rollback = self.deploy_repo.create(
            project=project,
            triggered_by=self.acting_user,
            status=Deployment.Status.PENDING,
            git_branch=project.git_branch,
            rollback_of=to_deployment,
        )

        task = run_rollback.apply_async(
            kwargs={
                "deployment_id": str(rollback.pk),
                "target_commit": to_deployment.commit_hash,
            },
            countdown=1,
        )
        self.deploy_repo.update(rollback, task_id=task.id)
        return rollback

    def _mark_failed(self, deployment: Deployment, log_lines: list, project: Project) -> None:
        self.deploy_repo.update(
            deployment,
            status=Deployment.Status.FAILED,
            finished_at=datetime.now(tz=timezone.utc),
            log="\n".join(log_lines),
        )
        self.project_repo.update(project, status=Project.Status.FAILED)
        self.audit.log(
            user=deployment.triggered_by,
            action="deployment.failed",
            resource_type="deployment",
            resource_id=str(deployment.pk),
            resource_name=project.name,
        )
        # Send notification
        self._notify_failure(deployment, project)

    def _notify_failure(self, deployment: Deployment, project: Project) -> None:
        """Send email and optional Slack notification on deployment failure."""
        from django.core.mail import mail_admins
        from django.conf import settings
        import requests

        try:
            mail_admins(
                subject=f"[EKAFY] Deployment FAILED — {project.name}",
                message=(
                    f"Deployment {deployment.pk} for project '{project.name}' failed.\n\n"
                    f"Triggered by: {deployment.triggered_by or 'system'}\n"
                    f"Branch: {deployment.git_branch}\n\n"
                    f"Last log lines:\n{deployment.log[-2000:] if deployment.log else 'No log.'}"
                ),
                fail_silently=True,
            )
        except Exception:  # noqa: BLE001
            pass

        slack_url = getattr(settings, "SLACK_WEBHOOK_URL", "")
        if slack_url:
            try:
                requests.post(slack_url, json={
                    "text": f":x: *EKAFY Deployment FAILED* — `{project.name}`\n"
                            f"Branch: `{deployment.git_branch}` | "
                            f"Triggered by: {getattr(deployment.triggered_by, 'username', 'system')}"
                }, timeout=5)
            except Exception:  # noqa: BLE001
                pass
