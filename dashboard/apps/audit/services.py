"""
apps.audit — Service Layer
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)


class AuditService:
    """Creates audit log entries. Called from all service layer methods."""

    def log(
        self,
        *,
        user=None,
        action: str,
        resource_type: str = "",
        resource_id: str = "",
        resource_name: str = "",
        ip_address: str | None = None,
        user_agent: str = "",
        meta: dict[str, Any] | None = None,
    ) -> None:
        """
        Create an audit log entry.

        Args:
            user: The EkafyUser performing the action (or None for system).
            action: Dot-notation action string (e.g. 'project.deployed').
            resource_type: Type of affected resource (e.g. 'project').
            resource_id: ID of affected resource.
            resource_name: Human-readable name of resource.
            ip_address: IP address of the actor.
            user_agent: User-Agent string.
            meta: Additional arbitrary metadata dict.
        """
        from .models import AuditLog

        try:
            AuditLog.objects.create(
                user=user,
                username_snapshot=user.username if user else "system",
                action=action,
                resource_type=resource_type,
                resource_id=str(resource_id),
                resource_name=resource_name,
                ip_address=ip_address,
                user_agent=user_agent,
                meta=meta or {},
            )
        except Exception as exc:  # noqa: BLE001
            # Never let audit logging block the main operation
            logger.error("Failed to write audit log (action=%s): %s", action, exc)

    def log_from_request(self, request, *, action: str, **kwargs) -> None:
        """Convenience method: extract user and IP from a Django request."""
        ip = self._get_client_ip(request)
        ua = request.META.get("HTTP_USER_AGENT", "")
        self.log(
            user=request.user if request.user.is_authenticated else None,
            action=action,
            ip_address=ip,
            user_agent=ua,
            **kwargs,
        )

    @staticmethod
    def _get_client_ip(request) -> str | None:
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")
