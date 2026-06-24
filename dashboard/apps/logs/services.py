"""
apps.logs — Log Service
Reads journalctl and file-based logs for managed projects.
"""
import logging
import subprocess
from pathlib import Path
from typing import Generator

from django.conf import settings

logger = logging.getLogger(__name__)


class LogService:
    """Provides access to systemd journal and file-based logs."""

    def get_journal_logs(
        self,
        service_name: str,
        *,
        lines: int = 200,
        since: str = "",
        until: str = "",
        search: str = "",
    ) -> str:
        """
        Retrieve journalctl output for a given service.

        Args:
            service_name: Systemd unit name (e.g. 'ekafy-myapp.service').
            lines: Number of recent lines to return.
            since: journalctl --since string (e.g. '1 hour ago').
            until: journalctl --until string.
            search: Grep pattern applied to output.

        Returns:
            Log content as a string.
        """
        cmd = [
            "sudo", "journalctl",
            "-u", service_name,
            f"-n", str(lines),
            "--no-pager",
            "--output=short-iso",
        ]
        if since:
            cmd += ["--since", since]
        if until:
            cmd += ["--until", until]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            output = result.stdout
            if search:
                output = "\n".join(
                    line for line in output.splitlines() if search.lower() in line.lower()
                )
            return output
        except subprocess.TimeoutExpired:
            return "Log retrieval timed out."
        except Exception as exc:  # noqa: BLE001
            return f"Error retrieving logs: {exc}"

    def get_file_logs(
        self,
        log_path: str,
        *,
        lines: int = 200,
        search: str = "",
    ) -> str:
        """Read the last N lines from a log file."""
        path = Path(log_path)
        if not path.exists():
            return f"Log file not found: {log_path}"

        try:
            result = subprocess.run(
                ["tail", f"-n{lines}", str(path)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            output = result.stdout
            if search:
                output = "\n".join(
                    line for line in output.splitlines() if search.lower() in line.lower()
                )
            return output
        except Exception as exc:  # noqa: BLE001
            return f"Error reading log file: {exc}"

    def stream_journal(self, service_name: str) -> Generator[str, None, None]:
        """
        Generator that yields new log lines from journalctl -f.
        Used for SSE streaming in views.
        """
        try:
            process = subprocess.Popen(
                ["sudo", "journalctl", "-f", "-u", service_name, "--no-pager", "--output=short-iso"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            for line in process.stdout:
                yield line.rstrip()
        except Exception as exc:  # noqa: BLE001
            yield f"Stream error: {exc}"

    def get_nginx_access_log(self, project_slug: str, lines: int = 200) -> str:
        """Read nginx access log for a project."""
        log_path = f"/var/log/nginx/ekafy-{project_slug}-access.log"
        return self.get_file_logs(log_path, lines=lines)

    def get_nginx_error_log(self, project_slug: str, lines: int = 200) -> str:
        """Read nginx error log for a project."""
        log_path = f"/var/log/nginx/ekafy-{project_slug}-error.log"
        return self.get_file_logs(log_path, lines=lines)

    def get_ekafy_dashboard_log(self, lines: int = 200) -> str:
        """Read the EKAFY dashboard's own log file."""
        log_path = f"{settings.EKAFY_LOGS_DIR}/ekafy_dashboard.log"
        return self.get_file_logs(log_path, lines=lines)
