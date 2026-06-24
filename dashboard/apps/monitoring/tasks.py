"""
apps.monitoring — Celery Tasks
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="monitoring.collect_system_metrics")
def collect_system_metrics() -> dict:
    """Collect system-wide CPU/RAM/disk metrics. Runs every 60s."""
    from .services import MonitoringService
    svc = MonitoringService()
    return svc.collect_system_metrics()


@shared_task(name="monitoring.check_project_health")
def check_project_health() -> dict:
    """Run HTTP health checks for all active projects. Runs every 5 min."""
    from .services import MonitoringService
    from apps.projects.models import Project

    svc = MonitoringService()
    results = {}
    projects = Project.objects.filter(
        status="active",
        health_check_url__isnull=False,
    ).exclude(health_check_url="")

    for project in projects:
        try:
            result = svc.check_project_health(project)
            results[project.slug] = result
        except Exception as exc:  # noqa: BLE001
            logger.warning("Health check failed for %s: %s", project.name, exc)
            results[project.slug] = {"status": "error", "error": str(exc)}

    return results


@shared_task(name="monitoring.cleanup_old_metrics")
def cleanup_old_metrics() -> dict:
    """Remove metric records older than 30 days. Runs daily."""
    from .services import MonitoringService
    svc = MonitoringService()
    deleted = svc.cleanup_old_metrics(days=30)
    logger.info("Cleaned up %d old metric records", deleted)
    return {"deleted": deleted}
