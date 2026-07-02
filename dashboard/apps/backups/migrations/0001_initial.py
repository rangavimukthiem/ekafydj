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
            name="Backup",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("backup_type", models.CharField(choices=[("db", "Database"), ("media", "Media Files"), ("full", "Full (DB + Media)")], default="db", max_length=10)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("running", "Running"), ("success", "Success"), ("failed", "Failed"), ("uploading", "Uploading to S3")], db_index=True, default="pending", max_length=15)),
                ("file_path", models.CharField(blank=True, max_length=500)),
                ("file_name", models.CharField(blank=True, max_length=255)),
                ("file_size", models.BigIntegerField(blank=True, null=True)),
                ("s3_key", models.CharField(blank=True, max_length=500)),
                ("s3_url", models.CharField(blank=True, max_length=1000)),
                ("log", models.TextField(blank=True)),
                ("task_id", models.CharField(blank=True, max_length=255)),
                ("is_scheduled", models.BooleanField(default=False)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="backups", to="projects.project")),
                ("triggered_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="triggered_backups", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "verbose_name": "Backup",
                "verbose_name_plural": "Backups",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="BackupSchedule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("enabled", models.BooleanField(default=True)),
                ("backup_type", models.CharField(choices=[("db", "Database"), ("media", "Media Files"), ("full", "Full (DB + Media)")], default="db", max_length=10)),
                ("cron_expression", models.CharField(default="0 2 * * *", max_length=100)),
                ("retention_days", models.IntegerField(default=30)),
                ("upload_to_s3", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("project", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="backup_schedule", to="projects.project")),
            ],
            options={
                "verbose_name": "Backup Schedule",
            },
        ),
    ]
