"""
EKAFY — Development Settings
"""
from .base import *  # noqa: F401, F403

DEBUG = True
SECRET_KEY = "dev-insecure-secret-key-change-in-prod-ekafy-2024"  # noqa: S105
ALLOWED_HOSTS = ["*"]

# ─── Development Database (local PostgreSQL or SQLite fallback) ───────────────
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "ekafy_dev",
        "USER": "postgres",
        "PASSWORD": "postgres",
        "HOST": "localhost",
        "PORT": "5432",
    }
}

# ─── Email (console output) ───────────────────────────────────────────────────
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ─── Django Debug Toolbar ─────────────────────────────────────────────────────
try:
    import debug_toolbar  # noqa: F401
    INSTALLED_APPS = INSTALLED_APPS + ["debug_toolbar"]  # noqa: F405
    MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE  # noqa: F405
    INTERNAL_IPS = ["127.0.0.1"]
except ImportError:
    pass

# ─── Development EKAFY Paths ─────────────────────────────────────────────────
EKAFY_BASE_DIR = "/tmp/ekafy_dev"  # noqa: S108
EKAFY_PROJECTS_DIR = "/tmp/ekafy_dev/projects"  # noqa: S108
EKAFY_LOGS_DIR = "/tmp/ekafy_dev/logs"  # noqa: S108
EKAFY_BACKUPS_DIR = "/tmp/ekafy_dev/backups"  # noqa: S108
EKAFY_DEPLOYMENTS_DIR = "/tmp/ekafy_dev/deployments"  # noqa: S108
EKAFY_SCRIPTS_DIR = str(BASE_DIR / "scripts")  # noqa: F405

# ─── Logging ──────────────────────────────────────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name}: {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG",
    },
    "loggers": {
        "django.db.backends": {
            "handlers": ["console"],
            "level": "WARNING",
        },
    },
}
