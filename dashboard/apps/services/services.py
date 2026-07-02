"""
apps.services — Systemd Service Control
Wraps systemctl commands for start/stop/restart/status of managed projects.
"""
import logging
import subprocess

from apps.audit.services import AuditService
from apps.core.exceptions import ServiceControlError
from apps.projects.models import Project
from apps.projects.repositories import ProjectRepository

logger = logging.getLogger(__name__)

SYSTEMCTL = "/usr/bin/systemctl"
JOURNALCTL = "/usr/bin/journalctl"
SUDO = "/usr/bin/sudo"


class SystemdService:
    """
    Interface to systemd for managing project service units.
    All methods log to the audit trail.
    """

    ALLOWED_ACTIONS = frozenset(["start", "stop", "restart", "reload", "enable", "disable"])

    def __init__(self, acting_user=None):
        self.acting_user = acting_user
        self.audit = AuditService()

    def get_status(self, project: Project) -> dict:
        """Return systemd service status as a structured dict."""
        try:
            result = subprocess.run(
                [SUDO, "-n", SYSTEMCTL, "status", project.systemd_service, "--no-pager"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            active = "active (running)" in result.stdout
            return {
                "active": active,
                "service": project.systemd_service,
                "output": result.stdout,
                "return_code": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"active": False, "service": project.systemd_service, "output": "Status check timed out", "return_code": -1}
        except Exception as exc:  # noqa: BLE001
            return {"active": False, "service": project.systemd_service, "output": str(exc), "return_code": -1}

    def start(self, project: Project) -> str:
        return self._control(project, "start")

    def stop(self, project: Project) -> str:
        return self._control(project, "stop")

    def restart(self, project: Project) -> str:
        return self._control(project, "restart")

    def reload(self, project: Project) -> str:
        return self._control(project, "reload")

    def _control(self, project: Project, action: str) -> str:
        """Run a systemctl action on a project's service unit."""
        if action not in self.ALLOWED_ACTIONS:
            raise ServiceControlError(f"Invalid systemd action: {action}")

        logger.info("systemctl %s %s (user=%s)", action, project.systemd_service, self.acting_user)

        try:
            result = subprocess.run(
                [SUDO, "-n", SYSTEMCTL, action, project.systemd_service],
                capture_output=True,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired as exc:
            raise ServiceControlError(f"systemctl {action} timed out for {project.systemd_service}") from exc

        if result.returncode != 0:
            raise ServiceControlError(
                f"systemctl {action} failed (rc={result.returncode}): {result.stderr}"
            )

        # Update project status in DB
        status_map = {
            "start": Project.Status.ACTIVE,
            "restart": Project.Status.ACTIVE,
            "reload": Project.Status.ACTIVE,
            "stop": Project.Status.STOPPED,
        }
        if action in status_map:
            ProjectRepository.update(project, status=status_map[action])

        self.audit.log(
            user=self.acting_user,
            action=f"service.{action}",
            resource_type="project",
            resource_id=str(project.pk),
            resource_name=project.name,
            meta={"service": project.systemd_service},
        )

        return result.stdout or f"Service {action} completed."

    def get_journal(self, project: Project, lines: int = 100) -> str:
        """Get recent journal log lines for a service."""
        try:
            result = subprocess.run(
                [SUDO, "-n", JOURNALCTL, "-u", project.systemd_service,
                 f"-n{lines}", "--no-pager", "--output=short-iso"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout
        except Exception as exc:  # noqa: BLE001
            return f"Failed to retrieve journal: {exc}"
