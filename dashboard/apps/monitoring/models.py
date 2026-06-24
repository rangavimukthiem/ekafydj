"""
apps.monitoring — System Metric Model
"""
from django.db import models
from apps.projects.models import Project


class SystemMetric(models.Model):
    """Point-in-time system resource snapshot."""

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    # System-wide
    cpu_percent = models.FloatField()
    memory_total = models.BigIntegerField()   # bytes
    memory_used = models.BigIntegerField()    # bytes
    memory_percent = models.FloatField()
    disk_total = models.BigIntegerField()     # bytes
    disk_used = models.BigIntegerField()      # bytes
    disk_percent = models.FloatField()
    load_avg_1 = models.FloatField(default=0)
    load_avg_5 = models.FloatField(default=0)
    load_avg_15 = models.FloatField(default=0)

    class Meta:
        verbose_name = "System Metric"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self) -> str:
        return f"Metric @ {self.timestamp:%Y-%m-%d %H:%M} cpu={self.cpu_percent}%"


class ProjectHealthCheck(models.Model):
    """HTTP health check result for a managed project."""

    class Status(models.TextChoices):
        HEALTHY = "healthy", "Healthy"
        UNHEALTHY = "unhealthy", "Unhealthy"
        UNKNOWN = "unknown", "Unknown"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="health_checks",
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.UNKNOWN)
    response_time_ms = models.IntegerField(null=True, blank=True)
    http_status_code = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        verbose_name = "Project Health Check"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["project", "timestamp"]),
        ]

    def __str__(self) -> str:
        return f"{self.project.name} [{self.status}] @ {self.timestamp:%H:%M}"
