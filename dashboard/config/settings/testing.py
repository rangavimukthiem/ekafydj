"""
EKAFY — Testing Settings
"""
from .base import *  # noqa: F401, F403

DEBUG = False
SECRET_KEY = "test-secret-key-not-for-production"  # noqa: S105

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Fast password hasher for tests
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Disable migrations for tests
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Disable Celery in tests (run tasks synchronously)
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

# Use in-memory cache
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}

# EKAFY dev paths
EKAFY_BASE_DIR = "/tmp/ekafy_test"  # noqa: S108
EKAFY_PROJECTS_DIR = "/tmp/ekafy_test/projects"  # noqa: S108
EKAFY_LOGS_DIR = "/tmp/ekafy_test/logs"  # noqa: S108
EKAFY_BACKUPS_DIR = "/tmp/ekafy_test/backups"  # noqa: S108
EKAFY_DEPLOYMENTS_DIR = "/tmp/ekafy_test/deployments"  # noqa: S108
EKAFY_SCRIPTS_DIR = str(BASE_DIR / "scripts")  # noqa: F405
