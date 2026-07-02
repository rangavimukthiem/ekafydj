"""
EKAFY — Celery Application
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")

app = Celery("ekafy")

# Load config from Django settings, namespace CELERY
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f"Request: {self.request!r}")


# ─── Periodic Task Schedule ───────────────────────────────────────────────────
app.conf.beat_schedule = {
    # Collect system metrics every minute
    "collect-system-metrics": {
        "task": "monitoring.collect_system_metrics",
        "schedule": 60.0,  # every 60 seconds
    },
    # Check project health every 5 minutes
    "check-project-health": {
        "task": "monitoring.check_project_health",
        "schedule": 300.0,  # every 5 minutes
    },
    # Run scheduled backups (checks DB for due schedules)
    "run-scheduled-backups": {
        "task": "backups.run_scheduled_backups",
        "schedule": crontab(minute="*/30"),
    },
    # Cleanup old deployment logs (older than 90 days)
    "cleanup-old-deployments": {
        "task": "deployments.cleanup_old_deployment_logs",
        "schedule": crontab(hour=2, minute=0),
    },
    # Cleanup old metrics (older than 30 days)
    "cleanup-old-metrics": {
        "task": "monitoring.cleanup_old_metrics",
        "schedule": crontab(hour=3, minute=0),
    },
}
