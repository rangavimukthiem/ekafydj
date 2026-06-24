"""
apps.projects — Project Model
The central entity in EKAFY. Each Project represents a managed Django application.
"""
from django.conf import settings
from django.db import models
from django.utils.text import slugify

from apps.core.models import BaseModel


class Project(BaseModel):
    """
    A managed Django project running on the VPS.
    """

    class Status(models.TextChoices):
        CREATING = "creating", "Creating"
        ACTIVE = "active", "Active"
        STOPPED = "stopped", "Stopped"
        FAILED = "failed", "Failed"
        ARCHIVED = "archived", "Archived"

    class PythonVersion(models.TextChoices):
        PY312 = "3.12", "Python 3.12"
        PY311 = "3.11", "Python 3.11"
        PY310 = "3.10", "Python 3.10"

    # Identity
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, db_index=True)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.CREATING, db_index=True)

    # Git
    git_url = models.CharField(max_length=500)
    git_branch = models.CharField(max_length=100, default="main")
    deploy_key_path = models.CharField(max_length=500, blank=True)  # path to SSH deploy key

    # Infrastructure paths (auto-computed from slug)
    venv_path = models.CharField(max_length=500, blank=True)
    repo_path = models.CharField(max_length=500, blank=True)
    project_dir = models.CharField(max_length=500, blank=True)

    # Python
    python_version = models.CharField(max_length=10, choices=PythonVersion.choices, default=PythonVersion.PY312)

    # Database
    db_name = models.CharField(max_length=100, unique=True)
    db_user = models.CharField(max_length=100)
    db_password = models.CharField(max_length=200)
    db_host = models.CharField(max_length=100, default="localhost")
    db_port = models.IntegerField(default=5432)

    # Systemd
    systemd_service = models.CharField(max_length=100, blank=True)  # e.g. "myapp.service"
    gunicorn_bind = models.CharField(max_length=100, default="unix:/run/gunicorn/{slug}.sock")
    gunicorn_workers = models.IntegerField(default=3)

    # Nginx
    nginx_conf_path = models.CharField(max_length=500, blank=True)
    domain = models.CharField(max_length=253, blank=True)
    port = models.IntegerField(null=True, blank=True)

    # Django settings
    django_settings_module = models.CharField(max_length=200, default="config.settings.production")
    django_wsgi_module = models.CharField(max_length=200, default="config.wsgi:application")
    secret_key = models.CharField(max_length=200, blank=True)

    # Health
    health_check_url = models.CharField(max_length=500, blank=True)
    last_health_check = models.DateTimeField(null=True, blank=True)
    is_healthy = models.BooleanField(null=True, blank=True)

    # Meta
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_projects",
    )
    tags = models.CharField(max_length=200, blank=True, help_text="Comma-separated tags")
    notes = models.TextField(blank=True)

    class Meta(BaseModel.Meta):
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    def __str__(self) -> str:
        return f"{self.name} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        # Auto-populate infrastructure paths from slug
        base = settings.EKAFY_PROJECTS_DIR
        if not self.project_dir:
            self.project_dir = f"{base}/{self.slug}"
        if not self.venv_path:
            self.venv_path = f"{base}/{self.slug}/.venv"
        if not self.repo_path:
            self.repo_path = f"{base}/{self.slug}/repo"
        if not self.systemd_service:
            self.systemd_service = f"ekafy-{self.slug}.service"
        if not self.nginx_conf_path:
            self.nginx_conf_path = f"/etc/nginx/sites-available/ekafy-{self.slug}"
        if not self.db_name:
            self.db_name = f"ekafy_{self.slug.replace('-', '_')}"
        if not self.db_user:
            self.db_user = f"ekafy_{self.slug.replace('-', '_')}"
        super().save(*args, **kwargs)

    @property
    def tag_list(self) -> list[str]:
        return [t.strip() for t in self.tags.split(",") if t.strip()]

    @property
    def is_running(self) -> bool:
        return self.status == self.Status.ACTIVE

    @property
    def status_badge_class(self) -> str:
        """Return a CSS class for status badge color."""
        return {
            "creating": "badge-warning",
            "active": "badge-success",
            "stopped": "badge-neutral",
            "failed": "badge-error",
            "archived": "badge-ghost",
        }.get(self.status, "badge-ghost")
