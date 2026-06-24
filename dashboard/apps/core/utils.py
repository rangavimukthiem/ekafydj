"""
apps.core — Utilities
Shell runner, path helpers, slug generation.
"""
import logging
import re
import subprocess
from pathlib import Path
from typing import Optional

from django.conf import settings

from .exceptions import ScriptExecutionError

logger = logging.getLogger(__name__)


def run_command(
    cmd: list[str] | str,
    *,
    cwd: Optional[str | Path] = None,
    timeout: int = 300,
    capture: bool = True,
    env: Optional[dict] = None,
) -> subprocess.CompletedProcess:
    """
    Run a shell command safely.

    Args:
        cmd: Command as list of strings or a shell string.
        cwd: Working directory.
        timeout: Timeout in seconds (default 300).
        capture: Whether to capture stdout/stderr.
        env: Optional environment variables dict.

    Returns:
        CompletedProcess instance.

    Raises:
        ScriptExecutionError: If the command returns a non-zero exit code.
    """
    is_shell = isinstance(cmd, str)
    logger.debug("Running command: %s (cwd=%s)", cmd, cwd)

    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            timeout=timeout,
            capture_output=capture,
            text=True,
            shell=is_shell,
            env=env,
        )
    except subprocess.TimeoutExpired as exc:
        raise ScriptExecutionError(
            f"Command timed out after {timeout}s: {cmd}",
            returncode=-1,
        ) from exc
    except FileNotFoundError as exc:
        raise ScriptExecutionError(
            f"Command not found: {cmd}",
            returncode=-1,
        ) from exc

    if result.returncode != 0:
        logger.error(
            "Command failed (rc=%d): %s\nstderr: %s",
            result.returncode,
            cmd,
            result.stderr,
        )
        raise ScriptExecutionError(
            f"Command failed with exit code {result.returncode}: {cmd}",
            returncode=result.returncode,
            stderr=result.stderr,
        )

    logger.debug("Command succeeded: %s", cmd)
    return result


def run_script(script_name: str, args: list[str] | None = None) -> subprocess.CompletedProcess:
    """
    Run a named EKAFY bash script from EKAFY_SCRIPTS_DIR.

    Args:
        script_name: Filename of the script (e.g. 'deploy_project.sh').
        args: Additional arguments to pass to the script.

    Returns:
        CompletedProcess instance.
    """
    scripts_dir = Path(settings.EKAFY_SCRIPTS_DIR)
    script_path = scripts_dir / script_name

    if not script_path.exists():
        raise ScriptExecutionError(f"Script not found: {script_path}")

    cmd = ["bash", str(script_path)] + (args or [])
    return run_command(cmd)


def slugify(text: str) -> str:
    """Convert a string to a URL and filesystem-safe slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    text = re.sub(r"^-+|-+$", "", text)
    return text


def get_project_dir(project_slug: str) -> Path:
    """Return the filesystem path for a managed project."""
    return Path(settings.EKAFY_PROJECTS_DIR) / project_slug


def get_project_repo_dir(project_slug: str) -> Path:
    """Return the git repo directory inside a managed project."""
    return get_project_dir(project_slug) / "repo"


def get_project_venv_dir(project_slug: str) -> Path:
    """Return the venv directory inside a managed project."""
    return get_project_dir(project_slug) / ".venv"


def get_project_log_path(project_slug: str) -> Path:
    """Return the log file path for a managed project."""
    return Path(settings.EKAFY_LOGS_DIR) / f"{project_slug}.log"


def format_bytes(num_bytes: int) -> str:
    """Human-readable byte size."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if num_bytes < 1024:
            return f"{num_bytes:.1f} {unit}"
        num_bytes //= 1024
    return f"{num_bytes:.1f} PB"


def ensure_dirs(*paths: str | Path) -> None:
    """Ensure a list of directories exist."""
    for path in paths:
        Path(path).mkdir(parents=True, exist_ok=True)
