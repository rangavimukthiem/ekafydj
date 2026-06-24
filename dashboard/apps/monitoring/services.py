"""
apps.monitoring — Service Layer
Collects CPU/RAM/disk metrics and performs HTTP health checks.
"""
import logging
import time
from datetime import datetime, timezone, timedelta

import requests

logger = logging.getLogger(__name__)


class MonitoringService:
    """Collects system metrics and performs project health checks."""

    def collect_system_metrics(self) -> dict:
        """
        Gather CPU, memory, disk, and load average from the OS.
        Returns a dict and persists to SystemMetric.
        """
        try:
            import psutil
        except ImportError:
            logger.error("psutil not installed — cannot collect system metrics")
            return {}

        cpu = psutil.cpu_percent(interval=1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        load = psutil.getloadavg()

        from .models import SystemMetric
        metric = SystemMetric.objects.create(
            cpu_percent=cpu,
            memory_total=mem.total,
            memory_used=mem.used,
            memory_percent=mem.percent,
            disk_total=disk.total,
            disk_used=disk.used,
            disk_percent=disk.percent,
            load_avg_1=load[0],
            load_avg_5=load[1],
            load_avg_15=load[2],
        )

        return {
            "cpu_percent": cpu,
            "memory_percent": mem.percent,
            "disk_percent": disk.percent,
            "load_avg_1": load[0],
            "metric_id": metric.pk,
        }

    def get_latest_metric(self) -> dict | None:
        """Return the most recent system metric as a dict."""
        from .models import SystemMetric
        from apps.core.utils import format_bytes

        metric = SystemMetric.objects.order_by("-timestamp").first()
        if not metric:
            return None

        return {
            "cpu_percent": metric.cpu_percent,
            "memory_percent": metric.memory_percent,
            "memory_used": format_bytes(metric.memory_used),
            "memory_total": format_bytes(metric.memory_total),
            "disk_percent": metric.disk_percent,
            "disk_used": format_bytes(metric.disk_used),
            "disk_total": format_bytes(metric.disk_total),
            "load_avg_1": metric.load_avg_1,
            "load_avg_5": metric.load_avg_5,
            "load_avg_15": metric.load_avg_15,
            "timestamp": metric.timestamp.isoformat(),
        }

    def get_metric_history(self, hours: int = 6) -> list[dict]:
        """Return time-series metrics for the past N hours (for charts)."""
        from .models import SystemMetric

        since = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
        metrics = SystemMetric.objects.filter(
            timestamp__gte=since
        ).order_by("timestamp").values(
            "timestamp", "cpu_percent", "memory_percent", "disk_percent", "load_avg_1"
        )

        return [
            {
                "t": m["timestamp"].isoformat(),
                "cpu": m["cpu_percent"],
                "mem": m["memory_percent"],
                "disk": m["disk_percent"],
                "load": m["load_avg_1"],
            }
            for m in metrics
        ]

    def check_project_health(self, project) -> dict:
        """
        Perform an HTTP health check for a project.
        Updates project.is_healthy and creates a ProjectHealthCheck record.
        """
        from .models import ProjectHealthCheck
        from apps.projects.repositories import ProjectRepository

        if not project.health_check_url:
            return {"status": "unknown", "reason": "No health check URL configured"}

        status = ProjectHealthCheck.Status.UNKNOWN
        response_time_ms = None
        http_code = None
        error_msg = ""

        try:
            start = time.monotonic()
            resp = requests.get(project.health_check_url, timeout=10, allow_redirects=True)
            elapsed = int((time.monotonic() - start) * 1000)

            response_time_ms = elapsed
            http_code = resp.status_code
            status = ProjectHealthCheck.Status.HEALTHY if resp.status_code < 400 else ProjectHealthCheck.Status.UNHEALTHY

        except requests.Timeout:
            error_msg = "Health check timed out"
            status = ProjectHealthCheck.Status.UNHEALTHY
        except requests.ConnectionError as exc:
            error_msg = f"Connection error: {exc}"
            status = ProjectHealthCheck.Status.UNHEALTHY
        except Exception as exc:  # noqa: BLE001
            error_msg = str(exc)
            status = ProjectHealthCheck.Status.UNHEALTHY

        ProjectHealthCheck.objects.create(
            project=project,
            status=status,
            response_time_ms=response_time_ms,
            http_status_code=http_code,
            error_message=error_msg,
        )

        # Update project health flag
        is_healthy = status == ProjectHealthCheck.Status.HEALTHY
        ProjectRepository.update(project, is_healthy=is_healthy, last_health_check=datetime.now(tz=timezone.utc))

        return {
            "status": status,
            "response_time_ms": response_time_ms,
            "http_status_code": http_code,
            "error": error_msg,
        }

    def cleanup_old_metrics(self, days: int = 30) -> int:
        """Remove metric records older than N days."""
        from .models import SystemMetric, ProjectHealthCheck

        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days)
        deleted_metrics, _ = SystemMetric.objects.filter(timestamp__lt=cutoff).delete()
        deleted_checks, _ = ProjectHealthCheck.objects.filter(timestamp__lt=cutoff).delete()
        return deleted_metrics + deleted_checks
