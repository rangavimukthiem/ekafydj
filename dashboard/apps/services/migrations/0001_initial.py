import uuid
import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ServiceStatus",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("service_name", models.CharField(max_length=100)),
                ("state", models.CharField(choices=[("active", "Active"), ("inactive", "Inactive"), ("failed", "Failed"), ("unknown", "Unknown")], db_index=True, default="unknown", max_length=20)),
                ("return_code", models.IntegerField(default=0)),
                ("output", models.TextField(blank=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="service_statuses", to="projects.project")),
            ],
            options={
                "verbose_name": "Service Status",
                "verbose_name_plural": "Service Statuses",
                "ordering": ["-created_at"],
            },
        ),
    ]
