import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Project",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(db_index=True, max_length=100, unique=True)),
                ("description", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("creating", "Creating"), ("active", "Active"), ("stopped", "Stopped"), ("failed", "Failed"), ("archived", "Archived")], db_index=True, default="creating", max_length=20)),
                ("git_url", models.CharField(max_length=500)),
                ("git_branch", models.CharField(default="main", max_length=100)),
                ("deploy_key_path", models.CharField(blank=True, max_length=500)),
                ("venv_path", models.CharField(blank=True, max_length=500)),
                ("repo_path", models.CharField(blank=True, max_length=500)),
                ("project_dir", models.CharField(blank=True, max_length=500)),
                ("python_version", models.CharField(choices=[("3.12", "Python 3.12"), ("3.11", "Python 3.11"), ("3.10", "Python 3.10")], default="3.12", max_length=10)),
                ("db_name", models.CharField(max_length=100, unique=True)),
                ("db_user", models.CharField(max_length=100)),
                ("db_password", models.CharField(max_length=200)),
                ("db_host", models.CharField(default="localhost", max_length=100)),
                ("db_port", models.IntegerField(default=5432)),
                ("systemd_service", models.CharField(blank=True, max_length=100)),
                ("gunicorn_bind", models.CharField(default="unix:/run/gunicorn/{slug}.sock", max_length=100)),
                ("gunicorn_workers", models.IntegerField(default=3)),
                ("nginx_conf_path", models.CharField(blank=True, max_length=500)),
                ("domain", models.CharField(blank=True, max_length=253)),
                ("port", models.IntegerField(blank=True, null=True)),
                ("django_settings_module", models.CharField(default="config.settings.production", max_length=200)),
                ("django_wsgi_module", models.CharField(default="config.wsgi:application", max_length=200)),
                ("secret_key", models.CharField(blank=True, max_length=200)),
                ("health_check_url", models.CharField(blank=True, max_length=500)),
                ("last_health_check", models.DateTimeField(blank=True, null=True)),
                ("is_healthy", models.BooleanField(blank=True, null=True)),
                ("tags", models.CharField(blank=True, help_text="Comma-separated tags", max_length=200)),
                ("notes", models.TextField(blank=True)),
                ("owner", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="owned_projects", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Project",
                "verbose_name_plural": "Projects",
                "ordering": ["-created_at"],
            },
        ),
    ]
