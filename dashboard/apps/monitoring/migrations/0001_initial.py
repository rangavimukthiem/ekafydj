import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("projects", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SystemMetric",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("cpu_percent", models.FloatField()),
                ("memory_total", models.BigIntegerField()),
                ("memory_used", models.BigIntegerField()),
                ("memory_percent", models.FloatField()),
                ("disk_total", models.BigIntegerField()),
                ("disk_used", models.BigIntegerField()),
                ("disk_percent", models.FloatField()),
                ("load_avg_1", models.FloatField(default=0)),
                ("load_avg_5", models.FloatField(default=0)),
                ("load_avg_15", models.FloatField(default=0)),
            ],
            options={
                "verbose_name": "System Metric",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.CreateModel(
            name="ProjectHealthCheck",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("timestamp", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("status", models.CharField(choices=[("healthy", "Healthy"), ("unhealthy", "Unhealthy"), ("unknown", "Unknown")], default="unknown", max_length=20)),
                ("response_time_ms", models.IntegerField(blank=True, null=True)),
                ("http_status_code", models.IntegerField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("project", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="health_checks", to="projects.project")),
            ],
            options={
                "verbose_name": "Project Health Check",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="systemmetric",
            index=models.Index(fields=["timestamp"], name="monitoring__timesta_8de2c5_idx"),
        ),
        migrations.AddIndex(
            model_name="projecthealthcheck",
            index=models.Index(fields=["project", "timestamp"], name="monitoring__project_32cf3a_idx"),
        ),
    ]
