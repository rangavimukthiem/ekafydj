"""
apps.projects — Service Layer
All business logic for project lifecycle: create, scaffold, archive.
"""
import logging
import secrets

from django.conf import settings

from apps.audit.services import AuditService
from apps.core.exceptions import ProjectAlreadyExistsError, ProjectNotFoundError, ScriptExecutionError
from apps.core.utils import run_privileged_script, slugify

from .models import Project
from .repositories import ProjectRepository

logger = logging.getLogger(__name__)


class ProjectService:
    """Handles project creation, scaffolding, and archival."""

    def __init__(self, acting_user=None):
        self.acting_user = acting_user
        self.repo = ProjectRepository()
        self.audit = AuditService()

    def create_project(
        self,
        *,
        name: str,
        git_url: str,
        git_branch: str = "main",
        domain: str = "",
        description: str = "",
        python_version: str = "3.12",
        gunicorn_workers: int = 3,
        django_settings_module: str = "config.settings.production",
    ) -> Project:
        """
        Create a new managed project:
        1. Validate slug uniqueness
        2. Generate credentials
        3. Persist to DB
        4. Call create_project.sh to scaffold filesystem
        """
        slug = slugify(name)

        if self.repo.exists_by_slug(slug):
            raise ProjectAlreadyExistsError(f"A project with slug '{slug}' already exists.")

        if self.repo.exists_by_name(name):
            raise ProjectAlreadyExistsError(f"A project named '{name}' already exists.")

        # Generate secure credentials
        db_password = secrets.token_urlsafe(24)
        secret_key = secrets.token_urlsafe(50)
        db_name = f"ekafy_{slug.replace('-', '_')}"
        db_user = f"ekafy_{slug.replace('-', '_')}"

        project = self.repo.create(
            name=name,
            slug=slug,
            description=description,
            git_url=git_url,
            git_branch=git_branch,
            domain=domain,
            python_version=python_version,
            gunicorn_workers=gunicorn_workers,
            django_settings_module=django_settings_module,
            db_name=db_name,
            db_user=db_user,
            db_password=db_password,
            secret_key=secret_key,
            status=Project.Status.CREATING,
            owner=self.acting_user,
        )

        logger.info("Created project DB record: %s (id=%s)", name, project.pk)

        # Scaffold filesystem (may fail on dev — non-fatal)
        try:
            self._scaffold_filesystem(project)
            self._create_systemd_service(project)
            self._create_nginx_config(project)
            self.repo.update(project, status=Project.Status.STOPPED)
        except ScriptExecutionError as exc:
            logger.error("Failed to scaffold project %s: %s", slug, exc)
            self.repo.update(project, status=Project.Status.FAILED)

        self.audit.log(
            user=self.acting_user,
            action="project.created",
            resource_type="project",
            resource_id=str(project.pk),
            resource_name=project.name,
            meta={"slug": slug, "git_url": git_url, "domain": domain},
        )

        return project

    def archive_project(self, project: Project) -> Project:
        """Mark a project as archived (does not delete files)."""
        if project.status == Project.Status.ACTIVE:
            raise ValueError("Stop the project before archiving it.")

        project = self.repo.update(project, status=Project.Status.ARCHIVED)

        self.audit.log(
            user=self.acting_user,
            action="project.archived",
            resource_type="project",
            resource_id=str(project.pk),
            resource_name=project.name,
        )
        return project

    def delete_project(self, project: Project) -> None:
        """Permanently remove project from DB (does not delete VPS files)."""
        name = project.name
        pk = str(project.pk)
        self.repo.delete(project)

        self.audit.log(
            user=self.acting_user,
            action="project.deleted",
            resource_type="project",
            resource_id=pk,
            resource_name=name,
        )

    def update_project(self, project: Project, **fields) -> Project:
        """Update project metadata fields."""
        project = self.repo.update(project, **fields)
        self.audit.log(
            user=self.acting_user,
            action="project.updated",
            resource_type="project",
            resource_id=str(project.pk),
            resource_name=project.name,
            meta=fields,
        )
        return project

    # ─── Private helpers ────────────────────────────────────────────────────

    def _scaffold_filesystem(self, project: Project) -> None:
        """Call create_project.sh to create directories, venv, and DB."""
        run_privileged_script(
            "create_project.sh",
            args=[
                project.slug,
                project.git_url,
                project.git_branch,
                project.python_version,
                project.db_name,
                project.db_user,
                project.db_password,
                settings.EKAFY_PROJECTS_DIR,
            ],
        )

    def _create_systemd_service(self, project: Project) -> None:
        """Generate and install the systemd service unit for the project."""
        run_privileged_script(
            "create_systemd_service.sh",
            args=[
                project.slug,
                project.systemd_service,
                project.venv_path,
                project.repo_path,
                project.django_wsgi_module,
                project.django_settings_module,
                str(project.gunicorn_workers),
                project.gunicorn_bind.replace("{slug}", project.slug),
            ],
        )

    def _create_nginx_config(self, project: Project) -> None:
        """Generate and install the nginx server block for the project."""
        if not project.domain:
            return
        run_privileged_script(
            "create_nginx_conf.sh",
            args=[
                project.slug,
                project.domain,
                project.nginx_conf_path,
                project.gunicorn_bind.replace("{slug}", project.slug),
            ],
        )
