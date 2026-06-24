"""
apps.core — Domain Exceptions
All EKAFY-specific exceptions live here.
"""


class EkafyError(Exception):
    """Base exception for all EKAFY errors."""

    def __init__(self, message: str = "An unexpected EKAFY error occurred."):
        self.message = message
        super().__init__(self.message)


class ProjectError(EkafyError):
    """Raised for project-related errors."""


class ProjectAlreadyExistsError(ProjectError):
    """Raised when creating a project with a duplicate slug."""


class ProjectNotFoundError(ProjectError):
    """Raised when a project cannot be found."""


class DeploymentError(EkafyError):
    """Raised for deployment-related errors."""


class DeploymentInProgressError(DeploymentError):
    """Raised when a deployment is already running for a project."""


class ServiceControlError(EkafyError):
    """Raised when systemd service control fails."""


class BackupError(EkafyError):
    """Raised for backup-related errors."""


class BackupNotFoundError(BackupError):
    """Raised when a backup file cannot be found."""


class LogError(EkafyError):
    """Raised for log access errors."""


class MonitoringError(EkafyError):
    """Raised for monitoring collection errors."""


class PermissionDeniedError(EkafyError):
    """Raised when a user lacks permission for an operation."""


class ScriptExecutionError(EkafyError):
    """Raised when a shell script exits with a non-zero code."""

    def __init__(self, message: str, returncode: int = -1, stderr: str = ""):
        self.returncode = returncode
        self.stderr = stderr
        super().__init__(message)
