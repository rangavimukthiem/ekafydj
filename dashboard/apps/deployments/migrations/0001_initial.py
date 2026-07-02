import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("projects", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Deployment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("running", "Running"), ("success", "Success"), ("failed", "Failed"), ("rolled_back", "Rolled Back")], db_index=True, default="pending", max_length=20)),
                ("commit_hash", models.CharField(blank=True, max_length=40)),
                ("commit_message", models.TextField(blank=True)),
                ("commit_author", models.CharField(blank=True, max_length=200)),
                ("git_branch", models.CharField(blank=True, max_length=100)),
                ("started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("log", models.TextField(blank=True)),
                ("task_id", models.CharField(blank=True, db_index=True, max_length=255)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="deployments", to="projects.project")),
                ("rollback_of", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="rollbacks", to="deployments.deployment")),
                ("triggered_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="triggered_deployments", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Deployment",
                "verbose_name_plural": "Deployments",
                "ordering": ["-created_at"],
            },
        ),
    ]
